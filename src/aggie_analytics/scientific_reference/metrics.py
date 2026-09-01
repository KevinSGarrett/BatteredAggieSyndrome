"""Independent scoring metrics. Do not import producer metric helpers."""

from __future__ import annotations

import math
from typing import Iterable, Sequence


def _as_pairs(
    predicted: Sequence[float], observed: Sequence[float]
) -> list[tuple[float, float]]:
    if len(predicted) != len(observed):
        raise ValueError("predicted and observed lengths differ")
    return list(zip((float(p) for p in predicted), (float(o) for o in observed)))


def brier_score(predicted: Sequence[float], observed: Sequence[float]) -> float:
    pairs = _as_pairs(predicted, observed)
    if not pairs:
        raise ValueError("empty Brier sample")
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs)


def log_loss(
    predicted: Sequence[float],
    observed: Sequence[float],
    *,
    epsilon: float = 1e-15,
) -> float:
    pairs = _as_pairs(predicted, observed)
    if not pairs:
        raise ValueError("empty log-loss sample")
    total = 0.0
    for probability, label in pairs:
        clipped = min(1.0 - epsilon, max(epsilon, probability))
        total += -(label * math.log(clipped) + (1.0 - label) * math.log(1.0 - clipped))
    return total / len(pairs)


def accuracy(predicted: Sequence[float], observed: Sequence[float]) -> float:
    pairs = _as_pairs(predicted, observed)
    if not pairs:
        raise ValueError("empty accuracy sample")
    correct = sum(int((p >= 0.5) == (y >= 0.5)) for p, y in pairs)
    return correct / len(pairs)


def calibration_bins(
    predicted: Sequence[float],
    observed: Sequence[float],
    *,
    bin_count: int = 10,
) -> list[dict[str, float | int]]:
    if bin_count <= 0:
        raise ValueError("bin_count must be positive")
    pairs = _as_pairs(predicted, observed)
    bins: list[dict[str, float | int]] = []
    for index in range(bin_count):
        low = index / bin_count
        high = (index + 1) / bin_count
        members = [
            pair
            for pair in pairs
            if (pair[0] >= low and pair[0] < high)
            or (index == bin_count - 1 and pair[0] == high)
        ]
        if not members:
            bins.append(
                {
                    "bin": index,
                    "low": low,
                    "high": high,
                    "count": 0,
                    "mean_predicted": 0.0,
                    "mean_observed": 0.0,
                }
            )
            continue
        mean_predicted = sum(pair[0] for pair in members) / len(members)
        mean_observed = sum(pair[1] for pair in members) / len(members)
        bins.append(
            {
                "bin": index,
                "low": low,
                "high": high,
                "count": len(members),
                "mean_predicted": mean_predicted,
                "mean_observed": mean_observed,
            }
        )
    return bins


def expected_observed_wins(
    predicted: Sequence[float], observed: Sequence[float]
) -> dict[str, float]:
    pairs = _as_pairs(predicted, observed)
    if not pairs:
        raise ValueError("empty expected/observed sample")
    return {
        "expected_wins": sum(pair[0] for pair in pairs),
        "observed_wins": sum(pair[1] for pair in pairs),
        "n": float(len(pairs)),
    }


def source_coverage(
    present: Iterable[bool], abstained: Iterable[bool]
) -> dict[str, int]:
    present_list = [bool(item) for item in present]
    abstain_list = [bool(item) for item in abstained]
    if len(present_list) != len(abstain_list):
        raise ValueError("coverage vectors differ in length")
    return {
        "rows": len(present_list),
        "present": sum(present_list),
        "abstained": sum(abstain_list),
        "usable": sum(
            1
            for available, skipped in zip(present_list, abstain_list)
            if available and not skipped
        ),
    }
