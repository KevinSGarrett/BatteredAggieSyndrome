from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import polars as pl


CLASSIFICATION = "PRELIMINARY_UNPROTECTED_EVENT_CHRONOLOGY_ONLY"
EXPECTED_FAMILIES = {
    "naive_historical_average",
    "home_field_empirical",
    "elo_rating_week_batched",
    "regularized_logistic",
    "regularized_linear_margin",
    "poisson_skellam_score_distribution",
    "hist_gradient_boosting",
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
    from aggie_analytics.modeling.preliminary import sha256_file

    manifest_path = (
        data_root
        / "manifests/preliminary_event_chronology/sha256"
        / args.run_identity
        / "run_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: Any = None) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("run_identity", manifest["run_identity"] == args.run_identity)
    check("classification", manifest["classification"] == CLASSIFICATION)
    check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-172")
    check("season_population", manifest["population"]["seasons"] == list(range(2010, 2026)))
    check("target_population", manifest["population"]["targets"] == 13356)
    check("historical_labels", manifest["population"]["historical_labels"] == 10593)
    check("contemporary_labels", manifest["population"]["contemporary_labels"] == 2763)
    start_drift = manifest["population"]["historical_source_start_drift"]
    check("historical_start_drift_rows", start_drift["drift_rows"] == 24)
    check("historical_start_exact_rows", start_drift["exact_match_rows"] == 10569)
    check("historical_start_drift_bound", start_drift["maximum_absolute_minutes"] == 270)
    check("historical_start_drift_fail_closed_bound", start_drift["accepted_bound_minutes"] == 270)
    check("feature_count", manifest["population"]["feature_count"] == 14)
    check("model_families", set(manifest["model_identities"]) == EXPECTED_FAMILIES)
    check("protected_split_closed", manifest["leakage_validation"]["protected_split_opened"] is False)
    check("no_fabricated_publication_time", manifest["leakage_validation"]["publication_timestamps_fabricated"] == 0)
    check("not_historical_known_at", manifest["leakage_validation"]["historical_known_at_eligible_rows"] == 0)
    check("protected_nonclaims", not any(manifest["protected_nonclaims"].values()))

    training_root = data_root / manifest["external_locations"]["training"]
    payload_by_name = {row["name"]: row for row in manifest["dataset_payloads"]}
    frames = {}
    for name, expected_rows in (
        ("feature_matrix.parquet", 13356),
        ("outcome_targets.parquet", 13356),
        ("split_assignments.parquet", 13356),
        ("training_matrix.parquet", 13356),
    ):
        path = training_root / name
        frame = pl.read_parquet(path)
        frames[name] = frame
        check(f"{name}_rows", frame.height == expected_rows, frame.height)
        check(f"{name}_hash", sha256_file(path) == payload_by_name[name]["sha256"])
        check(f"{name}_unique_games", frame["target_game_id"].n_unique() == frame.height)

    features = frames["feature_matrix.parquet"]
    targets = frames["outcome_targets.parquet"]
    assignments = frames["split_assignments.parquet"]
    check("feature_classification", features["classification"].unique().to_list() == [CLASSIFICATION])
    check("target_classification", targets["classification"].unique().to_list() == [CLASSIFICATION])
    check(
        "historical_source_start_authority",
        targets.filter(pl.col("season") <= 2022)[
            "chronological_cutoff_authority"
        ].unique().to_list()
        == ["PINNED_ACCEPTED_HISTORICAL_SOURCE_START_ALIGNED_TO_RANKINGS_FEATURE"],
    )
    check(
        "historical_start_drift_preserved",
        targets.filter(
            (pl.col("season") <= 2022)
            & (pl.col("source_minus_canonical_start_minutes") != 0)
        ).height
        == 24,
    )
    check(
        "historical_chronology_uses_pinned_source_start",
        targets.filter(pl.col("season") <= 2022).select(
            (pl.col("start_utc") == pl.col("source_game_start_utc")).all()
        ).item(),
    )
    check("target_outcome_exclusion", not features["target_outcome_in_feature_evidence"].any())
    check("rankings_target_exclusion", not features["rankings_target_outcome_in_feature_evidence"].any())
    check("feature_nonpit", not features["historical_known_at_eligible"].any())
    check("assignment_nonpit", not assignments["historical_known_at_eligible"].any())
    check(
        "split_counts",
        assignments.group_by("assignment").len().sort("assignment").to_dicts()
        == [
            {"assignment": "DEVELOPMENT_EVALUATION_UNPROTECTED", "len": 934},
            {"assignment": "DEVELOPMENT_FIT", "len": 10593},
            {"assignment": "DEVELOPMENT_TUNE", "len": 1829},
        ],
    )

    forecast_root = data_root / manifest["external_locations"]["forecast"]
    forecast_path = forecast_root / "predictions.parquet"
    predictions = pl.read_parquet(forecast_path)
    check("forecast_hash", sha256_file(forecast_path) == manifest["forecast_payload"]["sha256"])
    check("forecast_models", set(predictions["model_id"].unique()) == EXPECTED_FAMILIES)
    check("forecast_seasons", sorted(predictions["season"].unique()) == [2023, 2024, 2025])
    check("probabilities_finite", predictions["home_win_probability"].is_finite().all())
    check("probabilities_bounded", ((predictions["home_win_probability"] >= 0) & (predictions["home_win_probability"] <= 1)).all())
    check("prediction_classification", predictions["classification"].unique().to_list() == [CLASSIFICATION])

    for family, model_id in manifest["model_identities"].items():
        model_path = (
            data_root
            / "model_artifacts/preliminary_event_chronology/sha256"
            / model_id
            / "model.joblib"
        )
        record = next(row for row in manifest["models"] if row["family"] == family)
        check(f"model_{family}_hash", sha256_file(model_path) == record["artifact_sha256"])
        check(f"model_{family}_roundtrip", record["serialization_replay"] == "PASS")

    failures = [row for row in checks if not row["passed"]]
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "PRELIMINARY_EVENT_CHRONOLOGY_VALIDATION",
        "classification": CLASSIFICATION,
        "run_identity": args.run_identity,
        "manifest_sha256": sha256_file(manifest_path),
        "checks_passed": len(checks) - len(failures),
        "checks_failed": len(failures),
        "checks": checks,
        "result": "PASS" if not failures else "FAIL",
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: report[key] for key in ("result", "checks_passed", "checks_failed")}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
