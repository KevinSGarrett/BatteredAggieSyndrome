from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.validate_codex_usage_interlock import ROOT, validate


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
        self.assertTrue(any(item.startswith("RUNTIME_PROOF_MISSING:") for item in report["findings"]))

    def test_policy_forbids_billing_motive_inference(self) -> None:
        policy = json.loads(
            (ROOT / "instructions/policies/assistive_execution_interlock.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIs(policy["epistemic_boundary"]["billing_motive_claim_allowed"], False)


if __name__ == "__main__":
    unittest.main()
