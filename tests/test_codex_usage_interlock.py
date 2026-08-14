from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.validate_codex_usage_interlock import (
    ROOT,
    _validate_change_binding,
    validate,
)


class CodexUsageInterlockTests(unittest.TestCase):
    def test_static_contract_is_fail_closed_and_consistent(self) -> None:
        report = validate("static", Path(tempfile.gettempdir()))
        self.assertEqual([], report["findings"])
        self.assertEqual("PASS", report["result"])
        self.assertEqual("NOT_OPERATIONAL", report["runtime_state"])
        self.assertIs(report["codex_project_work_allowed"], False)

    def test_runtime_fails_when_independent_proof_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = validate("runtime", Path(directory))
        self.assertEqual("FAIL", report["result"])
        self.assertTrue(
            any(
                item.startswith("RUNTIME_PROOF_MISSING:") for item in report["findings"]
            )
        )
        self.assertNotIn("BLACK_BOX_EXACT_MAIN_DEPLOYMENT_MISMATCH", report["findings"])

    def test_clean_precommit_does_not_replay_historical_manifest_diff(self) -> None:
        with patch(
            "tools.validate_codex_usage_interlock._changed_paths",
            return_value=[],
        ):
            report = validate("pre-commit", Path(tempfile.gettempdir()))
        self.assertEqual([], report["findings"])
        self.assertEqual("PASS", report["result"])

    def test_staged_precommit_still_requires_exact_manifest_binding(self) -> None:
        with patch(
            "tools.validate_codex_usage_interlock._changed_paths",
            return_value=["tools/validate_codex_usage_interlock.py"],
        ):
            report = validate("pre-commit", Path(tempfile.gettempdir()))
        self.assertEqual("FAIL", report["result"])
        self.assertTrue(
            any(
                item.startswith("CHANGE_MANIFEST_DIFF_MISMATCH:")
                for item in report["findings"]
            )
        )

    def test_policy_forbids_billing_motive_inference(self) -> None:
        policy = json.loads(
            (
                ROOT / "instructions/policies/assistive_execution_interlock.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIs(
            policy["epistemic_boundary"]["billing_motive_claim_allowed"], False
        )

    def test_bootstrap_allowlist_admits_only_the_exact_service_switcher_path(
        self,
    ) -> None:
        policy = json.loads(
            (
                ROOT / "instructions/policies/assistive_execution_interlock.json"
            ).read_text(encoding="utf-8")
        )
        allowed = policy["bootstrap_allowed_paths"]
        self.assertIn("tools/switch_unified_assistive_services.ps1", allowed)
        self.assertNotIn("tools/", allowed)

    @staticmethod
    def _routed_project_fixture() -> tuple[dict, dict, dict]:
        policy = json.loads(
            (
                ROOT / "instructions/policies/assistive_execution_interlock.json"
            ).read_text(encoding="utf-8")
        )
        digest = "a" * 64
        manifest = {
            "work_unit_id": "AUTO-CURSOR-example",
            "jira_identity": "BAT-900",
            "work_class": "PROJECT_WORK",
            "ordinary_project_work_authorized": False,
            "base_commit": "e" * 40,
            "pre_routing_decision_sha256": digest,
            "changed_paths": ["artifacts/operations/example.json"],
        }
        binding = {
            "work_unit_id": "AUTO-CURSOR-example",
            "jira_identity": "BAT-900",
            "class": "PROJECT_WORK",
            "ordinary_project_work_authorized": False,
            "decision_sha256": digest,
            "source_commit": "e" * 40,
            "disposition": "ROUTED_TO_ASSISTIVE_PLANE",
            "allowed_paths": ["artifacts/operations/example.json"],
            "routed_project_adoption": {
                "dispatch_origin": "PERSISTENT_CONTROLLER",
                "manual_or_session_initiated": False,
                "unjustified_direct_execution": False,
                "provider_result_disposition": "REVIEW_ONLY",
                "final_disposition": "CODEX_REVIEW_MODIFIED",
                "provider_request_sha256": "b" * 64,
                "provider_result_sha256": "c" * 64,
                "provider_review_sha256": "d" * 64,
                "route_identity": "e" * 64,
                "schema_identity": "f" * 64,
                "policy_identity": "1" * 64,
                "provider": "cursor",
                "model": "gpt-5.3-codex",
                "task_format": "governed_cursor_repository_review_v1",
                "downstream_consumer": "POST-SUBTASK-129",
                "cleanup_contract": "Remove only verified reconstructible temporary files.",
                "codex_modifications": [
                    "Integrate the reviewed candidate within the routed scope."
                ],
            },
        }
        return policy, manifest, binding

    def test_controller_routed_review_modified_project_change_is_admitted(self) -> None:
        policy, manifest, binding = self._routed_project_fixture()
        findings: list[str] = []
        _validate_change_binding(policy, manifest, binding, findings)
        self.assertEqual([], findings)

    def test_manual_project_dispatch_is_rejected(self) -> None:
        policy, manifest, binding = self._routed_project_fixture()
        binding["routed_project_adoption"]["manual_or_session_initiated"] = True
        findings: list[str] = []
        _validate_change_binding(policy, manifest, binding, findings)
        self.assertIn("PROJECT_WORK_MANUAL_DISPATCH_FORBIDDEN", findings)

    def test_review_only_result_cannot_be_silently_accepted(self) -> None:
        policy, manifest, binding = self._routed_project_fixture()
        binding["routed_project_adoption"]["final_disposition"] = "ACCEPTED"
        findings: list[str] = []
        _validate_change_binding(policy, manifest, binding, findings)
        self.assertIn(
            "REVIEW_ONLY_RESULT_REQUIRES_EXPLICIT_CODEX_MODIFICATION_DISPOSITION",
            findings,
        )

    def test_project_change_outside_routed_allowlist_is_rejected(self) -> None:
        policy, manifest, binding = self._routed_project_fixture()
        manifest["changed_paths"].append("src/aggie_analytics/model.py")
        findings: list[str] = []
        _validate_change_binding(policy, manifest, binding, findings)
        self.assertTrue(
            any(
                item.startswith("PROJECT_WORK_ROUTED_PATH_OUTSIDE_ALLOWLIST:")
                for item in findings
            )
        )
        self.assertIn("PROJECT_WORK_ROUTED_ALLOWLIST_NOT_EXACT_CHANGE_SET", findings)

    def test_missing_provider_evidence_identity_is_rejected(self) -> None:
        policy, manifest, binding = self._routed_project_fixture()
        binding["routed_project_adoption"]["provider_result_sha256"] = ""
        findings: list[str] = []
        _validate_change_binding(policy, manifest, binding, findings)
        self.assertIn(
            "PROJECT_WORK_EVIDENCE_IDENTITY_INVALID:provider_result_sha256", findings
        )

    def test_exact_user_reserved_project_change_is_admitted_without_pipeline_promotion(
        self,
    ) -> None:
        policy, manifest, binding = self._routed_project_fixture()
        instruction_text = (
            "I WANT YOU TO JUST COMPLETLY MOVE AWAY FROM BUILDING THIS PIPELINE "
            "AND ONLY WORK ON THE BATTERERD AGGIE SYNDROME PROJECT"
        )
        binding.pop("routed_project_adoption")
        binding["disposition"] = "USER_EXPLICITLY_RESERVED_FOR_CODEX"
        binding["user_explicit_waiver"] = {
            "instruction_text": instruction_text,
            "instruction_sha256": hashlib.sha256(
                instruction_text.encode("utf-8")
            ).hexdigest(),
            "scope": "ALL_BATTERED_AGGIE_SYNDROME_PROJECT_WORK",
            "duration": "UNTIL_USER_REVOKES_OR_SUPERSEDES",
            "accepted_risk": "The assistive pipeline is not used for this work unit.",
            "work_unit_id": manifest["work_unit_id"],
        }
        decision_payload = dict(binding)
        decision_payload.pop("decision_sha256")
        binding["decision_sha256"] = hashlib.sha256(
            json.dumps(decision_payload, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        manifest["pre_routing_decision_sha256"] = binding["decision_sha256"]
        findings: list[str] = []
        _validate_change_binding(policy, manifest, binding, findings)
        self.assertEqual([], findings)
        self.assertEqual("NOT_OPERATIONAL", policy["runtime_state"])

    def test_user_reservation_requires_exact_instruction_hash_and_paths(self) -> None:
        policy, manifest, binding = self._routed_project_fixture()
        binding.pop("routed_project_adoption")
        binding["disposition"] = "USER_EXPLICITLY_RESERVED_FOR_CODEX"
        binding["user_explicit_waiver"] = {
            "instruction_text": "only BAS work",
            "instruction_sha256": "0" * 64,
            "scope": "ALL_BATTERED_AGGIE_SYNDROME_PROJECT_WORK",
            "duration": "UNTIL_USER_REVOKES_OR_SUPERSEDES",
            "accepted_risk": "The assistive pipeline is not used for this work unit.",
            "work_unit_id": manifest["work_unit_id"],
        }
        decision_payload = dict(binding)
        decision_payload.pop("decision_sha256")
        binding["decision_sha256"] = hashlib.sha256(
            json.dumps(decision_payload, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        manifest["pre_routing_decision_sha256"] = binding["decision_sha256"]
        manifest["changed_paths"].append("src/aggie_analytics/model.py")
        findings: list[str] = []
        _validate_change_binding(policy, manifest, binding, findings)
        self.assertIn("USER_RESERVATION_INSTRUCTION_HASH_MISMATCH", findings)
        self.assertTrue(
            any(
                item.startswith("USER_RESERVED_PROJECT_WORK_PATH_OUTSIDE_ALLOWLIST:")
                for item in findings
            )
        )


if __name__ == "__main__":
    unittest.main()
