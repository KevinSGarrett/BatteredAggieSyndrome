from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    from aggie_analytics.modeling.play_drive_augmented import (
        build_game_profile,
        fit_seasons_for_prediction,
        probability_metrics,
    )
except ModuleNotFoundError as exc:
    if exc.name != "numpy":
        raise
    build_game_profile = None
    fit_seasons_for_prediction = None
    probability_metrics = None


ROOT = Path(__file__).resolve().parents[1]
RUNNER_DEPENDENCIES_AVAILABLE = all(
    importlib.util.find_spec(name) is not None
    for name in ("joblib", "numpy", "polars", "sklearn")
)


class PreliminaryPlayDriveAugmentedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (ROOT / "configs/preliminary_play_drive_augmented_contract.json").read_text(encoding="utf-8")
        )

    def test_exact_inputs_and_authority(self) -> None:
        inputs = self.contract["authorized_inputs"]
        self.assertEqual(inputs["baseline_run_identity"], "a3914e3f5b3fa95c81b7ee08338e27901ac07da870277967234dbe1fb7cd2080")
        self.assertEqual(inputs["play_drive_feature_identity"], "b78d577db4a054a56f66aa5cd4e9649594876785e4143cb4669b62746c1b0e06")
        self.assertEqual(inputs["eligible_target_seasons"], [2023, 2024, 2025])
        self.assertEqual(inputs["eligibility"], "DEVELOPMENT_AND_PRELIMINARY_UNPROTECTED_ONLY")
        self.assertFalse(self.contract["chronology_policy"]["protected_split_opened"])
        self.assertFalse(any(self.contract["protected_nonclaims"].values()))

    def test_dense_replay_is_separately_lineaged_and_unprotected(self) -> None:
        contract = json.loads(
            (ROOT / "configs/preliminary_dense_play_drive_replay_contract.json").read_text(
                encoding="utf-8"
            )
        )
        inputs = contract["authorized_inputs"]
        self.assertEqual(contract["decision_unit"], "POST-SUBTASK-184")
        self.assertEqual(contract["classification"], "PRELIMINARY_UNPROTECTED")
        self.assertEqual(
            inputs["play_drive_feature_identity"],
            "1bd6f4c69932d5c401a3318517849fe1f1f6347d299f893809c536f52bec321d",
        )
        self.assertEqual(
            inputs["prior_play_drive_run_identity"],
            "8cc415cec979666f23ba616fea4cdc677566c16eaab254f1698bbfeb67906e56",
        )
        self.assertEqual(inputs["source_seasons"], list(range(2010, 2023)))
        self.assertFalse(contract["chronology_policy"]["protected_split_opened"])
        self.assertFalse(any(contract["protected_nonclaims"].values()))

    @unittest.skipUnless(
        RUNNER_DEPENDENCIES_AVAILABLE,
        "optional modeling runner dependencies unavailable",
    )
    def test_unsafe_storage_namespace_fails_closed(self) -> None:
        contract = json.loads(
            (ROOT / "configs/preliminary_dense_play_drive_replay_contract.json").read_text(
                encoding="utf-8"
            )
        )
        contract["storage_namespace"] = "../outside"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe-contract.json"
            path.write_text(json.dumps(contract), encoding="utf-8")
            run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/run_preliminary_play_drive_augmented.py"),
                    "--repo-root",
                    str(ROOT),
                    "--data-root",
                    str(ROOT),
                    "--contract-path",
                    str(path),
                    "--issued-at-utc",
                    "2026-08-11T00:00:00Z",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("storage namespace must be a safe relative path component", run.stderr)

    @unittest.skipIf(fit_seasons_for_prediction is None, "optional modeling dependencies unavailable")
    def test_walk_forward_fit_plan(self) -> None:
        self.assertEqual(fit_seasons_for_prediction(2023), ())
        self.assertEqual(fit_seasons_for_prediction(2024), (2023,))
        self.assertEqual(fit_seasons_for_prediction(2025), (2023, 2024))
        with self.assertRaises(ValueError):
            fit_seasons_for_prediction(2022)

    @unittest.skipIf(build_game_profile is None, "optional modeling dependencies unavailable")
    def test_profile_join_and_known_at_gate(self) -> None:
        target = {
            "target_game_id": "g1", "season": 2024, "start_utc": "2024-09-02T00:00:00Z",
            "cutoff_utc": "2024-09-01T00:00:00Z", "home_team_id": "h", "away_team_id": "a",
        }
        common = {
            "game_id": "g1", "historical_known_at_eligible": True, "protected_eligible": False,
            "source_known_at_utc": "2023-05-06T07:52:16Z", "cold_start": False,
            "play_count": 10, "play_game_count": 2, "play_season_count": 1, "epa_mean": 0.1,
            "stat_yardage_mean": 5.0, "rush_rate": 0.5, "pass_rate": 0.4,
            "scoring_play_rate": 0.1, "interception_rate": 0.01, "sack_rate": 0.02,
            "pass_completion_rate": 0.6, "drive_count": 3, "drive_game_count": 2,
            "drive_plays_mean": 6.0, "touchdown_drive_rate": 0.3,
            "field_goal_drive_rate": 0.1, "turnover_drive_rate": 0.1,
        }
        rows = [
            {**common, "team_role": "HOME", "team_id": "h", "opponent_team_id": "a"},
            {**common, "team_role": "AWAY", "team_id": "a", "opponent_team_id": "h", "play_count": 4},
        ]
        feature = build_game_profile(target, rows)
        self.assertEqual(feature["play_drive_play_count_diff"], 6.0)
        self.assertFalse(feature["play_drive_protected_eligible"])
        rows[0]["source_known_at_utc"] = "2025-01-01T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "after target cutoff"):
            build_game_profile(target, rows)

    @unittest.skipIf(probability_metrics is None, "optional modeling dependencies unavailable")
    def test_probability_diagnostics_are_finite(self) -> None:
        metrics = probability_metrics([0.0, 1.0], [0.2, 0.8])
        self.assertEqual(metrics["rows"], 2)
        self.assertAlmostEqual(metrics["brier"], 0.04)
        self.assertGreaterEqual(metrics["ece_10"], 0.0)


if __name__ == "__main__":
    unittest.main()
