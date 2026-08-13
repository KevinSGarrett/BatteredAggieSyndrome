from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json
from aggie_analytics.assistive_plane.controller_state import parse_rfc3339


OPENAI_LEDGER = Path(r"C:\BatteredAggieSyndrome.data\openai\usage\usage-ledger.jsonl")
OUTPUT_ROOT = Path(r"C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3")
OPENROUTER_ROOT = Path(r"C:\BatteredAggieSyndrome.data\assistive\openrouter")
CURSOR_ROOT = Path(r"C:\BatteredAggieSyndrome.data\assistive\cursor")
AUTHORITATIVE_ENV = Path(r"C:\BatteredAggieSyndrome\.env")
SERVICE_CAPTURE = OUTPUT_ROOT / "service-state/current/service-state.json"
CURRENT_INVENTORY = Path(r"C:\BatteredAggieSyndrome.data\assistive\inventory\current\inventory.json")
ALLOWED_RESULTS = {"PASS", "FAIL", "BLOCKED", "INCOMPLETE"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def settled_openai_calls(path: Path = OPENAI_LEDGER) -> int:
    if not path.is_file():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("event") == "SETTLED" or record.get("status") in {"SETTLED", "COMPLETED", "SUCCESS"}:
            count += 1
    return count


def credential_present_once(name: str, env_path: Path = AUTHORITATIVE_ENV) -> bool:
    if not env_path.is_file():
        return False
    matches = []
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == name:
            matches.append(bool(value.strip()))
    return matches == [True]


def json_artifacts(root: Path) -> list[dict[str, Any]]:
    artifacts = []
    if not root.is_dir():
        return artifacts
    for path in root.rglob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            artifacts.append(payload)
    return artifacts


def current_inventory(path: Path = CURRENT_INVENTORY) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("artifact_type") == "UNIFIED_ASSISTIVE_INVENTORY_POINTER":
        snapshot_path = Path(str(payload["snapshot_path"]))
        data = snapshot_path.read_bytes()
        if hashlib.sha256(data).hexdigest() != payload.get("snapshot_sha256"):
            raise RuntimeError("COMPLETENESS_INVENTORY_POINTER_HASH_MISMATCH")
        payload = json.loads(data)
    return payload


def derive_states(root: Path = ROOT, service_capture: Path | None = None) -> tuple[dict[str, str], dict[str, Any]]:
    policy = json.loads((root / "configs/unified_assistive_policy.json").read_text(encoding="utf-8"))
    openai_calls = settled_openai_calls()
    openrouter_manifests = json_artifacts(OPENROUTER_ROOT / "manifests")
    openrouter_ledger_path = OPENROUTER_ROOT / "usage" / "ledger.json"
    openrouter_ledger = json.loads(openrouter_ledger_path.read_text(encoding="utf-8")) if openrouter_ledger_path.is_file() else {}
    openrouter_spend = Decimal(str(openrouter_ledger.get("settled_usd", "0")))
    cursor_manifests = json_artifacts(CURSOR_ROOT / "manifests")
    cursor_agents = len({item.get("agent_id") for item in cursor_manifests if item.get("agent_id")})
    service = json.loads(service_capture.read_text(encoding="utf-8")) if service_capture and service_capture.is_file() else None
    inventory = current_inventory()
    semantic = inventory.get("external_evidence", {})
    cpu_qualified = bool(semantic.get("cpu_worker", {}).get("qualified"))
    local_routes = semantic.get("local_qwen", {}).get("routes", [])
    bge_ready = any(
        str(item.get("resolved_model", "")).startswith("bge-m3")
        and item.get("evidence_supported_state") == "READY"
        for item in local_routes
    )
    service_deployed = bool(service and service.get("result") == "PASS" and service.get("service_shell_state") == "DEPLOYED_HEALTHY")
    scheduler_real_cycles = int(service.get("scheduler", {}).get("real_cycles", 0)) if service else 0
    scheduler_operational = bool(service and service.get("scheduler", {}).get("operational"))
    if service_deployed and scheduler_operational:
        unified_state = "CONTROLLER_SCHEDULER_DEPLOYED_CAMPAIGNS_INCOMPLETE"
    elif service_deployed:
        unified_state = "SERVICE_SHELL_DEPLOYED_SCHEDULER_NOT_OPERATIONAL"
    else:
        unified_state = "INCOMPLETE_CONTROLLER_NOT_DEPLOYED"
    states = {
        "openai": "OPERATIONAL_CANDIDATE_ONLY" if openai_calls else "CONFIGURED_NOT_OPERATIONAL",
        "openrouter": "PAID_PILOT_IN_PROGRESS_NOT_OPERATIONAL" if openrouter_spend > 0 else "PAID_PILOT_AUTHORIZED_NOT_OPERATIONAL",
        "cursor": "PAID_PILOT_IN_PROGRESS_NOT_OPERATIONAL" if cursor_agents > 0 else "PAID_PILOT_AUTHORIZED_ZERO_REAL_AGENTS",
        "local_qwen": (
            "BGE_M3_EXACT_RETRIEVAL_READY_QWEN_EXACT_ROUTES_REJECTED"
            if bge_ready else "EXACT_EVALUATED_ROUTES_REJECTED_NEW_QUALIFICATION_PENDING"
        ),
        "remote_cpu_worker": (
            "EXACT_FIXED_FUNCTION_QUALIFIED_CAMPAIGN_INCOMPLETE"
            if cpu_qualified else "BLOCKED_PARTIAL_CORRECTED_DEPLOYMENT_PENDING"
        ),
        "unified_plane": unified_state,
    }
    evidence = {
        "settled_openai_calls": openai_calls,
        "new_controller_routed_openai_units": 0,
        "openrouter_real_manifests": len(openrouter_manifests),
        "openrouter_settled_usd": format(openrouter_spend, "f"),
        "cursor_real_agents": cursor_agents,
        "controller_os_supervision_verified": service_deployed,
        "watchdog_os_supervision_verified": service_deployed,
        "scheduler_real_cycles": scheduler_real_cycles,
        "scheduler_operational": scheduler_operational,
        "scheduler_dispatched_units": int(service.get("scheduler", {}).get("dispatched_units", 0)) if service else 0,
        "cpu_worker_exact_qualified": cpu_qualified,
        "bge_m3_exact_retrieval_ready": bge_ready,
        "service_capture_present": service is not None,
        "service_capture_result": service.get("result") if service else None,
        "soak_calendar_days": 0,
        "soak_only_units": 0,
        "failed_or_rejected_work_omitted": False,
        "structural_and_operational_results_separate": True,
        "credential_presence": {
            "openai": credential_present_once("OPENAI_API_KEY"),
            "openrouter": credential_present_once("OPENROUTER_API_KEY"),
            "cursor": credential_present_once("CURSOR_API_TOKEN"),
        },
        "hard_limits_usd": {
            name: budget["hard_limit_usd"]
            for name, budget in policy["budgets"].items()
            if "hard_limit_usd" in budget
        },
    }
    return states, evidence


def validate_claims(claims: dict[str, Any], states: dict[str, str]) -> list[str]:
    findings = []
    for provider, derived in states.items():
        if claims.get("claims", {}).get(provider) != derived:
            findings.append(f"CLAIM_EXCEEDS_OR_CONFLICTS_WITH_EVIDENCE:{provider}")
    if claims.get("fully_operational_claimed"):
        findings.append("FULL_OPERATIONAL_CLAIM_PREMATURE")
    if claims.get("sustained_operation_claimed"):
        findings.append("SUSTAINED_OPERATION_CLAIM_PREMATURE")
    if "overall_result" in claims and claims.get("overall_result") not in ALLOWED_RESULTS:
        findings.append("OVERALL_RESULT_SEMANTICS_INVALID")
    return findings


def evaluate_rows(registry: dict[str, Any], report_path: Path | None) -> tuple[list[dict[str, Any]], str, list[str]]:
    required_ids = [row["id"] for row in registry["rows"]]
    if report_path is None:
        rows = [
            {
                "id": row_id,
                "mandatory": True,
                "result": "INCOMPLETE",
                "observed": {},
                "required": {},
                "evidence": [],
                "findings": ["RUNTIME_ACCEPTANCE_EVIDENCE_NOT_YET_SUPPLIED"],
            }
            for row_id in required_ids
        ]
        return rows, "INCOMPLETE", ["MANDATORY_RUNTIME_ACCEPTANCE_REPORT_MISSING"]
    supplied = json.loads(report_path.read_text(encoding="utf-8"))
    rows = supplied.get("rows", [])
    findings: list[str] = []
    by_id = {row.get("id"): row for row in rows}
    if len(by_id) != len(rows):
        findings.append("DUPLICATE_ACCEPTANCE_RESULT_ROW")
    if set(by_id) != set(required_ids):
        findings.append("ACCEPTANCE_RESULT_POPULATION_MISMATCH")
    for row_id in required_ids:
        row = by_id.get(row_id)
        if row is None:
            continue
        result = row.get("result")
        if result not in ALLOWED_RESULTS:
            findings.append(f"ACCEPTANCE_RESULT_INVALID:{row_id}")
        if result == "PASS" and not row.get("evidence"):
            findings.append(f"PASS_WITHOUT_EVIDENCE:{row_id}")
    if findings or any(row.get("result") == "FAIL" for row in rows):
        overall = "FAIL"
    elif any(row.get("result") == "BLOCKED" for row in rows):
        overall = "BLOCKED"
    elif any(row.get("result") == "INCOMPLETE" for row in rows):
        overall = "INCOMPLETE"
    elif len(rows) == len(required_ids) and all(row.get("result") == "PASS" for row in rows):
        overall = "PASS"
    else:
        overall = "INCOMPLETE"
    return rows, overall, findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claims", type=Path, default=ROOT / "configs/unified_assistive_operational_claims.json")
    parser.add_argument("--acceptance-report", type=Path)
    parser.add_argument("--inventory-snapshot", type=Path)
    parser.add_argument("--service-capture", type=Path, default=SERVICE_CAPTURE)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    claims = json.loads(args.claims.read_text(encoding="utf-8"))
    registry_path = ROOT / "configs/unified_assistive_acceptance_ownership.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    service_capture = args.service_capture if args.service_capture and args.service_capture.is_file() else None
    states, evidence = derive_states(service_capture=service_capture)
    findings = validate_claims(claims, states)
    if service_capture is None:
        findings.append("LIVE_SERVICE_CAPTURE_MISSING")
    else:
        service = json.loads(service_capture.read_text(encoding="utf-8"))
        if service.get("result") != "PASS":
            findings.append("LIVE_SERVICE_CAPTURE_FAILED")
        observed_at = service.get("observed_at")
        if not observed_at or (datetime.now(timezone.utc) - parse_rfc3339(observed_at)).total_seconds() > 600:
            findings.append("LIVE_SERVICE_CAPTURE_STALE")
    rows, overall, row_findings = evaluate_rows(registry, args.acceptance_report)
    findings.extend(row_findings)
    inventory_sha256 = None
    inventory_pointer_sha256 = None
    latest_material_transition_at = None
    if args.inventory_snapshot is None:
        findings.append("CURRENT_INVENTORY_SNAPSHOT_MISSING")
    else:
        supplied_inventory = json.loads(args.inventory_snapshot.read_text(encoding="utf-8"))
        if supplied_inventory.get("artifact_type") == "UNIFIED_ASSISTIVE_INVENTORY_POINTER":
            inventory_pointer_sha256 = sha256(args.inventory_snapshot)
            inventory = current_inventory(args.inventory_snapshot)
            inventory_sha256 = str(supplied_inventory.get("snapshot_sha256"))
        else:
            inventory = supplied_inventory
            inventory_sha256 = sha256(args.inventory_snapshot)
        latest_material_transition_at = inventory.get("material_transition_at")
        if inventory.get("validation", {}).get("coverage_fraction") != 1.0:
            findings.append("READY_WORK_COVERAGE_INCOMPLETE")
        if inventory.get("mandatory_acceptance_rows") != 204:
            findings.append("INVENTORY_ACCEPTANCE_POPULATION_INVALID")
        generated = inventory.get("generated_at")
        if generated and latest_material_transition_at:
            generated_at = parse_rfc3339(generated)
            transition_at = parse_rfc3339(latest_material_transition_at)
            if generated_at < transition_at:
                findings.append("INVENTORY_SNAPSHOT_PREDATES_MATERIAL_TRANSITION")
    if findings:
        overall = "FAIL" if any(item.startswith(("CLAIM_", "ACCEPTANCE_", "PASS_", "OVERALL_")) for item in findings) else overall
    if claims.get("overall_result") != overall:
        findings.append(f"CLAIMED_OVERALL_RESULT_CONFLICT:{claims.get('overall_result')}:{overall}")
        if claims.get("overall_result") == "PASS":
            overall = "FAIL"
    report = {
        "schema_version": 2,
        "evaluation_id": hashlib.sha256((sha256(registry_path) + sha256(args.claims)).encode("ascii")).hexdigest(),
        "controller_build_commit": (
            json.loads(service_capture.read_text(encoding="utf-8")).get("release", {}).get("build_commit")
            if service_capture else "UNKNOWN_NOT_DEPLOYED"
        ),
        "inventory_sha256": inventory_sha256,
        "inventory_pointer_sha256": inventory_pointer_sha256,
        "latest_material_transition_at": latest_material_transition_at,
        "live_state_capture_sha256": sha256(service_capture) if service_capture else None,
        "derived_states": states,
        "claims_sha256": sha256(args.claims),
        "acceptance_registry_sha256": sha256(registry_path),
        "rows": rows,
        "overall_result": overall,
        "blocking_row_ids": [row["id"] for row in rows if row.get("result") != "PASS"],
        "weighted_attempted_offload_ratio": 0.0,
        "weighted_accepted_offload_ratio": 0.0,
        "measured_effective_savings_minutes": 0.0,
        "evidence_counts": evidence,
        "structural_validity": "SEPARATELY_VALIDATED",
        "findings": findings,
    }
    path, digest = write_content_addressed_json(args.output_root, "completeness", report)
    print(json.dumps({"status": overall, "path": str(path), "sha256": digest, "derived_states": states}, sort_keys=True))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
