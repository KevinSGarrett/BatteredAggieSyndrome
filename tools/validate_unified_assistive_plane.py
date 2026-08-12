from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.bypass import find_direct_endpoint_bypasses
from aggie_analytics.assistive_plane.cursor_backend import CursorRunPolicy
from aggie_analytics.assistive_plane.ollama_backend import OllamaRoutePolicy


REQUIRED_FILES = [
    "configs/unified_assistive_policy.json",
    "configs/assistive_provider_registry.json",
    "configs/assistive_route_readiness.json",
    "configs/unified_assistive_operational_claims.json",
    "configs/unified_assistive_ready_work.json",
    "governance/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
    "docs/architecture/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
    "docs/operations/UNIFIED_ASSISTIVE_EXECUTION_PLANE.md",
    "src/aggie_analytics/assistive_plane/orchestration.py",
    "src/aggie_analytics/assistive_plane/cursor_backend.py",
    "src/aggie_analytics/assistive_plane/ollama_backend.py",
    "src/aggie_analytics/assistive_plane/cpu_worker_backend.py",
    "tools/refresh_cursor_catalog.py",
    "tools/refresh_local_assistive_runtime.py",
    "tools/sync_unified_assistive_jira_graph.py",
    "tools/materialize_unified_assistive_inventory.py",
    "tools/run_local_qwen_qualification.py",
    "tools/validate_local_qwen_qualification.py",
    "configs/local_qwen_qualification.json",
    "schemas/assistive/local_qwen_candidate.schema.json",
    "artifacts/assistive/local_qwen_qualification.json",
    "configs/cpu_worker_qualification.json",
    "tools/cpu_worker_service.py",
    "tools/install_cpu_worker_service.ps1",
    "tools/qualify_cpu_worker.py",
    "tools/refresh_cpu_worker_readiness.py",
    "tools/validate_cpu_worker_readiness.py",
    "tools/validate_unified_assistive_completeness.py",
    "artifacts/assistive/cpu_worker_readiness.json",
]


def main() -> int:
    findings: list[str] = []
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            findings.append(f"REQUIRED_FILE_MISSING:{relative}")
    policy = json.loads((ROOT / "configs/unified_assistive_policy.json").read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "configs/assistive_provider_registry.json").read_text(encoding="utf-8"))
    if policy.get("effort_points") != [1, 2, 3, 5, 8]:
        findings.append("EFFORT_POINT_SET_INVALID")
    if policy["inventory"].get("required_coverage_fraction") != 1.0:
        findings.append("INVENTORY_COVERAGE_NOT_COMPLETE")
    expected = {"openai", "openrouter", "cursor", "local_qwen", "remote_cpu_worker", "codex_deterministic"}
    if set(registry.get("providers", {})) != expected:
        findings.append("PROVIDER_REGISTRY_INCOMPLETE")
    if policy["budgets"]["openrouter"]["hard_limit_usd"] != "25.00":
        findings.append("OPENROUTER_BUDGET_AUTHORITY_DRIFT")
    if policy["budgets"]["openrouter"].get("released_stage_usd") != "5.00":
        findings.append("OPENROUTER_RELEASE_STAGE_DRIFT")
    if policy["budgets"]["cursor"]["hard_limit_usd"] != "200.00":
        findings.append("CURSOR_BUDGET_AUTHORITY_DRIFT")
    if policy["budgets"]["cursor"].get("released_stage_usd") != "20.00":
        findings.append("CURSOR_RELEASE_STAGE_DRIFT")
    routes = json.loads((ROOT / "configs/assistive_route_readiness.json").read_text(encoding="utf-8"))
    rejected = [item for item in routes["routes"] if item["state"] == "NOT_READY"]
    if len(rejected) != 4:
        findings.append("EXACT_REJECTED_LOCAL_ROUTE_COUNT_INVALID")
    if routes.get("human_status_override_allowed") is not False:
        findings.append("HUMAN_STATUS_CAN_OVERRIDE_EMPIRICAL_REJECTION")
    expected_rejected = {
        ("qwen2.5:7b-instruct", "evidence_critical_local_candidate_10_packet", "BAT-562-local-qwen-10-packet-v1"),
        ("qwen2.5:7b-instruct", "evidence_critical_local_candidate_10_packet", "BAT-562-local-qwen-10-packet-v2"),
        ("qwen3-vl:8b-instruct-q4_K_M", "evidence_critical_local_candidate_10_packet", "BAT-562-local-qwen-10-packet-v3-qwen3vl8b"),
        ("qwen2.5-coder:7b-instruct-q4_K_M", "bounded_code_review_test_generation_parser_scaffolding", "local-coder-shadow-v1"),
    }
    rejected_identities = {
        (item["resolved_model"], item["task_format"], item["prompt_version"])
        for item in rejected
    }
    if rejected_identities != expected_rejected:
        findings.append("EXACT_REJECTED_LOCAL_ROUTE_IDENTITIES_INVALID")
    ready = [item for item in routes["routes"] if item["state"] == "READY"]
    if len(ready) != 1 or (
        ready[0]["resolved_model"],
        ready[0]["task_format"],
        ready[0]["prompt_version"],
    ) != ("bge-m3:latest", "embedding_dedup_semantic_candidate_retrieval", "embedding-shadow-v1"):
        findings.append("EXACT_READY_LOCAL_ROUTE_IDENTITIES_INVALID")
    try:
        CursorRunPolicy().validate()
        OllamaRoutePolicy("http://127.0.0.1:11434", "qwen2.5:7b-instruct", "845dbda0ea48").validate()
    except ValueError as exc:
        findings.append(f"DEFAULT_ROUTE_POLICY_INVALID:{exc}")
    findings.extend(find_direct_endpoint_bypasses(ROOT))
    if findings:
        print(json.dumps({"status": "FAIL", "findings": findings}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "provider_count": len(expected), "required_files": len(REQUIRED_FILES)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
