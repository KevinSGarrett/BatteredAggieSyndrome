"""R36-09: vintage selection must not depend on filename or input order.

The manager's probe (``VENUE_VINTAGE_PROBE.json``) held the same two
observations in two files and swapped which one sorted first, getting
``Old Venue`` once and ``New Venue`` the other time. These tests reproduce
that shape and require the answer to be a function of the declared vintage
alone.
"""

from __future__ import annotations

import itertools
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.venue_vintage import (  # noqa: E402
    CONFLICT_SAME_VINTAGE,
    EARTH_RADIUS_KM,
    NEUTRAL_SOURCE_DESIGNATED,
    NEUTRAL_SOURCE_NOT_NEUTRAL,
    NEUTRAL_UNKNOWN,
    NO_KNOWN_VINTAGE,
    POLICY_EARLIEST,
    POLICY_LATEST,
    SELECTED,
    great_circle_km,
    observations_from_payloads,
    ordinary_home_advantage_state,
    select_home_geography,
    travel_for_contest,
)

OLD = (
    2019,
    "digest-old",
    "old_sorts_first.json",
    [
        {
            "id": 1,
            "location": {
                "id": 10,
                "name": "Old Venue",
                "latitude": 30.0,
                "longitude": -90.0,
            },
        }
    ],
)
NEW = (
    2026,
    "digest-new",
    "new_sorts_first.json",
    [
        {
            "id": 1,
            "location": {
                "id": 20,
                "name": "New Venue",
                "latitude": 40.0,
                "longitude": -80.0,
            },
        }
    ],
)


class VintageSelectionTests(unittest.TestCase):
    def test_permuting_inputs_cannot_change_the_answer(self) -> None:
        answers = set()
        for order in itertools.permutations([OLD, NEW]):
            selected = select_home_geography(observations_from_payloads(order))
            answers.add(
                (
                    selected[1]["state"],
                    selected[1]["home_venue_id"],
                    selected[1]["latitude"],
                )
            )
        self.assertEqual(len(answers), 1, answers)

    def test_latest_declared_year_wins_not_first_filename(self) -> None:
        selected = select_home_geography(observations_from_payloads([OLD, NEW]))
        self.assertEqual(selected[1]["state"], SELECTED)
        self.assertEqual(selected[1]["home_venue_name"], "New Venue")
        self.assertEqual(selected[1]["selected_declared_year"], 2026)

    def test_earliest_policy_is_explicit_and_different(self) -> None:
        selected = select_home_geography(
            observations_from_payloads([OLD, NEW]), policy=POLICY_EARLIEST
        )
        self.assertEqual(selected[1]["home_venue_name"], "Old Venue")
        self.assertEqual(selected[1]["selected_declared_year"], 2019)

    def test_same_vintage_disagreement_fails_closed(self) -> None:
        conflicting = (
            2026,
            "digest-other",
            "other.json",
            [
                {
                    "id": 1,
                    "location": {
                        "id": 77,
                        "name": "Third Venue",
                        "latitude": 41.0,
                        "longitude": -81.0,
                    },
                }
            ],
        )
        selected = select_home_geography(
            observations_from_payloads([NEW, conflicting])
        )
        self.assertEqual(selected[1]["state"], CONFLICT_SAME_VINTAGE)
        self.assertIsNone(selected[1]["latitude"])
        self.assertEqual(len(selected[1]["candidates"]), 2)

    def test_identical_readings_at_one_vintage_are_not_a_conflict(self) -> None:
        duplicate = (2026, "digest-copy", "copy.json", NEW[3])
        selected = select_home_geography(observations_from_payloads([NEW, duplicate]))
        self.assertEqual(selected[1]["state"], SELECTED)

    def test_unknown_acquisition_year_cannot_be_ranked(self) -> None:
        undated = (None, "digest-undated", "undated.json", NEW[3])
        selected = select_home_geography(observations_from_payloads([undated]))
        self.assertEqual(selected[1]["state"], NO_KNOWN_VINTAGE)
        self.assertIsNone(selected[1]["latitude"])

    def test_unknown_policy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            select_home_geography([], policy="WHATEVER_SORTS_FIRST")


class GeodesicTests(unittest.TestCase):
    def test_independent_reference_distance(self) -> None:
        """College Station to Lambeau Field, checked against an independent value.

        Computed from the declared sphere radius with the haversine formula
        written out here rather than by calling the module under test.
        """

        import math

        lat1, lon1 = 30.6100, -96.3400   # Kyle Field
        lat2, lon2 = 44.5013, -88.0622   # Lambeau Field
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi, dlam = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        )
        expected = 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
        self.assertAlmostEqual(great_circle_km(lat1, lon1, lat2, lon2), expected, places=9)
        # ~1706 km; the band is wide enough to survive a coordinate
        # refinement and narrow enough to catch a unit or formula error.
        self.assertGreater(expected, 1650)
        self.assertLess(expected, 1760)

    def test_zero_distance_only_for_the_same_point(self) -> None:
        self.assertEqual(great_circle_km(30.0, -90.0, 30.0, -90.0), 0.0)


HOME_GEOGRAPHY = {
    194: {"state": SELECTED, "latitude": 41.8781, "longitude": -87.6298},   # Notre Dame stand-in
    275: {"state": SELECTED, "latitude": 43.0753, "longitude": -89.4066},   # Wisconsin, Madison
    999: {"state": NO_KNOWN_VINTAGE, "latitude": None, "longitude": None},
}
LAMBEAU = (44.5013, -88.0622)


class NeutralAndTravelTests(unittest.TestCase):
    def test_lambeau_fixture_has_two_legs_and_no_ordinary_hfa(self) -> None:
        """Notre Dame/Wisconsin at Lambeau: a designated home that is not home.

        The designated-home label cannot locate this game -- the venue is a
        third city -- so both sides travel and ordinary home advantage is
        suppressed by the source's neutral designation.
        """

        result = travel_for_contest(
            home_team_id=275,
            away_team_id=194,
            venue_point=LAMBEAU,
            home_geography=HOME_GEOGRAPHY,
            neutral_status=NEUTRAL_SOURCE_DESIGNATED,
        )
        self.assertEqual(result["legs_computed"], 2)
        self.assertGreater(result["home_leg"]["km"], 100)
        self.assertGreater(result["away_leg"]["km"], 100)
        self.assertEqual(result["ordinary_home_advantage_magnitude"], 0.0)
        self.assertFalse(result["ordinary_home_advantage_applies"])

    def test_swapping_sides_swaps_legs_and_keeps_the_venue(self) -> None:
        one = travel_for_contest(
            home_team_id=275,
            away_team_id=194,
            venue_point=LAMBEAU,
            home_geography=HOME_GEOGRAPHY,
            neutral_status=NEUTRAL_SOURCE_DESIGNATED,
        )
        other = travel_for_contest(
            home_team_id=194,
            away_team_id=275,
            venue_point=LAMBEAU,
            home_geography=HOME_GEOGRAPHY,
            neutral_status=NEUTRAL_SOURCE_DESIGNATED,
        )
        self.assertEqual(one["venue_point"], other["venue_point"])
        self.assertAlmostEqual(one["home_leg"]["km"], other["away_leg"]["km"], places=9)
        self.assertAlmostEqual(one["away_leg"]["km"], other["home_leg"]["km"], places=9)

    def test_unknown_neutral_status_fails_closed(self) -> None:
        state = ordinary_home_advantage_state(NEUTRAL_UNKNOWN)
        self.assertIsNone(state["ordinary_home_advantage_applies"])
        self.assertIsNone(state["ordinary_home_advantage_magnitude"])

    def test_ordinary_home_game_magnitude_is_not_zero(self) -> None:
        state = ordinary_home_advantage_state(NEUTRAL_SOURCE_NOT_NEUTRAL)
        self.assertTrue(state["ordinary_home_advantage_applies"])
        self.assertIsNone(state["ordinary_home_advantage_magnitude"])

    def test_missing_origin_leaves_the_leg_unknown_not_zero(self) -> None:
        result = travel_for_contest(
            home_team_id=999,
            away_team_id=194,
            venue_point=LAMBEAU,
            home_geography=HOME_GEOGRAPHY,
            neutral_status=NEUTRAL_SOURCE_DESIGNATED,
        )
        self.assertIsNone(result["home_leg"]["km"])
        self.assertEqual(result["legs_computed"], 1)

    def test_missing_venue_leaves_both_legs_unknown(self) -> None:
        result = travel_for_contest(
            home_team_id=275,
            away_team_id=194,
            venue_point=None,
            home_geography=HOME_GEOGRAPHY,
            neutral_status=NEUTRAL_UNKNOWN,
        )
        self.assertEqual(result["legs_computed"], 0)
        self.assertIsNone(result["ordinary_home_advantage_magnitude"])


if __name__ == "__main__":
    unittest.main()
