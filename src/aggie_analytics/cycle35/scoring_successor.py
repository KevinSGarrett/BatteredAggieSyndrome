"""R35-06/R35-07: score only admission-proven forecasts against canonical finals.

This is a successor to `cycle33.scoring_successor`, not an edit of it. The
predecessor's order-invariance, conflict quarantine and missing-evidence
rejection are retained behaviours; what changes is the *source of authority*:
admission comes from `cycle35.forecast_admission`, so a row is scored only
when a trusted allowlisted receipt committed it before the contest cutoff, for
the same ordered participants, under the same schedule version.

Two properties are deliberately structural rather than tested-by-example:

* **Zero is an answer.** No valid receipt anywhere yields zero scored rows and
  a populated rejection ledger. Nothing in this module can manufacture a
  forecast to raise that numerator.
* **Metrics are per candidate/cohort/checkpoint.** Pooling distinct candidates
  into one mean is how a weak model hides behind a strong one, so the grain is
  carried through to the output instead of being collapsed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle35.forecast_admission import (
    HOLD,
    SHADOW,
    TrustedReceiptStore,
    admit_many,
    ordered_participants,
)

SUCCESSOR_VERSION = "BAS-CYCLE35-SCORING-SUCCESSOR-v35.1"


def _brier(probability_home: float, home_won: bool) -> float:
    return (float(probability_home) - (1.0 if home_won else 0.0)) ** 2


def _winner(home_points: int, away_points: int) -> tuple[str, bool]:
    if home_points > away_points:
        return "HOME", True
    if away_points > home_points:
        return "AWAY", False
    return "TIE", False


def score_admitted_forecasts(
    finals: Sequence[Mapping[str, Any]],
    forecasts: Sequence[Mapping[str, Any]],
    *,
    store: TrustedReceiptStore,
    as_of_utc: datetime,
) -> dict[str, Any]:
    """Score admitted forecasts against already-adjudicated canonical finals.

    `finals` must be contests that an official-final replay has ALREADY
    admitted (terminal status verified against raw bytes, canonical
    participants bound). This function does not re-adjudicate them and never
    infers a winner from a supplied `winner` field -- it recomputes direction
    from the scores it was given, so a contradictory label cannot leak in.
    """

    contests_by_id: dict[str, Mapping[str, Any]] = {}
    unusable_finals: list[dict[str, Any]] = []
    for game in finals:
        cid = str(
            game.get("ncaa_contest_id")
            or game.get("canonical_contest_id")
            or game.get("ncaa_com_contest_id")
            or ""
        )
        if not cid:
            unusable_finals.append({"reason": "MISSING_CONTEST_ID"})
            continue
        if ordered_participants(game) is None:
            unusable_finals.append(
                {"contest_id": cid, "reason": "MISSING_ORDERED_PARTICIPANTS"}
            )
            continue
        contests_by_id[cid] = game

    admission = admit_many(
        forecasts, contests_by_id, store=store, as_of_utc=as_of_utc
    )

    scored: list[dict[str, Any]] = []
    for item in admission["admitted"]:
        cid, candidate, cohort, checkpoint = item["key"]
        game = contests_by_id.get(cid)
        if game is None:
            continue
        try:
            home_points = int(game["home_points"])
            away_points = int(game["away_points"])
        except (KeyError, TypeError, ValueError):
            unusable_finals.append(
                {"contest_id": cid, "reason": "NON_INTEGER_SCORES"}
            )
            continue
        winner, home_won = _winner(home_points, away_points)
        probability = float(item["probability_home"])
        if probability > 0.5:
            favorite = "HOME"
        elif probability < 0.5:
            favorite = "AWAY"
        else:
            favorite = "NO_DIRECTION"
        scored.append(
            {
                "ncaa_contest_id": cid,
                "candidate_id": candidate,
                "cohort": cohort,
                "checkpoint": checkpoint,
                "home_canonical_team_id": game["home_canonical_team_id"],
                "away_canonical_team_id": game["away_canonical_team_id"],
                "probability_home": probability,
                "brier": _brier(probability, home_won),
                "winner": winner,
                "predicted_favorite": favorite,
                "tie_rule": "NO_DIRECTION_AT_HALF",
                "receipt_id": item["verdict"]["receipt_id"],
                "commitment_time_utc": item["verdict"]["commitment_time_utc"],
                "cutoff_utc": item["verdict"]["cutoff_utc"],
                "trust_classification": SHADOW,
            }
        )

    # Per candidate/cohort/checkpoint, never pooled into one headline number.
    metrics: dict[str, Any] = {}
    for row in scored:
        bucket = "|".join((row["candidate_id"], row["cohort"], row["checkpoint"]))
        entry = metrics.setdefault(
            bucket,
            {
                "candidate_id": row["candidate_id"],
                "cohort": row["cohort"],
                "checkpoint": row["checkpoint"],
                "scored_rows": 0,
                "brier_sum": 0.0,
                "ties": 0,
                "no_direction": 0,
            },
        )
        entry["scored_rows"] += 1
        entry["brier_sum"] += row["brier"]
        if row["winner"] == "TIE":
            entry["ties"] += 1
        if row["predicted_favorite"] == "NO_DIRECTION":
            entry["no_direction"] += 1
    for entry in metrics.values():
        entry["brier_mean"] = (
            entry["brier_sum"] / entry["scored_rows"] if entry["scored_rows"] else None
        )

    return {
        "artifact_type": "CYCLE35_ADMITTED_FORECAST_SCORING",
        "successor_version": SUCCESSOR_VERSION,
        "contract_version": admission["contract_version"],
        "as_of_utc": admission["as_of_utc"],
        "store": admission["store"],
        "eligible_final_contests": len(contests_by_id),
        "unusable_finals": unusable_finals,
        "input_forecast_rows": admission["input_row_count"],
        "admitted_forecast_rows": admission["admitted_count"],
        "rejected_forecast_rows": admission["rejected_count"],
        "quarantined_conflicting_keys": admission["quarantined_conflicting_keys"],
        "scored_rows": scored,
        "scored_row_count": len(scored),
        "scored_unique_contests": len({row["ncaa_contest_id"] for row in scored}),
        "metrics_by_candidate_cohort_checkpoint": list(metrics.values()),
        "verdicts": admission["verdicts"],
        "zero_scored_is_valid_evidence_incompleteness": True,
        "winner_recomputed_from_scores_not_supplied_label": True,
        "trust_classification": SHADOW,
        "operator_hold": HOLD,
        "pit_admitted": False,
    }
