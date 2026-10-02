"""R34-04: the real 770-observation/468-contest recount pipeline runs and
produces the expected shape. Skipped if the raw scoreboard captures are not
present in this environment."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

_MODULE_PATH = REPO_ROOT / "tools" / "cycle34_r34_04_official_finals_recount.py"
_spec = importlib.util.spec_from_file_location("cycle34_r34_04_official_finals_recount", _MODULE_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)  # type: ignore[union-attr]

# W37R-68: the pipeline's configured output stays under the Cycle 34 ops receipts, and the tests below still check
# that; a test run writes into its own temporary directory, so the predecessor cycle's receipts are never
# rewritten (or, for R34-07's database, deleted and recreated) by a test.
_CONFIGURED_OUTPUT_DIR = _module.OUTPUT_DIR
_CONFIGURED_OUTPUT_PATH = getattr(_module, "OUTPUT_PATH", None)
_TEMP_OUTPUT = tempfile.TemporaryDirectory(prefix="bas-r34-")
for _name in ("OUTPUT_PATH", "DB_PATH", "SUMMARY_PATH"):
    if hasattr(_module, _name):
        setattr(_module, _name, Path(_TEMP_OUTPUT.name) / getattr(_module, _name).name)
_module.OUTPUT_DIR = Path(_TEMP_OUTPUT.name)


def tearDownModule() -> None:
    _TEMP_OUTPUT.cleanup()

RAW_READY = all((_module.RAW_ROOT / f).is_file() for f in _module.SCOREBOARD_FILES)


@unittest.skipUnless(RAW_READY, "raw NCAA.com scoreboard captures are not mounted in this environment")
class OfficialFinalsRecountTests(unittest.TestCase):
    def test_pipeline_runs_and_reports_real_counts(self) -> None:
        result = _module.run()
        self.assertEqual(result["total_observations_parsed"], sum(result["per_file_observation_counts"].values()))
        self.assertGreater(result["total_observations_parsed"], 0)
        # Internal consistency, not an assumed match to history:
        self.assertEqual(
            result["admitted_unique_games"] + result["quarantined_conflicts"] + result["nonfinal_contests"],
            result["unique_contest_count"],
        )
        matches_historical = result["total_observations_parsed"] == result["historical_recorded"]["observation_count"]
        print(f"recount matches historical 770/468/290 exactly: {matches_historical}")

    def test_output_file_written_under_cycle34_ops_only(self) -> None:
        result = _module.run()
        self.assertIn("\\ops\\cycle34\\", str(_CONFIGURED_OUTPUT_PATH))
        self.assertTrue(_module.OUTPUT_PATH.is_file())


if __name__ == "__main__":
    unittest.main()
