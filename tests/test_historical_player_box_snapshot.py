from __future__ import annotations

import json
import unittest
from pathlib import Path

from aggie_analytics.temporal.player_box_snapshot import _validate_contract_authority


ROOT = Path(__file__).resolve().parents[1]


class HistoricalPlayerBoxSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((ROOT / "configs" / "historical_player_box_snapshot_contract.json").read_text(encoding="utf-8"))

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

    def test_exact_surface_excludes_outcome_and_identity_control_fields(self) -> None:
        fields = set(self.contract["disposition"]["snapshot_fields"])
        forbidden = set(self.contract["disposition"]["forbidden_snapshot_fields"])
        self.assertFalse(fields & forbidden)
        self.assertNotIn("source_team_points", fields)
        self.assertNotIn("team_box_historical_outcome_match", fields)
        self.assertIn("player_label_raw", fields)
        self.assertIn("canonical_player_id_candidate", fields)
        self.assertEqual(self.contract["acceptance"]["expected_exact_value_incomplete_identity_cells"], 55)


if __name__ == "__main__":
    unittest.main()
