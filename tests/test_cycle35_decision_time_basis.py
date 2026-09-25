"""Cycle #35 continuation (20260921T055921Z), section 5 -- build determinism.

"Fix the 26 nondeterministic adjudication timestamps using a legitimate
event/build-time distinction; verify repeated release reconstruction."

The distinction being pinned here: an operator's decision happens at a
moment and that moment is a fact about the decision, the same in every
build. A standing rule applied by the build happened when the rule was
written, not when the run executed, so there is no event time for the run
to record -- and reading the clock invents one rather than finding one.

All 26 divergent rows were the second kind. The tests below hold the repair
to the honest shape of it: the fabricated time is gone, the comparison that
caught it still looks at the column, and a real stated time still survives
into the row unchanged.
"""

from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle35.coaching_release import (  # noqa: E402
    INCIDENTAL_EXCLUDED_COLUMNS,
    LEGACY_BUILD_CLOCK_NOT_AN_EVENT_TIME,
    OPERATOR_STATED_EVENT_TIME,
    STANDING_RULE_NO_EVENT_TIME,
    apply_migrations,
    record_adjudication,
    record_conflict,
    release_row_identities,
)


def fresh() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_migrations(conn)
    return conn


def a_conflict(conn: sqlite3.Connection, key: str = "obs-1") -> str:
    return record_conflict(
        conn,
        subject_kind="source_observation",
        subject_key=key,
        reason="PREDECESSOR_CLAIMED_VERIFIED_WITHOUT_ROW_LEVEL_RECEIPT",
    )


def only_row(conn: sqlite3.Connection) -> dict:
    return dict(conn.execute("SELECT * FROM adjudication").fetchone())


class StandingRuleTests(unittest.TestCase):
    def test_a_rule_applied_by_the_build_records_no_time(self) -> None:
        conn = fresh()
        record_adjudication(
            conn,
            conflict_id=a_conflict(conn),
            decision="HELD_AT_CANDIDATE_LAYER",
            decided_by="CYCLE35_R35_03_INGEST",
            basis="A standing rule, applied to every row meeting the condition.",
        )
        row = only_row(conn)
        self.assertEqual(row["decision_time_basis"], STANDING_RULE_NO_EVENT_TIME)
        self.assertEqual(row["decided_at_utc"], "")

    def test_the_same_decision_is_identical_across_two_builds(self) -> None:
        """This is the 26-row divergence, at unit grain."""

        rows = []
        for _ in range(2):
            conn = fresh()
            record_adjudication(
                conn,
                conflict_id=a_conflict(conn),
                decision="HELD_AT_CANDIDATE_LAYER",
                decided_by="CYCLE35_R35_03_INGEST",
                basis="A standing rule, applied to every row meeting the condition.",
            )
            rows.append(only_row(conn))
        self.assertEqual(rows[0], rows[1])

    def test_row_identities_agree_across_two_builds(self) -> None:
        """The content hash is what the replay actually compares."""

        identities = []
        for _ in range(2):
            conn = fresh()
            record_adjudication(
                conn,
                conflict_id=a_conflict(conn),
                decision="BOTH_RETAINED_NEITHER_PROMOTED",
                decided_by="CYCLE35_R35_05",
                basis="Co-occupancy and contradiction are not distinguishable here.",
            )
            identities.append(release_row_identities(conn)["adjudication"])
        self.assertEqual(identities[0], identities[1])


class StatedEventTimeTests(unittest.TestCase):
    def test_a_stated_time_is_kept_and_labelled_as_an_event_time(self) -> None:
        conn = fresh()
        record_adjudication(
            conn,
            conflict_id=a_conflict(conn),
            decision="HELD_AT_CANDIDATE_LAYER",
            decided_by="operator",
            basis="Decided on review of the receipt.",
            decided_at_utc="2026-09-14T10:00:00+00:00",
        )
        row = only_row(conn)
        self.assertEqual(row["decided_at_utc"], "2026-09-14T10:00:00+00:00")
        self.assertEqual(row["decision_time_basis"], OPERATOR_STATED_EVENT_TIME)

    def test_whitespace_is_not_a_stated_time(self) -> None:
        conn = fresh()
        record_adjudication(
            conn,
            conflict_id=a_conflict(conn),
            decision="HELD_AT_CANDIDATE_LAYER",
            decided_by="operator",
            basis="Nothing was actually stated.",
            decided_at_utc="   ",
        )
        self.assertEqual(only_row(conn)["decision_time_basis"], STANDING_RULE_NO_EVENT_TIME)


class NoFabricationTests(unittest.TestCase):
    """The repair must be the removal of a fabricated value, not a way of
    hiding the disagreement it caused."""

    def test_the_build_clock_is_unreachable_from_the_record_functions(self) -> None:
        source = (
            ROOT / "src" / "aggie_analytics" / "cycle35" / "coaching_release.py"
        ).read_text(encoding="utf-8")
        body = source.split("def apply_migrations")[1]
        self.assertNotIn(
            "datetime.now",
            body.split("def record_adjudication")[-1],
            "no code after the migration applier may read the wall clock",
        )

    def test_the_timestamp_column_is_still_compared(self) -> None:
        """Excluding it would silence the report and leave the fabricated
        value in the release. INCIDENTAL_EXCLUDED_COLUMNS stays empty."""

        self.assertEqual(INCIDENTAL_EXCLUDED_COLUMNS, {})

    def test_a_legacy_row_keeps_its_value_and_is_labelled(self) -> None:
        """Migrating an already-delivered database must neither erase the
        build-clock reading nor promote it to an event time."""

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        # Bring it only as far as the schema that had the fault.
        import aggie_analytics.cycle35.coaching_release as release

        for version, script in release.MIGRATIONS:
            if version >= 5:
                break
            conn.executescript(script)
        conn.execute(
            "INSERT INTO conflict (conflict_id, subject_kind, subject_key, reason) "
            "VALUES ('cfl:x','source_observation','obs-1','R')"
        )
        conn.execute(
            "INSERT INTO adjudication (adjudication_id, conflict_id, decision, "
            "decided_by, basis, decided_at_utc) VALUES "
            "('adj:x','cfl:x','HELD_AT_CANDIDATE_LAYER','build','r',"
            "'2026-09-20T22:13:41.512345+00:00')"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migration ("
            " version INTEGER PRIMARY KEY, applied_at_utc TEXT NOT NULL)"
        )
        conn.executemany(
            "INSERT INTO schema_migration (version, applied_at_utc) VALUES (?, 'x')",
            [(v,) for v, _ in release.MIGRATIONS if v < 5],
        )
        conn.commit()
        apply_migrations(conn)

        row = dict(conn.execute("SELECT * FROM adjudication").fetchone())
        self.assertEqual(row["decided_at_utc"], "2026-09-20T22:13:41.512345+00:00")
        self.assertEqual(
            row["decision_time_basis"], LEGACY_BUILD_CLOCK_NOT_AN_EVENT_TIME
        )


if __name__ == "__main__":
    unittest.main()
