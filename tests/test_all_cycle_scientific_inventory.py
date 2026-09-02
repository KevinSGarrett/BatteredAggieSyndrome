"""All-cycle inventory completeness and classification tests."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from tools.build_all_cycle_scientific_inventory import (  # noqa: E402
    cycle_commit_index,
    first_add_commit,
    verify_cycle_shas,
)
from tools.validate_affected_successors import validate as validate_successors  # noqa: E402
from tools.validate_all_cycle_scientific_inventory import validate  # noqa: E402

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

    def test_unmapped_artifacts_record_git_first_add_reason(self) -> None:
        inventory = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_ARTIFACT_INVENTORY.json").read_text(encoding="utf-8")
        )
        allowed_unmapped = {
            "GIT_FIRST_ADD_NOT_FOUND",
            "GIT_FIRST_ADD_AMBIGUOUS_CYCLE",
            "GIT_FIRST_ADD_BEFORE_CYCLE_1",
            "GIT_FIRST_ADD_AFTER_CYCLE_25",
            "GIT_FIRST_ADD_OUTSIDE_DECLARED_RANGES",
        }
        git_mapped = 0
        for item in inventory["artifacts"]:
            if item.get("mapping_note") == "GIT_FIRST_ADD":
                git_mapped += 1
                self.assertIsInstance(item["originating_cycle"], int)
                continue
            if item.get("originating_cycle") != "UNMAPPED":
                continue
            self.assertIn(item.get("mapping_note"), allowed_unmapped)
            self.assertNotEqual(item.get("mapping_note"), "UNMAPPED_NO_CYCLE_TOKEN")
        self.assertGreaterEqual(git_mapped, 1)

    def test_first_add_commit_uses_earliest_add(self) -> None:
        relative = (
            "artifacts/jira_evidence/POST-TASK-ALL-CYCLE-SCIENTIFIC-CLAIM-REGISTRY-001.json"
        )
        completed = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%H", "--", relative],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        commits = (completed.stdout or "").split()
        self.assertGreaterEqual(len(commits), 1)
        self.assertEqual(first_add_commit(relative), commits[-1])
        if len(commits) > 1:
            self.assertNotEqual(first_add_commit(relative), commits[0])

    def test_cycle_one_index_includes_declared_start_only(self) -> None:
        rows = verify_cycle_shas()
        index = cycle_commit_index(rows)
        cycle_one_start = str(rows[0]["starting_sha"])
        self.assertIn(1, index[cycle_one_start])
        self.assertEqual(index[cycle_one_start], [1])

    def test_pre_cycle_one_artifacts_are_not_guessed_as_cycle_one(self) -> None:
        inventory = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_ARTIFACT_INVENTORY.json").read_text(encoding="utf-8")
        )
        before = [
            item
            for item in inventory["artifacts"]
            if item.get("mapping_note") == "GIT_FIRST_ADD_BEFORE_CYCLE_1"
        ]
        self.assertGreaterEqual(len(before), 1)
        for item in before:
            self.assertEqual(item["originating_cycle"], "UNMAPPED")

    def test_post_cycle_25_jira_evidence_is_not_token_mapped_to_cycle_five(self) -> None:
        inventory = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_ARTIFACT_INVENTORY.json").read_text(encoding="utf-8")
        )
        rows = [
            item
            for item in inventory["artifacts"]
            if item.get("path")
            == "artifacts/jira_evidence/POST-TASK-ALL-CYCLE-SCIENTIFIC-CLAIM-REGISTRY-001.json"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["originating_cycle"], "UNMAPPED")
        self.assertEqual(rows[0]["mapping_note"], "GIT_FIRST_ADD_AFTER_CYCLE_25")

    def test_completeness_rule_does_not_treat_validator_pass_as_complete(self) -> None:
        inventory = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_ARTIFACT_INVENTORY.json").read_text(encoding="utf-8")
        )
        gate = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_TRUST_RECOVERY_GATE.json").read_text(encoding="utf-8")
        )
        rule = str(inventory.get("completeness_rule") or "").lower()
        self.assertGreater(inventory["unmapped_authority_count"], 0)
        self.assertIn("not that mapping is complete", rule)
        self.assertEqual(gate["inventory_completeness"], "INCOMPLETE_UNMAPPED_AUTHORITY")
        self.assertFalse(gate["scientific_trust_recovered"])

    def test_findings_evidence_is_posix_relative(self) -> None:
        drive = re.compile(r"^[A-Za-z]:[\\/]")
        payload = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_FINDINGS.json").read_text(encoding="utf-8")
        )
        for finding in payload["findings"]:
            for item in finding.get("evidence") or []:
                self.assertFalse(drive.match(str(item)), msg=item)
                self.assertNotIn("\\", str(item))


if __name__ == "__main__":
    unittest.main()
