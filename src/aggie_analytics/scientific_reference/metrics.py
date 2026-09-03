"""Independent scoring metrics. Do not import producer metric helpers.

Validate probability and label domains before clipping or binning. Empty
scored populations return null metrics with a reason, never a fabricated zero.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence


def _finite(value: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


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


def calibration_bins(
    predicted: Sequence[float],
    observed: Sequence[float],
    *,
    bin_count: int = 10,
) -> list[dict[str, float | int | None]]:
    if bin_count <= 0:
        raise ValueError("bin_count must be positive")
    pairs = _as_pairs(predicted, observed)
    bins: list[dict[str, float | int | None]] = []
    assigned = 0
    for index in range(bin_count):
        low = index / bin_count
        high = (index + 1) / bin_count
        members = [
            pair
            for pair in pairs
            if (pair[0] >= low and pair[0] < high)
            or (index == bin_count - 1 and pair[0] == high)
        ]
        assigned += len(members)
        if not members:
            bins.append(
                {
                    "bin": index,
                    "low": low,
                    "high": high,
                    "count": 0,
                    "mean_predicted": None,
                    "mean_observed": None,
                    "reason": "EMPTY_CALIBRATION_BIN",
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
    if assigned != len(pairs):
        raise ValueError("calibration bins omitted eligible rows")
    return bins


def expected_observed_wins(
    predicted: Sequence[float], observed: Sequence[float]
) -> dict[str, float | None]:
    pairs = _as_pairs(predicted, observed)
    if not pairs:
        return {
            "expected_wins": None,
            "observed_wins": None,
            "n": 0.0,
            "reason": "EMPTY_SCORED_POPULATION",
        }
    return {
        "expected_wins": sum(pair[0] for pair in pairs),
        "observed_wins": sum(pair[1] for pair in pairs),
        "n": float(len(pairs)),
    }


def _as_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field} requires an actual Boolean, not {value!r}")


def source_coverage(
    present: Iterable[Any], abstained: Iterable[Any]
) -> dict[str, int]:
    present_list = [_as_bool(item, field="present") for item in present]
    abstain_list = [_as_bool(item, field="abstained") for item in abstained]
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
