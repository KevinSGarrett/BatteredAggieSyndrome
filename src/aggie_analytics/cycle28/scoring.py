"""Cycle #28 official-final scoring successor.

Preserves Cycle #27 predecessor receipts as derivative observations. Admits
only atomic SOURCE_ACQUISITION_RECEIPT evidence for new scoring rows.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from aggie_analytics.cycle28.atomic_receipt import (
    DERIVATIVE_OBSERVATION_RECEIPT,
    SOURCE_ACQUISITION_RECEIPT,
    classify_cycle27_receipt,
)
from aggie_analytics.scientific_reference.cycle28_scoring import (
    IndependentScoringError,
    reconstruct_metrics,
    reject_non_final_score,
    reject_oriented_rows_as_games,
    reject_prekickoff_final,
    select_earliest_valid_terminal,
)

SCHEMA_VERSION = "aggie.shadow.week1_2026_cycle28_official_final_scoring.v1"
CONTRACT_ID = "CYCLE28-WEEK1-2026-OFFICIAL-FINAL-ATOMIC-RECEIPT-SUCCESSOR-V1"
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PREDECESSOR_CYCLE27_RECEIPT_CLASS = DERIVATIVE_OBSERVATION_RECEIPT

STATE_SCORED = "SCORED_OFFICIAL_FINAL_ATOMIC_RECEIPT"
STATE_AWAITING = "AWAITING_OFFICIAL_FINAL"
STATE_POSTPONED = "POSTPONED_OR_CANCELED"
STATE_CONFLICT = "CONFLICT_QUARANTINED"
STATE_ABSTAINED = "FORECAST_ABSTAINED"
STATE_NO_FORECAST = "NO_PREKICKOFF_FORECAST"
STATE_ACQUISITION_FAILED = "SOURCE_ACQUISITION_FAILED"

REQUIRED_SCORED_FIELDS = (
    "ncaa_contest_id",
    "ordered_participants",
    "frozen_forecast_row_identity",
    "checkpoint_identity",
    "kickoff_bound_or_confirmed_utc",
    "request_identity_sha256",
    "raw_response_sha256",
    "raw_response_relative_path",
    "acquisition_receipt_sha256",
    "acquisition_receipt_relative_path",
    "trusted_clock_retrieval_utc",
    "route_id",
    "final_status",
    "home_points",
    "away_points",
    "winner",
    "orientation",
    "temporal_admission_decision",
    "scoring_formula_id",
    "scored_row_identity",
)


class Cycle28ScoringError(ValueError):
    """Raised when a Cycle #28 scoring row cannot be admitted."""


def classify_predecessor_receipts(payloads: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {SOURCE_ACQUISITION_RECEIPT: 0, DERIVATIVE_OBSERVATION_RECEIPT: 0}
    timestamps: dict[str, int] = {}
    for payload in payloads:
        kind = classify_cycle27_receipt(payload)
        counts[kind] = counts.get(kind, 0) + 1
        stamp = str(payload.get("retrieved_at_utc") or "")
        timestamps[stamp] = timestamps.get(stamp, 0) + 1
    return {
        "receipt_count": len(payloads),
        "source_acquisition_count": counts[SOURCE_ACQUISITION_RECEIPT],
        "derivative_observation_count": counts[DERIVATIVE_OBSERVATION_RECEIPT],
        "shared_materialization_timestamp_count": max(timestamps.values()) if timestamps else 0,
        "shared_materialization_timestamp": max(timestamps, key=timestamps.get) if timestamps else None,
        "predecessor_preserved": True,
        "predecessor_deleted": False,
        "supersession": "CYCLE28_ATOMIC_SOURCE_ACQUISITION_SUCCESSOR",
    }


def require_scored_row_authority(row: Mapping[str, Any]) -> None:
    missing = [field for field in REQUIRED_SCORED_FIELDS if not row.get(field)]
    if missing:
        raise Cycle28ScoringError(f"scored row missing receipt/source authority: {missing}")
    if row.get("receipt_kind") != SOURCE_ACQUISITION_RECEIPT:
        raise Cycle28ScoringError("scored row must bind a SOURCE_ACQUISITION_RECEIPT")
    reject_non_final_score(str(row["final_status"]))
    reject_prekickoff_final(
        str(row["trusted_clock_retrieval_utc"]),
        str(row["kickoff_bound_or_confirmed_utc"]),
    )


def classify_contest(
    *,
    official_final_receipt: Mapping[str, Any] | None,
    acquisition_failed: bool,
    postponed_or_canceled: bool,
    forecast_row: Mapping[str, Any] | None,
    conflict: bool,
) -> str:
    if conflict:
        return STATE_CONFLICT
    if postponed_or_canceled:
        return STATE_POSTPONED
    if acquisition_failed:
        return STATE_ACQUISITION_FAILED
    if official_final_receipt is None:
        return STATE_AWAITING
    if forecast_row is None:
        return STATE_NO_FORECAST
    if forecast_row.get("publication_state") in {"ABSTAIN", "ABSTAIN_SCIENTIFIC_TRUST_GATE_BLOCKED"}:
        return STATE_ABSTAINED
    return STATE_SCORED


def score_game_grain(
    *,
    contests: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    unique_games = reject_oriented_rows_as_games(contests)
    predicted = [float(row["predicted_probability"]) for row in contests]
    observed = [float(row["observed_win"]) for row in contests]
    metrics = reconstruct_metrics(
        predicted=predicted,
        observed=observed,
        unique_game_count=unique_games,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "shadow_classification": SHADOW_CLASSIFICATION,
        "protected_lane": PROTECTED_LANE,
        "empirical_predictive_skill": "EMPIRICAL_PREDICTIVE_SKILL_NOT_ESTABLISHED",
        "tuned_from_week1_outcomes": False,
        "metrics": metrics,
        "unique_games": unique_games,
    }


def terminal_selection(receipts: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | str:
    return select_earliest_valid_terminal(receipts)


def reject_forecast_mutation(predecessor_hash: str, current_hash: str) -> None:
    if predecessor_hash != current_hash:
        raise Cycle28ScoringError("frozen forecast mutation/backfill is forbidden")


def reject_week1_outcome_tuning(used_for_fit: bool, used_for_selection: bool, used_for_promotion: bool) -> None:
    if used_for_fit or used_for_selection or used_for_promotion:
        raise Cycle28ScoringError("Week 1 outcomes cannot tune, select, or promote")
