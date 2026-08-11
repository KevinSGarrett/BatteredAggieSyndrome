from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
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


REPLAY_IDENTITY = "cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7"
REPLAY_MANIFEST_SHA256 = "7383dd69d4165d0e18f89ad690d155305e062d7f81ad9b0087233a90a044a888"
CORE_REGISTRY_IDENTITY = "10d0bd0adcef3fc1ba22fb9932f353cc59b0e5d4508c7891a1472d0221a454ac"
CORE_GAMES_SHA256 = "1d8b52e0ed409b9d7648d2a8fa89cf1bb0be1e037d5aea92642cf555378ae06a"
RUN_VERSION = "preliminary-unprotected-team-outcome-baseline-v1"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--issued-at-utc", required=True)
    result.add_argument("--summary-path", type=Path)
    return result


def write_parquet(rows: Sequence[Mapping[str, Any]], path: Path, sort_by: Sequence[str]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pl.from_dicts(list(rows), infer_schema_length=None)
    if sort_by:
        frame = frame.sort(list(sort_by))
    frame.write_parquet(path, compression="zstd", compression_level=9, statistics=True)
    return {"name": path.name, "rows": frame.height, "bytes": path.stat().st_size}


def move_or_verify(stage: Path, destination: Path, sha256_file) -> None:
    if destination.exists():
        staged = {item.relative_to(stage): sha256_file(item) for item in stage.rglob("*") if item.is_file()}
        existing = {
            item.relative_to(destination): sha256_file(item)
            for item in destination.rglob("*")
            if item.is_file()
        }
        if staged != existing:
            raise FileExistsError(f"immutable destination differs: {destination}")
        shutil.rmtree(stage)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(stage), str(destination))


def load_inputs(repo_root: Path, data_root: Path, helpers: Any) -> dict[str, Any]:
    feature_root = data_root / "features/historical_known_at/sha256" / REPLAY_IDENTITY
    state_root = data_root / "pit_state/historical_known_at/sha256" / REPLAY_IDENTITY
    replay_manifest = data_root / "manifests/historical_known_at/sha256" / REPLAY_IDENTITY / "known_at_replay_manifest.json"
    core_registry = data_root / "canonical/BAT-387/sha256" / CORE_REGISTRY_IDENTITY / "canonical_core_registry.csv"
    core_games = data_root / "canonical/SRC-002/core/games" / f"sha256_{CORE_GAMES_SHA256}.jsonl"
    paths = {
        "pregame_prior_rows": feature_root / "pregame_prior_rows.parquet",
        "target_game_cutoffs": feature_root / "target_game_cutoffs.parquet",
        "accepted_game_outcomes": state_root / "accepted_game_outcomes.parquet",
        "replay_manifest": replay_manifest,
        "core_registry": core_registry,
        "core_games": core_games,
    }
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned {name}: {path}")
    checks = {
        "replay_manifest": REPLAY_MANIFEST_SHA256,
        "core_registry": CORE_REGISTRY_IDENTITY,
        "core_games": CORE_GAMES_SHA256,
    }
    for name, expected in checks.items():
        actual = helpers.sha256_file(paths[name])
        if actual != expected:
            raise ValueError(f"pinned {name} hash drift: expected {expected}, found {actual}")
    manifest = json.loads(replay_manifest.read_text(encoding="utf-8"))
    if manifest.get("dataset_identity") != REPLAY_IDENTITY:
        raise ValueError("replay dataset identity drift")
    return {"paths": paths, "replay_manifest": manifest}


def materialize_dataset(inputs: dict[str, Any], helpers: Any) -> tuple[list[dict], list[dict], list[dict], str | None, dict]:
    paths = inputs["paths"]
    targets = pl.read_parquet(paths["target_game_cutoffs"]).sort(["start_utc", "game_id"]).to_dicts()
    priors = pl.read_parquet(paths["pregame_prior_rows"]).sort(["target_start_utc", "target_game_id", "team_id"]).to_dicts()
    by_game: dict[str, list[dict]] = defaultdict(list)
    for row in priors:
        by_game[str(row["target_game_id"])].append(row)
    features: list[dict] = []
    for target in targets:
        rows = by_game[str(target["game_id"])]
        if len(rows) != 2:
            raise ValueError(f"expected two prior rows for {target['game_id']}, found {len(rows)}")
        by_team = {row["team_id"]: row for row in rows}
        features.append(
            helpers.feature_row_from_team_priors(
                target,
                by_team[target["home_team_id"]],
                by_team[target["away_team_id"]],
            )
        )

    accepted = pl.read_parquet(
        paths["accepted_game_outcomes"], columns=["observation_id", "canonical_game_id"]
    )
    observation_to_game = {
        row["observation_id"]: row["canonical_game_id"] for row in accepted.to_dicts()
    }
    for feature in features:
        prior_rows = by_game[feature["target_game_id"]]
        evidence_ids = {
            observation_id
            for prior in prior_rows
            for observation_id in prior["eligible_observation_ids"]
        }
        feature["target_outcome_in_feature_evidence"] = any(
            observation_to_game.get(observation_id) == feature["target_game_id"]
            for observation_id in evidence_ids
        )

    core = pl.read_csv(paths["core_registry"], infer_schema_length=10000)
    games = core.filter((pl.col("entity_type") == "game") & (pl.col("record_type") == "ENTITY"))
    game_source = {row["canonical_id"]: str(row["source_entity_key"]) for row in games.to_dicts()}
    team_rows = core.filter((pl.col("entity_type") == "team") & (pl.col("record_type") == "ENTITY"))
    source_to_team = {str(row["source_entity_key"]): row["canonical_id"] for row in team_rows.to_dicts()}

    normalized_games: dict[str, dict] = {}
    with paths["core_games"].open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            normalized_games[str(row["source_game_id"])] = row
    outcome_targets: list[dict] = []
    assignments: list[dict] = []
    exclusions: list[dict] = []
    split = helpers.SplitPolicy()
    for target in targets:
        game_id = str(target["game_id"])
        source_game_id = game_source.get(game_id)
        normalized = normalized_games.get(str(source_game_id)) if source_game_id else None
        assignment = {
            "classification": helpers.CLASSIFICATION,
            "target_game_id": game_id,
            "season": int(target["season"]),
            "season_type": target["season_type"],
            "week": int(target["week"]),
            "start_utc": target["start_utc"],
            "assignment": split.assignment(int(target["season"])),
            "label_available": bool(normalized and normalized.get("completed")),
        }
        assignments.append(assignment)
        if not normalized or not normalized.get("completed"):
            exclusions.append(
                {
                    **assignment,
                    "reason": "OFFICIAL_COMPLETED_OUTCOME_NOT_PRESENT_IN_PINNED_CONTEMPORARY_CANONICAL_GAMES",
                    "disposition": "EXCLUDED_TARGET_NOT_FABRICATED",
                }
            )
            continue
        if normalized["season"] != target["season"] or normalized["week"] != target["week"]:
            raise ValueError(f"core registry / outcome season-week mismatch for {game_id}")
        home_points = int(normalized["home_points"])
        away_points = int(normalized["away_points"])
        home_win = 1.0 if home_points > away_points else 0.0 if home_points < away_points else 0.5
        outcome_targets.append(
            {
                "classification": helpers.CLASSIFICATION,
                "target_game_id": game_id,
                "source_game_id": str(source_game_id),
                "season": int(target["season"]),
                "season_type": target["season_type"],
                "week": int(target["week"]),
                "start_utc": target["start_utc"],
                "home_team_id": target["home_team_id"],
                "away_team_id": target["away_team_id"],
                "home_points": home_points,
                "away_points": away_points,
                "margin": home_points - away_points,
                "total": home_points + away_points,
                "home_win": home_win,
                "target_policy_version": "completed-official-outcome-target-v1",
                "target_source_sha256": CORE_GAMES_SHA256,
                "target_source_record_sha256": helpers.stable_hash(normalized),
                "assignment": assignment["assignment"],
            }
        )
    split_validation = helpers.validate_chronology(features, outcome_targets, split)

    tamu_source_ids: set[str] = set()
    for row in normalized_games.values():
        if row.get("home_team_label") == "Texas A&M":
            tamu_source_ids.add(str(row["home_source_team_id"]))
        if row.get("away_team_label") == "Texas A&M":
            tamu_source_ids.add(str(row["away_source_team_id"]))
    tamu_team_id = None
    if len(tamu_source_ids) == 1:
        tamu_team_id = source_to_team.get(next(iter(tamu_source_ids)))
    report = {
        "features": len(features),
        "targets": len(outcome_targets),
        "assignments": len(assignments),
        "exclusions": exclusions,
        "seasons": sorted({int(row["season"]) for row in features}),
        "split_counts": dict(sorted(Counter(row["assignment"] for row in assignments).items())),
        "label_counts_by_season": dict(sorted(Counter(str(row["season"]) for row in outcome_targets).items())),
        "cold_start_games": sum(bool(row["home_cold_start"] or row["away_cold_start"]) for row in features),
        "missing_feature_cells": {
            name: sum(row.get(name) is None for row in features) for name in helpers.FEATURE_COLUMNS
        },
        "split_validation": split_validation,
        "tamu_team_id": tamu_team_id,
    }
    return features, outcome_targets, assignments, tamu_team_id, report


def joined_rows(features: Sequence[dict], targets: Sequence[dict]) -> list[dict]:
    target_by_id = {row["target_game_id"]: row for row in targets}
    result = []
    for feature in features:
        target = target_by_id.get(feature["target_game_id"])
        if target is not None:
            result.append({**feature, **target, "cold_start": bool(feature["home_cold_start"] or feature["away_cold_start"])})
    return sorted(result, key=lambda row: (row["start_utc"], row["target_game_id"]))


def common_prediction(row: Mapping[str, Any], model_id: str, probability: float) -> dict[str, Any]:
    return {
        "classification": "PRELIMINARY_UNPROTECTED",
        "model_id": model_id,
        "target_game_id": row["target_game_id"],
        "season": int(row["season"]),
        "week": int(row["week"]),
        "start_utc": row["start_utc"],
        "assignment": row["assignment"],
        "home_team_id": row["home_team_id"],
        "away_team_id": row["away_team_id"],
        "neutral_site": bool(row["neutral_site"]),
        "cold_start": bool(row["cold_start"]),
        "home_win": float(row["home_win"]),
        "home_points": int(row["home_points"]),
        "away_points": int(row["away_points"]),
        "margin": int(row["margin"]),
        "total": int(row["total"]),
        "home_win_probability": float(probability),
        "calibrated_home_win_probability": float(probability),
    }


def add_calibration(predictions: list[dict], helpers: Any) -> Any:
    tune = [row for row in predictions if int(row["season"]) == 2024]
    calibrator = helpers.fit_logistic_calibrator(
        [row["home_win"] for row in tune], [row["home_win_probability"] for row in tune]
    )
    evaluation = [row for row in predictions if int(row["season"]) == 2025]
    if evaluation:
        calibrated = helpers.apply_logistic_calibrator(
            calibrator, [row["home_win_probability"] for row in evaluation]
        )
        for row, value in zip(evaluation, calibrated):
            row["calibrated_home_win_probability"] = float(value)
    return calibrator


def train_models(rows: Sequence[dict], accepted_outcomes_path: Path, helpers: Any) -> tuple[list[dict], list[dict], dict]:
    source = pl.read_parquet(accepted_outcomes_path).sort(["game_start_utc", "canonical_game_id"]).to_dicts()
    source_games = []
    source_home_wins = []
    for item in source:
        home_points, away_points = int(item["home_points"]), int(item["away_points"])
        home_win = 1.0 if home_points > away_points else 0.0 if home_points < away_points else 0.5
        source_home_wins.append(home_win)
        source_games.append(
            {
                "target_game_id": item["canonical_game_id"],
                "start_utc": item["game_start_utc"],
                "home_team_id": item["home_team_id"],
                "away_team_id": item["away_team_id"],
                "neutral_site": False,
                "home_win": home_win,
            }
        )
    predictions: list[dict] = []
    artifacts: list[dict] = []
    diagnostics: dict[str, Any] = {}

    naive_p = float(np.mean(source_home_wins))
    naive = [common_prediction(row, "naive_historical_average", naive_p) for row in rows]
    naive_cal = add_calibration(naive, helpers)
    predictions.extend(naive)
    artifacts.append({"family": "naive_historical_average", "state": {"probability": naive_p, "calibrator": naive_cal}, "fit_seasons": list(range(2010, 2023))})

    fit_2023 = [row for row in rows if row["season"] == 2023]
    home_non_neutral = [row["home_win"] for row in fit_2023 if not row["neutral_site"]]
    home_neutral = [row["home_win"] for row in fit_2023 if row["neutral_site"]]
    home_state = {"nonneutral_probability": float(np.mean(home_non_neutral)), "neutral_probability": float(np.mean(home_neutral))}
    home_preds = [
        common_prediction(row, "home_field_empirical", home_state["neutral_probability"] if row["neutral_site"] else home_state["nonneutral_probability"])
        for row in rows
        if row["season"] in (2024, 2025)
    ]
    home_cal = add_calibration(home_preds, helpers)
    predictions.extend(home_preds)
    artifacts.append({"family": "home_field_empirical", "state": {**home_state, "calibrator": home_cal}, "fit_seasons": [2023]})

    initial_ratings: dict[str, float] = {}
    _, initial_ratings = helpers.elo_predict_and_update(source_games, initial_ratings, k_factor=20.0, home_advantage=55.0)
    elo_grid = []
    for k_factor in (10.0, 20.0, 30.0, 40.0):
        for home_advantage in (0.0, 35.0, 55.0, 75.0, 95.0):
            dev_predictions, _ = helpers.elo_predict_and_update(fit_2023, initial_ratings, k_factor=k_factor, home_advantage=home_advantage)
            score = helpers.brier_score([row["home_win"] for row in dev_predictions], [row["home_win_probability"] for row in dev_predictions])
            elo_grid.append((score, k_factor, home_advantage))
    _, elo_k, elo_home = min(elo_grid)
    elo_development_rows = [row for row in rows if row["season"] in (2023, 2024)]
    elo_evaluation_rows = [row for row in rows if row["season"] == 2025]
    elo_development_raw, elo_ratings_at_evaluation_start = helpers.elo_predict_and_update(
        elo_development_rows,
        initial_ratings,
        k_factor=elo_k,
        home_advantage=elo_home,
    )
    elo_evaluation_raw, _ = helpers.elo_predict_and_update(
        elo_evaluation_rows,
        elo_ratings_at_evaluation_start,
        k_factor=elo_k,
        home_advantage=elo_home,
    )
    elo_raw = elo_development_raw + elo_evaluation_raw
    elo_predictions = [common_prediction(row, "elo_rating", row["home_win_probability"]) for row in elo_raw]
    elo_cal = add_calibration(elo_predictions, helpers)
    predictions.extend(elo_predictions)
    artifacts.append(
        {
            "family": "elo_rating",
            "state": {
                "k_factor": elo_k,
                "home_advantage": elo_home,
                "ratings": elo_ratings_at_evaluation_start,
                "ratings_known_through_season": 2024,
                "evaluation_replay_policy": "UPDATE_ONLY_AFTER_EACH_CHRONOLOGICALLY_COMPLETED_2025_GAME",
                "calibrator": elo_cal,
            },
            "fit_seasons": list(range(2010, 2025)),
        }
    )
    diagnostics["elo_development_grid"] = [{"brier": value, "k_factor": k, "home_advantage": h} for value, k, h in sorted(elo_grid)]
    diagnostics["elo_artifact_state_known_through_season"] = 2024

    train = [row for row in rows if row["season"] == 2023]
    tune = [row for row in rows if row["season"] == 2024]
    evaluation = [row for row in rows if row["season"] == 2025]
    imputer_2023 = helpers.MedianImputer.fit(train, helpers.FEATURE_COLUMNS, [2023])
    x_train = imputer_2023.transform(train)
    x_tune = imputer_2023.transform(tune)
    binary_train = np.asarray([row["home_win"] in (0.0, 1.0) for row in train])
    y_train_binary = np.asarray([int(row["home_win"]) for row in train])[binary_train]

    logistic_grid = []
    for c_value in (0.1, 1.0, 10.0):
        model = LogisticRegression(C=c_value, max_iter=2000, solver="lbfgs", random_state=0)
        model.fit(x_train[binary_train], y_train_binary)
        probability = model.predict_proba(x_tune)[:, 1]
        score = helpers.brier_score([row["home_win"] for row in tune], probability)
        logistic_grid.append((score, c_value))
    _, logistic_c = min(logistic_grid)
    combined = train + tune
    imputer_combined = helpers.MedianImputer.fit(combined, helpers.FEATURE_COLUMNS, [2023, 2024])
    x_combined = imputer_combined.transform(combined)
    x_evaluation = imputer_combined.transform(evaluation)
    combined_binary = np.asarray([row["home_win"] in (0.0, 1.0) for row in combined])
    logistic = LogisticRegression(C=logistic_c, max_iter=2000, solver="lbfgs", random_state=0)
    logistic.fit(x_combined[combined_binary], np.asarray([int(row["home_win"]) for row in combined])[combined_binary])
    tune_logistic = LogisticRegression(C=logistic_c, max_iter=2000, solver="lbfgs", random_state=0)
    tune_logistic.fit(x_train[binary_train], y_train_binary)
    logistic_predictions = [common_prediction(row, "regularized_logistic", value) for row, value in zip(tune, tune_logistic.predict_proba(x_tune)[:, 1])]
    logistic_predictions += [common_prediction(row, "regularized_logistic", value) for row, value in zip(evaluation, logistic.predict_proba(x_evaluation)[:, 1])]
    logistic_cal = add_calibration(logistic_predictions, helpers)
    predictions.extend(logistic_predictions)
    artifacts.append({"family": "regularized_logistic", "state": {"model": logistic, "imputer": imputer_combined, "calibrator": logistic_cal, "selected_c": logistic_c}, "fit_seasons": [2023, 2024]})
    diagnostics["logistic_tuning"] = [{"brier": score, "c": c_value} for score, c_value in sorted(logistic_grid)]

    ridge_grid = []
    y_margin_train = np.asarray([row["margin"] for row in train], dtype=float)
    for alpha in (1.0, 10.0, 100.0):
        model = Ridge(alpha=alpha)
        model.fit(x_train, y_margin_train)
        predicted = model.predict(x_tune)
        score = float(np.mean(np.abs(predicted - np.asarray([row["margin"] for row in tune]))))
        ridge_grid.append((score, alpha))
    _, ridge_alpha = min(ridge_grid)
    ridge_tune = Ridge(alpha=ridge_alpha).fit(x_train, y_margin_train)
    ridge = Ridge(alpha=ridge_alpha).fit(x_combined, np.asarray([row["margin"] for row in combined], dtype=float))
    ridge_predictions: list[dict] = []
    for part, values in ((tune, ridge_tune.predict(x_tune)), (evaluation, ridge.predict(x_evaluation))):
        for row, margin in zip(part, values):
            probability = 1.0 / (1.0 + math.exp(-float(margin) / 14.0))
            item = common_prediction(row, "regularized_linear_margin", probability)
            item["predicted_margin"] = float(margin)
            ridge_predictions.append(item)
    ridge_cal = add_calibration(ridge_predictions, helpers)
    predictions.extend(ridge_predictions)
    artifacts.append({"family": "regularized_linear_margin", "state": {"model": ridge, "imputer": imputer_combined, "probability_scale": 14.0, "calibrator": ridge_cal, "selected_alpha": ridge_alpha}, "fit_seasons": [2023, 2024]})
    diagnostics["ridge_tuning"] = [{"margin_mae": score, "alpha": alpha} for score, alpha in sorted(ridge_grid)]

    poisson_grid = []
    for alpha in (0.1, 1.0, 10.0):
        home_model = PoissonRegressor(alpha=alpha, max_iter=1000).fit(x_train, np.asarray([row["home_points"] for row in train]))
        away_model = PoissonRegressor(alpha=alpha, max_iter=1000).fit(x_train, np.asarray([row["away_points"] for row in train]))
        home_mu, away_mu = home_model.predict(x_tune), away_model.predict(x_tune)
        score = helpers.poisson_nll([row["home_points"] for row in tune], home_mu) + helpers.poisson_nll([row["away_points"] for row in tune], away_mu)
        poisson_grid.append((score, alpha))
    _, poisson_alpha = min(poisson_grid)
    poisson_home_tune = PoissonRegressor(alpha=poisson_alpha, max_iter=1000).fit(x_train, np.asarray([row["home_points"] for row in train]))
    poisson_away_tune = PoissonRegressor(alpha=poisson_alpha, max_iter=1000).fit(x_train, np.asarray([row["away_points"] for row in train]))
    poisson_home = PoissonRegressor(alpha=poisson_alpha, max_iter=1000).fit(x_combined, np.asarray([row["home_points"] for row in combined]))
    poisson_away = PoissonRegressor(alpha=poisson_alpha, max_iter=1000).fit(x_combined, np.asarray([row["away_points"] for row in combined]))
    poisson_predictions: list[dict] = []
    for part, home_mu, away_mu in (
        (tune, poisson_home_tune.predict(x_tune), poisson_away_tune.predict(x_tune)),
        (evaluation, poisson_home.predict(x_evaluation), poisson_away.predict(x_evaluation)),
    ):
        for row, home_value, away_value in zip(part, home_mu, away_mu):
            item = common_prediction(row, "poisson_skellam_score_distribution", helpers.skellam_home_win_probability(home_value, away_value))
            item.update({"predicted_home_points": float(home_value), "predicted_away_points": float(away_value), "predicted_margin": float(home_value - away_value)})
            poisson_predictions.append(item)
    poisson_cal = add_calibration(poisson_predictions, helpers)
    predictions.extend(poisson_predictions)
    artifacts.append({"family": "poisson_skellam_score_distribution", "state": {"home_model": poisson_home, "away_model": poisson_away, "imputer": imputer_combined, "calibrator": poisson_cal, "selected_alpha": poisson_alpha}, "fit_seasons": [2023, 2024]})
    diagnostics["poisson_tuning"] = [{"joint_nll": score, "alpha": alpha} for score, alpha in sorted(poisson_grid)]

    simple_families = {item["family"] for item in artifacts}
    expected_simple = {"naive_historical_average", "home_field_empirical", "elo_rating", "regularized_logistic", "regularized_linear_margin", "poisson_skellam_score_distribution"}
    if simple_families != expected_simple or any(not np.isfinite(row["home_win_probability"]) for row in predictions):
        raise ValueError("simple baseline gate failed")
    simple_roundtrip = {}
    for artifact in artifacts:
        buffer = io.BytesIO()
        joblib.dump(artifact, buffer, compress=0, protocol=5)
        buffer.seek(0)
        loaded = joblib.load(buffer)
        passed = loaded["family"] == artifact["family"] and loaded["fit_seasons"] == artifact["fit_seasons"]
        simple_roundtrip[artifact["family"]] = passed
    if not all(simple_roundtrip.values()):
        raise ValueError("simple baseline serialization replay failed before tree admission")
    diagnostics["simple_pipeline_gate"] = "PASS_BEFORE_TREE_BOOSTING"
    diagnostics["simple_serialization_replay_before_tree"] = simple_roundtrip

    tree_grid = []
    for leaf_nodes in (7, 15):
        model = HistGradientBoostingClassifier(max_leaf_nodes=leaf_nodes, l2_regularization=10.0, random_state=0)
        model.fit(x_train[binary_train], y_train_binary)
        probability = model.predict_proba(x_tune)[:, 1]
        tree_grid.append((helpers.brier_score([row["home_win"] for row in tune], probability), leaf_nodes))
    _, selected_leaves = min(tree_grid)
    tree_tune = HistGradientBoostingClassifier(max_leaf_nodes=selected_leaves, l2_regularization=10.0, random_state=0).fit(x_train[binary_train], y_train_binary)
    tree = HistGradientBoostingClassifier(max_leaf_nodes=selected_leaves, l2_regularization=10.0, random_state=0).fit(x_combined[combined_binary], np.asarray([int(row["home_win"]) for row in combined])[combined_binary])
    tree_predictions = [common_prediction(row, "hist_gradient_boosting", value) for row, value in zip(tune, tree_tune.predict_proba(x_tune)[:, 1])]
    tree_predictions += [common_prediction(row, "hist_gradient_boosting", value) for row, value in zip(evaluation, tree.predict_proba(x_evaluation)[:, 1])]
    tree_cal = add_calibration(tree_predictions, helpers)
    predictions.extend(tree_predictions)
    artifacts.append({"family": "hist_gradient_boosting", "state": {"model": tree, "imputer": imputer_combined, "calibrator": tree_cal, "selected_max_leaf_nodes": selected_leaves}, "fit_seasons": [2023, 2024]})
    diagnostics["tree_tuning"] = [{"brier": score, "max_leaf_nodes": leaves} for score, leaves in sorted(tree_grid)]
    return predictions, artifacts, diagnostics


def serialize_models(model_specs: Sequence[dict], dataset_identity: str, data_root: Path, stage_root: Path, helpers: Any) -> list[dict]:
    records = []
    for spec in model_specs:
        family = spec["family"]
        stage = stage_root / "models" / family
        stage.mkdir(parents=True, exist_ok=True)
        artifact_path = stage / "model.joblib"
        payload = {
            "classification": helpers.CLASSIFICATION,
            "run_version": RUN_VERSION,
            "dataset_identity": dataset_identity,
            **spec,
        }
        joblib.dump(payload, artifact_path, compress=3, protocol=5)
        artifact_sha = helpers.sha256_file(artifact_path)
        loaded = joblib.load(artifact_path)
        if loaded["classification"] != helpers.CLASSIFICATION or loaded["family"] != family:
            raise ValueError(f"artifact replay identity failure: {family}")
        model_identity = helpers.stable_hash(
            {
                "classification": helpers.CLASSIFICATION,
                "family": family,
                "dataset_identity": dataset_identity,
                "fit_seasons": spec["fit_seasons"],
                "artifact_sha256": artifact_sha,
            }
        )
        destination = data_root / "model_artifacts/preliminary_unprotected/sha256" / model_identity
        move_or_verify(stage, destination, helpers.sha256_file)
        records.append(
            {
                "classification": helpers.CLASSIFICATION,
                "family": family,
                "model_identity": model_identity,
                "dataset_identity": dataset_identity,
                "fit_seasons": spec["fit_seasons"],
                "artifact_path": f"model_artifacts/preliminary_unprotected/sha256/{model_identity}/model.joblib",
                "artifact_sha256": artifact_sha,
                "serialization_replay": "PASS",
            }
        )
    return records


def main() -> int:
    args = parser().parse_args()
    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    sys.path.insert(0, str(repo_root / "src"))
    from aggie_analytics.modeling import preliminary as helpers

    issued = datetime.fromisoformat(args.issued_at_utc.replace("Z", "+00:00"))
    if issued.tzinfo is None:
        raise ValueError("issued-at-utc must include UTC offset")
    contract_path = repo_root / "configs/preliminary_unprotected_baseline_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["classification"] != helpers.CLASSIFICATION:
        raise ValueError("contract classification drift")
    inputs = load_inputs(repo_root, data_root, helpers)
    features, targets, assignments, tamu_team_id, population = materialize_dataset(inputs, helpers)
    rows = joined_rows(features, targets)
    code_identities = {
        "preliminary_module_sha256": helpers.sha256_file(
            repo_root / "src/aggie_analytics/modeling/preliminary.py"
        ),
        "runner_sha256": helpers.sha256_file(Path(__file__).resolve()),
        "validator_sha256": helpers.sha256_file(
            repo_root / "tools/validate_preliminary_unprotected_baselines.py"
        ),
    }

    tmp_parent = data_root / "tmp/preliminary_unprotected"
    tmp_parent.mkdir(parents=True, exist_ok=True)
    stage_root = Path(tempfile.mkdtemp(prefix="baseline-v1-", dir=tmp_parent))
    try:
        dataset_stage = stage_root / "dataset"
        dataset_stage.mkdir(parents=True)
        payloads = []
        for records, name, sort_keys in (
            (features, "feature_matrix.parquet", ["start_utc", "target_game_id"]),
            (targets, "outcome_targets.parquet", ["start_utc", "target_game_id"]),
            (assignments, "split_assignments.parquet", ["start_utc", "target_game_id"]),
            (rows, "training_matrix.parquet", ["start_utc", "target_game_id"]),
        ):
            info = write_parquet(records, dataset_stage / name, sort_keys)
            info["sha256"] = helpers.sha256_file(dataset_stage / name)
            payloads.append(info)
        dataset_identity_basis = {
            "run_version": RUN_VERSION,
            "classification": helpers.CLASSIFICATION,
            "contract_sha256": helpers.sha256_file(contract_path),
            "input_identities": {
                "replay_dataset": REPLAY_IDENTITY,
                "replay_manifest": REPLAY_MANIFEST_SHA256,
                "core_registry": CORE_REGISTRY_IDENTITY,
                "core_games": CORE_GAMES_SHA256,
            },
            "code_identities": code_identities,
            "feature_columns": list(helpers.FEATURE_COLUMNS),
            "target_policy": contract["target_policy"],
            "split_policy": contract["split_policy"],
            "payloads": sorted(payloads, key=lambda item: item["name"]),
        }
        dataset_identity = helpers.stable_hash(dataset_identity_basis)
        dataset_destination = data_root / "training/preliminary_unprotected/sha256" / dataset_identity
        move_or_verify(dataset_stage, dataset_destination, helpers.sha256_file)

        predictions, model_specs, diagnostics = train_models(rows, inputs["paths"]["accepted_game_outcomes"], helpers)
        model_records = serialize_models(model_specs, dataset_identity, data_root, stage_root, helpers)
        model_id_by_family = {row["family"]: row["model_identity"] for row in model_records}
        for row in predictions:
            row["model_identity"] = model_id_by_family[row["model_id"]]
            row["dataset_identity"] = dataset_identity
            row["feature_identity"] = helpers.stable_hash({"dataset_identity": dataset_identity, "feature_columns": list(helpers.FEATURE_COLUMNS)})
            row["target_identity"] = helpers.stable_hash({"dataset_identity": dataset_identity, "target_policy": contract["target_policy"]})
            row["split_identity"] = helpers.stable_hash({"dataset_identity": dataset_identity, "split_policy": contract["split_policy"]})

        forecast_stage = stage_root / "forecast"
        forecast_stage.mkdir(parents=True)
        forecast_info = write_parquet(predictions, forecast_stage / "predictions.parquet", ["model_id", "start_utc", "target_game_id"])
        forecast_info["sha256"] = helpers.sha256_file(forecast_stage / "predictions.parquet")
        forecast_identity = helpers.stable_hash(
            {
                "classification": helpers.CLASSIFICATION,
                "dataset_identity": dataset_identity,
                "models": sorted(model_id_by_family.values()),
                "payload": forecast_info,
            }
        )
        forecast_destination = data_root / "forecast_snapshots/preliminary_unprotected/sha256" / forecast_identity
        move_or_verify(forecast_stage, forecast_destination, helpers.sha256_file)

        metrics = {}
        for family in sorted(model_id_by_family):
            family_rows = [row for row in predictions if row["model_id"] == family]
            metrics[family] = helpers.metrics_by_season_and_slice(family_rows, tamu_team_id)
        feature_identity = helpers.stable_hash({"dataset_identity": dataset_identity, "feature_columns": list(helpers.FEATURE_COLUMNS)})
        target_identity = helpers.stable_hash({"dataset_identity": dataset_identity, "target_policy": contract["target_policy"]})
        split_identity = helpers.stable_hash({"dataset_identity": dataset_identity, "split_policy": contract["split_policy"]})
        leakage = population["split_validation"]
        leakage.update(
            {
                "outcome_targets_materialized_separately": "PASS",
                "training_feature_source_seasons_max": 2022,
                "target_seasons_min": 2023,
                "model_fit_precedes_2025_evaluation": "PASS",
                "imputation_fit_seasons": [2023, 2024],
                "protected_split_opened": False,
            }
        )
        run_identity = helpers.stable_hash(
            {
                "run_version": RUN_VERSION,
                "classification": helpers.CLASSIFICATION,
                "dataset_identity": dataset_identity,
                "feature_identity": feature_identity,
                "target_identity": target_identity,
                "split_identity": split_identity,
                "model_identities": model_id_by_family,
                "forecast_identity": forecast_identity,
                "code_identities": code_identities,
            }
        )
        manifest = {
            "schema_version": "1.0.0",
            "artifact_type": "PRELIMINARY_UNPROTECTED_BASELINE_RUN",
            "classification": helpers.CLASSIFICATION,
            "run_version": RUN_VERSION,
            "run_identity": run_identity,
            "issued_at_utc": issued.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "decision_unit": "POST-TASK-PRELIMINARY-BASELINES-001",
            "input_identities": dataset_identity_basis["input_identities"],
            "code_identities": code_identities,
            "dataset_identity": dataset_identity,
            "feature_identity": feature_identity,
            "target_identity": target_identity,
            "split_identity": split_identity,
            "model_identities": model_id_by_family,
            "forecast_identity": forecast_identity,
            "population": population,
            "dataset_payloads": payloads,
            "models": model_records,
            "forecast_payload": forecast_info,
            "metrics": helpers.sanitize_for_json(metrics),
            "diagnostics": helpers.sanitize_for_json(diagnostics),
            "leakage_validation": leakage,
            "external_locations": {
                "training": f"training/preliminary_unprotected/sha256/{dataset_identity}",
                "models": "model_artifacts/preliminary_unprotected/sha256/<model_identity>",
                "forecast": f"forecast_snapshots/preliminary_unprotected/sha256/{forecast_identity}",
                "manifest": f"manifests/preliminary_unprotected/sha256/{run_identity}/run_manifest.json",
            },
            "limitations": [
                "All artifacts and metrics are PRELIMINARY_UNPROTECTED.",
                "The only admitted feature domain is the BAT-398 scoped 2010-2022 team-outcome context.",
                "One target game lacks an eligible completed outcome and is excluded without fabrication.",
                "The 2023 season is development fit; 2024 is development tuning; 2025 evaluation is unprotected.",
                "Calibration is fit on 2024 development tuning predictions and applied only to 2025 unprotected evaluation.",
                "No final historical readiness, production promotion, protected performance, A&M lift, BAS, or Aggie Excess result is established."
            ],
            "protected_nonclaims": {
                "final_historical_population_ready": False,
                "gap_002_resolved": False,
                "production_model_ready": False,
                "champion_promoted": False,
                "protected_performance_claimed": False,
                "tamu_specialization_lift_claimed": False,
                "bas_or_aggie_excess_claimed": False,
            },
            "cleanup": {"reconstructible_stage_removed": True, "abandoned_downloads": 0},
        }
        manifest_stage = stage_root / "manifest"
        manifest_stage.mkdir(parents=True)
        manifest_path = manifest_stage / "run_manifest.json"
        manifest_path.write_bytes(helpers.canonical_json(manifest) + b"\n")
        manifest_sha = helpers.sha256_file(manifest_path)
        manifest_destination = data_root / "manifests/preliminary_unprotected/sha256" / run_identity
        move_or_verify(manifest_stage, manifest_destination, helpers.sha256_file)
        output = {
            "classification": helpers.CLASSIFICATION,
            "run_identity": run_identity,
            "manifest_sha256": manifest_sha,
            "manifest_path": str(manifest_destination / "run_manifest.json"),
            "dataset_identity": dataset_identity,
            "feature_identity": feature_identity,
            "target_identity": target_identity,
            "split_identity": split_identity,
            "model_identities": model_id_by_family,
            "forecast_identity": forecast_identity,
            "population": population,
            "leakage_validation": leakage,
            "metrics": helpers.sanitize_for_json(metrics),
        }
        if args.summary_path:
            summary_path = args.summary_path.resolve()
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_bytes(helpers.canonical_json(output) + b"\n")
        print(
            json.dumps(
                {
                    "classification": helpers.CLASSIFICATION,
                    "run_identity": run_identity,
                    "manifest_sha256": manifest_sha,
                    "dataset_identity": dataset_identity,
                    "forecast_identity": forecast_identity,
                    "summary_path": str(args.summary_path.resolve()) if args.summary_path else None,
                },
                sort_keys=True,
            )
        )
    finally:
        if stage_root.exists():
            shutil.rmtree(stage_root)
        try:
            tmp_parent.rmdir()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
