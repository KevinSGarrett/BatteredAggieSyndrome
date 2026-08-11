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
        raise RuntimeError("team-box snapshot materialization requires the optional data-engineering environment") from exc
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
        raise ValueError("team-box candidate snapshot authority is not explicitly enabled")
    closed = (
        "immutable_raw_capture_mutation", "canonical_entity_mutation", "historical_pit_admission",
        "preliminary_chronological_replay_admission", "protected_training_admission",
        "protected_evaluation_admission", "champion_or_production_promotion", "forecast_publication",
    )
    if any(authority.get(key) is not False for key in closed):
        raise ValueError("team-box authority boundary is open beyond capture-time candidate use")


def _load_candidates(data_root: Path, contract: dict[str, Any]) -> tuple[Any, dict[str, Any], list[dict[str, Any]]]:
    pl = _polars()
    source = contract["source_contract"]
    manifest_path = data_root / Path(source["candidate_manifest_relative_path"])
    if not manifest_path.is_file() or sha256_file(manifest_path) != source["candidate_manifest_sha256"]:
        raise ValueError("team-box candidate manifest identity drift")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_identity") != source["candidate_dataset_identity"]:
        raise ValueError("team-box candidate dataset identity drift")
    if manifest.get("domain") != "team_box_scores" or manifest.get("grain") != "GAME_TEAM_BOX_WITH_SOURCE_STAT_MAP":
        raise ValueError("team-box candidate domain or grain drift")
    payloads = sorted(manifest.get("payloads", []), key=lambda item: int(item["season"]))
    if len(payloads) != contract["acceptance"]["expected_source_files"]:
        raise ValueError("team-box candidate file count drift")
    payload_root = data_root / Path(source["candidate_payload_root"])
    required = set(contract["disposition"]["snapshot_fields"]) | {
        "current_canonical_team_box_id", "current_capture_points_match", "current_capture_stats_match",
        "current_capture_exact_match", "admission_state",
    }
    frames: list[Any] = []
    profiles: list[dict[str, Any]] = []
    for item in payloads:
        season = int(item["season"])
        path = payload_root / Path(item["name"])
        if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256_file(path) != item["sha256"]:
            raise ValueError(f"team-box candidate payload identity drift for {season}")
        frame = pl.read_parquet(path)
        if frame.height != int(item["rows"]) or set(frame.columns) < required:
            raise ValueError(f"team-box candidate population or schema drift for {season}")
        if frame["season"].n_unique() != 1 or int(frame["season"][0]) != season:
            raise ValueError(f"team-box candidate season drift for {season}")
        if frame.filter(pl.col("historical_known_at_state") != source["historical_known_at_state"]).height:
            raise ValueError(f"team-box historical known-at state drift for {season}")
        profiles.append({
            "season": season,
            "rows": frame.height,
            "bytes": path.stat().st_size,
            "sha256": item["sha256"],
            "physical_schema_sha256": stable_hash(sorted((name, str(dtype)) for name, dtype in frame.schema.items())),
            "minimum_capture_known_at_utc": frame["capture_known_at_utc"].min(),
            "maximum_capture_known_at_utc": frame["capture_known_at_utc"].max(),
        })
        frames.append(frame)
    return pl.concat(frames, how="diagonal_relaxed").sort(["season", "source_game_id", "home_away", "observation_id"]), manifest, profiles


def _validate_source_stats(candidates: Any) -> tuple[int, dict[str, int]]:
    category_sets: dict[int, set[str]] = {}
    cell_count = 0
    for row in candidates.select("season", "stats_json", "stats_sha256", "stats_category_count", "duplicate_stats_categories_json").iter_rows(named=True):
        if hashlib.sha256(row["stats_json"].encode("utf-8")).hexdigest() != row["stats_sha256"]:
            raise ValueError("team-box stats hash drift")
        stats = json.loads(row["stats_json"])
        categories = [item.get("category") for item in stats]
        if len(stats) != int(row["stats_category_count"]):
            raise ValueError("team-box stat category count drift")
        if len(categories) != len(set(categories)) or json.loads(row["duplicate_stats_categories_json"]):
            raise ValueError("duplicate category within team-box observation")
        if any(not isinstance(item.get("category"), str) or not isinstance(item.get("stat"), str) for item in stats):
            raise ValueError("team-box stat cell schema drift")
        category_sets.setdefault(int(row["season"]), set()).update(categories)
        cell_count += len(stats)
    return cell_count, {str(season): len(values) for season, values in sorted(category_sets.items())}


def _explode_stat_cells(snapshot_rows: Any) -> Any:
    pl = _polars()
    dtype = pl.List(pl.Struct({"category": pl.String, "stat": pl.String}))
    cells = (
        snapshot_rows.select(
            "season", "season_type", "week", "source_game_id", "source_team_id", "home_away", "points",
            "observation_id", "canonical_game_id_candidate", "canonical_team_id_candidate", "source_capture_id",
            "source_request_id", "source_response_sha256", "capture_known_at_utc", "source_record_evidence_sha256",
            "historical_known_at_state", "reconciliation_disposition", "stats_json",
        )
        .with_columns(pl.col("stats_json").str.json_decode(dtype=dtype).alias("stat_item"))
        .drop("stats_json")
        .explode("stat_item", empty_as_null=True)
        .unnest("stat_item")
        .rename({"category": "stat_category", "stat": "stat_value_raw"})
        .sort(["season", "source_game_id", "canonical_team_id_candidate", "stat_category"])
    )
    ids = [
        "hist_team_box_stat_" + stable_hash({"observation_id": observation, "stat_category": category})[:24]
        for observation, category in cells.select("observation_id", "stat_category").iter_rows()
    ]
    return cells.with_columns(
        pl.Series("stat_cell_id", ids, dtype=pl.String),
        pl.lit("RAW_SOURCE_TEXT_NOT_PARSED").alias("stat_value_parse_state"),
        pl.lit(True).alias("capture_time_candidate_only"),
        pl.lit(False).alias("historical_pit_eligible"),
        pl.lit(False).alias("protected_eligible"),
    ).select("stat_cell_id", *cells.columns, "stat_value_parse_state", "capture_time_candidate_only", "historical_pit_eligible", "protected_eligible")


def _disposition(candidates: Any, contract: dict[str, Any]) -> tuple[Any, Any, Any, dict[str, Any]]:
    pl = _polars()
    rules = contract["disposition"]
    expected = contract["acceptance"]
    eligible = pl.col("reconciliation_disposition").is_in(rules["eligible_reconciliation_dispositions"])
    exact_source = candidates.filter(eligible)
    nonadmitted = candidates.filter(~eligible)
    if exact_source.height != expected["expected_exact_rows"] or nonadmitted.height != expected["expected_nonadmitted_rows"]:
        raise ValueError("team-box disposition population drift")
    if exact_source.filter(pl.col("canonical_game_id_candidate").is_null() | pl.col("canonical_team_id_candidate").is_null()).height:
        raise ValueError("exact team-box disposition lacks canonical game/team candidate")
    if nonadmitted.filter(pl.col("reconciliation_disposition") != rules["nonadmitted_reconciliation_disposition"]).height:
        raise ValueError("unexpected team-box nonadmitted disposition")
    if _duplicate_groups(candidates, ["observation_id"]) != expected["expected_duplicate_observation_ids"]:
        raise ValueError("duplicate team-box observation identity")
    if _duplicate_groups(exact_source, rules["natural_key"]) != expected["expected_duplicate_natural_keys"]:
        raise ValueError("duplicate exact team-box natural key")
    forbidden = set(rules["forbidden_snapshot_fields"]) & set(rules["snapshot_fields"])
    if forbidden:
        raise ValueError(f"forbidden team-box fields configured for snapshot: {sorted(forbidden)}")
    snapshot = exact_source.select(rules["snapshot_fields"]).with_columns(
        pl.lit(True).alias("capture_time_candidate_only"),
        pl.lit(False).alias("historical_pit_eligible"),
        pl.lit(False).alias("preliminary_replay_eligible"),
        pl.lit(False).alias("protected_eligible"),
    ).sort(["season", "source_game_id", "canonical_team_id_candidate"])
    nonadmitted = nonadmitted.with_columns(
        pl.lit("SOURCE_LEVEL_GAME_TEAM_BOX_WITHOUT_EXACT_CANONICAL_GAME_TEAM_RECONCILIATION").alias("nonadmission_reason"),
        pl.lit(False).alias("historical_pit_eligible"),
        pl.lit(False).alias("protected_eligible"),
    ).sort(["season", "source_game_id", "observation_id"])
    cells = _explode_stat_cells(snapshot)
    disposition_counts = {str(row["reconciliation_disposition"]): int(row["len"]) for row in candidates.group_by("reconciliation_disposition").len().iter_rows(named=True)}
    exact_by_season = {str(row["season"]): int(row["len"]) for row in snapshot.group_by("season").len().sort("season").iter_rows(named=True)}
    nonadmitted_by_season = {str(row["season"]): int(row["len"]) for row in nonadmitted.group_by("season").len().sort("season").iter_rows(named=True)}
    profile = {
        "source_rows": candidates.height,
        "source_games": candidates["source_game_id"].n_unique(),
        "exact_rows": snapshot.height,
        "exact_games": snapshot["source_game_id"].n_unique(),
        "exact_teams": snapshot["canonical_team_id_candidate"].n_unique(),
        "exact_stat_cells": cells.height,
        "nonadmitted_rows": nonadmitted.height,
        "nonadmitted_games": nonadmitted["source_game_id"].n_unique(),
        "side_swap_rows": candidates.filter(pl.col("historical_side_alignment") == "SWAPPED_SIDE_DISTINCT_POINTS").height,
        "side_swap_games": candidates.filter(pl.col("historical_side_alignment") == "SWAPPED_SIDE_DISTINCT_POINTS")["source_game_id"].n_unique(),
        "outcome_overlap_rows": candidates["historical_outcome_observation_id"].drop_nulls().len(),
        "disposition_counts": disposition_counts,
        "exact_by_season": exact_by_season,
        "nonadmitted_by_season": nonadmitted_by_season,
    }
    comparisons = {
        "source_rows": "expected_source_rows", "source_games": "expected_source_games", "exact_rows": "expected_exact_rows",
        "exact_games": "expected_exact_games", "exact_teams": "expected_exact_teams", "exact_stat_cells": "expected_exact_stat_cells",
        "nonadmitted_rows": "expected_nonadmitted_rows", "nonadmitted_games": "expected_nonadmitted_games",
        "side_swap_rows": "expected_side_swap_rows", "side_swap_games": "expected_side_swap_games", "outcome_overlap_rows": "expected_outcome_overlap_rows",
    }
    for actual, expected_key in comparisons.items():
        if profile[actual] != expected[expected_key]:
            raise ValueError(f"team-box population drift: {actual}")
    for actual, expected_key in (("disposition_counts", "expected_disposition_counts"), ("exact_by_season", "expected_exact_by_season"), ("nonadmitted_by_season", "expected_nonadmitted_by_season")):
        if profile[actual] != expected[expected_key]:
            raise ValueError(f"team-box population profile drift: {actual}")
    return snapshot, cells, nonadmitted, profile


def materialize(*, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs" / "historical_team_box_snapshot_contract.json"
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    _validate_contract_authority(contract)
    core_path = Path(__file__).resolve()
    builder_path = repo_root / "tools" / "build_historical_team_box_snapshot.py"
    candidates, candidate_manifest, source_profiles = _load_candidates(input_data_root, contract)
    expected = contract["acceptance"]
    if candidates.height != expected["expected_source_rows"] or set(candidates["season"].unique().to_list()) != set(contract["source_contract"]["source_seasons"]):
        raise ValueError("team-box source population or season coverage drift")
    stat_cells, category_counts = _validate_source_stats(candidates)
    if stat_cells != expected["expected_source_stat_cells"] or category_counts != expected["expected_category_counts_by_season"]:
        raise ValueError("team-box source stat population or category drift")
    physical_hashes = {item["physical_schema_sha256"] for item in source_profiles}
    if len(physical_hashes) != expected["expected_physical_schema_hashes"]:
        raise ValueError("team-box physical schema drift")
    source = contract["source_contract"]
    if candidates["capture_known_at_utc"].min() != source["minimum_capture_known_at_utc"] or candidates["capture_known_at_utc"].max() != source["maximum_capture_known_at_utc"]:
        raise ValueError("team-box capture-time envelope drift")
    snapshot, cells, nonadmitted, population = _disposition(candidates, contract)
    if cells["stat_category"].n_unique() != expected["expected_distinct_stat_categories"]:
        raise ValueError("team-box distinct stat-category drift")
    if cells.height + sum(len(json.loads(value)) for value in nonadmitted["stats_json"]) != stat_cells:
        raise ValueError("team-box stat-cell disposition conservation failure")
    record_hashes = {"snapshot": dataframe_record_sha256(snapshot), "cells": dataframe_record_sha256(cells), "nonadmitted": dataframe_record_sha256(nonadmitted)}
    manifest_path_in = input_data_root / Path(source["candidate_manifest_relative_path"])
    identity = stable_hash({
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "core_sha256": sha256_file(core_path),
        "builder_sha256": sha256_file(builder_path),
        "candidate_manifest_sha256": sha256_file(manifest_path_in),
        "candidate_payload_sha256": [item["sha256"] for item in candidate_manifest["payloads"]],
        "record_hashes": record_hashes,
        "classification": contract["classification"],
    })
    payload_root = output_data_root / "quarantine" / "historical_capture_time" / "sha256" / identity
    manifest_root = output_data_root / "manifests" / "historical_capture_time" / "sha256" / identity
    payload_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)
    snapshot_path = payload_root / "exact_reconciled_team_box_rows.parquet"
    cells_path = payload_root / "exact_reconciled_team_box_stat_cells.parquet"
    nonadmitted_path = payload_root / "source_only_team_box_rows.parquet"
    snapshot.write_parquet(snapshot_path, compression="zstd", statistics=True)
    cells.write_parquet(cells_path, compression="zstd", statistics=True)
    nonadmitted.write_parquet(nonadmitted_path, compression="zstd", statistics=True)
    payloads = [
        {"role": "EXACT_RECONCILED_CAPTURE_TIME_TEAM_BOX_ROWS", "name": snapshot_path.name, "rows": snapshot.height, "bytes": snapshot_path.stat().st_size, "sha256": sha256_file(snapshot_path), "record_sha256": record_hashes["snapshot"]},
        {"role": "EXACT_RECONCILED_CAPTURE_TIME_TEAM_BOX_STAT_CELLS", "name": cells_path.name, "rows": cells.height, "bytes": cells_path.stat().st_size, "sha256": sha256_file(cells_path), "record_sha256": record_hashes["cells"]},
        {"role": "SOURCE_ONLY_NONADMITTED_TEAM_BOX_ROWS", "name": nonadmitted_path.name, "rows": nonadmitted.height, "bytes": nonadmitted_path.stat().st_size, "sha256": sha256_file(nonadmitted_path), "record_sha256": record_hashes["nonadmitted"]},
    ]
    manifest = {
        "schema_version": "1.0.0", "artifact_type": "HISTORICAL_TEAM_BOX_CAPTURE_TIME_SNAPSHOT", "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"], "classification": contract["classification"], "dataset_identity": identity, "issued_at_utc": issued_at_utc,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "producer": {"python": sys.version.split()[0], "platform": platform.platform(), "polars": pl.__version__, "core_sha256": sha256_file(core_path), "builder_sha256": sha256_file(builder_path)},
        "input_identities": {"candidate_dataset": source["candidate_dataset_identity"], "candidate_manifest_sha256": source["candidate_manifest_sha256"], "candidate_payload_sha256": [item["sha256"] for item in candidate_manifest["payloads"]], "accepted_outcome_dataset": source["accepted_outcome_dataset_identity"]},
        "source_profiles": source_profiles,
        "population": {**population, "source_stat_cells": stat_cells, "nonadmitted_stat_cells": stat_cells - cells.height, "distinct_stat_categories": cells["stat_category"].n_unique(), "category_counts_by_season": category_counts, "physical_schema_hashes": sorted(physical_hashes)},
        "chronology": {"historical_known_at_state": source["historical_known_at_state"], "minimum_capture_known_at_utc": source["minimum_capture_known_at_utc"], "maximum_capture_known_at_utc": source["maximum_capture_known_at_utc"], "historical_publication_time_proved": False, "pre_capture_backcast": False},
        "payloads": payloads, "authority": contract["authority"], "negative_findings": contract["negative_findings"],
        "scientific_nonclaims": {"historical_population_ready": False, "gap_002_resolved": False, "production_model_ready": False, "trained_production_champion": False, "protected_performance_claimed": False, "tamu_specialization_lift_claimed": False, "bas_or_aggie_excess_result_claimed": False},
    }
    manifest_path = manifest_root / "historical_team_box_snapshot_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {"dataset_identity": identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "manifest": manifest, "snapshot_path": str(snapshot_path), "cells_path": str(cells_path), "nonadmitted_path": str(nonadmitted_path)}
