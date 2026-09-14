"""Persist 2013-2023 HC/OC/DC dispositions as row-level claims.

Successor to Cycle32 aggregate-only emission. Wikipedia is not official HTML.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
CYCLE32 = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
DEFAULT_OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z\implementation_output"
)
ROLES = ("head_coach", "offensive_coordinator", "defensive_coordinator")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def fold(value: str) -> str:
    return " ".join(str(value or "").split()).casefold()


def name_key(first: str, last: str) -> str:
    return " ".join(part for part in (first.strip(), last.strip()) if part).casefold()


def main() -> int:
    membership = load_jsonl(PRED / "HISTORICAL_MEMBERSHIP_2013_2023.jsonl")
    wiki = load_jsonl(
        CYCLE32 / "science" / "CYCLE32_HISTORICAL_WIKI_2013_2023_SUCCESSORS.jsonl"
    )
    cfbd = load_jsonl(PRED / "CFBD_COACHES_TRANCHE.jsonl")
    keys = sorted(
        {
            (str(row.get("program_id") or ""), int(row.get("season") or 0))
            for row in membership
            if row.get("program_id") and 2013 <= int(row.get("season") or 0) <= 2023
        }
    )
    wiki_by_cell: dict[tuple[str, int, str], set[str]] = defaultdict(set)
    wiki_status: dict[tuple[str, int], str] = {}
    wiki_source: dict[tuple[str, int], dict[str, Any]] = {}
    for row in wiki:
        pid = str(row.get("program_id") or "")
        season = int(row.get("season") or 0)
        wiki_status[(pid, season)] = str(row.get("status") or "")
        wiki_source[(pid, season)] = {
            "title": row.get("title"),
            "wikimedia_revision": row.get("wikimedia_revision"),
            "revision_timestamp": row.get("revision_timestamp"),
        }
        for episode in row.get("episodes") or []:
            role = str(episode.get("role") or "")
            person = fold(str(episode.get("person") or ""))
            if pid and season and role in ROLES and person:
                wiki_by_cell[(pid, season, role)].add(person)
    cfbd_hc: dict[tuple[str, int], set[str]] = defaultdict(set)
    for row in cfbd:
        person = name_key(
            str(row.get("firstName") or ""), str(row.get("lastName") or "")
        )
        if not person:
            continue
        for season in row.get("seasons") or []:
            year = int(season.get("year") or 0)
            team_id = season.get("teamId")
            if year < 2013 or year > 2023 or team_id is None:
                continue
            cfbd_hc[(f"SRC-002:TEAM:{team_id}", year)].add(person)
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for pid, season in keys:
        for role in ROLES:
            wiki_people = wiki_by_cell.get((pid, season, role), set())
            cfbd_people = (
                cfbd_hc.get((pid, season), set()) if role == "head_coach" else set()
            )
            page_status = wiki_status.get((pid, season), "NO_WIKI_ROW")
            if not wiki_people and not cfbd_people:
                if page_status in {"PAGE_MISSING", "NO_WIKI_ROW", ""}:
                    disposition = "BOTH_ABSENT_OR_PAGE_MISSING"
                else:
                    disposition = "ROLE_ABSENT_ON_WIKI_PAGE"
            elif wiki_people and not cfbd_people:
                disposition = (
                    "WIKI_ONLY_CFBD_MISSING"
                    if role == "head_coach"
                    else "WIKI_ONLY_NO_INDEPENDENT_PRIMARY"
                )
            elif cfbd_people and not wiki_people:
                disposition = "CFBD_ONLY_WIKI_MISSING"
            elif wiki_people == cfbd_people:
                disposition = "NAME_AGREEMENT_NOT_OFFICIAL_HTML"
            elif wiki_people & cfbd_people:
                disposition = "PARTIAL_OVERLAP_NOT_OFFICIAL_HTML"
            else:
                disposition = "CONFLICT_NOT_OFFICIAL_HTML"
            counts[disposition] += 1
            source = wiki_source.get((pid, season), {})
            rows.append(
                {
                    "program_id": pid,
                    "season": season,
                    "role": role,
                    "disposition": disposition,
                    "wiki_people": sorted(wiki_people),
                    "cfbd_people": sorted(cfbd_people),
                    "wiki_page_status": page_status,
                    "wikimedia_revision": source.get("wikimedia_revision"),
                    "wiki_title": source.get("title"),
                    "wikipedia_is_not_factual_verification": True,
                    "cfbd_is_not_official_html": True,
                    "pit_admitted": False,
                    "official_html_present": False,
                }
            )
    out_dir = DEFAULT_OUT / "science"
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl = out_dir / "CYCLE33_HISTORICAL_STAFF_CELL_ROWS.jsonl"
    jsonl.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    summary = {
        "artifact_type": "CYCLE33_HISTORICAL_STAFF_CELL_ROWS",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "row_count": len(rows),
        "expected_program_seasons_2013_2023": len(keys),
        "expected_role_cells": len(keys) * len(ROLES),
        "counts": dict(counts),
        "predecessor_aggregate_path": str(
            CYCLE32 / "science" / "CYCLE32_HISTORICAL_STAFF_CELL_DISPOSITIONS.json"
        ),
        "pit_admitted": False,
        "not_full_25_year_verification": True,
        "pre_2013_backlog_owner": "BAT-701",
    }
    (out_dir / "CYCLE33_HISTORICAL_STAFF_CELL_ROWS.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"row_count": len(rows), "counts": dict(counts)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
