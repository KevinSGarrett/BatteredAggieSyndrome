from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PreliminaryRankingsAugmentedContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (ROOT / "configs/preliminary_rankings_augmented_contract.json").read_text(
                encoding="utf-8"
            )
        )

    def test_exact_input_and_preliminary_authority(self) -> None:
        inputs = self.contract["authorized_inputs"]
        self.assertEqual(
            inputs["rankings_feature_identity"],
            "b165e076222104d71f345cf294d5b177d2c049bf1168b11c29e9cc5690375274",
        )
        self.assertEqual(
            inputs["eligibility"], "DEVELOPMENT_AND_PRELIMINARY_UNPROTECTED_ONLY"
        )
        self.assertFalse(self.contract["split_policy"]["protected_split_opened"])

    def test_missing_rank_is_not_fabricated(self) -> None:
        semantics = self.contract["feature_semantics"]
        self.assertEqual(semantics["unranked_numeric_value"], "NEVER_FABRICATE")
        self.assertIn("EXPLICIT_OBSERVED_INDICATORS", semantics["numeric_missingness"])
        self.assertEqual(
            semantics["points_and_first_place_votes"],
            "EXCLUDED_FROM_INITIAL_AUGMENTED_REPLAY",
        )

    def test_comparison_cannot_promote(self) -> None:
        comparison = self.contract["comparison_contract"]
        self.assertTrue(comparison["same_target_rows_required"])
        self.assertTrue(comparison["same_model_ladder_required"])
        self.assertEqual(
            comparison["adoption_authority"], "PRELIMINARY_RESEARCH_ONLY_NO_CHAMPION"
        )
        self.assertFalse(any(self.contract["protected_nonclaims"].values()))


if __name__ == "__main__":
    unittest.main()
