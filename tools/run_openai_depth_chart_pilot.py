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
    route: dict[str, str],
    case: dict[str, Any],
) -> AssistiveJob:
    fields = [fact["field"] for fact in case["expected_facts"]]
    prompt = (
        f"{prompt_base.rstrip()}\n\n"
        f"Case instruction: {case['instruction']}\n"
        f"Case ID: {case['case_id']}\n"
        f"Extract exactly these fields: {json.dumps(fields, separators=(',', ':'))}."
    )
    max_output_tokens = min(3072, max(1536, 512 + 192 * len(fields)))
    model = route["model"]
    return AssistiveJob(
        task_name=config["task_name"],
        jira_unit=config["jira_unit"],
        source_url=f"{case['source_url']}#page={case['source_locator'].split(':', 1)[1]}&case={case['case_id']}",
        source_capture_sha256=case["source_capture_sha256"],
        source_excerpt=case["source_excerpt"],
        prompt=prompt,
        prompt_version=config["prompt"]["version"],
        schema_path=schema_path,
        schema_version="1",
        model=model,
        reasoning_effort=route["reasoning_effort"],
        allocation=controller.registry["tasks"][config["task_name"]]["allocation_by_model"][model],
        destination="CANDIDATE",
        max_output_tokens=max_output_tokens,
        priority=Priority.NORMAL,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or preflight the official A&M depth-chart shadow pilot")
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--max-jobs", type=int, default=32)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    config = json.loads((ROOT / "configs" / "openai_depth_chart_pilot.json").read_text(encoding="utf-8"))
    controller = AssistiveController(ROOT)
    gold_path = args.gold.resolve(strict=True)
    gold_path.relative_to(controller.store.directory("evals"))
    gold = _jsonl(gold_path)
    prompt_spec = config["prompt"]
    prompt_path = ROOT / prompt_spec["path"]
    prompt_bytes = prompt_path.read_bytes()
    if hashlib.sha256(prompt_bytes).hexdigest() != prompt_spec["sha256"]:
        raise SystemExit("depth-chart pilot prompt hash mismatch")
    prompt_base = prompt_bytes.decode("utf-8")
    routes = config["routes"]
    required_models = set(controller.registry["tasks"][config["task_name"]]["requires_representative_models"])
    actual_models = {route["model"] for route in routes}
    if not required_models <= actual_models:
        raise SystemExit(f"depth-chart pilot lacks required representative models: {sorted(required_models - actual_models)}")
    job_count = len(gold) * len(routes)
    if job_count == 0 or job_count > args.max_jobs:
        raise SystemExit(f"bounded depth-chart pilot job count {job_count} is outside 1..{args.max_jobs}")

    schema_path = ROOT / config["output_schema"]
    jobs = [
        (route, case, _job(controller, config, prompt_base, schema_path, route, case))
        for route in routes
        for case in gold
    ]
    if args.plan_only:
        estimated_costs: Counter[str] = Counter()
        request_ids: list[str] = []
        for route, _case, job in jobs:
            prepared = controller.prepare(job, ProcessingMode.SYNCHRONOUS)
            request_ids.append(prepared["request_id"])
            estimated_costs[route["model"]] += prepared["estimate"].amount_usd
        manifest = controller.store.put_json(
            "evals",
            {
                "schema_version": 1,
                "artifact_type": "openai_tamu_depth_chart_pilot_preflight",
                "pilot_id": config["pilot_id"],
                "jira_unit": config["jira_unit"],
                "authority": config["authority"],
                "gold_sha256": hashlib.sha256(gold_path.read_bytes()).hexdigest(),
                "requested_jobs": job_count,
                "request_ids": sorted(request_ids),
                "models": [route["model"] for route in routes],
                "reasoning_efforts": {route["model"]: route["reasoning_effort"] for route in routes},
                "estimated_cost_usd_by_model": {
                    key: f"{value:.6f}" for key, value in sorted(estimated_costs.items())
                },
                "live_api_calls": 0,
                "actual_cost_usd": "0.000000",
                "final_disposition": "PREFLIGHT_PASS_LIVE_COMPARISON_PENDING_CREDENTIAL_RESTORATION",
            },
        )
        print(
            json.dumps(
                {
                    "result": "PASS",
                    "requested_jobs": job_count,
                    "models": [route["model"] for route in routes],
                    "request_ids": len(request_ids),
                    "estimated_cost_usd_by_model": {
                        key: f"{value:.6f}" for key, value in sorted(estimated_costs.items())
                    },
                    "manifest_path": str(manifest.path),
                    "manifest_sha256": manifest.sha256,
                    "live_api_calls": 0,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    costs: Counter[str] = Counter()
    fatal_provider_error: str | None = None
    for route, case, job in jobs:
        try:
            result = controller.run_sync(job)
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
                fatal_provider_error = type(exc).__name__
                break

    prediction_payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for row in rows
    ).encode("utf-8")
    predictions = controller.store.put_bytes("evals", prediction_payload, suffix=".tamu-depth-chart-predictions.jsonl")
    evaluation_payload: dict[str, Any] | None = None
    evaluation_artifact = None
    if rows:
        evaluation_schema = json.loads(schema_path.read_text(encoding="utf-8"))
        evaluation_payload = {
            "schema_version": 1,
            "artifact_type": "openai_tamu_depth_chart_pilot_evaluation",
            "pilot_id": config["pilot_id"],
            "jira_unit": config["jira_unit"],
            "authority": config["authority"],
            "gold_sha256": hashlib.sha256(gold_path.read_bytes()).hexdigest(),
            "predictions_sha256": predictions.sha256,
            "overall": evaluate(gold_path, predictions.path, evaluation_schema).as_dict(),
            "by_model": {
                route["model"]: evaluate(
                    gold_path,
                    predictions.path,
                    evaluation_schema,
                    model=route["model"],
                ).as_dict()
                for route in routes
            },
            "acceptance": config["acceptance"],
            "final_disposition": "SHADOW_EVALUATION_ONLY",
        }
        evaluation_artifact = controller.store.put_json("evals", evaluation_payload)
    manifest = controller.store.put_json(
        "evals",
        {
            "schema_version": 1,
            "artifact_type": "openai_tamu_depth_chart_pilot_run",
            "pilot_id": config["pilot_id"],
            "jira_unit": config["jira_unit"],
            "authority": config["authority"],
            "gold_sha256": hashlib.sha256(gold_path.read_bytes()).hexdigest(),
            "requested_jobs": job_count,
            "completed_predictions": len(rows),
            "failures": failures,
            "fatal_provider_error": fatal_provider_error,
            "predictions_sha256": predictions.sha256,
            "predictions_bytes": predictions.bytes,
            "evaluation_sha256": evaluation_artifact.sha256 if evaluation_artifact else None,
            "cost_usd_by_model": {key: f"{value:.6f}" for key, value in sorted(costs.items())},
            "historical_publication_time_state": "UNKNOWN",
            "canonical_or_pit_admission": False,
            "final_disposition": "SHADOW_PILOT_ONLY",
        },
    )
    print(
        json.dumps(
            {
                "requested_jobs": job_count,
                "completed_predictions": len(rows),
                "failure_count": len(failures),
                "predictions_path": str(predictions.path),
                "predictions_sha256": predictions.sha256,
                "evaluation_path": str(evaluation_artifact.path) if evaluation_artifact else None,
                "evaluation_sha256": evaluation_artifact.sha256 if evaluation_artifact else None,
                "manifest_path": str(manifest.path),
                "manifest_sha256": manifest.sha256,
                "cost_usd_by_model": {key: f"{value:.6f}" for key, value in sorted(costs.items())},
            },
            indent=2,
            sort_keys=True,
        )
    )
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
