from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

NORMAL_QUANTILE_95 = 1.959964


def clipped_logistic(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(min(value, 30.0), -30.0)))


def standard_normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def reconstruct_ridge_surfaces(
    *,
    expected_margin: float,
    residual_stdev: float,
    logistic_link_scale_divisor: float,
    normal_quantile: float = NORMAL_QUANTILE_95,
) -> dict[str, Any]:
    if residual_stdev <= 0.0 or logistic_link_scale_divisor <= 0.0:
        raise ValueError("ridge residual stdev and divisor must be positive")
    training_link_scale = residual_stdev / logistic_link_scale_divisor
    half = normal_quantile * residual_stdev
    interval = [expected_margin - half, expected_margin + half]
    return {
        "expected_margin": expected_margin,
        "residual_stdev": residual_stdev,
        "logistic_link_scale_divisor": logistic_link_scale_divisor,
        "training_link_scale": training_link_scale,
        "normal_quantile": normal_quantile,
        "interval": [round(interval[0], 10), round(interval[1], 10)],
        "probability_if_divisor_used_as_link_scale": clipped_logistic(
            expected_margin / logistic_link_scale_divisor
        ),
        "probability_if_training_link_scale": clipped_logistic(
            expected_margin / training_link_scale
        ),
        "probability_if_normal_residual_distribution": standard_normal_cdf(
            expected_margin / residual_stdev
        ),
        "interval_crosses_zero": interval[0] < 0.0 < interval[1],
        "divisor_equals_residual_stdev": math.isclose(
            logistic_link_scale_divisor, residual_stdev
        ),
    }


def cycle24_ridge_emitted_matches_divisor_as_link_scale(
    emitted_probability: float, reconstructed: Mapping[str, Any]
) -> bool:
    return math.isclose(
        float(emitted_probability),
        float(reconstructed["probability_if_divisor_used_as_link_scale"]),
        rel_tol=0.0,
        abs_tol=1e-9,
    )


def probability_and_interval_are_one_distribution(
    emitted_probability: float, reconstructed: Mapping[str, Any]
) -> bool:
    return math.isclose(
        float(emitted_probability),
        float(reconstructed["probability_if_normal_residual_distribution"]),
        rel_tol=0.0,
        abs_tol=1e-6,
    )


def classify_ridge_distribution_coherence(
    *,
    expected_margin: float | None,
    emitted_probability: float | None,
    interval: Sequence[float] | None,
    residual_stdev: float,
    logistic_link_scale_divisor: float,
    normal_quantile: float = NORMAL_QUANTILE_95,
    saturation_low: float = 0.01,
    saturation_high: float = 0.99,
) -> dict[str, Any]:
    if expected_margin is None or emitted_probability is None or not interval:
        return {
            "state": "COHERENCE_NOT_APPLICABLE",
            "reasons": ["PROBABILITY_OR_INTERVAL_ABSENT"],
            "reconstructed": None,
        }
    reconstructed = reconstruct_ridge_surfaces(
        expected_margin=float(expected_margin),
        residual_stdev=float(residual_stdev),
        logistic_link_scale_divisor=float(logistic_link_scale_divisor),
        normal_quantile=float(normal_quantile),
    )
    reconstructed["formulas"] = {
        "emitted_cycle24_probability": "logistic(expected_margin_home / logistic_link_scale_divisor)",
        "training_consistent_probability": (
            "logistic(expected_margin_home / (training_residual_stdev / "
            "logistic_link_scale_divisor))"
        ),
        "interval": (
            "expected_margin_home ± normal_quantile * training_residual_stdev"
        ),
        "interval_implied_home_win_probability": (
            "Phi(expected_margin_home / training_residual_stdev)"
        ),
    }
    reasons: list[str] = []
    uses_divisor_as_link = cycle24_ridge_emitted_matches_divisor_as_link_scale(
        float(emitted_probability), reconstructed
    )
    same_distribution = probability_and_interval_are_one_distribution(
        float(emitted_probability), reconstructed
    )
    stored_low, stored_high = float(interval[0]), float(interval[1])
    reconstructed["stored_interval_matches_residual_formula"] = math.isclose(
        stored_low, float(reconstructed["interval"][0]), rel_tol=0.0, abs_tol=1e-6
    ) and math.isclose(
        stored_high, float(reconstructed["interval"][1]), rel_tol=0.0, abs_tol=1e-6
    )
    reconstructed["interval_crosses_zero"] = stored_low < 0.0 < stored_high
    if uses_divisor_as_link and not reconstructed["divisor_equals_residual_stdev"]:
        reasons.append(
            "PROBABILITY_USED_DIVISOR_AS_LINK_SCALE_INTERVAL_USED_RESIDUAL_STDEV"
        )
    if reconstructed["interval_crosses_zero"] and (
        float(emitted_probability) <= saturation_low
        or float(emitted_probability) >= saturation_high
    ):
        reasons.append("SATURATED_PROBABILITY_WITH_INTERVAL_CROSSING_ZERO")
    if not same_distribution:
        reasons.append(
            "EMITTED_PROBABILITY_IS_NOT_P_MARGIN_GT_ZERO_UNDER_RESIDUAL_INTERVAL"
        )
    if reasons:
        state = "REVIEW_REQUIRED_PROBABILITY_DISTRIBUTION_INCOHERENCE"
    else:
        state = "PROBABILITY_AND_INTERVAL_COHERENT"
    return {
        "state": state,
        "reasons": reasons,
        "reconstructed": reconstructed,
        "emitted_probability": float(emitted_probability),
        "cycle24_row_rewritten": False,
        "mapping_changed": False,
        "chosen_using_a_and_m_or_market_or_week1_outcome": False,
        "threshold_class": "MATHEMATICAL_IDENTITY_NOT_CALIBRATED",
        "presented_as_one_distribution": state == "PROBABILITY_AND_INTERVAL_COHERENT",
        "different_estimands": not same_distribution,
    }


def audit_cycle24_ridge_forecast_row(
    row: Mapping[str, Any],
    *,
    residual_stdev: float,
    logistic_link_scale_divisor: float,
    normal_quantile: float,
    saturation_low: float,
    saturation_high: float,
) -> dict[str, Any]:
    classified = classify_ridge_distribution_coherence(
        expected_margin=row.get("expected_margin_home"),
        emitted_probability=row.get("probability_home"),
        interval=row.get("margin_interval_home"),
        residual_stdev=residual_stdev,
        logistic_link_scale_divisor=logistic_link_scale_divisor,
        normal_quantile=normal_quantile,
        saturation_low=saturation_low,
        saturation_high=saturation_high,
    )
    reconstructed = classified.get("reconstructed") or {}
    return {
        "forecast_row_identity": row.get("forecast_row_identity"),
        "contest_identity": row.get("contest_identity"),
        "ncaa_contest_id": row.get("ncaa_contest_id"),
        "candidate_id": row.get("candidate_id"),
        "row_state": row.get("row_state"),
        "expected_margin_home": row.get("expected_margin_home"),
        "margin_interval_home": row.get("margin_interval_home"),
        "emitted_probability_home": row.get("probability_home"),
        "probability_if_divisor_used_as_link_scale": reconstructed.get(
            "probability_if_divisor_used_as_link_scale"
        ),
        "probability_if_training_link_scale": reconstructed.get(
            "probability_if_training_link_scale"
        ),
        "probability_implied_by_residual_interval": reconstructed.get(
            "probability_if_normal_residual_distribution"
        ),
        "interval_crosses_zero": reconstructed.get("interval_crosses_zero"),
        "formulas": reconstructed.get("formulas"),
        "adequacy_state": classified["state"],
        "reasons": classified["reasons"],
        "threshold_class": classified["threshold_class"],
        "cycle24_row_rewritten": False,
        "mapping_changed": False,
        "chosen_using_a_and_m_or_market_or_week1_outcome": False,
        "presented_as_one_distribution": classified.get(
            "presented_as_one_distribution", False
        ),
        "different_estimands": classified.get("different_estimands", True),
    }
