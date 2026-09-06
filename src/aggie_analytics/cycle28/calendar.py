"""Week 1 Sunday/Monday calendar reconciliation and checkpoint classification.

Predecessor schedule and checkpoint records are never rewritten. A wrong
predecessor kickoff may receive a new corrected-calendar identity only when the
real cutoff is still future. Early captures stay EARLY_NON_CHECKPOINT_EVIDENCE.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

CORRECTED_CALENDAR_SCHEMA = "aggie.cycle28.week1_remaining_calendar.v1"
PREDECESSOR_IDENTITY_6618941 = "848cfdf60b74b8004f638fa0d41d7f66fc6d355b232f3f6fa5ea65db3ecfb6a4"

CONTEST_6618941 = "6618941"
CONTEST_6602874 = "6602874"
CONTEST_6620581 = "6620581"
CONTEST_6594400 = "6594400"

DISPOSITION_FROZEN = "FORECAST_FROZEN_AT_VALID_CUTOFF"
DISPOSITION_EVIDENCE = "EVIDENCE_CAPTURED_NO_TRUSTED_FORECAST"
DISPOSITION_ABSTAIN = "ABSTAIN_SCIENTIFIC_TRUST_GATE_BLOCKED"
DISPOSITION_MISSED = "MISSED_CUTOFF_NO_BACKFILL"
DISPOSITION_EARLY = "EARLY_NON_CHECKPOINT_EVIDENCE"
DISPOSITION_CONFLICT = "SOURCE_OR_TIME_CONFLICT_QUARANTINED"
DISPOSITION_FAILED = "ACQUISITION_FAILED_BEFORE_CUTOFF"
DISPOSITION_OPEN = "CAPTURE_ARMED_CUTOFF_STILL_FUTURE"

T24H = timedelta(hours=24)
T90M = timedelta(minutes=90)


class CalendarReconciliationError(ValueError):
    """Raised when a remaining-game calendar claim cannot be admitted."""


def parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise CalendarReconciliationError("kickoff instants must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def cutoff_pair(kickoff_utc: str) -> dict[str, str]:
    kickoff = parse_utc(kickoff_utc)
    return {
        "t24h_cutoff_utc": (kickoff - T24H).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "t90m_cutoff_utc": (kickoff - T90M).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kickoff_utc": kickoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def classify_checkpoint(
    *,
    now_utc: str,
    cutoff_utc: str,
    capture_utc: str | None,
    forecast_frozen: bool,
    predecessor_cutoff_utc: str | None = None,
    official_kickoff_confirmed: bool,
) -> str:
    now = parse_utc(now_utc)
    cutoff = parse_utc(cutoff_utc)
    if not official_kickoff_confirmed:
        return DISPOSITION_CONFLICT
    if capture_utc:
        captured = parse_utc(capture_utc)
        if predecessor_cutoff_utc and captured <= parse_utc(predecessor_cutoff_utc) < cutoff:
            return DISPOSITION_EARLY
        if captured > cutoff:
            return DISPOSITION_MISSED
        if forecast_frozen:
            return DISPOSITION_FROZEN
        return DISPOSITION_EVIDENCE
    if now < cutoff:
        return DISPOSITION_OPEN
    return DISPOSITION_MISSED


def reject_relabel_early_as_t90m(
    *,
    capture_utc: str,
    claimed_cutoff_utc: str,
    corrected_cutoff_utc: str,
) -> None:
    captured = parse_utc(capture_utc)
    claimed = parse_utc(claimed_cutoff_utc)
    corrected = parse_utc(corrected_cutoff_utc)
    if captured <= claimed < corrected:
        raise CalendarReconciliationError(
            "early/wrong-deadline capture cannot be relabeled as the corrected T-90M"
        )


def reject_backfill(now_utc: str, cutoff_utc: str, creating_new_capture: bool) -> None:
    if creating_new_capture and parse_utc(now_utc) >= parse_utc(cutoff_utc):
        raise CalendarReconciliationError("MISSED_CUTOFF_NO_BACKFILL")


def reject_sunday_into_monday_fitted_path(
    *,
    target_contest_id: str,
    feature_update_from_sunday_outcome: bool,
    predeclared_update_rule: bool,
) -> None:
    if (
        target_contest_id == CONTEST_6594400
        and feature_update_from_sunday_outcome
        and not predeclared_update_rule
    ):
        raise CalendarReconciliationError(
            "Sunday outcomes cannot enter the Monday fitted path without a predeclared rule"
        )


def reconcile_washington_state_washington(
    *,
    now_utc: str,
    predecessor_clock_text: str,
    predecessor_bound_utc: str,
    official_institutional_kickoff_utc: str,
    predecessor_t90m_capture_utc: str | None,
) -> dict[str, Any]:
    if predecessor_clock_text == "04:00 AM" and official_institutional_kickoff_utc == "2026-09-06T20:00:00Z":
        conflict = True
    else:
        conflict = predecessor_bound_utc != official_institutional_kickoff_utc
    cutoffs = cutoff_pair(official_institutional_kickoff_utc)
    t90m_state = classify_checkpoint(
        now_utc=now_utc,
        cutoff_utc=cutoffs["t90m_cutoff_utc"],
        capture_utc=None,
        forecast_frozen=False,
        predecessor_cutoff_utc="2026-09-06T06:30:00Z",
        official_kickoff_confirmed=True,
    )
    early_state = None
    if predecessor_t90m_capture_utc:
        captured = parse_utc(predecessor_t90m_capture_utc)
        claimed = parse_utc("2026-09-06T06:30:00Z")
        corrected = parse_utc(cutoffs["t90m_cutoff_utc"])
        if captured <= claimed < corrected:
            early_state = DISPOSITION_EARLY
    return {
        "ncaa_contest_id": CONTEST_6618941,
        "predecessor_contest_identity": PREDECESSOR_IDENTITY_6618941,
        "predecessor_source_published_clock_text": predecessor_clock_text,
        "predecessor_kickoff_utc_conservative_lower_bound": predecessor_bound_utc,
        "predecessor_preserved": True,
        "predecessor_rewritten": False,
        "official_institutional_kickoff_utc": official_institutional_kickoff_utc,
        "corrected_calendar_identity_kind": "CORRECTED_CALENDAR_SUCCESSOR",
        "conflict": conflict,
        "conflict_disposition": "CONFLICT_REVIEW_REQUIRED" if conflict else "CONSISTENT",
        "corrected_cutoffs": cutoffs,
        "real_t90m_disposition": t90m_state,
        "predecessor_t90m_capture_disposition": early_state,
        "real_t90m_was_met": t90m_state
        in {DISPOSITION_FROZEN, DISPOSITION_EVIDENCE, DISPOSITION_ABSTAIN},
    }


REMAINING_GAMES: tuple[dict[str, Any], ...] = (
    {
        "ncaa_contest_id": CONTEST_6618941,
        "matchup": "Washington State at Washington",
        "official_kickoff_utc": "2026-09-06T20:00:00Z",
        "site": "Husky Stadium, Seattle, Wash.",
        "site_state": "HOME_TEAM_SITE",
        "ordered_participants": ("Washington St.", "Washington"),
    },
    {
        "ncaa_contest_id": CONTEST_6602874,
        "matchup": "Notre Dame vs Wisconsin at Lambeau Field",
        "official_kickoff_utc": "2026-09-06T23:30:00Z",
        "site": "Lambeau Field, Green Bay, Wis.",
        "site_state": "NEUTRAL",
        "ordered_participants": ("Notre Dame", "Wisconsin"),
    },
    {
        "ncaa_contest_id": CONTEST_6620581,
        "matchup": "Louisville vs Ole Miss at Nissan Stadium",
        "official_kickoff_utc": "2026-09-06T23:30:00Z",
        "site": "Nissan Stadium, Nashville, TN",
        "site_state": "NEUTRAL",
        "ordered_participants": ("Louisville", "Ole Miss"),
    },
    {
        "ncaa_contest_id": CONTEST_6594400,
        "matchup": "SMU at Florida State",
        "official_kickoff_utc": "2026-09-07T23:30:00Z",
        "site": "Doak S. Campbell Stadium, Tallahassee, Fla.",
        "site_state": "HOME_TEAM_SITE",
        "ordered_participants": ("SMU", "Florida St."),
    },
)


def remaining_game_cutoffs() -> dict[str, dict[str, str]]:
    return {
        row["ncaa_contest_id"]: cutoff_pair(row["official_kickoff_utc"])
        for row in REMAINING_GAMES
    }


def live_owner_identity_match(
    *,
    reported: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> bool:
    """PID alone is never ownership proof."""

    keys = (
        "pid",
        "executable",
        "command_line",
        "creation_utc",
        "checkpoint",
        "contest_ids",
        "cutoff_utc",
    )
    if not all(key in reported and key in observed for key in keys):
        return False
    if reported["pid"] != observed["pid"]:
        return False
    if reported["executable"] != observed["executable"]:
        return False
    if str(reported["command_line"]) != str(observed["command_line"]):
        return False
    if reported["creation_utc"] != observed["creation_utc"]:
        return False
    if reported["checkpoint"] != observed["checkpoint"]:
        return False
    if list(reported["contest_ids"]) != list(observed["contest_ids"]):
        return False
    if reported["cutoff_utc"] != observed["cutoff_utc"]:
        return False
    return True
