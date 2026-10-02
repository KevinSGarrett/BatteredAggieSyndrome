"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-09: contest site, neutral status, venue support and travel.

The labels are the point of this module, so the tests pin them: a provider
venue-index match is never "independently confirmed" on its own, unknown
neutral status never becomes false, neutral removes the home term but not
travel, a missing coordinate is None rather than zero, and swapping the
designated sides swaps the legs and nothing else. The schedule-table
parsing is pinned on the three real formats that broke an earlier version.
"""

from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle37 import contest_site as site  # noqa: E402

VENUE = {"id": 1, "name": "Memorial Stadium (NE)", "city": "Lincoln", "state": "NE",
         "latitude": 40.8206, "longitude": -96.7056, "timezone": "America/Chicago"}
AWAY_VENUE = {"id": 2, "latitude": 34.0141, "longitude": -118.2879, "timezone": "America/Los_Angeles"}

PAGE = """
|{{CFB schedule entry
| date = September 2
| away = y
| opponent = [[2006 X team|X]]
| site_stadium = [[Memorial Stadium (Lincoln)|Memorial Stadium]]
| site_cityst = [[Lincoln, Nebraska|Lincoln, NE]]
|}}
|{{CFB schedule entry
| date = {{tooltip|September 9|Saturday}}
| site_stadium = Other Field
| site_cityst = Columbia SC
}}
|{{CFB schedule entry
| date = {{dow tooltip|January 1, 2007}}
| neutral = y
| site_stadium = [[Bowl Stadium]]
| site_cityst = [[Tampa, Florida|Tampa, FL]]<ref>{{cite web|date=January 3, 2007}}</ref>
}}
"""


class ParsingTests(unittest.TestCase):
    def test_every_entry_is_read_including_the_pipe_brace_closer(self) -> None:
        entries = site.parse_schedule_entries(PAGE)
        self.assertEqual([e["date_text"] for e in entries], ["September 2", "September 9", "January 1"])

    def test_flags_and_sites_are_kept_per_entry(self) -> None:
        first, second, third = site.parse_schedule_entries(PAGE)
        self.assertTrue(first["away"])
        self.assertFalse(second["away"])
        self.assertTrue(third["neutral"])
        self.assertEqual(first["site_stadium"], "Memorial Stadium")
        self.assertEqual(site.city_state(second["site_cityst"]), ("columbia", "SC"))
        self.assertEqual(site.city_state(third["site_cityst"]), ("tampa", "FL"))

    def test_a_citation_date_is_not_the_contest_date(self) -> None:
        self.assertEqual(site.date_field_text("September 3<ref>{{cite web|date=September 4, 2022}}</ref>"),
                         "September 3")

    def test_january_belongs_to_the_next_calendar_year(self) -> None:
        self.assertEqual(site.entry_date({"date_text": "January 1"}, 2006), date(2007, 1, 1))
        self.assertEqual(site.entry_date({"date_text": "September 2"}, 2006), date(2006, 9, 2))


class ConfirmationTests(unittest.TestCase):
    def entries(self):
        return site.parse_schedule_entries(PAGE)

    def test_date_and_city_confirm(self) -> None:
        result = site.confirm_contest(season=2006, start_utc="2006-09-02T19:30:00Z", venue=VENUE,
                                      entries=self.entries())
        self.assertEqual(result["state"], site.CONFIRM_SITE)
        self.assertIn("CITY", result["site_match_basis"])
        self.assertIn("STADIUM_NAME", result["site_match_basis"])

    def test_a_late_western_kickoff_is_read_in_the_venue_zone(self) -> None:
        # 03:30 UTC on the 3rd is the evening of the 2nd in Lincoln.
        result = site.confirm_contest(season=2006, start_utc="2006-09-03T03:30:00Z", venue=VENUE,
                                      entries=self.entries())
        self.assertEqual(result["feed_local_date"], "2006-09-02")
        self.assertEqual(result["date_tolerance_days"], 0)

    def test_a_different_city_is_a_conflict_not_a_confirmation(self) -> None:
        result = site.confirm_contest(season=2006, start_utc="2006-09-09T18:00:00Z", venue=VENUE,
                                      entries=self.entries())
        self.assertEqual(result["state"], site.CONFIRM_SITE_CONFLICT)

    def test_no_page_and_no_entry_are_distinct(self) -> None:
        self.assertEqual(site.confirm_contest(season=2006, start_utc="2006-10-01T18:00:00Z", venue=VENUE,
                                              entries=None)["state"], site.CONFIRM_NO_PAGE)
        self.assertEqual(site.confirm_contest(season=2006, start_utc="2006-10-21T18:00:00Z", venue=VENUE,
                                              entries=self.entries())["state"], site.CONFIRM_NO_ENTRY)

    def test_no_zone_is_guessed(self) -> None:
        _, basis = site.local_date("2006-09-02T19:30:00Z", None)
        self.assertEqual(basis, "UTC_DATE_NO_VENUE_TIMEZONE")


class LabelTests(unittest.TestCase):
    def test_a_provider_index_match_alone_is_not_independent(self) -> None:
        for state in (site.CONFIRM_NO_PAGE, site.CONFIRM_NO_ENTRY, site.CONFIRM_DATE_ONLY, site.CONFIRM_AMBIGUOUS):
            with self.subTest(state=state):
                self.assertEqual(site.venue_support(1, VENUE, {"state": state}), site.VENUE_PROVIDER_ONLY)
        self.assertEqual(site.venue_support(1, VENUE, {"state": site.CONFIRM_SITE}), site.VENUE_CONFIRMED)
        self.assertEqual(site.venue_support(None, None, {"state": site.CONFIRM_SITE}), site.VENUE_ABSENT)
        self.assertEqual(site.venue_support(9, None, {}), site.VENUE_UNRESOLVED)

    def test_unknown_neutral_stays_unknown(self) -> None:
        self.assertEqual(site.neutral_status(None), site.NEUTRAL_UNKNOWN)
        term = site.ordinary_home_term(site.NEUTRAL_UNKNOWN)
        self.assertIsNone(term["ordinary_home_term_applies"])
        self.assertIsNone(term["ordinary_home_term_magnitude"])

    def test_neutral_removes_the_home_term_only(self) -> None:
        self.assertEqual(site.ordinary_home_term(site.NEUTRAL_TRUE)["ordinary_home_term_magnitude"], 0.0)
        self.assertIsNone(site.ordinary_home_term(site.NEUTRAL_FALSE)["ordinary_home_term_magnitude"])


class TravelTests(unittest.TestCase):
    HOME = site.Origin(40.8206, -96.7056, "America/Chicago", venue_id=1)
    AWAY = site.Origin(34.0141, -118.2879, "America/Los_Angeles", venue_id=2)

    def row(self, *, neutral=True, home=HOME, away=AWAY, venue=VENUE):
        game = {"id": 7, "season": 2006, "startDate": "2006-09-16T19:00:00Z", "homeId": 1, "awayId": 2,
                "neutralSite": neutral, "venueId": 1}
        return site.contest_row(game=game, venue=venue, home=home, away=away,
                                confirmation={"state": site.CONFIRM_NO_PAGE}, previous={})

    def test_neutral_still_has_travel(self) -> None:
        row = self.row(neutral=True)
        self.assertEqual(row["legs_computed"], 2)
        self.assertGreater(row["away_leg"]["km"], 2000)
        self.assertEqual(row["ordinary_home_term_magnitude"], 0.0)

    def test_units_and_time_zone_shift(self) -> None:
        leg = self.row()["away_leg"]
        self.assertAlmostEqual(leg["miles"] * site.KM_PER_MILE, leg["km"], places=9)
        self.assertEqual(leg["tz_shift_hours"], 2.0)  # Pacific origin to a Central venue
        self.assertEqual(self.row()["home_leg"]["tz_shift_hours"], 0.0)

    def test_swapping_sides_swaps_the_legs_and_nothing_else(self) -> None:
        straight, swapped = self.row(), self.row(home=self.AWAY, away=self.HOME)
        self.assertEqual(straight["home_leg"]["km"], swapped["away_leg"]["km"])
        self.assertEqual(straight["away_leg"]["km"], swapped["home_leg"]["km"])
        self.assertEqual(straight["neutral_status"], swapped["neutral_status"])
        self.assertEqual(straight["venue_support"], swapped["venue_support"])

    def test_missing_coordinates_are_none_not_zero(self) -> None:
        row = self.row(venue={**VENUE, "latitude": None})
        self.assertIsNone(row["home_leg"]["km"])
        self.assertEqual(row["legs_computed"], 0)

    def test_a_nonfinite_or_impossible_coordinate_is_unknown_not_a_distance(self) -> None:
        for bad in (float("nan"), float("inf"), 123.0):
            with self.subTest(latitude=bad):
                row = self.row(venue={**VENUE, "latitude": bad})
                self.assertIsNone(row["home_leg"]["km"])
                self.assertEqual(row["home_leg"]["state"], "UNKNOWN_NONFINITE_OR_OUT_OF_RANGE_COORDINATE")

    def test_the_shift_follows_daylight_saving_at_kickoff(self) -> None:
        # Arizona keeps standard time; Los Angeles does not.
        origin = site.Origin(33.4, -112.0, "America/Phoenix")
        venue = {**AWAY_VENUE}
        september = site.leg(origin, venue, datetime(2006, 9, 16, 19, tzinfo=timezone.utc))
        november = site.leg(origin, venue, datetime(2006, 11, 18, 19, tzinfo=timezone.utc))
        self.assertEqual(september["tz_shift_hours"], 0.0)
        self.assertEqual(november["tz_shift_hours"], -1.0)
        self.assertGreater(september["km"], 0)

    def test_rest_days_count_only_earlier_contests(self) -> None:
        previous = {1: [datetime(2006, 9, 9, 19, tzinfo=timezone.utc), datetime(2006, 9, 16, 19, tzinfo=timezone.utc)]}
        self.assertEqual(site.rest_days(previous, 1, datetime(2006, 9, 16, 19, tzinfo=timezone.utc)), 7)
        self.assertIsNone(site.rest_days(previous, 5, datetime(2006, 9, 16, 19, tzinfo=timezone.utc)))



class SameSiteSpelledTwoWaysTests(unittest.TestCase):
    """v37.2: one stadium named two ways is not a site conflict (W37R-30)."""

    @staticmethod
    def confirm(venue: dict, stadium: str, cityst: str) -> dict:
        entry = {"date_text": "September 2", "away": False, "neutral": False, "site_stadium": stadium,
                 "site_cityst": cityst}
        return site.confirm_contest(season=2006, start_utc="2006-09-02T19:30:00Z", venue=venue, entries=[entry])

    def test_a_longer_official_name_of_the_same_stadium_confirms_in_the_same_state(self) -> None:
        wien = {"name": "Lawrence A. Wien Stadium", "city": "Manhattan", "state": "NY", "timezone": "America/New_York"}
        result = self.confirm(wien, "Robert K. Kraft Field at Lawrence A. Wien Stadium", "New York, NY")
        self.assertEqual(result["state"], site.CONFIRM_SITE)
        self.assertIn("STADIUM_NAME_TOKENS_SAME_STATE", result["site_match_basis"])
        self.assertIn("CITY_DECLARED_ALIAS_SAME_STATE", result["site_match_basis"])

    def test_an_initialism_confirms(self) -> None:
        ub = {"name": "UB Stadium", "city": "Amherst", "state": "NY", "timezone": "America/New_York"}
        self.assertEqual(self.confirm(ub, "University at Buffalo Stadium", "Buffalo, NY")["state"], site.CONFIRM_SITE)

    def test_a_state_name_without_a_comma_is_read(self) -> None:
        self.assertEqual(site.city_state("DeLand Florida"), ("deland", "FL"))

    def test_a_shared_word_in_another_state_is_still_a_conflict(self) -> None:
        nmsu = {"name": "Aggie Memorial Stadium", "city": "Las Cruces", "state": "NM", "timezone": "America/Denver"}
        self.assertEqual(self.confirm(nmsu, "Aggie Stadium", "Greensboro, NC")["state"], site.CONFIRM_SITE_CONFLICT)

    def test_generic_words_alone_never_match(self) -> None:
        self.assertFalse(site.stadium_tokens_match("War Memorial Stadium", "Memorial Stadium"))
        arkansas = {"name": "Razorback Stadium", "city": "Fayetteville", "state": "AR", "timezone": "America/Chicago"}
        self.assertEqual(self.confirm(arkansas, "War Memorial Stadium", "Little Rock, AR")["state"],
                         site.CONFIRM_SITE_CONFLICT)



class ZoneDatabaseTests(unittest.TestCase):
    """A missing time-zone database is refused, not read as a missing zone (W37R-53)."""

    def test_an_unknown_key_is_none_when_the_database_exists(self) -> None:
        self.assertIsNone(site.zone_or_none("Not/A_Zone"))

    def test_a_missing_database_is_refused(self) -> None:
        from unittest import mock
        from zoneinfo import ZoneInfoNotFoundError

        def unavailable(_name):
            raise ZoneInfoNotFoundError("no database")

        with mock.patch.object(site, "ZoneInfo", side_effect=unavailable), \
                mock.patch.object(site, "available_timezones", return_value=set()):
            with self.assertRaises(site.TimeZoneDatabaseUnavailable):
                site.zone_or_none("America/Chicago")
            with self.assertRaises(site.TimeZoneDatabaseUnavailable):
                site.local_date("2006-09-03T03:30:00Z", "America/Chicago")

    def test_no_declared_zone_is_still_none(self) -> None:
        self.assertIsNone(site.zone_or_none(None))


if __name__ == "__main__":
    unittest.main()
