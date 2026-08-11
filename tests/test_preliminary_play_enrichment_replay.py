from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    from aggie_analytics.modeling.play_enrichment_augmented import (
        PROFILE_FIELDS,
        build_game_profile,
        fit_seasons_for_prediction,
    )
except ModuleNotFoundError as exc:
    if exc.name != "numpy":
        raise
    PROFILE_FIELDS = ()
    build_game_profile = None
    fit_seasons_for_prediction = None


ROOT = Path(__file__).resolve().parents[1]
RUNNER_DEPENDENCIES_AVAILABLE = all(
    importlib.util.find_spec(name) is not None
    for name in ("joblib", "numpy", "polars", "sklearn")
)


class PreliminaryPlayEnrichmentReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (ROOT / "configs/preliminary_play_enrichment_replay_contract.json").read_text(
                encoding="utf-8"
            )
        )

    def test_contract_pins_exact_development_inputs(self) -> None:
        inputs = self.contract["authorized_inputs"]
        self.assertEqual(self.contract["decision_unit"], "POST-SUBTASK-187")
        self.assertEqual(self.contract["classification"], "PRELIMINARY_UNPROTECTED")
        self.assertEqual(
            inputs["profile_feature_identity"],
            "ce9564bddc73cd046a89ef2ac5bb80140e738c52aa2f69e0014f64e45a34dfbb",
        )
        self.assertEqual(
            inputs["prior_run_identity"],
            "fbd173efe68ee6aebc0e897ced096c29ce4ea4c6d794029e11fcb590dee60b2a",
        )
        self.assertEqual(inputs["eligible_target_seasons"], [2023, 2024, 2025])
        self.assertEqual(inputs["partial_source_seasons"], [2020])
        self.assertFalse(self.contract["chronology_policy"]["protected_split_opened"])
        self.assertFalse(any(self.contract["protected_nonclaims"].values()))

    @unittest.skipUnless(
        RUNNER_DEPENDENCIES_AVAILABLE,
        "optional modeling runner dependencies unavailable",
    )
    def test_unsafe_profile_module_fails_closed(self) -> None:
        contract = dict(self.contract)
        contract["profile_module"] = "../outside"
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
        self.assertIn("profile module must be a safe module name", run.stderr)

    @unittest.skipIf(fit_seasons_for_prediction is None, "optional dependencies unavailable")
    def test_walk_forward_fit_plan(self) -> None:
        self.assertEqual(fit_seasons_for_prediction(2023), ())
        self.assertEqual(fit_seasons_for_prediction(2024), (2023,))
        self.assertEqual(fit_seasons_for_prediction(2025), (2023, 2024))
        with self.assertRaises(ValueError):
            fit_seasons_for_prediction(2022)

    @unittest.skipIf(build_game_profile is None, "optional dependencies unavailable")
    def test_profile_join_preserves_candidate_only_authority(self) -> None:
        target = {
            "target_game_id": "g1",
            "season": 2024,
            "start_utc": "2024-09-02T00:00:00Z",
            "cutoff_utc": "2024-09-01T00:00:00Z",
            "home_team_id": "h",
            "away_team_id": "a",
        }
        common = {
            "game_id": "g1",
            "source_known_at_utc": "2023-05-05T03:50:21Z",
            "maximum_source_effective_at_utc": "2022-11-01T00:00:00Z",
            "cold_start": False,
            "protected_eligible": False,
            "classification": "DEVELOPMENT_ONLY_HISTORICAL_KNOWN_AT_EXACT_PLAY_ENRICHMENT",
            "authority": "DEVELOPMENT_ONLY",
            "metric_authority": "SOURCE_MODEL_CANDIDATE_NOT_OFFICIAL",
            "canonical_player_identity_promoted": False,
            "official_stat_authority": False,
            **{name: 1.0 for name in PROFILE_FIELDS},
        }
        rows = [
            {**common, "team_role": "HOME", "team_id": "h", "opponent_team_id": "a"},
            {
                **common,
                "team_role": "AWAY",
                "team_id": "a",
                "opponent_team_id": "h",
                "source_play_count": 0.25,
            },
        ]
        feature = build_game_profile(target, rows)
        self.assertEqual(feature["play_enrichment_source_play_count_diff"], 0.75)
        self.assertFalse(feature["play_enrichment_protected_eligible"])
        rows[0]["official_stat_authority"] = True
        with self.assertRaisesRegex(ValueError, "official-stat authority"):
            build_game_profile(target, rows)


if __name__ == "__main__":
    unittest.main()
