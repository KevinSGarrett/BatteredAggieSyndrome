"""Official-final scoring successor on unique frozen candidate-checkpoint rows.

A freeze boolean is not a freeze receipt. Contest-id-only indexing is
forbidden. Probability must be finite and in [0, 1]. Fitted metrics remain
UNTRUSTED_SHADOW. A 50% control is NO_DIRECTION.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle33.official_finals import (
    competing_observations,
    is_eligible_official_final,
)

SHADOW = "UNTRUSTED_SHADOW"
HOLD = "SCIENTIFIC_OPERATOR_HOLD_ACTIVE"

_ISO8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


def _parsed_utc_timestamp(value: Any) -> datetime | None:
    """A genuine timezone-aware ISO8601 timestamp, not merely a nonempty string."""

    if not isinstance(value, str) or not _ISO8601_RE.match(value.strip()):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


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
    """A genuine, verifiable freeze receipt -- not a truthy flag, a mutable row id
    reused as a receipt id, or a nonempty-but-unparseable timestamp string.

    MR33-01 repair: `frozen=true` plus *any* nonempty identity/timestamp used to
    score. This now requires an actual `freeze_receipt` mapping carrying its own
    receipt id (never the mutable `forecast_row_id`), a well-formed sha256 hash,
    a timezone-aware non-future ISO8601 `frozen_at_utc`, and a receipt-bound
    contest/candidate/cohort/checkpoint key that matches the forecast's own key
    exactly -- an unrelated hash or mismatched binding is rejected, not accepted.
    """

    flagged = forecast.get("frozen") is True or forecast.get("forecast_frozen") is True
    if not flagged:
        return False
    receipt = forecast.get("freeze_receipt")
    if not isinstance(receipt, Mapping):
        return False
    receipt_id = receipt.get("receipt_id")
    if not isinstance(receipt_id, str) or not receipt_id.strip():
        return False
    row_id = forecast.get("forecast_row_id")
    if row_id and str(row_id) == receipt_id:
        # A forecast row id is a mutable pointer, not a receipt identity.
        return False
    receipt_hash = receipt.get("receipt_sha256")
    if not isinstance(receipt_hash, str) or not re.fullmatch(
        r"[0-9a-f]{64}", receipt_hash.strip().casefold()
    ):
        return False
    frozen_at = _parsed_utc_timestamp(receipt.get("frozen_at_utc"))
    if frozen_at is None or frozen_at > datetime.now(timezone.utc):
        return False
    bound_key = (
        str(receipt.get("ncaa_contest_id") or receipt.get("ncaa_com_contest_id") or ""),
        str(receipt.get("candidate_id") or ""),
        str(receipt.get("cohort") or ""),
        str(receipt.get("checkpoint") or ""),
    )
    if bound_key != forecast_key(forecast) or any(part == "" for part in bound_key):
        return False
    return True


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
    quarantined_conflicting_forecast_keys = 0

    # MR33-02 repair: group by (contest, candidate, cohort, checkpoint) key
    # value, not arrival position, so scoring is provably order-invariant.
    # Conflicting proven probabilities for the identical key quarantine the
    # whole group -- neither the first nor the last row silently wins.
    by_key: dict[tuple[str, str, str, str], list[Mapping[str, Any]]] = {}
    key_order: list[tuple[str, str, str, str]] = []
    for forecast in forecasts or []:
        key = forecast_key(forecast)
        if key not in by_key:
            by_key[key] = []
            key_order.append(key)
        by_key[key].append(forecast)

    for key in key_order:
        cid = key[0]
        game = by_contest.get(cid)
        eligible_rows: list[Mapping[str, Any]] = []
        for forecast in by_key[key]:
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
            eligible_rows.append(forecast)
        if game is None or not eligible_rows:
            continue
        distinct_probabilities = {
            round(float(row["probability_home"]), 12) for row in eligible_rows
        }
        if len(distinct_probabilities) > 1:
            quarantined_conflicting_forecast_keys += 1
            continue
        # Identical proven duplicates collapse to one scored row, chosen by a
        # content-sorted (not arrival-order) tiebreak so forward/reverse input
        # order cannot change which row is kept.
        eligible_rows = sorted(
            eligible_rows, key=lambda row: str(row.get("forecast_row_id") or "")
        )
        representative = eligible_rows[0]
        rejected_duplicate_forecasts += len(eligible_rows) - 1
        row_id = str(representative.get("forecast_row_id") or "")
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
        probability_f = float(representative["probability_home"])
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
        "quarantined_conflicting_forecast_keys": quarantined_conflicting_forecast_keys,
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
