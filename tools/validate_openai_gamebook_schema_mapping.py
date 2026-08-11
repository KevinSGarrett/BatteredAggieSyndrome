from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.openai_assist.controller import AssistiveController  # noqa: E402
from aggie_analytics.openai_assist.evals import evaluate  # noqa: E402
from aggie_analytics.openai_assist.schemas import evidence_errors, validate_instance  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently validate the gamebook schema-mapping shadow run")
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    args = parser.parse_args()

    config = _json(ROOT / "configs" / "openai_gamebook_schema_mapping.json")
    controller = AssistiveController(ROOT)
    external_evals = controller.store.directory("evals")
    paths = {
        "gold": args.gold.resolve(strict=True),
        "predictions": args.predictions.resolve(strict=True),
        "evaluation": args.evaluation.resolve(strict=True),
        "run_manifest": args.run_manifest.resolve(strict=True),
    }
    for name, path in paths.items():
        try:
            path.relative_to(external_evals)
        except ValueError as exc:
            raise SystemExit(f"{name} must remain under the external OpenAI eval root") from exc

    prompt_path = ROOT / config["prompt"]["path"]
    if _sha(prompt_path) != config["prompt"]["sha256"]:
        raise SystemExit("prompt identity mismatch")
    schema_path = ROOT / config["output_schema"]
    schema = _json(schema_path)
    gold_rows = _jsonl(paths["gold"])
    predictions = _jsonl(paths["predictions"])
    evaluation = _json(paths["evaluation"])
    run = _json(paths["run_manifest"])
    gold = {row["case_id"]: row for row in gold_rows}
    if len(gold) != len(gold_rows):
        raise SystemExit("duplicate gold case identity")
    if run.get("gold_sha256") != _sha(paths["gold"]):
        raise SystemExit("run manifest gold binding mismatch")
    if run.get("predictions_sha256") != _sha(paths["predictions"]):
        raise SystemExit("run manifest prediction binding mismatch")
    if run.get("evaluation_sha256") != _sha(paths["evaluation"]):
        raise SystemExit("run manifest evaluation binding mismatch")
    if run.get("failures") or run.get("completed_predictions") != run.get("requested_jobs"):
        raise SystemExit("provider or controller failures remain in the run manifest")
    if any(run.get(field) != 0 for field in ["canonical_writes", "pit_writes", "training_feature_writes", "protected_truth_writes"]):
        raise SystemExit("run manifest reports a prohibited authoritative write")

    exact = 0
    mismatch_rows: list[dict[str, Any]] = []
    schema_errors: list[dict[str, Any]] = []
    authority_errors: list[dict[str, Any]] = []
    model_counts: Counter[str] = Counter()
    exact_by_model: Counter[str] = Counter()
    for row in predictions:
        case_id = row["case_id"]
        if case_id not in gold:
            raise SystemExit(f"prediction references unknown case: {case_id}")
        candidate = row["candidate"]
        errors = validate_instance(candidate, schema)
        errors.extend(evidence_errors(candidate, capture_sha256=gold[case_id]["source_capture_sha256"]))
        if errors:
            schema_errors.append({"model": row["model"], "case_id": case_id, "errors": errors})
        expected = {fact["field"]: (fact["status"], fact["value"]) for fact in gold[case_id]["expected_facts"]}
        actual = {fact["field"]: (fact["status"], fact["value"]) for fact in candidate.get("facts", [])}
        mismatches = {
            field: {"expected": list(value), "actual": list(actual[field]) if field in actual else None}
            for field, value in expected.items()
            if actual.get(field) != value
        }
        model_counts[row["model"]] += 1
        if not mismatches and not errors:
            exact += 1
            exact_by_model[row["model"]] += 1
        else:
            mismatch_rows.append({"model": row["model"], "case_id": case_id, "mismatches": mismatches})
        authority = {fact["field"]: fact["value"] for fact in candidate.get("facts", [])}
        if any(authority.get(field) is not False for field in ["canonical_authority", "pit_authority", "training_feature_authority"]):
            authority_errors.append({"model": row["model"], "case_id": case_id})

    recomputed = evaluate(paths["gold"], paths["predictions"], schema).as_dict()
    if recomputed != evaluation.get("overall"):
        raise SystemExit("evaluation report is not a byte-semantically reproducible metric computation")
    if schema_errors or authority_errors:
        raise SystemExit("schema, evidence, or authority invariant failed")
    if recomputed["strict_schema_rate"] != 1.0 or recomputed["evidence_accuracy"] != 1.0:
        raise SystemExit("strict schema or evidence accuracy invariant failed")
    if recomputed["unsupported_fact_rate"] != 0.0:
        raise SystemExit("unsupported factual output detected")

    model_decisions: dict[str, str] = {}
    for model, count in sorted(model_counts.items()):
        passed = exact_by_model[model]
        if passed == count:
            model_decisions[model] = "BOUNDED_SHADOW_EXACT_RETAIN_FOR_MORE_GOLD"
        elif model == "gpt-5-nano":
            model_decisions[model] = "REJECT_CURRENT_FORMAT_NO_BATCH"
        else:
            model_decisions[model] = "PARTIAL_HARD_CASE_REVIEW_ONLY"
    report = {
        "schema_version": 1,
        "artifact_type": "openai_gamebook_schema_mapping_independent_validation",
        "pilot_id": config["pilot_id"],
        "jira_unit": config["jira_unit"],
        "authority": config["authority"],
        "inputs": {name: {"path": str(path), "sha256": _sha(path)} for name, path in paths.items()},
        "metrics": recomputed,
        "model_runs": dict(sorted(model_counts.items())),
        "exact_runs_by_model": dict(sorted(exact_by_model.items())),
        "model_decisions": model_decisions,
        "dispositions": {
            "validated_exact_review_candidates": exact,
            "quarantined_exact_gold_mismatches": len(mismatch_rows),
            "rejected_provider_or_schema_failures": 0,
            "canonical_writes": 0,
            "pit_writes": 0,
            "training_feature_writes": 0,
            "protected_truth_writes": 0,
        },
        "mismatches": mismatch_rows,
        "batch_jobs": 0,
        "batch_decision": config["batch_decision"],
        "automatic_mapping_promotion": False,
        "historical_publication_time_state": "UNKNOWN",
        "final_disposition": "PASS_INVARIANTS_PARTIAL_EMPIRICAL_RESULT_SHADOW_REVIEW_ONLY",
    }
    artifact = controller.store.put_json("evals", report)
    print(
        json.dumps(
            {
                "status": "PASS",
                "validation_path": str(artifact.path),
                "validation_sha256": artifact.sha256,
                "validated_exact_review_candidates": exact,
                "quarantined_exact_gold_mismatches": len(mismatch_rows),
                "model_decisions": model_decisions,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
