from __future__ import annotations

import json
import importlib.util
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aggie_analytics.assistive_plane.controller_state import ControllerState
from aggie_analytics.assistive_plane.live_service import evaluate_live_service


ROOT = Path(__file__).resolve().parents[1]


class UnifiedLiveServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.runtime = Path(self.temporary.name) / "runtime"
        self.release = Path(self.temporary.name) / ("a" * 40)
        self.now = datetime(2026, 8, 13, tzinfo=timezone.utc)
        files = {"worker.py": {"bytes": 0, "sha256": ""}}
        (self.release / "worker.py").parent.mkdir(parents=True)
        (self.release / "worker.py").write_text("x\n", encoding="utf-8")
        import hashlib

        files["worker.py"]["bytes"] = (self.release / "worker.py").stat().st_size
        files["worker.py"]["sha256"] = hashlib.sha256((self.release / "worker.py").read_bytes()).hexdigest()
        (self.release / "RELEASE_MANIFEST.json").write_text(
            json.dumps({"build_commit": "a" * 40, "source_tree_sha256": "b" * 64, "files": files}),
            encoding="utf-8",
        )
        state = ControllerState(self.runtime / "state/orchestrator.sqlite3")
        state.initialize()
        state.acquire_leader("owner", "a" * 40, now=self.now)
        heartbeat = {
            "observed_at": self.now.isoformat().replace("+00:00", "Z"),
            "owner_id": "owner",
            "build_commit": "a" * 40,
            "dispatch_engine_state": "NOT_IMPLEMENTED_IN_THIS_ATOMIC_UNIT",
            "queue_evaluation_observations": 1,
        }
        watchdog = {
            "observed_at": self.now.isoformat().replace("+00:00", "Z"),
            "result": "PASS",
            "controller_alive": True,
            "controller_build_commit": "a" * 40,
            "watchdog_build_commit": "a" * 40,
        }
        for relative, payload in (
            ("evidence/current/controller-heartbeat.json", heartbeat),
            ("watchdog/current/watchdog-report.json", watchdog),
        ):
            path = self.runtime / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def tasks(self) -> list[dict[str, object]]:
        common = {
            "state": "Running",
            "enabled": True,
            "principal": "NT AUTHORITY\\LOCAL SERVICE",
            "run_level": "Limited",
            "logon_type": "ServiceAccount",
            "trigger_types": ["MSFT_TaskBootTrigger"],
            "execute": "python.exe",
            "arguments": f"serve --build-commit {'a' * 40}",
            "working_directory": str(self.release),
            "last_task_result": 267009,
        }
        return [
            {"task_name": "BAS-UnifiedAssistiveController", **common},
            {"task_name": "BAS-UnifiedAssistiveWatchdog", **common},
        ]

    def test_healthy_service_shell_is_not_operational_scheduler(self) -> None:
        report = evaluate_live_service(runtime_root=self.runtime, tasks=self.tasks(), now=self.now)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual("DEPLOYED_HEALTHY", report["service_shell_state"])
        self.assertFalse(report["scheduler"]["operational"])
        self.assertEqual(0, report["scheduler"]["real_cycles"])
        self.assertEqual("INCOMPLETE", report["overall_operational_completion"])
        self.assertEqual(
            "STARTUP_CAPABLE_NONINTERACTIVE_RUNTIME_VERIFIED_BOOT_OBSERVATION_PENDING",
            report["cold_boot_without_user_logon"],
        )

    def test_stale_heartbeat_or_system_principal_fails_capture(self) -> None:
        tasks = self.tasks()
        tasks[0]["principal"] = "NT AUTHORITY\\SYSTEM"
        report = evaluate_live_service(runtime_root=self.runtime, tasks=tasks, now=self.now + timedelta(seconds=91))
        self.assertEqual("FAIL", report["result"])
        self.assertIn("SERVICE_TASK_PRINCIPAL_INVALID:BAS-UnifiedAssistiveController", report["findings"])
        self.assertIn("SERVICE_CONTROLLER_HEARTBEAT_STALE", report["findings"])

    def test_interactive_logon_or_missing_boot_trigger_fails_capture(self) -> None:
        tasks = self.tasks()
        tasks[0]["principal"] = "kevin"
        tasks[0]["logon_type"] = "Interactive"
        tasks[0]["trigger_types"] = ["MSFT_TaskLogonTrigger"]
        report = evaluate_live_service(runtime_root=self.runtime, tasks=tasks, now=self.now)
        self.assertEqual("FAIL", report["result"])
        self.assertIn("SERVICE_TASK_PRINCIPAL_INVALID:BAS-UnifiedAssistiveController", report["findings"])
        self.assertIn("SERVICE_TASK_NOT_NONINTERACTIVE:BAS-UnifiedAssistiveController", report["findings"])
        self.assertIn("SERVICE_TASK_STARTUP_TRIGGER_MISSING:BAS-UnifiedAssistiveController", report["findings"])

    def test_watchdog_operational_failure_does_not_erase_structural_health(self) -> None:
        path = self.runtime / "watchdog/current/watchdog-report.json"
        watchdog = json.loads(path.read_text(encoding="utf-8"))
        watchdog.update(
            {
                "result": "FAIL",
                "structural_result": "PASS",
                "operational_result": "FAIL",
                "operational_findings": ["ELIGIBLE_UNITS_IDLING"],
            }
        )
        path.write_text(json.dumps(watchdog), encoding="utf-8")
        report = evaluate_live_service(runtime_root=self.runtime, tasks=self.tasks(), now=self.now)
        self.assertEqual("PASS", report["result"], report)
        self.assertEqual("DEPLOYED_HEALTHY", report["service_shell_state"])
        self.assertEqual("FAIL", report["watchdog"]["operational_result"])

    def test_inventory_cycles_without_dispatch_do_not_make_scheduler_operational(self) -> None:
        state = ControllerState(self.runtime / "state/orchestrator.sqlite3")
        state.record_cycle(
            cycle_id="cycle-1",
            inventory_sha256="c" * 64,
            eligible_units=1,
            dispatched_units=0,
            no_change=False,
            result="INCOMPLETE_IDLE_WITH_READY_WORK",
            now=self.now,
        )
        report = evaluate_live_service(runtime_root=self.runtime, tasks=self.tasks(), now=self.now)
        self.assertEqual(1, report["scheduler"]["real_cycles"])
        self.assertEqual(0, report["scheduler"]["dispatched_units"])
        self.assertFalse(report["scheduler"]["operational"])

    def test_completeness_derives_deployed_shell_without_scheduler_claim(self) -> None:
        capture = evaluate_live_service(runtime_root=self.runtime, tasks=self.tasks(), now=self.now)
        capture_path = Path(self.temporary.name) / "capture.json"
        capture_path.write_text(json.dumps(capture), encoding="utf-8")
        spec = importlib.util.spec_from_file_location(
            "validate_unified_assistive_completeness",
            ROOT / "tools/validate_unified_assistive_completeness.py",
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        states, evidence = module.derive_states(ROOT, capture_path)
        self.assertEqual("SERVICE_SHELL_DEPLOYED_SCHEDULER_NOT_OPERATIONAL", states["unified_plane"])
        self.assertTrue(evidence["controller_os_supervision_verified"])
        self.assertTrue(evidence["watchdog_os_supervision_verified"])
        self.assertFalse(evidence["scheduler_operational"])


if __name__ == "__main__":
    unittest.main()
