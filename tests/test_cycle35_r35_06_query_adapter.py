"""R35-06 tests for MF35-06: the installed staff-query CLI must consume the
actual cycle35 coaching release, not only the legacy cycle33 delivery.

The Cycle #35 manager follow-up (20260920T205200Z) ran the installed
`bas-staff-query` entry point's own code path -- `from
aggie_analytics.cycle33.query import team_staff` then
`team_staff(db, team='Princeton', season='2026')` against the delivered r7
release -- and got `OperationalError: no such table: staff_role_cells`. The
release the CLI is meant to serve uses `cycle35.coaching_release`'s
normalized schema; `cycle33.query` had never been taught to recognize it.

These tests exercise the fix from both sides: `aggie_analytics.cycle35.query`
directly (schema detection and the cycle35-native read functions), and
`aggie_analytics.cycle33.query`'s public functions -- the ones the installed
CLI actually calls -- proving they now dispatch correctly for EITHER schema
kind without changing legacy behavior for a legacy database.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.cycle33.query import (
    connect_for_import,
    connect_readonly,
    load_import,
)
from aggie_analytics.cycle33.query import (
    coach_career as legacy_dispatch_coach_career,
)
from aggie_analytics.cycle33.query import (
    team_staff as legacy_dispatch_team_staff,
)
from aggie_analytics.cycle33.query import (
    unresolved_roles as legacy_dispatch_unresolved_roles,
)
from aggie_analytics.cycle35.coaching_release import (
    LAYER_CANDIDATE,
    LAYER_OFFICIAL,
    add_episode,
    add_observation,
    add_role,
    open_release,
    register_source_file,
    transaction,
    upsert_person,
    upsert_program,
)
from aggie_analytics.cycle35.query import (
    SCHEMA_KIND_CYCLE33,
    SCHEMA_KIND_CYCLE35,
    SCHEMA_KIND_UNKNOWN,
    coach_career,
    role_state_conservation,
    schema_kind,
    team_schemes,
    team_staff,
    unresolved_roles,
)


def _build_release(tmp: Path) -> Path:
    """A real cycle35 release with one resolved role and one unresolved one,
    across two programs, exercising an alias so career lookup has something
    real to resolve through."""

    db_path = tmp / "release.sqlite"
    conn = open_release(db_path)
    source = tmp / "staff.html"
    source.write_text(
        "<table>"
        "<tr><td>Bob Surace</td><td>Head Coach</td></tr>"
        "<tr><td>New Coach</td><td>Offensive Coordinator</td></tr>"
        "</table>",
        encoding="utf-8",
    )
    with transaction(conn):
        source_file_id = register_source_file(
            conn, source, source_class="OFFICIAL_STAFF_HTML", rights_state="PRIVATE"
        )
        obs_official = add_observation(
            conn,
            source_file_id=source_file_id,
            locator="tr[0]",
            parser_identity="TEST",
            observed_person="Bob Surace",
            observed_title="Head Coach",
        )
        obs_candidate = add_observation(
            conn,
            source_file_id=source_file_id,
            locator="tr[1]",
            parser_identity="TEST",
            observed_person="New Coach",
            observed_title="Offensive Coordinator",
            evidence_layer=LAYER_CANDIDATE,
        )
        upsert_program(conn, "P:PRINCETON", display_name="Princeton", season=2026)
        hc_person = upsert_person(
            conn,
            "Bob Surace",
            identity_basis="TEST",
            aliases=[("Coach Surace", "NICKNAME")],
        )
        oc_person = upsert_person(conn, "New Coach", identity_basis="TEST")
        hc_episode = add_episode(
            conn,
            person_id=hc_person,
            program_id="P:PRINCETON",
            season="2026",
            date_precision="SEASON",
            evidence_layer=LAYER_OFFICIAL,
        )
        oc_episode = add_episode(
            conn,
            person_id=oc_person,
            program_id="P:PRINCETON",
            season="2026",
            date_precision="SEASON",
            evidence_layer=LAYER_CANDIDATE,
        )
        add_role(
            conn,
            episode_id=hc_episode,
            role_family="head_coach",
            exact_title_text="Head Coach",
            qualifiers=[],
            evidence_layer=LAYER_OFFICIAL,
            supporting_observations=[obs_official],
        )
        add_role(
            conn,
            episode_id=oc_episode,
            role_family="offensive_coordinator",
            exact_title_text="Offensive Coordinator",
            qualifiers=[],
            evidence_layer=LAYER_CANDIDATE,
            supporting_observations=[obs_candidate],
        )
    conn.commit()
    conn.close()
    return db_path


def _readonly(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


class SchemaDetectionTests(unittest.TestCase):
    def test_cycle35_release_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_release(Path(tmp))
            conn = _readonly(path)
            try:
                self.assertEqual(schema_kind(conn), SCHEMA_KIND_CYCLE35)
            finally:
                conn.close()

    def test_legacy_release_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.sqlite"
            writer = connect_for_import(path)
            load_import(writer, {"role_cells": []})
            writer.close()
            conn = connect_readonly(path)
            try:
                self.assertEqual(schema_kind(conn), SCHEMA_KIND_CYCLE33)
            finally:
                conn.close()

    def test_unrecognized_database_is_reported_not_guessed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.sqlite"
            conn = sqlite3.connect(str(path))
            conn.execute("CREATE TABLE unrelated_table (x INTEGER)")
            conn.commit()
            try:
                self.assertEqual(schema_kind(conn), SCHEMA_KIND_UNKNOWN)
            finally:
                conn.close()


class Cycle35NativeQueryTests(unittest.TestCase):
    def test_team_staff_returns_every_role_for_the_program_season(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_release(Path(tmp))
            conn = _readonly(path)
            try:
                rows = team_staff(conn, team="Princeton", season="2026")
            finally:
                conn.close()
            self.assertEqual(len(rows), 2)
            families = {row["role_family"] for row in rows}
            self.assertEqual(families, {"head_coach", "offensive_coordinator"})

    def test_team_staff_is_exact_not_substring(self) -> None:
        """The MR33-08 lesson applies here too -- a "Princeton" query must
        never also match some other program whose name merely contains it."""
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_release(Path(tmp))
            conn = _readonly(path)
            try:
                rows = team_staff(conn, team="Prince", season="2026")
            finally:
                conn.close()
            self.assertEqual(rows, [])

    def test_team_staff_unknown_program_returns_empty_not_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_release(Path(tmp))
            conn = _readonly(path)
            try:
                rows = team_staff(conn, team="Nonexistent University", season="2026")
            finally:
                conn.close()
            self.assertEqual(rows, [])

    def test_coach_career_resolves_by_canonical_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_release(Path(tmp))
            conn = _readonly(path)
            try:
                rows = coach_career(conn, person="Bob Surace")
            finally:
                conn.close()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["role_family"], "head_coach")

    def test_coach_career_resolves_by_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_release(Path(tmp))
            conn = _readonly(path)
            try:
                rows = coach_career(conn, person="Coach Surace")
            finally:
                conn.close()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["person"], "Bob Surace")

    def test_unresolved_roles_excludes_official_and_corroborated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_release(Path(tmp))
            conn = _readonly(path)
            try:
                unresolved = unresolved_roles(conn)
            finally:
                conn.close()
            self.assertEqual(len(unresolved), 1)
            self.assertEqual(unresolved[0]["role_family"], "offensive_coordinator")

    def test_team_schemes_on_an_unpopulated_table_is_an_honest_empty_list(self) -> None:
        """The real r7 release has zero `scheme_assertion` rows. This must
        return an empty list, not raise, and not fabricate a row."""
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_release(Path(tmp))
            conn = _readonly(path)
            try:
                rows = team_schemes(conn, program="Princeton", season="2026")
            finally:
                conn.close()
            self.assertEqual(rows, [])

    def test_role_state_conservation_partitions_every_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_release(Path(tmp))
            conn = _readonly(path)
            try:
                report = role_state_conservation(conn)
            finally:
                conn.close()
            self.assertEqual(report["table_row_count"], 2)
            self.assertTrue(report["states_partition_table"])
            self.assertTrue(report["no_row_is_unreachable"])
            self.assertEqual(report["state_counts"].get("VERIFIED"), 1)
            self.assertEqual(report["state_counts"].get("UNRESOLVED"), 1)


class InstalledEntrypointDispatchTests(unittest.TestCase):
    """These call the exact functions the installed `bas-staff-query` CLI's
    `main()` calls (`cycle33.query.team_staff` / `coach_career` /
    `unresolved_roles`), reproducing the manager's own probe shape:
    `from aggie_analytics.cycle33.query import team_staff; team_staff(db,
    team=..., season=...)`. Before MF35-06 this raised OperationalError
    against any cycle35 release; it must not anymore, and it must still
    behave exactly as before against a legacy database."""

    def test_cli_dispatch_does_not_raise_against_a_cycle35_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _build_release(Path(tmp))
            conn = _readonly(path)
            try:
                rows = legacy_dispatch_team_staff(conn, team="Princeton", season="2026")
                career = legacy_dispatch_coach_career(conn, person="Bob Surace")
                unresolved = legacy_dispatch_unresolved_roles(conn)
            finally:
                conn.close()
            self.assertEqual(len(rows), 2)
            self.assertEqual(len(career), 1)
            self.assertEqual(len(unresolved), 1)

    def test_legacy_database_dispatch_is_unaffected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.sqlite"
            writer = connect_for_import(path)
            load_import(
                writer,
                {
                    "role_cells": [
                        {
                            "observation_id": "obs1",
                            "team": "Air Force",
                            "season": "2018",
                            "role_column": "head_coach",
                            "person": "Troy Calhoun",
                            "disposition": "CONFIRMED_APPOINTMENT",
                            "verified": True,
                        }
                    ]
                },
            )
            writer.close()
            conn = connect_readonly(path)
            try:
                rows = legacy_dispatch_team_staff(conn, team="Air Force", season="2018")
                career = legacy_dispatch_coach_career(conn, person="Troy Calhoun")
            finally:
                conn.close()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["person"], "Troy Calhoun")
            self.assertEqual(len(career), 1)


if __name__ == "__main__":
    unittest.main()
