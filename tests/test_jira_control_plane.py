from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.validate_jira_control_plane import validate


class JiraControlPlaneTests(unittest.TestCase):
    def test_second_pass_date_is_dependency_free_utc(self):
        source = (ROOT / "jira/tools/second_pass_hardening.py").read_text(encoding="utf-8")
        self.assertIn("datetime.now(timezone.utc)", source)
        self.assertNotIn("ZoneInfo(", source)

    def test_local_mirror_strict_validation(self):
        self.assertEqual(validate(ROOT), [])

    def test_verified_live_target_metadata(self):
        self.assertEqual(validate(ROOT, require_live=True), [])
        profile = json.loads((ROOT / "jira/project/JIRA_TARGET_PROFILE.yaml").read_text(encoding="utf-8"))
        self.assertEqual(profile["project_key"], "BAT")
        self.assertEqual(profile["profile_status"], "LIVE_TARGET_CONFIGURED_AND_VERIFIED")
        self.assertEqual(profile["live_counts"]["issues"], 463)


if __name__ == "__main__":
    unittest.main()
