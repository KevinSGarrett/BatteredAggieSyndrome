from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, MutableMapping
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .contracts import canonical_json_bytes, sha256_value


ALLOWED_TASKS = frozenset({"CANONICAL_JSON", "LINE_HASH_MANIFEST", "EXACT_TEXT_DEDUP"})
MAX_RECORDS = 10_000
MAX_TEXT_BYTES = 4 * 1024 * 1024
MAX_ENVELOPE_TTL_SECONDS = 600
MAX_FUTURE_SKEW_SECONDS = 60
AUTHORITY = "DETERMINISTIC_NO_CANONICAL_OR_PROTECTED_WRITES"


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("CPU_WORKER_TIMESTAMP_TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _signature(value: dict[str, Any], signing_key: bytes) -> str:
    if len(signing_key) < 32:
        raise ValueError("CPU_WORKER_SIGNING_KEY_TOO_SHORT")
    return hmac.new(signing_key, canonical_json_bytes(value), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class CpuWorkerIdentity:
    dns_name: str
    os_name: str
    online: bool
    windows_hostname: str = "comfy-v4-cpu-01"
    node_id: str | None = None
    allowed_dns_name: str = "comfy-v4-cpu-01.tail9b05ab.ts.net"
    allowed_node_id: str = "nUxabVWSHb11CNTRL"

    def validate(self) -> None:
        if self.dns_name.rstrip(".").lower() != self.allowed_dns_name.lower():
            raise ValueError("CPU_WORKER_IDENTITY_MISMATCH")
        if self.windows_hostname.lower() != "comfy-v4-cpu-01":
            raise ValueError("CPU_WORKER_HOSTNAME_MISMATCH")
        if self.os_name.lower() != "windows":
            raise ValueError("CPU_WORKER_OS_MISMATCH")
        if not self.online:
            raise ValueError("CPU_WORKER_OFFLINE")
        if self.node_id != self.allowed_node_id:
            raise ValueError("CPU_WORKER_NODE_ID_MISMATCH")


@dataclass(frozen=True)
class CpuWorkerEndpoint:
    url: str
    allowed_dns_name: str = "comfy-v4-cpu-01.tail9b05ab.ts.net"

    def validate(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme != "https":
            raise ValueError("CPU_WORKER_PRIVATE_HTTPS_REQUIRED")
        if (parsed.hostname or "").rstrip(".").lower() != self.allowed_dns_name.lower():
            raise ValueError("CPU_WORKER_ENDPOINT_IDENTITY_MISMATCH")
        if parsed.port not in {None, 443} or parsed.path.rstrip("/"):
            raise ValueError("CPU_WORKER_ENDPOINT_PORT_OR_PATH_INVALID")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("CPU_WORKER_ENDPOINT_AUTHORITY_INVALID")


@dataclass(frozen=True)
class CpuWorkerJob:
    task: str
    payload: dict[str, Any]
    jira_unit: str
    contract_version: str = "cpu-worker-v2"
    policy_version: str = "unified-assistive-execution-plane-v2-operational-correction"

    def __post_init__(self) -> None:
        if self.task not in ALLOWED_TASKS:
            raise ValueError("CPU_WORKER_TASK_NOT_ALLOWED")
        if not self.jira_unit:
            raise ValueError("CPU_WORKER_JIRA_IDENTITY_REQUIRED")
        if len(canonical_json_bytes(self.payload)) > MAX_TEXT_BYTES:
            raise ValueError("CPU_WORKER_PAYLOAD_TOO_LARGE")

    def identity(self) -> str:
        return sha256_value({
            "contract_version": self.contract_version,
            "jira_unit": self.jira_unit,
            "payload": self.payload,
            "policy_version": self.policy_version,
            "task": self.task,
        })

    def request(
        self,
        signing_key: bytes,
        *,
        issued_at: datetime | None = None,
        ttl_seconds: int = 300,
        nonce: str | None = None,
    ) -> dict[str, Any]:
        if ttl_seconds <= 0 or ttl_seconds > MAX_ENVELOPE_TTL_SECONDS:
            raise ValueError("CPU_WORKER_ENVELOPE_TTL_INVALID")
        issued = (issued_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        unsigned = {
            "schema_version": 2,
            "contract_version": self.contract_version,
            "job_id": self.identity(),
            "jira_unit": self.jira_unit,
            "issued_at_utc": _utc_text(issued),
            "expires_at_utc": _utc_text(issued + timedelta(seconds=ttl_seconds)),
            "nonce": nonce or secrets.token_hex(16),
            "payload_sha256": sha256_value(self.payload),
            "policy_version": self.policy_version,
            "task": self.task,
            "payload": self.payload,
            "authority": AUTHORITY,
        }
        return {**unsigned, "signature": _signature(unsigned, signing_key)}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).strip()).casefold()


def execute_cpu_task(task: str, payload: dict[str, Any]) -> dict[str, Any]:
    if task not in ALLOWED_TASKS:
        raise ValueError("CPU_WORKER_TASK_NOT_ALLOWED")
    if task == "CANONICAL_JSON":
        if set(payload) != {"value"}:
            raise ValueError("CPU_WORKER_CANONICAL_JSON_INPUT_INVALID")
        data = canonical_json_bytes(payload["value"])
        return {"canonical_json": data.decode("utf-8"), "canonical_sha256": _sha_bytes(data)}
    if task == "LINE_HASH_MANIFEST":
        if set(payload) != {"lines"} or not isinstance(payload["lines"], list):
            raise ValueError("CPU_WORKER_LINE_HASH_INPUT_INVALID")
        lines = payload["lines"]
        if len(lines) > MAX_RECORDS or any(not isinstance(line, str) for line in lines):
            raise ValueError("CPU_WORKER_LINE_HASH_RECORDS_INVALID")
        return {
            "line_count": len(lines),
            "line_sha256": [_sha_bytes(line.encode("utf-8")) for line in lines],
            "joined_sha256": _sha_bytes("\n".join(lines).encode("utf-8")),
        }
    if set(payload) != {"records"} or not isinstance(payload["records"], list):
        raise ValueError("CPU_WORKER_DEDUP_INPUT_INVALID")
    records = payload["records"]
    if len(records) > MAX_RECORDS:
        raise ValueError("CPU_WORKER_DEDUP_RECORD_LIMIT")
    groups: dict[str, dict[str, Any]] = {}
    seen_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {"id", "text"}:
            raise ValueError("CPU_WORKER_DEDUP_RECORD_INVALID")
        record_id, text = record["id"], record["text"]
        if not isinstance(record_id, str) or not record_id or record_id in seen_ids or not isinstance(text, str):
            raise ValueError("CPU_WORKER_DEDUP_RECORD_IDENTITY_INVALID")
        seen_ids.add(record_id)
        digest = _sha_bytes(_normalize_text(text).encode("utf-8"))
        groups.setdefault(digest, {"normalized_sha256": digest, "record_ids": []})["record_ids"].append(record_id)
    ordered = []
    for digest in sorted(groups):
        groups[digest]["record_ids"].sort()
        ordered.append(groups[digest])
    return {"record_count": len(records), "unique_normalized_count": len(ordered), "groups": ordered}


def execute_cpu_request(
    request: dict[str, Any],
    signing_key: bytes,
    *,
    now: datetime | None = None,
    replay_registry: MutableMapping[str, str] | None = None,
) -> dict[str, Any]:
    required = {
        "schema_version", "contract_version", "job_id", "jira_unit", "issued_at_utc",
        "expires_at_utc", "nonce", "payload_sha256", "policy_version", "task", "payload",
        "authority", "signature",
    }
    if set(request) != required or request.get("schema_version") != 2:
        raise ValueError("CPU_WORKER_REQUEST_SCHEMA_INVALID")
    unsigned = {key: request[key] for key in required if key != "signature"}
    if not hmac.compare_digest(request["signature"], _signature(unsigned, signing_key)):
        raise ValueError("CPU_WORKER_SIGNATURE_INVALID")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    issued, expires = _utc(request["issued_at_utc"]), _utc(request["expires_at_utc"])
    if issued > current + timedelta(seconds=MAX_FUTURE_SKEW_SECONDS):
        raise ValueError("CPU_WORKER_ISSUED_AT_IN_FUTURE")
    if expires <= current:
        raise ValueError("CPU_WORKER_REQUEST_EXPIRED")
    if expires - issued > timedelta(seconds=MAX_ENVELOPE_TTL_SECONDS):
        raise ValueError("CPU_WORKER_ENVELOPE_TTL_INVALID")
    if request["payload_sha256"] != sha256_value(request["payload"]):
        raise ValueError("CPU_WORKER_PAYLOAD_HASH_MISMATCH")
    job = CpuWorkerJob(
        task=request["task"],
        payload=request["payload"],
        jira_unit=request["jira_unit"],
        contract_version=request["contract_version"],
        policy_version=request["policy_version"],
    )
    if request["job_id"] != job.identity():
        raise ValueError("CPU_WORKER_REQUEST_IDENTITY_MISMATCH")
    if request["authority"] != AUTHORITY:
        raise ValueError("CPU_WORKER_AUTHORITY_INVALID")
    envelope_sha256 = sha256_value(unsigned)
    if replay_registry is not None:
        prior = replay_registry.get(request["nonce"])
        if prior is not None and prior != envelope_sha256:
            raise ValueError("CPU_WORKER_REPLAY_INCONSISTENT")
        replay_registry[request["nonce"]] = envelope_sha256
    result = execute_cpu_task(job.task, job.payload)
    response_unsigned = {
        "schema_version": 2,
        "job_id": job.identity(),
        "nonce": request["nonce"],
        "task": job.task,
        "result": result,
        "result_sha256": sha256_value(result),
        "canonical_writes": 0,
        "protected_decisions": 0,
    }
    return {**response_unsigned, "signature": _signature(response_unsigned, signing_key)}


def verify_cpu_response(response: dict[str, Any], request: dict[str, Any], signing_key: bytes) -> None:
    signature = response.get("signature")
    unsigned = {key: value for key, value in response.items() if key != "signature"}
    if not isinstance(signature, str) or not hmac.compare_digest(signature, _signature(unsigned, signing_key)):
        raise RuntimeError("CPU_WORKER_RESPONSE_SIGNATURE_INVALID")
    if response.get("job_id") != request["job_id"] or response.get("nonce") != request["nonce"]:
        raise RuntimeError("CPU_WORKER_RESPONSE_IDENTITY_INVALID")
    if response.get("result_sha256") != sha256_value(response.get("result")):
        raise RuntimeError("CPU_WORKER_RESULT_HASH_INVALID")


class CpuWorkerClient:
    def __init__(self, endpoint: CpuWorkerEndpoint, storage_root: Path, signing_key: bytes, timeout_seconds: float = 30.0) -> None:
        endpoint.validate()
        if len(signing_key) < 32:
            raise ValueError("CPU_WORKER_SIGNING_KEY_TOO_SHORT")
        self.endpoint = endpoint
        self.storage_root = storage_root
        self.signing_key = signing_key
        self.timeout_seconds = timeout_seconds

    def submit(
        self,
        job: CpuWorkerJob,
        request_payload: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], Path]:
        request_payload = request_payload or job.request(self.signing_key)
        if request_payload.get("job_id") != job.identity():
            raise ValueError("CPU_WORKER_CLIENT_JOB_ENVELOPE_MISMATCH")
        request_data = canonical_json_bytes(request_payload)
        request = Request(
            f"{self.endpoint.url.rstrip('/')}/v2/jobs",
            data=request_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            if response.status != 200:
                raise RuntimeError(f"CPU_WORKER_HTTP_STATUS:{response.status}")
            body = response.read(MAX_TEXT_BYTES + 1)
        if len(body) > MAX_TEXT_BYTES:
            raise RuntimeError("CPU_WORKER_RESPONSE_TOO_LARGE")
        payload = json.loads(body.decode("utf-8"))
        verify_cpu_response(payload, request_payload, self.signing_key)
        if payload["result"] != execute_cpu_task(job.task, job.payload):
            raise RuntimeError("CPU_WORKER_RESULT_VALIDATION_FAILED")
        data = canonical_json_bytes({"request": request_payload, "response": payload}) + b"\n"
        digest = _sha_bytes(data)
        destination = self.storage_root / "results" / digest[:2] / f"{digest}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != data:
            raise RuntimeError("CPU_WORKER_CONTENT_ADDRESS_COLLISION")
        if not destination.exists():
            with NamedTemporaryFile(dir=destination.parent, prefix=".tmp-", delete=False) as temporary:
                temporary.write(data)
                temporary.flush()
                import os
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            try:
                os.replace(temporary_path, destination)
            finally:
                if temporary_path.exists():
                    temporary_path.unlink()
        return payload, destination
