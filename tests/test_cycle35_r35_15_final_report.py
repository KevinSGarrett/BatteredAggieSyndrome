"""R35-15 (Cycle #35 closeout review, 20260921T025300Z), sections 7 and 8.

"Do not use fixed narrative status dictionaries as authority."

Two lines of the final report were exactly that. The headline count of
remaining local work came from a keyword match on each blocker's own
wording, so it reported what the list said about itself rather than what
survived being checked. And the PR-checks row was the literal string
"12 of 12 pass" -- a status line that could not go red.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from r35_15_final_report import pr_check_summary  # noqa: E402

REAL_REPORT = (
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")
    / "20260921T025300Z_closeout"
    / "CYCLE35_FINAL_REPORT.md"
)


def write_ci(root: Path, payload: dict) -> None:
    (root / "CYCLE35_EXACT_HEAD_CI_STATUS.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


class PrCheckSummaryTests(unittest.TestCase):
    def test_a_failing_head_is_reported_as_failing(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_ci(
                root,
                {
                    "queried": True,
                    "head_sha": "bde83452467972306f9af19aa913355953e6b4fa",
                    "by_bucket": {"pass": 12, "fail": 6},
                },
            )
            summary = pr_check_summary(root)
        self.assertIn("12 of 18 pass", summary)
        self.assertIn("6 fail", summary)
        self.assertIn("bde834524679", summary)

    def test_a_fully_green_head_reports_no_failure_detail(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_ci(
                root,
                {"queried": True, "head_sha": "a" * 40, "by_bucket": {"pass": 18}},
            )
            summary = pr_check_summary(root)
        self.assertIn("18 of 18 pass", summary)
        self.assertNotIn("fail", summary)

    def test_an_unqueried_head_does_not_claim_a_result(self) -> None:
        """Silence about CI must not read as a pass."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_ci(root, {"queried": False})
            self.assertEqual(pr_check_summary(root), "NOT_QUERIED at report generation")

    def test_an_absent_artifact_does_not_claim_a_result(self) -> None:
        with TemporaryDirectory() as tmp:
            self.assertEqual(
                pr_check_summary(Path(tmp)), "NOT_QUERIED at report generation"
            )

    def test_a_pending_bucket_is_counted_in_the_denominator(self) -> None:
        """Reporting 12 of 12 while 6 are still running would be a pass claim
        about checks that have not finished."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_ci(
                root,
                {
                    "queried": True,
                    "head_sha": "b" * 40,
                    "by_bucket": {"pass": 12, "pending": 6},
                },
            )
            summary = pr_check_summary(root)
        self.assertIn("12 of 18 pass", summary)
        self.assertIn("6 pending", summary)


class RealReportTests(unittest.TestCase):
    def setUp(self) -> None:
        if not REAL_REPORT.is_file():
            self.skipTest("the final report has not been generated")
        self.text = REAL_REPORT.read_text(encoding="utf-8")

    def test_the_report_does_not_carry_the_hardcoded_pass_claim(self) -> None:
        self.assertNotIn(
            "12 of 12 pass, including core-validation", self.text
        )

    def test_the_headline_count_is_the_reconciled_one(self) -> None:
        """A count of blockers whose own wording mentions local work is not a
        count of local work that remains."""
        self.assertIn("real local work requiring no external authority", self.text)
        self.assertIn("checked against a delivered artifact", self.text)
        self.assertIn("REAL_LOCAL_WORK_REMAINING", self.text)

    def test_the_report_still_carries_the_hold(self) -> None:
        self.assertIn("IN_PROGRESS_LOCAL_WORK_REMAINS", self.text)
        self.assertIn("SCIENTIFIC_OPERATOR_HOLD_ACTIVE", self.text)


if __name__ == "__main__":
    unittest.main()
