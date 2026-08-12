from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_installer_is_limited_and_keeps_controller_and_watchdog_separate(self) -> None:
        installer = (REPO / "tools/install_unified_assistive_services.ps1").read_text(encoding="utf-8")
        self.assertIn("-RunLevel Limited", installer)
        self.assertIn("CONTROLLER_SERVICE_SYSTEM_IDENTITY_FORBIDDEN", installer)
        self.assertIn("BAS-UnifiedAssistiveController", installer)
        self.assertIn("BAS-UnifiedAssistiveWatchdog", installer)
        self.assertIn("Export-ScheduledTask", installer)
        self.assertIn("$requestedWhatIf = [bool]$WhatIfPreference", installer)
        self.assertIn("$WhatIfPreference = $false", installer)
        self.assertIn("cold_boot_without_user_logon = 'NOT_YET_PROVEN'", installer)


if __name__ == "__main__":
    unittest.main()
