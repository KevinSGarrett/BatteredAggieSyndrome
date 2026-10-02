"""Cycle #37 - Attempt #2 - ACTUAL_STATE

V37-01 regressions for the installed research consumer.

The finding had two halves that fail in opposite directions, and both are
covered here against synthetic databases built to each real schema's shape:

* the Cycle 36 national release was detected as ``UNKNOWN_SCHEMA`` and the
  entry point exited 1 against the database the cycle delivered;
* the published Cycle 35 release answered ``[]`` with exit 0 for a season
  that release does not contain, so an unanswerable query returned an answer.

The fixtures are built here rather than read from the delivered releases so
the suite runs unmounted. A separate lane exercises the real delivered bytes.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle33 import query as cli  # noqa: E402
from aggie_analytics.cycle35 import query as cycle35_query  # noqa: E402
from aggie_analytics.cycle36 import release_query  # noqa: E402


def build_cycle36(path: Path) -> None:
    """A minimal database carrying the national release's marker tables."""

    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE release_identity (key TEXT, value TEXT);
        CREATE TABLE canonical_program (
            program_id TEXT, source_namespace TEXT, source_entity_id TEXT,
            display_names TEXT, in_football_population INTEGER);
        CREATE TABLE program_alias (
            alias_id TEXT, program_id TEXT, original_alias TEXT,
            normalized_alias TEXT, alias_basis TEXT, effective_state TEXT,
            effective_start TEXT, effective_end TEXT, rename_source_url TEXT,
            source_payload_sha256 TEXT);
        CREATE TABLE alias_collision (
            collision_id TEXT, normalized_alias TEXT, match_basis TEXT,
            program_ids TEXT, disposition TEXT);
        CREATE TABLE program_season_membership (
            membership_id TEXT, program_id TEXT, season INTEGER,
            classification TEXT, classification_bucket TEXT, conference TEXT,
            era TEXT, membership_authority TEXT, payload_sha256 TEXT,
            request_identity_sha256 TEXT);
        CREATE TABLE season_population (
            season INTEGER, programs INTEGER, fbs INTEGER, fcs INTEGER,
            pre_classification INTEGER, other_division INTEGER, unknown INTEGER,
            state TEXT);
        CREATE TABLE staff_observation (
            observation_id TEXT, capture_path TEXT, payload_sha256 TEXT,
            program_id TEXT, display_name TEXT, person TEXT, source_title TEXT,
            record_selector TEXT, person_body_offset INTEGER,
            person_record_bound INTEGER, role_claim_supported INTEGER,
            reject_reason TEXT, evidence_tier TEXT, season INTEGER,
            season_state TEXT, source_class TEXT, pit_admitted INTEGER);
        CREATE TABLE staff_role_assignment (
            assignment_id TEXT, observation_id TEXT, role_code TEXT, unit TEXT,
            qualifiers TEXT, occupancy TEXT, taxonomy_version TEXT,
            is_core_role INTEGER, play_caller_inferred INTEGER);
        CREATE TABLE core_role_cell (
            cell_id TEXT, program_id TEXT, season INTEGER, role_code TEXT,
            coverage_state TEXT, observations INTEGER);
        CREATE TABLE coverage_summary (grain TEXT, bucket TEXT, value TEXT);
        CREATE TABLE career_episode (
            career_episode_id TEXT, span_id TEXT, pageid TEXT, page_title TEXT,
            wikidata_qid TEXT, wikimedia_revision TEXT, episode_index INTEGER,
            person_display_name TEXT, employer_raw TEXT,
            employer_resolution_state TEXT, employer_program_id TEXT,
            source_title TEXT, role_codes TEXT, start_year INTEGER,
            end_year INTEGER, ongoing INTEGER, source_year_text TEXT,
            evidence_class TEXT, state TEXT, flags TEXT, joined INTEGER,
            pit_admitted INTEGER);
        CREATE TABLE scheme_assertion (
            scheme_assertion_id TEXT, program_id TEXT, season INTEGER,
            side TEXT, source_text TEXT, normalized_families TEXT,
            source_disposition TEXT, state TEXT, evidence_tier TEXT,
            official_corroboration TEXT, page_title TEXT,
            wikimedia_revision TEXT, pit_admitted INTEGER,
            inferred_from_title INTEGER);
        CREATE TABLE scheme_conflict (
            conflict_id TEXT, page_title TEXT, season INTEGER, side TEXT,
            conflict_texts TEXT, program_resolution_state TEXT);
        CREATE TABLE responsibility_assertion (
            responsibility_id TEXT, person TEXT, program_id TEXT,
            season INTEGER, source_title TEXT, evidence_code TEXT,
            disposition TEXT, inferred_from_role_title INTEGER,
            pit_admitted INTEGER);
        CREATE TABLE unresolved_program_name (
            unresolved_id TEXT, raw_name TEXT, state TEXT, seasons TEXT,
            candidate_program_ids TEXT, detail TEXT);
        CREATE TABLE source_file (
            source_file_id TEXT, path TEXT, sha256 TEXT, bytes INTEGER,
            source_class TEXT, exists_at_build INTEGER);
        CREATE TABLE user_corpus_cell (
            user_cell_id TEXT, source_class TEXT, season INTEGER,
            team_as_written TEXT, subdivision_as_written TEXT,
            role_column TEXT, person_as_written TEXT,
            source_title_as_written TEXT, canonical_program_id TEXT,
            program_resolution_state TEXT, evidence_tier TEXT,
            verified INTEGER, pit_admitted INTEGER);
        CREATE TABLE audit_execution (audit_key TEXT, value TEXT);
        """
    )
    conn.execute("INSERT INTO release_identity VALUES ('release_id', 'TEST_R1')")
    # Cycle 37 Attempt 3 (MF37A02-04): national answers are dispatched by the
    # release's declared version, and a release that declares none is
    # refused. Every delivered national release declares one; this fixture
    # builds the Cycle 36 v36.1 shape (no lineage, no successor tables), so
    # it now says so instead of relying on the refusal-free old behaviour.
    conn.execute(
        "INSERT INTO release_identity VALUES "
        "('release_version', 'BAS-CYCLE36-NATIONAL-RELEASE-v36.1')"
    )
    conn.executemany(
        "INSERT INTO canonical_program VALUES (?,?,?,?,?)",
        [
            ("P:OHIO", "SRC", "1", json.dumps(["Ohio"]), 1),
            ("P:OHIOSTATE", "SRC", "2", json.dumps(["Ohio State"]), 1),
            ("P:TAMU", "SRC", "3", json.dumps(["Texas A&M"]), 1),
            ("P:ETAMU", "SRC", "4", json.dumps(["East Texas A&M"]), 1),
        ],
    )
    conn.executemany(
        "INSERT INTO program_alias VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            ("A1", "P:OHIOSTATE", "OSU", "osu", "SOURCE", "UNKNOWN", None, None, None, None),
        ],
    )
    conn.executemany(
        "INSERT INTO program_season_membership VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            ("M1", "P:OHIO", 1998, "I-A", "FBS", "MAC", "MODERN", "AUTH", "d1", "r1"),
            ("M2", "P:OHIOSTATE", 1998, "I-A", "FBS", "BIG TEN", "MODERN", "AUTH", "d2", "r2"),
            ("M3", "P:TAMU", 2026, "FBS", "FBS", "SEC", "MODERN", "AUTH", "d3", "r3"),
        ],
    )
    conn.executemany(
        "INSERT INTO season_population VALUES (?,?,?,?,?,?,?,?)",
        [(1998, 2, 2, 0, 0, 0, 0, "OK"), (2026, 1, 1, 0, 0, 0, 0, "OK")],
    )
    conn.executemany(
        "INSERT INTO staff_observation VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("O1", "cap/ohiostate.html", "s1", "P:OHIOSTATE", "Ohio State",
             "Ryan Day", "Head Coach", "sel", 10, 1, 1, None, "OFFICIAL", 2026,
             "SOURCE_STATED", "OFFICIAL", 0),
            ("O2", "cap/ohio.html", "s2", "P:OHIO", "Ohio", "Somebody Else",
             "Full Bio", "sel", 20, 0, 0, "NAME_POLLUTION", "CANDIDATE", None,
             "UNKNOWN", "OFFICIAL", 0),
        ],
    )
    conn.executemany(
        "INSERT INTO staff_role_assignment VALUES (?,?,?,?,?,?,?,?,?)",
        [("AS1", "O1", "HC", "TEAM", "principal", "SOLE", "v1", 1, 0)],
    )
    conn.executemany(
        "INSERT INTO core_role_cell VALUES (?,?,?,?,?,?)",
        [
            ("C1", "P:OHIOSTATE", 2026, "HC", "CONFIRMED", 1),
            ("C2", "P:OHIO", 2026, "HC", "NO_EVIDENCE", 0),
        ],
    )
    conn.executemany(
        "INSERT INTO coverage_summary VALUES (?,?,?)",
        [("program_season", "FBS", "2")],
    )
    conn.executemany(
        "INSERT INTO career_episode VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("E1", "S1", "123", "Ryan Day", "Q1", "rev1", 0, "Ryan Day",
             "Ohio State", "RESOLVED", "P:OHIOSTATE", "Head coach", "HC",
             2019, None, 1, "2019-present", "WIKIMEDIA", "ADMITTED", "", 1, 0),
        ],
    )
    conn.executemany(
        "INSERT INTO scheme_assertion VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("SC1", "P:OHIOSTATE", 2026, "OFFENSE", "spread", "SPREAD",
             "SOURCE_STATED", "CANDIDATE", "WIKIMEDIA", None, "Ohio State",
             "rev1", 0, 0),
        ],
    )
    conn.executemany(
        "INSERT INTO responsibility_assertion VALUES (?,?,?,?,?,?,?,?,?)",
        [("R1", "Ryan Day", "P:OHIOSTATE", 2026, "Head Coach", "TITLE",
          "REJECTED_TITLE_IS_NOT_A_PLAYCALL", 1, 0)],
    )
    conn.executemany(
        "INSERT INTO unresolved_program_name VALUES (?,?,?,?,?,?)",
        [("U1", "Miami", "AMBIGUOUS", "[1998]", "[]", "FL vs OH")],
    )
    conn.executemany(
        "INSERT INTO source_file VALUES (?,?,?,?,?,?)",
        [("F1", "cap/ohiostate.html", "s1", 100, "OFFICIAL", 1)],
    )
    conn.commit()
    conn.close()


def build_cycle35(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE canonical_program (
            program_id TEXT, display_name TEXT, classification TEXT,
            first_season TEXT, last_season TEXT);
        CREATE TABLE canonical_person (person_id TEXT, canonical_name TEXT);
        CREATE TABLE person_alias (person_id TEXT, alias TEXT);
        CREATE TABLE employment_episode (
            episode_id TEXT, person_id TEXT, program_id TEXT, season TEXT,
            valid_from TEXT, valid_to TEXT, date_precision TEXT,
            evidence_layer TEXT, pit_admitted INTEGER);
        CREATE TABLE formal_role_assertion (
            assertion_id TEXT, episode_id TEXT, role_family TEXT,
            exact_title_text TEXT, qualifiers TEXT,
            principal_role_blocked INTEGER, evidence_layer TEXT);
        """
    )
    conn.execute("INSERT INTO canonical_program VALUES ('G1','Texas A&M','FBS','1894','CURRENT')")
    conn.execute("INSERT INTO canonical_person VALUES ('PP1','Mike Elko')")
    conn.execute(
        "INSERT INTO employment_episode VALUES "
        "('E1','PP1','G1','CURRENT','2024-01-01',NULL,'DAY',"
        "'OFFICIAL_PRIMARY_CONFIRMED',0)"
    )
    conn.execute(
        "INSERT INTO formal_role_assertion VALUES "
        "('A1','E1','HC','Head Coach','principal',0,'OFFICIAL_PRIMARY_CONFIRMED')"
    )
    conn.commit()
    conn.close()


def build_unknown(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE something_else (x TEXT)")
    conn.commit()
    conn.close()


class SchemaDetection(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.c36 = self.base / "c36.sqlite"
        self.c35 = self.base / "c35.sqlite"
        self.unknown = self.base / "unknown.sqlite"
        build_cycle36(self.c36)
        build_cycle35(self.c35)
        build_unknown(self.unknown)

    def _conn(self, path: Path) -> sqlite3.Connection:
        # Windows will not remove a file with an open handle, so every
        # connection a test opens is closed before the temporary directory
        # is cleaned up. A teardown error would otherwise be reported as a
        # test error and obscure the actual result.
        conn = sqlite3.connect(str(path))
        self.addCleanup(conn.close)
        return conn

    def test_the_national_release_is_no_longer_unknown(self) -> None:
        self.assertEqual(
            cycle35_query.schema_kind(self._conn(self.c36)),
            cycle35_query.SCHEMA_KIND_CYCLE36,
        )

    def test_the_cycle35_release_is_still_detected(self) -> None:
        self.assertEqual(
            cycle35_query.schema_kind(self._conn(self.c35)),
            cycle35_query.SCHEMA_KIND_CYCLE35,
        )

    def test_an_unrelated_database_remains_unknown(self) -> None:
        self.assertEqual(
            cycle35_query.schema_kind(self._conn(self.unknown)),
            cycle35_query.SCHEMA_KIND_UNKNOWN,
        )

    def test_the_report_names_the_tables_it_decided_from(self) -> None:
        report = cycle35_query.schema_report(self._conn(self.c36))
        self.assertIn("core_role_cell", report["tables_present"])
        self.assertTrue(
            all(report["marker_sets"][cycle35_query.SCHEMA_KIND_CYCLE36].values())
        )

    def test_an_unknown_schema_fails_explicitly_not_emptily(self) -> None:
        with self.assertRaises(cli.StaffQueryError) as caught:
            cli.main(["--database", str(self.unknown), "--unresolved"])
        message = str(caught.exception)
        self.assertIn("something_else", message)
        self.assertIn("Refusing to guess", message)


class NationalReleaseQueries(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.database = self.base / "c36.sqlite"
        build_cycle36(self.database)
        self.conn = sqlite3.connect(str(self.database))
        self.addCleanup(self.conn.close)

    def test_exact_program_resolution_does_not_match_a_longer_name(self) -> None:
        resolved = release_query.resolve_program(self.conn, "Ohio")
        self.assertEqual(resolved["resolved"], ["P:OHIO"])
        self.assertFalse(resolved["ambiguous"])

    def test_texas_am_does_not_match_east_texas_am(self) -> None:
        resolved = release_query.resolve_program(self.conn, "Texas A&M")
        self.assertEqual(resolved["resolved"], ["P:TAMU"])

    def test_an_unknown_program_is_reported_as_unknown(self) -> None:
        resolved = release_query.resolve_program(self.conn, "Nowhere State")
        self.assertFalse(resolved["known"])
        self.assertEqual(resolved["resolved"], [])

    def test_an_unmatched_key_is_distinguishable_from_an_empty_answer(self) -> None:
        missing_key = release_query.team_staff(self.conn, team="Nowhere", season="2026")
        self.assertFalse(missing_key["answerable"])
        self.assertEqual(missing_key["row_count"], 0)

        real_key = release_query.team_staff(self.conn, team="Texas A&M", season="2026")
        self.assertTrue(real_key["answerable"])
        self.assertEqual(real_key["row_count"], 0)
        self.assertNotEqual(missing_key["answerable"], real_key["answerable"])

    def test_an_unknown_season_is_reported_as_unknown(self) -> None:
        result = release_query.team_staff(self.conn, team="Ohio State", season="1899")
        self.assertFalse(result["season"]["known"])

    def test_rejected_observations_are_returned_not_filtered(self) -> None:
        unresolved = release_query.unresolved_records(self.conn)
        identities = [
            row["observation_id"]
            for row in unresolved["rejected_or_unsupported_observations"]
        ]
        self.assertIn("O2", identities)

    def test_unresolved_classes_are_kept_separate(self) -> None:
        unresolved = release_query.unresolved_records(self.conn)
        self.assertEqual(unresolved["unresolved_program_name_count"], 1)
        self.assertEqual(unresolved["rejected_or_unsupported_observation_count"], 1)
        self.assertNotIn("unresolved_total", unresolved)

    def test_division_population_filters_by_declared_bucket(self) -> None:
        fbs = release_query.season_division_population(
            self.conn, season="1998", division="FBS"
        )
        self.assertEqual(fbs["row_count"], 2)
        fcs = release_query.season_division_population(
            self.conn, season="1998", division="FCS"
        )
        self.assertEqual(fcs["row_count"], 0)
        self.assertTrue(fcs["answerable"])

    def test_coverage_reports_the_declared_and_live_counts_side_by_side(self) -> None:
        coverage = release_query.coverage(self.conn)
        self.assertIn("declared_coverage_summary", coverage)
        self.assertIn("live_table_recount", coverage)
        self.assertEqual(coverage["live_table_recount"]["staff_observation"], 2)

    def test_provenance_drills_down_to_an_observation(self) -> None:
        drill = release_query.provenance(self.conn, observation_id="O1")
        self.assertTrue(drill["observation_drill_down"]["known"])
        self.assertEqual(
            drill["observation_drill_down"]["observation"]["payload_sha256"], "s1"
        )
        self.assertEqual(len(drill["observation_drill_down"]["role_assignments"]), 1)

    def test_provenance_for_an_absent_observation_says_so(self) -> None:
        drill = release_query.provenance(self.conn, observation_id="NOPE")
        self.assertFalse(drill["observation_drill_down"]["known"])

    def test_scheme_rows_carry_their_candidate_caveat(self) -> None:
        schemes = release_query.schemes(self.conn)
        self.assertEqual(schemes["row_count"], 1)
        self.assertIn("not official confirmation", schemes["caveat"])

    def test_a_rejected_responsibility_is_returned(self) -> None:
        rows = release_query.responsibilities(self.conn)["rows"]
        self.assertEqual(rows[0]["disposition"], "REJECTED_TITLE_IS_NOT_A_PLAYCALL")


class InstalledEntryPoint(unittest.TestCase):
    """The repair has to be reachable from the one installed entry point."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.c36 = self.base / "c36.sqlite"
        self.c35 = self.base / "c35.sqlite"
        build_cycle36(self.c36)
        build_cycle35(self.c35)

    def test_every_documented_national_query_exits_zero(self) -> None:
        invocations = [
            ["--schema"],
            ["--season", "1998", "--division", "FBS"],
            ["--season", "1998", "--division", "FCS"],
            ["--season", "2026"],
            ["--team", "Texas A&M", "--seasons-for-team"],
            ["--team", "Ohio State", "--season", "2026"],
            ["--person", "Ryan Day"],
            ["--unresolved"],
            ["--scheme"],
            ["--responsibility"],
            ["--coverage"],
            ["--provenance"],
            ["--provenance", "O1"],
        ]
        self.assertGreaterEqual(len(invocations), 12)
        for argv in invocations:
            with self.subTest(argv=argv):
                self.assertEqual(cli.main(["--database", str(self.c36), *argv]), 0)

    def test_a_national_flag_is_refused_against_a_cycle35_release(self) -> None:
        with self.assertRaises(cli.StaffQueryError) as caught:
            cli.main(["--database", str(self.c35), "--coverage"])
        self.assertIn("national-release queries", str(caught.exception))

    def _c35_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.c35))
        # `cycle35.query` reads rows by column name, so it depends on the
        # caller having set this row factory -- which `connect_readonly`
        # does. The fixture matches the real consumer rather than papering
        # over the dependency.
        conn.row_factory = sqlite3.Row
        self.addCleanup(conn.close)
        return conn

    def test_a_cycle35_answer_reports_which_keys_the_release_knows(self) -> None:
        payload = cli._legacy_dispatch(
            self._c35_conn(),
            _Namespace(team="Texas A&M", season="2024", person=None, unresolved=False),
        )
        self.assertFalse(payload["answerable"])
        self.assertFalse(payload["key_resolution"]["season"]["known"])
        self.assertTrue(payload["key_resolution"]["team"]["known"])
        self.assertEqual(payload["row_count"], 0)

    def test_a_cycle35_answer_for_a_real_key_is_answerable(self) -> None:
        payload = cli._legacy_dispatch(
            self._c35_conn(),
            _Namespace(team="Texas A&M", season="CURRENT", person=None, unresolved=False),
        )
        self.assertTrue(payload["answerable"])
        self.assertEqual(payload["row_count"], 1)


class _Namespace:
    """A stand-in for the parsed arguments, with the national flags off."""

    def __init__(self, **kwargs: object) -> None:
        defaults = {
            "team": None,
            "season": None,
            "person": None,
            "unresolved": False,
            "division": None,
            "seasons_for_team": False,
            "scheme": False,
            "responsibility": False,
            "coverage": False,
            "provenance": None,
            "schema": False,
        }
        defaults.update(kwargs)
        for key, value in defaults.items():
            setattr(self, key, value)


if __name__ == "__main__":
    unittest.main()
