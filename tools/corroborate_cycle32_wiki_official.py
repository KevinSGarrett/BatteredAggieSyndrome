"""Field-level 2026 official vs Wikipedia infobox comparison.

Wikipedia remains PARSED_ASSERTION / RETROSPECTIVE_CANDIDATE_ONLY.
Official HTML is the current staff factual source for these cells.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def names(cell: dict[str, Any]) -> list[str]:
    return [
        str(item.get("person") or "")
        for item in (cell.get("episode_refs") or [])
        if str(item.get("person") or "")
    ]


def main() -> int:
    matrix = load_jsonl(OUT / "science" / "CYCLE32_CURRENT_HC_OC_DC_MATRIX.jsonl")
    wiki = load_jsonl(PRED / "WIKIMEDIA_CURRENT_STAFF_CANDIDATES.jsonl") if (
        PRED / "WIKIMEDIA_CURRENT_STAFF_CANDIDATES.jsonl"
    ).is_file() else []
    programs = {
        str(row.get("program_id")): row
        for row in load_jsonl(PRED / "CURRENT_2026_PROGRAMS.jsonl")
    }
    wiki_by_program: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for row in wiki:
        pid = str(row.get("program_id") or "")
        for episode in row.get("episodes") or []:
            role = str(episode.get("role") or "")
            person = str(episode.get("person") or "")
            if pid and role and person:
                wiki_by_program[pid][role].append(person)
    claims: list[dict[str, Any]] = []
    for cell in matrix:
        pid = str(cell.get("program_id") or "")
        role = str(cell.get("role") or "")
        official_people = names(cell)
        wiki_people = wiki_by_program.get(pid, {}).get(role, [])
        official_fold = {name.casefold() for name in official_people}
        wiki_fold = {name.casefold() for name in wiki_people}
        if not official_people and not wiki_people:
            support = "BOTH_ABSENT"
        elif official_people and not wiki_people:
            support = "OFFICIAL_ONLY_WIKI_MISSING"
        elif wiki_people and not official_people:
            support = "WIKI_ONLY_NOT_OFFICIAL"
        elif official_fold == wiki_fold:
            support = "NAME_AGREEMENT_NOT_INDEPENDENT_CORROBORATION"
        elif official_fold & wiki_fold:
            support = "PARTIAL_OVERLAP_CONFLICT"
        else:
            support = "CONFLICT"
        claims.append(
            {
                "program_id": pid,
                "display_name": (programs.get(pid) or {}).get("display_name"),
                "role": role,
                "official_people": official_people,
                "wikipedia_people": wiki_people,
                "official_disposition": cell.get("disposition"),
                "field_support": support,
                "wikipedia_is_not_verification": True,
                "pit_admitted": False,
            }
        )
    counts: dict[str, int] = {}
    for row in claims:
        counts[row["field_support"]] = counts.get(row["field_support"], 0) + 1
    payload = {
        "artifact_type": "CYCLE32_WIKI_OFFICIAL_FIELD_CLAIMS",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "cells": len(claims),
        "wikipedia_current_candidate_rows": len(wiki),
        "wikipedia_is_not_factual_verification": True,
        "independent_primary_corroboration_complete": False,
        "pit_admitted": False,
        "support_counts": counts,
        "sample_conflicts": [row for row in claims if row["field_support"] in {"CONFLICT", "PARTIAL_OVERLAP_CONFLICT"}][:40],
        "notes": [
            "Name agreement between Wikipedia and official HTML is not independent corroboration when one may copy the other.",
            "WG32-06/08 full independent reference set remains unfinished for the historical tranche.",
        ],
    }
    out = OUT / "science" / "CYCLE32_WIKI_OFFICIAL_FIELD_CLAIMS.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cells": len(claims), "support_counts": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
