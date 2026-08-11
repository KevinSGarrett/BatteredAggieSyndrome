from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError("player-box snapshot materialization requires the optional data-engineering environment") from exc
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


def _duplicate_groups(frame: Any, keys: Iterable[str]) -> int:
    return frame.group_by(list(keys)).len().filter(_polars().col("len") > 1).height


def _validate_contract_authority(contract: dict[str, Any]) -> None:
    authority = contract["authority"]
    if authority.get("candidate_snapshot_materialization") is not True:
        raise ValueError("player-box candidate snapshot authority is not explicitly enabled")
    closed = (
        "immutable_raw_capture_mutation", "canonical_entity_mutation", "historical_pit_admission",
        "preliminary_chronological_replay_admission", "protected_training_admission",
        "protected_evaluation_admission", "champion_or_production_promotion", "forecast_publication",
    )
    if any(authority.get(key) is not False for key in closed):
        raise ValueError("player-box authority boundary is open beyond capture-time candidate use")


def _load_candidates(data_root: Path, contract: dict[str, Any]) -> tuple[Any, dict[str, Any], list[dict[str, Any]]]:
    pl = _polars()
    source, expected = contract["source_contract"], contract["acceptance"]
    manifest_path = data_root / Path(source["candidate_manifest_relative_path"])
    if not manifest_path.is_file() or sha256_file(manifest_path) != source["candidate_manifest_sha256"]:
        raise ValueError("player-box candidate manifest identity drift")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_identity") != source["candidate_dataset_identity"]:
        raise ValueError("player-box candidate dataset identity drift")
    if manifest.get("domain") != "player_box_scores" or manifest.get("grain") != "GAME_TEAM_PLAYER_CATEGORY_STAT_CELL":
        raise ValueError("player-box candidate domain or grain drift")
    payloads = sorted(manifest.get("payloads", []), key=lambda item: int(item["season"]))
    if len(payloads) != expected["expected_source_files"]:
        raise ValueError("player-box candidate file count drift")
    required = set(contract["disposition"]["snapshot_fields"]) | {"source_team_points", "team_box_historical_outcome_match", "admission_state"}
    payload_root = data_root / Path(source["candidate_payload_root"])
    frames, profiles = [], []
    for item in payloads:
        season, path = int(item["season"]), payload_root / Path(item["name"])
        if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256_file(path) != item["sha256"]:
            raise ValueError(f"player-box candidate payload identity drift for {season}")
        frame = pl.read_parquet(path)
        if frame.height != int(item["rows"]) or set(frame.columns) < required:
            raise ValueError(f"player-box candidate population or schema drift for {season}")
        if frame["season"].n_unique() != 1 or int(frame["season"][0]) != season:
            raise ValueError(f"player-box candidate season drift for {season}")
        if frame.filter(pl.col("historical_known_at_state") != source["historical_known_at_state"]).height:
            raise ValueError(f"player-box historical known-at state drift for {season}")
        profiles.append({
            "season": season, "rows": frame.height, "bytes": path.stat().st_size, "sha256": item["sha256"],
            "physical_schema_sha256": stable_hash(sorted((name, str(dtype)) for name, dtype in frame.schema.items())),
            "minimum_capture_known_at_utc": frame["capture_known_at_utc"].min(),
            "maximum_capture_known_at_utc": frame["capture_known_at_utc"].max(),
        })
        frames.append(frame)
    return pl.concat(frames, how="diagonal_relaxed"), manifest, profiles


def _disposition(candidates: Any, contract: dict[str, Any]) -> tuple[Any, Any, dict[str, Any]]:
    pl = _polars()
    rules, expected = contract["disposition"], contract["acceptance"]
    value_exact = pl.col("reconciliation_disposition").is_in(rules["eligible_reconciliation_dispositions"])
    complete_identity = (
        pl.col("canonical_game_id_candidate").is_not_null()
        & pl.col("canonical_team_id_candidate").is_not_null()
        & pl.col("canonical_player_id_candidate").is_not_null()
    )
    eligible = value_exact & complete_identity
    exact_source, nonadmitted = candidates.filter(eligible), candidates.filter(~eligible)
    if exact_source.height != expected["expected_exact_cells"] or nonadmitted.height != expected["expected_nonadmitted_cells"]:
        raise ValueError("player-box disposition population drift")
    required_identity = ~complete_identity
    if exact_source.filter(required_identity).height:
        raise ValueError("exact player-box disposition lacks canonical game/team/player candidate")
    incomplete_exact = nonadmitted.filter(value_exact & required_identity)
    if incomplete_exact.height != expected["expected_exact_value_incomplete_identity_cells"]:
        raise ValueError("player-box exact-value incomplete-identity population drift")
    unexpected_nonadmitted = ~pl.col("reconciliation_disposition").is_in(rules["nonadmitted_reconciliation_dispositions"]) & ~(value_exact & required_identity)
    if nonadmitted.filter(unexpected_nonadmitted).height:
        raise ValueError("unexpected player-box nonadmitted disposition")
    if _duplicate_groups(candidates, ["observation_id"]) != expected["expected_duplicate_observation_ids"]:
        raise ValueError("duplicate player-box observation identity")
    if _duplicate_groups(exact_source, rules["natural_key"]) != expected["expected_duplicate_natural_keys"]:
        raise ValueError("duplicate exact player-box natural key")
    if set(rules["forbidden_snapshot_fields"]) & set(rules["snapshot_fields"]):
        raise ValueError("forbidden player-box fields configured for snapshot")
    current = exact_source.filter(pl.col("reconciliation_disposition") == "CANDIDATE_CURRENT_CANONICAL_GAME_MULTISET_EXACT")
    play = exact_source.filter(pl.col("reconciliation_disposition") == "CANDIDATE_PLAY_DERIVED_METRIC_EXACT")
    if current.filter(pl.col("current_game_multiset_exact_match") != True).height:
        raise ValueError("current-multiset exact disposition lacks exact evidence")
    if play.filter((pl.col("player_event_value_exact") != True) | pl.col("player_event_observation_id").is_null()).height:
        raise ValueError("play-derived exact disposition lacks exact evidence")
    snapshot = exact_source.select(rules["snapshot_fields"]).with_columns(
        pl.lit(True).alias("capture_time_candidate_only"), pl.lit(False).alias("historical_pit_eligible"),
        pl.lit(False).alias("preliminary_replay_eligible"), pl.lit(False).alias("protected_eligible"),
    )
    nonadmitted = nonadmitted.with_columns(
        pl.when(value_exact & required_identity)
        .then(pl.lit("EXACT_VALUE_EVIDENCE_WITHOUT_COMPLETE_CANONICAL_GAME_TEAM_PLAYER_IDENTITY"))
        .when(pl.col("reconciliation_disposition") == "CANDIDATE_TEAM_BOX_GAME_TEAM_LINKED_PLAYER_STAT")
        .then(pl.lit("TEAM_BOX_GAME_TEAM_LINK_ONLY_WITHOUT_EXACT_PLAYER_STAT_CONFIRMATION"))
        .when(pl.col("reconciliation_disposition") == "QUARANTINE_PLAY_DERIVED_METRIC_VALUE_CONFLICT")
        .then(pl.lit("PLAY_DERIVED_METRIC_VALUE_CONFLICT"))
        .otherwise(pl.lit("INVALID_PLAYER_BOX_CORE"))
        .alias("nonadmission_reason"),
        pl.lit(False).alias("historical_pit_eligible"), pl.lit(False).alias("protected_eligible"),
    )
    def by_season(frame: Any) -> dict[str, int]:
        return {str(row["season"]): int(row["len"]) for row in frame.group_by("season").len().sort("season").iter_rows(named=True)}
    team_rows = candidates.select("season", "source_game_id", "source_team_normalized").unique()
    game_team_counts = team_rows.group_by("season", "source_game_id").len()
    whitespace = candidates.filter((pl.col("player_label_raw") != pl.col("player_label")).fill_null(True)).height
    profile = {
        "source_cells": candidates.height, "source_games": candidates["source_game_id"].n_unique(), "source_team_rows": team_rows.height,
        "source_player_ids": candidates["source_player_id"].n_unique(), "exact_cells": snapshot.height,
        "exact_games": snapshot["source_game_id"].n_unique(), "exact_player_ids": snapshot["source_player_id"].n_unique(),
        "nonadmitted_cells": nonadmitted.height, "nonadmitted_games": nonadmitted["source_game_id"].n_unique(),
        "categories": candidates["category"].n_unique(), "stat_types": candidates["stat_type"].n_unique(),
        "missing_player_id_cells": candidates["source_player_id"].null_count(), "missing_player_name_cells": candidates["player_label"].null_count(),
        "missing_stat_value_cells": candidates["stat_value_raw"].null_count(), "player_label_whitespace_drift_cells": whitespace,
        "games_with_two_team_rows": game_team_counts.filter(pl.col("len") == 2).height,
        "games_without_two_team_rows": game_team_counts.filter(pl.col("len") != 2).height,
        "missing_team_rows": int((2 - game_team_counts["len"]).sum()),
        "team_box_link_cells": candidates["team_box_observation_id"].drop_nulls().len(),
        "player_event_link_cells": candidates["player_event_observation_id"].drop_nulls().len(),
        "exact_value_incomplete_identity_cells": incomplete_exact.height,
        "disposition_counts": {str(row["reconciliation_disposition"]): int(row["len"]) for row in candidates.group_by("reconciliation_disposition").len().iter_rows(named=True)},
        "exact_by_season": by_season(snapshot), "nonadmitted_by_season": by_season(nonadmitted),
    }
    comparisons = {
        "source_cells": "expected_source_cells", "source_games": "expected_source_games", "source_team_rows": "expected_source_team_rows",
        "source_player_ids": "expected_source_player_ids", "exact_cells": "expected_exact_cells", "exact_games": "expected_exact_games",
        "exact_player_ids": "expected_exact_player_ids", "nonadmitted_cells": "expected_nonadmitted_cells", "nonadmitted_games": "expected_nonadmitted_games",
        "categories": "expected_categories", "stat_types": "expected_stat_types", "missing_player_id_cells": "expected_missing_player_id_cells",
        "missing_player_name_cells": "expected_missing_player_name_cells", "missing_stat_value_cells": "expected_missing_stat_value_cells",
        "player_label_whitespace_drift_cells": "expected_player_label_whitespace_drift_cells", "games_with_two_team_rows": "expected_games_with_two_team_rows",
        "games_without_two_team_rows": "expected_games_without_two_team_rows", "missing_team_rows": "expected_missing_team_rows",
        "team_box_link_cells": "expected_team_box_link_cells", "player_event_link_cells": "expected_player_event_link_cells",
        "exact_value_incomplete_identity_cells": "expected_exact_value_incomplete_identity_cells",
    }
    for actual, expected_key in comparisons.items():
        if profile[actual] != expected[expected_key]:
            raise ValueError(f"player-box population drift: {actual}; actual={profile[actual]} expected={expected[expected_key]}")
    for actual, expected_key in (("disposition_counts", "expected_disposition_counts"), ("exact_by_season", "expected_exact_by_season"), ("nonadmitted_by_season", "expected_nonadmitted_by_season")):
        if profile[actual] != expected[expected_key]:
            raise ValueError(f"player-box population profile drift: {actual}")
    return snapshot, nonadmitted, profile


def materialize(*, input_data_root: Path, output_data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    pl = _polars()
    contract_path = repo_root / "configs" / "historical_player_box_snapshot_contract.json"
    contract_bytes, core_path = contract_path.read_bytes(), Path(__file__).resolve()
    contract = json.loads(contract_bytes)
    _validate_contract_authority(contract)
    builder_path = repo_root / "tools" / "build_historical_player_box_snapshot.py"
    candidates, candidate_manifest, source_profiles = _load_candidates(input_data_root, contract)
    expected, source = contract["acceptance"], contract["source_contract"]
    if candidates.height != expected["expected_source_cells"] or set(candidates["season"].unique().to_list()) != set(source["source_seasons"]):
        raise ValueError("player-box source population or season coverage drift")
    physical_hashes = {item["physical_schema_sha256"] for item in source_profiles}
    if len(physical_hashes) != expected["expected_physical_schema_hashes"]:
        raise ValueError("player-box physical schema drift")
    if candidates["capture_known_at_utc"].min() != source["minimum_capture_known_at_utc"] or candidates["capture_known_at_utc"].max() != source["maximum_capture_known_at_utc"]:
        raise ValueError("player-box capture-time envelope drift")
    snapshot, nonadmitted, population = _disposition(candidates, contract)
    population["physical_schema_hashes"] = sorted(physical_hashes)
    runtime_root = output_data_root / "runtime" / "BAT-550"
    runtime_root.mkdir(parents=True, exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix="player-box-snapshot-", dir=runtime_root))
    try:
        staged_snapshot = staging_root / "exact_reconciled_player_box_stat_cells.parquet"
        staged_nonadmitted = staging_root / "nonadmitted_player_box_stat_cells.parquet"
        snapshot.write_parquet(staged_snapshot, compression="zstd", statistics=True)
        nonadmitted.write_parquet(staged_nonadmitted, compression="zstd", statistics=True)
        staged_hashes = {"snapshot": sha256_file(staged_snapshot), "nonadmitted": sha256_file(staged_nonadmitted)}
        identity = stable_hash({
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(), "core_sha256": sha256_file(core_path), "builder_sha256": sha256_file(builder_path),
            "candidate_manifest_sha256": source["candidate_manifest_sha256"], "candidate_payload_sha256": [item["sha256"] for item in candidate_manifest["payloads"]],
            "payload_sha256": staged_hashes, "classification": contract["classification"],
        })
        payload_root = output_data_root / "quarantine" / "historical_capture_time" / "sha256" / identity
        manifest_root = output_data_root / "manifests" / "historical_capture_time" / "sha256" / identity
        payload_root.mkdir(parents=True, exist_ok=True); manifest_root.mkdir(parents=True, exist_ok=True)
        snapshot_path, nonadmitted_path = payload_root / staged_snapshot.name, payload_root / staged_nonadmitted.name
        for staged, target, expected_hash in ((staged_snapshot, snapshot_path, staged_hashes["snapshot"]), (staged_nonadmitted, nonadmitted_path, staged_hashes["nonadmitted"])):
            if target.exists():
                if sha256_file(target) != expected_hash:
                    raise ValueError(f"existing player-box payload identity conflict: {target}")
                staged.unlink()
            else:
                os.replace(staged, target)
        payloads = [
            {"role": "EXACT_RECONCILED_CAPTURE_TIME_PLAYER_BOX_STAT_CELLS", "name": snapshot_path.name, "rows": snapshot.height, "bytes": snapshot_path.stat().st_size, "sha256": staged_hashes["snapshot"]},
            {"role": "NONADMITTED_PLAYER_BOX_STAT_CELLS", "name": nonadmitted_path.name, "rows": nonadmitted.height, "bytes": nonadmitted_path.stat().st_size, "sha256": staged_hashes["nonadmitted"]},
        ]
        manifest = {
            "schema_version": "1.0.0", "artifact_type": "HISTORICAL_PLAYER_BOX_CAPTURE_TIME_SNAPSHOT", "decision_unit": contract["decision_unit"],
            "jira_key": contract["jira_key"], "classification": contract["classification"], "dataset_identity": identity, "issued_at_utc": issued_at_utc,
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "producer": {"python": sys.version.split()[0], "platform": platform.platform(), "polars": pl.__version__, "core_sha256": sha256_file(core_path), "builder_sha256": sha256_file(builder_path)},
            "input_identities": {"candidate_dataset": source["candidate_dataset_identity"], "candidate_manifest_sha256": source["candidate_manifest_sha256"], "candidate_payload_sha256": [item["sha256"] for item in candidate_manifest["payloads"]], "team_box_snapshot_dataset": source["team_box_snapshot_dataset_identity"], "player_event_candidate": source["player_event_candidate_identity"]},
            "source_profiles": source_profiles, "population": population,
            "chronology": {"historical_known_at_state": source["historical_known_at_state"], "minimum_capture_known_at_utc": source["minimum_capture_known_at_utc"], "maximum_capture_known_at_utc": source["maximum_capture_known_at_utc"], "historical_publication_time_proved": False, "pre_capture_backcast": False},
            "payloads": payloads, "authority": contract["authority"], "negative_findings": contract["negative_findings"],
            "scientific_nonclaims": {"historical_population_ready": False, "gap_002_resolved": False, "gap_003_resolved": False, "official_player_box_scores_materialized": False, "preliminary_model_training_eligible": False, "production_model_ready": False, "trained_production_champion": False, "protected_performance_claimed": False, "tamu_specialization_lift_claimed": False, "bas_or_aggie_excess_result_claimed": False},
        }
        manifest_path = manifest_root / "historical_player_box_snapshot_manifest.json"
        manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
        return {"dataset_identity": identity, "manifest_path": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "manifest": manifest, "snapshot_path": str(snapshot_path), "nonadmitted_path": str(nonadmitted_path)}
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)
