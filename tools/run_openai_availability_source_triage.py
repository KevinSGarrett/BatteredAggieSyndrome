from __future__ import annotations

"""Run or preflight bounded candidate-only availability source triage."""

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

from aggie_analytics.openai_assist.contracts import Priority, ProcessingMode  # noqa: E402
from aggie_analytics.openai_assist.controller import AssistiveController, AssistiveJob  # noqa: E402


EXPECTED_FIELDS = [
    "source_selection_class",
    "team_scope",
    "temporal_scope",
    "availability_context",
    "subject_text",
    "historical_publication_time_utc",
]
ALLOWED_VALUES = {
    "source_selection_class": {
        "EXPLICIT_CONTEXT_SIGNAL_PAGE",
        "INJURY_MENTION_REVIEW_PAGE",
        "NO_SIGNAL_NEGATIVE_PAGE",
    },
    "team_scope": {"TAMU", "OPPONENT", "BOTH", "UNKNOWN"},
    "temporal_scope": {"CURRENT_PREGAME", "HISTORICAL_RECAP", "POSTGAME", "MIXED", "UNKNOWN"},
    "availability_context": {
        "EXPLICIT_CURRENT",
        "EXPLICIT_HISTORICAL",
        "POSTGAME_PARTICIPATION",
        "GENERIC_INJURY_MENTION",
        "NO_SIGNAL",
        "UNKNOWN",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def bound_file(data_root: Path, relative: str, expected_sha256: str) -> Path:
    path = data_root / Path(*relative.split("/"))
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise SystemExit(f"bound availability source artifact failure: {path}")
    return path


def make_job(
    controller: AssistiveController,
    config: dict[str, Any],
    prompt_base: str,
    route: dict[str, str],
    case: dict[str, Any],
) -> AssistiveJob:
    prompt = (
        f"{prompt_base.rstrip()}\n\n"
        f"Case ID: {case['case_id']}\n"
        "Classify the supplied excerpt under the six-field contract."
    )
    model = route["model"]
    return AssistiveJob(
        task_name=config["task_name"],
        jira_unit=config["jira_unit"],
        source_url=f"{case['source_url']}#page={case['page_number']}&case={case['case_id']}",
        source_capture_sha256=case["source_payload_sha256"],
        source_excerpt=case["source_excerpt"],
        prompt=prompt,
        prompt_version=config["prompt"]["version"],
        schema_path=ROOT / config["output_schema"],
        schema_version="1",
        model=model,
        reasoning_effort=route["reasoning_effort"],
        allocation=controller.registry["tasks"][config["task_name"]]["allocation_by_model"][model],
        destination="REVIEW",
        max_output_tokens=1792,
        priority=Priority.NORMAL,
    )


def validate_candidate(case: dict[str, Any], candidate: dict[str, Any] | None, controller_errors: tuple[str, ...]) -> list[str]:
    errors = list(controller_errors)
    if candidate is None:
        return [*errors, "NO_CANDIDATE"]
    if candidate.get("task_id") != "availability_source_triage":
        errors.append("task identity mismatch")
    if candidate.get("case_id") != case["case_id"]:
        errors.append("case identity mismatch")
    if candidate.get("source_capture_sha256") != case["source_payload_sha256"]:
        errors.append("source capture identity mismatch")
    if candidate.get("disposition") != "REVIEW":
        errors.append("candidate is not review-only")
    facts = candidate.get("facts") or []
    if [fact.get("field") for fact in facts] != EXPECTED_FIELDS:
        errors.append("six-field order/coverage mismatch")
    facts_by_field = {fact.get("field"): fact for fact in facts}
    if len(facts_by_field) != len(EXPECTED_FIELDS):
        errors.append("duplicate or missing fact field")
    for field, allowed in ALLOWED_VALUES.items():
        fact = facts_by_field.get(field, {})
        if fact.get("value") not in allowed:
            errors.append(f"invalid controlled value: {field}")
        if fact.get("status") != "SUPPORTED":
            errors.append(f"controlled classification is not supported: {field}")
        expected_evidence = [{
            "source_capture_sha256": case["source_payload_sha256"],
            "locator": "text:1",
            "excerpt_sha256": case["source_payload_sha256"],
        }]
        if fact.get("evidence") != expected_evidence:
            errors.append(f"evidence contract mismatch: {field}")
    selection = facts_by_field.get("source_selection_class", {})
    if selection.get("value") != case["source_selection_class"]:
        errors.append("deterministic source-selection class mismatch")
    subject = facts_by_field.get("subject_text", {})
    if subject.get("status") == "SUPPORTED":
        value = subject.get("value")
        if not isinstance(value, str) or value not in case["source_excerpt"]:
            errors.append("subject text is not an exact source substring")
        if not subject.get("evidence"):
            errors.append("supported subject lacks evidence")
    elif subject.get("status") not in {"UNKNOWN", "NOT_PRESENT", "CONFLICT"} or subject.get("value") is not None or subject.get("evidence"):
        errors.append("unsupported subject did not abstain")
    timestamp = facts_by_field.get("historical_publication_time_utc", {})
    if timestamp != {
        "field": "historical_publication_time_utc",
        "value": None,
        "status": "UNKNOWN",
        "evidence": [],
    }:
        errors.append("historical publication timestamp was not preserved UNKNOWN")
    if candidate.get("entity_top_k") != [] or candidate.get("entity_merge") is not None:
        errors.append("entity authority violation")
    if candidate.get("conflicts") != [] or candidate.get("notes") != ["PIT_TARGET_EXCLUDED"]:
        errors.append("conflict/PIT marker mismatch")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("C:/BatteredAggieSyndrome.data"))
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--max-jobs", type=int, default=64)
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    config_path = ROOT / "configs" / "openai_availability_source_triage.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source = config["source_sample"]
    sample_manifest_path = bound_file(data_root, source["manifest_relative_path"], source["manifest_sha256"])
    sample_path = bound_file(data_root, source["payload_relative_path"], source["payload_sha256"])
    validation_path = bound_file(data_root, source["validation_relative_path"], source["validation_report_sha256"])
    sample_manifest = json.loads(sample_manifest_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if sample_manifest["sample_identity"] != source["sample_identity"] or validation["status"] != "PASS":
        raise SystemExit("availability source sample is not independently admitted")
    cases = read_jsonl(sample_path)
    if len(cases) != source["sample_count"] or any(not case["openai_execution_admission"] for case in cases):
        raise SystemExit("availability source sample count/admission mismatch")

    prompt_path = ROOT / config["prompt"]["path"]
    if sha256_file(prompt_path) != config["prompt"]["sha256"]:
        raise SystemExit("availability source triage prompt hash mismatch")
    prompt_base = prompt_path.read_text(encoding="utf-8")
    controller = AssistiveController(ROOT)
    registry_task = controller.registry["tasks"][config["task_name"]]
    routes = config["routes"]
    required_models = set(registry_task["requires_representative_models"])
    actual_models = {route["model"] for route in routes}
    if not required_models <= actual_models:
        raise SystemExit(f"required representative models missing: {sorted(required_models - actual_models)}")
    jobs = [(route, case, make_job(controller, config, prompt_base, route, case)) for route in routes for case in cases]
    if not jobs or len(jobs) > args.max_jobs:
        raise SystemExit(f"bounded job count {len(jobs)} is outside 1..{args.max_jobs}")

    estimates: Counter[str] = Counter()
    request_ids: list[str] = []
    for route, _case, job in jobs:
        prepared = controller.prepare(job, ProcessingMode.SYNCHRONOUS)
        request_ids.append(prepared["request_id"])
        estimates[route["model"]] += prepared["estimate"].amount_usd
    if len(request_ids) != len(set(request_ids)):
        raise SystemExit("duplicate request identity in bounded workload")
    preflight = {
        "schema_version": 1,
        "artifact_type": "openai_tamu_availability_source_triage_preflight",
        "pilot_id": config["pilot_id"],
        "jira_unit": config["jira_unit"],
        "authority": config["authority"],
        "sample_identity": source["sample_identity"],
        "sample_manifest_sha256": source["manifest_sha256"],
        "sample_validation_report_sha256": source["validation_report_sha256"],
        "requested_jobs": len(jobs),
        "request_ids": sorted(request_ids),
        "models": [route["model"] for route in routes],
        "reasoning_efforts": {route["model"]: route["reasoning_effort"] for route in routes},
        "estimated_cost_usd_by_model": {key: f"{value:.6f}" for key, value in sorted(estimates.items())},
        "batch_jobs": 0,
        "batch_reason": config["acceptance"]["batch_scaleout"],
        "canonical_or_pit_admission": False,
    }
    preflight_artifact = controller.store.put_json("evals", preflight)
    if args.plan_only:
        print(json.dumps({**preflight, "manifest_path": str(preflight_artifact.path), "manifest_sha256": preflight_artifact.sha256}, indent=2, sort_keys=True))
        return 0

    before = controller.ledger.summary()
    predictions: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    usage_by_model: dict[str, Counter[str]] = defaultdict(Counter)
    cost_by_model: Counter[str] = Counter()
    completed_at: list[str] = []
    provider_calls_this_run = 0
    cached_results = 0
    for route, case, job in jobs:
        model = route["model"]
        try:
            result = controller.run_sync(job)
            provider_calls_this_run += int(not result.cached)
            cached_results += int(result.cached)
            cost_by_model[model] += Decimal(result.actual_cost_usd)
            cache_manifest = json.loads(controller._cache_path(result.request_id).read_text(encoding="utf-8"))
            completed_at.append(cache_manifest["completed_at"])
            for name, value in cache_manifest["usage"].items():
                usage_by_model[model][name] += int(value)
            local_errors = validate_candidate(case, result.candidate, result.validation_errors)
            local_disposition = "ACCEPTED_REVIEW_CANDIDATE" if not local_errors else "QUARANTINE"
            predictions.append({
                "case_id": case["case_id"],
                "model": model,
                "reasoning_effort": route["reasoning_effort"],
                "request_id": result.request_id,
                "response_sha256": result.response_sha256,
                "actual_cost_usd": result.actual_cost_usd,
                "cached": result.cached,
                "local_disposition": local_disposition,
                "local_validation_errors": local_errors,
                "candidate": result.candidate,
            })
        except Exception as exc:
            failures.append({
                "case_id": case["case_id"],
                "model": model,
                "reasoning_effort": route["reasoning_effort"],
                "error_type": type(exc).__name__,
                "disposition": "REJECTED_NO_CANDIDATE",
            })
            if type(exc).__name__ in {"AuthenticationError", "PermissionDeniedError", "CredentialError"}:
                break

    payload = b"".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        for row in predictions
    )
    predictions_artifact = controller.store.put_bytes("evals", payload, suffix=".availability-source-triage-predictions.jsonl")
    accepted = sum(row["local_disposition"] == "ACCEPTED_REVIEW_CANDIDATE" for row in predictions)
    quarantined = sum(row["local_disposition"] == "QUARANTINE" for row in predictions)
    by_model: dict[str, dict[str, Any]] = {}
    for route in routes:
        model = route["model"]
        rows = [row for row in predictions if row["model"] == model]
        by_model[model] = {
            "reasoning_effort": route["reasoning_effort"],
            "completed_results": len(rows),
            "accepted_review_candidates": sum(row["local_disposition"] == "ACCEPTED_REVIEW_CANDIDATE" for row in rows),
            "quarantined": sum(row["local_disposition"] == "QUARANTINE" for row in rows),
            "strict_and_local_validation_rate": (sum(not row["local_validation_errors"] for row in rows) / len(rows)) if rows else 0.0,
            "source_selection_accuracy": (sum(not any("source-selection class mismatch" in error for error in row["local_validation_errors"]) for row in rows) / len(rows)) if rows else 0.0,
            "historical_timestamp_fabrications": sum(any("timestamp" in error for error in row["local_validation_errors"]) for row in rows),
            "cost_usd": f"{cost_by_model[model]:.6f}",
            "usage": dict(sorted(usage_by_model[model].items())),
        }
    fact_values: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in predictions:
        if row["candidate"]:
            for fact in row["candidate"].get("facts", []):
                fact_values[row["case_id"]][fact.get("field", "")].add(json.dumps(fact.get("value"), sort_keys=True))
    disagreements = [
        {"case_id": case_id, "field": field, "values": sorted(values)}
        for case_id, fields in sorted(fact_values.items())
        for field, values in sorted(fields.items())
        if len(values) > 1
    ]
    after = controller.ledger.summary()
    run_manifest = {
        "schema_version": 1,
        "artifact_type": "openai_tamu_availability_source_triage_run",
        "pilot_id": config["pilot_id"],
        "jira_unit": config["jira_unit"],
        "authority": config["authority"],
        "sample_identity": source["sample_identity"],
        "requested_jobs": len(jobs),
        "provider_calls_this_run": provider_calls_this_run,
        "cached_results": cached_results,
        "completed_predictions": len(predictions),
        "failures": failures,
        "predictions_sha256": predictions_artifact.sha256,
        "predictions_bytes": predictions_artifact.bytes,
        "dispositions": {
            "accepted_review_candidate": accepted,
            "review_pending": accepted,
            "quarantine": quarantined,
            "rejected": len(failures),
            "canonical_writes": 0,
        },
        "results_by_model": by_model,
        "cross_model_disagreements": disagreements,
        "review_time_saved_seconds": 0,
        "batch_jobs": 0,
        "batch_reason": config["acceptance"]["batch_scaleout"],
        "ledger_before": before,
        "ledger_after": after,
        "last_successful_api_use_utc": max(completed_at) if completed_at else None,
        "historical_publication_time_state": "UNKNOWN",
        "canonical_or_pit_admission": False,
        "training_or_protected_use_admission": False,
        "final_disposition": "CANDIDATE_REVIEW_ONLY_CONTINUING_OPERATIONS_REMAIN_ACTIVE",
    }
    run_artifact = controller.store.put_json("evals", run_manifest)
    print(json.dumps({
        "result": "PASS" if len(predictions) == len(jobs) else "PARTIAL",
        "requested_jobs": len(jobs),
        "provider_calls_this_run": provider_calls_this_run,
        "cached_results": cached_results,
        "completed_predictions": len(predictions),
        "failures": len(failures),
        "dispositions": run_manifest["dispositions"],
        "results_by_model": by_model,
        "cumulative_spend_usd": after["settled_usd"],
        "remaining_budget_usd": after["remaining_usd"],
        "last_successful_api_use_utc": run_manifest["last_successful_api_use_utc"],
        "batch_jobs": 0,
        "batch_reason": run_manifest["batch_reason"],
        "predictions_path": str(predictions_artifact.path),
        "predictions_sha256": predictions_artifact.sha256,
        "manifest_path": str(run_artifact.path),
        "manifest_sha256": run_artifact.sha256,
    }, indent=2, sort_keys=True))
    return 0 if len(predictions) == len(jobs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
