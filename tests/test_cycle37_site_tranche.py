"""Cycle #37 - Attempt #2 - ACTUAL_STATE: the official-schedule parser of the W37R-30 site tranche."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cycle37" / "r37_09_site_tranche.py"


def _load():
    spec = importlib.util.spec_from_file_location("r37_09_site_tranche", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _game(classes: str, date: str, location: str, opponent: str) -> str:
    return (f'<li class="sidearm-schedule-game {classes}" data-game-id="1"><div>'
            f'<span class="sidearm-schedule-game-opponent-date flex-item-1"> <span>{date}</span> </span>'
            f'<div class="sidearm-schedule-game-location"> <span>{location}</span> </div>'
            f'<span class="sidearm-schedule-game-opponent-name"><a href="#">{opponent}</a></span>'
            f'</div></li>')


PAGE = ('<ul class="sidearm-schedule-games-container">'
        + _game("sidearm-schedule-away-game", "Aug 30 (Thu)", "Little Rock, Ark.", "UNLV")
        + _game("sidearm-schedule-home-game", "Sep 8 (Sat)", "Fayetteville, Ark.", "Boise State")
        + _game("sidearm-schedule-neutral-game", "Jan 1 (Tue)", "Dallas, Texas", "Bowl Opponent")
        + _game("sidearm-schedule-home-game", "TBA", "Fayetteville, Ark.", "Undated")
        + "</ul>")


class ScheduleParserTests(unittest.TestCase):
    """Dates, cities and sides come from the page's own entries; undated entries are dropped."""

    def test_entries_carry_date_city_side_and_opponent(self) -> None:
        tool = _load()
        entries = tool.parse_sidearm(PAGE, 2001)
        self.assertEqual([e["date"] for e in entries], ["2001-08-30", "2001-09-08", "2002-01-01"])
        self.assertEqual([e["city"] for e in entries], ["little rock", "fayetteville", "dallas"])
        self.assertEqual([e["side"] for e in entries], ["AWAY", "HOME", "NEUTRAL"])
        self.assertEqual(entries[0]["opponent"], "UNLV")

    def test_a_page_without_sidearm_entries_yields_nothing(self) -> None:
        tool = _load()
        self.assertEqual(tool.parse_sidearm("<html><body>schedule loads by script</body></html>", 2001), [])

    def test_city_normalisation_is_exact_after_case_and_punctuation(self) -> None:
        tool = _load()
        self.assertEqual(tool.norm_city("St. Louis"), "st louis")
        self.assertNotEqual(tool.norm_city("Saint Louis"), tool.norm_city("St. Louis"))


NESTED = ('<ul class="sidearm-schedule-games-container">'
          '<li class="sidearm-schedule-game sidearm-schedule-home-game"><div>'
          '<span class="sidearm-schedule-game-opponent-date flex-item-1"> <span>Nov 5 (Sat)</span> </span>'
          '<div class="sidearm-schedule-game-location"> <span></span> </div>'
          '<ul class="sidearm-schedule-game-links"><li>Box score</li></ul>'
          '<div class="sidearm-schedule-game-location"> <span>Daytona Beach, FL</span> <span>Stadium</span> </div>'
          '</div></li></ul>')

CARDS = ('<div class="s-game-card relative"><time>Sep 04</time> vs Bowling Green '
         '<svg class="s-icon s-icon-location"><path d="M0"/></svg><span>Norman, Okla.</span></div>'
         '<div class="s-game-card relative"><time>Oct 09</time> vs Texas '
         '<svg class="s-icon s-icon-location"><path d="M0"/></svg><span>Dallas, Texas</span></div>')


class LayoutTests(unittest.TestCase):
    """The first non-empty location of an entry is read, past nested lists; the card layout is read too."""

    def test_an_empty_first_location_block_and_a_nested_list_do_not_hide_the_location(self) -> None:
        tool = _load()
        entries = tool.parse_sidearm(NESTED, 2022)
        self.assertEqual([(e["date"], e["city"]) for e in entries], [("2022-11-05", "daytona beach")])

    def test_game_cards_give_date_and_city(self) -> None:
        tool = _load()
        entries = tool.parse_sidearm(CARDS, 2004)
        self.assertEqual([(e["date"], e["city"], e["side"]) for e in entries],
                         [("2004-09-04", "norman", "HOME"), ("2004-10-09", "dallas", "HOME")])


if __name__ == "__main__":
    unittest.main()
