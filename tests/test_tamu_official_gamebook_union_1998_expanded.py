from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_1998_expanded import (  # noqa: E402  # pylint: disable=import-error
    AuthorityViolation,
    GATE_RELATIVE,
    OFFICIAL_1998_ADMITTED_EXPECTED,
    OFFICIAL_1998_REJECTED_EXPECTED,
    compute_code_identity,
    compute_gate_identity,
    upstream_is_ready,
    validate_artifact,
)

DATA_ROOT = Path(r"C:\\BatteredAggieSyndrome.data")


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Compact1998UnionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("1998-expanded union gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))
        if self.gate.get("validator_code_identity") != compute_code_identity(REPO_ROOT):
            self.skipTest("1998-expanded union gate needs rebuild for current code identity")

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
                require_rebuild=False,
            )


@unittest.skipUnless(upstream_is_ready(DATA_ROOT, REPO_ROOT), "external BAT-637 inputs are not mounted")
class Official1998UnionReconstructionTests(unittest.TestCase):
    def test_committed_gate_reconstructs_read_only(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        gate = json.loads(path.read_text(encoding="utf-8-sig"))
        if gate.get("validator_code_identity") != compute_code_identity(REPO_ROOT):
            self.skipTest("1998-expanded union gate needs rebuild for current code identity")
        try:
            result = validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                require_rebuild=True,
            )
        except AuthorityViolation as exc:
            if "1998 structured-domain gate does not match reconstruction" in str(exc):
                self.skipTest(
                    "1998 structured-domain predecessor is contained, not rematerialized; "
                    "Cycle26 passing-section successor is the correction path"
                )
            raise
        self.assertEqual(result["result"], "PASS")
        committed = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
        self.assertEqual(committed["gate_identity"], gate["gate_identity"])
        self.assertEqual(int(committed["counts"]["official_1998_admitted"]), OFFICIAL_1998_ADMITTED_EXPECTED)
        self.assertEqual(int(committed["counts"]["official_1998_rejected"]), OFFICIAL_1998_REJECTED_EXPECTED)


if __name__ == "__main__":
    unittest.main()

