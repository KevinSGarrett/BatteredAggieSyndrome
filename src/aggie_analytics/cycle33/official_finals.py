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


def winner_from_scores(row: Mapping[str, Any]) -> str | None:
    """Direction recomputed from the scores themselves, never read off a label."""

    if not (
        _finite_nonneg_int(row.get("home_points"))
        and _finite_nonneg_int(row.get("away_points"))
    ):
        return None
    home = int(row["home_points"])
    away = int(row["away_points"])
    if home > away:
        return "HOME"
    if away > home:
        return "AWAY"
    return "TIE"


def supplied_winner_disagrees_with_scores(row: Mapping[str, Any]) -> bool:
    """True when a row carries a `winner` label its own scores contradict.

    MR34-09 repair: a 30-10 home victory labelled `winner: "AWAY"` passed the
    final-admission helper untouched, because admission only checked the
    lifecycle and that the two score fields were nonnegative integers. A row
    that contradicts itself is not a trustworthy observation of anything --
    one of its fields is wrong and nothing on the row says which. So it is
    quarantined for adjudication, not silently admitted, and not silently
    "corrected" by preferring the scores, which would invent a fact about
    which field the source got wrong.
    """

    supplied = row.get("winner") or row.get("winning_side")
    if supplied in (None, ""):
        return False
    computed = winner_from_scores(row)
    if computed is None:
        return False
    return str(supplied).strip().upper() != computed


def is_eligible_official_final(row: Mapping[str, Any]) -> bool:
    if observation_lifecycle(row) != "FINAL":
        return False
    if not (
        _finite_nonneg_int(row.get("home_points"))
        and _finite_nonneg_int(row.get("away_points"))
    ):
        return False
    return not supplied_winner_disagrees_with_scores(row)


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
    inconsistent: list[dict[str, Any]] = []
    for cid in order:
        group = by_id[cid]
        # MR34-09: a self-contradicting row is retained with its own exact
        # reason rather than collapsing into a generic "no eligible final".
        contradictions = [
            item for item in group if supplied_winner_disagrees_with_scores(item)
        ]
        if contradictions:
            inconsistent.append(
                {
                    "ncaa_contest_id": cid,
                    "reason": "SUPPLIED_WINNER_CONTRADICTS_SCORES",
                    "observations": contradictions,
                    "recomputed_winner": [
                        winner_from_scores(item) for item in contradictions
                    ],
                    "supplied_winner": [
                        item.get("winner") or item.get("winning_side")
                        for item in contradictions
                    ],
                }
            )
        finals = [item for item in group if is_eligible_official_final(item)]
        if not finals:
            nonfinal_only.append(
                {
                    "ncaa_contest_id": cid,
                    "observation_count": len(group),
                    "lifecycles": sorted(
                        {observation_lifecycle(item) for item in group}
                    ),
                    "reason": (
                        "ALL_FINALS_INTERNALLY_INCONSISTENT"
                        if contradictions
                        else "NO_ELIGIBLE_OFFICIAL_FINAL"
                    ),
                }
            )
            continue
        scores = {_score_tuple(item) for item in finals}
        # MR33-03 repair: canonical program IDs are checked on their own, never
        # only as a fallback behind display names. A name match must not hide
        # a conflicting canonical ID -- and a canonical-ID match cannot be
        # undermined by a name spelling difference either; both are tracked.
        names = {
            (
                str(item.get("home_name") or ""),
                str(item.get("away_name") or ""),
            )
            for item in finals
        }
        canonical_ids = {
            (
                str(item.get("home_canonical_team_id"))
                if item.get("home_canonical_team_id") not in (None, "")
                else None,
                str(item.get("away_canonical_team_id"))
                if item.get("away_canonical_team_id") not in (None, "")
                else None,
            )
            for item in finals
            if item.get("home_canonical_team_id") not in (None, "")
            or item.get("away_canonical_team_id") not in (None, "")
        }
        if len(scores) > 1 or len(names) > 1 or len(canonical_ids) > 1:
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
        "internally_inconsistent_observations": inconsistent,
        "nonfinal_contests": nonfinal_only,
        "winner_recomputed_from_scores_not_supplied_label": True,
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
