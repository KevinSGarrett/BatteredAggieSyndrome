"""Re-adjudicate predecessor wiki rows whose titles fail school identity.

Writes Cycle32 successors only. Does not overwrite
WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl. Wikipedia is not factual
verification.
"""

from __future__ import annotations

import json
import sys
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
    historical_season_page_title,
    season_title_matches_school,
)
from tools.acquire_cycle30_historical_wikimedia import (  # noqa: E402
    BUDGET,
    fetch_season,
)

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
YEAR_START = 2013
YEAR_END = 2023


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


def main() -> int:
    BUDGET["max_requests"] = 250
    predecessor = load_jsonl(PRED / "WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl")
    mismatches: list[dict[str, Any]] = []
    for row in predecessor:
        season = int(row.get("season") or 0)
        if not (YEAR_START <= season <= YEAR_END):
            continue
        school = str(row.get("school") or "")
        title = str(row.get("title") or row.get("requested_title") or "")
        if not school or not title:
            continue
        if season_title_matches_school(title, school):
            continue
        mismatches.append(row)
    ledger: list[dict[str, Any]] = []
    successors: list[dict[str, Any]] = []
    rebound = 0
    still_mismatch = 0
    page_missing = 0
    for row in mismatches:
        school = str(row.get("school") or "")
        year = int(row.get("season") or 0)
        guessed = historical_season_page_title(
            str(row.get("current_title") or ""), year, school=school
        ) or f"{year} {school} football team"
        try:
            parsed = fetch_season(
                school=school, year=year, guessed_title=guessed, ledger=ledger
            )
        except RuntimeError:
            parsed = {
                "title": guessed,
                "status": "QUEUED_CEILING",
                "pit_admitted": False,
                "episodes": [],
            }
        except Exception as exc:  # noqa: BLE001
            parsed = {
                "title": guessed,
                "status": f"ACQUISITION_FAILED:{type(exc).__name__}",
                "pit_admitted": False,
                "episodes": [],
            }
        bound_title = str(parsed.get("title") or guessed)
        identity_bound = bool(bound_title) and season_title_matches_school(
            bound_title, school
        )
        if parsed.get("status") == "REVISION_BOUND" and identity_bound:
            rebound += 1
        elif parsed.get("status") == "PAGE_MISSING":
            page_missing += 1
        else:
            still_mismatch += 1
        successors.append(
            {
                **parsed,
                "program_id": row.get("program_id"),
                "school": school,
                "season": year,
                "predecessor_title": str(row.get("title") or row.get("requested_title") or ""),
                "identity_bound": identity_bound,
                "driven_by": "PREDECESSOR_TITLE_SCHOOL_MISMATCH",
                "pit_admitted": False,
                "wikipedia_is_not_factual_verification": True,
                "artifact_class": "REAL_EVIDENCE",
            }
        )
    science = OUT / "science"
    write_jsonl(science / "CYCLE32_HISTORICAL_WIKI_MISMATCH_SUCCESSORS.jsonl", successors)
    summary = {
        "artifact_type": "CYCLE32_HISTORICAL_WIKI_MISMATCH_READJUDICATION",
        "predecessor_rows": len(predecessor),
        "mismatches_2013_2023": len(mismatches),
        "identity_bound_successors": rebound,
        "still_unbound_or_failed": still_mismatch,
        "page_missing": page_missing,
        "ledger_requests": len(ledger),
        "cache_hits": sum(1 for item in ledger if item.get("cached")),
        "wikipedia_is_not_factual_verification": True,
        "predecessor_file_not_overwritten": str(
            PRED / "WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl"
        ),
        "as_of_utc": utc_now(),
    }
    (science / "CYCLE32_HISTORICAL_WIKI_MISMATCH_READJUDICATION.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
