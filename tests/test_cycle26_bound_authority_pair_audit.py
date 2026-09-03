"""R26-22 prior-target pair audit regressions."""

from __future__ import annotations

import unittest

from aggie_analytics.data.cycle26_bound_authority_pair_audit import (
    EPISTEMIC_STATUS,
    census_team_prior_target_pairs,
    classify_prior_target_temporal_authority,
)


class BoundAuthorityPairAuditTests(unittest.TestCase):
    def test_clocked_proxy_is_not_a_universal_guarantee(self) -> None:
        classified = classify_prior_target_temporal_authority(
            "2022-09-03T18:00:00Z",
            "2022-09-03T23:00:00Z",
        )
        self.assertFalse(classified["admitted_under_proxy"])
        self.assertFalse(classified["universal_finality_guarantee"])
        self.assertFalse(classified["proven_historical_known_at"])
        self.assertEqual(classified["bound_epistemic_status"], EPISTEMIC_STATUS)
        admitted = classify_prior_target_temporal_authority(
            "2022-09-03T18:00:00Z",
            "2022-09-10T18:00:00Z",
        )
        self.assertTrue(admitted["admitted_under_proxy"])
        self.assertEqual(admitted["class"], "PROXY_CLOCKED_12H")
        self.assertFalse(admitted["proven_historical_known_at"])

    def test_timezone_naive_start_is_insufficient(self) -> None:
        classified = classify_prior_target_temporal_authority(
            "2022-09-03T18:00:00",
            "2022-09-10T18:00:00Z",
        )
        self.assertEqual(classified["class"], "INSUFFICIENT_START_EVIDENCE")
        self.assertFalse(classified["admitted_under_proxy"])

    def test_census_does_not_declare_leakage(self) -> None:
        observations = [
            {"canonical_team_id": "tamu", "canonical_game_id": "g1", "season": 2022},
            {"canonical_team_id": "tamu", "canonical_game_id": "g2", "season": 2022},
        ]
        starts = {
            "g1": "2022-09-03T18:00:00Z",
            "g2": "2022-09-10T18:00:00Z",
        }
        census = census_team_prior_target_pairs(observations, starts)
        self.assertEqual(census["admitted_proxy_pairs"], 1)
        self.assertEqual(census["team_count"], 1)
        naive = census_team_prior_target_pairs(
            observations,
            {"g1": "2022-09-03T18:00:00", "g2": "2022-09-10T18:00:00Z"},
        )
        self.assertGreaterEqual(naive["insufficient_start_games"], 1)


if __name__ == "__main__":
    unittest.main()
