from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json


OPENAI_LEDGER = Path(r"C:\BatteredAggieSyndrome.data\openai\usage\usage-ledger.jsonl")
OUTPUT_ROOT = Path(r"C:\BatteredAggieSyndrome.data\assistive\orchestrator")
OPENROUTER_ROOT = Path(r"C:\BatteredAggieSyndrome.data\assistive\openrouter")
CURSOR_ROOT = Path(r"C:\BatteredAggieSyndrome.data\assistive\cursor")


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


def credential_present_once(name: str, env_path: Path = ROOT / ".env") -> bool:
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


def derive_states(root: Path = ROOT) -> tuple[dict[str, str], dict[str, Any]]:
    policy = json.loads((root / "configs/unified_assistive_policy.json").read_text(encoding="utf-8"))
    local = json.loads((root / "artifacts/assistive/local_qwen_qualification.json").read_text(encoding="utf-8"))
    cpu = json.loads((root / "artifacts/assistive/cpu_worker_readiness.json").read_text(encoding="utf-8"))
    openai_calls = settled_openai_calls()
    openrouter_manifests = json_artifacts(OPENROUTER_ROOT / "manifests")
    openrouter_candidates = sum(item.get("disposition") == "CANDIDATE" for item in openrouter_manifests)
    openrouter_failures = sum(item.get("disposition") in {"REJECTED", "QUARANTINE"} for item in openrouter_manifests)
    openrouter_ledger_path = OPENROUTER_ROOT / "usage" / "ledger.json"
    openrouter_ledger = json.loads(openrouter_ledger_path.read_text(encoding="utf-8")) if openrouter_ledger_path.is_file() else {}
    openrouter_spend = Decimal(str(openrouter_ledger.get("settled_usd", "0")))
    cursor_manifests = json_artifacts(CURSOR_ROOT / "manifests")
    cursor_agents = len({item.get("agent_id") for item in cursor_manifests if item.get("agent_id")})
    states = {
        "openai": "OPERATIONAL_CANDIDATE_ONLY" if openai_calls else "CONFIGURED_NOT_OPERATIONAL",
        "openrouter": (
            "PAID_PILOT_IN_PROGRESS_NOT_OPERATIONAL"
            if openrouter_spend > 0 or openrouter_candidates > 0
            else "PAID_PILOT_AUTHORIZED_NOT_EXECUTED"
        ) if policy["budgets"]["openrouter"]["released_stage_usd"] == "5.00" else "BUDGET_BLOCKED",
        "cursor": (
            "PAID_PILOT_IN_PROGRESS_NOT_OPERATIONAL"
            if cursor_agents > 0
            else "PAID_PILOT_AUTHORIZED_ZERO_REAL_AGENTS"
        ) if policy["budgets"]["cursor"]["released_stage_usd"] == "20.00" else "BUDGET_BLOCKED",
        "local_qwen": "ONE_EMBEDDING_ROUTE_READY_EVIDENCE_AND_CODER_ROUTES_REJECTED"
        if local["qualification_disposition"] == "EMPIRICALLY_REJECTED_NO_OPERATIONAL_ROUTE"
        and any(item.get("result") == "PASS_CANDIDATE_RETRIEVAL_ONLY_EXACT_ROUTE_READY" for item in local.get("shadow_qualifications", []))
        else "EVIDENCE_CONFLICT",
        "remote_cpu_worker": "QUALIFIED_CANDIDATE_DETERMINISTIC_ONLY"
        if cpu["readiness_disposition"] == "QUALIFIED_CANDIDATE_DETERMINISTIC_ONLY"
        and cpu["qualification"]["disposition"] == "PASS"
        else "EVIDENCE_CONFLICT",
        "unified_plane": "IMPLEMENTED_NONLIVE",
    }
    evidence = {
        "settled_openai_calls": openai_calls,
        "openrouter_validated_candidates": openrouter_candidates,
        "openrouter_failed_or_quarantined_manifests": openrouter_failures,
        "openrouter_settled_usd": format(openrouter_spend, "f"),
        "cursor_real_agents": cursor_agents,
        "local_qwen_accepted_operational_routes": sum(
            item.get("result") == "PASS_CANDIDATE_RETRIEVAL_ONLY_EXACT_ROUTE_READY"
            for item in local.get("shadow_qualifications", [])
        ),
        "cpu_corrected_live_qualification_passes": int(
            cpu["readiness_disposition"] == "QUALIFIED_CANDIDATE_DETERMINISTIC_ONLY"
            and cpu["qualification"]["disposition"] == "PASS"
        ),
        "scheduler_real_cycles": 0,
        "soak_calendar_days": 0,
        "retries_health_catalog_counted_as_accepted": 0,
        "failed_or_rejected_work_omitted": False,
        "structural_and_operational_results_separate": True,
        "credential_presence": {
            "openai": credential_present_once("OPENAI_API_KEY"),
            "openrouter": credential_present_once("OPENROUTER_API_KEY"),
            "cursor": credential_present_once("CURSOR_API_TOKEN"),
        },
        "provider_catalogs_present": {
            "openrouter": (OPENROUTER_ROOT / "catalogs").is_dir(),
            "cursor": (CURSOR_ROOT / "catalogs").is_dir(),
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
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--claims",
        type=Path,
        default=ROOT / "configs/unified_assistive_operational_claims.json",
    )
    parser.add_argument("--inventory-snapshot", type=Path)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    claims = json.loads(args.claims.read_text(encoding="utf-8"))
    states, evidence = derive_states()
    findings = validate_claims(claims, states)
    inventory = None
    if args.inventory_snapshot:
        inventory = {
            "path": str(args.inventory_snapshot),
            "sha256": sha256(args.inventory_snapshot),
        }
        payload = json.loads(args.inventory_snapshot.read_text(encoding="utf-8"))
        if payload["validation"]["coverage_fraction"] != 1.0:
            findings.append("READY_WORK_COVERAGE_INCOMPLETE")
    report = {
        "schema_version": 1,
        "derived_states": states,
        "claims_sha256": sha256(args.claims),
        "inventory": inventory,
        "evidence_counts": evidence,
        "structural_validity": "SEPARATELY_VALIDATED",
        "operational_completeness": "PASS_HONEST_PARTIAL_STATE" if not findings else "FAIL",
        "findings": findings,
    }
    path, digest = write_content_addressed_json(args.output_root, "completeness", report)
    print(json.dumps({"status": "PASS" if not findings else "FAIL", "path": str(path), "sha256": digest, "derived_states": states}, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
