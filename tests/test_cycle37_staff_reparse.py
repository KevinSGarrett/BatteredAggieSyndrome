"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-03: staff season scope, record binding, role corrections and sport
exclusion. The season cases are the seven the Cycle #36 manager reproduced
(MF36-02), each with its expected verdict, plus new wrong-sport, wrong-page
and multiple-season cases. Every fixture is synthetic markup shaped like the
cached pages; none is a claim about a real person.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle37 import staff_record as sr  # noqa: E402
from aggie_analytics.cycle37 import staff_season_scope as ss  # noqa: E402

TABLE = "<table><tr><td>Alex Reed</td><td>Head Coach</td></tr></table>"


def season(source: str, person: str = "Alex Reed", shared: bool = False) -> dict:
    return ss.season_for_record(ss.scan(source), source.find(person), person=person, surname_shared_on_page=shared)


class ManagerSeasonCases(unittest.TestCase):
    """MF36-02: the manager's seven fixtures, verbatim in shape."""

    def test_positive_heading_binds(self) -> None:
        verdict = season("<h1>2026 Football Coaching Staff</h1>" + TABLE)
        self.assertEqual((verdict["state"], verdict["bound_season"]), (ss.BOUND_HEADING, 2026))

    def test_another_persons_hire_binds_nothing(self) -> None:
        verdict = season("<h1>Football Staff</h1><p>Bob Jones was hired on January 9, 2026.</p>" + TABLE)
        self.assertIsNone(verdict["bound_season"])

    def test_a_fundraiser_announcement_binds_nothing(self) -> None:
        verdict = season("<h1>Football Staff</h1><p>A stadium fundraiser was announced on January 9, 2026.</p>" + TABLE)
        self.assertIsNone(verdict["bound_season"])

    def test_a_basketball_subsection_is_another_sport(self) -> None:
        verdict = season("<h1>2026 Football Coaching Staff</h1><h2>Basketball Coaches</h2>" + TABLE)
        self.assertEqual(verdict["state"], ss.UNBOUND_OTHER_SPORT)

    def test_a_hidden_heading_labels_nothing(self) -> None:
        for wrapper in ("<div hidden>{}</div>", "<div aria-hidden='true'>{}</div>", "<div style='display:none'>{}</div>",
                        "<div class='sr-only'>{}</div>"):
            with self.subTest(wrapper=wrapper):
                verdict = season(wrapper.format("<h1>2026 Football Coaching Staff</h1>") + TABLE)
                self.assertIsNone(verdict["bound_season"])

    def test_a_1999_heading_is_a_real_label(self) -> None:
        verdict = season("<h1>1999 Football Coaching Staff</h1>" + TABLE)
        self.assertEqual(verdict["bound_season"], 1999)

    def test_a_december_hire_for_next_season_binds_the_stated_season(self) -> None:
        verdict = season("<h1>Football Staff</h1><p>Alex Reed was hired on December 30, 2025 to lead the team "
                         "beginning in 2026.</p>")
        self.assertEqual((verdict["state"], verdict["bound_season"]), (ss.BOUND_STATED, 2026))
        self.assertEqual(verdict["announcement_date"], "2025-December-30")


class NewSeasonCases(unittest.TestCase):
    def test_a_date_without_a_stated_season_is_kept_but_binds_nothing(self) -> None:
        verdict = season("<h1>Football Staff</h1>" + TABLE + "<p>Alex Reed was hired on January 9, 2026.</p>")
        self.assertEqual(verdict["state"], ss.UNBOUND_DATE_ONLY)
        self.assertEqual(verdict["announcement_date"], "2026-January-09")

    def test_an_honour_is_not_an_appointment(self) -> None:
        verdict = season("<h1>Football Staff</h1>" + TABLE + "<p>Alex Reed was named All-America on January 9, 1990.</p>")
        self.assertIsNone(verdict["announcement_date"])

    def test_a_shared_surname_cannot_be_attributed(self) -> None:
        verdict = season("<h1>Football Staff</h1>" + TABLE + "<p>Reed was hired to lead the team beginning in 2026.</p>",
                         shared=True)
        self.assertIsNone(verdict["bound_season"])

    def test_each_section_dates_its_own_rows(self) -> None:
        page = ("<h1>2025 Football Coaching Staff</h1><table><tr><td>Sam Lee</td><td>Head Coach</td></tr></table>"
                "<h1>2026 Football Coaching Staff</h1>" + TABLE)
        self.assertEqual(season(page)["bound_season"], 2026)
        self.assertEqual(season(page, person="Sam Lee")["bound_season"], 2025)

    def test_schedules_footers_and_out_of_range_years_date_nothing(self) -> None:
        for page in ("<h1>2026 Football Schedule</h1>" + TABLE,
                     TABLE + "<footer><h2>2026 Football Coaching Staff</h2></footer>",
                     "<h1>2027 Football Coaching Staff</h1>" + TABLE,
                     "<h1>1962 Football Coaching Staff</h1>" + TABLE):
            with self.subTest(page=page[:40]):
                self.assertIsNone(season(page)["bound_season"])

    def test_real_heading_forms_found_by_the_blind_sample(self) -> None:
        for heading in ("2026 Football Support Staff", "2026 Cowboy Football Staff",
                        "2026 Demon Football Coaching Staff", "2026-27 Football Coaching Staff"):
            with self.subTest(heading=heading):
                self.assertEqual(season(f"<h1>{heading}</h1>" + TABLE)["bound_season"], 2026)
        self.assertIsNone(season("<h1>2026 Men's Basketball Coaching Staff</h1>" + TABLE)["bound_season"])

    def test_a_label_is_judged_by_its_own_heading_not_its_neighbour(self) -> None:
        page = "<h1>2026 Coaching Staff</h1><h2>Basketball</h2><p>x</p><h2>Football</h2>" + TABLE
        self.assertEqual(season(page)["bound_season"], 2026)

    def test_an_unlocated_record_is_never_dated(self) -> None:
        verdict = ss.season_for_record(ss.scan("<h1>2026 Football Coaching Staff</h1>" + TABLE), None)
        self.assertEqual(verdict["state"], ss.UNBOUND_NOT_LOCATED)


class RecordTests(unittest.TestCase):
    def test_interface_phrases_leave_the_name(self) -> None:
        self.assertEqual(sr.clean_person("Tyson Kee Full Bio"), ("Tyson Kee", ["Full Bio"]))
        self.assertEqual(sr.clean_person("Anthony DiMichele Twitter Opens in a new window")[0], "Anthony DiMichele")
        self.assertEqual(sr.clean_person("Mark Bio"), ("Mark Bio", []))

    def test_interface_text_after_the_name_is_cut(self) -> None:
        self.assertEqual(sr.clean_person("Kai Ross Full Bio Football Support Staff")[0], "Kai Ross")
        self.assertEqual(sr.clean_person("JP Gourley '25 Full Bio Football Support Staff")[0], "JP Gourley")
        self.assertEqual(sr.clean_person("Ty Morgan 24")[0], "Ty Morgan")

    def test_the_page_spelling_wins_over_a_parser_that_drops_apostrophes(self) -> None:
        page = "<table><tr><td>Ray O'Daffer</td><td>Video Operations Assistant</td></tr></table>"
        verdict = sr.bind_record(page, page.encode(), "Ray ODaffer", "Video Operations Assistant")
        self.assertTrue(verdict["person_record_bound"])
        self.assertEqual(verdict["person_as_on_page"], "Ray O'Daffer")
        self.assertTrue(verdict["bytes_at_offset_are_the_name"])

    def test_extra_spaces_inside_a_name_still_verify(self) -> None:
        page = "<table><tr><td><span>Greg   Gasparato</span></td><td>Head Coach</td></tr></table>"
        verdict = sr.bind_record(page, page.encode(), "Greg Gasparato", "Head Coach")
        self.assertTrue(verdict["bytes_at_offset_are_the_name"])
        self.assertEqual(verdict["name_span"]["encoding"], "WHITESPACE_OR_NBSP_BETWEEN_NAME_PARTS")

    def test_a_row_naming_another_person_is_refused(self) -> None:
        page = ("<table><tr><td>Zach Hamer</td><td>Assistant Coach/Director of Player Development</td>"
                "<td>formerly with Camryn Crocker</td></tr></table>")
        data = page.encode()
        verdict = sr.bind_record(page, data, "Camryn Crocker", "Assistant Coach/Defensive Coordinator")
        self.assertFalse(verdict["person_record_bound"])
        self.assertEqual(verdict["state"], "REFUSED_RECORD_NAMES_ANOTHER_PERSON")

    def test_offsets_are_byte_exact_after_multibyte_text(self) -> None:
        page = "<p>Équipe — staff</p><table><tr><td>  <a href='/x'>José Núñez</a></td><td>Head Coach</td></tr></table>"
        data = page.encode("utf-8")
        verdict = sr.bind_record(page, data, "José Núñez", "Head Coach")
        span = verdict["name_span"]
        self.assertTrue(verdict["bytes_at_offset_are_the_name"])
        self.assertEqual(data[span["byte_start"]:span["byte_end"]].decode(), "José Núñez")
        self.assertNotEqual(span["byte_start"], span["char_start"])
        self.assertTrue(verdict["dom_row"]["row_contains_person"])

    def test_an_out_of_step_parsed_title_gives_way_to_the_own_records_title(self) -> None:
        page = ("<table><tr><td><a href='/c/1'>Pat One</a></td><td>Head Coach</td></tr>"
                "<tr><td><a href='/c/2'>Sam Two</a></td><td>Defensive Coordinator</td></tr></table>")
        # The upstream parse zipped titles one row late: Pat One carries Sam Two's title.
        binding = sr.bind_record(page, page.encode(), "Pat One", "Defensive Coordinator")
        self.assertTrue(binding["person_record_bound"])
        self.assertFalse(binding["role_claim_supported"])
        chosen = sr.title_for_row(binding, "Defensive Coordinator")
        self.assertEqual((chosen["title"], chosen["role_claim_supported"]), ("Head Coach", True))
        self.assertEqual(chosen["cycle36_title"], "Defensive Coordinator")

    def test_an_address_in_the_title_cell_is_not_a_title(self) -> None:
        binding = {"person_record_bound": True, "role_claim_supported": False,
                   "record_title": "football.recruiting@example.edu"}
        chosen = sr.title_for_row(binding, "Running Backs")
        self.assertEqual((chosen["title"], chosen["role_claim_supported"]), ("Running Backs", False))

    def test_an_unbound_person_keeps_the_parsed_title_unsupported(self) -> None:
        chosen = sr.title_for_row({"person_record_bound": False, "record_title": None}, "Head Coach")
        self.assertEqual(chosen["title_source"], "PARSED_TITLE_NOT_SUPPORTED_BY_OWN_RECORD")


class RoleTests(unittest.TestCase):
    def roles(self, title: str) -> dict:
        return {a["role"]: a for a in sr.assignments_v37(title)}

    def test_a_qualifier_in_another_segment_does_not_unmake_the_head_coach(self) -> None:
        roles = self.roles("Head Football Coach / Sr. Associate Athletic Director")
        self.assertEqual(roles["head_coach"]["occupancy"], "PRINCIPAL")
        self.assertNotIn("assistant_head_coach", roles)
        self.assertIn("athletic_director", roles)
        interim = self.roles("Offensive coordinator / interim head coach")
        self.assertEqual(interim["head_coach"]["occupancy"], "PRINCIPAL")
        self.assertIn("INTERIM", interim["head_coach"]["title_qualifiers"])

    def test_the_assistant_head_coach_and_sub_team_heads_stay_non_principal(self) -> None:
        self.assertEqual(self.roles("Associate Head Coach / Defensive Coordinator")["assistant_head_coach"]["occupancy"],
                         "QUALIFIED_NOT_PRINCIPAL")
        self.assertNotIn("head_coach", self.roles("Assistant coach/freshman head coach"))
        self.assertNotIn("head_coach", self.roles("Director of Internal Operations & Head Coach Logistics"))

    def test_an_executive_director_of_football_is_not_the_head_coach(self) -> None:
        for title in ("Executive Director of Football", "Associate AD, Executive Director of Football"):
            with self.subTest(title=title):
                roles = self.roles(title)
                self.assertNotIn("head_coach", roles)
                self.assertNotIn("assistant_head_coach", roles)
                self.assertEqual(roles["football_operations"]["taxonomy_correction"],
                                 "EXECUTIVE_DIRECTOR_OF_FOOTBALL_IS_NOT_HEAD_COACH")
        self.assertEqual(self.roles("Head Football Coach and Executive Director of Football")["head_coach"]["occupancy"],
                         "PRINCIPAL")

    def test_assistant_coach_dc_is_the_dc(self) -> None:
        dc = self.roles("Assistant Coach/Defensive Coordinator")["defensive_coordinator"]
        self.assertEqual((dc["occupancy"], dc["segment_qualifiers"]), ("PRINCIPAL", []))

    def test_an_assistant_to_the_dc_does_not_fill_it(self) -> None:
        for title in ("Assistant to the Defensive Coordinator", "Defensive Coordinator Assistant",
                      "Graduate Assistant - Defensive Coordinator", "Assistant Defensive Coordinator"):
            with self.subTest(title=title):
                self.assertEqual(self.roles(title)["defensive_coordinator"]["occupancy"], "QUALIFIED_NOT_PRINCIPAL")

    def test_support_to_the_head_coach_is_not_an_assistant_head_coach(self) -> None:
        roles = self.roles("Executive Assistant to the Head Football Coach")
        self.assertNotIn("assistant_head_coach", roles)
        self.assertIn("administrative_staff", roles)
        self.assertIn("assistant_head_coach", self.roles("Assistant Head Coach, Cornerbacks"))

    def test_an_academic_advisor_is_academic_staff(self) -> None:
        self.assertEqual(set(self.roles("Academic Advisor (Football)")), {"academic_staff"})

    def test_title_roles_and_qualifiers_stay_separate(self) -> None:
        roles = self.roles("Co-Defensive Coordinator/Linebackers")
        self.assertEqual(roles["defensive_coordinator"]["occupancy"], "CO_SHARED")
        self.assertEqual(roles["defensive_coordinator"]["segment_qualifiers"], ["CO"])
        self.assertEqual(roles["linebackers"]["segment_qualifiers"], [])
        self.assertEqual(roles["linebackers"]["source_title"], "Co-Defensive Coordinator/Linebackers")


class SportTests(unittest.TestCase):
    def test_another_sport_is_excluded_before_roles(self) -> None:
        self.assertFalse(sr.sport_scope("Head Coach", None, "https://x.edu/sports/mens-basketball/coaches",
                                        None)["football_role_admissible"])
        self.assertFalse(sr.sport_scope("Pitching Coach, Baseball", None, None, None)["football_role_admissible"])
        self.assertFalse(sr.sport_scope("Head Coach", "OTHER_SPORT_SECTION", None, None)["football_role_admissible"])

    def test_fb_in_a_multi_sport_title_is_football(self) -> None:
        verdict = sr.sport_scope("Deputy Athletic Director (FB, WBB, BOWLING, MBB, BSB)", "OTHER_SPORT_SECTION",
                                 None, None)
        self.assertEqual((verdict["scope"], verdict["basis"]), ("FOOTBALL", "TITLE_NAMES_FOOTBALL"))

    def test_a_shared_football_role_is_kept(self) -> None:
        verdict = sr.sport_scope("Director of Communications (Football, Men's Basketball)", None, None, None)
        self.assertTrue(verdict["football_role_admissible"])
        self.assertTrue(sr.sport_scope("Head Coach", None, "https://x.edu/sports/football/coaches",
                                       "Women's Basketball Staff")["football_role_admissible"])

    def test_sprint_football_is_another_sport(self) -> None:
        self.assertFalse(sr.sport_scope("Sprint Football Head Coach", None, None, None)["football_role_admissible"])
        self.assertFalse(sr.sport_scope("Head Coach", None, "https://x.edu/sports/sprint-football/roster",
                                        None)["football_role_admissible"])
        self.assertTrue(sr.sport_scope("Equipment (Football, Sprint Football)", None, None,
                                       None)["football_role_admissible"])

    def test_a_record_in_a_table_headed_by_another_sport_is_in_that_section(self) -> None:
        page = ("<h2>Staff Directory</h2><table><thead><tr><th>Football</th></tr><tr><th>Name</th><th>Title</th>"
                "</tr></thead><tbody><tr><td>Pat One</td><td>Offensive Coordinator</td></tr></tbody></table>"
                "<table><thead><tr><th>Sprint Football</th><th>@SprintFB</th></tr><tr><th>Name</th><th>Title</th>"
                "</tr></thead><tbody><tr><td>Sam Two</td><td>Offensive Coordinator</td></tr></tbody></table>")
        scanned = ss.scan(page)
        varsity = ss.record_sport_section(scanned, page.index("Pat One"))
        sprint = ss.record_sport_section(scanned, page.index("Sam Two"))
        self.assertEqual(varsity["state"], "FOOTBALL_SECTION")
        self.assertEqual(sprint["state"], "OTHER_SPORT_SECTION")
        self.assertIn("Sprint Football", sprint["heading"])
        self.assertEqual(ss.season_for_record(scanned, page.index("Sam Two"))["state"], ss.UNBOUND_OTHER_SPORT)


if __name__ == "__main__":
    unittest.main()
