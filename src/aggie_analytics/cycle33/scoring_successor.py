"""Official-final scoring successor on unique frozen candidate-checkpoint rows.

A freeze boolean is not a freeze receipt. Contest-id-only indexing is
forbidden. Probability must be finite and in [0, 1]. Fitted metrics remain
UNTRUSTED_SHADOW. A 50% control is NO_DIRECTION.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle33.official_finals import (
    competing_observations,
    is_eligible_official_final,
)

SHADOW = "UNTRUSTED_SHADOW"
HOLD = "SCIENTIFIC_OPERATOR_HOLD_ACTIVE"


def _brier(probability_home: float, home_won: bool) -> float:
    outcome = 1.0 if home_won else 0.0
    return (float(probability_home) - outcome) ** 2


def _finite_probability(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and 0.0 <= number <= 1.0


def forecast_key(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("ncaa_contest_id") or row.get("ncaa_com_contest_id") or ""),
        str(row.get("candidate_id") or row.get("candidate") or ""),
        str(row.get("cohort") or row.get("forecast_cohort") or ""),
        str(row.get("checkpoint") or row.get("checkpoint_id") or ""),
    )


def freeze_is_proven(forecast: Mapping[str, Any]) -> bool:
    """`frozen=true` alone is insufficient."""

    flagged = forecast.get("frozen") is True or forecast.get("forecast_frozen") is True
    if not flagged:
        return False
    receipt = forecast.get("freeze_receipt")
    if not isinstance(receipt, Mapping):
        receipt = {}
    identity = (
        forecast.get("freeze_receipt_id")
        or receipt.get("receipt_id")
        or forecast.get("forecast_row_id")
        or receipt.get("forecast_row_id")
    )
    frozen_at = (
        forecast.get("frozen_at_utc")
        or forecast.get("known_at_utc")
        or receipt.get("frozen_at_utc")
        or receipt.get("known_at_utc")
    )
    return bool(identity) and bool(frozen_at)


def score_unique_frozen_games(
    observations: Sequence[Mapping[str, Any]],
    *,
    forecasts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Score each proven frozen candidate/checkpoint against admitted finals."""

    grouped = competing_observations(observations)
    admitted = [
        game
        for game in grouped["admitted_unique_games"]
        if is_eligible_official_final(game)
    ]
    by_contest = {
        str(game.get("ncaa_com_contest_id") or game.get("ncaa_contest_id") or ""): game
        for game in admitted
    }
    scored: list[dict[str, Any]] = []
    excluded_unfrozen = 0
    excluded_abstained = 0
    excluded_no_forecast = 0
    excluded_unproven_freeze = 0
    excluded_invalid_probability = 0
    rejected_duplicate_forecasts = 0
    seen_keys: set[tuple[str, str, str, str]] = set()
    seen_row_ids: set[str] = set()
    for forecast in forecasts or []:
        cid = str(
            forecast.get("ncaa_contest_id") or forecast.get("ncaa_com_contest_id") or ""
        )
        key = forecast_key(forecast)
        row_id = str(forecast.get("forecast_row_id") or "")
        if key in seen_keys or (row_id and row_id in seen_row_ids):
            rejected_duplicate_forecasts += 1
            continue
        seen_keys.add(key)
        if row_id:
            seen_row_ids.add(row_id)
        game = by_contest.get(cid)
        if game is None:
            continue
        if forecast.get("abstained") or forecast.get("classification") == "ABSTAINED":
            excluded_abstained += 1
            continue
        if not freeze_is_proven(forecast):
            if forecast.get("frozen") or forecast.get("forecast_frozen"):
                excluded_unproven_freeze += 1
            else:
                excluded_unfrozen += 1
                if not forecast:
                    excluded_no_forecast += 1
            continue
        probability = forecast.get("probability_home")
        if not _finite_probability(probability):
            excluded_invalid_probability += 1
            continue
        home_points = int(game["home_points"])
        away_points = int(game["away_points"])
        if home_points > away_points:
            winner = "HOME"
            home_won = True
        elif away_points > home_points:
            winner = "AWAY"
            home_won = False
        else:
            winner = "TIE"
            home_won = False
        probability_f = float(probability)
        if probability_f > 0.5:
            favorite = "HOME"
        elif probability_f < 0.5:
            favorite = "AWAY"
        else:
            favorite = "NO_DIRECTION"
        scored.append(
            {
                "ncaa_contest_id": cid,
                "candidate_id": key[1],
                "cohort": key[2],
                "checkpoint": key[3],
                "forecast_row_id": row_id or None,
                "brier": _brier(probability_f, home_won),
                "winner": winner,
                "predicted_favorite": favorite,
                "tie_rule": "NO_DIRECTION_AT_HALF",
                "trust_classification": SHADOW,
            }
        )
    brier_mean = sum(row["brier"] for row in scored) / len(scored) if scored else None
    return {
        "observation_count": grouped["observation_count"],
        "unique_contest_count": grouped["unique_contest_count"],
        "admitted_unique_games": len(admitted),
        "quarantined_conflicts": len(grouped["quarantined_conflicts"]),
        "nonfinal_contests": len(grouped.get("nonfinal_contests") or []),
        "scored_unique_frozen_games": len({row["ncaa_contest_id"] for row in scored}),
        "scored_candidate_checkpoint_rows": len(scored),
        "excluded_unfrozen": excluded_unfrozen,
        "excluded_abstained": excluded_abstained,
        "excluded_no_forecast": excluded_no_forecast,
        "excluded_unproven_freeze": excluded_unproven_freeze,
        "excluded_invalid_probability": excluded_invalid_probability,
        "rejected_duplicate_forecasts": rejected_duplicate_forecasts,
        "brier_mean": brier_mean,
        "metrics_recomputed_on": "admitted_unique_frozen_candidate_checkpoint_rows",
        "unfrozen_excluded_from_scoring": True,
        "observation_vs_unique_reported_separately": True,
        "row_order_invariant": True,
        "trust_classification": SHADOW,
        "operator_hold": HOLD,
        "pit_admitted": False,
        "week2_outcomes_do_not_tune": True,
        "scored_rows": scored,
    }
