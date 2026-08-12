from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.schemas import validate_strict_schema  # noqa: E402


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    policy = json.loads((root / "configs/openrouter_assist_policy.json").read_text(encoding="utf-8"))
    if policy["budget"]["paid_hard_limit_usd"] != "25.00" or policy["budget"]["released_stage_usd"] != "5.00" or policy["budget"]["paid_calls_authorized"] is not True:
        errors.append("paid OpenRouter authority must preserve the authorized USD 25 hard cap and USD 5 released stage")
    if policy["budget"].get("authorization_id") != "USER-OPENROUTER-25-2026-08-12" or policy["budget"].get("nontransferable") is not True:
        errors.append("OpenRouter authorization identity or nontransferable boundary is invalid")
    if policy["budget"]["direct_openai_budget_transfer_usd"] != "0.00":
        errors.append("direct OpenAI funds must not transfer to OpenRouter")
    defaults = policy["provider_defaults"]
    required_defaults = {"require_parameters": True, "data_collection": "deny", "zdr": True, "allow_fallbacks": False, "cross_model_fallbacks": False}
    if defaults != required_defaults:
        errors.append("OpenRouter privacy/provider defaults drifted")
    if policy["api"]["batch_enabled"] is not False:
        errors.append("OpenRouter Batch Beta must remain disabled until its separate gate passes")
    registry = json.loads((root / "configs/assistive_provider_registry.json").read_text(encoding="utf-8"))
    required_invariants = {"ONE_PROVIDER_PER_REQUEST", "NO_BUDGET_TRANSFER_BETWEEN_PROVIDERS", "DETERMINISTIC_PROJECT_AUTHORITY_RETAINED", "NO_CANONICAL_OR_PROTECTED_TRUTH_WRITES"}
    if not required_invariants.issubset(set(registry["invariants"])):
        errors.append("provider-neutral registry invariants drifted")
    tasks = json.loads((root / "configs/openrouter_task_registry.json").read_text(encoding="utf-8"))["tasks"]
    for task_name, task in tasks.items():
        path = root / task["schema"]
        try:
            validate_strict_schema(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            errors.append(f"{task_name} strict schema: {exc}")
    backend_source = (root / "src/aggie_analytics/assistive_plane/openrouter_backend.py").read_text(encoding="utf-8")
    responses_endpoint = "https://openrouter.ai/api/v1/" + "responses"
    if backend_source.count(responses_endpoint) != 1:
        errors.append("OpenRouter API endpoint must be owned only once by the backend")
    for path in [root / "src", root / "tools", root / "tests"]:
        for candidate in path.rglob("*.py"):
            if candidate.name != "openrouter_backend.py" and responses_endpoint in candidate.read_text(encoding="utf-8", errors="ignore"):
                errors.append(f"scattered OpenRouter endpoint: {candidate.relative_to(root)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = validate(args.repo_root.resolve())
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: governed OpenRouter assistive foundation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
