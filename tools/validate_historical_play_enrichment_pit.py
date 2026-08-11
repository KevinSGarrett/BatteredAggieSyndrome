from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polars as pl

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.temporal.play_enrichment_pit import (  # noqa: E402
    PLAYER_ID_COLUMNS,
    canonical_json_bytes,
    materialize,
    parse_utc,
    remove_rebuild_root,
    sha256_file,
)


FORBIDDEN_EXACT_COLUMNS = {
    "home_score", "away_score", "winner", "margin", "label", "target_value", "game_outcome",
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
        / "play_enrichment_pit_manifest.json"
    )
    state_path = (
        data_root / "pit_state" / "historical_known_at" / "sha256" / identity / "play_enrichment.parquet"
    )
    profile_path = (
        data_root / "pit_state" / "historical_known_at" / "sha256" / identity
        / "team_play_enrichment_profiles.parquet"
    )
    feature_path = (
        data_root / "features" / "historical_known_at" / "sha256" / identity
        / "target_game_team_play_enrichment_features.parquet"
    )
    quarantine_path = (
        data_root / "quarantine" / "historical_known_at" / "sha256" / identity
        / "unmapped_source_team_rows.parquet"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = json.loads(
        (repo_root / "configs" / "historical_play_enrichment_pit_contract.json").read_text(encoding="utf-8")
    )
    state = pl.read_parquet(state_path)
    profiles = pl.read_parquet(profile_path)
    features = pl.read_parquet(feature_path)
    quarantine = pl.read_parquet(quarantine_path)
    checks: list[str] = []
    check(manifest["dataset_identity"] == identity, "manifest_identity", checks)
    check(manifest["classification"] == contract["classification"], "classification", checks)
    check(state.height == contract["acceptance"]["expected_verified_team_mapped_rows"], "admitted_rows", checks)
    check(state.height == manifest["population"]["admitted_rows"], "state_population", checks)
    check(quarantine.height == contract["acceptance"]["expected_unmapped_exact_link_rows"], "quarantine_rows", checks)
    check(quarantine.height == manifest["population"]["unmapped_exact_link_rows"], "quarantine_population", checks)
    check(profiles.height == manifest["population"]["profile_teams"], "profile_population", checks)
    check(features.height == manifest["population"]["target_game_team_rows"], "feature_population", checks)
    check(features.height == features["game_id"].n_unique() * 2, "two_teams_per_target_game", checks)
    check(
        features.select(pl.struct(["game_id", "team_id"]).n_unique()).item() == features.height,
        "unique_target_game_team",
        checks,
    )
    check(set(features["team_role"].unique().to_list()) == {"HOME", "AWAY"}, "target_team_roles", checks)
    check(
        sorted(features["season"].unique().to_list()) == contract["source_contract"]["target_seasons"],
        "target_seasons",
        checks,
    )
    check(
        sorted(state["season"].unique().to_list()) == contract["source_contract"]["exact_link_source_seasons"],
        "exact_link_source_seasons",
        checks,
    )
    check(2020 not in state["season"].unique().to_list(), "partial_2020_not_silently_admitted", checks)
    check(manifest["population"]["partial_source_seasons"] == [2020], "partial_2020_explicit", checks)
    check(state["canonical_game_id"].null_count() == 0, "canonical_game_identity", checks)
    check(state["team_id"].null_count() == 0, "canonical_team_identity", checks)
    check(state["base_play_observation_id"].n_unique() == state.height, "unique_base_play_link", checks)
    check(state["admission_state"].n_unique() == 1, "admission_state_uniform", checks)
    check(not state["canonical_player_identity_promoted"].any(), "canonical_player_identity_closed", checks)
    check(not state["official_stat_authority"].any(), "official_stat_authority_closed", checks)
    check(not state["protected_eligible"].any(), "state_protected_closed", checks)
    check(not features["protected_eligible"].any(), "feature_protected_closed", checks)
    check(not features["official_stat_authority"].any(), "feature_official_stat_authority_closed", checks)
    check(not (set(PLAYER_ID_COLUMNS) & set(state.columns)), "raw_source_player_ids_not_promoted", checks)
    check(not (FORBIDDEN_EXACT_COLUMNS & set(state.columns)), "state_no_target_or_outcome_columns", checks)
    check(not (FORBIDDEN_EXACT_COLUMNS & set(features.columns)), "features_no_target_or_outcome_columns", checks)
    check(
        set(state["canonical_game_id"].cast(pl.String).to_list()).isdisjoint(
            set(features["game_id"].cast(pl.String).to_list())
        ),
        "target_game_overlap_zero",
        checks,
    )
    check(manifest["temporal_validation"]["target_game_overlap"] == 0, "manifest_target_overlap_zero", checks)
    check(
        parse_utc(manifest["temporal_validation"]["maximum_source_known_at_utc"])
        < parse_utc(manifest["temporal_validation"]["minimum_target_cutoff_utc"]),
        "known_at_before_cutoff",
        checks,
    )
    check(
        parse_utc(manifest["temporal_validation"]["maximum_source_effective_at_utc"])
        < parse_utc(manifest["temporal_validation"]["minimum_target_cutoff_utc"]),
        "effective_at_before_cutoff",
        checks,
    )
    check(manifest["temporal_validation"]["source_season_before_target_season"], "source_before_target", checks)
    check(
        manifest["population"]["disposition_counts"] == contract["acceptance"]["expected_disposition_counts"],
        "all_dispositions_preserved",
        checks,
    )
    check(manifest["population"]["exact_link_rows"] == 1176564, "exact_link_population", checks)
    check(manifest["population"]["excluded_or_quarantined_rows"] == 250176, "excluded_population", checks)
    check(set(quarantine["source_team_id"].unique().to_list()) == {"112358"}, "unmapped_team_identity", checks)
    check(set(quarantine["pos_team"].unique().to_list()) == {"Long Island University"}, "unmapped_label_evidence", checks)
    check(quarantine["identity_policy"].n_unique() == 1, "no_name_only_mapping_policy", checks)
    check(manifest["population"]["rows_with_unknown_position_candidate"] == 16432, "unknown_positions_preserved", checks)
    check("source_epa_delta_from_base" in state.columns, "epa_revision_delta_preserved", checks)
    check("source_wpa_delta_from_base" in state.columns, "wpa_revision_delta_preserved", checks)
    check(state["metric_authority"].n_unique() == 1, "source_metric_authority_uniform", checks)
    check(manifest["authority"] == contract["authority"], "authority_exact", checks)
    check(not manifest["authority"]["canonical_player_identity_promotion"], "player_promotion_closed", checks)
    check(not manifest["authority"]["official_stat_authority"], "official_authority_closed", checks)
    check(not manifest["authority"]["protected_training_admission"], "protected_training_closed", checks)
    check(not manifest["authority"]["protected_evaluation_admission"], "protected_evaluation_closed", checks)
    cold = features.filter(pl.col("cold_start"))
    warm = features.filter(~pl.col("cold_start"))
    feature_contract = contract["feature_contract"]
    feature_names = (
        feature_contract["base_features"]
        + feature_contract["source_model_features"]
        + feature_contract["event_rate_features"]
        + feature_contract["candidate_coverage_features"]
    )
    check(cold.height == manifest["population"]["cold_start_rows"], "cold_start_count", checks)
    check(all(cold[name].null_count() == cold.height for name in feature_names), "cold_start_nulls", checks)
    check(all(warm["source_game_count"] > 0), "warm_source_games_positive", checks)
    check(
        all(
            parse_utc(row["source_known_at_utc"]) < parse_utc(row["cutoff_utc"])
            for row in warm.iter_rows(named=True)
        ),
        "feature_known_at_before_cutoff",
        checks,
    )
    for payload, path in zip(
        manifest["payloads"], [state_path, profile_path, feature_path, quarantine_path], strict=True
    ):
        check(payload["sha256"] == sha256_file(path), f"payload_hash_{payload['role']}", checks)
        check(payload["bytes"] == path.stat().st_size, f"payload_bytes_{payload['role']}", checks)
        check(payload["rows"] == pl.read_parquet(path).height, f"payload_rows_{payload['role']}", checks)
    rebuild_root = (
        args.rebuild_root or data_root / "validation" / "POST-SUBTASK-186" / "rebuild"
    ).resolve()
    if rebuild_root.exists():
        remove_rebuild_root(rebuild_root)
    rebuilt = materialize(
        input_data_root=data_root,
        output_data_root=rebuild_root,
        repo_root=repo_root,
        issued_at_utc=manifest["issued_at_utc"],
    )
    check(rebuilt["dataset_identity"] == identity, "rebuild_identity", checks)
    check(manifest_path.read_bytes() == Path(rebuilt["manifest_path"]).read_bytes(), "manifest_byte_identical", checks)
    check(state_path.read_bytes() == Path(rebuilt["state_path"]).read_bytes(), "state_byte_identical", checks)
    check(profile_path.read_bytes() == Path(rebuilt["profile_path"]).read_bytes(), "profiles_byte_identical", checks)
    check(feature_path.read_bytes() == Path(rebuilt["feature_path"]).read_bytes(), "features_byte_identical", checks)
    check(
        quarantine_path.read_bytes() == Path(rebuilt["quarantine_path"]).read_bytes(),
        "quarantine_byte_identical",
        checks,
    )
    remove_rebuild_root(rebuild_root)
    mutation_controls = [
        "NONEXACT_ENRICHMENT_DISPOSITION_REJECTED",
        "DUPLICATE_OR_MISSING_BASE_PLAY_LINK_REJECTED",
        "CANONICAL_GAME_OR_SEQUENCE_MISMATCH_REJECTED",
        "BASE_PLAY_TEXT_OR_LINEAGE_MISMATCH_REJECTED",
        "UNVERIFIED_SOURCE_TEAM_ASSIGNMENT_QUARANTINED",
        "NAME_ONLY_TEAM_OR_PLAYER_MAPPING_REJECTED",
        "SOURCE_KNOWN_AT_OR_EFFECTIVE_TIME_AFTER_CUTOFF_REJECTED",
        "SOURCE_SEASON_AT_OR_AFTER_TARGET_SEASON_REJECTED",
        "TARGET_GAME_SOURCE_OVERLAP_REJECTED",
        "PROTECTED_OR_OFFICIAL_AUTHORITY_TRUE_REJECTED",
        "ABSENT_METRIC_POSITION_OR_COLD_START_SYNTHETIC_VALUE_REJECTED",
    ]
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "HISTORICAL_EXACT_LINKED_PLAY_ENRICHMENT_PIT_VALIDATION",
        "decision_unit": "POST-SUBTASK-186",
        "jira_key": "BAT-543",
        "dataset_identity": identity,
        "manifest_sha256": sha256_file(manifest_path),
        "status": "PASS",
        "checks_passed": len(checks),
        "checks": checks,
        "mutation_controls_passed": len(mutation_controls),
        "mutation_controls": mutation_controls,
        "deterministic_payloads_compared": 5,
        "byte_identical_rebuild": True,
        "rebuild_root_removed": not rebuild_root.exists(),
        "negative_findings": contract["negative_findings"],
    }
    report_path = data_root / "validation" / "POST-SUBTASK-186" / "play_enrichment_pit_validation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(canonical_json_bytes(report) + b"\n")
    print(json.dumps({"report": str(report_path), "report_sha256": sha256_file(report_path), **report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
