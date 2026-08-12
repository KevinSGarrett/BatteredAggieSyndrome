from __future__ import annotations

import json
import unittest
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aggie_analytics.assistive_plane.cpu_worker_backend import (
    CpuWorkerEndpoint,
    CpuWorkerJob,
    execute_cpu_request,
    execute_cpu_task,
)
from aggie_analytics.assistive_plane.contracts import canonical_json_bytes
from tools.cpu_worker_service import handler


class CpuWorkerBackendTests(unittest.TestCase):
    def test_endpoint_is_exact_private_worker(self) -> None:
        CpuWorkerEndpoint("http://comfy-v4-cpu-01.tail9b05ab.ts.net:8765").validate()
        for endpoint in [
            "http://0.0.0.0:8765",
            "https://comfy-v4-cpu-01.tail9b05ab.ts.net:8765",
            "http://comfy-v4-cpu-01.tail9b05ab.ts.net:8000",
            "http://comfy-v4-cpu-01.tail9b05ab.ts.net:8765/path",
        ]:
            with self.assertRaises(ValueError):
                CpuWorkerEndpoint(endpoint).validate()

    def test_job_identity_and_request_are_stable(self) -> None:
        job = CpuWorkerJob("CANONICAL_JSON", {"value": {"b": 2, "a": 1}}, "BAT-563")
        self.assertEqual(job.identity(), CpuWorkerJob("CANONICAL_JSON", {"value": {"a": 1, "b": 2}}, "BAT-563").identity())
        response = execute_cpu_request(job.request())
        self.assertEqual(response["canonical_writes"], 0)
        self.assertEqual(response["protected_decisions"], 0)
        self.assertEqual(response["result"]["canonical_json"], '{"a":1,"b":2}')

    def test_request_identity_and_authority_fail_closed(self) -> None:
        request = CpuWorkerJob("LINE_HASH_MANIFEST", {"lines": ["a"]}, "BAT-563").request()
        request["request_id"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "CPU_WORKER_REQUEST_IDENTITY_MISMATCH"):
            execute_cpu_request(request)
        request = CpuWorkerJob("LINE_HASH_MANIFEST", {"lines": ["a"]}, "BAT-563").request()
        request["authority"] = "CANONICAL_WRITE"
        with self.assertRaisesRegex(ValueError, "CPU_WORKER_AUTHORITY_INVALID"):
            execute_cpu_request(request)

    def test_line_manifest_is_byte_stable(self) -> None:
        payload = {"lines": ["BAT-563", "worker", "candidate-only"]}
        self.assertEqual(execute_cpu_task("LINE_HASH_MANIFEST", payload), execute_cpu_task("LINE_HASH_MANIFEST", payload))

    def test_exact_dedup_is_deterministic_and_ordered(self) -> None:
        result = execute_cpu_task("EXACT_TEXT_DEDUP", {"records": [
            {"id": "b", "text": "  Texas A&M   Aggies"},
            {"id": "a", "text": "texas a&m aggies"},
            {"id": "c", "text": "Texas Aggies"},
        ]})
        self.assertEqual(result["record_count"], 3)
        self.assertEqual(result["unique_normalized_count"], 2)
        self.assertIn(["a", "b"], [group["record_ids"] for group in result["groups"]])

    def test_arbitrary_tasks_and_record_shapes_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "CPU_WORKER_TASK_NOT_ALLOWED"):
            CpuWorkerJob("SHELL", {"command": "whoami"}, "BAT-563")
        with self.assertRaisesRegex(ValueError, "CPU_WORKER_DEDUP_RECORD_INVALID"):
            execute_cpu_task("EXACT_TEXT_DEDUP", {"records": [{"path": "C:/"}]})

    def test_http_service_allows_only_exact_controller_and_fixed_request(self) -> None:
        with TemporaryDirectory() as temporary:
            server = HTTPServer(("127.0.0.1", 0), handler(controller_ip="127.0.0.1", storage_root=Path(temporary)))
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                job = CpuWorkerJob("CANONICAL_JSON", {"value": {"b": 2, "a": 1}}, "BAT-563")
                request = Request(
                    f"http://127.0.0.1:{server.server_port}/v1/jobs",
                    data=canonical_json_bytes(job.request()),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(payload, execute_cpu_request(job.request()))
                self.assertEqual(len(list(Path(temporary).rglob("*.json"))), 1)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

        with TemporaryDirectory() as temporary:
            server = HTTPServer(("127.0.0.1", 0), handler(controller_ip="100.79.129.63", storage_root=Path(temporary)))
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with self.assertRaises(HTTPError) as caught:
                    urlopen(f"http://127.0.0.1:{server.server_port}/health", timeout=2)
                self.assertEqual(caught.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
