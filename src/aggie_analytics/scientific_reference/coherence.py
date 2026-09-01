"""Independent pair, residual, and interval reconstruction."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

PROBABILITY_TOLERANCE = 1e-12
MARGIN_TOLERANCE = 1e-9


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def probability_from_normal_residual(expected_margin: float, residual_stdev: float) -> float:
    if residual_stdev <= 0:
        raise ValueError("residual_stdev must be positive")
    return _phi(expected_margin / residual_stdev)


def pair_normalize(
    home_probability: float,
    away_probability: float,
    home_margin: float,
    away_margin: float,
) -> dict[str, float | bool | str]:
    probability_sum = home_probability + away_probability
    margin_sum = home_margin + away_margin
    probability_ok = abs(probability_sum - 1.0) <= PROBABILITY_TOLERANCE
    margin_ok = abs(margin_sum) <= MARGIN_TOLERANCE
    favorite_ok = (home_probability >= 0.5) == (home_margin >= 0.0) or (
        abs(home_probability - 0.5) <= PROBABILITY_TOLERANCE
        and abs(home_margin) <= MARGIN_TOLERANCE
    )
    coherent = probability_ok and margin_ok and favorite_ok
    return {
        "home_probability": home_probability,
        "away_probability": away_probability,
        "home_margin": home_margin,
        "away_margin": away_margin,
        "probability_sum": probability_sum,
        "margin_sum": margin_sum,
        "probability_complementary": probability_ok,
        "margin_antisymmetric": margin_ok,
        "favorite_direction_agrees": favorite_ok,
        "coherent": coherent,
        "abstain_reason": (
            "" if coherent else "ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE"
        ),
    }


def interval_coverage(
    observed: Sequence[float],
    lower: Sequence[float],
    upper: Sequence[float],
) -> dict[str, float | int]:
    if not (len(observed) == len(lower) == len(upper)):
        raise ValueError("interval vectors differ in length")
    if not observed:
        raise ValueError("empty interval sample")
    covered = 0
    crossed_zero = 0
    for value, low, high in zip(observed, lower, upper):
        if low > high:
            raise ValueError("interval lower exceeds upper")
        if low <= value <= high:
            covered += 1
        if low < 0.0 < high:
            crossed_zero += 1
    return {
        "n": len(observed),
        "covered": covered,
        "coverage": covered / len(observed),
        "intervals_crossing_zero": crossed_zero,
    }


def residual_metrics(
    expected: Sequence[float], observed: Sequence[float]
) -> dict[str, float]:
    if len(expected) != len(observed):
        raise ValueError("residual vectors differ in length")
    if not expected:
        raise ValueError("empty residual sample")
    residuals = [float(y) - float(mu) for mu, y in zip(expected, observed)]
    mae = sum(abs(item) for item in residuals) / len(residuals)
    rmse = math.sqrt(sum(item * item for item in residuals) / len(residuals))
    return {"mae": mae, "rmse": rmse, "n": float(len(residuals))}


def joint_distribution_coherent(
    row: Mapping[str, float],
    *,
    residual_stdev: float,
    quantile: float,
) -> dict[str, float | bool | str]:
    expected = float(row["expected_margin_home"])
    emitted_probability = float(row["home_win_probability"])
    lower = float(row["interval_lower"])
    upper = float(row["interval_upper"])
    reconstructed_probability = probability_from_normal_residual(
        expected, residual_stdev
    )
    reconstructed_lower = expected - quantile * residual_stdev
    reconstructed_upper = expected + quantile * residual_stdev
    probability_match = abs(emitted_probability - reconstructed_probability) <= 1e-8
    interval_match = (
        abs(lower - reconstructed_lower) <= 1e-8
        and abs(upper - reconstructed_upper) <= 1e-8
    )
    coherent = probability_match and interval_match
    return {
        "reconstructed_probability": reconstructed_probability,
        "reconstructed_lower": reconstructed_lower,
        "reconstructed_upper": reconstructed_upper,
        "probability_matches_residual": probability_match,
        "interval_matches_residual": interval_match,
        "coherent": coherent,
        "abstain_reason": (
            "" if coherent else "ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE"
        ),
    }
