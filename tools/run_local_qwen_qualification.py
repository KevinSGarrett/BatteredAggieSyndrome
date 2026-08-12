from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json
from aggie_analytics.assistive_plane.contracts import sha256_value
from aggie_analytics.assistive_plane.redaction import contains_secret
from aggie_analytics.assistive_plane.schemas import validate_output, validate_strict_schema


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_source(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def json_value(payload: Any, dotted: str) -> Any:
    value = payload
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            raise RuntimeError(f"JSON_SELECTOR_MISSING:{dotted}")
        value = value[part]
    return value


def extract(packet: dict[str, Any], source: Path) -> str:
    if packet.get("json_fields"):
        payload = json.loads(source.read_text(encoding="utf-8"))
        selected = {field: json_value(payload, field) for field in packet["json_fields"]}
        return json.dumps(selected, indent=2, sort_keys=True, ensure_ascii=False)
    text = source.read_text(encoding="utf-8")
    start = text.find(packet["start_marker"])
    if start < 0:
        raise RuntimeError(f"START_MARKER_MISSING:{packet['task_id']}")
    end = text.find(packet["end_marker"], start + len(packet["start_marker"]))
    if end < 0:
        raise RuntimeError(f"END_MARKER_MISSING:{packet['task_id']}")
    return text[start:end].strip()


def request_json(url: str, payload: dict[str, Any] | None, attempts: int = 2) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError):
            if attempt == attempts:
                raise
            time.sleep(0.25 * attempt)
    raise RuntimeError("OLLAMA_RESPONSE_ABSENT")


def build_prompt(packet: dict[str, Any], excerpt: str, source_hash: str) -> str:
    return (
        "Produce one bounded project-assistance candidate. Use only the evidence below. "
        "Do not infer absent facts. Every finding must quote one exact complete numbered evidence line, "
        "including its Lxxx prefix and all punctuation, "
        "and must use the supplied source SHA-256 exactly. If the evidence is insufficient, use UNKNOWN. "
        "When the requested value is explicitly present, report it as CANDIDATE rather than UNKNOWN. "
        "Include requested symbolic identifiers and field names verbatim when present. "
        "The unsupported_facts array is only for claims in your own response that are not supported by evidence; "
        "do not put evidence limitations, missing fields, caveats, or recommended follow-up in unsupported_facts. "
        "Use summary or recommended_checks for limitations. "
        "Return only JSON matching the supplied schema.\n\n"
        f"TASK_ID: {packet['task_id']}\n"
        f"TASK_TYPE: {packet['task_type']}\n"
        f"INSTRUCTION: {packet['instruction']}\n"
        f"SOURCE_SHA256: {source_hash}\n"
        f"EVIDENCE:\n{excerpt}"
    )


def evaluate(packet: dict[str, Any], output: dict[str, Any], excerpt: str, source_hash: str) -> dict[str, Any]:
    combined = json.dumps(output, sort_keys=True, ensure_ascii=False).lower()
    expected = packet["expected_terms"]
    recalled = sum(1 for term in expected if term.lower() in combined)
    findings = output.get("findings", [])
    valid_findings = sum(
        1
        for finding in findings
        if finding.get("source_sha256") == source_hash
        and bool(finding.get("evidence_quote"))
        and finding.get("evidence_quote") in excerpt
    )
    invalid_findings = len(findings) - valid_findings
    unsupported = list(output.get("unsupported_facts", []))
    task_identity_valid = output.get("task_id") == packet["task_id"] and output.get("task_type") == packet["task_type"]
    expected_recall = recalled / len(expected) if expected else 1.0
    evidence_accuracy = valid_findings / len(findings) if findings else 0.0
    if not task_identity_valid or invalid_findings or unsupported:
        disposition = "QUARANTINE"
    elif expected_recall < 1.0 or not findings:
        disposition = "REVIEW"
    else:
        disposition = "ACCEPTED_CANDIDATE"
    return {
        "task_id": packet["task_id"],
        "task_type": packet["task_type"],
        "task_identity_valid": task_identity_valid,
        "expected_terms": expected,
        "expected_terms_recalled": recalled,
        "expected_term_recall": expected_recall,
        "finding_count": len(findings),
        "valid_evidence_findings": valid_findings,
        "invalid_evidence_findings": invalid_findings,
        "evidence_accuracy": evidence_accuracy,
        "unsupported_fact_count": len(unsupported) + invalid_findings,
        "disposition": disposition,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/local_qwen_qualification.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    schema_path = ROOT / config["schema_path"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate_strict_schema(schema)
    storage = Path(config["storage_root"])
    for category in ["requests", "responses", "manifests", "evals", "quarantine", "usage", "runtime", "tmp"]:
        (storage / category).mkdir(parents=True, exist_ok=True)
    tags = request_json(f"{config['endpoint']}/api/tags", None)
    models = [item for item in tags.get("models", []) if item.get("name") == config["model"] or item.get("model") == config["model"]]
    if len(models) != 1:
        raise RuntimeError("LOCAL_QWEN_MODEL_NOT_UNIQUE")
    digest = str(models[0].get("digest", ""))
    if not digest.startswith(config["expected_digest_prefix"]):
        raise RuntimeError("LOCAL_QWEN_MODEL_DIGEST_MISMATCH")
    schema_hash = sha256(schema_path)
    results: list[dict[str, Any]] = []
    response_hashes_by_task: dict[str, list[str]] = {}
    packets = list(config["packets"])
    executions = packets + [packets[0], packets[-1]]
    unload_succeeded = False
    try:
        for sequence, packet in enumerate(executions, start=1):
            source = resolve_source(packet["source_path"])
            source_hash = sha256(source)
            excerpt = extract(packet, source)
            excerpt = "\n".join(f"L{index:03d}: {line}" for index, line in enumerate(excerpt.splitlines(), start=1))
            prompt = build_prompt(packet, excerpt, source_hash)
            if contains_secret(prompt):
                raise RuntimeError(f"SECRET_DETECTED:{packet['task_id']}")
            request_payload = {
                "model": config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": schema,
                "options": {"temperature": 0, "num_ctx": config["context_tokens"], "num_predict": 600},
                "keep_alive": "5m",
            }
            request_record = {
                "schema_version": 1,
                "qualification_id": config["qualification_id"],
                "jira_unit": config["jira_unit"],
                "sequence": sequence,
                "task_id": packet["task_id"],
                "task_type": packet["task_type"],
                "source_path": str(source),
                "source_sha256": source_hash,
                "schema_sha256": schema_hash,
                "model": config["model"],
                "model_digest": digest,
                "context_tokens": config["context_tokens"],
                "prompt": prompt,
                "canonical_or_protected_authority": False,
            }
            _, request_hash = write_content_addressed_json(storage, "requests", request_record)
            started = time.perf_counter()
            response = request_json(f"{config['endpoint']}/api/chat", request_payload)
            elapsed = time.perf_counter() - started
            raw_content = response.get("message", {}).get("content", "")
            strict_valid = True
            strict_error = ""
            output: dict[str, Any] = {}
            try:
                output = json.loads(raw_content)
                validate_output(output, schema)
            except (json.JSONDecodeError, ValueError) as exc:
                strict_valid = False
                strict_error = str(exc)
            evaluation = (
                evaluate(packet, output, excerpt, source_hash)
                if strict_valid
                else {
                    "task_id": packet["task_id"],
                    "task_type": packet["task_type"],
                    "task_identity_valid": False,
                    "expected_terms": packet["expected_terms"],
                    "expected_terms_recalled": 0,
                    "expected_term_recall": 0.0,
                    "finding_count": 0,
                    "valid_evidence_findings": 0,
                    "invalid_evidence_findings": 0,
                    "evidence_accuracy": 0.0,
                    "unsupported_fact_count": 0,
                    "disposition": "QUARANTINE",
                }
            )
            response_record = {
                "schema_version": 1,
                "request_sha256": request_hash,
                "task_id": packet["task_id"],
                "model": response.get("model"),
                "model_digest": digest,
                "output": output if strict_valid else None,
                "output_sha256": sha256_value(output) if strict_valid else None,
                "raw_content": raw_content,
                "strict_schema_valid": strict_valid,
                "strict_schema_error": strict_error,
                "usage": {
                    "prompt_eval_count": response.get("prompt_eval_count"),
                    "eval_count": response.get("eval_count"),
                    "total_duration_ns": response.get("total_duration"),
                    "load_duration_ns": response.get("load_duration"),
                    "wall_seconds": round(elapsed, 6),
                },
                "evaluation": evaluation,
            }
            category = "responses" if evaluation["disposition"] != "QUARANTINE" else "quarantine"
            _, response_hash = write_content_addressed_json(storage, category, response_record)
            response_hashes_by_task.setdefault(packet["task_id"], []).append(
                response_record["output_sha256"] or response_hash
            )
            results.append({
                **evaluation,
                "strict_schema_valid": strict_valid,
                "request_sha256": request_hash,
                "response_sha256": response_hash,
                "usage": response_record["usage"],
            })
    finally:
        try:
            request_json(f"{config['endpoint']}/api/generate", {"model": config["model"], "prompt": "", "stream": False, "keep_alive": 0})
            unload_succeeded = True
        except Exception:
            unload_succeeded = False
    unique = results[: len(packets)]
    strict_rate = sum(item["strict_schema_valid"] for item in unique) / len(unique)
    finding_total = sum(item["finding_count"] for item in unique)
    valid_total = sum(item["valid_evidence_findings"] for item in unique)
    unsupported_total = sum(item["unsupported_fact_count"] for item in unique)
    expected_total = sum(len(item["expected_terms"]) for item in unique)
    expected_recalled = sum(item["expected_terms_recalled"] for item in unique)
    repeated = [hashes for hashes in response_hashes_by_task.values() if len(hashes) > 1]
    repeat_exact_rate = sum(1 for hashes in repeated if len(set(hashes)) == 1) / len(repeated) if repeated else 0.0
    dispositions: dict[str, int] = {}
    for item in unique:
        dispositions[item["disposition"]] = dispositions.get(item["disposition"], 0) + 1
    metrics = {
        "unique_packets": len(unique),
        "provider_calls": len(results),
        "task_types": len({item["task_type"] for item in unique}),
        "strict_schema_rate": strict_rate,
        "evidence_accuracy": valid_total / finding_total if finding_total else 0.0,
        "expected_term_recall": expected_recalled / expected_total if expected_total else 1.0,
        "unsupported_fact_rate": unsupported_total / finding_total if finding_total else 0.0,
        "repeat_exact_response_rate": repeat_exact_rate,
        "dispositions": dict(sorted(dispositions.items())),
        "prompt_tokens": sum((item["usage"].get("prompt_eval_count") or 0) for item in results),
        "output_tokens": sum((item["usage"].get("eval_count") or 0) for item in results),
        "wall_seconds": round(sum(item["usage"]["wall_seconds"] for item in results), 6),
        "unload_succeeded": unload_succeeded,
        "canonical_writes": 0,
        "protected_decisions": 0,
    }
    acceptance = config["acceptance"]
    passed = (
        metrics["unique_packets"] >= acceptance["packets_min"]
        and metrics["task_types"] >= acceptance["task_types_min"]
        and metrics["strict_schema_rate"] >= acceptance["strict_schema_rate_min"]
        and metrics["evidence_accuracy"] >= acceptance["evidence_accuracy_min"]
        and metrics["expected_term_recall"] >= acceptance["expected_term_recall_min"]
        and metrics["unsupported_fact_rate"] <= acceptance["unsupported_fact_rate_max"]
        and unload_succeeded
    )
    evaluation_record = {
        "schema_version": 1,
        "qualification_id": config["qualification_id"],
        "jira_unit": config["jira_unit"],
        "authority": config["authority"],
        "config_sha256": sha256(args.config),
        "schema_sha256": schema_hash,
        "model": config["model"],
        "model_digest": digest,
        "runtime": {"endpoint": "LOOPBACK", "context_tokens": config["context_tokens"], "parallel_requests": 1, "max_loaded_models": 1},
        "metrics": metrics,
        "acceptance": acceptance,
        "qualification_disposition": "PASS" if passed else "FAIL_PRESERVE_NEGATIVE_EVIDENCE",
        "results": unique,
    }
    path, digest_out = write_content_addressed_json(storage, "evals", evaluation_record)
    print(json.dumps({"status": evaluation_record["qualification_disposition"], "evaluation_path": str(path), "evaluation_sha256": digest_out, **metrics}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
