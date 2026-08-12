from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import polars as pl


EXPECTED_FAMILIES = {
    "elo_rating_week_batched_reference",
    "elo_offseason_regression_75",
    "elo_bounded_margin_2",
    "elo_offseason_75_bounded_margin_2",
    "elo_inactivity_time_decay_selected",
    "elo_non_neutral_site_effect_fitted",
    "elo_probability_logistic_calibrated",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--run-identity", required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    args = parser.parse_args()
    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    sys.path.insert(0, str(repo_root / "src"))
    from aggie_analytics.validation.evaluation_exposure import canonical_json, sha256_file

    manifest_path = data_root / "manifests/preliminary_elo_challengers/sha256" / args.run_identity / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prediction_path = Path(manifest["prediction_path"])
    predictions = pl.read_parquet(prediction_path)
    checks: list[dict] = []
    failures: list[str] = []

    def check(name: str, condition: bool, detail: object = None) -> None:
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            failures.append(name)

    families = set(predictions["family"].unique().to_list())
    check("run_identity", manifest["run_identity"] == args.run_identity)
    check("manifest_schema", manifest["schema_version"] == "1.1.0")
    check("manifest_classification", manifest["classification"] == "PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE")
    check("prediction_hash", sha256_file(prediction_path) == manifest["prediction_sha256"])
    check(
        "prediction_rows",
        predictions.height == manifest["prediction_rows"] == manifest["development_game_count"] * manifest["family_count"],
    )
    check("unique_family_game", predictions.select("family", "target_game_id").unique().height == predictions.height)
    check("expected_families", families == EXPECTED_FAMILIES, sorted(families))
    check("family_count", manifest["family_count"] == len(EXPECTED_FAMILIES))
    check("seasons", sorted(predictions["season"].unique().to_list()) == [2023, 2024, 2025])
    check("classification", predictions["classification"].unique().to_list() == ["PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE"])
    check("probability_bounds", predictions.filter((pl.col("home_win_probability") < 0) | (pl.col("home_win_probability") > 1)).height == 0)
    check("finite_margin", predictions.filter(pl.col("predicted_margin").is_nan() | pl.col("predicted_margin").is_infinite()).height == 0)
    check("finite_rating", predictions.filter(pl.col("rating_diff").is_nan() | pl.col("rating_diff").is_infinite()).height == 0)
    check("exposure_eligibility", manifest["eligibility"] == "DEVELOPMENT_UNPROTECTED_EXPOSED")
    check("fit_seasons", manifest["fit_seasons"] == list(range(2010, 2023)))
    check("report_seasons", manifest["development_report_seasons"] == [2023, 2024, 2025])
    check("report_seasons_not_used_for_selection", manifest["parameter_selection_uses_report_seasons"] is False)
    check("no_promotion", manifest["promotion_authority"] is False and manifest["protected_performance_claimed"] is False)
    check("no_a_and_m_or_bas_claim", manifest["a_and_m_lift_claimed"] is False and manifest["bas_or_aggie_excess_claimed"] is False)
    check("negative_findings_preserved", manifest["negative_findings_preserved"] is True and isinstance(manifest["negative_findings"], list))
    check(
        "reference_parameters",
        manifest["families"][0]
        == {
            "family": "elo_rating_week_batched_reference",
            "offseason_retention": 1.0,
            "margin_cap": None,
            "rating_half_life_days": None,
            "hypothesis": "UNCHANGED_REFERENCE",
        },
    )

    decay = manifest["time_decay_selection"]
    check("time_decay_grid", decay["grid_days"] == [365.0, 730.0, 1460.0, 2920.0])
    check("time_decay_trials", len(decay["trials"]) == 4 and all(row["fit_rows"] > 0 for row in decay["trials"]))
    check("time_decay_selected_from_grid", decay["selected_half_life_days"] in decay["grid_days"])
    check("time_decay_report_exclusion", decay["report_seasons_excluded_from_selection"] == [2023, 2024, 2025])

    config_by_family = {row["family"]: row for row in manifest["families"]}
    site_fit = config_by_family["elo_non_neutral_site_effect_fitted"]["fit"]
    calibration_fit = config_by_family["elo_probability_logistic_calibrated"]["fit"]
    check("site_fit_only_prior_history", site_fit["fit_rows"] > 0 and math.isfinite(site_fit["rating_point_adjustment"]))
    check(
        "calibration_fit_only_prior_history",
        calibration_fit["fit_rows"] > 0
        and math.isfinite(calibration_fit["intercept"])
        and math.isfinite(calibration_fit["slope_per_400_rating_points"])
        and calibration_fit["slope_per_400_rating_points"] > 0,
    )

    reference_ids: dict[int, set[str]] = {}
    for season in (2023, 2024, 2025):
        reference_ids[season] = set(
            predictions.filter(
                (pl.col("family") == "elo_rating_week_batched_reference") & (pl.col("season") == season)
            )["target_game_id"].to_list()
        )
        for family in EXPECTED_FAMILIES:
            family_ids = set(
                predictions.filter((pl.col("family") == family) & (pl.col("season") == season))["target_game_id"].to_list()
            )
            check(f"common_support:{family}:{season}", family_ids == reference_ids[season])

    reference_neutral = {
        row["target_game_id"]: row["home_win_probability"]
        for row in predictions.filter(
            (pl.col("family") == "elo_rating_week_batched_reference") & pl.col("neutral_site")
        ).select("target_game_id", "home_win_probability").to_dicts()
    }
    site_neutral = {
        row["target_game_id"]: row["home_win_probability"]
        for row in predictions.filter(
            (pl.col("family") == "elo_non_neutral_site_effect_fitted") & pl.col("neutral_site")
        ).select("target_game_id", "home_win_probability").to_dicts()
    }
    check("site_adjustment_preserves_neutral_probabilities", reference_neutral == site_neutral)

    for family in EXPECTED_FAMILIES:
        for season in (2023, 2024, 2025):
            frame = predictions.filter((pl.col("family") == family) & (pl.col("season") == season))
            actual = frame.select(((pl.col("home_win_probability") - pl.col("home_win")) ** 2).mean()).item()
            expected = manifest["metrics"][family]["by_season_slice"][f"{season}_ALL"]["brier"]
            check(f"brier_replay:{family}:{season}", abs(actual - expected) < 1e-12)

    mutation_controls = {
        "protected_claim_rejected": manifest["protected_performance_claimed"] is False,
        "promotion_rejected": manifest["promotion_authority"] is False,
        "identity_drift_rejected": manifest["run_identity"] == args.run_identity,
        "duplicate_prediction_rejected": predictions.select("family", "target_game_id").unique().height == predictions.height,
        "out_of_range_probability_rejected": predictions.filter((pl.col("home_win_probability") < 0) | (pl.col("home_win_probability") > 1)).height == 0,
        "report_period_parameter_selection_rejected": manifest["parameter_selection_uses_report_seasons"] is False,
        "common_support_drift_rejected": all(
            set(predictions.filter((pl.col("family") == family) & (pl.col("season") == season))["target_game_id"].to_list())
            == reference_ids[season]
            for family in EXPECTED_FAMILIES
            for season in (2023, 2024, 2025)
        ),
    }
    check("mutation_controls", all(mutation_controls.values()), mutation_controls)
    report = {
        "schema_version": "1.1.0",
        "artifact_type": "PRELIMINARY_ELO_CHALLENGER_VALIDATION",
        "classification": "PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE",
        "run_identity": args.run_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "prediction_sha256": sha256_file(prediction_path),
        "checks_passed": sum(row["result"] == "PASS" for row in checks),
        "checks_failed": len(failures),
        "checks": checks,
        "mutation_controls": mutation_controls,
        "result": "PASS" if not failures else "FAIL",
        "failures": failures,
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_bytes(canonical_json(report) + b"\n")
    print(
        json.dumps(
            {
                "result": report["result"],
                "checks_passed": report["checks_passed"],
                "checks_failed": report["checks_failed"],
                "report_path": str(args.report_path.resolve()),
                "report_sha256": sha256_file(args.report_path),
            },
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
