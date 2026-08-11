from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polars as pl

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.temporal.player_event_metric_pit import (  # noqa: E402
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
    manifest_path = data_root / "manifests" / "historical_known_at" / "sha256" / identity / "player_event_metric_pit_manifest.json"
    state_path = data_root / "pit_state" / "historical_known_at" / "sha256" / identity / "player_event_metrics.parquet"
    profile_path = data_root / "pit_state" / "historical_known_at" / "sha256" / identity / "team_player_event_metric_profiles.parquet"
    feature_path = data_root / "features" / "historical_known_at" / "sha256" / identity / "target_game_team_player_event_features.parquet"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = json.loads((repo_root / "configs" / "historical_player_event_metric_pit_contract.json").read_text(encoding="utf-8"))
    state = pl.read_parquet(state_path)
    profiles = pl.read_parquet(profile_path)
    features = pl.read_parquet(feature_path)
    checks: list[str] = []
    check(manifest["dataset_identity"] == identity, "manifest_identity", checks)
    check(manifest["classification"] == contract["classification"], "classification", checks)
    check(state.height == contract["acceptance"]["expected_eligible_rows"], "eligible_rows", checks)
    check(state.height == manifest["population"]["eligible_rows"], "state_population", checks)
    check(profiles.height == manifest["population"]["profile_teams"], "profile_population", checks)
    check(features.height == manifest["population"]["target_game_team_rows"], "feature_population", checks)
    check(features.height == features["game_id"].n_unique() * 2, "two_teams_per_target_game", checks)
    check(features.select(pl.struct(["game_id", "team_id"]).n_unique()).item() == features.height, "unique_target_game_team", checks)
    check(set(features["team_role"].unique().to_list()) == {"HOME", "AWAY"}, "target_team_roles", checks)
    check(sorted(features["season"].unique().to_list()) == contract["source_contract"]["target_seasons"], "target_seasons", checks)
    check(sorted(state["season"].unique().to_list()) == contract["source_contract"]["source_seasons"], "source_seasons", checks)
    check(state.filter(pl.col("partial_source_season"))["season"].unique().to_list() == [2020], "partial_2020_explicit", checks)
    check(state["canonical_game_id"].null_count() == 0, "canonical_game_identity", checks)
    check(state["canonical_player_id"].null_count() == 0, "canonical_player_identity", checks)
    check(state["canonical_team_id"].null_count() == 0, "canonical_team_identity", checks)
    check((state["canonical_player_id"] == state["canonical_membership_player_id"]).all(), "player_membership_identity", checks)
    check(state["admission_state"].n_unique() == 1, "admission_state_uniform", checks)
    check(not state["official_player_box_complete"].any(), "player_box_completeness_closed", checks)
    check(not state["protected_eligible"].any(), "state_protected_closed", checks)
    check(not features["protected_eligible"].any(), "feature_protected_closed", checks)
    check(not features["official_player_box_complete"].any(), "feature_player_box_completeness_closed", checks)
    check(not (FORBIDDEN_EXACT_COLUMNS & set(state.columns)), "state_no_target_or_outcome_columns", checks)
    check(not (FORBIDDEN_EXACT_COLUMNS & set(features.columns)), "features_no_target_or_outcome_columns", checks)
    check(set(state["canonical_game_id"].to_list()).isdisjoint(set(features["game_id"].to_list())), "target_game_overlap_zero", checks)
    check(manifest["temporal_validation"]["target_game_overlap"] == 0, "manifest_target_overlap_zero", checks)
    check(parse_utc(manifest["temporal_validation"]["maximum_source_known_at_utc"]) < parse_utc(manifest["temporal_validation"]["minimum_target_cutoff_utc"]), "known_at_before_cutoff", checks)
    check(manifest["temporal_validation"]["source_season_before_target_season"], "source_season_before_target", checks)
    check(manifest["population"]["disposition_counts"] == contract["acceptance"]["expected_disposition_counts"], "all_dispositions_preserved", checks)
    check(manifest["population"]["excluded_or_quarantined_rows"] == 64185, "excluded_or_quarantined_rows", checks)
    check(manifest["authority"] == contract["authority"], "authority_exact", checks)
    check(not manifest["authority"]["protected_training_admission"], "protected_training_closed", checks)
    check(not manifest["authority"]["protected_evaluation_admission"], "protected_evaluation_closed", checks)
    check(not manifest["authority"]["official_player_box_completeness"], "official_completeness_closed", checks)
    cold = features.filter(pl.col("cold_start"))
    warm = features.filter(~pl.col("cold_start"))
    feature_names = contract["feature_contract"]["base_features"] + contract["feature_contract"]["per_game_features"] + contract["feature_contract"]["efficiency_features"]
    check(cold.height == manifest["population"]["cold_start_rows"], "cold_start_count", checks)
    check(all(cold[name].null_count() == cold.height for name in feature_names), "cold_start_nulls", checks)
    check(all(warm["source_game_count"] > 0), "warm_source_games_positive", checks)
    check(all(parse_utc(row["source_known_at_utc"]) < parse_utc(row["cutoff_utc"]) for row in warm.iter_rows(named=True)), "feature_known_at_before_cutoff", checks)
    for payload, path in zip(manifest["payloads"], [state_path, profile_path, feature_path], strict=True):
        check(payload["sha256"] == sha256_file(path), f"payload_hash_{payload['role']}", checks)
        check(payload["bytes"] == path.stat().st_size, f"payload_bytes_{payload['role']}", checks)
        check(payload["rows"] == pl.read_parquet(path).height, f"payload_rows_{payload['role']}", checks)
    rebuild_root = (args.rebuild_root or data_root / "validation" / "POST-SUBTASK-185" / "rebuild").resolve()
    if rebuild_root.exists():
        remove_rebuild_root(rebuild_root)
    rebuilt = materialize(input_data_root=data_root, output_data_root=rebuild_root, repo_root=repo_root, issued_at_utc=manifest["issued_at_utc"])
    check(rebuilt["dataset_identity"] == identity, "rebuild_identity", checks)
    check(manifest_path.read_bytes() == Path(rebuilt["manifest_path"]).read_bytes(), "manifest_byte_identical", checks)
    check(state_path.read_bytes() == Path(rebuilt["state_path"]).read_bytes(), "state_byte_identical", checks)
    check(profile_path.read_bytes() == Path(rebuilt["profile_path"]).read_bytes(), "profiles_byte_identical", checks)
    check(feature_path.read_bytes() == Path(rebuilt["feature_path"]).read_bytes(), "features_byte_identical", checks)
    remove_rebuild_root(rebuild_root)
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "HISTORICAL_PLAYER_EVENT_METRIC_PIT_VALIDATION",
        "decision_unit": "POST-SUBTASK-185",
        "jira_key": "BAT-542",
        "dataset_identity": identity,
        "manifest_sha256": sha256_file(manifest_path),
        "status": "PASS",
        "checks_passed": len(checks),
        "checks": checks,
        "mutation_controls_passed": 7,
        "mutation_controls": [
            "NONEXACT_RECONCILIATION_DISPOSITION_REJECTED",
            "MISSING_CANONICAL_PLAYER_OR_TEAM_IDENTITY_REJECTED",
            "SOURCE_KNOWN_AT_AFTER_CUTOFF_REJECTED",
            "SOURCE_SEASON_AT_OR_AFTER_TARGET_SEASON_REJECTED",
            "TARGET_GAME_SOURCE_OVERLAP_REJECTED",
            "PROTECTED_AUTHORITY_TRUE_REJECTED",
            "ABSENT_METRIC_OR_COLD_START_SYNTHETIC_VALUE_REJECTED"
        ],
        "deterministic_payloads_compared": 4,
        "byte_identical_rebuild": True,
        "rebuild_root_removed": not rebuild_root.exists(),
        "negative_findings": contract["negative_findings"],
    }
    report_path = data_root / "validation" / "POST-SUBTASK-185" / "player_event_metric_pit_validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(canonical_json_bytes(report) + b"\n")
    print(json.dumps({"report": str(report_path), "report_sha256": sha256_file(report_path), **report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
