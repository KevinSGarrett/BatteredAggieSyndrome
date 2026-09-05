"""All-cycle inventory completeness and classification tests."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from tools.build_all_cycle_scientific_inventory import (  # noqa: E402
    cycle_commit_index,
    cycle_for_path,
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
            (ALL_CYCLES / "ALL_CYCLE_TRUST_RECOVERY_GATE.json").read_text(
                encoding="utf-8"
            )
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
            (ALL_CYCLES / "ALL_CYCLE_ARTIFACT_INVENTORY.json").read_text(
                encoding="utf-8"
            )
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
        relative = "artifacts/jira_evidence/POST-TASK-ALL-CYCLE-SCIENTIFIC-CLAIM-REGISTRY-001.json"
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
            (ALL_CYCLES / "ALL_CYCLE_ARTIFACT_INVENTORY.json").read_text(
                encoding="utf-8"
            )
        )
        before = [
            item
            for item in inventory["artifacts"]
            if item.get("mapping_note") == "GIT_FIRST_ADD_BEFORE_CYCLE_1"
        ]
        self.assertGreaterEqual(len(before), 1)
        for item in before:
            self.assertEqual(item["originating_cycle"], "UNMAPPED")

    def test_unique_git_first_add_overrides_path_token(self) -> None:
        inventory = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_ARTIFACT_INVENTORY.json").read_text(
                encoding="utf-8"
            )
        )
        rows = [
            item
            for item in inventory["artifacts"]
            if item.get("path") == "artifacts/pit/protected_replay_dry_run.json"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["mapping_note"], "GIT_FIRST_ADD")
        self.assertIsInstance(rows[0]["originating_cycle"], int)
        self.assertNotEqual(rows[0]["originating_cycle"], 17)

    def test_ambiguous_git_first_add_is_not_token_mapped(self) -> None:
        inventory = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_ARTIFACT_INVENTORY.json").read_text(
                encoding="utf-8"
            )
        )
        path_token = [
            item
            for item in inventory["artifacts"]
            if item.get("mapping_note") == "PATH_TOKEN"
        ]
        self.assertEqual(path_token, [])

    def test_path_token_heuristic_is_not_origin_authority(self) -> None:
        rows = verify_cycle_shas()
        self.assertEqual(
            cycle_for_path("artifacts/pit/protected_replay_dry_run.json", rows),
            17,
        )

    def test_post_cycle_25_jira_evidence_is_not_token_mapped_to_cycle_five(
        self,
    ) -> None:
        inventory = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_ARTIFACT_INVENTORY.json").read_text(
                encoding="utf-8"
            )
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
            (ALL_CYCLES / "ALL_CYCLE_ARTIFACT_INVENTORY.json").read_text(
                encoding="utf-8"
            )
        )
        gate = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_TRUST_RECOVERY_GATE.json").read_text(
                encoding="utf-8"
            )
        )
        rule = str(inventory.get("completeness_rule") or "").lower()
        self.assertGreater(inventory["unmapped_authority_count"], 0)
        self.assertIn("not that mapping is complete", rule)
        self.assertEqual(
            gate["inventory_completeness"], "INCOMPLETE_UNMAPPED_AUTHORITY"
        )
        self.assertFalse(gate["scientific_trust_recovered"])

    def test_census_includes_governance_protected_split_registry(self) -> None:
        inventory = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_ARTIFACT_INVENTORY.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("governance", inventory.get("census_roots") or [])
        rows = [
            item
            for item in inventory["artifacts"]
            if item.get("path") == "governance/PROTECTED_SPLIT_REGISTRY.csv"
        ]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["authority_bearing"])

    def test_census_includes_tokenless_files_inside_declared_roots(self) -> None:
        inventory = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_ARTIFACT_INVENTORY.json").read_text(
                encoding="utf-8"
            )
        )
        by_path = {item["path"]: item for item in inventory["artifacts"]}
        self.assertIn("configs/judging_rule_seal.json", by_path)
        self.assertIn("governance/BAS_EVALUATION_PROTOCOL.csv", by_path)
        self.assertIn("schemas/models/joint_score_distribution.json", by_path)
        producer = by_path[
            "src/aggie_analytics/data/week1_2026_forecast_input_binding_successor.py"
        ]
        validator = by_path[
            "src/aggie_analytics/validation/protected_split_authority.py"
        ]
        self.assertEqual(producer["scientific_claim_or_role"], "SCIENTIFIC_PRODUCER")
        self.assertEqual(validator["scientific_claim_or_role"], "SCIENTIFIC_VALIDATOR")
        rule = str(inventory.get("completeness_rule") or "").lower()
        self.assertIn("token or filename filters are not inclusion authority", rule)

    def test_findings_evidence_is_posix_relative(self) -> None:
        drive = re.compile(r"^[A-Za-z]:[\\/]")
        payload = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_FINDINGS.json").read_text(encoding="utf-8")
        )
        for finding in payload["findings"]:
            for item in finding.get("evidence") or []:
                self.assertFalse(drive.match(str(item)), msg=item)
                self.assertNotIn("\\", str(item))

    def test_pass_three_category_search_cannot_be_complete(self) -> None:
        matrix = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_THREE_PASS_AUDIT_MATRIX.json").read_text(
                encoding="utf-8"
            )
        )
        for item in matrix["cycles"]:
            self.assertNotEqual(
                item["passes"]["pass_three"],
                "COMPLETE",
                msg=f"cycle {item['cycle_number']}",
            )
            self.assertEqual(item["passes"]["pass_three"], "PARTIAL")
        audit = json.loads(
            (ALL_CYCLES / "CYCLE_01_SCIENTIFIC_AUDIT.json").read_text(encoding="utf-8")
        )
        self.assertEqual(audit["pass_three_adversarial"]["status"], "PARTIAL")
        self.assertIn(
            "category search",
            str(audit["pass_three_adversarial"]["limitation"]).lower(),
        )
        # Tampered COMPLETE under category-search limitation must fail validation.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            src = ALL_CYCLES
            dest = tmp_root / "artifacts" / "scientific_integrity" / "all_cycles"
            dest.mkdir(parents=True)
            for path in src.glob("*.json"):
                (dest / path.name).write_text(
                    path.read_text(encoding="utf-8"), encoding="utf-8"
                )
            tampered = json.loads(
                (dest / "CYCLE_01_SCIENTIFIC_AUDIT.json").read_text(encoding="utf-8")
            )
            tampered["pass_three_adversarial"]["status"] = "COMPLETE"
            (dest / "CYCLE_01_SCIENTIFIC_AUDIT.json").write_text(
                json.dumps(tampered), encoding="utf-8"
            )
            matrix_t = json.loads(
                (dest / "ALL_CYCLE_THREE_PASS_AUDIT_MATRIX.json").read_text(
                    encoding="utf-8"
                )
            )
            for item in matrix_t["cycles"]:
                if item["cycle_number"] == 1:
                    item["passes"]["pass_three"] = "COMPLETE"
            (dest / "ALL_CYCLE_THREE_PASS_AUDIT_MATRIX.json").write_text(
                json.dumps(matrix_t), encoding="utf-8"
            )
            findings = validate(tmp_root)
            joined = " ".join(findings)
            self.assertIn("AUDIT_PASS_THREE_FALSE_COMPLETE:01", joined)
            self.assertIn("PASS_THREE_CATEGORY_SEARCH_CANNOT_BE_COMPLETE:1", joined)

    def test_pass_two_does_not_stamp_every_cycle_missing_raw_payloads(self) -> None:
        missing_flags = []
        for cycle in range(1, 26):
            audit = json.loads(
                (ALL_CYCLES / f"CYCLE_{cycle:02d}_SCIENTIFIC_AUDIT.json").read_text(
                    encoding="utf-8"
                )
            )
            p2 = audit["pass_two_semantic"]
            missing_flags.append(p2["missing_raw_payloads"] is True)
            if p2["missing_raw_payloads"] is True:
                self.assertTrue(p2.get("missing_declared_payloads"))
        self.assertFalse(all(missing_flags))
        cycle_one = json.loads(
            (ALL_CYCLES / "CYCLE_01_SCIENTIFIC_AUDIT.json").read_text(encoding="utf-8")
        )
        self.assertFalse(cycle_one["pass_two_semantic"]["missing_raw_payloads"])
        self.assertEqual(cycle_one["pass_two_semantic"]["status"], "NOT_AUDITED_YET")
        self.assertNotEqual(cycle_one["trust_classification"], "SEMANTICALLY_AUDITED")
        matrix = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_THREE_PASS_AUDIT_MATRIX.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(matrix["cycles"][0]["passes"]["pass_two"], "NOT_AUDITED_YET")
        gate = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_TRUST_RECOVERY_GATE.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(gate["scientific_trust_recovered"])
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            dest = tmp_root / "artifacts" / "scientific_integrity" / "all_cycles"
            dest.mkdir(parents=True)
            for path in ALL_CYCLES.glob("*.json"):
                (dest / path.name).write_text(
                    path.read_text(encoding="utf-8"), encoding="utf-8"
                )
            for cycle in range(1, 26):
                audit_path = dest / f"CYCLE_{cycle:02d}_SCIENTIFIC_AUDIT.json"
                audit = json.loads(audit_path.read_text(encoding="utf-8"))
                audit["pass_two_semantic"]["missing_raw_payloads"] = True
                audit["pass_two_semantic"]["missing_declared_payloads"] = []
                audit_path.write_text(json.dumps(audit), encoding="utf-8")
            findings = validate(tmp_root)
            joined = " ".join(findings)
            self.assertIn("UNIFORM_MISSING_RAW_PAYLOADS_STAMP", joined)
            self.assertIn("MISSING_RAW_PAYLOADS_WITHOUT_DECLARED_GAPS:01", joined)


if __name__ == "__main__":
    unittest.main()
