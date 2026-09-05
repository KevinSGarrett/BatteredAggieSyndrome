"""Producer-side distribution helpers. Independent reference must not import this."""

from __future__ import annotations

import math
from typing import Mapping

PROBABILITY_TOLERANCE = 1e-12
MARGIN_TOLERANCE = 1e-9


def phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def probability_from_normal_residual(expected_margin: float, residual_stdev: float) -> float:
    if residual_stdev <= 0 or not math.isfinite(residual_stdev) or not math.isfinite(expected_margin):
        raise ValueError("expected margin must be finite and residual_stdev must be positive")
    return phi(expected_margin / residual_stdev)


def pair_normalize(
    home_probability: float,
    away_probability: float,
    home_margin: float,
    away_margin: float,
) -> dict[str, float | bool | str]:
    values = (home_probability, away_probability, home_margin, away_margin)
    if any(not math.isfinite(item) for item in values):
        return {
            "coherent": False,
            "abstain_reason": "ABSTAIN_NONFINITE_OR_INVALID_DOMAIN",
            "home_probability": home_probability,
            "away_probability": away_probability,
            "home_margin": home_margin,
            "away_margin": away_margin,
        }
    if not (0.0 <= home_probability <= 1.0 and 0.0 <= away_probability <= 1.0):
        return {
            "coherent": False,
            "abstain_reason": "ABSTAIN_PROBABILITY_OUT_OF_RANGE",
            "home_probability": home_probability,
            "away_probability": away_probability,
            "home_margin": home_margin,
            "away_margin": away_margin,
        }
    probability_ok = abs(home_probability + away_probability - 1.0) <= PROBABILITY_TOLERANCE
    margin_ok = abs(home_margin + away_margin) <= MARGIN_TOLERANCE
    toss_up = abs(home_probability - 0.5) <= PROBABILITY_TOLERANCE
    zero_margin = abs(home_margin) <= MARGIN_TOLERANCE
    if toss_up and zero_margin:
        favorite_ok = True
    elif toss_up or zero_margin:
        favorite_ok = False
    else:
        favorite_ok = (home_probability > 0.5) == (home_margin > 0.0)
    coherent = probability_ok and margin_ok and favorite_ok
    return {
        "home_probability": home_probability,
        "away_probability": away_probability,
        "home_margin": home_margin,
        "away_margin": away_margin,
        "probability_complementary": probability_ok,
        "margin_antisymmetric": margin_ok,
        "favorite_direction_agrees": favorite_ok,
        "coherent": coherent,
        "abstain_reason": "" if coherent else "ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE",
    }


def joint_from_same_normal(
    *,
    expected_margin: float,
    emitted_probability: float,
    lower: float,
    upper: float,
    residual_stdev: float,
    quantile: float,
) -> dict[str, float | bool | str]:
    reconstructed_probability = probability_from_normal_residual(expected_margin, residual_stdev)
    reconstructed_lower = expected_margin - quantile * residual_stdev
    reconstructed_upper = expected_margin + quantile * residual_stdev
    coherent = (
        abs(emitted_probability - reconstructed_probability) <= 1e-8
        and abs(lower - reconstructed_lower) <= 1e-8
        and abs(upper - reconstructed_upper) <= 1e-8
        and lower <= upper
    )
    return {
        "reconstructed_probability": reconstructed_probability,
        "reconstructed_lower": reconstructed_lower,
        "reconstructed_upper": reconstructed_upper,
        "coherent": coherent,
        "abstain_reason": "" if coherent else "ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE",
    }
