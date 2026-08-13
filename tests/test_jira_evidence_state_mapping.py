from __future__ import annotations

import unittest

from jira.tools.import_bat_live import custom_value, jira_custom_scalar


class JiraEvidenceStateMappingTests(unittest.TestCase):
    def test_maps_detailed_active_checkpoint_to_partial_select_option(self) -> None:
        canonical = (
            "ACTIVE_EMPIRICAL_CHECKPOINT_2020_RECONCILED_2018_2019_2021_DISCOVERY_RUNNING"
        )
        self.assertEqual("PARTIAL", jira_custom_scalar("Evidence State", canonical))
        self.assertEqual({"value": "PARTIAL"}, custom_value("Evidence State", canonical))

    def test_preserves_each_declared_jira_evidence_state(self) -> None:
        for value in ("PLANNED", "PARTIAL", "BLOCKED", "VERIFIED"):
            with self.subTest(value=value):
                self.assertEqual(value, jira_custom_scalar("Evidence State", value))

    def test_unknown_evidence_state_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "JIRA_EVIDENCE_STATE_MAPPING_REQUIRED"):
            jira_custom_scalar("Evidence State", "UNREVIEWED_DYNAMIC_STATE")

    def test_other_custom_fields_remain_exact(self) -> None:
        self.assertEqual("IN_PROGRESS", jira_custom_scalar("Logical Workflow State", "IN_PROGRESS"))


if __name__ == "__main__":
    unittest.main()
