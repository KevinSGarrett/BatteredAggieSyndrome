from __future__ import annotations

import json
from pathlib import Path
import unittest

from aggie_analytics.modeling.possession_pace_augmented import (
    DIAGNOSTIC_FIELDS,
    LOGISTIC_FEATURES,
    PACE_DIFFERENCE_FIELDS,
    build_game_profile,
    merge_prior_features,
)
from aggie_analytics.modeling.play_drive_augmented import DIFFERENCE_FIELDS as PRIOR_FIELDS


ROOT = Path(__file__).resolve().parents[1]


class PreliminaryPossessionPaceAblationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (ROOT / "configs/preliminary_possession_pace_ablation_contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.target = {
            "target_game_id": "g1",
            "season": 2024,
            "start_utc": "2024-09-02T00:00:00Z",
            "cutoff_utc": "2024-09-01T00:00:00Z",
            "home_team_id": "h",
            "away_team_id": "a",
        }
        common = {
            "game_id": "g1",
            "authority": "DEVELOPMENT_ONLY",
            "protected_eligible": False,
            "play_source_known_at_utc_max": "2023-05-06T07:52:16Z",
            "drive_source_known_at_utc_max": "2023-05-06T07:52:16Z",
            "cold_start": False,
            "offensive_plays_per_game": 70.0,
            "offensive_drives_per_game": 11.0,
            "observed_plays_per_drive_mean": 6.2,
            "regulation_drive_span_seconds_mean": 140.0,
            "regulation_drive_span_seconds_median": 120.0,
            "overtime_drive_rate": 0.01,
            "regulation_drive_span_eligible_rate": 0.99,
            "source_endpoint_reverse_rate": 0.05,
            "rule_era_transfer_mismatch": True,
        }
        self.profile_rows = [
            {
                **common,
                "team_role": "HOME",
                "team_id": "h",
                "opponent_team_id": "a",
            },
            {
                **common,
                "team_role": "AWAY",
                "team_id": "a",
                "opponent_team_id": "h",
                "offensive_plays_per_game": 64.0,
            },
        ]

    def test_contract_pins_nested_inputs_and_closes_protected_authority(self) -> None:
        inputs = self.contract["authorized_inputs"]
        self.assertEqual(
            inputs["profile_feature_identity"],
            "a719b03d2c91142802adb194c875677e07e29ab85bd6bf1f138749fb971cb213",
        )
        self.assertEqual(
            inputs["prior_run_identity"],
            "8cc415cec979666f23ba616fea4cdc677566c16eaab254f1698bbfeb67906e56",
        )
        self.assertTrue(self.contract["nested_prior_features"]["same_target_rows_required"])
        self.assertFalse(self.contract["chronology_policy"]["protected_split_opened"])
        self.assertFalse(any(self.contract["protected_nonclaims"].values()))

    def test_nested_join_adds_only_predeclared_candidate_features(self) -> None:
        feature = build_game_profile(self.target, self.profile_rows)
        prior = {
            "target_game_id": "g1",
            "home_team_id": "h",
            "away_team_id": "a",
            "cutoff_utc": self.target["cutoff_utc"],
            "home_profile_cold_start": 0.0,
            "away_profile_cold_start": 0.0,
            "play_drive_protected_eligible": False,
            "play_drive_source_known_at_utc": "2023-05-06T07:52:16Z",
            "play_drive_lineage_sha256": "a" * 64,
            **{name: 1.0 for name in PRIOR_FIELDS},
        }
        merged = merge_prior_features(feature, prior)
        self.assertEqual(merged["possession_pace_offensive_plays_per_game_diff"], 6.0)
        self.assertTrue(all(name in merged for name in PRIOR_FIELDS))
        self.assertTrue(all(name in LOGISTIC_FEATURES for name in PACE_DIFFERENCE_FIELDS))
        self.assertTrue(all(name not in LOGISTIC_FEATURES for name in DIAGNOSTIC_FIELDS))
        self.assertFalse(merged["possession_pace_protected_eligible"])

    def test_join_fails_closed_on_team_or_known_at_mismatch(self) -> None:
        bad_rows = [dict(row) for row in self.profile_rows]
        bad_rows[0]["play_source_known_at_utc_max"] = "2025-01-01T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "after target cutoff"):
            build_game_profile(self.target, bad_rows)

        feature = build_game_profile(self.target, self.profile_rows)
        prior = {
            "target_game_id": "g1",
            "home_team_id": "wrong",
            "away_team_id": "a",
            "cutoff_utc": self.target["cutoff_utc"],
            "home_profile_cold_start": 0.0,
            "away_profile_cold_start": 0.0,
            "play_drive_protected_eligible": False,
            "play_drive_source_known_at_utc": "2023-05-06T07:52:16Z",
            "play_drive_lineage_sha256": "a" * 64,
            **{name: 1.0 for name in PRIOR_FIELDS},
        }
        with self.assertRaisesRegex(ValueError, "home_team_id mismatch"):
            merge_prior_features(feature, prior)

    def test_missing_authority_is_allowed_only_for_explicit_cold_start(self) -> None:
        rows = [dict(row) for row in self.profile_rows]
        rows[0]["authority"] = None
        with self.assertRaisesRegex(ValueError, "invalid authority"):
            build_game_profile(self.target, rows)
        rows[0]["cold_start"] = True
        for name in self.contract["candidate_profile_fields"]:
            rows[0][name] = None
        feature = build_game_profile(self.target, rows)
        self.assertEqual(feature["home_profile_cold_start"], 1.0)


if __name__ == "__main__":
    unittest.main()
