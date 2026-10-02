"""Game-grain coherent predictive distributions. Cycle #24/#25 remain deprecated."""

from __future__ import annotations

import math
from typing import Any, Mapping

from aggie_analytics.data.producer_distribution_math import (
    joint_from_same_normal,
    pair_normalize,
    probability_from_normal_residual,
)

DEPRECATE_PREDECESSORS = (
    "week1_2026_ridge_distribution_coherence",
    "week1_2026_forecast_input_binding_successor",
)
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"


def _phi_ppf(p: float) -> float:
    """Acklam rational approximation with two Halley refinements (producer copy)."""
    if not 0.0 < p < 1.0:
        raise ValueError("quantile p must be in (0, 1)")
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577459590091e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    elif p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    else:
        q = p - 0.5
        r = q * q
        x = (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
        ) / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    for _ in range(2):
        cdf = 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
        pdf = math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
        if pdf == 0.0:
            break
        x = x - (cdf - p) / (pdf + (cdf - p) * x / 2.0)
    return x


def freeze_mapping_before_market() -> str:
    return "RESIDUAL_NORMAL_FROZEN_PRE_MARKET"


def game_grain_forecast(
    *,
    contest_id: str,
    home_team_key: str,
    away_team_key: str,
    expected_margin_home: float,
    residual_stdev: float,
    interval_probability: float = 0.8,
    trust_gate_open: bool = False,
    fold_local: bool = True,
) -> dict[str, Any]:
    if residual_stdev <= 0:
        raise ValueError("residual_stdev must be positive")
    if not fold_local:
        raise ValueError("mapping must be fold-local")
    quantile = _phi_ppf(0.5 + interval_probability / 2.0)
    home_probability = probability_from_normal_residual(
        expected_margin_home, residual_stdev
    )
    away_probability = 1.0 - home_probability
    home_margin = expected_margin_home
    away_margin = -expected_margin_home
    lower = expected_margin_home - quantile * residual_stdev
    upper = expected_margin_home + quantile * residual_stdev
    pair = pair_normalize(home_probability, away_probability, home_margin, away_margin)
    joint = joint_from_same_normal(
        expected_margin=expected_margin_home,
        emitted_probability=home_probability,
        lower=lower,
        upper=upper,
        residual_stdev=residual_stdev,
        quantile=quantile,
    )
    coherent = bool(pair["coherent"] and joint["coherent"])
    state = (
        "FORECAST_FROZEN"
        if coherent
        else "ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE"
    )
    if not trust_gate_open:
        state = "UNTRUSTED_SHADOW"
    return {
        "contest_id": contest_id,
        "home_team_key": home_team_key,
        "away_team_key": away_team_key,
        "grain": "GAME",
        "distribution": "NORMAL_RESIDUAL",
        "mapping_identity": freeze_mapping_before_market(),
        "home_win_probability": home_probability,
        "away_win_probability": away_probability,
        "expected_margin_home": home_margin,
        "expected_margin_away": away_margin,
        "interval_lower": lower,
        "interval_upper": upper,
        "interval_probability": interval_probability,
        "residual_stdev": residual_stdev,
        "pair": pair,
        "joint": joint,
        "row_state": state,
        "trust_classification": SHADOW_CLASSIFICATION,
        "deprecated_predecessors": list(DEPRECATE_PREDECESSORS),
        "oriented_rows_derived_from_game_grain": True,
        "includes_neutral_contests": True,
    }


def oriented_rows_from_game(game: Mapping[str, Any]) -> list[dict[str, Any]]:
    home = {
        "team_key": game["home_team_key"],
        "opponent_key": game["away_team_key"],
        "team_win_probability": game["home_win_probability"],
        "expected_margin": game["expected_margin_home"],
        "interval_lower": game["interval_lower"],
        "interval_upper": game["interval_upper"],
        "orientation": "HOME",
        "contest_id": game["contest_id"],
        "parent_forecast_identity": game.get("forecast_identity"),
        "checkpoint": game.get("checkpoint"),
        "candidate_id": game.get("candidate_id"),
    }
    away = {
        "team_key": game["away_team_key"],
        "opponent_key": game["home_team_key"],
        "team_win_probability": game["away_win_probability"],
        "expected_margin": game["expected_margin_away"],
        "interval_lower": -game["interval_upper"],
        "interval_upper": -game["interval_lower"],
        "orientation": "AWAY",
        "contest_id": game["contest_id"],
        "parent_forecast_identity": game.get("forecast_identity"),
        "checkpoint": game.get("checkpoint"),
        "candidate_id": game.get("candidate_id"),
    }
    return [home, away]
