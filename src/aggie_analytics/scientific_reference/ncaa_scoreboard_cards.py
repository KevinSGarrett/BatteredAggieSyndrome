"""Independent NCAA livestream scoreboard card reconstruction.

This copy must not import producer modeling helpers. Cycle 27 independent
scoring reconstruction uses this module rather than
``aggie_analytics.modeling.week_zero_official_final_scoring``.
"""

from __future__ import annotations

import html
import re
from typing import Any


_ROW_OPEN = re.compile(r'<tr\s+id="contest_(\d+)"\s*>')
_TEAM_ANCHOR = re.compile(r'href="/teams/(\d+)"\s*>([^<]+?)\s*</a>')
_SCORE_DIV = re.compile(r'<div\s+id="score_(\d+)"[^>]*>\s*(-?\d+)\s*</div>')
_NAME_RECORD = re.compile(r"^(.*?)\s*\((\d+)-(\d+)\)$")
_HEADER_DATETIME = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}\s*[AP]M)([^<]*)", re.IGNORECASE
)
_ATTENDANCE = re.compile(r"Attend:\s*([\d,]+)")
_TERMINAL_STATUS = re.compile(
    r"livestream_status_(\d+)\s+livestream_status\s+livestream_game_over\s*\">([^<]+?)\s*</div>"
)


def _split_name_and_record(raw: str) -> tuple[str, dict[str, int] | None]:
    text = html.unescape(raw).strip()
    match = _NAME_RECORD.match(text)
    if not match:
        return text, None
    return match.group(1).strip(), {
        "wins": int(match.group(2)),
        "losses": int(match.group(3)),
    }


def _normalize_source_date(value: str | None) -> str | None:
    if not value or "/" not in value:
        return None
    month, day, year = value.split("/")
    return f"{year}-{month}-{day}"


def reconstruct_scoreboard_cards(document: str) -> list[dict[str, Any]]:
    """Independently parse NCAA livestream contest cards from raw HTML."""
    terminal_status: dict[str, str] = {}
    for contest_id, status in _TERMINAL_STATUS.findall(document):
        terminal_status.setdefault(contest_id, status.strip())

    opens = list(_ROW_OPEN.finditer(document))
    per_contest: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []

    for index, match in enumerate(opens):
        contest_id = match.group(1)
        start = match.end()
        end = opens[index + 1].start() if index + 1 < len(opens) else len(document)
        segment = document[start:end]
        anchor = _TEAM_ANCHOR.search(segment)
        if anchor is None:
            continue
        score = _SCORE_DIV.search(segment)
        name, record = _split_name_and_record(anchor.group(2))
        entry = {
            "source_team_id": anchor.group(1),
            "source_team_name": name,
            "record_after_contest": record,
            "points": int(score.group(2)) if score else None,
            "source_score_element_id": score.group(1) if score else None,
        }
        if contest_id not in per_contest:
            per_contest[contest_id] = []
            order.append(contest_id)
        per_contest[contest_id].append(entry)

    cards: list[dict[str, Any]] = []
    for contest_id in order:
        rows = per_contest[contest_id]
        if len(rows) != 2:
            cards.append(
                {
                    "ncaa_contest_id": contest_id,
                    "parse_state": "REJECTED_PARTICIPANT_ROW_COUNT",
                    "participant_row_count": len(rows),
                }
            )
            continue
        anchor_position = document.find(f'<tr id="contest_{contest_id}">')
        header_slice = document[max(0, anchor_position - 1500) : anchor_position]
        header = _HEADER_DATETIME.search(header_slice)
        attendance = _ATTENDANCE.search(header_slice)
        away, home = rows[0], rows[1]
        winner = None
        if away["points"] is not None and home["points"] is not None:
            if home["points"] > away["points"]:
                winner = "HOME"
            elif away["points"] > home["points"]:
                winner = "AWAY"
            else:
                winner = "TIE"
        cards.append(
            {
                "ncaa_contest_id": contest_id,
                "parse_state": "PARSED",
                "source_published_game_date": _normalize_source_date(
                    header.group(1) if header else None
                ),
                "source_published_clock_text": header.group(2).strip()
                if header
                else None,
                "source_published_broadcast_text": (
                    (header.group(3).strip() or None) if header else None
                ),
                "attendance_text": attendance.group(1) if attendance else None,
                "final_status_text": terminal_status.get(contest_id),
                "final_status_is_terminal": contest_id in terminal_status,
                "away_source_team_id": away["source_team_id"],
                "away_source_team_name": away["source_team_name"],
                "away_points": away["points"],
                "away_record_after_contest": away["record_after_contest"],
                "home_source_team_id": home["source_team_id"],
                "home_source_team_name": home["source_team_name"],
                "home_points": home["points"],
                "home_record_after_contest": home["record_after_contest"],
                "winner_orientation": winner,
                "home_win": None if winner in (None, "TIE") else int(winner == "HOME"),
            }
        )
    return cards


_BOX_TEAM = re.compile(
    r'<a target="TEAMS_WIN" class="skipMask" href="/teams/(\d+)">([^<]+)</a>'
)
_BOX_BIG_SCORE = re.compile(
    r'<td valign="center" style="font-size:36px; color: [^"]+">\s*(-?\d+)\s*</td>'
)
_BOX_CONTEST = re.compile(r"/contests/(\d+)/")
_BOX_DATETIME = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}\s*[AP]M)")


def reconstruct_box_score_header(
    document: str, contest_id_hint: str | None = None
) -> dict[str, Any]:
    """Independently parse an NCAA contest box-score header. Does not hardcode scores."""
    contest_ids = _BOX_CONTEST.findall(document)
    contest_id = contest_id_hint or (contest_ids[0] if contest_ids else None)
    teams = _BOX_TEAM.findall(document)
    scores = _BOX_BIG_SCORE.findall(document)
    if contest_id is None or len(teams) < 2 or len(scores) < 2:
        return {
            "ncaa_contest_id": contest_id,
            "parse_state": "REJECTED_BOX_HEADER",
            "team_count": len(teams),
            "score_count": len(scores),
        }
    away_id, away_name = teams[0]
    home_id, home_name = teams[1]
    away_points = int(scores[0])
    home_points = int(scores[1])
    if home_points > away_points:
        winner = "HOME"
    elif away_points > home_points:
        winner = "AWAY"
    else:
        winner = "TIE"
    header = _BOX_DATETIME.search(document)
    return {
        "ncaa_contest_id": contest_id,
        "parse_state": "PARSED",
        "final_status_text": "FINAL",
        "final_status_is_terminal": True,
        "away_source_team_id": away_id,
        "away_source_team_name": html.unescape(away_name).strip(),
        "away_points": away_points,
        "home_source_team_id": home_id,
        "home_source_team_name": html.unescape(home_name).strip(),
        "home_points": home_points,
        "winner_orientation": winner,
        "source_published_clock_text": header.group(2) if header else None,
        "source_published_game_date": _normalize_source_date(
            header.group(1) if header else None
        ),
        "home_win": None if winner == "TIE" else int(winner == "HOME"),
    }
