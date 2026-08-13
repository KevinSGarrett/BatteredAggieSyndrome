from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aggie_analytics.assistive_plane.controller_state import ControllerState, process_is_live
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

    def test_orphan_recovery_releases_exact_bound_owner_and_records_event(self) -> None:
        owner = "host:12345:" + ("a" * 32)
        self.state.acquire_leader(owner, "b" * 40, now=self.now, ttl_seconds=120)
        with mock.patch("aggie_analytics.assistive_plane.controller_state.process_is_live", return_value=False):
            self.state.release_orphaned_leader(
                expected_owner_id=owner,
                expected_build_commit="b" * 40,
                expected_owner_pid=12345,
                recovery_evidence_sha256="e" * 64,
                now=self.now + timedelta(seconds=1),
            )
        status = self.state.status()
        self.assertIsNone(status["leader"])
        connection = self.state.connect()
        try:
            event = connection.execute(
                "SELECT event_type,payload_json FROM controller_events ORDER BY event_id DESC LIMIT 1"
            ).fetchone()
            self.assertEqual("CONTROLLER_ORPHAN_LEASE_RECOVERED", event["event_type"])
            self.assertIn('"expected_owner_pid":12345', event["payload_json"])
            self.assertIn('"recovery_evidence_sha256":"' + ("e" * 64) + '"', event["payload_json"])
        finally:
            connection.close()

    def test_orphan_recovery_fails_closed_on_owner_or_build_mismatch(self) -> None:
        owner = "host:12345:" + ("a" * 32)
        self.state.acquire_leader(owner, "b" * 40, now=self.now, ttl_seconds=120)
        with mock.patch("aggie_analytics.assistive_plane.controller_state.process_is_live", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "CONTROLLER_RECOVERY_LEASE_MISMATCH"):
                self.state.release_orphaned_leader(
                    expected_owner_id=owner,
                    expected_build_commit="c" * 40,
                    expected_owner_pid=12345,
                    recovery_evidence_sha256="e" * 64,
                    now=self.now + timedelta(seconds=1),
                )
            with self.assertRaisesRegex(RuntimeError, "CONTROLLER_RECOVERY_OWNER_PID_MISMATCH"):
                self.state.release_orphaned_leader(
                    expected_owner_id=owner,
                    expected_build_commit="b" * 40,
                    expected_owner_pid=99999,
                    recovery_evidence_sha256="e" * 64,
                    now=self.now + timedelta(seconds=1),
                )

    def test_orphan_recovery_rejects_still_live_owner_pid(self) -> None:
        owner = "host:12345:" + ("a" * 32)
        self.state.acquire_leader(owner, "b" * 40, now=self.now, ttl_seconds=120)
        with mock.patch(
            "aggie_analytics.assistive_plane.controller_state.process_is_live", return_value=True
        ):
            with self.assertRaisesRegex(RuntimeError, "CONTROLLER_RECOVERY_OWNER_PROCESS_LIVE"):
                self.state.release_orphaned_leader(
                    expected_owner_id=owner,
                    expected_build_commit="b" * 40,
                    expected_owner_pid=12345,
                    recovery_evidence_sha256="e" * 64,
                    now=self.now + timedelta(seconds=1),
                )

    def test_orphan_recovery_rejects_malformed_identities(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "CONTROLLER_RECOVERY_OWNER_ID_FORMAT_INVALID"):
            self.state.release_orphaned_leader(
                expected_owner_id="host:12345:not-a-canonical-owner-token",
                expected_build_commit="b" * 40,
                expected_owner_pid=12345,
                recovery_evidence_sha256="e" * 64,
            )
        with self.assertRaisesRegex(ValueError, "RECOVERY_BUILD_IDENTITY_INVALID"):
            self.state.release_orphaned_leader(
                expected_owner_id="host:12345:" + ("a" * 32),
                expected_build_commit="z" * 40,
                expected_owner_pid=12345,
                recovery_evidence_sha256="e" * 64,
            )
        with self.assertRaisesRegex(ValueError, "RECOVERY_EVIDENCE_IDENTITY_INVALID"):
            self.state.release_orphaned_leader(
                expected_owner_id="host:12345:" + ("a" * 32),
                expected_build_commit="b" * 40,
                expected_owner_pid=12345,
                recovery_evidence_sha256="z" * 64,
            )

    @unittest.skipUnless(os.name == "nt", "Windows process-probe regression")
    def test_windows_process_liveness_probe_is_non_mutating(self) -> None:
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            self.assertTrue(process_is_live(child.pid))
            self.assertIsNone(child.poll(), "liveness probe must not terminate the queried process")
        finally:
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=10)

    def test_undispatched_work_revision_is_preserved_and_superseded(self) -> None:
        self.register()
        self.state.register_work_unit(
            work_unit_id="UNIT-1",
            identity_sha256="a" * 64,
            jira_identity="BAT-560",
            effort_points=3,
            actor="test",
            now=self.now,
        )
        self.state.register_work_unit(
            work_unit_id="UNIT-1",
            identity_sha256="c" * 64,
            jira_identity="BAT-560",
            effort_points=3,
            actor="test",
            inventory_sha256="d" * 64,
            now=self.now,
        )
        connection = self.state.connect()
        try:
            revisions = connection.execute(
                "SELECT identity_sha256,superseded_by_sha256 FROM work_unit_revisions "
                "WHERE work_unit_id=? ORDER BY first_seen_at,identity_sha256",
                ("UNIT-1",),
            ).fetchall()
            self.assertEqual(2, len(revisions))
            old = next(row for row in revisions if row["identity_sha256"] == "a" * 64)
            self.assertEqual("c" * 64, old["superseded_by_sha256"])
            observation = connection.execute(
                "SELECT inventory_sha256 FROM work_unit_revision_observations WHERE work_unit_id=?",
                ("UNIT-1",),
            ).fetchone()
            self.assertEqual("d" * 64, observation["inventory_sha256"])
        finally:
            connection.close()

    def test_startup_recovery_requeues_only_expired_pre_dispatch_lease(self) -> None:
        self.register()
        claimed = self.state.claim_dispatch(
            work_unit_id="UNIT-1",
            dependencies=(),
            lease_id="lease-1",
            attempt_id="attempt-1",
            owner_id="owner-old",
            provider="remote_cpu_worker",
            route_identity="b" * 64,
            readiness_evidence_sha256="c" * 64,
            now=self.now,
            ttl_seconds=1,
        )
        self.assertTrue(claimed)

        recovery = self.state.reconcile_expired_work_leases(now=self.now + timedelta(seconds=2))

        self.assertEqual(
            {"expired_leases_observed": 1, "recovered_pre_dispatch": 1, "provider_reconciliation_required": 0},
            recovery,
        )
        connection = self.state.connect()
        try:
            self.assertEqual(
                "RETRY_WAIT",
                connection.execute("SELECT current_state FROM work_units WHERE work_unit_id='UNIT-1'").fetchone()[0],
            )
            self.assertEqual(
                "FAILED",
                connection.execute("SELECT state FROM dispatch_attempts WHERE attempt_id='attempt-1'").fetchone()[0],
            )
            self.assertEqual(
                "ABANDONED",
                connection.execute("SELECT status FROM work_leases WHERE lease_id='lease-1'").fetchone()[0],
            )
        finally:
            connection.close()
        self.assertTrue(
            self.state.claim_dispatch(
                work_unit_id="UNIT-1",
                dependencies=(),
                lease_id="lease-2",
                attempt_id="attempt-2",
                owner_id="owner-new",
                provider="remote_cpu_worker",
                route_identity="b" * 64,
                readiness_evidence_sha256="c" * 64,
                now=self.now + timedelta(seconds=2),
            )
        )

    def test_startup_recovery_never_retries_ambiguous_inflight_provider_attempt(self) -> None:
        self.register()
        self.state.claim_dispatch(
            work_unit_id="UNIT-1",
            dependencies=(),
            lease_id="lease-1",
            attempt_id="attempt-1",
            owner_id="owner-old",
            provider="remote_cpu_worker",
            route_identity="b" * 64,
            readiness_evidence_sha256="c" * 64,
            now=self.now,
            ttl_seconds=1,
        )
        request = Path(self.temp.name) / "request.json"
        request.write_text("{}", encoding="utf-8")
        self.state.record_dispatch(
            work_unit_id="UNIT-1",
            attempt_id="attempt-1",
            provider_run_id="run-1",
            provider="remote_cpu_worker",
            remote_identity="remote-1",
            request_sha256="d" * 64,
            request_artifact_path=request,
            actor="owner-old",
            now=self.now,
        )

        recovery = self.state.reconcile_expired_work_leases(now=self.now + timedelta(seconds=2))

        self.assertEqual(1, recovery["provider_reconciliation_required"])
        self.assertEqual(0, recovery["recovered_pre_dispatch"])
        connection = self.state.connect()
        try:
            self.assertEqual(
                "DISPATCHED",
                connection.execute("SELECT current_state FROM work_units WHERE work_unit_id='UNIT-1'").fetchone()[0],
            )
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM retry_records").fetchone()[0])
            self.assertEqual(
                "ABANDONED_INFLIGHT_PROVIDER_RECONCILIATION_REQUIRED",
                connection.execute("SELECT finding FROM incidents ORDER BY opened_at DESC LIMIT 1").fetchone()[0],
            )
        finally:
            connection.close()

    def test_active_work_revision_change_fails_closed(self) -> None:
        self.register()
        self.state.transition(
            work_unit_id="UNIT-1",
            expected_state="DISCOVERED",
            new_state="ELIGIBLE",
            reason="DEPENDENCIES_PASS",
            actor="test",
            now=self.now,
        )
        with self.assertRaisesRegex(RuntimeError, "IMMUTABLE_ACTIVE_WORK_UNIT_IDENTITY_CONFLICT"):
            self.state.register_work_unit(
                work_unit_id="UNIT-1",
                identity_sha256="c" * 64,
                jira_identity="BAT-560",
                effort_points=3,
                actor="test",
                inventory_sha256="d" * 64,
                now=self.now,
            )

    def test_pre_dispatch_revision_reappearance_fails_closed_without_sqlite_error(self) -> None:
        self.register()
        self.state.register_work_unit(
            work_unit_id="UNIT-1",
            identity_sha256="c" * 64,
            jira_identity="BAT-560",
            effort_points=3,
            actor="test",
            inventory_sha256="d" * 64,
            now=self.now,
        )
        with self.assertRaisesRegex(RuntimeError, "WORK_UNIT_REVISION_REAPPEARANCE_CONFLICT"):
            self.state.register_work_unit(
                work_unit_id="UNIT-1",
                identity_sha256="a" * 64,
                jira_identity="BAT-560",
                effort_points=3,
                actor="test",
                inventory_sha256="e" * 64,
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

    def test_status_remains_read_only_compatible_with_schema_v3_during_upgrade(self) -> None:
        database = Path(self.temp.name) / "schema-v3" / "orchestrator.sqlite3"
        state = ControllerState(database)
        state.initialize()
        connection = sqlite3.connect(database)
        try:
            connection.execute("PRAGMA foreign_keys=OFF")
            connection.execute("DROP TABLE dispatch_attempts")
            connection.execute("DROP TABLE reviews")
            connection.execute("UPDATE metadata SET value='3' WHERE key='schema_version'")
            connection.commit()
        finally:
            connection.close()

        status = state.status()

        self.assertEqual(3, status["schema_version"])
        self.assertEqual(0, status["dispatch_attempts"])
        self.assertEqual(0, status["closed_dispatch_attempts"])
        self.assertEqual({}, status["review_dispositions"])

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
        self.assertLess(elapsed, 1.0)

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
        self.assertLess(elapsed, 1.0)


if __name__ == "__main__":
    unittest.main()
