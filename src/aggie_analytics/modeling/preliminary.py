from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


CLASSIFICATION = "PRELIMINARY_UNPROTECTED"
FEATURE_COLUMNS = (
    "prior_win_rate_diff",
    "prior_points_for_mean_diff",
    "prior_points_against_mean_diff",
    "log1p_prior_games_diff",
    "home_field",
    "neutral_site",
    "home_cold_start",
    "away_cold_start",
)


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def stable_hash(value: object) -> str:
    return sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_probability(value: float) -> float:
    return float(min(max(value, 1e-9), 1.0 - 1e-9))


def brier_score(labels: Sequence[float], probabilities: Sequence[float]) -> float:
    y = np.asarray(labels, dtype=float)
    p = np.asarray(probabilities, dtype=float)
    if y.size == 0 or y.shape != p.shape:
        raise ValueError("nonempty equal-length labels and probabilities required")
    return float(np.mean((p - y) ** 2))


def log_loss(labels: Sequence[float], probabilities: Sequence[float]) -> float:
    y = np.asarray(labels, dtype=float)
    p = np.clip(np.asarray(probabilities, dtype=float), 1e-9, 1.0 - 1e-9)
    if y.size == 0 or y.shape != p.shape:
        raise ValueError("nonempty equal-length labels and probabilities required")
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def expected_calibration_error(
    labels: Sequence[float], probabilities: Sequence[float], bins: int = 10
) -> float:
    y = np.asarray(labels, dtype=float)
    p = np.asarray(probabilities, dtype=float)
    if bins < 2 or y.size == 0 or y.shape != p.shape:
        raise ValueError("valid bins and nonempty equal-length inputs required")
    total = float(y.size)
    result = 0.0
    edges = np.linspace(0.0, 1.0, bins + 1)
    for index in range(bins):
        if index == bins - 1:
            mask = (p >= edges[index]) & (p <= edges[index + 1])
        else:
            mask = (p >= edges[index]) & (p < edges[index + 1])
        if not np.any(mask):
            continue
        result += float(np.sum(mask)) / total * abs(float(np.mean(p[mask]) - np.mean(y[mask])))
    return float(result)


def poisson_nll(observed: Sequence[float], means: Sequence[float]) -> float:
    y = np.asarray(observed, dtype=float)
    mu = np.clip(np.asarray(means, dtype=float), 1e-9, None)
    if y.size == 0 or y.shape != mu.shape:
        raise ValueError("nonempty equal-length observations and means required")
    values = mu - y * np.log(mu) + np.vectorize(math.lgamma)(y + 1.0)
    return float(np.mean(values))


def skellam_home_win_probability(home_mean: float, away_mean: float) -> float:
    from scipy.stats import skellam

    home = max(float(home_mean), 1e-9)
    away = max(float(away_mean), 1e-9)
    tie = float(skellam.pmf(0, home, away))
    return safe_probability(float(1.0 - skellam.cdf(0, home, away) + 0.5 * tie))


@dataclass(frozen=True)
class SplitPolicy:
    train_season: int = 2023
    tune_season: int = 2024
    evaluation_season: int = 2025
    classification: str = CLASSIFICATION

    def assignment(self, season: int) -> str:
        mapping = {
            self.train_season: "DEVELOPMENT_FIT",
            self.tune_season: "DEVELOPMENT_TUNE",
            self.evaluation_season: "DEVELOPMENT_EVALUATION_UNPROTECTED",
        }
        if season not in mapping:
            raise ValueError(f"season {season} is outside the approved preliminary split")
        return mapping[season]

    def validate(self) -> None:
        if not self.train_season < self.tune_season < self.evaluation_season:
            raise ValueError("chronological split ordering is required")
        if self.classification != CLASSIFICATION:
            raise ValueError("preliminary split must remain PRELIMINARY_UNPROTECTED")


@dataclass(frozen=True)
class MedianImputer:
    feature_names: tuple[str, ...]
    medians: tuple[float, ...]
    fitted_seasons: tuple[int, ...]

    @classmethod
    def fit(
        cls,
        rows: Sequence[Mapping[str, Any]],
        feature_names: Sequence[str],
        fitted_seasons: Sequence[int],
    ) -> "MedianImputer":
        allowed = {int(value) for value in fitted_seasons}
        if not rows or not allowed:
            raise ValueError("training rows and fitted seasons are required")
        if any(int(row["season"]) not in allowed for row in rows):
            raise ValueError("imputer rows extend beyond declared fitted seasons")
        medians: list[float] = []
        for name in feature_names:
            values = [float(row[name]) for row in rows if row.get(name) is not None]
            medians.append(float(np.median(values)) if values else 0.0)
        return cls(tuple(feature_names), tuple(medians), tuple(sorted(allowed)))

    def transform(self, rows: Sequence[Mapping[str, Any]]) -> np.ndarray:
        result = np.empty((len(rows), len(self.feature_names)), dtype=float)
        for row_index, row in enumerate(rows):
            for column_index, (name, median) in enumerate(zip(self.feature_names, self.medians)):
                value = row.get(name)
                result[row_index, column_index] = median if value is None else float(value)
        return result

    def manifest(self) -> dict[str, Any]:
        return {
            "rule": "FIT_SPLIT_MEDIAN_WITH_EXPLICIT_COLD_START_INDICATORS",
            "feature_names": list(self.feature_names),
            "medians": dict(zip(self.feature_names, self.medians)),
            "fitted_seasons": list(self.fitted_seasons),
        }


def feature_row_from_team_priors(
    target: Mapping[str, Any],
    home: Mapping[str, Any],
    away: Mapping[str, Any],
) -> dict[str, Any]:
    if target["game_id"] != home["target_game_id"] or target["game_id"] != away["target_game_id"]:
        raise ValueError("target/prior game identity mismatch")
    if target["home_team_id"] != home["team_id"] or target["away_team_id"] != away["team_id"]:
        raise ValueError("target/prior team identity mismatch")
    if target["home_team_id"] != away["opponent_id"] or target["away_team_id"] != home["opponent_id"]:
        raise ValueError("opponent identity mismatch")

    def difference(name: str) -> float | None:
        left, right = home.get(name), away.get(name)
        if left is None or right is None:
            return None
        return float(left) - float(right)

    home_games = int(home.get("prior_games") or 0)
    away_games = int(away.get("prior_games") or 0)
    return {
        "classification": CLASSIFICATION,
        "target_game_id": target["game_id"],
        "season": int(target["season"]),
        "season_type": target["season_type"],
        "week": int(target["week"]),
        "start_utc": target["start_utc"],
        "cutoff_utc": home["cutoff_utc"],
        "home_team_id": target["home_team_id"],
        "away_team_id": target["away_team_id"],
        "neutral_site": float(bool(target["neutral_site"])),
        "home_field": float(not bool(target["neutral_site"])),
        "prior_win_rate_diff": difference("prior_win_rate"),
        "prior_points_for_mean_diff": difference("prior_points_for_mean"),
        "prior_points_against_mean_diff": difference("prior_points_against_mean"),
        "log1p_prior_games_diff": float(math.log1p(home_games) - math.log1p(away_games)),
        "home_cold_start": float(home_games == 0),
        "away_cold_start": float(away_games == 0),
        "home_prior_games": home_games,
        "away_prior_games": away_games,
        "home_prior_row_id": home["row_id"],
        "away_prior_row_id": away["row_id"],
        "home_prior_lineage_sha256": home["lineage_sha256"],
        "away_prior_lineage_sha256": away["lineage_sha256"],
        "target_outcome_in_feature_evidence": bool(
            target["game_id"] in set(home["eligible_observation_ids"])
            or target["game_id"] in set(away["eligible_observation_ids"])
        ),
    }


def fit_logistic_calibrator(labels: Sequence[float], probabilities: Sequence[float]) -> Any:
    from sklearn.linear_model import LogisticRegression

    y = np.asarray(labels, dtype=float)
    mask = np.isin(y, [0.0, 1.0])
    if np.sum(mask) < 20 or len(np.unique(y[mask])) < 2:
        return None
    p = np.clip(np.asarray(probabilities, dtype=float)[mask], 1e-6, 1.0 - 1e-6)
    x = np.log(p / (1.0 - p)).reshape(-1, 1)
    model = LogisticRegression(C=1.0, solver="lbfgs", random_state=0)
    model.fit(x, y[mask].astype(int))
    return model


def apply_logistic_calibrator(model: Any, probabilities: Sequence[float]) -> np.ndarray:
    p = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1.0 - 1e-6)
    if model is None:
        return p
    x = np.log(p / (1.0 - p)).reshape(-1, 1)
    return np.asarray(model.predict_proba(x)[:, 1], dtype=float)


def probability_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, float | int]:
    if not rows:
        return {"rows": 0}
    labels = [float(row["home_win"]) for row in rows]
    raw = [float(row["home_win_probability"]) for row in rows]
    calibrated = [float(row.get("calibrated_home_win_probability", row["home_win_probability"])) for row in rows]
    return {
        "rows": len(rows),
        "brier": brier_score(labels, raw),
        "log_loss": log_loss(labels, raw),
        "ece_10": expected_calibration_error(labels, raw),
        "calibrated_brier": brier_score(labels, calibrated),
        "calibrated_log_loss": log_loss(labels, calibrated),
        "calibrated_ece_10": expected_calibration_error(labels, calibrated),
    }


def score_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, float | int]:
    if not rows or not all("predicted_margin" in row for row in rows):
        return {"rows": 0}
    actual_margin = np.asarray([float(row["margin"]) for row in rows])
    predicted_margin = np.asarray([float(row["predicted_margin"]) for row in rows])
    result: dict[str, float | int] = {
        "rows": len(rows),
        "margin_mae": float(np.mean(np.abs(actual_margin - predicted_margin))),
        "margin_rmse": float(np.sqrt(np.mean((actual_margin - predicted_margin) ** 2))),
    }
    if all("predicted_home_points" in row and "predicted_away_points" in row for row in rows):
        home = np.asarray([float(row["home_points"]) for row in rows])
        away = np.asarray([float(row["away_points"]) for row in rows])
        home_mu = np.asarray([float(row["predicted_home_points"]) for row in rows])
        away_mu = np.asarray([float(row["predicted_away_points"]) for row in rows])
        result.update(
            {
                "home_points_mae": float(np.mean(np.abs(home - home_mu))),
                "away_points_mae": float(np.mean(np.abs(away - away_mu))),
                "total_mae": float(np.mean(np.abs((home + away) - (home_mu + away_mu)))),
                "joint_independent_poisson_nll": poisson_nll(home, home_mu) + poisson_nll(away, away_mu),
            }
        )
    return result


def metrics_by_season_and_slice(
    predictions: Sequence[Mapping[str, Any]], tamu_team_id: str | None
) -> list[dict[str, Any]]:
    groups: list[tuple[str, list[Mapping[str, Any]]]] = []
    seasons = sorted({int(row["season"]) for row in predictions})
    for season in seasons:
        season_rows = [row for row in predictions if int(row["season"]) == season]
        groups.append((f"SEASON_{season}_ALL", season_rows))
        groups.append((f"SEASON_{season}_NONNEUTRAL", [row for row in season_rows if not row["neutral_site"]]))
        groups.append((f"SEASON_{season}_COLD_START", [row for row in season_rows if row["cold_start"]]))
        if tamu_team_id:
            groups.append(
                (
                    f"SEASON_{season}_TEXAS_AM_INVOLVED",
                    [
                        row
                        for row in season_rows
                        if row["home_team_id"] == tamu_team_id or row["away_team_id"] == tamu_team_id
                    ],
                )
            )
    result = []
    for slice_id, rows in groups:
        result.append(
            {
                "classification": CLASSIFICATION,
                "slice": slice_id,
                "probability": probability_metrics(rows),
                "score": score_metrics(rows),
            }
        )
    return result


def validate_chronology(
    features: Sequence[Mapping[str, Any]], targets: Sequence[Mapping[str, Any]], split: SplitPolicy
) -> dict[str, Any]:
    split.validate()
    feature_ids = {row["target_game_id"] for row in features}
    target_ids = {row["target_game_id"] for row in targets}
    if len(feature_ids) != len(features) or len(target_ids) != len(targets):
        raise ValueError("duplicate feature or target game identity")
    if any(bool(row["target_outcome_in_feature_evidence"]) for row in features):
        raise ValueError("target-game identity appears in feature evidence")
    if not target_ids.issubset(feature_ids):
        raise ValueError("target without feature row")
    if any(row["classification"] != CLASSIFICATION for row in (*features, *targets)):
        raise ValueError("classification drift")
    assignments = {season: split.assignment(season) for season in (2023, 2024, 2025)}
    return {
        "classification": CLASSIFICATION,
        "target_game_identity_exclusion": "PASS",
        "future_target_feature_exclusion": "PASS",
        "duplicate_feature_ids": 0,
        "duplicate_target_ids": 0,
        "targets_without_features": 0,
        "chronological_split_order": "PASS",
        "assignments": assignments,
    }


def elo_predict_and_update(
    games: Sequence[Mapping[str, Any]],
    initial_ratings: Mapping[str, float],
    *,
    k_factor: float,
    home_advantage: float,
    scale: float = 400.0,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    if k_factor <= 0 or scale <= 0:
        raise ValueError("positive Elo k-factor and scale required")
    ratings = {str(key): float(value) for key, value in initial_ratings.items()}
    predictions: list[dict[str, Any]] = []
    for row in sorted(games, key=lambda item: (item["start_utc"], item["target_game_id"])):
        home_id, away_id = str(row["home_team_id"]), str(row["away_team_id"])
        home_rating, away_rating = ratings.get(home_id, 1500.0), ratings.get(away_id, 1500.0)
        adjustment = 0.0 if bool(row["neutral_site"]) else float(home_advantage)
        probability = 1.0 / (1.0 + 10.0 ** (-(home_rating - away_rating + adjustment) / scale))
        predictions.append({**dict(row), "home_win_probability": float(probability)})
        if row.get("home_win") is None:
            continue
        result = float(row["home_win"])
        delta = float(k_factor) * (result - probability)
        ratings[home_id] = home_rating + delta
        ratings[away_id] = away_rating - delta
    return predictions, ratings


def sanitize_for_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): sanitize_for_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_for_json(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
