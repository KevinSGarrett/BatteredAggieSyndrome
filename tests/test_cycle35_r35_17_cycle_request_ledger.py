"""R35-17 (Cycle #35 closeout review, 20260921T025300Z), section 6: "The
final packet resets both budgets to 0 used / 50 remaining, lists no
component ledgers, and records zero infrastructure requests... Those
receipts were not erased by creating a new output directory."

The defect was structural: the packet globbed component ledgers out of its
own --out-dir, so a fresh directory reported a whole cycle as unspent.
These tests pin the cycle-scoped reconstruction, the deduplication rule,
and the real figures the manager independently recorded.
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

from r35_17_cycle_request_ledger import (  # noqa: E402
    CYCLE_RUNS,
    bind_prior_readbacks,
    build,
    collect,
    request_identity,
)


def _ledger(path: Path, entries: list[dict], spent: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "artifact_type": "CYCLE35_REQUEST_LEDGER_TEST",
                "entries": entries,
                "entry_count": len(entries),
                "spent": spent or {},
                "outcome_counts": {},
            }
        ),
        encoding="utf-8",
    )


def _entry(url: str, budget: str, spent: bool, **extra) -> dict:
    row = {
        "url": url,
        "at_utc": "2026-09-20T19:57:12.930039+00:00",
        "attempt": 1,
        "page": None,
        "budget": budget,
        "outcome": "FETCHED_OK" if spent else "CACHE_HIT_NO_REQUEST_SPENT",
        "spent_a_request": spent,
    }
    row.update(extra)
    return row


class RequestIdentityTests(unittest.TestCase):
    def test_the_same_attempt_has_one_identity(self) -> None:
        entry = _entry("https://example/a", "coaching_history", True)
        self.assertEqual(request_identity(entry), request_identity(dict(entry)))

    def test_a_retry_is_a_distinct_request_not_a_duplicate(self) -> None:
        """A retry really did spend budget. Collapsing it into the first
        attempt would under-count real spend."""
        first = _entry("https://example/a", "coaching_history", True, attempt=1)
        retry = _entry("https://example/a", "coaching_history", True, attempt=2)
        self.assertNotEqual(request_identity(first), request_identity(retry))

    def test_a_second_page_is_a_distinct_request(self) -> None:
        one = _entry("https://example/a", "coaching_history", True, page=1)
        two = _entry("https://example/a", "coaching_history", True, page=2)
        self.assertNotEqual(request_identity(one), request_identity(two))


class CollectAcrossDirectoriesTests(unittest.TestCase):
    def test_spend_is_summed_across_every_run_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ledger(
                root / "run_a" / "CYCLE35_REQUEST_LEDGER_ONE.json",
                [_entry("https://example/1", "coaching_history", True)],
            )
            _ledger(
                root / "run_b" / "CYCLE35_REQUEST_LEDGER_TWO.json",
                [_entry("https://example/2", "availability_context", True)],
            )
            out = collect(root)
        self.assertEqual(out["component_ledger_count"], 2)
        self.assertEqual(out["budgets"]["coaching_history"]["used_cycle_lifetime"], 1)
        self.assertEqual(out["budgets"]["availability_context"]["used_cycle_lifetime"], 1)

    def test_an_entry_recorded_in_two_directories_is_counted_once(self) -> None:
        shared = _entry("https://example/same", "coaching_history", True)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ledger(root / "run_a" / "CYCLE35_REQUEST_LEDGER_A.json", [shared])
            _ledger(root / "run_b" / "CYCLE35_REQUEST_LEDGER_B.json", [dict(shared)])
            out = collect(root)
        self.assertEqual(out["unique_request_entries"], 1)
        self.assertEqual(out["duplicate_entries_collapsed"], 1)
        self.assertEqual(out["budgets"]["coaching_history"]["used_cycle_lifetime"], 1)

    def test_cache_hits_do_not_spend_budget_but_are_counted(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ledger(
                root / "run" / "CYCLE35_REQUEST_LEDGER_C.json",
                [
                    _entry("https://example/x", "coaching_history", False),
                    _entry("https://example/y", "coaching_history", True),
                ],
            )
            out = collect(root)
        self.assertEqual(out["budgets"]["coaching_history"]["used_cycle_lifetime"], 1)
        self.assertEqual(out["cache_hits_no_request_spent"], 1)

    def test_an_empty_root_reports_zero_without_claiming_a_ceiling_reset(self) -> None:
        with TemporaryDirectory() as tmp:
            out = collect(Path(tmp))
        self.assertEqual(out["component_ledger_count"], 0)
        self.assertEqual(out["budgets"]["coaching_history"]["remaining"], 50)

    def test_a_missing_ledger_file_is_not_evidence_of_zero_spend(self) -> None:
        with TemporaryDirectory() as tmp:
            result = build(Path(tmp))
        self.assertTrue(result["missing_ledger_files_do_not_mean_zero_spend"])
        self.assertTrue(result["budget_is_cycle_scoped_not_process_scoped"])


class RealCycleReconstructionTests(unittest.TestCase):
    """Reproduces the manager's independently recorded cycle figures: 7
    coaching/history, 8 availability/context, 17 infrastructure readbacks,
    with component receipts that a new output directory did not erase."""

    def setUp(self) -> None:
        if not CYCLE_RUNS.is_dir():
            self.skipTest("cycle run root is not mounted")

    def test_real_cycle_budgets_match_the_recorded_component_receipts(self) -> None:
        result = build(CYCLE_RUNS)
        self.assertEqual(
            result["budgets"]["coaching_history"]["used_cycle_lifetime"], 7
        )
        self.assertEqual(
            result["budgets"]["availability_context"]["used_cycle_lifetime"], 8
        )
        self.assertEqual(result["infrastructure_readback_requests"], 17)

    def test_component_ledgers_are_found_outside_any_single_output_directory(self) -> None:
        result = build(CYCLE_RUNS)
        self.assertGreaterEqual(result["component_ledger_count"], 4)
        directories = {
            Path(item["path"]).parent.name
            for item in result["component_ledgers"]
            if item.get("readable")
        }
        self.assertTrue(directories)

    def test_prior_readbacks_are_bound_not_declared_absent(self) -> None:
        """The packet stated no live readback was performed this cycle. A
        readback artifact recording 11 issues already existed."""
        readbacks = bind_prior_readbacks(CYCLE_RUNS)
        self.assertTrue(readbacks["prior_readback_performed_this_cycle"])
        self.assertGreaterEqual(readbacks["artifact_count"], 1)
        jira = [
            item
            for item in readbacks["artifacts"]
            if "JIRA_LIVE_READBACK" in item["path"]
        ]
        self.assertTrue(jira)
        self.assertEqual(jira[0].get("issues_count"), 11)

    def test_no_paid_review_is_recorded(self) -> None:
        result = build(CYCLE_RUNS)
        self.assertEqual(result["paid_model_calls"], 0)
        self.assertEqual(result["paid_reviewer_calls"], 0)
        self.assertEqual(result["paid_ai_review_labels_applied"], 0)


if __name__ == "__main__":
    unittest.main()
