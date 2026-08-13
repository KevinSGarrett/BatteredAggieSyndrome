from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .contracts import canonical_json_bytes, sha256_value
from .controller_state import ControllerState, rfc3339
from .cpu_worker_backend import MAX_RECORDS
from .orchestration import (
    ATOMIC_EXECUTABLE,
    ReadyWorkInventory,
    ReadyWorkUnit,
    RouteDecision,
    RoutingDisposition,
    validate_work_unit_roles,
)


MAX_DISCOVERED_MANIFEST_BYTES = 1024 * 1024
MAX_DISCOVERED_UNITS = 64
MAX_PROVIDER_WORK_BYTES = 2 * 1024 * 1024
MAX_PROVIDER_WORK_UNITS = 64
MAX_PROVIDER_WORK_SCAN_UNITS = 4096
DISCOVERY_NAMES = frozenset({"run.json", "progress.json"})
DYNAMIC_PREFIXES = (
    "AUTO-CPU-MANIFEST-",
    "AUTO-CPU-LINE-HASH-",
    "AUTO-CPU-TEXT-DEDUP-",
    "AUTO-BGE-",
    "AUTO-OAI-",
    "AUTO-OR-",
)
CPU_MANIFEST_TASK_FORMAT = "cpu_worker_canonical_manifest_v1"
CPU_MANIFEST_SCHEMA_SHA256 = hashlib.sha256(
    b"cpu_worker_canonical_manifest_v1:value:any-json;candidate-only;exact-local-replay"
).hexdigest()
CPU_LINE_HASH_TASK_FORMAT = "cpu_worker_line_hash_manifest_v1"
CPU_LINE_HASH_SCHEMA_SHA256 = hashlib.sha256(
    b"cpu_worker_line_hash_manifest_v1:lines:utf8-list;candidate-only;exact-local-replay"
).hexdigest()
CPU_TEXT_DEDUP_TASK_FORMAT = "cpu_worker_exact_text_dedup_v1"
CPU_TEXT_DEDUP_SCHEMA_SHA256 = hashlib.sha256(
    b"cpu_worker_exact_text_dedup_v1:records:id-text;nfkc-whitespace-casefold;candidate-only"
).hexdigest()
CPU_EXACT_ROUTES = {
    "CANONICAL_JSON": (CPU_MANIFEST_TASK_FORMAT, CPU_MANIFEST_SCHEMA_SHA256, "AUTO-CPU-MANIFEST-"),
    "LINE_HASH_MANIFEST": (
        CPU_LINE_HASH_TASK_FORMAT,
        CPU_LINE_HASH_SCHEMA_SHA256,
        "AUTO-CPU-LINE-HASH-",
    ),
    "EXACT_TEXT_DEDUP": (
        CPU_TEXT_DEDUP_TASK_FORMAT,
        CPU_TEXT_DEDUP_SCHEMA_SHA256,
        "AUTO-CPU-TEXT-DEDUP-",
    ),
}
OPENROUTER_TASK_FORMAT = "governed_openrouter_candidate_v1"
READY_WORK_UNIT_FIELDS = frozenset(ReadyWorkUnit.__dataclass_fields__)
ROUTE_DECISION_FIELDS = frozenset(RouteDecision.__dataclass_fields__)


def cpu_qualification_evidence_sha256(
    snapshot: dict[str, Any], task: str = "CANONICAL_JSON"
) -> str | None:
    if task not in CPU_EXACT_ROUTES:
        return None
    evidence = snapshot.get("external_evidence", {}).get("cpu_worker", {})
    if not evidence.get("qualified"):
        return None

    def valid_sha256(value: object) -> bool:
        text = str(value)
        return len(text) == 64 and all(character in "0123456789abcdef" for character in text)

    qualifications = evidence.get("qualifications", [])
    if not isinstance(qualifications, list):
        return None
    for qualification in qualifications:
        tasks = qualification.get("tasks") if isinstance(qualification, dict) else None
        if (
            isinstance(qualification, dict)
            and isinstance(tasks, list)
            and task in tasks
            and valid_sha256(qualification.get("evidence_sha256"))
            and valid_sha256(qualification.get("readiness_evidence_sha256"))
        ):
            return str(qualification["readiness_evidence_sha256"])
    return None


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _content_addressed_json(root: Path, category: str, payload: dict[str, Any]) -> tuple[Path, str]:
    data = canonical_json_bytes(payload) + b"\n"
    digest = hashlib.sha256(data).hexdigest()
    destination = root / category / "sha256" / digest / "packet.json"
    if destination.exists():
        if destination.read_bytes() != data:
            raise RuntimeError("RUNTIME_INVENTORY_CONTENT_ADDRESS_COLLISION")
    else:
        _atomic_write(destination, data)
    return destination, digest


def _verified_json(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise RuntimeError("RUNTIME_INVENTORY_REFERENCED_HASH_MISMATCH")
    payload = json.loads(data)
    if not isinstance(payload, dict):
        raise ValueError("RUNTIME_INVENTORY_JSON_NOT_OBJECT")
    return payload


@dataclass(frozen=True)
class RuntimeInventoryConfig:
    current_path: Path
    snapshot_root: Path
    packet_root: Path
    manifests_root: Path
    provider_work_root: Path | None = None
    release_root: Path | None = None
    build_commit: str | None = None
    refresh_max_age_seconds: int = 240

    def validate(self) -> None:
        if self.refresh_max_age_seconds <= 0:
            raise ValueError("RUNTIME_INVENTORY_REFRESH_AGE_INVALID")
        if not self.manifests_root.is_absolute():
            raise ValueError("RUNTIME_INVENTORY_MANIFEST_ROOT_NOT_ABSOLUTE")
        if self.provider_work_root is not None and not self.provider_work_root.is_absolute():
            raise ValueError("RUNTIME_INVENTORY_PROVIDER_WORK_ROOT_NOT_ABSOLUTE")
        if (self.release_root is None) != (self.build_commit is None):
            raise ValueError("RUNTIME_INVENTORY_RELEASE_IDENTITY_INCOMPLETE")
        if self.release_root is not None and not self.release_root.is_absolute():
            raise ValueError("RUNTIME_INVENTORY_RELEASE_ROOT_NOT_ABSOLUTE")
        if self.build_commit is not None and (
            len(self.build_commit) != 40
            or any(character not in "0123456789abcdef" for character in self.build_commit)
        ):
            raise ValueError("RUNTIME_INVENTORY_BUILD_COMMIT_INVALID")


class RuntimeInventoryRefresher:
    """Derive immutable granular work from real external manifests and refresh a small pointer."""

    def __init__(self, state: ControllerState, config: RuntimeInventoryConfig) -> None:
        config.validate()
        self.state = state
        self.config = config

    def _load_current_snapshot(self) -> tuple[dict[str, Any], str]:
        payload = _verified_json(self.config.current_path)
        if payload.get("artifact_type") == "UNIFIED_ASSISTIVE_INVENTORY_POINTER":
            snapshot_path = Path(str(payload["snapshot_path"]))
            snapshot_sha256 = str(payload["snapshot_sha256"])
            return _verified_json(snapshot_path, snapshot_sha256), snapshot_sha256
        data = self.config.current_path.read_bytes()
        return payload, hashlib.sha256(data).hexdigest()

    def _deployed_release(self) -> dict[str, Any] | None:
        if self.config.release_root is None or self.config.build_commit is None:
            return None
        release = self.config.release_root.resolve(strict=True)
        if release.name != self.config.build_commit:
            raise RuntimeError("RUNTIME_INVENTORY_RELEASE_DIRECTORY_BUILD_MISMATCH")
        manifest_path = release / "RELEASE_MANIFEST.json"
        manifest_data = manifest_path.read_bytes()
        manifest = json.loads(manifest_data)
        if manifest.get("build_commit") != self.config.build_commit:
            raise RuntimeError("RUNTIME_INVENTORY_RELEASE_MANIFEST_BUILD_MISMATCH")
        return {
            "build_commit": self.config.build_commit,
            "release_root": str(release),
            "release_manifest_sha256": hashlib.sha256(manifest_data).hexdigest(),
            "source_tree_sha256": manifest.get("source_tree_sha256"),
            "evidence_scope": "IMMUTABLE_DEPLOYED_RELEASE_FROM_MERGED_MAIN",
        }

    def _discover(self, moment: datetime) -> list[tuple[ReadyWorkUnit, RouteDecision, dict[str, Any]]]:
        root = self.config.manifests_root.resolve(strict=True)
        candidates = sorted(
            (
                path
                for path in root.rglob("*.json")
                if path.name in DISCOVERY_NAMES and 0 < path.stat().st_size <= MAX_DISCOVERED_MANIFEST_BYTES
            ),
            key=lambda path: path.relative_to(root).as_posix(),
        )
        if len(candidates) > MAX_DISCOVERED_UNITS:
            raise RuntimeError("RUNTIME_INVENTORY_DISCOVERY_BOUND_EXCEEDED")
        discovered: list[tuple[ReadyWorkUnit, RouteDecision, dict[str, Any]]] = []
        now = rfc3339(moment)
        for source in candidates:
            resolved = source.resolve(strict=True)
            if root not in resolved.parents:
                raise RuntimeError("RUNTIME_INVENTORY_SOURCE_OUTSIDE_ALLOWLIST")
            raw = resolved.read_bytes()
            source_sha256 = hashlib.sha256(raw).hexdigest()
            value = json.loads(raw)
            relative = resolved.relative_to(root).as_posix()
            packet = {
                "schema_version": 1,
                "artifact_type": "CPU_WORKER_CANONICAL_MANIFEST_PACKET",
                "task": "CANONICAL_JSON",
                "task_format": CPU_MANIFEST_TASK_FORMAT,
                "jira_unit": "BAT-563",
                "source_path": str(resolved),
                "source_relative_path": relative,
                "source_sha256": source_sha256,
                "payload": {"value": value},
                "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
            }
            packet_path, packet_sha256 = _content_addressed_json(self.config.packet_root, "packets", packet)
            work_unit_id = f"AUTO-CPU-MANIFEST-{packet_sha256[:20]}"
            unit = ReadyWorkUnit(
                work_unit_id=work_unit_id,
                jira_unit="BAT-563",
                task_format=CPU_MANIFEST_TASK_FORMAT,
                schema_sha256=CPU_MANIFEST_SCHEMA_SHA256,
                authority="CANDIDATE_ONLY",
                source_hashes=(source_sha256, packet_sha256),
                dependencies=(),
                pre_routing_effort_points=1,
                scope=f"Exact canonicalization and provenance QA for external manifest {relative}",
            )
            decision = RouteDecision(
                work_unit_id=work_unit_id,
                work_unit_identity=unit.identity(),
                disposition=RoutingDisposition.REMOTE_CPU_WORKER,
                provider="remote_cpu_worker",
                model="DETERMINISTIC_CPU_WORKER_V2",
                reason="EXACT_CPU_WORKER_QUALIFICATION_PASS_MANIFEST_QA",
                decided_at=now,
            )
            discovered.append(
                (unit, decision, {"packet_path": str(packet_path), "packet_sha256": packet_sha256})
            )
        return discovered

    @staticmethod
    def _valid_sha256(value: object) -> bool:
        text = str(value)
        return len(text) == 64 and all(character in "0123456789abcdef" for character in text)

    @classmethod
    def _provider_readiness(cls, snapshot: dict[str, Any], packet: dict[str, Any]) -> str | None:
        provider = packet.get("provider")
        if provider == "remote_cpu_worker":
            task = str(packet.get("task", ""))
            route = CPU_EXACT_ROUTES.get(task)
            if route is not None and packet.get("task_format") == route[0]:
                return cpu_qualification_evidence_sha256(snapshot, task)
        if provider == "openai_direct":
            evidence = snapshot.get("external_evidence", {}).get("openai", {})
            digest = evidence.get("manifest_sha256")
            return str(digest) if evidence.get("present") and cls._valid_sha256(digest) else None
        if provider == "ollama_local" and packet.get("task_format") == "embedding_dedup_semantic_candidate_retrieval":
            routes = snapshot.get("external_evidence", {}).get("local_qwen", {}).get("routes", [])
            for route in routes if isinstance(routes, list) else []:
                exact = (
                    route.get("provider") == "ollama_local"
                    and route.get("resolved_model") == packet.get("model")
                    and route.get("model_digest") == packet.get("model_digest")
                    and route.get("task_format") == packet.get("task_format")
                    and route.get("policy_version") == packet.get("policy_version")
                    and route.get("prompt_version") == packet.get("prompt_version")
                    and route.get("schema_version") == packet.get("route_schema_version")
                    and route.get("schema_sha256") == packet.get("schema_sha256")
                )
                if exact and route.get("evidence_supported_state") == "READY" and route.get("evidence_verified") is True:
                    digest = route.get("evidence_sha256")
                    return str(digest) if cls._valid_sha256(digest) else None
        if provider == "openrouter" and packet.get("task_format") == OPENROUTER_TASK_FORMAT:
            routes = snapshot.get("external_evidence", {}).get("openrouter", {}).get("routes", [])
            for route in routes if isinstance(routes, list) else []:
                exact = (
                    route.get("provider") == "openrouter"
                    and route.get("task_format") == OPENROUTER_TASK_FORMAT
                    and route.get("task_id") == packet.get("task_id")
                    and route.get("schema_sha256") == packet.get("schema_sha256")
                    and route.get("request_schema_version") == packet.get("request_schema_version")
                    and route.get("provider_policy_version") == packet.get("provider_policy_version")
                    and route.get("model") == packet.get("model")
                    and route.get("reasoning_effort") == packet.get("reasoning_effort")
                )
                if not exact:
                    continue
                readiness = route.get("readiness_evidence_sha256")
                route_evidence = route.get("route_evidence_sha256")
                budget = route.get("budget_evidence_sha256")
                if (
                    route.get("readiness_supported_state") != "READY"
                    or route.get("evidence_verified") is not True
                    or not cls._valid_sha256(readiness)
                    or not cls._valid_sha256(route_evidence)
                    or not cls._valid_sha256(budget)
                ):
                    continue
                try:
                    released_stage_usd = Decimal(str(route.get("budget_released_stage_usd", "0")))
                    remaining_usd = Decimal(str(route.get("budget_remaining_usd", "0")))
                except InvalidOperation:
                    continue
                if released_stage_usd <= Decimal("0") or remaining_usd <= Decimal("0"):
                    continue
                return sha256_value(
                    {
                        "readiness_evidence_sha256": str(readiness),
                        "route_evidence_sha256": str(route_evidence),
                        "budget_evidence_sha256": str(budget),
                        "budget_remaining_usd": format(remaining_usd, "f"),
                    }
                )
        return None

    def _discover_provider_work(
        self, snapshot: dict[str, Any], moment: datetime
    ) -> list[tuple[ReadyWorkUnit, RouteDecision, dict[str, Any]]]:
        root_value = self.config.provider_work_root
        if root_value is None or not root_value.exists():
            return []
        root = root_value.resolve(strict=True)
        candidates = sorted(
            (path for path in root.rglob("*.json") if 0 < path.stat().st_size <= MAX_PROVIDER_WORK_BYTES),
            key=lambda path: path.relative_to(root).as_posix(),
        )
        if len(candidates) > MAX_PROVIDER_WORK_SCAN_UNITS:
            raise RuntimeError("RUNTIME_INVENTORY_PROVIDER_WORK_SCAN_BOUND_EXCEEDED")
        discovered: list[tuple[ReadyWorkUnit, RouteDecision, dict[str, Any]]] = []
        for source in candidates:
            resolved = source.resolve(strict=True)
            if root not in resolved.parents:
                raise RuntimeError("RUNTIME_INVENTORY_PROVIDER_WORK_OUTSIDE_ALLOWLIST")
            raw = resolved.read_bytes()
            source_sha256 = hashlib.sha256(raw).hexdigest()
            packet = json.loads(raw)
            if not isinstance(packet, dict) or packet.get("schema_version") != 1:
                raise ValueError("RUNTIME_INVENTORY_PROVIDER_PACKET_INVALID")
            if packet.get("authority") != "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES":
                raise ValueError("RUNTIME_INVENTORY_PROVIDER_PACKET_AUTHORITY_INVALID")
            provider = packet.get("provider")
            task_format = packet.get("task_format")
            openrouter_identity_hashes: dict[str, str] | None = None
            if provider == "openai_direct" and task_format == "governed_openai_candidate_v1":
                prefix = "AUTO-OAI-"
                disposition = RoutingDisposition.DIRECT_OPENAI
                model = packet.get("job", {}).get("model")
            elif provider == "openrouter" and task_format == OPENROUTER_TASK_FORMAT:
                task_id = packet.get("task_id")
                authority = packet.get("authority")
                prompt_version = packet.get("prompt_version")
                request_schema_version = packet.get("request_schema_version")
                provider_policy_version = packet.get("provider_policy_version")
                reasoning_effort = packet.get("reasoning_effort")
                max_output_tokens = packet.get("max_output_tokens")
                base_commit = packet.get("base_commit")
                evidence_excerpts = packet.get("evidence_excerpts")
                openrouter_identity_hashes = packet.get("identity_hashes")
                if (
                    not isinstance(task_id, str)
                    or not task_id
                    or not isinstance(authority, str)
                    or not authority
                    or not isinstance(prompt_version, str)
                    or not prompt_version
                    or not isinstance(request_schema_version, str)
                    or not request_schema_version
                    or not isinstance(provider_policy_version, str)
                    or not provider_policy_version
                    or not isinstance(reasoning_effort, str)
                    or not reasoning_effort
                    or not isinstance(max_output_tokens, int)
                    or max_output_tokens <= 0
                    or not isinstance(base_commit, str)
                    or len(base_commit) != 40
                    or any(character not in "0123456789abcdef" for character in base_commit)
                    or base_commit != snapshot.get("git", {}).get("origin_main")
                    or not isinstance(evidence_excerpts, list)
                    or not evidence_excerpts
                    or any(not isinstance(item, str) or not item for item in evidence_excerpts)
                    or not isinstance(openrouter_identity_hashes, dict)
                ):
                    raise ValueError("RUNTIME_INVENTORY_OPENROUTER_PACKET_INVALID")
                required_hashes = {
                    "task_sha256",
                    "schema_sha256",
                    "policy_sha256",
                    "model_sha256",
                    "reasoning_sha256",
                    "source_sha256",
                }
                if set(openrouter_identity_hashes) != required_hashes or not all(
                    self._valid_sha256(openrouter_identity_hashes[key]) for key in required_hashes
                ):
                    raise ValueError("RUNTIME_INVENTORY_OPENROUTER_PACKET_HASHES_INVALID")
                prefix = "AUTO-OR-"
                disposition = RoutingDisposition.OPENROUTER
                model = packet.get("model")
            elif provider == "ollama_local" and task_format == "embedding_dedup_semantic_candidate_retrieval":
                prefix = "AUTO-BGE-"
                disposition = RoutingDisposition.LOCAL_QWEN
                model = packet.get("model")
            elif provider == "remote_cpu_worker" and str(packet.get("task", "")) in CPU_EXACT_ROUTES:
                task = str(packet["task"])
                expected_format, expected_schema, prefix = CPU_EXACT_ROUTES[task]
                payload = packet.get("payload")
                payload_shape_valid = (
                    task == "CANONICAL_JSON"
                    and isinstance(payload, dict)
                    and set(payload) == {"value"}
                ) or (
                    task == "LINE_HASH_MANIFEST"
                    and isinstance(payload, dict)
                    and set(payload) == {"lines"}
                    and isinstance(payload["lines"], list)
                    and bool(payload["lines"])
                    and len(payload["lines"]) <= MAX_RECORDS
                    and all(isinstance(item, str) for item in payload["lines"])
                ) or (
                    task == "EXACT_TEXT_DEDUP"
                    and isinstance(payload, dict)
                    and set(payload) == {"records"}
                    and isinstance(payload["records"], list)
                    and bool(payload["records"])
                    and len(payload["records"]) <= MAX_RECORDS
                    and all(
                        isinstance(item, dict)
                        and set(item) == {"id", "text"}
                        and isinstance(item["id"], str)
                        and bool(item["id"])
                        and isinstance(item["text"], str)
                        for item in payload["records"]
                    )
                    and len({item["id"] for item in payload["records"]})
                    == len(payload["records"])
                )
                if (
                    task_format != expected_format
                    or packet.get("schema_sha256") != expected_schema
                    or not payload_shape_valid
                ):
                    raise ValueError("RUNTIME_INVENTORY_CPU_PROVIDER_PACKET_INVALID")
                disposition = RoutingDisposition.REMOTE_CPU_WORKER
                model = "DETERMINISTIC_CPU_WORKER_V2"
            else:
                raise ValueError("RUNTIME_INVENTORY_PROVIDER_PACKET_ROUTE_INVALID")
            readiness = self._provider_readiness(snapshot, packet)
            if readiness is None:
                raise RuntimeError("RUNTIME_INVENTORY_PROVIDER_EXACT_ROUTE_NOT_READY")
            jira_unit = str(packet.get("jira_unit", ""))
            schema_sha256 = str(packet.get("schema_sha256", ""))
            if not jira_unit or not self._valid_sha256(schema_sha256):
                raise ValueError("RUNTIME_INVENTORY_PROVIDER_PACKET_IDENTITY_INVALID")
            source_hashes = packet.get("source_hashes", [])
            if not isinstance(source_hashes, list) or not source_hashes or not all(self._valid_sha256(item) for item in source_hashes):
                raise ValueError("RUNTIME_INVENTORY_PROVIDER_SOURCE_HASHES_INVALID")
            if provider == "openrouter":
                assert openrouter_identity_hashes is not None
                expected_hashes = {
                    "task_sha256": sha256_value(
                        {
                            "task_id": packet["task_id"],
                            "jira_unit": jira_unit,
                            "authority": packet["authority"],
                        }
                    ),
                    "schema_sha256": sha256_value(
                        {
                            "schema_version": packet["request_schema_version"],
                            "schema_sha256": schema_sha256,
                        }
                    ),
                    "policy_sha256": sha256_value(
                        {
                            "provider_policy_version": packet["provider_policy_version"],
                            "task_format": task_format,
                        }
                    ),
                    "model_sha256": sha256_value({"model": packet.get("model")}),
                    "reasoning_sha256": sha256_value(
                        {
                            "reasoning_effort": packet["reasoning_effort"],
                            "max_output_tokens": packet["max_output_tokens"],
                        }
                    ),
                    "source_sha256": sha256_value(tuple(source_hashes)),
                }
                if openrouter_identity_hashes != expected_hashes:
                    raise ValueError("RUNTIME_INVENTORY_OPENROUTER_IDENTITY_HASH_MISMATCH")
            packet_path, packet_sha256 = _content_addressed_json(self.config.packet_root, "provider-packets", packet)
            work_unit_id = prefix + packet_sha256[:20]
            unit = ReadyWorkUnit(
                work_unit_id=work_unit_id,
                jira_unit=jira_unit,
                task_format=str(task_format),
                schema_sha256=schema_sha256,
                authority="CANDIDATE_ONLY",
                source_hashes=tuple([*source_hashes, source_sha256, packet_sha256]),
                dependencies=tuple(packet.get("dependencies", [])),
                pre_routing_effort_points=int(packet.get("pre_routing_effort_points", 1)),
                scope=str(packet.get("scope", "Governed granular candidate-only provider work")),
            )
            decision = RouteDecision(
                work_unit_id=work_unit_id,
                work_unit_identity=unit.identity(),
                disposition=disposition,
                provider=str(provider),
                model=str(model),
                reason="EXACT_ROUTE_READY_AND_GRANULAR_PACKET_MATERIALIZED",
                decided_at=rfc3339(moment),
            )
            discovered.append((unit, decision, {
                "packet_path": str(packet_path), "packet_sha256": packet_sha256,
                "readiness_evidence_sha256": readiness,
            }))
        states = self.state.work_unit_states({unit.work_unit_id for unit, _, _ in discovered})
        active = [entry for entry in discovered if states.get(entry[0].work_unit_id) != "CLOSED"]
        if len(active) > MAX_PROVIDER_WORK_UNITS:
            raise RuntimeError("RUNTIME_INVENTORY_PROVIDER_WORK_ACTIVE_BOUND_EXCEEDED")
        return active

    @staticmethod
    def _cpu_qualified(snapshot: dict[str, Any]) -> bool:
        return cpu_qualification_evidence_sha256(snapshot) is not None

    def refresh(self, *, now: datetime | None = None) -> dict[str, Any]:
        moment = now or datetime.now(timezone.utc)
        base, base_sha256 = self._load_current_snapshot()
        deployed_release = self._deployed_release()
        if not self._cpu_qualified(base):
            raise RuntimeError("RUNTIME_INVENTORY_CPU_QUALIFICATION_NOT_ESTABLISHED")

        prior_units = {
            item["work_unit_id"]: item
            for item in base.get("work_units", [])
            if str(item.get("work_unit_id", "")).startswith(DYNAMIC_PREFIXES)
        }
        prior_decisions = {
            item["work_unit_id"]: item
            for item in base.get("route_decisions", [])
            if str(item.get("work_unit_id", "")).startswith(DYNAMIC_PREFIXES)
        }
        execution_packets = dict(base.get("execution_packets", {}))
        work_unit_roles = dict(base.get("work_unit_roles", {}))
        if not work_unit_roles:
            work_unit_roles = {
                str(item["work_unit_id"]): ATOMIC_EXECUTABLE
                for item in base.get("work_units", [])
            }
        provider_work_findings: list[dict[str, str]] = []
        try:
            provider_work = self._discover_provider_work(base, moment)
        except (OSError, KeyError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            finding = {
                "finding": type(exc).__name__ + ":" + str(exc)[:240],
                "observed_at": rfc3339(moment),
                "disposition": "PROVIDER_WORK_DEFERRED_CPU_AND_DETERMINISTIC_DISCOVERY_CONTINUES",
            }
            provider_work_findings.append(finding)
            self.state.append_event("PROVIDER_WORK_DISCOVERY_DEFERRED", finding, now=moment)
            provider_work = []
        discovered = [*self._discover(moment), *provider_work]
        for unit, decision, packet in discovered:
            prior_units.setdefault(unit.work_unit_id, asdict(unit))
            prior_decisions.setdefault(
                unit.work_unit_id,
                {**asdict(decision), "disposition": decision.disposition.value},
            )
            execution_packets.setdefault(unit.work_unit_id, packet)
            work_unit_roles.setdefault(unit.work_unit_id, ATOMIC_EXECUTABLE)

        status = self.state.work_unit_states(set(prior_units))
        for work_unit_id, current_state in status.items():
            if current_state == "CLOSED" and prior_decisions[work_unit_id]["disposition"] != RoutingDisposition.COMPLETED.value:
                prior_decisions[work_unit_id] = {
                    **prior_decisions[work_unit_id],
                    "disposition": RoutingDisposition.COMPLETED.value,
                    "provider": None,
                    "model": None,
                    "reason": "CONTROLLER_EXECUTION_CLOSED_WITH_DURABLE_EVIDENCE",
                    "decided_at": rfc3339(moment),
                }

        static_units = [
            item for item in base.get("work_units", [])
            if not str(item.get("work_unit_id", "")).startswith(DYNAMIC_PREFIXES)
        ]
        static_decisions = [
            item for item in base.get("route_decisions", [])
            if not str(item.get("work_unit_id", "")).startswith(DYNAMIC_PREFIXES)
        ]
        work_units = static_units + [prior_units[key] for key in sorted(prior_units)]
        route_decisions = static_decisions + [prior_decisions[key] for key in sorted(prior_decisions)]
        inventory = ReadyWorkInventory(
            [
                ReadyWorkUnit(
                    **{
                        **{key: value for key, value in item.items() if key in READY_WORK_UNIT_FIELDS},
                        "source_hashes": tuple(item["source_hashes"]),
                        "dependencies": tuple(item["dependencies"]),
                    }
                )
                for item in work_units
            ],
            [
                RouteDecision(
                    **{
                        **{key: value for key, value in item.items() if key in ROUTE_DECISION_FIELDS},
                        "disposition": RoutingDisposition(item["disposition"]),
                    }
                )
                for item in route_decisions
            ],
        )
        validation = inventory.validate()
        role_validation = validate_work_unit_roles(inventory.units, work_unit_roles)
        static_base_identity = base.get(
            "static_base_inventory_identity",
            base.get("validation", {}).get("inventory_identity", base_sha256),
        )
        material_identity = sha256_value(
            {
                "base_inventory_identity": static_base_identity,
                "execution_packets": execution_packets,
                "execution_states": status,
                "route_decisions": route_decisions,
                "work_units": work_units,
                "work_unit_roles": work_unit_roles,
                "provider_work_findings": provider_work_findings,
                "deployed_release": deployed_release,
            }
        )
        snapshot = {
            **{key: value for key, value in base.items() if key not in {"generated_at", "validation", "work_units", "work_unit_roles", "work_unit_role_validation", "route_decisions", "execution_packets", "runtime_material_identity", "provider_work_findings", "git", "deployed_release"}},
            "schema_version": 2,
            "artifact_type": "UNIFIED_ASSISTIVE_RUNTIME_INVENTORY",
            "generated_at": rfc3339(moment),
            "runtime_material_identity": material_identity,
            "static_base_inventory_identity": static_base_identity,
            "work_units": work_units,
            "work_unit_roles": work_unit_roles,
            "work_unit_role_validation": role_validation,
            "route_decisions": route_decisions,
            "execution_packets": execution_packets,
            "execution_states": status,
            "provider_work_findings": provider_work_findings,
            "git": (
                {
                    "deployed_head": deployed_release["build_commit"],
                    "merged_main_identity_at_release_build": deployed_release["build_commit"],
                    "status_porcelain_sha256": hashlib.sha256(b"").hexdigest(),
                    "status_evidence": "IMMUTABLE_RELEASE_TREE_NO_WORKTREE_MUTATION_SURFACE",
                    "evidence_scope": deployed_release["evidence_scope"],
                }
                if deployed_release is not None
                else base.get("git")
            ),
            "deployed_release": deployed_release,
            "validation": validation,
            "canonical_or_protected_authority": False,
        }
        if base.get("runtime_material_identity") == material_identity:
            snapshot_sha256 = base_sha256
            snapshot_path = self.config.snapshot_root / "snapshots" / "sha256" / snapshot_sha256 / "inventory.json"
            if not snapshot_path.is_file():
                source = self.config.current_path
                current_payload = _verified_json(source)
                if current_payload.get("artifact_type") == "UNIFIED_ASSISTIVE_INVENTORY_POINTER":
                    source = Path(str(current_payload["snapshot_path"]))
                data = source.read_bytes()
                if hashlib.sha256(data).hexdigest() != snapshot_sha256:
                    raise RuntimeError("RUNTIME_INVENTORY_REUSE_HASH_MISMATCH")
                _atomic_write(snapshot_path, data)
        else:
            data = canonical_json_bytes(snapshot) + b"\n"
            snapshot_sha256 = hashlib.sha256(data).hexdigest()
            snapshot_path = self.config.snapshot_root / "snapshots" / "sha256" / snapshot_sha256 / "inventory.json"
            if snapshot_path.exists():
                if snapshot_path.read_bytes() != data:
                    raise RuntimeError("RUNTIME_INVENTORY_SNAPSHOT_COLLISION")
            else:
                _atomic_write(snapshot_path, data)
        pointer = {
            "schema_version": 2,
            "artifact_type": "UNIFIED_ASSISTIVE_INVENTORY_POINTER",
            "snapshot_path": str(snapshot_path),
            "snapshot_sha256": snapshot_sha256,
            "inventory_identity": validation["inventory_identity"],
            "runtime_material_identity": material_identity,
            "refreshed_at": rfc3339(moment),
        }
        _atomic_write(self.config.current_path, canonical_json_bytes(pointer) + b"\n")
        return {
            "result": "PASS",
            "snapshot_path": str(snapshot_path),
            "snapshot_sha256": snapshot_sha256,
            "inventory_identity": validation["inventory_identity"],
            "runtime_material_identity": material_identity,
            "granular_units": len(prior_units),
            "refreshed_at": pointer["refreshed_at"],
        }
