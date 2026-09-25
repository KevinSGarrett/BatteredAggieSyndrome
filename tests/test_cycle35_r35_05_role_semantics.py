"""R35-05 tests for MF35-05: the release build must preserve the real
structured role/qualifier semantics `assignments_from_title` already
computes, and must never fill a missing season in by assumption.

The Cycle #35 manager follow-up found two concrete defects in
tools/cycle35/r35_03_build_coaching_release.py's ingestion:

* `ingest_reparsed_staff` took `sorted(principal_role_families(title))`,
  kept only `families[0]` as the row's `role_family`, and stuffed the
  REMAINING family names into `qualifiers` -- which is not what a qualifier
  is (CO/INTERIM/ASSISTANT/etc, not "the other HC/OC/DC bucket"). Real
  multi-assignment titles like Mike Weick's "Assistant Head Coach/Co-
  Defensive Coordinator/Inside Linebackers" collapsed to a single
  `defensive_coordinator` row with an empty `qualifiers` list, discarding
  the CO qualifier, the assistant-head-coach assignment and the position
  assignment entirely.
* `ingest_membership` computed `season = int(row.get("season") or 2026)`,
  silently assuming 2026 for any row with no stated season -- the exact
  "filled in by assumption" fabrication the finding named.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import tools.cycle35.r35_03_build_coaching_release as builder  # noqa: E402
from aggie_analytics.cycle35.coaching_release import (  # noqa: E402
    assertions_not_entailed_by_linked_observations,
    open_release,
)


def _write_reparsed_row(tmp: Path, raw_html: Path, **overrides) -> dict:
    row = {
        "raw_path": str(raw_html),
        "person": "Test Coach",
        "program_id": "P:TEST",
        "source_title": "Head Coach",
        "rebuilt_record_selector": "tr[0]",
        "rebuilt_record_title": "Head Coach",
        "episode_key": "P:TEST|head_coach|Test Coach|Head Coach|abc|0|0",
        "strata": {"era": "CURRENT"},
        "rebuilt_role_claim_supported": True,
        "rebuilt_person_record_bound": True,
        "disposition": "RETAINED_SUPPORTED",
    }
    row.update(overrides)
    return row


class MultiRoleIngestionTests(unittest.TestCase):
    def _run(self, tmp: Path, rows: list[dict]) -> tuple[sqlite3.Connection, dict]:
        raw_html = tmp / "staff.html"
        raw_html.write_text("<table></table>", encoding="utf-8")
        rebuild_rows = tmp / "rebuild_rows.jsonl"
        rebuild_rows.write_text(
            "\n".join(json.dumps(row) for row in rows), encoding="utf-8"
        )
        conn = open_release(tmp / "release.sqlite")
        stats = builder.ingest_reparsed_staff(conn, rebuild_rows)
        conn.commit()
        return conn, stats

    def test_multi_assignment_title_produces_one_row_per_real_assignment(self) -> None:
        """The exact Mike Weick title the manager found in the real r7
        release: three real assignments (assistant head coach, a CO-shared
        DC seat, and an inside-linebackers position role), each with the CO
        qualifier where the source text actually says "Co-"."""
        title = "Assistant Head Coach/Co-Defensive Coordinator/Inside Linebackers"
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            conn, stats = self._run(
                tmp,
                [
                    _write_reparsed_row(
                        tmp, tmp / "staff.html",
                        person="Mike Weick", source_title=title,
                        rebuilt_record_title=title,
                    )
                ],
            )
            rows = conn.execute(
                "SELECT role_family, qualifiers, principal_role_blocked, "
                "exact_title_text FROM formal_role_assertion"
            ).fetchall()
            role_families = {r["role_family"] for r in rows}
            self.assertIn("defensive_coordinator", role_families)
            self.assertIn("inside_linebackers", role_families)
            self.assertGreaterEqual(len(rows), 2)

            dc_row = next(r for r in rows if r["role_family"] == "defensive_coordinator")
            self.assertIn("CO", json.loads(dc_row["qualifiers"]))
            self.assertFalse(dc_row["principal_role_blocked"])

            for row in rows:
                self.assertEqual(row["exact_title_text"], title)

            # Every emitted assertion must actually be entailed by the
            # observation it is linked to -- proving MF35-05's multi-role
            # ingestion and MF35-03's entailment check are compatible, not
            # just individually passing.
            self.assertEqual(assertions_not_entailed_by_linked_observations(conn), [])
            conn.close()

    def test_simple_single_role_title_is_unaffected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            conn, stats = self._run(
                tmp,
                [_write_reparsed_row(tmp, tmp / "staff.html", source_title="Head Coach",
                                      rebuilt_record_title="Head Coach")],
            )
            rows = conn.execute(
                "SELECT role_family, qualifiers, principal_role_blocked "
                "FROM formal_role_assertion"
            ).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["role_family"], "head_coach")
            self.assertEqual(json.loads(rows[0]["qualifiers"]), [])
            self.assertFalse(rows[0]["principal_role_blocked"])
            conn.close()

    def test_unmapped_title_falls_back_to_unspecified_assistant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            conn, stats = self._run(
                tmp,
                [_write_reparsed_row(tmp, tmp / "staff.html", source_title="",
                                      rebuilt_record_title="")],
            )
            rows = conn.execute(
                "SELECT role_family, principal_role_blocked FROM formal_role_assertion"
            ).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["role_family"], "UNSPECIFIED_ASSISTANT")
            self.assertTrue(rows[0]["principal_role_blocked"])
            conn.close()

    def test_co_shared_offensive_coordinator_qualifier_is_preserved(self) -> None:
        title = "Co-Offensive Coordinator/Quarterbacks"
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            conn, stats = self._run(
                tmp,
                [_write_reparsed_row(tmp, tmp / "staff.html", source_title=title,
                                      rebuilt_record_title=title)],
            )
            rows = conn.execute(
                "SELECT role_family, qualifiers FROM formal_role_assertion"
            ).fetchall()
            oc_row = next(r for r in rows if r["role_family"] == "offensive_coordinator")
            self.assertIn("CO", json.loads(oc_row["qualifiers"]))
            conn.close()


class MembershipSeasonTests(unittest.TestCase):
    def _run_membership(self, tmp: Path, rows: list[dict]) -> tuple[sqlite3.Connection, dict]:
        membership_path = tmp / "membership.jsonl"
        membership_path.write_text(
            "\n".join(json.dumps(row) for row in rows), encoding="utf-8"
        )
        original_membership = builder.MEMBERSHIP
        builder.MEMBERSHIP = (membership_path,)
        try:
            conn = open_release(tmp / "release.sqlite")
            stats = builder.ingest_membership(conn)
            conn.commit()
        finally:
            builder.MEMBERSHIP = original_membership
        return conn, stats

    def test_row_with_a_stated_season_is_ingested_normally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            conn, stats = self._run_membership(
                tmp, [{"program_id": "P:1", "display_name": "Example", "season": 2018}]
            )
            self.assertEqual(stats["rows_missing_season"], 0)
            self.assertEqual(stats["programs"], 1)
            row = conn.execute(
                "SELECT first_season, last_season FROM canonical_program WHERE program_id = ?",
                ("P:1",),
            ).fetchone()
            self.assertEqual(row["first_season"], 2018)
            conn.close()

    def test_row_missing_season_is_skipped_not_assumed_2026(self) -> None:
        """MF35-05: this previously computed `int(row.get("season") or
        2026)`, so a row with no stated season silently became a 2026
        program-season binding. It must now be skipped and counted, never
        dated by assumption."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            conn, stats = self._run_membership(
                tmp, [{"program_id": "P:NO_SEASON", "display_name": "Unknown Year"}]
            )
            self.assertEqual(stats["rows_missing_season"], 1)
            self.assertEqual(stats["programs"], 0)
            row = conn.execute(
                "SELECT * FROM canonical_program WHERE program_id = ?",
                ("P:NO_SEASON",),
            ).fetchone()
            self.assertIsNone(row)
            cells = conn.execute(
                "SELECT COUNT(*) FROM expected_cell WHERE program_id = ?",
                ("P:NO_SEASON",),
            ).fetchone()[0]
            self.assertEqual(cells, 0)
            conn.close()

    def test_empty_string_season_is_also_treated_as_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            conn, stats = self._run_membership(
                tmp, [{"program_id": "P:BLANK", "season": ""}]
            )
            self.assertEqual(stats["rows_missing_season"], 1)
            conn.close()

    def test_mixed_rows_only_skip_the_ones_missing_a_season(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            conn, stats = self._run_membership(
                tmp,
                [
                    {"program_id": "P:WITH", "season": 2020},
                    {"program_id": "P:WITHOUT"},
                ],
            )
            self.assertEqual(stats["rows_missing_season"], 1)
            self.assertEqual(stats["programs"], 1)
            conn.close()


if __name__ == "__main__":
    unittest.main()
