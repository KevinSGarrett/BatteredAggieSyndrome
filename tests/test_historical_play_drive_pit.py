from __future__ import annotations

import json
import unittest
from pathlib import Path

import polars as pl

from aggie_analytics.temporal.play_drive_pit import (
    _build_features,
    _build_profiles,
    classify_drive_result,
    cutoff_utc,
)


ROOT = Path(__file__).resolve().parents[1]


class HistoricalPlayDrivePitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / "configs" / "historical_play_drive_pit_aggregate_contract.json").read_text(encoding="utf-8")
        )

    def test_cutoff_is_explicitly_before_target_start(self) -> None:
        self.assertEqual(cutoff_utc("2023-08-26T18:30:00Z", 24), "2023-08-25T18:30:00Z")

    def test_drive_result_classes_are_conservative(self) -> None:
        self.assertEqual(classify_drive_result("RUSHING TD", self.contract), (True, False, False))
        self.assertEqual(classify_drive_result("FG GOOD", self.contract), (False, True, False))
        self.assertEqual(classify_drive_result("INT", self.contract), (False, False, True))
        self.assertEqual(classify_drive_result("INT RETURN TOUCH", self.contract), (False, False, False))

    def test_profiles_and_target_rows_preserve_cold_start(self) -> None:
        play_disposition = self.contract["source_contract"]["play_disposition"]
        drive_disposition = self.contract["source_contract"]["drive_disposition"]
        plays = pl.DataFrame(
            {
                "reconciliation_disposition": [play_disposition, play_disposition],
                "offense_team_id": [1, 1],
                "canonical_game_id": ["old-1", "old-2"],
                "season": [2021, 2022],
                "epa": [0.1, -0.1],
                "stat_yardage": [5, 3],
                "rush": [True, False],
                "pass": [False, True],
                "scoring_play": [False, True],
                "interception": [False, False],
                "sack": [False, False],
                "pass_attempt": [False, True],
                "completion": [False, True],
                "source_known_at_utc": ["2023-05-01T00:00:00Z", "2023-05-02T00:00:00Z"],
                "effective_at_utc": ["2021-09-01T00:00:00Z", "2022-09-01T00:00:00Z"],
            }
        )
        drives = pl.DataFrame(
            {
                "reconciliation_disposition": [drive_disposition],
                "offense_team_id": [1],
                "canonical_game_id": ["old-2"],
                "source_play_rows": [2],
                "drive_result": ["TD"],
            }
        )
        targets = pl.DataFrame(
            {
                "game_id": ["target-1"],
                "season": [2023],
                "season_type": ["regular"],
                "week": [1],
                "start_utc": ["2023-08-26T18:30:00Z"],
                "cutoff_lead_hours": [24],
                "home_team_id": ["1"],
                "away_team_id": ["2"],
                "neutral_site": [False],
            }
        )
        team_map = pl.DataFrame({"source_team_id": ["1"], "team_id": ["1"]})
        profiles, counts = _build_profiles(plays, drives, team_map, self.contract)
        rows = _build_features(targets, profiles)
        self.assertEqual(counts["exact_play_rows"], 2)
        self.assertEqual(rows.height, 2)
        home = rows.filter(pl.col("team_role") == "HOME").row(0, named=True)
        away = rows.filter(pl.col("team_role") == "AWAY").row(0, named=True)
        self.assertFalse(home["cold_start"])
        self.assertEqual(home["play_count"], 2)
        self.assertTrue(away["cold_start"])
        self.assertIsNone(away["play_count"])
        self.assertFalse(home["protected_eligible"])

    def test_contract_keeps_protected_authority_closed(self) -> None:
        authority = self.contract["authority"]
        self.assertTrue(authority["pit_state_admission"])
        self.assertTrue(authority["development_feature_admission"])
        self.assertFalse(authority["protected_training_admission"])
        self.assertFalse(authority["protected_evaluation_admission"])
        self.assertFalse(authority["champion_or_production_promotion"])


if __name__ == "__main__":
    unittest.main()
