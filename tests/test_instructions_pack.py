from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.validate_autonomous_controls import validate


class InstructionPackTests(unittest.TestCase):
    def test_strict_instruction_control_validation(self):
        self.assertEqual(validate(ROOT, strict=True), [])

    def test_prompt_compliance_has_56_unique_sections(self):
        policy = json.loads((ROOT / "instructions/policies/prompt_compliance.json").read_text(encoding="utf-8"))
        sections = [entry["section"] for entry in policy["entries"]]
        self.assertEqual(policy["section_count"], 56)
        self.assertEqual(len(sections), 56)
        self.assertEqual(len(set(sections)), 56)

    def test_no_wave_26_is_machine_enforced(self):
        manifest = json.loads((ROOT / "instructions/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["final_numbered_wave"], "W25")
        self.assertIs(manifest["wave_26_allowed"], False)


if __name__ == "__main__":
    unittest.main()
