"""Actual-clock Week 2 closeout. Historical deadlines are never re-armed."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

TAMU_ASU_HISTORICAL = {
    "contest_identity": "Texas A&M vs Arizona State",
    "kickoff_local_described": "2026-09-12",
    "t24h_deadline_utc": "2026-09-11T16:00:00Z",
    "t90m_deadline_utc": "2026-09-12T14:30:00Z",
    "rearm_forbidden": True,
    "backfill_forbidden": True,
    "missouri_state_identity_forbidden": True,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def deadline_disposition(
    *,
    now: datetime,
    deadline_utc: str,
    evidence_present: bool,
    freeze_present: bool,
    captured_after_deadline: bool,
) -> str:
    deadline = datetime.fromisoformat(deadline_utc.replace("Z", "+00:00"))
    if now < deadline:
        return (
            "FUTURE_NOT_YET_ELIGIBLE" if not evidence_present else "EVIDENCE_CAPTURED"
        )
    if freeze_present:
        return "FORECAST_FROZEN"
    if evidence_present and captured_after_deadline:
        return "EVIDENCE_CAPTURED_LATE_TRUE_TIMESTAMP"
    if evidence_present:
        return "EVIDENCE_CAPTURED"
    return "MISSED_CUTOFF_NO_BACKFILL"


def closeout_row(
    contest: Mapping[str, Any],
    *,
    now: datetime,
    t24h: str | None,
    t90m: str | None,
    evidence: Mapping[str, Any] | None = None,
    freeze: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    evidence = evidence or {}
    freeze = freeze or {}
    t24h_state = (
        deadline_disposition(
            now=now,
            deadline_utc=t24h,
            evidence_present=bool(evidence.get("t24h")),
            freeze_present=bool(freeze.get("t24h")),
            captured_after_deadline=bool(evidence.get("t24h_late")),
        )
        if t24h
        else "CUTOFF_UNKNOWN"
    )
    t90m_state = (
        deadline_disposition(
            now=now,
            deadline_utc=t90m,
            evidence_present=bool(evidence.get("t90m")),
            freeze_present=bool(freeze.get("t90m")),
            captured_after_deadline=bool(evidence.get("t90m_late")),
        )
        if t90m
        else "CUTOFF_UNKNOWN"
    )
    identity = str(contest.get("canonical_contest_id") or contest.get("label") or "")
    if (
        "missouri" in identity.casefold()
        and "arizona" in str(contest.get("label") or "").casefold()
    ):
        raise ValueError(
            "September 5 Missouri State identity cannot label another game"
        )
    return {
        "contest": dict(contest),
        "as_of_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "t24h_deadline_utc": t24h,
        "t90m_deadline_utc": t90m,
        "t24h_disposition": t24h_state,
        "t90m_disposition": t90m_state,
        "forecast_classification": "UNTRUSTED_SHADOW",
        "retroactive_forecast_forbidden": True,
        "week2_outcomes_do_not_tune_or_select": True,
        "official_finals_score_only": True,
    }


def cutoffs_from_kickoff_epoch(epoch: int | None, *, now: datetime) -> dict[str, Any]:
    """Derive T-24H / T-90M from official kickoff. Do not copy calendar prose."""

    if epoch is None:
        return {
            "t24h_deadline_utc": None,
            "t90m_deadline_utc": None,
            "t24h_disposition": "CUTOFF_UNKNOWN",
            "t90m_disposition": "CUTOFF_UNKNOWN",
            "kickoff_utc": None,
            "cutoff_source": "KICKOFF_EPOCH_MISSING",
        }
    kickoff = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    t24h = kickoff - timedelta(hours=24)
    t90m = kickoff - timedelta(minutes=90)
    dummy = {"canonical_contest_id": "epoch", "label": "epoch"}
    row = closeout_row(
        dummy,
        now=now,
        t24h=t24h.strftime("%Y-%m-%dT%H:%M:%SZ"),
        t90m=t90m.strftime("%Y-%m-%dT%H:%M:%SZ"),
        evidence=None,
        freeze=None,
    )
    return {
        "t24h_deadline_utc": row["t24h_deadline_utc"],
        "t90m_deadline_utc": row["t90m_deadline_utc"],
        "t24h_disposition": row["t24h_disposition"],
        "t90m_disposition": row["t90m_disposition"],
        "kickoff_utc": kickoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cutoff_source": "NCAA_START_TIME_EPOCH",
        "forecast_classification": "UNTRUSTED_SHADOW",
        "retroactive_forecast_forbidden": True,
    }


def historical_tamu_asu_row(
    now: datetime, *, evidence: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    return {
        **TAMU_ASU_HISTORICAL,
        **closeout_row(
            {
                "label": TAMU_ASU_HISTORICAL["contest_identity"],
                "canonical_contest_id": "TAMU-ASU-2026-09-12",
            },
            now=now,
            t24h=TAMU_ASU_HISTORICAL["t24h_deadline_utc"],
            t90m=TAMU_ASU_HISTORICAL["t90m_deadline_utc"],
            evidence=evidence,
        ),
        "rearm_attempted": False,
        "invented_forecast": False,
    }
