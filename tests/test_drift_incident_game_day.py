from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.operations.incidents import (  # noqa: E402
    compute_incident_artifact_identity,
    run_incident_drill,
    validate_incident_artifact,
)


class DriftIncidentGameDayExecutionTests(unittest.TestCase):
    def _run(self) -> tuple[dict, Path]:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        artifact = root / "drift_incident_game_day.json"
        payload = run_incident_drill(
            output_path=artifact,
            work_root=root / "work",
            repo_root=ROOT,
        )
        return payload, artifact

    def test_runner_executes_all_required_scenarios(self) -> None:
        payload, artifact = self._run()
        validate_incident_artifact(payload, repo_root=ROOT)
        loaded = json.loads(artifact.read_text(encoding="utf-8"))
        self.assertEqual(loaded["artifact_identity"], payload["artifact_identity"])
        self.assertEqual(loaded["maturity"], "DETERMINISTIC_LOCAL_INCIDENT_DRILL_VERIFIED")
        self.assertFalse(loaded["live_incident_execution_completed"])
        self.assertEqual(loaded["eligibility"], "EXTERNAL_DELIVERY_NOT_CONFIGURED")
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
        self.assertFalse(by_id["outage"]["external_delivery_claimed"])
        self.assertEqual(len(by_id["outage"]["control_observations"]), 3)
        self.assertTrue(by_id["schema"]["validator_rejected_payload"])
        self.assertEqual(by_id["schema"]["state_hash_before"], by_id["schema"]["state_hash_after"])
        self.assertTrue(by_id["stale_forecast"]["freshness_gate_rejected"])
        self.assertTrue(by_id["disk"]["last_known_good_unchanged"])
        self.assertTrue(by_id["disk"]["recovery_path_observed"])
        self.assertTrue(by_id["corrupt_artifact"]["verification_rejected_corruption"])
        self.assertNotEqual(
            by_id["corrupt_artifact"]["corrupt_archive_sha256"],
            by_id["corrupt_artifact"]["baseline_backup_sha256"],
        )
        self.assertTrue(by_id["model"]["publication_failed_closed"])
        self.assertEqual(by_id["model"]["publication_decision"], "REJECT_UNREGISTERED_MODEL")
        self.assertTrue(by_id["security"]["persisted_events_redacted_only"])
        self.assertTrue(by_id["governance_conflict"]["execution_rejected"])
        self.assertFalse(by_id["security"]["raw_secret_present"])

    def test_semantic_contract_rejects_fabricated_mutation_even_with_new_identity(self) -> None:
        payload, _ = self._run()
        mutated = json.loads(json.dumps(payload))
        mutated["executed_incidents"][0]["unsafe_training_blocked"] = False
        mutated["artifact_identity"] = compute_incident_artifact_identity(mutated)
        with self.assertRaisesRegex(ValueError, "not derived from observations"):
            validate_incident_artifact(mutated, repo_root=ROOT)

    def test_validator_rejects_tampered_outage_raw_observation_after_rehash(self) -> None:
        payload, _ = self._run()
        mutated = json.loads(json.dumps(payload))
        mutated["executed_incidents"][0]["control_observations"][0]["decision"] = "ALLOW_LOCAL_RECOVERY_ONLY"
        mutated["executed_incidents"][0]["control_observations"][0]["allowed"] = True
        mutated["artifact_identity"] = compute_incident_artifact_identity(mutated)
        with self.assertRaisesRegex(ValueError, "do not match evaluate_outage_control"):
            validate_incident_artifact(mutated, repo_root=ROOT)

    def test_validator_rejects_tampered_schema_hashes_after_rehash(self) -> None:
        payload, _ = self._run()
        mutated = json.loads(json.dumps(payload))
        schema = next(row for row in mutated["executed_incidents"] if row["scenario_id"] == "schema")
        schema["state_hash_after"] = "a" * 64
        schema["unaffected_scopes_preserved"] = True
        mutated["artifact_identity"] = compute_incident_artifact_identity(mutated)
        with self.assertRaisesRegex(ValueError, "not derived from observations"):
            validate_incident_artifact(mutated, repo_root=ROOT)

    def test_validator_rejects_tampered_model_guard_inputs_after_rehash(self) -> None:
        payload, _ = self._run()
        mutated = json.loads(json.dumps(payload))
        model = next(row for row in mutated["executed_incidents"] if row["scenario_id"] == "model")
        model["model_id"] = "model-prod-a"
        model["threshold_values"] = {"THR-001": 0.5}
        model["protected_results_available"] = True
        model["precommitted_criteria_passed"] = True
        model["publication_failed_closed"] = True
        mutated["artifact_identity"] = compute_incident_artifact_identity(mutated)
        with self.assertRaisesRegex(ValueError, "not derived from observations"):
            validate_incident_artifact(mutated, repo_root=ROOT)

    def test_validator_rejects_tampered_governance_conclusion_after_rehash(self) -> None:
        payload, _ = self._run()
        mutated = json.loads(json.dumps(payload))
        gov = next(row for row in mutated["executed_incidents"] if row["scenario_id"] == "governance_conflict")
        gov["execution_rejected"] = False
        gov["governance_conflict_detected"] = False
        mutated["artifact_identity"] = compute_incident_artifact_identity(mutated)
        with self.assertRaisesRegex(ValueError, "not derived from observations"):
            validate_incident_artifact(mutated, repo_root=ROOT)

    def test_validation_rejects_missing_scenario(self) -> None:
        payload, _ = self._run()
        mutated = json.loads(json.dumps(payload))
        mutated["executed_incidents"] = [
            row for row in mutated["executed_incidents"] if row["scenario_id"] != "model"
        ]
        mutated["artifact_identity"] = compute_incident_artifact_identity(mutated)
        with self.assertRaisesRegex(ValueError, "scenario coverage mismatch"):
            validate_incident_artifact(mutated, repo_root=ROOT)

    def test_validation_rejects_duplicate_scenario(self) -> None:
        payload, _ = self._run()
        mutated = json.loads(json.dumps(payload))
        mutated["executed_incidents"].append(dict(mutated["executed_incidents"][0]))
        mutated["artifact_identity"] = compute_incident_artifact_identity(mutated)
        with self.assertRaisesRegex(ValueError, "duplicate scenario_id"):
            validate_incident_artifact(mutated, repo_root=ROOT)

    def test_validation_rejects_unknown_scenario(self) -> None:
        payload, _ = self._run()
        mutated = json.loads(json.dumps(payload))
        mutated["executed_incidents"][0]["scenario_id"] = "unknown_scenario"
        mutated["artifact_identity"] = compute_incident_artifact_identity(mutated)
        with self.assertRaisesRegex(ValueError, "unknown scenario_id"):
            validate_incident_artifact(mutated, repo_root=ROOT)


if __name__ == "__main__":
    unittest.main()
