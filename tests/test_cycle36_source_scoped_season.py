"""R36-03: the season a staff record is dated by must govern that record.

The five fixtures the Cycle #35 manager review used are reproduced verbatim
(``ADVERSARIAL_PROBE_RESULTS.json``): one positive control and four negative
controls that the predecessor bound to 2026. New cases cover the wrong sport,
the wrong school's section, several season sections on one page, and a
conflict inside a single heading.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.source_scoped_season import (  # noqa: E402
    BOUND_ANNOUNCEMENT,
    BOUND_HEADING,
    CTX_CHROME,
    CTX_COMMENT,
    CTX_PROSE,
    CTX_SCRIPT,
    UNBOUND_CONFLICT,
    UNBOUND_NO_ADMISSIBLE,
    UNBOUND_OUT_OF_SCOPE,
    scan_capture,
    season_evidence_for_capture,
    season_for_record,
)

#: Byte-for-byte the manager's synthetic probes.
MANAGER_FIXTURES = {
    "positive": (
        "<h1>2026 Football Coaching Staff</h1><table><tr><td>A Person</td>"
        "<td>Head Coach</td></tr></table>"
    ),
    "comment_only": (
        "<!-- archived 2026 Football Coaching Staff --><h1>Football Staff</h1>"
        "<table><tr><td>A Person</td><td>Head Coach</td></tr></table>"
    ),
    "script_only": (
        '<script>var previousTitle="2026 Football Coaching Staff";</script>'
        "<h1>Football Staff</h1>"
    ),
    "archive_navigation": (
        '<nav><a href="/2026">2026 Football Coaching Staff</a></nav>'
        "<h1>Football Staff</h1>"
    ),
    "biography": (
        "<h1>Football Staff</h1><p>He joined the 2026 football staff before "
        "moving to this school.</p>"
    ),
}


def _bind(markup: str, needle: str = "A Person") -> dict:
    offset = markup.find(needle)
    scanned = scan_capture(markup)
    return season_for_record(scanned, offset if offset >= 0 else None)


class ManagerFixtureTests(unittest.TestCase):
    def test_positive_control_still_binds(self) -> None:
        result = _bind(MANAGER_FIXTURES["positive"])
        self.assertEqual(result["state"], BOUND_HEADING)
        self.assertEqual(result["bound_season"], 2026)

    def test_comment_year_does_not_bind(self) -> None:
        result = _bind(MANAGER_FIXTURES["comment_only"])
        self.assertEqual(result["state"], UNBOUND_NO_ADMISSIBLE)
        self.assertIsNone(result["bound_season"])
        self.assertIn(
            CTX_COMMENT, {label["context"] for label in result["labels"]}
        )

    def test_script_year_does_not_bind(self) -> None:
        result = _bind(MANAGER_FIXTURES["script_only"], needle="Football Staff")
        self.assertEqual(result["state"], UNBOUND_NO_ADMISSIBLE)
        self.assertIn(CTX_SCRIPT, {label["context"] for label in result["labels"]})

    def test_archive_navigation_year_does_not_bind(self) -> None:
        result = _bind(MANAGER_FIXTURES["archive_navigation"], needle="Football Staff")
        self.assertEqual(result["state"], UNBOUND_NO_ADMISSIBLE)
        self.assertIn(CTX_CHROME, {label["context"] for label in result["labels"]})

    def test_biography_year_does_not_bind(self) -> None:
        markup = MANAGER_FIXTURES["biography"]
        result = _bind(markup, needle="He joined")
        self.assertEqual(result["state"], UNBOUND_NO_ADMISSIBLE)
        self.assertIn(CTX_PROSE, {label["context"] for label in result["labels"]})

    def test_every_manager_fixture_matches_its_expectation(self) -> None:
        expected = {
            "positive": 2026,
            "comment_only": None,
            "script_only": None,
            "archive_navigation": None,
            "biography": None,
        }
        for name, markup in MANAGER_FIXTURES.items():
            with self.subTest(fixture=name):
                offset = markup.find("A Person")
                result = season_for_record(
                    scan_capture(markup), offset if offset >= 0 else 0
                )
                self.assertEqual(result["bound_season"], expected[name])


class NewNegativeControlTests(unittest.TestCase):
    def test_another_sport_section_does_not_bind_football(self) -> None:
        markup = (
            "<h1>2025 Women&#39;s Basketball Coaching Staff</h1>"
            "<table><tr><td>A Person</td></tr></table>"
        )
        self.assertIsNone(_bind(markup)["bound_season"])

    def test_wrong_school_section_dates_only_its_own_rows(self) -> None:
        markup = (
            "<h2>2026 Football Staff</h2><table><tr><td>A Person</td></tr></table>"
            "<h2>Rival University 2023 Football Staff</h2>"
            "<table><tr><td>B Person</td></tr></table>"
        )
        self.assertEqual(_bind(markup, "A Person")["bound_season"], 2026)
        self.assertEqual(_bind(markup, "B Person")["bound_season"], 2023)

    def test_several_season_sections_bind_per_record(self) -> None:
        markup = (
            "<h2>2026 Football Staff</h2><table><tr><td>A Person</td></tr></table>"
            "<h2>2025 Football Staff</h2><table><tr><td>B Person</td></tr></table>"
        )
        self.assertEqual(_bind(markup, "A Person")["bound_season"], 2026)
        self.assertEqual(_bind(markup, "B Person")["bound_season"], 2025)

    def test_two_seasons_in_one_heading_are_a_conflict(self) -> None:
        markup = (
            "<h1>2026 Football Coaching Staff and 2024 Football Coaching Staff</h1>"
            "<table><tr><td>A Person</td></tr></table>"
        )
        result = _bind(markup)
        self.assertEqual(result["state"], UNBOUND_CONFLICT)
        self.assertEqual(result["conflicting_seasons"], [2024, 2026])

    def test_attribute_value_is_not_rendered_text(self) -> None:
        markup = (
            '<div data-season="2026 Football Coaching Staff"><h1>Football Staff</h1>'
            "<table><tr><td>A Person</td></tr></table></div>"
        )
        self.assertEqual(_bind(markup)["state"], UNBOUND_NO_ADMISSIBLE)

    def test_template_subtree_is_not_rendered_text(self) -> None:
        markup = (
            "<template><h1>2026 Football Coaching Staff</h1></template>"
            "<h1>Football Staff</h1><table><tr><td>A Person</td></tr></table>"
        )
        self.assertEqual(_bind(markup)["state"], UNBOUND_NO_ADMISSIBLE)

    def test_media_guide_year_is_corroboration_only(self) -> None:
        markup = (
            "<h1>2019 Football Media Guide</h1>"
            "<table><tr><td>A Person</td></tr></table>"
        )
        self.assertEqual(_bind(markup)["state"], UNBOUND_NO_ADMISSIBLE)


class PositivePathTests(unittest.TestCase):
    def test_football_roster_heading_binds(self) -> None:
        markup = (
            "<h1>2024 Football Roster</h1><table><tr><td>A Person</td></tr></table>"
        )
        result = _bind(markup)
        self.assertEqual(result["state"], BOUND_HEADING)
        self.assertEqual(result["bound_season"], 2024)

    def test_dated_announcement_binds_its_own_block(self) -> None:
        markup = (
            "<h1>Football Staff</h1><div class='bio'><span>A Person</span>"
            "<p>was named offensive coordinator on January 9, 2026.</p></div>"
        )
        result = _bind(markup)
        self.assertEqual(result["state"], BOUND_ANNOUNCEMENT)
        self.assertEqual(result["bound_season"], 2026)

    def test_unlocated_record_cannot_be_dated(self) -> None:
        scanned = scan_capture(MANAGER_FIXTURES["positive"])
        result = season_for_record(scanned, None)
        self.assertEqual(result["state"], UNBOUND_OUT_OF_SCOPE)
        self.assertIsNone(result["bound_season"])

    def test_record_before_the_heading_is_not_dated_by_it(self) -> None:
        markup = (
            "<table><tr><td>A Person</td></tr></table>"
            "<h1>2026 Football Coaching Staff</h1>"
        )
        result = _bind(markup)
        self.assertEqual(result["state"], UNBOUND_OUT_OF_SCOPE)

    def test_capture_level_helper_reports_each_record(self) -> None:
        markup = (
            "<h2>2026 Football Staff</h2><table><tr><td>A Person</td></tr></table>"
            "<h2>2025 Football Staff</h2><table><tr><td>B Person</td></tr></table>"
        )
        report = season_evidence_for_capture(
            markup, [markup.find("A Person"), markup.find("B Person")]
        )
        self.assertEqual(
            [record["bound_season"] for record in report["records"]], [2026, 2025]
        )
        self.assertEqual(report["admissible_label_count"], 2)


if __name__ == "__main__":
    unittest.main()
