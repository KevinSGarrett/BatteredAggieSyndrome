"""Validate and deterministically rebuild the bounded Elo uncertainty run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import polars as pl  # noqa: E402
import run_preliminary_elo_uncertainty as candidate  # noqa: E402


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
    manifest_path = (
        data_root
        / "manifests/preliminary_elo_uncertainty/sha256"
        / args.run_identity
        / "run_manifest.json"
    )
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
        checks.append(
            {"check": name, "result": "PASS" if condition else "FAIL", "detail": detail}
        )
        if not condition:
            failures.append(name)

    expected_families = [
        candidate.REFERENCE_FAMILY,
        candidate.SUPPORT_FAMILY,
        candidate.BOOTSTRAP_FAMILY,
    ]
    check(
        "run_identity",
        manifest["run_identity"]
        == args.run_identity
        == rebuilt_manifest["run_identity"],
    )
    check("classification", manifest["classification"] == candidate.CLASSIFICATION)
    check("families", manifest["families"] == expected_families)
    check(
        "input_dataset_identity",
        manifest["dataset_identity"] == candidate.DATASET_IDENTITY,
    )
    check(
        "input_dataset_hash",
        candidate.sha256_file(input_path) == manifest["dataset_sha256"],
    )
    check(
        "prediction_hash",
        candidate.sha256_file(Path(manifest["prediction_path"]))
        == manifest["prediction_sha256"],
    )
    check(
        "input_classification",
        inputs["classification"].unique().to_list()
        == ["PRELIMINARY_UNPROTECTED_EVENT_CHRONOLOGY_ONLY"],
    )
    check(
        "input_assignment_scope",
        set(inputs["assignment"].unique().to_list())
        == {
            "DEVELOPMENT_FIT",
            "DEVELOPMENT_TUNE",
            "DEVELOPMENT_EVALUATION_UNPROTECTED",
        },
    )
    check(
        "target_evidence_exclusion",
        inputs.filter(
            pl.col("target_outcome_in_feature_evidence")
            | pl.col("rankings_target_outcome_in_feature_evidence")
        ).height
        == 0,
    )
    check(
        "cutoff_before_start",
        inputs.filter(pl.col("cutoff_utc") >= pl.col("start_utc")).height == 0,
    )
    check(
        "historical_known_at_closed",
        inputs.filter(pl.col("historical_known_at_eligible")).height == 0,
    )
    check(
        "fit_only",
        manifest["fit_seasons"] == list(range(2010, 2023))
        and manifest["fit_rows"] == 10593,
    )
    check("report_only", manifest["report_only_exposed_seasons"] == [2023, 2024, 2025])
    check(
        "report_not_selection",
        manifest["parameter_selection_uses_report_seasons"] is False,
    )
    check(
        "same_game_closed",
        manifest["target_game_outcome_used_before_prediction"] is False,
    )
    check("prediction_rows", predictions.height == manifest["prediction_rows"] == 8289)
    check(
        "unique_family_game",
        predictions.select("family", "target_game_id").unique().height
        == predictions.height,
    )
    check(
        "seasons",
        sorted(predictions["season"].unique().to_list()) == [2023, 2024, 2025],
    )
    check(
        "probability_bounds",
        predictions.filter(~pl.col("home_win_probability").is_between(0.0, 1.0)).height
        == 0,
    )
    check(
        "positive_finite_variance",
        predictions.filter(
            (pl.col("margin_variance") <= 0.0)
            | pl.col("margin_variance").is_nan()
            | pl.col("margin_variance").is_infinite()
        ).height
        == 0,
    )
    check(
        "standard_deviation_formula",
        predictions.filter(
            (
                pl.col("margin_standard_deviation") - pl.col("margin_variance").sqrt()
            ).abs()
            > 1e-12
        ).height
        == 0,
    )
    reference = predictions.filter(pl.col("family") == candidate.REFERENCE_FAMILY)
    support = predictions.filter(pl.col("family") == candidate.SUPPORT_FAMILY)
    joined = reference.join(support, on="target_game_id", suffix="_support")
    check(
        "support_mean_unchanged",
        joined.filter(
            (
                (
                    pl.col("home_win_probability")
                    - pl.col("home_win_probability_support")
                ).abs()
                > 1e-15
            )
            | (
                (pl.col("predicted_margin") - pl.col("predicted_margin_support")).abs()
                > 1e-15
            )
        ).height
        == 0,
    )
    check(
        "support_formula",
        predictions.filter(
            (
                pl.col("uncertainty_support")
                - (
                    1.0 / (pl.col("home_prior_games") + 1).sqrt()
                    + 1.0 / (pl.col("away_prior_games") + 1).sqrt()
                )
            ).abs()
            > 1e-12
        ).height
        == 0,
    )
    bootstrap = predictions.filter(pl.col("family") == candidate.BOOTSTRAP_FAMILY)
    check(
        "bootstrap_epistemic_nonnegative",
        bootstrap.filter(
            pl.col("epistemic_margin_variance").is_null()
            | (pl.col("epistemic_margin_variance") < 0.0)
        ).height
        == 0,
    )
    check(
        "bootstrap_member_count",
        manifest["bootstrap_members"] == 64
        and len(manifest["bootstrap_member_fits"]) == 64,
    )
    check(
        "bootstrap_members_fit_only",
        all(row["fit_rows"] == 10593 for row in manifest["bootstrap_member_fits"]),
    )
    check(
        "support_stability_claim",
        manifest["support_distribution_stable"]
        == all(
            manifest["effects_vs_reference"][candidate.SUPPORT_FAMILY][f"{season}_ALL"][
                f"{metric}_delta"
            ]
            < 0.0
            for season in candidate.REPORT_SEASONS
            for metric in ("normal_margin_nll", "interval_80_score")
        ),
    )
    check(
        "bootstrap_rejected_distribution",
        manifest["bootstrap_distribution_stable"] is False,
    )
    check(
        "bootstrap_rejected_probability",
        manifest["bootstrap_probability_stable"] is False,
    )
    check("surfaces_not_combined", manifest["uncertainty_surfaces_combined"] is False)
    check(
        "candidate_only",
        manifest["eligibility"] == "DEVELOPMENT_UNPROTECTED_EXPOSED_CANDIDATE_ONLY"
        and manifest["promotion_authority"] is False
        and manifest["protected_performance_claimed"] is False,
    )
    check(
        "a_and_m_bas_closed",
        manifest["a_and_m_lift_claimed"] is False
        and manifest["bas_or_aggie_excess_claimed"] is False,
    )
    for season in candidate.REPORT_SEASONS:
        reference_ids = set(
            reference.filter(pl.col("season") == season)["target_game_id"].to_list()
        )
        for family in expected_families:
            family_ids = set(
                predictions.filter(
                    (pl.col("family") == family) & (pl.col("season") == season)
                )["target_game_id"].to_list()
            )
            check(f"common_support_{family}_{season}", family_ids == reference_ids)
    comparable = {
        key: value
        for key, value in manifest.items()
        if key not in {"prediction_path", "prediction_sha256"}
    }
    check("deterministic_manifest_rebuild", comparable == rebuilt_manifest)
    rebuilt_frame = pl.DataFrame(rebuilt_rows, infer_schema_length=None).sort(
        ["family", "season", "season_type", "week", "start_utc", "target_game_id"]
    )
    rebuilt_path = rebuild_root / "predictions.parquet"
    rebuilt_path.parent.mkdir(parents=True, exist_ok=True)
    rebuilt_frame.write_parquet(rebuilt_path, compression="zstd")
    check(
        "byte_identical_predictions",
        rebuilt_path.read_bytes() == Path(manifest["prediction_path"]).read_bytes(),
    )
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "PRELIMINARY_ELO_UNCERTAINTY_VALIDATION",
        "classification": candidate.CLASSIFICATION,
        "run_identity": args.run_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": candidate.sha256_file(manifest_path),
        "prediction_sha256": manifest["prediction_sha256"],
        "checks_passed": sum(row["result"] == "PASS" for row in checks),
        "checks_failed": len(failures),
        "checks": checks,
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
