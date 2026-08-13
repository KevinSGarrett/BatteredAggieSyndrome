from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.orchestration import ReadyWorkInventory, ReadyWorkUnit, RouteDecision, RoutingDisposition, write_content_addressed_json


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def git_value(*arguments: str) -> str:
    result = subprocess.run(["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def external_evidence_identity(root: Path) -> dict[str, Any]:
    if not root.is_dir():
        return {"present": False, "file_count": 0, "manifest_sha256": None}
    records = []
    for path in sorted(root.rglob("*.json")):
        try:
            records.append({"path": path.relative_to(root).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size})
        except OSError:
            continue
    return {
        "present": True,
        "file_count": len(records),
        "manifest_sha256": hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def record_for(local_id: str) -> tuple[Path, dict[str, Any]]:
    matches = list((ROOT / "jira/records/issues").rglob(f"{local_id}_*.json"))
    if len(matches) != 1:
        raise RuntimeError(f"JIRA_RECORD_NOT_UNIQUE:{local_id}:{len(matches)}")
    return matches[0], json.loads(matches[0].read_text(encoding="utf-8"))


def paid_budget_admitted(policy: dict[str, Any], provider: str) -> bool:
    from decimal import Decimal

    budget = policy["budgets"][provider]
    return (
        bool(budget.get("authorization_id"))
        and Decimal(budget["hard_limit_usd"]) > 0
        and Decimal(budget.get("released_stage_usd", "0")) > 0
    )


def route_readiness_for(item: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any] | None:
    provider = item.get("provider")
    route_providers = {route["provider"] for route in readiness["routes"]}
    if provider == "local_qwen":
        expected_keys = (
            "model_digest",
            "prompt_version",
            "schema_version",
            "schema_sha256",
            "policy_version",
            "execution_surface",
        )
        missing = [key for key in expected_keys if not item.get(key)]
        if missing:
            raise RuntimeError(
                "ROUTE_IDENTITY_INCOMPLETE:"
                f"{item.get('work_unit_id') or item.get('local_id') or 'UNKNOWN'}:"
                + ",".join(missing)
            )
    model = item.get("model")
    task_format = item.get("task_format")
    matches = []
    for route in readiness["routes"]:
        if route["resolved_model"] != model or route["task_format"] != task_format:
            continue
        if provider not in {route["provider"], "local_qwen"}:
            continue
        if provider == "local_qwen" or provider in route_providers:
            if any(
                item.get(key) != route.get(key)
                for key in (
                    "model_digest",
                    "prompt_version",
                    "schema_version",
                    "schema_sha256",
                    "policy_version",
                    "execution_surface",
                )
            ):
                continue
        matches.append(route)
    if len(matches) > 1:
        raise RuntimeError(f"ROUTE_READINESS_NOT_UNIQUE:{model}:{task_format}")
    return matches[0] if matches else None


def derive_decision(
    item: dict[str, Any], record: dict[str, Any], policy: dict[str, Any], readiness: dict[str, Any]
) -> tuple[RoutingDisposition, str | None, str | None, str]:
    work_unit_id = item.get("work_unit_id") or item["local_id"]
    is_shadow = "::" in work_unit_id
    if not is_shadow and record.get("workflow_state") == "DONE":
        return RoutingDisposition.COMPLETED, None, None, item["reason"]
    provider = item.get("provider")
    route = route_readiness_for(item, readiness)
    if route is not None and route["state"] != "READY":
        return (
            RoutingDisposition.SUSPENDED_REJECTED_ROUTE
            if route["state"] == "NOT_READY"
            else RoutingDisposition.CAPABILITY_BLOCKED,
            provider,
            item.get("model"),
            route["reason"],
        )
    if provider in {"openrouter", "cursor"} and not paid_budget_admitted(policy, provider):
        return (
            RoutingDisposition.BUDGET_BLOCKED,
            provider,
            item.get("model"),
            f"PAID_{provider.upper()}_BUDGET_NOT_AUTHORIZED",
        )
    return RoutingDisposition(item["disposition"]), provider, item.get("model"), item["reason"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=ROOT / "configs/unified_assistive_ready_work.json")
    parser.add_argument("--storage-root", type=Path, default=Path(r"C:\BatteredAggieSyndrome.data\assistive\inventory"))
    args = parser.parse_args()
    seed = json.loads(args.seed.read_text(encoding="utf-8"))
    policy_path = ROOT / "configs/unified_assistive_policy.json"
    provider_registry_path = ROOT / "configs/assistive_provider_registry.json"
    route_readiness_path = ROOT / "configs/assistive_route_readiness.json"
    acceptance_ownership_path = ROOT / "configs/unified_assistive_acceptance_ownership.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    readiness = json.loads(route_readiness_path.read_text(encoding="utf-8"))
    ownership = json.loads(acceptance_ownership_path.read_text(encoding="utf-8"))
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    units: list[ReadyWorkUnit] = []
    pending: list[dict[str, Any]] = []
    source_records: list[dict[str, str]] = []
    transition_times = [parse_timestamp(seed.get("material_transition_at"))]
    for item in seed["work_units"]:
        record_local_id = item.get("record_local_id") or item["local_id"]
        work_unit_id = item.get("work_unit_id") or item["local_id"]
        record_path, record = record_for(record_local_id)
        schema_path = ROOT / item["schema_path"]
        unit = ReadyWorkUnit(
            work_unit_id=work_unit_id,
            jira_unit=record["jira_key"],
            task_format=item["task_format"],
            schema_sha256=sha256(schema_path),
            authority=item["authority"],
            source_hashes=(sha256(record_path),),
            dependencies=tuple(record.get("dependencies", [])),
            pre_routing_effort_points=item["pre_routing_effort_points"],
            scope=item["scope"],
        )
        units.append(unit)
        pending.append((item, record))
        source_records.append({
            "work_unit_id": work_unit_id,
            "record_local_id": record_local_id,
            "jira_key": record["jira_key"],
            "workflow_state": record.get("workflow_state", "UNKNOWN"),
            "live_status_mirror": record.get("operational_jira", {}).get("status_raw", "UNKNOWN"),
            "live_updated_at": record.get("operational_jira", {}).get("jira_updated_at"),
            "last_synced_at": record.get("operational_jira", {}).get("last_synced_at"),
            "record_sha256": sha256(record_path),
        })
        transition_times.extend(
            [
                parse_timestamp(record.get("operational_jira", {}).get("jira_updated_at")),
                parse_timestamp(record.get("operational_jira", {}).get("last_synced_at")),
            ]
        )
    represented = {item.get("record_local_id") or item["local_id"] for item in seed["work_units"]}
    required_owners = set(ownership["owner_records"])
    missing_owners = sorted(required_owners - represented)
    if missing_owners:
        raise RuntimeError(f"MANDATORY_JIRA_OWNER_ABSENT_FROM_INVENTORY:{','.join(missing_owners)}")
    decisions = []
    for unit, (item, record) in zip(units, pending, strict=True):
        disposition, provider, model, reason = derive_decision(item, record, policy, readiness)
        decisions.append(RouteDecision(
            work_unit_id=unit.work_unit_id,
            work_unit_identity=unit.identity(),
            disposition=disposition,
            provider=provider,
            model=model,
            reason=reason,
            decided_at=generated_at,
        ))
    report = ReadyWorkInventory(units, decisions).validate()
    head = git_value("rev-parse", "HEAD")
    origin_main = git_value("rev-parse", "origin/main")
    status_porcelain_sha256 = hashlib.sha256(git_value("status", "--porcelain").encode()).hexdigest()
    snapshot = {
        "schema_version": 1,
        "inventory_seed_id": seed["inventory_seed_id"],
        "material_transition_at": max(item for item in transition_times if item is not None).isoformat().replace("+00:00", "Z"),
        "generated_at": generated_at,
        "decisions_derived_from_current_evidence": True,
        "seed_sha256": sha256(args.seed),
        "policy_sha256": sha256(policy_path),
        "provider_registry_sha256": sha256(provider_registry_path),
        "route_readiness_sha256": sha256(route_readiness_path),
        "acceptance_ownership_sha256": sha256(acceptance_ownership_path),
        "mandatory_acceptance_rows": ownership["mandatory_row_count"],
        "git": {
            "head": head,
            "origin_main": origin_main,
            "status_porcelain_sha256": status_porcelain_sha256,
        },
        "external_evidence": {
            "openai": external_evidence_identity(Path(r"C:\BatteredAggieSyndrome.data\openai")),
            "openrouter": external_evidence_identity(Path(r"C:\BatteredAggieSyndrome.data\assistive\openrouter")),
            "cursor": external_evidence_identity(Path(r"C:\BatteredAggieSyndrome.data\assistive\cursor")),
            "local": external_evidence_identity(Path(r"C:\BatteredAggieSyndrome.data\assistive\local-qwen")),
            "cpu_worker": external_evidence_identity(Path(r"C:\BatteredAggieSyndrome.data\assistive\cpu-worker")),
        },
        "work_units": [
            {
                "work_unit_id": unit.work_unit_id,
                "jira_unit": unit.jira_unit,
                "task_format": unit.task_format,
                "schema_sha256": unit.schema_sha256,
                "authority": unit.authority,
                "source_hashes": list(unit.source_hashes),
                "dependencies": list(unit.dependencies),
                "pre_routing_effort_points": unit.pre_routing_effort_points,
                "scope": unit.scope,
                "identity": unit.identity(),
            }
            for unit in units
        ],
        "route_decisions": [
            {
                "work_unit_id": decision.work_unit_id,
                "work_unit_identity": decision.work_unit_identity,
                "disposition": decision.disposition.value,
                "provider": decision.provider,
                "model": decision.model,
                "reason": decision.reason,
                "decided_at": decision.decided_at,
            }
            for decision in decisions
        ],
        "source_records": source_records,
        "validation": report,
        "canonical_or_protected_authority": False,
    }
    path, digest = write_content_addressed_json(args.storage_root, "snapshots", snapshot)
    snapshot_bytes = path.read_bytes()
    if hashlib.sha256(snapshot_bytes).hexdigest() != digest:
        raise RuntimeError("INVENTORY_SNAPSHOT_HASH_MISMATCH")
    promotion_findings = []
    if head != origin_main:
        promotion_findings.append("INVENTORY_PROMOTION_REQUIRES_CURRENT_MAIN")
    if status_porcelain_sha256 != hashlib.sha256(b"").hexdigest():
        promotion_findings.append("INVENTORY_PROMOTION_REQUIRES_CLEAN_WORKTREE")
    current_path = args.storage_root / "current" / "inventory.json"
    if not promotion_findings:
        atomic_write(current_path, snapshot_bytes)
        if current_path.read_bytes() != snapshot_bytes:
            raise RuntimeError("INVENTORY_CURRENT_POINTER_VERIFY_FAILED")
    print(json.dumps({
        "status": "PASS" if not promotion_findings else "BLOCKED",
        "snapshot_path": str(path),
        "snapshot_sha256": digest,
        "current_path": str(current_path) if not promotion_findings else None,
        "promotion_findings": promotion_findings,
        **report,
    }, sort_keys=True))
    return 0 if not promotion_findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
