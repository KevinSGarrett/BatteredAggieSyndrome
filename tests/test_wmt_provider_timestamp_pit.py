from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

from aggie_analytics.temporal.wmt_provider_timestamp_pit import (
    _build_coverage,
    nested_record,
    provider_known_at,
)


ROOT = Path(__file__).resolve().parents[1]


class WmtProviderTimestampPitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((ROOT / "configs" / "wmt_provider_timestamp_pit_contract.json").read_text(encoding="utf-8"))

    def test_maximum_provider_version_is_known_at(self) -> None:
        value, fields = provider_known_at(
            {"created_at": "2021-01-01T00:00:00Z", "updated_at": "2022-03-04T05:06:07Z"},
            ["created_at", "updated_at"],
        )
        self.assertEqual(value, "2022-03-04T05:06:07Z")
        self.assertEqual(fields, ["updated_at"])

    def test_missing_invalid_and_timezone_less_timestamps_fail_closed(self) -> None:
        for record in ({}, {"created_at": "bad"}, {"created_at": "2021-01-01T00:00:00"}):
            with self.assertRaises(ValueError):
                provider_known_at(record, ["created_at", "updated_at"])

    def test_domain_path_never_falls_back_to_outer_game_time(self) -> None:
        outer = {"game_date": "2013-08-31T00:00:00Z", "action": {"created_at": "2020-06-18T00:00:00Z"}}
        exact = nested_record(outer, ["action"])
        self.assertNotIn("game_date", exact)
        self.assertEqual(provider_known_at(exact, ["created_at"])[0], "2020-06-18T00:00:00Z")

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_coverage_requires_both_effective_and_provider_time_before_cutoff(self) -> None:
        records = pl.DataFrame(
            {
                "domain": ["game", "game", "plays"],
                "wmt_game_id": ["old", "future", "old"],
                "available_at_utc": ["2021-01-01T00:00:00Z", "2024-01-01T00:00:00Z", "2022-01-01T00:00:00Z"],
            }
        )
        targets = pl.DataFrame(
            {
                "game_id": ["target"], "season": [2023], "season_type": ["regular"], "week": [1],
                "start_utc": ["2023-09-01T00:00:00Z"], "cutoff_lead_hours": [24],
            }
        )
        row = _build_coverage(records, targets, self.contract["classification"]).row(0, named=True)
        self.assertEqual(row["game_record_count"], 1)
        self.assertEqual(row["plays_record_count"], 1)
        self.assertEqual(row["total_record_count"], 2)
        self.assertTrue(row["coverage_diagnostic_only"])
        self.assertFalse(row["protected_eligible"])

    def test_contract_keeps_protected_and_direct_model_authority_closed(self) -> None:
        authority = self.contract["authority"]
        self.assertTrue(authority["development_pit_state_admission"])
        self.assertFalse(authority["preliminary_unprotected_training_direct_feature"])
        self.assertFalse(authority["protected_training_admission"])
        self.assertFalse(authority["champion_or_production_promotion"])


if __name__ == "__main__":
    unittest.main()
