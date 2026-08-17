from __future__ import annotations

import copy
import unittest
from pathlib import Path

from tools.run_leakage_battery import (
    SCENARIOS,
    _compute_artifact_identity,
    build_results,
    validate_results,
)

ROOT = Path(__file__).resolve().parents[1]


class LeakageBatteryResultsTests(unittest.TestCase):
    def test_build_results_has_required_scenarios_and_blocked_status(self) -> None:
        payload = build_results(ROOT)
        self.assertEqual(payload["schema_version"], "aggie.pit.leakage_battery.v1")
        self.assertEqual([row["scenario_id"] for row in payload["scenarios"]], SCENARIOS)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn("ROW_LEVEL_MATRIX_PAYLOADS_UNAVAILABLE", payload["remaining_blockers"])
        validate_results(payload, ROOT)

    def test_validate_rejects_semantic_tamper_even_with_recomputed_identity(self) -> None:
        payload = build_results(ROOT)
        mutated = copy.deepcopy(payload)
        row = next(item for item in mutated["scenarios"] if item["scenario_id"] == "known_at_timestamp_enforcement")
        row["observed_result"] = "FAIL"
        mutated["artifact_identity"] = _compute_artifact_identity(mutated)
        with self.assertRaisesRegex(ValueError, "scenario observed_result mismatch: known_at_timestamp_enforcement"):
            validate_results(mutated, ROOT)

    def test_validate_rejects_missing_scenario(self) -> None:
        payload = build_results(ROOT)
        payload["scenarios"] = payload["scenarios"][:-1]
        payload["artifact_identity"] = _compute_artifact_identity(payload)
        with self.assertRaisesRegex(ValueError, "scenario set/order mismatch"):
            validate_results(payload, ROOT)


if __name__ == "__main__":
    unittest.main()
