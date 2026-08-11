from __future__ import annotations

import json
from pathlib import Path
import unittest

from aggie_analytics.modeling.preliminary_rankings import augment_with_rankings


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

    def test_rankings_join_preserves_missing_numeric_rank(self) -> None:
        feature = {
            "target_game_id": "g1", "season": 2025,
            "home_team_id": "home", "away_team_id": "away",
            "cutoff_utc": "2025-09-01T00:00:00Z",
        }
        common = {
            "target_game_id": "g1", "cutoff_utc": feature["cutoff_utc"],
            "poll_available": True, "poll_first_eligible_at_utc": "2025-08-31T00:00:00Z",
            "feature_row_id": "row", "source_observation_id": None,
        }
        rows = [
            {**common, "team_side": "HOME", "canonical_team_id": "home", "rank": 5, "team_listed_in_poll": True},
            {**common, "team_side": "AWAY", "canonical_team_id": "away", "rank": None, "team_listed_in_poll": False},
        ]
        augmented, coverage = augment_with_rankings([feature], rows)
        self.assertIsNone(augmented[0]["ap_rank_diff"])
        self.assertEqual(augmented[0]["home_ap_rank_observed"], 1.0)
        self.assertEqual(augmented[0]["away_ap_rank_observed"], 0.0)
        self.assertEqual(coverage["rank_diff_missing"], 1)

    def test_future_rankings_evidence_fails_closed(self) -> None:
        feature = {"target_game_id": "g1", "season": 2025, "home_team_id": "h", "away_team_id": "a", "cutoff_utc": "2025-09-01T00:00:00Z"}
        rows = [
            {"target_game_id":"g1","team_side":side,"canonical_team_id":team,"cutoff_utc":feature["cutoff_utc"],"poll_available":True,"team_listed_in_poll":True,"rank":1,"poll_first_eligible_at_utc":"2025-09-02T00:00:00Z","feature_row_id":side,"source_observation_id":side}
            for side, team in (("HOME","h"),("AWAY","a"))
        ]
        with self.assertRaisesRegex(ValueError, "future rankings evidence"):
            augment_with_rankings([feature], rows)


if __name__ == "__main__":
    unittest.main()
