from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import polars as pl


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--run-identity", required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    args = parser.parse_args()
    root = args.data_root.resolve()
    manifest_path = root / "manifests/preliminary_unprotected/sha256" / args.run_identity / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict] = []

    def check(name: str, condition: bool, detail=None) -> None:
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})

    check("run_identity", manifest["run_identity"] == args.run_identity)
    check("classification", manifest["classification"] == "PRELIMINARY_UNPROTECTED")
    check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-171")
    check("protected_nonclaims", not any(manifest["protected_nonclaims"].values()))
    check("protected_split_closed", manifest["leakage_validation"]["protected_split_opened"] is False)
    check("same_target_rows", manifest["leakage_validation"]["same_target_rows_as_baseline"] == "PASS")
    check("no_future_rankings", manifest["leakage_validation"]["rankings_future_rows"] == 0)
    check("no_rankings_outcomes", manifest["leakage_validation"]["rankings_target_outcome_fields"] == 0)

    training_root = root / manifest["external_locations"]["training"]
    frames = {}
    for info in manifest["dataset_payloads"]:
        path = training_root / info["name"]
        check(f"payload_exists:{info['name']}", path.is_file())
        if path.is_file():
            frames[info["name"]] = pl.read_parquet(path)
            check(f"payload_hash:{info['name']}", sha256_file(path) == info["sha256"])
            check(f"payload_rows:{info['name']}", frames[info["name"]].height == info["rows"])
    features = frames["feature_matrix.parquet"]
    training = frames["training_matrix.parquet"]
    targets = frames["outcome_targets.parquet"]
    check("feature_games_unique", features["target_game_id"].n_unique() == features.height)
    check("training_games_unique", training["target_game_id"].n_unique() == training.height)
    check("training_target_population_equal", set(training["target_game_id"]) == set(targets["target_game_id"]))
    check("rank_columns_present", {"ap_rank_diff","home_ap_rank_observed","away_ap_rank_observed","ap_poll_available","home_ap_listed","away_ap_listed"}.issubset(features.columns))
    check("rank_diff_requires_both", features.filter(pl.col("ap_rank_diff").is_not_null() & ((pl.col("home_ap_rank_observed") != 1.0) | (pl.col("away_ap_rank_observed") != 1.0))).height == 0)
    check("missing_rank_diff_explicit", features.filter(pl.col("ap_rank_diff").is_null() & (pl.col("home_ap_rank_observed") == 1.0) & (pl.col("away_ap_rank_observed") == 1.0)).height == 0)
    check("feature_outcome_exclusion", features.filter(pl.col("target_outcome_in_feature_evidence") | pl.col("rankings_target_outcome_in_feature_evidence")).height == 0)
    check("seasons", set(training["season"].unique()) == {2023, 2024, 2025})
    check("comparison_rows_equal", all(row["rows_equal"] for row in manifest["baseline_comparison"].values()))
    check("all_model_families", set(manifest["model_identities"]) == {"naive_historical_average","home_field_empirical","elo_rating","regularized_logistic","regularized_linear_margin","poisson_skellam_score_distribution","hist_gradient_boosting"})
    for model in manifest["models"]:
        path = root / model["artifact_path"]
        check(f"model_hash:{model['family']}", path.is_file() and sha256_file(path) == model["artifact_sha256"])
        if path.is_file():
            payload = joblib.load(path)
            check(f"model_replay:{model['family']}", payload["family"] == model["family"] and payload["dataset_identity"] == manifest["dataset_identity"])
    forecast = root / manifest["external_locations"]["forecast"] / "predictions.parquet"
    check("forecast_hash", forecast.is_file() and sha256_file(forecast) == manifest["forecast_payload"]["sha256"])
    if forecast.is_file():
        predictions = pl.read_parquet(forecast)
        check("forecast_rows", predictions.height == manifest["forecast_payload"]["rows"])
        check("forecast_probabilities", predictions.filter((pl.col("home_win_probability") <= 0) | (pl.col("home_win_probability") >= 1)).height == 0)
    failures = [row for row in checks if row["result"] == "FAIL"]
    report = {"schema_version":"1.0.0","artifact_type":"PRELIMINARY_RANKINGS_AUGMENTED_VALIDATION","classification":"PRELIMINARY_UNPROTECTED","run_identity":args.run_identity,"manifest_sha256":sha256_file(manifest_path),"result":"PASS" if not failures else "FAIL","checks_passed":len(checks)-len(failures),"checks_failed":len(failures),"checks":checks,"failures":failures}
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"result":report["result"],"checks_passed":report["checks_passed"],"checks_failed":report["checks_failed"],"report_sha256":sha256_file(args.report_path)}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
