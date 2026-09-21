"""R35-29 (Cycle #35 continuation, 20260921T055921Z), section 4.

"The inspected release has zero scheme and responsibility assertions. Before
treating these as source-unavailable, reconcile the declared predecessor
scheme/career/user-corpus caches and their ingest routes. Earlier cycles
produced scheme observations; check the actual artifacts."

They did, and the packet's stated basis -- "no acquired source states
offensive or defensive scheme" -- is false: 9,111 stated scheme claims are
sitting in the cycle33 cache.

But the fix is not to wire the ingest. The claims key their program by
Wikipedia page title and the canonical population keys by display name, with
no crosswalk between them. The obvious string rule binds "Texas
A&M-Commerce Lions" to canonical "Texas", and its failures are mostly
invisible: that one surfaced only because "Texas Longhorns" happened to
appear in the same season. These tests pin the refusal so a later change
cannot quietly start ingesting on that rule.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_29_scheme_ingest import (  # noqa: E402
    BLANK,
    scheme_claims_with_content,
    summary,
    team_from_page_title,
    token_prefix,
)

REAL_ARTIFACT = (
    Path("C:/BatteredAggieSyndrome.data/ops/cycle35/runs")
    / "20260921T055921Z_implementation"
    / "CYCLE35_SCHEME_INGEST.json"
)


class PageTitleTests(unittest.TestCase):
    def test_a_season_page_title_reduces_to_its_team_name(self) -> None:
        self.assertEqual(
            team_from_page_title("2005 North Texas Mean Green football team"),
            "North Texas Mean Green",
        )

    def test_a_non_season_title_reduces_to_nothing(self) -> None:
        for title in ("North Texas", "", "Towson Tigers", "2005 North Texas"):
            with self.subTest(title=title):
                self.assertIsNone(team_from_page_title(title))


class UnsafePrefixRuleTests(unittest.TestCase):
    """The rule is kept only to quantify what a crosswalk would recover.
    These tests document precisely why its output is never ingested."""

    def test_it_binds_a_different_school_to_texas(self) -> None:
        self.assertTrue(token_prefix("Texas", "Texas A&M-Commerce Lions"))

    def test_it_binds_both_miami_schools_to_one_program(self) -> None:
        self.assertTrue(token_prefix("Miami", "Miami Hurricanes"))
        self.assertTrue(token_prefix("Miami", "Miami RedHawks"))

    def test_it_does_not_match_an_unrelated_leading_token(self) -> None:
        self.assertFalse(token_prefix("North Texas", "Texas Longhorns"))
        self.assertFalse(token_prefix("Towson", "Towson Tigers Baseball".replace("Towson", "Tulsa", 1)))


class ClaimSelectionTests(unittest.TestCase):
    def test_an_empty_infobox_field_is_not_a_scheme(self) -> None:
        claims = [
            {"claim_kind": "SCHEME", "disposition": BLANK, "source_text": ""},
            {"claim_kind": "SCHEME", "disposition": "OK", "source_text": "   "},
        ]
        self.assertEqual(scheme_claims_with_content(claims), [])

    def test_a_stated_scheme_is_selected(self) -> None:
        claims = [
            {
                "claim_kind": "SCHEME",
                "disposition": "SOURCE_REPORTED_FAMILY_TAGGED",
                "source_text": "[[Spread offense|Pro spread]]",
            }
        ]
        self.assertEqual(len(scheme_claims_with_content(claims)), 1)

    def test_tenure_claims_are_not_scheme_claims(self) -> None:
        claims = [
            {"claim_kind": "TENURE", "disposition": "OK", "source_text": "2005-2010"}
        ]
        self.assertEqual(scheme_claims_with_content(claims), [])


class RefusalTests(unittest.TestCase):
    def test_the_summary_ingests_nothing_and_says_why(self) -> None:
        prepared = {
            "claims_total": 10,
            "scheme_claims": 5,
            "scheme_claims_with_stated_text": 3,
            "resolution_states": {},
            "candidate_rows": [],
            "unresolved_examples": [],
            "source_text_conflicts": 0,
            "program_collisions": [],
        }
        result = summary(prepared)
        self.assertTrue(result["ingest_refused"])
        self.assertEqual(result["rows_ingested"], 0)
        self.assertIn("silently", result["why_ingest_is_refused"])
        self.assertIn("crosswalk", result["remaining_work"])

    def test_the_acceptance_predicate_is_measurable(self) -> None:
        result = summary(
            {
                "claims_total": 0,
                "scheme_claims": 0,
                "scheme_claims_with_stated_text": 0,
                "resolution_states": {},
                "candidate_rows": [],
                "unresolved_examples": [],
                "source_text_conflicts": 0,
                "program_collisions": [],
            }
        )
        predicate = result["remaining_work"]
        self.assertIn("at most one canonical program", predicate)
        self.assertIn("no two distinct page-title teams", predicate)


class RealReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        if not REAL_ARTIFACT.is_file():
            self.skipTest("the scheme reconciliation has not been generated")
        self.result = json.loads(REAL_ARTIFACT.read_text(encoding="utf-8"))

    def test_nothing_was_ingested(self) -> None:
        self.assertEqual(self.result["rows_ingested"], 0)
        self.assertTrue(self.result["ingest_refused"])

    def test_the_evidence_gap_claim_is_contradicted(self) -> None:
        """The packet says no source states a scheme. Thousands do."""
        self.assertGreater(self.result["scheme_claims_with_stated_text"], 5000)

    def test_real_collisions_were_found_and_recorded(self) -> None:
        self.assertGreater(self.result["program_collision_count"], 0)
        teams = {
            team
            for entry in self.result["program_collisions"]
            for team in entry["distinct_page_teams"]
        }
        self.assertTrue(any("Miami" in t for t in teams))

    def test_what_a_crosswalk_would_recover_is_quantified(self) -> None:
        self.assertGreater(self.result["candidate_rows_if_a_crosswalk_existed"], 0)


if __name__ == "__main__":
    unittest.main()
