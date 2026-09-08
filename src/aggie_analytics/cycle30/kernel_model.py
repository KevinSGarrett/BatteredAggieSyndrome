"""Predeclared simple national baseline candidates. Fold-local unique-game grain."""

from __future__ import annotations

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


class KernelModelError(ValueError):
    """Raised when a predeclared candidate cannot be fit or scored."""


def _sigmoid(logits: np.ndarray) -> np.ndarray:
    clipped = np.clip(logits, -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def design_matrix(
    rows: Sequence[Mapping[str, Any]], candidate: str
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    if candidate not in CANDIDATES:
        raise KernelModelError(f"undeclared candidate {candidate}")
    labels = []
    features = []
    consumed = ["intercept"]
    if candidate != "intercept_only":
        consumed.append(
            "prior_margin_diff" if "margin" in candidate else "prior_win_rate_diff"
        )
    if "ordinary_home" in candidate:
        consumed.append("ordinary_home_exposure")
    for row in rows:
        if row.get("tie"):
            continue
        y = 1.0 if row.get("home_win_label") else 0.0
        home = row.get("home_features") or {}
        away = row.get("away_features") or {}
        vector = [1.0]
        if candidate == "prior_margin_diff":
            vector.append(
                float(home.get("pit_prior_margin_mean") or 0.0)
                - float(away.get("pit_prior_margin_mean") or 0.0)
            )
        elif candidate == "prior_margin_diff_ordinary_home":
            vector.append(
                float(home.get("pit_prior_margin_mean") or 0.0)
                - float(away.get("pit_prior_margin_mean") or 0.0)
            )
            exposure = row.get("ordinary_home_exposure")
            if exposure is None:
                continue
            vector.append(float(exposure))
        elif candidate == "prior_win_rate_diff_ordinary_home":
            vector.append(
                float(home.get("pit_prior_win_rate") or 0.0)
                - float(away.get("pit_prior_win_rate") or 0.0)
            )
            exposure = row.get("ordinary_home_exposure")
            if exposure is None:
                continue
            vector.append(float(exposure))
        labels.append(y)
        features.append(vector)
    if not features:
        raise KernelModelError("no eligible unique-game rows")
    return np.asarray(features, dtype=float), np.asarray(labels, dtype=float), consumed


def fit_logistic(
    features: np.ndarray, labels: np.ndarray, *, ridge: float
) -> np.ndarray:
    n, k = features.shape
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
    return _sigmoid(features @ weights)


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
    x_train, y_train, consumed = design_matrix(train, candidate)
    weights = fit_logistic(x_train, y_train, ridge=ridge)
    x_eval, y_eval, _ = design_matrix(evaluate, candidate)
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
        "exposed_seasons_excluded": list(EXPOSED_SEASONS),
        "predeclared": PREDECLARED,
        "coaching_consumed": False,
        "travel_consumed": False,
        "ridge_lambda": ridge,
        "grain": "UNIQUE_GAME",
    }
