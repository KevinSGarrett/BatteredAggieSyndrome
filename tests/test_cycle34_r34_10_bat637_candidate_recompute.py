"""R34-10: the BAT-637 candidate recompute pipeline runs, produces a full
(not truncated) candidate identity, and never touches the guarded source
module. Skipped if the real tracked gate637 file / lake ledger aren't
present."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

_MODULE_PATH = REPO_ROOT / "tools" / "cycle34_r34_10_bat637_candidate_recompute.py"
_spec = importlib.util.spec_from_file_location("cycle34_r34_10_bat637_candidate_recompute", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)  # type: ignore[union-attr]

GATE637_PATH = REPO_ROOT / "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json"
LEDGER_PATH = (
    Path(r"C:\BatteredAggieSyndrome.data")
    / "features/tamu_official_1998_2009_rejection_integrity/sha256"
    / "1b79f1bac9883e93fca9a6154493cf646059986fdc8bff4491ddbc8715631574"
    / "rejection_ledger.json"
)
DATA_READY = GATE637_PATH.is_file() and LEDGER_PATH.is_file()


@unittest.skipUnless(DATA_READY, "real gate637/lake ledger not mounted in this environment")
class Bat637CandidateRecomputeTests(unittest.TestCase):
    def test_pipeline_produces_a_full_candidate_identity(self) -> None:
        result = _module.run()
        self.assertIsNotNone(result.get("candidate_gate"))
        gate_identity = result["candidate_payload_summary"]["gate_identity"]
        union_identity = result["candidate_payload_summary"]["union_identity"]
        # Full identity digests, not truncated prefixes (this repo's
        # stable_hash/compute_identity helpers produce hex digests of
        # varying length depending on algorithm; the point of this
        # assertion is "full digest," not a specific length).
        self.assertGreaterEqual(len(gate_identity), 64)
        self.assertRegex(gate_identity, r"^[0-9a-f]+$")
        self.assertGreaterEqual(len(union_identity), 64)
        self.assertRegex(union_identity, r"^[0-9a-f]+$")
        self.assertFalse(result["pin_matches_live"])

    def test_guarded_source_module_is_never_imported(self) -> None:
        # The recompute module's own source (read above, imports only
        # ncaa_contest_reconciliation and artifact_binding) never imports the
        # guarded tamu_official_gamebook_union_1998_rejection_complete module
        # at all -- checked here by asserting it is absent from sys.modules
        # after running, without shelling out to git (kept minimal).
        _module.run()
        self.assertNotIn(
            "aggie_analytics.data.tamu_official_gamebook_union_1998_rejection_complete",
            sys.modules,
            "the guarded module must never be imported by this recompute script",
        )


if __name__ == "__main__":
    unittest.main()
