"""Compare 2013-2023 Wikipedia HC names to cached CFBD /coaches.

CFBD is another provider, not official HTML and not PIT admission.
Wikipedia remains RETROSPECTIVE_CANDIDATE_ONLY.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
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


def name_key(first: str, last: str) -> str:
    return " ".join(part for part in (first.strip(), last.strip()) if part).casefold()


def main() -> int:
    wiki = load_jsonl(OUT / "science" / "CYCLE32_HISTORICAL_WIKI_2013_2023_SUCCESSORS.jsonl")
    cfbd = load_jsonl(PRED / "CFBD_COACHES_TRANCHE.jsonl")
    cfbd_hc: dict[tuple[str, int], set[str]] = defaultdict(set)
    years: set[int] = set()
    for row in cfbd:
        first = str(row.get("firstName") or "")
        last = str(row.get("lastName") or "")
        person = name_key(first, last)
        if not person:
            continue
        for season in row.get("seasons") or []:
            year = int(season.get("year") or 0)
            team_id = season.get("teamId")
            if year < 2013 or year > 2023 or team_id is None:
                continue
            years.add(year)
            cfbd_hc[(f"SRC-002:TEAM:{team_id}", year)].add(person)
    counts: Counter[str] = Counter()
    compared = 0
    for row in wiki:
        pid = str(row.get("program_id") or "")
        season = int(row.get("season") or 0)
        if season < 2013 or season > 2023:
            continue
        wiki_hc = {
            str(ep.get("person") or "").casefold().strip()
            for ep in (row.get("episodes") or [])
            if str(ep.get("role") or "") == "head_coach" and str(ep.get("person") or "").strip()
        }
        provider = cfbd_hc.get((pid, season), set())
        if not wiki_hc and not provider:
            counts["BOTH_ABSENT"] += 1
            continue
        compared += 1
        if wiki_hc and not provider:
            counts["WIKI_ONLY_CFBD_MISSING"] += 1
        elif provider and not wiki_hc:
            counts["CFBD_ONLY_WIKI_MISSING"] += 1
        elif wiki_hc == provider:
            counts["NAME_AGREEMENT_NOT_OFFICIAL_HTML"] += 1
        elif wiki_hc & provider:
            counts["PARTIAL_OVERLAP"] += 1
        else:
            counts["CONFLICT"] += 1
    payload = {
        "artifact_type": "CYCLE32_WIKI_CFBD_HC_FIELD_CLAIMS",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "wikipedia_is_not_factual_verification": True,
        "cfbd_is_not_official_html": True,
        "pit_admitted": False,
        "cfbd_years": sorted(years),
        "wiki_rows": len(wiki),
        "compared_cells": compared,
        "counts": dict(counts),
        "note": "Head-coach name agreement with CFBD /coaches is not independent official corroboration of OC/DC or PIT.",
    }
    out = OUT / "science" / "CYCLE32_WIKI_CFBD_HC_FIELD_CLAIMS.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"compared_cells": compared, "counts": dict(counts), "cfbd_years": sorted(years)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
