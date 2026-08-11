from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import joblib
import numpy as np
import polars as pl


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def matrix(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> np.ndarray:
    return np.asarray([[np.nan if row.get(name) is None else float(row[name]) for name in columns] for row in rows], dtype=float)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--run-identity", required=True)
    parser.add_argument("--report-path", type=Path)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    sys.path.insert(0, str(repo_root / "src"))
    from aggie_analytics.modeling import wmt_tamu_shadow as helpers

    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            raise ValueError(f"validation failed: {name}: {detail}")

    manifest_path = data_root / "manifests/preliminary_wmt_tamu_shadow/sha256" / args.run_identity / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    check("run_identity", manifest["run_identity"] == args.run_identity)
    check("classification", manifest["classification"] == helpers.CLASSIFICATION)
    check("decision_unit", manifest["decision_unit"] == "POST-SUBTASK-180")
    check("population", manifest["population"]["rows"] == 39 and manifest["population"]["rows_by_season"] == {"2023": 13, "2024": 13, "2025": 13})
    check("protected_nonclaims", not any(manifest["protected_nonclaims"].values()))
    check("protected_authority_closed", not any(manifest["authority"][key] for key in ("protected_training", "protected_evaluation", "champion_or_production_promotion", "forecast_publication", "tamu_specialization_lift_claim", "bas_or_aggie_excess_claim")))

    training_root = data_root / manifest["external_locations"]["training"]
    payload_by_name = {row["name"]: row for row in manifest["dataset_payloads"]}
    for name, expected in payload_by_name.items():
        path = training_root / name
        check(f"training_payload_exists:{name}", path.is_file())
        check(f"training_payload_hash:{name}", sha256_file(path) == expected["sha256"])
    training = pl.read_parquet(training_root / "training_matrix.parquet").sort(["start_utc", "target_game_id"])
    check("training_rows", training.height == 39 and training["target_game_id"].n_unique() == 39)
    check("training_seasons", training.group_by("season").len().sort("season").to_dicts() == [{"season": 2023, "len": 13}, {"season": 2024, "len": 13}, {"season": 2025, "len": 13}])
    check("feature_missingness", all(training[name].null_count() == 0 for name in helpers.WMT_FEATURES))
    check("known_at_order", training.filter(pl.col("latest_source_available_at_utc") >= pl.col("cutoff_utc")).height == 0)
    check("effective_order", training.filter(pl.col("latest_source_effective_at_utc") >= pl.col("cutoff_utc")).height == 0)
    check("feature_protected_false", training.filter(pl.col("wmt_protected_eligible")).height == 0)

    forecast_path = data_root / manifest["external_locations"]["forecast"] / "predictions.parquet"
    check("forecast_hash", sha256_file(forecast_path) == manifest["forecast_payload"]["sha256"])
    forecast = pl.read_parquet(forecast_path)
    check("forecast_rows", forecast.height == 78)
    check("forecast_population", forecast.group_by(["model_id", "season"]).len().sort(["model_id", "season"])["len"].to_list() == [13, 13, 13, 13, 13, 13])
    check("forecast_protected_false", forecast.filter(pl.col("protected_eligible")).height == 0)
    frozen = forecast.filter(pl.col("season") == 2023)
    joined = frozen.join(training.select(["target_game_id", "baseline_tamu_probability", "baseline_tamu_margin"]), on="target_game_id")
    logistic_frozen = joined.filter(pl.col("model_id") == "wmt_tamu_logistic_shadow_stacker")
    ridge_frozen = joined.filter(pl.col("model_id") == "wmt_tamu_ridge_margin_shadow_stacker")
    check("2023_logistic_exact_fallback", np.allclose(logistic_frozen["tamu_win_probability"].to_numpy(), logistic_frozen["baseline_tamu_probability"].to_numpy(), atol=0.0, rtol=0.0))
    check("2023_ridge_exact_fallback", np.allclose(ridge_frozen["predicted_tamu_margin"].to_numpy(), ridge_frozen["baseline_tamu_margin"].to_numpy(), atol=0.0, rtol=0.0))

    training_rows = training.to_dicts()
    numerical_replays = 0
    for model in manifest["models"]:
        artifact_path = data_root / model["artifact_path"]
        check(f"model_hash:{model['family']}", sha256_file(artifact_path) == model["artifact_sha256"])
        payload = joblib.load(artifact_path)
        check(f"model_identity:{model['family']}", payload["family"] == model["family"] and payload["dataset_identity"] == manifest["dataset_identity"])
        columns = payload["feature_columns"]
        for season in (2024, 2025):
            rows = [row for row in training_rows if int(row["season"]) == season]
            predictions = forecast.filter((pl.col("model_id") == model["family"]) & (pl.col("season") == season)).sort(["start_utc", "target_game_id"])
            estimator = payload["models_by_prediction_season"][season]
            if model["family"] == "wmt_tamu_logistic_shadow_stacker":
                replay = estimator.predict_proba(matrix(rows, columns))[:, 1]
                stored = predictions["tamu_win_probability"].to_numpy()
            else:
                replay = estimator.predict(matrix(rows, columns))
                stored = predictions["predicted_tamu_margin"].to_numpy()
            check(f"numerical_replay:{model['family']}:{season}", np.allclose(replay, stored, atol=1e-12, rtol=1e-12))
            numerical_replays += 1
    check("chronological_fit_2024", manifest["diagnostics"]["fit_plan"]["2024"]["fit_seasons"] == [2023] and manifest["diagnostics"]["fit_plan"]["2024"]["fit_rows"] == 13)
    check("chronological_fit_2025", manifest["diagnostics"]["fit_plan"]["2025"]["fit_seasons"] == [2023, 2024] and manifest["diagnostics"]["fit_plan"]["2025"]["fit_rows"] == 26)
    check("leakage_zero", manifest["leakage_validation"]["target_game_or_future_outcomes_in_fit"] == 0 and manifest["leakage_validation"]["post_cutoff_feature_rows"] == 0)

    report = {
        "schema_version": "1.0.0",
        "artifact_type": "PRELIMINARY_WMT_TAMU_SHADOW_VALIDATION",
        "decision_unit": "POST-SUBTASK-180",
        "jira_key": "BAT-537",
        "classification": helpers.CLASSIFICATION,
        "result": "PASS_PRELIMINARY_ONLY",
        "run_identity": args.run_identity,
        "manifest_sha256": sha256_file(manifest_path),
        "checks_passed": len(checks),
        "checks_failed": 0,
        "numerical_model_replays": numerical_replays,
        "checks": checks,
        "protected_promotion_opened": False,
    }
    payload = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    report_path = args.report_path or data_root / "validation/POST-SUBTASK-180/validation-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
