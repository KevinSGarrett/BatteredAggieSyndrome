"""Independent Cycle #29 metrics.

Does not import ``aggie_analytics.scientific_reference.metrics``. A probability
of exactly 0.5 has no directional accuracy claim.
"""

from __future__ import annotations

import math
from typing import Sequence

EPS = 1e-15


class IndependentMetricError(ValueError):
    """Raised when independent metrics cannot be computed."""


def _pairs(
    predicted: Sequence[float], observed: Sequence[float]
) -> list[tuple[float, float]]:
    if len(predicted) != len(observed):
        raise IndependentMetricError("predicted and observed lengths differ")
    pairs: list[tuple[float, float]] = []
    for probability, label in zip(predicted, observed):
        p = float(probability)
        y = float(label)
        if not math.isfinite(p) or not 0.0 <= p <= 1.0:
            raise IndependentMetricError("predicted probability must be in [0, 1]")
        if y not in {0.0, 1.0}:
            raise IndependentMetricError("binary label must be 0 or 1")
        pairs.append((p, y))
    return pairs


def brier_score(predicted: Sequence[float], observed: Sequence[float]) -> float | None:
    pairs = _pairs(predicted, observed)
    if not pairs:
        return None
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def log_loss(predicted: Sequence[float], observed: Sequence[float]) -> float | None:
    pairs = _pairs(predicted, observed)
    if not pairs:
        return None
    total = 0.0
    for probability, label in pairs:
        clipped = min(1.0 - EPS, max(EPS, probability))
        total += -(label * math.log(clipped) + (1.0 - label) * math.log(1.0 - clipped))
    return total / len(pairs)


def directional_accuracy(
    predicted: Sequence[float], observed: Sequence[float]
) -> dict[str, float | int | None | str]:
    """Accuracy excluding exact 0.5 control probabilities.

    ``p == 0.5`` is not a home or away prediction.
    """

    pairs = _pairs(predicted, observed)
    directional = [(p, y) for p, y in pairs if p != 0.5]
    excluded = len(pairs) - len(directional)
    if not directional:
        return {
            "accuracy": None,
            "n_directional": 0,
            "n_excluded_base_rate": excluded,
            "reason": "BASE_RATE_HALF_HAS_NO_DIRECTIONAL_CLAIM",
        }
    correct = 0
    for probability, label in directional:
        predicted_home = probability > 0.5
        observed_home = label >= 0.5
        if predicted_home == observed_home:
            correct += 1
    return {
        "accuracy": correct / len(directional),
        "n_directional": len(directional),
        "n_excluded_base_rate": excluded,
        "reason": None,
    }


def reject_half_as_directional(probability: float, counted_as_prediction: bool) -> None:
    if probability == 0.5 and counted_as_prediction:
        raise IndependentMetricError(
            "base-rate 0.5 cannot be counted as a directional prediction"
        )
