from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aggie_analytics.assistive_plane.contracts import canonical_json_bytes
from aggie_analytics.assistive_plane.cpu_worker_backend import (
    CpuWorkerEndpoint,
    CpuWorkerIdentity,
    CpuWorkerJob,
    execute_cpu_request,
    execute_cpu_task,
    verify_cpu_response,
)
from tools.cpu_worker_service import BoundedWorkerServer, WorkerRuntime, handler


KEY = b"k" * 32
NOW = datetime(2026, 8, 12, 19, 30, tzinfo=timezone.utc)


class CpuWorkerBackendTests(unittest.TestCase):
    def test_installer_uses_current_noninteractive_tailscale_cli(self) -> None:
        installer = (Path(__file__).resolve().parents[1] / "tools" / "install_cpu_worker_service.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("tailscale funnel reset", installer)
        self.assertIn("tailscale serve --bg --yes --https=443", installer)
        self.assertNotIn("tailscale funnel 443 off", installer)

    def test_installer_uses_manifest_bound_worker_owned_python_runtime(self) -> None:
        installer = (Path(__file__).resolve().parents[1] / "tools" / "install_cpu_worker_service.ps1").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("Get-Command python", installer)
        self.assertIn("runtime_manifest.csv", installer)
        self.assertIn("CPU_WORKER_RUNTIME_MANIFEST_COVERAGE_MISMATCH", installer)
        self.assertIn("CPU_WORKER_RUNTIME_UNMANIFESTED_FILE", installer)
        self.assertIn("CPU_WORKER_RUNTIME_HASH_MISMATCH", installer)
        self.assertIn("CPU_WORKER_RUNTIME_VERSION_MISMATCH", installer)
        self.assertIn("CPU_WORKER_RUNTIME_ARCHITECTURE_MISMATCH", installer)
        self.assertIn("runtime\\python.exe", installer)
        self.assertIn("New-ScheduledTaskAction -Execute $runtimePythonInstalled", installer)
        self.assertIn("LOCAL SERVICE:(OI)(CI)RX", installer)
        self.assertNotIn("[IO.Path]::GetRelativePath", installer)
        self.assertNotIn("AppData", installer)

    def test_worker_identity_requires_exact_stable_node(self) -> None:
        CpuWorkerIdentity(
            "comfy-v4-cpu-01.tail9b05ab.ts.net",
            "windows",
            True,
            node_id="nUxabVWSHb11CNTRL",
        ).validate()
        with self.assertRaisesRegex(ValueError, "CPU_WORKER_NODE_ID_MISMATCH"):
            CpuWorkerIdentity(
                "comfy-v4-cpu-01.tail9b05ab.ts.net",
                "windows",
                True,
                node_id="different-node",
            ).validate()

    def test_endpoint_requires_private_magicdns_https(self) -> None:
        CpuWorkerEndpoint("https://comfy-v4-cpu-01.tail9b05ab.ts.net").validate()
        for endpoint in [
            "http://comfy-v4-cpu-01.tail9b05ab.ts.net:8765",
            "https://other.tail9b05ab.ts.net",
            "https://comfy-v4-cpu-01.tail9b05ab.ts.net:8765",
            "https://comfy-v4-cpu-01.tail9b05ab.ts.net/path",
        ]:
            with self.assertRaises(ValueError):
                CpuWorkerEndpoint(endpoint).validate()

    def request(self, *, nonce: str = "n" * 32, issued: datetime = NOW) -> dict[str, object]:
        return CpuWorkerJob("CANONICAL_JSON", {"value": {"b": 2, "a": 1}}, "BAT-563").request(
            KEY, issued_at=issued, nonce=nonce
        )

    def test_signed_job_identity_and_response_are_stable(self) -> None:
        job = CpuWorkerJob("CANONICAL_JSON", {"value": {"b": 2, "a": 1}}, "BAT-563")
        self.assertEqual(job.identity(), CpuWorkerJob("CANONICAL_JSON", {"value": {"a": 1, "b": 2}}, "BAT-563").identity())
        request = self.request()
        response = execute_cpu_request(request, KEY, now=NOW)
        verify_cpu_response(response, request, KEY)
        self.assertEqual(response["canonical_writes"], 0)
        self.assertEqual(response["protected_decisions"], 0)
        self.assertEqual(response["result"]["canonical_json"], '{"a":1,"b":2}')

    def test_invalid_signature_expiry_and_replay_inconsistency_fail_closed(self) -> None:
        request = self.request()
        request["signature"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "CPU_WORKER_SIGNATURE_INVALID"):
            execute_cpu_request(request, KEY, now=NOW)
        expired = self.request(issued=NOW - timedelta(hours=1))
        with self.assertRaisesRegex(ValueError, "CPU_WORKER_REQUEST_EXPIRED"):
            execute_cpu_request(expired, KEY, now=NOW)
        registry: dict[str, str] = {}
        original = self.request(nonce="r" * 32)
        execute_cpu_request(original, KEY, now=NOW, replay_registry=registry)
        duplicate = dict(original)
        duplicate["issued_at_utc"] = (NOW - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
        unsigned = {key: value for key, value in duplicate.items() if key != "signature"}
        import hashlib, hmac
        duplicate["signature"] = hmac.new(KEY, canonical_json_bytes(unsigned), hashlib.sha256).hexdigest()
        with self.assertRaisesRegex(ValueError, "CPU_WORKER_REPLAY_INCONSISTENT"):
            execute_cpu_request(duplicate, KEY, now=NOW, replay_registry=registry)

    def test_identity_authority_payload_and_task_fail_closed(self) -> None:
        request = self.request()
        request["job_id"] = "0" * 64
        unsigned = {key: value for key, value in request.items() if key != "signature"}
        import hashlib, hmac
        request["signature"] = hmac.new(KEY, canonical_json_bytes(unsigned), hashlib.sha256).hexdigest()
        with self.assertRaisesRegex(ValueError, "CPU_WORKER_REQUEST_IDENTITY_MISMATCH"):
            execute_cpu_request(request, KEY, now=NOW)
        with self.assertRaisesRegex(ValueError, "CPU_WORKER_TASK_NOT_ALLOWED"):
            CpuWorkerJob("SHELL", {"command": "whoami"}, "BAT-563")
        with self.assertRaisesRegex(ValueError, "CPU_WORKER_DEDUP_RECORD_INVALID"):
            execute_cpu_task("EXACT_TEXT_DEDUP", {"records": [{"path": "C:/"}]})

    def test_runtime_rejects_path_like_job_identity_before_filesystem_use(self) -> None:
        with TemporaryDirectory() as temporary:
            request = self.request()
            request["job_id"] = ("../" * 21) + "."
            with self.assertRaisesRegex(ValueError, "CPU_WORKER_RUNTIME_IDENTITY_INVALID"):
                WorkerRuntime(Path(temporary), KEY).execute(request)
            self.assertEqual([], list(Path(temporary).rglob("*.json")))

    def test_startup_recovers_interrupted_leases_and_orphan_scratch(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = WorkerRuntime(root, KEY)
            interrupted_digest = "a" * 64
            orphan_digest = "b" * 64
            invalid_digest = "not-a-digest"
            lease = root / "runtime" / "leases" / f"{interrupted_digest}.json"
            lease.parent.mkdir(parents=True)
            lease.write_text(json.dumps({"job_id": "c" * 64, "envelope_sha256": interrupted_digest}), encoding="utf-8")
            interrupted_scratch = root / "runtime" / "scratch" / interrupted_digest
            interrupted_scratch.mkdir(parents=True)
            (interrupted_scratch / "partial.bin").write_bytes(b"partial")
            orphan_scratch = root / "runtime" / "scratch" / orphan_digest
            orphan_scratch.mkdir(parents=True)
            (orphan_scratch / "partial.bin").write_bytes(b"orphan")
            invalid_scratch = root / "runtime" / "scratch" / invalid_digest
            invalid_scratch.mkdir(parents=True)
            self.assertEqual(2, runtime.recover_interrupted_jobs())
            self.assertFalse(lease.exists())
            self.assertFalse(interrupted_scratch.exists())
            self.assertFalse(orphan_scratch.exists())
            self.assertTrue(invalid_scratch.exists())
            recovery_events = list((root / "runtime" / "recovery").rglob("*.json"))
            self.assertEqual(2, len(recovery_events))
            event_names = {json.loads(path.read_text(encoding="utf-8"))["event"] for path in recovery_events}
            self.assertEqual({"INTERRUPTED_JOB_RECOVERY", "ORPHAN_SCRATCH_RECOVERY"}, event_names)
            self.assertEqual(0, runtime.recover_interrupted_jobs())

    def test_replace_stops_existing_task_before_preserving_install_root(self) -> None:
        installer = (Path(__file__).resolve().parents[1] / "tools" / "install_cpu_worker_service.ps1").read_text(
            encoding="utf-8"
        )
        stop_position = installer.index("Stop-ScheduledTask -TaskName $taskName")
        move_position = installer.index("Move-Item -LiteralPath $InstallRoot -Destination $recovery")
        self.assertLess(stop_position, move_position)
        self.assertIn("CPU_WORKER_EXISTING_TASK_STOP_TIMEOUT", installer)

    def test_deterministic_tasks(self) -> None:
        payload = {"lines": ["BAT-563", "worker", "candidate-only"]}
        self.assertEqual(execute_cpu_task("LINE_HASH_MANIFEST", payload), execute_cpu_task("LINE_HASH_MANIFEST", payload))
        result = execute_cpu_task("EXACT_TEXT_DEDUP", {"records": [
            {"id": "b", "text": "  Texas A&M   Aggies"},
            {"id": "a", "text": "texas a&m aggies"},
            {"id": "c", "text": "Texas Aggies"},
        ]})
        self.assertEqual(result["unique_normalized_count"], 2)
        self.assertIn(["a", "b"], [group["record_ids"] for group in result["groups"]])

    def test_loopback_service_requires_tailscale_serve_identity_and_hmac(self) -> None:
        with TemporaryDirectory() as temporary:
            server = BoundedWorkerServer(("127.0.0.1", 0), handler(
                signing_key=KEY,
                storage_root=Path(temporary),
                expected_user_login="coordinator@example.test",
            ))
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                request_payload = CpuWorkerJob(
                    "CANONICAL_JSON", {"value": {"b": 2, "a": 1}}, "BAT-563"
                ).request(KEY, nonce="s" * 32)
                request = Request(
                    f"http://127.0.0.1:{server.server_port}/v2/jobs",
                    data=canonical_json_bytes(request_payload),
                    headers={"Content-Type": "application/json", "Tailscale-User-Login": "coordinator@example.test"},
                    method="POST",
                )
                with urlopen(request, timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                verify_cpu_response(payload, request_payload, KEY)
                first_files = sorted(path.relative_to(temporary).as_posix() for path in Path(temporary).rglob("*.json"))
                self.assertTrue(any(path.startswith("results/") for path in first_files))
                self.assertTrue(any(path.startswith("runtime/nonces/") for path in first_files))
                self.assertTrue(any(path.startswith("runtime/replays/") for path in first_files))
                self.assertFalse(any(path.startswith("runtime/leases/") for path in first_files))
                self.assertFalse(any(path.startswith("runtime/scratch/") for path in first_files))
                with urlopen(request, timeout=2) as response:
                    replay = json.loads(response.read().decode("utf-8"))
                self.assertEqual(payload, replay)
                replay_files = sorted(path.relative_to(temporary).as_posix() for path in Path(temporary).rglob("*.json"))
                self.assertEqual(first_files, replay_files)
                with self.assertRaises(HTTPError) as caught:
                    urlopen(f"http://127.0.0.1:{server.server_port}/health", timeout=2)
                self.assertEqual(caught.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
