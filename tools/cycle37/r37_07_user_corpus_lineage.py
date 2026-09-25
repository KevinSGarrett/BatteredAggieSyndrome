"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-07 AC02 / MF36-07: cell-grain lineage for the 110,044 user-corpus cells,
and the declared rights of every source class the release carries.

The delivered release keeps each user cell's team, season, role column and
person as written, but not where in which file it was written. This tool
replays the Cycle #33 importer over the same 54-file snapshot (whose file
digests the importer checks against the manifest), aligns its named cells
one for one with the delivered rows, and checks every aligned pair on team,
season, role column and person. Each cell then carries its file and digest,
its CSV record ordinal and physical line range, its column header, column
index and spreadsheet address, and the character span of the person inside
the cell text.

Rights are bound to the project's declared source register
(``docs/data_research/w06/SOURCE_ACCESS_LICENSE_MATRIX.csv``). A source class
the register does not list is recorded as undeclared, not given a label.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle33 import user_coaches
from aggie_analytics import atomic_io as _bas_atomic  # noqa: E402

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
DELIVERED = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle36/runs/20260921T200027Z/implementation_output"
                 r"/CYCLE36_USER_CORPUS_CELLS.jsonl")
REGISTER = ROOT / "docs" / "data_research" / "w06" / "SOURCE_ACCESS_LICENSE_MATRIX.csv"
#: The release's source classes and the register row each one is, or None.
SOURCE_CLASSES = {
    "OFFICIAL_STAFF_HTML": "SRC-005",
    "CFBD_GAMES_AND_TEAMS": "SRC-002",
    "WIKIMEDIA_ENCYCLOPEDIA_REVISIONS": None,
    "USER_CORPUS_2000_2012": None,
    "USER_CORPUS_2013_2026": None,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def column_letters(index: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA."""

    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def record_lines(path: Path) -> tuple[list[str], list[tuple[int, int]]]:
    """Headers, and each data record's first and last physical line (1-based)."""

    text = path.read_bytes().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text), strict=True)
    headers = next(reader)
    spans = []
    before = reader.line_num
    for _ in reader:
        spans.append((before + 1, reader.line_num))
        before = reader.line_num
    return headers, spans


def lineage(out_dir: Path) -> dict[str, Any]:
    imported = user_coaches.import_snapshot(import_time_utc="2026-09-23T00:00:00+00:00")
    snapshot = Path(user_coaches.DEFAULT_SNAPSHOT)
    files = {row["relative_path"]: row for row in imported["files"]}
    named = [cell for cell in imported["role_cells"] if cell.get("person") is not None]

    def in_range(cell: dict[str, Any], low: int, high: int) -> bool:
        season = str(cell.get("season") or "")
        return season.isdigit() and low <= int(season) <= high

    replay = ([cell for cell in named if in_range(cell, 2000, 2012)]
              + [cell for cell in named if in_range(cell, 2013, 2026)])
    delivered = [json.loads(line) for line in DELIVERED.read_text(encoding="utf-8").splitlines() if line.strip()]
    geometry = {name: record_lines(snapshot / name) for name in files}

    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / "R37_07_USER_CORPUS_LINEAGE.jsonl"
    mismatches: list[dict[str, Any]] = []
    span_missing = 0
    with _bas_atomic.open_write(rows_path, "w", encoding="utf-8", newline="\n") as handle:
        for index, (cell, row) in enumerate(zip(replay, delivered)):
            expected = (str(row.get("team_as_written")), str(row.get("season_as_written") or row.get("season")),
                        str(row.get("role_column")), str(row.get("person_as_written")))
            got = (str(cell.get("team")), str(cell.get("season")), str(cell.get("role_column")), str(cell.get("person")))
            if expected != got:
                mismatches.append({"user_cell_id": index + 1, "delivered": expected, "replayed": got})
            name = cell["source_file"]
            headers, spans = geometry[name]
            column = headers.index(cell["role_column"]) if cell["role_column"] in headers else None
            first, last = spans[cell["record_ordinal"]]
            text = str(cell.get("cell_text") or "")
            start = text.find(str(cell["person"]))
            span_missing += start < 0
            handle.write(json.dumps({
                "user_cell_id": index + 1, "source_class": row.get("source_class"), "source_file": name,
                "snapshot_path": str(snapshot / name), "file_sha256": files[name]["sha256"],
                "record_ordinal": cell["record_ordinal"], "csv_lines": [first, last],
                "column_header": cell["role_column"], "column_index": column,
                "spreadsheet_cell": (f"{column_letters(column)}{cell['record_ordinal'] + 2}"
                                     if column is not None else None),
                "cell_text_sha256": sha256_bytes(text.encode("utf-8")),
                "person_char_span": [start, start + len(str(cell["person"]))] if start >= 0 else None,
                "segment_text": cell.get("segment_text"), "observation_id": cell.get("observation_id"),
            }, sort_keys=True) + "\n")
    register_rows = {row["source_id"]: row for row in csv.DictReader(REGISTER.open(encoding="utf-8"))}
    rights = []
    for source_class, source_id in SOURCE_CLASSES.items():
        row = register_rows.get(source_id) if source_id else None
        rights.append({
            "source_class": source_class, "register_source_id": source_id,
            "state": "DECLARED_IN_PROJECT_REGISTER" if row else "NOT_DECLARED_IN_PROJECT_REGISTER",
            "terms_or_license": (row or {}).get("terms_or_license"),
            "redistribution": (row or {}).get("redistribution"),
            "private_research_policy": (row or {}).get("private_research_policy"),
            "public_repository_suitability": (row or {}).get("public_repository_suitability"),
            "local_only_recommendation": (row or {}).get("local_only_recommendation"),
            "classification": ("USER_COMPILED_RESEARCH_OBSERVATION; per-file fact_verification in the snapshot "
                               "manifest" if source_class.startswith("USER_CORPUS") else None),
        })
    summary = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-07",
        "rows": ["R37-07-AC02", "R37-07-CF-MF36-07"],
        "delivered_cells": len(delivered), "replayed_named_cells": len(replay),
        "aligned": min(len(delivered), len(replay)), "mismatches": mismatches[:50],
        "mismatch_count": len(mismatches), "person_span_not_found_in_cell": span_missing,
        "snapshot": {"path": str(snapshot), "files": len(files),
                     "manifest_digests_checked_by_importer": True},
        "delivered_source": {"path": str(DELIVERED), "sha256": sha256_bytes(DELIVERED.read_bytes())},
        "register": {"path": str(REGISTER.relative_to(ROOT)).replace("\\", "/"),
                     "sha256": sha256_bytes(REGISTER.read_bytes())},
        "source_rights": rights,
        "grain_accounting": {
            key: imported.get(key) for key in (
                "file_count", "staff_file_count", "queue_file_count", "staff_observation_count", "staff_row_count",
                "queue_row_count", "physically_present_role_cells", "parsed_person_segment_count",
                "emitted_role_assignment_records", "role_cell_count", "distinct_source_role_cell_ids",
                "records_with_person", "canonical_people_count", "quarantined_count")
        } | {"named_cells_in_release": len(delivered),
             "grains_are_not_unique_people": imported.get("grains_are_not_unique_people")},
        "spreadsheet_address_basis": ("header on row 1; data record n on row n + 2 as a spreadsheet opens the CSV; "
                                      "csv_lines gives the physical lines of the record in the file"),
        "written": {"rows": str(rows_path), "rows_sha256": sha256_bytes(rows_path.read_bytes())},
    }
    _bas_atomic.write_text(out_dir / "R37_07_USER_CORPUS_LINEAGE.json", json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs")
    args = parser.parse_args(argv)
    summary = lineage(args.out)
    print(json.dumps({k: summary[k] for k in ("delivered_cells", "replayed_named_cells", "mismatch_count",
                                               "person_span_not_found_in_cell")}, indent=1))
    return 0 if summary["mismatch_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
