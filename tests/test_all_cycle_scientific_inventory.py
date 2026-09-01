"""All-cycle inventory completeness and classification tests."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from tools.validate_affected_successors import validate as validate_successors  # noqa: E402
from tools.validate_all_cycle_scientific_inventory import validate  # noqa: E402
from tools.validate_codex_scientific_review import validate_payload  # noqa: E402
from tools.validate_pr_review_finding_ledger import validate as validate_ledger  # noqa: E402

ALL_CYCLES = REPO_ROOT / "artifacts" / "scientific_integrity" / "all_cycles"


class AllCycleInventoryTests(unittest.TestCase):
    def test_inventory_validator_passes(self) -> None:
        self.assertEqual([], validate(REPO_ROOT))

    def test_twenty_five_cycle_audits_exist(self) -> None:
        for cycle in range(1, 26):
            path = ALL_CYCLES / f"CYCLE_{cycle:02d}_SCIENTIFIC_AUDIT.json"
            self.assertTrue(path.is_file(), msg=str(path))
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["cycle_number"], cycle)
            self.assertNotEqual(payload["trust_classification"], "SEMANTICALLY_AUDITED")

    def test_trust_gate_does_not_claim_recovery(self) -> None:
        gate = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_TRUST_RECOVERY_GATE.json").read_text(encoding="utf-8")
        )
        self.assertFalse(gate["scientific_trust_recovered"])
        self.assertFalse(gate["cycle_25_5_complete"])
        self.assertEqual(gate["week1_forecast_credibility"], "UNTRUSTED_SHADOW")
        self.assertEqual(gate["t24h_state"], "OPEN")
        self.assertEqual(gate["t90m_state"], "OPEN")

    def test_affected_successors_propagate(self) -> None:
        self.assertEqual([], validate_successors(REPO_ROOT))

    def test_codex_review_rejects_empty_and_unresolved_p0(self) -> None:
        self.assertIn("CODEX_REVIEW_EMPTY", validate_payload({}))
        payload = {
            "pr_number": 1,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "reviewed_merge_sha": "c" * 40,
            "changed_file_inventory": ["src/x.py"],
            "changed_file_digest": "",
            "review_rule_identity": "cycle25_5",
            "model": "gpt-5.4",
            "reasoning_effort": "high",
            "findings_p0": ["p0"],
            "findings_p1": [],
            "findings_p2": [],
            "scientific_invariants_checked": [
                "pit_known_at",
                "target_game_exclusion",
                "current_opponent_binding",
                "game_grain_pair_coherence",
                "probability_margin_distribution_coherence",
                "immutable_forecasts",
                "protected_exposure",
                "report_artifact_agreement",
                "producer_validator_independence",
            ],
            "critical_files_not_reviewed": [],
            "limitations": ["no human review"],
            "verdict": "PASS",
        }
        findings = validate_payload(payload, expected_files=["src/x.py"])
        self.assertTrue(
            any("UNRESOLVED_P0_P1" in item or "DIGEST" in item for item in findings)
        )

    def test_cursor_cannot_self_approve_p0_false_positive(self) -> None:
        findings = validate_ledger(
            {
                "findings": [
                    {
                        "reviewer": "Cursor",
                        "reviewed_sha": "c1c310da6bcae25641977fe409e3034b8c08010a",
                        "finding": "example",
                        "severity": "P0",
                        "affected_files": ["src/x.py"],
                        "implementation_response": "disagree",
                        "disposition": "FALSE_POSITIVE_PROVEN",
                        "evidence": "none",
                        "regression_test": "none",
                        "follow_up_review_identity": "none",
                        "final_authority": "Cursor",
                    }
                ]
            }
        )
        self.assertTrue(any("SELF_APPROVAL" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
