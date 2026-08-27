from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_1998_season_index import (  # noqa: E402  # pylint: disable=import-error
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
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and lake_is_ready(DATA_ROOT, REPO_ROOT)


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class Compact1998GateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = REPO_ROOT / GATE_RELATIVE
        if not path.is_file():
            self.skipTest("1998 gate not materialized yet")
        self.gate = json.loads(path.read_text(encoding="utf-8-sig"))
        if self.gate.get("validator_code_identity") != compute_code_identity(REPO_ROOT):
            self.skipTest("1998 gate needs rebuild for current code identity")

    def test_history_href_removed_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "history href proof"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, history_href_proof=""),
                require_rebuild=False,
            )

    def test_invented_url_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "guessed"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(
                    self.gate,
                    official_index_url="https://files.12thman.com/history/football/years/2001.html",
                ),
                require_rebuild=False,
            )


@unittest.skipUnless(LAKE_READY, "external BAT-634 1998 capture is not mounted")
class Official1998CaptureTests(unittest.TestCase):
    def test_committed_gate_reconstructs(self) -> None:
        materialize(repo_root=REPO_ROOT, data_root=DATA_ROOT)
        result = validate_artifact(
            repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True
        )
        self.assertEqual(result["result"], "PASS")
        self.assertGreaterEqual(int(result["scheduled_games"] or 0), 1)


if __name__ == "__main__":
    unittest.main()
