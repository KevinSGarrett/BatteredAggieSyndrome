"""Pure tests; no network, processes, shared payload writes or scheduler changes."""

import unittest
from datetime import datetime, timedelta, timezone

from aggie_analytics.operations.checkpoint_failover_policy import decide


class FailoverPolicyTests(unittest.TestCase):
    def setUp(self):
        self.cutoff = datetime(2026, 9, 4, 23, tzinfo=timezone.utc)
        self.kw = dict(
            now=self.cutoff - timedelta(minutes=25),
            wake=self.cutoff - timedelta(minutes=45),
            cutoff=self.cutoff,
            capture_window_open=self.cutoff - timedelta(minutes=60),
            primary_alive=False,
            last_progress=None,
            completion_receipt_verified=False,
            completed_at=None,
            attempts=1,
        )

    def decision(self, **changes):
        return decide(**(self.kw | changes)).action

    def test_dead_primary_retries_before_deadline(self):
        self.assertEqual(self.decision(), "START_RETRY_AFTER_EXCLUSIVE_LEASE")

    def test_start_message_is_not_completion(self):
        self.assertEqual(
            self.decision(primary_alive=True, last_progress=self.kw["now"]),
            "MONITOR_PRIMARY",
        )

    def test_hung_primary_is_not_duplicated(self):
        self.assertEqual(
            self.decision(
                primary_alive=True, last_progress=self.kw["now"] - timedelta(minutes=7)
            ),
            "STALLED_PRIMARY",
        )

    def test_primary_without_progress_is_not_success(self):
        self.assertEqual(self.decision(primary_alive=True), "STALLED_PRIMARY")

    def test_cannot_retry_at_cutoff(self):
        self.assertEqual(self.decision(now=self.cutoff), "MISSED_CUTOFF_NO_BACKFILL")

    def test_no_late_recovery(self):
        self.assertEqual(
            self.decision(now=self.cutoff + timedelta(seconds=1)),
            "MISSED_CUTOFF_NO_BACKFILL",
        )

    def test_budgeted_time_reserve(self):
        self.assertEqual(
            self.decision(now=self.cutoff - timedelta(minutes=4)),
            "INSUFFICIENT_TIME_FOR_RETRY",
        )

    def test_bounded_retries(self):
        self.assertEqual(self.decision(attempts=3), "RETRY_BUDGET_EXHAUSTED")

    def test_wait_before_wake(self):
        self.assertEqual(self.decision(now=self.cutoff - timedelta(minutes=50)), "WAIT")

    def test_on_time_receipt_retained_after_deadline(self):
        self.assertEqual(
            self.decision(
                now=self.cutoff + timedelta(minutes=10),
                completion_receipt_verified=True,
                completed_at=self.cutoff - timedelta(minutes=1),
            ),
            "COMPLETE",
        )

    def test_late_receipt_is_not_backfilled(self):
        self.assertEqual(
            self.decision(
                now=self.cutoff + timedelta(minutes=10),
                completion_receipt_verified=True,
                completed_at=self.cutoff + timedelta(seconds=1),
            ),
            "MISSED_CUTOFF_NO_BACKFILL",
        )

    def test_unverified_filename_not_completion(self):
        self.assertEqual(
            self.decision(
                now=self.cutoff + timedelta(minutes=10),
                completed_at=self.cutoff - timedelta(minutes=1),
            ),
            "MISSED_CUTOFF_NO_BACKFILL",
        )

    def test_future_receipt_rejected(self):
        with self.assertRaises(ValueError):
            self.decision(completion_receipt_verified=True, completed_at=self.cutoff)

    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            self.decision(now=self.kw["now"].replace(tzinfo=None))

    def test_verified_flag_requires_time(self):
        with self.assertRaises(ValueError):
            self.decision(completion_receipt_verified=True)

    def test_future_progress_rejected(self):
        with self.assertRaises(ValueError):
            self.decision(last_progress=self.cutoff)

    def test_invalid_attempts_rejected(self):
        for value in (True, -1, 4, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.decision(attempts=value)

    def test_old_checkpoint_receipt_rejected(self):
        with self.assertRaises(ValueError):
            self.decision(
                completion_receipt_verified=True,
                completed_at=self.cutoff - timedelta(days=1),
            )

    def test_completion_exactly_at_cutoff(self):
        self.assertEqual(
            self.decision(
                now=self.cutoff,
                completion_receipt_verified=True,
                completed_at=self.cutoff,
            ),
            "COMPLETE",
        )

    def test_exact_retry_budget_admitted(self):
        self.assertEqual(
            self.decision(now=self.cutoff - timedelta(minutes=5)),
            "START_RETRY_AFTER_EXCLUSIVE_LEASE",
        )

    def test_exact_progress_timeout_monitored(self):
        self.assertEqual(
            self.decision(
                primary_alive=True, last_progress=self.kw["now"] - timedelta(minutes=6)
            ),
            "MONITOR_PRIMARY",
        )

    def test_invalid_capture_window_rejected(self):
        with self.assertRaises(ValueError):
            self.decision(capture_window_open=self.cutoff)


if __name__ == "__main__":
    unittest.main()
