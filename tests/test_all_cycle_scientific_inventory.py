"""All-cycle inventory completeness and classification tests."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from tools.validate_affected_successors import validate as validate_successors  # noqa: E402
from tools.validate_all_cycle_scientific_inventory import validate  # noqa: E402

ALL_CYCLES = REPO_ROOT / "artifacts" / "scientific_integrity" / "all_cycles"


class AllCycleInventoryTests(unittest.TestCase):
    def test_inventory_validator_passes(self) -> None:
        self.assertEqual([], validate(REPO_ROOT))

    def test_twenty_five_cycle_audits_exist(self) -> None:
        for cycle in range(1, 26):
            path = ALL_CYCLES / f"CYCLE_{cycle:02d}_SCIENTIFIC_AUDIT.json"
            self.assertTrue(path.is_file(), msg=str(path))
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["cycle_number"], cycle)
            self.assertNotEqual(payload["trust_classification"], "SEMANTICALLY_AUDITED")

    def test_trust_gate_does_not_claim_recovery(self) -> None:
        gate = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_TRUST_RECOVERY_GATE.json").read_text(encoding="utf-8")
        )
        self.assertFalse(gate["scientific_trust_recovered"])
        self.assertFalse(gate["cycle_25_5_complete"])
        self.assertEqual(gate["week1_forecast_credibility"], "UNTRUSTED_SHADOW")
        self.assertEqual(gate["t24h_state"], "OPEN")
        self.assertEqual(gate["t90m_state"], "OPEN")

    def test_affected_successors_propagate(self) -> None:
        self.assertEqual([], validate_successors(REPO_ROOT))

    def test_findings_evidence_is_posix_relative(self) -> None:
        drive = re.compile(r"^[A-Za-z]:[\\/]")
        payload = json.loads(
            (ALL_CYCLES / "ALL_CYCLE_FINDINGS.json").read_text(encoding="utf-8")
        )
        for finding in payload["findings"]:
            for item in finding.get("evidence") or []:
                self.assertFalse(drive.match(str(item)), msg=item)
                self.assertNotIn("\\", str(item))


if __name__ == "__main__":
    unittest.main()
