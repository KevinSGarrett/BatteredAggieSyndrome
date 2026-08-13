from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from aggie_analytics.assistive_plane.controller_state import ControllerState, LeaderLock
from aggie_analytics.assistive_plane.service_runtime import (
    ControllerService,
    ControllerServiceConfig,
    WatchdogService,
    WatchdogServiceConfig,
)
from aggie_analytics.assistive_plane.watchdog import ReadOnlyWatchdog


REPO = Path(__file__).resolve().parents[1]


class UnifiedControllerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Path(self.temp.name) / "runtime"
        self.commit = "b" * 40

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_controller_holds_leader_writes_immutable_heartbeats_and_stops_cleanly(self) -> None:
        stop = threading.Event()
        service = ControllerService(
            ControllerServiceConfig(
                runtime_root=self.runtime,
                owner_id="test-owner",
                build_commit=self.commit,
                heartbeat_seconds=0.05,
                queue_evaluation_seconds=0.08,
                lease_ttl_seconds=2,
            )
        )
        result: list[dict[str, object]] = []
        errors: list[BaseException] = []

        def run() -> None:
            try:
                result.append(service.run(stop))
            except BaseException as exc:  # pragma: no cover - assertion surface
                errors.append(exc)

        thread = threading.Thread(target=run)
        thread.start()
        current = self.runtime / "evidence/current/controller-heartbeat.json"
        deadline = time.monotonic() + 3
        while not current.is_file() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(current.is_file())
        with self.assertRaisesRegex(RuntimeError, "CONTROLLER_LEADER_LOCK_HELD"):
            LeaderLock(self.runtime / "runtime/controller.lock").acquire()
        report = ReadOnlyWatchdog(self.runtime / "state/orchestrator.sqlite3").inspect()
        self.assertEqual("PASS", report["result"])
        payload = current.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        immutable = self.runtime / "evidence/controller-heartbeats/sha256" / digest / "report.json"
        self.assertEqual(payload, immutable.read_bytes())
        stop.set()
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors)
        self.assertEqual("GRACEFUL", result[0]["shutdown"])
        status = ControllerState(self.runtime / "state/orchestrator.sqlite3").status()
        self.assertIsNone(status["leader"])
        self.assertEqual(0, status["scheduler_cycles"])

    def test_independent_watchdog_emits_report_when_controller_is_stopped(self) -> None:
        state = ControllerState(self.runtime / "state/orchestrator.sqlite3")
        state.initialize()
        service = WatchdogService(
            WatchdogServiceConfig(runtime_root=self.runtime, build_commit=self.commit, interval_seconds=0.01)
        )
        result = service.run(threading.Event(), maximum_runtime_seconds=0)
        self.assertEqual(1, result["reports"])
        report = json.loads((self.runtime / "watchdog/current/watchdog-report.json").read_text(encoding="utf-8"))
        self.assertEqual("FAIL", report["result"])
        self.assertIn("CONTROLLER_LEADER_MISSING", report["findings"])
        self.assertEqual("INCOMPLETE", report["overall_operational_completion"])

    def test_service_rejects_invalid_build_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "CONTROLLER_BUILD_COMMIT_INVALID"):
            ControllerServiceConfig(self.runtime, "owner", "not-a-commit").validate()

    def test_zero_duration_bounded_run_still_emits_initial_heartbeat(self) -> None:
        service = ControllerService(
            ControllerServiceConfig(runtime_root=self.runtime, owner_id="test-owner", build_commit=self.commit)
        )
        result = service.run(threading.Event(), maximum_runtime_seconds=0)
        self.assertEqual(1, result["heartbeat_count"])
        self.assertTrue((self.runtime / "evidence/current/controller-heartbeat.json").is_file())

    def test_heartbeat_preserves_release_dispatch_truth_after_no_change_cycle(self) -> None:
        service = ControllerService(
            ControllerServiceConfig(runtime_root=self.runtime, owner_id="test-owner", build_commit=self.commit)
        )
        service.state.status = Mock(
            return_value={
                "scheduler_cycles": 2,
                "scheduler_dispatched_units": 3,
                "scheduler_provider_calls": 3,
                "release_scheduler_dispatched_units": 0,
                "release_scheduler_provider_calls": 0,
                "active_idle_intervals": 0,
                "journal_mode": "WAL",
                "integrity_check": "ok",
                "schema_version": 4,
            }
        )
        heartbeat = service._heartbeat_payload(
            started_at="2026-08-13T00:00:00Z",
            sequence=2,
            queue_evaluations=2,
            last_scheduler_evaluation={
                "result": "PASS_NO_CHANGE_ZERO_CALLS",
                "inventory_sha256": "a" * 64,
                "eligible_units": 0,
                "dispatched_units": 0,
                "provider_calls": 0,
                "dispatch_engine_state": "INVENTORY_SCHEDULER_ACTIVE_PROVIDER_DISPATCH_PENDING",
            },
        )
        self.assertEqual("INVENTORY_SCHEDULER_CONTROLLER_ROUTED_DISPATCH_ACTIVE", heartbeat["dispatch_engine_state"])
        self.assertEqual(0, heartbeat["release_scheduler_dispatched_units"])
        self.assertEqual(3, heartbeat["scheduler_provider_calls"])
        self.assertEqual(0, heartbeat["release_scheduler_provider_calls"])
        self.assertEqual(0, heartbeat["scheduler_latest_cycle_provider_calls"])
        blocked = service._heartbeat_payload(
            started_at="2026-08-13T00:00:00Z",
            sequence=3,
            queue_evaluations=3,
            last_scheduler_evaluation={
                "result": "FAIL",
                "dispatch_engine_state": "INVENTORY_SCHEDULER_BLOCKED",
            },
        )
        self.assertEqual("INVENTORY_SCHEDULER_BLOCKED", blocked["dispatch_engine_state"])

    def test_controller_records_runtime_failure_as_not_graceful(self) -> None:
        service = ControllerService(
            ControllerServiceConfig(
                runtime_root=self.runtime,
                owner_id="test-owner",
                build_commit=self.commit,
                heartbeat_seconds=0.05,
                queue_evaluation_seconds=0.08,
                lease_ttl_seconds=2,
            )
        )
        with patch.object(service.state, "heartbeat", side_effect=RuntimeError("INJECTED_FAILURE")):
            with self.assertRaisesRegex(RuntimeError, "INJECTED_FAILURE"):
                service.run(threading.Event())
        connection = service.state.connect()
        try:
            row = connection.execute(
                "SELECT payload_json FROM controller_events WHERE event_type='CONTROLLER_SERVICE_STOPPED' ORDER BY event_id DESC LIMIT 1"
            ).fetchone()
            self.assertFalse(json.loads(row[0])["graceful"])
        finally:
            connection.close()


class UnifiedReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = REPO / "tools/build_unified_assistive_release.py"
        spec = importlib.util.spec_from_file_location("build_unified_release", path)
        assert spec and spec.loader
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_minimal_release_is_hash_bound_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "releases"

            def fake_git(*arguments: str) -> str:
                return "c" * 40 if arguments == ("rev-parse", "HEAD") else ""

            with patch.object(self.module, "git", side_effect=fake_git):
                release, manifest = self.module.build_release(output, expected_commit="c" * 40)
                second_release, second_manifest = self.module.build_release(output, expected_commit="c" * 40)
            self.assertEqual(release, second_release)
            self.assertEqual(manifest["source_tree_sha256"], second_manifest["source_tree_sha256"])
            self.assertEqual(set(self.module.FILES), set(manifest["files"]))
            self.assertEqual("INCOMPLETE_UNTIL_DEPLOYED_AND_QUALIFIED", manifest["operational_completion"])
            package_init = release / "src/aggie_analytics/assistive_plane/__init__.py"
            self.assertEqual(
                "GENERATED_MINIMAL_PACKAGE_INITIALIZER",
                manifest["files"]["src/aggie_analytics/assistive_plane/__init__.py"]["source_kind"],
            )
            self.assertNotIn("dispatcher", package_init.read_text(encoding="utf-8"))
            unexpected = release / "src/aggie_analytics/assistive_plane/__pycache__/runtime.pyc"
            unexpected.parent.mkdir(parents=True)
            unexpected.write_bytes(b"reconstructible bytecode")
            with (
                patch.object(self.module, "git", side_effect=fake_git),
                self.assertRaisesRegex(RuntimeError, "IMMUTABLE_RELEASE_UNEXPECTED_FILE_SET"),
            ):
                self.module.build_release(output, expected_commit="c" * 40)
            unexpected.unlink()
            unexpected.parent.rmdir()
            runtime = Path(temporary) / "runtime"
            launched = subprocess.run(
                [
                    sys.executable,
                    str(release / "tools/run_unified_assistive_controller.py"),
                    "serve",
                    "--runtime-root",
                    str(runtime),
                    "--build-commit",
                    "c" * 40,
                    "--heartbeat-seconds",
                    "0.02",
                    "--queue-evaluation-seconds",
                    "0.03",
                    "--lease-ttl-seconds",
                    "2",
                    "--maximum-runtime-seconds",
                    "0.05",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(0, launched.returncode, launched.stderr)
            self.assertTrue((runtime / "evidence/current/controller-heartbeat.json").is_file())

    def test_installer_is_limited_and_keeps_controller_and_watchdog_separate(self) -> None:
        installer = (REPO / "tools/install_unified_assistive_services.ps1").read_text(encoding="utf-8")
        self.assertIn("-RunLevel Limited", installer)
        self.assertIn("CONTROLLER_SERVICE_SYSTEM_IDENTITY_FORBIDDEN", installer)
        self.assertIn("BAS-UnifiedAssistiveController", installer)
        self.assertIn("BAS-UnifiedAssistiveWatchdog", installer)
        self.assertIn("Export-ScheduledTask", installer)
        self.assertIn("$requestedWhatIf = [bool]$WhatIfPreference", installer)
        self.assertIn("$WhatIfPreference = $false", installer)
        self.assertIn("[ValidateSet('LocalService', 'InteractiveUser')]", installer)
        self.assertIn("New-ScheduledTaskTrigger -AtStartup", installer)
        self.assertIn("'NT AUTHORITY\\LOCAL SERVICE'", installer)
        self.assertIn("-LogonType ServiceAccount -RunLevel Limited", installer)
        self.assertIn("CONTROLLER_LOCAL_SERVICE_SIGNING_KEY_MISSING", installer)
        self.assertIn("$openrouterRoot", installer)
        self.assertIn("$cursorRoot", installer)
        self.assertIn("$localQwenRoot", installer)
        self.assertIn("CONTROLLER_LOCAL_SERVICE_ELEVATION_REQUIRED_BEFORE_MUTATION", installer)
        self.assertIn("'*S-1-5-19:(OI)(CI)RX'", installer)
        self.assertIn("'*S-1-5-19:(OI)(CI)M'", installer)
        self.assertIn("'*S-1-5-19:R'", installer)
        self.assertIn("STARTUP_CAPABLE_CONFIGURATION_BOOT_OBSERVATION_PENDING", installer)
        self.assertIn("CONTROLLER_RECOVERY_ACTION_IDENTITY_MISMATCH", installer)
        self.assertIn("CONTROLLER_RECOVERY_ACTION_PATH_MISMATCH", installer)
        self.assertIn("CONTROLLER_RECOVERY_ACTION_EXECUTABLE_MISMATCH", installer)
        self.assertIn("CONTROLLER_RECOVERY_ACTION_DIRECTORY_BUILD_MISMATCH", installer)
        self.assertIn("CONTROLLER_RECOVERY_BUILD_BINDING_MISMATCH", installer)
        self.assertIn("CONTROLLER_RECOVERY_OWNER_PROCESS_STILL_LIVE", installer)
        self.assertIn("CONTROLLER_RECOVERY_OWNER_PROCESS_MISSING_WHILE_TASK_RUNNING", installer)
        self.assertIn("CONTROLLER_RECOVERY_LEASE_MISSING_WHILE_TASK_RUNNING", installer)
        self.assertIn("RELEASE_FILE_SET_MISMATCH", installer)
        self.assertIn("$controllerArguments = '-B", installer)
        self.assertIn("$watchdogArguments = '-B", installer)
        self.assertIn("^(?:-B\\s+)?", installer)
        self.assertIn("CLEAN_SHUTDOWN_NO_LEASE", installer)
        self.assertIn("CLEAN_SHUTDOWN_RELEASED_LEASE", installer)
        self.assertIn("EXACT_ORPHAN_LEASE_RELEASED", installer)
        self.assertIn("CONTROLLER_RECOVERY_POST_STOP_LEASE_MISMATCH", installer)
        self.assertIn("service-state\\recovery-evidence\\sha256", installer)
        self.assertIn("CONTROLLER_RECOVERY_EVIDENCE_HASH_MISMATCH", installer)
        self.assertIn("recover-orphaned-lease", installer)
        self.assertIn("--expected-owner-id", installer)
        self.assertIn("--expected-build-commit", installer)
        self.assertIn("--expected-owner-pid", installer)
        self.assertIn("--recovery-evidence-sha256", installer)


class WatchdogCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = REPO / "tools/run_unified_assistive_watchdog.py"
        spec = importlib.util.spec_from_file_location("run_unified_assistive_watchdog", path)
        assert spec and spec.loader
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_inspect_enables_full_operational_audit_and_release_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "assistive" / "orchestrator-v3"
            expected_commit = "d" * 40
            inspector = Mock()
            inspector.inspect.return_value = {"result": "FAIL", "findings": ["ELIGIBLE_UNITS_IDLING"]}
            with (
                patch.object(self.module, "ReadOnlyWatchdog", return_value=inspector) as watchdog,
                patch.object(self.module, "commit_identity", return_value=expected_commit),
                patch.object(
                    sys,
                    "argv",
                    [
                        "run_unified_assistive_watchdog.py",
                        "inspect",
                        "--runtime-root",
                        str(runtime),
                    ],
                ),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(1, self.module.main())
            watchdog.assert_called_once_with(
                runtime / "state" / "orchestrator.sqlite3",
                90,
                inventory_path=runtime.parent / "inventory" / "current" / "inventory.json",
                scheduler_report_path=runtime / "evidence" / "current" / "scheduler-evaluation.json",
                expected_build_commit=expected_commit,
            )


if __name__ == "__main__":
    unittest.main()
