"""Cache-only reparse of predecessor 2013-2023 wiki season rows.

Writes Cycle32 successors. Does not overwrite
WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl. Wikipedia extraction is not
factual verification (WG32-06). Stored-revision replay is used when the
cached title query exists; cache misses stay visible and are not live-fetched.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aggie_analytics.cycle30.coaching import (  # noqa: E402
    season_page_supports_requested_year,
    season_title_matches_school,
)
from tools.acquire_cycle30_historical_wikimedia import (  # noqa: E402
    BUDGET,
    fetch_title,
)

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
YEAR_START = 1963
YEAR_END = 2026


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    BUDGET["max_requests"] = 0
    predecessor = load_jsonl(PRED / "WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl")
    frame = [
        row
        for row in predecessor
        if YEAR_START <= int(row.get("season") or 0) <= YEAR_END
    ]
    ledger: list[dict[str, Any]] = []
    successors: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    cache_hits = 0
    cache_missing = 0
    identity_bound = 0
    season_supported = 0
    hc_oc_dc_episodes = 0
    for row in frame:
        school = str(row.get("school") or "")
        year = int(row.get("season") or 0)
        title = str(row.get("title") or row.get("requested_title") or "")
        parsed: dict[str, Any]
        if not title:
            parsed = {
                "status": "NO_TITLE",
                "episodes": [],
                "pit_admitted": False,
            }
        else:
            try:
                parsed = fetch_title(title, ledger)
            except RuntimeError:
                cache_missing += 1
                parsed = {
                    "title": title,
                    "status": "CACHE_MISSING",
                    "episodes": [],
                    "pit_admitted": False,
                }
            else:
                if any(item.get("cached") for item in ledger[-1:]):
                    cache_hits += 1
        bound_title = str(parsed.get("title") or title)
        identity = bool(bound_title) and season_title_matches_school(bound_title, school)
        supported = bool(
            bound_title
            and season_page_supports_requested_year(
                page_title=bound_title,
                wikitext="",
                year=year,
            )
        )
        if identity:
            identity_bound += 1
        if supported:
            season_supported += 1
        episodes = list(parsed.get("episodes") or [])
        if parsed.get("status") == "REVISION_BOUND" and (not identity or not supported):
            parsed = {
                **parsed,
                "status": "IDENTITY_OR_SEASON_REJECTED",
                "rejected_title": bound_title,
                "episodes": [],
                "preserved_candidate_episodes": episodes,
            }
            episodes = []
        hc_oc_dc_episodes += sum(
            1
            for item in episodes
            if str(item.get("role") or "")
            in {"head_coach", "offensive_coordinator", "defensive_coordinator"}
        )
        status_counts[str(parsed.get("status") or "UNKNOWN")] += 1
        successors.append(
            {
                **parsed,
                "program_id": row.get("program_id"),
                "school": school,
                "season": year,
                "predecessor_title": title,
                "predecessor_status": row.get("status"),
                "identity_bound": identity,
                "season_supported": supported,
                "driven_by": "PREDECESSOR_2013_2023_CACHE_REPARSE",
                "pit_admitted": False,
                "wikipedia_is_not_factual_verification": True,
                "artifact_class": "REAL_EVIDENCE",
            }
        )
    coverage = {
        "artifact_type": "CYCLE32_HISTORICAL_WIKI_CACHE_REPARSE",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "predecessor_file_not_overwritten": str(
            PRED / "WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl"
        ),
        "predecessor_rows": len(predecessor),
        "frame_rows": len(frame),
        "year_start": YEAR_START,
        "year_end": YEAR_END,
        "successor_rows": len(successors),
        "cache_hits": cache_hits,
        "cache_missing": cache_missing,
        "identity_bound": identity_bound,
        "season_supported": season_supported,
        "hc_oc_dc_candidate_episodes": hc_oc_dc_episodes,
        "status_counts": dict(status_counts),
        "pit_admitted": False,
        "wikipedia_is_not_factual_verification": True,
        "live_requests": 0,
    }
    science = OUT / "science"
    write_jsonl(science / "CYCLE32_HISTORICAL_WIKI_PREDECESSOR_SUCCESSORS.jsonl", successors)
    write_json(science / "CYCLE32_HISTORICAL_WIKI_PREDECESSOR_REPARSE.json", coverage)
    tranche = [
        row
        for row in successors
        if 2013 <= int(row.get("season") or 0) <= 2023
    ]
    write_jsonl(science / "CYCLE32_HISTORICAL_WIKI_2013_2023_SUCCESSORS.jsonl", tranche)
    print(json.dumps(coverage, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
