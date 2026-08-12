from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from .contracts import canonical_json_bytes, sha256_value


ALLOWED_EFFORT_POINTS = frozenset({1, 2, 3, 5, 8})


class RoutingDisposition(StrEnum):
    CODEX_DETERMINISTIC = "CODEX_DETERMINISTIC"
    DIRECT_OPENAI = "DIRECT_OPENAI"
    OPENROUTER = "OPENROUTER"
    CURSOR = "CURSOR"
    LOCAL_QWEN = "LOCAL_QWEN"
    REMOTE_CPU_WORKER = "REMOTE_CPU_WORKER"
    DEFERRED_DEPENDENCY = "DEFERRED_DEPENDENCY"
    BUDGET_BLOCKED = "BUDGET_BLOCKED"
    CAPABILITY_BLOCKED = "CAPABILITY_BLOCKED"
    REJECTED_NO_VALUE = "REJECTED_NO_VALUE"


class ReadinessState(StrEnum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ReadyWorkUnit:
    work_unit_id: str
    jira_unit: str
    task_format: str
    schema_sha256: str
    authority: str
    source_hashes: tuple[str, ...]
    dependencies: tuple[str, ...]
    pre_routing_effort_points: int
    scope: str

    def __post_init__(self) -> None:
        if self.pre_routing_effort_points not in ALLOWED_EFFORT_POINTS:
            raise ValueError("INVALID_PRE_ROUTING_EFFORT")
        if not self.work_unit_id or not self.jira_unit or not self.scope:
            raise ValueError("WORK_UNIT_IDENTITY_INCOMPLETE")
        if len(self.schema_sha256) != 64:
            raise ValueError("SCHEMA_IDENTITY_INVALID")
        if any(len(value) != 64 for value in self.source_hashes):
            raise ValueError("SOURCE_IDENTITY_INVALID")

    def identity(self) -> str:
        return sha256_value(asdict(self))


@dataclass(frozen=True)
class RouteDecision:
    work_unit_id: str
    work_unit_identity: str
    disposition: RoutingDisposition
    provider: str | None
    model: str | None
    reason: str
    decided_at: str


@dataclass(frozen=True)
class RouteKey:
    provider: str
    resolved_model: str
    task_format: str
    schema_sha256: str
    policy_version: str

    def identity(self) -> str:
        return sha256_value(asdict(self))


@dataclass(frozen=True)
class RouteReadiness:
    key: RouteKey
    state: ReadinessState
    evidence_sha256: str
    reason: str


@dataclass(frozen=True)
class ProviderBudget:
    provider: str
    currency: str
    hard_limit_usd: str
    released_usd: str
    spent_usd: str
    authorization_id: str | None

    def admits_paid_work(self) -> bool:
        from decimal import Decimal

        hard = Decimal(self.hard_limit_usd)
        released = Decimal(self.released_usd)
        spent = Decimal(self.spent_usd)
        return bool(self.authorization_id) and hard > 0 and released > spent and spent < hard


class ReadyWorkInventory:
    def __init__(self, units: Iterable[ReadyWorkUnit], decisions: Iterable[RouteDecision]) -> None:
        self.units = tuple(units)
        self.decisions = tuple(decisions)

    def validate(self) -> dict[str, Any]:
        unit_by_id: dict[str, ReadyWorkUnit] = {}
        for unit in self.units:
            if unit.work_unit_id in unit_by_id:
                raise ValueError(f"DUPLICATE_WORK_UNIT:{unit.work_unit_id}")
            unit_by_id[unit.work_unit_id] = unit
        decisions: dict[str, RouteDecision] = {}
        for decision in self.decisions:
            if decision.work_unit_id in decisions:
                raise ValueError(f"MULTIPLE_ROUTE_DISPOSITIONS:{decision.work_unit_id}")
            unit = unit_by_id.get(decision.work_unit_id)
            if unit is None:
                raise ValueError(f"ROUTE_FOR_UNKNOWN_WORK_UNIT:{decision.work_unit_id}")
            if decision.work_unit_identity != unit.identity():
                raise ValueError(f"PRE_ROUTING_IDENTITY_CHANGED:{decision.work_unit_id}")
            decisions[decision.work_unit_id] = decision
        missing = sorted(set(unit_by_id) - set(decisions))
        if missing:
            raise ValueError(f"MISSING_ROUTE_DISPOSITION:{','.join(missing)}")
        counts: dict[str, int] = {}
        points: dict[str, int] = {}
        for unit_id, decision in decisions.items():
            name = decision.disposition.value
            counts[name] = counts.get(name, 0) + 1
            points[name] = points.get(name, 0) + unit_by_id[unit_id].pre_routing_effort_points
        ordered = sorted(self.units, key=lambda item: item.work_unit_id)
        return {
            "schema_version": 1,
            "work_unit_count": len(unit_by_id),
            "disposition_count": len(decisions),
            "coverage_fraction": 1.0,
            "effort_points_total": sum(item.pre_routing_effort_points for item in self.units),
            "counts_by_disposition": dict(sorted(counts.items())),
            "effort_points_by_disposition": dict(sorted(points.items())),
            "inventory_identity": sha256_value([asdict(item) for item in ordered]),
        }


class ReadinessRegistry:
    def __init__(self, entries: Iterable[RouteReadiness]) -> None:
        self._entries: dict[str, RouteReadiness] = {}
        for entry in entries:
            identity = entry.key.identity()
            if identity in self._entries:
                raise ValueError(f"DUPLICATE_ROUTE_READINESS:{identity}")
            if len(entry.evidence_sha256) != 64:
                raise ValueError("READINESS_EVIDENCE_IDENTITY_INVALID")
            self._entries[identity] = entry

    def require(self, key: RouteKey) -> RouteReadiness:
        entry = self._entries.get(key.identity())
        if entry is None:
            raise ValueError("ROUTE_READINESS_NOT_ESTABLISHED")
        if entry.state is not ReadinessState.READY:
            raise ValueError(f"ROUTE_NOT_READY:{entry.state.value}:{entry.reason}")
        return entry


def validate_cursor_request(*, model: str, reasoning: str, fast: bool, work_on_current_branch: bool, auto_create_pr: bool) -> None:
    if model != "gpt-5.3-codex":
        raise ValueError("CURSOR_CODEX_MODEL_NOT_EXACT")
    if reasoning not in {"low", "medium"}:
        raise ValueError("CURSOR_REASONING_NOT_ALLOWED")
    if fast:
        raise ValueError("CURSOR_FAST_NOT_ALLOWED")
    if work_on_current_branch:
        raise ValueError("CURSOR_CURRENT_BRANCH_WRITE_NOT_ALLOWED")
    if auto_create_pr:
        raise ValueError("CURSOR_AUTOMATIC_PR_NOT_ALLOWED")


def validate_ollama_route(*, endpoint: str, max_loaded_models: int, parallel_requests: int, context_tokens: int, model_digest: str) -> None:
    parsed = urlparse(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("OLLAMA_NON_LOOPBACK_ENDPOINT")
    if max_loaded_models != 1 or parallel_requests != 1:
        raise ValueError("OLLAMA_CONCURRENCY_POLICY_VIOLATION")
    if context_tokens > 4096:
        raise ValueError("OLLAMA_INITIAL_CONTEXT_LIMIT_EXCEEDED")
    if len(model_digest) < 12:
        raise ValueError("OLLAMA_MODEL_DIGEST_REQUIRED")


def validate_cpu_worker_identity(*, dns_name: str, os_name: str, online: bool, allowed_dns_name: str) -> None:
    if dns_name.rstrip(".").lower() != allowed_dns_name.rstrip(".").lower():
        raise ValueError("CPU_WORKER_IDENTITY_MISMATCH")
    if os_name.lower() != "windows":
        raise ValueError("CPU_WORKER_OS_MISMATCH")
    if not online:
        raise ValueError("CPU_WORKER_OFFLINE")


def write_content_addressed_json(root: Path, category: str, payload: dict[str, Any]) -> tuple[Path, str]:
    data = canonical_json_bytes(payload) + b"\n"
    digest = hashlib.sha256(data).hexdigest()
    destination = root / category / digest[:2] / f"{digest}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_bytes() != data:
        raise RuntimeError("CONTENT_ADDRESS_COLLISION")
    destination.write_bytes(data)
    return destination, digest


def load_inventory(path: Path) -> ReadyWorkInventory:
    payload = json.loads(path.read_text(encoding="utf-8"))
    units = [
        ReadyWorkUnit(**{**item, "source_hashes": tuple(item["source_hashes"]), "dependencies": tuple(item["dependencies"])})
        for item in payload["work_units"]
    ]
    decisions = [
        RouteDecision(**{**item, "disposition": RoutingDisposition(item["disposition"])})
        for item in payload["route_decisions"]
    ]
    return ReadyWorkInventory(units, decisions)
