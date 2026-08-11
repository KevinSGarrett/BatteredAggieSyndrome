from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Iterable


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("advanced-game snapshot materialization requires the optional data-engineering environment") from exc
    return polars


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dataframe_record_sha256(frame: Any) -> str:
    digest = hashlib.sha256()
    for row in frame.iter_rows(named=True):
        digest.update(canonical_json_bytes(row) + b"\n")
    return digest.hexdigest()


def _duplicate_groups(frame: Any, keys: Iterable[str]) -> int:
    return frame.group_by(list(keys)).len().filter(_polars().col("len") > 1).height


def _validate_contract_authority(contract: dict[str, Any]) -> None:
    authority = contract["authority"]
    if authority.get("candidate_snapshot_materialization") is not True:
        raise ValueError("advanced-game candidate snapshot authority is not explicitly enabled")
    closed = (
        "immutable_raw_capture_mutation", "canonical_entity_mutation", "historical_pit_admission",
        "preliminary_chronological_replay_admission", "protected_training_admission",
        "protected_evaluation_admission", "champion_or_production_promotion", "forecast_publication",
    )
    if any(authority.get(key) is not False for key in closed):
        raise ValueError("advanced-game authority boundary is open beyond capture-time candidate use")


def _flatten_paths(value: Any, prefix: str = "") -> tuple[set[str], dict[str, Any]]:
    structural: set[str] = set()
    leaves: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            structural.add(path)
            if isinstance(child, dict):
                nested_structural, nested_leaves = _flatten_paths(child, path)
                structural.update(nested_structural)
                leaves.update(nested_leaves)
            else:
                leaves[path] = child
    return structural, leaves


def _load_candidates(data_root: Path, contract: dict[str, Any]) -> tuple[Any, dict[str, Any], list[dict[str, Any]]]:
    pl = _polars()
    source, expected = contract["source_contract"], contract["acceptance"]
    manifest_path = data_root / Path(source["candidate_manifest_relative_path"])
    if not manifest_path.is_file() or sha256_file(manifest_path) != source["candidate_manifest_sha256"]:
        raise ValueError("advanced-game candidate manifest identity drift")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_identity") != source["candidate_dataset_identity"]:
        raise ValueError("advanced-game candidate dataset identity drift")
    if manifest.get("domain") != "advanced_game_statistics" or manifest.get("grain") != "GAME_TEAM_ADVANCED_OFFENSE_DEFENSE_STAT_MAP":
        raise ValueError("advanced-game candidate domain or grain drift")
    payloads = sorted(manifest.get("payloads", []), key=lambda item: int(item["season"]))
    if len(payloads) != expected["expected_source_files"]:
        raise ValueError("advanced-game candidate file count drift")
    required = set(contract["disposition"]["snapshot_fields"]) | {"current_canonical_advanced_id", "current_capture_exact_match", "admission_state"}
    payload_root = data_root / Path(source["candidate_payload_root"])
    frames, profiles = [], []
    for item in payloads:
        season, path = int(item["season"]), payload_root / Path(item["name"])
        if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256_file(path) != item["sha256"]:
            raise ValueError(f"advanced-game candidate payload identity drift for {season}")
        frame = pl.read_parquet(path)
        if frame.height != int(item["rows"]) or set(frame.columns) < required:
            raise ValueError(f"advanced-game candidate population or schema drift for {season}")
        if frame["season"].n_unique() != 1 or int(frame["season"][0]) != season:
            raise ValueError(f"advanced-game candidate season drift for {season}")
        if frame.filter(pl.col("historical_known_at_state") != source["historical_known_at_state"]).height:
            raise ValueError(f"advanced-game historical known-at state drift for {season}")
        profiles.append({
            "season": season, "rows": frame.height, "bytes": path.stat().st_size, "sha256": item["sha256"],
            "physical_schema_sha256": stable_hash(sorted((name, str(dtype)) for name, dtype in frame.schema.items())),
            "minimum_capture_known_at_utc": frame["capture_known_at_utc"].min(),
            "maximum_capture_known_at_utc": frame["capture_known_at_utc"].max(),
        })
        frames.append(frame)
    return pl.concat(frames, how="diagonal_relaxed").sort(["season", "source_game_id", "source_team_normalized", "observation_id"]), manifest, profiles


def _validate_source_values(candidates: Any, contract: dict[str, Any]) -> dict[str, Any]:
    expected = contract["acceptance"]
    structural_paths: set[str] = set()
    leaf_paths: set[str] = set()
    missing_leaf_cells = 0
    for row in candidates.select("offense_json", "offense_sha256", "defense_json", "defense_sha256").iter_rows(named=True):
        for side in ("offense", "defense"):
            raw = row[f"{side}_json"]
            if hashlib.sha256(raw.encode("utf-8")).hexdigest() != row[f"{side}_sha256"]:
                raise ValueError(f"advanced-game {side} hash drift")
            value = json.loads(raw)
            structure, leaves = _flatten_paths(value, side)
            structure.add(side)
            structural_paths.update(structure)
            leaf_paths.update(leaves)
            missing_leaf_cells += sum(value is None for value in leaves.values())
    if len(structural_paths) != expected["expected_field_path_count"] or len(leaf_paths) != expected["expected_leaf_path_count"]:
        raise ValueError("advanced-game nested structural path drift")
    leaf_cells = candidates.height * len(leaf_paths)
    if leaf_cells != expected["expected_source_leaf_cells"] or missing_leaf_cells != expected["expected_missing_leaf_cells"]:
        raise ValueError("advanced-game leaf population or missingness drift")
    reciprocal_games = 0
    for group in candidates.partition_by(["season", "source_game_id"], maintain_order=True):
        if group.height != 2:
            raise ValueError("advanced-game source game does not have exactly two team rows")
        rows = group.select("offense_json", "defense_json").to_dicts()
        if rows[0]["offense_json"] == rows[1]["defense_json"] and rows[1]["offense_json"] == rows[0]["defense_json"]:
            reciprocal_games += 1
    if reciprocal_games != expected["expected_reciprocal_games"]:
        raise ValueError("advanced-game offense/defense reciprocity drift")
    return {
        "field_paths": sorted(structural_paths), "field_path_count": len(structural_paths),
        "leaf_paths": sorted(leaf_paths), "leaf_path_count": len(leaf_paths), "leaf_cells": leaf_cells,
        "missing_leaf_cells": missing_leaf_cells, "reciprocal_games": reciprocal_games,
    }


def _disposition(candidates: Any, contract: dict[str, Any]) -> tuple[Any, Any, dict[str, Any]]:
    pl = _polars()
    rules, expected = contract["disposition"], contract["acceptance"]
    eligible = pl.col("reconciliation_disposition").is_in(rules["eligible_reconciliation_dispositions"])
    exact_source, nonadmitted = candidates.filter(eligible), candidates.filter(~eligible)
    if exact_source.height != expected["expected_exact_rows"] or nonadmitted.height != expected["expected_nonadmitted_rows"]:
        raise ValueError("advanced-game disposition population drift")
    if exact_source.filter(pl.col("canonical_game_id_candidate").is_null() | pl.col("canonical_team_id_candidate").is_null()).height:
        raise ValueError("exact advanced-game disposition lacks canonical game/team candidate")
    if nonadmitted.filter(~pl.col("reconciliation_disposition").is_in(rules["nonadmitted_reconciliation_dispositions"])).height:
        raise ValueError("unexpected advanced-game nonadmitted disposition")
    if _duplicate_groups(candidates, ["observation_id"]) != expected["expected_duplicate_observation_ids"]:
        raise ValueError("duplicate advanced-game observation identity")
    if _duplicate_groups(exact_source, rules["natural_key"]) != expected["expected_duplicate_natural_keys"]:
        raise ValueError("duplicate exact advanced-game natural key")
    collision = nonadmitted.filter(pl.col("reconciliation_disposition") == "CANDIDATE_TEAM_BOX_GAME_TEAM_LINKED_ADVANCED_STATS")
    if collision.height != expected["expected_team_box_only_collision_rows"] or collision["source_game_id"].n_unique() != expected["expected_team_box_only_collision_games"]:
        raise ValueError("team-box-only canonical collision population drift")
    if set(rules["forbidden_snapshot_fields"]) & set(rules["snapshot_fields"]):
        raise ValueError("forbidden advanced-game fields configured for snapshot")
    snapshot = exact_source.select(rules["snapshot_fields"]).with_columns(
        pl.lit(True).alias("capture_time_candidate_only"), pl.lit(False).alias("historical_pit_eligible"),
        pl.lit(False).alias("preliminary_replay_eligible"), pl.lit(False).alias("protected_eligible"),
    ).sort(["season", "source_game_id", "canonical_team_id_candidate"])
    nonadmitted = nonadmitted.with_columns(
        pl.when(pl.col("reconciliation_disposition") == "CANDIDATE_TEAM_BOX_GAME_TEAM_LINKED_ADVANCED_STATS")
        .then(pl.lit("TEAM_BOX_ONLY_LINK_WITH_DUPLICATE_CANONICAL_GAME_TEAM_COLLISION"))
        .otherwise(pl.lit("SOURCE_LEVEL_ADVANCED_STATS_WITHOUT_EXACT_CANONICAL_GAME_TEAM_RECONCILIATION"))
        .alias("nonadmission_reason"),
        pl.lit(False).alias("historical_pit_eligible"), pl.lit(False).alias("protected_eligible"),
    ).sort(["season", "source_game_id", "source_team_normalized", "observation_id"])
    def by_season(frame: Any) -> dict[str, int]:
        return {str(row["season"]): int(row["len"]) for row in frame.group_by("season").len().sort("season").iter_rows(named=True)}
    profile = {
        "source_rows": candidates.height, "source_games": candidates["source_game_id"].n_unique(),
        "exact_rows": snapshot.height, "exact_games": snapshot["source_game_id"].n_unique(), "exact_teams": snapshot["canonical_team_id_candidate"].n_unique(),
        "nonadmitted_rows": nonadmitted.height, "nonadmitted_games": nonadmitted["source_game_id"].n_unique(),
        "team_box_link_rows": candidates["team_box_observation_id"].drop_nulls().len(),
        "team_box_outcome_match_rows": candidates.filter(pl.col("team_box_historical_outcome_match") == True).height,
        "team_box_only_collision_rows": collision.height, "team_box_only_collision_games": collision["source_game_id"].n_unique(),
        "disposition_counts": {str(row["reconciliation_disposition"]): int(row["len"]) for row in candidates.group_by("reconciliation_disposition").len().iter_rows(named=True)},
        "exact_by_season": by_season(snapshot), "nonadmitted_by_season": by_season(nonadmitted),
    }
    comparisons = {
        "source_rows": "expected_source_rows", "source_games": "expected_source_games", "exact_rows": "expected_exact_rows", "exact_games": "expected_exact_games",
        "exact_teams": "expected_exact_teams", "nonadmitted_rows": "expected_nonadmitted_rows", "nonadmitted_games": "expected_nonadmitted_games",
        "team_box_link_rows": "expected_team_box_link_rows", "team_box_outcome_match_rows": "expected_team_box_outcome_match_rows",
        "team_box_only_collision_rows": "expected_team_box_only_collision_rows", "team_box_only_collision_games": "expected_team_box_only_collision_games",
    }
    for actual, expected_key in comparisons.items():
        if profile[actual] != expected[expected_key]:
            raise ValueError(f"advanced-game population drift: {actual}")
    for actual, expected_key in (("disposition_counts", "expected_disposition_counts"), ("exact_by_season", "expected_exact_by_season"), ("nonadmitted_by_season", "expected_nonadmitted_by_season")):
        if profile[actual] != expected[expected_key]:
            raise ValueError(f"advanced-game population profile drift: {actual}")
    return snapshot, nonadmitted, profile


def materialize(*, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs" / "historical_advanced_game_snapshot_contract.json"
    contract_bytes, core_path = contract_path.read_bytes(), Path(__file__).resolve()
    contract = json.loads(contract_bytes)
    _validate_contract_authority(contract)
    builder_path = repo_root / "tools" / "build_historical_advanced_game_snapshot.py"
    candidates, candidate_manifest, source_profiles = _load_candidates(input_data_root, contract)
    expected, source = contract["acceptance"], contract["source_contract"]
    if candidates.height != expected["expected_source_rows"] or set(candidates["season"].unique().to_list()) != set(source["source_seasons"]):
        raise ValueError("advanced-game source population or season coverage drift")
    physical_hashes = {item["physical_schema_sha256"] for item in source_profiles}
    if len(physical_hashes) != expected["expected_physical_schema_hashes"]:
        raise ValueError("advanced-game physical schema drift")
    if candidates["capture_known_at_utc"].min() != source["minimum_capture_known_at_utc"] or candidates["capture_known_at_utc"].max() != source["maximum_capture_known_at_utc"]:
        raise ValueError("advanced-game capture-time envelope drift")
    nested_profile = _validate_source_values(candidates, contract)
    snapshot, nonadmitted, population = _disposition(candidates, contract)
    population.update({
        "source_leaf_cells": nested_profile["leaf_cells"], "exact_leaf_cells": snapshot.height * nested_profile["leaf_path_count"],
        "nonadmitted_leaf_cells": nonadmitted.height * nested_profile["leaf_path_count"],
        "field_paths": nested_profile["field_paths"], "field_path_count": nested_profile["field_path_count"],
        "leaf_paths": nested_profile["leaf_paths"], "leaf_path_count": nested_profile["leaf_path_count"],
        "missing_leaf_cells": nested_profile["missing_leaf_cells"], "reciprocal_games": nested_profile["reciprocal_games"],
        "physical_schema_hashes": sorted(physical_hashes),
    })
    for field, expected_key in (("exact_leaf_cells", "expected_exact_leaf_cells"), ("nonadmitted_leaf_cells", "expected_nonadmitted_leaf_cells")):
        if population[field] != expected[expected_key]:
            raise ValueError(f"advanced-game {field} drift")
    record_hashes = {"snapshot": dataframe_record_sha256(snapshot), "nonadmitted": dataframe_record_sha256(nonadmitted)}
    manifest_path_in = input_data_root / Path(source["candidate_manifest_relative_path"])
    identity = stable_hash({
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(), "core_sha256": sha256_file(core_path), "builder_sha256": sha256_file(builder_path),
        "candidate_manifest_sha256": sha256_file(manifest_path_in), "candidate_payload_sha256": [item["sha256"] for item in candidate_manifest["payloads"]],
        "record_hashes": record_hashes, "classification": contract["classification"],
    })
    payload_root = output_data_root / "quarantine" / "historical_capture_time" / "sha256" / identity
    manifest_root = output_data_root / "manifests" / "historical_capture_time" / "sha256" / identity
    payload_root.mkdir(parents=True, exist_ok=True); manifest_root.mkdir(parents=True, exist_ok=True)
    snapshot_path, nonadmitted_path = payload_root / "exact_reconciled_advanced_game_rows.parquet", payload_root / "nonadmitted_advanced_game_rows.parquet"
    snapshot.write_parquet(snapshot_path, compression="zstd", statistics=True)
    nonadmitted.write_parquet(nonadmitted_path, compression="zstd", statistics=True)
    payloads = [
        {"role": "EXACT_RECONCILED_CAPTURE_TIME_ADVANCED_GAME_ROWS", "name": snapshot_path.name, "rows": snapshot.height, "bytes": snapshot_path.stat().st_size, "sha256": sha256_file(snapshot_path), "record_sha256": record_hashes["snapshot"]},
        {"role": "NONADMITTED_ADVANCED_GAME_ROWS", "name": nonadmitted_path.name, "rows": nonadmitted.height, "bytes": nonadmitted_path.stat().st_size, "sha256": sha256_file(nonadmitted_path), "record_sha256": record_hashes["nonadmitted"]},
    ]
    manifest = {
        "schema_version": "1.0.0", "artifact_type": "HISTORICAL_ADVANCED_GAME_CAPTURE_TIME_SNAPSHOT", "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"], "classification": contract["classification"], "dataset_identity": identity, "issued_at_utc": issued_at_utc,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "producer": {"python": sys.version.split()[0], "platform": platform.platform(), "polars": pl.__version__, "core_sha256": sha256_file(core_path), "builder_sha256": sha256_file(builder_path)},
        "input_identities": {"candidate_dataset": source["candidate_dataset_identity"], "candidate_manifest_sha256": source["candidate_manifest_sha256"], "candidate_payload_sha256": [item["sha256"] for item in candidate_manifest["payloads"]], "team_box_snapshot_dataset": source["team_box_snapshot_dataset_identity"]},
        "source_profiles": source_profiles, "population": population,
        "chronology": {"historical_known_at_state": source["historical_known_at_state"], "minimum_capture_known_at_utc": source["minimum_capture_known_at_utc"], "maximum_capture_known_at_utc": source["maximum_capture_known_at_utc"], "historical_publication_time_proved": False, "pre_capture_backcast": False},
        "payloads": payloads, "authority": contract["authority"], "negative_findings": contract["negative_findings"],
        "scientific_nonclaims": {"historical_population_ready": False, "gap_002_resolved": False, "preliminary_model_training_eligible": False, "production_model_ready": False, "trained_production_champion": False, "protected_performance_claimed": False, "tamu_specialization_lift_claimed": False, "bas_or_aggie_excess_result_claimed": False},
    }
    manifest_path = manifest_root / "historical_advanced_game_snapshot_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {"dataset_identity": identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "manifest": manifest, "snapshot_path": str(snapshot_path), "nonadmitted_path": str(nonadmitted_path)}
