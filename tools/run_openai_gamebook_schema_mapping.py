from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.openai_assist.contracts import Priority, ProcessingMode  # noqa: E402
from aggie_analytics.openai_assist.controller import AssistiveController, AssistiveJob  # noqa: E402
from aggie_analytics.openai_assist.evals import evaluate  # noqa: E402


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _job(
    controller: AssistiveController,
    config: dict[str, Any],
    prompt_base: str,
    schema_path: Path,
    route: dict[str, Any],
    case: dict[str, Any],
) -> AssistiveJob:
    fields = [fact["field"] for fact in case["expected_facts"]]
    prompt = (
        f"{prompt_base.rstrip()}\n\n"
        f"Case ID: {case['case_id']}\n"
        f"Return task_id exactly {config['task_name']} and case_id exactly {case['case_id']}.\n"
        f"Return disposition REVIEW. Extract exactly these fields in this order: "
        f"{json.dumps(fields, separators=(',', ':'))}.\n"
        "For every SUPPORTED fact, evidence must contain exactly one item whose "
        "source_capture_sha256 and excerpt_sha256 both equal SOURCE_CAPTURE_SHA256 and whose locator is evidence:1."
    )
    model = route["model"]
    return AssistiveJob(
        task_name=config["task_name"],
        jira_unit=config["jira_unit"],
        source_url=f"{case['source_url']}#record={case['source_record_sha256']}&case={case['case_id']}",
        source_capture_sha256=case["source_capture_sha256"],
        source_excerpt=case["source_excerpt"],
        prompt=prompt,
        prompt_version=config["prompt"]["version"],
        schema_path=schema_path,
        schema_version="1",
        model=model,
        reasoning_effort=route["reasoning_effort"],
        allocation=controller.registry["tasks"][config["task_name"]]["allocation_by_model"][model],
        destination="REVIEW",
        max_output_tokens=2048,
        priority=Priority.NORMAL,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or preflight the governed gamebook schema-mapping review")
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "openai_gamebook_schema_mapping.json")
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--max-jobs", type=int, default=20)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    config = json.loads(args.config.resolve(strict=True).read_text(encoding="utf-8"))
    controller = AssistiveController(ROOT)
    gold_path = args.gold.resolve(strict=True)
    gold_path.relative_to(controller.store.directory("evals"))
    gold = _jsonl(gold_path)
    by_id = {row["case_id"]: row for row in gold}
    if len(by_id) != len(gold):
        raise SystemExit("duplicate gamebook schema-mapping gold case identity")

    prompt_path = ROOT / config["prompt"]["path"]
    prompt_bytes = prompt_path.read_bytes()
    if hashlib.sha256(prompt_bytes).hexdigest() != config["prompt"]["sha256"]:
        raise SystemExit("gamebook schema-mapping prompt hash mismatch")
    prompt_base = prompt_bytes.decode("utf-8")
    schema_path = ROOT / config["output_schema"]
    required_models = set(controller.registry["tasks"][config["task_name"]]["requires_representative_models"])
    actual_models = {route["model"] for route in config["routes"]}
    if not required_models <= actual_models:
        raise SystemExit(f"schema-mapping review lacks required models: {sorted(required_models - actual_models)}")

    jobs: list[tuple[dict[str, Any], dict[str, Any], AssistiveJob]] = []
    for route in config["routes"]:
        for case_id in route["case_ids"]:
            if case_id not in by_id:
                raise SystemExit(f"route references absent gold case: {case_id}")
            case = by_id[case_id]
            jobs.append((route, case, _job(controller, config, prompt_base, schema_path, route, case)))
    if len(jobs) == 0 or len(jobs) > args.max_jobs:
        raise SystemExit(f"bounded schema-mapping job count {len(jobs)} is outside 1..{args.max_jobs}")

    if args.plan_only:
        estimates: Counter[str] = Counter()
        request_ids: list[str] = []
        for route, _case, job in jobs:
            prepared = controller.prepare(job, ProcessingMode.SYNCHRONOUS)
            estimates[route["model"]] += prepared["estimate"].amount_usd
            request_ids.append(prepared["request_id"])
        manifest = controller.store.put_json(
            "evals",
            {
                "schema_version": 1,
                "artifact_type": "openai_gamebook_schema_mapping_preflight",
                "pilot_id": config["pilot_id"],
                "jira_unit": config["jira_unit"],
                "authority": config["authority"],
                "gold_sha256": hashlib.sha256(gold_path.read_bytes()).hexdigest(),
                "requested_jobs": len(jobs),
                "request_ids": sorted(request_ids),
                "estimated_cost_usd_by_model": {k: f"{v:.6f}" for k, v in sorted(estimates.items())},
                "batch_jobs": 0,
                "batch_reason": config["batch_decision"],
                "live_api_calls": 0,
                "final_disposition": "PREFLIGHT_PASS_SYNCHRONOUS_GOLD_COMPARISON_READY",
            },
        )
        print(
            json.dumps(
                {
                    "result": "PASS",
                    "requested_jobs": len(jobs),
                    "request_ids": len(request_ids),
                    "estimated_cost_usd_by_model": {k: f"{v:.6f}" for k, v in sorted(estimates.items())},
                    "manifest_path": str(manifest.path),
                    "manifest_sha256": manifest.sha256,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    costs: Counter[str] = Counter()
    cached = 0
    for route, case, job in jobs:
        try:
            result = controller.run_sync(job)
            cached += int(result.cached)
            costs[route["model"]] += Decimal(result.actual_cost_usd)
            if result.candidate is None:
                failures.append(
                    {
                        "model": route["model"],
                        "case_id": case["case_id"],
                        "error": "NO_CANDIDATE",
                        "disposition": result.disposition,
                        "validation_errors": list(result.validation_errors),
                    }
                )
                continue
            rows.append(
                {
                    "case_id": case["case_id"],
                    "model": route["model"],
                    "reasoning_effort": route["reasoning_effort"],
                    "actual_cost_usd": result.actual_cost_usd,
                    "review_time_saved_seconds": 0,
                    "request_id": result.request_id,
                    "response_sha256": result.response_sha256,
                    "cached": result.cached,
                    "disposition": result.disposition,
                    "validation_errors": list(result.validation_errors),
                    "entity_merge": result.candidate.get("entity_merge"),
                    "entity_top_k": result.candidate.get("entity_top_k", []),
                    "candidate": result.candidate,
                }
            )
        except Exception as exc:
            failures.append({"model": route["model"], "case_id": case["case_id"], "error": type(exc).__name__})
            if type(exc).__name__ in {"AuthenticationError", "BadRequestError", "PermissionDeniedError", "CredentialError"}:
                break

    prediction_payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for row in rows
    ).encode("utf-8")
    predictions = controller.store.put_bytes(
        "evals", prediction_payload, suffix=".gamebook-schema-mapping-predictions.jsonl"
    )
    evaluation_artifact = None
    evaluation_payload = None
    if rows:
        evaluation_schema = json.loads(schema_path.read_text(encoding="utf-8"))
        models_with_rows = sorted({row["model"] for row in rows})
        evaluation_payload = {
            "schema_version": 1,
            "artifact_type": "openai_gamebook_schema_mapping_evaluation",
            "pilot_id": config["pilot_id"],
            "jira_unit": config["jira_unit"],
            "authority": config["authority"],
            "gold_sha256": hashlib.sha256(gold_path.read_bytes()).hexdigest(),
            "predictions_sha256": predictions.sha256,
            "overall": evaluate(gold_path, predictions.path, evaluation_schema).as_dict(),
            "by_model": {
                model: evaluate(gold_path, predictions.path, evaluation_schema, model=model).as_dict()
                for model in models_with_rows
            },
            "acceptance": config["acceptance"],
            "canonical_or_pit_admission": False,
            "training_feature_admission": False,
            "final_disposition": "SHADOW_CANDIDATE_REVIEW_ONLY",
        }
        evaluation_artifact = controller.store.put_json("evals", evaluation_payload)
    run_manifest = controller.store.put_json(
        "evals",
        {
            "schema_version": 1,
            "artifact_type": "openai_gamebook_schema_mapping_run",
            "pilot_id": config["pilot_id"],
            "jira_unit": config["jira_unit"],
            "authority": config["authority"],
            "gold_sha256": hashlib.sha256(gold_path.read_bytes()).hexdigest(),
            "requested_jobs": len(jobs),
            "provider_calls": len(rows),
            "provider_calls_this_invocation": len(rows) + len(failures) - cached,
            "cached_results_this_invocation": cached,
            "completed_predictions": len(rows),
            "failures": failures,
            "predictions_sha256": predictions.sha256,
            "predictions_bytes": predictions.bytes,
            "evaluation_sha256": evaluation_artifact.sha256 if evaluation_artifact else None,
            "cost_usd_by_model": {k: f"{v:.6f}" for k, v in sorted(costs.items())},
            "batch_jobs": 0,
            "batch_reason": config["batch_decision"],
            "canonical_writes": 0,
            "pit_writes": 0,
            "training_feature_writes": 0,
            "protected_truth_writes": 0,
            "final_disposition": "SHADOW_CANDIDATE_REVIEW_ONLY",
        },
    )
    print(
        json.dumps(
            {
                "requested_jobs": len(jobs),
                "completed_predictions": len(rows),
                "failure_count": len(failures),
                "cached_results": cached,
                "predictions_path": str(predictions.path),
                "predictions_sha256": predictions.sha256,
                "evaluation_path": str(evaluation_artifact.path) if evaluation_artifact else None,
                "evaluation_sha256": evaluation_artifact.sha256 if evaluation_artifact else None,
                "manifest_path": str(run_manifest.path),
                "manifest_sha256": run_manifest.sha256,
                "cost_usd_by_model": {k: f"{v:.6f}" for k, v in sorted(costs.items())},
                "overall": evaluation_payload["overall"] if evaluation_payload else None,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
