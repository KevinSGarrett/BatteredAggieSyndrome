"""Operator-hold receipt identity and fail-closed mutation tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aggie_analytics.governance.scientific_trust_recovery_hold import (
    STARTING_SHA,
    compute_identity,
    validate_hold,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class ScientificTrustRecoveryHoldTests(unittest.TestCase):
    def test_receipt_identity_binds(self) -> None:
        path = (
            REPO_ROOT
            / "artifacts"
            / "scientific_integrity"
            / "OPERATOR_HOLD_RECEIPT.json"
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["audited_starting_sha"], STARTING_SHA)
        self.assertEqual(payload["status"], "ACTIVE")
        self.assertFalse(payload["cycle25_hold_incident"]["hold_was_implemented"])
        self.assertEqual(
            set(payload["cycle25_hold_incident"]["merged_prs_despite_intended_hold"]),
            {665, 666, 667},
        )
        self.assertEqual(
            payload["receipt_identity"],
            compute_identity(payload, "receipt_identity"),
        )

    def test_active_hold_passes_on_current_tree(self) -> None:
        findings = validate_hold(REPO_ROOT)
        self.assertEqual([], findings)

    def test_done_transition_fails_closed(self) -> None:
        findings = validate_hold(REPO_ROOT, proposed_done_keys=["BAT-688"])
        self.assertIn("HOLD_PROPOSED_DONE_WHILE_ACTIVE:BAT-688", findings)

    def test_scientific_merge_fails_closed(self) -> None:
        findings = validate_hold(
            REPO_ROOT, proposed_merges=["scientific:BAT-690-national-foundation"]
        )
        self.assertTrue(
            any(item.startswith("HOLD_SCIENTIFIC_MERGE_WHILE_ACTIVE") for item in findings)
        )

    def test_parent_progress_comment_fails_closed(self) -> None:
        findings = validate_hold(
            REPO_ROOT,
            proposed_parent_comment="CYCLE_25_5_BAT-523_PARENT_PROGRESS draft",
        )
        self.assertIn("HOLD_PROHIBITED_BAT_523_PARENT_PROGRESS_COMMENT", findings)

    def test_completion_claim_fails_closed(self) -> None:
        findings = validate_hold(
            REPO_ROOT, proposed_completion_claim="Cycle #25.5 complete"
        )
        self.assertIn("HOLD_COMPLETION_CLAIM_WHILE_ACTIVE", findings)

    def test_tampered_receipt_identity_fails(self) -> None:
        original = (
            REPO_ROOT
            / "artifacts"
            / "scientific_integrity"
            / "OPERATOR_HOLD_RECEIPT.json"
        )
        payload = json.loads(original.read_text(encoding="utf-8"))
        payload["status"] = "RELEASED"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "artifacts" / "scientific_integrity"
            target.mkdir(parents=True)
            (target / "OPERATOR_HOLD_RECEIPT.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            contract_src = (
                REPO_ROOT / "configs" / "scientific_trust_recovery_hold_contract.json"
            )
            dest_contract = root / "configs"
            dest_contract.mkdir()
            dest_contract.joinpath(
                "scientific_trust_recovery_hold_contract.json"
            ).write_bytes(contract_src.read_bytes())
            registry_src = (
                REPO_ROOT
                / "jira"
                / "reconciliation"
                / "BAT_AUXILIARY_ISSUE_REGISTRY.json"
            )
            dest_reg = root / "jira" / "reconciliation"
            dest_reg.mkdir(parents=True)
            dest_reg.joinpath("BAT_AUXILIARY_ISSUE_REGISTRY.json").write_bytes(
                registry_src.read_bytes()
            )
            findings = validate_hold(root)
            self.assertTrue(
                any(
                    item in findings
                    for item in (
                        "HOLD_RECEIPT_IDENTITY_MISMATCH",
                        "HOLD_STATUS_NOT_ACTIVE:RELEASED",
                    )
                )
            )


if __name__ == "__main__":
    unittest.main()
