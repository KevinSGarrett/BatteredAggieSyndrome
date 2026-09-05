"""Independent current-opponent and temporal-order reconstruction."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping


def _nonempty_id(value: object, *, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} must be a nonempty identifier")
    return text


def _parse_utc(value: str, *, source_timezone: str | None = None) -> datetime:
    text = value.strip()
    if not text:
        raise ValueError("timestamp is empty")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        if not source_timezone:
            raise ValueError("timezone-naive timestamp requires explicit source timezone authority")
        if source_timezone.upper() not in {"UTC", "Z", "+00:00"}:
            raise ValueError("unproven source timezone cannot be auto-assigned to UTC")
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def temporal_order_ok(
    known_at_utc: str,
    cutoff_utc: str,
    *,
    acquisition_utc: str | None = None,
    source_timezone: str | None = None,
) -> bool:
    known = _parse_utc(known_at_utc, source_timezone=source_timezone)
    cutoff = _parse_utc(cutoff_utc, source_timezone=source_timezone)
    if known > cutoff:
        return False
    if acquisition_utc is not None and _parse_utc(acquisition_utc, source_timezone=source_timezone) > cutoff:
        return False
    return True


def current_opponent_bound(
    target_row: Mapping[str, object],
    current_contest: Mapping[str, object],
) -> dict[str, object]:
    try:
        target_team = _nonempty_id(target_row.get("team_key"), field="team_key")
        contest_home = _nonempty_id(current_contest.get("home_team_key"), field="home_team_key")
        contest_away = _nonempty_id(current_contest.get("away_team_key"), field="away_team_key")
    except ValueError as exc:
        return {
            "bound": False,
            "reason": f"EMPTY_IDENTIFIER:{exc}",
            "required_opponent": None,
        }
    contest_id = str(current_contest.get("contest_id") or "").strip()
    if not contest_id:
        return {
            "bound": False,
            "reason": "EMPTY_CONTEST_ID",
            "required_opponent": None,
        }
    if target_team not in {contest_home, contest_away}:
        return {
            "bound": False,
            "reason": "TARGET_NOT_IN_CURRENT_CONTEST",
            "required_opponent": None,
        }
    required_opponent = contest_away if target_team == contest_home else contest_home
    copied_opponent = str(target_row.get("opponent_key") or "").strip()
    if not copied_opponent:
        return {
            "bound": False,
            "reason": "EMPTY_OPPONENT_ID",
            "required_opponent": required_opponent,
        }
    historical_transplant = bool(target_row.get("copied_from_terminal_historical_row"))
    bound = copied_opponent == required_opponent and not historical_transplant
    return {
        "bound": bound,
        "reason": "" if bound else "CURRENT_OPPONENT_NOT_BOUND",
        "required_opponent": required_opponent,
        "copied_opponent": copied_opponent,
        "historical_transplant": historical_transplant,
        "contest_id": contest_id,
    }


def field_readiness(
    required_fields: Mapping[str, object],
    *,
    missingness_is_not_evidence: bool = True,
) -> dict[str, object]:
    missing = [name for name, value in required_fields.items() if value in (None, "", [])]
    ood = [
        name
        for name, value in required_fields.items()
        if str(value).startswith("OOD_")
    ]
    ready = not missing and not ood
    return {
        "ready": ready,
        "missing_fields": missing,
        "ood_fields": ood,
        "missingness_treated_as_evidence": False if missingness_is_not_evidence else True,
        "abstain_reason": (
            ""
            if ready
            else ("MISSING_REQUIRED_FIELDS" if missing else "OOD_REQUIRED_FIELDS")
        ),
    }
