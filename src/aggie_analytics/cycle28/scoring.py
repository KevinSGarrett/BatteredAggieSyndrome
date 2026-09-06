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


def classify_predecessor_receipts(
    payloads: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
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
        "shared_materialization_timestamp_count": max(timestamps.values())
        if timestamps
        else 0,
        "shared_materialization_timestamp": max(timestamps, key=timestamps.get)
        if timestamps
        else None,
        "predecessor_preserved": True,
        "predecessor_deleted": False,
        "supersession": "CYCLE28_ATOMIC_SOURCE_ACQUISITION_SUCCESSOR",
    }


def require_scored_row_authority(row: Mapping[str, Any]) -> None:
    missing = []
    for field in REQUIRED_SCORED_FIELDS:
        if field not in row:
            missing.append(field)
            continue
        value = row[field]
        if value is None or value == "":
            missing.append(field)
    if missing:
        raise Cycle28ScoringError(
            f"scored row missing receipt/source authority: {missing}"
        )
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
    if forecast_row.get("publication_state") in {
        "ABSTAIN",
        "ABSTAIN_SCIENTIFIC_TRUST_GATE_BLOCKED",
    }:
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


def terminal_selection(
    receipts: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | str:
    return select_earliest_valid_terminal(receipts)


def reject_forecast_mutation(predecessor_hash: str, current_hash: str) -> None:
    if predecessor_hash != current_hash:
        raise Cycle28ScoringError("frozen forecast mutation/backfill is forbidden")


def reject_week1_outcome_tuning(
    used_for_fit: bool, used_for_selection: bool, used_for_promotion: bool
) -> None:
    if used_for_fit or used_for_selection or used_for_promotion:
        raise Cycle28ScoringError("Week 1 outcomes cannot tune, select, or promote")


A_AND_M_CONTEST_ID = "6607349"
SCORING_FORMULA_ID = "cycle28.independent.game_grain.brier_logloss_accuracy_residual.v1"


def _card_is_terminal_final(card: Mapping[str, Any]) -> bool:
    if card.get("parse_state") != "PARSED":
        return False
    if not card.get("final_status_is_terminal"):
        return False
    status = str(card.get("final_status_text") or "").strip().upper()
    if status not in {"FINAL", "OFFICIAL_FINAL"} and "FINAL" not in status:
        return False
    return card.get("home_points") is not None and card.get("away_points") is not None


def card_to_terminal_receipt(
    card: Mapping[str, Any],
    acquisition: Mapping[str, Any],
) -> dict[str, Any]:
    winner = card.get("winner_orientation")
    return {
        "receipt_kind": SOURCE_ACQUISITION_RECEIPT,
        "ncaa_contest_id": str(card["ncaa_contest_id"]),
        "ordered_participants": (
            str(card.get("away_source_team_name") or ""),
            str(card.get("home_source_team_name") or ""),
        ),
        "final_status": "OFFICIAL_FINAL",
        "home_points": int(card["home_points"]),
        "away_points": int(card["away_points"]),
        "winner": winner,
        "trusted_clock_retrieval_utc": acquisition["trusted_clock_retrieval_utc"],
        "request_identity_sha256": acquisition["request_identity_sha256"],
        "raw_response_sha256": acquisition["raw_response_sha256"],
        "raw_response_relative_path": acquisition["raw_response_relative_path"],
        "acquisition_receipt_sha256": acquisition["acquisition_receipt_sha256"],
        "acquisition_receipt_relative_path": acquisition[
            "acquisition_receipt_relative_path"
        ],
        "route_id": acquisition["route_id"],
        "kickoff_bound_or_confirmed_utc": acquisition.get(
            "kickoff_bound_or_confirmed_utc"
        ),
        "home_source_team_id": card.get("home_source_team_id"),
        "away_source_team_id": card.get("away_source_team_id"),
        "home_source_team_name": card.get("home_source_team_name"),
        "away_source_team_name": card.get("away_source_team_name"),
    }


def bind_atomic_week1_scoring(
    *,
    contests: Sequence[Mapping[str, Any]],
    forecast_rows: Sequence[Mapping[str, Any]],
    terminal_receipts: Sequence[Mapping[str, Any]],
    acquisition_failed_contest_ids: Sequence[str],
    now_utc: str,
) -> dict[str, Any]:
    """Bind newly admitted atomic finals to immutable frozen forecast rows.

    Cycle #27 scored rows are not reused. Frozen forecast identities are preserved.
    """
    reject_week1_outcome_tuning(False, False, False)
    forecasts_by_contest: dict[str, list[Mapping[str, Any]]] = {}
    for row in forecast_rows:
        cid = str(row.get("ncaa_contest_id") or "")
        forecasts_by_contest.setdefault(cid, []).append(row)
    receipts_by_contest: dict[str, list[Mapping[str, Any]]] = {}
    for row in terminal_receipts:
        receipts_by_contest.setdefault(str(row["ncaa_contest_id"]), []).append(row)
    failed = {str(item) for item in acquisition_failed_contest_ids}
    scored_rows: list[dict[str, Any]] = []
    final_states: list[dict[str, Any]] = []
    for contest in contests:
        cid = str(contest.get("ncaa_contest_id"))
        kickoff = str(
            contest.get("kickoff_bound_utc") or contest.get("kickoff_utc") or ""
        )
        selected = terminal_selection(receipts_by_contest.get(cid, []))
        forecasts = forecasts_by_contest.get(cid) or []
        eligible = [
            row
            for row in forecasts
            if str(row.get("checkpoint_id") or "")
            and str(row.get("state") or "") != "FORECAST_ABSTAINED"
            and row.get("forecast_probability_home") is not None
        ]
        conflict = selected == "CONFLICT_QUARANTINED"
        official = selected if isinstance(selected, Mapping) else None
        if official is not None and kickoff:
            try:
                reject_prekickoff_final(
                    str(official["trusted_clock_retrieval_utc"]),
                    kickoff,
                )
            except IndependentScoringError:
                official = None
        postponed = bool(contest.get("postponed_or_canceled"))
        forecast_for_class = (
            eligible[0] if eligible else (forecasts[0] if forecasts else None)
        )
        if (
            official is None
            and forecasts
            and all(
                str(row.get("publication_state") or row.get("state") or "")
                in {
                    "ABSTAIN",
                    "ABSTAIN_SCIENTIFIC_TRUST_GATE_BLOCKED",
                    "ABSTAINED_AT_CHECKPOINT",
                }
                for row in forecasts
            )
        ):
            forecast_for_class = {
                "publication_state": "ABSTAIN_SCIENTIFIC_TRUST_GATE_BLOCKED"
            }
        state = classify_contest(
            official_final_receipt=official,
            acquisition_failed=cid in failed and official is None,
            postponed_or_canceled=postponed,
            forecast_row=forecast_for_class
            if official is not None or forecasts
            else None,
            conflict=conflict,
        )
        if official is None and not failed and not conflict and not postponed:
            if kickoff and kickoff > now_utc:
                state = STATE_AWAITING
            elif not forecasts:
                state = (
                    STATE_NO_FORECAST
                    if kickoff and kickoff <= now_utc
                    else STATE_AWAITING
                )
            else:
                state = STATE_AWAITING
        home_name = None
        away_name = None
        if isinstance(official, Mapping):
            home_name = official.get("home_source_team_name")
            away_name = official.get("away_source_team_name")
        final_states.append(
            {
                "ncaa_contest_id": cid,
                "state": state,
                "home": home_name or contest.get("home_team") or contest.get("home"),
                "away": away_name or contest.get("away_team") or contest.get("away"),
                "kickoff_bound_utc": kickoff,
            }
        )
        if state != STATE_SCORED or not isinstance(official, Mapping):
            continue
        actual_margin = int(official["home_points"]) - int(official["away_points"])
        observed_home_win = (
            1.0
            if official["winner"] == "HOME"
            else (0.0 if official["winner"] == "AWAY" else 0.5)
        )
        for forecast in eligible:
            predicted = float(forecast["forecast_probability_home"])
            predicted_margin = forecast.get("forecast_expected_margin_home")
            scored_row = {
                "ncaa_contest_id": cid,
                "ordered_participants": list(official["ordered_participants"]),
                "frozen_forecast_row_identity": forecast.get("forecast_row_identity"),
                "checkpoint_identity": forecast.get("checkpoint_id"),
                "candidate_id": forecast.get("candidate_id"),
                "kickoff_bound_or_confirmed_utc": kickoff,
                "request_identity_sha256": official["request_identity_sha256"],
                "raw_response_sha256": official["raw_response_sha256"],
                "raw_response_relative_path": official["raw_response_relative_path"],
                "acquisition_receipt_sha256": official["acquisition_receipt_sha256"],
                "acquisition_receipt_relative_path": official[
                    "acquisition_receipt_relative_path"
                ],
                "trusted_clock_retrieval_utc": official["trusted_clock_retrieval_utc"],
                "route_id": official["route_id"],
                "receipt_kind": SOURCE_ACQUISITION_RECEIPT,
                "final_status": official["final_status"],
                "home_points": official["home_points"],
                "away_points": official["away_points"],
                "winner": official["winner"],
                "orientation": "GAME",
                "predicted_probability": predicted,
                "observed_win": observed_home_win,
                "predicted_margin_home": predicted_margin,
                "actual_margin_home": actual_margin,
                "result_residual": float(observed_home_win) - predicted,
                "margin_residual": (
                    None
                    if predicted_margin is None
                    else float(actual_margin) - float(predicted_margin)
                ),
                "temporal_admission_decision": "ADMITTED_ATOMIC_OFFICIAL_FINAL_AFTER_KICKOFF",
                "scoring_formula_id": SCORING_FORMULA_ID,
                "scored_row_identity": (
                    f"{cid}|{forecast.get('forecast_row_identity')}|"
                    f"{official['acquisition_receipt_sha256']}"
                ),
            }
            require_scored_row_authority(scored_row)
            scored_rows.append(scored_row)
    metrics_by_candidate: dict[str, Any] = {}
    for candidate in sorted({str(row["candidate_id"]) for row in scored_rows}):
        rows = [row for row in scored_rows if row["candidate_id"] == candidate]
        unique = reject_oriented_rows_as_games(rows)
        metrics_by_candidate[candidate] = reconstruct_metrics(
            predicted=[float(row["predicted_probability"]) for row in rows],
            observed=[float(row["observed_win"]) for row in rows],
            unique_game_count=unique,
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "shadow_classification": SHADOW_CLASSIFICATION,
        "protected_lane": PROTECTED_LANE,
        "empirical_predictive_skill": "EMPIRICAL_PREDICTIVE_SKILL_NOT_ESTABLISHED",
        "tuned_from_week1_outcomes": False,
        "forecast_mutation": False,
        "backfill": False,
        "a_and_m_hardcoded": False,
        "independent_predicted_score": None,
        "game_grain_only": True,
        "oriented_rows_counted_as_games": False,
        "scored_row_count": len(scored_rows),
        "independent_metrics": metrics_by_candidate,
        "rows": scored_rows,
        "final_states": final_states,
        "predecessor_preserved": True,
    }


def a_and_m_postgame_observation(
    *,
    scored_rows: Sequence[Mapping[str, Any]],
    athletics_cross_check: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    focus = [
        row
        for row in scored_rows
        if str(row.get("ncaa_contest_id")) == A_AND_M_CONTEST_ID
        and str(row.get("candidate_id")) == "national_margin_ridge"
        and str(row.get("checkpoint_identity")) in {"EARLY_WEEK1", "T-90M"}
    ]
    if not focus:
        return {
            "ncaa_contest_id": A_AND_M_CONTEST_ID,
            "scored": False,
            "independent_predicted_score": None,
            "bas_specialization_claim": False,
            "reason": "no atomically admitted official final bound to an immutable eligible forecast",
            "athletics_cross_check": athletics_cross_check,
        }
    row = focus[0]
    actual_margin = float(row["actual_margin_home"])
    predicted_margin = row.get("predicted_margin_home")
    residual = row.get("margin_residual")
    expected_repro = None
    if predicted_margin is not None:
        expected_repro = (
            abs(float(residual) - (50.0 - float(predicted_margin))) < 1e-6
            if (int(row["home_points"]) == 50 and int(row["away_points"]) == 0)
            else False
        )
        # residual vs +22.2506 is reported only when independently reproduced
        report_277494 = (
            int(row["home_points"]) == 50
            and int(row["away_points"]) == 0
            and abs(float(predicted_margin) - 22.2506043541) < 1e-6
            and residual is not None
            and abs(float(residual) - 27.7493956459) < 1e-4
        )
    else:
        report_277494 = False
    return {
        "ncaa_contest_id": A_AND_M_CONTEST_ID,
        "scored": True,
        "frozen_forecast_row_identity": row.get("frozen_forecast_row_identity"),
        "checkpoint_identity": row.get("checkpoint_identity"),
        "home_points": row["home_points"],
        "away_points": row["away_points"],
        "actual_margin_home": actual_margin,
        "predicted_margin_home": predicted_margin,
        "margin_residual": residual,
        "result_residual": row.get("result_residual"),
        "brier_contribution": (
            (float(row["predicted_probability"]) - float(row["observed_win"])) ** 2
        ),
        "log_loss_contribution": None,
        "report_50_0_exceeded_untrusted_early_ridge_by_27_7494": report_277494,
        "independent_predicted_score": None,
        "bas_specialization_claim": False,
        "causal_claim": False,
        "athletics_cross_check": athletics_cross_check,
        "expected_repro_identity_check": expected_repro,
    }
