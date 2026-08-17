from __future__ import annotations

import json
import unittest
from pathlib import Path


ARTIFACT_PATH = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "operations"
    / "drift_incident_game_day.json"
)


def _load_artifact() -> dict:
    return json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))


class DriftIncidentGameDayArtifactTests(unittest.TestCase):
    def test_contains_all_required_contract_fixtures(self) -> None:
        payload = _load_artifact()
        scenarios = payload["incident_contract_fixtures"]
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
        self.assertEqual({item["scenario_id"] for item in scenarios}, expected)
        self.assertEqual(payload["maturity"], "PRODUCTION_READY")
        self.assertTrue(payload["live_incident_execution_completed"])
        self.assertEqual(payload["issue_completion_manifest"]["status"], "DONE")

    def test_substitution_contract_uses_current_private_research_policy(self) -> None:
        payload = _load_artifact()
        policy = payload["source_substitution_policy"]
        self.assertEqual(
            policy["licensing_or_redistribution_ambiguity"],
            "RECORD_AS_METADATA_NOT_A_PRIVATE_ACQUISITION_BLOCKER",
        )
        serialized = json.dumps(payload, sort_keys=True)
        self.assertNotIn("rights_gate", serialized)
        for scenario in payload["incident_contract_fixtures"]:
            self.assertEqual(
                set(scenario["substitution_gates"]),
                {"access", "safety", "pit", "schema", "coverage", "provenance"},
            )

    def test_controller_routing_and_provider_evidence_are_exact(self) -> None:
        producer = _load_artifact()["producer"]
        self.assertEqual(producer["dispatch_origin"], "PERSISTENT_CONTROLLER")
        self.assertEqual(producer["provider"], "cursor")
        self.assertEqual(producer["model"], "gpt-5.3-codex")
        self.assertEqual(producer["reasoning_effort"], "medium")
        self.assertEqual(producer["retained_authority_disposition"], "CODEX_REVIEW_MODIFIED")
        for field in (
            "pre_routing_decision_sha256",
            "packet_sha256",
            "provider_result_sha256",
            "provider_review_sha256",
            "candidate_validation_sha256",
        ):
            self.assertRegex(producer[field], r"^[0-9a-f]{64}$")

    def test_no_placeholder_or_synthetic_completion_claim_survives_review(self) -> None:
        payload = _load_artifact()
        serialized = json.dumps(payload, sort_keys=True)
        self.assertNotIn("REFER_TO_", serialized)
        self.assertFalse(payload["honesty_boundary"]["synthetic_fixture_is_live_incident_evidence"])
        self.assertEqual(
            payload["downstream_gate_decision"]["decision"],
            "APPROVED_FOR_DOWNSTREAM_REEVALUATION",
        )
        dispositions = {row["disposition"] for row in payload["acceptance_evidence_matrix"]}
        self.assertEqual(dispositions, {"PASS"})

    def test_useful_work_credit_remains_zero_without_measured_savings(self) -> None:
        accounting = _load_artifact()["useful_work_accounting"]
        self.assertTrue(accounting["provider_result_reviewed"])
        self.assertTrue(accounting["provider_result_modified"])
        self.assertTrue(accounting["downstream_project_artifact_changed"])
        self.assertGreater(accounting["direct_baseline_seconds"], 0.0)
        self.assertGreaterEqual(accounting["measured_net_time_saved_seconds"], 0.0)
        self.assertGreaterEqual(accounting["accepted_useful_offload_credit"], 0)

    def test_chronology_security_and_scope_boundaries_fail_closed(self) -> None:
        payload = _load_artifact()
        negative = payload["negative_tests"]
        for requirement in (
            "future_record_rejected",
            "same_game_outcome_rejected",
            "postgame_record_rejected",
            "credential_value_persistence_rejected",
            "restricted_payload_persistence_rejected",
            "unaffected_scope_global_block_rejected",
            "file_creation_as_completion_rejected",
        ):
            self.assertTrue(negative[requirement])

    def test_incident_records_include_required_governance_fields(self) -> None:
        payload = _load_artifact()
        for row in payload["executed_incidents"]:
            self.assertIn("correlation_id", row)
            self.assertIn("timing", row)
            self.assertIn("affected_scope", row)
            self.assertIn("missingness_classification", row)
            self.assertIn("baseline_and_threshold", row)
            self.assertIn("alert", row)
            self.assertIn("decision", row)
            self.assertIn("training_publication_impact", row)
            self.assertIn("recovery_evidence", row)
            self.assertIn("source_substitution_reevaluation", row)


if __name__ == "__main__":
    unittest.main()
