"""CONTROL-07 trusted-control protocol: FAIL/BLOCKED and bootstrap boundary."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from aggie_analytics.governance.trusted_control_change_protocol import (
    CONTROL_SURFACES,
    bind_current_tree,
    evaluate_changed_control_surfaces,
    evaluate_missing_sha_and_failed_rerun,
    evaluate_review_payload_acceptance,
    evaluate_unreviewed_critical,
    load_protocol,
)

REPO = Path(__file__).resolve().parents[1]
PROTOCOL = (
    REPO
    / "artifacts"
    / "scientific_integrity"
    / "cycle27"
    / "CYCLE27_TRUSTED_CONTROL_CHANGE_PROTOCOL.json"
)
HEAD = "3fcc710438a75f15abc23392c6136ac077f25e7b"
INVARIANTS = [
    "pit_known_at",
    "target_game_exclusion",
    "current_opponent_binding",
    "game_grain_pair_coherence",
    "probability_margin_distribution_coherence",
    "immutable_forecasts",
    "protected_exposure",
    "report_artifact_agreement",
    "producer_validator_independence",
]


def _digest(files: list[str]) -> str:
    encoded = json.dumps(sorted(files), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class Cycle27TrustedControlProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = load_protocol(PROTOCOL)
        files = ["src/x.py"]
        self.payload = {
            "pr_number": 678,
            "base_sha": "55e12a5aad3a7e843204fcba619c3cb3d3d6194d",
            "head_sha": HEAD,
            "reviewed_merge_sha": "f37bffa1b4897bad822393131e94e10d3bea1720",
            "changed_file_inventory": files,
            "changed_file_digest": _digest(files),
            "review_rule_identity": self.protocol["bindings"]["rules"][
                "review_rule_identity"
            ],
            "model": "gpt-5.3-codex",
            "reasoning_effort": "medium",
            "findings_p0": [],
            "findings_p1": [],
            "findings_p2": [],
            "scientific_invariants_checked": INVARIANTS,
            "critical_files_not_reviewed": [],
            "limitations": [],
            "verdict": "PASS",
        }

    def test_protocol_is_preparation_not_approval(self) -> None:
        self.assertTrue(self.protocol["this_pack_is_not_approval"])
        self.assertEqual(self.protocol["bootstrap_status"], "PREPARATION_NOT_APPROVED")
        self.assertFalse(self.protocol["merge_authorized"])
        self.assertTrue(
            self.protocol[
                "hosted_workflow_must_continue_fetching_checker_from_protected_base"
            ]
        )
        bindings = bind_current_tree(REPO)
        self.assertEqual(
            self.protocol["bindings"]["prompt"]["sha256"],
            bindings["prompt"]["sha256"],
        )
        self.assertEqual(
            self.protocol["bindings"]["schema"]["sha256"],
            bindings["schema"]["sha256"],
        )
        self.assertEqual(
            self.protocol["bindings"]["rules"]["sha256"],
            bindings["rules"]["sha256"],
        )
        self.assertEqual(
            self.protocol["bindings"]["checker"]["proposed_successor_sha256"],
            bindings["checker"]["proposed_successor_sha256"],
        )
        self.assertEqual(bindings["model"]["trusted_value"], "gpt-5.3-codex")
        self.assertTrue(bindings["model"]["workflow_currently_supplies_trusted_model"])
        self.assertEqual(bindings["effort"]["trusted_value"], "medium")
        self.assertTrue(bindings["effort"]["workflow_currently_supplies_trusted_effort"])

    def test_schema_valid_fail_json_fails_acceptance(self) -> None:
        payload = dict(self.payload)
        payload["verdict"] = "FAIL"
        payload["findings_p0"] = ["p0"]
        result = evaluate_review_payload_acceptance(payload, protocol=self.protocol)
        self.assertTrue(result["schema_valid"])
        self.assertFalse(result["accepted"])
        self.assertIn("CODEX_REVIEW_UNSUCCESSFUL_VERDICT:FAIL", result["findings"])

    def test_schema_valid_blocked_json_fails_acceptance(self) -> None:
        payload = dict(self.payload)
        payload["verdict"] = "BLOCKED"
        result = evaluate_review_payload_acceptance(payload, protocol=self.protocol)
        self.assertTrue(result["schema_valid"])
        self.assertFalse(result["accepted"])
        self.assertIn("CODEX_REVIEW_UNSUCCESSFUL_VERDICT:BLOCKED", result["findings"])
        payload["verdict"] = "BLOCKED_INSUFFICIENT_EVIDENCE"
        blocked = evaluate_review_payload_acceptance(payload, protocol=self.protocol)
        self.assertFalse(blocked["accepted"])

    def test_empty_and_malformed_fail(self) -> None:
        empty = evaluate_review_payload_acceptance({}, protocol=self.protocol)
        self.assertFalse(empty["accepted"])
        self.assertFalse(empty["schema_valid"])
        self.assertIn("CODEX_REVIEW_EMPTY", empty["findings"])

    def test_missing_sha_fails(self) -> None:
        result = evaluate_missing_sha_and_failed_rerun(
            head_sha=HEAD,
            checks=[
                {"name": "codex-review", "conclusion": "success"},
                {"name": "codecov/patch", "head_sha": HEAD, "conclusion": "success"},
            ],
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(
            any(
                "REQUIRED_CHECK_MISSING_HEAD_SHA" in item for item in result["findings"]
            )
        )

    def test_newer_failed_rerun_beats_older_success(self) -> None:
        result = evaluate_missing_sha_and_failed_rerun(
            head_sha=HEAD,
            checks=[
                {
                    "name": "codex-review",
                    "head_sha": HEAD,
                    "conclusion": "success",
                    "completed_at": "2026-09-04T15:00:00Z",
                    "id": 1,
                },
                {
                    "name": "codex-review",
                    "head_sha": HEAD,
                    "conclusion": "failure",
                    "completed_at": "2026-09-04T15:22:00Z",
                    "id": 2,
                },
                {
                    "name": "codecov/patch",
                    "head_sha": HEAD,
                    "conclusion": "success",
                    "completed_at": "2026-09-04T15:23:00Z",
                    "id": 3,
                },
            ],
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(
            any("REQUIRED_CHECK_NOT_SUCCESS" in item for item in result["findings"])
        )

    def test_changed_rules_or_prompt_without_approval_fails(self) -> None:
        result = evaluate_changed_control_surfaces(
            protocol=self.protocol,
            changed_files=[".github/CODE_REVIEW_RULES.md", "src/x.py"],
        )
        self.assertFalse(result["accepted"])
        self.assertIn("TRUSTED_CONTROL_RULES_OR_PROMPT_CHANGED", result["findings"])
        prompt = evaluate_changed_control_surfaces(
            protocol=self.protocol,
            changed_files=[".github/codex/prompts/scientific-review.md"],
        )
        self.assertFalse(prompt["accepted"])

    def test_unreviewed_critical_fails(self) -> None:
        payload = dict(self.payload)
        payload["critical_files_not_reviewed"] = ["src/critical.py"]
        result = evaluate_unreviewed_critical(payload)
        self.assertFalse(result["accepted"])
        review = evaluate_review_payload_acceptance(payload, protocol=self.protocol)
        self.assertFalse(review["accepted"])
        self.assertIn(
            "CODEX_REVIEW_PASS_WITH_UNREVIEWED_CRITICAL_FILES", review["findings"]
        )

    def test_bootstrap_boundary_without_approval_fails(self) -> None:
        result = evaluate_changed_control_surfaces(
            protocol=self.protocol,
            changed_files=list(CONTROL_SURFACES),
        )
        self.assertFalse(result["accepted"])
        self.assertIn(
            "TRUSTED_CONTROL_BOOTSTRAP_BOUNDARY_WITHOUT_APPROVAL",
            result["findings"],
        )
        pass_payload = evaluate_review_payload_acceptance(
            self.payload, protocol=self.protocol
        )
        self.assertFalse(pass_payload["accepted"])
        self.assertIn(
            "TRUSTED_CONTROL_BOOTSTRAP_BOUNDARY_WITHOUT_APPROVAL",
            pass_payload["findings"],
        )
        approved = evaluate_changed_control_surfaces(
            protocol=self.protocol,
            changed_files=["tools/validate_codex_scientific_review.py"],
            approval_receipt={
                "bootstrap_approved": True,
                "author": "CYCLE27_CURSOR_AGENT",
                "independent_reviewer": "independent-github-reviewer",
            },
        )
        self.assertTrue(approved["accepted"])


if __name__ == "__main__":
    unittest.main()
