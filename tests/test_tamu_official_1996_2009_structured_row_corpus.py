from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for name, module in list(sys.modules.items()):
    if name == "aggie_analytics" or name.startswith("aggie_analytics."):
        origin = getattr(module, "__file__", "") or ""
        if origin and str(REPO_ROOT / "src").lower() not in origin.lower():
            del sys.modules[name]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_1996_2009_structured_row_corpus import (  # noqa: E402  # pylint: disable=import-error
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
class Corpus19962009Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Reconstruction only. Materialization stays in the explicit build command
        # so a test run can never rewrite the tracked gate it is checking.
        reconstruct_objects(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        cls.gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))

    def test_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(int(self.gate["counts"]["seasons"]), 14)
        self.assertEqual(int(self.gate["counts"]["games"]), 150)
        self.assertGreaterEqual(int(self.gate["counts"]["serialized_rows_total"]), 61454)

    def test_open_protected_lane_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "does not match independent reconstruction"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
            )


if __name__ == "__main__":
    unittest.main()
