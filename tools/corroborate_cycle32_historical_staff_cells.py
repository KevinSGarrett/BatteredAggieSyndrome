"""Per-program/season/role dispositions for 2013-2023 HC/OC/DC.

Wikipedia remains RETROSPECTIVE_CANDIDATE_ONLY. CFBD /coaches is HC-only
provider agreement, not official HTML. Sportradar current roster is not a
historical official staff capture. Independent OC/DC official corroboration
stays unfinished where no historical official HTML exists.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
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
    wiki = load_jsonl(OUT / "science" / "CYCLE32_HISTORICAL_WIKI_2013_2023_SUCCESSORS.jsonl")
    cfbd = load_jsonl(PRED / "CFBD_COACHES_TRANCHE.jsonl")
    official_current = load_jsonl(OUT / "science" / "CYCLE32_CURRENT_HC_OC_DC_MATRIX.jsonl")
    sportradar = load_jsonl(PRED / "SPORTSRADAR_STAFF_PARSED.jsonl")

    keys = sorted(
        {
            (str(row.get("program_id") or ""), int(row.get("season") or 0))
            for row in membership
            if row.get("program_id") and 2013 <= int(row.get("season") or 0) <= 2023
        }
    )
    wiki_by_cell: dict[tuple[str, int, str], set[str]] = defaultdict(set)
    wiki_status: dict[tuple[str, int], str] = {}
    for row in wiki:
        pid = str(row.get("program_id") or "")
        season = int(row.get("season") or 0)
        wiki_status[(pid, season)] = str(row.get("status") or "")
        for episode in row.get("episodes") or []:
            role = str(episode.get("role") or "")
            person = fold(str(episode.get("person") or ""))
            if pid and season and role in ROLES and person:
                wiki_by_cell[(pid, season, role)].add(person)

    cfbd_hc: dict[tuple[str, int], set[str]] = defaultdict(set)
    for row in cfbd:
        person = name_key(str(row.get("firstName") or ""), str(row.get("lastName") or ""))
        if not person:
            continue
        for season in row.get("seasons") or []:
            year = int(season.get("year") or 0)
            team_id = season.get("teamId")
            if year < 2013 or year > 2023 or team_id is None:
                continue
            cfbd_hc[(f"SRC-002:TEAM:{team_id}", year)].add(person)

    current_2026: dict[tuple[str, str], set[str]] = defaultdict(set)
    for cell in official_current:
        pid = str(cell.get("program_id") or "")
        role = str(cell.get("role") or "")
        if str(cell.get("disposition") or "").startswith("CONFIRMED"):
            for episode in cell.get("episode_refs") or []:
                person = fold(str(episode.get("person") or ""))
                if pid and role in ROLES and person:
                    current_2026[(pid, role)].add(person)

    sr_current: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in sportradar:
        pid = str(row.get("program_id") or "")
        role = str(row.get("role") or "")
        person = fold(str(row.get("person") or ""))
        if pid and role in ROLES and person:
            sr_current[(pid, role)].add(person)

    counts: Counter[str] = Counter()
    role_counts: dict[str, Counter[str]] = {role: Counter() for role in ROLES}
    sample_unofficial_oc_dc = 0
    for pid, season in keys:
        for role in ROLES:
            wiki_people = wiki_by_cell.get((pid, season, role), set())
            cfbd_people = cfbd_hc.get((pid, season), set()) if role == "head_coach" else set()
            page_status = wiki_status.get((pid, season), "NO_WIKI_ROW")
            if not wiki_people and not cfbd_people:
                if page_status in {"PAGE_MISSING", "NO_WIKI_ROW", ""}:
                    disposition = "BOTH_ABSENT_OR_PAGE_MISSING"
                else:
                    disposition = "ROLE_ABSENT_ON_WIKI_PAGE"
            elif wiki_people and not cfbd_people:
                if role == "head_coach":
                    disposition = "WIKI_ONLY_CFBD_MISSING"
                else:
                    disposition = "WIKI_ONLY_NO_INDEPENDENT_PRIMARY"
                    sample_unofficial_oc_dc += 1
            elif cfbd_people and not wiki_people:
                disposition = "CFBD_ONLY_WIKI_MISSING"
            elif wiki_people == cfbd_people:
                disposition = "NAME_AGREEMENT_NOT_OFFICIAL_HTML"
            elif wiki_people & cfbd_people:
                disposition = "PARTIAL_OVERLAP_NOT_OFFICIAL_HTML"
            else:
                disposition = "CONFLICT_NOT_OFFICIAL_HTML"
            counts[disposition] += 1
            role_counts[role][disposition] += 1

    payload = {
        "artifact_type": "CYCLE32_HISTORICAL_STAFF_CELL_DISPOSITIONS",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "expected_program_seasons_2013_2023": len(keys),
        "expected_role_cells": len(keys) * len(ROLES),
        "wikipedia_is_not_factual_verification": True,
        "cfbd_is_not_official_html": True,
        "sportradar_current_roster_is_not_historical_official": True,
        "pit_admitted": False,
        "independent_official_oc_dc_corroboration_complete": False,
        "counts": dict(counts),
        "counts_by_role": {role: dict(counter) for role, counter in role_counts.items()},
        "wiki_only_oc_dc_cells": sample_unofficial_oc_dc,
        "current_2026_official_confirmed_role_people": {
            role: sum(1 for key in current_2026 if key[1] == role)
            for role in ROLES
        },
        "sportradar_current_role_people": {
            role: sum(1 for key in sr_current if key[1] == role)
            for role in ROLES
        },
        "note": (
            "2013-2023 OC/DC cells with Wikipedia names remain "
            "WIKI_ONLY_NO_INDEPENDENT_PRIMARY until official historical HTML, "
            "media-guide, or contemporaneous announcement evidence is captured. "
            "CFBD /coaches does not supply OC/DC. Sportradar full-roster coaches "
            "here are current snapshots, not year-bound historical appointments."
        ),
    }
    out = OUT / "science" / "CYCLE32_HISTORICAL_STAFF_CELL_DISPOSITIONS.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "expected_role_cells": payload["expected_role_cells"],
                "counts": dict(counts),
                "wiki_only_oc_dc_cells": sample_unofficial_oc_dc,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
