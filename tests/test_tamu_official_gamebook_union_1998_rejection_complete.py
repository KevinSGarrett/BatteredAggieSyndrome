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

from aggie_analytics.data.tamu_official_gamebook_union_1998_rejection_complete import (  # noqa: E402  # pylint: disable=import-error
    GATE_RELATIVE,
    AuthorityViolation,
    compute_identity,
    materialize_union,
    validate_artifact,
)

DATA_ROOT = Path(r"C:\\BatteredAggieSyndrome.data")
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and DATA_ROOT.exists()


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_identity(tampered, "gate_identity")
    return tampered


@unittest.skipUnless(LAKE_READY, "external Cycle #18 data root is not mounted")
class RejectionCompleteUnionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        materialize_union(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        cls.gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))

    def test_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(int(self.gate["counts"]["unmatched_rejected"]), 17)

    def test_protected_lane_open_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "does not match independent reconstruction"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
            )


if __name__ == "__main__":
    unittest.main()
