from __future__ import annotations

import unittest
from pathlib import Path

from aggie_analytics.cycle28.decommission import validate_retired_assistive_decommission
from tools.validate_retired_assistive_pipeline_decommission import validate


ROOT = Path(__file__).resolve().parents[1]


class RetiredAssistiveDecommissionTests(unittest.TestCase):
    def test_live_repo_has_no_active_fort_knox_authority(self) -> None:
        findings = validate_retired_assistive_decommission(ROOT)
        self.assertEqual([], findings)
        self.assertEqual([], validate(ROOT))

    def test_agents_md_does_not_require_fort_knox_reading(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("Before any material work, read", text)
        self.assertIn("RETIRED_HISTORICAL_ONLY", text)

    def test_ci_does_not_run_old_interlock(self) -> None:
        text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertNotIn("validate_unified_assistive_plane.py", text)
        self.assertNotIn("validate_codex_usage_interlock.py", text)
        self.assertIn("validate_retired_assistive_pipeline_decommission.py", text)


if __name__ == "__main__":
    unittest.main()
