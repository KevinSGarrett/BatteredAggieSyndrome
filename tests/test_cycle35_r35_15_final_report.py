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

from r35_15_final_report import (  # noqa: E402
    network_budget_paragraph,
    pr_check_summary,
)

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


class NetworkBudgetParagraphTests(unittest.TestCase):
    """This paragraph used to assert both ceilings were "fully unspent" and
    list two items a budget would buy that had already been bought."""

    def test_the_spend_is_read_from_the_ledger(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CYCLE35_CYCLE_WIDE_REQUEST_LEDGER.json").write_text(
                json.dumps(
                    {
                        "budgets": {
                            "availability_context": {
                                "ceiling": 50,
                                "used_cycle_lifetime": 8,
                            },
                            "coaching_history": {
                                "ceiling": 50,
                                "used_cycle_lifetime": 7,
                            },
                        },
                        "cache_hits_no_request_spent": 46,
                        "paid_model_calls": 0,
                        "paid_provider_calls": 0,
                        "paid_reviewer_calls": 0,
                    }
                ),
                encoding="utf-8",
            )
            paragraph = network_budget_paragraph(root, cycle_root=root)
        self.assertIn("availability_context 8/50", paragraph)
        self.assertIn("coaching_history 7/50", paragraph)
        self.assertNotIn("fully unspent", paragraph)

    def test_already_done_work_is_excluded_from_what_a_budget_would_buy(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CYCLE35_CYCLE_WIDE_REQUEST_LEDGER.json").write_text(
                json.dumps({"budgets": {}}), encoding="utf-8"
            )
            paragraph = network_budget_paragraph(root, cycle_root=root)
        self.assertIn("already carried out this cycle", paragraph)
        self.assertIn("NOT on that list", paragraph)

    def test_a_missing_ledger_makes_no_spend_claim(self) -> None:
        """Silence about spend must not read as zero spend.

        The search root is pinned to the empty directory: left unpinned the
        fallback reaches the real cycle tree and serves another run's
        ledger, which is the failure mode this test exists to rule out.
        """
        with TemporaryDirectory() as tmp:
            paragraph = network_budget_paragraph(Path(tmp), cycle_root=Path(tmp))
        self.assertIn("no claim is made about what has been spent", paragraph)
        self.assertNotIn("unspent", paragraph)

    def test_an_empty_out_dir_does_not_silently_serve_another_runs_ledger(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            pinned = network_budget_paragraph(Path(tmp), cycle_root=Path(tmp))
        self.assertIn("was not found", pinned)


class BlockerTableTests(unittest.TestCase):
    def test_the_table_shows_the_reconciled_category_not_the_declared_kind(
        self,
    ) -> None:
        if not REAL_REPORT.is_file():
            self.skipTest("the final report has not been generated")
        text = REAL_REPORT.read_text(encoding="utf-8")
        self.assertIn("| Requirement | Reconciled category |", text)
        self.assertIn("RESOLVED_BY_WORK_COMPLETED_IN_THIS_REVIEW", text)
        self.assertIn("reproduced verbatim from the declared unit list", text)

    def test_the_report_no_longer_says_the_branch_was_never_pushed(self) -> None:
        if not REAL_REPORT.is_file():
            self.skipTest("the final report has not been generated")
        self.assertNotIn(
            "the branch has never been pushed",
            REAL_REPORT.read_text(encoding="utf-8"),
        )



if __name__ == "__main__":
    unittest.main()
