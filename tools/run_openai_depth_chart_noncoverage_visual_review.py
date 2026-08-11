from __future__ import annotations

"""Preflight or run bounded governed visual QA for depth-chart noncoverage."""

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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_path(data_root: Path, identity: str) -> Path:
    return (
        data_root
        / "manifests"
        / "historical_known_at"
        / "sha256"
        / identity
        / "tamu_depth_chart_noncoverage_review_manifest.json"
    )


def job_for(
    controller: AssistiveController,
    config: dict[str, Any],
    prompt: str,
    record: dict[str, Any],
    sample: dict[str, Any],
    image_path: Path,
) -> AssistiveJob:
    source_excerpt = (
        f"CASE_ID={sample['case_id']}\n"
        f"PDF_PAGE_LOCATOR={record['review_page_locator']}\n"
        f"PAGE_IMAGE_SHA256={record['rendered_image_sha256']}\n"
        f"PAGE_TEXT_SHA256={record['review_page_text_sha256']}\n"
        "HISTORICAL_PUBLICATION_TIME_STATE=UNKNOWN\n"
        "CANONICAL_OR_PIT_ADMISSION=false"
    )
    return AssistiveJob(
        task_name=config["task_name"],
        jira_unit=config["jira_unit"],
        source_url=f"{record['source_url']}#page={record['review_page_number']}",
        source_capture_sha256=record["source_response_sha256"],
        source_excerpt=source_excerpt,
        prompt=prompt,
        prompt_version=config["prompt"]["version"],
        schema_path=ROOT / config["output_schema"],
        schema_version="1",
        model=sample["model"],
        reasoning_effort=sample["reasoning_effort"],
        allocation=controller.registry["tasks"][config["task_name"]]["allocation_by_model"][sample["model"]],
        destination="CANDIDATE",
        max_output_tokens=1536,
        priority=Priority.NORMAL,
        source_image_path=image_path,
        source_image_mime_type="image/png",
        source_image_detail=sample["image_detail"],
    )


def candidate_errors(candidate: dict[str, Any], record: dict[str, Any], task_name: str) -> list[str]:
    errors: list[str] = []
    if candidate.get("task_id") != task_name:
        errors.append("task identity mismatch")
    if candidate.get("source_capture_sha256") != record["source_response_sha256"]:
        errors.append("source capture identity mismatch")
    if candidate.get("disposition") != "CANDIDATE":
        errors.append("visual review disposition is not CANDIDATE")
    expected = {
        "page_classification": "STARTING_LINEUP_HISTORY_NOT_DEPTH_CHART",
        "depth_chart_present": False,
        "starting_lineup_history_present": True,
        "historical_publication_time_utc": None,
        "historical_publication_time_state": "UNKNOWN",
    }
    for field, value in expected.items():
        if candidate.get(field) != value:
            errors.append(f"{field} mismatch")
    evidence = candidate.get("evidence") or {}
    if evidence.get("source_capture_sha256") != record["source_response_sha256"]:
        errors.append("evidence capture mismatch")
    if evidence.get("locator") != record["review_page_locator"]:
        errors.append("page locator mismatch")
    if evidence.get("rendered_image_sha256") != record["rendered_image_sha256"]:
        errors.append("rendered-image evidence hash mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    config = json.loads((ROOT / "configs" / "openai_depth_chart_noncoverage_review.json").read_text(encoding="utf-8"))
    controller = AssistiveController(ROOT)
    data_root = controller.store.root.parent
    deterministic = config["deterministic_result"]
    source_manifest_path = manifest_path(data_root, deterministic["dataset_identity"])
    if sha256_file(source_manifest_path) != deterministic["manifest_sha256"]:
        raise SystemExit("depth-chart noncoverage review manifest hash mismatch")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    records = {row["source_request_id"]: row for row in source_manifest["records"]}
    prompt_path = ROOT / config["prompt"]["path"]
    if sha256_file(prompt_path) != config["prompt"]["sha256"]:
        raise SystemExit("depth-chart noncoverage visual prompt hash mismatch")
    prompt = prompt_path.read_text(encoding="utf-8")
    image_root = data_root / source_manifest["page_images"]["directory"]
    jobs: list[tuple[dict[str, Any], dict[str, Any], AssistiveJob]] = []
    for sample in config["visual_samples"]:
        record = records.get(sample["source_request_id"])
        if record is None:
            raise SystemExit(f"configured visual sample is outside the deterministic review: {sample['case_id']}")
        if record["season"] != sample["season"] or record["season_ordinal"] != sample["season_ordinal"]:
            raise SystemExit(f"configured visual sample metadata mismatch: {sample['case_id']}")
        image_path = image_root / record["rendered_image_name"]
        if sha256_file(image_path) != record["rendered_image_sha256"]:
            raise SystemExit(f"configured visual sample image hash mismatch: {sample['case_id']}")
        jobs.append((sample, record, job_for(controller, config, prompt, record, sample, image_path)))
    if len(jobs) != 2:
        raise SystemExit("bounded visual QA must contain exactly the two predeclared format samples")

    estimates: Counter[str] = Counter()
    request_ids: list[str] = []
    prepared_rows: list[dict[str, Any]] = []
    for sample, record, job in jobs:
        prepared = controller.prepare(job, ProcessingMode.SYNCHRONOUS)
        request_ids.append(prepared["request_id"])
        estimates[job.model] += prepared["estimate"].amount_usd
        prepared_rows.append(
            {
                "case_id": sample["case_id"],
                "request_id": prepared["request_id"],
                "model": job.model,
                "reasoning_effort": job.reasoning_effort,
                "estimated_input_tokens": prepared["estimate"].tokens.input_tokens,
                "estimated_max_usd": f"{prepared['estimate'].amount_usd:.6f}",
                "source_capture_sha256": record["source_response_sha256"],
                "rendered_image_sha256": record["rendered_image_sha256"],
                "page_locator": record["review_page_locator"],
            }
        )
    if args.plan_only:
        manifest = controller.store.put_json(
            "evals",
            {
                "schema_version": 1,
                "artifact_type": "openai_depth_chart_noncoverage_visual_preflight",
                "review_id": config["review_id"],
                "jira_unit": config["jira_unit"],
                "authority": config["authority"],
                "deterministic_dataset_identity": deterministic["dataset_identity"],
                "jobs": prepared_rows,
                "estimated_max_usd_by_model": {
                    key: f"{value:.6f}" for key, value in sorted(estimates.items())
                },
                "live_api_calls": 0,
                "batch_jobs": 0,
                "final_disposition": "PREFLIGHT_PASS_BOUNDED_SYNCHRONOUS_VISUAL_QA_READY",
            },
        )
        print(
            json.dumps(
                {
                    "result": "PASS",
                    "jobs": prepared_rows,
                    "estimated_max_usd_by_model": {
                        key: f"{value:.6f}" for key, value in sorted(estimates.items())
                    },
                    "manifest_path": str(manifest.path),
                    "manifest_sha256": manifest.sha256,
                    "live_api_calls": 0,
                    "batch_jobs": 0,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    rows: list[dict[str, Any]] = []
    cost = Decimal("0")
    for sample, record, job in jobs:
        result = controller.run_sync(job)
        errors = list(result.validation_errors)
        if result.candidate is None:
            errors.append("NO_CANDIDATE")
        else:
            errors.extend(candidate_errors(result.candidate, record, config["task_name"]))
        cost += Decimal(result.actual_cost_usd)
        rows.append(
            {
                "case_id": sample["case_id"],
                "request_id": result.request_id,
                "model": job.model,
                "reasoning_effort": job.reasoning_effort,
                "actual_cost_usd": result.actual_cost_usd,
                "cached": result.cached,
                "controller_disposition": result.disposition,
                "validation_errors": errors,
                "candidate": result.candidate,
            }
        )
    prediction_payload = b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
        for row in rows
    )
    predictions = controller.store.put_bytes(
        "evals", prediction_payload, suffix=".depth-chart-noncoverage-visual-predictions.jsonl"
    )
    exact = sum(not row["validation_errors"] for row in rows)
    run_manifest = controller.store.put_json(
        "evals",
        {
            "schema_version": 1,
            "artifact_type": "openai_depth_chart_noncoverage_visual_run",
            "review_id": config["review_id"],
            "jira_unit": config["jira_unit"],
            "authority": config["authority"],
            "deterministic_dataset_identity": deterministic["dataset_identity"],
            "requested_jobs": len(jobs),
            "provider_calls": sum(not row["cached"] for row in rows),
            "cached_results": sum(row["cached"] for row in rows),
            "exact_candidates": exact,
            "quarantined_or_rejected": len(rows) - exact,
            "predictions_sha256": predictions.sha256,
            "actual_cost_usd_by_model": {"gpt-4o-mini": f"{cost:.6f}"},
            "batch_jobs": 0,
            "batch_reason": "TWO_CASE_NEW_VISUAL_FORMAT_REQUIRES_BOUNDED_SYNCHRONOUS_QA_NOT_SCALE_OUT",
            "canonical_writes": 0,
            "pit_writes": 0,
            "training_feature_writes": 0,
            "historical_publication_time_state": "UNKNOWN",
            "final_disposition": (
                "PASS_EXACT_CANDIDATE_ONLY_NEGATIVE_FINDING_CONFIRMED"
                if exact == len(rows)
                else "PARTIAL_OR_FAIL_RETAIN_DETERMINISTIC_NEGATIVE_FINDING_AND_QUARANTINE_MODEL_OUTPUT"
            ),
        },
    )
    print(
        json.dumps(
            {
                "requested_jobs": len(jobs),
                "provider_calls": sum(not row["cached"] for row in rows),
                "cached_results": sum(row["cached"] for row in rows),
                "exact_candidates": exact,
                "failure_count": len(rows) - exact,
                "predictions_path": str(predictions.path),
                "predictions_sha256": predictions.sha256,
                "manifest_path": str(run_manifest.path),
                "manifest_sha256": run_manifest.sha256,
                "actual_cost_usd_by_model": {"gpt-4o-mini": f"{cost:.6f}"},
                "batch_jobs": 0,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return int(exact != len(rows))


if __name__ == "__main__":
    raise SystemExit(main())
