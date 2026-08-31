"""Conditions the BAT-674 anchor-only scoreboard fallback must satisfy to be retained.

The fallback exists so that a minimal scoreboard payload exposing contest anchors but
no contest table rows still preserves those contest identifiers as observations.  It is
retained only while it can never invent a final, a score or a contest.
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.modeling.week_zero_live_shadow_execution import (  # noqa: E402
    parse_official_finals,
)

DISPOSITION_PATH = ROOT / "artifacts/shadow/week_zero_2026_scoreboard_fallback_disposition.json"
CONTRACT = {
    "official_final_status_tokens": ["Final", "FINAL"],
    "non_final_status_tokens": ["Canceled", "Cancelled", "Postponed", "Suspended", "No Contest"],
}

ANCHOR_ONLY_DOCUMENT = """<html><body>
<a href="/contests/6586325/box_score">box score</a>
<a href="/contests/6594398/box_score">box score</a>
</body></html>"""

ROW_DOCUMENT = """<html><body>
<tr id="contest_6586325">
  <td><a href="/teams/622184">Memphis</a></td>
  <td><div id="score_622184">27</div></td>
</tr>
<tr id="contest_6586325">
  <td><a href="/teams/622197">UNLV</a></td>
  <td><div id="score_622197">21</div></td>
</tr>
</body></html>"""


def finals_for(document: str) -> list[dict]:
    return parse_official_finals(document, game_date="2026-08-29", contract=CONTRACT)


class AnchorOnlyFallbackTests(unittest.TestCase):
    def test_the_fallback_preserves_contest_identifiers_it_would_otherwise_drop(self) -> None:
        finals = finals_for(ANCHOR_ONLY_DOCUMENT)
        self.assertEqual(
            ["6586325", "6594398"], sorted(row["ncaa_contest_id"] for row in finals)
        )

    def test_an_absent_status_never_becomes_a_final(self) -> None:
        for row in finals_for(ANCHOR_ONLY_DOCUMENT):
            self.assertEqual("", row["official_status_text"])
            self.assertNotEqual("OFFICIAL_FINAL_OBSERVED", row["official_status_state"])

    def test_no_score_is_inferred_when_the_page_carries_none(self) -> None:
        for row in finals_for(ANCHOR_ONLY_DOCUMENT):
            self.assertIsNone(row["away_points"])
            self.assertIsNone(row["home_points"])

    def test_no_missing_contest_is_substituted(self) -> None:
        finals = finals_for(ANCHOR_ONLY_DOCUMENT)
        self.assertEqual(2, len(finals))
        self.assertNotIn("6602787", {row["ncaa_contest_id"] for row in finals})

    def test_the_fallback_does_not_engage_when_contest_rows_are_present(self) -> None:
        finals = finals_for(ROW_DOCUMENT)
        self.assertEqual(1, len(finals))
        self.assertEqual("6586325", finals[0]["ncaa_contest_id"])
        self.assertEqual(27, finals[0]["away_points"])
        self.assertEqual(21, finals[0]["home_points"])

    def test_an_empty_document_yields_no_contest_at_all(self) -> None:
        self.assertEqual([], finals_for("<html></html>"))


class DispositionBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.disposition = json.loads(DISPOSITION_PATH.read_text(encoding="utf-8"))

    def test_the_disposition_is_owned_by_the_successor_issue(self) -> None:
        self.assertEqual("BAT-674", self.disposition["successor_ownership"])

    def test_every_retention_condition_is_declared(self) -> None:
        conditions = self.disposition["conditions"]
        self.assertTrue(conditions["absent_status_never_becomes_final"])
        self.assertTrue(conditions["api_first_acquisition_remains_preferred"])
        self.assertTrue(conditions["code_identity_is_bound"])
        self.assertTrue(conditions["no_missing_contest_is_substituted"])
        self.assertTrue(conditions["no_score_is_inferred"])
        self.assertEqual(
            Path(__file__).relative_to(ROOT).as_posix(), conditions["tests_cover_every_condition"]
        )

    def test_the_bound_code_identity_matches_the_module_on_disk(self) -> None:
        for block in ("bound_code_identity", "fixture_identity"):
            module = ROOT / self.disposition[block]["module"]
            self.assertEqual(
                hashlib.sha256(module.read_bytes()).hexdigest(),
                self.disposition[block]["sha256"],
                f"{block} is stale",
            )

    def test_cfbd_priority_is_preserved(self) -> None:
        self.assertTrue(self.disposition["cfbd_priority_preserved"])


if __name__ == "__main__":
    unittest.main()
