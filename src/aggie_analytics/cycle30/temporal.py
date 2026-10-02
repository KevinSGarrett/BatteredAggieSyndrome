"""Aware UTC temporal parsing with explicit source precision.

Exact 00:00 UTC is never automatically a date-only record. Precision is a
declared field. Conservative completion bounds are labeled assumptions, not
publication proof.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PRECISION_INSTANT = "INSTANT"
PRECISION_DATE_ONLY = "DATE_ONLY"
PRECISION_UNKNOWN = "UNKNOWN"
ALLOWED_PRECISION = {PRECISION_INSTANT, PRECISION_DATE_ONLY, PRECISION_UNKNOWN}

DEFAULT_DATE_ONLY_START_OFFSET_DAYS = -1
DEFAULT_DATE_ONLY_COMPLETION_OFFSET_DAYS = 2
DEFAULT_PUBLISHED_DURATION_HOURS = 12.0
ASSUMPTION_CONSERVATIVE_COMPLETION = "ASSUMPTION_CONSERVATIVE_COMPLETION_BOUND_V1"


class TemporalError(ValueError):
    """Raised when a timestamp cannot be admitted as an aware UTC instant."""


def parse_aware_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise TemporalError("timestamp must be a nonempty string")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if _lacks_offset(text):
        raise TemporalError(
            "naive or offset-less timestamps are not temporal authority"
        )
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise TemporalError(f"malformed timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise TemporalError("naive timestamps are not temporal authority")
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


def reject_lexical_order(left: str, right: str) -> tuple[datetime, datetime]:
    """Parse both instants; string order is not consulted."""

    return parse_aware_utc(left), parse_aware_utc(right)


def clock_is_utc_midnight(instant: datetime) -> bool:
    utc = instant.astimezone(timezone.utc)
    return (
        utc.hour == 0 and utc.minute == 0 and utc.second == 0 and utc.microsecond == 0
    )


def resolve_precision(
    *,
    declared_precision: str | None,
    instant: datetime | None = None,
) -> str:
    if declared_precision in ALLOWED_PRECISION:
        return declared_precision
    if declared_precision:
        raise TemporalError(f"unknown date precision {declared_precision}")
    # Midnight is not inferred as date-only. Absence is UNKNOWN.
    if instant is not None and clock_is_utc_midnight(instant):
        return PRECISION_UNKNOWN
    if instant is not None:
        return PRECISION_INSTANT
    return PRECISION_UNKNOWN


def earliest_start_bound(
    instant: datetime,
    *,
    precision: str,
    policy: Mapping[str, Any] | None = None,
) -> tuple[datetime, str]:
    policy = policy or {}
    resolved = resolve_precision(declared_precision=precision, instant=instant)
    if resolved == PRECISION_DATE_ONLY:
        offset = int(
            policy.get(
                "date_only_start_offset_days", DEFAULT_DATE_ONLY_START_OFFSET_DAYS
            )
        )
        return instant + timedelta(days=offset), ASSUMPTION_CONSERVATIVE_COMPLETION
    if resolved == PRECISION_UNKNOWN:
        offset = int(
            policy.get(
                "date_only_start_offset_days", DEFAULT_DATE_ONLY_START_OFFSET_DAYS
            )
        )
        return instant + timedelta(days=offset), "UNKNOWN_PRECISION_CONSERVATIVE_BOUND"
    return instant, "DECLARED_INSTANT"


def completion_bound(
    instant: datetime,
    *,
    precision: str,
    policy: Mapping[str, Any] | None = None,
) -> tuple[datetime, str]:
    """Labeled conservative bound. Not proof a result was published."""

    policy = policy or {}
    resolved = resolve_precision(declared_precision=precision, instant=instant)
    if resolved == PRECISION_DATE_ONLY:
        offset = int(
            policy.get(
                "date_only_completion_offset_days",
                DEFAULT_DATE_ONLY_COMPLETION_OFFSET_DAYS,
            )
        )
        return instant + timedelta(days=offset), ASSUMPTION_CONSERVATIVE_COMPLETION
    hours = float(
        policy.get("published_duration_hours", DEFAULT_PUBLISHED_DURATION_HOURS)
    )
    return instant + timedelta(hours=hours), ASSUMPTION_CONSERVATIVE_COMPLETION


def reject_midnight_as_date_only(instant: datetime, claimed_date_only: bool) -> None:
    if clock_is_utc_midnight(instant) and claimed_date_only:
        raise TemporalError("exact 00:00 UTC is not automatically a date-only record")


def reject_dst_ambiguous_local(local_text: str, zone_name: str) -> None:
    try:
        zone = ZoneInfo(zone_name)
    except ZoneInfoNotFoundError as exc:
        raise TemporalError(f"unknown IANA zone: {zone_name}") from exc
    naive = datetime.fromisoformat(local_text)
    if naive.tzinfo is not None:
        raise TemporalError("local DST check expects a naive civil datetime")
    first = naive.replace(tzinfo=zone, fold=0)
    second = naive.replace(tzinfo=zone, fold=1)
    if first.astimezone(timezone.utc) != second.astimezone(timezone.utc):
        raise TemporalError("DST-ambiguous local timestamp is not temporal authority")


def reject_invented_tolerance(
    *, calendar_window: Mapping[str, Any], claimed_tolerance: Any
) -> None:
    if claimed_tolerance not in {None, "", 0, False}:
        if "invented" in str(claimed_tolerance).lower() or claimed_tolerance is True:
            raise TemporalError("checkpoint tolerance cannot be invented")
    allowed = calendar_window.get("allowed_tolerance")
    if allowed is None and claimed_tolerance not in {None, "", 0, False}:
        raise TemporalError("checkpoint window must come from calendar authority")
