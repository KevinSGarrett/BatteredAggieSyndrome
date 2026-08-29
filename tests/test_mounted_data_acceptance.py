from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_mounted_data_acceptance, validate_mounted_acceptance_gate


ROOT = Path(__file__).resolve().parents[1]


class MountedAcceptanceTests(unittest.TestCase):
    def test_missing_data_root_fails(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(run_mounted_data_acceptance.AcceptanceFailure, "AGGIE_ANALYTICS_DATA_ROOT_REQUIRED"):
                run_mounted_data_acceptance.resolve_data_root(None)

    def test_missing_required_raw_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = run_mounted_data_acceptance.RawRequirement(
                source_gate="artifacts/data_lake/example_gate.json",
                raw_relative_path="raw/example/sha256_missing.html",
                raw_sha256="0" * 64,
            )
            with self.assertRaisesRegex(run_mounted_data_acceptance.AcceptanceFailure, "REQUIRED_RAW_MISSING"):
                run_mounted_data_acceptance.verify_required_raw_manifest(Path(tmp), [missing])

    def test_altered_raw_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            raw_relative = Path("raw/example/sha256_payload.html")
            raw_path = data_root / raw_relative
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(b"authoritative-bytes")
            requirement = run_mounted_data_acceptance.RawRequirement(
                source_gate="artifacts/data_lake/example_gate.json",
                raw_relative_path=raw_relative.as_posix(),
                raw_sha256=hashlib.sha256(b"tampered").hexdigest(),
            )
            with self.assertRaisesRegex(run_mounted_data_acceptance.AcceptanceFailure, "REQUIRED_RAW_SHA_MISMATCH"):
                run_mounted_data_acceptance.verify_required_raw_manifest(data_root, [requirement])

    def test_skipped_critical_test_fails_policy(self) -> None:
        contract = {"skip_budget": {"critical_suite_allowed_skips": 0}}
        result = {"executed": 10, "failed": 0, "errored": 0, "skipped": 1}
        findings = run_mounted_data_acceptance.evaluate_run_policy(result, contract)
        self.assertIn("CRITICAL_SKIP_BUDGET_EXCEEDED:1>0", findings)

    def test_zero_executed_tests_fails_policy(self) -> None:
        contract = {"skip_budget": {"critical_suite_allowed_skips": 0}}
        result = {"executed": 0, "failed": 0, "errored": 0, "skipped": 0}
        findings = run_mounted_data_acceptance.evaluate_run_policy(result, contract)
        self.assertIn("ZERO_EXECUTED_TESTS", findings)

    def test_forged_success_after_rehash_fails_gate_validation(self) -> None:
        contract = json.loads((ROOT / "configs/mounted_acceptance_contract.json").read_text(encoding="utf-8"))
        gate = {
            "schema_version": "aggie.validation.mounted_acceptance_gate.v1",
            "artifact_type": "MOUNTED_ACCEPTANCE_GATE",
            "classification": "CYCLE18_19_CRITICAL_MOUNTED_ACCEPTANCE",
            "result": "PASS",
            "contract_id": contract["contract_id"],
            "repo_head_sha": "a" * 40,
            "code_identity": "b" * 64,
            "critical_suite": list(contract["critical_suite"]),
            "test_inventory": ["tests.example.Case.test_alpha"],
            "test_inventory_identity": "c" * 64,
            "skip_budget": dict(contract["skip_budget"]),
            "expected_full_suite_skips": list(contract["expected_full_suite_skips"]),
            "network_error_marker": contract["network_error_marker"],
            "counts": {"executed": 1, "passed": 1, "failed": 0, "errored": 0, "skipped": 0},
            "failure_tests": [],
            "error_tests": [],
            "skipped_tests": [],
            "required_raw_manifest": [],
            "required_raw_manifest_identity": "d" * 64,
            "data_root_manifest_identities": {},
            "acceptance_result_identity": "e" * 64,
            "acceptance_result_relative_path": "validation/mounted_acceptance/sha256/fake/acceptance_result.json",
        }
        gate["gate_identity"] = validate_mounted_acceptance_gate.compute_gate_identity(gate)
        self.assertEqual([], validate_mounted_acceptance_gate.validate_gate_document(gate, contract))

        forged = dict(gate)
        forged["counts"] = {"executed": 1, "passed": 0, "failed": 1, "errored": 0, "skipped": 0}
        forged["gate_identity"] = validate_mounted_acceptance_gate.compute_gate_identity(forged)
        findings = validate_mounted_acceptance_gate.validate_gate_document(forged, contract)
        self.assertIn("MOUNTED_ACCEPTANCE_FAILURES_PRESENT", findings)


class MaterializationCommitTests(unittest.TestCase):
    """BAT-673: the gate provenance commit is precommitted, never sampled from the checkout."""

    def contract(self) -> dict:
        return json.loads(
            (ROOT / "configs/mounted_acceptance_contract.json").read_text(encoding="utf-8-sig")
        )

    def test_head_sampling_helper_is_gone(self) -> None:
        self.assertFalse(hasattr(run_mounted_data_acceptance, "git_head_sha"))
        source = (ROOT / "tools/run_mounted_data_acceptance.py").read_text(encoding="utf-8")
        self.assertNotIn("rev-parse", source)

    def test_pinned_commit_is_returned_and_exists_in_history(self) -> None:
        contract = self.contract()
        resolved = run_mounted_data_acceptance.materialization_commit(ROOT, contract)
        self.assertEqual(contract["materialization_commit"], resolved)

    def test_pinned_commit_does_not_track_the_working_checkout(self) -> None:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        resolved = run_mounted_data_acceptance.materialization_commit(ROOT, self.contract())
        committed = json.loads(
            (ROOT / "artifacts/validation/mounted_acceptance_gate.json").read_text(encoding="utf-8-sig")
        )
        # The reproduced provenance follows the contract, not whatever is checked out, so the
        # committed gate stays reproducible no matter how far HEAD advances past it.
        self.assertEqual(committed["repo_head_sha"], resolved)
        if head != resolved:
            self.assertNotEqual(head, resolved)

    def test_missing_pinned_commit_fails_closed(self) -> None:
        contract = self.contract()
        del contract["materialization_commit"]
        with self.assertRaisesRegex(
            run_mounted_data_acceptance.AcceptanceFailure, "must predeclare materialization_commit"
        ):
            run_mounted_data_acceptance.materialization_commit(ROOT, contract)

    def test_malformed_pinned_commit_fails_closed(self) -> None:
        for bad in ("", "not-a-sha", "A" * 40, "7303fd0c", "0" * 41):
            contract = self.contract()
            contract["materialization_commit"] = bad
            with self.subTest(value=bad):
                with self.assertRaisesRegex(
                    run_mounted_data_acceptance.AcceptanceFailure,
                    "must predeclare materialization_commit",
                ):
                    run_mounted_data_acceptance.materialization_commit(ROOT, contract)

    def test_stripped_authority_label_fails_closed(self) -> None:
        contract = self.contract()
        contract["materialization_commit_authority"] = "SAMPLED_FROM_CHECKOUT"
        with self.assertRaisesRegex(
            run_mounted_data_acceptance.AcceptanceFailure, "authority label missing or altered"
        ):
            run_mounted_data_acceptance.materialization_commit(ROOT, contract)

    def test_commit_absent_from_history_fails_closed(self) -> None:
        contract = self.contract()
        contract["materialization_commit"] = "0" * 40
        with self.assertRaisesRegex(
            run_mounted_data_acceptance.AcceptanceFailure, "MATERIALIZATION_COMMIT_NOT_IN_HISTORY"
        ):
            run_mounted_data_acceptance.materialization_commit(ROOT, contract)


if __name__ == "__main__":
    unittest.main()
