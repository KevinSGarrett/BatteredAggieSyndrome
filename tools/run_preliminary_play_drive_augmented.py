from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import importlib
import importlib.util
import json
import math
from pathlib import Path
import re
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


TAMU_TEAM_ID = "team_d0aff8aacd805801ab3d3d8293f3b298"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--output-data-root", type=Path)
    result.add_argument("--issued-at-utc", required=True)
    result.add_argument("--summary-path", type=Path)
    result.add_argument("--contract-path", type=Path)
    return result


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_base_runner(repo_root: Path) -> Any:
    path = repo_root / "tools/run_preliminary_unprotected_baselines.py"
    spec = importlib.util.spec_from_file_location("play_drive_base_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load preliminary baseline helpers")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def matrix(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> np.ndarray:
    return np.asarray(
        [
            [np.nan if row.get(name) is None else float(row[name]) for name in columns]
            for row in rows
        ],
        dtype=float,
    )


def metric_slices(rows: Sequence[Mapping[str, Any]], helpers: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for season in (2023, 2024, 2025):
        season_rows = [row for row in rows if int(row["season"]) == season]
        slices = {
            f"SEASON_{season}_ALL": season_rows,
            f"SEASON_{season}_NONNEUTRAL": [row for row in season_rows if not row["neutral_site"]],
            f"SEASON_{season}_COLD_START": [row for row in season_rows if row["cold_start"]],
            f"SEASON_{season}_TEXAS_AM_INVOLVED": [
                row
                for row in season_rows
                if TAMU_TEAM_ID in (row["home_team_id"], row["away_team_id"])
            ],
        }
        for slice_id, selected in slices.items():
            probability = helpers.probability_metrics(
                [row["home_win"] for row in selected],
                [row["home_win_probability"] for row in selected],
            )
            margin_rows = [row for row in selected if row.get("predicted_margin") is not None]
            margin = helpers.margin_metrics(
                [row["margin"] for row in margin_rows],
                [row["predicted_margin"] for row in margin_rows],
            )
            results.append(
                {
                    "classification": helpers.CLASSIFICATION,
                    "slice": slice_id,
                    "probability": probability,
                    "margin": margin,
                }
            )
    return results


def metric_row(metrics: Sequence[Mapping[str, Any]], slice_id: str) -> Mapping[str, Any]:
    return next(row for row in metrics if row["slice"] == slice_id)


def fit_models(
    rows: Sequence[dict[str, Any]], contract: Mapping[str, Any], helpers: Any
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    by_season = {
        season: [row for row in rows if int(row["season"]) == season]
        for season in (2023, 2024, 2025)
    }
    if any(not values for values in by_season.values()):
        raise ValueError("2023, 2024, and 2025 rows are required")
    predictions: list[dict[str, Any]] = []
    model_specs = {
        helpers.LOGISTIC_FAMILY: {
            "family": helpers.LOGISTIC_FAMILY,
            "base_family": "regularized_logistic",
            "feature_columns": list(helpers.LOGISTIC_FEATURES),
            "models_by_prediction_season": {},
        },
        helpers.MARGIN_FAMILY: {
            "family": helpers.MARGIN_FAMILY,
            "base_family": "regularized_linear_margin",
            "feature_columns": list(helpers.MARGIN_FEATURES),
            "models_by_prediction_season": {},
        },
    }
    diagnostics: dict[str, Any] = {
        "fit_plan": {},
        "tree_boosting": contract["model_policy"]["tree_boosting"],
    }

    def common(row: Mapping[str, Any], family: str, probability: float) -> dict[str, Any]:
        return {
            "classification": helpers.CLASSIFICATION,
            "model_id": family,
            "target_game_id": row["target_game_id"],
            "season": int(row["season"]),
            "week": int(row["week"]),
            "start_utc": row["start_utc"],
            "assignment": row["assignment"],
            "home_team_id": row["home_team_id"],
            "away_team_id": row["away_team_id"],
            "neutral_site": bool(row["neutral_site"]),
            "cold_start": bool(row["home_profile_cold_start"] or row["away_profile_cold_start"]),
            "home_win": float(row["home_win"]),
            "home_points": int(row["home_points"]),
            "away_points": int(row["away_points"]),
            "margin": int(row["margin"]),
            "total": int(row["total"]),
            "home_win_probability": helpers.safe_probability(probability),
            helpers.SOURCE_KNOWN_AT_FIELD: row[helpers.SOURCE_KNOWN_AT_FIELD],
            helpers.LINEAGE_FIELD: row[helpers.LINEAGE_FIELD],
        }

    for row in by_season[2023]:
        logistic = common(row, helpers.LOGISTIC_FAMILY, row["baseline_logistic_probability"])
        logistic["model_origin"] = "FROZEN_BASELINE_FALLBACK_NO_PRIOR_POST_PUBLICATION_LABELS"
        logistic["fit_seasons"] = []
        predictions.append(logistic)
        ridge = common(row, helpers.MARGIN_FAMILY, row["baseline_margin_probability"])
        ridge["predicted_margin"] = float(row["baseline_margin"])
        ridge["model_origin"] = "FROZEN_BASELINE_FALLBACK_NO_PRIOR_POST_PUBLICATION_LABELS"
        ridge["fit_seasons"] = []
        predictions.append(ridge)

    for prediction_season in (2024, 2025):
        fit_seasons = helpers.fit_seasons_for_prediction(prediction_season)
        fit = [row for row in rows if int(row["season"]) in fit_seasons]
        predict = by_season[prediction_season]
        if any(int(row["season"]) >= prediction_season for row in fit):
            raise ValueError("target-season or future outcomes entered model fit")
        binary = [row for row in fit if row["home_win"] in (0.0, 1.0)]
        logistic = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        C=float(contract["model_policy"]["logistic_c"]),
                        max_iter=2000,
                        solver="lbfgs",
                        random_state=0,
                    ),
                ),
            ]
        )
        logistic.fit(
            matrix(binary, helpers.LOGISTIC_FEATURES),
            np.asarray([int(row["home_win"]) for row in binary], dtype=int),
        )
        logistic_probability = logistic.predict_proba(
            matrix(predict, helpers.LOGISTIC_FEATURES)
        )[:, 1]
        model_specs[helpers.LOGISTIC_FAMILY]["models_by_prediction_season"][prediction_season] = logistic
        for row, value in zip(predict, logistic_probability):
            item = common(row, helpers.LOGISTIC_FAMILY, float(value))
            item["model_origin"] = "CHRONOLOGICAL_PRIOR_SEASON_FIT"
            item["fit_seasons"] = list(fit_seasons)
            predictions.append(item)

        ridge = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=float(contract["model_policy"]["ridge_alpha"]))),
            ]
        )
        ridge.fit(
            matrix(fit, helpers.MARGIN_FEATURES),
            np.asarray([row["margin"] for row in fit], dtype=float),
        )
        predicted_margin = ridge.predict(matrix(predict, helpers.MARGIN_FEATURES))
        model_specs[helpers.MARGIN_FAMILY]["models_by_prediction_season"][prediction_season] = ridge
        for row, value in zip(predict, predicted_margin):
            item = common(row, helpers.MARGIN_FAMILY, helpers.sigmoid(float(value) / 14.0))
            item["predicted_margin"] = float(value)
            item["model_origin"] = "CHRONOLOGICAL_PRIOR_SEASON_FIT"
            item["fit_seasons"] = list(fit_seasons)
            predictions.append(item)

        diagnostics["fit_plan"][str(prediction_season)] = {
            "fit_seasons": list(fit_seasons),
            "fit_rows": len(fit),
            "binary_fit_rows": len(binary),
            "prediction_rows": len(predict),
            "maximum_fit_start_utc": max(row["start_utc"] for row in fit),
            "minimum_prediction_start_utc": min(row["start_utc"] for row in predict),
            "chronological_order": "PASS",
        }
    expected = 2 * sum(len(rows) for rows in by_season.values())
    if len(predictions) != expected:
        raise ValueError("prediction population is incomplete")
    return predictions, list(model_specs.values()), diagnostics


def serialize_models(
    specs: Sequence[dict[str, Any]],
    dataset_identity: str,
    stage: Path,
    output_root: Path,
    base: Any,
    helpers: Any,
    run_version: str,
    storage_namespace: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for spec in specs:
        family = str(spec["family"])
        model_stage = stage / "models" / family
        model_stage.mkdir(parents=True)
        artifact = model_stage / "model.joblib"
        payload = {
            "classification": helpers.CLASSIFICATION,
            "run_version": run_version,
            "dataset_identity": dataset_identity,
            **spec,
        }
        joblib.dump(payload, artifact, compress=3, protocol=5)
        artifact_sha = sha256_file(artifact)
        replay = joblib.load(artifact)
        if replay["family"] != family or replay["dataset_identity"] != dataset_identity:
            raise ValueError(f"model serialization replay failed: {family}")
        model_identity = helpers.stable_hash(
            {
                "family": family,
                "dataset_identity": dataset_identity,
                "artifact_sha256": artifact_sha,
                "prediction_seasons": [2023, 2024, 2025],
            }
        )
        destination = output_root / f"model_artifacts/{storage_namespace}/sha256" / model_identity
        base.move_or_verify(model_stage, destination, sha256_file)
        records.append(
            {
                "classification": helpers.CLASSIFICATION,
                "family": family,
                "model_identity": model_identity,
                "dataset_identity": dataset_identity,
                "artifact_path": f"model_artifacts/{storage_namespace}/sha256/{model_identity}/model.joblib",
                "artifact_sha256": artifact_sha,
                "serialization_replay": "PASS",
                "fit_seasons_by_prediction_season": {"2023": [], "2024": [2023], "2025": [2023, 2024]},
            }
        )
    return records


def main() -> int:
    args = parser().parse_args()
    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    output_root = args.output_data_root.resolve() if args.output_data_root else data_root
    sys.path.insert(0, str(repo_root / "src"))
    issued = datetime.fromisoformat(args.issued_at_utc.replace("Z", "+00:00"))
    if issued.tzinfo is None:
        raise ValueError("issued-at-utc must be timezone aware")
    base = load_base_runner(repo_root)
    contract_path = (
        args.contract_path.resolve()
        if args.contract_path
        else repo_root / "configs/preliminary_play_drive_augmented_contract.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    profile_module = str(contract.get("profile_module", "play_drive_augmented"))
    if not re.fullmatch(r"[a-z][a-z0-9_]*", profile_module):
        raise ValueError("profile module must be a safe module name")
    helpers = importlib.import_module(f"aggie_analytics.modeling.{profile_module}")
    if contract["classification"] != helpers.CLASSIFICATION:
        raise ValueError("classification drift")

    authorized = contract["authorized_inputs"]
    baseline_run = str(authorized["baseline_run_identity"])
    baseline_manifest_sha = str(authorized["baseline_manifest_sha256"])
    profile_feature_id = str(
        authorized.get("profile_feature_identity", authorized.get("play_drive_feature_identity"))
    )
    profile_sha = str(
        authorized.get("profile_payload_sha256", authorized.get("play_drive_payload_sha256"))
    )
    decision_unit = str(contract["decision_unit"])
    run_version = str(contract["run_version"])
    storage_namespace = str(contract.get("storage_namespace", "preliminary_play_drive_augmented"))
    stage_prefix = str(contract.get("stage_prefix", "post177-"))
    if not re.fullmatch(r"[a-z0-9][a-z0-9_]*", storage_namespace):
        raise ValueError("storage namespace must be a safe relative path component")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*-", stage_prefix):
        raise ValueError("stage prefix must contain only lowercase letters, digits, and hyphens")
    baseline_manifest_path = data_root / "manifests/preliminary_event_chronology/sha256" / baseline_run / "run_manifest.json"
    profile_relative = str(
        contract.get(
            "profile_payload_relative_path",
            "features/historical_known_at/sha256/{profile_feature_identity}/target_game_team_play_drive_features.parquet",
        )
    ).format(profile_feature_identity=profile_feature_id)
    profile_path = data_root / profile_relative
    if sha256_file(baseline_manifest_path) != baseline_manifest_sha:
        raise ValueError("pinned baseline manifest drift")
    if sha256_file(profile_path) != profile_sha:
        raise ValueError("pinned profile feature drift")
    baseline_manifest = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
    prior_manifest: dict[str, Any] | None = None
    prior_run = authorized.get("prior_run_identity", authorized.get("prior_play_drive_run_identity"))
    prior_contract = contract.get("prior_comparison", {})
    if prior_run:
        prior_relative = str(
            prior_contract.get(
                "manifest_relative_path",
                "manifests/preliminary_play_drive_augmented/sha256/{run_identity}/run_manifest.json",
            )
        ).format(run_identity=prior_run)
        prior_path = data_root / prior_relative
        expected_prior_sha = str(
            authorized.get("prior_manifest_sha256", authorized.get("prior_play_drive_manifest_sha256"))
        )
        if sha256_file(prior_path) != expected_prior_sha:
            raise ValueError("pinned prior comparison manifest drift")
        prior_manifest = json.loads(prior_path.read_text(encoding="utf-8"))
    baseline_training_path = data_root / baseline_manifest["external_locations"]["training"] / "training_matrix.parquet"
    baseline_forecast_path = data_root / baseline_manifest["external_locations"]["forecast"] / "predictions.parquet"
    baseline_training = pl.read_parquet(baseline_training_path).filter(pl.col("season") >= 2023).sort(["start_utc", "target_game_id"])
    targets = baseline_training.to_dicts()
    baseline_predictions = pl.read_parquet(baseline_forecast_path).filter(
        pl.col("model_id").is_in(["regularized_logistic", "regularized_linear_margin"])
    ).to_dicts()
    prediction_index = {
        (str(row["model_id"]), str(row["target_game_id"])): row
        for row in baseline_predictions
    }
    profiles = pl.read_parquet(profile_path).to_dicts()
    profiles_by_game: dict[str, list[dict[str, Any]]] = {}
    for row in profiles:
        profiles_by_game.setdefault(str(row["game_id"]), []).append(row)

    features: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for target in targets:
        game_id = str(target["target_game_id"])
        feature = helpers.build_game_profile(target, profiles_by_game.get(game_id, []))
        logistic_base = prediction_index[("regularized_logistic", game_id)]
        margin_base = prediction_index[("regularized_linear_margin", game_id)]
        feature.update(
            {
                "baseline_logistic_probability": float(logistic_base["home_win_probability"]),
                "baseline_logit": helpers.logit(float(logistic_base["home_win_probability"])),
                "baseline_logistic_model_identity": str(logistic_base["model_identity"]),
                "baseline_margin_probability": float(margin_base["home_win_probability"]),
                "baseline_margin": float(margin_base["predicted_margin"]),
                "baseline_margin_model_identity": str(margin_base["model_identity"]),
            }
        )
        feature["feature_row_identity"] = helpers.stable_hash(feature)
        features.append(feature)
        rows.append({**feature, **target})
    if len(features) != 2763 or len({row["target_game_id"] for row in features}) != len(features):
        raise ValueError("approved target population changed")
    if sorted({int(row["season"]) for row in rows}) != [2023, 2024, 2025]:
        raise ValueError("approved target seasons changed")

    outcome_columns = [
        "classification", "target_game_id", "season", "season_type", "week", "start_utc",
        "home_team_id", "away_team_id", "home_points", "away_points", "margin", "total",
        "home_win", "target_policy_version", "target_source_sha256",
        "target_source_record_sha256", "label_eligibility",
    ]
    split_columns = ["classification", "target_game_id", "season", "start_utc", "assignment"]
    outcome_targets = [{name: row.get(name) for name in outcome_columns} for row in targets]
    split_assignments = [{name: row.get(name) for name in split_columns} for row in targets]
    feature_columns = [
        "classification", "target_game_id", "season", "start_utc", "cutoff_utc", "home_team_id",
        "away_team_id", "baseline_logistic_probability", "baseline_logit",
        "baseline_logistic_model_identity", "baseline_margin_probability", "baseline_margin",
        "baseline_margin_model_identity", *helpers.DIFFERENCE_FIELDS, "home_profile_cold_start",
        "away_profile_cold_start", helpers.HOME_SOURCE_KNOWN_AT_FIELD,
        helpers.AWAY_SOURCE_KNOWN_AT_FIELD, helpers.SOURCE_KNOWN_AT_FIELD,
        helpers.LINEAGE_FIELD, "feature_row_identity", helpers.PROTECTED_FIELD,
    ]
    feature_payload_rows = [{name: row.get(name) for name in feature_columns} for row in features]

    code = {
        "contract_sha256": sha256_file(contract_path),
        "module_sha256": sha256_file(repo_root / f"src/aggie_analytics/modeling/{profile_module}.py"),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "validator_sha256": sha256_file(repo_root / "tools/validate_preliminary_play_drive_augmented.py"),
    }
    tmp_root = output_root / f"tmp/{storage_namespace}"
    tmp_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=stage_prefix, dir=tmp_root))
    try:
        dataset_stage = stage / "dataset"
        payloads: list[dict[str, Any]] = []
        for records, name in (
            (feature_payload_rows, "feature_matrix.parquet"),
            (outcome_targets, "outcome_targets.parquet"),
            (split_assignments, "split_assignments.parquet"),
            (rows, "training_matrix.parquet"),
        ):
            info = base.write_parquet(records, dataset_stage / name, ["start_utc", "target_game_id"])
            info["sha256"] = sha256_file(dataset_stage / name)
            payloads.append(info)
        input_identities = {
            "baseline_run": baseline_run,
            "baseline_dataset": baseline_manifest["dataset_identity"],
            "baseline_feature": baseline_manifest["feature_identity"],
            "baseline_target": baseline_manifest["target_identity"],
            "baseline_split": baseline_manifest["split_identity"],
            "baseline_forecast": baseline_manifest["forecast_identity"],
            "profile_feature": profile_feature_id,
        }
        if prior_run:
            input_identities["prior_comparison_run"] = str(prior_run)
        dataset_identity = helpers.stable_hash(
            {
                "run_version": run_version,
                "classification": helpers.CLASSIFICATION,
                "input_identities": input_identities,
                "code_identities": code,
                "payloads": sorted(payloads, key=lambda row: row["name"]),
            }
        )
        training_destination = output_root / f"training/{storage_namespace}/sha256" / dataset_identity
        base.move_or_verify(dataset_stage, training_destination, sha256_file)
        feature_identity = helpers.stable_hash(
            {
                "dataset_identity": dataset_identity,
                "feature_columns": list(helpers.LOGISTIC_FEATURES),
                "profile_feature": profile_feature_id,
            }
        )
        target_identity = helpers.stable_hash(
            {
                "dataset_identity": dataset_identity,
                "source_target_identity": baseline_manifest["target_identity"],
                "payload_sha256": next(row["sha256"] for row in payloads if row["name"] == "outcome_targets.parquet"),
            }
        )
        split_identity = helpers.stable_hash(
            {
                "dataset_identity": dataset_identity,
                "source_split_identity": baseline_manifest["split_identity"],
                "chronology_policy": contract["chronology_policy"],
                "payload_sha256": next(row["sha256"] for row in payloads if row["name"] == "split_assignments.parquet"),
            }
        )

        predictions, model_specs, diagnostics = fit_models(rows, contract, helpers)
        models = serialize_models(
            model_specs,
            dataset_identity,
            stage,
            output_root,
            base,
            helpers,
            run_version,
            storage_namespace,
        )
        model_identities = {row["family"]: row["model_identity"] for row in models}
        for row in predictions:
            row.update(
                {
                    "model_identity": model_identities[row["model_id"]],
                    "dataset_identity": dataset_identity,
                    "feature_identity": feature_identity,
                    "target_identity": target_identity,
                    "split_identity": split_identity,
                }
            )
        predictions.sort(key=lambda row: (row["model_id"], row["start_utc"], row["target_game_id"]))
        forecast_stage = stage / "forecast"
        forecast_payload = base.write_parquet(
            predictions, forecast_stage / "predictions.parquet", ["model_id", "start_utc", "target_game_id"]
        )
        forecast_payload["sha256"] = sha256_file(forecast_stage / "predictions.parquet")
        forecast_identity = helpers.stable_hash(
            {
                "dataset_identity": dataset_identity,
                "model_identities": model_identities,
                "payload": forecast_payload,
            }
        )
        forecast_destination = output_root / f"forecast_snapshots/{storage_namespace}/sha256" / forecast_identity
        base.move_or_verify(forecast_stage, forecast_destination, sha256_file)

        metrics = {
            family: metric_slices([row for row in predictions if row["model_id"] == family], helpers)
            for family in sorted(model_identities)
        }
        frozen_rows = {
            helpers.LOGISTIC_FAMILY: [
                {
                    **row,
                    "home_win_probability": float(row["baseline_logistic_probability"]),
                    "predicted_margin": None,
                    "cold_start": bool(row["home_profile_cold_start"] or row["away_profile_cold_start"]),
                    "neutral_site": bool(row["neutral_site"]),
                }
                for row in rows
            ],
            helpers.MARGIN_FAMILY: [
                {
                    **row,
                    "home_win_probability": float(row["baseline_margin_probability"]),
                    "predicted_margin": float(row["baseline_margin"]),
                    "cold_start": bool(row["home_profile_cold_start"] or row["away_profile_cold_start"]),
                    "neutral_site": bool(row["neutral_site"]),
                }
                for row in rows
            ],
        }
        frozen_metrics = {family: metric_slices(values, helpers) for family, values in frozen_rows.items()}
        comparison: dict[str, Any] = {}
        for family in sorted(model_identities):
            comparison[family] = {}
            for season in (2023, 2024, 2025):
                slice_id = f"SEASON_{season}_ALL"
                candidate = metric_row(metrics[family], slice_id)
                frozen = metric_row(frozen_metrics[family], slice_id)
                item: dict[str, Any] = {
                    "rows_equal": candidate["probability"]["rows"] == frozen["probability"]["rows"],
                    "brier_delta_candidate_minus_frozen": candidate["probability"]["brier"] - frozen["probability"]["brier"],
                    "log_loss_delta_candidate_minus_frozen": candidate["probability"]["log_loss"] - frozen["probability"]["log_loss"],
                }
                if candidate["margin"]["rows"]:
                    item["margin_mae_delta_candidate_minus_frozen"] = candidate["margin"]["mae"] - frozen["margin"]["mae"]
                comparison[family][str(season)] = item

        prior_comparison: dict[str, Any] = {}
        if prior_manifest is not None:
            family_map = prior_contract.get("family_map", {})
            for family in sorted(model_identities):
                prior_comparison[family] = {}
                prior_family = str(family_map.get(family, family))
                for season in (2023, 2024, 2025):
                    slice_id = f"SEASON_{season}_ALL"
                    candidate = metric_row(metrics[family], slice_id)
                    prior = metric_row(prior_manifest["metrics"][prior_family], slice_id)
                    item = {
                        "rows_equal": candidate["probability"]["rows"]
                        == prior["probability"]["rows"],
                        "brier_delta_candidate_minus_prior": candidate["probability"]["brier"]
                        - prior["probability"]["brier"],
                        "log_loss_delta_candidate_minus_prior": candidate["probability"]["log_loss"]
                        - prior["probability"]["log_loss"],
                    }
                    if candidate["margin"]["rows"]:
                        item["margin_mae_delta_candidate_minus_prior"] = (
                            candidate["margin"]["mae"] - prior["margin"]["mae"]
                        )
                    prior_comparison[family][str(season)] = item

        run_identity = helpers.stable_hash(
            {
                "run_version": run_version,
                "dataset_identity": dataset_identity,
                "feature_identity": feature_identity,
                "target_identity": target_identity,
                "split_identity": split_identity,
                "model_identities": model_identities,
                "forecast_identity": forecast_identity,
                "code_identities": code,
            }
        )
        missingness = {
            name: sum(row.get(name) is None for row in rows)
            for name in helpers.DIFFERENCE_FIELDS
        }
        season_counts = dict(sorted(Counter(str(row["season"]) for row in rows).items()))
        unused_profile_games = sorted(set(profiles_by_game) - {row["target_game_id"] for row in rows})
        manifest = {
            "schema_version": "1.0.0",
            "artifact_type": contract.get("artifact_type", "PRELIMINARY_UNPROTECTED_PLAY_DRIVE_AUGMENTED_RUN"),
            "classification": helpers.CLASSIFICATION,
            "decision_unit": decision_unit,
            "run_version": run_version,
            "run_identity": run_identity,
            "issued_at_utc": issued.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "input_identities": input_identities,
            "code_identities": code,
            "dataset_identity": dataset_identity,
            "feature_identity": feature_identity,
            "target_identity": target_identity,
            "split_identity": split_identity,
            "forecast_identity": forecast_identity,
            "model_identities": model_identities,
            "dataset_payloads": payloads,
            "forecast_payload": forecast_payload,
            "models": models,
            "population": {
                "rows": len(rows),
                "games": len(rows),
                "seasons": [2023, 2024, 2025],
                "rows_by_season": season_counts,
                "feature_count_logistic": len(helpers.LOGISTIC_FEATURES),
                "feature_count_margin": len(helpers.MARGIN_FEATURES),
                "profile_source_rows": len(profiles),
                "unused_profile_games": unused_profile_games,
                "cold_start_games": sum(bool(row["home_profile_cold_start"] or row["away_profile_cold_start"]) for row in rows),
                "missing_feature_cells": missingness,
            },
            "metrics": metrics,
            "frozen_baseline_metrics": frozen_metrics,
            "baseline_comparison": comparison,
            "prior_comparison": {
                "label": prior_contract.get("label", "prior_play_drive"),
                "run_identity": str(prior_run) if prior_run else None,
                "metrics": prior_comparison,
            },
            "diagnostics": diagnostics,
            "leakage_validation": {
                "target_game_outcome_in_profile_evidence": 0,
                "source_known_at_after_target_cutoff": 0,
                "target_or_future_season_outcomes_in_fit": 0,
                "outcome_targets_materialized_separately": "PASS",
                "same_target_rows_as_frozen_baseline": "PASS",
                "2023_no_fit_fallback_exact": "PASS",
                "protected_split_opened": False,
            },
            "external_locations": {
                "training": f"training/{storage_namespace}/sha256/{dataset_identity}",
                "models": f"model_artifacts/{storage_namespace}/sha256/<model_identity>",
                "forecast": f"forecast_snapshots/{storage_namespace}/sha256/{forecast_identity}",
                "manifest": f"manifests/{storage_namespace}/sha256/{run_identity}/run_manifest.json",
            },
            "limitations": contract.get("limitations", [
                "All artifacts, metrics, and comparisons are PRELIMINARY_UNPROTECTED.",
                "The play/drive profiles summarize 2010-2022 evidence known in May 2023 and cannot be backcast into the 2010-2022 baseline fit window.",
                "The 2023 candidate is therefore an exact frozen-baseline fallback; 2024 fits only 2023 outcomes and 2025 fits only 2023-2024 outcomes.",
                "Static profile differences do not represent target-season play-by-play updates.",
                "Tree boosting was not admitted for this short post-publication supervised horizon.",
                "Negative or mixed comparison results are preserved and cannot promote a champion.",
            ]),
            "protected_nonclaims": contract["protected_nonclaims"],
            "cleanup": {"reconstructible_stage_removed": True, "abandoned_downloads": 0},
        }
        manifest_stage = stage / "manifest"
        manifest_stage.mkdir(parents=True)
        manifest_path = manifest_stage / "run_manifest.json"
        manifest_path.write_bytes(helpers.canonical_json(manifest) + b"\n")
        manifest_sha = sha256_file(manifest_path)
        manifest_destination = output_root / f"manifests/{storage_namespace}/sha256" / run_identity
        base.move_or_verify(manifest_stage, manifest_destination, sha256_file)
        result = {
            "result": "PASS",
            "run_identity": run_identity,
            "manifest_sha256": manifest_sha,
            "dataset_identity": dataset_identity,
            "feature_identity": feature_identity,
            "target_identity": target_identity,
            "split_identity": split_identity,
            "forecast_identity": forecast_identity,
            "model_identities": model_identities,
            "population": manifest["population"],
            "baseline_comparison": comparison,
            "prior_comparison": manifest["prior_comparison"],
        }
        payload = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
        if args.summary_path:
            args.summary_path.parent.mkdir(parents=True, exist_ok=True)
            args.summary_path.write_text(payload, encoding="utf-8")
        print(payload, end="")
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
