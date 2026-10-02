"""Independent Cycle #29 temporal reconstruction.

Must not import ``aggie_analytics.cycle29`` or any producer helper.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DATE_ONLY_CLOCK = "00:00"
DEFAULT_DATE_ONLY_START_OFFSET_DAYS = -1
DEFAULT_DATE_ONLY_COMPLETION_OFFSET_DAYS = 2
DEFAULT_PUBLISHED_DURATION_HOURS = 12.0


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


def is_date_only_utc_midnight(instant: datetime) -> bool:
    utc = instant.astimezone(timezone.utc)
    return (
        utc.strftime("%H:%M") == DATE_ONLY_CLOCK
        and utc.second == 0
        and utc.microsecond == 0
    )


def earliest_start_bound(
    instant: datetime, policy: Mapping[str, Any] | None = None
) -> datetime:
    policy = policy or {}
    if is_date_only_utc_midnight(instant):
        offset = int(
            policy.get(
                "date_only_start_offset_days", DEFAULT_DATE_ONLY_START_OFFSET_DAYS
            )
        )
        return instant + timedelta(days=offset)
    return instant


def completion_bound(
    instant: datetime, policy: Mapping[str, Any] | None = None
) -> datetime:
    policy = policy or {}
    if is_date_only_utc_midnight(instant):
        offset = int(
            policy.get(
                "date_only_completion_offset_days",
                DEFAULT_DATE_ONLY_COMPLETION_OFFSET_DAYS,
            )
        )
        return instant + timedelta(days=offset)
    hours = float(
        policy.get("published_duration_hours", DEFAULT_PUBLISHED_DURATION_HOURS)
    )
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


def cutoff_span_classification(
    *,
    request_start_utc: str,
    request_end_utc: str,
    cutoff_utc: str,
) -> str:
    start = parse_aware_utc(request_start_utc)
    end = parse_aware_utc(request_end_utc)
    cutoff = parse_aware_utc(cutoff_utc)
    if end <= cutoff:
        return "ENDED_AT_OR_BEFORE_CUTOFF"
    if start <= cutoff < end:
        return "START_BEFORE_CUTOFF_END_AFTER_CUTOFF"
    return "STARTED_AFTER_CUTOFF"
