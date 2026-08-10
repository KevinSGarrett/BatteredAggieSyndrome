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

from aggie_analytics.openai_assist.controller import AssistiveController, AssistiveJob  # noqa: E402
from aggie_analytics.openai_assist.contracts import Priority  # noqa: E402


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _case_prompt(base: str, case: dict[str, Any]) -> str:
    fields = [item["field"] for item in case["expected_facts"]]
    return (
        f"{base.rstrip()}\n\n"
        f"Evaluation case_id: {case['case_id']}. Extract exactly these requested fields: "
        f"{json.dumps(fields, separators=(',', ':'))}. Do not copy or infer expected answers; "
        "apply only the contractual semantics above to the supplied source excerpt."
    )


def _request_manifest(controller: AssistiveController, request_id: str) -> dict[str, Any]:
    path = controller.store.directory("manifests") / "requests" / f"{request_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the governed, shadow-only OpenAI model corpus")
    parser.add_argument("--model", action="append", dest="models")
    parser.add_argument("--case", action="append", dest="cases")
    parser.add_argument("--run-label", default="primary")
    parser.add_argument("--max-jobs", type=int, default=24)
    args = parser.parse_args()

    policy = json.loads((ROOT / "configs" / "openai_evaluation_policy.json").read_text(encoding="utf-8"))
    prompt_spec = policy["prompt"]
    prompt_path = ROOT / prompt_spec["path"]
    prompt_bytes = prompt_path.read_bytes()
    if hashlib.sha256(prompt_bytes).hexdigest() != prompt_spec["sha256"]:
        raise SystemExit("evaluation prompt hash does not match policy")
    base_prompt = prompt_bytes.decode("utf-8")
    gold_path = ROOT / policy["gold_corpus"]
    if hashlib.sha256(gold_path.read_bytes()).hexdigest() != policy["gold_corpus_sha256"]:
        raise SystemExit("evaluation gold-corpus hash does not match policy")
    gold = _jsonl(gold_path)
    selected_cases = set(args.cases or [case["case_id"] for case in gold])
    unknown_cases = selected_cases - {case["case_id"] for case in gold}
    if unknown_cases:
        raise SystemExit(f"unknown evaluation cases: {sorted(unknown_cases)}")
    gold = [case for case in gold if case["case_id"] in selected_cases]

    routes = [*policy["comparison_routes"], policy["reference_route"]]
    if args.models:
        selected_models = set(args.models)
        unknown_models = selected_models - {route["model"] for route in routes}
        if unknown_models:
            raise SystemExit(f"models are not registered evaluation routes: {sorted(unknown_models)}")
        routes = [route for route in routes if route["model"] in selected_models]
    job_count = len(gold) * len(routes)
    if job_count == 0 or job_count > args.max_jobs:
        raise SystemExit(f"bounded job count {job_count} is outside 1..{args.max_jobs}")

    controller = AssistiveController(ROOT)
    schema_path = ROOT / policy["output_schema"]
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    fatal_provider_error: str | None = None
    token_totals: Counter[str] = Counter()
    cost_totals: Counter[str] = Counter()
    for route in routes:
        model = route["model"]
        effort = route["reasoning_effort"]
        for case in gold:
            excerpt = case["source_excerpt"]
            capture_sha256 = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
            if capture_sha256 != case["source_capture_sha256"]:
                raise SystemExit(f"gold capture identity mismatch: {case['case_id']}")
            job = AssistiveJob(
                task_name="assistive_model_evaluation",
                jira_unit="POST-SUBTASK-161",
                source_url=f"file:{policy['gold_corpus']}#{case['case_id']}",
                source_capture_sha256=capture_sha256,
                source_excerpt=excerpt,
                prompt=_case_prompt(base_prompt, case),
                prompt_version=f"{prompt_spec['version']}-{args.run_label}",
                schema_path=schema_path,
                schema_version="1",
                model=model,
                reasoning_effort=effort,
                allocation="PROBE_PROMPT_EVAL",
                destination="CANDIDATE",
                max_output_tokens=1024,
                priority=Priority.NORMAL,
            )
            try:
                result = controller.run_sync(job)
                manifest = _request_manifest(controller, result.request_id)
                usage = manifest["usage"]
                for key in ["input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens"]:
                    token_totals[f"{model}:{key}"] += int(usage[key])
                cost_totals[model] += Decimal(result.actual_cost_usd)
                candidate = result.candidate
                if candidate is None:
                    failures.append({"model": model, "case_id": case["case_id"], "error": "NO_CANDIDATE"})
                    continue
                rows.append(
                    {
                        "case_id": case["case_id"],
                        "model": model,
                        "reasoning_effort": effort,
                        "actual_cost_usd": result.actual_cost_usd,
                        "review_time_saved_seconds": 0,
                        "disposition": result.disposition,
                        "validation_errors": list(result.validation_errors),
                        "entity_merge": candidate.get("entity_merge"),
                        "entity_top_k": candidate.get("entity_top_k", []),
                        "candidate": candidate,
                    }
                )
            except Exception as exc:  # preserve a bounded failure and continue independent routes
                failures.append(
                    {"model": model, "case_id": case["case_id"], "error": type(exc).__name__}
                )
                if type(exc).__name__ in {"AuthenticationError", "BadRequestError", "PermissionDeniedError"}:
                    fatal_provider_error = type(exc).__name__
                    break
        if fatal_provider_error is not None:
            break

    payload = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows).encode("utf-8")
    predictions = controller.store.put_bytes("evals", payload, suffix=".predictions.jsonl")
    manifest = controller.store.put_json(
        "evals",
        {
            "schema_version": 1,
            "artifact_type": "openai_assist_model_evaluation_run",
            "policy_id": policy["policy_id"],
            "prompt_version": f"{prompt_spec['version']}-{args.run_label}",
            "prompt_sha256": prompt_spec["sha256"],
            "gold_corpus_version": policy["gold_corpus_version"],
            "gold_corpus_sha256": policy["gold_corpus_sha256"],
            "jira_unit": "POST-SUBTASK-161",
            "authority": policy["authority"],
            "requested_jobs": job_count,
            "completed_predictions": len(rows),
            "failures": failures,
            "fatal_provider_error": fatal_provider_error,
            "models": [route["model"] for route in routes],
            "reasoning_efforts": {route["model"]: route["reasoning_effort"] for route in routes},
            "cases": [case["case_id"] for case in gold],
            "predictions_sha256": predictions.sha256,
            "predictions_bytes": predictions.bytes,
            "cost_usd_by_model": {key: f"{value:.6f}" for key, value in sorted(cost_totals.items())},
            "tokens_by_model": {
                key: value for key, value in sorted(token_totals.items())
            },
            "final_disposition": "SHADOW_EVALUATION_ONLY",
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
                "manifest_path": str(manifest.path),
                "manifest_sha256": manifest.sha256,
                "cost_usd_by_model": {key: f"{value:.6f}" for key, value in sorted(cost_totals.items())},
            },
            indent=2,
            sort_keys=True,
        )
    )
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
