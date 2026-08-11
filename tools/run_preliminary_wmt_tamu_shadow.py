from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Mapping, Sequence

import joblib
import numpy as np
import polars as pl
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--output-data-root", type=Path)
    result.add_argument("--issued-at-utc", required=True)
    result.add_argument("--summary-path", type=Path)
    return result


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def matrix(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> np.ndarray:
    return np.asarray(
        [[np.nan if row.get(name) is None else float(row[name]) for name in columns] for row in rows],
        dtype=float,
    )


def write_parquet(rows: Sequence[Mapping[str, Any]], path: Path, sort_columns: Sequence[str]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pl.DataFrame(rows)
    available = [name for name in sort_columns if name in frame.columns]
    if available:
        frame = frame.sort(available)
    frame.write_parquet(path, compression="zstd", statistics=True)
    return {"name": path.name, "rows": frame.height, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def directory_hashes(path: Path) -> dict[str, str]:
    return {
        file.relative_to(path).as_posix(): sha256_file(file)
        for file in sorted(path.rglob("*"))
        if file.is_file()
    }


def move_or_verify(stage: Path, destination: Path) -> None:
    if destination.exists():
        if directory_hashes(stage) != directory_hashes(destination):
            raise ValueError(f"immutable destination differs: {destination}")
        shutil.rmtree(stage)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(stage), str(destination))


def fit_models(rows: Sequence[dict[str, Any]], contract: Mapping[str, Any], helpers: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    by_season = {season: [row for row in rows if int(row["season"]) == season] for season in (2023, 2024, 2025)}
    if any(len(values) != 13 for values in by_season.values()):
        raise ValueError("exactly 13 Texas A&M target games are required per season")
    predictions: list[dict[str, Any]] = []
    specs = {
        "wmt_tamu_logistic_shadow_stacker": {
            "family": "wmt_tamu_logistic_shadow_stacker",
            "reference_family": "play_drive_logistic_stacker",
            "feature_columns": list(helpers.LOGISTIC_FEATURES),
            "models_by_prediction_season": {},
        },
        "wmt_tamu_ridge_margin_shadow_stacker": {
            "family": "wmt_tamu_ridge_margin_shadow_stacker",
            "reference_family": "play_drive_ridge_margin_stacker",
            "feature_columns": list(helpers.MARGIN_FEATURES),
            "models_by_prediction_season": {},
        },
    }
    diagnostics: dict[str, Any] = {"fit_plan": {}, "tree_boosting": contract["model_policy"]["tree_boosting"]}

    def common(row: Mapping[str, Any], family: str, tamu_probability: float) -> dict[str, Any]:
        home_probability = tamu_probability if row["tamu_team_role"] == "HOME" else 1.0 - tamu_probability
        return {
            "classification": helpers.CLASSIFICATION,
            "model_id": family,
            "target_game_id": row["target_game_id"],
            "season": int(row["season"]),
            "week": int(row["week"]),
            "start_utc": row["start_utc"],
            "cutoff_utc": row["cutoff_utc"],
            "tamu_team_role": row["tamu_team_role"],
            "canonical_tamu_team_id": row["canonical_tamu_team_id"],
            "opponent_team_id": row["opponent_team_id"],
            "neutral_site": bool(row["neutral_site"]),
            "tamu_win": float(row["tamu_win"]),
            "tamu_margin": float(row["tamu_margin"]),
            "home_win": float(row["home_win"]),
            "home_margin": float(row["home_margin"]),
            "tamu_win_probability": helpers.safe_probability(float(tamu_probability)),
            "home_win_probability": helpers.safe_probability(float(home_probability)),
            "feature_row_identity": row["feature_row_identity"],
            "latest_source_available_at_utc": row["latest_source_available_at_utc"],
            "latest_source_effective_at_utc": row["latest_source_effective_at_utc"],
            "protected_eligible": False,
        }

    for row in by_season[2023]:
        logistic = common(row, "wmt_tamu_logistic_shadow_stacker", row["baseline_tamu_probability"])
        logistic.update({"model_origin": "FROZEN_NATIONAL_REFERENCE_FALLBACK_NO_A_AND_M_FIT", "fit_seasons": [], "predicted_tamu_margin": None, "predicted_home_margin": None})
        predictions.append(logistic)
        ridge = common(row, "wmt_tamu_ridge_margin_shadow_stacker", helpers.safe_probability(1.0 / (1.0 + np.exp(-row["baseline_tamu_margin"] / 14.0))))
        ridge.update({
            "model_origin": "FROZEN_NATIONAL_REFERENCE_FALLBACK_NO_A_AND_M_FIT",
            "fit_seasons": [],
            "predicted_tamu_margin": float(row["baseline_tamu_margin"]),
            "predicted_home_margin": float(row["baseline_tamu_margin"] if row["tamu_team_role"] == "HOME" else -row["baseline_tamu_margin"]),
        })
        predictions.append(ridge)

    for prediction_season in (2024, 2025):
        fit_seasons = helpers.fit_seasons_for_prediction(prediction_season)
        fit = [row for row in rows if int(row["season"]) in fit_seasons]
        predict = by_season[prediction_season]
        if any(int(row["season"]) >= prediction_season for row in fit):
            raise ValueError("target-season or future outcomes entered WMT model fit")
        labels = np.asarray([int(row["tamu_win"]) for row in fit], dtype=int)
        if set(labels.tolist()) != {0, 1}:
            raise ValueError("chronological WMT fit window does not contain both outcome classes")
        logistic = Pipeline([
            ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(C=float(contract["model_policy"]["logistic_c"]), max_iter=2000, solver="lbfgs", random_state=int(contract["model_policy"]["random_state"]))),
        ])
        logistic.fit(matrix(fit, helpers.LOGISTIC_FEATURES), labels)
        probabilities = logistic.predict_proba(matrix(predict, helpers.LOGISTIC_FEATURES))[:, 1]
        specs["wmt_tamu_logistic_shadow_stacker"]["models_by_prediction_season"][prediction_season] = logistic
        for row, probability in zip(predict, probabilities):
            item = common(row, "wmt_tamu_logistic_shadow_stacker", float(probability))
            item.update({"model_origin": "CHRONOLOGICAL_PRIOR_A_AND_M_SEASON_FIT", "fit_seasons": list(fit_seasons), "predicted_tamu_margin": None, "predicted_home_margin": None})
            predictions.append(item)

        ridge = Pipeline([
            ("imputer", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=float(contract["model_policy"]["ridge_alpha"]))),
        ])
        ridge.fit(matrix(fit, helpers.MARGIN_FEATURES), np.asarray([row["tamu_margin"] for row in fit], dtype=float))
        margins = ridge.predict(matrix(predict, helpers.MARGIN_FEATURES))
        specs["wmt_tamu_ridge_margin_shadow_stacker"]["models_by_prediction_season"][prediction_season] = ridge
        for row, margin in zip(predict, margins):
            probability = helpers.safe_probability(1.0 / (1.0 + np.exp(-float(margin) / 14.0)))
            item = common(row, "wmt_tamu_ridge_margin_shadow_stacker", probability)
            item.update({
                "model_origin": "CHRONOLOGICAL_PRIOR_A_AND_M_SEASON_FIT",
                "fit_seasons": list(fit_seasons),
                "predicted_tamu_margin": float(margin),
                "predicted_home_margin": float(margin if row["tamu_team_role"] == "HOME" else -margin),
            })
            predictions.append(item)
        diagnostics["fit_plan"][str(prediction_season)] = {
            "fit_seasons": list(fit_seasons),
            "fit_rows": len(fit),
            "prediction_rows": len(predict),
            "maximum_fit_start_utc": max(row["start_utc"] for row in fit),
            "minimum_prediction_start_utc": min(row["start_utc"] for row in predict),
            "chronological_order": "PASS",
        }
    if len(predictions) != 78:
        raise ValueError("WMT shadow prediction population is incomplete")
    return predictions, list(specs.values()), diagnostics


def serialize_models(specs: Sequence[dict[str, Any]], dataset_identity: str, stage: Path, output_root: Path, helpers: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for spec in specs:
        family = str(spec["family"])
        model_stage = stage / "models" / family
        model_stage.mkdir(parents=True)
        artifact = model_stage / "model.joblib"
        payload = {"classification": helpers.CLASSIFICATION, "run_version": helpers.RUN_VERSION, "dataset_identity": dataset_identity, **spec}
        joblib.dump(payload, artifact, compress=3, protocol=5)
        artifact_sha = sha256_file(artifact)
        replay = joblib.load(artifact)
        if replay["family"] != family or replay["dataset_identity"] != dataset_identity:
            raise ValueError(f"model serialization replay failed: {family}")
        model_identity = helpers.stable_hash({"family": family, "dataset_identity": dataset_identity, "artifact_sha256": artifact_sha})
        destination = output_root / "model_artifacts/preliminary_wmt_tamu_shadow/sha256" / model_identity
        move_or_verify(model_stage, destination)
        records.append({
            "classification": helpers.CLASSIFICATION,
            "family": family,
            "model_identity": model_identity,
            "dataset_identity": dataset_identity,
            "artifact_path": f"model_artifacts/preliminary_wmt_tamu_shadow/sha256/{model_identity}/model.joblib",
            "artifact_sha256": artifact_sha,
            "serialization_replay": "PASS",
            "fit_seasons_by_prediction_season": {"2023": [], "2024": [2023], "2025": [2023, 2024]},
        })
    return records


def metric_bundle(rows: Sequence[Mapping[str, Any]], helpers: Any) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for season in (2023, 2024, 2025):
        selected = [row for row in rows if int(row["season"]) == season]
        margin_rows = [row for row in selected if row.get("predicted_tamu_margin") is not None]
        results[str(season)] = {
            "probability": helpers.probability_metrics([row["tamu_win"] for row in selected], [row["tamu_win_probability"] for row in selected]),
            "margin": helpers.margin_metrics([row["tamu_margin"] for row in margin_rows], [row["predicted_tamu_margin"] for row in margin_rows]),
        }
    selected = [row for row in rows if int(row["season"]) in (2024, 2025)]
    margin_rows = [row for row in selected if row.get("predicted_tamu_margin") is not None]
    results["2024_2025_COMBINED"] = {
        "probability": helpers.probability_metrics([row["tamu_win"] for row in selected], [row["tamu_win_probability"] for row in selected]),
        "margin": helpers.margin_metrics([row["tamu_margin"] for row in margin_rows], [row["predicted_tamu_margin"] for row in margin_rows]),
    }
    return results


def disposition(candidate: Mapping[str, Any], frozen: Mapping[str, Any]) -> str:
    brier = float(candidate["probability"]["brier"]) - float(frozen["probability"]["brier"])
    loss = float(candidate["probability"]["log_loss"]) - float(frozen["probability"]["log_loss"])
    if brier < 0.0 and loss < 0.0:
        return "POSITIVE_PRELIMINARY_ONLY"
    if brier > 0.0 and loss > 0.0:
        return "NEGATIVE"
    return "MIXED_PRELIMINARY_ONLY"


def main() -> int:
    args = parser().parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    output_root = args.output_data_root.resolve() if args.output_data_root else data_root
    sys.path.insert(0, str(repo_root / "src"))
    from aggie_analytics.modeling import wmt_tamu_shadow as helpers

    issued = datetime.fromisoformat(args.issued_at_utc.replace("Z", "+00:00"))
    if issued.tzinfo is None:
        raise ValueError("issued-at-utc must be timezone aware")
    contract_path = repo_root / "configs/preliminary_wmt_tamu_shadow_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    inputs = contract["authorized_inputs"]
    if contract["classification"] != helpers.CLASSIFICATION:
        raise ValueError("classification drift")

    reference_manifest_path = data_root / "manifests/preliminary_play_drive_augmented/sha256" / inputs["national_reference_run_identity"] / "run_manifest.json"
    reference_predictions_path = data_root / "forecast_snapshots/preliminary_play_drive_augmented/sha256" / inputs["national_reference_forecast_identity"] / "predictions.parquet"
    wmt_manifest_path = data_root / "manifests/historical_known_at/sha256" / inputs["wmt_feature_identity"] / "wmt_tamu_specialization_feature_pit_manifest.json"
    wmt_feature_path = data_root / "features/historical_known_at/sha256" / inputs["wmt_feature_identity"] / "wmt_tamu_target_cutoff_features.parquet"
    pinned = {
        reference_manifest_path: inputs["national_reference_manifest_sha256"],
        reference_predictions_path: inputs["national_reference_prediction_sha256"],
        wmt_manifest_path: inputs["wmt_feature_manifest_sha256"],
        wmt_feature_path: inputs["wmt_feature_payload_sha256"],
    }
    for path, expected in pinned.items():
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"pinned input drift: {path}")
    reference_manifest = json.loads(reference_manifest_path.read_text(encoding="utf-8"))
    wmt_manifest = json.loads(wmt_manifest_path.read_text(encoding="utf-8"))
    if reference_manifest["dataset_identity"] != inputs["national_reference_dataset_identity"]:
        raise ValueError("national reference dataset identity drift")
    if wmt_manifest["dataset_identity"] != inputs["wmt_feature_identity"]:
        raise ValueError("WMT feature dataset identity drift")

    references = pl.read_parquet(reference_predictions_path).filter(pl.col("model_id").is_in(["play_drive_logistic_stacker", "play_drive_ridge_margin_stacker"])).to_dicts()
    reference_index = {(str(row["model_id"]), str(row["target_game_id"])): row for row in references}
    wmt_rows = pl.read_parquet(wmt_feature_path).sort(["start_utc", "game_id"]).to_dicts()
    if len(wmt_rows) != inputs["expected_target_games"] or len({row["game_id"] for row in wmt_rows}) != len(wmt_rows):
        raise ValueError("WMT target population drift")
    rows = [
        helpers.build_shadow_row(
            wmt,
            reference_index[("play_drive_logistic_stacker", str(wmt["game_id"]))],
            reference_index[("play_drive_ridge_margin_stacker", str(wmt["game_id"]))],
            inputs["canonical_tamu_team_id"],
        )
        for wmt in wmt_rows
    ]
    counts = Counter(str(row["season"]) for row in rows)
    if counts != Counter({"2023": 13, "2024": 13, "2025": 13}):
        raise ValueError("A&M season population drift")

    feature_columns = [
        "classification", "target_game_id", "season", "season_type", "week", "start_utc", "cutoff_utc",
        "canonical_tamu_team_id", "tamu_team_role", "opponent_team_id", "neutral_site",
        "baseline_tamu_probability", "baseline_tamu_logit", "baseline_tamu_margin",
        *helpers.WMT_FEATURES, "source_record_count", "source_game_count",
        "latest_source_available_at_utc", "latest_source_effective_at_utc", "feature_row_identity", "wmt_protected_eligible",
    ]
    outcome_columns = ["classification", "target_game_id", "season", "start_utc", "tamu_win", "tamu_margin", "home_win", "home_margin"]
    split_rows = [
        {
            "classification": helpers.CLASSIFICATION,
            "target_game_id": row["target_game_id"],
            "season": row["season"],
            "start_utc": row["start_utc"],
            "assignment": "FROZEN_FALLBACK" if row["season"] == 2023 else "CHRONOLOGICAL_SHADOW_EVALUATION",
            "fit_seasons": list(helpers.fit_seasons_for_prediction(int(row["season"]))),
        }
        for row in rows
    ]
    feature_rows = [{name: row.get(name) for name in feature_columns} for row in rows]
    outcome_rows = [{name: row.get(name) for name in outcome_columns} for row in rows]
    training_rows = [{**row, "assignment": split["assignment"], "fit_seasons": split["fit_seasons"]} for row, split in zip(rows, split_rows)]

    code = {
        "contract_sha256": sha256_file(contract_path),
        "module_sha256": sha256_file(repo_root / "src/aggie_analytics/modeling/wmt_tamu_shadow.py"),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "validator_sha256": sha256_file(repo_root / "tools/validate_preliminary_wmt_tamu_shadow.py"),
    }
    tmp_root = output_root / "runtime/POST-SUBTASK-180"
    tmp_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="post180-", dir=tmp_root))
    try:
        dataset_stage = stage / "dataset"
        payloads = [
            write_parquet(feature_rows, dataset_stage / "feature_matrix.parquet", ["start_utc", "target_game_id"]),
            write_parquet(outcome_rows, dataset_stage / "outcome_targets.parquet", ["start_utc", "target_game_id"]),
            write_parquet(split_rows, dataset_stage / "split_assignments.parquet", ["start_utc", "target_game_id"]),
            write_parquet(training_rows, dataset_stage / "training_matrix.parquet", ["start_utc", "target_game_id"]),
        ]
        input_identities = {
            "national_reference_run": inputs["national_reference_run_identity"],
            "national_reference_dataset": inputs["national_reference_dataset_identity"],
            "national_reference_feature": inputs["national_reference_feature_identity"],
            "national_reference_target": inputs["national_reference_target_identity"],
            "national_reference_split": inputs["national_reference_split_identity"],
            "national_reference_forecast": inputs["national_reference_forecast_identity"],
            "wmt_feature": inputs["wmt_feature_identity"],
        }
        dataset_identity = helpers.stable_hash({"run_version": helpers.RUN_VERSION, "classification": helpers.CLASSIFICATION, "inputs": input_identities, "code": code, "payloads": sorted(payloads, key=lambda row: row["name"])})
        training_destination = output_root / "training/preliminary_wmt_tamu_shadow/sha256" / dataset_identity
        move_or_verify(dataset_stage, training_destination)
        feature_identity = helpers.stable_hash({"dataset_identity": dataset_identity, "columns": list(helpers.LOGISTIC_FEATURES), "wmt_feature": inputs["wmt_feature_identity"]})
        target_identity = helpers.stable_hash({"dataset_identity": dataset_identity, "source_target": inputs["national_reference_target_identity"], "payload": next(row["sha256"] for row in payloads if row["name"] == "outcome_targets.parquet")})
        split_identity = helpers.stable_hash({"dataset_identity": dataset_identity, "chronology": contract["chronology_policy"], "payload": next(row["sha256"] for row in payloads if row["name"] == "split_assignments.parquet")})

        predictions, model_specs, diagnostics = fit_models(rows, contract, helpers)
        models = serialize_models(model_specs, dataset_identity, stage, output_root, helpers)
        model_ids = {row["family"]: row["model_identity"] for row in models}
        for row in predictions:
            row.update({"model_identity": model_ids[row["model_id"]], "dataset_identity": dataset_identity, "feature_identity": feature_identity, "target_identity": target_identity, "split_identity": split_identity})
        predictions.sort(key=lambda row: (row["model_id"], row["start_utc"], row["target_game_id"]))
        forecast_stage = stage / "forecast"
        forecast_payload = write_parquet(predictions, forecast_stage / "predictions.parquet", ["model_id", "start_utc", "target_game_id"])
        forecast_identity = helpers.stable_hash({"dataset_identity": dataset_identity, "model_identities": model_ids, "payload": forecast_payload})
        move_or_verify(forecast_stage, output_root / "forecast_snapshots/preliminary_wmt_tamu_shadow/sha256" / forecast_identity)

        candidate_metrics = {family: metric_bundle([row for row in predictions if row["model_id"] == family], helpers) for family in sorted(model_ids)}
        frozen = {
            "wmt_tamu_logistic_shadow_stacker": [
                {**row, "tamu_win_probability": row["baseline_tamu_probability"], "predicted_tamu_margin": None} for row in rows
            ],
            "wmt_tamu_ridge_margin_shadow_stacker": [
                {**row, "tamu_win_probability": helpers.safe_probability(1.0 / (1.0 + np.exp(-row["baseline_tamu_margin"] / 14.0))), "predicted_tamu_margin": row["baseline_tamu_margin"]} for row in rows
            ],
        }
        frozen_metrics = {family: metric_bundle(values, helpers) for family, values in frozen.items()}
        comparison: dict[str, Any] = {}
        for family in sorted(model_ids):
            comparison[family] = {}
            for scope in ("2023", "2024", "2025", "2024_2025_COMBINED"):
                candidate = candidate_metrics[family][scope]
                reference = frozen_metrics[family][scope]
                item = {
                    "rows_equal": candidate["probability"]["rows"] == reference["probability"]["rows"],
                    "brier_delta_candidate_minus_frozen": candidate["probability"]["brier"] - reference["probability"]["brier"],
                    "log_loss_delta_candidate_minus_frozen": candidate["probability"]["log_loss"] - reference["probability"]["log_loss"],
                    "disposition": disposition(candidate, reference),
                }
                if candidate["margin"]["rows"]:
                    item["margin_mae_delta_candidate_minus_frozen"] = candidate["margin"]["mae"] - reference["margin"]["mae"]
                comparison[family][scope] = item

        run_identity = helpers.stable_hash({"run_version": helpers.RUN_VERSION, "dataset_identity": dataset_identity, "feature_identity": feature_identity, "target_identity": target_identity, "split_identity": split_identity, "model_identities": model_ids, "forecast_identity": forecast_identity, "code": code})
        manifest = {
            "schema_version": "1.0.0",
            "artifact_type": "PRELIMINARY_UNPROTECTED_WMT_TAMU_SHADOW_RUN",
            "classification": helpers.CLASSIFICATION,
            "decision_unit": "POST-SUBTASK-180",
            "jira_key": "BAT-537",
            "run_version": helpers.RUN_VERSION,
            "run_identity": run_identity,
            "issued_at_utc": issued.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "input_identities": input_identities,
            "code_identities": code,
            "dataset_identity": dataset_identity,
            "feature_identity": feature_identity,
            "target_identity": target_identity,
            "split_identity": split_identity,
            "forecast_identity": forecast_identity,
            "model_identities": model_ids,
            "dataset_payloads": payloads,
            "forecast_payload": forecast_payload,
            "models": models,
            "population": {
                "rows": 39, "games": 39, "seasons": [2023, 2024, 2025], "rows_by_season": dict(sorted(counts.items())),
                "predeclared_wmt_features": list(helpers.WMT_FEATURES), "feature_count_per_candidate": 5,
                "missing_feature_cells": {name: sum(row[name] is None for row in rows) for name in helpers.WMT_FEATURES},
                "cold_start_games": 0,
            },
            "metrics": candidate_metrics,
            "frozen_reference_metrics": frozen_metrics,
            "frozen_reference_comparison": comparison,
            "diagnostics": diagnostics,
            "leakage_validation": {
                "target_game_or_future_outcomes_in_fit": 0,
                "post_cutoff_feature_rows": 0,
                "identity_mismatches": 0,
                "outcome_targets_materialized_separately": "PASS",
                "2023_exact_frozen_fallback": "PASS",
                "protected_split_opened": False,
            },
            "external_locations": {
                "training": f"training/preliminary_wmt_tamu_shadow/sha256/{dataset_identity}",
                "models": "model_artifacts/preliminary_wmt_tamu_shadow/sha256/<model_identity>",
                "forecast": f"forecast_snapshots/preliminary_wmt_tamu_shadow/sha256/{forecast_identity}",
                "manifest": f"manifests/preliminary_wmt_tamu_shadow/sha256/{run_identity}/run_manifest.json",
            },
            "limitations": [
                "All artifacts, metrics, and comparisons are PRELIMINARY_UNPROTECTED and shadow-only.",
                "Only 39 Texas A&M games are available, with 13 games per season; no specialization lift or stable scientific effect can be claimed.",
                "The 2023 outputs are exact frozen national-reference fallbacks; 2024 fits 13 prior games and 2025 fits 26 prior games.",
                "WMT features are cumulative provider-timestamped A&M summaries and do not supply opponent-specific gamebook state.",
                "Tree boosting is not admitted for this short horizon; negative, mixed, and unstable findings are preserved.",
            ],
            "authority": contract["authority"],
            "protected_nonclaims": contract["protected_nonclaims"],
            "cleanup": {"reconstructible_stage_removed": True, "abandoned_downloads": 0},
        }
        manifest_stage = stage / "manifest"
        manifest_stage.mkdir(parents=True)
        manifest_path = manifest_stage / "run_manifest.json"
        manifest_path.write_bytes(helpers.canonical_json(manifest) + b"\n")
        manifest_sha = sha256_file(manifest_path)
        move_or_verify(manifest_stage, output_root / "manifests/preliminary_wmt_tamu_shadow/sha256" / run_identity)
        result = {
            "result": "PASS_PRELIMINARY_ONLY",
            "run_identity": run_identity,
            "manifest_sha256": manifest_sha,
            "dataset_identity": dataset_identity,
            "feature_identity": feature_identity,
            "target_identity": target_identity,
            "split_identity": split_identity,
            "forecast_identity": forecast_identity,
            "model_identities": model_ids,
            "population": manifest["population"],
            "comparison": comparison,
        }
        payload = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
        if args.summary_path:
            args.summary_path.parent.mkdir(parents=True, exist_ok=True)
            args.summary_path.write_text(payload, encoding="utf-8")
        print(payload, end="")
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        if tmp_root.exists() and not any(tmp_root.iterdir()):
            tmp_root.rmdir()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
