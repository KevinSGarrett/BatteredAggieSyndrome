"""Cycle32 regression fixtures for Cycle31 manager counterexamples.

These enter production functions. They do not certify national completeness.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from aggie_analytics.cycle30.availability import join_candidates_to_roster
from aggie_analytics.cycle30.coaching import (
    career_episode_seasons,
    excluded_official_role_spans,
    historical_season_page_title,
    official_page_binds_program,
    parse_infobox_college_coach,
    parse_official_staff_html,
    parse_wikimedia_infobox,
    program_identity_binds,
    role_families_from_title,
    season_page_supports_requested_year,
    season_title_matches_school,
    select_college_football_wiki_title,
)
from aggie_analytics.cycle30.contracts_v2 import (
    ContractV2Error,
    round_trip_game_context,
    round_trip_staff_snapshot,
    staff_snapshot_v2_from_bas_matrix_cell,
)
from aggie_analytics.cycle30.kernel_model import (
    KernelModelError,
    design_matrix,
    fit_logistic,
    fold_local_fit,
    predict_proba,
    swap_participants,
)
from aggie_analytics.cycle30.populations import (
    current_deletion_does_not_shrink_history,
    historical_program_season_keys,
    insert_discontinued_program_changes_coverage,
)
from aggie_analytics.cycle30.pit_kernel import (
    PROVEN,
    RETROSPECTIVE,
    forecast_freeze_authority,
    validate_row_authority,
)
from aggie_analytics.cycle30.scoring import ScoringError, admit_official_final
from aggie_analytics.scientific_reference.cycle30.pit import (
    IndependentPitError,
    challenge_kernel_rows,
)


VALID_RECEIPT = "a" * 64
ROOT = Path(__file__).resolve().parents[1]


def _load_tool(filename: str):
    spec = importlib.util.spec_from_file_location(
        filename.replace(".py", ""), ROOT / "tools" / filename
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _staff_packet(**overrides):
    packet = {
        "program_id": "TEST",
        "as_of_utc": "2026-09-09T00:00:00Z",
        "role": "head_coach",
        "formal_title": None,
        "responsibility": "UNKNOWN",
        "episode_refs": [],
        "episode_cardinality": 0,
        "disposition": "UNKNOWN_NOT_LISTED",
        "attempt_count": 1,
        "pit_admitted": False,
    }
    packet.update(overrides)
    return packet


class Cycle32ManagerCounterexamples(unittest.TestCase):
    def test_malformed_unproven_receipt_cannot_prove(self) -> None:
        verdict = validate_row_authority(
            {
                "source_id": "SRC",
                "effective_utc": "2018-09-01T19:00:00Z",
                "known_at_utc": "2018-09-01T19:00:00Z",
                "receipt_sha256": "not-a-hash",
                "classification": "UNPROVEN",
                "evidence_class": "UNPROVEN",
                "source_publication_utc": "2018-08-31T19:00:00Z",
            },
            target_cutoff="2018-09-01T19:00:00Z",
        )
        self.assertNotEqual(verdict, PROVEN)
        self.assertIn(verdict, {RETROSPECTIVE, "SOURCE_AUTHORITY_UNPROVEN"})

    def test_valid_publication_receipt_can_prove(self) -> None:
        verdict = validate_row_authority(
            {
                "source_id": "SRC",
                "effective_utc": "2018-09-01T19:00:00Z",
                "known_at_utc": "2018-09-01T19:00:00Z",
                "receipt_sha256": VALID_RECEIPT,
                "classification": "PUBLICATION",
                "evidence_class": "PUBLICATION",
                "source_publication_utc": "2018-08-31T19:00:00Z",
            },
            target_cutoff="2018-09-01T19:00:00Z",
        )
        self.assertEqual(verdict, "PROVEN_PIT_TRAINING_ROW")

    def test_forecast_freeze_is_not_feature_proof(self) -> None:
        freeze = forecast_freeze_authority(
            {"snapshot_timestamp_utc": "2018-09-01T12:00:00Z"},
            receipt_sha256=VALID_RECEIPT,
        )
        self.assertFalse(freeze.get("allow_retrospective_prior"))
        verdict = validate_row_authority(
            freeze, target_cutoff="2018-09-01T19:00:00Z"
        )
        self.assertNotEqual(verdict, "PROVEN_PIT_TRAINING_ROW")

    def test_missing_numeric_predictor_is_not_zero(self) -> None:
        rows = [
            {
                "home_win_label": True,
                "home_features": {"pit_prior_margin_mean": None},
                "away_features": {"pit_prior_margin_mean": -8.0},
            }
        ]
        with self.assertRaises(KernelModelError):
            design_matrix(rows, "prior_margin_diff")

    def test_missing_label_is_not_a_loss(self) -> None:
        rows = [{"home_features": {}, "away_features": {}}]
        with self.assertRaises(KernelModelError):
            design_matrix(rows, "intercept_only")

    def test_raw_21_14_caller_0_99_rejected(self) -> None:
        page = "<span id='livestream_status_1'>Final</span>"
        with self.assertRaises(ScoringError):
            admit_official_final(
                page_text=page,
                contest_id="1",
                contest_hint="1",
                score_element_ids=["home-score", "away-score"],
                ordered_participant_ids=["H", "A"],
                page_url="https://example.test/1",
                embedded_contest_id="1",
                canonical_home_id="H",
                canonical_away_id="A",
                displayed_home_name="Home",
                displayed_away_name="Away",
                name_only=False,
                home_points=0,
                away_points=99,
                kickoff_utc="2026-09-05T16:00:00Z",
                retrieval_utc="2026-09-05T23:00:00Z",
                http_status=200,
                upstream_status=200,
                body=page.encode("utf-8"),
            )

    def test_stats_page_layout_without_scoreboard_object_rejected(self) -> None:
        page = "<html><h1>Stats</title> Final 21-14 Home vs Away</html>"
        with self.assertRaises(ScoringError):
            admit_official_final(
                page_text=page,
                contest_id="1",
                contest_hint="1",
                score_element_ids=["home-score", "away-score"],
                ordered_participant_ids=["H", "A"],
                page_url="https://example.test/stats/1",
                embedded_contest_id="1",
                canonical_home_id="H",
                canonical_away_id="A",
                displayed_home_name="Home",
                displayed_away_name="Away",
                name_only=False,
                home_points=0,
                away_points=99,
                kickoff_utc="2026-09-05T16:00:00Z",
                retrieval_utc="2026-09-05T23:00:00Z",
                http_status=200,
                upstream_status=200,
                body=page.encode("utf-8"),
            )

    def test_mismatched_page_bytes_rejected(self) -> None:
        page = (
            "<span id='livestream_status_6603962'>Final</span>"
            '{"contestId":6603962,"url":"\\/game\\/6603962",'
            '"gameState":"F","statusCodeDisplay":"Final",'
            '"teams":[{"isHome":false,"seoname":"smu","nameShort":"SMU","score":14},'
            '{"isHome":true,"seoname":"florida-st","nameShort":"Florida St.","score":21}]}'
        )
        with self.assertRaises(ScoringError):
            admit_official_final(
                page_text=page,
                contest_id="6603962",
                contest_hint="6603962",
                score_element_ids=["home-score", "away-score"],
                ordered_participant_ids=["H", "A"],
                page_url="https://example.test/game/6603962",
                embedded_contest_id="6603962",
                canonical_home_id="H",
                canonical_away_id="A",
                displayed_home_name="Florida State",
                displayed_away_name="SMU",
                name_only=False,
                home_points=21,
                away_points=14,
                kickoff_utc="2026-09-05T16:00:00Z",
                retrieval_utc="2026-09-06T01:00:00Z",
                http_status=200,
                upstream_status=200,
                body=b"<html>different bytes</html>",
            )

    def test_valid_raw_final_still_admits(self) -> None:
        page = (
            "<span id='livestream_status_6603962'>Final</span>"
            '{"contestId":6603962,"url":"\\/game\\/6603962",'
            '"gameState":"F","statusCodeDisplay":"Final",'
            '"teams":[{"isHome":false,"seoname":"smu","nameShort":"SMU","score":14},'
            '{"isHome":true,"seoname":"florida-st","nameShort":"Florida St.","score":21}]}'
        )
        admitted = admit_official_final(
            page_text=page,
            contest_id="6603962",
            contest_hint="6603962",
            score_element_ids=["home-score", "away-score"],
            ordered_participant_ids=["H", "A"],
            page_url="https://example.test/game/6603962",
            embedded_contest_id="6603962",
            canonical_home_id="H",
            canonical_away_id="A",
            displayed_home_name="Florida State",
            displayed_away_name="SMU",
            name_only=False,
            home_points=21,
            away_points=14,
            kickoff_utc="2026-09-05T16:00:00Z",
            retrieval_utc="2026-09-06T01:00:00Z",
            http_status=200,
            upstream_status=200,
            body=page.encode("utf-8"),
        )
        self.assertEqual(admitted["home_points"], 21)
        self.assertEqual(admitted["away_points"], 14)
        self.assertEqual(admitted["state"], "SCORE_ADMITTED")

    def test_kernel_rows_tamper_is_challenged(self) -> None:
        with self.assertRaises(IndependentPitError):
            challenge_kernel_rows(
                [
                    {
                        "home_points": 21,
                        "away_points": 14,
                        "home_win_label": False,
                        "home_features": {"pit_prior_margin_mean": 999999},
                        "away_features": {"pit_prior_margin_mean": 0},
                    }
                ]
            )

    def test_staff_fraction_bool_null_duplicate_confirmed_empty(self) -> None:
        with self.assertRaises(ContractV2Error):
            round_trip_staff_snapshot(_staff_packet(attempt_count=1.9))
        with self.assertRaises(ContractV2Error):
            round_trip_staff_snapshot(_staff_packet(attempt_count=True))
        with self.assertRaises(ContractV2Error):
            round_trip_staff_snapshot(_staff_packet(program_id=None))
        with self.assertRaises(ContractV2Error):
            round_trip_staff_snapshot(
                _staff_packet(
                    disposition="CONFIRMED_SINGLE_OCCUPANT",
                    episode_refs=[],
                    episode_cardinality=0,
                )
            )
        with self.assertRaises(ContractV2Error):
            round_trip_staff_snapshot(
                _staff_packet(episode_refs=["E1", "E1"], episode_cardinality=2)
            )
        with self.assertRaises(ContractV2Error):
            round_trip_staff_snapshot(
                _staff_packet(episode_refs=["E1"], episode_cardinality=1.9)
            )

    def test_game_context_rejects_invalid_participants_and_types(self) -> None:
        with self.assertRaises(ContractV2Error):
            round_trip_game_context(
                {
                    "canonical_game_id": None,
                    "source_order": "nonsense",
                    "canonical_home_id": "SAME",
                    "canonical_away_id": "SAME",
                    "designated_home_id": "THIRD",
                    "ordinary_home_exposure_designated_home": 0,
                    "site_class": "NEUTRAL",
                    "unknowns": "not-an-object",
                }
            )

    def test_wrong_school_titles_do_not_bind(self) -> None:
        cases = (
            ("Arizona", "Football Coaches - Northern Arizona University Athletics"),
            ("Illinois", "Football Coaches - Eastern Illinois University Athletics"),
            ("Kansas", "2026 Football Coaches - Kansas State University Athletics"),
            ("Louisiana", "Football Coaches - Southeastern Louisiana University Athletics"),
            ("New Mexico", "Football Coaches - New Mexico State University Athletics"),
            ("Ohio", "2026 Football Coaches | Ohio State"),
            ("Southern", "Football Coaches - Southern Utah University Athletics"),
            ("Tennessee State", "Football Coaches - East Tennessee State University"),
            ("Utah", "Football Coaches - Utah State University Athletics"),
        )
        for school, title in cases:
            with self.subTest(school=school):
                self.assertFalse(season_title_matches_school(title, school))
                self.assertFalse(
                    official_page_binds_program(
                        program_name=school, page_title=title, page_url="https://example.test"
                    )
                )
        self.assertTrue(
            season_title_matches_school(
                "2026 Football Coaches - University of Arizona Athletics", "Arizona"
            )
        )
        self.assertFalse(
            program_identity_binds(
                requested="Arizona",
                observed_text="Northern Arizona Lumberjacks https://www.nauathletics.com",
            )
        )
        self.assertTrue(
            program_identity_binds(
                requested="Arizona State",
                observed_text="Staff Directory https://thesundevils.com/staff-directory?path=football",
            )
        )
        self.assertFalse(
            program_identity_binds(
                requested="Ohio",
                observed_text="2026 Football Coaches https://ohiostatebuckeyes.com/sports/football/coaches",
            )
        )

    def test_support_title_is_not_head_coach(self) -> None:
        self.assertEqual(
            role_families_from_title("Executive Coordinator for the Head Coach"),
            (),
        )
        self.assertEqual(role_families_from_title("Head Football Coach"), ("head_coach",))
        self.assertEqual(
            role_families_from_title("Swette Family Endowed Football Coach"),
            ("head_coach",),
        )
        self.assertEqual(
            role_families_from_title("Head Coach - Football Sports Performance"),
            (),
        )
        self.assertEqual(
            role_families_from_title("Deputy Head Coach/Tight Ends Coach"),
            (),
        )
        self.assertEqual(
            role_families_from_title("Director of Head Coach Operations"),
            (),
        )
        self.assertEqual(
            role_families_from_title(
                "Executive Director of Head Coach Operations / Football Administration"
            ),
            (),
        )
        self.assertEqual(
            role_families_from_title("Head Coach of Offense/Quarterbacks"),
            (),
        )
        self.assertEqual(
            role_families_from_title(
                "Senior Head Coach Analyst & Roster Revenue Share"
            ),
            (),
        )
        self.assertEqual(role_families_from_title("Consultant to Head Coach"), ())
        self.assertEqual(role_families_from_title("Advisor to Head Coach"), ())
        self.assertEqual(
            role_families_from_title(
                "Director of Player Development and Senior Advisor to the Head Football Coach"
            ),
            (),
        )
        self.assertEqual(
            role_families_from_title("Head Coach of Defense, Linebackers"),
            (),
        )
        self.assertEqual(role_families_from_title("Head Coach Assistant"), ())
        self.assertEqual(
            role_families_from_title("Head Coach Assistant / Recruiting Assistant"),
            (),
        )

    def test_vue_mispair_bare_hc_dropped_when_person_is_coordinator(self) -> None:
        from aggie_analytics.cycle30.coaching import fill_current_role_matrix

        programs = [
            {
                "program_id": "SRC-002:TEAM:36",
                "display_name": "Colorado State",
            }
        ]
        people = {
            "SRC-002:TEAM:36": [
                {
                    "person": "Jim Mora",
                    "title": "Head Coach",
                    "span_id": "dom:csu:Jim Mora:Head Coach",
                    "page_url": "https://csurams.com/sports/football/coaches",
                },
                {
                    "person": "Tyson Summers",
                    "title": "Defensive Coordinator",
                    "span_id": "dom:csu:Tyson Summers:Defensive Coordinator",
                    "page_url": "https://csurams.com/sports/football/coaches",
                },
                {
                    "person": "Tyson Summers",
                    "title": "Head Coach",
                    "span_id": "dom:csu:Tyson Summers:Head Coach",
                    "page_url": "https://csurams.com/sports/football/coaches",
                },
            ]
        }
        cells = [
            {
                "program_id": "SRC-002:TEAM:36",
                "role": "head_coach",
                "as_of_utc": "2026-09-11T06:33:52Z",
            },
            {
                "program_id": "SRC-002:TEAM:36",
                "role": "defensive_coordinator",
                "as_of_utc": "2026-09-11T06:33:52Z",
            },
        ]
        filled = fill_current_role_matrix(
            cells,
            programs=programs,
            cfbd_hc_by_school={},
            official_people_by_program=people,
            official_attempts_by_program={
                "SRC-002:TEAM:36": {
                    "status": "CAPTURED",
                    "page_url": "https://csurams.com/sports/football/coaches",
                }
            },
        )
        hc = next(row for row in filled if row["role"] == "head_coach")
        dc = next(row for row in filled if row["role"] == "defensive_coordinator")
        self.assertEqual(
            [item["person"] for item in hc["episode_refs"]],
            ["Jim Mora"],
        )
        self.assertEqual(hc["disposition"], "CONFIRMED_APPOINTMENT")
        self.assertEqual(
            [item["person"] for item in dc["episode_refs"]],
            ["Tyson Summers"],
        )

    def test_jacksonville_season_title_rejects_jacksonville_state(self) -> None:
        self.assertTrue(
            season_title_matches_school(
                "2013 Jacksonville Dolphins football team", "Jacksonville"
            )
        )
        self.assertFalse(
            season_title_matches_school(
                "2013 Jacksonville State Gamecocks football team", "Jacksonville"
            )
        )
        self.assertEqual(
            historical_season_page_title(
                "2014 Ohio State Buckeyes football team", 2014, school="Ohio"
            ),
            "2014 Ohio football team",
        )

    def test_baseball_title_excluded_from_football_html(self) -> None:
        html = (
            "<title>Football Coaches - Arizona State University Athletics</title>"
            "<div class='sidearm-roster-coach-name'>Willie Bloomquist</div>"
            "<div class='sidearm-roster-coach-title'>Head Coach, Baseball</div>"
            "<div class='sidearm-roster-coach-name'>Kenny Dillingham</div>"
            "<div class='sidearm-roster-coach-title'>Head Football Coach</div>"
        )
        rows = parse_official_staff_html(
            html,
            page_url="https://thesundevils.com/sports/football/coaches",
            program_name="Arizona State",
        )
        people = {row["person"] for row in rows}
        self.assertIn("Kenny Dillingham", people)
        self.assertNotIn("Willie Bloomquist", people)

    def test_staff_directory_football_department_excludes_baseball(self) -> None:
        html = (
            "<title>Staff Directory - Arizona State University Athletics</title>"
            '<tbody class="staff-directory-table-department">'
            '<tr class="staff-directory-table-department__head">'
            '<td class="staff-directory-table-department__title" colspan="5">'
            "<!--[--><span>Baseball Fax#: (480) 965-9309</span></td></tr>"
            '<tr class="staff-directory-table-member-position">'
            '<td class="staff-directory-table-member-position__name">'
            '<a href="/staff/willie-bloomquist">Willie Bloomquist</a></td>'
            '<td class="staff-directory-table-member-position__position">'
            "<p>Head Coach</p></td></tr></tbody>"
            '<tbody class="staff-directory-table-department">'
            '<tr class="staff-directory-table-department__head">'
            '<td class="staff-directory-table-department__title" colspan="5">'
            "<!--[--><span>Football (480)965-3429</span></td></tr>"
            '<tr class="staff-directory-table-member-position">'
            '<td class="staff-directory-table-member-position__name">'
            '<a href="/staff/kenny-dillingham">Kenny Dillingham</a></td>'
            '<td class="staff-directory-table-member-position__position">'
            "<p>Swette Family Endowed Football Coach</p></td></tr></tbody>"
        )
        rows = parse_official_staff_html(
            html,
            page_url="https://thesundevils.com/staff-directory?path=football",
            program_name="Arizona State",
        )
        people = {row["person"] for row in rows}
        self.assertIn("Kenny Dillingham", people)
        self.assertNotIn("Willie Bloomquist", people)
        hc = [row for row in rows if row.get("role") == "head_coach"]
        self.assertEqual([row["person"] for row in hc], ["Kenny Dillingham"])

    def test_wrong_school_html_raises(self) -> None:
        html = "<title>Football Coaches - Northern Arizona University Athletics</title>"
        with self.assertRaises(Exception):
            parse_official_staff_html(
                html,
                page_url="https://www.nauathletics.com/sports/football/coaches",
                program_name="Arizona",
            )

    def test_basketball_infobox_does_not_create_football_hc(self) -> None:
        wikitext = (
            "{{Infobox college basketball coach\n"
            "| coach_years1 = 2020–present\n"
            "| coach_team1 = [[Wrong School]]\n"
            "}}\n"
            "{{Infobox college coach\n"
            "| coach_years1 = 2018–2019\n"
            "| coach_team1 = [[Right School]] (HC)\n"
            "}}\n"
        )
        episodes = parse_infobox_college_coach(
            wikitext, revision_id="1", page_title="Coach"
        )
        programs = {row["program_raw"] for row in episodes}
        self.assertIn("Right School", programs)
        self.assertNotIn("Wrong School", programs)

    def test_two_coordinator_links_are_preserved(self) -> None:
        wikitext = (
            "{{Infobox college football team\n"
            "| off_coach = [[Alice One]] and [[Bob Two]]\n"
            "}}\n"
        )
        rows = parse_wikimedia_infobox(wikitext, revision_id="9", page_title="Team")
        people = {row["person"] for row in rows}
        self.assertIn("Alice One", people)
        self.assertIn("Bob Two", people)

    def test_wikitext_leftover_keys_are_not_people(self) -> None:
        wikitext = (
            "{{Infobox college football team\n"
            "| head_coach = [[Kerwin Bell]]\n"
            "| off_coach = | oc_year =\n"
            "| def_coach = [[Jerry Odom]]\n"
            "}}\n"
        )
        rows = parse_wikimedia_infobox(wikitext, revision_id="9", page_title="Team")
        people = {row["person"] for row in rows}
        self.assertIn("Kerwin Bell", people)
        self.assertIn("Jerry Odom", people)
        self.assertNotIn("| oc_year =", people)
        self.assertFalse(any("=" in str(row["person"]) for row in rows))

    def test_repeated_career_index_does_not_overwrite_other_template(self) -> None:
        wikitext = (
            "{{Infobox college coach\n| coach_years1 = 2001–2005\n"
            "| coach_team1 = [[First Job]] (HC)\n}}\n"
            "{{Infobox college basketball coach\n"
            "| coach_years1 = 2020–present\n| coach_team1 = [[Other Sport]]\n}}\n"
        )
        episodes = parse_infobox_college_coach(
            wikitext, revision_id="2", page_title="Coach"
        )
        self.assertEqual(episodes[0]["program_raw"], "First Job")
        self.assertEqual(episodes[0]["start_year"], 2001)
        self.assertEqual(episodes[0]["end_year"], 2005)

    def test_generic_and_wrong_year_pages_fail_season_support(self) -> None:
        self.assertFalse(
            season_page_supports_requested_year(
                page_title="Texas A&M Aggies football", wikitext="", year=1963
            )
        )
        self.assertFalse(
            season_page_supports_requested_year(
                page_title="2026 Texas A&M Aggies football team",
                wikitext="",
                year=1963,
            )
        )
        self.assertTrue(
            season_page_supports_requested_year(
                page_title="1963 Texas A&M Aggies football team",
                wikitext="",
                year=1963,
            )
        )

    def test_present_does_not_expand_through_2026(self) -> None:
        seasons = career_episode_seasons(
            {
                "start_year": 2010,
                "end_year": None,
                "ongoing": True,
            }
        )
        self.assertEqual(seasons, [2010])
        self.assertNotIn(2026, seasons)

    def test_participant_swap_preserves_team_keyed_intercept_only(self) -> None:
        row = {
            "season": 2020,
            "home_canonical_team_id": "A",
            "away_canonical_team_id": "B",
            "home_win_label": True,
            "ordinary_home_exposure": 0,
            "site_class": "NEUTRAL",
            "home_features": {"pit_prior_margin_mean": 7.0},
            "away_features": {"pit_prior_margin_mean": -3.0},
        }
        swapped = swap_participants(row)
        base, _, _, _ = design_matrix([row], "intercept_only")
        other, _, _, _ = design_matrix([swapped], "intercept_only")
        p_base = predict_proba(base, [])
        p_swap = predict_proba(other, [])
        self.assertAlmostEqual(float(p_base[0]), 0.5)
        self.assertAlmostEqual(float(p_swap[0]), 1.0 - float(p_base[0]))

    def test_cross_program_alex_smith_is_not_verified(self) -> None:
        joined = join_candidates_to_roster(
            [{"candidate_name": "Alex Smith", "program_id": "PROGRAM_A"}],
            [
                {
                    "full_name": "Alex Smith",
                    "program_id": "PROGRAM_B",
                    "canonical_person_id": "PERSON:B",
                }
            ],
        )
        self.assertEqual(joined["joined_to_verified_roster"], 0)
        self.assertFalse(joined["rows"][0]["joined_to_verified_roster"])

    def test_bas_matrix_cell_converts_without_losing_episodes(self) -> None:
        packet = staff_snapshot_v2_from_bas_matrix_cell(
            {
                "program_id": "SRC-002:TEAM:333",
                "role": "head_coach",
                "disposition": "CONFIRMED_APPOINTMENT",
                "attempt_count": 1,
                "as_of_utc": "2026-09-11T05:00:00Z",
                "episode_refs": [
                    {
                        "person": "Kalen DeBoer",
                        "span_id": "dom:https://rolltide.com/sports/football/coaches:Kalen DeBoer:Head Coach",
                        "source_title": "Head Coach",
                    }
                ],
            }
        )
        self.assertEqual(packet["disposition"], "CONFIRMED_SINGLE_OCCUPANT")
        self.assertEqual(len(packet["episode_refs"]), 1)
        self.assertEqual(packet["bas_episode_extension"][0]["person"], "Kalen DeBoer")

    def test_historical_coverage_changes_on_discontinued_insert(self) -> None:
        keys = historical_program_season_keys(
            [
                {"program_id": "SRC-002:TEAM:1", "season": 2013},
                {"program_id": "SRC-002:TEAM:1", "season": 2014},
            ]
        )
        changed = insert_discontinued_program_changes_coverage(
            keys, program_id="SRC-002:TEAM:DISCONTINUED", season=2013
        )
        self.assertEqual(changed["after"]["n_keys"], 3)
        current_deletion_does_not_shrink_history(
            keys | {("SRC-002:TEAM:DISCONTINUED", 2013)},
            ["SRC-002:TEAM:1"],
            deleted_program_id="SRC-002:TEAM:1",
        )

    def test_fold_local_fit_missing_numeric_is_excluded(self) -> None:
        rows = [
            {
                "season": 2015,
                "home_win_label": True,
                "home_features": {},
                "away_features": {},
            },
            {
                "season": 2015,
                "home_win_label": False,
                "home_features": {"pit_prior_margin_mean": 3.0},
                "away_features": {"pit_prior_margin_mean": 1.0},
            },
            {
                "season": 2021,
                "home_win_label": True,
                "home_features": {"pit_prior_margin_mean": 2.0},
                "away_features": {"pit_prior_margin_mean": 1.0},
            },
        ]
        result = fold_local_fit(rows, candidate="prior_margin_diff")
        self.assertGreaterEqual(result["excluded_train"]["missing_numeric"], 1)
        self.assertEqual(result["train_games"], 1)

    def test_science_cli_rejects_coordinated_tamper(self) -> None:
        import json
        import subprocess
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            rows_path = Path(tmp) / "tampered.jsonl"
            rows_path.write_text(
                json.dumps(
                    {
                        "home_points": 21,
                        "away_points": 14,
                        "home_win_label": False,
                        "home_features": {"pit_prior_margin_mean": 999999},
                        "away_features": {"pit_prior_margin_mean": 0},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "tools/validate_cycle30_gates.py",
                    "--repo-root",
                    ".",
                    "--mode",
                    "SCIENCE",
                    "--kernel-rows",
                    str(rows_path),
                ],
                cwd=str(Path(__file__).resolve().parents[1]),
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("FAIL science", completed.stdout + completed.stderr)

    def test_wiki_title_selector_rejects_wrong_school_first_hits(self) -> None:
        cases = (
            (
                "Arizona",
                "Northern Arizona Lumberjacks football",
                "Arizona Wildcats football",
            ),
            (
                "Illinois",
                "Eastern Illinois Panthers football",
                "Illinois Fighting Illini football",
            ),
            (
                "Kansas",
                "Kansas State Wildcats football",
                "Kansas Jayhawks football",
            ),
            ("Ohio", "Ohio State Buckeyes football", "Ohio Bobcats football"),
            ("Utah", "Utah State Aggies football", "Utah Utes football"),
            (
                "Georgia",
                "Georgia national football team",
                "Georgia Bulldogs football",
            ),
        )
        for school, wrong, right in cases:
            chosen = select_college_football_wiki_title(
                [{"title": wrong}, {"title": right}], school
            )
            self.assertEqual(chosen, right, school)
            self.assertTrue(season_title_matches_school(right, school), school)
            self.assertFalse(season_title_matches_school(wrong, school), school)

    def test_same_name_different_programs_keep_distinct_person_ids(self) -> None:
        from aggie_analytics.cycle30.coaching import stable_person_id

        one = stable_person_id(program_id="SRC-002:TEAM:12", person="Alex Smith")
        two = stable_person_id(program_id="SRC-002:TEAM:2305", person="Alex Smith")
        self.assertNotEqual(one, two)

    def test_mixed_missing_numeric_excludes_without_zero_impute(self) -> None:
        rows = [
            {
                "season": 2015,
                "home_win_label": True,
                "home_features": {"pit_prior_margin_mean": None},
                "away_features": {"pit_prior_margin_mean": -8.0},
            },
            {
                "season": 2015,
                "home_win_label": False,
                "home_features": {"pit_prior_margin_mean": 4.0},
                "away_features": {"pit_prior_margin_mean": 1.0},
            },
        ]
        features, labels, _, excluded = design_matrix(rows, "prior_margin_diff")
        self.assertEqual(len(labels), 1)
        self.assertEqual(excluded["missing_numeric"], 1)
        self.assertEqual(float(features[0][0]), 3.0)

    def test_tied_probability_is_no_direction(self) -> None:
        from aggie_analytics.cycle30.kernel_model import favorite_direction

        self.assertEqual(favorite_direction(0.5), "NO_DIRECTION")
        self.assertEqual(favorite_direction(0.51), "HOME")
        self.assertEqual(favorite_direction(0.49), "AWAY")

    def test_washington_2026_head_coach_occupies_oc_when_operator_declares_dual_hat(
        self,
    ) -> None:
        from aggie_analytics.cycle30.coaching import fill_current_role_matrix

        programs = [
            {"program_id": "SRC-002:TEAM:264", "display_name": "Washington"}
        ]
        page = "https://gohuskies.com/coaches.aspx?path=football"
        people = {
            "SRC-002:TEAM:264": [
                {
                    "person": "Jedd Fisch",
                    "title": "Head Football Coach",
                    "role": "head_coach",
                    "span_id": f"dom:{page}:Jedd Fisch:Head Football Coach",
                    "page_url": page,
                },
                {
                    "person": "Kevin Cummings",
                    "title": "Pass Game Coordinator/Wide Receivers Coach",
                    "role": "OTHER_POSITION",
                    "span_id": f"dom:{page}:Kevin Cummings:Pass Game Coordinator/Wide Receivers Coach",
                    "page_url": page,
                },
                {
                    "person": "JP Losman",
                    "title": "Quarterbacks Coach",
                    "role": "OTHER_POSITION",
                    "span_id": f"dom:{page}:JP Losman:Quarterbacks Coach",
                    "page_url": page,
                },
                {
                    "person": "Ryan Walters",
                    "title": "Defensive Coordinator",
                    "role": "defensive_coordinator",
                    "span_id": f"dom:{page}:Ryan Walters:Defensive Coordinator",
                    "page_url": page,
                },
            ]
        }
        filled = fill_current_role_matrix(
            [
                {
                    "program_id": "SRC-002:TEAM:264",
                    "role": role,
                    "as_of_utc": "2026-09-11T07:04:58Z",
                }
                for role in (
                    "head_coach",
                    "offensive_coordinator",
                    "defensive_coordinator",
                )
            ],
            programs=programs,
            cfbd_hc_by_school={},
            official_people_by_program=people,
            official_attempts_by_program={
                "SRC-002:TEAM:264": {"status": "CAPTURED", "page_url": page}
            },
        )
        by_role = {row["role"]: row for row in filled}
        oc = by_role["offensive_coordinator"]
        self.assertEqual(oc["disposition"], "CONFIRMED_APPOINTMENT")
        self.assertEqual(
            [item["person"] for item in oc["episode_refs"]],
            ["Jedd Fisch"],
        )
        self.assertEqual(
            by_role["head_coach"]["episode_refs"][0]["person_id"],
            oc["episode_refs"][0]["person_id"],
        )
        self.assertNotEqual(
            by_role["head_coach"]["episode_refs"][0]["span_id"],
            oc["episode_refs"][0]["span_id"],
        )
        self.assertEqual(
            oc["episode_refs"][0]["dual_occupancy_with"],
            "head_coach",
        )
        self.assertEqual(
            oc["episode_refs"][0]["occupancy_authority"],
            "OPERATOR_CONTEMPORANEOUS_DECLARATION",
        )
        self.assertFalse(oc["episode_refs"][0].get("pit_admitted"))
        self.assertNotEqual(
            oc["episode_refs"][0].get("source"),
            "OFFICIAL_STAFF_HTML",
        )
        self.assertNotIn(
            oc["episode_refs"][0].get("responsibility"),
            {"offense_play_caller", "play_caller"},
        )
        self.assertNotEqual(oc["episode_refs"][0].get("play_caller"), True)
        self.assertEqual(
            role_families_from_title(oc["episode_refs"][0]["source_title"]),
            ("head_coach",),
        )
        self.assertEqual(
            [item["person"] for item in by_role["defensive_coordinator"]["episode_refs"]],
            ["Ryan Walters"],
        )
        self.assertEqual(
            role_families_from_title("Head Football Coach"),
            ("head_coach",),
        )

    def test_missing_oc_title_is_not_head_coach_oc_without_declaration(self) -> None:
        from aggie_analytics.cycle30.coaching import fill_current_role_matrix

        pid = "SRC-002:TEAM:999901"
        people = {
            pid: [
                {
                    "person": "Pat Example",
                    "title": "Head Football Coach",
                    "role": "head_coach",
                    "page_url": "https://example.edu/sports/football/coaches",
                },
                {
                    "person": "Sam Example",
                    "title": "Pass Game Coordinator/Wide Receivers Coach",
                    "role": "OTHER_POSITION",
                    "page_url": "https://example.edu/sports/football/coaches",
                },
                {
                    "person": "Alex Example",
                    "title": "Defensive Coordinator",
                    "role": "defensive_coordinator",
                    "page_url": "https://example.edu/sports/football/coaches",
                },
            ]
        }
        filled = fill_current_role_matrix(
            [
                {"program_id": pid, "role": "head_coach", "as_of_utc": "2026-09-11T07:04:58Z"},
                {
                    "program_id": pid,
                    "role": "offensive_coordinator",
                    "as_of_utc": "2026-09-11T07:04:58Z",
                },
            ],
            programs=[{"program_id": pid, "display_name": "Example"}],
            cfbd_hc_by_school={},
            official_people_by_program=people,
            official_attempts_by_program={
                pid: {
                    "status": "CAPTURED",
                    "page_url": "https://example.edu/sports/football/coaches",
                }
            },
        )
        oc = next(row for row in filled if row["role"] == "offensive_coordinator")
        self.assertEqual(oc["disposition"], "UNKNOWN_NOT_LISTED")
        self.assertFalse(oc.get("episode_refs"))

    def test_listed_oc_title_is_not_replaced_by_head_coach_dual_occupancy(
        self,
    ) -> None:
        from aggie_analytics.cycle30.coaching import fill_current_role_matrix

        pid = "SRC-002:TEAM:264"
        page = "https://gohuskies.com/coaches.aspx?path=football"
        people = {
            pid: [
                {
                    "person": "Jedd Fisch",
                    "title": "Head Football Coach",
                    "role": "head_coach",
                    "page_url": page,
                },
                {
                    "person": "Other Coordinator",
                    "title": "Offensive Coordinator",
                    "role": "offensive_coordinator",
                    "page_url": page,
                },
            ]
        }
        filled = fill_current_role_matrix(
            [
                {
                    "program_id": pid,
                    "role": "offensive_coordinator",
                    "as_of_utc": "2026-09-11T07:04:58Z",
                }
            ],
            programs=[{"program_id": pid, "display_name": "Washington"}],
            cfbd_hc_by_school={},
            official_people_by_program=people,
            official_attempts_by_program={pid: {"status": "CAPTURED", "page_url": page}},
        )
        oc = filled[0]
        self.assertEqual(
            [item["person"] for item in oc["episode_refs"]],
            ["Other Coordinator"],
        )
        self.assertNotIn("dual_occupancy_with", oc["episode_refs"][0])

    def test_sole_head_coach_is_kept_when_coordinator_title_is_a_duplicate_mispair(
        self,
    ) -> None:
        from aggie_analytics.cycle30.coaching import fill_current_role_matrix

        pid = "SRC-002:TEAM:135"
        people = {
            pid: [
                {
                    "person": "P.J. Fleck",
                    "title": "Offensive Coordinator / Quarterbacks",
                    "page_url": "https://gophersports.com/sports/football/coaches",
                },
                {
                    "person": "Greg Harbaugh Jr.",
                    "title": "Offensive Coordinator / Quarterbacks",
                    "page_url": "https://gophersports.com/sports/football/coaches",
                },
                {
                    "person": "P.J. Fleck",
                    "title": "Head Coach",
                    "page_url": "https://gophersports.com/sports/football/coaches",
                },
            ]
        }
        filled = fill_current_role_matrix(
            [
                {"program_id": pid, "role": "head_coach", "as_of_utc": "2026-09-11T07:25:04Z"},
                {
                    "program_id": pid,
                    "role": "offensive_coordinator",
                    "as_of_utc": "2026-09-11T07:25:04Z",
                },
            ],
            programs=[{"program_id": pid, "display_name": "Minnesota"}],
            cfbd_hc_by_school={},
            official_people_by_program=people,
            official_attempts_by_program={
                pid: {
                    "status": "CAPTURED",
                    "page_url": "https://gophersports.com/sports/football/coaches",
                }
            },
        )
        by_role = {row["role"]: row for row in filled}
        self.assertEqual(by_role["head_coach"]["disposition"], "CONFIRMED_APPOINTMENT")
        self.assertEqual(
            [item["person"] for item in by_role["head_coach"]["episode_refs"]],
            ["P.J. Fleck"],
        )
        self.assertEqual(
            [item["person"] for item in by_role["offensive_coordinator"]["episode_refs"]],
            ["Greg Harbaugh Jr."],
        )

    def test_vue_zip_does_not_put_oc_on_dc_when_another_dc_exists(self) -> None:
        from aggie_analytics.cycle30.coaching import fill_current_role_matrix

        pid = "SRC-002:TEAM:135"
        page = "https://gophersports.com/sports/football/coaches"
        people = {
            pid: [
                {
                    "person": "P.J. Fleck",
                    "title": "Offensive Coordinator / Quarterbacks",
                    "page_url": page,
                },
                {
                    "person": "Greg Harbaugh Jr.",
                    "title": "Defensive Coordinator / Safeties",
                    "page_url": page,
                },
                {
                    "person": "Danny Collins",
                    "title": "Cornerbacks / Co-Defensive Coordinator",
                    "page_url": page,
                },
                {
                    "person": "P.J. Fleck",
                    "title": "Head Coach",
                    "page_url": page,
                },
                {
                    "person": "Greg Harbaugh Jr.",
                    "title": "Offensive Coordinator / Quarterbacks",
                    "page_url": page,
                },
                {
                    "person": "Danny Collins",
                    "title": "Defensive Coordinator / Safeties",
                    "page_url": page,
                },
            ]
        }
        filled = fill_current_role_matrix(
            [
                {
                    "program_id": pid,
                    "role": "head_coach",
                    "as_of_utc": "2026-09-11T15:27:56Z",
                },
                {
                    "program_id": pid,
                    "role": "offensive_coordinator",
                    "as_of_utc": "2026-09-11T15:27:56Z",
                },
                {
                    "program_id": pid,
                    "role": "defensive_coordinator",
                    "as_of_utc": "2026-09-11T15:27:56Z",
                },
            ],
            programs=[{"program_id": pid, "display_name": "Minnesota"}],
            cfbd_hc_by_school={},
            official_people_by_program=people,
            official_attempts_by_program={pid: {"status": "CAPTURED", "page_url": page}},
        )
        by_role = {row["role"]: row for row in filled}
        self.assertEqual(
            [item["person"] for item in by_role["head_coach"]["episode_refs"]],
            ["P.J. Fleck"],
        )
        self.assertEqual(
            [item["person"] for item in by_role["offensive_coordinator"]["episode_refs"]],
            ["Greg Harbaugh Jr."],
        )
        dc_people = [item["person"] for item in by_role["defensive_coordinator"]["episode_refs"]]
        self.assertNotIn("Greg Harbaugh Jr.", dc_people)
        self.assertIn("Danny Collins", dc_people)

    def test_career_roundtrip_rejects_string_pit_and_namesakes(self) -> None:
        from aggie_analytics.cycle30.coaching import career_episode_roundtrip

        payload = career_episode_roundtrip(
            program_id="SRC-002:TEAM:135",
            person="Greg Harbaugh Jr.",
            career_episodes=[
                {
                    "person": "Greg Harbaugh Jr.",
                    "program_raw": "Minnesota",
                    "role": "offensive_coordinator",
                    "start_year": 2023,
                    "end_year": 2025,
                    "ongoing": False,
                    "pit_admitted": "false",
                    "span_id": "wikimedia:Greg Harbaugh Jr.:1:career:1:offensive_coordinator",
                },
                {
                    "person": "Greg Harbaugh",
                    "program_raw": "Other School",
                    "role": "offensive_coordinator",
                    "start_year": 2018,
                    "end_year": 2022,
                    "ongoing": False,
                    "pit_admitted": "true",
                    "span_id": "wikimedia:Greg Harbaugh:1:career:1:offensive_coordinator",
                },
            ],
        )
        self.assertEqual(payload["episode_cardinality"], 1)
        self.assertFalse(payload["episodes"][0]["pit_admitted"])
        self.assertFalse(payload["pit_admitted"])
        self.assertEqual(payload["namesake_rejected"], 1)
        self.assertTrue(str(payload["person_id"]).startswith("BAS:PERSON:"))

    def test_head_coach_support_is_not_program_head_coach(self) -> None:
        self.assertEqual(role_families_from_title("Head Coach"), ("head_coach",))
        self.assertEqual(
            role_families_from_title("Head Coach Support/Staff Operations"),
            (),
        )
        self.assertEqual(
            role_families_from_title("E. Bronson Ingram Chair in Football"),
            ("head_coach",),
        )
        self.assertEqual(
            role_families_from_title("Bradford M. Freeman Director of Football"),
            ("head_coach",),
        )
        self.assertEqual(
            role_families_from_title("Director of Football Operations"),
            (),
        )
        self.assertEqual(
            role_families_from_title("Director of Football Academics & Freshman Transition"),
            (),
        )
        self.assertEqual(
            role_families_from_title("Assistant Director of Football Creative Media"),
            (),
        )
        self.assertEqual(
            role_families_from_title("Director of Football Scouting"),
            (),
        )
        self.assertEqual(
            role_families_from_title("Andrew Luck Director of Offense"),
            ("offensive_coordinator",),
        )
        self.assertEqual(
            role_families_from_title(
                "Willie Shaw Director of Defense & Defensive Backs Coach"
            ),
            ("defensive_coordinator",),
        )
        self.assertEqual(
            role_families_from_title("Assistant Director of Offense"),
            (),
        )
        self.assertEqual(
            role_families_from_title("Director of Offense Recruiting"),
            (),
        )
        self.assertEqual(
            role_families_from_title("Director of Defense Recruiting"),
            (),
        )
        self.assertEqual(
            role_families_from_title("Director of Offensive Player Personnel"),
            (),
        )
        self.assertEqual(
            role_families_from_title("Assoc. Head Coach / OC / QB"),
            ("offensive_coordinator",),
        )
        self.assertEqual(
            role_families_from_title("Assoc. Head Coach / DC / LB"),
            ("defensive_coordinator",),
        )
        self.assertEqual(
            role_families_from_title(
                "Assistant Football Coach/Outside Linebackers Recruits: "
                "Maryland, Washington, D.C., Virginia"
            ),
            (),
        )
        self.assertEqual(
            role_families_from_title(
                "Special Assistant to the Defensive Coordinator"
            ),
            (),
        )
        self.assertEqual(
            role_families_from_title(
                "Special Assistant to the Offensive Coordinator"
            ),
            (),
        )
        self.assertEqual(
            role_families_from_title(
                "Assistant Head Coach / Defensive Coordinator"
            ),
            ("defensive_coordinator",),
        )

    def test_stanford_official_director_titles_are_oc_dc(self) -> None:
        html = """
        <html><head><title>Stanford Athletics</title></head><body>
        <tbody class="staff-directory-table-department">
        <tr><td class="staff-directory-table-department__title"><span>Football</span></td></tr>
        <tr class="staff-directory-table-member-position">
          <td class="staff-directory-table-member-position__name">Tavita Pritchard</td>
          <td class="staff-directory-table-member-position__position"><p>Bradford M. Freeman Director of Football</p></td>
        </tr>
        <tr class="staff-directory-table-member-position">
          <td class="staff-directory-table-member-position__name">Terry Heffernan</td>
          <td class="staff-directory-table-member-position__position"><p>Andrew Luck Director of Offense</p></td>
        </tr>
        <tr class="staff-directory-table-member-position">
          <td class="staff-directory-table-member-position__name">Kris Richard</td>
          <td class="staff-directory-table-member-position__position"><p>Willie Shaw Director of Defense &amp; Defensive Backs Coach</p></td>
        </tr>
        </tbody>
        </body></html>
        """
        people = parse_official_staff_html(
            html,
            page_url="https://gostanford.com/staff-directory?path=football",
            program_name="Stanford",
        )
        by_role = {}
        for row in people:
            by_role.setdefault(row["role"], []).append(row["person"])
        self.assertEqual(by_role.get("head_coach"), ["Tavita Pritchard"])
        self.assertEqual(by_role.get("offensive_coordinator"), ["Terry Heffernan"])
        self.assertEqual(by_role.get("defensive_coordinator"), ["Kris Richard"])

    def test_2026_season_infobox_lists_hc_oc_dc_as_wiki_candidates(self) -> None:
        wikitext = (
            "{{Infobox college football team\n"
            "|HeadCoach=[[Tavita Pritchard]]\n"
            "|OffCoach=[[Terry Heffernan]]\n"
            "|DefCoach=[[Kris Richard]]\n"
            "}}\n"
        )
        rows = parse_wikimedia_infobox(
            wikitext,
            revision_id="1",
            page_title="2026 Stanford Cardinal football team",
        )
        by_role = {row["role"]: row["person"] for row in rows}
        self.assertEqual(by_role["head_coach"], "Tavita Pritchard")
        self.assertEqual(by_role["offensive_coordinator"], "Terry Heffernan")
        self.assertEqual(by_role["defensive_coordinator"], "Kris Richard")
        self.assertTrue(all(row.get("pit_admitted") is False for row in rows))

    def test_football_directory_keeps_sole_head_coach_when_support_title_exists(
        self,
    ) -> None:
        html = """
        <html><head><title>Nebraska Athletics</title></head><body>
        <tbody class="staff-directory-table-department">
        <tr><td class="staff-directory-table-department__title"><span>Football</span></td></tr>
        <tr class="staff-directory-table-member-position">
          <td class="staff-directory-table-member-position__name">Matt Rhule</td>
          <td class="staff-directory-table-member-position__position"><p>Head Coach</p></td>
        </tr>
        <tr class="staff-directory-table-member-position">
          <td class="staff-directory-table-member-position__name">Halle Childers</td>
          <td class="staff-directory-table-member-position__position"><p>Head Coach Support/Staff Operations</p></td>
        </tr>
        <tr class="staff-directory-table-member-position">
          <td class="staff-directory-table-member-position__name">Dana Holgorsen</td>
          <td class="staff-directory-table-member-position__position"><p>Offensive Coordinator</p></td>
        </tr>
        </tbody>
        </body></html>
        """
        people = parse_official_staff_html(
            html,
            page_url="https://huskers.com/staff-directory/department/football",
            program_name="Nebraska",
        )
        hc = [row for row in people if row["role"] == "head_coach"]
        self.assertEqual([row["person"] for row in hc], ["Matt Rhule"])

    def test_endowed_football_chair_and_director_are_kept_as_head_coach(self) -> None:
        html = """
        <html><head><title>Vanderbilt Athletics</title></head><body>
        <tbody class="staff-directory-table-department">
        <tr><td class="staff-directory-table-department__title"><span>Football</span></td></tr>
        <tr class="staff-directory-table-member-position">
          <td class="staff-directory-table-member-position__name">Clark Lea</td>
          <td class="staff-directory-table-member-position__position"><p>E. Bronson Ingram Chair in Football</p></td>
        </tr>
        <tr class="staff-directory-table-member-position">
          <td class="staff-directory-table-member-position__name">Tim Beck</td>
          <td class="staff-directory-table-member-position__position"><p>Offensive Coordinator</p></td>
        </tr>
        </tbody>
        </body></html>
        """
        people = parse_official_staff_html(
            html,
            page_url="https://vucommodores.com/staff-directory?path=football",
            program_name="Vanderbilt",
        )
        self.assertEqual(
            [row["person"] for row in people if row["role"] == "head_coach"],
            ["Clark Lea"],
        )

    def test_arkansas_football_table_binds_head_coach(self) -> None:
        html = """
        <html><head><title>Arkansas Razorbacks</title></head><body>
        <table>
        <thead><tr><th> Baseball </th><th> Position </th></tr></thead>
        <tbody><tr><td> Other Person </td><td> Head Coach </td></tr></tbody>
        </table>
        <div data-coach-sport-category-id="273">
        <table>
        <thead><tr><th> Football </th><th> Position </th></tr></thead>
        <tbody>
        <tr><td><a href="/coache/ryan-silverfield/"> Ryan Silverfield </a></td><td> Head Coach </td></tr>
        <tr><td><a href="/coache/tim-cramsey/"> Tim Cramsey </a></td><td> Offensive Coordinator </td></tr>
        </tbody>
        </table>
        </div>
        </body></html>
        """
        people = parse_official_staff_html(
            html,
            page_url="https://arkansasrazorbacks.com/staff-directory?path=football",
            program_name="Arkansas",
        )
        self.assertEqual(
            [row["person"] for row in people if row["role"] == "head_coach"],
            ["Ryan Silverfield"],
        )

    def test_presto_all_sports_directory_keeps_head_coach_near_football_coordinators(
        self,
    ) -> None:
        html = """
        <html><head><title>Kentucky Athletics</title></head><body>
        <tr class="staff-directory_table_row">
          <td class="staff-directory_table_row_name"><div class="name">Mark Pope</div></td>
          <td class="staff-directory_table_row_title"><p>Head Coach</p></td>
        </tr>
        <tr class="staff-directory_table_row">
          <td class="staff-directory_table_row_name"><div class="name">Will Stein</div></td>
          <td class="staff-directory_table_row_title"><p>Head Coach</p></td>
        </tr>
        <tr class="staff-directory_table_row">
          <td class="staff-directory_table_row_name"><div class="name">Jay Bateman</div></td>
          <td class="staff-directory_table_row_title"><p>Defensive Coordinator</p></td>
        </tr>
        <tr class="staff-directory_table_row">
          <td class="staff-directory_table_row_name"><div class="name">Joe Sloan</div></td>
          <td class="staff-directory_table_row_title"><p>Offensive Coordinator</p></td>
        </tr>
        </body></html>
        """
        people = parse_official_staff_html(
            html,
            page_url="https://ukathletics.com/staff-directory?path=football",
            program_name="Kentucky",
        )
        self.assertEqual(
            [row["person"] for row in people if row["role"] == "head_coach"],
            ["Will Stein"],
        )


class Wiki32ExactManagerFixtures(unittest.TestCase):
    def test_wiki32_pos01_single_football_hc(self) -> None:
        text = "{{Infobox college football season\n| head_coach = [[Valid Coach]]\n}}"
        got = parse_wikimedia_infobox(
            text, revision_id="101", page_title="2020 Test football team"
        )
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["person"], "Valid Coach")
        self.assertFalse(got[0]["pit_admitted"])

    def test_wiki32_01_basketball_season_infobox_is_not_football_hc(self) -> None:
        text = (
            "{{Infobox college football season\n| head_coach = [[Valid Coach]]\n}}"
            "\n== Basketball ==\n"
            "{{Infobox college basketball season\n| head_coach = [[Basketball Coach]]\n}}"
        )
        got = parse_wikimedia_infobox(
            text, revision_id="102", page_title="2020 Test football team"
        )
        people = {row["person"] for row in got}
        self.assertIn("Valid Coach", people)
        self.assertNotIn("Basketball Coach", people)

    def test_wiki32_02_slash_separated_coordinators_are_both_kept(self) -> None:
        text = (
            "{{Infobox college football season\n"
            "| off_coach = [[First Coach]] / [[Second Coach]]\n}}"
        )
        got = parse_wikimedia_infobox(
            text, revision_id="103", page_title="2020 Test football team"
        )
        people = [row["person"] for row in got]
        self.assertEqual(people, ["First Coach", "Second Coach"])

    def test_wiki32_03_repeated_index_across_college_coach_templates(self) -> None:
        career = (
            "{{Infobox college coach\n| coach_years1 = 2000\n"
            "| coach_team1 = [[School A]] (OC)\n}}\n"
            "{{Infobox college coach\n| coach_years1 = 2020\n"
            "| coach_team1 = [[School B]] (DC)\n}}"
        )
        got = parse_infobox_college_coach(
            career, revision_id="104", page_title="Example Coach"
        )
        programs = [(row["program_raw"], row["start_year"]) for row in got]
        self.assertIn(("School A", 2000), programs)
        self.assertIn(("School B", 2020), programs)

    def test_wiki32_04_generic_and_wrong_year_pages_do_not_search(self) -> None:
        hist = _load_tool("acquire_cycle30_historical_wikimedia.py")
        for bound in (
            "Test University football",
            "2026 Test University football team",
        ):
            response = {
                "title": bound,
                "status": "REVISION_BOUND",
                "episodes": [{"person": "Example Coach"}],
            }
            with patch.object(hist, "fetch_title", return_value=response), patch.object(
                hist,
                "search_season_title",
                side_effect=AssertionError("should not access live search"),
            ):
                got = hist.fetch_season(
                    school="Test University",
                    year=1963,
                    guessed_title="1963 Test University football team",
                    ledger=[],
                )
            self.assertNotEqual(got.get("status"), "REVISION_BOUND")
            self.assertEqual(got.get("status"), "SEASON_UNSUPPORTED")
            self.assertEqual(got.get("episodes"), [])
            self.assertEqual(got.get("requested_season"), 1963)

    def test_wiki32_05_present_stops_at_revision_observation_year(self) -> None:
        graph = _load_tool("acquire_cycle30_wiki_coach_graph.py")
        episode = {
            "person": "Example Coach",
            "program_raw": "School A",
            "role": "offensive_coordinator",
            "start_year": 2009,
            "end_year": None,
            "ongoing": True,
            "source_year_text": "2009–present",
        }
        got = graph.expand_seasons(
            {
                "title": "Example Coach",
                "revision_timestamp": "2010-10-01T00:00:00Z",
                "episodes": [episode],
            }
        )
        seasons = [row["season"] for row in got]
        self.assertEqual(seasons, [2009, 2010])
        self.assertNotIn(2026, seasons)

    def test_wiki32_nested_nowrap_keeps_both_coordinators(self) -> None:
        text = (
            "{{Infobox college football season\n"
            "| off_coach = {{nowrap|[[First Coach]] / [[Second Coach]]}}\n}}"
        )
        got = parse_wikimedia_infobox(
            text, revision_id="105", page_title="2020 Test football team"
        )
        people = [row["person"] for row in got]
        self.assertEqual(people, ["First Coach", "Second Coach"])

    def test_wiki32_citation_span_is_not_field_verification(self) -> None:
        text = (
            "{{Infobox college football season\n"
            "| head_coach = [[Valid Coach]]<ref>{{cite web|title=Staff}}</ref>\n"
            "| off_coach = [[No Cite Coach]]\n}}"
        )
        got = parse_wikimedia_infobox(
            text, revision_id="106", page_title="2020 Test football team"
        )
        by_person = {row["person"]: row for row in got}
        self.assertTrue(by_person["Valid Coach"]["source_citation_spans"])
        self.assertEqual(by_person["No Cite Coach"]["source_citation_spans"], [])
        self.assertEqual(by_person["Valid Coach"]["factual_support"], "PARSED_ASSERTION")
        self.assertTrue(by_person["Valid Coach"]["citation_present_is_not_verification"])
        self.assertFalse(by_person["Valid Coach"]["pit_admitted"])

    def test_wiki32_college_coach_swapped_index_does_not_pair(self) -> None:
        career = (
            "{{Infobox college coach\n| coach_years1 = 2000\n"
            "| coach_team2 = [[School B]] (OC)\n"
            "| coach_years2 = 2020\n"
            "| coach_team1 = [[School A]] (HC)\n}}"
        )
        got = parse_infobox_college_coach(
            career, revision_id="107", page_title="Example Coach"
        )
        programs = {(row["program_raw"], row["start_year"], row["role"]) for row in got}
        self.assertEqual(
            programs,
            {("School A", 2000, "head_coach"), ("School B", 2020, "offensive_coordinator")},
        )

    def test_wiki32_college_coach_unpaired_index_is_not_zipped(self) -> None:
        career = (
            "{{Infobox college coach\n| coach_years1 = 2000\n"
            "| coach_team2 = [[School B]] (OC)\n}}"
        )
        got = parse_infobox_college_coach(
            career, revision_id="108", page_title="Example Coach"
        )
        self.assertEqual(got, [])

    def test_excluded_span_reason_codes_preserve_non_football_titles(self) -> None:
        html = (
            "<title>Football Coaches - Arizona State University Athletics</title>"
            "<div class='sidearm-roster-coach-name'>Willie Bloomquist</div>"
            "<div class='sidearm-roster-coach-title'>Head Coach, Baseball</div>"
            "<div class='sidearm-roster-coach-name'>Kenny Dillingham</div>"
            "<div class='sidearm-roster-coach-title'>Head Football Coach</div>"
        )
        excluded: list[dict[str, str]] = []
        rows = parse_official_staff_html(
            html,
            page_url="https://thesundevils.com/sports/football/coaches",
            program_name="Arizona State",
            excluded_spans=excluded,
        )
        people = {row["person"] for row in rows}
        self.assertIn("Kenny Dillingham", people)
        self.assertNotIn("Willie Bloomquist", people)
        self.assertTrue(
            any(
                row.get("person") == "Willie Bloomquist"
                and row.get("reason_code") == "NON_FOOTBALL_TITLE"
                for row in excluded
            )
        )

    def test_position_group_title_is_kept_as_other_position_not_oc(self) -> None:
        html = (
            "<title>Football Coaches - Florida Atlantic Athletics</title>"
            '<table><tbody>'
            '<tr class="s-table-body__row">'
            '<td><a href="/sports/football/roster/coaches/zach-kittley/1845">'
            "<span>Zach Kittley</span></a></td>"
            '<td class="s-table-body_cell"><span>Hagerty Family Head Football Coach</span></td>'
            "</tr>"
            '<tr class="s-table-body__row">'
            '<td><a href="/sports/football/roster/coaches/chris-perkins/1844">'
            "<span>Chris Perkins</span></a></td>"
            '<td class="s-table-body_cell"><span>Running Backs</span></td>'
            "</tr>"
            '<tr class="s-table-body__row">'
            '<td><a href="/sports/football/roster/coaches/brett-dewhurst/1846">'
            "<span>Brett Dewhurst</span></a></td>"
            '<td class="s-table-body_cell"><span>Defensive Coordinator</span></td>'
            "</tr>"
            "</tbody></table>"
        )
        rows = parse_official_staff_html(
            html,
            page_url="https://fausports.com/sports/football/coaches",
            program_name="Florida Atlantic",
        )
        by_person = {row["person"]: row for row in rows}
        self.assertEqual(by_person["Zach Kittley"]["role"], "head_coach")
        self.assertEqual(by_person["Brett Dewhurst"]["role"], "defensive_coordinator")
        self.assertEqual(by_person["Chris Perkins"]["role"], "OTHER_POSITION")
        self.assertEqual(by_person["Chris Perkins"]["title"], "Running Backs")
        self.assertFalse(any(row["role"] == "offensive_coordinator" for row in rows))

    def test_vue_zip_opposite_coordinator_has_exclusion_reason(self) -> None:
        people = [
            {
                "person": "P.J. Fleck",
                "title": "Head Coach",
                "span_id": "a",
                "page_url": "https://gophersports.com/sports/football/coaches",
            },
            {
                "person": "Greg Harbaugh Jr.",
                "title": "Offensive Coordinator",
                "span_id": "b",
                "page_url": "https://gophersports.com/sports/football/coaches",
            },
            {
                "person": "Greg Harbaugh Jr.",
                "title": "Defensive Coordinator / Safeties",
                "span_id": "c",
                "page_url": "https://gophersports.com/sports/football/coaches",
            },
            {
                "person": "Danny Collins",
                "title": "Defensive Coordinator",
                "span_id": "d",
                "page_url": "https://gophersports.com/sports/football/coaches",
            },
        ]
        excluded = excluded_official_role_spans(people, program_id="SRC-002:TEAM:135")
        self.assertTrue(
            any(
                row.get("person") == "Greg Harbaugh Jr."
                and row.get("role") == "defensive_coordinator"
                and row.get("reason_code") == "VUE_ZIP_OPPOSITE_COORDINATOR"
                for row in excluded
            )
        )

    def test_neutral_prior_margin_diff_swap_mirrors_team_keyed_probability(self) -> None:
        row = {
            "season": 2020,
            "home_canonical_team_id": "A",
            "away_canonical_team_id": "B",
            "home_win_label": True,
            "ordinary_home_exposure": 0,
            "site_class": "NEUTRAL",
            "home_features": {"pit_prior_margin_mean": 7.0},
            "away_features": {"pit_prior_margin_mean": -3.0},
        }
        swapped = swap_participants(row)
        self.assertEqual(swapped.get("ordinary_home_exposure"), 0)
        x_base, _, _, _ = design_matrix([row], "prior_margin_diff")
        x_swap, _, _, _ = design_matrix([swapped], "prior_margin_diff")
        weights = fit_logistic(x_base, [1.0], ridge=1.0)
        p_base = predict_proba(x_base, weights)
        p_swap = predict_proba(x_swap, weights)
        self.assertAlmostEqual(float(p_swap[0]), 1.0 - float(p_base[0]))
        x_home, _, _, _ = design_matrix([row], "prior_margin_diff_ordinary_home")
        x_home_swap, _, _, _ = design_matrix(
            [swapped], "prior_margin_diff_ordinary_home"
        )
        home_weights = fit_logistic(x_home, [1.0], ridge=1.0)
        p_home = predict_proba(x_home, home_weights)
        p_home_swap = predict_proba(x_home_swap, home_weights)
        self.assertAlmostEqual(float(p_home_swap[0]), 1.0 - float(p_home[0]))


class Cycle32CompletionContract(unittest.TestCase):
    def test_locally_failing_cannot_be_only_external_blocked(self) -> None:
        from aggie_analytics.cycle30.cycle_completion import (
            CycleCompletionError,
            cannot_mark_external_blocked_while_local_counterexample_fails,
        )

        with self.assertRaises(CycleCompletionError):
            cannot_mark_external_blocked_while_local_counterexample_fails(
                locally_failing=True, state="BLOCKED_EXTERNAL"
            )

    def test_placeholder_cannot_map_100(self) -> None:
        from aggie_analytics.cycle30.cycle_completion import (
            CycleCompletionError,
            cannot_map_placeholder_as_complete,
        )

        with self.assertRaises(CycleCompletionError):
            cannot_map_placeholder_as_complete(resolved=True, placeholder=True)

    def test_source_head_mismatch_fails(self) -> None:
        from aggie_analytics.cycle30.cycle_completion import (
            CycleCompletionError,
            require_source_head_match,
        )

        with self.assertRaises(CycleCompletionError):
            require_source_head_match(reported_head="aaa", actual_head="bbb")

    def test_missing_requirement_fails(self) -> None:
        from aggie_analytics.cycle30.cycle_completion import (
            CycleCompletionError,
            require_requirement_present,
        )

        with self.assertRaises(CycleCompletionError):
            require_requirement_present(["R32-01"], expected=["R32-01", "R32-02"])

    def test_invalid_state_fails(self) -> None:
        from aggie_analytics.cycle30.cycle_completion import (
            CycleCompletionError,
            validate_state,
        )

        with self.assertRaises(CycleCompletionError):
            validate_state("ALL_LOCAL_RECONSTRUCTION_COMPLETE")

    def test_skipped_required_test_cannot_pass(self) -> None:
        from aggie_analytics.cycle30.cycle_completion import (
            CycleCompletionError,
            cannot_pass_with_skipped_required_test,
        )

        with self.assertRaises(CycleCompletionError):
            cannot_pass_with_skipped_required_test(
                skipped_required=True, result="PASS"
            )

    def test_repeated_executions_are_not_unique_coverage(self) -> None:
        from aggie_analytics.cycle30.cycle_completion import unique_test_coverage

        self.assertEqual(unique_test_coverage(executions=120, unique_tests=58), 58)

    def test_forbidden_complete_headline(self) -> None:
        from aggie_analytics.cycle30.cycle_completion import (
            CycleCompletionError,
            validate_ledger,
        )

        with self.assertRaises(CycleCompletionError):
            validate_ledger(
                {
                    "headline": "CYCLE_COMPLETE",
                    "hold": "ACTIVE",
                    "git_head": "abc",
                    "actual_git_head": "aaa",
                    "requirements": [{"requirement_id": "R32-01", "state": "VERIFIED"}],
                    "expected_ids": ["R32-01"],
                }
            )


if __name__ == "__main__":
    unittest.main()
