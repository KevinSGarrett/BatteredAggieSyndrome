from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RetiredInterlockHistoricalTests(unittest.TestCase):
    def test_historical_policy_remains_not_operational_and_is_not_an_active_gate(self) -> None:
        policy = json.loads(
            (
                ROOT / "instructions/policies/assistive_execution_interlock.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(policy["runtime_state"], "NOT_OPERATIONAL")
        self.assertIs(policy["empty_queue_authorizes_fallback"], False)
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        start = (ROOT / "instructions/START_HERE.md").read_text(encoding="utf-8")
        self.assertNotIn("Before any material work, read", agents)
        self.assertNotIn("always, before every material work unit", start.lower())
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertNotIn("validate_codex_usage_interlock.py", ci)


if __name__ == "__main__":
    unittest.main()
