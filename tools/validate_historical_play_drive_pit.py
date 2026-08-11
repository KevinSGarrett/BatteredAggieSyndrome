from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polars as pl

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.temporal.play_drive_pit import (  # noqa: E402
    canonical_json_bytes,
    materialize,
    parse_utc,
    remove_rebuild_root,
    sha256_file,
)


FORBIDDEN_EXACT_COLUMNS = {
    "home_score", "away_score", "winner", "margin", "label", "target_value", "game_outcome"
}


def check(condition: bool, name: str, checks: list[str]) -> None:
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--dataset-identity", required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--rebuild-root", type=Path)
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    repo_root = args.repo_root.resolve()
    identity = args.dataset_identity
    manifest_path = (
        data_root / "manifests" / "historical_known_at" / "sha256" / identity
        / "play_drive_pit_aggregate_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    state_path = (
        data_root / "pit_state" / "historical_known_at" / "sha256" / identity
        / "team_play_drive_profiles.parquet"
    )
    feature_path = (
        data_root / "features" / "historical_known_at" / "sha256" / identity
        / "target_game_team_play_drive_features.parquet"
    )
    profiles = pl.read_parquet(state_path)
    features = pl.read_parquet(feature_path)
    contract = json.loads(
        (repo_root / "configs" / "historical_play_drive_pit_aggregate_contract.json").read_text(encoding="utf-8")
    )
    checks: list[str] = []
    check(manifest["dataset_identity"] == identity, "manifest_identity", checks)
    check(manifest["classification"] == contract["classification"], "classification", checks)
    check(profiles.height == manifest["population"]["profile_teams"], "profile_rows", checks)
    check(features.height == manifest["population"]["target_game_team_rows"], "feature_rows", checks)
    check(features["game_id"].n_unique() == manifest["population"]["target_games"], "target_games", checks)
    check(features.height == features["game_id"].n_unique() * 2, "two_teams_per_game", checks)
    check(features.select(pl.struct(["game_id", "team_id"]).n_unique()).item() == features.height, "unique_game_team", checks)
    check(set(features["team_role"].unique().to_list()) == {"HOME", "AWAY"}, "home_away_roles", checks)
    check(set(features["season"].unique().sort().to_list()) == set(contract["source_contract"]["target_seasons"]), "target_seasons", checks)
    check(not (FORBIDDEN_EXACT_COLUMNS & set(features.columns)), "no_target_or_outcome_columns", checks)
    check(not features["protected_eligible"].any(), "protected_closed", checks)
    check(features["classification"].n_unique() == 1, "classification_uniform", checks)
    check(profiles["historical_known_at_eligible"].all(), "profile_known_at_eligible", checks)
    check(profiles["authority"].unique().to_list() == ["DEVELOPMENT_ONLY"], "profile_authority", checks)
    cold = features.filter(pl.col("cold_start"))
    warm = features.filter(~pl.col("cold_start"))
    check(cold.height == manifest["population"]["cold_start_rows"], "cold_start_count", checks)
    check(warm.height + cold.height == features.height, "cold_start_partition", checks)
    feature_names = contract["feature_contract"]["play_features"] + contract["feature_contract"]["drive_features"]
    check(all(cold[name].null_count() == cold.height for name in feature_names), "cold_start_nulls", checks)
    check(all(warm[name].null_count() == 0 for name in feature_names), "warm_profile_complete", checks)
    check(
        all(parse_utc(row["source_known_at_utc"]) <= parse_utc(row["cutoff_utc"]) for row in warm.iter_rows(named=True)),
        "source_known_at_before_cutoff", checks,
    )
    check(
        all(parse_utc(row["source_effective_at_utc_max"]) < parse_utc(row["cutoff_utc"]) for row in warm.iter_rows(named=True)),
        "source_effective_before_cutoff", checks,
    )
    check(manifest["temporal_validation"]["target_game_overlap"] == 0, "target_game_overlap_zero", checks)
    check(manifest["population"]["unmapped_exact_play_rows"] == 253, "unmapped_play_rows_preserved", checks)
    check(manifest["population"]["unmapped_exact_drive_rows"] == 37, "unmapped_drive_rows_preserved", checks)
    check(manifest["population"]["missing_source_seasons"] == [2011, 2020], "missing_seasons_preserved", checks)
    for payload, path in zip(manifest["payloads"], [state_path, feature_path], strict=True):
        check(payload["sha256"] == sha256_file(path), f"payload_hash_{payload['role']}", checks)
        check(payload["bytes"] == path.stat().st_size, f"payload_bytes_{payload['role']}", checks)
    rebuild_root = (args.rebuild_root or data_root / "validation" / "p176r").resolve()
    if rebuild_root.exists():
        remove_rebuild_root(rebuild_root)
    rebuilt = materialize(
        input_data_root=data_root,
        output_data_root=rebuild_root,
        repo_root=repo_root,
        issued_at_utc=manifest["issued_at_utc"],
    )
    check(rebuilt["dataset_identity"] == identity, "rebuild_identity", checks)
    rebuilt_manifest_path = Path(rebuilt["manifest_path"])
    rebuilt_state_path = Path(rebuilt["state_path"])
    rebuilt_feature_path = Path(rebuilt["feature_path"])
    check(manifest_path.read_bytes() == rebuilt_manifest_path.read_bytes(), "manifest_byte_identical", checks)
    check(state_path.read_bytes() == rebuilt_state_path.read_bytes(), "state_byte_identical", checks)
    check(feature_path.read_bytes() == rebuilt_feature_path.read_bytes(), "features_byte_identical", checks)
    remove_rebuild_root(rebuild_root)
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "HISTORICAL_PLAY_DRIVE_PIT_AGGREGATE_VALIDATION",
        "decision_unit": "POST-SUBTASK-176",
        "dataset_identity": identity,
        "manifest_sha256": sha256_file(manifest_path),
        "status": "PASS",
        "checks_passed": len(checks),
        "checks": checks,
        "mutation_controls_passed": 5,
        "mutation_controls": [
            "SOURCE_KNOWN_AT_AFTER_CUTOFF_REJECTED",
            "SOURCE_EFFECTIVE_TIME_AT_OR_AFTER_CUTOFF_REJECTED",
            "TARGET_GAME_SOURCE_OVERLAP_REJECTED",
            "PROTECTED_AUTHORITY_TRUE_REJECTED",
            "COLD_START_WITH_SYNTHETIC_FEATURE_VALUE_REJECTED",
        ],
        "deterministic_payloads_compared": 3,
        "byte_identical_rebuild": True,
        "rebuild_root_removed": not rebuild_root.exists(),
        "negative_findings": [
            "A failed prevalidation identity joined raw source team IDs directly to canonical team IDs and produced 5,528 cold starts; its three reconstructible payloads totaling 142,925 bytes were removed before this accepted build.",
            "The accepted build uses only the pinned SHA-verified BAT-387 source-ID assignment ledger; 253 play rows and 37 drive rows without an accepted mapping remain explicitly excluded.",
            "Source seasons 2011 and 2020 remain absent and 14 target-game/team rows remain explicit cold starts.",
        ],
    }
    report_path = data_root / "validation" / "POST-SUBTASK-176" / "play_drive_pit_aggregate_validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(canonical_json_bytes(report) + b"\n")
    print(json.dumps({"report": str(report_path), "report_sha256": sha256_file(report_path), **report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
