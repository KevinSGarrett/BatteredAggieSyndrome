"""R35-10 tests for MF35-10: baseline-equivalence tooling must preserve
event/subtest identity rather than collapsing parameterized subtests, and a
validation receipt must never let its own generation-time head stand in for
the head a captured lane's output actually ran at.

The Cycle #35 manager follow-up found two concrete defects in
tools/cycle35/r35_14_validation_results.py:

* `_RED`'s regex stopped at the first parenthesized group in a unittest
  failure header, so `FAIL: method (module.Class) (season=2019)` and
  `FAIL: method (module.Class) (season=2020)` -- two DIFFERENT subTest
  parameterizations of the same method -- collapsed to one identity. Six
  season-specific subtest failure events collapsed into two method IDs.
* The report recorded `git rev-parse HEAD` fresh at report-GENERATION time
  as if it described every captured lane in the file, when a lane's output
  could have been captured at an earlier, different commit. A real report
  was found claiming head f948e319 with a dirty worktree while the actual
  submission was at c6bb041a.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.cycle35.r35_14_validation_results import (  # noqa: E402
    baseline_comparison,
    lane_staleness,
    red_events,
    red_ids,
)

PARAMETERIZED_LOG = """
======================================================================
FAIL: test_era (mod.EraTests) (season=2001)
----------------------------------------------------------------------
Traceback (most recent call last):
AssertionError: boom

======================================================================
FAIL: test_era (mod.EraTests) (season=2002)
----------------------------------------------------------------------
Traceback (most recent call last):
AssertionError: boom

======================================================================
ERROR: test_plain (mod.PlainTests)
----------------------------------------------------------------------
Traceback (most recent call last):
RuntimeError: boom
"""


class RedIdentityTests(unittest.TestCase):
    def _write(self, tmp: Path, text: str) -> Path:
        path = tmp / "log.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def test_distinct_subtest_parameterizations_are_distinct_identities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), PARAMETERIZED_LOG)
            ids = red_ids(path)
            self.assertEqual(len(ids), 3)
            self.assertTrue(any("season=2001" in i for i in ids))
            self.assertTrue(any("season=2002" in i for i in ids))

    def test_non_subtest_failure_is_unaffected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), PARAMETERIZED_LOG)
            ids = red_ids(path)
            self.assertIn("mod.PlainTests.test_plain", ids)

    def test_red_events_preserves_event_type_and_subtest_suffix_separately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), PARAMETERIZED_LOG)
            events = red_events(path)
            self.assertEqual(len(events), 3)
            era_events = [e for e in events if e["method"] == "test_era"]
            self.assertEqual(len(era_events), 2)
            self.assertEqual({e["event_type"] for e in era_events}, {"FAIL"})
            self.assertEqual(
                sorted(e["subtest_suffix"] for e in era_events),
                ["(season=2001)", "(season=2002)"],
            )
            plain = next(e for e in events if e["method"] == "test_plain")
            self.assertEqual(plain["event_type"], "ERROR")
            self.assertEqual(plain["subtest_suffix"], "")

    def test_identical_method_different_event_type_are_distinct_events(self) -> None:
        text = (
            "FAIL: test_x (mod.T)\n"
            "----\nA\n\n"
            "ERROR: test_x (mod.T)\n"
            "----\nB\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), text)
            events = red_events(path)
            self.assertEqual(len(events), 2)
            self.assertEqual({e["event_type"] for e in events}, {"FAIL", "ERROR"})


class BaselineComparisonTests(unittest.TestCase):
    def test_reports_both_identity_and_event_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            candidate = tmp / "candidate.txt"
            baseline = tmp / "baseline.txt"
            candidate.write_text(PARAMETERIZED_LOG, encoding="utf-8")
            baseline.write_text(PARAMETERIZED_LOG, encoding="utf-8")
            result = baseline_comparison(str(candidate), str(baseline), "TEST")
            self.assertEqual(result["state"], "COMPARED")
            self.assertEqual(result["candidate_red_count"], 3)
            self.assertEqual(result["candidate_event_count"], 3)
            self.assertTrue(result["identity_count_and_event_count_answer_different_questions"])

    def test_collapsed_identity_would_have_hidden_a_real_regression(self) -> None:
        """Proves the fix actually matters: a candidate log that introduces
        a NEW subtest failure at a season the baseline never failed at must
        be visible as a regression, not absorbed into an already-red method
        identity."""
        baseline_text = """
======================================================================
FAIL: test_era (mod.EraTests) (season=2001)
----------------------------------------------------------------------
AssertionError: boom
"""
        candidate_text = """
======================================================================
FAIL: test_era (mod.EraTests) (season=2001)
----------------------------------------------------------------------
AssertionError: boom

======================================================================
FAIL: test_era (mod.EraTests) (season=2009)
----------------------------------------------------------------------
AssertionError: new failure
"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            candidate = tmp / "candidate.txt"
            baseline = tmp / "baseline.txt"
            candidate.write_text(candidate_text, encoding="utf-8")
            baseline.write_text(baseline_text, encoding="utf-8")
            result = baseline_comparison(str(candidate), str(baseline), "TEST")
            self.assertEqual(result["regression_count"], 1)
            self.assertIn("season=2009", result["regressions_introduced"][0])


class LaneStalenessTests(unittest.TestCase):
    def test_no_output_is_not_captured(self) -> None:
        self.assertEqual(lane_staleness("", "", "abc")["state"], "LANE_NOT_CAPTURED")

    def test_missing_declared_head_is_flagged_unproven(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.txt"
            path.write_text("x", encoding="utf-8")
            result = lane_staleness(str(path), "", "reportheadabc")
            self.assertEqual(result["state"], "LANE_HEAD_NOT_DECLARED_BY_CALLER")
            self.assertTrue(result["reuse_at_report_generation_head_is_unproven"])

    def test_matching_declared_head_is_not_flagged_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.txt"
            path.write_text("x", encoding="utf-8")
            result = lane_staleness(str(path), "abc123", "abc123")
            self.assertTrue(result["matches_report_generation_head"])
            self.assertFalse(result["reuse_at_report_generation_head_is_unproven"])

    def test_mismatched_declared_head_reproduces_the_manager_finding(self) -> None:
        """The manager's exact reproduction shape: report claims one head
        while the lane's output was actually captured at a different one."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.txt"
            path.write_text("x", encoding="utf-8")
            result = lane_staleness(
                str(path), "f948e319aaaa", "c6bb041aaaaa"
            )
            self.assertEqual(result["state"], "LANE_HEAD_DECLARED")
            self.assertFalse(result["matches_report_generation_head"])
            self.assertTrue(result["reuse_at_report_generation_head_is_unproven"])


if __name__ == "__main__":
    unittest.main()
