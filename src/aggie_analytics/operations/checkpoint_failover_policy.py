"""Unapplied, side-effect-free checkpoint failover decision policy.

Integration must supply a verified completion receipt, process identity and real
progress timestamp. A START log or existing filename is not a verified receipt.
The caller must acquire an exclusive lease before any START_RETRY, pin the runner
and use bounded acquisitions. This module does not launch, stop or certify runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str


def utc(value: datetime, name: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{name} must be an aware datetime")
    return value.astimezone(timezone.utc)


def decide(
    *,
    now: datetime,
    wake: datetime,
    cutoff: datetime,
    capture_window_open: datetime,
    primary_alive: bool,
    last_progress: datetime | None,
    completion_receipt_verified: bool,
    completed_at: datetime | None,
    attempts: int,
    max_attempts: int = 3,
    required_attempt_budget: timedelta = timedelta(minutes=5),
    progress_timeout: timedelta = timedelta(minutes=6),
) -> Decision:
    """Decide conservatively; no late run is called an on-time checkpoint.

    STALLED_PRIMARY requires ownership/recovery investigation, not a concurrent
    duplicate launch. Fresh progress never means completion. Receipt verification
    must bind the exact contest/cohort, checkpoint, run and evidence identities;
    a valid hash alone is insufficient. Retry budget includes lease acquisition,
    process startup, collection, writing and independent receipt verification.
    """
    now, wake, cutoff = utc(now, "now"), utc(wake, "wake"), utc(cutoff, "cutoff")
    capture_window_open = utc(capture_window_open, "capture_window_open")
    if wake >= cutoff:
        raise ValueError("wake must precede cutoff")
    if not capture_window_open <= wake < cutoff:
        raise ValueError("capture window must open no later than wake")
    if type(primary_alive) is not bool or type(completion_receipt_verified) is not bool:
        raise ValueError("state flags must be booleans")
    if type(attempts) is not int or type(max_attempts) is not int:
        raise ValueError("attempt counts must be integers")
    if attempts < 0 or max_attempts < 1 or attempts > max_attempts:
        raise ValueError("invalid attempt counts")
    if required_attempt_budget <= timedelta(0) or progress_timeout <= timedelta(0):
        raise ValueError("budgets must be positive")
    if last_progress is not None:
        last_progress = utc(last_progress, "last_progress")
        if last_progress > now:
            raise ValueError("future progress is not valid observation evidence")
    if completed_at is not None:
        completed_at = utc(completed_at, "completed_at")
        if completed_at > now:
            raise ValueError("completion cannot be in the future")
    if completion_receipt_verified:
        if completed_at is None:
            raise ValueError("verified completion requires its completion instant")
        if completed_at < capture_window_open:
            raise ValueError(
                "receipt predates this checkpoint's permitted capture window"
            )
        if completed_at <= cutoff:
            return Decision("COMPLETE", "verified receipt completed by cutoff")
        return Decision("MISSED_CUTOFF_NO_BACKFILL", "receipt completed after cutoff")
    if now >= cutoff:
        return Decision("MISSED_CUTOFF_NO_BACKFILL", "no verified completion by cutoff")
    if now < wake:
        return Decision("WAIT", "wake has not arrived")
    if primary_alive:
        if last_progress is None or now - last_progress > progress_timeout:
            return Decision(
                "STALLED_PRIMARY", "verify ownership and recover; do not duplicate"
            )
        return Decision("MONITOR_PRIMARY", "live progress is not a completion receipt")
    if attempts >= max_attempts:
        return Decision(
            "RETRY_BUDGET_EXHAUSTED", "do not invent a successful checkpoint"
        )
    if now + required_attempt_budget > cutoff:
        return Decision(
            "INSUFFICIENT_TIME_FOR_RETRY", "do not launch guaranteed-late recovery"
        )
    return Decision(
        "START_RETRY_AFTER_EXCLUSIVE_LEASE", "dead primary; retry can fit before cutoff"
    )
