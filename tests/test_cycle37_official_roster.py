"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-11: players and season read from an official roster page. Fixtures are
shaped like the cached roster pages; none is a claim about a player.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle37 import official_roster as ro  # noqa: E402


def nuxt_page(season_markup: str) -> str:
    # devalue: index 0 is the root list, which references the player object.
    data = [[1], {"firstName": 2, "lastName": 3, "jerseyNumber": 4, "positionShort": 5}, "Pat", "One", "0", "QB"]
    return (f"<html><head><title>Football - Example Athletics</title></head><body>{season_markup}"
            f'<script type="application/json" id="__NUXT_DATA__">{json.dumps(data)}</script></body></html>')


class RosterTests(unittest.TestCase):
    def test_a_nuxt_payload_is_decoded_exactly(self) -> None:
        parsed = ro.parse_roster(nuxt_page("<h1>2026 Football Roster</h1>"))
        self.assertEqual(parsed["method"], "NUXT_PAYLOAD")
        self.assertEqual([(p["name"], p["jersey"], p["position"]) for p in parsed["players"]], [("Pat One", "0", "QB")])
        self.assertEqual(parsed["season"], 2026)

    def test_a_roster_entry_wrapping_the_person_carries_the_number(self) -> None:
        # The person record states another number (a former season's); the roster entry's is used.
        # devalue: every value is an index into the array.
        data = [[1, 3], {"roster_id": 6, "jersey_number": 2, "player": 3}, "30",
                {"first_name": 4, "last_name": 5, "jersey_number": 7}, "Jo", "Three", 7, "4"]
        page = f'<script id="__NUXT_DATA__" type="application/json">{json.dumps(data)}</script>'
        self.assertEqual([(p["name"], p["jersey"]) for p in ro.parse_roster(page)["players"]], [("Jo Three", "30")])

    def test_entries_of_several_rosters_are_not_read_as_one(self) -> None:
        data = [[1, 4], {"roster_id": 6, "jersey_number": 2, "player": 3}, "30",
                {"first_name": 7, "last_name": 8, "jersey_number": -1},
                {"roster_id": 9, "jersey_number": 5, "player": 3}, "4", 7, "Jo", "Three", 8]
        page = f'<script id="__NUXT_DATA__" type="application/json">{json.dumps(data)}</script>'
        self.assertEqual(ro.parse_roster(page)["players"], [])

    def test_the_roster_container_class_states_the_season(self) -> None:
        page = nuxt_page('<div class="roster roster-sport-football roster-season-2026"><h2>Football 2026</h2></div>')
        self.assertEqual(ro.parse_roster(page)["season"], 2026)

    def test_a_page_that_states_no_season_has_none(self) -> None:
        self.assertIsNone(ro.parse_roster(nuxt_page("<h1>Football</h1>"))["season"])

    def test_another_sports_season_class_is_not_a_football_season(self) -> None:
        page = nuxt_page('<div class="roster roster-sport-baseball roster-season-2026"></div>')
        self.assertIsNone(ro.parse_roster(page)["season"])

    def test_a_table_needs_number_and_name_columns(self) -> None:
        page = ("<table><thead><tr><th>No.</th><th>Name</th><th>Pos.</th></tr></thead>"
                "<tbody><tr><td>7</td><td>Sam Two</td><td>WR</td></tr></tbody></table>")
        parsed = ro.parse_roster(page)
        self.assertEqual((parsed["method"], parsed["players"][0]["jersey"]), ("ROSTER_TABLE", "7"))
        self.assertEqual(ro.parse_roster("<table><thead><tr><th>Name</th></tr></thead></table>")["players"], [])


if __name__ == "__main__":
    unittest.main()
