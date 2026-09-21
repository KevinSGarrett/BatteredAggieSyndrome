"""R35-20: build the coaching release twice and compare its full scientific content.

Cycle #35 closeout review (20260921T025300Z), section 1: "execute the two
real release rebuilds in separate isolated outputs; compare complete
scientific row contents, source links, conflict dispositions and expected
populations, not just IDs or counts."

Two independent builds of identical inputs must produce identical
SCIENTIFIC content. The comparison deliberately does not stop at row
counts or primary keys: `release_row_identities` hashes every column of
every row across all fifteen content tables, which is what makes a
changed `exact_title_text`, `role_family` or `evidence_layer` visible.
The database FILE bytes are expected to differ -- SQLite page layout is
not a scientific fact -- which is exactly why row identity rather than
file hash is the test.

On top of the identity comparison this tool reports, per build and as a
diff, the specific dimensions the review named:

* source links      -- assertion_support rows, and any assertion lacking one
* conflict dispositions -- conflict and adjudication rows by state
* expected populations  -- expected_cell rows and their declared totals

Read-only with respect to any existing release: both builds are written
into fresh isolated directories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle35.coaching_release import (  # noqa: E402
    _CONTENT_TABLES,
    release_row_identities,
)

BUILDER = REPO_ROOT / "tools" / "cycle35" / "r35_03_build_coaching_release.py"
DEFAULT_REBUILD_ROWS = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\20260920T172801Z"
    r"\implementation_output\R35_02_STAFF_REBUILD_ROWS.jsonl"
)


def sha256_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def run_build(out_dir: Path, rebuild_rows: Path, release_name: str, career_tranche: str) -> dict[str, Any]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-B",
        str(BUILDER),
        "--out-dir",
        str(out_dir),
        "--rebuild-rows",
        str(rebuild_rows),
        "--release-name",
        release_name,
    ]
    if career_tranche:
        command += ["--career-tranche", career_tranche]
    env = {
        **dict(__import__("os").environ),
        "PYTHONPATH": str(REPO_ROOT / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
    }
    started = datetime.now(timezone.utc)
    completed = subprocess.run(
        command, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    ended = datetime.now(timezone.utc)
    databases = sorted(out_dir.glob("*.sqlite"))
    return {
        "command": command,
        "exit_code": completed.returncode,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
        "duration_seconds": round((ended - started).total_seconds(), 3),
        "out_dir": str(out_dir),
        "database": str(databases[0]) if databases else None,
        "database_sha256": sha256_file(databases[0]) if databases else None,
        "stderr_tail": (completed.stderr or "").strip().splitlines()[-8:],
    }


def scientific_profile(db_path: Path) -> dict[str, Any]:
    """Full scientific content of one release, not just its counts."""

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        counts: dict[str, int] = {}
        for table, _ in _CONTENT_TABLES:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
            counts[table] = int(cursor.fetchone()[0])

        identities = release_row_identities(conn)

        cursor.execute(
            "SELECT assertion_table, COUNT(*) AS n FROM assertion_support "
            "GROUP BY assertion_table ORDER BY assertion_table"
        )
        support_by_table = {str(r["assertion_table"]): int(r["n"]) for r in cursor.fetchall()}
        cursor.execute(
            "SELECT COUNT(*) FROM formal_role_assertion a WHERE NOT EXISTS ("
            "SELECT 1 FROM assertion_support s WHERE s.assertion_id = a.assertion_id)"
        )
        unsupported = int(cursor.fetchone()[0])

        def group(table: str, column: str) -> dict[str, int]:
            try:
                cursor.execute(
                    f"SELECT {column} AS k, COUNT(*) AS n FROM {table} "  # noqa: S608
                    f"GROUP BY {column} ORDER BY {column}"
                )
            except sqlite3.OperationalError:
                return {}
            return {str(r["k"]): int(r["n"]) for r in cursor.fetchall()}

        return {
            "row_counts": counts,
            "row_identities": identities,
            "source_links": {
                "assertion_support_rows": counts.get("assertion_support", 0),
                "by_assertion_table": support_by_table,
                "formal_role_assertions_without_support": unsupported,
            },
            "conflict_dispositions": {
                "conflict_rows": counts.get("conflict", 0),
                "conflict_by_state": group("conflict", "conflict_state"),
                "adjudication_rows": counts.get("adjudication", 0),
                "adjudication_by_decision": group("adjudication", "decision"),
                "person_identity_adjudications": counts.get(
                    "person_identity_adjudication", 0
                ),
            },
            "expected_populations": {
                "expected_cell_rows": counts.get("expected_cell", 0),
                "by_season_sample": group("expected_cell", "season"),
            },
            "evidence_layers": group("formal_role_assertion", "evidence_layer"),
        }
    finally:
        conn.close()


#: Columns this module writes from the wall clock at build time. They are
#: NOT removed from the content hash -- coaching_release.py argues
#: explicitly that who decided what and when is part of the adjudication
#: record, and INCIDENTAL_EXCLUDED_COLUMNS "must never be used to make a
#: real disagreement disappear". They are named here only so a divergence
#: confined to them can be REPORTED precisely rather than hidden.
BUILD_CLOCK_COLUMNS: dict[str, frozenset[str]] = {
    "adjudication": frozenset({"decided_at_utc"}),
    "person_identity_adjudication": frozenset({"decided_at_utc"}),
}


def column_level_diff(first_db: Path, second_db: Path, table: str, order_by: tuple[str, ...]) -> dict[str, Any]:
    """Which columns actually differ, and in how many rows."""

    def rows_of(path: Path) -> list[dict[str, Any]]:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            conn.row_factory = sqlite3.Row
            order = ", ".join(order_by)
            return [
                dict(row)
                for row in conn.execute(f"SELECT * FROM {table} ORDER BY {order}")  # noqa: S608
            ]
        finally:
            conn.close()

    left, right = rows_of(first_db), rows_of(second_db)
    if len(left) != len(right):
        return {
            "table": table,
            "row_count_differs": True,
            "first_rows": len(left),
            "second_rows": len(right),
        }
    differing: dict[str, int] = {}
    for a, b in zip(left, right):
        for column in a:
            if a[column] != b[column]:
                differing[column] = differing.get(column, 0) + 1
    clock = BUILD_CLOCK_COLUMNS.get(table, frozenset())
    return {
        "table": table,
        "row_count_differs": False,
        "rows": len(left),
        "columns_differing": differing,
        "all_differing_columns_are_build_clock": bool(differing)
        and set(differing).issubset(clock),
        "build_clock_columns_for_this_table": sorted(clock),
    }


def diff_profiles(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    """Every scientific difference between two builds, by dimension."""

    differences: list[dict[str, Any]] = []

    for table in sorted(set(first["row_counts"]) | set(second["row_counts"])):
        a, b = first["row_counts"].get(table), second["row_counts"].get(table)
        if a != b:
            differences.append(
                {"dimension": "row_count", "table": table, "first": a, "second": b}
            )

    ident_a, ident_b = first["row_identities"], second["row_identities"]
    for key in sorted(set(ident_a) | set(ident_b)):
        if ident_a.get(key) != ident_b.get(key):
            differences.append(
                {
                    "dimension": "row_identity",
                    "table": key,
                    "first": ident_a.get(key),
                    "second": ident_b.get(key),
                }
            )

    for dimension in ("source_links", "conflict_dispositions", "expected_populations", "evidence_layers"):
        if first.get(dimension) != second.get(dimension):
            differences.append(
                {
                    "dimension": dimension,
                    "first": first.get(dimension),
                    "second": second.get(dimension),
                }
            )

    return {
        "identical": not differences,
        "difference_count": len(differences),
        "differences": differences,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--rebuild-rows", default=str(DEFAULT_REBUILD_ROWS))
    parser.add_argument("--career-tranche", default="")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rebuild_rows = Path(args.rebuild_rows)
    if not rebuild_rows.is_file():
        result = {
            "artifact_type": "CYCLE35_DETERMINISTIC_RELEASE_REPLAY",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "state": "NOT_RUN_INPUT_ABSENT",
            "rebuild_rows": str(rebuild_rows),
            "reason": "The staff rebuild-rows input is not present, so two "
            "real builds of identical inputs cannot be performed.",
        }
        (out_dir / "CYCLE35_DETERMINISTIC_RELEASE_REPLAY.json").write_text(
            json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(json.dumps(result, indent=1))
        return 1

    builds = []
    for index in (1, 2):
        build = run_build(
            out_dir / f"replay_{index}",
            rebuild_rows,
            f"replay{index}",
            args.career_tranche,
        )
        build["replay"] = index
        builds.append(build)

    failed = [b for b in builds if b["exit_code"] != 0 or not b["database"]]
    if failed:
        result = {
            "artifact_type": "CYCLE35_DETERMINISTIC_RELEASE_REPLAY",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "state": "BUILD_FAILED",
            "builds": builds,
        }
        (out_dir / "CYCLE35_DETERMINISTIC_RELEASE_REPLAY.json").write_text(
            json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(json.dumps({"state": "BUILD_FAILED",
                          "exit_codes": [b["exit_code"] for b in builds],
                          "stderr": [b["stderr_tail"] for b in builds]}, indent=1))
        return 1

    profiles = [scientific_profile(Path(b["database"])) for b in builds]
    comparison = diff_profiles(profiles[0], profiles[1])

    # For every table whose identity hash moved, report WHICH columns moved
    # and in how many rows, so a divergence can be characterised exactly
    # instead of being either hidden or left as an opaque hash mismatch.
    order_by = dict(_CONTENT_TABLES)
    column_diffs = [
        column_level_diff(
            Path(builds[0]["database"]),
            Path(builds[1]["database"]),
            item["table"],
            order_by.get(item["table"], ("rowid",)),
        )
        for item in comparison["differences"]
        if item["dimension"] == "row_identity"
    ]
    comparison["column_level_diffs"] = column_diffs
    non_clock = [
        diff
        for diff in column_diffs
        if diff.get("row_count_differs") or not diff.get("all_differing_columns_are_build_clock")
    ]
    comparison["differences_outside_build_clock_columns"] = len(non_clock) + sum(
        1 for item in comparison["differences"] if item["dimension"] != "row_identity"
    )
    comparison["scientific_content_identical_apart_from_build_clock"] = (
        comparison["differences_outside_build_clock_columns"] == 0
    )

    result = {
        "artifact_type": "CYCLE35_DETERMINISTIC_RELEASE_REPLAY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "state": "COMPARED",
        "rebuild_rows": str(rebuild_rows),
        "rebuild_rows_sha256": sha256_file(rebuild_rows),
        "builds": builds,
        "profiles": profiles,
        "comparison": comparison,
        "scientific_content_identical": comparison["identical"],
        "scientific_content_identical_apart_from_build_clock": comparison[
            "scientific_content_identical_apart_from_build_clock"
        ],
        "build_clock_columns_are_reported_not_excluded": (
            "coaching_release.INCIDENTAL_EXCLUDED_COLUMNS stays empty. A "
            "divergence confined to a wall-clock column is characterised "
            "here by name and row count rather than removed from the hash, "
            "because that set must never be used to make a real "
            "disagreement disappear."
        ),
        "database_file_bytes_identical": (
            builds[0]["database_sha256"] == builds[1]["database_sha256"]
        ),
        "why_row_identity_not_file_hash": (
            "SQLite page layout is not a scientific fact. Two builds of the "
            "same inputs may differ byte-for-byte while carrying identical "
            "scientific content, so the test is full per-row content "
            "identity across every content table, plus source links, "
            "conflict dispositions and expected populations."
        ),
        "tables_compared": [table for table, _ in _CONTENT_TABLES],
        "comparison_covers_every_column_not_just_keys": True,
    }
    (out_dir / "CYCLE35_DETERMINISTIC_RELEASE_REPLAY.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "state": result["state"],
                "scientific_content_identical": result["scientific_content_identical"],
                "database_file_bytes_identical": result["database_file_bytes_identical"],
                "difference_count": comparison["difference_count"],
                "differences_outside_build_clock_columns": comparison[
                    "differences_outside_build_clock_columns"
                ],
                "scientific_content_identical_apart_from_build_clock": comparison[
                    "scientific_content_identical_apart_from_build_clock"
                ],
                "column_level_diffs": comparison["column_level_diffs"],
                "tables_compared": len(result["tables_compared"]),
                "row_counts": profiles[0]["row_counts"],
                "source_links": profiles[0]["source_links"],
                "conflict_dispositions": profiles[0]["conflict_dispositions"],
                "expected_populations": {
                    "expected_cell_rows": profiles[0]["expected_populations"][
                        "expected_cell_rows"
                    ]
                },
            },
            indent=1,
        )
    )
    return 0 if comparison["identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
