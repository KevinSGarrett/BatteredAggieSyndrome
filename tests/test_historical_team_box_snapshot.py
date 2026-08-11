from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

from aggie_analytics.temporal.team_box_snapshot import _disposition, _validate_contract_authority


ROOT = Path(__file__).resolve().parents[1]


class HistoricalTeamBoxSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((ROOT / "configs" / "historical_team_box_snapshot_contract.json").read_text(encoding="utf-8"))

    def test_contract_is_capture_time_candidate_only(self) -> None:
        _validate_contract_authority(self.contract)
        authority = self.contract["authority"]
        self.assertTrue(authority["candidate_snapshot_materialization"])
        for key in (
            "immutable_raw_capture_mutation", "canonical_entity_mutation", "historical_pit_admission",
            "preliminary_chronological_replay_admission", "protected_training_admission",
            "protected_evaluation_admission", "champion_or_production_promotion", "forecast_publication",
        ):
            self.assertFalse(authority[key])

    def test_open_historical_pit_authority_is_rejected(self) -> None:
        contract = json.loads(json.dumps(self.contract))
        contract["authority"]["historical_pit_admission"] = True
        with self.assertRaises(ValueError):
            _validate_contract_authority(contract)

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_exact_row_is_candidate_snapshot_and_source_only_row_stays_nonadmitted(self) -> None:
        contract = json.loads(json.dumps(self.contract))
        exact_disposition = contract["disposition"]["eligible_reconciliation_dispositions"][0]
        source_disposition = contract["disposition"]["nonadmitted_reconciliation_disposition"]
        contract["acceptance"].update({
            "expected_source_rows": 2, "expected_source_games": 2, "expected_exact_rows": 1,
            "expected_exact_games": 1, "expected_exact_teams": 1, "expected_exact_stat_cells": 1,
            "expected_nonadmitted_rows": 1, "expected_nonadmitted_games": 1,
            "expected_side_swap_rows": 0, "expected_side_swap_games": 0, "expected_outcome_overlap_rows": 2,
            "expected_disposition_counts": {exact_disposition: 1, source_disposition: 1},
            "expected_exact_by_season": {"2020": 1}, "expected_nonadmitted_by_season": {"2020": 1},
        })
        stats_json = '[{"category":"totalYards","stat":"100"}]'
        common = {field: None for field in contract["disposition"]["snapshot_fields"]}
        common.update({
            "schema_version": "1.0.0", "season": 2020, "season_type": "regular", "week": 1,
            "source_team_id": "1", "source_team": "Team", "source_conference": "League", "home_away": "home",
            "points": 7, "stats_json": stats_json, "stats_sha256": hashlib.sha256(stats_json.encode()).hexdigest(),
            "stats_category_count": 1, "duplicate_stats_categories_json": "[]", "source_capture_id": "cap",
            "source_request_id": "req", "source_response_sha256": "a" * 64, "source_response_bytes": 10,
            "source_game_row_number": 1, "source_team_row_number": 1, "capture_known_at_utc": "2026-08-09T19:00:00Z",
            "source_record_evidence_sha256": "b" * 64, "historical_outcome_observation_id": "outcome",
            "historical_outcome_source_known_at_utc": "2023-05-05T00:00:00Z", "historical_side_points": 7,
            "historical_game_side_point_match": True, "historical_side_alignment": "DIRECT_SIDE_AND_POINTS",
            "historical_known_at_state": contract["source_contract"]["historical_known_at_state"], "row_lineage_sha256": "c" * 64,
            "current_canonical_team_box_id": None, "current_capture_points_match": None,
            "current_capture_stats_match": None, "current_capture_exact_match": None, "admission_state": "CANDIDATE",
        })
        rows = [
            {**common, "source_game_id": "g1", "observation_id": "o1", "canonical_game_id_candidate": "cg1", "canonical_team_id_candidate": "ct1", "reconciliation_disposition": exact_disposition},
            {**common, "source_game_id": "g2", "observation_id": "o2", "canonical_game_id_candidate": None, "canonical_team_id_candidate": None, "reconciliation_disposition": source_disposition},
        ]
        snapshot, cells, nonadmitted, profile = _disposition(pl.DataFrame(rows), contract)
        self.assertEqual(profile["exact_rows"], 1)
        self.assertEqual(nonadmitted.height, 1)
        self.assertFalse(snapshot["historical_pit_eligible"].item())
        self.assertFalse(snapshot["preliminary_replay_eligible"].item())
        self.assertEqual(cells["stat_value_raw"].item(), "100")
        self.assertEqual(cells["stat_value_parse_state"].item(), "RAW_SOURCE_TEXT_NOT_PARSED")


if __name__ == "__main__":
    unittest.main()
