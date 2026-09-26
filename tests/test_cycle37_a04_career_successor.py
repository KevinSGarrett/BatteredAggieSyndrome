"""Cycle #37 — Attempt #4 — MF37A03-04/05 and the explicitly selected career successor (R37A04-04/05/06).

MF37A03-04. The delivered row ``R37-05:61958463:1368703693:COACHING:6:0`` keeps the raw text
``[[Rutgers ...|Rutgers]] (DFO)`` yet states ``role_text=null`` and ``head_coach``/``PRINCIPAL``: v37.2 filed an
unrecognized parenthetical as an employer qualifier and then applied the head-coach convention. STQC, SA and an
arbitrary ``UNRECOGNIZED_JOB`` took the same route.

MF37A03-05. Raw ``coach_years6 = 2009–?`` became ``start = end = 2009``, ``ongoing = false``: the range pattern
did not know an unknown endpoint and the single-year fallback consumed the known one.

The parser tests keep every positive control the finding names (a TX location, an explicit OC, multiple roles,
the genuine no-title convention, closed/single/abbreviated/discontinuous/present years) beside the negatives.
``*_challenge`` cases are this attempt's own: a place-shaped word no vocabulary knows, the same abbreviation
meaning two things on two pages, a deleted ``{{abbr}}``, spelled-out field names, a years field with no team.

The successor tests build small owned predecessor and successor files and check every named refusal of
:func:`aggie_analytics.cycle37.career_successor.attach_successor` -- wrong predecessor digest, tampered ledger,
duplicate and missing identities, activation and authority claims, a pinned file digest -- and the per-row
raw-byte and predecessor-binding checks. The installed CLI over the real delivered release is exercised by the
CAREER_SUCCESSOR and INSTALLED_CONSUMER_C01 lanes.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle37"))

from aggie_analytics.cycle37 import career_infobox as ci  # noqa: E402
from aggie_analytics.cycle37 import career_successor as cs  # noqa: E402


def assignments(row: dict) -> list[dict]:
    import r37_05_career_reparse as reparse  # noqa: PLC0415

    return reparse.assignments_for(row)


def team_row(raw: str | None, family: str = "COACHING") -> dict:
    return {"family": family, "team": ci.parse_team(raw) if raw is not None else None}


class UnknownRoleParentheticalTests(unittest.TestCase):
    """MF37A03-04: an unresolved parenthetical is neither a qualifier nor a head-coach appointment."""

    def test_the_manager_codes_are_unresolved_and_never_head_coach(self) -> None:
        for raw, code in (("[[Rutgers Scarlet Knights football|Rutgers]] (DFO)", "DFO"),
                          ("[[Texas A&M–Commerce Lions football|Texas A&M–Commerce]] (STQC)", "STQC"),
                          ("[[Auburn Tigers football|Auburn]] (SA)", "SA"),
                          ("[[Rutgers Scarlet Knights football|Rutgers]] (UNRECOGNIZED_JOB)", "UNRECOGNIZED_JOB")):
            with self.subTest(code=code):
                team = ci.parse_team(raw)
                self.assertEqual(team["role_basis"], "UNRESOLVED_PARENTHETICAL")
                self.assertIsNone(team["role_text"])
                self.assertNotIn(code, team["employer_qualifiers"])
                self.assertEqual([item["text"] for item in team["unresolved_parentheticals"]], [code])
                roles = assignments({"family": "COACHING", "team": team})
                self.assertEqual([(a["role"], a["occupancy"]) for a in roles], [("role_unresolved", "UNRESOLVED")])
                self.assertEqual(roles[0]["unresolved_text"], [code])

    def test_known_qualifiers_explicit_roles_and_the_no_title_convention_are_kept(self) -> None:
        cases = (
            ("Stamford HS (TX)", "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL", None, ["TX"], "head_coach"),
            ("[[Rutgers Scarlet Knights football|Rutgers]] (OC)", "EXPLICIT_PARENTHETICAL", "OC", [], None),
            ("Iowa (OC/QB)", "EXPLICIT_PARENTHETICAL", "OC/QB", [], None),
            ("Miami (OH) (DE)", "EXPLICIT_PARENTHETICAL", "DE", ["OH"], None),
            ("Iowa", "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL", None, [], "head_coach"),
            ("Hamilton HS (Hamilton, Ohio)", "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL", None, ["Hamilton, Ohio"],
             "head_coach"),
            ("Toledo (Ill.)", "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL", None, ["Ill."], "head_coach"),
            ("Montreal Alouettes (CFL)", "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL", None, ["CFL"], "head_coach"),
            ("Podunk HS (football, basketball)", "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL", None,
             ["football, basketball"], "head_coach"),
        )
        for raw, basis, role, qualifiers, convention in cases:
            with self.subTest(raw=raw):
                team = ci.parse_team(raw)
                self.assertEqual((team["role_basis"], team["role_text"], team["employer_qualifiers"]),
                                 (basis, role, qualifiers))
                self.assertEqual(team["unresolved_parentheticals"], [])
                roles = assignments({"family": "COACHING", "team": team})
                if convention:
                    self.assertEqual([(a["role"], a["occupancy"]) for a in roles], [("head_coach", "PRINCIPAL")])
                else:
                    self.assertNotIn("head_coach", [a["role"] for a in roles])
        multi = assignments({"family": "COACHING", "team": ci.parse_team("Iowa (AHC/OC/QB)")})
        self.assertGreaterEqual(len({a["role"] for a in multi}), 2)

    def test_novel_and_place_shaped_unknowns_challenge(self) -> None:
        # Words that look like places or roles but belong to no vocabulary are not guessed either way.
        for inner in ("XYZQ", "trainer", "Narnia", "commissioner", "?", "/", "1st stint"):
            with self.subTest(inner=inner):
                team = ci.parse_team(f"Iowa ({inner})")
                self.assertEqual(team["role_basis"], "UNRESOLVED_PARENTHETICAL", team)
                self.assertNotIn("head_coach", [a["role"] for a in assignments({"family": "COACHING", "team": team})])
        empty = ci.parse_team("Iowa ()")
        self.assertEqual(empty["unresolved_parentheticals"][0]["basis"], "EMPTY_PARENTHETICAL")

    def test_an_abbreviation_means_only_what_its_own_row_states_challenge(self) -> None:
        # "SA" is "Student assistant" on one page and "Special assistant to the president" on another.
        student = ci.parse_team("Iowa ({{tooltip|SA|Student assistant}})")
        special = ci.parse_team("Iowa ({{abbr|SA|Special assistant to the president}})")
        bare = ci.parse_team("Iowa (SA)")
        self.assertEqual(student["role_text"], "Student assistant")
        self.assertEqual(special["role_text"], "Special assistant to the president")
        self.assertEqual(student["role_parentheticals"][0]["basis"], "EXPANSION_STATED_BY_THIS_ROWS_TEMPLATE")
        self.assertEqual(bare["role_basis"], "UNRESOLVED_PARENTHETICAL")

    def test_a_deleted_abbreviation_template_is_displayed_challenge(self) -> None:
        # v37.2 removed every template, so "({{abbr|OC|...}})" was an empty qualifier and a head coach.
        team = ci.parse_team("Iowa ({{abbr|OC|Offensive coordinator}})")
        self.assertEqual((team["role_text"], team["employer_display"]), ("OC", "Iowa"))
        self.assertEqual(ci.plain("{{nowrap|Texas A&M}}"), "Texas A&M")

    def test_an_unpaired_parenthesis_does_not_swallow_the_role_challenge(self) -> None:
        # Cached revision text: an unpaired "(" in the link display hid "(DC)", and the row became a head coach.
        team = ci.parse_team("[[Claremore High School|Claremore (HS (OK)]] ([[Defensive coordinator|DC]])")
        self.assertEqual((team["role_text"], team["role_basis"]), ("DC", "EXPLICIT_PARENTHETICAL"))
        self.assertNotIn("head_coach", [a["role"] for a in assignments({"family": "COACHING", "team": team})])
        # An unpaired parenthesis outside every link is unresolved text, never the head-coach convention.
        open_code = ci.parse_team("[[Rutgers Scarlet Knights football|Rutgers]] (DFO")
        self.assertEqual(open_code["role_basis"], "UNRESOLVED_PARENTHETICAL")
        self.assertEqual(open_code["unresolved_parentheticals"][0]["basis"], "UNPAIRED_PARENTHESIS_OUTSIDE_THE_LINKS")
        self.assertNotIn("head_coach", [a["role"] for a in assignments({"family": "COACHING", "team": open_code})])
        # An unpaired link target no longer hides the display's own qualifier; paired text reads as before.
        self.assertEqual(ci.parse_team("[[Escanab *USFL(a High School|Escanaba HS (MI)]]")["employer_qualifiers"], ["MI"])
        self.assertEqual(ci.parse_team("[[Graham High School (Texas)|Graham HS (TX)]]")["employer_qualifiers"],
                         ["Texas", "TX"])

    def test_a_years_field_with_no_team_states_no_role_challenge(self) -> None:
        self.assertEqual([(a["role"], a["basis"]) for a in assignments(team_row(None))],
                         [("role_not_stated", "TEAM_FIELD_ABSENT")])

    def test_spelled_out_career_fields_are_read_under_their_own_index_challenge(self) -> None:
        text = ("{{Infobox CFL biography\n| name = X\n| coaching_years1 = 1983\n"
                "| coaching_team1 = [[Miami RedHawks football|Miami (OH)]] (Assistant coach)\n"
                "| playing_years1 = 1978–1981\n| playing_team1 = Ohio State\n"
                "| coach_years1 = 1990\n| coach_team1 = Iowa\n}}")
        rows = {(r["family"], r["index"]): r for r in ci.career_rows(text)["rows"]}
        self.assertIn(("COACHING", 1), rows)
        self.assertIn(("COACHING", ci.VARIANT_FIELD_INDEX_OFFSET + 1), rows)
        self.assertIn(("PLAYING", ci.VARIANT_FIELD_INDEX_OFFSET + 1), rows)
        variant = rows[("COACHING", ci.VARIANT_FIELD_INDEX_OFFSET + 1)]
        self.assertEqual((variant["team"]["employer_display"], variant["team"]["role_text"]),
                         ("Miami (OH)", "Assistant coach"))

    def test_pastadmin_lists_are_read_under_their_own_index_challenge(self) -> None:
        text = ("{{Infobox NFL biography\n| name = X\n| pastexecutive =\n* [[Buffalo Bills]] (1990–1995)<br>GM\n"
                "| pastadmin =\n* [[Cincinnati Bearcats football|Cincinnati]] (1996–2000)<br>Athletic director\n}}")
        rows = {(r["family"], r["index"]): r for r in ci.career_rows(text)["rows"]}
        self.assertIn(("ADMINISTRATIVE", 1001), rows)
        admin = rows[("ADMINISTRATIVE", 3001)]
        self.assertEqual((admin["team"]["employer_display"], admin["team"]["role_text"], admin["list_field"]),
                         ("Cincinnati", "Athletic director", "pastadmin"))
        self.assertEqual([(i["start"], i["end"]) for i in admin["intervals"]], [(1996, 2000)])


class UncertainYearTests(unittest.TestCase):
    """MF37A03-05: an unknown or uncertain endpoint is never a closed single year or an ongoing tenure."""

    def one(self, raw: str) -> dict:
        intervals = ci.parse_years(raw)
        self.assertEqual(len(intervals), 1, intervals)
        return intervals[0]

    def test_the_manager_endpoints(self) -> None:
        open_end = self.one("2009–?")
        self.assertEqual((open_end["start"], open_end["end"], open_end["ongoing"]), (2009, None, False))
        self.assertEqual((open_end["start_state"], open_end["end_state"]), ("STATED", "UNKNOWN"))
        self.assertEqual((open_end["definite_first_season"], open_end["definite_last_season"]), (2009, 2009))
        self.assertEqual(open_end["as_written"], "2009–?")
        open_start = self.one("?–2009")
        self.assertEqual((open_start["start"], open_start["end"], open_start["start_state"]), (None, 2009, "UNKNOWN"))
        self.assertEqual((open_start["definite_first_season"], open_start["definite_last_season"]), (2009, 2009))

    def test_definite_meanings_are_unchanged(self) -> None:
        cases = {"2009": (2009, 2009, False, 2009, 2009), "2009–2011": (2009, 2011, False, 2009, 2011),
                 "1990–92": (1990, 1992, False, 1990, 1992), "2009–present": (2009, None, True, 2009, None),
                 "2019 (spring)": (2019, 2019, False, 2019, 2019)}
        for raw, (start, end, ongoing, first, last) in cases.items():
            with self.subTest(raw=raw):
                interval = self.one(raw)
                self.assertEqual((interval["start"], interval["end"], interval["ongoing"],
                                  interval["definite_first_season"], interval["definite_last_season"]),
                                 (start, end, ongoing, first, last))
        pair = ci.parse_years("1990, 1992–1994")
        self.assertEqual([(i["start"], i["end"]) for i in pair], [(1990, 1990), (1992, 1994)])

    def test_every_uncertain_syntax_in_the_cached_revisions(self) -> None:
        cases = {
            "191?–1921": (None, 1921, "PARTIAL", "STATED", 1919, 1921),
            "c. 1950": (None, None, "APPROXIMATE", "APPROXIMATE", None, None),
            "1950s": (None, None, "DECADE", "DECADE", None, None),
            "late 1950s": (None, None, "DECADE", "DECADE", None, None),
            "1999–": (1999, None, "STATED", "UNKNOWN", 1999, 1999),
            "–1999": (None, 1999, "UNKNOWN", "STATED", 1999, 1999),
            "2000–after 2005": (2000, None, "STATED", "AFTER", 2000, 2005),
            "1990–1994 or 1995": (1990, None, "STATED", "ALTERNATIVES", 1990, 1994),
            "2010–201x": (2010, None, "STATED", "PARTIAL", 2010, 2010),
            "1990?": (None, None, "QUESTIONED", "QUESTIONED", None, None),
            "c. 1950–1955": (None, 1955, "APPROXIMATE", "STATED", 1955, 1955),
            "?": (None, None, "UNKNOWN", "UNKNOWN", None, None),
            "Unknown": (None, None, "UNKNOWN", "UNKNOWN", None, None),
            "?–present": (None, None, "UNKNOWN", "PRESENT", None, None),
        }
        for raw, (start, end, start_state, end_state, first, last) in cases.items():
            with self.subTest(raw=raw):
                interval = self.one(raw)
                self.assertEqual((interval["start"], interval["end"], interval["start_state"], interval["end_state"],
                                  interval["definite_first_season"], interval["definite_last_season"]),
                                 (start, end, start_state, end_state, first, last))
                self.assertFalse(interval["ongoing"] and end_state != "PRESENT")

    def test_a_circa_template_is_approximate_not_exact_challenge(self) -> None:
        # 359 cached years fields write "{{Circa|1984}}"; the season-template rule had made each an exact year.
        for raw in ("{{Circa|1984}}", "{{circa|1984|lk=no}}", "{{c.|1984}}"):
            with self.subTest(raw=raw):
                interval = self.one(raw)
                self.assertEqual((interval["start_state"], interval["definite_first_season"], interval["as_written"]),
                                 ("APPROXIMATE", None, "c. 1984"))
        bounded = self.one("{{circa|1973}}–1975")
        self.assertEqual((bounded["start_state"], bounded["end"], bounded["definite_first_season"]),
                         ("APPROXIMATE", 1975, 1975))
        # A circa template around a range makes both years approximate; a bare one approximates the year after it.
        whole = self.one("{{Circa|1959–1962}}")
        self.assertEqual((whole["start_state"], whole["end_state"], whole["definite_first_season"], whole["as_written"]),
                         ("APPROXIMATE", "APPROXIMATE", None, "c. 1959–c. 1962"))
        self.assertEqual(self.one("{{Circa|1990–?}}")["end_state"], "UNKNOWN")
        self.assertEqual(self.one("{{circa}} 1940")["start_state"], "APPROXIMATE")
        # Season templates still render their stated year.
        self.assertEqual([(i["start"], i["end"]) for i in ci.parse_years("{{CFL Year|2007}}–{{CFL Year|2009}}")],
                         [(2007, 2009)])

    def test_entity_and_minus_dashes_are_one_range_not_two_years(self) -> None:
        for raw in ("1990&ndash;1995", "1990−1995", "1990 to 1995"):
            with self.subTest(raw=raw):
                interval = self.one(raw)
                self.assertEqual((interval["start"], interval["end"]), (1990, 1995))
        self.assertEqual(self.one("1990−1995")["as_written"], "1990−1995")

    def test_contradictory_bounds_are_not_definite(self) -> None:
        interval = self.one("1995–1990")
        self.assertFalse(interval["bounds_consistent"])
        self.assertIsNone(interval["definite_first_season"])


# ------------------------------------------------------------------ successor contract


def _predecessor(path: Path, rows: list[dict]) -> Path:
    conn = sqlite3.connect(path)
    conn.execute(f"CREATE TABLE {cs.PREDECESSOR_TABLE} ({', '.join(chr(34) + c + chr(34) for c in cs.PREDECESSOR_COLUMNS)})")
    for row in rows:
        conn.execute(f"INSERT INTO {cs.PREDECESSOR_TABLE} VALUES ({', '.join('?' for _ in cs.PREDECESSOR_COLUMNS)})",
                     [row.get(c) for c in cs.PREDECESSOR_COLUMNS])
    conn.commit()
    conn.close()
    return path


def _successor(path: Path, predecessor: Path, episodes: list[dict], dispositions: list[dict],
               **identity_overrides: str) -> Path:
    conn = sqlite3.connect(path)
    conn.execute(f"CREATE TABLE {cs.IDENTITY_TABLE} (key TEXT, value TEXT)")
    conn.execute(f"CREATE TABLE {cs.EPISODE_TABLE} ({', '.join(chr(34) + c + chr(34) for c in cs.EPISODE_COLUMNS)})")
    conn.execute(f"CREATE TABLE {cs.DISPOSITION_TABLE} ({', '.join(cs.DISPOSITION_COLUMNS)})")
    for episode in episodes:
        conn.execute(f"INSERT INTO {cs.EPISODE_TABLE} VALUES ({', '.join('?' for _ in cs.EPISODE_COLUMNS)})",
                     [episode.get(c) for c in cs.EPISODE_COLUMNS])
    for row in dispositions:
        conn.execute(f"INSERT INTO {cs.DISPOSITION_TABLE} VALUES ({', '.join('?' for _ in cs.DISPOSITION_COLUMNS)})",
                     [row.get(c) for c in cs.DISPOSITION_COLUMNS])
    conn.commit()
    identity = {"format_version": cs.FORMAT_VERSION, "successor_version": cs.SUCCESSOR_VERSION,
                "predecessor_database_sha256": cs.sha256_file(predecessor), "predecessor_table": cs.PREDECESSOR_TABLE,
                "predecessor_row_count": str(len({d["predecessor_episode_id"] for d in dispositions})),
                "default_activation": cs.NOT_ACTIVATED, "acceptance_state": cs.NOT_ACCEPTED,
                "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": "0"}
    for table, columns, key in ((cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, "episode_id"),
                                (cs.DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, "predecessor_episode_id")):
        digest, count = cs.table_ledger(conn, table, columns, key)
        identity[f"ledger::{table}::sha256"], identity[f"ledger::{table}::rows"] = digest, str(count)
    identity.update(identity_overrides)
    conn.executemany(f"INSERT INTO {cs.IDENTITY_TABLE} VALUES (?, ?)", sorted(identity.items()))
    conn.commit()
    conn.close()
    return path


#: Cycle #37 - Attempt #9 (MF37A08-01): the revision the two fixture rows cite states their two jobs.
CONTRACT_REVISION = ("{{Infobox college coach\n| name = Fixture Person\n| coach_years1 = 2009\n"
                     "| coach_team1 = [[Fixture State]] (OC)\n| coach_years2 = 2009\n"
                     "| coach_team2 = [[Fixture Tech]] (DC)\n}}\n")


def _witnessed(n: int) -> dict:
    """Row ``n``'s genuine witnesses: the ``coach_team{n}`` and ``coach_years{n}`` values and their texts."""

    fields = {}
    for kind in ("team", "years"):
        marker = f"| coach_{kind}{n} = "
        start = CONTRACT_REVISION.index(marker) + len(marker)
        end = CONTRACT_REVISION.index("\n", start)
        fields[f"{kind}_char_span"], fields[f"{kind}_raw"] = json.dumps([start, end]), CONTRACT_REVISION[start:end]
    return fields


class SuccessorContractTests(unittest.TestCase):
    # Cycle #37 - Attempt #5 (MF37A04-02): the consumer now proves lineage and raw evidence from the rows, so this
    # fixture carries what every real successor row carries -- a Wikimedia-shaped raw payload, the revision text's
    # SHA-256, the lineage state and the disposition. Every assertion below is unchanged.
    #
    # Cycle #37 - Attempt #9 (MF37A08-01): an edge is now anchored by the source units its two rows' identities name in
    # the revision they cite, never by their text, so a row whose identity names nothing there can carry no lineage.
    # The revision was the bare string "revision text", naming no job; it is now an infobox stating the two jobs
    # (coach_team1/2, coach_years1/2), and each row records its witnesses, as every genuine row does. The raw-byte
    # test keeps its serve-time assertion by changing the capture after the attach (a capture is now read at attach
    # for every row, so a change made before it is refused there, for the same cause -- asserted too). Every other
    # assertion is unchanged.
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.raw = self.root / "raw.json"
        self.raw.write_bytes(json.dumps({"query": {"pages": {"1": {
            "pageid": 1, "title": "Fixture Person (American football)", "pageprops": {"wikibase_item": "Q1"},
            "revisions": [{"revid": 1, "slots": {"main": {"*": CONTRACT_REVISION}}}]}}}}).encode("utf-8"))
        raw_sha = hashlib.sha256(self.raw.read_bytes()).hexdigest()
        text_sha = hashlib.sha256(CONTRACT_REVISION.encode("utf-8")).hexdigest()
        self.old = [{"episode_id": f"R37-05:1:1:COACHING:{n}:0", "pageid": 1, "revision": "1", "family": "COACHING",
                     "row_index": n, "interval_index": 0, "start": 2009, "end": 2009, "ongoing": 0,
                     "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": 0, "raw_file": str(self.raw),
                     "raw_file_sha256": raw_sha, "wikitext_sha256": text_sha, "assignments": "[]",
                     "page_title": "Fixture Person (American football)", "person_display": "Fixture Person",
                     "wikidata_qid": "Q1", **_witnessed(n)} for n in (1, 2)]
        self.predecessor = _predecessor(self.root / "predecessor.sqlite", self.old)
        self.episodes = [{"episode_id": f"C37A04:1:1:COACHING:{n}:0", "pageid": 1, "revision": "1",
                          "family": "COACHING", "row_index": n, "interval_index": 0, "start": 2009, "end": None,
                          "ongoing": 0, "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": 0,
                          "raw_file": str(self.raw), "raw_file_sha256": raw_sha, "assignments": "[]",
                          "wikitext_sha256": text_sha, "lineage_state": cs.DERIVED, **_witnessed(n),
                          "page_title": "Fixture Person (American football)", "person_display": "Fixture Person",
                          "wikidata_qid": "Q1",
                          "disposition": cs.UNRESOLVED_EXPLICIT,
                          "predecessor_episode_ids": json.dumps([f"R37-05:1:1:COACHING:{n}:0"]),
                          "definite_first_season": 2009, "definite_last_season": 2009,
                          "uncertainty_classes": json.dumps(["UNKNOWN_END"])} for n in (1, 2)]
        self.dispositions = [{"predecessor_episode_id": row["episode_id"], "disposition": cs.UNRESOLVED_EXPLICIT,
                              "successor_episode_ids": json.dumps([f"C37A04:1:1:COACHING:{row['row_index']}:0"]),
                              "changed_fields": "{}", "predecessor_row_sha256": cs.predecessor_row_digest(row),
                              "screens": "[]", "reason": "fixture"} for row in self.old]

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def attach(self, successor: Path, **kw):
        conn = sqlite3.connect(self.predecessor.resolve().as_uri() + "?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            return cs.attach_successor(conn, successor, database=self.predecessor, **kw), conn
        except Exception:
            conn.close()
            raise

    def refused(self, code: str, successor: Path, **kw) -> None:
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            _binding, conn = self.attach(successor, **kw)
            conn.close()
        self.assertEqual(caught.exception.code, code, str(caught.exception))

    def test_a_bound_successor_attaches_and_is_selected_only_by_name(self) -> None:
        successor = _successor(self.root / "ok.sqlite", self.predecessor, self.episodes, self.dispositions)
        binding, conn = self.attach(successor)
        try:
            self.assertEqual(binding["selection"], "EXPLICIT_CAREER_SUCCESSOR")
            self.assertEqual(binding["default_activation"], cs.NOT_ACTIVATED)
            self.assertEqual(conn.execute(f"SELECT COUNT(*) FROM {cs.VIEW_NAME}").fetchone()[0], 2)
            self.assertEqual(cs.verify_raw_bytes([dict(r) for r in conn.execute(f"SELECT * FROM {cs.VIEW_NAME}").fetchall()]), 2)
        finally:
            conn.close()

    def test_a_successor_of_another_predecessor_is_refused(self) -> None:
        successor = _successor(self.root / "wrong.sqlite", self.predecessor, self.episodes, self.dispositions,
                               predecessor_database_sha256="0" * 64)
        self.refused(cs.REFUSED_PREDECESSOR, successor)

    def test_tampered_successor_rows_are_refused(self) -> None:
        successor = _successor(self.root / "tampered.sqlite", self.predecessor, self.episodes, self.dispositions)
        conn = sqlite3.connect(successor)
        conn.execute(f"UPDATE {cs.EPISODE_TABLE} SET \"end\" = 2012 WHERE episode_id LIKE '%:1:0'")
        conn.commit()
        conn.close()
        self.refused(cs.REFUSED_LEDGER, successor)

    def test_missing_and_duplicate_identities_are_refused(self) -> None:
        missing = _successor(self.root / "missing.sqlite", self.predecessor, self.episodes, self.dispositions[:1],
                             predecessor_row_count="2")
        self.refused(cs.REFUSED_COVERAGE, missing)
        duplicate = _successor(self.root / "duplicate.sqlite", self.predecessor, self.episodes + self.episodes[:1],
                               self.dispositions)
        self.refused(cs.REFUSED_COVERAGE, duplicate)
        foreign = [{**self.episodes[0], "episode_id": "R37-05:1:1:COACHING:1:0"}, self.episodes[1]]
        self.refused(cs.REFUSED_COVERAGE, _successor(self.root / "foreign.sqlite", self.predecessor, foreign,
                                                     self.dispositions))

    def test_activation_and_fabricated_authority_are_refused(self) -> None:
        self.refused(cs.REFUSED_ACTIVATION, _successor(self.root / "active.sqlite", self.predecessor, self.episodes,
                                                       self.dispositions, default_activation="DEFAULT_ACTIVATED"))
        self.refused(cs.REFUSED_AUTHORITY, _successor(self.root / "accepted.sqlite", self.predecessor, self.episodes,
                                                      self.dispositions, acceptance_state="ACCEPTED"))
        pit = [{**self.episodes[0], "pit_admitted": 1}, self.episodes[1]]
        self.refused(cs.REFUSED_AUTHORITY, _successor(self.root / "pit.sqlite", self.predecessor, pit,
                                                      self.dispositions))

    def test_a_pinned_file_digest_must_match(self) -> None:
        successor = _successor(self.root / "pinned.sqlite", self.predecessor, self.episodes, self.dispositions)
        self.refused(cs.REFUSED_FILE_DIGEST, successor, expected_sha256="f" * 64)
        binding, conn = self.attach(successor, expected_sha256=cs.sha256_file(successor))
        conn.close()
        self.assertEqual(binding["successor_file_sha256"], cs.sha256_file(successor))

    def test_changed_raw_bytes_are_refused_when_a_row_is_served(self) -> None:
        successor = _successor(self.root / "raw.sqlite", self.predecessor, self.episodes, self.dispositions)
        binding, conn = self.attach(successor)
        self.raw.write_bytes(b'{"raw": "changed"}')        # A9: changed after the attach, before the rows are served
        try:
            with self.assertRaises(cs.CareerSuccessorError) as caught:
                cs.verify_raw_bytes([dict(r) for r in conn.execute(f"SELECT * FROM {cs.VIEW_NAME}").fetchall()])
            self.assertEqual(caught.exception.code, cs.REFUSED_RAW)
        finally:
            conn.close()
        self.refused(cs.REFUSED_RAW, successor)             # A9: the same change seen by a later attach


if __name__ == "__main__":
    unittest.main()
