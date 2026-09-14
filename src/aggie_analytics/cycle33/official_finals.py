"""Detect competing official-final observations before identity deduplication.

Pregame/live/cancelled rows are preserved and are not admitted finals.
Lawful pre→live→final progression is not a competing-final conflict.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence


class OfficialFinalConflict(ValueError):
    """Raised when competing finals cannot be first-won or last-won."""


def _contest_id(row: Mapping[str, Any]) -> str:
    return str(row.get("ncaa_contest_id") or row.get("ncaa_com_contest_id") or "")


def _score_tuple(row: Mapping[str, Any]) -> tuple[Any, Any, Any]:
    return (
        row.get("home_points"),
        row.get("away_points"),
        row.get("winner") or row.get("winning_side"),
    )


def _finite_nonneg_int(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return False
    try:
        number = int(value)
    except (TypeError, ValueError):
        return False
    return number == value and number >= 0


def observation_lifecycle(row: Mapping[str, Any]) -> str:
    state = str(row.get("game_state") or "").strip().upper()
    display = str(row.get("status_code_display") or "").strip().casefold()
    terminal = str(row.get("terminal_state") or "")
    if state in {"C"} or display in {"cancelled", "canceled"}:
        return "CANCELLED"
    if display in {"postponed"} or state in {"D"}:
        return "POSTPONED"
    if state in {"P"} or display in {"pre", "pregame"}:
        return "PREGAME"
    if state in {"L"} or display in {"live", "inprogress", "in progress"}:
        return "LIVE"
    if (
        (state == "F" and display == "final")
        or terminal == "TERMINAL_STATUS_ESTABLISHED"
        or display == "final"
    ):
        return "FINAL"
    return "STATUS_UNKNOWN"


def is_eligible_official_final(row: Mapping[str, Any]) -> bool:
    if observation_lifecycle(row) != "FINAL":
        return False
    return _finite_nonneg_int(row.get("home_points")) and _finite_nonneg_int(
        row.get("away_points")
    )


def competing_observations(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Preserve every observation. Admit only source-bound official finals."""

    preserved = [dict(row) for row in rows]
    by_id: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    unlabeled = 0
    for row in preserved:
        cid = _contest_id(row)
        if not cid:
            unlabeled += 1
            continue
        if cid not in by_id:
            by_id[cid] = []
            order.append(cid)
        by_id[cid].append(dict(row))
    unique: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    nonfinal_only: list[dict[str, Any]] = []
    for cid in order:
        group = by_id[cid]
        finals = [item for item in group if is_eligible_official_final(item)]
        if not finals:
            nonfinal_only.append(
                {
                    "ncaa_contest_id": cid,
                    "observation_count": len(group),
                    "lifecycles": sorted(
                        {observation_lifecycle(item) for item in group}
                    ),
                    "reason": "NO_ELIGIBLE_OFFICIAL_FINAL",
                }
            )
            continue
        scores = {_score_tuple(item) for item in finals}
        teams = {
            (
                str(item.get("home_name") or item.get("home_canonical_team_id") or ""),
                str(item.get("away_name") or item.get("away_canonical_team_id") or ""),
            )
            for item in finals
        }
        if len(scores) > 1 or len(teams) > 1:
            quarantined.append(
                {
                    "ncaa_contest_id": cid,
                    "observation_count": len(group),
                    "eligible_final_count": len(finals),
                    "reason": "COMPETING_OFFICIAL_FINALS",
                    "observations": group,
                    "lawful_progression_not_conflict": True,
                }
            )
            continue
        unique.append(finals[0])
    return {
        "observation_count": len(rows),
        "unique_contest_count": len(order),
        "discovered_contest_count": len(order),
        "unlabeled_observation_count": unlabeled,
        "admitted_unique_games": unique,
        "admitted_official_finals": unique,
        "quarantined_conflicts": quarantined,
        "nonfinal_contests": nonfinal_only,
        "first_win_forbidden": True,
        "last_win_forbidden": True,
        "pregame_live_not_admitted_as_final": True,
        "preserved_observations": preserved,
    }


def require_no_conflicts(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = competing_observations(rows)
    if result["quarantined_conflicts"]:
        ids = [row["ncaa_contest_id"] for row in result["quarantined_conflicts"]]
        raise OfficialFinalConflict(f"competing official finals: {ids}")
    return result["admitted_unique_games"]
