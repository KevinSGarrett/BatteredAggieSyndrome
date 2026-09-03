"""Independent pair, residual, and interval reconstruction.

This module must not import producer forecast, metric, or interval helpers.
Quantiles are derived from a documented inverse-normal implementation, never
from a producer-supplied constant treated as an independent expected result.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

PROBABILITY_TOLERANCE = 1e-12
MARGIN_TOLERANCE = 1e-9
# Acklam (2003) rational approximation; documented relative error about 1.15e-9.
# Peter J. Acklam, "An algorithm for computing the inverse normal cumulative
# distribution function", https://web.archive.org/web/20151030215612/
# http://home.online.no/~pjacklam/notes/invnorm/
PPF_RELATIVE_ERROR_BOUND = 1.15e-9
CDF_PPF_ABS_TOLERANCE = 1e-8
QUANTILE_ABS_TOLERANCE = 1.2e-8

_ACKLAM_A = (
    -3.969683028665376e01,
    2.209460984245205e02,
    -2.759285104469687e02,
    1.383577459590091e02,
    -3.066479806614716e01,
    2.506628277459239e00,
)
_ACKLAM_B = (
    -5.447609879822406e01,
    1.615858368580409e02,
    -1.556989798598866e02,
    6.680131188771972e01,
    -1.328068155288572e01,
)
_ACKLAM_C = (
    -7.784894002430293e-03,
    -3.223964580411365e-01,
    -2.400758277161838e00,
    -2.549732539343734e00,
    4.374664141464968e00,
    2.938163982698783e00,
)
_ACKLAM_D = (
    7.784695709041462e-03,
    3.224671290700398e-01,
    2.445134137142996e00,
    3.754408661907416e00,
)
_ACKLAM_P_LOW = 0.02425


def _finite(value: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def inverse_normal_cdf(p: float) -> float:
    """Standard-normal inverse CDF using Acklam's 2003 rational approximation."""
    if not _finite(p) or not 0.0 < p < 1.0:
        raise ValueError("p must be finite and in (0, 1)")
    plow = _ACKLAM_P_LOW
    phigh = 1.0 - plow
    a = _ACKLAM_A
    b = _ACKLAM_B
    c = _ACKLAM_C
    d = _ACKLAM_D
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    if p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / (((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
    ) / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)


def standard_normal_cdf(z: float) -> float:
    if not _finite(z):
        raise ValueError("z must be finite")
    return _phi(z)


def interval_quantile(interval_mass: float) -> float:
    """Two-sided central quantile z such that P(-z < Z < z) = interval_mass."""
    if not _finite(interval_mass) or not 0.0 < interval_mass < 1.0:
        raise ValueError("interval mass must be finite and in (0, 1)")
    tail = (1.0 - interval_mass) / 2.0
    return inverse_normal_cdf(1.0 - tail)


def probability_from_normal_residual(expected_margin: float, residual_stdev: float) -> float:
    if not _finite(expected_margin) or not _finite(residual_stdev):
        raise ValueError("expected margin and scale must be finite")
    if residual_stdev <= 0:
        raise ValueError("residual_stdev must be positive")
    return _phi(expected_margin / residual_stdev)


def pair_normalize(
    home_probability: float,
    away_probability: float,
    home_margin: float,
    away_margin: float,
) -> dict[str, float | bool | str]:
    values = (home_probability, away_probability, home_margin, away_margin)
    if any(not _finite(item) for item in values):
        return {
            "home_probability": home_probability,
            "away_probability": away_probability,
            "home_margin": home_margin,
            "away_margin": away_margin,
            "probability_sum": float("nan"),
            "margin_sum": float("nan"),
            "probability_complementary": False,
            "margin_antisymmetric": False,
            "favorite_direction_agrees": False,
            "coherent": False,
            "abstain_reason": "ABSTAIN_NONFINITE_OR_INVALID_DOMAIN",
        }
    if not (0.0 <= home_probability <= 1.0 and 0.0 <= away_probability <= 1.0):
        return {
            "home_probability": home_probability,
            "away_probability": away_probability,
            "home_margin": home_margin,
            "away_margin": away_margin,
            "probability_sum": home_probability + away_probability,
            "margin_sum": home_margin + away_margin,
            "probability_complementary": False,
            "margin_antisymmetric": False,
            "favorite_direction_agrees": False,
            "coherent": False,
            "abstain_reason": "ABSTAIN_PROBABILITY_OUT_OF_RANGE",
        }
    probability_sum = home_probability + away_probability
    margin_sum = home_margin + away_margin
    probability_ok = abs(probability_sum - 1.0) <= PROBABILITY_TOLERANCE
    margin_ok = abs(margin_sum) <= MARGIN_TOLERANCE
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
) -> dict[str, float | int | None]:
    if not (len(observed) == len(lower) == len(upper)):
        raise ValueError("interval vectors differ in length")
    if not observed:
        return {
            "n": 0,
            "covered": 0,
            "coverage": None,
            "intervals_crossing_zero": 0,
            "reason": "EMPTY_SCORED_POPULATION",
        }
    covered = 0
    crossed_zero = 0
    for value, low, high in zip(observed, lower, upper):
        if not all(_finite(item) for item in (value, low, high)):
            raise ValueError("interval values must be finite")
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
) -> dict[str, float | None]:
    if len(expected) != len(observed):
        raise ValueError("residual vectors differ in length")
    if not expected:
        return {"mae": None, "rmse": None, "n": 0.0, "reason": "EMPTY_SCORED_POPULATION"}
    residuals = [float(y) - float(mu) for mu, y in zip(expected, observed)]
    if any(not _finite(item) for item in residuals):
        raise ValueError("residuals must be finite")
    mae = sum(abs(item) for item in residuals) / len(residuals)
    rmse = math.sqrt(sum(item * item for item in residuals) / len(residuals))
    return {"mae": mae, "rmse": rmse, "n": float(len(residuals))}


def joint_distribution_coherent(
    row: Mapping[str, float],
    *,
    residual_stdev: float,
    interval_mass: float | None = None,
    quantile: float | None = None,
) -> dict[str, float | bool | str]:
    """Reconstruct probability and interval from the same fitted normal.

    ``quantile`` is accepted only as a producer-emitted diagnostic to compare
    against the independently computed inverse-CDF quantile. It is never the
    independent expected result.
    """
    expected = row.get("expected_margin_home")
    emitted_probability = row.get("home_win_probability")
    lower = row.get("interval_lower")
    upper = row.get("interval_upper")
    if any(not _finite(float(item)) for item in (expected, emitted_probability, lower, upper, residual_stdev) if item is not None):
        return {
            "reconstructed_probability": float("nan"),
            "reconstructed_lower": float("nan"),
            "reconstructed_upper": float("nan"),
            "independent_quantile": float("nan"),
            "probability_matches_residual": False,
            "interval_matches_residual": False,
            "coherent": False,
            "abstain_reason": "ABSTAIN_NONFINITE_OR_INVALID_DOMAIN",
        }
    expected_f = float(expected)
    emitted_probability_f = float(emitted_probability)
    lower_f = float(lower)
    upper_f = float(upper)
    if residual_stdev <= 0 or not _finite(residual_stdev):
        return {
            "reconstructed_probability": float("nan"),
            "reconstructed_lower": float("nan"),
            "reconstructed_upper": float("nan"),
            "independent_quantile": float("nan"),
            "probability_matches_residual": False,
            "interval_matches_residual": False,
            "coherent": False,
            "abstain_reason": "ABSTAIN_NONPOSITIVE_SCALE",
        }
    if lower_f > upper_f:
        return {
            "reconstructed_probability": float("nan"),
            "reconstructed_lower": lower_f,
            "reconstructed_upper": upper_f,
            "independent_quantile": float("nan"),
            "probability_matches_residual": False,
            "interval_matches_residual": False,
            "coherent": False,
            "abstain_reason": "ABSTAIN_REVERSED_INTERVAL",
        }
    if interval_mass is None:
        if quantile is None:
            raise ValueError("interval_mass or quantile diagnostic is required")
        if not _finite(float(quantile)) or float(quantile) <= 0:
            return {
                "reconstructed_probability": float("nan"),
                "reconstructed_lower": float("nan"),
                "reconstructed_upper": float("nan"),
                "independent_quantile": float("nan"),
                "probability_matches_residual": False,
                "interval_matches_residual": False,
                "coherent": False,
                "abstain_reason": "ABSTAIN_INVALID_INTERVAL_MASS",
            }
        independent_quantile = float(quantile)
    else:
        if not _finite(interval_mass) or not 0.0 < float(interval_mass) < 1.0:
            return {
                "reconstructed_probability": float("nan"),
                "reconstructed_lower": float("nan"),
                "reconstructed_upper": float("nan"),
                "independent_quantile": float("nan"),
                "probability_matches_residual": False,
                "interval_matches_residual": False,
                "coherent": False,
                "abstain_reason": "ABSTAIN_INVALID_INTERVAL_MASS",
            }
        independent_quantile = interval_quantile(float(interval_mass))
        if quantile is not None and abs(float(quantile) - independent_quantile) > QUANTILE_ABS_TOLERANCE:
            return {
                "reconstructed_probability": probability_from_normal_residual(
                    expected_f, residual_stdev
                ),
                "reconstructed_lower": expected_f - independent_quantile * residual_stdev,
                "reconstructed_upper": expected_f + independent_quantile * residual_stdev,
                "independent_quantile": independent_quantile,
                "probability_matches_residual": False,
                "interval_matches_residual": False,
                "coherent": False,
                "abstain_reason": "ABSTAIN_PRODUCER_QUANTILE_DISAGREES_INDEPENDENT_PPF",
            }
    reconstructed_probability = probability_from_normal_residual(
        expected_f, residual_stdev
    )
    reconstructed_lower = expected_f - independent_quantile * residual_stdev
    reconstructed_upper = expected_f + independent_quantile * residual_stdev
    probability_match = (
        _finite(emitted_probability_f)
        and 0.0 <= emitted_probability_f <= 1.0
        and abs(emitted_probability_f - reconstructed_probability) <= 1e-8
    )
    interval_match = (
        abs(lower_f - reconstructed_lower) <= 1e-8
        and abs(upper_f - reconstructed_upper) <= 1e-8
    )
    coherent = probability_match and interval_match
    return {
        "reconstructed_probability": reconstructed_probability,
        "reconstructed_lower": reconstructed_lower,
        "reconstructed_upper": reconstructed_upper,
        "independent_quantile": independent_quantile,
        "probability_matches_residual": probability_match,
        "interval_matches_residual": interval_match,
        "coherent": coherent,
        "abstain_reason": (
            "" if coherent else "ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE"
        ),
    }
