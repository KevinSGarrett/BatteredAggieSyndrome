from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.audit_control_plane import audit
from tools.generate_instruction_manifest import generate
from tools.select_next_work import select


class AutonomousControlToolTests(unittest.TestCase):
    def test_activation_blocker_resolutions_are_honest_and_hashed(self):
        evidence = json.loads((ROOT / "artifacts/jira_evidence/POST-SUBTASK-001.json").read_text(encoding="utf-8"))
        outputs = {row["path"]: row for row in evidence["outputs"]}
        hydration_path = "artifacts/implementation_preflight/hydration_binding_supersession.json"
        data_root_path = "artifacts/implementation_preflight/data_root_activation.json"

        hydration = json.loads((ROOT / hydration_path).read_text(encoding="utf-8"))
        self.assertEqual(hydration["decision"]["status"], "FORMALLY_SUPERSEDED_FOR_POST_W25_EXECUTION")
        self.assertFalse(hydration["historical_fact"]["missing_bytes_reconstructed"])
        self.assertFalse(hydration["historical_fact"]["historical_pair_binding_claimed"])
        self.assertTrue(hydration["decision"]["negative_evidence_retained"])

        data_root = json.loads((ROOT / data_root_path).read_text(encoding="utf-8"))
        self.assertTrue(data_root["outside_repository"])
        self.assertTrue(data_root["local_env_ignored"])
        self.assertEqual(data_root["activation_state"]["status"], "CONFIGURED_EMPTY_EXTERNAL_ROOT")
        self.assertFalse(data_root["activation_state"]["source_data_materialized"])

        for relative in (hydration_path, data_root_path):
            payload = (ROOT / relative).read_bytes()
            self.assertEqual(outputs[relative]["bytes"], len(payload))
            self.assertEqual(outputs[relative]["sha256"], hashlib.sha256(payload).hexdigest())

    def test_control_plane_audit_is_redacted_and_bound(self):
        result = audit(ROOT)
        self.assertEqual(result["repo_root"], str(ROOT.resolve()))
        self.assertFalse(result["redaction"]["secret_values_included"])
        self.assertTrue(set(result["environment_aliases"].values()).issubset({"PRESENT_REDACTED", "ABSENT"}))
        encoded = json.dumps(result)
        self.assertNotIn("Authorization: Basic", encoded)
        self.assertNotIn("Authorization: Bearer", encoded)

    def test_instruction_hashes_are_current(self):
        self.assertEqual(generate(ROOT, check=True), [])

    def test_selector_returns_only_dependency_ready_atomic_work(self):
        items = select(ROOT)
        self.assertEqual(items[0]["jira_key"], "BAT-479")
        self.assertEqual(items[0]["selection_class"], "RESUME_IN_PROGRESS")
        for item in items:
            self.assertTrue(item["local_id"].startswith("POST-SUBTASK-"))
            self.assertIn(item["priority"], {"P0", "P1", "P2", "P3"})

    def test_selector_resumes_valid_in_progress_before_new_ready_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = root / "jira/records/issues/subtasks"
            records.mkdir(parents=True)
            fixtures = [
                {
                    "local_id": "POST-SUBTASK-001",
                    "jira_key": "BAT-1",
                    "execution_mode": "ATOMIC_EXECUTION",
                    "workflow_state": "IN_PROGRESS",
                    "ready": False,
                    "priority": "P0",
                    "critical_path": True,
                    "dependencies": [],
                    "operational_jira": {"status_raw": "In Progress"},
                },
                {
                    "local_id": "POST-SUBTASK-002",
                    "jira_key": "BAT-2",
                    "execution_mode": "ATOMIC_EXECUTION",
                    "workflow_state": "READY",
                    "ready": True,
                    "priority": "P0",
                    "critical_path": True,
                    "dependencies": [],
                    "operational_jira": {"status_raw": "To Do"},
                },
            ]
            for index, fixture in enumerate(fixtures):
                (records / f"fixture-{index}.json").write_text(json.dumps(fixture), encoding="utf-8")
            items = select(root)
            self.assertEqual([item["jira_key"] for item in items], ["BAT-1", "BAT-2"])
            self.assertEqual(items[0]["selection_class"], "RESUME_IN_PROGRESS")


if __name__ == "__main__":
    unittest.main()
