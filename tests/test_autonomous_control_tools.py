from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.audit_control_plane import audit
from tools.generate_instruction_manifest import generate
from tools.select_next_work import select


class AutonomousControlToolTests(unittest.TestCase):
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
        for item in items:
            self.assertTrue(item["local_id"].startswith("POST-SUBTASK-"))
            self.assertIn(item["priority"], {"P0", "P1", "P2", "P3"})


if __name__ == "__main__":
    unittest.main()
