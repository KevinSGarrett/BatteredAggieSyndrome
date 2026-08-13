from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .contracts import sha256_value
from .controller_state import ControllerState, parse_rfc3339, rfc3339
from .cpu_worker_backend import CpuWorkerClient, CpuWorkerEndpoint, CpuWorkerJob
from .inventory_runtime import cpu_qualification_evidence_sha256
from .ollama_backend import OLLAMA_LOOPBACK_ENDPOINT
from .orchestration import (
    ATOMIC_EXECUTABLE,
    ReadyWorkInventory,
    RoutingDisposition,
    load_inventory,
    validate_work_unit_roles,
)
from .provider_adapters import BgeM3CandidateAdapter, GovernedOpenAIAdapter, ProviderAdapterResult


ROUTABLE_DISPOSITIONS = frozenset(
    {
        RoutingDisposition.DIRECT_OPENAI,
        RoutingDisposition.OPENROUTER,
        RoutingDisposition.CURSOR,
        RoutingDisposition.LOCAL_QWEN,
        RoutingDisposition.REMOTE_CPU_WORKER,
    }
)


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def content_addressed_write(root: Path, category: str, payload: dict[str, Any], *, current_name: str) -> tuple[Path, str]:
    data = canonical_json_bytes(payload)
    digest = hashlib.sha256(data).hexdigest()
    immutable = root / category / "sha256" / digest / "report.json"
    if immutable.exists():
        if immutable.read_bytes() != data:
            raise RuntimeError("CONTENT_ADDRESSED_SCHEDULER_EVIDENCE_COLLISION")
    else:
        atomic_write(immutable, data)
    atomic_write(root / "current" / current_name, data)
    return immutable, digest


@dataclass(frozen=True)
class SchedulerConfig:
    inventory_current_path: Path
    evidence_root: Path
    inventory_max_age_seconds: int = 300
    cycle_interval_seconds: int = 21600
    owner_id: str = "inventory-scheduler"
    cpu_worker_endpoint: str | None = None
    cpu_worker_storage_root: Path | None = None
    cpu_worker_signing_key_path: Path | None = None
    max_dispatch_per_cycle: int = 3
    release_root: Path | None = None
    bge_endpoint: str = OLLAMA_LOOPBACK_ENDPOINT
    openai_enabled: bool = True

    def validate(self) -> None:
        if self.inventory_max_age_seconds <= 0:
            raise ValueError("SCHEDULER_INVENTORY_MAX_AGE_INVALID")
        if self.cycle_interval_seconds <= 0:
            raise ValueError("SCHEDULER_CYCLE_INTERVAL_INVALID")
        if self.max_dispatch_per_cycle <= 0:
            raise ValueError("SCHEDULER_DISPATCH_BOUND_INVALID")
        cpu_fields = (
            self.cpu_worker_endpoint,
            self.cpu_worker_storage_root,
            self.cpu_worker_signing_key_path,
        )
        if any(value is not None for value in cpu_fields) and not all(value is not None for value in cpu_fields):
            raise ValueError("SCHEDULER_CPU_WORKER_CONFIG_INCOMPLETE")


class InventoryScheduler:
    """Fail-closed inventory evaluator; provider dispatch is a separate admitted layer."""

    def __init__(
        self,
        state: ControllerState,
        config: SchedulerConfig,
        *,
        adapters: dict[str, Any] | None = None,
    ) -> None:
        config.validate()
        self.state = state
        self.config = config
        self._adapters = adapters

    def _load(self, now: datetime) -> tuple[dict[str, Any], ReadyWorkInventory, str, float]:
        path = self.config.inventory_current_path
        pointer_data = path.read_bytes()
        pointer = json.loads(pointer_data)
        if pointer.get("artifact_type") == "UNIFIED_ASSISTIVE_INVENTORY_POINTER":
            refreshed_at = parse_rfc3339(str(pointer["refreshed_at"]))
            snapshot_path = Path(str(pointer["snapshot_path"]))
            data = snapshot_path.read_bytes()
            inventory_sha256 = hashlib.sha256(data).hexdigest()
            if inventory_sha256 != pointer.get("snapshot_sha256"):
                raise ValueError("SCHEDULER_INVENTORY_POINTER_HASH_MISMATCH")
            payload = json.loads(data)
            inventory_path = snapshot_path
            freshness_at = refreshed_at
        else:
            data = pointer_data
            inventory_sha256 = hashlib.sha256(data).hexdigest()
            payload = pointer
            inventory_path = path
            freshness_at = parse_rfc3339(str(payload["generated_at"]))
        if not isinstance(payload, dict):
            raise ValueError("SCHEDULER_INVENTORY_NOT_OBJECT")
        age_seconds = max(0.0, (now - freshness_at).total_seconds())
        if freshness_at > now + timedelta(seconds=60):
            raise ValueError("SCHEDULER_INVENTORY_CLOCK_SKEW")
        if age_seconds > self.config.inventory_max_age_seconds:
            raise ValueError("SCHEDULER_INVENTORY_STALE")
        inventory = load_inventory(inventory_path)
        validation = inventory.validate()
        if validation.get("coverage_fraction") != 1.0:
            raise ValueError("SCHEDULER_INVENTORY_COVERAGE_INCOMPLETE")
        if validation != payload.get("validation"):
            raise ValueError("SCHEDULER_INVENTORY_VALIDATION_MISMATCH")
        roles = payload.get("work_unit_roles")
        if roles is not None:
            if not isinstance(roles, dict):
                raise ValueError("SCHEDULER_WORK_UNIT_ROLES_INVALID")
            role_validation = validate_work_unit_roles(inventory.units, roles)
            if role_validation != payload.get("work_unit_role_validation"):
                raise ValueError("SCHEDULER_WORK_UNIT_ROLE_VALIDATION_MISMATCH")
        if payload.get("canonical_or_protected_authority") is not False:
            raise ValueError("SCHEDULER_INVENTORY_AUTHORITY_INVALID")
        git = payload.get("git", {})
        if git.get("head") != git.get("origin_main"):
            raise ValueError("SCHEDULER_INVENTORY_NOT_CURRENT_MAIN")
        if git.get("status_porcelain_sha256") != hashlib.sha256(b"").hexdigest():
            raise ValueError("SCHEDULER_INVENTORY_DIRTY_WORKTREE")
        return payload, inventory, inventory_sha256, age_seconds

    def _cpu_client(self) -> CpuWorkerClient | None:
        if self.config.cpu_worker_endpoint is None:
            return None
        key_path = self.config.cpu_worker_signing_key_path
        storage_root = self.config.cpu_worker_storage_root
        if key_path is None or storage_root is None:
            raise RuntimeError("SCHEDULER_CPU_WORKER_CONFIG_INCOMPLETE")
        key = key_path.read_bytes()
        return CpuWorkerClient(CpuWorkerEndpoint(self.config.cpu_worker_endpoint), storage_root, key)

    def _load_execution_packet(self, payload: dict[str, Any], work_unit_id: str) -> tuple[dict[str, Any], str]:
        reference = payload.get("execution_packets", {}).get(work_unit_id)
        if not isinstance(reference, dict):
            raise RuntimeError("SCHEDULER_EXECUTION_PACKET_MISSING")
        path = Path(str(reference["packet_path"]))
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != reference.get("packet_sha256"):
            raise RuntimeError("SCHEDULER_EXECUTION_PACKET_HASH_MISMATCH")
        packet = json.loads(data)
        if packet.get("authority") != "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES":
            raise RuntimeError("SCHEDULER_EXECUTION_PACKET_AUTHORITY_INVALID")
        return packet, digest

    def _provider_adapters(self) -> dict[str, Any]:
        if self._adapters is not None:
            return self._adapters
        adapters: dict[str, Any] = {"ollama_local": BgeM3CandidateAdapter(self.config.bge_endpoint)}
        if self.config.openai_enabled:
            if self.config.release_root is None:
                raise RuntimeError("SCHEDULER_OPENAI_RELEASE_ROOT_MISSING")
            adapters["openai_direct"] = GovernedOpenAIAdapter(self.config.release_root)
        return adapters

    def _dispatch_cpu(
        self,
        *,
        payload: dict[str, Any],
        work_unit: Any,
        decision: Any,
        moment: datetime,
        client: CpuWorkerClient,
    ) -> dict[str, Any] | None:
        packet, packet_sha256 = self._load_execution_packet(payload, decision.work_unit_id)
        if packet.get("task") not in {"CANONICAL_JSON", "LINE_HASH_MANIFEST", "EXACT_TEXT_DEDUP"}:
            raise RuntimeError("SCHEDULER_CPU_EXECUTION_PACKET_TASK_INVALID")
        route_identity = sha256_value(
            {
                "provider": decision.provider,
                "model": decision.model,
                "task_format": work_unit.task_format,
                "schema_sha256": work_unit.schema_sha256,
                "packet_sha256": packet_sha256,
            }
        )
        return self._dispatch_cpu_after_route(
            payload=payload,
            work_unit=work_unit,
            decision=decision,
            moment=moment,
            client=client,
            packet=packet,
            packet_sha256=packet_sha256,
            route_identity=route_identity,
        )

    def _dispatch_candidate_provider(
        self,
        *,
        payload: dict[str, Any],
        work_unit: Any,
        decision: Any,
        moment: datetime,
        adapter: Any,
    ) -> dict[str, Any] | None:
        packet, packet_sha256 = self._load_execution_packet(payload, decision.work_unit_id)
        reference = payload["execution_packets"][decision.work_unit_id]
        readiness_evidence_sha256 = reference.get("readiness_evidence_sha256")
        if not isinstance(readiness_evidence_sha256, str) or len(readiness_evidence_sha256) != 64:
            raise RuntimeError("SCHEDULER_PROVIDER_READINESS_EVIDENCE_MISSING")
        route_identity = sha256_value({
            "provider": decision.provider,
            "model": decision.model,
            "task_format": work_unit.task_format,
            "schema_sha256": work_unit.schema_sha256,
            "packet_sha256": packet_sha256,
            "readiness_evidence_sha256": readiness_evidence_sha256,
        })
        attempt_number = self.state.dispatch_attempt_count(decision.work_unit_id) + 1
        attempt_id = hashlib.sha256(
            f"{work_unit.identity()}:{route_identity}:attempt-{attempt_number}".encode()
        ).hexdigest()
        lease_id = hashlib.sha256(f"{attempt_id}:lease".encode()).hexdigest()
        claimed = self.state.claim_dispatch(
            work_unit_id=decision.work_unit_id,
            dependencies=work_unit.dependencies,
            lease_id=lease_id,
            attempt_id=attempt_id,
            owner_id=self.config.owner_id,
            provider=str(decision.provider),
            route_identity=route_identity,
            readiness_evidence_sha256=readiness_evidence_sha256,
            now=moment,
        )
        if not claimed:
            return None
        provider_call_attempted = False
        try:
            request = {
                "schema_version": 1,
                "artifact_type": "GOVERNED_PROVIDER_DISPATCH_REQUEST",
                "work_unit_id": decision.work_unit_id,
                "attempt_id": attempt_id,
                "provider": decision.provider,
                "route_identity": route_identity,
                "packet_sha256": packet_sha256,
                "readiness_evidence_sha256": readiness_evidence_sha256,
                "authority": "CANDIDATE_ONLY",
            }
            request_path, request_sha256 = content_addressed_write(
                self.config.evidence_root, "provider-requests", request,
                current_name=f"request-{decision.work_unit_id}.json",
            )
            provider_run_id = hashlib.sha256(f"{attempt_id}:{route_identity}".encode()).hexdigest()
            self.state.record_dispatch(
                work_unit_id=decision.work_unit_id,
                attempt_id=attempt_id,
                provider_run_id=provider_run_id,
                provider=str(decision.provider),
                remote_identity=route_identity,
                request_sha256=request_sha256,
                request_artifact_path=request_path,
                actor=self.config.owner_id,
                resource={"packet_sha256": packet_sha256},
                now=moment,
            )
            result: ProviderAdapterResult = adapter.run(packet)
            provider_call_attempted = bool(result.resource.get("provider_calls", 1))
            result_payload = {
                "schema_version": 1,
                "artifact_type": "GOVERNED_PROVIDER_CANDIDATE_RESULT",
                "work_unit_id": decision.work_unit_id,
                "attempt_id": attempt_id,
                "provider": decision.provider,
                "remote_identity": result.remote_identity,
                "result": result.result,
                "disposition": result.disposition,
                "validation_errors": list(result.validation_errors),
                "actual_cost_usd": result.actual_cost_usd,
                "resource": result.resource,
                "authority": "CANDIDATE_ONLY",
            }
            artifact_path, artifact_sha256 = content_addressed_write(
                self.config.evidence_root, "provider-results", result_payload,
                current_name=f"result-{decision.work_unit_id}.json",
            )
            result_sha256 = sha256_value(result.result)
            completed = datetime.now(timezone.utc)
            self.state.record_result_and_artifact(
                work_unit_id=decision.work_unit_id,
                attempt_id=attempt_id,
                provider_run_id=provider_run_id,
                result_sha256=result_sha256,
                artifact_path=artifact_path,
                actor=self.config.owner_id,
                now=completed,
            )
            validation = {
                "work_unit_id": decision.work_unit_id,
                "attempt_id": attempt_id,
                "packet_sha256": packet_sha256,
                "result_sha256": result_sha256,
                "validation_errors": list(result.validation_errors),
                "authority": result.result.get("authority"),
                "canonical_writes": result.result.get("canonical_writes", 0),
                "protected_decisions": result.result.get("protected_decisions", 0),
            }
            if validation["canonical_writes"] != 0 or validation["protected_decisions"] != 0:
                raise RuntimeError("SCHEDULER_PROVIDER_AUTHORITY_VIOLATION")
            _, validation_sha256 = content_addressed_write(
                self.config.evidence_root, "dispatch-validations", validation,
                current_name=f"validation-{decision.work_unit_id}.json",
            )
            review = {
                "work_unit_id": decision.work_unit_id,
                "attempt_id": attempt_id,
                "disposition": result.disposition,
                "validation_sha256": validation_sha256,
                "candidate_only": True,
            }
            _, review_sha256 = content_addressed_write(
                self.config.evidence_root, "review-queue", review,
                current_name=f"review-{decision.work_unit_id}.json",
            )
            cleanup = {
                "work_unit_id": decision.work_unit_id,
                "attempt_id": attempt_id,
                "action": "NO_RECONSTRUCTIBLE_TEMP_CREATED",
                "bytes_removed": 0,
            }
            _, cleanup_sha256 = content_addressed_write(
                self.config.evidence_root, "cleanup", cleanup,
                current_name=f"cleanup-{decision.work_unit_id}.json",
            )
            self.state.complete_candidate_work(
                work_unit_id=decision.work_unit_id,
                attempt_id=attempt_id,
                lease_id=lease_id,
                validation_sha256=validation_sha256,
                review_sha256=review_sha256,
                cleanup_sha256=cleanup_sha256,
                validator="GOVERNED_PROVIDER_SCHEMA_EVIDENCE_AUTHORITY",
                validation_result="PASS" if not result.validation_errors else "QUARANTINED",
                reviewer="DURABLE_CANDIDATE_REVIEW_QUEUE",
                disposition=result.disposition,
                actual_cost_usd=result.actual_cost_usd,
                settlement_reason="AUTHORITATIVE_PROVIDER_LEDGER_RECONCILED",
                cleanup_action="NO_RECONSTRUCTIBLE_TEMP_CREATED",
                resource={**result.resource, "actual_cost_usd_exact": result.actual_cost_usd, "remote_identity": result.remote_identity},
                actor=self.config.owner_id,
                now=completed,
            )
            return {
                "work_unit_id": decision.work_unit_id,
                "provider": decision.provider,
                "attempt_id": attempt_id,
                "provider_run_id": provider_run_id,
                "result_sha256": result_sha256,
                "artifact_path": str(artifact_path),
                "artifact_sha256": artifact_sha256,
                "review_disposition": result.disposition,
                "actual_cost_usd": result.actual_cost_usd,
                "provider_call_attempted": provider_call_attempted,
            }
        except Exception as exc:
            retryable_names = {"APIConnectionError", "APITimeoutError", "TimeoutError", "URLError"}
            retryable = attempt_number < 3 and (isinstance(exc, (OSError, TimeoutError)) or exc.__class__.__name__ in retryable_names)
            self.state.record_dispatch_failure(
                work_unit_id=decision.work_unit_id,
                attempt_id=attempt_id,
                lease_id=lease_id,
                error_code=type(exc).__name__ + ":" + str(exc)[:240],
                actor=self.config.owner_id,
                retryable=retryable,
                now=moment,
            )
            return {
                "work_unit_id": decision.work_unit_id,
                "provider": decision.provider,
                "attempt_id": attempt_id,
                "failed": True,
                "retryable": retryable,
                "provider_call_attempted": provider_call_attempted,
                "finding": type(exc).__name__ + ":" + str(exc)[:240],
            }

    def _dispatch_cpu_after_route(
        self,
        *,
        payload: dict[str, Any],
        work_unit: Any,
        decision: Any,
        moment: datetime,
        client: CpuWorkerClient,
        packet: dict[str, Any],
        packet_sha256: str,
        route_identity: str,
    ) -> dict[str, Any] | None:
        readiness_evidence_sha256 = cpu_qualification_evidence_sha256(payload)
        if readiness_evidence_sha256 is None:
            raise RuntimeError("SCHEDULER_CPU_QUALIFICATION_NOT_ESTABLISHED")
        attempt_number = self.state.dispatch_attempt_count(decision.work_unit_id) + 1
        attempt_id = hashlib.sha256(
            f"{work_unit.identity()}:{route_identity}:attempt-{attempt_number}".encode()
        ).hexdigest()
        lease_id = hashlib.sha256(f"{attempt_id}:lease".encode()).hexdigest()
        claimed = self.state.claim_dispatch(
            work_unit_id=decision.work_unit_id,
            dependencies=work_unit.dependencies,
            lease_id=lease_id,
            attempt_id=attempt_id,
            owner_id=self.config.owner_id,
            provider=str(decision.provider),
            route_identity=route_identity,
            readiness_evidence_sha256=readiness_evidence_sha256,
            now=moment,
        )
        if not claimed:
            return None
        provider_call_attempted = False
        try:
            job = CpuWorkerJob(
                task=str(packet["task"]),
                payload=dict(packet["payload"]),
                jira_unit=str(packet["jira_unit"]),
            )
            request_payload = job.request(client.signing_key, issued_at=moment, nonce=attempt_id[:32])
            request_sha256 = sha256_value(request_payload)
            request_artifact_path, _ = content_addressed_write(
                self.config.evidence_root,
                "provider-requests",
                request_payload,
                current_name=f"request-{decision.work_unit_id}.json",
            )
            provider_run_id = hashlib.sha256(f"{attempt_id}:{job.identity()}".encode()).hexdigest()
            self.state.record_dispatch(
                work_unit_id=decision.work_unit_id,
                attempt_id=attempt_id,
                provider_run_id=provider_run_id,
                provider=str(decision.provider),
                remote_identity=job.identity(),
                request_sha256=request_sha256,
                request_artifact_path=request_artifact_path,
                actor=self.config.owner_id,
                now=moment,
            )
            provider_call_attempted = True
            response, artifact_path = client.submit(job, request_payload)
            result_sha256 = sha256_value(response["result"])
            completed = datetime.now(timezone.utc)
            self.state.record_result_and_artifact(
                work_unit_id=decision.work_unit_id,
                attempt_id=attempt_id,
                provider_run_id=provider_run_id,
                result_sha256=result_sha256,
                artifact_path=artifact_path,
                actor=self.config.owner_id,
                now=completed,
            )
            validation = {
                "work_unit_id": decision.work_unit_id,
                "attempt_id": attempt_id,
                "packet_sha256": packet_sha256,
                "result_sha256": result_sha256,
                "exact_local_replay": True,
                "canonical_writes": response["canonical_writes"],
                "protected_decisions": response["protected_decisions"],
            }
            _, validation_sha256 = content_addressed_write(
                self.config.evidence_root, "dispatch-validations", validation,
                current_name=f"validation-{decision.work_unit_id}.json",
            )
            review = {
                "work_unit_id": decision.work_unit_id,
                "attempt_id": attempt_id,
                "disposition": "REVIEW_ONLY",
                "reason": "EXACT_DETERMINISTIC_QA_NO_AUTHORITATIVE_MUTATION",
                "validation_sha256": validation_sha256,
            }
            _, review_sha256 = content_addressed_write(
                self.config.evidence_root, "review-queue", review,
                current_name=f"review-{decision.work_unit_id}.json",
            )
            cleanup = {
                "work_unit_id": decision.work_unit_id,
                "attempt_id": attempt_id,
                "action": "NO_RECONSTRUCTIBLE_TEMP_CREATED",
                "bytes_removed": 0,
            }
            _, cleanup_sha256 = content_addressed_write(
                self.config.evidence_root, "cleanup", cleanup,
                current_name=f"cleanup-{decision.work_unit_id}.json",
            )
            self.state.complete_validated_review_only(
                work_unit_id=decision.work_unit_id,
                attempt_id=attempt_id,
                lease_id=lease_id,
                validation_sha256=validation_sha256,
                review_sha256=review_sha256,
                cleanup_sha256=cleanup_sha256,
                actor=self.config.owner_id,
                now=completed,
            )
            return {
                "work_unit_id": decision.work_unit_id,
                "provider": decision.provider,
                "attempt_id": attempt_id,
                "provider_run_id": provider_run_id,
                "result_sha256": result_sha256,
                "artifact_path": str(artifact_path),
                "review_disposition": "REVIEW_ONLY",
                "provider_call_attempted": True,
            }
        except Exception as exc:
            retryable = attempt_number < 3 and isinstance(exc, (OSError, TimeoutError, RuntimeError))
            self.state.record_dispatch_failure(
                work_unit_id=decision.work_unit_id,
                attempt_id=attempt_id,
                lease_id=lease_id,
                error_code=type(exc).__name__ + ":" + str(exc)[:240],
                actor=self.config.owner_id,
                retryable=retryable,
                now=moment,
            )
            return {
                "work_unit_id": decision.work_unit_id,
                "provider": decision.provider,
                "attempt_id": attempt_id,
                "failed": True,
                "retryable": retryable,
                "provider_call_attempted": provider_call_attempted,
                "finding": type(exc).__name__ + ":" + str(exc)[:240],
            }

    def _cycle_due(self, inventory_sha256: str, now: datetime) -> bool:
        status = self.state.status()
        latest = status.get("scheduler_latest_cycle")
        if latest is None or latest["inventory_sha256"] != inventory_sha256:
            return True
        completed = parse_rfc3339(latest["completed_at"])
        return (now - completed).total_seconds() >= self.config.cycle_interval_seconds

    def evaluate(self, *, now: datetime | None = None) -> dict[str, Any]:
        moment = now or datetime.now(timezone.utc)
        observed_at = rfc3339(moment)
        try:
            payload, inventory, inventory_sha256, age_seconds = self._load(moment)
        except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
            report = {
                "schema_version": 1,
                "artifact_type": "UNIFIED_ASSISTIVE_SCHEDULER_EVALUATION",
                "observed_at": observed_at,
                "result": "BLOCKED",
                "finding": str(exc),
                "inventory_path": str(self.config.inventory_current_path),
                "provider_calls": 0,
                "cycle_recorded": False,
                "dispatch_engine_state": "INVENTORY_SCHEDULER_BLOCKED",
                "operational_completion": "INCOMPLETE",
            }
            _, evidence_sha256 = content_addressed_write(
                self.config.evidence_root, "scheduler-evaluations", report, current_name="scheduler-evaluation.json"
            )
            self.state.append_event(
                "SCHEDULER_INVENTORY_BLOCKED",
                {"finding": str(exc), "evidence_sha256": evidence_sha256},
                now=moment,
            )
            report["evidence_sha256"] = evidence_sha256
            return report

        units = {unit.work_unit_id: unit for unit in inventory.units}
        try:
            for unit in inventory.units:
                self.state.register_work_unit(
                    work_unit_id=unit.work_unit_id,
                    identity_sha256=unit.identity(),
                    jira_identity=unit.jira_unit,
                    effort_points=unit.pre_routing_effort_points,
                    actor="inventory-scheduler",
                    inventory_sha256=inventory_sha256,
                    now=moment,
                )
        except RuntimeError as exc:
            if str(exc) not in {
                "IMMUTABLE_ACTIVE_WORK_UNIT_IDENTITY_CONFLICT",
                "WORK_UNIT_REVISION_REAPPEARANCE_CONFLICT",
            }:
                raise
            report = {
                "schema_version": 1,
                "artifact_type": "UNIFIED_ASSISTIVE_SCHEDULER_EVALUATION",
                "observed_at": observed_at,
                "result": "BLOCKED",
                "finding": str(exc),
                "inventory_path": str(self.config.inventory_current_path),
                "inventory_sha256": inventory_sha256,
                "provider_calls": 0,
                "cycle_recorded": False,
                "dispatch_engine_state": "INVENTORY_WORK_UNIT_REVISION_BLOCKED",
                "operational_completion": "INCOMPLETE",
            }
            _, evidence_sha256 = content_addressed_write(
                self.config.evidence_root,
                "scheduler-evaluations",
                report,
                current_name="scheduler-evaluation.json",
            )
            self.state.append_event(
                "SCHEDULER_WORK_UNIT_REVISION_BLOCKED",
                {"finding": str(exc), "inventory_sha256": inventory_sha256, "evidence_sha256": evidence_sha256},
                now=moment,
            )
            report["evidence_sha256"] = evidence_sha256
            return report
        eligible = [
            decision
            for decision in inventory.decisions
            if (
                decision.disposition in ROUTABLE_DISPOSITIONS
                and decision.provider
                and payload.get("work_unit_roles", {}).get(
                    decision.work_unit_id, ATOMIC_EXECUTABLE
                ) == ATOMIC_EXECUTABLE
            )
        ]
        cycle_due = self._cycle_due(inventory_sha256, moment)
        dispatched: list[dict[str, Any]] = []
        provider_calls = 0
        cpu_client = self._cpu_client()
        provider_packets_present = any(
            decision.disposition is not RoutingDisposition.REMOTE_CPU_WORKER
            and decision.work_unit_id in payload.get("execution_packets", {})
            for decision in eligible
        )
        adapters = self._provider_adapters() if cycle_due and provider_packets_present else {}
        if cycle_due:
            for decision in eligible:
                if len(dispatched) >= self.config.max_dispatch_per_cycle:
                    break
                if decision.work_unit_id not in payload.get("execution_packets", {}):
                    continue
                try:
                    if decision.disposition is RoutingDisposition.REMOTE_CPU_WORKER:
                        if cpu_client is None:
                            continue
                        result = self._dispatch_cpu(
                            payload=payload,
                            work_unit=units[decision.work_unit_id],
                            decision=decision,
                            moment=moment,
                            client=cpu_client,
                        )
                    elif decision.provider in adapters:
                        result = self._dispatch_candidate_provider(
                            payload=payload,
                            work_unit=units[decision.work_unit_id],
                            decision=decision,
                            moment=moment,
                            adapter=adapters[str(decision.provider)],
                        )
                    else:
                        continue
                except (OSError, KeyError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                    result = {
                        "work_unit_id": decision.work_unit_id,
                        "provider": decision.provider,
                        "failed": True,
                        "retryable": False,
                        "provider_call_attempted": False,
                        "finding": type(exc).__name__ + ":" + str(exc)[:240],
                    }
                if result is not None:
                    dispatched.append(result)
                    provider_calls += int(bool(result.get("provider_call_attempted")))
        outcomes = dispatched
        failures = [item for item in outcomes if item.get("failed")]
        successful_dispatches = [item for item in outcomes if not item.get("failed")]
        dispatched_ids = {item["work_unit_id"] for item in outcomes}
        current_states = self.state.work_unit_states(set(units))
        idle_units = []
        for decision in eligible:
            if decision.work_unit_id in dispatched_ids or current_states.get(decision.work_unit_id) in {"CLOSED", "RETRY_WAIT", "FAILED"}:
                continue
            reason = "PROVIDER_DISPATCH_ADAPTER_NOT_INSTALLED_IN_ACTIVE_RELEASE"
            if decision.disposition is RoutingDisposition.REMOTE_CPU_WORKER:
                if cpu_client is None:
                    reason = "CPU_WORKER_ADAPTER_NOT_CONFIGURED"
                elif decision.work_unit_id not in payload.get("execution_packets", {}):
                    reason = "EXECUTION_PACKET_NOT_MATERIALIZED"
                elif not cycle_due:
                    reason = "SCHEDULER_CYCLE_INTERVAL_NOT_DUE"
                else:
                    reason = "BOUNDED_DISPATCH_CAPACITY_DEFERRED"
            elif decision.work_unit_id not in payload.get("execution_packets", {}):
                reason = "EXECUTION_PACKET_NOT_MATERIALIZED"
            elif not cycle_due:
                reason = "SCHEDULER_CYCLE_INTERVAL_NOT_DUE"
            elif decision.provider not in adapters:
                reason = "PROVIDER_DISPATCH_ADAPTER_NOT_CONFIGURED"
            else:
                reason = "BOUNDED_DISPATCH_CAPACITY_DEFERRED"
            idle_units.append({
                "work_unit_id": decision.work_unit_id,
                "provider": decision.provider,
                "disposition": decision.disposition.value,
                "effort_points": units[decision.work_unit_id].pre_routing_effort_points,
                "reason": reason,
            })
        cycle_seed = f"{inventory_sha256}:{observed_at}".encode("utf-8")
        cycle_id = hashlib.sha256(cycle_seed).hexdigest()
        report = {
            "schema_version": 1,
            "artifact_type": "UNIFIED_ASSISTIVE_SCHEDULER_EVALUATION",
            "observed_at": observed_at,
            "result": "FAIL" if failures and not successful_dispatches else "INCOMPLETE" if failures or idle_units else "PASS",
            "inventory_path": str(self.config.inventory_current_path),
            "inventory_sha256": inventory_sha256,
            "inventory_age_seconds": age_seconds,
            "inventory_identity": payload["validation"]["inventory_identity"],
            "work_unit_count": len(inventory.units),
            "eligible_units": len(eligible),
            "campaign_owner_units": sum(
                role == "CAMPAIGN_OWNER"
                for role in payload.get("work_unit_roles", {}).values()
            ),
            "qualification_record_units": sum(
                role == "QUALIFICATION_RECORD"
                for role in payload.get("work_unit_roles", {}).values()
            ),
            "eligible_effort_points": sum(item["effort_points"] for item in idle_units),
            "dispatched_units": len(dispatched),
            "provider_calls": provider_calls,
            "dispatched": dispatched,
            "failures": failures,
            "idle_units": idle_units,
            "cycle_due": cycle_due,
            "cycle_recorded": cycle_due,
            "cycle_id": cycle_id if cycle_due else None,
            "no_change": not eligible,
            "dispatch_engine_state": (
                "INVENTORY_SCHEDULER_CONTROLLER_ROUTED_DISPATCH_ACTIVE"
                if dispatched else "INVENTORY_SCHEDULER_ACTIVE_PROVIDER_DISPATCH_PENDING"
            ),
            "operational_completion": "INCOMPLETE",
        }
        _, evidence_sha256 = content_addressed_write(
            self.config.evidence_root, "scheduler-evaluations", report, current_name="scheduler-evaluation.json"
        )
        active_idle_ids: set[str] = set()
        for item in idle_units:
            idle_id = hashlib.sha256(
                f"{item['work_unit_id']}:{inventory_sha256}:{item['provider']}:{item['reason']}:{observed_at}".encode("utf-8")
            ).hexdigest()
            self.state.record_idle_interval(
                idle_id=idle_id,
                work_unit_id=item["work_unit_id"],
                inventory_sha256=inventory_sha256,
                provider=str(item["provider"]),
                reason=item["reason"],
                evidence_sha256=evidence_sha256,
                now=moment,
            )
            active_idle_ids.add(item["work_unit_id"])
        self.state.resolve_idle_intervals(active_idle_ids, now=moment)
        if cycle_due:
            self.state.record_cycle(
                cycle_id=cycle_id,
                inventory_sha256=inventory_sha256,
                eligible_units=len(eligible),
                dispatched_units=len(dispatched),
                no_change=not eligible,
                result=(
                    "FAIL_CONTROLLER_ROUTED_DISPATCH"
                    if failures and not successful_dispatches else
                    "INCOMPLETE_CONTROLLER_ROUTED_DISPATCH_FAILURES"
                    if failures else
                    "PASS_CONTROLLER_ROUTED_DISPATCH"
                    if dispatched and not idle_units else
                    "INCOMPLETE_PARTIAL_CONTROLLER_ROUTED_DISPATCH"
                    if dispatched else
                    "INCOMPLETE_IDLE_WITH_READY_WORK"
                    if idle_units else "PASS_NO_CHANGE_ZERO_CALLS"
                ),
                evidence_sha256=evidence_sha256,
                now=moment,
            )
        report["evidence_sha256"] = evidence_sha256
        return report
