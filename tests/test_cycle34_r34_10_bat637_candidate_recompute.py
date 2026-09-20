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
        # Bug found by this round's full MOUNTED suite run (not visible when
        # this test file was run in isolation): a bare "is the guarded module
        # present in sys.modules" check is unreliable in a full pytest
        # process, because *other* test files (which legitimately test the
        # guarded module itself, e.g. test_tamu_official_gamebook_union_1998_
        # rejection_complete.py) import it first for their own reasons,
        # making this check fail even though THIS script never imports it.
        # Fixed two ways, neither shelling out to a subprocess:
        #
        # 1. Static check (primary, process-independent): read this recompute
        #    script's own source text and confirm the guarded module's dotted
        #    name never appears in an import statement at all.
        guarded_name = "aggie_analytics.data.tamu_official_gamebook_union_1998_rejection_complete"
        source_text = _MODULE_PATH.read_text(encoding="utf-8")
        for line in source_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                self.assertNotIn(
                    guarded_name,
                    stripped,
                    "the guarded module must never appear in this recompute script's own imports",
                )

        # 2. Dynamic check (secondary): the guarded module must not be newly
        #    added to sys.modules as a RESULT of calling run() -- comparing
        #    before/after membership, not absolute presence, so a prior
        #    test's legitimate import of the guarded module elsewhere in the
        #    same pytest process cannot cause a false failure here.
        was_present_before = guarded_name in sys.modules
        _module.run()
        is_present_after = guarded_name in sys.modules
        if not was_present_before:
            self.assertFalse(
                is_present_after,
                "run() must not cause the guarded module to be imported",
            )


if __name__ == "__main__":
    unittest.main()
