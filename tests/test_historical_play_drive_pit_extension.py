from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

from aggie_analytics.temporal.play_drive_pit import _build_profiles, _eligible_source_rows


ROOT = Path(__file__).resolve().parents[1]


class HistoricalPlayDrivePitExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / "configs" / "historical_play_drive_pit_extension_contract.json").read_text(encoding="utf-8")
        )

    def test_contract_closes_season_gap_without_expanding_protected_authority(self) -> None:
        source = self.contract["source_contract"]
        self.assertEqual(source["source_seasons"], list(range(2010, 2023)))
        self.assertEqual(source["missing_source_seasons"], [])
        self.assertEqual([layer["source_seasons"] for layer in source["source_layers"]][-1], [2011, 2020])
        authority = self.contract["authority"]
        self.assertTrue(authority["development_feature_admission"])
        self.assertTrue(authority["preliminary_unprotected_training_candidate"])
        self.assertFalse(authority["protected_training_admission"])
        self.assertFalse(authority["protected_evaluation_admission"])
        self.assertFalse(authority["champion_or_production_promotion"])

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_multiple_source_dispositions_are_admitted_and_quarantine_is_excluded(self) -> None:
        source = self.contract["source_contract"]
        dispositions = source["play_dispositions"]
        rows = pl.DataFrame(
            {
                "reconciliation_disposition": [dispositions[0], dispositions[1], "QUARANTINED"],
                "value": [1, 2, 3],
            }
        )
        admitted = _eligible_source_rows(rows, source, "play")
        self.assertEqual(admitted["value"].to_list(), [1, 2])

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_profile_builder_combines_base_and_gap_rows_without_inventing_values(self) -> None:
        source = self.contract["source_contract"]
        plays = pl.DataFrame(
            {
                "reconciliation_disposition": [source["play_dispositions"][0], source["play_dispositions"][1]],
                "offense_team_id": [1, 1],
                "canonical_game_id": ["base", "gap"],
                "season": [2010, 2011],
                "epa": [0.0, 1.0],
                "stat_yardage": [2, 4],
                "rush": [True, False],
                "pass": [False, True],
                "scoring_play": [False, True],
                "interception": [False, False],
                "sack": [False, False],
                "pass_attempt": [False, True],
                "completion": [False, True],
                "source_known_at_utc": ["2022-07-25T17:33:07Z", "2022-07-25T17:33:07Z"],
                "effective_at_utc": ["2010-09-01T00:00:00Z", "2011-09-01T00:00:00Z"],
            }
        )
        drives = pl.DataFrame(
            {
                "reconciliation_disposition": [source["drive_dispositions"][0], source["drive_dispositions"][1]],
                "offense_team_id": [1, 1],
                "canonical_game_id": ["base", "gap"],
                "source_play_rows": [1, 1],
                "drive_result": ["PUNT", "TD"],
            }
        )
        team_map = pl.DataFrame({"source_team_id": ["1"], "team_id": ["team-1"]})
        profiles, counts = _build_profiles(plays, drives, team_map, self.contract)
        self.assertEqual(counts["exact_play_rows"], 2)
        self.assertEqual(counts["exact_drive_rows"], 2)
        self.assertEqual(profiles.row(0, named=True)["play_season_count"], 2)
        self.assertEqual(profiles.row(0, named=True)["epa_mean"], 0.5)


if __name__ == "__main__":
    unittest.main()
