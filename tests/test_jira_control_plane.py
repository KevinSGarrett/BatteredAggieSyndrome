from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.validate_jira_control_plane import ALLOWED_AUXILIARY_LOGICAL_STATES, validate


class JiraControlPlaneTests(unittest.TestCase):
    def test_second_pass_date_is_dependency_free_utc(self):
        source = (ROOT / "jira/tools/second_pass_hardening.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("datetime.now(timezone.utc)", source)
        self.assertNotIn("ZoneInfo(", source)

    def test_local_mirror_strict_validation(self):
        self.assertEqual(validate(ROOT), [])

    def test_auxiliary_logical_states_use_bounded_vocabulary(self):
        registry = json.loads(
            (ROOT / "jira/reconciliation/BAT_AUXILIARY_ISSUE_REGISTRY.json").read_text(
                encoding="utf-8"
            )
        )
        invalid = [
            f"{item.get('jira_key')}:{item.get('logical_state')}"
            for item in registry["issues"]
            if item.get("logical_state") not in ALLOWED_AUXILIARY_LOGICAL_STATES
        ]
        self.assertEqual([], invalid)
        self.assertIn("DONE", ALLOWED_AUXILIARY_LOGICAL_STATES)
        self.assertIn("REVIEW", ALLOWED_AUXILIARY_LOGICAL_STATES)
        self.assertNotIn("COMPLETE", ALLOWED_AUXILIARY_LOGICAL_STATES)
        self.assertNotIn("IN_REVIEW", ALLOWED_AUXILIARY_LOGICAL_STATES)

    def test_verified_live_target_metadata(self):
        self.assertEqual(validate(ROOT, require_live=True), [])
        profile = json.loads(
            (ROOT / "jira/project/JIRA_TARGET_PROFILE.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(profile["project_key"], "BAT")
        self.assertEqual(
            profile["profile_status"], "LIVE_TARGET_CONFIGURED_AND_VERIFIED"
        )
        canonical_count = len(
            list((ROOT / "jira" / "records" / "issues").rglob("*.json"))
        )
        auxiliary = json.loads(
            (
                ROOT / "jira" / "reconciliation" / "BAT_AUXILIARY_ISSUE_REGISTRY.json"
            ).read_text(encoding="utf-8")
        )
        pending = profile.get("local_sync", {}).get("pending_issue_ids", [])
        self.assertEqual(
            profile["live_counts"]["issues"] + len(pending),
            canonical_count + len(auxiliary["issues"]),
        )
        self.assertEqual(pending, [])
        self.assertEqual(profile["local_sync"]["state"], "LIVE_SYNCHRONIZED")
        self.assertTrue(profile["local_sync"]["last_successful_sync"])


if __name__ == "__main__":
    unittest.main()
