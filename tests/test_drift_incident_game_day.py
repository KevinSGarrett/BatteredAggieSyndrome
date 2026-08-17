from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.operations.incidents import (  # noqa: E402
    run_incident_drill,
    validate_incident_artifact,
)


class DriftIncidentGameDayExecutionTests(unittest.TestCase):
    def _run(self) -> tuple[dict, Path]:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        artifact = root / "drift_incident_game_day.json"
        payload = run_incident_drill(output_path=artifact, work_root=root / "work")
        return payload, artifact

    def test_runner_executes_all_required_scenarios(self) -> None:
        payload, artifact = self._run()
        validate_incident_artifact(payload)
        loaded = json.loads(artifact.read_text(encoding="utf-8"))
        self.assertEqual(loaded["artifact_identity"], payload["artifact_identity"])
        self.assertEqual(loaded["maturity"], "DETERMINISTIC_LOCAL_INCIDENT_DRILL_VERIFIED")
        self.assertFalse(loaded["live_incident_execution_completed"])
        expected = {
            "outage",
            "schema",
            "stale_forecast",
            "disk",
            "corrupt_artifact",
            "model",
            "security",
            "governance_conflict",
        }
        self.assertEqual({row["scenario_id"] for row in loaded["executed_incidents"]}, expected)

    def test_fail_closed_guards_are_observed_not_attested(self) -> None:
        payload, _ = self._run()
        by_id = {row["scenario_id"]: row for row in payload["executed_incidents"]}
        self.assertTrue(by_id["outage"]["unsafe_training_blocked"])
        self.assertTrue(by_id["schema"]["validator_rejected_payload"])
        self.assertTrue(by_id["stale_forecast"]["freshness_gate_rejected"])
        self.assertTrue(by_id["disk"]["last_known_good_unchanged"])
        self.assertTrue(by_id["corrupt_artifact"]["verification_rejected_corruption"])
        self.assertTrue(by_id["model"]["publication_failed_closed"])
        self.assertTrue(by_id["security"]["persisted_events_redacted_only"])
        self.assertTrue(by_id["governance_conflict"]["execution_rejected"])
        self.assertFalse(by_id["security"]["raw_secret_present"])

    def test_artifact_identity_rejects_fabricated_mutation(self) -> None:
        payload, _ = self._run()
        mutated = json.loads(json.dumps(payload))
        mutated["executed_incidents"][0]["unsafe_training_blocked"] = False
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            validate_incident_artifact(mutated)


if __name__ == "__main__":
    unittest.main()
