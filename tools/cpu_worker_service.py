from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import NamedTemporaryFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.contracts import canonical_json_bytes
from aggie_analytics.assistive_plane.cpu_worker_backend import MAX_TEXT_BYTES, execute_cpu_request


MIN_FREE_BYTES = 256 * 1024 * 1024
MAX_EXECUTION_SECONDS = 20.0
MAX_QUEUE = 8
SHA256_HEX = re.compile(r"[0-9a-f]{64}\Z")


def _digest_component(value: str) -> str:
    if SHA256_HEX.fullmatch(value) is None:
        raise ValueError("CPU_WORKER_PATH_DIGEST_INVALID")
    return value


def _atomic_write(destination: Path, data: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() != data:
            raise RuntimeError("CPU_WORKER_CONTENT_ADDRESS_COLLISION")
        return
    with NamedTemporaryFile(dir=destination.parent, prefix=".tmp-", delete=False) as temporary:
        temporary.write(data)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, destination)


def _content_addressed_event(storage_root: Path, category: str, payload: dict[str, object]) -> Path:
    data = canonical_json_bytes(payload) + b"\n"
    digest = hashlib.sha256(data).hexdigest()
    destination = storage_root / "runtime" / category / digest[:2] / f"{digest}.json"
    _atomic_write(destination, data)
    return destination


class WorkerRuntime:
    def __init__(self, storage_root: Path, signing_key: bytes) -> None:
        self.storage_root = storage_root
        self.signing_key = signing_key
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def _nonce_path(self, nonce: str) -> Path:
        digest = _digest_component(hashlib.sha256(nonce.encode("utf-8")).hexdigest())
        return self.storage_root / "runtime" / "nonces" / digest[:2] / f"{digest}.json"

    def _replay_path(self, envelope_sha256: str) -> Path:
        envelope_sha256 = _digest_component(envelope_sha256)
        return self.storage_root / "runtime" / "replays" / envelope_sha256[:2] / f"{envelope_sha256}.json"

    def recover_interrupted_jobs(self) -> int:
        leases_root = self.storage_root / "runtime" / "leases"
        scratch_root = self.storage_root / "runtime" / "scratch"
        recovered = 0
        lease_digests: set[str] = set()
        if leases_root.exists():
            for lease in sorted(leases_root.glob("*.json")):
                envelope_sha256 = lease.stem
                if SHA256_HEX.fullmatch(envelope_sha256) is None:
                    continue
                lease_digests.add(envelope_sha256)
                job_id: object = None
                try:
                    lease_payload = json.loads(lease.read_text(encoding="utf-8"))
                    job_id = lease_payload.get("job_id")
                except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                    job_id = None
                scratch = scratch_root / envelope_sha256
                removed_bytes = 0
                if scratch.is_dir():
                    removed_bytes = sum(path.stat().st_size for path in scratch.rglob("*") if path.is_file())
                    shutil.rmtree(scratch)
                elif scratch.exists():
                    removed_bytes = scratch.stat().st_size
                    scratch.unlink()
                lease.unlink()
                _content_addressed_event(self.storage_root, "recovery", {
                    "event": "INTERRUPTED_JOB_RECOVERY",
                    "job_id": job_id,
                    "envelope_sha256": envelope_sha256,
                    "lease_removed": True,
                    "scratch_removed": True,
                    "bytes_removed": removed_bytes,
                })
                recovered += 1
        if scratch_root.exists():
            for scratch in sorted(scratch_root.iterdir()):
                envelope_sha256 = scratch.name
                if SHA256_HEX.fullmatch(envelope_sha256) is None or envelope_sha256 in lease_digests:
                    continue
                removed_bytes = 0
                if scratch.is_dir():
                    removed_bytes = sum(path.stat().st_size for path in scratch.rglob("*") if path.is_file())
                    shutil.rmtree(scratch)
                elif scratch.is_file():
                    removed_bytes = scratch.stat().st_size
                    scratch.unlink()
                else:
                    continue
                _content_addressed_event(self.storage_root, "recovery", {
                    "event": "ORPHAN_SCRATCH_RECOVERY",
                    "job_id": None,
                    "envelope_sha256": envelope_sha256,
                    "lease_removed": False,
                    "scratch_removed": True,
                    "bytes_removed": removed_bytes,
                })
                recovered += 1
        return recovered

    def execute(self, request_payload: dict[str, object]) -> dict[str, object]:
        request_data = canonical_json_bytes(request_payload)
        envelope_sha256 = _digest_component(hashlib.sha256(request_data).hexdigest())
        nonce = request_payload.get("nonce")
        job_id = request_payload.get("job_id")
        if (
            not isinstance(nonce, str)
            or not nonce
            or not isinstance(job_id, str)
            or SHA256_HEX.fullmatch(job_id) is None
        ):
            raise ValueError("CPU_WORKER_RUNTIME_IDENTITY_INVALID")
        nonce_path = self._nonce_path(nonce)
        replay_path = self._replay_path(envelope_sha256)
        if nonce_path.exists():
            prior = json.loads(nonce_path.read_text(encoding="utf-8"))
            if prior.get("envelope_sha256") != envelope_sha256:
                raise ValueError("CPU_WORKER_REPLAY_INCONSISTENT")
            if replay_path.exists():
                return json.loads(replay_path.read_text(encoding="utf-8"))["response"]
        free_bytes = shutil.disk_usage(self.storage_root).free
        if free_bytes < MIN_FREE_BYTES:
            raise ValueError("CPU_WORKER_DISK_ADMISSION_REJECTED")
        lease = self.storage_root / "runtime" / "leases" / f"{envelope_sha256}.json"
        lease.parent.mkdir(parents=True, exist_ok=True)
        try:
            with lease.open("x", encoding="utf-8") as handle:
                json.dump({"job_id": job_id, "envelope_sha256": envelope_sha256}, handle, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as exc:
            raise ValueError("CPU_WORKER_JOB_LEASE_BUSY") from exc
        scratch = self.storage_root / "runtime" / "scratch" / envelope_sha256
        scratch.mkdir(parents=True, exist_ok=False)
        started = time.monotonic()
        removed_bytes = 0
        try:
            response_payload = execute_cpu_request(request_payload, self.signing_key)
            elapsed = time.monotonic() - started
            if elapsed > MAX_EXECUTION_SECONDS:
                raise ValueError("CPU_WORKER_EXECUTION_TIMEOUT")
            _atomic_write(
                nonce_path,
                canonical_json_bytes({"nonce_sha256": nonce_path.stem, "envelope_sha256": envelope_sha256}) + b"\n",
            )
            _atomic_write(
                replay_path,
                canonical_json_bytes({"envelope_sha256": envelope_sha256, "response": response_payload}) + b"\n",
            )
            return response_payload
        finally:
            if scratch.exists():
                removed_bytes = sum(path.stat().st_size for path in scratch.rglob("*") if path.is_file())
                shutil.rmtree(scratch)
            lease.unlink(missing_ok=True)
            _content_addressed_event(self.storage_root, "cleanup", {
                "event": "JOB_CLEANUP",
                "job_id": job_id,
                "envelope_sha256": envelope_sha256,
                "scratch_removed": True,
                "bytes_removed": removed_bytes,
            })


class BoundedWorkerServer(HTTPServer):
    request_queue_size = MAX_QUEUE


def handler(
    *,
    signing_key: bytes,
    storage_root: Path,
    expected_user_login: str | None = None,
    required_app_capability: str | None = None,
):
    if not expected_user_login and not required_app_capability:
        raise ValueError("CPU_WORKER_TRUSTED_SERVE_IDENTITY_REQUIRED")
    runtime = WorkerRuntime(storage_root, signing_key)

    class WorkerHandler(BaseHTTPRequestHandler):
        server_version = "AggieCpuWorker/2"

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

        def trusted_serve_proxy(self) -> bool:
            if self.client_address[0] not in {"127.0.0.1", "::1"}:
                return False
            if expected_user_login and self.headers.get("Tailscale-User-Login") == expected_user_login:
                return True
            if required_app_capability:
                raw = self.headers.get("Tailscale-App-Capabilities", "")
                try:
                    return required_app_capability in json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    return False
            return False

        def do_GET(self) -> None:  # noqa: N802
            if not self.trusted_serve_proxy():
                self.send_json(403, {"error": "CPU_WORKER_TRUSTED_SERVE_IDENTITY_REJECTED"})
                return
            if self.path != "/health":
                self.send_json(404, {"error": "NOT_FOUND"})
                return
            self.send_json(200, {
                "status": "READY_FOR_LIVE_QUALIFICATION",
                "schema_version": 2,
                "authority": "DETERMINISTIC_NO_CANONICAL_OR_PROTECTED_WRITES",
                "bind": "LOOPBACK_ONLY",
                "transport": "TAILSCALE_SERVE_PRIVATE_HTTPS",
                "public_funnel": False,
            })

        def do_POST(self) -> None:  # noqa: N802
            if not self.trusted_serve_proxy():
                self.send_json(403, {"error": "CPU_WORKER_TRUSTED_SERVE_IDENTITY_REJECTED"})
                return
            if self.path != "/v2/jobs":
                self.send_json(404, {"error": "NOT_FOUND"})
                return
            try:
                self.connection.settimeout(30.0)
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_TEXT_BYTES:
                    raise ValueError("CPU_WORKER_REQUEST_SIZE_INVALID")
                request_data = self.rfile.read(length)
                request_payload = json.loads(request_data.decode("utf-8"))
                response_payload = runtime.execute(request_payload)
                data = canonical_json_bytes({"request": request_payload, "response": response_payload}) + b"\n"
                digest = _digest_component(hashlib.sha256(data).hexdigest())
                destination = storage_root / "results" / digest[:2] / f"{digest}.json"
                _atomic_write(destination, data)
                self.send_json(200, response_payload)
            except (TimeoutError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                self.send_json(400, {"error": str(exc)})
            except RuntimeError as exc:
                self.send_json(500, {"error": str(exc)})

    return WorkerHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="Private deterministic Aggie CPU worker v2")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--signing-key-file", type=Path, required=True)
    identity = parser.add_mutually_exclusive_group(required=True)
    identity.add_argument("--expected-user-login")
    identity.add_argument("--required-app-capability")
    args = parser.parse_args()
    if args.bind != "127.0.0.1":
        raise RuntimeError("CPU_WORKER_LOOPBACK_BIND_REQUIRED")
    signing_key = args.signing_key_file.read_bytes()
    if len(signing_key) < 32:
        raise RuntimeError("CPU_WORKER_SIGNING_KEY_TOO_SHORT")
    args.storage_root.mkdir(parents=True, exist_ok=True)
    recovered_interrupted_jobs = WorkerRuntime(args.storage_root, signing_key).recover_interrupted_jobs()
    server = BoundedWorkerServer((args.bind, args.port), handler(
        signing_key=signing_key,
        storage_root=args.storage_root,
        expected_user_login=args.expected_user_login,
        required_app_capability=args.required_app_capability,
    ))
    _content_addressed_event(args.storage_root, "lifecycle", {
        "event": "STARTUP",
        "authority": "DETERMINISTIC_NO_CANONICAL_OR_PROTECTED_WRITES",
        "bind": args.bind,
        "port": args.port,
        "recovered_interrupted_jobs": recovered_interrupted_jobs,
    })
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
        _content_addressed_event(args.storage_root, "lifecycle", {
            "event": "CLEAN_SHUTDOWN",
            "authority": "DETERMINISTIC_NO_CANONICAL_OR_PROTECTED_WRITES",
            "bind": args.bind,
            "port": args.port,
        })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
