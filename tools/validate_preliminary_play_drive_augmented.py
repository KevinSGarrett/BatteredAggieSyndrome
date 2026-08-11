from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
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
    return np.asarray(
        [
            [np.nan if row.get(name) is None else float(row[name]) for name in columns]
            for row in rows
        ],
        dtype=float,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--run-identity", required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    parser.add_argument("--contract-path", type=Path)
    parser.add_argument("--rebuild-root", type=Path)
    args = parser.parse_args()
    repo_root, root = args.repo_root.resolve(), args.data_root.resolve()
    sys.path.insert(0, str(repo_root / "src"))
    from aggie_analytics.modeling import play_drive_augmented as helpers

    contract_path = (
        args.contract_path.resolve()
        if args.contract_path
        else repo_root / "configs/preliminary_play_drive_augmented_contract.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    authorized = contract["authorized_inputs"]
    storage_namespace = str(contract.get("storage_namespace", "preliminary_play_drive_augmented"))
    if not re.fullmatch(r"[a-z0-9][a-z0-9_]*", storage_namespace):
        raise ValueError("storage namespace must be a safe relative path component")
    manifest_path = root / f"manifests/{storage_namespace}/sha256" / args.run_identity / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})

    check("run_identity", manifest["run_identity"] == args.run_identity)
    check("classification", manifest["classification"] == helpers.CLASSIFICATION)
    check("decision_unit", manifest["decision_unit"] == contract["decision_unit"])
    check("protected_nonclaims", not any(manifest["protected_nonclaims"].values()))
    check("protected_split_closed", manifest["leakage_validation"]["protected_split_opened"] is False)
    check("target_outcome_excluded", manifest["leakage_validation"]["target_game_outcome_in_play_drive_evidence"] == 0)
    check("future_outcomes_excluded", manifest["leakage_validation"]["target_or_future_season_outcomes_in_fit"] == 0)
    check("2023_fallback", manifest["leakage_validation"]["2023_no_fit_fallback_exact"] == "PASS")
    check("exact_input_baseline", manifest["input_identities"]["baseline_run"] == authorized["baseline_run_identity"])
    check("exact_input_play_drive", manifest["input_identities"]["play_drive_feature"] == authorized["play_drive_feature_identity"])

    training_root = root / manifest["external_locations"]["training"]
    frames: dict[str, pl.DataFrame] = {}
    for info in manifest["dataset_payloads"]:
        path = training_root / info["name"]
        check(f"payload_exists:{info['name']}", path.is_file())
        if path.is_file():
            frame = pl.read_parquet(path)
            frames[info["name"]] = frame
            check(f"payload_hash:{info['name']}", sha256_file(path) == info["sha256"])
            check(f"payload_rows:{info['name']}", frame.height == info["rows"])
    required_payloads = {"feature_matrix.parquet", "outcome_targets.parquet", "split_assignments.parquet", "training_matrix.parquet"}
    check("all_dataset_payloads", set(frames) == required_payloads)
    training = frames.get("training_matrix.parquet", pl.DataFrame())
    features = frames.get("feature_matrix.parquet", pl.DataFrame())
    targets = frames.get("outcome_targets.parquet", pl.DataFrame())
    splits = frames.get("split_assignments.parquet", pl.DataFrame())
    if training.height:
        check("training_rows", training.height == 2763)
        check("training_games_unique", training["target_game_id"].n_unique() == training.height)
        check("seasons", set(training["season"].unique()) == {2023, 2024, 2025})
        check("population_alignment", set(training["target_game_id"]) == set(features["target_game_id"]) == set(targets["target_game_id"]) == set(splits["target_game_id"]))
        check("source_before_cutoff", training.filter(pl.col("play_drive_source_known_at_utc") > pl.col("cutoff_utc")).height == 0)
        check("protected_feature_false", training.filter(pl.col("play_drive_protected_eligible") != False).height == 0)  # noqa: E712
        check("feature_lineage_unique", features["feature_row_identity"].n_unique() == features.height)
        check("feature_columns", set(helpers.DIFFERENCE_FIELDS).issubset(training.columns))

    forecast_path = root / manifest["external_locations"]["forecast"] / "predictions.parquet"
    check("forecast_exists", forecast_path.is_file())
    forecast = pl.read_parquet(forecast_path) if forecast_path.is_file() else pl.DataFrame()
    if forecast.height:
        check("forecast_hash", sha256_file(forecast_path) == manifest["forecast_payload"]["sha256"])
        check("forecast_rows", forecast.height == 5526 == manifest["forecast_payload"]["rows"])
        check("forecast_families", set(forecast["model_id"].unique()) == {"play_drive_logistic_stacker", "play_drive_ridge_margin_stacker"})
        check("forecast_probability_bounds", forecast.filter((pl.col("home_win_probability") <= 0) | (pl.col("home_win_probability") >= 1)).height == 0)
        check("forecast_classification", set(forecast["classification"].unique()) == {helpers.CLASSIFICATION})
        check("forecast_dataset_identity", set(forecast["dataset_identity"].unique()) == {manifest["dataset_identity"]})
        fallback = forecast.filter(pl.col("season") == 2023)
        check("fallback_origin", set(fallback["model_origin"].unique()) == {"FROZEN_BASELINE_FALLBACK_NO_PRIOR_POST_PUBLICATION_LABELS"})

    training_rows = training.sort(["start_utc", "target_game_id"]).to_dicts() if training.height else []
    model_families: set[str] = set()
    for model in manifest["models"]:
        family = str(model["family"])
        model_families.add(family)
        artifact_path = root / model["artifact_path"]
        check(f"model_exists:{family}", artifact_path.is_file())
        if not artifact_path.is_file():
            continue
        check(f"model_hash:{family}", sha256_file(artifact_path) == model["artifact_sha256"])
        payload = joblib.load(artifact_path)
        check(f"model_identity:{family}", payload["family"] == family and payload["dataset_identity"] == manifest["dataset_identity"])
        for prediction_season in (2024, 2025):
            estimator = payload["models_by_prediction_season"][prediction_season]
            selected = [row for row in training_rows if int(row["season"]) == prediction_season]
            expected = forecast.filter((pl.col("model_id") == family) & (pl.col("season") == prediction_season)).sort(["start_utc", "target_game_id"])
            if family == "play_drive_logistic_stacker":
                replay = estimator.predict_proba(matrix(selected, payload["feature_columns"]))[:, 1]
                actual = expected["home_win_probability"].to_numpy()
            else:
                replay = estimator.predict(matrix(selected, payload["feature_columns"]))
                actual = expected["predicted_margin"].to_numpy()
            check(f"numerical_replay:{family}:{prediction_season}", bool(np.allclose(replay, actual, rtol=0, atol=1e-12)))
    check("model_families", model_families == {"play_drive_logistic_stacker", "play_drive_ridge_margin_stacker"})
    for family, seasons in manifest["baseline_comparison"].items():
        check(f"comparison_rows:{family}", all(item["rows_equal"] for item in seasons.values()))
    if manifest.get("prior_play_drive_comparison"):
        for family, seasons in manifest["prior_play_drive_comparison"].items():
            check(
                f"prior_comparison_rows:{family}",
                all(item["rows_equal"] for item in seasons.values()),
            )

    deterministic_payloads_compared = 0
    if args.rebuild_root:
        rebuild_root = args.rebuild_root.resolve()
        relative_paths = [
            f"{manifest['external_locations']['training']}/{info['name']}"
            for info in manifest["dataset_payloads"]
        ]
        relative_paths.extend(
            [
                f"{manifest['external_locations']['forecast']}/predictions.parquet",
                manifest["external_locations"]["manifest"],
                *(model["artifact_path"] for model in manifest["models"]),
            ]
        )
        for relative in relative_paths:
            original = root / relative
            rebuilt = rebuild_root / relative
            check(f"rebuild_exists:{relative}", rebuilt.is_file())
            if original.is_file() and rebuilt.is_file():
                deterministic_payloads_compared += 1
                check(
                    f"rebuild_byte_identity:{relative}",
                    sha256_file(original) == sha256_file(rebuilt),
                )

    failures = [item for item in checks if item["result"] == "FAIL"]
    report = {
        "schema_version": "1.0.0",
        "artifact_type": "PRELIMINARY_PLAY_DRIVE_AUGMENTED_VALIDATION",
        "classification": helpers.CLASSIFICATION,
        "decision_unit": contract["decision_unit"],
        "run_identity": args.run_identity,
        "manifest_sha256": sha256_file(manifest_path),
        "result": "PASS" if not failures else "FAIL",
        "checks_passed": len(checks) - len(failures),
        "checks_failed": len(failures),
        "deterministic_payloads_compared": deterministic_payloads_compared,
        "byte_identical_rebuild": bool(args.rebuild_root) and not any(
            item["result"] == "FAIL" and item["check"].startswith("rebuild_")
            for item in checks
        ),
        "checks": checks,
        "failures": failures,
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "checks_passed": report["checks_passed"], "checks_failed": report["checks_failed"], "report_sha256": sha256_file(args.report_path)}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
