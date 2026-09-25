"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-07 regressions for the corrected national release successor.

Each test names an invariant the successor must have. Three of them exist
because this attempt got the thing wrong first and the error was caught by
an independent check rather than by the builder:

* the coverage-state vocabulary must be *imported*, not restated -- an
  earlier version spelled it ``CONFIRMED_CORE_CELL`` and silently relabelled
  every cell;
* a corrected observation must retain its original program, and an
  observation the predecessor left unbound must retain that too;
* the lineage must reach the consumer, because a release that records the
  original program while the installed CLI never returns it is half a repair.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle33 import query as cli  # noqa: E402
from aggie_analytics.cycle36 import release_query  # noqa: E402
from aggie_analytics.cycle36.release_builder import (  # noqa: E402
    CONFIRMED,
    NO_EVIDENCE,
)
from aggie_analytics.cycle37.corrected_release import (  # noqa: E402
    CorrectedReleaseError,
    build_corrected_release,
    verify_predecessor,
)

HEX = "ab" * 32


def build_predecessor(path: Path, source_file: Path) -> None:
    """A minimal national release with the tables the successor needs."""

    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE release_identity (key TEXT, value TEXT);
        CREATE TABLE audit_execution (audit_key TEXT, value TEXT);
        CREATE TABLE canonical_program (program_id TEXT, source_namespace TEXT,
            source_entity_id TEXT, display_names TEXT, in_football_population INTEGER);
        CREATE TABLE program_alias (alias_id TEXT, program_id TEXT, original_alias TEXT,
            normalized_alias TEXT, alias_basis TEXT, effective_state TEXT,
            effective_start TEXT, effective_end TEXT, rename_source_url TEXT,
            source_payload_sha256 TEXT);
        CREATE TABLE alias_collision (collision_id TEXT, normalized_alias TEXT,
            match_basis TEXT, program_ids TEXT, disposition TEXT);
        CREATE TABLE program_season_membership (membership_id TEXT, program_id TEXT,
            season INTEGER, classification TEXT, classification_bucket TEXT,
            conference TEXT, era TEXT, membership_authority TEXT, payload_sha256 TEXT,
            request_identity_sha256 TEXT);
        CREATE TABLE season_population (season INTEGER, programs INTEGER, fbs INTEGER,
            fcs INTEGER, pre_classification INTEGER, other_division INTEGER,
            unknown INTEGER, state TEXT);
        CREATE TABLE staff_observation (observation_id TEXT, capture_path TEXT,
            payload_sha256 TEXT, program_id TEXT, display_name TEXT, person TEXT,
            source_title TEXT, record_selector TEXT, person_body_offset INTEGER,
            person_record_bound INTEGER, role_claim_supported INTEGER,
            reject_reason TEXT, evidence_tier TEXT, season INTEGER,
            season_state TEXT, source_class TEXT, pit_admitted INTEGER);
        CREATE TABLE staff_role_assignment (assignment_id TEXT, observation_id TEXT,
            role_code TEXT, unit TEXT, qualifiers TEXT, occupancy TEXT,
            taxonomy_version TEXT, is_core_role INTEGER, play_caller_inferred INTEGER);
        CREATE TABLE core_role_cell (cell_id TEXT, program_id TEXT, season INTEGER,
            role_code TEXT, coverage_state TEXT, observations INTEGER);
        CREATE TABLE coverage_summary (grain TEXT, bucket TEXT, value TEXT);
        CREATE TABLE scheme_assertion (scheme_assertion_id TEXT, program_id TEXT,
            season INTEGER, side TEXT, source_text TEXT, normalized_families TEXT,
            source_disposition TEXT, state TEXT, evidence_tier TEXT,
            official_corroboration TEXT, page_title TEXT, wikimedia_revision TEXT,
            pit_admitted INTEGER, inferred_from_title INTEGER);
        CREATE TABLE scheme_conflict (conflict_id TEXT, page_title TEXT, season INTEGER,
            side TEXT, conflict_texts TEXT, program_resolution_state TEXT);
        CREATE TABLE responsibility_assertion (responsibility_id TEXT, person TEXT,
            program_id TEXT, season INTEGER, source_title TEXT, evidence_code TEXT,
            disposition TEXT, inferred_from_role_title INTEGER, pit_admitted INTEGER);
        CREATE TABLE user_corpus_cell (user_cell_id TEXT, source_class TEXT,
            season INTEGER, team_as_written TEXT, subdivision_as_written TEXT,
            role_column TEXT, person_as_written TEXT, source_title_as_written TEXT,
            canonical_program_id TEXT, program_resolution_state TEXT,
            evidence_tier TEXT, verified INTEGER, pit_admitted INTEGER);
        CREATE TABLE career_episode (career_episode_id TEXT, span_id TEXT, pageid TEXT,
            page_title TEXT, wikidata_qid TEXT, wikimedia_revision TEXT,
            episode_index INTEGER, person_display_name TEXT, employer_raw TEXT,
            employer_resolution_state TEXT, employer_program_id TEXT,
            source_title TEXT, role_codes TEXT, start_year INTEGER, end_year INTEGER,
            ongoing INTEGER, source_year_text TEXT, evidence_class TEXT, state TEXT,
            flags TEXT, joined INTEGER, pit_admitted INTEGER);
        CREATE TABLE unresolved_program_name (unresolved_id TEXT, raw_name TEXT,
            state TEXT, seasons TEXT, candidate_program_ids TEXT, detail TEXT);
        CREATE TABLE source_file (source_file_id TEXT, path TEXT, sha256 TEXT,
            bytes INTEGER, source_class TEXT, exists_at_build INTEGER);
        """
    )
    conn.execute("INSERT INTO release_identity VALUES ('release_id','PRED')")
    conn.executemany(
        "INSERT INTO canonical_program VALUES (?,?,?,?,?)",
        [("P:OHIO", "SRC", "1", json.dumps(["Ohio"]), 1),
         ("P:OSU", "SRC", "2", json.dumps(["Ohio State"]), 1)],
    )
    conn.executemany(
        "INSERT INTO program_season_membership VALUES (?,?,?,?,?,?,?,?,?,?)",
        [("M1", "P:OHIO", 2026, "FBS", "FBS", "MAC", "MODERN", "A", "d", "r"),
         ("M2", "P:OSU", 2026, "FBS", "FBS", "BIG TEN", "MODERN", "A", "d", "r")],
    )
    conn.execute("INSERT INTO season_population VALUES (2026,2,2,0,0,0,0,'OK')")
    conn.executemany(
        "INSERT INTO staff_observation VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            # Wrongly bound to Ohio; the capture is Ohio State's.
            ("O1", "cap/osu.html", "d-osu", "P:OHIO", "Ohio", "Ryan Day",
             "Head Coach", "s", 1, 1, 1, None, "OFFICIAL_HTML_RECORD_BOUND",
             2026, "SOURCE_STATED", "OFFICIAL", 0),
            # Unresolvable capture; must be kept and flagged, never re-bound.
            ("O2", "cap/uk.html", "d-uk", "P:OHIO", "Ohio", "Somebody",
             "Coach", "s", 1, 1, 1, None, "OFFICIAL_HTML_RECORD_BOUND",
             2026, "SOURCE_STATED", "OFFICIAL", 0),
            # The predecessor left this one unbound entirely.
            ("O3", "cap/none.html", "d-none", None, None, "Unbound Person",
             "Coach", "s", 1, 0, 0, "NO_DECLARED_ATTEMPT",
             "CANDIDATE_FROM_UNBOUND_CAPTURE", None, "UNKNOWN", "OFFICIAL", 0),
        ],
    )
    conn.executemany(
        "INSERT INTO staff_role_assignment VALUES (?,?,?,?,?,?,?,?,?)",
        [("A1", "O1", "head_coach", "TEAM", "principal", "SOLE", "v1", 1, 0),
         ("A2", "O2", "head_coach", "TEAM", "principal", "SOLE", "v1", 1, 0)],
    )
    conn.executemany(
        "INSERT INTO core_role_cell VALUES (?,?,?,?,?,?)",
        [("C1", "P:OHIO", 2026, "head_coach", CONFIRMED, 2),
         ("C2", "P:OSU", 2026, "head_coach", NO_EVIDENCE, 0)],
    )
    conn.execute("INSERT INTO coverage_summary VALUES ('CORE_ROLE_CELL','TOTAL','2')")
    conn.execute(
        "INSERT INTO source_file VALUES (?,?,?,?,?,?)",
        ("F1", str(source_file), hashlib.sha256(source_file.read_bytes()).hexdigest(),
         source_file.stat().st_size, "OFFICIAL", 1),
    )
    conn.commit()
    conn.close()


CROSSWALK: dict[str, Any] = {
    "corrections": [
        {"payload_sha256": "d-osu", "from_program_id": "P:OHIO",
         "to_program_id": "P:OSU", "to_display_name": "Ohio State",
         "reason": "the page's own title names Ohio State"}
    ],
    "quarantined": [
        {"payload_sha256": "d-uk", "state": "UNCORROBORATED_NAME_FORM_NOT_MATCHED",
         "reason": "no declared program is covered by this page's identity"}
    ],
    "rows": [
        {"capture_path": "cap/osu.html", "request_identity": "r1",
         "payload_sha256": "d-osu", "route": "https://ohiostatebuckeyes.com/x",
         "claim_count": 2,
         "claimed_programs": [{"program_id": "P:OHIO"}, {"program_id": "P:OSU"}],
         "previous_binding": {"program_id": "P:OHIO"},
         "admitted_program_id": "P:OSU", "state": "CONFIRMED_BY_SOURCE_IDENTITY",
         "reason": "the page names Ohio State",
         "page_identity": {"title": "Football Coaches - Ohio State",
                           "canonical_href": "/sports/football/coaches",
                           "og_site_name": "Ohio State", "route_host": "ohiostatebuckeyes.com"}},
        {"capture_path": "cap/uk.html", "request_identity": "r2",
         "payload_sha256": "d-uk", "route": "https://ukathletics.com/x",
         "claim_count": 1, "claimed_programs": [{"program_id": "P:OHIO"}],
         "previous_binding": {"program_id": "P:OHIO"}, "admitted_program_id": None,
         "state": "UNCORROBORATED_NAME_FORM_NOT_MATCHED",
         "reason": "no declared program is covered",
         "page_identity": {"title": "Staff Directory - UK Athletics"}},
    ],
}


class Harness(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.source_file = self.base / "declared_input.json"
        self.source_file.write_text('{"declared": true}\n', encoding="utf-8")
        self.predecessor = self.base / "predecessor.sqlite"
        build_predecessor(self.predecessor, self.source_file)
        self.predecessor_sha = hashlib.sha256(self.predecessor.read_bytes()).hexdigest()

    def build(self, destination: str = "successor.sqlite", **kwargs: Any) -> dict[str, Any]:
        options: dict[str, Any] = dict(
            predecessor=self.predecessor,
            crosswalk=CROSSWALK,
            crosswalk_sha256="c" * 64,
            destination=self.base / destination,
            predecessor_sha256=self.predecessor_sha,
        )
        options.update(kwargs)
        return build_corrected_release(**options)

    def conn(self, path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(str(path))
        connection.row_factory = sqlite3.Row
        self.addCleanup(connection.close)
        return connection


class FailsClosed(Harness):
    def test_a_digest_mismatch_refuses_before_writing(self) -> None:
        with self.assertRaises(CorrectedReleaseError) as caught:
            self.build(predecessor_sha256="f" * 64)
        self.assertIn("refusing to build", str(caught.exception))
        self.assertFalse((self.base / "successor.sqlite").exists())

    def test_a_missing_declared_input_refuses(self) -> None:
        self.source_file.unlink()
        with self.assertRaises(CorrectedReleaseError) as caught:
            self.build()
        self.assertIn("failed verification", str(caught.exception))
        self.assertFalse((self.base / "successor.sqlite").exists())

    def test_a_tampered_declared_input_refuses(self) -> None:
        self.source_file.write_text('{"declared": "tampered"}\n', encoding="utf-8")
        with self.assertRaises(CorrectedReleaseError):
            self.build()
        self.assertFalse((self.base / "successor.sqlite").exists())

    def test_an_existing_destination_is_never_overwritten(self) -> None:
        self.build()
        with self.assertRaises(CorrectedReleaseError) as caught:
            self.build()
        self.assertIn("never overwritten", str(caught.exception))

    def test_verification_reports_what_it_checked(self) -> None:
        report = verify_predecessor(self.predecessor, self.predecessor_sha)
        self.assertTrue(report["predecessor_sha256_matches_recorded"])
        self.assertEqual(report["source_files_rehashed"], 1)


class CorrectionSemantics(Harness):
    def setUp(self) -> None:
        super().setUp()
        self.result = self.build()
        self.successor = Path(self.result["database"])
        self.db = self.conn(self.successor)

    def test_the_predecessor_is_not_modified(self) -> None:
        self.assertEqual(
            hashlib.sha256(self.predecessor.read_bytes()).hexdigest(),
            self.predecessor_sha,
        )

    def test_the_corrected_row_moves_and_keeps_its_original(self) -> None:
        row = dict(self.db.execute(
            "SELECT * FROM staff_observation WHERE observation_id='O1'").fetchone())
        self.assertEqual(row["program_id"], "P:OSU")
        self.assertEqual(row["original_program_id"], "P:OHIO")
        self.assertEqual(row["binding_state"], "CORRECTED_BY_SOURCE_IDENTITY")
        self.assertEqual(row["admitted_for_coverage"], 1)

    def test_the_unresolved_row_is_kept_flagged_and_not_rebound(self) -> None:
        row = dict(self.db.execute(
            "SELECT * FROM staff_observation WHERE observation_id='O2'").fetchone())
        self.assertEqual(row["program_id"], "P:OHIO", "a quarantined row is never re-bound")
        self.assertEqual(row["admitted_for_coverage"], 0)
        self.assertIn("NOT_MATCHED", row["binding_state"])

    def test_a_predecessor_null_binding_is_retained_as_null(self) -> None:
        row = dict(self.db.execute(
            "SELECT * FROM staff_observation WHERE observation_id='O3'").fetchone())
        self.assertIsNone(row["program_id"])
        self.assertIsNone(row["original_program_id"])

    def test_no_row_is_created_or_destroyed(self) -> None:
        pred = self.conn(self.predecessor)
        for table in ("staff_observation", "staff_role_assignment",
                      "program_season_membership", "canonical_program"):
            with self.subTest(table=table):
                self.assertEqual(
                    self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0],
                    pred.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0],
                )

    def test_every_change_is_recorded_as_a_row(self) -> None:
        changes = {r["observation_id"]: dict(r) for r in
                   self.db.execute("SELECT * FROM observation_binding_change")}
        self.assertEqual(changes["O1"]["change_kind"], "REBOUND")
        self.assertEqual(changes["O2"]["change_kind"], "FLAGGED_NOT_ADMITTED")

    def test_capture_level_lineage_is_a_table_not_a_file_listing(self) -> None:
        row = dict(self.db.execute(
            "SELECT * FROM source_identity_binding WHERE payload_sha256='d-osu'").fetchone())
        self.assertEqual(row["route"], "https://ohiostatebuckeyes.com/x")
        self.assertEqual(row["previous_program_id"], "P:OHIO")
        self.assertEqual(row["admitted_program_id"], "P:OSU")
        self.assertIn("Ohio State", row["page_title"])

    def test_lineage_names_the_predecessor_it_derived_from(self) -> None:
        lineage = {r["key"]: r["value"] for r in
                   self.db.execute("SELECT key, value FROM release_lineage")}
        self.assertEqual(lineage["predecessor_sha256"], self.predecessor_sha)
        self.assertEqual(lineage["predecessor_modified"], "false")
        self.assertEqual(lineage["activation_state"],
                         "NOT_ACTIVATED_SEPARATE_OWNER_DECISION")


class CoverageVocabulary(Harness):
    """W37R-10: the states must be the predecessor's, not a new spelling."""

    def test_recomputed_cells_use_the_imported_state_names(self) -> None:
        db = self.conn(Path(self.build()["database"]))
        states = {r[0] for r in db.execute(
            "SELECT DISTINCT coverage_state FROM core_role_cell")}
        self.assertTrue(states <= {CONFIRMED, NO_EVIDENCE}, states)
        self.assertNotIn("CONFIRMED_CORE_CELL", states)

    def test_the_corrected_program_gains_and_the_wrong_one_loses(self) -> None:
        db = self.conn(Path(self.build()["database"]))
        cells = {(r["program_id"], r["role_code"]): r["coverage_state"]
                 for r in db.execute("SELECT * FROM core_role_cell")}
        self.assertEqual(cells[("P:OSU", "head_coach")], CONFIRMED)
        # Ohio's only remaining evidence is the quarantined row, which does
        # not count, so the cell it used to confirm loses its confirmation.
        self.assertEqual(cells[("P:OHIO", "head_coach")], NO_EVIDENCE)

    def test_the_predecessor_coverage_is_retained_for_the_diff(self) -> None:
        db = self.conn(Path(self.build()["database"]))
        self.assertEqual(
            db.execute("SELECT value FROM predecessor_coverage_summary "
                       "WHERE grain='CORE_ROLE_CELL' AND bucket='TOTAL'").fetchone()[0],
            "2",
        )


class Determinism(Harness):
    def test_two_builds_of_the_same_inputs_share_a_content_identity(self) -> None:
        first = self.build("a.sqlite")
        second = self.build("b.sqlite")
        self.assertEqual(first["content_identity"], second["content_identity"])

    def test_the_identity_excludes_the_audit_clock(self) -> None:
        first = self.build("c.sqlite", audit={"run": "one"})
        second = self.build("d.sqlite", audit={"run": "two"})
        self.assertEqual(first["content_identity"], second["content_identity"])

    def test_a_changed_correction_changes_the_identity(self) -> None:
        first = self.build("e.sqlite")
        altered = json.loads(json.dumps(CROSSWALK))
        altered["corrections"] = []
        second = self.build("f.sqlite", crosswalk=altered)
        self.assertNotEqual(first["content_identity"], second["content_identity"])


class LineageReachesTheConsumer(Harness):
    """W37R-12: a correction the CLI cannot return is half a repair."""

    def test_team_staff_returns_the_original_and_the_binding_state(self) -> None:
        successor = Path(self.build()["database"])
        db = self.conn(successor)
        payload = release_query.team_staff(db, team="Ohio State", season="2026")
        self.assertTrue(payload["answerable"])
        row = payload["rows"][0]
        self.assertEqual(row["original_program_id"], "P:OHIO")
        self.assertEqual(row["binding_state"], "CORRECTED_BY_SOURCE_IDENTITY")

    def test_provenance_returns_the_lineage_columns(self) -> None:
        successor = Path(self.build("p.sqlite")["database"])
        db = self.conn(successor)
        drill = release_query.provenance(db, observation_id="O1")
        self.assertEqual(
            drill["observation_drill_down"]["observation"]["original_program_id"],
            "P:OHIO",
        )

    def test_the_same_consumer_still_reads_an_uncorrected_release(self) -> None:
        """The columns are optional; the predecessor has none of them."""

        db = self.conn(self.predecessor)
        payload = release_query.team_staff(db, team="Ohio", season="2026")
        self.assertTrue(payload["answerable"])
        self.assertNotIn("binding_state", payload["rows"][0])

    def test_the_installed_entry_point_answers_against_the_successor(self) -> None:
        successor = Path(self.build("q.sqlite")["database"])
        self.assertEqual(
            cli.main(["--database", str(successor), "--team", "Ohio State",
                      "--season", "2026"]),
            0,
        )


def reparsed(capture: str, index: int, person: str, **overrides: Any) -> dict[str, Any]:
    """One R37-03 reparse row in the shape the reparse tool writes."""

    row: dict[str, Any] = {
        "capture_path": capture, "observation_index": index, "payload_sha256": "d-" + capture,
        "program_id": None, "identity_state": "UNCLAIMED_CAPTURE", "delivered_program_id": None,
        "person_raw": person, "person": person, "person_cleaning_removed": [], "source_title": "Head Coach",
        "binding": {"state": "BOUND_TO_OWN_RECORD", "person_record_bound": True, "role_claim_supported": True,
                    "record_selector": "tr[1]", "char_offset": 10, "record_version": "v",
                    "name_span": {"char_start": 12, "byte_start": 12, "byte_end": 20, "verified": True}},
        "evidence_tier": "OFFICIAL_HTML_RECORD_BOUND", "season": 2026, "season_state": "BOUND",
        "source_effective_season": 2026, "announcement_date": None, "season_parser_version": "v37",
        "sport_scope": {"scope": "FOOTBALL", "basis": "PAGE", "football_role_admissible": True},
        "assignments": [{"role": "head_coach", "unit": "TEAM", "occupancy": "PRINCIPAL", "title_qualifiers": [],
                         "segment": None, "segment_qualifiers": [], "qualifier_scope": "TITLE",
                         "taxonomy_correction": None, "taxonomy_version": "v37"}],
        "admitted_for_coverage": True, "diff": {"state": "UNCHANGED", "changes": {}},
    }
    row.update(overrides)
    return row


class StaffReparseSuccessor(Harness):
    """R37-03: the staff tables rebuilt from reparsed rows, aligned to predecessor ids."""

    def rows(self) -> list[dict[str, Any]]:
        return [
            reparsed("cap/osu.html", 0, "Ryan Day", program_id="P:OSU", delivered_program_id="P:OHIO",
                     identity_state="CONFIRMED_BY_SOURCE_IDENTITY",
                     diff={"state": "CHANGED", "changes": {"admitted_program_id": {"cycle36": "P:OHIO",
                                                                                   "cycle37": "P:OSU"}}}),
            reparsed("cap/uk.html", 0, "Somebody", delivered_program_id="P:OHIO", admitted_for_coverage=False,
                     identity_state="UNCORROBORATED_NAME_FORM_NOT_MATCHED",
                     evidence_tier="CANDIDATE_CAPTURE_PROGRAM_NOT_CONFIRMED"),
            reparsed("cap/none.html", 0, "Unbound Person", admitted_for_coverage=False,
                     evidence_tier="CANDIDATE_CAPTURE_PROGRAM_NOT_CONFIRMED"),
            reparsed("cap/new.html", 0, "New Member", admitted_for_coverage=False,
                     identity_state="NEW_CACHE_MEMBER_NOT_IN_CROSSWALK",
                     evidence_tier="CANDIDATE_CAPTURE_PROGRAM_NOT_CONFIRMED"),
        ]

    def test_rows_keep_their_predecessor_ids_and_the_diff_is_queryable(self) -> None:
        result = self.build(staff_rows=self.rows(), staff_rows_sha256="e" * 64)
        db = self.conn(Path(result["database"]))
        ids = {r["person"]: r["observation_id"]
               for r in db.execute("SELECT person, observation_id FROM staff_observation")}
        self.assertEqual(ids["Ryan Day"], "O1")
        self.assertEqual(ids["Unbound Person"], "O3")
        self.assertTrue(str(ids["New Member"]).startswith("R37-03-NEW-"))
        change = db.execute("SELECT field, cycle36_value, cycle37_value FROM staff_reparse_change").fetchone()
        self.assertEqual(tuple(change), ("admitted_program_id", '"P:OHIO"', '"P:OSU"'))
        self.assertIn("v37.2", result["release_version"])
        self.assertIn("staff_reparse_change", result["tables"])

    def test_cells_are_recomputed_from_the_reparsed_rows(self) -> None:
        result = self.build(staff_rows=self.rows(), staff_rows_sha256="e" * 64)
        db = self.conn(Path(result["database"]))
        cells = {(r["program_id"], r["role_code"]): r["coverage_state"]
                 for r in db.execute("SELECT program_id, role_code, coverage_state FROM core_role_cell")}
        self.assertEqual(cells[("P:OSU", "head_coach")], CONFIRMED)
        # The uncorroborated capture keeps its delivered program but is not admitted.
        self.assertNotEqual(cells[("P:OHIO", "head_coach")], CONFIRMED)
        somebody = db.execute("SELECT program_id, admitted_for_coverage FROM staff_observation "
                              "WHERE person='Somebody'").fetchone()
        self.assertEqual(tuple(somebody), ("P:OHIO", 0))

    def test_a_row_that_does_not_match_its_aligned_predecessor_refuses(self) -> None:
        rows = self.rows()
        rows[0]["person_raw"] = "Someone Else"
        with self.assertRaises(CorrectedReleaseError):
            self.build(staff_rows=rows, staff_rows_sha256="e" * 64)

    def test_reparsed_rows_need_their_ledger_digest(self) -> None:
        with self.assertRaises(CorrectedReleaseError):
            self.build(staff_rows=self.rows())


class CellLineage(Harness):
    """R37-07 AC02: every user cell reaches its file, record, column and span."""

    def setUp(self) -> None:
        super().setUp()
        conn = sqlite3.connect(str(self.predecessor))
        conn.execute("INSERT INTO user_corpus_cell VALUES ('1','USER_CORPUS_2000_2012',2000,'Air Force','FBS',"
                     "'Head Coach','Fisher DeBerry','Head Coach','P:OHIO','RESOLVED',"
                     "'USER_COMPILED_RESEARCH_OBSERVATION',0,0)")
        conn.commit()
        conn.close()
        self.predecessor_sha = hashlib.sha256(self.predecessor.read_bytes()).hexdigest()
        self.lineage = [{"user_cell_id": "1", "source_class": "USER_CORPUS_2000_2012", "source_file": "2000.csv",
                         "file_sha256": "f" * 64, "record_ordinal": 0, "csv_lines": [2, 2],
                         "column_header": "Head Coach", "column_index": 2, "spreadsheet_cell": "C2",
                         "cell_text_sha256": "a" * 64, "person_char_span": [0, 14], "segment_text": "Fisher DeBerry"}]
        self.rights = [{"source_class": "OFFICIAL_STAFF_HTML", "register_source_id": "SRC-005",
                        "state": "DECLARED_IN_PROJECT_REGISTER", "terms_or_license": "REVIEW_TERMS"},
                       {"source_class": "USER_CORPUS_2000_2012", "register_source_id": None,
                        "state": "NOT_DECLARED_IN_PROJECT_REGISTER"}]

    def test_each_cell_reaches_its_coordinates(self) -> None:
        result = self.build(user_lineage=self.lineage, source_rights=self.rights, lineage_sha256="9" * 64)
        db = self.conn(Path(result["database"]))
        row = db.execute("SELECT c.person_as_written, l.source_file, l.spreadsheet_cell, l.person_char_start "
                         "FROM user_corpus_cell c JOIN user_corpus_cell_lineage l ON l.user_cell_id = c.user_cell_id"
                         ).fetchone()
        self.assertEqual(tuple(row), ("Fisher DeBerry", "2000.csv", "C2", 0))
        states = dict(db.execute("SELECT source_class, state FROM source_rights").fetchall())
        self.assertEqual(states["USER_CORPUS_2000_2012"], "NOT_DECLARED_IN_PROJECT_REGISTER")
        self.assertIn("user_corpus_cell_lineage", result["tables"])

    def test_lineage_must_cover_the_corpus_one_for_one(self) -> None:
        orphan = [dict(self.lineage[0], user_cell_id="99")]
        with self.assertRaises(CorrectedReleaseError):
            self.build(user_lineage=orphan, source_rights=self.rights, lineage_sha256="9" * 64)
        with self.assertRaises(CorrectedReleaseError):
            self.build(destination="second.sqlite", user_lineage=[], source_rights=self.rights,
                       lineage_sha256="9" * 64)

    def test_lineage_and_rights_come_together(self) -> None:
        with self.assertRaises(CorrectedReleaseError):
            self.build(user_lineage=self.lineage, lineage_sha256="9" * 64)


class SuccessorTables(Harness):
    """R37-05/R37-06 ledgers ride beside the predecessor tables, never over them."""

    def test_a_ledger_becomes_its_own_table_and_the_predecessor_stays(self) -> None:
        rows = [{"episode_id": "E1", "assignments": [{"role": "head_coach"}], "joined": False},
                {"episode_id": "E2", "note": "only here"}]
        result = self.build(successor_tables={"career_episode_successor": (rows, "d" * 64)})
        db = self.conn(Path(result["database"]))
        got = db.execute("SELECT assignments, episode_id, joined, note FROM career_episode_successor "
                         "ORDER BY episode_id").fetchall()
        self.assertEqual([tuple(r) for r in got],
                         [('[{"role": "head_coach"}]', "E1", 0, None), (None, "E2", None, "only here")])
        self.assertEqual(db.execute("SELECT COUNT(*) FROM career_episode").fetchone()[0], 0)
        self.assertIn("career_episode_successor", result["tables"])

    def test_a_bad_name_or_missing_digest_refuses(self) -> None:
        for tables in ({"career_episode": ([], "d" * 64)}, {"x; drop": ([], "d" * 64)},
                       {"career_episode_successor": ([], "not-a-digest")}):
            with self.subTest(tables=list(tables)):
                with self.assertRaises(CorrectedReleaseError):
                    self.build(destination=f"s{abs(hash(str(tables)))}.sqlite", successor_tables=tables)


class QualifiedEvidenceDoesNotConfirm(unittest.TestCase):
    """MF36-14: a qualified title cannot confirm a principal core cell."""

    def cells(self, occupancies: list[str]) -> dict[str, tuple[str, int]]:
        from aggie_analytics.cycle37.corrected_release import _recompute_core_cells

        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.executescript("""
            CREATE TABLE core_role_cell (program_id TEXT, season INTEGER, role_code TEXT,
                                         coverage_state TEXT, observations INTEGER);
            CREATE TABLE program_season_membership (program_id TEXT, season INTEGER);
            CREATE TABLE staff_observation (observation_id TEXT, program_id TEXT, season INTEGER,
                person_record_bound INTEGER, role_claim_supported INTEGER, evidence_tier TEXT,
                admitted_for_coverage INTEGER);
            CREATE TABLE staff_role_assignment (observation_id TEXT, role_code TEXT, occupancy TEXT);
            INSERT INTO program_season_membership VALUES ('p', 2025);
        """)
        for number, occupancy in enumerate(occupancies):
            conn.execute("INSERT INTO staff_observation VALUES (?,?,?,?,?,?,?)",
                         (f"o{number}", "p", 2025, 1, 1, "OFFICIAL_HTML_RECORD_BOUND", 1))
            conn.execute("INSERT INTO staff_role_assignment VALUES (?,?,?)",
                         (f"o{number}", "defensive_coordinator", occupancy))
        _recompute_core_cells(conn)
        return {role: (state, count) for role, state, count in conn.execute(
            "SELECT role_code, coverage_state, observations FROM core_role_cell")}

    def test_qualified_only_evidence_is_a_candidate(self) -> None:
        state, count = self.cells(["QUALIFIED_NOT_PRINCIPAL"])["defensive_coordinator"]
        self.assertNotEqual(state, CONFIRMED)
        self.assertEqual(count, 1)

    def test_principal_evidence_still_confirms(self) -> None:
        self.assertEqual(self.cells(["PRINCIPAL"])["defensive_coordinator"][0], CONFIRMED)

    def test_qualified_beside_principal_changes_nothing(self) -> None:
        self.assertEqual(self.cells(["QUALIFIED_NOT_PRINCIPAL", "PRINCIPAL"])["defensive_coordinator"],
                         (CONFIRMED, 2))

    def test_an_empty_cell_stays_no_evidence(self) -> None:
        self.assertEqual(self.cells([])["head_coach"], (NO_EVIDENCE, 0))


if __name__ == "__main__":
    unittest.main()
