"""R36-11: jersey zero, surname suffixes and duplicate numbers, preserved.

Each of these was a real defect in an earlier cycle, so each gets a control
that fails if the fix is lost. The national denominator keeps every declared
program, including the ones whose conference publishes nothing.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.availability_identity import (  # noqa: E402
    AMBIGUOUS_JERSEY,
    AMBIGUOUS_NAME,
    CONFLICT,
    NO_MATCH,
    NO_REPORT_STATE,
    NO_ROSTER,
    RESOLVED_NAME_AND_JERSEY,
    RESOLVED_NAME_ONLY,
    RosterPlayer,
    normalize_jersey,
    policy_denominator,
    resolve_player,
    roster_from_rows,
    strip_suffix,
)

PROGRAM = "Alabama"


def player(pid, first, last, jersey, position="WR") -> RosterPlayer:
    return RosterPlayer(
        player_id=pid,
        program_id=PROGRAM,
        season=2026,
        first_name=first,
        last_name=last,
        jersey=normalize_jersey(jersey),
        position=position,
    )


ROSTER = [
    player("1", "AK", "Dear", "0"),
    player("2", "Sam", "Smith", "7"),
    player("3", "Chris", "Jones", "7", position="DL"),
    player("4", "Pat", "Doe", None),
    player("5", "Pat", "Doe", "41"),
    player("6", "Lee", "Ward", "22"),
    player("7", "Lee", "Ward Jr.", "23"),
]


class JerseyTests(unittest.TestCase):
    def test_jersey_zero_is_a_jersey(self) -> None:
        self.assertEqual(normalize_jersey("#0"), "0")
        self.assertEqual(normalize_jersey("0"), "0")
        self.assertEqual(normalize_jersey(0), "0")

    def test_absent_jersey_is_not_zero(self) -> None:
        for value in (None, "", "   ", "#", "n/a"):
            with self.subTest(value=value):
                self.assertIsNone(normalize_jersey(value))

    def test_a_player_wearing_zero_resolves(self) -> None:
        result = resolve_player(
            program=PROGRAM, player_name="AK Dear", jersey="#0", roster=ROSTER, season=2026
        )
        self.assertEqual(result["state"], RESOLVED_NAME_AND_JERSEY)
        self.assertEqual(result["canonical_player_id"], "1")


class SuffixTests(unittest.TestCase):
    def test_suffix_is_stripped_into_a_separate_key_not_discarded(self) -> None:
        self.assertEqual(strip_suffix("Lee Ward Jr."), "lee ward")
        result = resolve_player(
            program=PROGRAM, player_name="Lee Ward Jr.", jersey="23", roster=ROSTER, season=2026
        )
        self.assertEqual(result["state"], RESOLVED_NAME_AND_JERSEY)
        self.assertEqual(result["canonical_player_id"], "7")

    def test_father_and_son_are_not_merged_by_the_stripped_form(self) -> None:
        """Both carry 'lee ward' once stripped; only the jersey separates them."""

        elder = resolve_player(
            program=PROGRAM, player_name="Lee Ward", jersey="22", roster=ROSTER, season=2026
        )
        younger = resolve_player(
            program=PROGRAM, player_name="Lee Ward Jr.", jersey="23", roster=ROSTER, season=2026
        )
        self.assertEqual(elder["canonical_player_id"], "6")
        self.assertEqual(younger["canonical_player_id"], "7")
        self.assertNotEqual(elder["canonical_player_id"], younger["canonical_player_id"])

    def test_a_suffix_only_match_is_marked_lower_confidence(self) -> None:
        result = resolve_player(
            program=PROGRAM, player_name="Lee Ward III", jersey="23", roster=ROSTER, season=2026
        )
        self.assertTrue(result["matched_on_suffix_stripped_name_only"])
        self.assertEqual(result["confidence"], "MEDIUM_SUFFIX_STRIPPED")


class AmbiguityTests(unittest.TestCase):
    def test_duplicate_jersey_alone_does_not_resolve(self) -> None:
        result = resolve_player(
            program=PROGRAM, player_name="Nobody Here", jersey="7", roster=ROSTER, season=2026
        )
        self.assertEqual(result["state"], AMBIGUOUS_JERSEY)
        self.assertIsNone(result["canonical_player_id"])

    def test_duplicate_jersey_with_an_agreeing_name_resolves(self) -> None:
        result = resolve_player(
            program=PROGRAM, player_name="Chris Jones", jersey="7", roster=ROSTER, season=2026
        )
        self.assertEqual(result["canonical_player_id"], "3")

    def test_name_and_jersey_pointing_apart_is_a_conflict(self) -> None:
        result = resolve_player(
            program=PROGRAM, player_name="Sam Smith", jersey="22", roster=ROSTER, season=2026
        )
        self.assertEqual(result["state"], CONFLICT)
        self.assertIsNone(result["canonical_player_id"])

    def test_duplicate_name_without_a_jersey_is_ambiguous(self) -> None:
        result = resolve_player(
            program=PROGRAM, player_name="Pat Doe", jersey=None, roster=ROSTER, season=2026
        )
        self.assertEqual(result["state"], AMBIGUOUS_NAME)

    def test_unknown_name_does_not_match_the_nearest_player(self) -> None:
        result = resolve_player(
            program=PROGRAM, player_name="Samuel Smithers", jersey=None, roster=ROSTER, season=2026
        )
        self.assertEqual(result["state"], NO_MATCH)

    def test_no_roster_for_the_program(self) -> None:
        result = resolve_player(
            program="Some Other School", player_name="AK Dear", jersey="0", roster=ROSTER, season=2026
        )
        self.assertEqual(result["state"], NO_ROSTER)

    def test_unique_name_without_a_jersey_resolves_at_lower_confidence(self) -> None:
        result = resolve_player(
            program=PROGRAM, player_name="Sam Smith", jersey=None, roster=ROSTER, season=2026
        )
        self.assertEqual(result["state"], RESOLVED_NAME_ONLY)
        self.assertEqual(result["confidence"], "MEDIUM")


class ScopeTests(unittest.TestCase):
    """MF36-08: a roster row must be this program's, in this season."""

    def test_an_empty_program_row_from_1999_does_not_resolve_a_2026_statement(self) -> None:
        stray = RosterPlayer(player_id="99", program_id="", season=1999, first_name="AK", last_name="Dear",
                             jersey="0", position="WR")
        result = resolve_player(program="Georgia", player_name="AK Dear", jersey="0", roster=[stray],
                                season=2026)
        self.assertIsNone(result["canonical_player_id"])
        self.assertEqual(result["refused_rows_without_a_program"], 1)

    def test_a_wrong_season_row_of_the_same_program_does_not_resolve(self) -> None:
        old = RosterPlayer(player_id="98", program_id=PROGRAM, season=2019, first_name="AK", last_name="Dear",
                           jersey="0", position="WR")
        result = resolve_player(program=PROGRAM, player_name="AK Dear", jersey="0", roster=[old], season=2026)
        self.assertEqual(result["state"], NO_ROSTER)
        self.assertEqual(result["refused_rows_of_this_program_in_another_season"], 1)

    def test_a_statement_without_a_season_or_program_is_not_resolved(self) -> None:
        from aggie_analytics.cycle36.availability_identity import NO_PROGRAM, NO_SEASON

        self.assertEqual(resolve_player(program=PROGRAM, player_name="AK Dear", jersey="0",
                                        roster=ROSTER)["state"], NO_SEASON)
        self.assertEqual(resolve_player(program="", player_name="AK Dear", jersey="0", roster=ROSTER,
                                        season=2026)["state"], NO_PROGRAM)


class DenominatorTests(unittest.TestCase):
    def test_no_report_conferences_stay_in_the_denominator(self) -> None:
        rows = [
            {"conference": "SEC", "policy_status": "KNOWN_PUBLIC_POLICY"},
            {"conference": "SEC", "policy_status": "KNOWN_PUBLIC_POLICY"},
            {"conference": "Big Sky", "policy_status": "FCS_VARIES_BY_PROGRAM"},
            {"conference": "Ivy", "policy_status": "UNKNOWN_POLICY"},
        ]
        result = policy_denominator(rows)
        self.assertEqual(result["declared_programs"], 4)
        self.assertEqual(result["by_conference"]["Big Sky"]["programs"], 1)
        self.assertEqual(
            result["by_conference"]["Big Sky"]["with_known_public_policy"], 0
        )
        self.assertEqual(result["no_report_state"], NO_REPORT_STATE)

    def test_no_report_is_never_healthy(self) -> None:
        self.assertEqual(NO_REPORT_STATE, "UNKNOWN_NOT_HEALTHY")

    def test_roster_rows_load_with_jersey_normalisation(self) -> None:
        players = roster_from_rows(
            [
                {
                    "id": "9",
                    "team": PROGRAM,
                    "source_year": "2026",
                    "firstName": "Zero",
                    "lastName": "Player",
                    "jersey": 0,
                }
            ]
        )
        self.assertEqual(players[0].jersey, "0")


if __name__ == "__main__":
    unittest.main()
