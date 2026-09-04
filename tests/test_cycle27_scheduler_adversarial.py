"""Cycle 27 scheduler and lease adversarial tests. Offline; no live PID kills."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.operations.checkpoint_failover_policy import decide  # noqa: E402
from aggie_analytics.operations.checkpoint_lease import (  # noqa: E402
    acquire,
    lease_action_is_completion,
)


UTC = timezone.utc


class Cycle27SchedulerAdversarialTests(unittest.TestCase):
    def _times(self) -> dict[str, datetime]:
        cutoff = datetime(2026, 9, 4, 21, 0, tzinfo=UTC)
        wake = datetime(2026, 9, 4, 20, 15, tzinfo=UTC)
        window = datetime(2026, 9, 4, 20, 0, tzinfo=UTC)
        return {"cutoff": cutoff, "wake": wake, "window": window}

    def test_start_is_not_completion(self) -> None:
        self.assertFalse(lease_action_is_completion("ACQUIRED"))
        self.assertFalse(lease_action_is_completion("RENEWED"))
        self.assertTrue(lease_action_is_completion("EVIDENCE_CAPTURED"))

    def test_failed_acquisition_and_insufficient_retry_minutes(self) -> None:
        times = self._times()
        late = decide(
            now=times["cutoff"] - timedelta(minutes=2),
            wake=times["wake"],
            cutoff=times["cutoff"],
            capture_window_open=times["window"],
            primary_alive=False,
            last_progress=None,
            completion_receipt_verified=False,
            completed_at=None,
            attempts=1,
            required_attempt_budget=timedelta(minutes=5),
        )
        self.assertEqual(late.action, "INSUFFICIENT_TIME_FOR_RETRY")

    def test_start_then_hang_does_not_duplicate(self) -> None:
        times = self._times()
        hung = decide(
            now=times["wake"] + timedelta(minutes=10),
            wake=times["wake"],
            cutoff=times["cutoff"],
            capture_window_open=times["window"],
            primary_alive=True,
            last_progress=times["wake"],
            completion_receipt_verified=False,
            completed_at=None,
            attempts=0,
            progress_timeout=timedelta(minutes=6),
        )
        self.assertEqual(hung.action, "STALLED_PRIMARY")

    def test_stale_pid_and_lease_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = acquire(
                checkpoint="FRI_T90M",
                owner="primary",
                run_id="run-a",
                ttl_seconds=600,
                heartbeat_seconds=30,
                pid=40708,
                lease_root=root,
                pid_alive=lambda pid: True,
                now_unix=1_000_000,
            )
            self.assertTrue(first["ok"])
            collision = acquire(
                checkpoint="FRI_T90M",
                owner="failover",
                run_id="run-b",
                ttl_seconds=600,
                heartbeat_seconds=30,
                pid=41416,
                lease_root=root,
                pid_alive=lambda pid: True,
                now_unix=1_000_010,
            )
            self.assertFalse(collision["ok"])
            self.assertEqual(collision["action"], "HELD_BY_LIVE_OWNER")
            stale = acquire(
                checkpoint="FRI_T90M",
                owner="recovery",
                run_id="run-c",
                ttl_seconds=600,
                heartbeat_seconds=30,
                pid=99999,
                lease_root=root,
                pid_alive=lambda pid: False,
                now_unix=1_000_700,
            )
            self.assertNotEqual(stale.get("action"), "ACQUIRED")
            self.assertEqual(stale["action"], "STALE_OWNER_REQUIRES_VERIFIED_RECOVERY")

    def test_unrelated_old_receipt_is_not_this_checkpoint(self) -> None:
        times = self._times()
        with self.assertRaises(ValueError):
            decide(
                now=times["wake"],
                wake=times["wake"],
                cutoff=times["cutoff"],
                capture_window_open=times["window"],
                primary_alive=False,
                last_progress=None,
                completion_receipt_verified=True,
                completed_at=times["window"] - timedelta(hours=1),
                attempts=0,
            )

    def test_late_after_cutoff_is_not_backfill(self) -> None:
        times = self._times()
        missed = decide(
            now=times["cutoff"] + timedelta(minutes=1),
            wake=times["wake"],
            cutoff=times["cutoff"],
            capture_window_open=times["window"],
            primary_alive=False,
            last_progress=None,
            completion_receipt_verified=False,
            completed_at=None,
            attempts=1,
        )
        self.assertEqual(missed.action, "MISSED_CUTOFF_NO_BACKFILL")


if __name__ == "__main__":
    unittest.main()
