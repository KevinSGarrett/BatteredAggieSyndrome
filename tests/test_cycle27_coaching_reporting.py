"""Cycle 27 coaching census and staff-packet adversarial tests.

Isolated fixtures only. Coaches Poll is not staff; a head-coach boolean is not
full coverage; titles are not play-callers; missing is UNKNOWN not NONE; coach
bonuses are forbidden.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.context_intelligence.coaching import (  # noqa: E402
    manual_coach_bonus,
)
from aggie_analytics.data.cycle27_coaching_reporting import (  # noqa: E402
    FOCUS_AWAY_CANONICAL,
    FOCUS_CONTEST_ID,
    FOCUS_HOME_CANONICAL,
    UNKNOWN_NOT_NONE,
    _fetch_result,
    apply_coach_bonus,
    build_coaching_census,
    build_staff_context_packet,
    classify_feature_as_staff_evidence,
    classify_head_coach_presence_boolean,
    classify_missing_role,
    classify_page_identity,
    classify_title_versus_play_caller,
    inspect_source_acquisition_registry,
    parse_staff_directory_html,
)


def _spine_universe() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(91):
        contest = f"{6600000 + index}"
        if index == 0:
            contest = FOCUS_CONTEST_ID
            home = FOCUS_HOME_CANONICAL
            away = FOCUS_AWAY_CANONICAL
        else:
            home = f"SRC-002:TEAM:{1000 + index}"
            away = f"SRC-002:TEAM:{2000 + index}"
        for team, opponent, orientation in (
            (home, away, "HOME"),
            (away, home, "AWAY"),
        ):
            rows.append(
                {
                    "ncaa_contest_id": contest,
                    "canonical_team_id": team,
                    "opponent_canonical_team_id": opponent,
                    "source_team_id": team,
                    "season": 2026,
                    "site_orientation": orientation,
                    "conference_name": "SEC"
                    if team == FOCUS_HOME_CANONICAL
                    else "CUSA",
                    "subdivision": "FBS",
                }
            )
    return rows


class Cycle27CoachingReportingTests(unittest.TestCase):
    def test_coaches_poll_is_not_staff_evidence(self) -> None:
        poll = classify_feature_as_staff_evidence("coaches_poll_rank")
        missing = classify_feature_as_staff_evidence("coaches_poll_rank_missing")
        self.assertFalse(poll["is_staff_evidence"])
        self.assertEqual(poll["classification"], "COACHES_POLL_RANKING_NOT_STAFF")
        self.assertFalse(missing["is_staff_evidence"])
        self.assertNotEqual(poll["classification"], "NAMED_STAFF_OR_ROLE_FIELD")

    def test_head_coach_boolean_is_not_full_staff_coverage(self) -> None:
        classified = classify_head_coach_presence_boolean(True)
        self.assertTrue(classified["head_coach_evidence_present"])
        self.assertFalse(classified["full_staff_coverage"])
        self.assertFalse(classified["normalized_staff_history"])
        self.assertEqual(
            classified["classification"],
            "HEAD_COACH_CELL_NONEMPTY_BOOLEAN_NOT_STAFF_COVERAGE",
        )

    def test_title_is_not_play_caller(self) -> None:
        classified = classify_title_versus_play_caller("Offensive Coordinator")
        self.assertEqual(classified["title_role_id"], "OFFENSIVE_COORDINATOR")
        self.assertFalse(classified["title_is_play_caller_proof"])
        self.assertEqual(
            classified["play_caller_status"], "UNKNOWN_NOT_INFERRED_FROM_TITLE"
        )
        even_named = classify_title_versus_play_caller(
            "Offensive Coordinator / Play Caller"
        )
        self.assertTrue(even_named["title_mentions_play_caller"])
        self.assertFalse(even_named["title_is_play_caller_proof"])
        self.assertEqual(
            even_named["play_caller_status"], "UNKNOWN_NOT_INFERRED_FROM_TITLE"
        )
        associate = classify_title_versus_play_caller("Associate Head Coach")
        self.assertNotEqual(associate["title_role_id"], "HEAD_COACH")
        self.assertFalse(associate["title_is_play_caller_proof"])

    def test_missing_role_is_unknown_not_none(self) -> None:
        classified = classify_missing_role(None)
        self.assertEqual(classified["status"], UNKNOWN_NOT_NONE)
        self.assertFalse(classified["confirmed_absent"])
        self.assertFalse(classified["confirmed_none"])
        self.assertNotEqual(classified["status"], "NONE")
        self.assertNotEqual(classified["status"], "ABSENT")

    def test_coach_bonus_is_forbidden(self) -> None:
        with self.assertRaises(RuntimeError):
            apply_coach_bonus(3.0)
        with self.assertRaises(RuntimeError):
            manual_coach_bonus(points=7)

    def test_registry_without_coach_entry_is_source_absent(self) -> None:
        inspected = inspect_source_acquisition_registry(
            {
                "registry_status": "VERIFIED",
                "source_count": 1,
                "sources": [
                    {
                        "source_id": "CFBD",
                        "endpoints": [{"path": "/games"}, {"path": "/lines"}],
                    }
                ],
            }
        )
        self.assertFalse(inspected["coach_entry_present"])
        self.assertEqual(
            inspected["structured_coaching_route"], "SOURCE_ABSENT_NOT_REGISTERED"
        )

    def test_wrong_sport_page_is_conflict_not_staff_coverage(self) -> None:
        identity = classify_page_identity(
            "https://12thman.com/coaches.aspx?path=football",
            "https://12thman.com/sports/womens-golf/roster/season/2016-17/staff/trelle-mccombs",
            b"<html>golf staff</html>",
        )
        self.assertFalse(identity["ok"])
        self.assertEqual(identity["reason"], "WRONG_RESOURCE_REDIRECT")
        self.assertEqual(identity.get("detail"), "WRONG_SPORT_PAGE")
        fetched = _fetch_result(
            "https://12thman.com/coaches.aspx?path=football",
            200,
            b"<html>golf staff</html>",
            None,
            "2026-09-04T16:45:00Z",
            final_url=(
                "https://12thman.com/sports/womens-golf/roster/season/2016-17/"
                "staff/trelle-mccombs"
            ),
        )
        self.assertEqual(fetched["fetch_disposition"], "BLOCKED")
        self.assertNotEqual(fetched["fetch_disposition"], "RETRIEVED")
        self.assertEqual(fetched["page_identity"], "WRONG_RESOURCE_REDIRECT")
        self.assertEqual(fetched["error"], "WRONG_RESOURCE_REDIRECT")
        golf_url = (
            "https://12thman.com/sports/womens-golf/roster/season/2016-17/"
            "staff/trelle-mccombs"
        )
        packet = build_staff_context_packet(
            team_label="Texas A&M",
            canonical_team_id=FOCUS_HOME_CANONICAL,
            ncaa_contest_id=FOCUS_CONTEST_ID,
            urls=["https://12thman.com/coaches.aspx?path=football"],
            issued_at_utc="2026-09-04T16:45:00Z",
            registry_inspection={"coach_entry_present": False},
            opener=lambda url: (200, b"<html>golf staff</html>", "", golf_url),
        )
        self.assertEqual(packet["retrieved_count"], 0)
        self.assertEqual(packet["blocked_count"], 1)
        self.assertEqual(packet["title_observations"], [])

    def test_parser_does_not_infer_play_caller_from_title(self) -> None:
        html = """
        <div class="sidearm-roster-coach-name">Pat Example</div>
        <div class="sidearm-roster-coach-title">Offensive Coordinator</div>
        <div class="sidearm-roster-coach-name">Alex Example</div>
        <div class="sidearm-roster-coach-title">Head Coach</div>
        """
        people = parse_staff_directory_html(html)
        self.assertGreaterEqual(len(people), 2)
        for person in people:
            self.assertFalse(person["title_is_play_caller_proof"])
            self.assertEqual(person["consumption"], "NOT_CONSUMED_BY_MODEL")
            self.assertEqual(person["effective_date_status"], "UNKNOWN_NOT_SYNTHESIZED")
            self.assertIsNone(person["effective_from"])

    def test_vue_table_titles_are_not_play_callers(self) -> None:
        html = """
        <tr><td><span class="s-text-paragraph-small-bold text-theme-link-light underline">Casey Woods</span></td>
        <td><span>Head Coach</span></td></tr>
        <tr><td><span class="s-text-paragraph-small-bold text-theme-link-light underline">Mark Cala</span></td>
        <td><span>Offensive Coordinator / Quarterbacks</span></td></tr>
        <tr><td><span class="s-text-paragraph-small-bold text-theme-link-light underline">Jack Curtis</span></td>
        <td><span>Defensive Coordinator / Safeties</span></td></tr>
        """
        people = parse_staff_directory_html(html)
        roles = {person["title_role_id"]: person for person in people}
        self.assertEqual(roles["HEAD_COACH"]["source_person_name"], "Casey Woods")
        self.assertEqual(
            roles["OFFENSIVE_COORDINATOR"]["source_person_name"], "Mark Cala"
        )
        self.assertEqual(
            roles["DEFENSIVE_COORDINATOR"]["source_person_name"], "Jack Curtis"
        )
        for person in people:
            self.assertFalse(person["title_is_play_caller_proof"])
            self.assertEqual(
                person["play_caller_status"], "UNKNOWN_NOT_INFERRED_FROM_TITLE"
            )
            self.assertEqual(person["consumption"], "NOT_CONSUMED_BY_MODEL")
            self.assertIsNone(person["effective_from"])

    def test_census_does_not_claim_national_coverage_from_two_teams(self) -> None:
        def opener(url: str) -> tuple[int, bytes, str]:
            if "missouri" in url:
                html = (
                    b'<div class="sidearm-roster-coach-name">Casey Example</div>'
                    b'<div class="sidearm-roster-coach-title">Head Coach</div>'
                )
                return 200, html, ""
            return 404, b"", "HTTP Error 404: Not Found"

        home_packet = build_staff_context_packet(
            team_label="Texas A&M",
            canonical_team_id=FOCUS_HOME_CANONICAL,
            ncaa_contest_id=FOCUS_CONTEST_ID,
            urls=["https://example.test/tamu/coaches"],
            issued_at_utc="2026-09-04T16:45:00Z",
            registry_inspection={"coach_entry_present": False},
            opener=opener,
        )
        away_packet = build_staff_context_packet(
            team_label="Missouri State",
            canonical_team_id=FOCUS_AWAY_CANONICAL,
            ncaa_contest_id=FOCUS_CONTEST_ID,
            urls=["https://example.test/missouri/coaches"],
            issued_at_utc="2026-09-04T16:45:00Z",
            registry_inspection={"coach_entry_present": False},
            opener=opener,
        )
        self.assertEqual(home_packet["blocked_count"], 1)
        self.assertEqual(away_packet["retrieved_count"], 1)
        census = build_coaching_census(
            issued_at_utc="2026-09-04T16:45:00Z",
            spine_rows=_spine_universe(),
            feature_column_names=[
                "prior_games_played",
                "is_home",
                "coaches_poll_rank",
                "coaches_poll_rank_missing",
            ],
            fitted_design_columns={
                "ALL_ADMITTED_FEATURES": [
                    "intercept",
                    "prior_games_played",
                    "coaches_poll_rank",
                    "is_home",
                ]
            },
            acquisition_registry={"sources": [{"endpoints": [{"path": "/games"}]}]},
            domain_admission={
                "domains": [
                    {
                        "domain_id": "coaching_staff",
                        "decision": "SOURCE_ABSENT",
                        "known_at_basis": "SOURCE_ABSENT",
                        "evidence_route": "ABSENT",
                    }
                ]
            },
            authority_head_coach_boolean_retained=False,
            cycle26_successor_consumes_coaching=False,
            focus_packets={
                FOCUS_HOME_CANONICAL: home_packet,
                FOCUS_AWAY_CANONICAL: away_packet,
            },
        )
        self.assertEqual(census["universe"]["contest_count"], 91)
        self.assertEqual(census["universe"]["unique_team_seasons"], 182)
        self.assertFalse(census["national_coverage_claimed_from_two_focus_teams"])
        self.assertEqual(
            census["fitted_design"]["actual_model_consumption"], "NOT_CONSUMED"
        )
        self.assertEqual(census["counts"]["not_yet_audited_team_seasons"], 180)
        self.assertEqual(census["counts"]["not_consumed_team_seasons"], 182)
        self.assertEqual(
            census["national_domain_admission"]["decision"], "SOURCE_ABSENT"
        )
        json.dumps(census["counts"])

    def test_unresolved_source_is_not_labeled_canonical(self) -> None:
        rows = _spine_universe()
        rows[3]["canonical_team_id"] = None
        rows[3]["source_team_id"] = "622407"
        census = build_coaching_census(
            issued_at_utc="2026-09-04T16:45:00Z",
            spine_rows=rows,
            feature_column_names=["prior_games_played", "is_home"],
            fitted_design_columns={"ALL_ADMITTED_FEATURES": ["intercept"]},
            acquisition_registry={"sources": []},
            domain_admission={"domains": []},
            authority_head_coach_boolean_retained=False,
            cycle26_successor_consumes_coaching=False,
            focus_packets={
                FOCUS_HOME_CANONICAL: {"team_label": "Texas A&M"},
                FOCUS_AWAY_CANONICAL: {"team_label": "Missouri State"},
            },
        )
        unresolved = [
            row
            for row in census["team_seasons"]
            if row.get("source_team_id") == "622407"
        ]
        self.assertEqual(len(unresolved), 1)
        self.assertIsNone(unresolved[0]["canonical_team_id"])
        self.assertEqual(
            unresolved[0]["canonical_bind_state"], "UNRESOLVED_SOURCE_ENTITY"
        )
        self.assertNotEqual(unresolved[0]["canonical_team_id"], "622407")
        self.assertIn("unresolved_source", census["universe"]["deduplicated_on"][0])


if __name__ == "__main__":
    unittest.main()
