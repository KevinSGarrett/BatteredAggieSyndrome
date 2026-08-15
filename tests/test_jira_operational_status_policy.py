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

    def test_reconciliation_returns_stale_active_issue_to_canonical_to_do(self) -> None:
        class FakeClient:
            def __init__(self) -> None:
                self.posts: list[tuple[str, dict[str, object]]] = []

            def get(self, path: str) -> dict[str, object]:
                self.assert_transition_path = path
                return {"transitions": [{"id": "11", "to": {"name": "To Do"}}]}

            def post(self, path: str, payload: dict[str, object]) -> None:
                self.posts.append((path, payload))

        rows = [
            {"Local Issue ID": "POST-SUBTASK-202", "Status": "To Do"},
            {"Local Issue ID": "POST-SUBTASK-001", "Status": "Done"},
        ]
        key_map = {"POST-SUBTASK-202": "BAT-561", "POST-SUBTASK-001": "BAT-1"}
        issues = [
            {
                "key": "BAT-561",
                "fields": {"status": {"name": "In Progress"}, "customfield_local": "POST-SUBTASK-202"},
            },
            {
                "key": "BAT-1",
                "fields": {"status": {"name": "Done"}, "customfield_local": "POST-SUBTASK-001"},
            },
        ]
        client = FakeClient()
        ledger: dict[str, object] = {}
        with tempfile.TemporaryDirectory() as temp:
            ledger_path = Path(temp) / "ledger.json"
            with (
                patch.object(import_bat_live, "LEDGER_PATH", ledger_path),
                patch.object(import_bat_live, "load_completion_policy", return_value={"local_issue_ids": []}),
                patch.object(import_bat_live, "map_existing_issues", return_value=(key_map, issues)),
            ):
                import_bat_live.reconcile_non_done_operational_statuses(
                    client,
                    ledger,
                    rows,
                    key_map,
                    {},
                    "customfield_local",
                )

        self.assertEqual(
            client.posts,
            [("/rest/api/3/issue/BAT-561/transitions", {"transition": {"id": "11"}})],
        )
        self.assertEqual(ledger["operational_status_reconciliation"]["changed_count"], 1)

    def test_reconciliation_is_idempotent_when_status_already_matches(self) -> None:
        class FakeClient:
            def get(self, path: str) -> dict[str, object]:
                raise AssertionError(f"No transition lookup expected: {path}")

            def post(self, path: str, payload: dict[str, object]) -> None:
                raise AssertionError(f"No transition expected: {path} {payload}")

        rows = [{"Local Issue ID": "POST-SUBTASK-202", "Status": "To Do"}]
        key_map = {"POST-SUBTASK-202": "BAT-561"}
        issues = [
            {
                "key": "BAT-561",
                "fields": {"status": {"name": "To Do"}, "customfield_local": "POST-SUBTASK-202"},
            }
        ]
        ledger: dict[str, object] = {}
        with tempfile.TemporaryDirectory() as temp:
            with (
                patch.object(import_bat_live, "LEDGER_PATH", Path(temp) / "ledger.json"),
                patch.object(import_bat_live, "load_completion_policy", return_value={"local_issue_ids": []}),
                patch.object(import_bat_live, "map_existing_issues", return_value=(key_map, issues)),
            ):
                import_bat_live.reconcile_non_done_operational_statuses(
                    FakeClient(), ledger, rows, key_map, {}, "customfield_local"
                )

        self.assertEqual(ledger["operational_status_reconciliation"]["changed_count"], 0)

    def test_reconciliation_fails_closed_when_target_transition_is_unavailable(self) -> None:
        class FakeClient:
            def get(self, path: str) -> dict[str, object]:
                return {"transitions": [{"id": "22", "to": {"name": "In Review"}}]}

            def post(self, path: str, payload: dict[str, object]) -> None:
                raise AssertionError(f"Unexpected transition: {path} {payload}")

        rows = [{"Local Issue ID": "POST-SUBTASK-202", "Status": "To Do"}]
        key_map = {"POST-SUBTASK-202": "BAT-561"}
        issues = [
            {
                "key": "BAT-561",
                "fields": {"status": {"name": "In Progress"}, "customfield_local": "POST-SUBTASK-202"},
            }
        ]
        with (
            patch.object(import_bat_live, "load_completion_policy", return_value={"local_issue_ids": []}),
            patch.object(import_bat_live, "map_existing_issues", return_value=(key_map, issues)),
        ):
            with self.assertRaisesRegex(RuntimeError, "No transition to To Do is available for BAT-561"):
                import_bat_live.reconcile_non_done_operational_statuses(
                    FakeClient(), {}, rows, key_map, {}, "customfield_local"
                )


if __name__ == "__main__":
    unittest.main()
