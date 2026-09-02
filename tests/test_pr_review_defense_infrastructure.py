"""Review-infrastructure validators for Codex scientific review and finding ledger."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.validate_codex_scientific_review import validate_payload  # noqa: E402
from tools.validate_pr_review_finding_ledger import validate as validate_ledger  # noqa: E402


class PrReviewDefenseInfrastructureTests(unittest.TestCase):
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

    def test_inventory_builder_does_not_write_finding_ledger(self) -> None:
        text = (
            REPO_ROOT / "tools" / "build_all_cycle_scientific_inventory.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("PR_REVIEW_FINDING_LEDGER.json", text)


if __name__ == "__main__":
    unittest.main()
