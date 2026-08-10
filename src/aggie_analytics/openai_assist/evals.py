from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence
from typing import Any

from .schemas import evidence_errors, validate_instance


@dataclass(frozen=True)
class EvaluationReport:
    cases: int
    prediction_runs: int
    strict_schema_rate: float
    field_precision: float
    field_recall: float
    supported_facts: int
    evidence_accuracy: float | None
    abstention_facts: int
    correct_abstention_rate: float | None
    unsupported_fact_rate: float | None
    merge_decisions: int
    false_merge_rate: float | None
    entity_top_k_cases: int
    entity_top_k_recall: float | None
    repeated_run_groups: int
    repeated_run_consistency: float | None
    cross_model_groups: int
    cross_model_disagreement_rate: float | None
    total_cost_usd: float
    accepted_records: int
    cost_per_accepted_record_usd: float | None
    review_time_saved_seconds: float
    quarantine_rate: float

    def as_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, **self.__dict__}


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(
    gold_path: Path,
    predictions_path: Path | Sequence[Path],
    schema: dict[str, Any],
    *,
    model: str | None = None,
) -> EvaluationReport:
    gold_rows = _jsonl(gold_path)
    prediction_paths = [predictions_path] if isinstance(predictions_path, Path) else list(predictions_path)
    predictions = [row for path in prediction_paths for row in _jsonl(path)]
    if model is not None:
        predictions = [row for row in predictions if row.get("model") == model]
    gold = {row["case_id"]: row for row in gold_rows}
    if len(gold) != len(gold_rows):
        raise ValueError("duplicate gold case identity")
    if not predictions:
        raise ValueError("evaluation predictions are empty")

    schema_valid = quarantined = 0
    true_positive = false_positive = false_negative = 0
    evidence_correct = evidence_total = 0
    abstention_correct = abstention_total = 0
    unsupported = supported_total = 0
    false_merges = merge_decisions = 0
    top_k_hits = top_k_cases = 0
    fingerprints: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    case_fingerprints: dict[str, dict[str, str]] = defaultdict(dict)
    total_cost = 0.0
    accepted_records = 0
    review_time_saved = 0.0

    for row in predictions:
        case_id = row["case_id"]
        if case_id not in gold:
            raise ValueError(f"prediction references unknown case: {case_id}")
        case = gold[case_id]
        candidate = row["candidate"]
        errors = validate_instance(candidate, schema)
        errors.extend(evidence_errors(candidate, capture_sha256=case["source_capture_sha256"]))
        schema_valid += int(not errors)
        quarantined += int(bool(errors) or candidate.get("disposition") == "QUARANTINE")
        accepted_records += int(not errors and candidate.get("disposition") in {"CANDIDATE", "REVIEW"})
        total_cost += float(row.get("actual_cost_usd", 0.0))
        review_time_saved += float(row.get("review_time_saved_seconds", 0.0))

        expected = {item["field"]: item for item in case["expected_facts"]}
        actual = {item["field"]: item for item in candidate.get("facts", [])}
        for field, fact in actual.items():
            exp = expected.get(field)
            if exp is not None and fact.get("status") == exp["status"] and fact.get("value") == exp["value"]:
                true_positive += 1
            else:
                false_positive += 1
            if fact.get("status") == "SUPPORTED":
                supported_total += 1
                locators = {item.get("locator") for item in fact.get("evidence", [])}
                wanted = set((exp or {}).get("evidence_locators", []))
                evidence_total += 1
                evidence_correct += int(bool(wanted) and wanted <= locators)
                if exp is None or exp.get("status") != "SUPPORTED":
                    unsupported += 1
        for field, exp in expected.items():
            fact = actual.get(field)
            if fact is None or fact.get("status") != exp["status"] or fact.get("value") != exp["value"]:
                false_negative += 1

        for field, exp in expected.items():
            if exp["status"] in {"UNKNOWN", "NOT_PRESENT", "CONFLICT"}:
                abstention_total += 1
                actual_fact = actual.get(field)
                abstention_correct += int(
                    actual_fact is not None
                    and actual_fact.get("status") == exp["status"]
                    and actual_fact.get("value") is None
                )

        if case.get("entity_merge_expected") is not None:
            merge_decisions += 1
            proposed = row.get("entity_merge", False)
            false_merges += int(bool(proposed) and not bool(case["entity_merge_expected"]))
        if case.get("entity_expected_id"):
            top_k_cases += 1
            top_k_hits += int(case["entity_expected_id"] in row.get("entity_top_k", []))

        fingerprint = json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        fingerprints[(case_id, row.get("model", ""), row.get("reasoning_effort", ""))].append(fingerprint)
        case_fingerprints[case_id][row.get("model", "")] = fingerprint

    repeat_groups = [values for values in fingerprints.values() if len(values) > 1]
    repeat_consistency = (
        sum(len(set(values)) == 1 for values in repeat_groups) / len(repeat_groups)
        if repeat_groups
        else None
    )
    disagreement_groups = [values for values in case_fingerprints.values() if len(values) > 1]
    disagreement_rate = (
        sum(len(set(values.values())) > 1 for values in disagreement_groups) / len(disagreement_groups)
        if disagreement_groups
        else None
    )
    return EvaluationReport(
        cases=len(gold),
        prediction_runs=len(predictions),
        strict_schema_rate=schema_valid / len(predictions),
        field_precision=true_positive / max(1, true_positive + false_positive),
        field_recall=true_positive / max(1, true_positive + false_negative),
        supported_facts=supported_total,
        evidence_accuracy=(evidence_correct / evidence_total if evidence_total else None),
        abstention_facts=abstention_total,
        correct_abstention_rate=(abstention_correct / abstention_total if abstention_total else None),
        unsupported_fact_rate=(unsupported / supported_total if supported_total else None),
        merge_decisions=merge_decisions,
        false_merge_rate=(false_merges / merge_decisions if merge_decisions else None),
        entity_top_k_cases=top_k_cases,
        entity_top_k_recall=(top_k_hits / top_k_cases if top_k_cases else None),
        repeated_run_groups=len(repeat_groups),
        repeated_run_consistency=repeat_consistency,
        cross_model_groups=len(disagreement_groups),
        cross_model_disagreement_rate=disagreement_rate,
        total_cost_usd=total_cost,
        accepted_records=accepted_records,
        cost_per_accepted_record_usd=(total_cost / accepted_records if accepted_records else None),
        review_time_saved_seconds=review_time_saved,
        quarantine_rate=quarantined / len(predictions),
    )
