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
    budget = policy.payload["budget"]
    if policy.payload.get("governing_plan_sha256") != "651bbff29cb929cdc441178f67df59e87600a3bc8a54516a942562c7d09aa523":
        errors.append("OpenAI policy is not bound to the superseding Terra/Sol plan")
    if budget["allocations"].get("TERRA_COMPLEX") != "15.00":
        errors.append("Terra base budget must be USD 15")
    if budget["allocations"].get("SOL_GOLD_HARD") != "10.00":
        errors.append("Sol base budget must be USD 10")
    if budget["allocations"].get("VALUE_GATED_RESERVE") != "22.00":
        errors.append("value-gated reserve must be USD 22")
    if budget["model_caps"].get("gpt-5.6-terra", {}).get("reserve_max_usd") != "25.00":
        errors.append("Terra reserve maximum must be USD 25")
    if budget["model_caps"].get("gpt-5.6-sol", {}).get("reserve_max_usd") != "17.00":
        errors.append("Sol reserve maximum must be USD 17")
    if budget.get("initial_pilot_required_models") != ["gpt-5.6-terra", "gpt-5.6-sol"]:
        errors.append("initial pilot must require representative Terra and Sol calls")
    registry = json.loads((root / "configs" / "openai_task_registry.json").read_text(encoding="utf-8"))
    if registry.get("routing_objective") != "ACCEPTED_EVIDENCE_VERIFIED_RECORDS_PER_DOLLAR":
        errors.append("router objective is not accepted evidence-verified records per dollar")
    for task_name in ["gamebook_extraction", "entity_review", "quarantine_schema_classification"]:
        task = registry["tasks"][task_name]
        if task.get("default_model") != "gpt-5-nano":
            errors.append(f"{task_name} must default validated bulk work to GPT-5 Nano")
        if not {"gpt-5.6-terra", "gpt-5.6-sol"}.issubset(set(task.get("allowed_models", []))):
            errors.append(f"{task_name} must preserve meaningful Terra/Sol escalation routes")
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

    gamebook_policy = json.loads(
        (root / "configs" / "openai_gamebook_pilot.json").read_text(encoding="utf-8")
    )
    gamebook_prompt = gamebook_policy["prompt"]
    gamebook_prompt_path = root / gamebook_prompt["path"]
    if hashlib.sha256(gamebook_prompt_path.read_bytes()).hexdigest() != gamebook_prompt["sha256"]:
        errors.append("OpenAI gamebook pilot prompt hash disagrees with policy")
    if gamebook_policy["authority"] != "SHADOW_CANDIDATE_ONLY":
        errors.append("OpenAI gamebook pilot must remain shadow candidate only")
    play_samples = [
        sample
        for sample in gamebook_policy["samples"]
        if sample.get("extractor", {}).get("type") == "parquet_play"
    ]
    if len(play_samples) != 5:
        errors.append("OpenAI gamebook pilot must retain the predeclared five-play gold sample")
    required_gamebook_domains = {
        "drives",
        "plays",
        "team_box_scores",
        "player_box_scores",
        "roster_starter_facts",
        "venue",
        "officials",
        "weather",
        "attendance",
        "source_metadata",
    }
    declared_domains = set(gamebook_policy.get("required_domains", []))
    covered_domains = {
        domain for sample in gamebook_policy["samples"] for domain in sample.get("domains", [])
    }
    if declared_domains != required_gamebook_domains:
        errors.append("OpenAI gamebook pilot required-domain contract is incomplete or expanded without review")
    if covered_domains != required_gamebook_domains:
        errors.append("OpenAI gamebook pilot gold configuration does not cover every required domain")
    if gamebook_policy["acceptance"]["unsupported_fact_rate_max"] != 0.0:
        errors.append("OpenAI gamebook pilot must require zero unsupported facts")

    entity_policy = json.loads(
        (root / "configs" / "openai_entity_review_pilot.json").read_text(encoding="utf-8")
    )
    entity_prompt = entity_policy["prompt"]
    entity_prompt_path = root / entity_prompt["path"]
    if hashlib.sha256(entity_prompt_path.read_bytes()).hexdigest() != entity_prompt["sha256"]:
        errors.append("OpenAI entity-review pilot prompt hash disagrees with policy")
    if entity_policy["authority"] != "SHADOW_REVIEW_ONLY_NO_MERGE_AUTHORITY":
        errors.append("OpenAI entity-review pilot must remain shadow review only")
    positive_ids = entity_policy.get("positive_resolution_ids", [])
    ambiguous_ids = entity_policy.get("ambiguous_resolution_ids", [])
    if len(positive_ids) != 6 or len(set(positive_ids)) != 6:
        errors.append("OpenAI entity-review pilot must retain six unique positive gold cases")
    if len(ambiguous_ids) != 6 or len(set(ambiguous_ids)) != 6:
        errors.append("OpenAI entity-review pilot must retain six unique ambiguous gold cases")
    acceptance = entity_policy.get("predeclared_acceptance", {})
    for metric in [
        "strict_schema_rate", "field_precision", "field_recall", "evidence_accuracy",
        "correct_abstention_rate", "entity_top_k_recall",
    ]:
        if acceptance.get(metric) != 1.0:
            errors.append(f"OpenAI entity-review pilot must require {metric}=1.0")
    for metric in [
        "unsupported_fact_rate", "false_merge_rate", "candidate_set_error_rate", "canonical_writes",
    ]:
        if acceptance.get(metric) != 0.0:
            errors.append(f"OpenAI entity-review pilot must require {metric}=0.0")

    entity_report = json.loads(
        (root / "artifacts" / "openai_assist" / "entity_review_pilot.json").read_text(
            encoding="utf-8"
        )
    )
    if entity_report["authority"] != "SHADOW_REVIEW_ONLY_NO_MERGE_AUTHORITY":
        errors.append("OpenAI entity-review report grants unsafe authority")
    for metric in [
        "strict_schema_rate", "field_precision", "field_recall", "evidence_accuracy",
        "correct_abstention_rate", "entity_top_k_recall",
    ]:
        if entity_report["results"].get(metric) != 1.0:
            errors.append(f"OpenAI entity-review report failed {metric}")
    for metric in [
        "unsupported_fact_rate", "false_merge_rate", "candidate_set_error_rate", "canonical_writes",
    ]:
        if entity_report["results"].get(metric) != 0.0:
            errors.append(f"OpenAI entity-review report failed {metric}")
    if entity_report["route_decision"].get("merge_authority") is not False:
        errors.append("OpenAI entity-review route decision must deny merge authority")
    if entity_report["results"].get("completed_predictions") != 36:
        errors.append("OpenAI entity-review report must retain all 36 bounded predictions")
    entity_models = {key.split(":", 1)[0] for key in entity_report.get("models", {})}
    if not {"gpt-5.6-terra", "gpt-5.6-sol"}.issubset(entity_models):
        errors.append("entity-review pilot did not include representative Terra and Sol calls")

    gamebook_report = json.loads(
        (root / "artifacts" / "openai_assist" / "gamebook_pilot.json").read_text(encoding="utf-8")
    )
    gamebook_models = {key.split(":", 1)[0] for key in gamebook_report.get("models", {})}
    if not {"gpt-5.6-terra", "gpt-5.6-sol"}.issubset(gamebook_models):
        errors.append("gamebook pilot did not include representative Terra and Sol calls")

    rebalance_report = json.loads(
        (root / "artifacts" / "openai_assist" / "router_rebalance.json").read_text(
            encoding="utf-8"
        )
    )
    if rebalance_report.get("governing_plan", {}).get("sha256") != policy.payload.get(
        "governing_plan_sha256"
    ):
        errors.append("router-rebalance evidence is not bound to the active governing plan")
    rebalance_usage = rebalance_report.get("usage_at_rebalance", {})
    if rebalance_usage.get("settled_usd") != "2.665852":
        errors.append("router-rebalance evidence does not preserve the pre-migration settled usage")
    if rebalance_usage.get("new_api_calls_for_rebalance") != 0:
        errors.append("router policy migration must not consume OpenAI credits")
    rebalance_authority = rebalance_report.get("authority", {})
    if rebalance_authority.get("canonical_writes") != 0:
        errors.append("router-rebalance evidence reports canonical writes")
    if rebalance_authority.get("protected_truth_writes") != 0:
        errors.append("router-rebalance evidence reports protected-truth writes")

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
