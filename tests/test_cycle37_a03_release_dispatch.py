"""Cycle #37 — Attempt #3 — IN_PROGRESS_LOCAL_WORK_REMAINS

MF37A02-04 regressions: the installed research consumer must answer career
and responsibility questions from the corrected tables a release declares,
keep the superseded predecessor rows reachable only through an explicit
legacy audit mode, keep older releases readable, page with exact totals and
refuse every malformed release by name.

The manager counterexample was Bill Anderson's predecessor row whose title
is the state qualifier ``TX``: the delivered correction reads the employer
as ``Stamford HS (TX)``, but ``bas-staff-query --person`` returned the
predecessor row. The fixture below reproduces that row pair exactly in
shape; the delivered database itself is exercised by the attempt lanes.
"""

from __future__ import annotations

import contextlib
import io
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
from aggie_analytics.cycle36 import release_query as rq  # noqa: E402

V361 = "BAS-CYCLE36-NATIONAL-RELEASE-v36.1"
V371 = "BAS-CYCLE37-CORRECTED-NATIONAL-RELEASE-v37.1"
V372 = "BAS-CYCLE37-CORRECTED-NATIONAL-RELEASE-v37.2-STAFF-REPARSE"
BILL = "Bill Anderson (American football, born 1925)"

BASE_SCHEMA = """
CREATE TABLE release_identity (key TEXT, value TEXT);
CREATE TABLE canonical_program (program_id TEXT, source_namespace TEXT, source_entity_id TEXT,
    display_names TEXT, in_football_population INTEGER);
CREATE TABLE program_alias (alias_id TEXT, program_id TEXT, original_alias TEXT,
    normalized_alias TEXT, alias_basis TEXT, effective_state TEXT, effective_start TEXT,
    effective_end TEXT, rename_source_url TEXT, source_payload_sha256 TEXT);
CREATE TABLE alias_collision (collision_id TEXT, normalized_alias TEXT, match_basis TEXT,
    program_ids TEXT, disposition TEXT);
CREATE TABLE program_season_membership (membership_id TEXT, program_id TEXT, season INTEGER,
    classification TEXT, classification_bucket TEXT, conference TEXT, era TEXT,
    membership_authority TEXT, payload_sha256 TEXT, request_identity_sha256 TEXT);
CREATE TABLE season_population (season INTEGER, programs INTEGER, fbs INTEGER, fcs INTEGER,
    pre_classification INTEGER, other_division INTEGER, unknown INTEGER, state TEXT);
CREATE TABLE staff_observation (observation_id TEXT, capture_path TEXT, payload_sha256 TEXT,
    program_id TEXT, display_name TEXT, person TEXT, source_title TEXT, record_selector TEXT,
    person_body_offset INTEGER, person_record_bound INTEGER, role_claim_supported INTEGER,
    reject_reason TEXT, evidence_tier TEXT, season INTEGER, season_state TEXT,
    source_class TEXT, pit_admitted INTEGER);
CREATE TABLE staff_role_assignment (assignment_id TEXT, observation_id TEXT, role_code TEXT,
    unit TEXT, qualifiers TEXT, occupancy TEXT, taxonomy_version TEXT, is_core_role INTEGER,
    play_caller_inferred INTEGER);
CREATE TABLE core_role_cell (cell_id TEXT, program_id TEXT, season INTEGER, role_code TEXT,
    coverage_state TEXT, observations INTEGER);
CREATE TABLE coverage_summary (grain TEXT, bucket TEXT, value TEXT);
CREATE TABLE career_episode (career_episode_id INTEGER, span_id TEXT, pageid TEXT,
    page_title TEXT, wikidata_qid TEXT, wikimedia_revision TEXT, episode_index INTEGER,
    person_display_name TEXT, employer_raw TEXT, employer_resolution_state TEXT,
    employer_program_id TEXT, source_title TEXT, role_codes TEXT, start_year INTEGER,
    end_year INTEGER, ongoing INTEGER, source_year_text TEXT, evidence_class TEXT,
    state TEXT, flags TEXT, joined INTEGER, pit_admitted INTEGER);
CREATE TABLE scheme_assertion (scheme_assertion_id TEXT, program_id TEXT, season INTEGER,
    side TEXT, source_text TEXT, normalized_families TEXT, source_disposition TEXT,
    state TEXT, evidence_tier TEXT, official_corroboration TEXT, page_title TEXT,
    wikimedia_revision TEXT, pit_admitted INTEGER, inferred_from_title INTEGER);
CREATE TABLE scheme_conflict (conflict_id TEXT, page_title TEXT, season INTEGER, side TEXT,
    conflict_texts TEXT, program_resolution_state TEXT);
CREATE TABLE responsibility_assertion (responsibility_id INTEGER, person TEXT,
    program_id TEXT, season INTEGER, source_title TEXT, evidence_code TEXT,
    disposition TEXT, inferred_from_role_title INTEGER, pit_admitted INTEGER);
CREATE TABLE unresolved_program_name (unresolved_id TEXT, raw_name TEXT, state TEXT,
    seasons TEXT, candidate_program_ids TEXT, detail TEXT);
CREATE TABLE source_file (source_file_id TEXT, path TEXT, sha256 TEXT, bytes INTEGER,
    source_class TEXT, exists_at_build INTEGER);
CREATE TABLE user_corpus_cell (user_cell_id TEXT, source_class TEXT, season INTEGER,
    team_as_written TEXT, subdivision_as_written TEXT, role_column TEXT,
    person_as_written TEXT, source_title_as_written TEXT, canonical_program_id TEXT,
    program_resolution_state TEXT, evidence_tier TEXT, verified INTEGER, pit_admitted INTEGER);
"""

SUCCESSOR_SCHEMA = """
CREATE TABLE release_lineage (key TEXT, value TEXT);
CREATE TABLE career_episode_successor (assignments TEXT, classification TEXT,
    employer_display TEXT, employer_kind TEXT, employer_link_basis TEXT,
    employer_link_target TEXT, employer_qualifiers TEXT, "end" INTEGER, episode_id TEXT,
    evidence_class TEXT, family TEXT, homonym_display_name INTEGER, interval_index INTEGER,
    "join" TEXT, ongoing INTEGER, page_title TEXT, pageid INTEGER, parser_version TEXT,
    person_display TEXT, pit_admitted INTEGER, population_state TEXT, raw_file TEXT,
    raw_file_sha256 TEXT, resolution TEXT, revision TEXT, role_basis TEXT, role_text TEXT,
    row_index INTEGER, start INTEGER, team_byte_span TEXT, team_char_span TEXT,
    team_raw TEXT, wikidata_qid TEXT, wikitext_sha256 TEXT, years_as_written TEXT,
    years_char_span TEXT, years_raw TEXT);
CREATE TABLE career_predecessor_disposition (changes TEXT, pageid INTEGER,
    predecessor_span_id TEXT, reparse_episode_ids TEXT, row_index INTEGER, state TEXT);
CREATE TABLE responsibility_successor (capture_path TEXT, disposition TEXT,
    duplicate_of_title_statement TEXT, evidence_code TEXT, known_at TEXT, matched_text TEXT,
    observation_id TEXT, observation_join TEXT, offset_in_plain_text INTEGER,
    offset_in_rendered_text INTEGER, page_kind TEXT, page_title TEXT, payload_sha256 TEXT,
    person TEXT, person_attributed TEXT, predecessor_disposition TEXT,
    predecessor_evidence_code TEXT, predecessor_row_index INTEGER, predecessor_version TEXT,
    program_as_written TEXT, program_binding_state TEXT, program_id TEXT,
    program_resolution TEXT, quoted_span TEXT, reasons TEXT,
    release_responsibility_id INTEGER, responsibility_version TEXT, revision_id INTEGER,
    revision_timestamp TEXT, season INTEGER, sentence TEXT, source_kind TEXT,
    source_title TEXT, subject TEXT, subject_basis TEXT, successor_key TEXT,
    wiki_file TEXT, years_as_written TEXT);
"""

PROGRAMS = [
    ("P:TAMU", "SRC", "1", json.dumps(["Texas A&M"]), 1),
    ("P:OHIOSTATE", "SRC", "2", json.dumps(["Ohio State"]), 1),
    ("P:OHIO", "SRC", "3", json.dumps(["Ohio"]), 1),
    ("P:LEHIGH", "SRC", "4", json.dumps(["Lehigh"]), 1),
]

#: Predecessor career rows. Row 1 is the manager's counterexample shape: the
#: state qualifier ``TX`` parsed as a title and the employer truncated.
PREDECESSOR_CAREER = [
    (1, "w:100:career:1", "100", BILL, "Q1", "r100", 0, BILL, "Stamford HS",
     "UNRESOLVED_NO_DECLARED_NAME_MATCHES_THIS_QUERY", None, "TX", "[]", 1967, 1968, 0,
     "1967-1968", "RETROSPECTIVE_CANDIDATE_ONLY", "REFUSED_EMPLOYER_RESOLVES_TO_NO_DECLARED_PROGRAM",
     '["SOURCE_PARSE_ARTIFACT_TITLE_LOOKS_LIKE_AN_EMPLOYER_QUALIFIER"]', 0, 0),
    (2, "w:100:career:2", "100", BILL, "Q1", "r100", 1, BILL, "Abilene Christian",
     "RESOLVED_SINGLE_CANONICAL_PROGRAM", None, "assistant", '["assistant_unspecified"]',
     1969, 1970, 0, "1969-1970", "RETROSPECTIVE_CANDIDATE_ONLY", "REFUSED", "[]", 0, 0),
    (3, "w:100:career:3", "100", BILL, "Q1", "r100", 2, BILL, "Phantom", "UNRESOLVED",
     None, "HC", '["head_coach"]', 1990, 1991, 0, "1990-1991", "RETROSPECTIVE_CANDIDATE_ONLY",
     "REFUSED", "[]", 0, 0),
    (4, "w:200:career:1", "200", "Mike Elko", "Q2", "r200", 0, "Mike Elko", "Texas A&M",
     "RESOLVED_SINGLE_CANONICAL_PROGRAM", "P:TAMU", "HC", '["head_coach"]', 2024, None, 1,
     "2024-present", "RETROSPECTIVE_CANDIDATE_ONLY", "ADMITTED", "[]", 0, 0),
    (5, "w:200:career:2", "200", "Mike Elko", "Q2", "r200", 1, "Mike Elko", "Ohio State",
     "RESOLVED_SINGLE_CANONICAL_PROGRAM", "P:OHIOSTATE", "DC", '["defensive_coordinator"]',
     2010, 2012, 0, "2010-2012", "RETROSPECTIVE_CANDIDATE_ONLY", "ADMITTED", "[]", 0, 0),
    (6, "w:300:career:1", "300", "Bill Anderson (coach)", "Q3", "r300", 0,
     "Bill Anderson (coach)", "Lehigh", "RESOLVED_SINGLE_CANONICAL_PROGRAM", "P:LEHIGH",
     "OC", '["offensive_coordinator"]', 1985, 1990, 0, "1985-1990",
     "RETROSPECTIVE_CANDIDATE_ONLY", "ADMITTED", "[]", 0, 0),
]

PREDECESSOR_CAREER_COLUMNS = {
    "career_episode_id", "span_id", "pageid", "page_title", "wikidata_qid",
    "wikimedia_revision", "episode_index", "person_display_name", "employer_raw",
    "employer_resolution_state", "employer_program_id", "source_title", "role_codes",
    "start_year", "end_year", "ongoing", "source_year_text", "evidence_class", "state",
    "flags", "joined", "pit_admitted",
}


def successor(episode: str, pageid: int, title: str, display: str, family: str, row: int,
              employer: str, roles: list[str], start: int | None, end: int | None,
              ongoing: int, program: str | None, by_season: dict[str, str],
              interval: int = 0) -> dict[str, Any]:
    divisions = sorted(set(by_season.values()))
    return {
        "assignments": json.dumps([{"role": role} for role in roles]),
        "classification": json.dumps({"by_season": by_season, "divisions": divisions})
        if by_season else "{}",
        "employer_display": employer, "employer_kind": "COLLEGE_OR_OTHER_FOOTBALL_PROGRAM",
        "employer_link_basis": "LINKED_ON_THIS_ROW", "employer_link_target": employer,
        "employer_qualifiers": "[]", "end": end, "episode_id": episode,
        "evidence_class": "RETROSPECTIVE_SECONDARY_WIKIMEDIA_REVISION", "family": family,
        "homonym_display_name": 0, "interval_index": interval,
        "join": json.dumps({"state": "NOT_ATTEMPTED"}), "ongoing": ongoing,
        "page_title": title, "pageid": pageid, "parser_version": "BAS-CAREER-INFOBOX-v37.2",
        "person_display": display, "pit_admitted": 0,
        "population_state": "IN_POPULATION_CANDIDATE_EPISODE",
        "raw_file": f"raw/{pageid}.json", "raw_file_sha256": "f" * 64,
        "resolution": json.dumps({"candidates": [], "program_id": program,
                                  "state": "RESOLVED" if program else "UNRESOLVED"}),
        "revision": f"r{pageid}", "role_basis": "EXPLICIT", "role_text": None,
        "row_index": row, "start": start, "team_byte_span": "[10, 20]",
        "team_char_span": "[10, 20]", "team_raw": employer, "wikidata_qid": f"Q{pageid}",
        "wikitext_sha256": "e" * 64, "years_as_written": None if start is None else f"{start}-{end}",
        "years_char_span": None if start is None else "[1, 9]",
        "years_raw": None if start is None else f"{start}-{end}",
    }


SUCCESSOR_CAREER = [
    successor("R:100:COACHING:1:0", 100, BILL, "Bill Anderson", "COACHING", 1,
              "Stamford HS (TX)", ["head_coach"], 1967, 1968, 0, None, {}),
    successor("R:100:COACHING:2:0", 100, BILL, "Bill Anderson", "COACHING", 2,
              "Abilene Christian", ["assistant_unspecified"], 1969, 1970, 0, None,
              {"1969": "ii/iii", "1970": "ii/iii"}),
    successor("R:100:PLAYING:1:0", 100, BILL, "Bill Anderson", "PLAYING", 1,
              "Pepperdine", ["player"], 1947, 1949, 0, None, {}),
    successor("R:200:COACHING:1:0", 200, "Mike Elko", "Mike Elko", "COACHING", 1,
              "Texas A&M", ["head_coach"], 2024, None, 1, "P:TAMU",
              {"2024": "fbs", "2025": "fbs", "2026": "fbs"}),
    successor("R:200:COACHING:2:0", 200, "Mike Elko", "Mike Elko", "COACHING", 2,
              "Ohio State", ["defensive_coordinator"], 2010, 2012, 0, "P:OHIOSTATE",
              {"2010": "fbs", "2011": "fbs", "2012": "fbs"}),
    successor("R:300:COACHING:1:0", 300, "Bill Anderson (coach)", "Bill Anderson",
              "COACHING", 1, "Lehigh", ["offensive_coordinator"], 1985, 1990, 0, "P:LEHIGH",
              {str(season): "fcs" for season in range(1985, 1991)}),
    successor("R:300:COACHING:2:0", 300, "Bill Anderson (coach)", "Bill Anderson",
              "COACHING", 2, "Unknown College", ["head_coach"], None, None, 0, None, {}),
]

DISPOSITIONS = [
    (json.dumps({"employer": {"predecessor": "Stamford HS", "reparse": "Stamford HS (TX)"}}),
     100, "w:100:career:1", json.dumps(["R:100:COACHING:1:0"]), 1, "CORRECTED"),
    ("{}", 100, "w:100:career:2", json.dumps(["R:100:COACHING:2:0"]), 2, "RETAINED"),
    ("{}", 100, "w:100:career:3", "[]", 3, "REJECTED_NO_SUCH_ROW_IN_THE_REVISION"),
    ("{}", 200, "w:200:career:1", json.dumps(["R:200:COACHING:1:0"]), 1, "RETAINED"),
    ("{}", 200, "w:200:career:2", json.dumps(["R:200:COACHING:2:0"]), 2, "RETAINED"),
    ("{}", 300, "w:300:career:1", json.dumps(["R:300:COACHING:1:0"]), 1, "RETAINED"),
]

PREDECESSOR_RESPONSIBILITY = [
    (1, "Mike Elko", "P:TAMU", 2026, "Head Coach", "HEAD_COACH_TITLE_IS_NOT_PLAY_CALLING",
     "REJECTED_TITLE_IS_NOT_A_RESPONSIBILITY_STATEMENT", 1, 0),
    (2, "Coach Two", "P:OHIO", 2026, "Offensive Coordinator",
     "COORDINATOR_TITLE_IS_NOT_PLAY_CALLING",
     "REJECTED_TITLE_IS_NOT_A_RESPONSIBILITY_STATEMENT", 1, 0),
]


def responsibility(key: str, **values: Any) -> dict[str, Any]:
    row = {name: None for name in (
        "capture_path", "disposition", "duplicate_of_title_statement", "evidence_code",
        "known_at", "matched_text", "observation_id", "observation_join",
        "offset_in_plain_text", "offset_in_rendered_text", "page_kind", "page_title",
        "payload_sha256", "person", "person_attributed", "predecessor_disposition",
        "predecessor_evidence_code", "predecessor_row_index", "predecessor_version",
        "program_as_written", "program_binding_state", "program_id", "program_resolution",
        "quoted_span", "reasons", "release_responsibility_id", "responsibility_version",
        "revision_id", "revision_timestamp", "season", "sentence", "source_kind",
        "source_title", "subject", "subject_basis", "successor_key", "wiki_file",
        "years_as_written")}
    row.update(successor_key=key, responsibility_version="BAS-RESPONSIBILITY-CONTEXT-v37.2")
    row.update(values)
    return row


SUCCESSOR_RESPONSIBILITY = [
    responsibility("k1", source_kind="PREDECESSOR_ROW", release_responsibility_id=1,
                   predecessor_row_index=1, predecessor_version="v36.1",
                   predecessor_disposition="REJECTED_TITLE_IS_NOT_A_RESPONSIBILITY_STATEMENT",
                   predecessor_evidence_code="HEAD_COACH_TITLE_IS_NOT_PLAY_CALLING",
                   person="Mike Elko", program_id="P:TAMU", season=2026, source_title="Head Coach",
                   evidence_code="HEAD_COACH_TITLE_IS_NOT_PLAY_CALLING",
                   disposition="REJECTED_TITLE_IS_NOT_A_RESPONSIBILITY_STATEMENT",
                   capture_path="cap/tamu.html", observation_id="O1"),
    responsibility("k2", source_kind="PREDECESSOR_ROW", release_responsibility_id=2,
                   predecessor_row_index=2, predecessor_version="v36.1",
                   predecessor_disposition="REJECTED_TITLE_IS_NOT_A_RESPONSIBILITY_STATEMENT",
                   predecessor_evidence_code="COORDINATOR_TITLE_IS_NOT_PLAY_CALLING",
                   person="Coach Two", program_id="P:OHIOSTATE", season=2026,
                   source_title="Offensive Coordinator",
                   evidence_code="COORDINATOR_TITLE_IS_NOT_PLAY_CALLING",
                   disposition="REJECTED_TITLE_IS_NOT_A_RESPONSIBILITY_STATEMENT",
                   capture_path="cap/osu.html"),
    responsibility("k3", source_kind="ENCYCLOPEDIA_REVISION",
                   disposition="CANDIDATE_HISTORICAL_EXPLICIT_STATEMENT", page_title="Some Coach",
                   wiki_file="abc.json", revision_id=5, offset_in_plain_text=10,
                   sentence="He called plays."),
]

LINEAGE = {
    "successor_table::career_episode_successor::ledger_sha256": "a" * 64,
    "successor_table::career_predecessor_disposition::ledger_sha256": "b" * 64,
    "successor_table::responsibility_successor::ledger_sha256": "c" * 64,
    "predecessor_sha256": "d" * 64,
    "predecessor_modified": "false",
    "activation_state": "NOT_ACTIVATED_SEPARATE_OWNER_DECISION",
}


def _insert(conn: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        names = ", ".join(f'"{name}"' for name in row)
        marks = ", ".join("?" for _ in row)
        conn.execute(f'INSERT INTO "{table}" ({names}) VALUES ({marks})', tuple(row.values()))


def build(path: Path, **options: Any) -> Path:
    if path.exists():
        raise FileExistsError(path)
    conn = sqlite3.connect(str(path))
    try:
        _build(conn, **options)
    finally:
        conn.close()
    return path


def _build(conn: sqlite3.Connection, *, version: str | None = V372, successors: bool = True,
           lineage: dict[str, str] | None = None, lineage_table: bool | None = None) -> None:
    conn.executescript(BASE_SCHEMA)
    if version is not None:
        conn.execute("INSERT INTO release_identity VALUES ('release_version', ?)", (version,))
    conn.executemany("INSERT INTO canonical_program VALUES (?,?,?,?,?)", PROGRAMS)
    conn.executemany("INSERT INTO season_population VALUES (?,?,?,?,?,?,?,?)",
                     [(2026, 1, 1, 0, 0, 0, 0, "OK")])
    conn.execute("INSERT INTO staff_observation VALUES ('O1','cap/tamu.html','s1','P:TAMU',"
                 "'Texas A&M','Mike Elko','Head Coach','tr[1]',1,1,1,NULL,'OFFICIAL',2026,"
                 "'SOURCE_STATED','OFFICIAL',0)")
    conn.executemany(f"INSERT INTO career_episode VALUES ({','.join('?' * 22)})",
                     PREDECESSOR_CAREER)
    conn.executemany(f"INSERT INTO responsibility_assertion VALUES ({','.join('?' * 9)})",
                     PREDECESSOR_RESPONSIBILITY)
    conn.executemany("INSERT INTO scheme_assertion VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     [(f"SC{index}", "P:TAMU", 2026, "OFFENSE", "spread", "SPREAD", "SOURCE_STATED",
                       "CANDIDATE", "WIKIMEDIA", None, "Texas A&M", "r", 0, 0)
                      for index in range(5)])
    if lineage_table is None:
        lineage_table = successors
    if lineage_table:
        conn.executescript(SUCCESSOR_SCHEMA if successors else
                           "CREATE TABLE release_lineage (key TEXT, value TEXT);")
        values = dict(LINEAGE if successors else {}) if lineage is None else dict(lineage)
        values.setdefault("successor_release_version", version or "")
        conn.executemany("INSERT INTO release_lineage VALUES (?, ?)", sorted(values.items()))
    if successors:
        _insert(conn, "career_episode_successor", SUCCESSOR_CAREER)
        conn.executemany("INSERT INTO career_predecessor_disposition VALUES (?,?,?,?,?,?)",
                         DISPOSITIONS)
        _insert(conn, "responsibility_successor", SUCCESSOR_RESPONSIBILITY)
    conn.commit()


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self._built = 0

    def db(self, name: str | None = None, **options: Any) -> Path:
        # Every call builds a fresh file: a test that builds twice must not
        # append a second copy of every table to its first database.
        self._built += 1
        stem = Path(name).stem if name else "r"
        return build(self.base / f"{stem}-{self._built}.sqlite", **options)

    def conn(self, path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(str(path))
        self.addCleanup(conn.close)
        return conn

    def cli(self, path: Path, *argv: str) -> dict[str, Any]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = cli.main(["--database", str(path), *argv])
        self.assertEqual(code, 0)
        return json.loads(buffer.getvalue())

    def refused(self, path: Path, *argv: str) -> str:
        with self.assertRaises(cli.StaffQueryError) as caught:
            with contextlib.redirect_stdout(io.StringIO()):
                cli.main(["--database", str(path), *argv])
        return str(caught.exception)


class TheManagerCounterexample(Base):
    """``--person`` must not expose the predecessor ``TX`` title any more."""

    def test_the_installed_person_query_returns_the_corrected_rows(self) -> None:
        payload = self.cli(self.db(), "--person", BILL)
        self.assertEqual(payload["release_dispatch"]["mode"], rq.MODE_CORRECTED_SUCCESSOR)
        self.assertEqual(payload["release_dispatch"]["selected_table"], "career_episode_successor")
        rows = payload["career_episodes"]
        self.assertTrue(rows)
        self.assertTrue(all("episode_id" in row for row in rows))
        self.assertFalse(any(row.get("source_title") == "TX" for row in rows))
        self.assertFalse(any(row.get("employer_raw") == "Stamford HS" for row in rows))
        stamford = [row for row in rows if row["employer_display"] == "Stamford HS (TX)"]
        self.assertEqual(len(stamford), 1)
        self.assertEqual(stamford[0]["corrected"]["roles"], ["head_coach"])
        self.assertEqual(stamford[0]["corrected"]["interval"]["start"], 1967)
        self.assertEqual(stamford[0]["predecessor_dispositions"][0]["state"], "CORRECTED")
        self.assertEqual(
            stamford[0]["predecessor_dispositions"][0]["changes"]["employer"]["predecessor"],
            "Stamford HS",
        )

    def test_the_library_default_is_the_correction_too(self) -> None:
        conn = self.conn(self.db())
        career = rq.coach_career(conn, person=BILL)
        self.assertEqual(career["release_dispatch"]["mode"], rq.MODE_CORRECTED_SUCCESSOR)
        self.assertFalse(any("span_id" in row for row in career["career_episodes"]))
        listing = rq.career_listing(conn)
        self.assertEqual(listing["release_dispatch"]["selected_table"], "career_episode_successor")
        resp = rq.responsibilities(conn)
        self.assertEqual(resp["release_dispatch"]["selected_table"], "responsibility_successor")

    def test_the_rejected_predecessor_row_is_reported_not_dropped(self) -> None:
        payload = self.cli(self.db(), "--person", BILL)
        orphans = payload["predecessor_rows_without_successor"]
        self.assertEqual([row["predecessor_span_id"] for row in orphans], ["w:100:career:3"])
        self.assertEqual(orphans[0]["state"], "REJECTED_NO_SUCH_ROW_IN_THE_REVISION")

    def test_a_new_successor_row_says_it_has_no_predecessor(self) -> None:
        rows = self.cli(self.db(), "--person", BILL)["career_episodes"]
        playing = [row for row in rows if row["family"] == "PLAYING"]
        self.assertEqual(playing[0]["lineage_state"], "NEW_IN_SUCCESSOR_NO_PREDECESSOR_ROW")
        self.assertEqual(playing[0]["predecessor_dispositions"], [])

    def test_every_corrected_row_carries_its_source_locator(self) -> None:
        for row in self.cli(self.db(), "--career", "--all")["rows"]:
            with self.subTest(episode=row["episode_id"]):
                locator = row["locator"]
                self.assertEqual(locator["raw_file"], row["raw_file"])
                self.assertEqual(locator["raw_file_sha256"], row["raw_file_sha256"])
                self.assertEqual(locator["wikitext_sha256"], row["wikitext_sha256"])
                self.assertEqual(locator["team_char_span"], json.loads(row["team_char_span"]))


class PersonIdentity(Base):
    def test_a_shared_display_name_lists_each_identity(self) -> None:
        payload = self.cli(self.db(), "--person", "Bill Anderson")
        self.assertEqual(payload["career_identity_count"], 2)
        self.assertTrue(payload["career_identity_ambiguous"])
        self.assertEqual({row["pageid"] for row in payload["career_episodes"]}, {100, 300})

    def test_pageid_selects_one_identity(self) -> None:
        payload = self.cli(self.db(), "--person", "Bill Anderson", "--pageid", "300")
        self.assertEqual({row["pageid"] for row in payload["career_episodes"]}, {300})
        self.assertFalse(payload["career_identity_ambiguous"])

    def test_page_title_matches_exactly(self) -> None:
        payload = self.cli(self.db(), "--person", BILL)
        self.assertEqual(payload["career_identity_count"], 1)
        self.assertEqual(payload["career_identities"][0]["matched_on_page_title"], 1)


class LegacyAudit(Base):
    def test_legacy_audit_returns_superseded_rows_with_their_disposition(self) -> None:
        payload = self.cli(self.db(), "--person", BILL, "--legacy-audit")
        self.assertEqual(payload["release_dispatch"]["mode"], rq.MODE_LEGACY_PREDECESSOR_AUDIT)
        rows = payload["career_episodes"]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["row_status"] == "SUPERSEDED_PREDECESSOR_ROW" for row in rows))
        tx = [row for row in rows if row["source_title"] == "TX"][0]
        self.assertEqual(tx["successor_disposition"][0]["state"], "CORRECTED")
        self.assertEqual(tx["successor_disposition"][0]["successor_episode_ids"],
                         ["R:100:COACHING:1:0"])

    def test_legacy_responsibility_rows_name_their_successors(self) -> None:
        payload = self.cli(self.db(), "--responsibility", "--legacy-audit")
        self.assertEqual(payload["release_dispatch"]["selected_table"], "responsibility_assertion")
        rows = {row["responsibility_id"]: row for row in payload["rows"]}
        self.assertEqual(rows[2]["successor_rows"][0]["program_id"], "P:OHIOSTATE")
        self.assertEqual(rows[2]["program_id"], "P:OHIO")

    def test_legacy_audit_is_refused_where_it_does_not_apply(self) -> None:
        message = self.refused(self.db(), "--team", "Texas A&M", "--season", "2026",
                               "--legacy-audit")
        self.assertIn("--legacy-audit", message)
        self.assertIn("--legacy-audit", self.refused(self.db("b.sqlite"), "--coverage",
                                                     "--legacy-audit"))


class Responsibilities(Base):
    def test_corrected_rows_show_old_to_new_changes(self) -> None:
        payload = self.cli(self.db(), "--responsibility", "--all")
        self.assertEqual(payload["release_dispatch"]["mode"], rq.MODE_CORRECTED_SUCCESSOR)
        rows = {row["successor_key"]: row for row in payload["rows"]}
        self.assertEqual(set(rows), {"k1", "k2", "k3"})
        self.assertEqual(rows["k2"]["predecessor"]["changed_fields"], ["program_id"])
        self.assertEqual(rows["k2"]["predecessor"]["program_id"], "P:OHIO")
        self.assertEqual(rows["k1"]["predecessor"]["changed_fields"], [])
        self.assertEqual(rows["k3"]["lineage_state"], "NEW_IN_SUCCESSOR_NO_PREDECESSOR_ROW")
        self.assertEqual(rows["k3"]["locator"]["wiki_file"], "abc.json")
        self.assertEqual(rows["k1"]["locator"]["observation_payload_sha256"], "s1")
        self.assertEqual(payload["pagination"]["total_count"], 3)

    def test_filters_are_exact(self) -> None:
        payload = self.cli(self.db(), "--responsibility", "--team", "Ohio State")
        self.assertEqual([row["successor_key"] for row in payload["rows"]], ["k2"])
        payload = self.cli(self.db("b.sqlite"), "--responsibility", "--source-kind",
                           "ENCYCLOPEDIA_REVISION")
        self.assertEqual([row["successor_key"] for row in payload["rows"]], ["k3"])
        payload = self.cli(self.db("c.sqlite"), "--responsibility", "--person", "mike  ELKO")
        self.assertEqual([row["successor_key"] for row in payload["rows"]], ["k1"])

    def test_source_kind_is_refused_on_a_predecessor_table(self) -> None:
        message = self.refused(self.db(), "--responsibility", "--legacy-audit",
                               "--source-kind", "STAFF_TITLE")
        self.assertIn(rq.REFUSED_FILTER_NOT_CARRIED_BY_SELECTED_TABLE, message)


class Pagination(Base):
    def _page_through(self, path: Path, *argv: str, key: str, limit: int) -> list[str]:
        seen: list[str] = []
        offset = 0
        pages = 0
        while True:
            payload = self.cli(path, *argv, "--limit", str(limit), "--offset", str(offset))
            pages += 1
            seen.extend(str(row[key]) for row in payload["rows"])
            nxt = payload["pagination"]["next_offset"]
            if nxt is None:
                self.assertTrue(payload["pagination"]["is_last_page"])
                break
            self.assertEqual(nxt, offset + limit)
            offset = nxt
            self.assertLess(pages, 50)
        return seen

    def test_pages_reconcile_to_the_selected_table(self) -> None:
        path = self.db()
        seen = self._page_through(path, "--career", key="episode_id", limit=2)
        oracle = {row[0] for row in self.conn(path).execute(
            "SELECT episode_id FROM career_episode_successor")}
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(set(seen), oracle)
        whole = self.cli(path, "--career", "--all")
        self.assertEqual([row["episode_id"] for row in whole["rows"]], seen)
        self.assertEqual(whole["pagination"]["total_count"], len(oracle))
        self.assertEqual(whole["release_dispatch"]["selected_table_row_count"], len(oracle))

    def test_legacy_pages_reconcile_to_the_predecessor_table(self) -> None:
        path = self.db()
        seen = self._page_through(path, "--career", "--legacy-audit",
                                  key="career_episode_id", limit=4)
        self.assertEqual(sorted(seen, key=int), [str(row[0]) for row in PREDECESSOR_CAREER])

    def test_responsibility_pages_reconcile(self) -> None:
        path = self.db()
        seen = self._page_through(path, "--responsibility", key="successor_key", limit=1)
        self.assertEqual(sorted(seen), ["k1", "k2", "k3"])

    def test_scheme_pages_reconcile(self) -> None:
        path = self.db()
        seen = self._page_through(path, "--scheme", key="scheme_assertion_id", limit=2)
        self.assertEqual(sorted(seen), [f"SC{index}" for index in range(5)])

    def test_an_offset_past_the_end_is_an_empty_last_page(self) -> None:
        payload = self.cli(self.db(), "--career", "--offset", "100")
        self.assertEqual(payload["rows"], [])
        self.assertIsNone(payload["pagination"]["next_offset"])
        self.assertEqual(payload["pagination"]["total_count"], len(SUCCESSOR_CAREER))

    def test_invalid_pagination_is_refused(self) -> None:
        path = self.db()
        self.assertIn(rq.REFUSED_INVALID_PAGINATION, self.refused(path, "--career", "--limit", "0"))
        self.assertIn(rq.REFUSED_INVALID_PAGINATION,
                      self.refused(path, "--career", "--offset", "-1"))
        self.assertIn("mutually exclusive", self.refused(path, "--career", "--all", "--limit", "5"))
        self.assertIn("--limit", self.refused(path, "--team", "Texas A&M", "--season", "2026",
                                              "--limit", "5"))


class CareerFilters(Base):
    def keys(self, *argv: str) -> set[str]:
        return {row["episode_id"] for row in self.cli(self.db(), "--career", "--all", *argv)["rows"]}

    def test_season_covers_the_stated_interval_including_ongoing(self) -> None:
        self.assertEqual(self.keys("--season", "2026"), {"R:200:COACHING:1:0"})
        self.assertEqual(self.keys("--season", "1968"), {"R:100:COACHING:1:0"})

    def test_division_with_season_uses_that_season_classification(self) -> None:
        self.assertEqual(self.keys("--season", "2011", "--division", "FBS"), {"R:200:COACHING:2:0"})
        self.assertEqual(self.keys("--season", "1987", "--division", "fcs"), {"R:300:COACHING:1:0"})
        self.assertEqual(self.keys("--season", "2011", "--division", "FCS"), set())

    def test_role_family_and_team_are_exact(self) -> None:
        self.assertEqual(self.keys("--role", "offensive_coordinator"), {"R:300:COACHING:1:0"})
        self.assertEqual(self.keys("--family", "playing"), {"R:100:PLAYING:1:0"})
        self.assertEqual(self.keys("--team", "Ohio State"), {"R:200:COACHING:2:0"})
        self.assertEqual(self.keys("--team", "Ohio"), set())

    def test_rows_without_an_interval_are_counted_not_hidden(self) -> None:
        payload = self.cli(self.db(), "--career", "--season", "1987")
        self.assertEqual(
            payload["missingness"]["rows_without_a_season_value_matching_the_other_filters"], 1
        )

    def test_an_unknown_team_is_unanswerable_not_empty(self) -> None:
        payload = self.cli(self.db(), "--career", "--team", "Nowhere State")
        self.assertFalse(payload["answerable"])

    def test_a_non_integer_season_is_refused(self) -> None:
        self.assertIn(rq.REFUSED_SEASON_IS_NOT_AN_INTEGER,
                      self.refused(self.db(), "--career", "--season", "CURRENT"))


class OlderReleasesStayReadable(Base):
    def test_a_v36_release_answers_from_its_own_table_in_its_own_shape(self) -> None:
        path = self.db("v36.sqlite", version=V361, successors=False)
        payload = self.cli(path, "--person", BILL)
        self.assertEqual(payload["release_dispatch"]["mode"], rq.MODE_PREDECESSOR_ONLY_RELEASE)
        self.assertEqual(payload["career_episode_count"], 3)
        for row in payload["career_episodes"]:
            self.assertEqual(set(row), PREDECESSOR_CAREER_COLUMNS)
        responsibility = self.cli(path, "--responsibility")
        self.assertEqual(responsibility["rows"][0]["disposition"],
                         "REJECTED_TITLE_IS_NOT_A_RESPONSIBILITY_STATEMENT")
        coverage = self.cli(path, "--coverage")
        self.assertEqual(coverage["successor_conservation"], {})
        self.assertEqual(coverage["release_dispatch"]["career"]["selected_table"], "career_episode")

    def test_legacy_audit_on_a_predecessor_only_release_says_what_it_read(self) -> None:
        path = self.db("v36.sqlite", version=V361, successors=False)
        payload = self.cli(path, "--person", BILL, "--legacy-audit")
        self.assertEqual(payload["release_dispatch"]["mode"], rq.MODE_PREDECESSOR_ONLY_RELEASE)
        self.assertTrue(payload["release_dispatch"]["legacy_audit_requested"])

    def test_a_v37_1_release_without_successors_is_predecessor_only(self) -> None:
        path = self.db("v371.sqlite", version=V371, successors=False, lineage_table=True)
        payload = self.cli(path, "--career", "--all")
        self.assertEqual(payload["release_dispatch"]["mode"], rq.MODE_PREDECESSOR_ONLY_RELEASE)
        self.assertEqual(payload["pagination"]["total_count"], len(PREDECESSOR_CAREER))

    def test_a_predecessor_table_does_not_pretend_to_carry_divisions(self) -> None:
        path = self.db("v36.sqlite", version=V361, successors=False)
        self.assertIn(rq.REFUSED_FILTER_NOT_CARRIED_BY_SELECTED_TABLE,
                      self.refused(path, "--career", "--division", "FBS"))


class MalformedReleasesAreRefused(Base):
    def mutate(self, sql: str, **options: Any) -> Path:
        path = self.db("m.sqlite", **options)
        conn = sqlite3.connect(str(path))
        conn.executescript(sql)
        conn.commit()
        conn.close()
        return path

    def assertRefused(self, path: Path, code: str, *argv: str) -> None:
        for query in (argv or ("--person", BILL), ("--responsibility",), ("--coverage",)):
            with self.subTest(query=query):
                self.assertIn(code, self.refused(path, *query))

    def test_no_identity_table(self) -> None:
        path = self.mutate("DROP TABLE release_identity;")
        self.assertIn(rq.REFUSED_RELEASE_IDENTITY_TABLE_ABSENT, self.refused(path, "--person", BILL))

    def test_no_declared_version(self) -> None:
        path = self.db(version=None)
        self.assertIn(rq.REFUSED_RELEASE_VERSION_NOT_DECLARED, self.refused(path, "--person", BILL))
        self.assertIn(rq.REFUSED_RELEASE_VERSION_NOT_DECLARED,
                      self.refused(path, "--team", "Texas A&M", "--season", "2026"))

    def test_an_unregistered_version(self) -> None:
        path = self.mutate(
            "UPDATE release_identity SET value='BAS-FUTURE-v99' WHERE key='release_version';"
            "UPDATE release_lineage SET value='BAS-FUTURE-v99' "
            "WHERE key='successor_release_version';"
        )
        self.assertRefused(path, rq.REFUSED_RELEASE_VERSION_NOT_SUPPORTED)

    def test_lineage_naming_another_version(self) -> None:
        path = self.mutate("UPDATE release_lineage SET value='other' "
                           "WHERE key='successor_release_version';")
        self.assertRefused(path, rq.REFUSED_LINEAGE_VERSION_DISAGREES)

    def test_a_lineage_table_the_version_does_not_declare(self) -> None:
        path = self.db(version=V361, successors=False, lineage_table=True)
        self.assertIn(rq.REFUSED_LINEAGE_NOT_DECLARED_BY_VERSION,
                      self.refused(path, "--person", BILL))

    def test_a_declared_successor_that_is_absent(self) -> None:
        path = self.mutate("DROP TABLE career_episode_successor;")
        self.assertIn(rq.REFUSED_REQUIRED_TABLES_ABSENT, self.refused(path, "--person", BILL))
        path = self.mutate("DROP TABLE responsibility_successor;")
        self.assertIn(rq.REFUSED_REQUIRED_TABLES_ABSENT, self.refused(path, "--responsibility"))

    def test_a_present_successor_that_is_undeclared(self) -> None:
        path = self.mutate("DELETE FROM release_lineage WHERE key LIKE 'successor_table::%';")
        self.assertIn(rq.REFUSED_UNDECLARED_SUCCESSOR_TABLE, self.refused(path, "--person", BILL))
        self.assertIn(rq.REFUSED_UNDECLARED_SUCCESSOR_TABLE, self.refused(path, "--responsibility"))

    def test_a_career_successor_declared_without_its_disposition(self) -> None:
        path = self.mutate("DELETE FROM release_lineage WHERE key = "
                           "'successor_table::career_predecessor_disposition::ledger_sha256';")
        self.assertIn(rq.REFUSED_SUCCESSOR_DECLARATION_INCOMPLETE,
                      self.refused(path, "--career"))

    def test_a_missing_required_column(self) -> None:
        path = self.mutate("ALTER TABLE career_episode_successor DROP COLUMN raw_file;")
        message = self.refused(path, "--career")
        self.assertIn(rq.REFUSED_REQUIRED_COLUMNS_ABSENT, message)
        self.assertIn("raw_file", message)

    def test_an_absent_predecessor_table(self) -> None:
        path = self.mutate("DROP TABLE responsibility_assertion;")
        self.assertIn(rq.REFUSED_REQUIRED_TABLES_ABSENT, self.refused(path, "--responsibility"))

    def test_schema_reports_a_refusal_instead_of_failing(self) -> None:
        path = self.db(version=None)
        report = self.cli(path, "--schema")
        self.assertEqual(report["release_dispatch"]["refused"], rq.REFUSED_RELEASE_VERSION_NOT_DECLARED)


class Conservation(Base):
    def test_coverage_accounts_every_predecessor_and_successor_row(self) -> None:
        coverage = self.cli(self.db(), "--coverage")
        career = coverage["successor_conservation"]["career"]
        self.assertTrue(career["balanced"])
        self.assertEqual(career["predecessor_rows"], 6)
        self.assertEqual(career["predecessor_rows_mapped_to_a_successor"], 5)
        self.assertEqual(career["predecessor_rows_mapped_to_no_successor"], 1)
        self.assertEqual(career["successor_rows"], 7)
        self.assertEqual(career["successor_rows_derived_from_predecessor_rows"], 5)
        self.assertEqual(career["successor_rows_new_in_successor_by_family"],
                         {"COACHING": 1, "PLAYING": 1})
        responsibility = coverage["successor_conservation"]["responsibility"]
        self.assertTrue(responsibility["balanced"])
        self.assertEqual(responsibility["successor_rows_new_in_successor_by_source_kind"],
                         {"ENCYCLOPEDIA_REVISION": 1})
        recount = coverage["live_table_recount"]
        self.assertEqual(recount["career_episode_successor"], 7)
        self.assertEqual(recount["responsibility_successor"], 3)

    def test_an_unbalanced_disposition_is_reported(self) -> None:
        path = self.db()
        conn = sqlite3.connect(str(path))
        conn.execute("DELETE FROM career_predecessor_disposition WHERE predecessor_span_id = "
                     "'w:200:career:2'")
        conn.commit()
        conn.close()
        career = self.cli(path, "--coverage")["successor_conservation"]["career"]
        self.assertFalse(career["balanced"])
        self.assertEqual(career["predecessor_rows_without_a_disposition"], 1)


class OtherSchemasRefuseTheNewFlags(Base):
    def test_a_flat_cycle33_database_refuses_career_and_modifiers(self) -> None:
        path = self.base / "flat.sqlite"
        conn = cli.connect_for_import(path)
        conn.close()
        for argv in (["--career"], ["--person", "X", "--legacy-audit"],
                     ["--person", "X", "--limit", "2"]):
            with self.subTest(argv=argv):
                self.assertIn("national-release queries", self.refused(path, *argv))


if __name__ == "__main__":
    unittest.main()
