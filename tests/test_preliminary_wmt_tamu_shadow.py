from __future__ import annotations

import json
from pathlib import Path
import unittest

from aggie_analytics.modeling.wmt_tamu_shadow import (
    NUMPY_AVAILABLE,
    WMT_FEATURES,
    build_shadow_row,
    fit_seasons_for_prediction,
    probability_metrics,
)


ROOT = Path(__file__).resolve().parents[1]


class PreliminaryWmtTamuShadowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (ROOT / "configs/preliminary_wmt_tamu_shadow_contract.json").read_text(encoding="utf-8")
        )

    def test_exact_inputs_feature_set_and_authority(self) -> None:
        inputs = self.contract["authorized_inputs"]
        self.assertEqual(inputs["national_reference_run_identity"], "8cc415cec979666f23ba616fea4cdc677566c16eaab254f1698bbfeb67906e56")
        self.assertEqual(inputs["wmt_feature_identity"], "337ca2219b8787d9c4c1c4e5b2644436ac2b21bdcd39bf532286250168601815")
        self.assertEqual(inputs["expected_target_games"], 39)
        self.assertEqual(tuple(self.contract["feature_policy"]["predeclared_wmt_columns"]), WMT_FEATURES)
        self.assertFalse(self.contract["chronology_policy"]["protected_split_opened"])
        self.assertFalse(any(self.contract["protected_nonclaims"].values()))

    def test_walk_forward_plan(self) -> None:
        self.assertEqual(fit_seasons_for_prediction(2023), ())
        self.assertEqual(fit_seasons_for_prediction(2024), (2023,))
        self.assertEqual(fit_seasons_for_prediction(2025), (2023, 2024))
        with self.assertRaises(ValueError):
            fit_seasons_for_prediction(2022)

    def test_exact_join_orientation_and_cutoff(self) -> None:
        wmt = {
            "game_id": "g1", "season": 2024, "season_type": "regular", "week": 1,
            "start_utc": "2024-09-02T00:00:00Z", "cutoff_utc": "2024-09-01T00:00:00Z",
            "canonical_tamu_team_id": "tamu", "team_role": "AWAY", "opponent_team_id": "opp",
            "neutral_site": False, "protected_eligible": False, "cold_start": False,
            "latest_source_available_at_utc": "2024-08-30T00:00:00Z",
            "latest_source_effective_at_utc": "2024-08-29T00:00:00Z",
            "source_record_count": 100, "source_game_count": 10,
            "action_penalty_rate": 0.02, "play_scoring_rate": 0.05,
            "drive_turnover_rate": 0.1, "player_starter_rate": 0.7,
        }
        common = {
            "target_game_id": "g1", "season": 2024, "start_utc": "2024-09-02T00:00:00Z",
            "home_team_id": "opp", "away_team_id": "tamu", "home_win": 0.0, "margin": -7,
            "home_win_probability": 0.3,
        }
        logistic = {**common, "model_id": "play_drive_logistic_stacker", "predicted_margin": None}
        margin = {**common, "model_id": "play_drive_ridge_margin_stacker", "predicted_margin": -3.5}
        row = build_shadow_row(wmt, logistic, margin, "tamu")
        self.assertAlmostEqual(row["baseline_tamu_probability"], 0.7)
        self.assertAlmostEqual(row["baseline_tamu_margin"], 3.5)
        self.assertEqual(row["tamu_win"], 1.0)
        self.assertEqual(row["tamu_margin"], 7.0)
        wmt["latest_source_available_at_utc"] = wmt["cutoff_utc"]
        with self.assertRaisesRegex(ValueError, "strictly before"):
            build_shadow_row(wmt, logistic, margin, "tamu")

    @unittest.skipUnless(NUMPY_AVAILABLE, "optional NumPy modeling dependency unavailable")
    def test_probability_metrics_are_finite(self) -> None:
        metrics = probability_metrics([0.0, 1.0], [0.2, 0.8])
        self.assertEqual(metrics["rows"], 2)
        self.assertAlmostEqual(metrics["brier"], 0.04)


if __name__ == "__main__":
    unittest.main()
