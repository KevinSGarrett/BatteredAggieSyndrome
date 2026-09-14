"""Official-final scoring successor on unique frozen games only."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from aggie_analytics.cycle33.official_finals import competing_observations

SHADOW = "UNTRUSTED_SHADOW"
HOLD = "SCIENTIFIC_OPERATOR_HOLD_ACTIVE"


def _brier(probability_home: float, home_won: bool) -> float:
    outcome = 1.0 if home_won else 0.0
    return (float(probability_home) - outcome) ** 2


def score_unique_frozen_games(
    observations: Sequence[Mapping[str, Any]],
    *,
    forecasts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Recompute metrics on admitted unique frozen games. Unfrozen excluded."""

    grouped = competing_observations(observations)
    forecast_by_id = {
        str(row.get("ncaa_contest_id") or row.get("ncaa_com_contest_id") or ""): dict(
            row
        )
        for row in (forecasts or [])
        if row.get("ncaa_contest_id") or row.get("ncaa_com_contest_id")
    }
    scored: list[dict[str, Any]] = []
    excluded_unfrozen = 0
    excluded_abstained = 0
    excluded_no_forecast = 0
    for game in grouped["admitted_unique_games"]:
        cid = str(game.get("ncaa_com_contest_id") or game.get("ncaa_contest_id") or "")
        forecast = forecast_by_id.get(cid) or {}
        if forecast.get("abstained") or forecast.get("classification") == "ABSTAINED":
            excluded_abstained += 1
            continue
        if not forecast.get("frozen") and forecast.get("forecast_frozen") is not True:
            excluded_unfrozen += 1
            if not forecast:
                excluded_no_forecast += 1
            continue
        home_points = game.get("home_points")
        away_points = game.get("away_points")
        if home_points is None or away_points is None:
            continue
        probability = forecast.get("probability_home")
        if probability is None:
            excluded_no_forecast += 1
            continue
        home_won = int(home_points) > int(away_points)
        scored.append(
            {
                "ncaa_contest_id": cid,
                "brier": _brier(float(probability), home_won),
                "winner": "HOME"
                if home_won
                else "AWAY"
                if int(away_points) > int(home_points)
                else "TIE",
                "trust_classification": SHADOW,
            }
        )
    brier_mean = sum(row["brier"] for row in scored) / len(scored) if scored else None
    return {
        "observation_count": grouped["observation_count"],
        "unique_contest_count": grouped["unique_contest_count"],
        "admitted_unique_games": len(grouped["admitted_unique_games"]),
        "quarantined_conflicts": len(grouped["quarantined_conflicts"]),
        "scored_unique_frozen_games": len(scored),
        "excluded_unfrozen": excluded_unfrozen,
        "excluded_abstained": excluded_abstained,
        "excluded_no_forecast": excluded_no_forecast,
        "brier_mean": brier_mean,
        "metrics_recomputed_on": "admitted_unique_frozen_games_only",
        "unfrozen_excluded_from_scoring": True,
        "observation_vs_unique_reported_separately": True,
        "trust_classification": SHADOW,
        "operator_hold": HOLD,
        "pit_admitted": False,
        "week2_outcomes_do_not_tune": True,
    }
