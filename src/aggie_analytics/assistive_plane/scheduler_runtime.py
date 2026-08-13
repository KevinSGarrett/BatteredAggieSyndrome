from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .controller_state import ControllerState, parse_rfc3339, rfc3339
from .orchestration import ReadyWorkInventory, RoutingDisposition, load_inventory


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

    def validate(self) -> None:
        if self.inventory_max_age_seconds <= 0:
            raise ValueError("SCHEDULER_INVENTORY_MAX_AGE_INVALID")
        if self.cycle_interval_seconds <= 0:
            raise ValueError("SCHEDULER_CYCLE_INTERVAL_INVALID")


class InventoryScheduler:
    """Fail-closed inventory evaluator; provider dispatch is a separate admitted layer."""

    def __init__(self, state: ControllerState, config: SchedulerConfig) -> None:
        config.validate()
        self.state = state
        self.config = config

    def _load(self, now: datetime) -> tuple[dict[str, Any], ReadyWorkInventory, str, float]:
        path = self.config.inventory_current_path
        data = path.read_bytes()
        inventory_sha256 = hashlib.sha256(data).hexdigest()
        payload = json.loads(data)
        if not isinstance(payload, dict):
            raise ValueError("SCHEDULER_INVENTORY_NOT_OBJECT")
        generated_at = parse_rfc3339(str(payload["generated_at"]))
        age_seconds = max(0.0, (now - generated_at).total_seconds())
        if generated_at > now + timedelta(seconds=60):
            raise ValueError("SCHEDULER_INVENTORY_CLOCK_SKEW")
        if age_seconds > self.config.inventory_max_age_seconds:
            raise ValueError("SCHEDULER_INVENTORY_STALE")
        inventory = load_inventory(path)
        validation = inventory.validate()
        if validation.get("coverage_fraction") != 1.0:
            raise ValueError("SCHEDULER_INVENTORY_COVERAGE_INCOMPLETE")
        if validation != payload.get("validation"):
            raise ValueError("SCHEDULER_INVENTORY_VALIDATION_MISMATCH")
        if payload.get("canonical_or_protected_authority") is not False:
            raise ValueError("SCHEDULER_INVENTORY_AUTHORITY_INVALID")
        git = payload.get("git", {})
        if git.get("head") != git.get("origin_main"):
            raise ValueError("SCHEDULER_INVENTORY_NOT_CURRENT_MAIN")
        if git.get("status_porcelain_sha256") != hashlib.sha256(b"").hexdigest():
            raise ValueError("SCHEDULER_INVENTORY_DIRTY_WORKTREE")
        return payload, inventory, inventory_sha256, age_seconds

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
        for unit in inventory.units:
            self.state.register_work_unit(
                work_unit_id=unit.work_unit_id,
                identity_sha256=unit.identity(),
                jira_identity=unit.jira_unit,
                effort_points=unit.pre_routing_effort_points,
                actor="inventory-scheduler",
                now=moment,
            )
        eligible = [
            decision
            for decision in inventory.decisions
            if decision.disposition in ROUTABLE_DISPOSITIONS and decision.provider
        ]
        idle_units = [
            {
                "work_unit_id": decision.work_unit_id,
                "provider": decision.provider,
                "disposition": decision.disposition.value,
                "effort_points": units[decision.work_unit_id].pre_routing_effort_points,
                "reason": "PROVIDER_DISPATCH_ADAPTER_NOT_INSTALLED_IN_ACTIVE_RELEASE",
            }
            for decision in eligible
        ]
        cycle_due = self._cycle_due(inventory_sha256, moment)
        cycle_seed = f"{inventory_sha256}:{observed_at}".encode("utf-8")
        cycle_id = hashlib.sha256(cycle_seed).hexdigest()
        report = {
            "schema_version": 1,
            "artifact_type": "UNIFIED_ASSISTIVE_SCHEDULER_EVALUATION",
            "observed_at": observed_at,
            "result": "INCOMPLETE" if idle_units else "PASS",
            "inventory_path": str(self.config.inventory_current_path),
            "inventory_sha256": inventory_sha256,
            "inventory_age_seconds": age_seconds,
            "inventory_identity": payload["validation"]["inventory_identity"],
            "work_unit_count": len(inventory.units),
            "eligible_units": len(eligible),
            "eligible_effort_points": sum(item["effort_points"] for item in idle_units),
            "dispatched_units": 0,
            "provider_calls": 0,
            "idle_units": idle_units,
            "cycle_due": cycle_due,
            "cycle_recorded": cycle_due,
            "cycle_id": cycle_id if cycle_due else None,
            "no_change": not eligible,
            "dispatch_engine_state": "INVENTORY_SCHEDULER_ACTIVE_PROVIDER_DISPATCH_PENDING",
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
                dispatched_units=0,
                no_change=not eligible,
                result="INCOMPLETE_IDLE_WITH_READY_WORK" if idle_units else "PASS_NO_CHANGE_ZERO_CALLS",
                evidence_sha256=evidence_sha256,
                now=moment,
            )
        report["evidence_sha256"] = evidence_sha256
        return report
