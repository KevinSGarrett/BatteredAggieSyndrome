from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import joblib
import polars as pl


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--run-identity", required=True)
    result.add_argument("--report-path", type=Path, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    sys.path.insert(0, str(repo_root / "src"))
    from aggie_analytics.modeling import preliminary as helpers

    manifest_path = (
        data_root
        / "manifests/preliminary_unprotected/sha256"
        / args.run_identity
        / "run_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    checks: list[dict] = []

    def check(name: str, condition: bool, detail: object = None) -> None:
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            failures.append(name)

    check("run_identity", manifest.get("run_identity") == args.run_identity)
    check("classification", manifest.get("classification") == helpers.CLASSIFICATION)
    check("protected_split_closed", manifest["leakage_validation"].get("protected_split_opened") is False)
    check("target_game_exclusion", manifest["leakage_validation"].get("target_game_identity_exclusion") == "PASS")
    check("future_feature_exclusion", manifest["leakage_validation"].get("future_target_feature_exclusion") == "PASS")
    check("separate_targets", manifest["leakage_validation"].get("outcome_targets_materialized_separately") == "PASS")
    check("nonclaims", not any(manifest["protected_nonclaims"].values()))

    dataset_root = data_root / "training/preliminary_unprotected/sha256" / manifest["dataset_identity"]
    expected_payloads = {row["name"]: row for row in manifest["dataset_payloads"]}
    for name, expected in expected_payloads.items():
        path = dataset_root / name
        check(f"dataset_exists:{name}", path.is_file())
        if path.is_file():
            check(f"dataset_hash:{name}", helpers.sha256_file(path) == expected["sha256"])
            check(f"dataset_rows:{name}", pl.read_parquet(path).height == expected["rows"])
            frame = pl.read_parquet(path)
            if "classification" in frame.columns:
                check(
                    f"dataset_classification:{name}",
                    frame.select(pl.col("classification").unique()).to_series().to_list()
                    == [helpers.CLASSIFICATION],
                )

    feature_frame = pl.read_parquet(dataset_root / "feature_matrix.parquet")
    target_frame = pl.read_parquet(dataset_root / "outcome_targets.parquet")
    split_frame = pl.read_parquet(dataset_root / "split_assignments.parquet")
    training_frame = pl.read_parquet(dataset_root / "training_matrix.parquet")
    check("feature_unique_games", feature_frame["target_game_id"].n_unique() == feature_frame.height)
    check("target_unique_games", target_frame["target_game_id"].n_unique() == target_frame.height)
    check("training_exact_labeled_population", training_frame.height == target_frame.height)
    check("assignments_preserve_unlabeled_game", split_frame.height == feature_frame.height)
    check(
        "chronological_assignment_map",
        set(split_frame.select("season", "assignment").unique().iter_rows())
        == {
            (2023, "DEVELOPMENT_FIT"),
            (2024, "DEVELOPMENT_TUNE"),
            (2025, "DEVELOPMENT_EVALUATION_UNPROTECTED"),
        },
    )
    check(
        "no_feature_target_evidence",
        feature_frame.filter(pl.col("target_outcome_in_feature_evidence") == True).height == 0,  # noqa: E712
    )

    for model in manifest["models"]:
        artifact_path = data_root / model["artifact_path"]
        check(f"model_exists:{model['family']}", artifact_path.is_file())
        if artifact_path.is_file():
            check(
                f"model_hash:{model['family']}",
                helpers.sha256_file(artifact_path) == model["artifact_sha256"],
            )
            loaded = joblib.load(artifact_path)
            check(
                f"model_replay:{model['family']}",
                loaded.get("classification") == helpers.CLASSIFICATION
                and loaded.get("family") == model["family"]
                and loaded.get("dataset_identity") == manifest["dataset_identity"],
            )
            if model["family"] == "elo_rating":
                check(
                    "elo_artifact_pre_evaluation_cutoff",
                    loaded["state"].get("ratings_known_through_season") == 2024
                    and 2025 not in loaded.get("fit_seasons", []),
                )

    forecast_path = (
        data_root
        / "forecast_snapshots/preliminary_unprotected/sha256"
        / manifest["forecast_identity"]
        / "predictions.parquet"
    )
    check("forecast_exists", forecast_path.is_file())
    if forecast_path.is_file():
        check("forecast_hash", helpers.sha256_file(forecast_path) == manifest["forecast_payload"]["sha256"])
        forecast = pl.read_parquet(forecast_path)
        check("forecast_rows", forecast.height == manifest["forecast_payload"]["rows"])
        check(
            "forecast_classification",
            forecast.select(pl.col("classification").unique()).to_series().to_list()
            == [helpers.CLASSIFICATION],
        )
        check(
            "forecast_probabilities_bounded",
            forecast.filter(
                (pl.col("home_win_probability") < 0)
                | (pl.col("home_win_probability") > 1)
                | (pl.col("calibrated_home_win_probability") < 0)
                | (pl.col("calibrated_home_win_probability") > 1)
            ).height
            == 0,
        )
        check(
            "forecast_only_unprotected_assignments",
            set(forecast["assignment"].unique().to_list())
            <= {
                "DEVELOPMENT_FIT",
                "DEVELOPMENT_TUNE",
                "DEVELOPMENT_EVALUATION_UNPROTECTED",
            },
        )

    mutation_controls = {
        "protected_claim_rejected": manifest["protected_nonclaims"].get("protected_performance_claimed") is False,
        "target_in_feature_rejected": feature_frame.filter(pl.col("target_outcome_in_feature_evidence") == True).height == 0,  # noqa: E712
        "future_split_rejected": target_frame.filter(pl.col("season") < 2023).height == 0,
        "missing_label_preserved": split_frame.filter(pl.col("label_available") == False).height == 1,  # noqa: E712
        "tree_after_simple_gate": manifest["diagnostics"].get("simple_pipeline_gate") == "PASS_BEFORE_TREE_BOOSTING",
    }
    check("mutation_controls", all(mutation_controls.values()), mutation_controls)

    report = {
        "schema_version": "1.0.0",
        "artifact_type": "PRELIMINARY_UNPROTECTED_BASELINE_VALIDATION",
        "classification": helpers.CLASSIFICATION,
        "run_identity": args.run_identity,
        "manifest_path": str(manifest_path),
        "manifest_sha256": helpers.sha256_file(manifest_path),
        "checks_passed": sum(item["result"] == "PASS" for item in checks),
        "checks_failed": len(failures),
        "checks": checks,
        "mutation_controls": mutation_controls,
        "result": "PASS" if not failures else "FAIL",
        "failures": failures,
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_bytes(helpers.canonical_json(report) + b"\n")
    print(
        json.dumps(
            {
                "result": report["result"],
                "checks_passed": report["checks_passed"],
                "checks_failed": report["checks_failed"],
                "report_path": str(args.report_path.resolve()),
                "report_sha256": helpers.sha256_file(args.report_path),
            },
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
