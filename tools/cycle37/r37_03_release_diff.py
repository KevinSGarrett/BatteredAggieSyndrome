"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-03 AC11: the complete old/new row and cell diff between the corrected
release before the staff reparse (v37.1) and the release that carries it
(v37.2), and every evidence artifact that read the old release.

Rows are compared by their own identity column, and each shared row cell by
cell; a table without an identity column is compared as a multiset of whole
rows. The diff is written in full, not sampled. Descendants are the attempt's
evidence files that name the old release's content identity; each is listed
with whether a rerun against the new release exists.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
KEYS = {"staff_observation": "observation_id", "core_role_cell": "cell_id",
        "observation_binding_change": "observation_id", "canonical_program": "program_id",
        "career_episode": "episode_id"}
#: A table whose identity column is a build sequence is compared on its natural columns:
#: assignment ids are renumbered whenever any observation's assignments change.
NATURAL = {"staff_role_assignment": ["observation_id", "role_code", "unit", "qualifiers", "occupancy",
                                     "is_core_role"]}


def _open(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def _tables(conn: sqlite3.Connection) -> dict[str, list[str]]:
    names = [r[0] for r in conn.execute("select name from sqlite_master where type='table' order by name")]
    return {n: [c[1] for c in conn.execute(f'pragma table_info("{n}")')] for n in names}


def _rows(conn: sqlite3.Connection, table: str, columns: list[str]) -> list[tuple]:
    return conn.execute(f'select {", ".join(chr(34) + c + chr(34) for c in columns)} from "{table}"').fetchall()


def diff_table(old: sqlite3.Connection, new: sqlite3.Connection, table: str, old_cols: list[str],
               new_cols: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    key = KEYS.get(table)
    detail: list[dict[str, Any]] = []
    if key and key in old_cols and key in new_cols:
        shared = [c for c in new_cols if c in old_cols]
        before = {row[0]: row for row in _rows(old, table, [key, *shared])}
        after = {row[0]: row for row in _rows(new, table, [key, *shared])}
        changed_cells = collections.Counter()
        for ident in sorted(set(before) | set(after), key=str):
            if ident not in after:
                detail.append({"table": table, "id": ident, "change": "REMOVED"})
            elif ident not in before:
                detail.append({"table": table, "id": ident, "change": "ADDED"})
            else:
                for column, a, b in zip(shared, before[ident][1:], after[ident][1:]):
                    if a != b:
                        changed_cells[column] += 1
                        detail.append({"table": table, "id": ident, "change": "CELL", "column": column,
                                       "old": a, "new": b})
        summary = {"compared_by": key, "old_rows": len(before), "new_rows": len(after),
                   "added": sum(1 for d in detail if d["change"] == "ADDED"),
                   "removed": sum(1 for d in detail if d["change"] == "REMOVED"),
                   "rows_with_changed_cells": len({d["id"] for d in detail if d["change"] == "CELL"}),
                   "changed_cells_by_column": dict(changed_cells),
                   "columns_only_in_new": [c for c in new_cols if c not in old_cols],
                   "columns_only_in_old": [c for c in old_cols if c not in new_cols]}
        return summary, detail
    shared = NATURAL.get(table) or [c for c in new_cols if c in old_cols]
    before = collections.Counter(_rows(old, table, shared))
    after = collections.Counter(_rows(new, table, shared))
    added, removed = after - before, before - after
    for row, count in sorted(added.items(), key=str):
        detail.append({"table": table, "change": "ADDED", "row": list(row), "count": count})
    for row, count in sorted(removed.items(), key=str):
        detail.append({"table": table, "change": "REMOVED", "row": list(row), "count": count})
    return {"compared_by": f"NATURAL_COLUMNS {shared}" if table in NATURAL else "WHOLE_ROW_MULTISET",
            "old_rows": sum(before.values()), "new_rows": sum(after.values()),
            "added": sum(added.values()), "removed": sum(removed.values()),
            "columns_only_in_new": [c for c in new_cols if c not in old_cols],
            "columns_only_in_old": [c for c in old_cols if c not in new_cols]}, detail


def descendants(old_identity: str, new_identity: str) -> list[dict[str, Any]]:
    """Evidence files that read the old release, and whether a rerun names the new one."""

    found = []
    for path in sorted((ATTEMPT / "evidence").rglob("*.json")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if old_identity in text:
            found.append({"path": str(path.relative_to(ATTEMPT)), "names_old_release": True,
                          "names_new_release": new_identity in text})
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--new", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs")
    args = parser.parse_args(argv)
    old_identity, new_identity = args.old.parent.name, args.new.parent.name
    old, new = _open(args.old), _open(args.new)
    old_tables, new_tables = _tables(old), _tables(new)
    summaries, rows_written = {}, 0
    args.out.mkdir(parents=True, exist_ok=True)
    detail_path = args.out / "R37_03_RELEASE_DIFF_ROWS.jsonl"
    with _bas_atomic.open_write(detail_path, "w", encoding="utf-8") as handle:
        for table in sorted(set(old_tables) | set(new_tables)):
            if table not in old_tables:
                summaries[table] = {"state": "TABLE_ADDED", "new_rows": new.execute(
                    f'select count(*) from "{table}"').fetchone()[0]}
                continue
            if table not in new_tables:
                summaries[table] = {"state": "TABLE_REMOVED"}
                continue
            summary, detail = diff_table(old, new, table, old_tables[table], new_tables[table])
            summaries[table] = {"state": "UNCHANGED" if not detail else "CHANGED", **summary}
            for item in detail:
                handle.write(json.dumps(item, sort_keys=True, default=str) + "\n")
                rows_written += 1
    core = [json.loads(line) for line in detail_path.read_text(encoding="utf-8").splitlines()
            if '"table": "core_role_cell"' in line]
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-03-AC11",
        "old_release": {"content_identity": old_identity, "path": str(args.old)},
        "new_release": {"content_identity": new_identity, "path": str(args.new)},
        "tables": summaries, "diff_rows_written": rows_written,
        "diff_rows_sha256": hashlib.sha256(detail_path.read_bytes()).hexdigest(),
        "core_cells_changed": len({d["id"] for d in core}),
        "core_cell_changes": core[:200],
        "descendants": descendants(old_identity, new_identity),
        "not_claimed": "A diff of what changed. It does not show either release is correct beyond the tests and "
                       "samples cited with it.",
    }
    _bas_atomic.write_text(args.out / "R37_03_RELEASE_DIFF.json", json.dumps(report, indent=2, default=str) + "\n",
                                                       encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("core_cell_changes", "tables")}, indent=1,
                     default=str)[:3000])
    print(json.dumps({t: {k: v for k, v in s.items() if k in ("state", "added", "removed",
                                                                "rows_with_changed_cells")}
                      for t, s in summaries.items()}, indent=0)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
