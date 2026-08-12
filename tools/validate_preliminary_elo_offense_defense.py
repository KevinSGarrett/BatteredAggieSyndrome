"""Validate and deterministically rebuild the offense/defense Elo challenger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import polars as pl  # noqa: E402
import run_preliminary_elo_offense_defense as candidate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--run-identity", required=True)
    parser.add_argument("--rebuild-root", type=Path, required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    args = parser.parse_args()
    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    rebuild_root = args.rebuild_root.resolve()
    if rebuild_root.exists():
        raise ValueError(f"rebuild root already exists: {rebuild_root}")
    manifest_path = data_root / "manifests/preliminary_elo_offense_defense/sha256" / args.run_identity / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    predictions = pl.read_parquet(manifest["prediction_path"])
    input_path = (
        data_root
        / "training/preliminary_event_chronology/sha256"
        / candidate.DATASET_IDENTITY
        / "training_matrix.parquet"
    )
    inputs = pl.read_parquet(input_path)
    rebuilt_manifest, rebuilt_rows = candidate.compute(repo_root, data_root)
    checks: list[dict[str, object]] = []
    failures: list[str] = []

    def check(name: str, condition: bool, detail: object = None) -> None:
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            failures.append(name)

    check("run_identity", manifest["run_identity"] == args.run_identity == rebuilt_manifest["run_identity"])
    check("classification", manifest["classification"] == candidate.CLASSIFICATION)
    expected_families = [
        candidate.REFERENCE_FAMILY,
        candidate.BOUNDED_MARGIN_FAMILY,
        candidate.CALIBRATED_SCALAR_FAMILY,
        candidate.CANDIDATE_FAMILY,
    ]
    check("families", manifest["families"] == expected_families)
    check("family_count", manifest["family_count"] == 4)
    check("prediction_hash", candidate.sha256_file(Path(manifest["prediction_path"])) == manifest["prediction_sha256"])
    check("input_dataset_identity", manifest["dataset_identity"] == candidate.DATASET_IDENTITY)
    check("input_dataset_hash", candidate.sha256_file(input_path) == manifest["dataset_sha256"])
    check(
        "input_classification",
        inputs["classification"].unique().to_list() == ["PRELIMINARY_UNPROTECTED_EVENT_CHRONOLOGY_ONLY"],
    )
    check(
        "input_assignment_scope",
        set(inputs["assignment"].unique().to_list())
        == {"DEVELOPMENT_FIT", "DEVELOPMENT_TUNE", "DEVELOPMENT_EVALUATION_UNPROTECTED"},
    )
    check(
        "input_target_evidence_exclusion",
        inputs.filter(pl.col("target_outcome_in_feature_evidence") | pl.col("rankings_target_outcome_in_feature_evidence")).height
        == 0,
    )
    check("input_cutoff_before_start", inputs.filter(pl.col("cutoff_utc") >= pl.col("start_utc")).height == 0)
    check(
        "historical_known_at_not_overclaimed",
        inputs.filter(pl.col("historical_known_at_eligible")).height == 0
        and manifest["eligibility"] == "DEVELOPMENT_UNPROTECTED_EXPOSED_CANDIDATE_ONLY",
    )
    check("prediction_rows", predictions.height == manifest["prediction_rows"] == manifest["development_game_count"] * 4)
    check("unique_family_game", predictions.select("family", "target_game_id").unique().height == predictions.height)
    check("seasons", sorted(predictions["season"].unique().to_list()) == [2023, 2024, 2025])
    check("probability_bounds", predictions.filter(~pl.col("home_win_probability").is_between(0.0, 1.0)).height == 0)
    check("finite_margin", predictions.filter(pl.col("predicted_margin").is_nan() | pl.col("predicted_margin").is_infinite()).height == 0)
    check("report_not_selection", manifest["parameter_selection_uses_report_seasons"] is False)
    check("bootstrap_honesty", manifest["bootstrap_added_after_first_result_inspection"] is True)
    check("target_game_leakage_closed", manifest["target_game_outcome_used_before_prediction"] is False)
    check("candidate_only", manifest["eligibility"] == "DEVELOPMENT_UNPROTECTED_EXPOSED_CANDIDATE_ONLY")
    check("protected_closed", manifest["protected_performance_claimed"] is False and manifest["promotion_authority"] is False)
    check("a_and_m_bas_closed", manifest["a_and_m_lift_claimed"] is False and manifest["bas_or_aggie_excess_claimed"] is False)
    check("selection_trials", len(manifest["selection_trials"]) == 12 and all(row["fit_rows"] > 0 for row in manifest["selection_trials"]))
    check("selection_fit_only", manifest["fit_seasons"] == list(range(2010, 2023)))
    check("report_only", manifest["report_only_exposed_seasons"] == [2023, 2024, 2025])
    selected = manifest["selected_parameters"]
    check("selected_from_grid", any(row == selected for row in manifest["selection_trials"]))
    check(
        "bootstrap_shape",
        set(manifest["post_result_bootstrap_diagnostic"]) == {"2023", "2024", "2025"}
        and all(
            result[metric]["rows"] > 0
            and result[metric]["replicates"] == 2000
            and result[metric]["percentile_95_lower"] <= result[metric]["percentile_95_upper"]
            for result in manifest["post_result_bootstrap_diagnostic"].values()
            for metric in ("brier_vs_calibrated_scalar", "log_loss_vs_calibrated_scalar", "margin_mae_vs_bounded_scalar")
        ),
    )
    candidate_rows = predictions.filter(pl.col("family") == candidate.CANDIDATE_FAMILY)
    check(
        "components_finite",
        all(
            candidate_rows.filter(pl.col(field).is_null() | pl.col(field).is_nan() | pl.col(field).is_infinite()).height == 0
            for field in (
                "home_offense_component",
                "home_defense_component",
                "away_offense_component",
                "away_defense_component",
            )
        ),
    )
    check(
        "information_scarcity_bounds",
        candidate_rows.filter(
            ~pl.col("home_information_scarcity").is_between(0.0, 1.0)
            | ~pl.col("away_information_scarcity").is_between(0.0, 1.0)
        ).height
        == 0,
    )
    check(
        "component_games_nonnegative",
        candidate_rows.filter((pl.col("home_component_games") < 0) | (pl.col("away_component_games") < 0)).height == 0,
    )
    scarcity_mismatch = candidate_rows.filter(
        (
            (pl.col("home_information_scarcity") - (1.0 / (pl.col("home_component_games") + 1).sqrt())).abs()
            > 1e-12
        )
        | (
            (pl.col("away_information_scarcity") - (1.0 / (pl.col("away_component_games") + 1).sqrt())).abs()
            > 1e-12
        )
    )
    check("information_scarcity_formula", scarcity_mismatch.height == 0)
    bootstrap = manifest["post_result_bootstrap_diagnostic"]
    check(
        "bootstrap_disposition_consistency",
        manifest["bootstrap_all_core_95_upper_below_zero"]
        == all(
            bootstrap[str(season)][metric]["percentile_95_upper"] < 0.0
            for season in candidate.REPORT_SEASONS
            for metric in ("brier_vs_calibrated_scalar", "log_loss_vs_calibrated_scalar", "margin_mae_vs_bounded_scalar")
        )
        and manifest["disposition"]
        == "PROMISING_POST_RESULT_BOOTSTRAP_SUPPORTED_REQUIRES_UNTOUCHED_PROTECTED_REPLICATION",
    )
    for season in candidate.REPORT_SEASONS:
        reference_ids = set(
            predictions.filter((pl.col("family") == candidate.REFERENCE_FAMILY) & (pl.col("season") == season))[
                "target_game_id"
            ].to_list()
        )
        for family in expected_families:
            family_ids = set(
                predictions.filter((pl.col("family") == family) & (pl.col("season") == season))["target_game_id"].to_list()
            )
            check(f"common_support_{family}_{season}", reference_ids == family_ids)
    comparable_manifest = {key: value for key, value in manifest.items() if key not in {"prediction_path", "prediction_sha256"}}
    check("deterministic_manifest_rebuild", comparable_manifest == rebuilt_manifest)
    rebuilt_frame = pl.DataFrame(rebuilt_rows, infer_schema_length=None).sort(
        ["family", "season", "season_type", "week", "start_utc", "target_game_id"]
    )
    rebuilt_path = rebuild_root / "predictions.parquet"
    rebuilt_path.parent.mkdir(parents=True, exist_ok=True)
    rebuilt_frame.write_parquet(rebuilt_path, compression="zstd")
    check("byte_identical_prediction_rebuild", rebuilt_path.read_bytes() == Path(manifest["prediction_path"]).read_bytes())
    mutation_controls = {
        "protected_claim_closed": manifest["protected_performance_claimed"] is False,
        "promotion_closed": manifest["promotion_authority"] is False,
        "report_selection_closed": manifest["parameter_selection_uses_report_seasons"] is False,
        "target_game_leakage_closed": manifest["target_game_outcome_used_before_prediction"] is False,
        "identity_drift_closed": manifest["run_identity"] == args.run_identity,
    }
    check("mutation_controls", all(mutation_controls.values()), mutation_controls)
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "PRELIMINARY_ELO_OFFENSE_DEFENSE_VALIDATION",
        "classification": candidate.CLASSIFICATION,
        "run_identity": args.run_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": candidate.sha256_file(manifest_path),
        "prediction_sha256": manifest["prediction_sha256"],
        "checks_passed": sum(row["result"] == "PASS" for row in checks),
        "checks_failed": len(failures),
        "checks": checks,
        "mutation_controls": mutation_controls,
        "result": "PASS" if not failures else "FAIL",
        "failures": failures,
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_bytes(candidate.canonical_json(report) + b"\n")
    print(
        json.dumps(
            {
                "result": report["result"],
                "checks_passed": report["checks_passed"],
                "checks_failed": report["checks_failed"],
                "report_path": str(args.report_path.resolve()),
                "report_sha256": candidate.sha256_file(args.report_path),
            },
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
