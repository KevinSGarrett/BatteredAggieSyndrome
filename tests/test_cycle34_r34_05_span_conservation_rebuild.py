"""R34-05: the real 798-cell rebuild pipeline runs and produces the expected
shape. Skipped if the predecessor's real evidence directory is not present
in this environment (matches the repo's existing LAKE_READY skip pattern)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

_MODULE_PATH = REPO_ROOT / "tools" / "cycle34_r34_05_span_conservation_rebuild.py"
_spec = importlib.util.spec_from_file_location("cycle34_r34_05_span_conservation_rebuild", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)  # type: ignore[union-attr]

PREDECESSOR_READY = _module.PREDECESSOR_SPAN_SUCCESSOR.is_file()


@unittest.skipUnless(
    PREDECESSOR_READY, "predecessor Cycle33 evidence directory is not mounted in this environment"
)
class SpanConservationRebuildTests(unittest.TestCase):
    def test_pipeline_runs_and_reproduces_expected_shape(self) -> None:
        result = _module.run()
        self.assertEqual(result["total_cells"], 798)
        self.assertTrue(result["episode_conservation_holds"])
        self.assertEqual(result["total_episodes_in"], 880)
        self.assertEqual(result["total_episodes_out_after_repair"], 880)
        # Do NOT assert the historical 643/101/26/28 figures blindly -- assert
        # that the repaired counts are INTERNALLY CONSISTENT (sum to 798,
        # non-negative) and separately report whether they happen to match
        # the historical record, per the instruction not to assume a match.
        counts = result["disposition_counts_after_repair"]
        self.assertEqual(sum(counts.values()), 798)
        for value in counts.values():
            self.assertGreaterEqual(value, 0)
        matches_historical = counts == result["historical_recorded_disposition_counts"]
        # Recorded as an observed fact, not asserted as a requirement --
        # print so the actual outcome is visible in test output either way.
        print(f"repaired counts match historical record exactly: {matches_historical}")

    def test_output_file_is_written_under_cycle34_ops_only(self) -> None:
        result = _module.run()
        self.assertTrue(str(_module.OUTPUT_PATH).startswith(
            r"C:\BatteredAggieSyndrome.data\ops\cycle34\\"
        ) or "\\ops\\cycle34\\" in str(_module.OUTPUT_PATH))
        self.assertTrue(_module.OUTPUT_PATH.is_file())


if __name__ == "__main__":
    unittest.main()
