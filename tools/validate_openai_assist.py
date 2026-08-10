from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from aggie_analytics.openai_assist.policy import AssistivePolicy  # noqa: E402
from aggie_analytics.openai_assist.schemas import validate_strict_output_schema  # noqa: E402
from validate_product_supply_chain import lock_policy_errors, normalize_name  # noqa: E402


def _unsupported_structured_output_keywords(value: object, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"maxItems", "minItems", "uniqueItems"}:
                errors.append(f"{path}.{key}")
            errors.extend(_unsupported_structured_output_keywords(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_unsupported_structured_output_keywords(child, f"{path}[{index}]"))
    return errors


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        policy = AssistivePolicy.load(root)
    except Exception as exc:
        return [f"policy: {exc}"]
    for schema_name in ["assistive_candidate.schema.json", "assistive_evaluation.schema.json"]:
        try:
            schema = json.loads(
                (root / "schemas" / "openai" / schema_name).read_text(encoding="utf-8")
            )
            validate_strict_output_schema(schema)
            for keyword_path in _unsupported_structured_output_keywords(schema):
                errors.append(f"unsupported Structured Outputs keyword: {schema_name}:{keyword_path}")
        except Exception as exc:
            errors.append(f"strict schema {schema_name}: {exc}")

    evaluation_policy = json.loads(
        (root / "configs" / "openai_evaluation_policy.json").read_text(encoding="utf-8")
    )
    prompt = evaluation_policy["prompt"]
    prompt_path = root / prompt["path"]
    prompt_sha256 = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    if prompt_sha256 != prompt["sha256"]:
        errors.append("OpenAI evaluation prompt hash disagrees with policy")
    gold_path = root / evaluation_policy["gold_corpus"]
    if hashlib.sha256(gold_path.read_bytes()).hexdigest() != evaluation_policy["gold_corpus_sha256"]:
        errors.append("OpenAI evaluation gold-corpus hash disagrees with policy")
    if evaluation_policy["acceptance"]["unsupported_fact_rate_max"] != 0.0:
        errors.append("OpenAI evaluation must require zero unsupported facts")
    if evaluation_policy["acceptance"]["false_merge_rate_max"] != 0.0:
        errors.append("OpenAI evaluation must require zero false merges")

    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    direct = project["project"].get("optional-dependencies", {}).get("openai-assist", [])
    if direct != ["openai==2.53.0"]:
        errors.append("openai-assist optional dependency must be exactly openai==2.53.0")
    entries, lock_errors = lock_policy_errors(root / "requirements" / "openai-assist.lock")
    errors.extend(f"openai lock: {error}" for error in lock_errors)
    locked = {entry.normalized_name: entry.version for entry in entries}
    if locked.get(normalize_name("openai")) != "2.53.0":
        errors.append("OpenAI SDK direct pin and lock disagree")
    if len(entries) != 17:
        errors.append(f"OpenAI assist lock must contain 17 exact packages, got {len(entries)}")

    package_root = root / "src" / "aggie_analytics"
    for path in package_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(root).as_posix()
        if "from openai import" in text and not relative.endswith("openai_assist/controller.py"):
            errors.append(f"scattered direct OpenAI SDK import: {relative}")
        if "openai_assist" in text and "src/aggie_analytics/openai_assist/" not in relative:
            errors.append(f"forecast/runtime package imports optional assistive plane: {relative}")
    if policy.payload["api"]["responses_endpoint"] != "/v1/responses":
        errors.append("new work must use the Responses API")
    if policy.payload["api"]["store"] is not False:
        errors.append("Responses requests must set store false")
    if any(path.name == ".env" for path in root.rglob(".env") if path.parent != root):
        errors.append("a credential file was copied below the worktree root")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = validate(args.repo_root.resolve())
    if errors:
        print("FAIL: OpenAI assistive-plane validation")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: OpenAI assistive-plane policy, schema, dependency, authority, and isolation gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
