from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .contracts import canonical_json_bytes, sha256_value
from .orchestration import validate_cpu_worker_identity


ALLOWED_TASKS = frozenset({"CANONICAL_JSON", "LINE_HASH_MANIFEST", "EXACT_TEXT_DEDUP"})
MAX_RECORDS = 10_000
MAX_TEXT_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True)
class CpuWorkerIdentity:
    dns_name: str
    os_name: str
    online: bool
    allowed_dns_name: str = "comfy-v4-cpu-01.tail9b05ab.ts.net"

    def validate(self) -> None:
        validate_cpu_worker_identity(
            dns_name=self.dns_name,
            os_name=self.os_name,
            online=self.online,
            allowed_dns_name=self.allowed_dns_name,
        )


@dataclass(frozen=True)
class CpuWorkerEndpoint:
    url: str
    allowed_dns_name: str = "comfy-v4-cpu-01.tail9b05ab.ts.net"
    allowed_port: int = 8765

    def validate(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme != "http":
            raise ValueError("CPU_WORKER_TAILSCALE_HTTP_REQUIRED")
        if (parsed.hostname or "").rstrip(".").lower() != self.allowed_dns_name.rstrip(".").lower():
            raise ValueError("CPU_WORKER_ENDPOINT_IDENTITY_MISMATCH")
        if parsed.port != self.allowed_port or parsed.path.rstrip("/"):
            raise ValueError("CPU_WORKER_ENDPOINT_PORT_OR_PATH_INVALID")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("CPU_WORKER_ENDPOINT_AUTHORITY_INVALID")


@dataclass(frozen=True)
class CpuWorkerJob:
    task: str
    payload: dict[str, Any]
    jira_unit: str
    contract_version: str = "cpu-worker-v1"

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
            "task": self.task,
        })

    def request(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "contract_version": self.contract_version,
            "request_id": self.identity(),
            "jira_unit": self.jira_unit,
            "task": self.task,
            "payload": self.payload,
            "authority": "DETERMINISTIC_NO_CANONICAL_OR_PROTECTED_WRITES",
        }


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
        normalized = _normalize_text(text)
        digest = _sha_bytes(normalized.encode("utf-8"))
        group = groups.setdefault(digest, {"normalized_sha256": digest, "record_ids": []})
        group["record_ids"].append(record_id)
    ordered = []
    for digest in sorted(groups):
        group = groups[digest]
        group["record_ids"].sort()
        ordered.append(group)
    return {
        "record_count": len(records),
        "unique_normalized_count": len(ordered),
        "groups": ordered,
    }


def execute_cpu_request(request: dict[str, Any]) -> dict[str, Any]:
    required = {"schema_version", "contract_version", "request_id", "jira_unit", "task", "payload", "authority"}
    if set(request) != required or request.get("schema_version") != 1:
        raise ValueError("CPU_WORKER_REQUEST_SCHEMA_INVALID")
    job = CpuWorkerJob(
        task=request["task"],
        payload=request["payload"],
        jira_unit=request["jira_unit"],
        contract_version=request["contract_version"],
    )
    if request["request_id"] != job.identity():
        raise ValueError("CPU_WORKER_REQUEST_IDENTITY_MISMATCH")
    if request["authority"] != "DETERMINISTIC_NO_CANONICAL_OR_PROTECTED_WRITES":
        raise ValueError("CPU_WORKER_AUTHORITY_INVALID")
    result = execute_cpu_task(job.task, job.payload)
    return {
        "schema_version": 1,
        "request_id": job.identity(),
        "task": job.task,
        "result": result,
        "result_sha256": sha256_value(result),
        "canonical_writes": 0,
        "protected_decisions": 0,
    }


class CpuWorkerClient:
    def __init__(self, endpoint: CpuWorkerEndpoint, storage_root: Path, timeout_seconds: float = 30.0) -> None:
        endpoint.validate()
        self.endpoint = endpoint
        self.storage_root = storage_root
        self.timeout_seconds = timeout_seconds

    def submit(self, job: CpuWorkerJob) -> tuple[dict[str, Any], Path]:
        request_payload = job.request()
        request_data = canonical_json_bytes(request_payload)
        request = Request(
            f"{self.endpoint.url.rstrip('/')}/v1/jobs",
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
        expected = execute_cpu_request(request_payload)
        if payload != expected:
            raise RuntimeError("CPU_WORKER_RESULT_VALIDATION_FAILED")
        data = canonical_json_bytes({"request": request_payload, "response": payload}) + b"\n"
        digest = _sha_bytes(data)
        destination = self.storage_root / "results" / digest[:2] / f"{digest}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != data:
            raise RuntimeError("CPU_WORKER_CONTENT_ADDRESS_COLLISION")
        destination.write_bytes(data)
        return payload, destination
