from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jira.tools import import_bat_live


class JiraOperationalStatusPolicyTests(unittest.TestCase):
    def _write_record(self, root: Path, *, target_status: str = "In Progress") -> None:
        payload = {
            "local_id": "POST-SUBTASK-202",
            "workflow_state": "BLOCKED",
            "jira_operational_status_policy": {
                "schema_version": 1,
                "mode": "EXPLICIT_ACTIVE_EXECUTION",
                "target_status": target_status,
                "rationale": "Verified campaign work is active while its shared dependency remains incomplete.",
                "evidence_refs": ["BAT-560", "BAT-561"],
                "clear_when": "Clear when verified active execution ends.",
            },
        }
        (root / "record.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_explicit_active_policy_preserves_live_status_without_changing_logical_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_record(root)
            with patch.object(import_bat_live, "RECORDS_ROOT", root):
                policies = import_bat_live.load_operational_status_policies()

        row = {"Local Issue ID": "POST-SUBTASK-202", "Status": "To Do"}
        actual = import_bat_live.expected_operational_status(
            row,
            policies,
            {"local_issue_ids": [], "jira_operational_override": {}},
        )
        self.assertEqual(actual, "In Progress")
        self.assertEqual(policies["POST-SUBTASK-202"]["mode"], "EXPLICIT_ACTIVE_EXECUTION")

    def test_unlisted_issue_retains_derived_import_status(self) -> None:
        row = {"Local Issue ID": "POST-SUBTASK-205", "Status": "To Do"}
        actual = import_bat_live.expected_operational_status(
            row,
            {},
            {"local_issue_ids": [], "jira_operational_override": {}},
        )
        self.assertEqual(actual, "To Do")

    def test_embedded_live_mirror_is_not_operational_policy_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "record.json").write_text(
                json.dumps(
                    {
                        "local_id": "POST-SUBTASK-205",
                        "workflow_state": "BLOCKED",
                        "operational_jira": {"status_raw": "In Progress"},
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(import_bat_live, "RECORDS_ROOT", root):
                policies = import_bat_live.load_operational_status_policies()

        row = {"Local Issue ID": "POST-SUBTASK-205", "Status": "To Do"}
        self.assertEqual(
            import_bat_live.expected_operational_status(
                row,
                policies,
                {"local_issue_ids": [], "jira_operational_override": {}},
            ),
            "To Do",
        )

    def test_policy_cannot_force_done_or_other_unvalidated_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._write_record(root, target_status="Done")
            with patch.object(import_bat_live, "RECORDS_ROOT", root):
                with self.assertRaisesRegex(RuntimeError, "may only declare In Progress"):
                    import_bat_live.load_operational_status_policies()


if __name__ == "__main__":
    unittest.main()
