import json
import math
from pathlib import Path
import sys
import unittest


try:
    import numpy  # noqa: F401
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by core-only CI
    raise unittest.SkipTest("preliminary modeling tests require the optional modeling dependencies") from exc


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.modeling.preliminary import (  # noqa: E402
    CLASSIFICATION,
    FEATURE_COLUMNS,
    MedianImputer,
    SplitPolicy,
    brier_score,
    elo_predict_and_update,
    feature_row_from_team_priors,
    log_loss,
    validate_chronology,
)


class PreliminaryUnprotectedBaselineTests(unittest.TestCase):
    def setUp(self):
        self.target = {
            "game_id": "g1",
            "season": 2023,
            "season_type": "regular",
            "week": 1,
            "start_utc": "2023-09-01T00:00:00Z",
            "home_team_id": "h",
            "away_team_id": "a",
            "neutral_site": False,
        }
        self.home = {
            "row_id": "rh",
            "target_game_id": "g1",
            "cutoff_utc": "2023-08-31T00:00:00Z",
            "team_id": "h",
            "opponent_id": "a",
            "prior_games": 10,
            "prior_win_rate": 0.7,
            "prior_points_for_mean": 30.0,
            "prior_points_against_mean": 20.0,
            "eligible_observation_ids": ["obs-old"],
            "lineage_sha256": "1" * 64,
        }
        self.away = {
            "row_id": "ra",
            "target_game_id": "g1",
            "cutoff_utc": "2023-08-31T00:00:00Z",
            "team_id": "a",
            "opponent_id": "h",
            "prior_games": 0,
            "prior_win_rate": None,
            "prior_points_for_mean": None,
            "prior_points_against_mean": None,
            "eligible_observation_ids": [],
            "lineage_sha256": "2" * 64,
        }

    def test_contract_is_scoped_and_preserves_protected_gate(self):
        contract = json.loads(
            (ROOT / "configs" / "preliminary_unprotected_baseline_contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["classification"], CLASSIFICATION)
        self.assertEqual(
            contract["authorized_inputs"]["bat523_scoped_replay_dataset_identity"],
            "cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7",
        )
        self.assertFalse(contract["split_policy"]["protected_split_opened"])
        self.assertIn(
            "EXPANDED_QUALITY_SUPPORTED_HISTORY",
            contract["dependency_contract"]["protected_promotion_still_requires"],
        )

    def test_feature_pairing_and_cold_start_are_explicit(self):
        row = feature_row_from_team_priors(self.target, self.home, self.away)
        self.assertEqual(row["classification"], CLASSIFICATION)
        self.assertEqual(row["away_cold_start"], 1.0)
        self.assertIsNone(row["prior_win_rate_diff"])
        self.assertFalse(row["target_outcome_in_feature_evidence"])
        mutated = dict(self.away, opponent_id="wrong")
        with self.assertRaises(ValueError):
            feature_row_from_team_priors(self.target, self.home, mutated)

    def test_imputer_rejects_future_season_during_fit(self):
        first = feature_row_from_team_priors(self.target, self.home, self.away)
        first["season"] = 2023
        second = dict(first, season=2024, prior_win_rate_diff=100.0)
        with self.assertRaises(ValueError):
            MedianImputer.fit([first, second], FEATURE_COLUMNS, [2023])
        imputer = MedianImputer.fit([first], FEATURE_COLUMNS, [2023])
        transformed = imputer.transform([first])
        self.assertTrue(math.isfinite(float(transformed[0, 0])))

    def test_split_and_target_game_leakage_fail_closed(self):
        feature = feature_row_from_team_priors(self.target, self.home, self.away)
        target = {
            "classification": CLASSIFICATION,
            "target_game_id": "g1",
            "season": 2023,
        }
        result = validate_chronology([feature], [target], SplitPolicy())
        self.assertEqual(result["target_game_identity_exclusion"], "PASS")
        bad = dict(feature, target_outcome_in_feature_evidence=True)
        with self.assertRaises(ValueError):
            validate_chronology([bad], [target], SplitPolicy())

    def test_elo_replay_is_chronological_and_deterministic(self):
        games = [
            {
                "target_game_id": "g1",
                "start_utc": "2023-09-01T00:00:00Z",
                "home_team_id": "a",
                "away_team_id": "b",
                "neutral_site": False,
                "home_win": 1.0,
            },
            {
                "target_game_id": "g2",
                "start_utc": "2023-09-08T00:00:00Z",
                "home_team_id": "b",
                "away_team_id": "a",
                "neutral_site": True,
                "home_win": 0.0,
            },
        ]
        first, ratings_a = elo_predict_and_update(games, {}, k_factor=20, home_advantage=55)
        second, ratings_b = elo_predict_and_update(games, {}, k_factor=20, home_advantage=55)
        self.assertEqual(first, second)
        self.assertEqual(ratings_a, ratings_b)
        self.assertGreater(first[0]["home_win_probability"], 0.5)
        self.assertLess(first[1]["home_win_probability"], 0.5)

    def test_probability_metrics_support_ties_without_fabrication(self):
        self.assertAlmostEqual(brier_score([0.0, 0.5, 1.0], [0.1, 0.5, 0.9]), 0.0066666667)
        self.assertGreater(log_loss([0.0, 0.5, 1.0], [0.1, 0.5, 0.9]), 0.0)


if __name__ == "__main__":
    unittest.main()
