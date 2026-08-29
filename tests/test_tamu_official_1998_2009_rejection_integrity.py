from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_1998_2009_rejection_integrity import (  # noqa: E402  # pylint: disable=import-error
    ADMITTED_ROW_GAP_URLS,
    AuthorityViolation,
    GATE_RELATIVE,
    compute_identity,
    reconstruct_objects,
    validate_artifact,
)

DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and DATA_ROOT.exists()


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_identity(tampered, "gate_identity")
    return tampered


@unittest.skipUnless(LAKE_READY, "external Cycle #18 data root is not mounted")
class RejectionIntegrityGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Reconstruction only. Materialization stays in the explicit build command
        # so a test run can never rewrite the tracked gate it is checking.
        reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        cls.gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))

    def test_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(int(self.gate["complete_rejection_count"]), 40)
        self.assertEqual(int(self.gate["active_rejection_count"]), 17)
        self.assertEqual(int(self.gate["superseded_rejection_count"]), 23)

    def test_protected_lane_open_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "does not match independent reconstruction"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
            )

    def test_gap_url_relabel_fails(self) -> None:
        bad = _mutated(self.gate, admitted_row_gap_urls=[ADMITTED_ROW_GAP_URLS[0]])
        with self.assertRaisesRegex(AuthorityViolation, "does not match independent reconstruction"):
            validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=bad)


if __name__ == "__main__":
    unittest.main()
