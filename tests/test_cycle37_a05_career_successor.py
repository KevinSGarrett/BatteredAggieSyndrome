"""Cycle #37 — Attempt #5 — MF37A04-02/03/04: the corrected explicit career successor (R37A05-02/03/04).

MF37A04-03. ``{{NFL Year|1987|1989}}`` became 1987 and ``{{nfly|2023|present}}`` became 2023: every template whose
first argument is a year was rendered as that year. A nested list line's own date
(``** Defensive quality control coach {{nfly|2005|2006}})``) was replaced by its parent's wider one. The parser
tests below read every form the independent template census enumerated -- one season, a range, to present, an end
written empty -- and keep every other shape as an explicitly unresolved date that carries its raw text.

MF37A04-04. "Special teams / defensive passing game coordinator" carried the OFFENSE unit: a side-dependent role
took the v1.1 default. The taxonomy tests take all 33 titles of the manager's screen and the controls.

MF37A04-02. A resealed file with a deleted row, nulled raw fields and a dangling disposition was accepted: the
consumer checked counts and ledgers, not lineage. The contract tests build small owned predecessor, Attempt 4 and
Attempt 5 files and check each named refusal of
:func:`aggie_analytics.cycle37.career_successor.attach_successor` and of the raw-evidence verifier, by cause.
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

from aggie_analytics.cycle37 import career_infobox as ci  # noqa: E402
from aggie_analytics.cycle37 import career_successor as cs  # noqa: E402
from aggie_analytics.cycle37 import staff_record  # noqa: E402


def one(raw: str) -> list[tuple]:
    return [(i["start"], i["end"], i["ongoing"], i["start_state"], i["end_state"]) for i in ci.parse_years(raw)]


class SeasonTemplateGrammarTests(unittest.TestCase):
    """Every season-template form the census enumerated, read as it displays; nothing cut to its first year."""

    def test_the_manager_ranges_keep_both_endpoints(self) -> None:
        self.assertEqual(one("{{NFL Year|1987|1989}}"), [(1987, 1989, False, ci.STATED, ci.STATED)])
        self.assertEqual(one("{{nfly|2015|2019}}"), [(2015, 2019, False, ci.STATED, ci.STATED)])
        self.assertEqual(one("{{cfl year|1998|2001}}"), [(1998, 2001, False, ci.STATED, ci.STATED)])
        self.assertEqual(one("{{cfly|2003|2004}}"), [(2003, 2004, False, ci.STATED, ci.STATED)])
        present = ci.parse_years("{{nfly|2023|present}}")
        self.assertEqual((present[0]["start"], present[0]["ongoing"], present[0]["end_state"]), (2023, True, ci.PRESENT))

    def test_single_seasons_and_template_ranges_are_unchanged(self) -> None:
        self.assertEqual(one("{{nfly|1953}}"), [(1953, 1953, False, ci.STATED, ci.STATED)])
        self.assertEqual(one("{{nfly|2010}}–{{nfly|2012}}"), [(2010, 2012, False, ci.STATED, ci.STATED)])
        self.assertEqual(one("{{NFL Year|1953}}; {{NFL Year|1956|1961}}"),
                         [(1953, 1953, False, ci.STATED, ci.STATED), (1956, 1961, False, ci.STATED, ci.STATED)])
        self.assertEqual(one("2004–2007"), [(2004, 2007, False, ci.STATED, ci.STATED)])

    def test_an_end_season_written_empty_is_an_open_end(self) -> None:
        interval = ci.parse_years("{{nfly|2015|}}")[0]
        self.assertEqual((interval["start"], interval["end"], interval["ongoing"], interval["end_state"]),
                         (2015, None, False, ci.UNKNOWN))
        self.assertEqual((interval["definite_first_season"], interval["definite_last_season"]), (2015, 2015))

    def test_unsupported_shapes_stay_explicitly_unresolved_with_their_raw_text(self) -> None:
        for raw in ("{{nfl year|1987|89}}", "{{nfl year|1990|end=1992}}", "{{nfly|1990|1991|1992}}",
                    "{{rhe season|2001|2002}}", "{{some date|1999}}"):
            with self.subTest(raw=raw):
                intervals = ci.parse_years(raw)
                self.assertTrue(intervals, raw)
                self.assertIn(ci.UNRESOLVED_TEMPLATE, (intervals[0]["start_state"], intervals[0]["end_state"]))
                self.assertIsNone(intervals[0]["start"])
                self.assertEqual(ci.unresolved_templates(ci.plain(raw, dates=True)), [raw])
                self.assertEqual(intervals[0]["as_written"], raw)

    def test_citations_are_not_dates_and_display_text_keeps_one_season(self) -> None:
        self.assertEqual(one("2009–2011<ref>{{cite web|title=2012 roster|date=2012}}</ref>"),
                         [(2009, 2011, False, ci.STATED, ci.STATED)])
        self.assertEqual(ci.plain("{{nfly|2012}}"), "2012")
        self.assertEqual(ci.plain("{{nfly|2012|2014}}"), "2012–2014")


LIST_PAGE = """{{Infobox NFL biography
| name = Example Coach
| pastcoaching =
* [[Cleveland Browns]] ({{nfly|2005|2008}})
** Defensive quality control coach {{nfly|2005|2006}})
** Defensive assistant
** Defensive backs coach ({{nfly|2007|2008}})
* [[Philadelphia Eagles]] ({{nfly|2015|2019}})<br>Defensive backs coach
}}
"""


class NestedListDateTests(unittest.TestCase):
    """A nested line keeps its own date; a line with none inherits its parent's and names the parent."""

    def setUp(self) -> None:
        parsed = ci.career_rows(LIST_PAGE)
        self.rows = {row["index"]: row for row in parsed["rows"]}

    def span_text(self, row: dict) -> str:
        return LIST_PAGE[row["years_span"][0]:row["years_span"][1]]

    def test_every_line_reads_its_own_date(self) -> None:
        cases = {1001: ("ITEM_DATE_IN_BALANCED_PARENTHESES", (2005, 2008)),
                 1002: ("CHILD_DATE_WITHOUT_BALANCED_PARENTHESES", (2005, 2006)),
                 1004: ("CHILD_DATE_IN_BALANCED_PARENTHESES", (2007, 2008)),
                 1005: ("ITEM_DATE_IN_BALANCED_PARENTHESES", (2015, 2019))}
        for index, (basis, years) in cases.items():
            with self.subTest(index=index):
                row = self.rows[index]
                self.assertEqual(row["date_basis"], basis)
                self.assertEqual([(i["start"], i["end"]) for i in row["intervals"]], [years])
                self.assertEqual(self.span_text(row), row["years_raw"])
                self.assertIsNone(row["date_parent"])

    def test_a_line_without_a_date_inherits_and_names_its_parent(self) -> None:
        child = self.rows[1003]
        self.assertEqual(child["date_basis"], "INHERITED_FROM_PARENT_ITEM")
        self.assertIsNone(child["years_span"])
        self.assertEqual(child["date_parent"], {"row_index": 1001, "years_raw": "{{nfly|2005|2008}}",
                                                "years_span": self.rows[1001]["years_span"]})
        self.assertEqual([(i["start"], i["end"]) for i in child["intervals"]], [(2005, 2008)])
        self.assertEqual(child["team"]["role_text"], "Defensive assistant")

    def test_a_childs_explicit_date_is_never_replaced_by_the_parents(self) -> None:
        self.assertNotEqual(self.rows[1002]["years_raw"], self.rows[1001]["years_raw"])
        self.assertEqual(self.rows[1002]["team"]["role_text"], "Defensive quality control coach")


ROLE_LINE_PAGE = """{{Infobox NFL biography
| pastcoaching =
* St. Louis Rams (1999–2005)<br />- Offensive coordinator (1999)<br />- Head coach (2000–2005)
* [[Fresno State Bulldogs football|Fresno State]] (1987-1989)<br>Outside linebackers coach<br>Co-defensive coordinator (1988)
* [[Mount Airy High School|Mount Airy (NC)]] <br>Head coach (1966–1968)
* [[University of Alabama|Alabama]] (2012–2014) <br> Assistant offensive line coach (2012 CFB Champion as Asst. Coach)
* Philadelphia Eagles ({{NFL Year|2020}})<br>Senior offensive consultant<ref>{{cite web |title=x (2019) |date=March 5, 2020}}</ref>
}}
"""


class DatedRoleLineTests(unittest.TestCase):
    """Role lines after a break that state their own dates are their own rows (found by the Attempt 5 census)."""

    def setUp(self) -> None:
        self.rows = {row["index"]: row for row in ci.career_rows(ROLE_LINE_PAGE)["rows"]}

    def summary(self, index: int) -> tuple:
        row = self.rows[index]
        return ((row["team"] or {}).get("role_text"), row["date_basis"],
                [(i["start"], i["end"]) for i in row["intervals"]])

    def test_each_dated_role_line_is_its_own_row(self) -> None:
        self.assertEqual(self.summary(1001), (None, "ITEM_DATE_IN_BALANCED_PARENTHESES", [(1999, 2005)]))
        self.assertEqual(self.summary(100101), ("Offensive coordinator", "ROLE_LINE_DATE_IN_BALANCED_PARENTHESES",
                                                [(1999, 1999)]))
        self.assertEqual(self.summary(100102), ("Head coach", "ROLE_LINE_DATE_IN_BALANCED_PARENTHESES",
                                                [(2000, 2005)]))
        self.assertEqual(self.rows[1001]["team"]["role_basis"], "LIST_ROW_STATES_NO_ROLE")
        for index in (100101, 100102):
            row = self.rows[index]
            self.assertEqual((row["role_line_of_index"], row["team"]["employer_display"]), (1001, "St. Louis Rams"))
            self.assertEqual(ROLE_LINE_PAGE[row["years_span"][0]:row["years_span"][1]], row["years_raw"])
            self.assertEqual(ROLE_LINE_PAGE[row["team_span"][0]:row["team_span"][1]], row["team_raw"])

    def test_an_undated_role_line_inherits_and_names_the_employer_line(self) -> None:
        self.assertEqual(self.summary(100201), ("Outside linebackers coach", "INHERITED_FROM_PARENT_ITEM", [(1987, 1989)]))
        self.assertEqual(self.rows[100201]["date_parent"]["row_index"], 1002)
        self.assertEqual(self.summary(100202), ("Co-defensive coordinator", "ROLE_LINE_DATE_IN_BALANCED_PARENTHESES",
                                                [(1988, 1988)]))
        self.assertEqual(self.summary(100301), ("Head coach", "ROLE_LINE_DATE_IN_BALANCED_PARENTHESES", [(1966, 1968)]))
        self.assertEqual(self.summary(1003)[1:], ("NO_DATE_STATED", []))

    def test_leading_linked_and_adjacent_dates_are_the_lines_own(self) -> None:
        page = """{{Infobox NFL biography
| pastcoaching =
* [[San Antonio Gunslingers (USFL team)|San Antonio Bulls]] ([[American Football Association (1977–1983)#1983|1983]]–{{USFL Year|1984}})
* {{NFL Year|1978}} [[New York Jets]] (LB/ST)
* {{AFL Year|1987}}–{{AFL Year|1990}} [[Tampa Bay Storm|Pittsburgh Gladiators]] (HC)
* [[Cleveland Browns]] ({{NFL Year|2002}}); ({{NFL Year|2004}})
* [[Iowa Hawkeyes (1990s)|Iowa]] (OC)<ref>{{cite web|title=Hire (2010)}}</ref>
}}
"""
        rows = {row["index"]: row for row in ci.career_rows(page)["rows"]}
        read = {index: ([(i["start"], i["end"]) for i in row["intervals"]], (row["team"] or {}).get("role_text"))
                for index, row in rows.items()}
        # A parenthesis inside a link belongs to the link: the date is the display year and the season template.
        self.assertEqual(read[1001], ([(1983, 1984)], None))
        self.assertEqual(read[1002], ([(1978, 1978)], "LB/ST"))
        self.assertEqual(read[1003], ([(1987, 1990)], "HC"))
        self.assertEqual(read[1004], ([(2002, 2002), (2004, 2004)], None))
        # A decade inside a link and a year inside a reference are not the line's date.
        self.assertEqual(read[1005], ([], "OC"))
        for row in rows.values():
            if row["years_span"]:
                self.assertEqual(page[row["years_span"][0]:row["years_span"][1]], row["years_raw"])

    def test_list_template_items_are_lines_and_a_template_list_is_read(self) -> None:
        page = """{{Infobox NFL biography
| pastcoaching = {{bulleted list
|[[Toledo Rockets football|Toledo]] (1966)<br/>Graduate assistant
|[[Oakland Invaders]] ({{USFL Year|1983}}–{{USFL Year|1985}})<br/>Defensive coordinator
}}
| pastexecutive =
* {{Ubl|Purdue (1943)|Assistant coach}}
* {{ubl|[[Denver Broncos]] (1972–1977; [[Position coach|LB coach]])|[[Houston Oilers]] (1978–1982; [[Position coach|DB coach]])}}
}}
"""
        rows = ci.career_rows(page)["rows"]
        read = {(row["family"], row["index"]): ((row["team"] or {}).get("employer_display"),
                                                 (row["team"] or {}).get("role_text"),
                                                 [(i["start"], i["end"]) for i in row["intervals"]]) for row in rows}
        # A whole field written as one {{bulleted list}} was read as no rows at all.
        self.assertEqual(read[("COACHING", 1001)], ("Toledo", "Graduate assistant", [(1966, 1966)]))
        self.assertEqual(read[("COACHING", 1002)], ("Oakland Invaders", "Defensive coordinator", [(1983, 1985)]))
        # "{{Ubl|Purdue (1943)|Assistant coach}}" was the employer "Purdue |Assistant coach" with no role.
        self.assertEqual(read[("ADMINISTRATIVE", 1001)], ("Purdue", "Assistant coach", [(1943, 1943)]))
        # Two employers in one list template: each keeps its own date; the words beside a date are kept
        # verbatim as an unresolved role, never "no role stated".
        self.assertEqual(read[("ADMINISTRATIVE", 1002)][0::2], ("Denver Broncos", [(1972, 1977)]))
        self.assertEqual(read[("ADMINISTRATIVE", 100201)][0::2], ("Houston Oilers", [(1978, 1982)]))
        by_index = {(row["family"], row["index"]): row for row in rows}
        for key in (("ADMINISTRATIVE", 1002), ("ADMINISTRATIVE", 100201)):
            self.assertEqual(by_index[key]["team"]["role_basis"], "UNRESOLVED_PARENTHETICAL")
            self.assertEqual(by_index[key]["team"]["unresolved_parentheticals"][-1]["basis"],
                             "WORDS_BESIDE_THE_DATE_IN_ITS_PARENTHETICAL")
        for row in rows:
            self.assertEqual(page[row["team_span"][0]:row["team_span"][1]], row["team_raw"])
            if row["years_span"]:
                self.assertEqual(page[row["years_span"][0]:row["years_span"][1]], row["years_raw"])

    def test_a_template_block_beside_bullets_and_literal_text_in_a_revision(self) -> None:
        page = """{{Infobox NFL biography
| pastteams =
* [[Philadelphia Eagles]]<nowiki> ({{NFL Year|(1990-1991)</nowiki>
* [[Indianapolis Colts]] ({{NFL Year|1992}})*
| pastcoaching = {{bulleted list
| [[San Antonio Riders]] (1992)<br>Assistant
| [[Seattle Seahawks]] ({{nfly|1999}}–{{nfly|2007}})<br>Running backs coach
}}
* [[West Georgia Wolves football|West Georgia]] (2025–present) <br> Running backs coach
| highlights = <!-- a | bar and {{ braces in a comment -->
* [[World Bowl]] champion
}}
"""
        rows = {(row["family"], row["index"]): row for row in ci.career_rows(page)["rows"]}
        # Bullet lines keep their numbers; the template block's items follow them.
        self.assertEqual(rows[("COACHING", 1001)]["team"]["employer_display"], "West Georgia")
        self.assertEqual([(i["start"], i["end"]) for i in rows[("COACHING", 1003)]["intervals"]], [(1999, 2007)])
        # <nowiki> text is literal: it neither opens a template nor swallows the parameters after it.
        self.assertEqual(sorted(k for k in rows if k[0] == "PLAYING"), [("PLAYING", 1001), ("PLAYING", 1002)])
        self.assertEqual(rows[("PLAYING", 1001)]["intervals"], [])
        self.assertEqual([(i["start"], i["end"]) for i in rows[("PLAYING", 1002)]["intervals"]], [(1992, 1992)])
        for row in rows.values():
            self.assertEqual(page[row["team_span"][0]:row["team_span"][1]], row["team_raw"])

    def test_a_commented_out_infobox_is_not_the_revisions_statement(self) -> None:
        page = """{{Infobox college coach
| coach_years1 = 2001–2004
| coach_team1 = [[Iowa Hawkeyes football|Iowa]] (OC)
}}
<!--
{{Infobox NFL biography
| pastcoaching =
* [[Chicago Bears]] ({{NFL Year|2008|2009}})
}}
-->
"""
        parsed = ci.career_rows(page)
        self.assertEqual(parsed["infoboxes"], ["college coach"])
        self.assertEqual([(row["family"], row["index"]) for row in parsed["rows"]], [("COACHING", 1)])

    def test_annotations_and_reference_dates_do_not_split_a_row(self) -> None:
        self.assertEqual(self.summary(1004), ("Assistant offensive line coach (2012 CFB Champion as Asst. Coach)",
                                              "ITEM_DATE_IN_BALANCED_PARENTHESES", [(2012, 2014)]))
        self.assertEqual(self.summary(1005), ("Senior offensive consultant", "ITEM_DATE_IN_BALANCED_PARENTHESES",
                                              [(2020, 2020)]))
        self.assertFalse([i for i in self.rows if i > 100000 and i // ci.ROLE_LINE_INDEX_FACTOR in (1004, 1005)])


#: The 33 titles of the manager's Attempt 4 defensive passing-game screen (CAREER_SEMANTIC_CENSUS.json).
MANAGER_DEFENSIVE_TITLES = (
    "Defensive backs coach & defensive passing game coordinator",
    "Defensive backs coach/Defensive passing game coordinator",
    "Special teams / defensive passing game coordinator",
    "Defensive pass game coordinator", "Defensive pass game coordinator & safeties coach",
    "Defensive passing game coordinator & secondary coach", "Cornerbacks coach & defensive passing game coordinator",
    "Defensive pass game coordinator & Safeties coach", "Defensive pass game coordinator & defensive backs coach",
    "Defensive pass game coordinator & cornerbacks coach", "Defensive pass game coordinator & secondary coach",
    "Assistant head coach & defensive pass game coordinator",
    "Assistant head coach, special teams coordinator, & defensive pass game coordinator",
    "Defensive pass game coordinator and cornerbacks coach", "Defensive passing game coordinator & defensive backs coach",
    "Secondary coach & Defensive pass game coordinator", "Defensive Pass Game Coordinator/DB",
    "Defensive passing game coordinator", "Secondary/Defensive pass game coordinator",
    "Secondaries coach & defensive pass game coordinator", "Defensive passing game coordinator/secondary coach",
    "defensive passing game coordinator",
)


def unit(title: str, role: str) -> tuple[str, str]:
    found = {a["role"]: a for a in staff_record.assignments_v37(title)}
    return found[role]["unit"], found[role]["unit_basis"]


class RoleUnitTests(unittest.TestCase):
    """A side-dependent role takes its unit only from the words that modify it."""

    def test_every_manager_title_is_defense(self) -> None:
        for title in MANAGER_DEFENSIVE_TITLES:
            with self.subTest(title=title):
                self.assertEqual(unit(title, "pass_game_coordinator"), ("DEFENSE", "SIDE_STATED_FOR_THE_ROLE"))

    def test_controls(self) -> None:
        self.assertEqual(unit("Offensive passing game coordinator & quarterbacks coach", "pass_game_coordinator"),
                         ("OFFENSE", "SIDE_STATED_FOR_THE_ROLE"))
        # Nothing modifies the coordinator; the quarterbacks coach beside it does not lend it a side.
        self.assertEqual(unit("Passing game coordinator & quarterbacks coach", "pass_game_coordinator"),
                         ("UNKNOWN", "SIDE_NOT_STATED_FOR_THE_ROLE"))
        self.assertEqual(unit("Offensive and defensive quality control", "quality_control"),
                         ("UNKNOWN", "BOTH_SIDES_STATED_FOR_THE_ROLE"))
        self.assertEqual(unit("Analyst (Defense)", "analyst"), ("DEFENSE", "SIDE_STATED_FOR_THE_ROLE"))
        self.assertEqual(unit("Offensive quality control", "quality_control"), ("OFFENSE", "SIDE_STATED_FOR_THE_ROLE"))
        # A side on another role in the title is not borrowed.
        self.assertEqual(unit("Defensive line coach & quality control", "quality_control"),
                         ("UNKNOWN", "SIDE_NOT_STATED_FOR_THE_ROLE"))

    def test_intrinsic_units_are_unchanged(self) -> None:
        self.assertEqual(unit("Offensive coordinator", "offensive_coordinator"), ("OFFENSE", "INTRINSIC_ROLE_UNIT"))
        self.assertEqual(unit("Defensive coordinator", "defensive_coordinator"), ("DEFENSE", "INTRINSIC_ROLE_UNIT"))
        self.assertTrue(staff_record.TAXONOMY_VERSION.startswith("BAS-COACH-ROLE-TAXONOMY-v37.5-"))
        self.assertFalse(any(a["play_caller_inferred"] for a in staff_record.assignments_v37(MANAGER_DEFENSIVE_TITLES[0])))


# ------------------------------------------------------------------ successor contract

REVISION_TEXT = "* [[Iowa]] (2009–2010)\n* [[Ohio]] (2011)\n"
IDS = (1, 2)


def _pid(n: int) -> str:
    return f"R37-05:1:1:COACHING:{n}:0"


def _a4(n: int) -> str:
    return f"C37A04:1:1:COACHING:{n}:0"


def _a5(n: int) -> str:
    return f"C37A05:1:1:COACHING:{n}:0"


def _table(path: Path, table: str, columns: tuple[str, ...], rows: list[dict]) -> None:
    conn = sqlite3.connect(path)
    conn.execute(f"CREATE TABLE {table} ({', '.join(chr(34) + c + chr(34) for c in columns)})")
    for row in rows:
        conn.execute(f"INSERT INTO {table} VALUES ({', '.join('?' for _ in columns)})", [row.get(c) for c in columns])
    conn.commit()
    conn.close()


class A05SuccessorContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.raw = self.root / "raw.json"
        self.raw.write_bytes(json.dumps({"query": {"pages": {"1": {"pageid": 1, "revisions": [
            {"revid": 1, "slots": {"main": {"*": REVISION_TEXT}}}]}}}}).encode("utf-8"))
        self.raw_sha = hashlib.sha256(self.raw.read_bytes()).hexdigest()
        self.text_sha = hashlib.sha256(REVISION_TEXT.encode("utf-8")).hexdigest()
        base = {"pageid": 1, "revision": "1", "family": "COACHING", "interval_index": 0, "ongoing": 0,
                "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": 0, "raw_file": str(self.raw),
                "raw_file_sha256": self.raw_sha, "assignments": "[]"}
        self.old = [{**base, "episode_id": _pid(n), "row_index": n, "start": 2009, "end": 2009} for n in IDS]
        self.predecessor = self.root / "predecessor.sqlite"
        _table(self.predecessor, cs.PREDECESSOR_TABLE, cs.PREDECESSOR_COLUMNS, self.old)
        self.a4_rows = [{**base, "episode_id": _a4(n), "row_index": n, "start": 2009, "end": 2009,
                         "wikitext_sha256": self.text_sha} for n in IDS]
        self.a4 = self.root / "a04.sqlite"
        _table(self.a4, cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, self.a4_rows)
        team = "[[Iowa]] "
        years_start = REVISION_TEXT.index("2009–2010")
        self.episodes = [{**base, "episode_id": _a5(n), "row_index": n, "start": 2009, "end": 2010 if n == 1 else 2011,
                          "wikitext_sha256": self.text_sha, "lineage_state": cs.DERIVED,
                          "disposition": cs.CORRECTED, "predecessor_episode_ids": json.dumps([_pid(n)]),
                          "a04_episode_ids": json.dumps([_a4(n)]), "a04_lineage_state": cs.A04_DERIVED,
                          "a04_disposition": cs.CORRECTED, "date_basis": "ITEM_DATE_IN_BALANCED_PARENTHESES",
                          "uncertainty_classes": "[]"} for n in IDS]
        self.episodes[0].update({"team_raw": team.strip(), "team_char_span": json.dumps([2, 2 + len(team.strip())]),
                                 "years_raw": "2009–2010",
                                 "years_char_span": json.dumps([years_start, years_start + len("2009–2010")])})
        self.dispositions = [{"predecessor_episode_id": _pid(n), "disposition": cs.CORRECTED,
                              "successor_episode_ids": json.dumps([_a5(n)]), "changed_fields": "{}",
                              "predecessor_row_sha256": cs.predecessor_row_digest(self.old[n - 1]), "screens": "[]",
                              "reason": "fixture"} for n in IDS]
        self.mapping = [{"a04_episode_id": _a4(n), "disposition": cs.CORRECTED, "a05_episode_ids": json.dumps([_a5(n)]),
                         "changed_fields": "{}", "a04_row_sha256": cs.episode_row_digest(self.a4_rows[n - 1]),
                         "screens": "[]", "reason": "fixture"} for n in IDS]

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def successor(self, name: str, episodes=None, dispositions=None, mapping=None, **overrides: str) -> Path:
        """Write a successor and seal it: every ledger is recomputed, so only lineage can refuse it."""

        episodes = self.episodes if episodes is None else episodes
        dispositions = self.dispositions if dispositions is None else dispositions
        mapping = self.mapping if mapping is None else mapping
        path = self.root / name
        _table(path, cs.A05_EPISODE_TABLE, cs.A05_EPISODE_COLUMNS, episodes)
        _table(path, cs.A05_DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, dispositions)
        _table(path, cs.A05_FROM_A04_TABLE, cs.A04_MAP_COLUMNS, mapping)
        conn = sqlite3.connect(path)
        conn.execute(f"CREATE TABLE {cs.IDENTITY_TABLE} (key TEXT, value TEXT)")
        identity = {"format_version": cs.A05_FORMAT_VERSION, "successor_version": cs.A05_SUCCESSOR_VERSION,
                    "predecessor_database_sha256": cs.sha256_file(self.predecessor),
                    "predecessor_table": cs.PREDECESSOR_TABLE, "predecessor_row_count": str(len(self.old)),
                    "a04_successor_path": str(self.a4), "a04_successor_sha256": cs.sha256_file(self.a4),
                    "a04_successor_row_count": str(len(self.a4_rows)),
                    "default_activation": cs.NOT_ACTIVATED, "acceptance_state": cs.NOT_ACCEPTED,
                    "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": "0"}
        for table, columns, key in ((cs.A05_EPISODE_TABLE, cs.A05_EPISODE_COLUMNS, "episode_id"),
                                    (cs.A05_DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, "predecessor_episode_id"),
                                    (cs.A05_FROM_A04_TABLE, cs.A04_MAP_COLUMNS, "a04_episode_id")):
            digest, count = cs.table_ledger(conn, table, columns, key)
            identity[f"ledger::{table}::sha256"], identity[f"ledger::{table}::rows"] = digest, str(count)
        identity.update(overrides)
        conn.executemany(f"INSERT INTO {cs.IDENTITY_TABLE} VALUES (?, ?)", sorted(identity.items()))
        conn.commit()
        conn.close()
        return path

    def attach(self, successor: Path, **kw):
        conn = sqlite3.connect(self.predecessor.resolve().as_uri() + "?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            return cs.attach_successor(conn, successor, database=self.predecessor, **kw), conn
        except Exception:
            conn.close()
            raise

    def refused(self, code: str, successor: Path, **kw) -> str:
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            _binding, conn = self.attach(successor, **kw)
            conn.close()
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        return str(caught.exception)

    def served(self, successor: Path) -> list[dict]:
        _binding, conn = self.attach(successor)
        try:
            return [dict(r) for r in conn.execute(f"SELECT * FROM {cs.VIEW_NAME} ORDER BY episode_id")]
        finally:
            conn.close()

    # -- accepted

    def test_a_sealed_successor_attaches_with_lineage_proved_from_its_rows(self) -> None:
        binding, conn = self.attach(self.successor("ok.sqlite"))
        try:
            self.assertEqual((binding["format_version"], binding["episode_table"], binding["a04_table"]),
                             (cs.A05_FORMAT_VERSION, cs.A05_EPISODE_TABLE, cs.A05_FROM_A04_TABLE))
            lineage = binding["lineage_proved_independently_of_the_ledgers"]
            self.assertEqual((lineage["edges"], lineage["a04_edges"], lineage["a04_file_check"]),
                             (2, 2, "A04_FILE_IDENTITY_SET_EQUAL"))
            self.assertIsNone(binding["superseded_semantics"])
            rows = [dict(r) for r in conn.execute(f"SELECT * FROM {cs.VIEW_NAME} ORDER BY episode_id")]
        finally:
            conn.close()
        verified = cs.RawBytesVerifier().verify(rows[0])
        self.assertEqual(verified, {"raw_file_sha256": True, "wikitext_sha256": True, "team_char_span": True,
                                    "years_char_span": True})
        self.assertEqual(cs.RawBytesVerifier().verify(rows[1])["years_char_span"], "NOT_RECORDED")

    def test_an_added_row_is_accepted_only_as_added(self) -> None:
        added = {**self.episodes[1], "episode_id": _a5(3), "row_index": 3, "predecessor_episode_ids": "[]",
                 "lineage_state": cs.ADDED_STATES[cs.A05_FORMAT_VERSION], "disposition": "ADDED",
                 "a04_episode_ids": "[]", "a04_lineage_state": cs.A04_ADDED, "a04_disposition": "ADDED_IN_A05"}
        binding, conn = self.attach(self.successor("added.sqlite", episodes=self.episodes + [added]))
        conn.close()
        self.assertEqual(binding["lineage_proved_independently_of_the_ledgers"]["episodes_added_without_predecessor"], 1)
        claimed = {**added, "lineage_state": cs.DERIVED}
        self.refused(cs.REFUSED_INCOMPATIBLE, self.successor("claimed.sqlite", episodes=self.episodes + [claimed]))

    def test_the_a4_format_still_attaches_and_is_named_superseded(self) -> None:
        path = self.root / "a4-format.sqlite"
        episodes = [{**row, "predecessor_episode_ids": json.dumps([_pid(n)]), "lineage_state": cs.DERIVED,
                     "disposition": cs.UNCHANGED} for n, row in zip(IDS, self.a4_rows)]
        dispositions = [{**row, "disposition": cs.UNCHANGED, "successor_episode_ids": json.dumps([_a4(n)])}
                        for n, row in zip(IDS, self.dispositions)]
        _table(path, cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, episodes)
        _table(path, cs.DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, dispositions)
        conn = sqlite3.connect(path)
        conn.execute(f"CREATE TABLE {cs.IDENTITY_TABLE} (key TEXT, value TEXT)")
        identity = {"format_version": cs.FORMAT_VERSION, "successor_version": cs.SUCCESSOR_VERSION,
                    "predecessor_database_sha256": cs.sha256_file(self.predecessor),
                    "predecessor_table": cs.PREDECESSOR_TABLE, "predecessor_row_count": str(len(self.old)),
                    "default_activation": cs.NOT_ACTIVATED, "acceptance_state": cs.NOT_ACCEPTED,
                    "evidence_class": cs.EVIDENCE_CLASS, "pit_admitted": "0"}
        for table, columns, key in ((cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, "episode_id"),
                                    (cs.DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, "predecessor_episode_id")):
            digest, count = cs.table_ledger(conn, table, columns, key)
            identity[f"ledger::{table}::sha256"], identity[f"ledger::{table}::rows"] = digest, str(count)
        conn.executemany(f"INSERT INTO {cs.IDENTITY_TABLE} VALUES (?, ?)", sorted(identity.items()))
        conn.commit()
        conn.close()
        binding, conn = self.attach(path)
        conn.close()
        self.assertEqual((binding["episode_table"], binding["a04_table"]), (cs.EPISODE_TABLE, None))
        self.assertIn("MF37A04-03/04", binding["superseded_semantics"])

    # -- the manager's resealed challenge and its variants

    def test_a_resealed_deleted_row_is_a_dangling_reference(self) -> None:
        text = self.refused(cs.REFUSED_DANGLING, self.successor("deleted.sqlite", episodes=self.episodes[1:]))
        self.assertIn(_a5(1), text)

    def test_nulled_raw_fields_are_refused_at_attach(self) -> None:
        for field, value in (("raw_file_sha256", None), ("raw_file", None), ("wikitext_sha256", ""),
                             ("raw_file_sha256", "not-a-digest")):
            with self.subTest(field=field, value=value):
                episodes = [{**self.episodes[0], field: value}, self.episodes[1]]
                self.refused(cs.REFUSED_RAW_EVIDENCE_ABSENT, self.successor(f"raw-{field}-{value}.sqlite", episodes))

    def test_a_self_consistent_rewrite_is_a_different_file_under_the_delivered_pin(self) -> None:
        delivered = self.successor("delivered.sqlite")
        pin = cs.sha256_file(delivered)
        dispositions = [{**self.dispositions[0], "disposition": cs.NOT_PRODUCED, "successor_episode_ids": "[]"},
                        self.dispositions[1]]
        dangling_a04 = self.successor("rewrite-a.sqlite", episodes=self.episodes[1:], dispositions=dispositions)
        self.refused(cs.REFUSED_A04_MAPPING, dangling_a04)
        mapping = [{**self.mapping[0], "disposition": cs.NOT_PRODUCED, "a05_episode_ids": "[]"}, self.mapping[1]]
        rewrite = self.successor("rewrite-b.sqlite", episodes=self.episodes[1:], dispositions=dispositions,
                                 mapping=mapping)
        self.refused(cs.REFUSED_FILE_DIGEST, rewrite, expected_sha256=pin)

    # -- lineage refusals by cause

    def test_missing_extra_and_duplicate_rows_are_refused(self) -> None:
        self.refused(cs.REFUSED_COVERAGE, self.successor("missing.sqlite", dispositions=self.dispositions[:1]))
        extra = {**self.dispositions[1], "predecessor_episode_id": _pid(9)}
        self.refused(cs.REFUSED_COVERAGE, self.successor("extra.sqlite", dispositions=self.dispositions + [extra]))
        self.refused(cs.REFUSED_COVERAGE, self.successor("duplicate.sqlite", episodes=self.episodes + self.episodes[:1]))

    def test_an_identity_that_is_not_its_rows_locator_is_refused(self) -> None:
        moved = [{**self.episodes[0], "row_index": 7}, self.episodes[1]]
        self.refused(cs.REFUSED_INVALID_IDENTITY, self.successor("moved.sqlite", episodes=moved))

    def test_malformed_lineage_is_refused(self) -> None:
        for value in ("not json", json.dumps(_pid(1)), json.dumps([_pid(1), _pid(1)])):
            with self.subTest(value=value):
                episodes = [{**self.episodes[0], "predecessor_episode_ids": value}, self.episodes[1]]
                self.refused(cs.REFUSED_MALFORMED_LINEAGE, self.successor(f"malformed-{len(value)}.sqlite", episodes))

    def test_a_reference_to_a_row_that_does_not_exist_is_refused(self) -> None:
        dispositions = [{**self.dispositions[0], "successor_episode_ids": json.dumps([_a5(9)])}, self.dispositions[1]]
        self.refused(cs.REFUSED_DANGLING, self.successor("dangling-forward.sqlite", dispositions=dispositions))
        episodes = [{**self.episodes[0], "predecessor_episode_ids": json.dumps([_pid(9)])}, self.episodes[1]]
        self.refused(cs.REFUSED_DANGLING, self.successor("dangling-back.sqlite", episodes=episodes))

    def test_an_edge_stated_one_way_only_is_refused(self) -> None:
        episodes = [{**self.episodes[0], "predecessor_episode_ids": json.dumps([_pid(1), _pid(2)])}, self.episodes[1]]
        self.refused(cs.REFUSED_NONRECIPROCAL, self.successor("one-way.sqlite", episodes=episodes))

    def test_a_disposition_that_contradicts_its_edges_is_refused(self) -> None:
        not_produced = [{**self.dispositions[0], "disposition": cs.NOT_PRODUCED}, self.dispositions[1]]
        self.refused(cs.REFUSED_INCOMPATIBLE, self.successor("np.sqlite", dispositions=not_produced))
        wrong_column = [{**self.episodes[0], "disposition": cs.UNCHANGED}, self.episodes[1]]
        self.refused(cs.REFUSED_INCOMPATIBLE, self.successor("column.sqlite", episodes=wrong_column))
        unknown = [{**self.dispositions[0], "disposition": "FIXED"}, self.dispositions[1]]
        self.refused(cs.REFUSED_COVERAGE, self.successor("unknown.sqlite", dispositions=unknown))

    def test_a_broken_attempt4_mapping_is_refused(self) -> None:
        self.refused(cs.REFUSED_A04_MAPPING, self.successor("a4-missing.sqlite", mapping=self.mapping[:1]))
        foreign = [self.mapping[0], {**self.mapping[1], "a04_episode_id": _a4(7)}]
        episodes = [self.episodes[0], {**self.episodes[1], "a04_episode_ids": json.dumps([_a4(7)])}]
        self.refused(cs.REFUSED_A04_MAPPING, self.successor("a4-foreign.sqlite", episodes=episodes, mapping=foreign))
        column = [{**self.episodes[0], "a04_disposition": cs.UNCHANGED}, self.episodes[1]]
        self.refused(cs.REFUSED_A04_MAPPING, self.successor("a4-column.sqlite", episodes=column))
        sealed = self.successor("a4-changed.sqlite")
        conn = sqlite3.connect(self.a4)
        conn.execute(f"UPDATE {cs.EPISODE_TABLE} SET \"end\" = 2015")
        conn.commit()
        conn.close()
        self.refused(cs.REFUSED_A04_MAPPING, sealed)

    def test_an_absent_attempt4_file_is_named_not_assumed(self) -> None:
        successor = self.successor("a4-absent.sqlite", a04_successor_path=str(self.root / "gone.sqlite"))
        binding, conn = self.attach(successor)
        conn.close()
        self.assertEqual(binding["lineage_proved_independently_of_the_ledgers"]["a04_file_check"],
                         "A04_FILE_ABSENT_SET_EQUALITY_NOT_CHECKED")

    def test_tampered_tables_and_versions_are_refused(self) -> None:
        successor = self.successor("tampered.sqlite")
        conn = sqlite3.connect(successor)
        conn.execute(f"UPDATE {cs.A05_FROM_A04_TABLE} SET disposition = '{cs.UNCHANGED}'")
        conn.commit()
        conn.close()
        self.refused(cs.REFUSED_LEDGER, successor)
        self.refused(cs.REFUSED_VERSION, self.successor("version.sqlite", successor_version=cs.SUCCESSOR_VERSION))

    # -- raw evidence when a row is served

    def test_changed_removed_or_misplaced_raw_evidence_is_refused_when_served(self) -> None:
        rows = self.served(self.successor("served.sqlite"))
        wrong_text = {**rows[0], "wikitext_sha256": "0" * 64}
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            cs.RawBytesVerifier().verify(wrong_text)
        self.assertEqual(caught.exception.code, cs.REFUSED_RAW_TEXT)
        misplaced = {**rows[0], "years_char_span": json.dumps([0, 4])}
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            cs.RawBytesVerifier().verify(misplaced)
        self.assertEqual(caught.exception.code, cs.REFUSED_RAW_SPAN)
        self.raw.write_bytes(b'{"raw": "changed"}')
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            cs.verify_raw_bytes(rows)
        self.assertEqual(caught.exception.code, cs.REFUSED_RAW)
        self.raw.unlink()
        with self.assertRaises(cs.CareerSuccessorError) as caught:
            cs.verify_raw_bytes(rows)
        self.assertEqual(caught.exception.code, cs.REFUSED_RAW_FILE_ABSENT)


if __name__ == "__main__":
    unittest.main()
