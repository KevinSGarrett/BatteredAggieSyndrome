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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the real-data shadow gamebook extraction pilot")
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--max-jobs", type=int, default=36)
    args = parser.parse_args()

    config = json.loads((ROOT / "configs" / "openai_gamebook_pilot.json").read_text(encoding="utf-8"))
    controller = AssistiveController(ROOT)
    gold_path = args.gold.resolve(strict=True)
    gold_path.relative_to(controller.store.directory("evals"))
    gold = _jsonl(gold_path)
    prompt_spec = config["prompt"]
    prompt_path = ROOT / prompt_spec["path"]
    prompt_bytes = prompt_path.read_bytes()
    if hashlib.sha256(prompt_bytes).hexdigest() != prompt_spec["sha256"]:
        raise SystemExit("gamebook pilot prompt hash mismatch")
    prompt_base = prompt_bytes.decode("utf-8").rstrip()
    routes = config["routes"]
    job_count = len(gold) * len(routes)
    if job_count == 0 or job_count > args.max_jobs:
        raise SystemExit(f"bounded pilot job count {job_count} is outside 1..{args.max_jobs}")

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    costs: Counter[str] = Counter()
    schema_path = ROOT / config["output_schema"]
    for route in routes:
        for case in gold:
            fields = [fact["field"] for fact in case["expected_facts"]]
            prompt = f"{prompt_base}\n\nExtract exactly these fields: {json.dumps(fields, separators=(',', ':'))}."
            job = AssistiveJob(
                task_name=config["task_name"],
                jira_unit=config["jira_unit"],
                source_url=f"{case['source_url']}#case={case['case_id']}",
                source_capture_sha256=case["source_capture_sha256"],
                source_excerpt=case["source_excerpt"],
                prompt=prompt,
                prompt_version=prompt_spec["version"],
                schema_path=schema_path,
                schema_version="1",
                model=route["model"],
                reasoning_effort=route["reasoning_effort"],
                allocation="PROBE_PROMPT_EVAL",
                destination="CANDIDATE",
                max_output_tokens=1024,
                priority=Priority.NORMAL,
            )
            try:
                result = controller.run_sync(job)
                candidate = result.candidate
                costs[route["model"]] += Decimal(result.actual_cost_usd)
                if candidate is None:
                    failures.append({"model": route["model"], "case_id": case["case_id"], "error": "NO_CANDIDATE"})
                    continue
                rows.append({"case_id": case["case_id"], "model": route["model"], "reasoning_effort": route["reasoning_effort"], "actual_cost_usd": result.actual_cost_usd, "review_time_saved_seconds": 0, "disposition": result.disposition, "validation_errors": list(result.validation_errors), "entity_merge": candidate.get("entity_merge"), "entity_top_k": candidate.get("entity_top_k", []), "candidate": candidate})
            except Exception as exc:
                failures.append({"model": route["model"], "case_id": case["case_id"], "error": type(exc).__name__})
                if type(exc).__name__ in {"AuthenticationError", "BadRequestError", "PermissionDeniedError"}:
                    break
        if failures and failures[-1]["error"] in {"AuthenticationError", "BadRequestError", "PermissionDeniedError"}:
            break
    payload = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows).encode("utf-8")
    predictions = controller.store.put_bytes("evals", payload, suffix=".gamebook-predictions.jsonl")
    manifest = controller.store.put_json("evals", {"schema_version": 2, "artifact_type": "openai_gamebook_pilot_run", "pilot_id": config["pilot_id"], "jira_unit": config["jira_unit"], "authority": config["authority"], "prompt_version": prompt_spec["version"], "prompt_sha256": prompt_spec["sha256"], "gold_sha256": hashlib.sha256(gold_path.read_bytes()).hexdigest(), "case_count": len(gold), "required_domains": config["required_domains"], "requested_jobs": job_count, "completed_predictions": len(rows), "failures": failures, "predictions_sha256": predictions.sha256, "predictions_bytes": predictions.bytes, "cost_usd_by_model": {key: f"{value:.6f}" for key, value in sorted(costs.items())}, "final_disposition": "SHADOW_PILOT_ONLY"})
    print(json.dumps({"requested_jobs": job_count, "completed_predictions": len(rows), "failure_count": len(failures), "predictions_path": str(predictions.path), "predictions_sha256": predictions.sha256, "manifest_path": str(manifest.path), "manifest_sha256": manifest.sha256, "cost_usd_by_model": {key: f"{value:.6f}" for key, value in sorted(costs.items())}}, indent=2, sort_keys=True))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
