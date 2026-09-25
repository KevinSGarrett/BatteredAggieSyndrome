"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-11: the rules the availability tool applies to rendered conference
reports, the schedule binding and the policy ledger. Fixtures are shaped like
the rendered report views; none is a claim about a player.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SPEC = importlib.util.spec_from_file_location("r37_11_availability", ROOT / "tools" / "cycle37" / "r37_11_availability.py")
av = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(av)

GAME = {"id": 7, "season": 2026, "homeTeam": "Kansas", "awayTeam": "Arizona State", "neutralSite": False,
        "conferenceGame": True, "startDate": "2026-09-19T23:30:00.000Z"}
INDEX = {tuple(sorted(("Kansas", "Arizona State"))): [GAME]}


class ContestBinding(unittest.TestCase):
    def test_both_teams_and_the_local_date_bind_one_contest(self) -> None:
        bound = av.bind_contest("Arizona State", "9/19/26 at Kansas", INDEX)
        self.assertEqual((bound["state"], bound["canonical_contest_id"]), ("CONTEST_BOUND", "SRC-002:GAME:7"))

    def test_an_evening_kickoff_on_the_next_utc_day_still_binds(self) -> None:
        late = {**GAME, "startDate": "2026-09-20T02:30:00.000Z"}
        bound = av.bind_contest("Kansas", "9/19/26 vs. Arizona State", {tuple(sorted(("Kansas", "Arizona State"))): [late]})
        self.assertEqual(bound["state"], "CONTEST_BOUND")

    def test_home_and_away_disagreement_is_reported(self) -> None:
        self.assertEqual(av.bind_contest("Arizona State", "9/19/26 vs. Kansas", INDEX)["state"],
                         "CONTEST_BOUND_ORIENTATION_DISAGREES")

    def test_a_label_naming_the_program_itself_is_not_guessed(self) -> None:
        bound = av.bind_contest("Kansas", "9/19/26 vs. Kansas", INDEX)
        self.assertEqual(bound["state"], "CONTEST_LABEL_NAMES_THE_PROGRAM_ITSELF")
        self.assertNotIn("canonical_contest_id", bound)

    def test_no_game_on_that_date_is_not_bound(self) -> None:
        self.assertEqual(av.bind_contest("Kansas", "10/3/26 vs. Arizona State", INDEX)["state"],
                         "CONTEST_NOT_UNIQUELY_IN_SCHEDULE_VINTAGE")


class VendorText(unittest.TestCase):
    def test_both_date_forms(self) -> None:
        self.assertEqual(av._vendor_date("9/12/26"), date(2026, 9, 12))
        self.assertEqual(av._vendor_date("Sat, Sep 12, 2026"), date(2026, 9, 12))
        self.assertIsNone(av._vendor_date("TBA"))

    def test_a_dash_is_a_published_empty_stage_not_a_status(self) -> None:
        self.assertIsNone(av._normalized("-"))
        self.assertEqual(av._normalized("Game Time Decision"), "GAME_TIME_DECISION")

    def test_a_posting_time_is_read_in_eastern_daylight_time(self) -> None:
        match = av._POSTED.search("INITIAL REPORT\nReport posted on Tuesday, September 22 at 11:00pm ET\nOUT")
        self.assertEqual(match.groups(), ("September", "22", "11", "00", "pm"))


class PolicyLedger(unittest.TestCase):
    def test_every_governing_policy_is_in_the_ledger(self) -> None:
        ids = {spec["policy_id"] for spec in av.POLICY_SOURCES}
        self.assertTrue(set(av.GOVERNING_2026.values()) <= ids)

    def test_no_policy_claims_fcs_or_an_absence_rule_it_does_not_quote(self) -> None:
        for spec in av.POLICY_SOURCES:
            with self.subTest(policy=spec["policy_id"]):
                self.assertNotIn("FCS", spec["conference"])
                if spec["absence_rule"] == "ABSENT_FROM_A_REPORT_PRESUMED_AVAILABLE":
                    self.assertTrue(any("not" in quote and ("listed" in quote or "included" in quote)
                                        for quote in spec["quotes"]))


if __name__ == "__main__":
    unittest.main()
