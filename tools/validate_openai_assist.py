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
    for task_name in ["gamebook_extraction", "depth_chart_document_extraction", "entity_review", "quarantine_schema_classification"]:
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

    depth_policy = json.loads(
        (root / "configs" / "openai_depth_chart_pilot.json").read_text(encoding="utf-8")
    )
    depth_prompt = depth_policy["prompt"]
    depth_prompt_path = root / depth_prompt["path"]
    if hashlib.sha256(depth_prompt_path.read_bytes()).hexdigest() != depth_prompt["sha256"]:
        errors.append("OpenAI depth-chart pilot prompt hash disagrees with policy")
    if depth_policy["authority"] != "SHADOW_DOCUMENT_CANDIDATE_ONLY_NO_PIT_OR_AVAILABILITY_ADMISSION":
        errors.append("OpenAI depth-chart pilot grants unsafe authority")
    if len(depth_policy.get("samples", [])) != 7:
        errors.append("OpenAI depth-chart pilot must retain seven representative official pages")
    depth_routes = {route["model"]: route for route in depth_policy.get("routes", [])}
    if set(depth_routes) != {"gpt-5-nano", "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"}:
        errors.append("OpenAI depth-chart pilot must compare Nano, Luna, Terra, and Sol")
    if depth_routes.get("gpt-5.6-terra", {}).get("reasoning_effort") != "low":
        errors.append("OpenAI depth-chart pilot must give Terra explicit low reasoning")
    if depth_routes.get("gpt-5.6-sol", {}).get("reasoning_effort") != "medium":
        errors.append("OpenAI depth-chart pilot must give Sol explicit medium reasoning")
    if depth_policy["source_candidate"].get("historical_publication_time_state") != "UNKNOWN":
        errors.append("OpenAI depth-chart pilot must preserve unknown historical publication time")
    if depth_policy["source_candidate"].get("canonical_or_pit_admission") is not False:
        errors.append("OpenAI depth-chart pilot source cannot be canonically or PIT admitted")
    depth_acceptance = depth_policy.get("acceptance", {})
    if depth_acceptance.get("unsupported_fact_rate_max") != 0.0:
        errors.append("OpenAI depth-chart pilot must require zero unsupported facts")
    if depth_acceptance.get("historical_timestamp_fabrication_max") != 0:
        errors.append("OpenAI depth-chart pilot must require zero fabricated timestamps")

    availability_policy = json.loads(
        (root / "configs" / "openai_availability_source_triage.json").read_text(encoding="utf-8")
    )
    availability_prompt = availability_policy["prompt"]
    availability_prompt_path = root / availability_prompt["path"]
    if hashlib.sha256(availability_prompt_path.read_bytes()).hexdigest() != availability_prompt["sha256"]:
        errors.append("availability source-triage prompt hash disagrees with policy")
    availability_task = registry["tasks"].get("availability_source_triage", {})
    if availability_task.get("jira_unit") != "POST-SUBTASK-168":
        errors.append("continuing availability source triage is not bound to POST-SUBTASK-168")
    if availability_task.get("candidate_destination") != "REVIEW":
        errors.append("availability source triage must remain review-only")
    availability_routes = {route["model"]: route for route in availability_policy.get("routes", [])}
    if set(availability_routes) != {"gpt-5-nano", "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"}:
        errors.append("availability source triage must compare Nano, Luna, Terra, and Sol")
    if availability_policy["source_sample"].get("historical_publication_time_state") != "UNKNOWN":
        errors.append("availability source triage must preserve unknown historical publication time")
    if availability_policy["source_sample"].get("canonical_or_pit_admission") is not False:
        errors.append("availability source triage cannot have canonical/PIT authority")
    if availability_policy["acceptance"].get("unsupported_fact_rate_max") != 0.0:
        errors.append("availability source triage must require zero unsupported facts")
    if availability_policy["acceptance"].get("historical_timestamp_fabrication_max") != 0:
        errors.append("availability source triage must require zero fabricated timestamps")

    continuous_report = json.loads(
        (root / "artifacts" / "openai_assist" / "continuous_operations.json").read_text(encoding="utf-8")
    )
    if continuous_report.get("decision_unit") != "POST-SUBTASK-168":
        errors.append("continuing OpenAI report has the wrong Jira identity")
    checkpoint = continuous_report.get("availability_source_triage_checkpoint", {})
    if checkpoint.get("provider_calls") != 64 or checkpoint.get("batch_jobs") != 0:
        errors.append("continuing OpenAI report has unexpected job counts")
    if not {"gpt-5.6-terra", "gpt-5.6-sol"}.issubset(set(checkpoint.get("models", {}))):
        errors.append("continuing OpenAI report lacks representative Terra/Sol work")
    dispositions = checkpoint.get("dispositions", {})
    if dispositions.get("canonical_writes") != 0 or dispositions.get("rejected") != 0:
        errors.append("continuing OpenAI report crossed authority or lost provider results")
    gamebook_checkpoint = continuous_report.get("gamebook_schema_mapping_checkpoint", {})
    if gamebook_checkpoint.get("provider_calls") != 14 or gamebook_checkpoint.get("batch_jobs") != 0:
        errors.append("gamebook schema-mapping checkpoint has unexpected job counts")
    if set(gamebook_checkpoint.get("models", {})) != {
        "gpt-5-nano", "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"
    }:
        errors.append("gamebook schema-mapping checkpoint lacks the balanced model comparison")
    gamebook_metrics = gamebook_checkpoint.get("metrics", {})
    if (
        gamebook_metrics.get("strict_schema_rate") != 1.0
        or gamebook_metrics.get("evidence_accuracy") != 1.0
        or gamebook_metrics.get("unsupported_fact_rate") != 0.0
    ):
        errors.append("gamebook schema-mapping checkpoint violates schema/evidence invariants")
    if any(
        gamebook_metrics.get(field) != 0
        for field in ["canonical_writes", "pit_writes", "training_feature_writes", "protected_truth_writes"]
    ):
        errors.append("gamebook schema-mapping checkpoint crossed candidate-only authority")
    if gamebook_checkpoint.get("source_population", {}).get(
        "games_with_actions_but_no_explicit_play_collection"
    ) != 50:
        errors.append("gamebook schema-mapping checkpoint does not bind the source gap population")
    visual_checkpoint = continuous_report.get("depth_chart_noncoverage_visual_checkpoint", {})
    if visual_checkpoint.get("provider_calls") != 4 or visual_checkpoint.get("batch_jobs") != 0:
        errors.append("depth-chart noncoverage visual checkpoint has unexpected job counts")
    if visual_checkpoint.get("deterministic_classification") != "STARTING_LINEUP_HISTORY_NOT_DEPTH_CHART":
        errors.append("depth-chart noncoverage visual checkpoint changed the deterministic negative finding")
    visual_model = visual_checkpoint.get("models", {}).get("gpt-4o-mini", {})
    if visual_model.get("corrected_exact_review_candidates") != 2:
        errors.append("depth-chart noncoverage fixed-object visual review did not retain two exact candidates")
    if any(
        visual_checkpoint.get(field) != 0
        for field in ["canonical_writes", "pit_writes", "training_feature_writes", "protected_truth_writes"]
    ):
        errors.append("depth-chart noncoverage visual checkpoint crossed candidate-only authority")
    budget_checkpoint = continuous_report.get("budget", {})
    if (
        budget_checkpoint.get("remaining_usd") != "95.469485"
        or budget_checkpoint.get("settled_usd") != "4.530515"
        or budget_checkpoint.get("cumulative_calls") != 492
    ):
        errors.append("continuing OpenAI report does not reconcile the usage ledger")
    if continuous_report.get("completion", {}).get("continuing_operations_active") is not True:
        errors.append("BAT-522 was incorrectly treated as terminal API use")

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

    depth_report = json.loads(
        (root / "artifacts" / "openai_assist" / "depth_chart_pilot.json").read_text(
            encoding="utf-8"
        )
    )
    if depth_report.get("authority") != depth_policy["authority"]:
        errors.append("OpenAI depth-chart report disagrees with its candidate-only authority")
    comparison = depth_report.get("comparison_plan", {})
    if comparison.get("request_count") != 28 or comparison.get("request_id_count") != 28:
        errors.append("OpenAI depth-chart preflight must retain all 28 governed request identities")
    depth_report_models = {route.get("model") for route in comparison.get("routes", [])}
    if not {"gpt-5.6-terra", "gpt-5.6-sol"}.issubset(depth_report_models):
        errors.append("OpenAI depth-chart preflight lacks meaningful Terra and Sol routes")
    if comparison.get("preflight_result") != "PASS":
        errors.append("OpenAI depth-chart request preflight did not pass")
    if comparison.get("live_api_calls") != 0 or comparison.get("actual_cost_usd") != "0.000000":
        errors.append("OpenAI depth-chart checkpoint must not claim unexecuted live spend")
    admission = depth_report.get("admission", {})
    for key in [
        "canonical_player_identity", "availability_or_injury_truth", "historical_publication_time",
        "pit_state", "training_features", "protected_evaluation", "forecast_or_publication",
    ]:
        if admission.get(key) is not False:
            errors.append(f"OpenAI depth-chart report grants unsafe {key} admission")

    quarantine_policy = json.loads(
        (root / "configs" / "openai_quarantine_schema_pilot.json").read_text(encoding="utf-8")
    )
    quarantine_prompt = quarantine_policy["prompt"]
    quarantine_prompt_path = root / quarantine_prompt["path"]
    if hashlib.sha256(quarantine_prompt_path.read_bytes()).hexdigest() != quarantine_prompt["sha256"]:
        errors.append("OpenAI quarantine/schema pilot prompt hash disagrees with policy")
    expected_categories = {
        "CORRUPTION", "MISSINGNESS", "SCHEMA_DRIFT", "INCOMPATIBLE_MAPPING",
        "EVIDENCE_ABSENT", "CROSS_SOURCE_CONFLICT", "PIT_RISK", "TARGET_LEAKAGE",
    }
    if {case["classification_code"] for case in quarantine_policy["cases"]} != expected_categories:
        errors.append("OpenAI quarantine/schema pilot does not cover every required risk category")
    quarantine_routes = {route["model"]: route for route in quarantine_policy["routes"]}
    if set(quarantine_routes) != {"gpt-5-nano", "gpt-5.6-terra", "gpt-5.6-sol"}:
        errors.append("OpenAI quarantine/schema pilot must compare Nano, Terra, and Sol")
    expected_case_counts = {"gpt-5-nano": 8, "gpt-5.6-terra": 4, "gpt-5.6-sol": 2}
    for model, expected_count in expected_case_counts.items():
        if len(quarantine_routes.get(model, {}).get("case_ids", [])) != expected_count:
            errors.append(f"OpenAI quarantine/schema pilot route count disagrees for {model}")
    quarantine_acceptance = quarantine_policy["predeclared_acceptance"]
    for metric in [
        "strict_schema_rate", "exact_classification_rate", "evidence_accuracy",
        "deterministic_route_accuracy", "canonical_authority_none_rate",
        "quarantine_preservation_rate",
    ]:
        if quarantine_acceptance.get(metric) != 1.0:
            errors.append(f"OpenAI quarantine/schema pilot must require {metric}=1.0")
    for metric in ["unsupported_fact_rate", "canonical_writes", "protected_truth_writes"]:
        if quarantine_acceptance.get(metric) != 0.0 and quarantine_acceptance.get(metric) != 0:
            errors.append(f"OpenAI quarantine/schema pilot must require {metric}=0")
    quarantine_report = json.loads(
        (root / "artifacts" / "openai_assist" / "quarantine_schema_pilot.json").read_text(
            encoding="utf-8"
        )
    )
    if quarantine_report.get("governing_plan_sha256") != policy.payload.get(
        "governing_plan_sha256"
    ):
        errors.append("OpenAI quarantine/schema report is not bound to the active plan")
    if quarantine_report.get("status") != "COMPLETE_NEGATIVE_PROMOTION_RESULT":
        errors.append("OpenAI quarantine/schema negative promotion result was not preserved")
    execution = quarantine_report.get("execution", {})
    if execution.get("synchronous_jobs") != 14 or execution.get("batch_jobs") != 0:
        errors.append("OpenAI quarantine/schema report has unexpected job counts")
    report_models = execution.get("models", {})
    if set(report_models) != {"gpt-5-nano", "gpt-5.6-terra", "gpt-5.6-sol"}:
        errors.append("OpenAI quarantine/schema report lacks the required model comparison")
    observed = quarantine_report.get("observed", {})
    if observed.get("canonical_writes") != 0 or observed.get("protected_truth_writes") != 0:
        errors.append("OpenAI quarantine/schema report crossed its candidate-only authority boundary")
    if observed.get("quarantine_preservation_rate") != 1.0:
        errors.append("OpenAI quarantine/schema report did not preserve every quarantine")
    decision = quarantine_report.get("promotion_decision", {})
    if decision.get("predeclared_gate_passed") is not False:
        errors.append("OpenAI quarantine/schema failed gate must not be rewritten as passing")
    if any(decision.get(key) is not False for key in [
        "nano_batch_promoted", "terra_reserve_released", "sol_reserve_released",
    ]):
        errors.append("OpenAI quarantine/schema report grants an unsupported promotion or reserve release")

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
