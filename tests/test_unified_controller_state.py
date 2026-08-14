from __future__ import annotations

import json
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

    def test_initialize_reconciles_unresolved_incident_for_already_closed_unit(self) -> None:
        self.register()
        connection = self.state.connect()
        try:
            connection.execute(
                "UPDATE work_units SET current_state='QUARANTINED' WHERE work_unit_id='UNIT-1'"
            )
            connection.execute(
                "INSERT INTO incidents(incident_id,work_unit_id,finding,opened_at) VALUES(?,?,?,?)",
                ("incident-closed", "UNIT-1", "PRIOR_TRANSIENT_FAILURE", self.now.isoformat()),
            )
            connection.commit()
        finally:
            connection.close()
        self.state.initialize()
        connection = self.state.connect()
        try:
            row = connection.execute(
                "SELECT resolved_at FROM incidents WHERE incident_id='incident-closed'"
            ).fetchone()
        finally:
            connection.close()
        self.assertIsNotNone(row["resolved_at"])

    def test_watchdog_fails_stale_without_controller_mutation(self) -> None:
        self.state.acquire_leader("owner-a", "b" * 40, now=self.now, ttl_seconds=120)
        report = ReadOnlyWatchdog(self.database).inspect(now=self.now + timedelta(seconds=121))
        self.assertEqual("FAIL", report["result"])
        self.assertIn("CONTROLLER_HEARTBEAT_STALE", report["findings"])
        self.assertIn("CONTROLLER_LEASE_EXPIRED", report["findings"])

    def test_watchdog_fails_closed_when_closed_unit_loses_artifact_or_reconciliation(self) -> None:
        self.register()
        self.state.acquire_leader("owner-a", "b" * 40, now=self.now, ttl_seconds=120)
        self.assertTrue(
            self.state.claim_dispatch(
                work_unit_id="UNIT-1",
                dependencies=(),
                lease_id="lease-1",
                attempt_id="attempt-1",
                owner_id="owner-a",
                provider="remote_cpu_worker",
                route_identity="b" * 64,
                readiness_evidence_sha256="c" * 64,
                now=self.now,
            )
        )
        request = Path(self.temp.name) / "request.json"
        request.write_text('{"request":1}', encoding="utf-8")
        self.state.record_dispatch(
            work_unit_id="UNIT-1",
            attempt_id="attempt-1",
            provider_run_id="run-1",
            provider="remote_cpu_worker",
            remote_identity="remote-1",
            request_sha256="d" * 64,
            request_artifact_path=request,
            actor="owner-a",
            now=self.now,
        )
        result = Path(self.temp.name) / "result.json"
        result.write_text('{"result":1}', encoding="utf-8")
        self.state.record_result_and_artifact(
            work_unit_id="UNIT-1",
            attempt_id="attempt-1",
            provider_run_id="run-1",
            result_sha256="e" * 64,
            artifact_path=result,
            actor="owner-a",
            now=self.now,
        )
        connection = self.state.connect()
        try:
            connection.execute(
                "INSERT INTO incidents(incident_id,work_unit_id,attempt_id,finding,opened_at) "
                "VALUES(?,?,?,?,?)",
                ("incident-1", "UNIT-1", "attempt-1", "TRANSIENT_PROVIDER_FAILURE", self.now.isoformat()),
            )
            connection.commit()
        finally:
            connection.close()
        self.state.complete_validated_review_only(
            work_unit_id="UNIT-1",
            attempt_id="attempt-1",
            lease_id="lease-1",
            validation_sha256="f" * 64,
            review_sha256="1" * 64,
            cleanup_sha256="2" * 64,
            actor="owner-a",
            now=self.now,
        )
        connection = self.state.connect()
        try:
            incident = connection.execute(
                "SELECT resolved_at FROM incidents WHERE incident_id='incident-1'"
            ).fetchone()
        finally:
            connection.close()
        self.assertIsNotNone(incident["resolved_at"])
        watchdog = ReadOnlyWatchdog(self.database, expected_build_commit="b" * 40)
        complete = watchdog.inspect(now=self.now + timedelta(seconds=1))
        self.assertEqual(0, complete["closed_units_missing_evidence"])
        self.assertEqual(0, complete["closed_units_missing_execution_artifacts"])
        self.assertEqual(0, complete["closed_unit_execution_artifact_identity_mismatches"])
        self.assertEqual(0, complete["closed_units_missing_reconciliation"])
        self.assertEqual(0, complete["closed_unit_reconciliation_identity_mismatches"])

        result.write_text('{"tampered":1}', encoding="utf-8")
        tampered_artifact = watchdog.inspect(now=self.now + timedelta(seconds=1))
        self.assertIn("CLOSED_UNIT_EXECUTION_ARTIFACT_IDENTITY_MISMATCH", tampered_artifact["findings"])
        self.assertEqual(1, tampered_artifact["closed_unit_execution_artifact_identity_mismatches"])
        result.write_text('{"result":1}', encoding="utf-8")

        connection = self.state.connect()
        try:
            connection.execute("DELETE FROM execution_artifacts WHERE work_unit_id='UNIT-1'")
            connection.commit()
        finally:
            connection.close()
        missing_artifact = watchdog.inspect(now=self.now + timedelta(seconds=1))
        self.assertIn("CLOSED_UNIT_EXECUTION_ARTIFACT_MISSING", missing_artifact["findings"])
        self.assertEqual(1, missing_artifact["closed_units_missing_evidence"])
        self.assertEqual(1, missing_artifact["closed_units_missing_execution_artifacts"])

        connection = self.state.connect()
        try:
            connection.execute(
                "UPDATE reconciliation_records SET result_identity=? WHERE work_unit_id='UNIT-1'",
                ("9" * 64,),
            )
            connection.commit()
        finally:
            connection.close()
        missing_both = watchdog.inspect(now=self.now + timedelta(seconds=1))
        self.assertIn("CLOSED_UNIT_RECONCILIATION_IDENTITY_MISMATCH", missing_both["findings"])
        self.assertEqual(1, missing_both["closed_unit_reconciliation_identity_mismatches"])

    def test_candidate_settlement_preserves_dispatch_packet_provenance(self) -> None:
        self.register()
        self.assertTrue(
            self.state.claim_dispatch(
                work_unit_id="UNIT-1",
                dependencies=(),
                lease_id="lease-1",
                attempt_id="attempt-1",
                owner_id="owner-a",
                provider="cursor",
                route_identity="b" * 64,
                readiness_evidence_sha256="c" * 64,
                now=self.now,
            )
        )
        request = Path(self.temp.name) / "request.json"
        request.write_text('{"request":1}', encoding="utf-8")
        self.state.record_dispatch(
            work_unit_id="UNIT-1",
            attempt_id="attempt-1",
            provider_run_id="run-1",
            provider="cursor",
            remote_identity="cursor-agent",
            request_sha256="d" * 64,
            request_artifact_path=request,
            actor="owner-a",
            resource={
                "packet_path": "C:/immutable/packet.json",
                "packet_sha256": "e" * 64,
                "handle": {"agent_id": "cursor-agent"},
            },
            now=self.now,
        )
        result = Path(self.temp.name) / "result.json"
        result.write_text('{"result":1}', encoding="utf-8")
        self.state.record_result_and_artifact(
            work_unit_id="UNIT-1",
            attempt_id="attempt-1",
            provider_run_id="run-1",
            result_sha256="f" * 64,
            artifact_path=result,
            actor="owner-a",
            now=self.now,
        )
        with self.assertRaisesRegex(
            RuntimeError, "PROVIDER_SETTLEMENT_PACKET_PROVENANCE_CONFLICT"
        ):
            self.state.complete_candidate_work(
                work_unit_id="UNIT-1",
                attempt_id="attempt-1",
                lease_id="lease-1",
                validation_sha256="4" * 64,
                review_sha256="5" * 64,
                cleanup_sha256="6" * 64,
                validator="TEST_VALIDATOR",
                validation_result="PASS",
                reviewer="TEST_REVIEWER",
                disposition="REVIEW_ONLY",
                actual_cost_usd="0.25",
                settlement_reason="TEST_SETTLEMENT",
                cleanup_action="TEST_CLEANUP",
                actor="owner-a",
                resource={"packet_sha256": "9" * 64},
                now=self.now,
            )
        self.assertEqual(
            "RESULT_RECEIVED", self.state.work_unit_states({"UNIT-1"})["UNIT-1"]
        )
        self.state.complete_candidate_work(
            work_unit_id="UNIT-1",
            attempt_id="attempt-1",
            lease_id="lease-1",
            validation_sha256="1" * 64,
            review_sha256="2" * 64,
            cleanup_sha256="3" * 64,
            validator="TEST_VALIDATOR",
            validation_result="PASS",
            reviewer="TEST_REVIEWER",
            disposition="REVIEW_ONLY",
            actual_cost_usd="0.25",
            settlement_reason="TEST_SETTLEMENT",
            cleanup_action="TEST_CLEANUP",
            actor="owner-a",
            resource={"run_id": "cursor-run", "actual_cost_usd_exact": "0.25"},
            now=self.now,
        )
        connection = self.state.connect()
        try:
            resource = json.loads(
                connection.execute(
                    "SELECT resource_json FROM provider_runs WHERE attempt_id='attempt-1'"
                ).fetchone()[0]
            )
        finally:
            connection.close()
        self.assertEqual("C:/immutable/packet.json", resource["packet_path"])
        self.assertEqual("e" * 64, resource["packet_sha256"])
        self.assertEqual("cursor-agent", resource["handle"]["agent_id"])
        self.assertEqual("cursor-run", resource["run_id"])

    def test_single_database_leader_fails_closed(self) -> None:
        self.state.acquire_leader("owner-a", "b" * 40, now=self.now)
        with self.assertRaisesRegex(RuntimeError, "CONTROLLER_DATABASE_LEADER_ACTIVE"):
            self.state.acquire_leader("owner-b", "c" * 40, now=self.now + timedelta(seconds=1))

    def test_pre_routing_decision_is_immutable_and_unjustified_execution_fails_audit(self) -> None:
        base = {
            "work_unit_id": "BAT-560-BOOTSTRAP-1",
            "jira_identity": "BAT-560",
            "repository_identity": "BatteredAggieSyndrome",
            "source_commit": "b" * 40,
            "task_category": "PIPELINE_BOOTSTRAP_REPAIR",
            "effort_points": 5,
            "candidate_routes": ["CODEX"],
            "selected_route": "CODEX",
            "route_identity": "codex-desktop-final-authority",
            "budget_admission": "NOT_APPLICABLE",
            "packet_identity": None,
            "lease_identity": None,
            "disposition": "EMERGENCY_PIPELINE_REPAIR",
            "reason_code": "PERSISTENT_WORK_PRODUCER_MISSING",
            "evidence_sha256": "e" * 64,
            "discovered_at": self.now.isoformat().replace("+00:00", "Z"),
        }
        identity = self.state.record_pre_routing_decision(decision=base, now=self.now)
        self.assertEqual(64, len(identity))
        self.assertEqual(identity, self.state.record_pre_routing_decision(decision=base, now=self.now))
        with self.assertRaisesRegex(RuntimeError, "PRE_ROUTING_DECISION_IMMUTABILITY_CONFLICT"):
            self.state.record_pre_routing_decision(
                decision={**base, "reason_code": "DIFFERENT_REASON"}, now=self.now
            )

        unjustified = {
            **base,
            "work_unit_id": "PROJECT-WORK-1",
            "task_category": "HISTORICAL_EXTRACTION",
            "candidate_routes": ["openai_direct", "openrouter"],
            "selected_route": "CODEX",
            "disposition": "UNJUSTIFIED_DIRECT_EXECUTION",
            "reason_code": "QUEUE_EMPTY",
        }
        self.state.record_pre_routing_decision(decision=unjustified, now=self.now)
        self.state.acquire_leader("owner-a", "b" * 40, now=self.now)
        report = ReadOnlyWatchdog(
            self.database,
            inventory_path=Path(self.temp.name) / "missing-inventory.json",
        ).inspect(now=self.now + timedelta(seconds=1))
        self.assertIn("UNJUSTIFIED_DIRECT_EXECUTION_PRESENT", report["operational_findings"])
        self.assertEqual(1, report["unjustified_direct_execution_count"])

    def test_operational_condition_opens_once_after_threshold_and_resolves(self) -> None:
        self.assertFalse(
            self.state.observe_operational_condition(
                condition_id="PROVIDER_STARVATION:cursor",
                finding="P0_PROVIDER_STARVATION:cursor",
                threshold_seconds=1800,
                evidence_sha256="f" * 64,
                now=self.now,
            )
        )
        self.assertFalse(
            self.state.observe_operational_condition(
                condition_id="PROVIDER_STARVATION:cursor",
                finding="P0_PROVIDER_STARVATION:cursor",
                threshold_seconds=1800,
                evidence_sha256="f" * 64,
                now=self.now + timedelta(minutes=29),
            )
        )
        self.assertTrue(
            self.state.observe_operational_condition(
                condition_id="PROVIDER_STARVATION:cursor",
                finding="P0_PROVIDER_STARVATION:cursor",
                threshold_seconds=1800,
                evidence_sha256="f" * 64,
                now=self.now + timedelta(minutes=30),
            )
        )
        self.assertFalse(
            self.state.observe_operational_condition(
                condition_id="PROVIDER_STARVATION:cursor",
                finding="P0_PROVIDER_STARVATION:cursor",
                threshold_seconds=1800,
                evidence_sha256="f" * 64,
                now=self.now + timedelta(minutes=31),
            )
        )
        self.state.resolve_operational_conditions(
            set(),
            managed_prefixes=("PROVIDER_STARVATION:",),
            now=self.now + timedelta(minutes=32),
        )
        connection = self.state.connect()
        try:
            condition = connection.execute(
                "SELECT incident_opened,resolved_at FROM operational_conditions WHERE condition_id=?",
                ("PROVIDER_STARVATION:cursor",),
            ).fetchone()
            incidents = connection.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(1, condition["incident_opened"])
        self.assertIsNotNone(condition["resolved_at"])
        self.assertEqual(1, incidents)

    def test_restart_rebinds_only_submitted_cursor_run_without_new_attempt(self) -> None:
        self.register()
        owner = "host:12345:" + ("a" * 32)
        self.state.acquire_leader(owner, "b" * 40, now=self.now, ttl_seconds=60)
        self.assertTrue(
            self.state.claim_dispatch(
                work_unit_id="UNIT-1",
                dependencies=(),
                lease_id="lease-cursor",
                attempt_id="attempt-cursor",
                owner_id=owner,
                provider="cursor",
                route_identity="c" * 64,
                readiness_evidence_sha256="d" * 64,
                now=self.now,
                ttl_seconds=60,
            )
        )
        request = Path(self.temp.name) / "cursor-request.json"
        request.write_text('{"request":1}', encoding="utf-8")
        self.state.record_dispatch(
            work_unit_id="UNIT-1",
            attempt_id="attempt-cursor",
            provider_run_id="run-cursor",
            provider="cursor",
            remote_identity="bc-agent",
            request_sha256="e" * 64,
            request_artifact_path=request,
            actor=owner,
            resource={"handle": {"agent_id": "bc-agent"}},
            now=self.now,
        )
        recovery_time = self.now + timedelta(seconds=61)
        self.assertEqual(
            {"expired_leases_observed": 1, "recovered_pre_dispatch": 0, "provider_reconciliation_required": 1},
            self.state.reconcile_expired_work_leases(now=recovery_time),
        )
        new_owner = "host:54321:" + ("f" * 32)
        self.state.acquire_leader(new_owner, "b" * 40, now=recovery_time)
        self.assertEqual(
            1,
            self.state.recover_cursor_inflight_leases(owner_id=new_owner, now=recovery_time),
        )
        inflight = self.state.inflight_provider_runs("cursor")
        self.assertEqual(1, len(inflight))
        self.assertEqual("attempt-cursor", inflight[0]["attempt_id"])
        self.assertEqual(1, self.state.dispatch_attempt_count("UNIT-1"))
        connection = self.state.connect()
        try:
            lease = connection.execute(
                "SELECT owner_id,status FROM work_leases WHERE lease_id='lease-cursor'"
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(new_owner, lease["owner_id"])
        self.assertEqual("ACTIVE", lease["status"])

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
        self.assertLess(elapsed, 2.0, "bounded runtime must not sleep the configured five-second interval")

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
        self.assertLess(elapsed, 2.0, "bounded runtime must not sleep the configured five-second interval")


if __name__ == "__main__":
    unittest.main()
