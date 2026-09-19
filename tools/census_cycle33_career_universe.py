"""Historical/current people universe from cached wiki team-season pages.

Does not infer continuous careers from repeated yearly names.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Tool scripts must import the local package after PATH setup.
# ruff: noqa: E402
from aggie_analytics.cycle33.career_identity import _fold as fold_name

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    wiki = load_jsonl(OUT / "CYCLE33_WIKI_STAFF_SUCCESSORS.jsonl")
    joins = load_jsonl(OUT / "CYCLE33_CURRENT_OCCUPANT_CAREER_JOINS.jsonl")
    by_person: dict[str, dict[str, Any]] = {}
    occurrences: dict[str, list[dict[str, Any]]] = {}
    for page in wiki:
        season = str(page.get("season") or "")
        title = str(page.get("title") or "")
        for ep in page.get("episodes") or []:
            person = str(ep.get("person") or "").strip()
            if not person:
                continue
            key = fold_name(person)
            bucket = by_person.setdefault(
                key,
                {
                    "person": person,
                    "seasons": set(),
                    "roles": set(),
                    "pages": set(),
                    "not_inferred_continuous": True,
                },
            )
            bucket["seasons"].add(season)
            bucket["roles"].add(str(ep.get("role") or ""))
            bucket["pages"].add(title)
            occurrences.setdefault(key, []).append(
                {
                    "wiki_title": title,
                    "season": season,
                    "role": ep.get("role"),
                    "not_inferred_continuous": True,
                }
            )
    unresolved: list[dict[str, Any]] = []
    for row in joins:
        if row.get("career_join_state") == "EVIDENCE_BOUND_CAREER_JOIN":
            continue
        key = fold_name(str(row.get("person") or ""))
        hits = occurrences.get(key) or []
        unresolved.append(
            {
                "person": row.get("person"),
                "program_display": row.get("program_display") or row.get("employer"),
                "program_id": row.get("program_id"),
                "role": row.get("role"),
                "career_join_state": row.get("career_join_state"),
                "wiki_team_season_occurrence_count": len(hits),
                "wiki_team_season_occurrences_head": hits[:12],
                "next_action": (
                    "BIND_PERSON_CAREER_PAGE_THEN_EMPLOYER_INTERVAL"
                    if hits
                    else "LOCATE_FOOTBALL_CAREER_PAGE_THEN_EMPLOYER_INTERVAL"
                ),
                "pit_admitted": False,
            }
        )
    payload = {
        "artifact_type": "CYCLE33_CAREER_PEOPLE_UNIVERSE",
        "wiki_team_season_pages": len(wiki),
        "distinct_infobox_people": len(by_person),
        "current_occupant_join_rows": len(joins),
        "current_occupants_are_not_national_historical_denominator": True,
        "unresolved_current_join_keys": len(unresolved),
        "unresolved_with_wiki_team_season_occurrences": sum(
            1 for row in unresolved if row["wiki_team_season_occurrence_count"]
        ),
        "historical_infobox_is_not_career_join": True,
        "continuous_career_not_inferred_from_yearly_names": True,
        "pit_admitted": False,
    }
    (OUT / "CYCLE33_CAREER_PEOPLE_UNIVERSE.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "CYCLE33_CAREER_UNRESOLVED_KEYS.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in unresolved) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
