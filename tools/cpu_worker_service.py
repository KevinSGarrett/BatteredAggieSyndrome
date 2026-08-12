from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.contracts import canonical_json_bytes
from aggie_analytics.assistive_plane.cpu_worker_backend import MAX_TEXT_BYTES, execute_cpu_request


def handler(*, controller_ip: str, storage_root: Path):
    class WorkerHandler(BaseHTTPRequestHandler):
        server_version = "AggieCpuWorker/1"

        def log_message(self, format: str, *args: object) -> None:
            return

        def send_json(self, status: int, payload: dict[str, object]) -> None:
            data = canonical_json_bytes(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def allowed(self) -> bool:
            return self.client_address[0] == controller_ip

        def do_GET(self) -> None:  # noqa: N802
            if not self.allowed():
                self.send_json(403, {"error": "CPU_WORKER_CONTROLLER_IDENTITY_REJECTED"})
                return
            if self.path != "/health":
                self.send_json(404, {"error": "NOT_FOUND"})
                return
            self.send_json(200, {
                "status": "READY",
                "schema_version": 1,
                "authority": "DETERMINISTIC_NO_CANONICAL_OR_PROTECTED_WRITES",
                "public_exposure": False,
                "allowed_controller_ip": controller_ip,
            })

        def do_POST(self) -> None:  # noqa: N802
            if not self.allowed():
                self.send_json(403, {"error": "CPU_WORKER_CONTROLLER_IDENTITY_REJECTED"})
                return
            if self.path != "/v1/jobs":
                self.send_json(404, {"error": "NOT_FOUND"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_TEXT_BYTES:
                    raise ValueError("CPU_WORKER_REQUEST_SIZE_INVALID")
                request_data = self.rfile.read(length)
                request_payload = json.loads(request_data.decode("utf-8"))
                response_payload = execute_cpu_request(request_payload)
                data = canonical_json_bytes({"request": request_payload, "response": response_payload}) + b"\n"
                digest = __import__("hashlib").sha256(data).hexdigest()
                destination = storage_root / "results" / digest[:2] / f"{digest}.json"
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists() and destination.read_bytes() != data:
                    raise RuntimeError("CPU_WORKER_CONTENT_ADDRESS_COLLISION")
                destination.write_bytes(data)
                self.send_json(200, response_payload)
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                self.send_json(400, {"error": str(exc)})
            except RuntimeError as exc:
                self.send_json(500, {"error": str(exc)})

    return WorkerHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="Private deterministic Aggie CPU worker")
    parser.add_argument("--bind", required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--controller-ip", required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    args = parser.parse_args()
    if args.bind in {"0.0.0.0", "::", "127.0.0.1", "localhost"}:
        raise RuntimeError("CPU_WORKER_EXACT_TAILSCALE_BIND_REQUIRED")
    args.storage_root.mkdir(parents=True, exist_ok=True)
    server = HTTPServer((args.bind, args.port), handler(controller_ip=args.controller_ip, storage_root=args.storage_root))
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
