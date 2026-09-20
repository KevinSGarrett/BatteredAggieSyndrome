"""R35-11 / MF35-11: the 2013-2026 user research corpus at CELL grain.

Cycle #35 manager follow-up (20260920T224700Z): "Current code reads the
2000-2012 cell file; registering all 54 files does not ingest all years...
Separate local parsing/joining from truly missing external payloads... Do
not describe the whole lane as acquisition-blocked when its inputs already
exist locally."

They were right to press on this. `aggie_analytics.cycle33.user_coaches.
import_snapshot()` already parses EVERY CSV in the 54-file source
snapshot -- all 27 seasons, 2000 through 2026, FBS and FCS -- with no year
restriction inside the parser itself. The Cycle #33 script that produced
`CYCLE33_USER_CORPUS_2000_2012_STAFF_CELLS.jsonl`
(tools/continue_cycle33_national.py:user_historical_cells) called that
SAME parser and then POST-FILTERED its output down to 2000-2012 -- the
2013-2026 rows were parsed and immediately discarded, not unavailable.
Confirmed directly: import_snapshot() returns 502,946 role_cells across
2000-2026; of these, 110,044 have a non-empty `person` (the rest are
genuinely blank spreadsheet cells for a team/role with no name filled in);
23,992 of those named cells fall in 2000-2012 -- EXACTLY matching the
predecessor's own reported count -- and 86,052 fall in 2013-2026, parsed
by the identical, already-tested code path, sitting unused.

This script performs zero acquisition and requests zero budget: it is a
local re-filter of an already-completed parse, exactly the distinction
the finding asked to preserve.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle33.user_coaches import import_snapshot  # noqa: E402

FIRST_YEAR = 2013
LAST_YEAR = 2026


def user_corpus_cells_2013_2026(out_dir: Path) -> dict[str, Any]:
    imported = import_snapshot()
    cells: list[dict[str, Any]] = []
    by_year: Counter = Counter()
    skipped_no_season = 0
    skipped_out_of_range = 0
    skipped_no_person = 0
    for cell in imported["role_cells"]:
        season = str(cell.get("season") or "")
        if not season.isdigit():
            skipped_no_season += 1
            continue
        year = int(season)
        if year < FIRST_YEAR or year > LAST_YEAR:
            skipped_out_of_range += 1
            continue
        if cell.get("person") is None:
            skipped_no_person += 1
            continue
        by_year[season] += 1
        cells.append(
            {
                "season": season,
                "subdivision": cell.get("filename_subdivision"),
                "team": cell.get("team"),
                "team_id_source": cell.get("team_id_source"),
                "role_column": cell.get("role_column"),
                "person": cell.get("person"),
                "source_title": cell.get("source_title"),
                "disposition": "USER_COMPILED_RESEARCH_OBSERVATION",
                "verified": False,
                "pit_admitted": False,
                "source_class": "USER_COMPILED_RESEARCH_OBSERVATION",
            }
        )
    cells_path = out_dir / "CYCLE35_USER_CORPUS_2013_2026_STAFF_CELLS.jsonl"
    cells_path.write_text(
        "\n".join(json.dumps(row) for row in cells), encoding="utf-8"
    )
    summary = {
        "artifact_type": "CYCLE35_USER_CORPUS_2013_2026_STAFF_CELLS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": len(cells),
        "by_year": dict(by_year),
        "years_covered": sorted(int(y) for y in by_year),
        "skipped_no_season": skipped_no_season,
        "skipped_out_of_range": skipped_out_of_range,
        "skipped_no_person_blank_cell": skipped_no_person,
        "source_files_parsed": len(imported.get("files") or []),
        "not_replacement_population": True,
        "not_verified_wholesale": True,
        "same_parser_as_2000_2012_no_new_acquisition": True,
        "cells_path": str(cells_path),
        "pit_admitted": False,
    }
    (out_dir / "CYCLE35_USER_CORPUS_2013_2026_STAFF_CELLS.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = user_corpus_cells_2013_2026(out_dir)
    print(json.dumps(
        {
            "row_count": summary["row_count"],
            "years_covered": summary["years_covered"],
            "skipped_out_of_range": summary["skipped_out_of_range"],
            "skipped_no_person_blank_cell": summary["skipped_no_person_blank_cell"],
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
