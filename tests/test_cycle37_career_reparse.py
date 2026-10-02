"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-05: career rows read from the revision's own infobox. Each fixture is
wikitext shaped like the cached pages (the Bill Anderson and Jim Tressel
shapes in particular) and pins one rule; none is a claim about a person.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle37 import career_infobox as ci  # noqa: E402

COACH_BOX = """{{Infobox college coach
| name = A Coach
| player_years1 = 1947–1949
| player_team1 = [[Pepperdine Waves football|Pepperdine]]
| coach_years1 = 1953–1966
| coach_team1 = [[Stamford High School (Texas)|Stamford HS (TX)]] (assistant)
| coach_years2 = 1967–1968
| coach_team2 = Stamford HS (TX)
| coach_years3 = 1984–85
| coach_team3 = [[Howard Payne Yellow Jackets football|Howard Payne]] ([[Offensive coordinator|OC]])
| coach_years4 = 1988, 1990
| coach_team4 = Howard Payne
| coach_years5 = 2019–present
| coach_team5 = [[Miami RedHawks football|Miami (OH)]] (QB/WR)
}}
'''A Coach''' was a coach."""


class InfoboxRows(unittest.TestCase):
    def setUp(self) -> None:
        self.result = ci.career_rows(COACH_BOX)
        self.rows = {(r["family"], r["index"]): r for r in self.result["rows"]}

    def test_a_location_qualifier_is_not_a_title(self) -> None:
        row = self.rows[("COACHING", 2)]
        self.assertEqual(row["team"]["employer_display"], "Stamford HS (TX)")
        self.assertEqual(row["team"]["employer_qualifiers"], ["TX"])
        self.assertIsNone(row["team"]["role_text"])
        self.assertEqual(row["team"]["role_basis"], "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL")

    def test_the_role_parenthetical_and_the_link_are_kept_apart(self) -> None:
        team = self.rows[("COACHING", 3)]["team"]
        self.assertEqual((team["employer_display"], team["role_text"]), ("Howard Payne", "OC"))
        self.assertEqual(team["employer_link_target"], "Howard Payne Yellow Jackets football")
        self.assertEqual(self.rows[("COACHING", 3)]["intervals"][0]["end"], 1985)

    def test_an_unlinked_repeat_inherits_the_earlier_link(self) -> None:
        team = self.rows[("COACHING", 4)]["team"]
        self.assertEqual(team["employer_link_target"], "Howard Payne Yellow Jackets football")
        self.assertEqual(team["employer_link_basis"], "SAME_DISPLAY_LINKED_EARLIER_ON_THIS_PAGE")
        self.assertEqual([(i["start"], i["end"]) for i in self.rows[("COACHING", 4)]["intervals"]],
                         [(1988, 1988), (1990, 1990)])

    def test_present_is_an_open_interval(self) -> None:
        interval = self.rows[("COACHING", 5)]["intervals"][0]
        self.assertEqual((interval["start"], interval["end"], interval["ongoing"]), (2019, None, True))
        self.assertEqual(self.rows[("COACHING", 5)]["team"]["employer_display"], "Miami (OH)")

    def test_playing_years_are_typed_apart(self) -> None:
        self.assertEqual(self.rows[("PLAYING", 1)]["family"], "PLAYING")

    def test_spans_are_the_revisions_own_text(self) -> None:
        for row in self.result["rows"]:
            start, end = row["team_span"]
            self.assertEqual(COACH_BOX[start:end], row["team_raw"])


class OtherShapes(unittest.TestCase):
    def test_a_career_box_embedded_as_a_module_is_read(self) -> None:
        text = ("{{Infobox officeholder\n| name = X\n| module = {{Infobox college coach\n| embed = yes\n"
                "| coach_years1 = 1975–1978\n| coach_team1 = [[Akron Zips football|Akron]] ([[Graduate assistant|GA]])\n"
                "}}\n}}")
        rows = ci.career_rows(text)["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["infobox"], "college coach")
        self.assertEqual(rows[0]["team"]["role_text"], "GA")

    def test_a_bulleted_career_list_is_read(self) -> None:
        text = ("{{Infobox NFL biography\n| pastcoaching =\n"
                "* [[Rutgers Scarlet Knights football|Rutgers]] (1997–1998)<br>Running backs coach\n"
                "* [[Buffalo Bills]] ({{nfly|2000}})<br>Running backs coach\n"
                "| pastteams =\n* [[Kansas City Chiefs]] * ({{nfly|1988}})\n}}")
        rows = ci.career_rows(text)["rows"]
        coaching = [r for r in rows if r["family"] == "COACHING"]
        self.assertEqual([r["team"]["employer_display"] for r in coaching], ["Rutgers", "Buffalo Bills"])
        self.assertEqual(coaching[1]["intervals"][0]["start"], 2000)
        self.assertEqual(coaching[0]["team"]["role_text"], "Running backs coach")
        self.assertEqual(coaching[1]["employer_kind"], "PROFESSIONAL")
        playing = [r for r in rows if r["family"] == "PLAYING"][0]
        self.assertEqual(playing["team"]["employer_display"], "Kansas City Chiefs")

    def test_employer_kinds(self) -> None:
        for raw, kind in (("[[Skyline High School (Washington)|Skyline High School]]", "HIGH_SCHOOL"),
                          ("[[Philadelphia Eagles]]", "PROFESSIONAL"),
                          ("[[Eastern Michigan Eagles football|Eastern Michigan]]", "COLLEGE_OR_OTHER_FOOTBALL_PROGRAM"),
                          ("Stamford HS (TX)", "HIGH_SCHOOL")):
            with self.subTest(raw=raw):
                self.assertEqual(ci.employer_kind(ci.parse_team(raw)), kind)

    def test_position_abbreviations_are_roles_and_state_codes_are_places(self) -> None:
        for raw, display, role in (("Pacific (CA) (OLB)", "Pacific (CA)", "OLB"),
                                   ("Oregon State (DE)", "Oregon State", "DE"),
                                   ("Georgia Tech (Chief of Staff)", "Georgia Tech", "Chief of Staff"),
                                   ("Mississippi State (S)", "Mississippi State", "S"),
                                   ("Akron (GA)", "Akron", "GA"),
                                   ("Howard (DC)", "Howard", "DC"),
                                   ("Howard (AL)", "Howard (AL)", None),
                                   ("Cabrillo HS (CA) (DC)", "Cabrillo HS (CA)", "DC"),
                                   ("Indiana (QC)", "Indiana", "QC"),
                                   ("Kansas (Nickels)", "Kansas", "Nickels"),
                                   ("Dartmouth (adviser)", "Dartmouth", "adviser"),
                                   ("Florida (DQC)", "Florida", "DQC"),
                                   ("Wisconsin (compliance)", "Wisconsin", "compliance"),
                                   ("Akron (1st stint)", "Akron (1st stint)", None),
                                   ("Smyrna HS (DE) (DC)", "Smyrna HS (DE)", "DC"),
                                   ("Miami (OH) (DE)", "Miami (OH)", "DE")):
            with self.subTest(raw=raw):
                team = ci.parse_team(raw)
                self.assertEqual((team["employer_display"], team["role_text"]), (display, role))

    def test_a_both_ways_code_on_a_school_without_a_place_is_flagged(self) -> None:
        team = ci.parse_team("Smyrna HS (DE)")
        self.assertEqual(team["role_text"], "DE")
        self.assertTrue(team["role_parentheticals"][0]["place_or_role_ambiguous"])

    def test_another_sports_programme_is_not_a_football_employer(self) -> None:
        for raw in ("[[Holy Cross Crusaders track and field|Holy Cross]]", "[[Michigan State Spartans baseball|Michigan State]]",
                    "[[Maryland Terrapins men's lacrosse|Maryland]] (co-HC)"):
            with self.subTest(raw=raw):
                self.assertEqual(ci.employer_kind(ci.parse_team(raw)), "OTHER_SPORT_PROGRAM")
        self.assertEqual(ci.employer_kind(ci.parse_team("[[Holy Cross Crusaders football|Holy Cross]]")),
                         "COLLEGE_OR_OTHER_FOOTBALL_PROGRAM")

    def test_a_wrapped_list_item_and_its_nested_roles(self) -> None:
        text = ("{{Infobox NFL biography\n| pastcoaching =\n"
                "* [[Baltimore Ravens]] ({{nfly|2012}}) <br /> Offensive quality control coach\n"
                "* {{ubl|[[Michigan Wolverines football|Michigan]] (2015–2023)}}\n"
                "** {{ubl|Tight ends coach (2015–2016)}}\n"
                "** {{ubl|Running backs coach (2017–2018)}}\n}}")
        rows = [r for r in ci.career_rows(text)["rows"] if r["family"] == "COACHING"]
        michigan = [r for r in rows if r["team"]["employer_display"] == "Michigan"]
        self.assertEqual(len(michigan), 3)
        self.assertEqual(michigan[0]["team"]["role_basis"], "LIST_ROW_STATES_NO_ROLE")
        self.assertEqual([(r["team"]["role_text"], r["intervals"][0]["start"]) for r in michigan[1:]],
                         [("Tight ends coach", 2015), ("Running backs coach", 2017)])
        self.assertEqual(michigan[1]["team"]["role_basis"], "NESTED_LIST_LINE_UNDER_EMPLOYER")

    def test_a_page_without_an_infobox_has_no_rows(self) -> None:
        self.assertEqual(ci.career_rows("'''Someone''' was a coach.")["rows"], [])


if __name__ == "__main__":
    unittest.main()
