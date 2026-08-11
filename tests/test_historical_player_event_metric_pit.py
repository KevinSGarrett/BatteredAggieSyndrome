from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

from aggie_analytics.temporal.player_event_metric_pit import (
    _admitted_state,
    _build_features,
    _build_profiles,
    cutoff_utc,
    disposition_counts,
)


ROOT = Path(__file__).resolve().parents[1]


class HistoricalPlayerEventMetricPitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((ROOT / "configs" / "historical_player_event_metric_pit_contract.json").read_text(encoding="utf-8"))

    def test_cutoff_is_explicitly_before_target_start(self) -> None:
        self.assertEqual(cutoff_utc("2023-08-26T18:30:00Z", 24), "2023-08-25T18:30:00Z")

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_only_exact_rows_enter_state_and_missing_metrics_remain_null(self) -> None:
        exact = self.contract["source_contract"]["eligible_disposition"]
        common = {
            "season": 2022, "game_id": 1, "canonical_game_id": "old-1", "player_id": "p1",
            "canonical_player_id": "cp1", "canonical_membership_player_id": "cp1", "canonical_team_id": "t1",
            "canonical_team_label": "Team", "aggregation": "SUM", "source_event_rows": 1,
            "source_capture_id": "c", "source_payload_sha256": "a", "source_commit_sha": self.contract["source_contract"]["source_commit_sha"],
            "source_known_at_utc": self.contract["source_contract"]["source_known_at_utc"], "source_schema_sha256": "s",
            "source_aggregate_evidence_sha256": "e", "current_capture_id": "cc", "current_payload_sha256": "cp",
            "current_request_sha256": "cr", "upstream_independence": self.contract["source_contract"]["cross_route_independence"],
        }
        rows = []
        for index, (category, stat_type, value, disposition) in enumerate([
            ("passing", "YDS", 250, exact),
            ("rushing", "YDS", 100, "QUARANTINE_CROSS_ROUTE_PLAYER_METRIC_VALUE_CONFLICT"),
        ]):
            rows.append({**common, "observation_id": f"o{index}", "category": category, "stat_type": stat_type, "source_value": value,
                         "reconciliation_disposition": disposition, "row_lineage_sha256": f"h{index}"})
        candidates = pl.DataFrame(rows)
        self.assertEqual(disposition_counts(candidates)[exact], 1)
        state = _admitted_state(candidates, self.contract)
        profiles = _build_profiles(state, self.contract)
        self.assertEqual(state.height, 1)
        self.assertEqual(profiles["passing_yds"].item(), 250)
        self.assertIsNone(profiles["rushing_yds_per_source_game"].item())

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_target_features_preserve_cold_start_and_authority(self) -> None:
        profiles = pl.DataFrame({
            "team_id": ["t1"], "source_game_count": [1], "source_known_at_utc": ["2023-05-05T03:50:21Z"],
            "authority": ["DEVELOPMENT_ONLY"], "protected_eligible": [False],
        })
        targets = pl.DataFrame({
            "game_id": ["target-1"], "season": [2023], "season_type": ["regular"], "week": [1],
            "start_utc": ["2023-08-26T18:30:00Z"], "cutoff_lead_hours": [24],
            "home_team_id": ["t1"], "away_team_id": ["t2"], "neutral_site": [False],
        })
        features = _build_features(targets, profiles, self.contract)
        home = features.filter(pl.col("team_role") == "HOME").row(0, named=True)
        away = features.filter(pl.col("team_role") == "AWAY").row(0, named=True)
        self.assertFalse(home["cold_start"])
        self.assertTrue(away["cold_start"])
        self.assertFalse(home["protected_eligible"])
        self.assertFalse(home["official_player_box_complete"])

    def test_contract_keeps_complete_and_protected_authority_closed(self) -> None:
        authority = self.contract["authority"]
        self.assertTrue(authority["pit_state_admission"])
        self.assertTrue(authority["development_feature_admission"])
        self.assertFalse(authority["official_player_box_completeness"])
        self.assertFalse(authority["protected_training_admission"])
        self.assertFalse(authority["protected_evaluation_admission"])
        self.assertFalse(authority["champion_or_production_promotion"])


if __name__ == "__main__":
    unittest.main()
