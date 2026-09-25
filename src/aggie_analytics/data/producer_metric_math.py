"""Producer-side scoring metrics. Independent reference must not import this."""

from __future__ import annotations

import math
from typing import Sequence


def _finite(value: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _as_pairs(
    predicted: Sequence[float], observed: Sequence[float]
) -> list[tuple[float, float]]:
    if len(predicted) != len(observed):
        raise ValueError("predicted and observed lengths differ")
    pairs: list[tuple[float, float]] = []
    for probability, label in zip(predicted, observed):
        if not _finite(float(probability)) or not 0.0 <= float(probability) <= 1.0:
            raise ValueError("predicted probability must be finite and in [0, 1]")
        if not _finite(float(label)) or float(label) not in {0.0, 1.0}:
            raise ValueError("binary label must be 0 or 1")
        pairs.append((float(probability), float(label)))
    return pairs


def brier_score(predicted: Sequence[float], observed: Sequence[float]) -> float | None:
    pairs = _as_pairs(predicted, observed)
    if not pairs:
        return None
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def log_loss(
    predicted: Sequence[float],
    observed: Sequence[float],
    *,
    epsilon: float = 1e-15,
) -> float | None:
    pairs = _as_pairs(predicted, observed)
    if not pairs:
        return None
    total = 0.0
    for probability, label in pairs:
        clipped = min(1.0 - epsilon, max(epsilon, probability))
        total += -(label * math.log(clipped) + (1.0 - label) * math.log(1.0 - clipped))
    return total / len(pairs)


def accuracy(predicted: Sequence[float], observed: Sequence[float]) -> float | None:
    pairs = _as_pairs(predicted, observed)
    if not pairs:
        return None
    correct = sum(int((p >= 0.5) == (y >= 0.5)) for p, y in pairs)
    return correct / len(pairs)
