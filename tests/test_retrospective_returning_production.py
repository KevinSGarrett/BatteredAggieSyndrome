from __future__ import annotations

import json
from pathlib import Path
import unittest

from aggie_analytics.features.returning_production import (
    PAIR_FIELDS,
    calculate_transition_records,
    safe_share,
    signed_ratio,
)


ROOT = Path(__file__).resolve().parents[1]


class RetrospectiveReturningProductionTests(unittest.TestCase):
    def test_contract_keeps_shared_snaps_and_target_features_closed(self) -> None:
        contract = json.loads(
            (ROOT / "configs/retrospective_returning_production_contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn(
            "shared_snap_continuity",
            contract["feature_contract"]["unsupported_fields"],
        )
        self.assertFalse(contract["authority"]["target_game_feature_admission"])
        self.assertFalse(contract["authority"]["preliminary_training_admission"])
        self.assertFalse(any(contract["protected_nonclaims"].values()))

    def test_safe_share_fails_closed_outside_unit_interval(self) -> None:
        self.assertIsNone(safe_share(0, 0))
        self.assertEqual(safe_share(1, 2), 0.5)
        with self.assertRaises(ValueError):
            safe_share(3, 2)

    def test_signed_ratio_preserves_legitimate_net_yardage_anomaly(self) -> None:
        self.assertEqual(signed_ratio(101, 100), 1.01)
        self.assertEqual(signed_ratio(-1, 100), -0.01)
        self.assertIsNone(signed_ratio(1, 0))

    def test_same_team_membership_controls_returning_production(self) -> None:
        roster = [
            {"season": 2020, "canonical_team_id": "t", "canonical_team_label": "T", "canonical_player_id": "a", "source_known_at_utc": "2023-05-01T00:00:00Z"},
            {"season": 2020, "canonical_team_id": "t", "canonical_team_label": "T", "canonical_player_id": "b", "source_known_at_utc": "2023-05-01T00:00:00Z"},
            {"season": 2021, "canonical_team_id": "t", "canonical_team_label": "T", "canonical_player_id": "a", "source_known_at_utc": "2023-05-01T00:00:00Z"},
            {"season": 2021, "canonical_team_id": "t", "canonical_team_label": "T", "canonical_player_id": "c", "source_known_at_utc": "2023-05-01T00:00:00Z"},
        ]
        metrics = []
        for pair in PAIR_FIELDS:
            metrics.extend(
                [
                    {"season": 2020, "canonical_team_id": "t", "canonical_team_label": "T", "canonical_player_id": "a", "category": pair[0], "stat_type": pair[1], "source_value": 30, "source_known_at_utc": "2023-05-01T00:00:00Z"},
                    {"season": 2020, "canonical_team_id": "t", "canonical_team_label": "T", "canonical_player_id": "b", "category": pair[0], "stat_type": pair[1], "source_value": 70, "source_known_at_utc": "2023-05-01T00:00:00Z"},
                ]
            )
        features, components, coverage = calculate_transition_records(
            roster,
            metrics,
            [2021],
            "RESEARCH",
            {2020},
        )
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0]["roster_retention_rate"], 0.5)
        self.assertEqual(features[0]["roster_arrival_rate"], 0.5)
        self.assertEqual(features[0]["roster_jaccard"], 1 / 3)
        for field in PAIR_FIELDS.values():
            self.assertEqual(features[0][field], 0.3)
        self.assertEqual(len(components), 6)
        self.assertTrue(coverage[0]["partial_prior_metric_season"])
        self.assertFalse(features[0]["target_game_feature_eligible"])


if __name__ == "__main__":
    unittest.main()
