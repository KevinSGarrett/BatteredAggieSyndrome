"""Detect competing official-final observations before identity deduplication."""

from __future__ import annotations

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


def competing_observations(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Group every observation. Conflicts quarantine; they do not first-win."""

    by_id: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for row in rows:
        cid = _contest_id(row)
        if not cid:
            continue
        if cid not in by_id:
            by_id[cid] = []
            order.append(cid)
        by_id[cid].append(dict(row))
    unique: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    for cid in order:
        group = by_id[cid]
        scores = {_score_tuple(item) for item in group}
        teams = {
            (
                str(item.get("home_name") or item.get("home_canonical_team_id") or ""),
                str(item.get("away_name") or item.get("away_canonical_team_id") or ""),
            )
            for item in group
        }
        if len(scores) > 1 or len(teams) > 1:
            quarantined.append(
                {
                    "ncaa_contest_id": cid,
                    "observation_count": len(group),
                    "reason": "COMPETING_OFFICIAL_FINALS",
                    "observations": group,
                }
            )
            continue
        unique.append(group[0])
    return {
        "observation_count": len(rows),
        "unique_contest_count": len(order),
        "admitted_unique_games": unique,
        "quarantined_conflicts": quarantined,
        "first_win_forbidden": True,
        "last_win_forbidden": True,
    }


def require_no_conflicts(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = competing_observations(rows)
    if result["quarantined_conflicts"]:
        ids = [row["ncaa_contest_id"] for row in result["quarantined_conflicts"]]
        raise OfficialFinalConflict(f"competing official finals: {ids}")
    return result["admitted_unique_games"]
