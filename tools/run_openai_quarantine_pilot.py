from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.openai_assist.contracts import Priority  # noqa: E402
from aggie_analytics.openai_assist.controller import AssistiveController, AssistiveJob  # noqa: E402
from aggie_analytics.openai_assist.schemas import evidence_errors, validate_instance  # noqa: E402


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _request_manifest(controller: AssistiveController, request_id: str) -> dict[str, Any]:
    path = controller.store.directory("manifests") / "requests" / f"{request_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_fingerprint(candidate: dict[str, Any]) -> str:
    facts = [
        {"field": fact.get("field"), "value": fact.get("value"), "status": fact.get("status")}
        for fact in candidate.get("facts", [])
    ]
    return json.dumps(facts, sort_keys=True, separators=(",", ":"))


def _metrics(
    gold: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
    schema: dict[str, Any],
) -> dict[str, Any]:
    exact = schema_valid = evidence_correct = evidence_total = unsupported = supported = 0
    route_correct = authority_none = quarantine_preserved = 0
    by_model: dict[str, dict[str, int]] = defaultdict(lambda: {"runs": 0, "exact": 0})
    overlap: dict[str, set[str]] = defaultdict(set)
    total_cost = Decimal("0")
    for row in rows:
        case = gold[row["case_id"]]
        candidate = row["candidate"]
        errors = validate_instance(candidate, schema)
        errors.extend(evidence_errors(candidate, capture_sha256=case["source_capture_sha256"]))
        schema_valid += int(not errors)
        expected = {fact["field"]: fact for fact in case["expected_facts"]}
        actual = {fact.get("field"): fact for fact in candidate.get("facts", [])}
        is_exact = list(actual) == list(expected)
        for field, expected_fact in expected.items():
            actual_fact = actual.get(field, {})
            fact_exact = (
                actual_fact.get("value") == expected_fact["value"]
                and actual_fact.get("status") == expected_fact["status"]
            )
            is_exact = is_exact and fact_exact
            if actual_fact.get("status") == "SUPPORTED":
                supported += 1
                evidence_total += 1
                evidence_correct += int(actual_fact.get("evidence") == expected_fact["expected_evidence"])
                unsupported += int(not fact_exact)
        exact += int(is_exact and not errors)
        route_correct += int(
            actual.get("remediation_route", {}).get("value")
            == expected["remediation_route"]["value"]
        )
        authority_none += int(actual.get("canonical_authority", {}).get("value") == "NONE")
        quarantine_preserved += int(candidate.get("disposition") == "QUARANTINE")
        by_model[row["model"]]["runs"] += 1
        by_model[row["model"]]["exact"] += int(is_exact and not errors)
        overlap[row["case_id"]].add(_candidate_fingerprint(candidate))
        total_cost += Decimal(row["actual_cost_usd"])
    run_count = len(rows)
    accepted = exact
    case_counts = Counter(row["case_id"] for row in rows)
    comparison_groups = [
        values for case_id, values in overlap.items() if case_counts[case_id] > 1
    ]
    disagreement = sum(len(values) > 1 for values in comparison_groups)
    return {
        "prediction_runs": run_count,
        "strict_schema_rate": schema_valid / run_count if run_count else 0.0,
        "exact_classification_rate": exact / run_count if run_count else 0.0,
        "evidence_accuracy": evidence_correct / evidence_total if evidence_total else None,
        "unsupported_fact_rate": unsupported / supported if supported else None,
        "deterministic_route_accuracy": route_correct / run_count if run_count else 0.0,
        "canonical_authority_none_rate": authority_none / run_count if run_count else 0.0,
        "quarantine_preservation_rate": quarantine_preserved / run_count if run_count else 0.0,
        "accepted_classifications": accepted,
        "quarantined_source_records_released": 0,
        "canonical_writes": 0,
        "protected_truth_writes": 0,
        "comparison_groups": len(comparison_groups),
        "cross_model_disagreement_rate": disagreement / len(comparison_groups) if comparison_groups else None,
        "total_cost_usd": f"{total_cost:.6f}",
        "cost_per_accepted_classification_usd": f"{total_cost / accepted:.6f}" if accepted else None,
        "review_time_saved_seconds": None,
        "review_savings_measured": False,
        "by_model": {
            model: {
                **counts,
                "exact_classification_rate": counts["exact"] / counts["runs"] if counts["runs"] else 0.0,
            }
            for model, counts in sorted(by_model.items())
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run governed shadow quarantine/schema classification Pilot C")
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--max-jobs", type=int, default=16)
    args = parser.parse_args()

    config = json.loads((ROOT / "configs" / "openai_quarantine_schema_pilot.json").read_text(encoding="utf-8"))
    controller = AssistiveController(ROOT)
    gold_path = args.gold.resolve(strict=True)
    gold_path.relative_to(controller.store.directory("evals"))
    gold_rows = _jsonl(gold_path)
    gold = {row["case_id"]: row for row in gold_rows}
    if len(gold) != len(gold_rows):
        raise SystemExit("duplicate Pilot C case identity")
    expected_cases = {case["case_id"] for case in config["cases"]}
    if set(gold) != expected_cases:
        raise SystemExit("Pilot C gold cases disagree with the governed config")
    prompt_spec = config["prompt"]
    prompt_path = ROOT / prompt_spec["path"]
    prompt_bytes = prompt_path.read_bytes()
    if hashlib.sha256(prompt_bytes).hexdigest() != prompt_spec["sha256"]:
        raise SystemExit("Pilot C prompt hash mismatch")
    prompt_base = prompt_bytes.decode("utf-8").rstrip()
    scheduled = [(route, case_id) for route in config["routes"] for case_id in route["case_ids"]]
    if len(scheduled) == 0 or len(scheduled) > args.max_jobs:
        raise SystemExit(f"bounded Pilot C job count {len(scheduled)} is outside 1..{args.max_jobs}")

    schema_path = ROOT / config["output_schema"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    tokens: Counter[str] = Counter()
    costs: Counter[str] = Counter()
    for route, case_id in scheduled:
        case = gold[case_id]
        fields = [fact["field"] for fact in case["expected_facts"]]
        prompt = (
            f"{prompt_base}\n\nCase instruction: copy case_id {case_id}. "
            f"Return exactly these facts in order: {json.dumps(fields, separators=(',', ':'))}."
        )
        model = route["model"]
        job = AssistiveJob(
            task_name=config["task_name"],
            jira_unit=config["jira_unit"],
            source_url=case["source_url"],
            source_capture_sha256=case["source_capture_sha256"],
            source_excerpt=case["source_excerpt"],
            prompt=prompt,
            prompt_version=prompt_spec["version"],
            schema_path=schema_path,
            schema_version="1",
            model=model,
            reasoning_effort=route["reasoning_effort"],
            allocation=controller.registry["tasks"][config["task_name"]]["allocation_by_model"][model],
            destination="QUARANTINE",
            max_output_tokens=1280,
            priority=Priority.NORMAL,
        )
        try:
            result = controller.run_sync(job)
            manifest = _request_manifest(controller, result.request_id)
            usage = manifest["usage"]
            for key in ["input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens"]:
                tokens[f"{model}:{key}"] += int(usage[key])
            costs[model] += Decimal(result.actual_cost_usd)
            if result.candidate is None:
                failures.append({"model": model, "case_id": case_id, "error": "NO_CANDIDATE"})
                continue
            rows.append(
                {
                    "case_id": case_id,
                    "model": model,
                    "reasoning_effort": route["reasoning_effort"],
                    "role": route["role"],
                    "actual_cost_usd": result.actual_cost_usd,
                    "disposition": result.disposition,
                    "validation_errors": list(result.validation_errors),
                    "candidate": result.candidate,
                }
            )
        except Exception as exc:
            failures.append({"model": model, "case_id": case_id, "error": type(exc).__name__})

    payload = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows).encode("utf-8")
    predictions = controller.store.put_bytes("evals", payload, suffix=".quarantine-schema-predictions.jsonl")
    metrics = _metrics(gold, rows, schema) if rows else {}
    acceptance = config["predeclared_acceptance"]
    acceptance_pass = not failures and all(metrics.get(key) == value for key, value in acceptance.items())
    manifest = controller.store.put_json(
        "evals",
        {
            "schema_version": 1,
            "artifact_type": "openai_quarantine_schema_pilot_run",
            "pilot_id": config["pilot_id"],
            "jira_unit": config["jira_unit"],
            "authority": config["authority"],
            "prompt_version": prompt_spec["version"],
            "prompt_sha256": prompt_spec["sha256"],
            "gold_sha256": hashlib.sha256(gold_path.read_bytes()).hexdigest(),
            "case_count": len(gold),
            "requested_jobs": len(scheduled),
            "completed_predictions": len(rows),
            "failures": failures,
            "models": {route["model"]: {"reasoning_effort": route["reasoning_effort"], "role": route["role"], "case_count": len(route["case_ids"])} for route in config["routes"]},
            "predictions_sha256": predictions.sha256,
            "predictions_bytes": predictions.bytes,
            "cost_usd_by_model": {key: f"{value:.6f}" for key, value in sorted(costs.items())},
            "tokens_by_model": dict(sorted(tokens.items())),
            "metrics": metrics,
            "predeclared_acceptance": acceptance,
            "acceptance_pass": acceptance_pass,
            "budget_after_run": controller.ledger.summary(),
            "final_disposition": "SHADOW_QUARANTINE_CLASSIFICATION_ONLY",
            "reserve_release_eligible": False,
        },
    )
    print(json.dumps({"requested_jobs": len(scheduled), "completed_predictions": len(rows), "failure_count": len(failures), "acceptance_pass": acceptance_pass, "predictions_path": str(predictions.path), "predictions_sha256": predictions.sha256, "manifest_path": str(manifest.path), "manifest_sha256": manifest.sha256, "cost_usd_by_model": {key: f"{value:.6f}" for key, value in sorted(costs.items())}, "metrics": metrics, "budget_after_run": controller.ledger.summary()}, indent=2, sort_keys=True))
    return int(bool(failures) or not acceptance_pass)


if __name__ == "__main__":
    raise SystemExit(main())
