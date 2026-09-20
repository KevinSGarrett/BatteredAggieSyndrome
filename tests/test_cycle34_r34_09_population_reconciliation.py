"""R34-09: the real 13,280-candidate/8,216-game population reconciliation
pipeline runs and produces the expected shape. Skipped if the real
predecessor candidate-population file is not present."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

_MODULE_PATH = REPO_ROOT / "tools" / "cycle34_r34_09_population_reconciliation.py"
_spec = importlib.util.spec_from_file_location("cycle34_r34_09_population_reconciliation", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)  # type: ignore[union-attr]

INPUT_READY = _module.INPUT_PATH.is_file()


@unittest.skipUnless(INPUT_READY, "real PIT_KERNEL_ROWS.jsonl candidate population is not mounted")
class PopulationReconciliationTests(unittest.TestCase):
    def test_pipeline_runs_and_reports_real_counts(self) -> None:
        result = _module.run()
        self.assertEqual(result["total_candidate_population_rows"], 13280)
        self.assertEqual(result["fit_cohort_2013_2023_row_count"], 8216)
        self.assertIsNone(result["validate_fit_population_on_real_full_population"]["error"])
        self.assertIsNone(result["fold_local_fit_intercept_only_on_real_2013_2023_cohort"]["error"])
        # The negative control MUST trigger -- this is what proves the MR33-09
        # fix is load-bearing, not a no-op, even though the real dataset itself
        # is fully identified.
        self.assertTrue(result["negative_control_on_corrupted_copy_of_real_sample"]["triggered"])

    def test_output_file_written_under_cycle34_ops_only(self) -> None:
        result = _module.run()
        self.assertIn("\\ops\\cycle34\\", str(_module.OUTPUT_PATH))
        self.assertTrue(_module.OUTPUT_PATH.is_file())


if __name__ == "__main__":
    unittest.main()
