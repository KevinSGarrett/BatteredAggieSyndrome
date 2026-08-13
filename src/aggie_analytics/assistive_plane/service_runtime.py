from __future__ import annotations

import hashlib
import json
import os
import socket
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .controller_state import ControllerState, LeaderLock, rfc3339
from .inventory_runtime import RuntimeInventoryConfig, RuntimeInventoryRefresher
from .scheduler_runtime import InventoryScheduler, SchedulerConfig
from .watchdog import ReadOnlyWatchdog


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


class ContentAddressedReportStore:
    """Immutable evidence plus a replaceable pointer to the latest observation."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def write(self, category: str, payload: dict[str, Any], *, current_name: str) -> tuple[Path, str]:
        data = canonical_json_bytes(payload)
        digest = hashlib.sha256(data).hexdigest()
        immutable = self.root / category / "sha256" / digest / "report.json"
        if immutable.exists():
            if immutable.read_bytes() != data:
                raise RuntimeError("CONTENT_ADDRESSED_REPORT_COLLISION")
        else:
            atomic_write(immutable, data)
        atomic_write(self.root / "current" / current_name, data)
        return immutable, digest


@dataclass(frozen=True)
class ControllerServiceConfig:
    runtime_root: Path
    owner_id: str
    build_commit: str
    heartbeat_seconds: float = 30.0
    queue_evaluation_seconds: float = 60.0
    lease_ttl_seconds: int = 120
    inventory_current_path: Path | None = None
    inventory_max_age_seconds: int = 300
    scheduler_cycle_interval_seconds: int = 21600
    inventory_refresh_max_age_seconds: int = 240
    cpu_worker_endpoint: str | None = "https://comfy-v4-cpu-01.tail9b05ab.ts.net"
    cpu_worker_signing_key_path: Path | None = None
    max_dispatch_per_cycle: int = 3

    def validate(self) -> None:
        if self.heartbeat_seconds <= 0 or self.heartbeat_seconds >= self.lease_ttl_seconds:
            raise ValueError("CONTROLLER_HEARTBEAT_INTERVAL_INVALID")
        if self.queue_evaluation_seconds <= 0:
            raise ValueError("CONTROLLER_QUEUE_INTERVAL_INVALID")
        if self.inventory_max_age_seconds <= 0 or self.scheduler_cycle_interval_seconds <= 0:
            raise ValueError("CONTROLLER_SCHEDULER_INTERVAL_INVALID")
        if self.inventory_refresh_max_age_seconds <= 0 or self.max_dispatch_per_cycle <= 0:
            raise ValueError("CONTROLLER_EXECUTION_BOUND_INVALID")
        if len(self.build_commit) != 40 or any(character not in "0123456789abcdef" for character in self.build_commit.lower()):
            raise ValueError("CONTROLLER_BUILD_COMMIT_INVALID")


class ControllerService:
    """Long-lived leader with a fail-closed inventory scheduler and honest dispatch boundary."""

    def __init__(self, config: ControllerServiceConfig) -> None:
        config.validate()
        self.config = config
        self.database = config.runtime_root / "state" / "orchestrator.sqlite3"
        self.state = ControllerState(self.database)
        self.store = ContentAddressedReportStore(config.runtime_root / "evidence")
        inventory_path = config.inventory_current_path or (
            config.runtime_root.parent / "inventory" / "current" / "inventory.json"
        )
        data_root = config.runtime_root.parents[1]
        cpu_worker_root = config.runtime_root.parent / "cpu_worker"
        signing_key_path = config.cpu_worker_signing_key_path or (
            cpu_worker_root / "controller" / "secrets" / "worker-v2.bin"
        )
        self.inventory_refresher = RuntimeInventoryRefresher(
            self.state,
            RuntimeInventoryConfig(
                current_path=inventory_path,
                snapshot_root=config.runtime_root.parent / "inventory" / "runtime",
                packet_root=config.runtime_root,
                manifests_root=data_root / "manifests",
                refresh_max_age_seconds=config.inventory_refresh_max_age_seconds,
            ),
        )
        self.scheduler = InventoryScheduler(
            self.state,
            SchedulerConfig(
                inventory_current_path=inventory_path,
                evidence_root=config.runtime_root / "evidence",
                inventory_max_age_seconds=config.inventory_max_age_seconds,
                cycle_interval_seconds=config.scheduler_cycle_interval_seconds,
                owner_id=config.owner_id,
                cpu_worker_endpoint=config.cpu_worker_endpoint,
                cpu_worker_storage_root=cpu_worker_root,
                cpu_worker_signing_key_path=signing_key_path,
                max_dispatch_per_cycle=config.max_dispatch_per_cycle,
            ),
        )

    def _heartbeat_payload(
        self,
        *,
        started_at: str,
        sequence: int,
        queue_evaluations: int,
        last_scheduler_evaluation: dict[str, Any] | None,
        last_inventory_refresh: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        status = self.state.status()
        scheduler = last_scheduler_evaluation or {}
        return {
            "schema_version": 1,
            "artifact_type": "UNIFIED_ASSISTIVE_CONTROLLER_HEARTBEAT",
            "observed_at": rfc3339(datetime.now(timezone.utc)),
            "started_at": started_at,
            "owner_id": self.config.owner_id,
            "hostname": socket.gethostname(),
            "process_id": os.getpid(),
            "build_commit": self.config.build_commit,
            "heartbeat_sequence": sequence,
            "queue_evaluation_observations": queue_evaluations,
            "real_scheduler_cycles_recorded_by_service": status["scheduler_cycles"],
            "scheduler_dispatched_units": status["scheduler_dispatched_units"],
            "scheduler_active_idle_intervals": status["active_idle_intervals"],
            "scheduler_last_result": scheduler.get("result", "NOT_YET_EVALUATED"),
            "scheduler_inventory_sha256": scheduler.get("inventory_sha256"),
            "scheduler_eligible_units": scheduler.get("eligible_units", 0),
            "scheduler_provider_calls": scheduler.get("provider_calls", 0),
            "scheduler_inventory_refresh": last_inventory_refresh,
            "dispatch_engine_state": scheduler.get(
                "dispatch_engine_state", "INVENTORY_SCHEDULER_WAITING_FOR_FIRST_EVALUATION"
            ),
            "operational_completion": "INCOMPLETE",
            "database": {
                "journal_mode": status["journal_mode"],
                "integrity_check": status["integrity_check"],
                "schema_version": status["schema_version"],
            },
        }

    def run(self, stop_event: threading.Event, *, maximum_runtime_seconds: float | None = None) -> dict[str, Any]:
        started_monotonic = time.monotonic()
        started_at = rfc3339(datetime.now(timezone.utc))
        heartbeat_sequence = 0
        queue_evaluations = 0
        next_heartbeat = started_monotonic
        next_queue_observation = started_monotonic
        last_scheduler_evaluation: dict[str, Any] | None = None
        last_inventory_refresh: dict[str, Any] | None = None
        completed_normally = False
        lock = LeaderLock(self.config.runtime_root / "runtime" / "controller.lock")
        self.state.initialize()
        with lock:
            self.state.acquire_leader(
                self.config.owner_id,
                self.config.build_commit,
                ttl_seconds=self.config.lease_ttl_seconds,
            )
            self.state.append_event(
                "CONTROLLER_SERVICE_STARTED",
                {
                    "owner_id": self.config.owner_id,
                    "build_commit": self.config.build_commit,
                    "pid": os.getpid(),
                    "hostname": socket.gethostname(),
                },
            )
            try:
                while not stop_event.is_set():
                    moment = time.monotonic()
                    remaining_runtime = (
                        None
                        if maximum_runtime_seconds is None
                        else maximum_runtime_seconds - (moment - started_monotonic)
                    )
                    queue_budget_available = remaining_runtime is None or remaining_runtime >= min(
                        1.0, self.config.queue_evaluation_seconds
                    )
                    if moment >= next_queue_observation and queue_budget_available:
                        queue_evaluations += 1
                        try:
                            last_inventory_refresh = self.inventory_refresher.refresh()
                        except (OSError, KeyError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                            last_inventory_refresh = {
                                "result": "BLOCKED",
                                "finding": str(exc),
                                "refreshed_at": rfc3339(datetime.now(timezone.utc)),
                            }
                            self.state.append_event(
                                "RUNTIME_INVENTORY_REFRESH_BLOCKED",
                                {"finding": str(exc)},
                            )
                        last_scheduler_evaluation = self.scheduler.evaluate()
                        next_queue_observation = moment + self.config.queue_evaluation_seconds
                    if moment >= next_heartbeat:
                        self.state.heartbeat(
                            self.config.owner_id,
                            ttl_seconds=self.config.lease_ttl_seconds,
                        )
                        heartbeat_sequence += 1
                        self.store.write(
                            "controller-heartbeats",
                            self._heartbeat_payload(
                                started_at=started_at,
                                sequence=heartbeat_sequence,
                                queue_evaluations=queue_evaluations,
                                last_scheduler_evaluation=last_scheduler_evaluation,
                                last_inventory_refresh=last_inventory_refresh,
                            ),
                            current_name="controller-heartbeat.json",
                        )
                        next_heartbeat = moment + self.config.heartbeat_seconds
                    if maximum_runtime_seconds is not None and moment - started_monotonic >= maximum_runtime_seconds:
                        break
                    delay_candidates = [next_heartbeat - moment, next_queue_observation - moment, 0.25]
                    wait_timeout = max(0.01, min(delay_candidates))
                    if maximum_runtime_seconds is not None:
                        remaining_runtime = maximum_runtime_seconds - (time.monotonic() - started_monotonic)
                        if remaining_runtime <= 0:
                            break
                        wait_timeout = min(wait_timeout, remaining_runtime)
                    stop_event.wait(wait_timeout)
                completed_normally = True
            finally:
                self.state.append_event(
                    "CONTROLLER_SERVICE_STOPPED",
                    {
                        "owner_id": self.config.owner_id,
                        "build_commit": self.config.build_commit,
                        "graceful": completed_normally,
                    },
                )
                self.state.release_leader(self.config.owner_id)
        report = {
            "result": "PASS",
            "service": "controller",
            "shutdown": "GRACEFUL",
            "heartbeat_count": heartbeat_sequence,
            "queue_observation_count": queue_evaluations,
            "real_scheduler_cycles": self.state.status()["scheduler_cycles"],
            "operational_completion": "INCOMPLETE",
        }
        self.store.write("controller-service-events", report, current_name="controller-service-last-exit.json")
        return report


@dataclass(frozen=True)
class WatchdogServiceConfig:
    runtime_root: Path
    build_commit: str
    interval_seconds: float = 300.0
    heartbeat_max_age_seconds: int = 90

    def validate(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("WATCHDOG_INTERVAL_INVALID")
        if self.heartbeat_max_age_seconds <= 0:
            raise ValueError("WATCHDOG_HEARTBEAT_MAX_AGE_INVALID")
        if len(self.build_commit) != 40:
            raise ValueError("WATCHDOG_BUILD_COMMIT_INVALID")


class WatchdogService:
    def __init__(self, config: WatchdogServiceConfig) -> None:
        config.validate()
        self.config = config
        self.database = config.runtime_root / "state" / "orchestrator.sqlite3"
        self.store = ContentAddressedReportStore(config.runtime_root / "watchdog")
        self.watchdog = ReadOnlyWatchdog(
            self.database,
            config.heartbeat_max_age_seconds,
            expected_build_commit=config.build_commit,
        )

    def run(
        self,
        stop_event: threading.Event,
        *,
        maximum_runtime_seconds: float | None = None,
        on_report: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        reports = 0
        last: dict[str, Any] = {}
        with LeaderLock(self.config.runtime_root / "runtime" / "watchdog.lock"):
            while not stop_event.is_set():
                last = self.watchdog.inspect()
                last.update(
                    {
                        "artifact_type": "UNIFIED_ASSISTIVE_INDEPENDENT_WATCHDOG_REPORT",
                        "watchdog_build_commit": self.config.build_commit,
                        "watchdog_pid": os.getpid(),
                        "watchdog_hostname": socket.gethostname(),
                        "observed_at": rfc3339(datetime.now(timezone.utc)),
                        "full_operational_audit": "EVIDENCE_DERIVED_AND_FAIL_CLOSED",
                        "overall_operational_completion": "INCOMPLETE",
                    }
                )
                self.store.write("reports", last, current_name="watchdog-report.json")
                reports += 1
                if on_report is not None:
                    on_report(last)
                if maximum_runtime_seconds is not None and time.monotonic() - started >= maximum_runtime_seconds:
                    break
                wait_timeout = self.config.interval_seconds
                if maximum_runtime_seconds is not None:
                    remaining_runtime = maximum_runtime_seconds - (time.monotonic() - started)
                    if remaining_runtime <= 0:
                        break
                    wait_timeout = min(wait_timeout, remaining_runtime)
                stop_event.wait(wait_timeout)
        return {"result": "PASS", "service": "watchdog", "reports": reports, "last_report": last}
