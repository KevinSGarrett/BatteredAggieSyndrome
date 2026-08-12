from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "artifacts/assistive/local_qwen_qualification.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    findings: list[str] = []
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    contract = summary["acceptance_contract"]
    runs = summary["runs"]
    if summary.get("qualification_disposition") != "EMPIRICALLY_REJECTED_NO_OPERATIONAL_ROUTE":
        findings.append("QUALIFICATION_DISPOSITION_DRIFT")
    if summary["acceptance_decision"].get("operational_route_ready") is not False:
        findings.append("FAILED_ROUTE_PROMOTED")
    if summary["acceptance_decision"].get("admitted_models") != []:
        findings.append("ADMITTED_MODEL_PRESENT")
    if len(runs) != 3:
        findings.append("RUN_COUNT_INVALID")

    calls = packets = prompt_tokens = output_tokens = canonical = protected = 0
    models: set[str] = set()
    for run in runs:
        path = Path(run["evaluation_path"])
        expected_hash = run["evaluation_sha256"]
        if not path.is_file():
            findings.append(f"EVALUATION_MISSING:{expected_hash}")
            continue
        if sha256(path) != expected_hash or path.stem != expected_hash:
            findings.append(f"EVALUATION_IDENTITY_INVALID:{expected_hash}")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        metrics = payload["metrics"]
        models.add(payload["model"])
        if payload["qualification_id"] != run["qualification_id"]:
            findings.append(f"QUALIFICATION_ID_MISMATCH:{expected_hash}")
        if payload["model_digest"] != run["model_digest"]:
            findings.append(f"MODEL_DIGEST_MISMATCH:{expected_hash}")
        for key, expected in run["metrics"].items():
            if metrics.get(key) != expected:
                findings.append(f"METRIC_MISMATCH:{expected_hash}:{key}")
        if metrics["unique_packets"] < contract["packets_min"]:
            findings.append(f"PACKET_MINIMUM_MISSED:{expected_hash}")
        if metrics["task_types"] < contract["task_types_min"]:
            findings.append(f"TASK_TYPE_MINIMUM_MISSED:{expected_hash}")
        passed = (
            metrics["strict_schema_rate"] >= contract["strict_schema_rate_min"]
            and metrics["evidence_accuracy"] >= contract["evidence_accuracy_min"]
            and metrics["expected_term_recall"] >= contract["expected_term_recall_min"]
            and metrics["unsupported_fact_rate"] <= contract["unsupported_fact_rate_max"]
        )
        if passed or payload.get("qualification_disposition") != "FAIL_PRESERVE_NEGATIVE_EVIDENCE":
            findings.append(f"NEGATIVE_DECISION_NOT_SUPPORTED:{expected_hash}")
        if not metrics.get("unload_succeeded"):
            findings.append(f"MODEL_NOT_UNLOADED:{expected_hash}")
        calls += metrics["provider_calls"]
        packets += metrics["unique_packets"]
        prompt_tokens += metrics["prompt_tokens"]
        output_tokens += metrics["output_tokens"]
        canonical += metrics["canonical_writes"]
        protected += metrics["protected_decisions"]

    aggregate = summary["aggregate"]
    expected_aggregate = {
        "provider_calls": calls,
        "unique_packet_executions": packets,
        "models_evaluated": len(models),
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "canonical_writes": canonical,
        "protected_decisions": protected,
    }
    for key, expected in expected_aggregate.items():
        if aggregate.get(key) != expected:
            findings.append(f"AGGREGATE_MISMATCH:{key}")
    if canonical or protected:
        findings.append("AUTHORITY_BOUNDARY_VIOLATION")
    if findings:
        print(json.dumps({"status": "FAIL", "findings": findings}, indent=2))
        return 1
    print(json.dumps({
        "status": "PASS",
        "runs": len(runs),
        "provider_calls": calls,
        "unique_packet_executions": packets,
        "task_types": 3,
        "models_evaluated": len(models),
        "operational_route_ready": False,
        "canonical_writes": canonical,
        "protected_decisions": protected,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
