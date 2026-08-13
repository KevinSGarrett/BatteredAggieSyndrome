from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import canonical_json_bytes, sha256_value
from .controller_state import ControllerState, rfc3339
from .orchestration import ReadyWorkInventory, ReadyWorkUnit, RouteDecision, RoutingDisposition


MAX_DISCOVERED_MANIFEST_BYTES = 1024 * 1024
MAX_DISCOVERED_UNITS = 64
DISCOVERY_NAMES = frozenset({"run.json", "progress.json"})
CPU_MANIFEST_TASK_FORMAT = "cpu_worker_canonical_manifest_v1"
CPU_MANIFEST_SCHEMA_SHA256 = hashlib.sha256(
    b"cpu_worker_canonical_manifest_v1:value:any-json;candidate-only;exact-local-replay"
).hexdigest()


def cpu_qualification_evidence_sha256(snapshot: dict[str, Any]) -> str | None:
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
        if (
            isinstance(qualification, dict)
            and "CANONICAL_JSON" in qualification.get("tasks", [])
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
    refresh_max_age_seconds: int = 240

    def validate(self) -> None:
        if self.refresh_max_age_seconds <= 0:
            raise ValueError("RUNTIME_INVENTORY_REFRESH_AGE_INVALID")
        if not self.manifests_root.is_absolute():
            raise ValueError("RUNTIME_INVENTORY_MANIFEST_ROOT_NOT_ABSOLUTE")


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
    def _cpu_qualified(snapshot: dict[str, Any]) -> bool:
        return cpu_qualification_evidence_sha256(snapshot) is not None

    def refresh(self, *, now: datetime | None = None) -> dict[str, Any]:
        moment = now or datetime.now(timezone.utc)
        base, base_sha256 = self._load_current_snapshot()
        if not self._cpu_qualified(base):
            raise RuntimeError("RUNTIME_INVENTORY_CPU_QUALIFICATION_NOT_ESTABLISHED")

        prior_units = {
            item["work_unit_id"]: item
            for item in base.get("work_units", [])
            if str(item.get("work_unit_id", "")).startswith("AUTO-CPU-MANIFEST-")
        }
        prior_decisions = {
            item["work_unit_id"]: item
            for item in base.get("route_decisions", [])
            if str(item.get("work_unit_id", "")).startswith("AUTO-CPU-MANIFEST-")
        }
        execution_packets = dict(base.get("execution_packets", {}))
        discovered = self._discover(moment)
        for unit, decision, packet in discovered:
            prior_units.setdefault(unit.work_unit_id, asdict(unit))
            prior_decisions.setdefault(
                unit.work_unit_id,
                {**asdict(decision), "disposition": decision.disposition.value},
            )
            execution_packets.setdefault(unit.work_unit_id, packet)

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
            if not str(item.get("work_unit_id", "")).startswith("AUTO-CPU-MANIFEST-")
        ]
        static_decisions = [
            item for item in base.get("route_decisions", [])
            if not str(item.get("work_unit_id", "")).startswith("AUTO-CPU-MANIFEST-")
        ]
        work_units = static_units + [prior_units[key] for key in sorted(prior_units)]
        route_decisions = static_decisions + [prior_decisions[key] for key in sorted(prior_decisions)]
        inventory = ReadyWorkInventory(
            [ReadyWorkUnit(**{**item, "source_hashes": tuple(item["source_hashes"]), "dependencies": tuple(item["dependencies"])}) for item in work_units],
            [RouteDecision(**{**item, "disposition": RoutingDisposition(item["disposition"])}) for item in route_decisions],
        )
        validation = inventory.validate()
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
            }
        )
        snapshot = {
            **{key: value for key, value in base.items() if key not in {"generated_at", "validation", "work_units", "route_decisions", "execution_packets", "runtime_material_identity"}},
            "schema_version": 2,
            "artifact_type": "UNIFIED_ASSISTIVE_RUNTIME_INVENTORY",
            "generated_at": rfc3339(moment),
            "runtime_material_identity": material_identity,
            "static_base_inventory_identity": static_base_identity,
            "work_units": work_units,
            "route_decisions": route_decisions,
            "execution_packets": execution_packets,
            "execution_states": status,
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
