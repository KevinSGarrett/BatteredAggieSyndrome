from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.openai_assist.contracts import (  # noqa: E402
    Priority,
    ProcessingMode,
    canonical_json_bytes,
    sha256_value,
)
from aggie_analytics.openai_assist.controller import AssistiveController, AssistiveJob  # noqa: E402


DEFAULT_QUEUE = Path(r"C:\BatteredAggieSyndrome.data\assistive\provider_work\requests")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _queue(value: dict[str, Any], root: Path) -> tuple[Path, str]:
    data = canonical_json_bytes(value) + b"\n"
    digest = hashlib.sha256(data).hexdigest()
    destination = root / "sha256" / digest[:2] / f"{digest}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() != data:
            raise RuntimeError("OPENAI_PROVIDER_WORK_CONTENT_ADDRESS_COLLISION")
        return destination, digest
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".openai-provider-work-", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return destination, digest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Queue one governed gamebook candidate for the persistent OpenAI scheduler adapter"
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--queue-root", type=Path, default=DEFAULT_QUEUE)
    args = parser.parse_args()

    config_path = args.config.resolve(strict=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    controller = AssistiveController(ROOT)
    gold_path = args.gold.resolve(strict=True)
    gold_path.relative_to(controller.store.directory("evals"))
    matches = [row for row in _load_jsonl(gold_path) if row.get("case_id") == args.case_id]
    if len(matches) != 1:
        raise SystemExit("gamebook candidate case identity must resolve exactly once")
    case = matches[0]
    routes = [route for route in config["routes"] if args.case_id in route.get("case_ids", [])]
    if len(routes) != 1:
        raise SystemExit("gamebook candidate route identity must resolve exactly once")
    route = routes[0]

    prompt_path = ROOT / config["prompt"]["path"]
    prompt_data = prompt_path.read_bytes()
    if hashlib.sha256(prompt_data).hexdigest() != config["prompt"]["sha256"]:
        raise SystemExit("gamebook candidate prompt hash mismatch")
    fields = [fact["field"] for fact in case["expected_facts"]]
    prompt = (
        f"{prompt_data.decode('utf-8').rstrip()}\n\n"
        f"Case ID: {case['case_id']}\n"
        f"Return task_id exactly {config['task_name']} and case_id exactly {case['case_id']}.\n"
        "Return disposition REVIEW. Extract exactly these fields in this order: "
        f"{json.dumps(fields, separators=(',', ':'))}.\n"
        "For every SUPPORTED fact, evidence must contain exactly one item whose "
        "source_capture_sha256 and excerpt_sha256 both equal SOURCE_CAPTURE_SHA256 and whose "
        "locator is evidence:1."
    )
    schema_path = ROOT / config["output_schema"]
    schema = controller._load_schema(schema_path)
    model = str(route["model"])
    allocation = controller.registry["tasks"][config["task_name"]]["allocation_by_model"][model]
    job = AssistiveJob(
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
        allocation=allocation,
        destination="REVIEW",
        max_output_tokens=2048,
        priority=Priority.NORMAL,
    )
    prepared = controller.prepare(job, ProcessingMode.SYNCHRONOUS)
    packet = {
        "schema_version": 1,
        "provider": "openai_direct",
        "jira_unit": config["jira_unit"],
        "task_format": "governed_openai_candidate_v1",
        "schema_sha256": sha256_value(schema),
        "source_hashes": sorted(
            {
                hashlib.sha256(gold_path.read_bytes()).hexdigest(),
                case["source_capture_sha256"],
                case["source_payload_sha256"],
                case["source_record_evidence_sha256"],
            }
        ),
        "dependencies": [],
        "pre_routing_effort_points": 3,
        "scope": (
            f"Governed controller-routed gamebook schema review for {case['case_id']}; "
            "candidate-only with no canonical, PIT, training, protected, or publication authority."
        ),
        "job": {
            "task_name": job.task_name,
            "jira_unit": job.jira_unit,
            "source_url": job.source_url,
            "source_capture_sha256": job.source_capture_sha256,
            "source_excerpt": job.source_excerpt,
            "prompt": job.prompt,
            "prompt_version": job.prompt_version,
            "schema_path": config["output_schema"],
            "schema_version": job.schema_version,
            "model": job.model,
            "reasoning_effort": job.reasoning_effort,
            "allocation": job.allocation,
            "destination": job.destination,
            "max_output_tokens": job.max_output_tokens,
            "priority": job.priority.value,
            "release_reason": job.release_reason,
            "admission_review_id": job.admission_review_id,
            "source_image_path": None,
            "source_image_mime_type": None,
            "source_image_detail": None,
        },
        "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
    }
    destination, packet_sha256 = _queue(packet, args.queue_root)
    print(
        json.dumps(
            {
                "result": "PASS",
                "packet_path": str(destination),
                "packet_sha256": packet_sha256,
                "request_id": prepared["request_id"],
                "model": model,
                "reasoning_effort": route["reasoning_effort"],
                "live_api_calls": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
