from __future__ import annotations

import hashlib
import importlib.util
import inspect
import io
import json
import os
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
from aggie_analytics.assistive_plane.live_service import evaluate_live_service
from aggie_analytics.assistive_plane.service_runtime import (
    ControllerService,
    ControllerServiceConfig,
    WatchdogService,
    WatchdogServiceConfig,
    atomic_write,
    canonical_json_bytes,
)
from aggie_analytics.assistive_plane.watchdog import ReadOnlyWatchdog


REPO = Path(__file__).resolve().parents[1]


class UnifiedControllerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Path(self.temp.name) / "runtime"
        self.commit = "b" * 40

    def test_atomic_write_retries_transient_windows_replace_denial(self) -> None:
        destination = self.runtime / "evidence/current/heartbeat.json"
        original_replace = Path.replace
        attempts = 0

        def transient_denial(source: Path, target: Path) -> Path:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise PermissionError("simulated Windows sharing violation")
            return original_replace(source, target)

        with patch.object(Path, "replace", autospec=True, side_effect=transient_denial):
            atomic_write(destination, b"heartbeat\n")
        self.assertEqual(3, attempts)
        self.assertEqual(b"heartbeat\n", destination.read_bytes())

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

    def test_watchdog_default_and_cycle_wait_preserve_five_minute_freshness(self) -> None:
        config = WatchdogServiceConfig(runtime_root=self.runtime, build_commit=self.commit)
        self.assertEqual(240.0, config.interval_seconds)
        self.assertEqual(
            300,
            inspect.signature(evaluate_live_service)
            .parameters["watchdog_max_age_seconds"]
            .default,
        )
        self.assertEqual(
            139.0,
            WatchdogService._remaining_cycle_wait(240.0, 100.0, 201.0),
        )
        self.assertEqual(
            0.0,
            WatchdogService._remaining_cycle_wait(240.0, 100.0, 350.0),
        )

    def test_watchdog_acknowledges_stop_request_without_waiting_full_interval(self) -> None:
        request = {
            "artifact_type": "UNIFIED_ASSISTIVE_SERVICE_STOP_REQUEST",
            "build_commit": self.commit,
            "request_id": "b" * 32,
            "requested_at": "2026-08-13T00:00:00Z",
            "role": "watchdog",
            "schema_version": 1,
        }
        data = canonical_json_bytes(request)
        atomic_write(self.runtime / "control/watchdog-stop.json", data)
        service = WatchdogService(
            WatchdogServiceConfig(runtime_root=self.runtime, build_commit=self.commit, interval_seconds=300)
        )
        started = time.monotonic()
        result = service.run(threading.Event(), maximum_runtime_seconds=2)
        digest = hashlib.sha256(data).hexdigest()
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(0, result["reports"])
        self.assertEqual(
            data,
            (self.runtime / "control/acknowledged/watchdog/sha256" / digest / "request.json").read_bytes(),
        )

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

    def test_controller_acknowledges_exact_build_stop_request_and_releases_leader(self) -> None:
        request = {
            "artifact_type": "UNIFIED_ASSISTIVE_SERVICE_STOP_REQUEST",
            "build_commit": self.commit,
            "request_id": "a" * 32,
            "requested_at": "2026-08-13T00:00:00Z",
            "role": "controller",
            "schema_version": 1,
        }
        data = canonical_json_bytes(request)
        atomic_write(self.runtime / "control/controller-stop.json", data)
        service = ControllerService(
            ControllerServiceConfig(runtime_root=self.runtime, owner_id="test-owner", build_commit=self.commit)
        )
        result = service.run(threading.Event(), maximum_runtime_seconds=2)
        digest = hashlib.sha256(data).hexdigest()
        self.assertEqual("GRACEFUL", result["shutdown"])
        self.assertFalse((self.runtime / "control/controller-stop.json").exists())
        self.assertEqual(
            data,
            (self.runtime / "control/acknowledged/controller/sha256" / digest / "request.json").read_bytes(),
        )
        self.assertIsNone(ControllerState(self.runtime / "state/orchestrator.sqlite3").status()["leader"])

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

    def test_heartbeat_continues_while_inventory_evaluation_is_slow(self) -> None:
        service = ControllerService(
            ControllerServiceConfig(
                runtime_root=self.runtime,
                owner_id="test-owner",
                build_commit=self.commit,
                heartbeat_seconds=0.03,
                queue_evaluation_seconds=0.02,
                lease_ttl_seconds=2,
            )
        )

        refresh_entered = threading.Event()
        release_refresh = threading.Event()
        stop = threading.Event()

        def slow_refresh():
            refresh_entered.set()
            release_refresh.wait(timeout=2)
            return {"result": "PASS", "snapshot_sha256": "a" * 64}

        results: list[dict[str, object]] = []
        with (
            patch.object(service.inventory_refresher, "refresh", side_effect=slow_refresh),
            patch.object(
                service.scheduler,
                "evaluate",
                return_value={"result": "PASS_NO_CHANGE_ZERO_CALLS", "provider_calls": 0},
            ),
        ):
            thread = threading.Thread(target=lambda: results.append(service.run(stop)))
            thread.start()
            self.assertTrue(refresh_entered.wait(timeout=3))
            time.sleep(0.16)
            heartbeat = json.loads(
                (self.runtime / "evidence/current/controller-heartbeat.json").read_text(encoding="utf-8")
            )
            release_refresh.set()
            stop.set()
            thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertGreaterEqual(heartbeat["heartbeat_sequence"], 2)
        self.assertGreaterEqual(results[0]["heartbeat_count"], 2)


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
        self.assertIn("-AllowStartIfOnBatteries", installer)
        self.assertIn("-DontStopIfGoingOnBatteries", installer)
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
        self.assertIn("& $python -B $controllerScript status", installer)
        self.assertIn("& $python -B $controllerScript recover-orphaned-lease", installer)
        self.assertNotIn("& $python $controllerScript", installer)
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
        self.assertIn("launch_unified_assistive_service.py", installer)
        self.assertIn("activate_unified_assistive_release.py", installer)
        self.assertIn("--role controller", installer)
        self.assertIn("--role watchdog", installer)
        self.assertIn("future_release_switch_elevation_required = $false", installer)
        self.assertIn("STABLE_LAUNCHER_ACL_FAILED", installer)
        self.assertIn("'*S-1-5-19:RX'", installer)

    def test_non_elevated_switch_never_registers_or_elevates_tasks(self) -> None:
        switcher = (REPO / "tools/switch_unified_assistive_services.ps1").read_text(encoding="utf-8")
        self.assertIn("activate_unified_assistive_release.py", switcher)
        self.assertIn("Start-ScheduledTask", switcher)
        self.assertIn("task_registration_performed = $false", switcher)
        self.assertIn("rollback_available = [bool]$previousPointer", switcher)
        self.assertIn("$failedPointerBackup = Join-Path", switcher)
        self.assertIn(
            "[System.IO.File]::Replace($rollback, $pointerPath, $failedPointerBackup)",
            switcher,
        )
        self.assertNotIn("[System.IO.File]::Replace($rollback, $pointerPath, $null)", switcher)
        self.assertIn("RELEASE_POINTER_ROLLBACK_VERIFICATION_FAILED", switcher)
        self.assertNotIn("Register-ScheduledTask", switcher)
        self.assertNotIn("Stop-ScheduledTask", switcher)
        self.assertNotIn("Start-Process", switcher)
        self.assertNotIn("RunAs", switcher)
        self.assertIn("UNIFIED_ASSISTIVE_SERVICE_STOP_REQUEST", switcher)
        self.assertIn("SERVICE_STOP_ACKNOWLEDGEMENT_MISSING", switcher)
        self.assertIn(
            "while (-not (Test-Path -LiteralPath $acknowledgements[$role] -PathType Leaf))",
            switcher,
        )
        self.assertIn("if ((Get-Date) -ge $deadline)", switcher)
        self.assertIn("POST_STOP_CONTROLLER_LEADER_REMAINS", switcher)
        self.assertIn("$GracefulStopTimeoutSeconds = 90", switcher)
        self.assertIn("AddSeconds($GracefulStopTimeoutSeconds)", switcher)


class StableServiceLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        launcher_path = REPO / "tools/launch_unified_assistive_service.py"
        launcher_spec = importlib.util.spec_from_file_location("stable_launcher_tests", launcher_path)
        assert launcher_spec and launcher_spec.loader
        cls.launcher = importlib.util.module_from_spec(launcher_spec)
        launcher_spec.loader.exec_module(cls.launcher)
        activator_path = REPO / "tools/activate_unified_assistive_release.py"
        activator_spec = importlib.util.spec_from_file_location("stable_activator_tests", activator_path)
        assert activator_spec and activator_spec.loader
        cls.activator = importlib.util.module_from_spec(activator_spec)
        activator_spec.loader.exec_module(cls.activator)

    def make_release(self, root: Path, commit: str = "e" * 40) -> Path:
        release = root / "releases" / commit
        files: dict[str, dict[str, object]] = {}
        for relative in (
            "tools/run_unified_assistive_controller.py",
            "tools/run_unified_assistive_watchdog.py",
        ):
            path = release / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("print('service')\n", encoding="utf-8")
            files[relative] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
                "source_kind": "TEST",
            }
        manifest = {
            "schema_version": 1,
            "artifact_type": "UNIFIED_ASSISTIVE_CONTROLLER_RELEASE",
            "build_commit": commit,
            "source_tree_sha256": "f" * 64,
            "files": files,
        }
        (release / "RELEASE_MANIFEST.json").write_text(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        return release

    def test_activation_and_validation_bind_exact_content_addressed_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "runtime"
            runtime.mkdir()
            release = self.make_release(runtime)
            result = self.activator.activate(runtime, release)
            validated_release, manifest = self.launcher.validate_release(runtime)
            self.assertEqual(release.resolve(), validated_release)
            self.assertEqual("e" * 40, manifest["build_commit"])
            pointer = runtime / "deployment/current-release.json"
            self.assertEqual(result["pointer_sha256"], hashlib.sha256(pointer.read_bytes()).hexdigest())
            immutable = Path(result["immutable_pointer_path"])
            self.assertEqual(pointer.read_bytes(), immutable.read_bytes())

    def test_tampered_release_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "runtime"
            runtime.mkdir()
            release = self.make_release(runtime)
            self.activator.activate(runtime, release)
            (release / "tools/run_unified_assistive_controller.py").write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "RELEASE_FILE_IDENTITY_MISMATCH"):
                self.launcher.validate_release(runtime)

    def test_pointer_path_escape_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "runtime"
            runtime.mkdir()
            release = self.make_release(runtime)
            self.activator.activate(runtime, release)
            pointer_path = runtime / "deployment/current-release.json"
            pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
            outside = Path(temporary) / "outside"
            outside.mkdir()
            pointer["release_root"] = str(outside)
            pointer_path.write_text(json.dumps(pointer), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "RELEASE_POINTER_PATH_INVALID"):
                self.launcher.validate_release(runtime)

    def test_launch_execs_only_the_role_bound_script(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "runtime"
            runtime.mkdir()
            release = self.make_release(runtime)
            self.activator.activate(runtime, release)
            with patch.object(self.launcher.subprocess, "run", return_value=Mock(returncode=0)) as execute:
                result = self.launcher.launch("controller", runtime)
            arguments = execute.call_args.args[0]
            self.assertTrue(os.path.samefile(release / "tools/run_unified_assistive_controller.py", arguments[2]))
            self.assertIn("--build-commit", arguments)
            self.assertNotIn("run_unified_assistive_watchdog.py", " ".join(arguments))
            self.assertEqual(0, result["child_exit_code"])

    def test_launcher_remains_attached_and_propagates_child_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "runtime"
            runtime.mkdir()
            release = self.make_release(runtime)
            self.activator.activate(runtime, release)
            with patch.object(self.launcher.subprocess, "run", return_value=Mock(returncode=17)):
                with self.assertRaisesRegex(RuntimeError, "SERVICE_CHILD_EXITED:17"):
                    self.launcher.launch("watchdog", runtime)


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
