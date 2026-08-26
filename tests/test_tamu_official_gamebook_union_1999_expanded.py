from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_1999_expanded import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    OFFICIAL_1999_ADMITTED_EXPECTED,
    OFFICIAL_1999_REJECTED_EXPECTED,
    compute_code_identity,
    compute_gate_identity,
    lake_is_ready,
    materialize_union,
    validate_artifact,
 )  # pylint: disable=import-error

DATA_ROOT = Path(r"C:\\BatteredAggieSyndrome.data")
LAKE_READY = lake_is_ready(DATA_ROOT, REPO_ROOT)


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Compact1999UnionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("1999-expanded union gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))
        if self.gate.get("validator_code_identity") != compute_code_identity(REPO_ROOT):
            self.skipTest("1999-expanded union gate needs rebuild for current code identity")

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
                require_rebuild=False,
            )

    def test_forged_1999_counts_fail(self) -> None:
        counts = json.loads(json.dumps(self.gate["counts"]))
        counts["official_1999_admitted"] = OFFICIAL_1999_ADMITTED_EXPECTED + 1
        with self.assertRaisesRegex(AuthorityViolation, "admission count"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, counts=counts),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-633 inputs are not mounted")
class Official1999UnionReconstructionTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        materialize_union(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        result = validate_artifact(
            repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True
        )
        self.assertEqual(result["result"], "PASS")
        gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        self.assertEqual(int(gate["counts"]["official_1999_admitted"]), OFFICIAL_1999_ADMITTED_EXPECTED)
        self.assertEqual(int(gate["counts"]["official_1999_rejected"]), OFFICIAL_1999_REJECTED_EXPECTED)
        self.assertTrue(gate["domain_semantics_by_game"])


if __name__ == "__main__":
    unittest.main()
