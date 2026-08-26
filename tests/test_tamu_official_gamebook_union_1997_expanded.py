from __future__ import annotations

import json
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

from aggie_analytics.data.tamu_official_gamebook_union_1997_expanded import (  # noqa: E402  # pylint: disable=import-error
    AuthorityViolation,
    GATE_RELATIVE,
    compute_identity,
    materialize_union,
    validate_artifact,
)

DATA_ROOT = Path(r"C:\\BatteredAggieSyndrome.data")


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_identity(tampered, "gate_identity")
    return tampered


class Official1997ExpandedUnionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        materialize_union(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        cls.gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))

    def test_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        self.assertEqual(result["result"], "PASS")
        self.assertGreaterEqual(int(self.gate["counts"]["rejected_urls_complete"]), 17)

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "does not match independent reconstruction"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
            )


if __name__ == "__main__":
    unittest.main()
