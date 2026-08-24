from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_1998_structured_domains import (  # noqa: E402  # pylint: disable=import-error
    AuthorityViolation,
    GATE_RELATIVE,
    compute_code_identity,
    compute_gate_identity,
    lake_is_ready,
    materialize,
    validate_artifact,
)

DATA_ROOT = Path(
    os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
)
LAKE_READY = lake_is_ready(DATA_ROOT)


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Compact1998StructuredDomainGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("1998 structured-domain gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))
        if self.gate.get("validator_code_identity") != compute_code_identity(REPO_ROOT):
            self.skipTest("1998 structured-domain gate needs rebuild for current code identity")

    def test_protected_lane_opened_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "protected lane"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, protected_lane="OPEN"),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-636 1998 captures are not mounted")
class Official1998StructuredReconstructionTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        materialize(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        result = validate_artifact(
            repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True
        )
        self.assertEqual(result["result"], "PASS")
        self.assertGreaterEqual(int(result["parsed_games"] or 0), 1)


if __name__ == "__main__":
    unittest.main()
