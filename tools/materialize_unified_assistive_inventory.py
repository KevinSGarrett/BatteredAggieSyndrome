from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import subprocess
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.orchestration import (
    ReadyWorkInventory,
    ReadyWorkUnit,
    RouteDecision,
    RoutingDisposition,
    validate_work_unit_roles,
    write_content_addressed_json,
)


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
        "latest_write_at": max(
            (datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) for path in root.rglob("*.json")),
            default=None,
        ).isoformat().replace("+00:00", "Z") if records else None,
    }


def verified_content_addressed_json(path: Path) -> dict[str, Any]:
    digest = sha256(path)
    if path.stem != digest:
        raise RuntimeError(f"EXTERNAL_EVIDENCE_CONTENT_ADDRESS_MISMATCH:{path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"EXTERNAL_EVIDENCE_NOT_OBJECT:{path}")
    return payload


def local_qwen_semantic_evidence(root: Path, readiness: dict[str, Any]) -> dict[str, Any]:
    routes: list[dict[str, Any]] = []
    for route in readiness["routes"]:
        evidence_sha256 = route.get("evidence_sha256")
        evidence_path = root / "evals" / str(evidence_sha256)[:2] / f"{evidence_sha256}.json"
        evidence_verified = False
        evidence_disposition = None
        findings: list[str] = []
        if evidence_path.is_file():
            payload = verified_content_addressed_json(evidence_path)
            evidence_disposition = payload.get("qualification_disposition")
            if payload.get("model") != route["resolved_model"]:
                findings.append("MODEL_IDENTITY_MISMATCH")
            if payload.get("model_digest") != route["model_digest"]:
                findings.append("MODEL_DIGEST_MISMATCH")
            if payload.get("canonical_or_protected_authority") is True:
                findings.append("AUTHORITY_BOUNDARY_INVALID")
            if payload.get("metrics", {}).get("canonical_writes", 0) != 0:
                findings.append("CANONICAL_WRITE_EVIDENCE_INVALID")
            if payload.get("metrics", {}).get("protected_decisions", 0) != 0:
                findings.append("PROTECTED_DECISION_EVIDENCE_INVALID")
            evidence_verified = not findings
        else:
            findings.append("EVIDENCE_ARTIFACT_MISSING")
        empirical_ready = (
            route["state"] == "READY"
            and evidence_verified
            and isinstance(evidence_disposition, str)
            and evidence_disposition.startswith("PASS_")
        )
        evidence_supported_state = "READY" if empirical_ready else "NOT_READY"
        if route["state"] == "NOT_READY":
            evidence_supported_state = "NOT_READY"
        routes.append(
            {
                "provider": route["provider"],
                "resolved_model": route["resolved_model"],
                "model_digest": route["model_digest"],
                "task_format": route["task_format"],
                "prompt_version": route["prompt_version"],
                "schema_version": route["schema_version"],
                "schema_sha256": route["schema_sha256"],
                "policy_version": route["policy_version"],
                "execution_surface": route["execution_surface"],
                "registry_state": route["state"],
                "evidence_supported_state": evidence_supported_state,
                "evidence_sha256": evidence_sha256,
                "evidence_verified": evidence_verified,
                "qualification_disposition": evidence_disposition,
                "findings": findings,
            }
        )
    return {
        **external_evidence_identity(root),
        "routes": routes,
        "ready_exact_routes": sum(item["evidence_supported_state"] == "READY" for item in routes),
        "rejected_or_unqualified_exact_routes": sum(
            item["evidence_supported_state"] == "NOT_READY" for item in routes
        ),
    }


def cpu_worker_semantic_evidence(root: Path) -> dict[str, Any]:
    qualified: list[dict[str, Any]] = []
    findings: list[str] = []
    readiness_records: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "readiness").rglob("*.json")) if (root / "readiness").is_dir() else []:
        try:
            payload = verified_content_addressed_json(path)
        except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
            findings.append(str(exc))
            continue
        qualification_id = payload.get("qualification_id")
        required_gates = {
            "cleanup",
            "coordinator_grant",
            "live_replay",
            "minimal_bundle_hash_match",
            "private_https",
            "restart_recovery",
            "restricted_service_identity",
            "signed_envelope",
        }
        peer = payload.get("peer", {})
        if (
            qualification_id == "BAT-563-private-cpu-worker-v2-corrected-architecture"
            and payload.get("readiness_disposition") == "READY_FOR_LIVE_QUALIFICATION"
            and payload.get("blockers") == []
            and required_gates.issubset(set(payload.get("passed_gates", [])))
            and payload.get("canonical_writes") == 0
            and payload.get("protected_decisions") == 0
            and payload.get("prototype_direct_http_disabled") is True
            and payload.get("public_funnel_configured_by_project") is False
            and peer.get("dns_name") == "comfy-v4-cpu-01.tail9b05ab.ts.net"
            and peer.get("windows_hostname") == "comfy-v4-cpu-01"
            and peer.get("os") == "windows"
            and peer.get("durable_ip_identity") is False
            and isinstance(peer.get("node_id"), str)
            and bool(peer.get("node_id"))
        ):
            readiness_records[str(qualification_id)] = {
                "evidence_sha256": path.stem,
                "peer": peer,
            }
    for path in sorted((root / "qualifications").rglob("*.json")) if (root / "qualifications").is_dir() else []:
        try:
            payload = verified_content_addressed_json(path)
        except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
            findings.append(str(exc))
            continue
        if payload.get("qualification_disposition") != "PASS":
            continue
        if payload.get("qualification_id") != "BAT-563-private-cpu-worker-v2-corrected-architecture":
            continue
        required = {
            "authority": "DETERMINISTIC_NO_CANONICAL_OR_PROTECTED_WRITES",
            "canonical_writes": 0,
            "protected_decisions": 0,
            "signing_key_recorded": False,
        }
        if any(payload.get(key) != value for key, value in required.items()):
            findings.append(f"CPU_WORKER_QUALIFICATION_BOUNDARY_INVALID:{path.name}")
            continue
        tranches = payload.get("tranches", [])
        expected_tasks = {"CANONICAL_JSON", "LINE_HASH_MANIFEST", "EXACT_TEXT_DEDUP"}
        if (
            len(tranches) < 3
            or not all(item.get("byte_identical_replay") is True for item in tranches)
            or {item.get("task") for item in tranches} != expected_tasks
        ):
            findings.append(f"CPU_WORKER_REPLAY_EVIDENCE_INCOMPLETE:{path.name}")
            continue
        readiness = readiness_records.get(str(payload.get("qualification_id")))
        if readiness is None:
            findings.append(f"CPU_WORKER_READINESS_EVIDENCE_MISSING:{path.name}")
            continue
        worker_identity = payload.get("worker_identity", {})
        if any(
            worker_identity.get(field) != readiness["peer"].get(field)
            for field in ("node_id", "dns_name", "windows_hostname", "os", "durable_ip_identity")
        ):
            findings.append(f"CPU_WORKER_READINESS_IDENTITY_MISMATCH:{path.name}")
            continue
        qualified.append(
            {
                "qualification_id": payload.get("qualification_id"),
                "qualification_run_id": payload.get("qualification_run_id"),
                "evidence_sha256": path.stem,
                "readiness_evidence_sha256": readiness["evidence_sha256"],
                "worker_identity": worker_identity,
                "tranche_count": len(tranches),
                "tasks": sorted({item.get("task") for item in tranches}),
            }
        )
    return {
        **external_evidence_identity(root),
        "qualified": bool(qualified),
        "qualifications": qualified,
        "findings": findings,
        "authority": "BOUNDED_DETERMINISTIC_WORKER_ONLY",
    }


def cursor_semantic_evidence(root: Path) -> dict[str, Any]:
    dispositions: list[dict[str, Any]] = []
    findings: list[str] = []
    disposition_root = root / "dispositions"
    for path in sorted(disposition_root.rglob("*.json")) if disposition_root.is_dir() else []:
        try:
            payload = verified_content_addressed_json(path)
        except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
            findings.append(str(exc))
            continue
        if (
            payload.get("candidate_only") is not True
            or payload.get("canonical_authority") is not False
            or payload.get("protected_authority") is True
        ):
            findings.append(f"CURSOR_AUTHORITY_BOUNDARY_INVALID:{path.name}")
            continue
        dispositions.append(payload)
    unique_jobs = {str(item.get("job_id")) for item in dispositions if item.get("job_id")}
    unique_agents = {str(item.get("agent_id")) for item in dispositions if item.get("agent_id")}
    controller_routed = [item for item in dispositions if item.get("dispatch_origin") == "PERSISTENT_CONTROLLER"]
    return {
        **external_evidence_identity(root),
        "real_review_dispositions": len(dispositions),
        "unique_jobs": len(unique_jobs),
        "unique_agents": len(unique_agents),
        "accepted_useful": sum(int(item.get("accepted_useful_results", 0)) for item in dispositions),
        "modified": sum(int(item.get("modified_results", 0)) for item in dispositions),
        "review_only": sum(int(item.get("review_only_results", 0)) for item in dispositions),
        "quarantined": sum(int(item.get("quarantined_results", 0)) for item in dispositions),
        "rejected": sum(int(item.get("rejected_results", 0)) for item in dispositions),
        "failed": sum(int(item.get("provider_failures", 0)) for item in dispositions),
        "settled_usd": format(
            sum(
                (Decimal(str(item.get("provider_usage", {}).get("actual_usd", "0"))) for item in dispositions),
                Decimal("0"),
            ),
            "f",
        ),
        "controller_routed_units": len(controller_routed),
        "transitional_or_manual_units": len(dispositions) - len(controller_routed),
        "findings": findings,
    }


def openrouter_semantic_evidence(root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    request_records: list[dict[str, Any]] = []
    review_records: list[dict[str, Any]] = []
    settlement_records: list[dict[str, Any]] = []
    categories: set[str] = set()
    request_ids: list[str] = []
    review_ids: list[str] = []

    def load_records(category: str) -> list[dict[str, Any]]:
        loaded: list[dict[str, Any]] = []
        category_root = root / category
        for path in sorted(category_root.rglob("*.json")) if category_root.is_dir() else []:
            try:
                loaded.append(verified_content_addressed_json(path))
            except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
                findings.append(str(exc))
        return loaded

    request_records.extend(load_records("requests"))
    review_records.extend(load_records("reviews"))
    review_records.extend(load_records("dispositions"))
    settlement_records.extend(load_records("settlements"))
    settlement_records.extend(load_records("usage"))

    for record in request_records:
        request_id = record.get("request_id")
        if isinstance(request_id, str) and request_id:
            request_ids.append(request_id)
        category = record.get("category")
        if isinstance(category, str) and category:
            categories.add(category)
        provider = record.get("provider")
        model = record.get("model")
        if provider not in {"openrouter", None} or not isinstance(model, str) or not model:
            findings.append("OPENROUTER_REQUEST_ROUTE_IDENTITY_INCOMPLETE")

    for record in review_records:
        request_id = record.get("request_id")
        if isinstance(request_id, str) and request_id:
            request_ids.append(request_id)
        review_id = record.get("review_id")
        if isinstance(review_id, str) and review_id:
            review_ids.append(review_id)
        accepted = int(record.get("accepted_useful_results", 0))
        modified = int(record.get("modified_results", 0))
        review_only = int(record.get("review_only_results", 0))
        quarantined = int(record.get("quarantined_results", 0))
        rejected = int(record.get("rejected_results", 0))
        provider_usage = record.get("provider_usage", {})
        has_disposition = any(value > 0 for value in (accepted, modified, review_only, quarantined, rejected))
        if has_disposition and "actual_usd" not in provider_usage:
            findings.append("OPENROUTER_PROVIDER_USAGE_MISSING")
        quality_claim = (
            record.get("quality_claim")
            or record.get("quality_claims")
            or record.get("quality_threshold_passed")
            or record.get("quality_gate_passed")
        )
        if quality_claim and accepted <= 0:
            findings.append("OPENROUTER_QUALITY_CLAIM_UNSUPPORTED")
        category = record.get("category")
        if isinstance(category, str) and category:
            categories.add(category)

    duplicate_request_ids = sorted({item for item in request_ids if request_ids.count(item) > 1})
    duplicate_review_ids = sorted({item for item in review_ids if review_ids.count(item) > 1})
    if duplicate_request_ids:
        findings.append(f"OPENROUTER_DUPLICATE_REQUEST_IDENTITY:{','.join(duplicate_request_ids)}")
    if duplicate_review_ids:
        findings.append(f"OPENROUTER_DUPLICATE_REVIEW_IDENTITY:{','.join(duplicate_review_ids)}")

    accepted_useful = sum(int(record.get("accepted_useful_results", 0)) for record in review_records)
    modified = sum(int(record.get("modified_results", 0)) for record in review_records)
    review_only = sum(int(record.get("review_only_results", 0)) for record in review_records)
    quarantined = sum(int(record.get("quarantined_results", 0)) for record in review_records)
    rejected = sum(int(record.get("rejected_results", 0)) for record in review_records)
    provider_failures = sum(int(record.get("provider_failures", 0)) for record in review_records)
    settled_usd = sum(
        (Decimal(str(record.get("provider_usage", {}).get("actual_usd", "0"))) for record in review_records),
        Decimal("0"),
    )
    settlement_total_usd = sum(
        (
            Decimal(
                str(
                    record.get("actual_usd")
                    or record.get("settled_usd")
                    or record.get("amount_usd")
                    or "0"
                )
            )
            for record in settlement_records
        ),
        Decimal("0"),
    )
    unresolved_settlement = any(
        record.get("reconciled") is False
        or str(record.get("status", "")).upper() in {"PENDING", "UNRECONCILED", "FAILED"}
        for record in settlement_records
    )
    if unresolved_settlement or (review_records and settlement_total_usd != settled_usd):
        findings.append("OPENROUTER_SETTLEMENT_UNRECONCILED")

    minimums = policy.get("execution_minimums", {}).get("openrouter", {})
    accepted_threshold = int(minimums.get("accepted_useful", 0))
    unit_threshold = int(minimums.get("units", 0))
    category_threshold = int(minimums.get("categories", 0))
    has_live_evidence = bool(request_records or review_records or settlement_records)
    if review_records and accepted_useful < accepted_threshold:
        findings.append("OPENROUTER_ACCEPTED_USEFUL_BELOW_POLICY_THRESHOLD")

    exact_route_ready = bool(request_records) and all(
        isinstance(record.get("provider"), str)
        and record.get("provider") == "openrouter"
        and isinstance(record.get("model"), str)
        and bool(record.get("model"))
        for record in request_records
    )
    operationally_admitted = (
        exact_route_ready
        and len(set(request_ids)) >= unit_threshold
        and len(categories) >= category_threshold
        and accepted_useful >= accepted_threshold
        and not findings
    )
    state = "CONFIGURED"
    if has_live_evidence:
        state = "PAID_PILOT_IN_PROGRESS"
    if exact_route_ready:
        state = "EXACT_ROUTE_READY"
    if findings:
        state = "EMPIRICALLY_REJECTED_OR_INSUFFICIENT"
    if operationally_admitted:
        state = "OPERATIONALLY_ADMITTED"

    return {
        **external_evidence_identity(root),
        "state": state,
        "requests": len(request_records),
        "unique_requests": len(set(request_ids)),
        "reviews": len(review_records),
        "unique_reviews": len(set(review_ids)),
        "categories_covered": len(categories),
        "accepted_useful": accepted_useful,
        "modified": modified,
        "review_only": review_only,
        "quarantined": quarantined,
        "rejected": rejected,
        "failed": provider_failures,
        "settled_usd": format(settled_usd, "f"),
        "settlement_total_usd": format(settlement_total_usd, "f"),
        "exact_route_ready": exact_route_ready,
        "operationally_admitted": operationally_admitted,
        "findings": sorted(set(findings)),
    }


def route_state_from_semantic_evidence(
    route: dict[str, Any], semantic_evidence: dict[str, Any]
) -> str:
    for item in semantic_evidence["local_qwen"]["routes"]:
        identity_fields = (
            "resolved_model",
            "model_digest",
            "task_format",
            "prompt_version",
            "schema_version",
            "schema_sha256",
            "policy_version",
            "execution_surface",
        )
        if all(item[field] == route[field] for field in identity_fields):
            return str(item["evidence_supported_state"])
    return "NOT_READY"


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
        if provider == "local_qwen":
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
    item: dict[str, Any],
    record: dict[str, Any],
    policy: dict[str, Any],
    readiness: dict[str, Any],
    semantic_evidence: dict[str, Any] | None = None,
) -> tuple[RoutingDisposition, str | None, str | None, str]:
    work_unit_id = item.get("work_unit_id") or item["local_id"]
    is_shadow = "::" in work_unit_id
    if not is_shadow and record.get("workflow_state") == "DONE":
        return RoutingDisposition.COMPLETED, None, None, item["reason"]
    provider = item.get("provider")
    route = route_readiness_for(item, readiness)
    if route is not None and semantic_evidence is not None:
        semantic_state = route_state_from_semantic_evidence(route, semantic_evidence)
        if semantic_state != route["state"]:
            return (
                RoutingDisposition.CAPABILITY_BLOCKED,
                provider,
                item.get("model"),
                "ROUTE_REGISTRY_CONFLICTS_WITH_SEMANTIC_RUNTIME_EVIDENCE",
            )
    if provider == "local_qwen" and route is None:
        return (
            RoutingDisposition.CAPABILITY_BLOCKED,
            provider,
            item.get("model"),
            "EXACT_ROUTE_READINESS_NOT_ESTABLISHED",
        )
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
    if (
        (item.get("record_local_id") or item.get("local_id")) == "POST-SUBTASK-204"
        and semantic_evidence is not None
        and semantic_evidence["cpu_worker"]["qualified"]
    ):
        return (
            RoutingDisposition.REMOTE_CPU_WORKER,
            "remote_cpu_worker",
            "DETERMINISTIC_CPU_WORKER_V2",
            "EXACT_CPU_WORKER_QUALIFICATION_PASS_CONTINUING_CAMPAIGN_READY",
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
    external_roots = {
        "openai": Path(r"C:\BatteredAggieSyndrome.data\openai"),
        "openrouter": Path(r"C:\BatteredAggieSyndrome.data\assistive\openrouter"),
        "cursor": Path(r"C:\BatteredAggieSyndrome.data\assistive\cursor"),
        "local_qwen": Path(r"C:\BatteredAggieSyndrome.data\assistive\local_qwen"),
        "cpu_worker": Path(r"C:\BatteredAggieSyndrome.data\assistive\cpu_worker"),
    }
    semantic_evidence = {
        "openai": external_evidence_identity(external_roots["openai"]),
        "openrouter": openrouter_semantic_evidence(external_roots["openrouter"], policy),
        "cursor": cursor_semantic_evidence(external_roots["cursor"]),
        "local_qwen": local_qwen_semantic_evidence(external_roots["local_qwen"], readiness),
        "cpu_worker": cpu_worker_semantic_evidence(external_roots["cpu_worker"]),
    }
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    units: list[ReadyWorkUnit] = []
    work_unit_roles: dict[str, str] = {}
    pending: list[dict[str, Any]] = []
    source_records: list[dict[str, str]] = []
    transition_times = [parse_timestamp(seed.get("material_transition_at"))]
    transition_times.extend(parse_timestamp(value.get("latest_write_at")) for value in semantic_evidence.values())
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
        work_unit_roles[work_unit_id] = item["inventory_role"]
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
        disposition, provider, model, reason = derive_decision(
            item, record, policy, readiness, semantic_evidence
        )
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
    role_validation = validate_work_unit_roles(units, work_unit_roles)
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
        "external_evidence": semantic_evidence,
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
        "work_unit_roles": work_unit_roles,
        "work_unit_role_validation": role_validation,
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
