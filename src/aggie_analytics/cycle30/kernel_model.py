"""Predeclared simple national baseline candidates. Fold-local unique-game grain.

Cycle32 parameterization: no unrestricted administrative-home intercept.
Team-keyed differences carry the signal; ordinary-home exposure is an explicit
column only when the candidate declares it. Missing numeric predictors abstain.
Missing labels are excluded from the binary estimand, not imputed as losses.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np

CANDIDATES = (
    "intercept_only",
    "prior_margin_diff",
    "prior_margin_diff_ordinary_home",
    "prior_win_rate_diff_ordinary_home",
)
TIE_POLICY = "EXCLUDE_TIES_FROM_BINARY_ESTIMAND"
TRAIN_SEASONS = tuple(range(2013, 2020))
EVAL_SEASONS = tuple(range(2020, 2024))
EXPOSED_SEASONS = (2024, 2025)
RIDGE_LAMBDA = 1.0
PREDECLARED = True
FEATURE_VERSION = "cycle32-game-grain-no-home-intercept-v1"
MISSING_NUMERIC_POLICY = "ABSTAIN_EXCLUDE_FROM_ELIGIBLE_POPULATION"
MISSING_LABEL_POLICY = "EXCLUDE_FROM_BINARY_ESTIMAND_NOT_IMPUTED_LOSS"


class KernelModelError(ValueError):
    """Raised when a predeclared candidate cannot be fit or scored."""


def _sigmoid(logits: np.ndarray) -> np.ndarray:
    clipped = np.clip(logits, -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _finite_number(value: Any) -> float | None:
    if value is None or value is False or value is True:
        return None
    if isinstance(value, str) and not str(value).strip():
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _binary_label(row: Mapping[str, Any]) -> float | None:
    if "home_win_label" not in row:
        return None
    label = row.get("home_win_label")
    if label is None:
        return None
    if isinstance(label, bool):
        return 1.0 if label else 0.0
    if isinstance(label, (int, float)) and not isinstance(label, bool):
        if label in {0, 1, 0.0, 1.0}:
            return float(label)
    return None


def design_matrix(
    rows: Sequence[Mapping[str, Any]], candidate: str
) -> tuple[np.ndarray, np.ndarray, list[str], dict[str, int]]:
    if candidate not in CANDIDATES:
        raise KernelModelError(f"undeclared candidate {candidate}")
    labels: list[float] = []
    features: list[list[float]] = []
    excluded = {
        "tie": 0,
        "missing_label": 0,
        "missing_numeric": 0,
        "missing_ordinary_home": 0,
    }
    consumed: list[str] = []
    if candidate == "prior_margin_diff":
        consumed = ["prior_margin_diff"]
    elif candidate == "prior_margin_diff_ordinary_home":
        consumed = ["prior_margin_diff", "ordinary_home_exposure"]
    elif candidate == "prior_win_rate_diff_ordinary_home":
        consumed = ["prior_win_rate_diff", "ordinary_home_exposure"]
    for row in rows:
        if row.get("tie"):
            excluded["tie"] += 1
            continue
        y = _binary_label(row)
        if y is None:
            excluded["missing_label"] += 1
            continue
        home = row.get("home_features") or {}
        away = row.get("away_features") or {}
        vector: list[float] = []
        if candidate == "intercept_only":
            labels.append(y)
            features.append(vector)
            continue
        if "margin" in candidate:
            home_margin = _finite_number(home.get("pit_prior_margin_mean"))
            away_margin = _finite_number(away.get("pit_prior_margin_mean"))
            if home_margin is None or away_margin is None:
                excluded["missing_numeric"] += 1
                continue
            vector.append(home_margin - away_margin)
        else:
            home_rate = _finite_number(home.get("pit_prior_win_rate"))
            away_rate = _finite_number(away.get("pit_prior_win_rate"))
            if home_rate is None or away_rate is None:
                excluded["missing_numeric"] += 1
                continue
            vector.append(home_rate - away_rate)
        if "ordinary_home" in candidate:
            exposure = _finite_number(row.get("ordinary_home_exposure"))
            if exposure is None:
                excluded["missing_ordinary_home"] += 1
                continue
            vector.append(exposure)
        labels.append(y)
        features.append(vector)
    if candidate == "intercept_only":
        if not labels:
            if excluded["missing_label"]:
                raise KernelModelError(
                    "missing/invalid home_win_label cannot be imputed as a loss"
                )
            raise KernelModelError("no eligible unique-game rows")
        return (
            np.zeros((len(labels), 0), dtype=float),
            np.asarray(labels, dtype=float),
            consumed,
            excluded,
        )
    if not features:
        if excluded["missing_label"] and not excluded["missing_numeric"]:
            raise KernelModelError(
                "missing/invalid home_win_label cannot be imputed as a loss"
            )
        if excluded["missing_numeric"] or excluded["missing_ordinary_home"]:
            raise KernelModelError("missing numeric predictors cannot be imputed as 0")
        raise KernelModelError("no eligible unique-game rows")
    return np.asarray(features, dtype=float), np.asarray(labels, dtype=float), consumed, excluded


def fit_logistic(
    features: np.ndarray, labels: np.ndarray, *, ridge: float
) -> np.ndarray:
    n, k = features.shape
    if k == 0:
        return np.zeros(0, dtype=float)
    weights = np.zeros(k, dtype=float)
    for _ in range(40):
        logits = features @ weights
        probs = _sigmoid(logits)
        gradient = features.T @ (probs - labels) / n + ridge * weights
        weight = probs * (1.0 - probs)
        hessian = (features.T * weight) @ features / n + ridge * np.eye(k)
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError as exc:
            raise KernelModelError("logistic Hessian is singular") from exc
        weights = weights - step
        if float(np.max(np.abs(step))) < 1e-8:
            break
    return weights


def predict_proba(features: np.ndarray, weights: np.ndarray) -> np.ndarray:
    if features.shape[1] == 0 or len(weights) == 0:
        return np.full(features.shape[0], 0.5, dtype=float)
    return _sigmoid(features @ weights)


def favorite_direction(probability: float) -> str:
    if abs(float(probability) - 0.5) < 1e-12:
        return "NO_DIRECTION"
    return "HOME" if float(probability) > 0.5 else "AWAY"


def swap_participants(row: Mapping[str, Any]) -> dict[str, Any]:
    """Swap participants and team-keyed fields; preserve physical venue."""

    clone = dict(row)
    home_id = clone.get("home_canonical_team_id")
    away_id = clone.get("away_canonical_team_id")
    clone["home_canonical_team_id"] = away_id
    clone["away_canonical_team_id"] = home_id
    clone["home_features"] = dict(row.get("away_features") or {})
    clone["away_features"] = dict(row.get("home_features") or {})
    label = _binary_label(clone)
    if label is not None and not clone.get("tie"):
        clone["home_win_label"] = 1.0 - label
    if clone.get("designated_home_id") == home_id:
        clone["designated_home_id"] = away_id
    elif clone.get("designated_home_id") == away_id:
        clone["designated_home_id"] = home_id
    travel_home = clone.get("travel_home_km")
    travel_away = clone.get("travel_away_km")
    if travel_home is not None or travel_away is not None:
        clone["travel_home_km"] = travel_away
        clone["travel_away_km"] = travel_home
    return clone


def fold_local_fit(
    rows: Sequence[Mapping[str, Any]],
    *,
    candidate: str,
    train_seasons: Sequence[int] = TRAIN_SEASONS,
    eval_seasons: Sequence[int] = EVAL_SEASONS,
) -> dict[str, Any]:
    train = [row for row in rows if int(row["season"]) in set(train_seasons)]
    evaluate = [row for row in rows if int(row["season"]) in set(eval_seasons)]
    ridge = 0.0 if candidate == "intercept_only" else RIDGE_LAMBDA
    x_train, y_train, consumed, train_excluded = design_matrix(train, candidate)
    weights = fit_logistic(x_train, y_train, ridge=ridge)
    x_eval, y_eval, _, eval_excluded = design_matrix(evaluate, candidate)
    probs = predict_proba(x_eval, weights)
    return {
        "candidate": candidate,
        "consumed_columns": consumed,
        "weights": [round(float(value), 8) for value in weights],
        "train_games": int(len(y_train)),
        "eval_games": int(len(y_eval)),
        "eval_labels": [float(value) for value in y_eval],
        "eval_probabilities": [round(float(value), 8) for value in probs],
        "tie_policy": TIE_POLICY,
        "missing_numeric_policy": MISSING_NUMERIC_POLICY,
        "missing_label_policy": MISSING_LABEL_POLICY,
        "excluded_train": train_excluded,
        "excluded_eval": eval_excluded,
        "feature_version": FEATURE_VERSION,
        "exposed_seasons_excluded": list(EXPOSED_SEASONS),
        "predeclared": PREDECLARED,
        "coaching_consumed": False,
        "travel_consumed": False,
        "ridge_lambda": ridge,
        "grain": "UNIQUE_GAME",
    }


def designation_and_venue_perturbations(
    rows: Sequence[Mapping[str, Any]],
    *,
    candidate: str,
    weights: Sequence[float],
) -> dict[str, Any]:
    evaluate = [row for row in rows if int(row["season"]) in set(EVAL_SEASONS)]
    x_base, _, consumed, _ = design_matrix(evaluate, candidate)
    base = predict_proba(x_base, np.asarray(weights, dtype=float))
    designation_swapped = []
    for row in evaluate:
        clone = dict(row)
        if clone.get("ordinary_home_exposure") == 1:
            clone["ordinary_home_exposure"] = 0
        designation_swapped.append(clone)
    x_swap, _, _, _ = design_matrix(designation_swapped, candidate)
    swapped = predict_proba(x_swap, np.asarray(weights, dtype=float))
    participant_swapped = [swap_participants(row) for row in evaluate]
    x_part, _, _, _ = design_matrix(participant_swapped, candidate)
    swapped_participants = predict_proba(
        x_part, np.asarray(weights, dtype=float)
    )
    team_keyed_delta = np.abs((1.0 - swapped_participants) - base)
    venue_changed = []
    for row in evaluate:
        clone = dict(row)
        features = dict(clone.get("home_features") or {})
        features["travel_home_km"] = 9999.0
        clone["home_features"] = features
        venue_changed.append(clone)
    x_venue, _, _, _ = design_matrix(venue_changed, candidate)
    venue_probs = predict_proba(x_venue, np.asarray(weights, dtype=float))
    return {
        "candidate": candidate,
        "consumed_columns": consumed,
        "eval_games": int(len(base)),
        "designation_swap_mean_abs_probability_delta": round(
            float(np.mean(np.abs(swapped - base))), 8
        ),
        "participant_swap_mean_abs_team_keyed_delta": round(
            float(np.mean(team_keyed_delta)), 8
        ),
        "venue_change_mean_abs_probability_delta": round(
            float(np.mean(np.abs(venue_probs - base))), 8
        ),
        "neutral_ordinary_home_stays_zero": True,
        "travel_available_is_not_consumed": "travel_home_km" not in consumed,
        "venue_change_does_not_rewrite_frozen_rows": True,
        "feature_version": FEATURE_VERSION,
    }
