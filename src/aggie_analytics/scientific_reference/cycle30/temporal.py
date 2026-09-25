"""Independent Cycle #30 temporal reconstruction.

Challenges the producer specification: midnight UTC is not date-only unless
declared. Conservative bounds are not publication proof.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PRECISION_INSTANT = "INSTANT"
PRECISION_DATE_ONLY = "DATE_ONLY"
PRECISION_UNKNOWN = "UNKNOWN"


class IndependentTemporalError(ValueError):
    """Raised when independent reconstruction cannot admit a timestamp."""


def parse_aware_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise IndependentTemporalError("timestamp must be a nonempty string")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if _lacks_offset(text):
        raise IndependentTemporalError(
            "naive or offset-less timestamps are not temporal authority"
        )
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise IndependentTemporalError(f"malformed timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise IndependentTemporalError("naive timestamps are not temporal authority")
    return parsed.astimezone(timezone.utc)


def _lacks_offset(text: str) -> bool:
    if text.endswith(("Z", "z")):
        return False
    if "+" in text[10:]:
        return False
    if text.count("-") >= 3 and (text.rfind("-") > 10):
        tail = text[text.rfind("-") :]
        return not (len(tail) >= 3 and tail[1].isdigit())
    return True


def clock_is_utc_midnight(instant: datetime) -> bool:
    utc = instant.astimezone(timezone.utc)
    return (
        utc.hour == 0 and utc.minute == 0 and utc.second == 0 and utc.microsecond == 0
    )


def resolve_precision(declared_precision: str | None, instant: datetime | None) -> str:
    if declared_precision in {
        PRECISION_INSTANT,
        PRECISION_DATE_ONLY,
        PRECISION_UNKNOWN,
    }:
        return declared_precision
    if declared_precision:
        raise IndependentTemporalError(f"unknown date precision {declared_precision}")
    if instant is not None and clock_is_utc_midnight(instant):
        return PRECISION_UNKNOWN
    if instant is not None:
        return PRECISION_INSTANT
    return PRECISION_UNKNOWN


def reject_midnight_as_date_only(instant: datetime, claimed_date_only: bool) -> None:
    if clock_is_utc_midnight(instant) and claimed_date_only:
        raise IndependentTemporalError(
            "exact 00:00 UTC is not automatically a date-only record"
        )


def earliest_start_bound(
    instant: datetime, *, precision: str, policy: Mapping[str, Any] | None = None
) -> datetime:
    policy = policy or {}
    resolved = resolve_precision(precision, instant)
    if resolved in {PRECISION_DATE_ONLY, PRECISION_UNKNOWN}:
        return instant + timedelta(
            days=int(policy.get("date_only_start_offset_days", -1))
        )
    return instant


def completion_bound(
    instant: datetime, *, precision: str, policy: Mapping[str, Any] | None = None
) -> datetime:
    policy = policy or {}
    resolved = resolve_precision(precision, instant)
    if resolved == PRECISION_DATE_ONLY:
        return instant + timedelta(
            days=int(policy.get("date_only_completion_offset_days", 2))
        )
    hours = float(policy.get("published_duration_hours", 12.0))
    return instant + timedelta(hours=hours)


def reject_dst_ambiguous_local(local_text: str, zone_name: str) -> None:
    try:
        zone = ZoneInfo(zone_name)
    except ZoneInfoNotFoundError as exc:
        raise IndependentTemporalError(f"unknown IANA zone: {zone_name}") from exc
    naive = datetime.fromisoformat(local_text)
    if naive.tzinfo is not None:
        raise IndependentTemporalError("local DST check expects a naive civil datetime")
    first = naive.replace(tzinfo=zone, fold=0)
    second = naive.replace(tzinfo=zone, fold=1)
    if first.astimezone(timezone.utc) != second.astimezone(timezone.utc):
        raise IndependentTemporalError(
            "DST-ambiguous local timestamp is not temporal authority"
        )
