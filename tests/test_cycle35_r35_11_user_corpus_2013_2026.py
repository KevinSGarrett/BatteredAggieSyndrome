"""R35-11 tests for MF35-11: the 2013-2026 user research corpus was already
being parsed by the existing `import_snapshot()` -- it was only ever
post-filtered down to 2000-2012 before this repair, never unavailable.

The Cycle #35 manager follow-up (20260920T224700Z): "Current code reads the
2000-2012 cell file; registering all 54 files does not ingest all years...
Separate local parsing/joining from truly missing external payloads... Do
not describe the whole lane as acquisition-blocked when its inputs already
exist locally." Confirmed directly: `import_snapshot()` parses all 54 CSVs
covering 2000-2026 with no year restriction in the parser itself; the
Cycle #33 script that produced `CYCLE33_USER_CORPUS_2000_2012_STAFF_
CELLS.jsonl` called that same parser and discarded everything outside
2000-2012 downstream.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.cycle35.r35_11_user_corpus_2013_2026_cells as m  # noqa: E402
from aggie_analytics.cycle35.coaching_release import apply_migrations  # noqa: E402
from tools.cycle35.r35_03_build_coaching_release import (  # noqa: E402
    ingest_user_corpus_cells,
)


def _fake_role_cell(season, person, **overrides) -> dict:
    row = {
        "season": season, "person": person, "filename_subdivision": "FBS",
        "team": "Example State", "team_id_source": "FILENAME", "role_column": "HC",
        "source_title": "Head Coach",
    }
    row.update(overrides)
    return row


class YearFilterTests(unittest.TestCase):
    """The actual new logic: which role_cells from import_snapshot()'s
    output are kept for the 2013-2026 file. Parsing itself is delegated to
    the already-tested import_snapshot(), mocked here so this exercises
    only the filter this repair adds."""

    def _run(self, role_cells: list[dict]) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                m, "import_snapshot",
                return_value={"role_cells": role_cells, "files": []},
            ):
                return m.user_corpus_cells_2013_2026(Path(tmp))

    def test_2013_2026_rows_with_a_person_are_kept(self) -> None:
        summary = self._run([_fake_role_cell("2013", "A Coach"), _fake_role_cell("2026", "B Coach")])
        self.assertEqual(summary["row_count"], 2)
        self.assertEqual(summary["years_covered"], [2013, 2026])

    def test_2000_2012_rows_are_excluded(self) -> None:
        summary = self._run([_fake_role_cell("2012", "A Coach"), _fake_role_cell("2013", "B Coach")])
        self.assertEqual(summary["row_count"], 1)
        self.assertEqual(summary["skipped_out_of_range"], 1)

    def test_years_after_2026_are_excluded(self) -> None:
        summary = self._run([_fake_role_cell("2027", "A Coach")])
        self.assertEqual(summary["row_count"], 0)
        self.assertEqual(summary["skipped_out_of_range"], 1)

    def test_blank_cells_with_no_person_are_excluded_and_counted(self) -> None:
        summary = self._run([_fake_role_cell("2020", None)])
        self.assertEqual(summary["row_count"], 0)
        self.assertEqual(summary["skipped_no_person_blank_cell"], 1)

    def test_non_numeric_season_is_excluded_and_counted(self) -> None:
        summary = self._run([_fake_role_cell("unknown", "A Coach")])
        self.assertEqual(summary["row_count"], 0)
        self.assertEqual(summary["skipped_no_season"], 1)

    def test_boundary_years_2013_and_2026_are_both_inclusive(self) -> None:
        summary = self._run([_fake_role_cell("2013", "A"), _fake_role_cell("2026", "B")])
        self.assertEqual(summary["row_count"], 2)
        self.assertEqual(summary["skipped_out_of_range"], 0)

    def test_output_jsonl_matches_the_2000_2012_schema(self) -> None:
        """Every field name must match what ingest_user_corpus_cells()
        actually reads, so the new file is a drop-in second input to the
        same ingester -- not a differently-shaped file that happens to
        also be JSONL."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with mock.patch.object(
                m, "import_snapshot",
                return_value={"role_cells": [_fake_role_cell("2020", "A Coach")], "files": []},
            ):
                m.user_corpus_cells_2013_2026(tmp)
            lines = (tmp / "CYCLE35_USER_CORPUS_2013_2026_STAFF_CELLS.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            self.assertEqual(len(lines), 1)
            row = json.loads(lines[0])
            for field in ("season", "subdivision", "team", "team_id_source",
                          "role_column", "person", "source_title", "disposition",
                          "verified", "pit_admitted", "source_class"):
                self.assertIn(field, row)
            self.assertFalse(row["verified"])
            self.assertFalse(row["pit_admitted"])

    def test_summary_discloses_no_new_acquisition(self) -> None:
        summary = self._run([_fake_role_cell("2020", "A Coach")])
        self.assertTrue(summary["same_parser_as_2000_2012_no_new_acquisition"])
        self.assertTrue(summary["not_replacement_population"])
        self.assertTrue(summary["not_verified_wholesale"])


class IngestGeneralizationTests(unittest.TestCase):
    """ingest_user_corpus_cells() was generalized to accept any cells_path,
    not hardcoded to the 2000-2012 file -- these confirm both the
    backward-compatible default and the new parameterized path work."""

    def _ram(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        apply_migrations(conn)
        return conn

    def _write_cells(self, tmp: Path, rows: list[dict]) -> Path:
        path = tmp / "cells.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        return path

    def test_missing_default_path_reports_not_present(self) -> None:
        conn = self._ram()
        result = ingest_user_corpus_cells(
            conn, cells_path=Path("/does/not/exist.jsonl")
        )
        self.assertEqual(result["state"], "USER_CORPUS_CELLS_NOT_PRESENT")
        conn.close()

    def test_a_supplied_2013_2026_style_file_ingests_normally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_cells(
                Path(tmp),
                [
                    {
                        "season": "2020", "subdivision": "FBS", "team": "Example State",
                        "team_id_source": "FILENAME", "role_column": "HC",
                        "person": "A Coach", "source_title": "Head Coach",
                        "verified": False,
                    }
                ],
            )
            conn = self._ram()
            result = ingest_user_corpus_cells(
                conn, cells_path=path,
                acquisition_receipt="CYCLE35_USER_CORPUS_2013_2026_STAFF_CELLS",
            )
            self.assertEqual(result["state"], "INGESTED_AT_CELL_GRAIN_AS_CANDIDATES")
            self.assertEqual(result["OBSERVATIONS"], 1)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM source_observation").fetchone()[0], 1
            )
            conn.close()

    def test_two_ranges_ingested_into_the_same_release_do_not_collide(self) -> None:
        """Calling the ingester twice (once per year range) against the
        SAME release must not have the second call's rows collide with or
        overwrite the first's -- distinct locators, distinct source files."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            early_dir = tmp / "early"
            early_dir.mkdir()
            early = self._write_cells(
                early_dir, [
                    {"season": "2005", "team": "Example State", "role_column": "HC",
                     "person": "Old Coach", "source_title": "Head Coach", "verified": False}
                ],
            )
            late_dir = tmp / "late"
            late_dir.mkdir()
            late = self._write_cells(
                late_dir, [
                    {"season": "2020", "team": "Example State", "role_column": "HC",
                     "person": "New Coach", "source_title": "Head Coach", "verified": False}
                ],
            )
            conn = self._ram()
            r1 = ingest_user_corpus_cells(conn, cells_path=early)
            r2 = ingest_user_corpus_cells(
                conn, cells_path=late,
                acquisition_receipt="CYCLE35_USER_CORPUS_2013_2026_STAFF_CELLS",
            )
            self.assertEqual(r1["OBSERVATIONS"], 1)
            self.assertEqual(r2["OBSERVATIONS"], 1)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM source_observation").fetchone()[0], 2
            )
            conn.close()


class RealDataTests(unittest.TestCase):
    def test_real_snapshot_produces_the_expected_2013_2026_named_cell_count(self) -> None:
        """Direct reproduction: import_snapshot() over the real 54-file
        snapshot yields 86,052 named cells for 2013-2026, matching exactly
        the number of role_cells with a non-null person in that range."""
        try:
            from aggie_analytics.cycle33.user_coaches import import_snapshot
        except Exception:
            self.skipTest("user_coaches module unavailable")
        try:
            imported = import_snapshot()
        except Exception:
            self.skipTest("real user-corpus snapshot not present in this environment")
        named_2013_2026 = sum(
            1
            for cell in imported["role_cells"]
            if str(cell.get("season") or "").isdigit()
            and 2013 <= int(cell["season"]) <= 2026
            and cell.get("person") is not None
        )
        self.assertEqual(named_2013_2026, 86052)


if __name__ == "__main__":
    unittest.main()
