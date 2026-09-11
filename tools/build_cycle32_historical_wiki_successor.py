"""Drive historical wiki coverage from 285-program expected keys.

Writes Cycle32 successors. Does not overwrite
WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl. Wikipedia extraction is not
factual verification (WG32-06).
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
    expected = json.loads(
        (OUT / "science" / "CYCLE32_HISTORICAL_EXPECTED_KEYS.json").read_text(
            encoding="utf-8"
        )
    )
    membership = load_jsonl(PRED / "HISTORICAL_MEMBERSHIP_2013_2023.jsonl")
    current_ids = {
        str(row.get("program_id"))
        for row in load_jsonl(PRED / "CURRENT_2026_PROGRAMS.jsonl")
    }
    frame_keys: list[tuple[str, int, str]] = []
    for row in membership:
        pid = str(row.get("program_id") or "")
        season = int(row.get("season") or 0)
        school = str(row.get("display_name") or row.get("school") or "")
        if YEAR_START <= season <= YEAR_END and pid:
            frame_keys.append((pid, season, school))
    predecessor = load_jsonl(PRED / "WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl")
    pred_index: dict[tuple[str, int], dict[str, Any]] = {}
    for row in predecessor:
        key = (str(row.get("program_id") or ""), int(row.get("season") or 0))
        pred_index[key] = row
    covered = 0
    title_mismatch = 0
    missing_from_predecessor = 0
    discontinued_missing: list[dict[str, Any]] = []
    for pid, season, school in frame_keys:
        row = pred_index.get((pid, season))
        if row is None:
            missing_from_predecessor += 1
            if pid not in current_ids:
                discontinued_missing.append(
                    {
                        "program_id": pid,
                        "school": school,
                        "season": season,
                    }
                )
            continue
        covered += 1
        title = str(row.get("title") or row.get("requested_title") or "")
        if title and not season_title_matches_school(title, school):
            title_mismatch += 1
    BUDGET["max_requests"] = 80
    ledger: list[dict[str, Any]] = []
    successor_rows: list[dict[str, Any]] = []
    fetched = 0
    for item in discontinued_missing:
        school = str(item["school"])
        year = int(item["season"])
        guessed = historical_season_page_title("", year, school=school) or (
            f"{year} {school} football team"
        )
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
        successor_rows.append(
            {
                **parsed,
                "program_id": item["program_id"],
                "school": school,
                "season": year,
                "current_title": None,
                "driven_by": "HISTORICAL_EXPECTED_KEYS_NOT_CURRENT_266",
                "in_current_266": False,
                "pit_admitted": False,
                "wikipedia_is_not_factual_verification": True,
                "artifact_class": "REAL_EVIDENCE",
            }
        )
        fetched += 1
    science = OUT / "science"
    write_jsonl(science / "CYCLE32_HISTORICAL_WIKI_DISCONTINUED_2013_2023.jsonl", successor_rows)
    coverage = {
        "artifact_type": "CYCLE32_HISTORICAL_WIKI_FRAME_COVERAGE",
        "authority": "CFBD_MEMBERSHIP_2013_2023_NOT_CURRENT_TIMES_YEARS",
        "expected_keys_2013_2023": len(frame_keys),
        "historical_program_n_all_years": expected.get("historical_program_n"),
        "predecessor_rows": len(predecessor),
        "predecessor_covers_frame_keys": covered,
        "predecessor_title_school_mismatch": title_mismatch,
        "frame_keys_absent_from_predecessor": missing_from_predecessor,
        "discontinued_program_seasons_2013_2023": len(discontinued_missing),
        "discontinued_fetched_this_run": fetched,
        "revision_bound_discontinued": sum(
            1 for row in successor_rows if row.get("status") == "REVISION_BOUND"
        ),
        "page_missing_discontinued": sum(
            1 for row in successor_rows if row.get("status") == "PAGE_MISSING"
        ),
        "wikipedia_is_not_factual_verification": True,
        "predecessor_file_not_overwritten": str(
            PRED / "WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl"
        ),
        "pit_admitted": False,
        "as_of_utc": utc_now(),
    }
    (science / "CYCLE32_HISTORICAL_WIKI_FRAME_COVERAGE.json").write_text(
        json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(coverage, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
