from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

from aggie_analytics.temporal.advanced_game_snapshot import _disposition, _flatten_paths, _validate_contract_authority


ROOT = Path(__file__).resolve().parents[1]


class HistoricalAdvancedGameSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((ROOT / "configs" / "historical_advanced_game_snapshot_contract.json").read_text(encoding="utf-8"))

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

    def test_nested_paths_distinguish_structure_and_leaves(self) -> None:
        structure, leaves = _flatten_paths({"offense": {"ppa": 0.1, "passing": {"success": 0.4}}})
        self.assertEqual(structure, {"offense", "offense.ppa", "offense.passing", "offense.passing.success"})
        self.assertEqual(leaves, {"offense.ppa": 0.1, "offense.passing.success": 0.4})

    @unittest.skipIf(pl is None, "optional data-engineering dependency polars is not installed")
    def test_team_box_only_collision_stays_nonadmitted(self) -> None:
        contract = json.loads(json.dumps(self.contract))
        eligible = contract["disposition"]["eligible_reconciliation_dispositions"][0]
        collision = "CANDIDATE_TEAM_BOX_GAME_TEAM_LINKED_ADVANCED_STATS"
        contract["acceptance"].update({
            "expected_source_rows": 3, "expected_source_games": 2, "expected_exact_rows": 1, "expected_exact_games": 1,
            "expected_exact_teams": 1, "expected_nonadmitted_rows": 2, "expected_nonadmitted_games": 1,
            "expected_team_box_link_rows": 3, "expected_team_box_outcome_match_rows": 1,
            "expected_team_box_only_collision_rows": 2, "expected_team_box_only_collision_games": 1,
            "expected_disposition_counts": {eligible: 1, collision: 2}, "expected_exact_by_season": {"2020": 1},
            "expected_nonadmitted_by_season": {"2020": 2},
        })
        common = {field: None for field in set(contract["disposition"]["snapshot_fields"]) | {"current_canonical_advanced_id", "current_capture_exact_match", "admission_state"}}
        common.update({
            "schema_version": "1.0.0", "season": 2020, "season_type": "regular", "week": 1,
            "source_capture_id": "cap", "source_request_id": "req", "source_response_sha256": "a" * 64,
            "source_response_bytes": 10, "source_row_number": 1, "capture_known_at_utc": "2026-08-09T19:00:00Z",
            "source_record_evidence_sha256": "b" * 64, "offense_json": "{}", "offense_sha256": "c" * 64,
            "defense_json": "{}", "defense_sha256": "d" * 64, "team_box_observation_id": "tb",
            "historical_known_at_state": contract["source_contract"]["historical_known_at_state"], "row_lineage_sha256": "e" * 64,
        })
        rows = [
            {**common, "source_game_id": "g1", "source_team": "A", "source_team_normalized": "a", "source_opponent": "B", "source_opponent_normalized": "b", "observation_id": "o1", "canonical_game_id_candidate": "cg1", "canonical_team_id_candidate": "ct1", "canonical_opponent_id_candidate": "ct2", "home_away_candidate": "home", "team_box_historical_outcome_match": True, "reconciliation_disposition": eligible},
            {**common, "source_game_id": "g2", "source_team": "C", "source_team_normalized": "c", "source_opponent": "D", "source_opponent_normalized": "d", "observation_id": "o2", "canonical_game_id_candidate": "cg2", "canonical_team_id_candidate": "ct3", "canonical_opponent_id_candidate": "ct3", "home_away_candidate": "home", "team_box_historical_outcome_match": None, "reconciliation_disposition": collision},
            {**common, "source_game_id": "g2", "source_team": "D", "source_team_normalized": "d", "source_opponent": "C", "source_opponent_normalized": "c", "observation_id": "o3", "canonical_game_id_candidate": "cg2", "canonical_team_id_candidate": "ct3", "canonical_opponent_id_candidate": "ct3", "home_away_candidate": "away", "team_box_historical_outcome_match": None, "reconciliation_disposition": collision},
        ]
        snapshot, nonadmitted, profile = _disposition(pl.DataFrame(rows), contract)
        self.assertEqual(snapshot.height, 1)
        self.assertEqual(nonadmitted.height, 2)
        self.assertEqual(profile["team_box_only_collision_games"], 1)
        self.assertEqual(nonadmitted["nonadmission_reason"].unique().to_list(), ["TEAM_BOX_ONLY_LINK_WITH_DUPLICATE_CANONICAL_GAME_TEAM_COLLISION"])
        self.assertFalse(snapshot["historical_pit_eligible"].item())


if __name__ == "__main__":
    unittest.main()
