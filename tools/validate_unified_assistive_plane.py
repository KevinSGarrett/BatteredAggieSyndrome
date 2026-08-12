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
    if policy["budgets"]["openrouter"]["hard_limit_usd"] != "0.00":
        findings.append("OPENROUTER_BUDGET_AUTHORITY_DRIFT")
    if policy["budgets"]["cursor"]["hard_limit_usd"] != "0.00":
        findings.append("CURSOR_BUDGET_AUTHORITY_DRIFT")
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
