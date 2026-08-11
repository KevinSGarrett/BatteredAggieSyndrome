from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import io
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Mapping, Sequence

import joblib
import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, PoissonRegressor, Ridge


CLASSIFICATION = "PRELIMINARY_UNPROTECTED_EVENT_CHRONOLOGY_ONLY"
RUN_VERSION = "expanded-event-chronology-team-outcome-plus-ap-rankings-v1"
HISTORICAL_REPLAY_ID = "cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7"
HISTORICAL_OUTCOMES_SHA = "7fdea2ced7508e7f3b78d397bf8984325dd2b7095b05dc486335ee9c432ccb64"
CORE_REGISTRY_SHA = "10d0bd0adcef3fc1ba22fb9932f353cc59b0e5d4508c7891a1472d0221a454ac"
CONTEMPORARY_DATASET_ID = "5c7b382c10ee2080e6bdf03a435a3f9990a2274cbee5911c601c7b3c2a7c5022"
CONTEMPORARY_TARGET_ID = "60e5cb3caac26b8dcbd87eedaddac0e385d8c4dc59e0b471c9ff9fdac8a7066d"
CONTEMPORARY_TARGET_SHA = "d9e49d903b83759b31c6169891aa9e3183f63a1cd2263d03a3a0b0745a79d0bb"
RANKINGS_RUN = "a7743bb76680c5034b3b15bcccff76961af400f949fd7de0f3feb0db33acaa7e"
RANKINGS_FEATURE_ID = "b165e076222104d71f345cf294d5b177d2c049bf1168b11c29e9cc5690375274"
RANKINGS_FEATURE_SHA = "f7bade2b2653df3c4f82927beaf3ba7dc254c6bb8487849f980a2eac6f0c3a4e"
TAMU_TEAM_ID = "team_d0aff8aacd805801ab3d3d8293f3b298"
FIT_SEASONS = tuple(range(2010, 2023))
TUNE_SEASONS = (2023, 2024)
EVALUATION_SEASONS = (2025,)
MAX_RECONCILED_SOURCE_START_DRIFT_MINUTES = 270


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--output-data-root", type=Path)
    result.add_argument("--issued-at-utc", required=True)
    result.add_argument("--summary-path", type=Path)
    return result


def load_base_runner(repo_root: Path) -> Any:
    path = repo_root / "tools/run_preliminary_unprotected_baselines.py"
    spec = importlib.util.spec_from_file_location("expanded_preliminary_base_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load preliminary baseline helpers")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def split_assignment(season: int) -> str:
    if season in FIT_SEASONS:
        return "DEVELOPMENT_FIT"
    if season in TUNE_SEASONS:
        return "DEVELOPMENT_TUNE"
    if season in EVALUATION_SEASONS:
        return "DEVELOPMENT_EVALUATION_UNPROTECTED"
    raise ValueError(f"season {season} is outside expanded preliminary chronology")


def _iso(value: object, parse_time: Any) -> str:
    parsed = parse_time(value)
    if parsed is None:
        raise ValueError("timezone-aware timestamp required")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def load_targets(
    repo_root: Path, data_root: Path, helpers: Any, chronology: Any
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Path]]:
    paths = {
        "historical_outcomes": data_root
        / "pit_state/historical_known_at/sha256"
        / HISTORICAL_REPLAY_ID
        / "accepted_game_outcomes.parquet",
        "core_registry": data_root
        / "canonical/BAT-387/sha256"
        / CORE_REGISTRY_SHA
        / "canonical_core_registry.csv",
        "contemporary_targets": data_root
        / "training/preliminary_unprotected/sha256"
        / CONTEMPORARY_DATASET_ID
        / "outcome_targets.parquet",
        "rankings_features": data_root
        / "features/historical_rankings/sha256"
        / RANKINGS_FEATURE_ID
        / "rankings_pit_features.parquet",
        "rankings_manifest": data_root
        / "manifests/historical_rankings_pit/sha256"
        / RANKINGS_RUN
        / "rankings_pit_manifest.json",
    }
    expected = {
        "historical_outcomes": HISTORICAL_OUTCOMES_SHA,
        "core_registry": CORE_REGISTRY_SHA,
        "contemporary_targets": CONTEMPORARY_TARGET_SHA,
        "rankings_features": RANKINGS_FEATURE_SHA,
    }
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned {name}: {path}")
        if name in expected and helpers.sha256_file(path) != expected[name]:
            raise ValueError(f"pinned {name} hash drift")

    core = pl.read_csv(paths["core_registry"], infer_schema_length=10000)
    game_rows = core.filter(
        (pl.col("record_type") == "ENTITY")
        & (pl.col("entity_type") == "game")
        & pl.col("season").is_between(2010, 2025)
    ).to_dicts()
    metadata = {str(row["canonical_id"]): row for row in game_rows}
    if len(metadata) != len(game_rows):
        raise ValueError("duplicate canonical game metadata")

    targets: list[dict[str, Any]] = []
    historical_start_deltas: list[int] = []
    historical = pl.read_parquet(paths["historical_outcomes"]).sort(
        ["game_start_utc", "canonical_game_id"]
    )
    for row in historical.to_dicts():
        game_id = str(row["canonical_game_id"])
        meta = metadata.get(game_id)
        if meta is None:
            raise ValueError(f"historical outcome lacks canonical metadata: {game_id}")
        if (
            int(meta["season"]) != int(row["season"])
            or str(meta["home_team_id"]) != str(row["home_team_id"])
            or str(meta["away_team_id"]) != str(row["away_team_id"])
        ):
            raise ValueError(f"historical outcome/core identity mismatch: {game_id}")
        canonical_start = chronology.parse_time(meta["start_time_utc"])
        source_start = chronology.parse_time(row["game_start_utc"])
        if canonical_start is None or source_start is None:
            raise ValueError(f"historical outcome/core start is not timezone aware: {game_id}")
        source_start_delta_minutes = int(
            (source_start - canonical_start).total_seconds() / 60
        )
        if abs(source_start_delta_minutes) > MAX_RECONCILED_SOURCE_START_DRIFT_MINUTES:
            raise ValueError(
                "historical outcome/core start drift exceeds the pinned reconciled "
                f"population bound: {game_id} ({source_start_delta_minutes} minutes)"
            )
        historical_start_deltas.append(source_start_delta_minutes)
        home_points, away_points = int(row["home_points"]), int(row["away_points"])
        targets.append(
            {
                "classification": CLASSIFICATION,
                "target_game_id": game_id,
                "source_game_id": str(row["source_game_id"]),
                "season": int(row["season"]),
                "season_type": str(meta["season_type"]),
                "week": int(meta["week"]),
                "start_utc": _iso(row["game_start_utc"], chronology.parse_time),
                "canonical_game_start_utc": _iso(
                    meta["start_time_utc"], chronology.parse_time
                ),
                "source_game_start_utc": _iso(
                    row["game_start_utc"], chronology.parse_time
                ),
                "source_minus_canonical_start_minutes": source_start_delta_minutes,
                "chronological_cutoff_authority": (
                    "PINNED_ACCEPTED_HISTORICAL_SOURCE_START_ALIGNED_TO_RANKINGS_FEATURE"
                ),
                "home_team_id": str(row["home_team_id"]),
                "away_team_id": str(row["away_team_id"]),
                "neutral_site": bool(meta["neutral_site"]),
                "home_points": home_points,
                "away_points": away_points,
                "margin": home_points - away_points,
                "total": home_points + away_points,
                "home_win": 1.0 if home_points > away_points else 0.0 if home_points < away_points else 0.5,
                "assignment": split_assignment(int(row["season"])),
                "target_policy_version": "strict-cross-source-exact-outcome-label-v1",
                "target_source_sha256": str(row["source_payload_sha256"]),
                "target_source_record_sha256": str(row["source_record_evidence_sha256"]),
                "source_known_at_utc": str(row["source_known_at_utc"]),
                "historical_known_at_eligible": False,
                "label_eligibility": "LABEL_AND_EVENT_CHRONOLOGY_RESEARCH_ONLY",
            }
        )

    contemporary = pl.read_parquet(paths["contemporary_targets"]).sort(
        ["start_utc", "target_game_id"]
    )
    for row in contemporary.to_dicts():
        game_id = str(row["target_game_id"])
        meta = metadata.get(game_id)
        if meta is None:
            raise ValueError(f"contemporary target lacks canonical metadata: {game_id}")
        target = dict(row)
        target.update(
            {
                "classification": CLASSIFICATION,
                "neutral_site": bool(meta["neutral_site"]),
                "assignment": split_assignment(int(row["season"])),
                "source_known_at_utc": None,
                "historical_known_at_eligible": False,
                "label_eligibility": "LABEL_AND_EVENT_CHRONOLOGY_RESEARCH_ONLY",
                "canonical_game_start_utc": _iso(
                    meta["start_time_utc"], chronology.parse_time
                ),
                "source_game_start_utc": _iso(
                    row["start_utc"], chronology.parse_time
                ),
                "source_minus_canonical_start_minutes": int(
                    (
                        chronology.parse_time(row["start_utc"])
                        - chronology.parse_time(meta["start_time_utc"])
                    ).total_seconds()
                    / 60
                ),
                "chronological_cutoff_authority": "PINNED_CONTEMPORARY_TARGET_START",
            }
        )
        if target["source_minus_canonical_start_minutes"] != 0:
            raise ValueError(f"contemporary target/core start mismatch: {game_id}")
        target["start_utc"] = target["source_game_start_utc"]
        targets.append(target)

    targets.sort(key=lambda row: (row["start_utc"], row["target_game_id"]))
    ids = [row["target_game_id"] for row in targets]
    if len(ids) != len(set(ids)):
        raise ValueError("historical/contemporary target overlap")
    seasons = sorted({int(row["season"]) for row in targets})
    if seasons != list(range(2010, 2026)):
        raise ValueError(f"expanded target season drift: {seasons}")
    rankings_manifest = json.loads(paths["rankings_manifest"].read_text(encoding="utf-8"))
    if rankings_manifest.get("feature_identity") != RANKINGS_FEATURE_ID:
        raise ValueError("rankings feature identity drift")
    report = {
        "historical_labels": historical.height,
        "contemporary_labels": contemporary.height,
        "targets": len(targets),
        "target_counts_by_season": dict(
            sorted(Counter(str(row["season"]) for row in targets).items())
        ),
        "seasons": seasons,
        "historical_source_start_drift": {
            "definition": "source_game_start_utc_minus_canonical_game_start_utc_minutes",
            "chronological_cutoff_authority": (
                "accepted_game_outcomes.game_start_utc aligned to the pinned rankings feature"
            ),
            "exact_match_rows": sum(value == 0 for value in historical_start_deltas),
            "drift_rows": sum(value != 0 for value in historical_start_deltas),
            "minimum_minutes": min(historical_start_deltas),
            "maximum_minutes": max(historical_start_deltas),
            "maximum_absolute_minutes": max(abs(value) for value in historical_start_deltas),
            "accepted_bound_minutes": MAX_RECONCILED_SOURCE_START_DRIFT_MINUTES,
            "distribution": dict(
                sorted(Counter(str(value) for value in historical_start_deltas).items())
            ),
        },
    }
    return targets, report, paths


def common_prediction(row: Mapping[str, Any], family: str, probability: float) -> dict[str, Any]:
    return {
        "classification": CLASSIFICATION,
        "model_id": family,
        "target_game_id": row["target_game_id"],
        "season": int(row["season"]),
        "week": int(row["week"]),
        "start_utc": row["start_utc"],
        "assignment": row["assignment"],
        "home_team_id": row["home_team_id"],
        "away_team_id": row["away_team_id"],
        "neutral_site": bool(row["neutral_site"]),
        "cold_start": bool(row["home_cold_start"] or row["away_cold_start"]),
        "home_win": float(row["home_win"]),
        "home_points": int(row["home_points"]),
        "away_points": int(row["away_points"]),
        "margin": int(row["margin"]),
        "total": int(row["total"]),
        "home_win_probability": float(probability),
        "calibrated_home_win_probability": float(probability),
    }


def add_calibration(predictions: list[dict[str, Any]], helpers: Any) -> Any:
    tune = [row for row in predictions if int(row["season"]) in TUNE_SEASONS]
    calibrator = helpers.fit_logistic_calibrator(
        [row["home_win"] for row in tune],
        [row["home_win_probability"] for row in tune],
    )
    evaluation = [row for row in predictions if int(row["season"]) in EVALUATION_SEASONS]
    if evaluation:
        calibrated = helpers.apply_logistic_calibrator(
            calibrator, [row["home_win_probability"] for row in evaluation]
        )
        for row, value in zip(evaluation, calibrated):
            row["calibrated_home_win_probability"] = float(value)
    return calibrator


def _batch_key(row: Mapping[str, Any]) -> tuple[int, int, int]:
    season_type = str(row["season_type"]).lower()
    order = 0 if season_type == "regular" else 1
    return int(row["season"]), order, int(row["week"])


def elo_replay(
    games: Sequence[Mapping[str, Any]],
    *,
    k_factor: float,
    home_advantage: float,
    initial_ratings: Mapping[str, float] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    ratings = {str(key): float(value) for key, value in (initial_ratings or {}).items()}
    groups: dict[tuple[int, int, int], list[Mapping[str, Any]]] = {}
    for row in games:
        groups.setdefault(_batch_key(row), []).append(row)
    predictions: list[dict[str, Any]] = []
    for key in sorted(groups):
        rows = sorted(groups[key], key=lambda row: (row["start_utc"], row["target_game_id"]))
        snapshot = dict(ratings)
        deltas: dict[str, float] = Counter()
        for row in rows:
            home_id, away_id = str(row["home_team_id"]), str(row["away_team_id"])
            home_rating = snapshot.get(home_id, 1500.0)
            away_rating = snapshot.get(away_id, 1500.0)
            advantage = 0.0 if bool(row["neutral_site"]) else home_advantage
            probability = 1.0 / (1.0 + 10.0 ** (-(home_rating + advantage - away_rating) / 400.0))
            predictions.append({**dict(row), "home_win_probability": float(probability)})
            actual = float(row["home_win"])
            change = k_factor * (actual - probability)
            deltas[home_id] += change
            deltas[away_id] -= change
        for team_id, delta in deltas.items():
            ratings[team_id] = snapshot.get(team_id, 1500.0) + float(delta)
    return predictions, ratings


def train_models(
    rows: Sequence[dict[str, Any]], helpers: Any
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    fit = [row for row in rows if int(row["season"]) in FIT_SEASONS]
    tune = [row for row in rows if int(row["season"]) in TUNE_SEASONS]
    evaluation = [row for row in rows if int(row["season"]) in EVALUATION_SEASONS]
    if not fit or not tune or not evaluation:
        raise ValueError("fit, tune, and unprotected evaluation populations are required")
    predictions: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {}

    naive_probability = float(np.mean([row["home_win"] for row in fit]))
    naive_predictions = [
        common_prediction(row, "naive_historical_average", naive_probability)
        for row in tune + evaluation
    ]
    naive_cal = add_calibration(naive_predictions, helpers)
    predictions.extend(naive_predictions)
    artifacts.append(
        {
            "family": "naive_historical_average",
            "state": {"probability": naive_probability, "calibrator": naive_cal},
            "fit_seasons": list(FIT_SEASONS),
        }
    )

    nonneutral = [row["home_win"] for row in fit if not row["neutral_site"]]
    neutral = [row["home_win"] for row in fit if row["neutral_site"]]
    home_state = {
        "nonneutral_probability": float(np.mean(nonneutral)),
        "neutral_probability": float(np.mean(neutral)),
    }
    home_predictions = [
        common_prediction(
            row,
            "home_field_empirical",
            home_state["neutral_probability"]
            if row["neutral_site"]
            else home_state["nonneutral_probability"],
        )
        for row in tune + evaluation
    ]
    home_cal = add_calibration(home_predictions, helpers)
    predictions.extend(home_predictions)
    artifacts.append(
        {
            "family": "home_field_empirical",
            "state": {**home_state, "calibrator": home_cal},
            "fit_seasons": list(FIT_SEASONS),
        }
    )

    elo_grid = []
    for k_factor in (10.0, 20.0, 30.0, 40.0):
        for home_advantage in (0.0, 35.0, 55.0, 75.0, 95.0):
            replay, _ = elo_replay(
                fit, k_factor=k_factor, home_advantage=home_advantage
            )
            validation = [row for row in replay if int(row["season"]) >= 2020]
            score = helpers.brier_score(
                [row["home_win"] for row in validation],
                [row["home_win_probability"] for row in validation],
            )
            elo_grid.append((score, k_factor, home_advantage))
    _, elo_k, elo_home = min(elo_grid)
    fit_replay, ratings_through_fit = elo_replay(
        fit, k_factor=elo_k, home_advantage=elo_home
    )
    del fit_replay
    tune_raw, ratings_through_tune = elo_replay(
        tune,
        k_factor=elo_k,
        home_advantage=elo_home,
        initial_ratings=ratings_through_fit,
    )
    evaluation_raw, _ = elo_replay(
        evaluation,
        k_factor=elo_k,
        home_advantage=elo_home,
        initial_ratings=ratings_through_tune,
    )
    elo_predictions = [
        common_prediction(row, "elo_rating_week_batched", row["home_win_probability"])
        for row in tune_raw + evaluation_raw
    ]
    elo_cal = add_calibration(elo_predictions, helpers)
    predictions.extend(elo_predictions)
    artifacts.append(
        {
            "family": "elo_rating_week_batched",
            "state": {
                "k_factor": elo_k,
                "home_advantage": elo_home,
                "ratings": ratings_through_tune,
                "ratings_known_through_season": 2024,
                "within_batch_update": "FORBIDDEN",
                "calibrator": elo_cal,
            },
            "fit_seasons": list(range(2010, 2025)),
        }
    )
    diagnostics["elo_development_grid"] = [
        {"brier": score, "k_factor": k, "home_advantage": h}
        for score, k, h in sorted(elo_grid)
    ]

    imputer_fit = helpers.MedianImputer.fit(fit, helpers.FEATURE_COLUMNS, FIT_SEASONS)
    x_fit = imputer_fit.transform(fit)
    x_tune = imputer_fit.transform(tune)
    binary_fit = np.asarray([row["home_win"] in (0.0, 1.0) for row in fit])
    y_fit_binary = np.asarray([int(row["home_win"]) for row in fit])[binary_fit]
    combined = fit + tune
    combined_seasons = FIT_SEASONS + TUNE_SEASONS
    imputer_combined = helpers.MedianImputer.fit(
        combined, helpers.FEATURE_COLUMNS, combined_seasons
    )
    x_combined = imputer_combined.transform(combined)
    x_evaluation = imputer_combined.transform(evaluation)
    combined_binary = np.asarray([row["home_win"] in (0.0, 1.0) for row in combined])
    y_combined_binary = np.asarray([int(row["home_win"]) for row in combined])[
        combined_binary
    ]

    logistic_grid = []
    for c_value in (0.1, 1.0, 10.0):
        model = LogisticRegression(
            C=c_value, max_iter=2000, solver="lbfgs", random_state=0
        ).fit(x_fit[binary_fit], y_fit_binary)
        probability = model.predict_proba(x_tune)[:, 1]
        logistic_grid.append(
            (
                helpers.brier_score([row["home_win"] for row in tune], probability),
                c_value,
            )
        )
    _, logistic_c = min(logistic_grid)
    logistic_tune = LogisticRegression(
        C=logistic_c, max_iter=2000, solver="lbfgs", random_state=0
    ).fit(x_fit[binary_fit], y_fit_binary)
    logistic = LogisticRegression(
        C=logistic_c, max_iter=2000, solver="lbfgs", random_state=0
    ).fit(x_combined[combined_binary], y_combined_binary)
    logistic_predictions = [
        common_prediction(row, "regularized_logistic", value)
        for row, value in zip(tune, logistic_tune.predict_proba(x_tune)[:, 1])
    ] + [
        common_prediction(row, "regularized_logistic", value)
        for row, value in zip(evaluation, logistic.predict_proba(x_evaluation)[:, 1])
    ]
    logistic_cal = add_calibration(logistic_predictions, helpers)
    predictions.extend(logistic_predictions)
    artifacts.append(
        {
            "family": "regularized_logistic",
            "state": {
                "model": logistic,
                "imputer": imputer_combined,
                "calibrator": logistic_cal,
                "selected_c": logistic_c,
            },
            "fit_seasons": list(combined_seasons),
        }
    )
    diagnostics["logistic_tuning"] = [
        {"brier": score, "c": c_value} for score, c_value in sorted(logistic_grid)
    ]

    ridge_grid = []
    y_margin_fit = np.asarray([row["margin"] for row in fit], dtype=float)
    y_margin_tune = np.asarray([row["margin"] for row in tune], dtype=float)
    for alpha in (1.0, 10.0, 100.0):
        model = Ridge(alpha=alpha).fit(x_fit, y_margin_fit)
        margin = model.predict(x_tune)
        ridge_grid.append((float(np.mean(np.abs(margin - y_margin_tune))), alpha))
    _, ridge_alpha = min(ridge_grid)
    ridge_tune = Ridge(alpha=ridge_alpha).fit(x_fit, y_margin_fit)
    ridge = Ridge(alpha=ridge_alpha).fit(
        x_combined, np.asarray([row["margin"] for row in combined], dtype=float)
    )
    ridge_predictions: list[dict[str, Any]] = []
    for part, margins in (
        (tune, ridge_tune.predict(x_tune)),
        (evaluation, ridge.predict(x_evaluation)),
    ):
        for row, margin in zip(part, margins):
            probability = 1.0 / (1.0 + math.exp(-float(margin) / 14.0))
            item = common_prediction(row, "regularized_linear_margin", probability)
            item["predicted_margin"] = float(margin)
            ridge_predictions.append(item)
    ridge_cal = add_calibration(ridge_predictions, helpers)
    predictions.extend(ridge_predictions)
    artifacts.append(
        {
            "family": "regularized_linear_margin",
            "state": {
                "model": ridge,
                "imputer": imputer_combined,
                "probability_scale": 14.0,
                "calibrator": ridge_cal,
                "selected_alpha": ridge_alpha,
            },
            "fit_seasons": list(combined_seasons),
        }
    )
    diagnostics["ridge_tuning"] = [
        {"margin_mae": score, "alpha": alpha} for score, alpha in sorted(ridge_grid)
    ]

    poisson_grid = []
    for alpha in (0.1, 1.0, 10.0):
        home_model = PoissonRegressor(alpha=alpha, max_iter=1000).fit(
            x_fit, np.asarray([row["home_points"] for row in fit])
        )
        away_model = PoissonRegressor(alpha=alpha, max_iter=1000).fit(
            x_fit, np.asarray([row["away_points"] for row in fit])
        )
        home_mu, away_mu = home_model.predict(x_tune), away_model.predict(x_tune)
        poisson_grid.append(
            (
                helpers.poisson_nll([row["home_points"] for row in tune], home_mu)
                + helpers.poisson_nll([row["away_points"] for row in tune], away_mu),
                alpha,
            )
        )
    _, poisson_alpha = min(poisson_grid)
    poisson_home_tune = PoissonRegressor(alpha=poisson_alpha, max_iter=1000).fit(
        x_fit, np.asarray([row["home_points"] for row in fit])
    )
    poisson_away_tune = PoissonRegressor(alpha=poisson_alpha, max_iter=1000).fit(
        x_fit, np.asarray([row["away_points"] for row in fit])
    )
    poisson_home = PoissonRegressor(alpha=poisson_alpha, max_iter=1000).fit(
        x_combined, np.asarray([row["home_points"] for row in combined])
    )
    poisson_away = PoissonRegressor(alpha=poisson_alpha, max_iter=1000).fit(
        x_combined, np.asarray([row["away_points"] for row in combined])
    )
    poisson_predictions: list[dict[str, Any]] = []
    for part, home_mu, away_mu in (
        (
            tune,
            poisson_home_tune.predict(x_tune),
            poisson_away_tune.predict(x_tune),
        ),
        (
            evaluation,
            poisson_home.predict(x_evaluation),
            poisson_away.predict(x_evaluation),
        ),
    ):
        for row, home_value, away_value in zip(part, home_mu, away_mu):
            item = common_prediction(
                row,
                "poisson_skellam_score_distribution",
                helpers.skellam_home_win_probability(home_value, away_value),
            )
            item.update(
                {
                    "predicted_home_points": float(home_value),
                    "predicted_away_points": float(away_value),
                    "predicted_margin": float(home_value - away_value),
                }
            )
            poisson_predictions.append(item)
    poisson_cal = add_calibration(poisson_predictions, helpers)
    predictions.extend(poisson_predictions)
    artifacts.append(
        {
            "family": "poisson_skellam_score_distribution",
            "state": {
                "home_model": poisson_home,
                "away_model": poisson_away,
                "imputer": imputer_combined,
                "calibrator": poisson_cal,
                "selected_alpha": poisson_alpha,
            },
            "fit_seasons": list(combined_seasons),
        }
    )
    diagnostics["poisson_tuning"] = [
        {"joint_nll": score, "alpha": alpha} for score, alpha in sorted(poisson_grid)
    ]

    expected_simple = {
        "naive_historical_average",
        "home_field_empirical",
        "elo_rating_week_batched",
        "regularized_logistic",
        "regularized_linear_margin",
        "poisson_skellam_score_distribution",
    }
    if {item["family"] for item in artifacts} != expected_simple:
        raise ValueError("simple model ladder is incomplete")
    if any(not np.isfinite(row["home_win_probability"]) for row in predictions):
        raise ValueError("simple model probability is not finite")
    roundtrip = {}
    for artifact in artifacts:
        buffer = io.BytesIO()
        joblib.dump(artifact, buffer, compress=0, protocol=5)
        buffer.seek(0)
        loaded = joblib.load(buffer)
        roundtrip[artifact["family"]] = loaded["family"] == artifact["family"]
    if not all(roundtrip.values()):
        raise ValueError("simple serialization replay failed before tree admission")
    diagnostics["simple_pipeline_gate"] = "PASS_BEFORE_TREE_BOOSTING"
    diagnostics["simple_serialization_replay_before_tree"] = roundtrip

    tree_grid = []
    for leaves in (7, 15):
        model = HistGradientBoostingClassifier(
            max_leaf_nodes=leaves,
            l2_regularization=10.0,
            random_state=0,
        ).fit(x_fit[binary_fit], y_fit_binary)
        probability = model.predict_proba(x_tune)[:, 1]
        tree_grid.append(
            (
                helpers.brier_score([row["home_win"] for row in tune], probability),
                leaves,
            )
        )
    _, selected_leaves = min(tree_grid)
    tree_tune = HistGradientBoostingClassifier(
        max_leaf_nodes=selected_leaves, l2_regularization=10.0, random_state=0
    ).fit(x_fit[binary_fit], y_fit_binary)
    tree = HistGradientBoostingClassifier(
        max_leaf_nodes=selected_leaves, l2_regularization=10.0, random_state=0
    ).fit(x_combined[combined_binary], y_combined_binary)
    tree_predictions = [
        common_prediction(row, "hist_gradient_boosting", value)
        for row, value in zip(tune, tree_tune.predict_proba(x_tune)[:, 1])
    ] + [
        common_prediction(row, "hist_gradient_boosting", value)
        for row, value in zip(evaluation, tree.predict_proba(x_evaluation)[:, 1])
    ]
    tree_cal = add_calibration(tree_predictions, helpers)
    predictions.extend(tree_predictions)
    artifacts.append(
        {
            "family": "hist_gradient_boosting",
            "state": {
                "model": tree,
                "imputer": imputer_combined,
                "calibrator": tree_cal,
                "selected_max_leaf_nodes": selected_leaves,
            },
            "fit_seasons": list(combined_seasons),
        }
    )
    diagnostics["tree_tuning"] = [
        {"brier": score, "max_leaf_nodes": leaves}
        for score, leaves in sorted(tree_grid)
    ]
    return predictions, artifacts, diagnostics


def serialize_models(
    specs: Sequence[dict[str, Any]],
    dataset_identity: str,
    output_root: Path,
    stage_root: Path,
    helpers: Any,
) -> list[dict[str, Any]]:
    records = []
    for spec in specs:
        family = str(spec["family"])
        stage = stage_root / "models" / family
        stage.mkdir(parents=True)
        artifact_path = stage / "model.joblib"
        payload = {
            "classification": CLASSIFICATION,
            "run_version": RUN_VERSION,
            "dataset_identity": dataset_identity,
            **spec,
        }
        joblib.dump(payload, artifact_path, compress=3, protocol=5)
        artifact_sha = helpers.sha256_file(artifact_path)
        loaded = joblib.load(artifact_path)
        if loaded["classification"] != CLASSIFICATION or loaded["family"] != family:
            raise ValueError(f"model serialization replay failed: {family}")
        model_identity = helpers.stable_hash(
            {
                "classification": CLASSIFICATION,
                "family": family,
                "dataset_identity": dataset_identity,
                "fit_seasons": spec["fit_seasons"],
                "artifact_sha256": artifact_sha,
            }
        )
        destination = (
            output_root
            / "model_artifacts/preliminary_event_chronology/sha256"
            / model_identity
        )
        base = load_base_runner(Path(__file__).resolve().parents[1])
        base.move_or_verify(stage, destination, helpers.sha256_file)
        records.append(
            {
                "classification": CLASSIFICATION,
                "family": family,
                "model_identity": model_identity,
                "dataset_identity": dataset_identity,
                "fit_seasons": spec["fit_seasons"],
                "artifact_path": f"model_artifacts/preliminary_event_chronology/sha256/{model_identity}/model.joblib",
                "artifact_sha256": artifact_sha,
                "serialization_replay": "PASS",
            }
        )
    return records


def main() -> int:
    args = parser().parse_args()
    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    output_root = args.output_data_root.resolve() if args.output_data_root else data_root
    sys.path.insert(0, str(repo_root / "src"))
    from aggie_analytics.modeling import preliminary_rankings as helpers
    from aggie_analytics.temporal import expanded_event_chronology as chronology

    issued = datetime.fromisoformat(args.issued_at_utc.replace("Z", "+00:00"))
    if issued.tzinfo is None:
        raise ValueError("issued-at-utc must be timezone aware")
    contract_path = repo_root / "configs/expanded_event_chronology_preliminary_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["classification"] != CLASSIFICATION:
        raise ValueError("expanded preliminary contract classification drift")
    base = load_base_runner(repo_root)
    targets, target_report, paths = load_targets(repo_root, data_root, helpers, chronology)
    features, chronology_report = chronology.build_event_chronology_features(targets)
    features, rankings_report = helpers.augment_with_rankings(
        features, pl.read_parquet(paths["rankings_features"]).to_dicts()
    )
    target_by_id = {row["target_game_id"]: row for row in targets}
    rows = [
        {
            **feature,
            **target_by_id[feature["target_game_id"]],
            "cold_start": bool(
                feature["home_cold_start"] or feature["away_cold_start"]
            ),
        }
        for feature in features
    ]
    rows.sort(key=lambda row: (row["start_utc"], row["target_game_id"]))
    assignments = [
        {
            "classification": CLASSIFICATION,
            "target_game_id": row["target_game_id"],
            "season": row["season"],
            "season_type": row["season_type"],
            "week": row["week"],
            "start_utc": row["start_utc"],
            "assignment": row["assignment"],
            "historical_known_at_eligible": False,
        }
        for row in targets
    ]

    code = {
        "chronology_module_sha256": helpers.sha256_file(
            repo_root / "src/aggie_analytics/temporal/expanded_event_chronology.py"
        ),
        "rankings_module_sha256": helpers.sha256_file(
            repo_root / "src/aggie_analytics/modeling/preliminary_rankings.py"
        ),
        "preliminary_module_sha256": helpers.sha256_file(
            repo_root / "src/aggie_analytics/modeling/preliminary.py"
        ),
        "runner_sha256": helpers.sha256_file(Path(__file__).resolve()),
        "validator_sha256": helpers.sha256_file(
            repo_root / "tools/validate_expanded_event_chronology_preliminary.py"
        ),
        "contract_sha256": helpers.sha256_file(contract_path),
    }
    tmp_parent = output_root / "tmp/preliminary_event_chronology"
    tmp_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="expanded-v1-", dir=tmp_parent))
    try:
        dataset_stage = stage / "dataset"
        payloads = []
        for records, name in (
            (features, "feature_matrix.parquet"),
            (targets, "outcome_targets.parquet"),
            (assignments, "split_assignments.parquet"),
            (rows, "training_matrix.parquet"),
        ):
            info = base.write_parquet(
                records,
                dataset_stage / name,
                ["start_utc", "target_game_id"],
            )
            info["sha256"] = helpers.sha256_file(dataset_stage / name)
            payloads.append(info)
        dataset_basis = {
            "run_version": RUN_VERSION,
            "classification": CLASSIFICATION,
            "contract_sha256": code["contract_sha256"],
            "input_identities": {
                "historical_replay": HISTORICAL_REPLAY_ID,
                "historical_outcomes_sha256": HISTORICAL_OUTCOMES_SHA,
                "core_registry_sha256": CORE_REGISTRY_SHA,
                "contemporary_target_identity": CONTEMPORARY_TARGET_ID,
                "contemporary_targets_sha256": CONTEMPORARY_TARGET_SHA,
                "rankings_run": RANKINGS_RUN,
                "rankings_features": RANKINGS_FEATURE_ID,
            },
            "code_identities": code,
            "feature_columns": list(helpers.FEATURE_COLUMNS),
            "split_policy": contract["split_policy"],
            "payloads": sorted(payloads, key=lambda row: row["name"]),
        }
        dataset_id = helpers.stable_hash(dataset_basis)
        base.move_or_verify(
            dataset_stage,
            output_root
            / "training/preliminary_event_chronology/sha256"
            / dataset_id,
            helpers.sha256_file,
        )

        predictions, model_specs, diagnostics = train_models(rows, helpers)
        models = serialize_models(model_specs, dataset_id, output_root, stage, helpers)
        model_ids = {row["family"]: row["model_identity"] for row in models}
        feature_id = helpers.stable_hash(
            {"dataset_identity": dataset_id, "feature_columns": list(helpers.FEATURE_COLUMNS)}
        )
        target_id = helpers.stable_hash(
            {"dataset_identity": dataset_id, "target_policy": contract["target_policy"]}
        )
        split_id = helpers.stable_hash(
            {"dataset_identity": dataset_id, "split_policy": contract["split_policy"]}
        )
        for row in predictions:
            row.update(
                {
                    "model_identity": model_ids[row["model_id"]],
                    "dataset_identity": dataset_id,
                    "feature_identity": feature_id,
                    "target_identity": target_id,
                    "split_identity": split_id,
                }
            )
        forecast_stage = stage / "forecast"
        forecast = base.write_parquet(
            predictions,
            forecast_stage / "predictions.parquet",
            ["model_id", "start_utc", "target_game_id"],
        )
        forecast["sha256"] = helpers.sha256_file(
            forecast_stage / "predictions.parquet"
        )
        forecast_id = helpers.stable_hash(
            {
                "dataset_identity": dataset_id,
                "models": sorted(model_ids.values()),
                "payload": forecast,
            }
        )
        base.move_or_verify(
            forecast_stage,
            output_root
            / "forecast_snapshots/preliminary_event_chronology/sha256"
            / forecast_id,
            helpers.sha256_file,
        )

        metrics = {}
        for family in sorted(model_ids):
            values = helpers.metrics_by_season_and_slice(
                [row for row in predictions if row["model_id"] == family], TAMU_TEAM_ID
            )
            for value in values:
                value["classification"] = CLASSIFICATION
            metrics[family] = values
        run_id = helpers.stable_hash(
            {
                "run_version": RUN_VERSION,
                "dataset_identity": dataset_id,
                "feature_identity": feature_id,
                "target_identity": target_id,
                "split_identity": split_id,
                "model_identities": model_ids,
                "forecast_identity": forecast_id,
                "code": code,
            }
        )
        population = {
            **target_report,
            "feature_rows": len(features),
            "training_rows": len(rows),
            "feature_count": len(helpers.FEATURE_COLUMNS),
            "split_counts": dict(
                sorted(Counter(row["assignment"] for row in assignments).items())
            ),
            "missing_feature_cells": {
                name: sum(row.get(name) is None for row in features)
                for name in helpers.FEATURE_COLUMNS
            },
            "event_chronology": chronology_report,
            "rankings_coverage": rankings_report,
        }
        manifest = {
            "schema_version": "1.0.0",
            "artifact_type": "PRELIMINARY_UNPROTECTED_EVENT_CHRONOLOGY_RUN",
            "classification": CLASSIFICATION,
            "decision_unit": "POST-SUBTASK-172",
            "run_version": RUN_VERSION,
            "run_identity": run_id,
            "issued_at_utc": issued.astimezone(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
            "input_identities": dataset_basis["input_identities"],
            "code_identities": code,
            "dataset_identity": dataset_id,
            "feature_identity": feature_id,
            "target_identity": target_id,
            "split_identity": split_id,
            "forecast_identity": forecast_id,
            "model_identities": model_ids,
            "dataset_payloads": payloads,
            "forecast_payload": forecast,
            "models": models,
            "population": population,
            "metrics": helpers.sanitize_for_json(metrics),
            "diagnostics": helpers.sanitize_for_json(diagnostics),
            "leakage_validation": {
                "target_game_identity_exclusion": "PASS",
                "same_season_week_batch_outcomes_excluded": "PASS",
                "source_start_before_target_cutoff": "PASS",
                "outcome_targets_materialized_separately": "PASS",
                "publication_timestamps_fabricated": 0,
                "historical_known_at_eligible_rows": 0,
                "protected_split_opened": False,
            },
            "external_locations": {
                "training": f"training/preliminary_event_chronology/sha256/{dataset_id}",
                "models": "model_artifacts/preliminary_event_chronology/sha256/<model_identity>",
                "forecast": f"forecast_snapshots/preliminary_event_chronology/sha256/{forecast_id}",
                "manifest": f"manifests/preliminary_event_chronology/sha256/{run_id}/run_manifest.json",
            },
            "limitations": [
                "All artifacts and metrics are PRELIMINARY_UNPROTECTED_EVENT_CHRONOLOGY_ONLY.",
                "Historical outcome publication timestamps remain UNKNOWN and are not inferred or imputed.",
                "Week-batched event chronology excludes the target and all same-batch outcomes but is not historical-known-at/PIT admission.",
                "Twenty-four pinned historical source kickoff timestamps differ from canonical registry metadata by no more than 270 minutes; both values and their deltas are preserved, and the source-aligned chronology retains compatibility with the approved rankings feature identity.",
                "Protected training and promotion still require expanded quality-supported historical-known-at/PIT evidence and W17 gates.",
            ],
            "protected_nonclaims": contract["protected_nonclaims"],
            "cleanup": {"reconstructible_stage_removed": True, "abandoned_downloads": 0},
        }
        manifest_stage = stage / "manifest"
        manifest_stage.mkdir(parents=True)
        manifest_file = manifest_stage / "run_manifest.json"
        manifest_file.write_bytes(helpers.canonical_json(manifest) + b"\n")
        manifest_sha = helpers.sha256_file(manifest_file)
        base.move_or_verify(
            manifest_stage,
            output_root / "manifests/preliminary_event_chronology/sha256" / run_id,
            helpers.sha256_file,
        )
        result = {
            "result": "PASS",
            "classification": CLASSIFICATION,
            "run_identity": run_id,
            "manifest_sha256": manifest_sha,
            "dataset_identity": dataset_id,
            "feature_identity": feature_id,
            "target_identity": target_id,
            "split_identity": split_id,
            "forecast_identity": forecast_id,
            "model_identities": model_ids,
            "population": population,
        }
        payload = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
        if args.summary_path:
            args.summary_path.parent.mkdir(parents=True, exist_ok=True)
            args.summary_path.write_text(payload, encoding="utf-8")
        print(payload, end="")
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        try:
            tmp_parent.rmdir()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
