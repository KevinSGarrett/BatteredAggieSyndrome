from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.contracts import sha256_value
from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json
from aggie_analytics.assistive_plane.redaction import contains_secret
from aggie_analytics.assistive_plane.schemas import validate_output, validate_strict_schema
from tools.run_local_qwen_qualification import extract, request_json, resolve_source, sha256


PATCH_PATH = re.compile(r"^(?:---|\+\+\+) [ab]/(.+)$", re.MULTILINE)


def prompt_for(packet: dict[str, Any], excerpt: str, source_sha256: str) -> str:
    allowed = ", ".join(packet["allowed_paths"])
    return (
        "Return one bounded coding-assistance candidate as strict JSON. Use only the numbered source excerpt. "
        "Do not claim to have run tests or inspected files outside the excerpt. Evidence quotes must be exact complete "
        "numbered lines. Any unified diff must use --- a/path and +++ b/path headers and may touch only the allowed "
        "paths. Do not include credentials, shell commands, network calls, canonical-data writes, or protected decisions. "
        "If no correction is justified, return an empty patch and REVIEW or UNKNOWN.\n\n"
        f"TASK_ID: {packet['task_id']}\nTASK_TYPE: {packet['task_type']}\n"
        f"INSTRUCTION: {packet['instruction']}\nALLOWED_PATHS: {allowed}\n"
        f"SOURCE_SHA256: {source_sha256}\nSOURCE:\n{excerpt}"
    )


def evaluate(packet: dict[str, Any], output: dict[str, Any], excerpt: str) -> dict[str, Any]:
    findings = output.get("findings", [])
    valid_findings = sum(
        bool(item.get("evidence_quote")) and item["evidence_quote"] in excerpt
        for item in findings
    )
    patch = output.get("patch", "")
    patch_paths = sorted(set(PATCH_PATH.findall(patch)))
    proposed_paths = sorted(set(output.get("proposed_paths", [])))
    allowed = set(packet["allowed_paths"])
    paths_valid = set(patch_paths).issubset(allowed) and set(proposed_paths).issubset(allowed)
    patch_contract_valid = (not packet["patch_required"] or bool(patch.strip())) and (
        not patch.strip() or bool(patch_paths)
    )
    combined = json.dumps(output, sort_keys=True, ensure_ascii=False).lower()
    recalled = sum(term.lower() in combined for term in packet["expected_terms"])
    unsupported = output.get("unsupported_facts", [])
    identity_valid = output.get("task_id") == packet["task_id"] and output.get("task_type") == packet["task_type"]
    evidence_accuracy = valid_findings / len(findings) if findings else 0.0
    expected_recall = recalled / len(packet["expected_terms"])
    accepted = (
        identity_valid
        and paths_valid
        and patch_contract_valid
        and evidence_accuracy >= 0.9
        and expected_recall >= 0.8
        and not unsupported
        and not contains_secret(json.dumps(output, ensure_ascii=False))
    )
    return {
        "task_id": packet["task_id"],
        "task_type": packet["task_type"],
        "identity_valid": identity_valid,
        "finding_count": len(findings),
        "valid_evidence_findings": valid_findings,
        "evidence_accuracy": evidence_accuracy,
        "expected_terms": packet["expected_terms"],
        "expected_terms_recalled": recalled,
        "expected_term_recall": expected_recall,
        "patch_paths": patch_paths,
        "proposed_paths": proposed_paths,
        "allowed_paths_valid": paths_valid,
        "patch_contract_valid": patch_contract_valid,
        "unsupported_fact_count": len(unsupported),
        "disposition": "ACCEPTED_SHADOW_CANDIDATE" if accepted else "QUARANTINE_OR_REVIEW",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/local_coder_shadow_qualification.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    schema_path = ROOT / config["schema_path"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate_strict_schema(schema)
    tags = request_json(f"{config['endpoint']}/api/tags", None)
    matches = [item for item in tags["models"] if item.get("name") == config["model"]]
    if len(matches) != 1 or matches[0].get("digest") != config["expected_digest"]:
        raise RuntimeError("LOCAL_CODER_EXACT_DIGEST_MISMATCH")
    storage = Path(config["storage_root"])
    results: list[dict[str, Any]] = []
    unload_succeeded = False
    try:
        for sequence, packet in enumerate(config["packets"], start=1):
            source = resolve_source(packet["source_path"])
            source_sha256 = sha256(source)
            raw_excerpt = extract(packet, source)
            excerpt = "\n".join(f"L{index:03d}: {line}" for index, line in enumerate(raw_excerpt.splitlines(), start=1))
            prompt = prompt_for(packet, excerpt, source_sha256)
            if contains_secret(prompt):
                raise RuntimeError("LOCAL_CODER_PROMPT_SECRET_DETECTED")
            request_payload = {
                "model": config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": schema,
                "options": {"temperature": 0, "num_ctx": config["context_tokens"], "num_predict": 1200},
                "keep_alive": "5m",
            }
            request_record = {
                "schema_version": 1,
                "qualification_id": config["qualification_id"],
                "jira_unit": config["jira_unit"],
                "sequence": sequence,
                "task_id": packet["task_id"],
                "task_type": packet["task_type"],
                "source_path": packet["source_path"],
                "source_sha256": source_sha256,
                "allowed_paths": packet["allowed_paths"],
                "schema_sha256": sha256(schema_path),
                "model": config["model"],
                "model_digest": config["expected_digest"],
                "prompt": prompt,
                "direct_mutation_authority": False,
                "canonical_or_protected_authority": False,
            }
            _, request_sha256 = write_content_addressed_json(storage, "requests", request_record)
            started = time.perf_counter()
            response = request_json(f"{config['endpoint']}/api/chat", request_payload)
            elapsed = time.perf_counter() - started
            raw = response.get("message", {}).get("content", "")
            output: dict[str, Any] = {}
            strict_valid = True
            strict_error = ""
            try:
                output = json.loads(raw)
                validate_output(output, schema)
            except (json.JSONDecodeError, ValueError) as exc:
                strict_valid = False
                strict_error = str(exc)
            evaluation = evaluate(packet, output, excerpt) if strict_valid else {
                "task_id": packet["task_id"], "task_type": packet["task_type"],
                "identity_valid": False, "finding_count": 0, "valid_evidence_findings": 0,
                "evidence_accuracy": 0.0, "expected_terms": packet["expected_terms"],
                "expected_terms_recalled": 0, "expected_term_recall": 0.0, "patch_paths": [],
                "proposed_paths": [], "allowed_paths_valid": False, "patch_contract_valid": False,
                "unsupported_fact_count": 0, "disposition": "QUARANTINE_OR_REVIEW",
            }
            response_record = {
                "schema_version": 1,
                "request_sha256": request_sha256,
                "model": response.get("model"),
                "model_digest": config["expected_digest"],
                "output": output if strict_valid else None,
                "output_sha256": sha256_value(output) if strict_valid else None,
                "raw_content": raw,
                "strict_schema_valid": strict_valid,
                "strict_schema_error": strict_error,
                "evaluation": evaluation,
                "usage": {
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "output_tokens": response.get("eval_count", 0),
                    "total_duration_ns": response.get("total_duration"),
                    "wall_seconds": round(elapsed, 6),
                },
            }
            category = "responses" if evaluation["disposition"] == "ACCEPTED_SHADOW_CANDIDATE" else "quarantine"
            _, response_sha256 = write_content_addressed_json(storage, category, response_record)
            results.append({
                **evaluation,
                "strict_schema_valid": strict_valid,
                "request_sha256": request_sha256,
                "response_sha256": response_sha256,
                "usage": response_record["usage"],
            })
    finally:
        try:
            request_json(f"{config['endpoint']}/api/generate", {"model": config["model"], "prompt": "", "stream": False, "keep_alive": 0})
            unload_succeeded = True
        except Exception:
            unload_succeeded = False
    finding_total = sum(item["finding_count"] for item in results)
    metrics = {
        "packets": len(results),
        "task_types": len({item["task_type"] for item in results}),
        "strict_schema_rate": sum(item["strict_schema_valid"] for item in results) / len(results),
        "allowed_path_rate": sum(item["allowed_paths_valid"] for item in results) / len(results),
        "evidence_accuracy": sum(item["valid_evidence_findings"] for item in results) / finding_total if finding_total else 0.0,
        "expected_term_recall": sum(item["expected_terms_recalled"] for item in results) / sum(len(item["expected_terms"]) for item in results),
        "unsupported_fact_rate": sum(item["unsupported_fact_count"] for item in results) / finding_total if finding_total else 0.0,
        "accepted_shadow_candidates": sum(item["disposition"] == "ACCEPTED_SHADOW_CANDIDATE" for item in results),
        "quarantine_or_review": sum(item["disposition"] != "ACCEPTED_SHADOW_CANDIDATE" for item in results),
        "prompt_tokens": sum(item["usage"]["prompt_tokens"] for item in results),
        "output_tokens": sum(item["usage"]["output_tokens"] for item in results),
        "wall_seconds": round(sum(item["usage"]["wall_seconds"] for item in results), 6),
        "model_size_bytes": matches[0].get("size"),
        "unload_succeeded": unload_succeeded,
        "review_time_saved_seconds": 0.0,
        "direct_mutations": 0,
        "canonical_writes": 0,
        "protected_decisions": 0,
    }
    acceptance = config["acceptance"]
    passed = (
        metrics["packets"] >= acceptance["packets_min"]
        and metrics["task_types"] >= acceptance["unique_task_types_min"]
        and metrics["strict_schema_rate"] >= acceptance["strict_schema_rate_min"]
        and metrics["allowed_path_rate"] >= acceptance["allowed_path_rate_min"]
        and metrics["evidence_accuracy"] >= acceptance["evidence_accuracy_min"]
        and metrics["expected_term_recall"] >= acceptance["expected_term_recall_min"]
        and metrics["unsupported_fact_rate"] <= acceptance["unsupported_fact_rate_max"]
        and unload_succeeded
    )
    record = {
        "schema_version": 1,
        "qualification_id": config["qualification_id"],
        "jira_unit": config["jira_unit"],
        "authority": config["authority"],
        "config_sha256": sha256(args.config),
        "schema_sha256": sha256(schema_path),
        "model": config["model"],
        "model_digest": config["expected_digest"],
        "metrics": metrics,
        "acceptance": acceptance,
        "results": results,
        "qualification_disposition": "PASS_SHADOW_CANDIDATE_ONLY" if passed else "FAIL_PRESERVE_NEGATIVE_EVIDENCE",
        "automatic_patch_application": False,
        "operational_route_ready": False,
    }
    path, digest = write_content_addressed_json(storage, "evals", record)
    print(json.dumps({"status": record["qualification_disposition"], "path": str(path), "sha256": digest, **metrics}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
