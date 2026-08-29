from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_1996_season_index import (  # noqa: E402  # pylint: disable=import-error
    AuthorityViolation,
    GATE_RELATIVE,
    compute_code_identity,
    compute_gate_identity,
    validate_artifact,
)
from aggie_analytics.data.season_index_offline_reconstruction import (  # noqa: E402
    reconstruct_season_index,
)

DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = bool(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")) and DATA_ROOT.exists()


def _mutated(gate: dict, **changes):
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


@unittest.skipUnless(LAKE_READY, "external Cycle #18 data root is not mounted")
class Official1996SeasonIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gate = json.loads((REPO_ROOT / GATE_RELATIVE).read_text(encoding="utf-8-sig"))

    def test_reconstruction_is_read_only_and_reproduces_the_committed_gate(self) -> None:
        rebuilt = reconstruct_season_index(
            1996, repo_root=REPO_ROOT, data_root=DATA_ROOT, gate=self.gate
        )
        self.assertEqual(rebuilt["gate"], self.gate)

    def test_gate_reconstructs(self) -> None:
        result = validate_artifact(repo_root=REPO_ROOT, data_root=DATA_ROOT, require_rebuild=True)
        self.assertEqual(result["result"], "PASS")
        self.assertGreaterEqual(int(result["scheduled_games"] or 0), 1)

    def test_history_href_removed_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "history href proof"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, history_href_proof=""),
                require_rebuild=False,
            )

    def test_stale_code_identity_fails(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "stale code identity"):
            validate_artifact(
                repo_root=REPO_ROOT,
                data_root=DATA_ROOT,
                gate=_mutated(self.gate, validator_code_identity="0" * 64),
                require_rebuild=False,
            )
        self.assertEqual(self.gate["validator_code_identity"], compute_code_identity(REPO_ROOT))


if __name__ == "__main__":
    unittest.main()
