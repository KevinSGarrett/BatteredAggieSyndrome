from __future__ import annotations

import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aggie_analytics.assistive_plane.controller_state import ControllerState
from aggie_analytics.assistive_plane.service_runtime import (
    ControllerService,
    ControllerServiceConfig,
    WatchdogService,
    WatchdogServiceConfig,
)
from aggie_analytics.assistive_plane.watchdog import ReadOnlyWatchdog


class UnifiedControllerStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "orchestrator.sqlite3"
        self.state = ControllerState(self.database)
        self.state.initialize()
        self.now = datetime(2026, 8, 12, 23, 0, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def register(self) -> None:
        self.state.register_work_unit(
            work_unit_id="UNIT-1",
            identity_sha256="a" * 64,
            jira_identity="BAT-560",
            effort_points=3,
            actor="test",
            now=self.now,
        )

    def test_sqlite_wal_and_watchdog_live_heartbeat(self) -> None:
        self.state.acquire_leader("owner-a", "b" * 40, now=self.now)
        report = ReadOnlyWatchdog(self.database).inspect(now=self.now + timedelta(seconds=30))
        self.assertEqual("PASS", report["result"])
        self.assertTrue(report["controller_alive"])
        self.assertEqual("WAL", report["journal_mode"])

    def test_watchdog_fails_stale_without_controller_mutation(self) -> None:
        self.state.acquire_leader("owner-a", "b" * 40, now=self.now, ttl_seconds=120)
        report = ReadOnlyWatchdog(self.database).inspect(now=self.now + timedelta(seconds=121))
        self.assertEqual("FAIL", report["result"])
        self.assertIn("CONTROLLER_HEARTBEAT_STALE", report["findings"])
        self.assertIn("CONTROLLER_LEASE_EXPIRED", report["findings"])

    def test_single_database_leader_fails_closed(self) -> None:
        self.state.acquire_leader("owner-a", "b" * 40, now=self.now)
        with self.assertRaisesRegex(RuntimeError, "CONTROLLER_DATABASE_LEADER_ACTIVE"):
            self.state.acquire_leader("owner-b", "c" * 40, now=self.now + timedelta(seconds=1))

    def test_work_identity_and_transition_are_compare_and_swap(self) -> None:
        self.register()
        self.state.register_work_unit(
            work_unit_id="UNIT-1",
            identity_sha256="a" * 64,
            jira_identity="BAT-560",
            effort_points=3,
            actor="test",
            now=self.now,
        )
        with self.assertRaisesRegex(RuntimeError, "IMMUTABLE_WORK_UNIT_IDENTITY_CONFLICT"):
            self.state.register_work_unit(
                work_unit_id="UNIT-1",
                identity_sha256="c" * 64,
                jira_identity="BAT-560",
                effort_points=3,
                actor="test",
                now=self.now,
            )
        self.assertEqual(
            1,
            self.state.transition(
                work_unit_id="UNIT-1",
                expected_state="DISCOVERED",
                new_state="ELIGIBLE",
                reason="DEPENDENCIES_PASS",
                actor="test",
                now=self.now,
            ),
        )
        with self.assertRaisesRegex(RuntimeError, "COMPARE_AND_SWAP_STATE_CONFLICT"):
            self.state.transition(
                work_unit_id="UNIT-1",
                expected_state="DISCOVERED",
                new_state="ELIGIBLE",
                reason="DUPLICATE",
                actor="test",
                now=self.now,
            )

    def test_budget_reservation_settlement_and_hard_stop(self) -> None:
        self.register()
        self.state.configure_budget("openrouter", "25.00", "5.00", "AUTH", now=self.now)
        snapshot = self.state.reserve(
            reservation_id="RES-1",
            provider="openrouter",
            work_unit_id="UNIT-1",
            estimated_usd="1.25",
            now=self.now,
        )
        self.assertEqual(375, snapshot.available_cents)
        same = self.state.reserve(
            reservation_id="RES-1",
            provider="openrouter",
            work_unit_id="UNIT-1",
            estimated_usd="1.25",
            now=self.now,
        )
        self.assertEqual(snapshot, same)
        settled = self.state.settle("RES-1", "1.10", now=self.now)
        self.assertEqual(110, settled.settled_cents)
        with self.assertRaisesRegex(RuntimeError, "PROVIDER_BUDGET_ADMISSION_REJECTED"):
            self.state.reserve(
                reservation_id="RES-2",
                provider="openrouter",
                work_unit_id="UNIT-1",
                estimated_usd="4.00",
                now=self.now,
            )

    def test_no_change_cycle_cannot_hide_dispatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "NO_CHANGE_CYCLE_DISPATCH_CONFLICT"):
            self.state.record_cycle(
                cycle_id="CYCLE-1",
                inventory_sha256="d" * 64,
                eligible_units=1,
                dispatched_units=1,
                no_change=True,
                result="PASS",
                now=self.now,
            )

    def test_watchdog_bounded_runtime_does_not_sleep_full_interval(self) -> None:
        state = ControllerState(Path(self.temp.name) / "runtime" / "state" / "orchestrator.sqlite3")
        state.initialize()
        service = WatchdogService(
            WatchdogServiceConfig(
                runtime_root=Path(self.temp.name) / "runtime",
                build_commit="b" * 40,
                interval_seconds=5.0,
            )
        )
        started = time.monotonic()
        service.run(threading.Event(), maximum_runtime_seconds=0.05)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.4)

    def test_controller_bounded_runtime_does_not_sleep_past_deadline(self) -> None:
        service = ControllerService(
            ControllerServiceConfig(
                runtime_root=Path(self.temp.name) / "runtime",
                owner_id="test-owner",
                build_commit="b" * 40,
                heartbeat_seconds=5.0,
                queue_evaluation_seconds=5.0,
                lease_ttl_seconds=10,
            )
        )
        started = time.monotonic()
        service.run(threading.Event(), maximum_runtime_seconds=0.05)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.2)


if __name__ == "__main__":
    unittest.main()
