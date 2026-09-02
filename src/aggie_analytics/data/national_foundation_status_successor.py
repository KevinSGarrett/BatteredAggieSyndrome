"""National-foundation scientific successor: structured status, not notes substring."""

from __future__ import annotations

from typing import Any, Mapping

FALSE_QUARANTINE_GAME_ID = "SRC-002:GAME:312472199"
STRUCTURED_NON_FINAL_STATUS = frozenset(
    {"canceled", "cancelled", "postponed", "suspended"}
)
PREDECESSOR_NON_FINAL_TOKENS = ("canceled", "cancelled", "postponed", "suspended")


def _text(value: object) -> str:
    return str(value or "").strip()


def predecessor_substring_non_final_reason(row: Mapping[str, Any]) -> str | None:
    notes = " ".join(
        filter(None, (_text(row.get("notes")), _text(row.get("seasonType"))))
    ).lower()
    for token in PREDECESSOR_NON_FINAL_TOKENS:
        if token in notes:
            return f"source row carries a {token} marker"
    return None


def structured_non_final_reason(row: Mapping[str, Any]) -> str | None:
    status = _text(row.get("status") or row.get("gameStatus")).lower()
    if status in STRUCTURED_NON_FINAL_STATUS:
        return f"structured_status:{status}"
    completed = bool(row.get("completed"))
    home_points = row.get("homePoints")
    away_points = row.get("awayPoints")
    if not completed:
        if home_points is not None or away_points is not None:
            return "scores_without_completion"
        return "not_completed"
    if home_points is None or away_points is None:
        return "completed_without_scores"
    return None


def classify_status_successor(row: Mapping[str, Any]) -> dict[str, Any]:
    game_id = _text(row.get("canonical_game_id") or row.get("id"))
    predecessor = predecessor_substring_non_final_reason(row)
    structured = structured_non_final_reason(row)
    completed = bool(row.get("completed"))
    home_points = row.get("homePoints")
    away_points = row.get("awayPoints")
    false_quarantine = (
        game_id == FALSE_QUARANTINE_GAME_ID
        and predecessor is not None
        and structured is None
        and completed
        and home_points is not None
        and away_points is not None
    )
    if structured is not None:
        disposition = "QUARANTINE_STRUCTURED_NON_FINAL"
    elif false_quarantine:
        disposition = "RESTORE_FALSE_SUBSTRING_QUARANTINE"
    elif predecessor is not None and structured is None:
        disposition = "KEEP_COMPLETED_IGNORE_INCIDENTAL_NOTE_TOKEN"
    else:
        disposition = "ADMIT_COMPLETED"
    return {
        "canonical_game_id": game_id,
        "predecessor_substring_reason": predecessor,
        "structured_reason": structured,
        "false_quarantine_corrected": false_quarantine,
        "disposition": disposition,
        "protected_season": int(row.get("season") or 0) in {2024, 2025},
    }
