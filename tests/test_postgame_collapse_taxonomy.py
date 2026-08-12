from __future__ import annotations

import json
import unittest
from pathlib import Path

from aggie_analytics.features.postgame_collapse_taxonomy import oriented_team_taxonomy


ROOT = Path(__file__).resolve().parents[1]


class PostgameCollapseTaxonomyTests(unittest.TestCase):
    def test_losing_team_surrenders_leads_and_has_downside_residual(self) -> None:
        row = oriented_team_taxonomy(final_margin=-3, expected_margin=8, observed_leads=[0, 7, 14, 10, -3], late_observed_leads=[10, 3, -3])
        self.assertTrue(row["lead_surrendered_7"])
        self.assertTrue(row["lead_surrendered_14"])
        self.assertFalse(row["lead_surrendered_21"])
        self.assertTrue(row["fourth_quarter_lead_surrendered"])
        self.assertEqual(row["largest_lead_surrendered"], 14)
        self.assertEqual(row["national_expected_margin_residual"], -11)
        self.assertTrue(row["downside_residual_7"])
        self.assertFalse(row["downside_residual_14"])

    def test_win_is_not_a_surrender_and_unknown_reference_stays_unknown(self) -> None:
        row = oriented_team_taxonomy(final_margin=1, expected_margin=None, observed_leads=[0, 14, -7, 1], late_observed_leads=[-7, 1])
        self.assertFalse(row["lead_surrendered_7"])
        self.assertFalse(row["fourth_quarter_lead_surrendered"])
        self.assertIsNone(row["largest_lead_surrendered"])
        self.assertIsNone(row["national_expected_margin_residual"])
        self.assertIsNone(row["downside_residual_7"])

    def test_contract_forbids_pregame_and_protected_use(self) -> None:
        contract = json.loads((ROOT / "configs" / "preliminary_postgame_collapse_taxonomy_contract.json").read_text(encoding="utf-8"))
        self.assertFalse(contract["eligibility"]["pregame_feature"])
        self.assertFalse(contract["eligibility"]["historical_original_pit"])
        self.assertFalse(contract["eligibility"]["protected_evaluation"])
        self.assertFalse(contract["authority"]["bas_or_aggie_excess_authority"])
        self.assertTrue(contract["validation"]["partial_coverage_preserved"])


if __name__ == "__main__":
    unittest.main()
