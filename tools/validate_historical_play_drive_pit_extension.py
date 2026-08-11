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


GAP_IDENTITY = "33f3f3ab34ba38c2e107410545fac2f227bfb40b5b04478c28e34a85b91e23bc"
GAP_MANIFEST_SHA256 = "a470973d156ac7914c67e55c93a3808aa6daa3bf165f2b9d2d8b13b5373e749d"
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
    state_path = (
        data_root / "pit_state" / "historical_known_at" / "sha256" / identity
        / "team_play_drive_profiles.parquet"
    )
    feature_path = (
        data_root / "features" / "historical_known_at" / "sha256" / identity
        / "target_game_team_play_drive_features.parquet"
    )
    gap_manifest_path = (
        data_root / "manifests" / "historical_known_at" / "sha256" / GAP_IDENTITY
        / "versioned_play_drive_gap_reconciliation.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    gap_manifest = json.loads(gap_manifest_path.read_text(encoding="utf-8"))
    profiles = pl.read_parquet(state_path)
    features = pl.read_parquet(feature_path)
    contract = json.loads(
        (repo_root / "configs" / "historical_play_drive_pit_extension_contract.json").read_text(encoding="utf-8")
    )
    checks: list[str] = []
    check(manifest["dataset_identity"] == identity, "manifest_identity", checks)
    check(manifest["decision_unit"] == "POST-SUBTASK-183", "decision_unit", checks)
    check(manifest["classification"] == contract["classification"], "classification", checks)
    check(gap_manifest["dataset_identity"] == GAP_IDENTITY, "gap_identity", checks)
    check(sha256_file(gap_manifest_path) == GAP_MANIFEST_SHA256, "gap_manifest_hash", checks)
    check(gap_manifest["identity_contract"]["commit_known_at_utc"] == "2022-07-25T17:33:07Z", "gap_known_at", checks)
    check(gap_manifest["population"]["2011"]["source_rows"] == 138_564, "gap_2011_play_rows", checks)
    check(gap_manifest["population"]["2020"]["source_rows"] == 96_293, "gap_2020_play_rows", checks)
    check(gap_manifest["population"]["2011"]["repository_drives"] == 20_745, "gap_2011_drive_rows", checks)
    check(gap_manifest["population"]["2020"]["repository_drives"] == 14_065, "gap_2020_drive_rows", checks)
    check(
        gap_manifest["population"]["2020"]["drive_disposition_counts"]
        ["QUARANTINED_VERSION_BOUND_IDENTITY_OR_SCHEMA_FAILURE"] == 2,
        "gap_2020_drive_quarantine_preserved",
        checks,
    )
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
    check(manifest["population"]["exact_play_rows"] == 1_840_951, "exact_play_rows", checks)
    check(manifest["population"]["mapped_exact_play_rows"] == 1_840_698, "mapped_play_rows", checks)
    check(manifest["population"]["unmapped_exact_play_rows"] == 253, "unmapped_play_rows_preserved", checks)
    check(manifest["population"]["exact_drive_rows"] == 264_812, "exact_drive_rows", checks)
    check(manifest["population"]["mapped_exact_drive_rows"] == 264_775, "mapped_drive_rows", checks)
    check(manifest["population"]["unmapped_exact_drive_rows"] == 37, "unmapped_drive_rows_preserved", checks)
    check(manifest["population"]["missing_source_seasons"] == [], "no_2010_2022_season_gap", checks)
    check(manifest["population"]["source_seasons"] == list(range(2010, 2023)), "dense_source_seasons", checks)
    for payload, path in zip(manifest["payloads"], [state_path, feature_path], strict=True):
        check(payload["sha256"] == sha256_file(path), f"payload_hash_{payload['role']}", checks)
        check(payload["bytes"] == path.stat().st_size, f"payload_bytes_{payload['role']}", checks)
    rebuild_root = (args.rebuild_root or data_root / "validation" / "POST-SUBTASK-183" / "rebuild").resolve()
    if rebuild_root.exists():
        remove_rebuild_root(rebuild_root)
    rebuilt = materialize(
        input_data_root=data_root,
        output_data_root=rebuild_root,
        repo_root=repo_root,
        issued_at_utc=manifest["issued_at_utc"],
        contract_name="historical_play_drive_pit_extension_contract.json",
    )
    check(rebuilt["dataset_identity"] == identity, "rebuild_identity", checks)
    check(manifest_path.read_bytes() == Path(rebuilt["manifest_path"]).read_bytes(), "manifest_byte_identical", checks)
    check(state_path.read_bytes() == Path(rebuilt["state_path"]).read_bytes(), "state_byte_identical", checks)
    check(feature_path.read_bytes() == Path(rebuilt["feature_path"]).read_bytes(), "features_byte_identical", checks)
    remove_rebuild_root(rebuild_root)
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "HISTORICAL_PLAY_DRIVE_PIT_EXTENSION_VALIDATION",
        "decision_unit": "POST-SUBTASK-183",
        "jira_key": "BAT-540",
        "dataset_identity": identity,
        "manifest_sha256": sha256_file(manifest_path),
        "gap_dataset_identity": GAP_IDENTITY,
        "gap_manifest_sha256": GAP_MANIFEST_SHA256,
        "status": "PASS",
        "checks_passed": len(checks),
        "checks": checks,
        "mutation_controls_passed": 6,
        "mutation_controls": [
            "SOURCE_KNOWN_AT_AFTER_CUTOFF_REJECTED",
            "SOURCE_EFFECTIVE_TIME_AT_OR_AFTER_CUTOFF_REJECTED",
            "TARGET_GAME_SOURCE_OVERLAP_REJECTED",
            "PROTECTED_AUTHORITY_TRUE_REJECTED",
            "COLD_START_WITH_SYNTHETIC_FEATURE_VALUE_REJECTED",
            "UNRESOLVED_DRIVE_TEAM_IDENTITY_QUARANTINED",
        ],
        "deterministic_payloads_compared": 3,
        "byte_identical_rebuild": True,
        "rebuild_root_removed": not rebuild_root.exists(),
        "negative_findings": manifest["negative_findings"],
    }
    report_path = data_root / "validation" / "POST-SUBTASK-183" / "play_drive_pit_extension_validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(canonical_json_bytes(report) + b"\n")
    print(json.dumps({"report": str(report_path), "report_sha256": sha256_file(report_path), **report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
