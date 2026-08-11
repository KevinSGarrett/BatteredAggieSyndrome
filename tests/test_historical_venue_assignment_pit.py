from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

from aggie_analytics.temporal.venue_assignment_pit import _disposition, normalize_numeric_identifier


ROOT = Path(__file__).resolve().parents[1]


class HistoricalVenueAssignmentPitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((ROOT / "configs" / "historical_venue_assignment_pit_contract.json").read_text(encoding="utf-8"))

    def test_numeric_identifier_schema_variants_normalize_exactly(self) -> None:
        self.assertEqual(normalize_numeric_identifier(312440275), "312440275")
        self.assertEqual(normalize_numeric_identifier(312440275.0), "312440275")
        self.assertEqual(normalize_numeric_identifier("312440275.0"), "312440275")
        for invalid in (None, True, "", "312440275.5", float("nan")):
            with self.assertRaises(ValueError):
                normalize_numeric_identifier(invalid)

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_only_explicit_id_and_name_enter_admitted_state(self) -> None:
        common = {
            "season_type": 2, "game_start_utc": "2022-09-01T00:00:00Z", "home_team_id": "h", "away_team_id": "a",
            "venue_address_city": None, "venue_address_state": None, "venue_capacity_source_raw": 0.0, "venue_capacity": None, "venue_indoor": None,
            "venue_source_capture_id": "c", "venue_source_payload_sha256": "p", "venue_source_commit_sha": "k",
            "venue_source_known_at_utc": "2023-05-05T00:00:00Z", "venue_source_schema_sha256": "s",
            "source_game_id_dtype": "Int32", "partial_source_season": False,
        }
        joined = pl.DataFrame([
            {**common, "source_game_id": "1", "canonical_game_id": "g1", "season": 2022, "venue_id": "100", "venue_full_name": "Field"},
            {**common, "source_game_id": "2", "canonical_game_id": "g2", "season": 2022, "venue_id": None, "venue_full_name": None},
        ])
        state, quarantine = _disposition(joined, self.contract)
        self.assertEqual(state.height, 1)
        self.assertEqual(quarantine.height, 1)
        self.assertEqual(quarantine["disposition"].item(), "NOT_PRESENT_VENUE_ID_AND_NAME")
        self.assertEqual(state["venue_capacity_source_raw"].item(), 0.0)
        self.assertIsNone(state["venue_capacity"].item())
        self.assertFalse(state["timeless_canonical_venue_truth"].item())
        self.assertFalse(state["protected_eligible"].item())

    def test_contract_prohibits_backfill_and_protected_authority(self) -> None:
        authority = self.contract["authority"]
        self.assertTrue(authority["pit_state_admission"])
        self.assertTrue(authority["record_time_venue_evidence"])
        self.assertFalse(authority["timeless_canonical_venue_catalog"])
        self.assertFalse(authority["current_catalog_historical_backfill"])
        self.assertFalse(authority["protected_training_admission"])
        self.assertFalse(authority["protected_evaluation_admission"])
        self.assertFalse(authority["champion_or_production_promotion"])


if __name__ == "__main__":
    unittest.main()
