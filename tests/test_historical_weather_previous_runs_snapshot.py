from __future__ import annotations

import json
import unittest
from pathlib import Path

from aggie_analytics.temporal.weather_previous_runs_snapshot import _validate_contract_authority


ROOT = Path(__file__).resolve().parents[1]


class HistoricalWeatherPreviousRunsSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / "configs" / "historical_weather_previous_runs_snapshot_contract.json").read_text(encoding="utf-8")
        )

    def test_contract_is_nominal_lead_candidate_only(self) -> None:
        _validate_contract_authority(self.contract)
        authority = self.contract["authority"]
        self.assertTrue(authority["candidate_snapshot_materialization"])
        self.assertTrue(authority["nominal_lead_semantics_verified"])
        for key in (
            "immutable_raw_capture_mutation",
            "canonical_weather_mutation",
            "exact_run_initialization_inference",
            "api_availability_inference",
            "venue_effective_time_backcast",
            "observed_weather_substitution",
            "historical_pit_admission",
            "preliminary_chronological_replay_admission",
            "protected_training_admission",
            "protected_evaluation_admission",
            "champion_or_production_promotion",
            "forecast_publication",
        ):
            self.assertFalse(authority[key])

    def test_open_historical_pit_authority_is_rejected(self) -> None:
        contract = json.loads(json.dumps(self.contract))
        contract["authority"]["historical_pit_admission"] = True
        with self.assertRaises(ValueError):
            _validate_contract_authority(contract)

    def test_snapshot_excludes_outcomes_and_preserves_unknown_time_fields(self) -> None:
        fields = set(self.contract["disposition"]["snapshot_fields"])
        forbidden = set(self.contract["disposition"]["forbidden_snapshot_fields"])
        self.assertFalse(fields & forbidden)
        self.assertNotIn("home_points", fields)
        self.assertNotIn("away_points", fields)
        self.assertIn("historical_model_run_initialization_at_utc", fields)
        self.assertIn("historical_api_available_at_utc", fields)
        self.assertEqual(self.contract["acceptance"]["expected_nonadmitted_cells"], 75350)


if __name__ == "__main__":
    unittest.main()
