from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.budget import BudgetLedger, BudgetRejected  # noqa: E402
from aggie_analytics.assistive_plane.cursor_backend import (  # noqa: E402
    CursorApiError,
    CursorBackend,
    CursorCloudClient,
    CursorRunPolicy,
)
from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json  # noqa: E402


ENV = Path(r"C:\BatteredAggieSyndrome\.env")
STORE = Path(r"C:\BatteredAggieSyndrome.data\assistive\cursor")
POLICY = ROOT / "configs" / "unified_assistive_policy.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def job_identity(spec: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(spec)).hexdigest()


def agent_identity(job_id: str) -> str:
    return f"bc-{uuid.UUID(job_id[:32])}"


def ledger(policy: dict[str, Any]) -> BudgetLedger:
    budget = policy["budgets"]["cursor"]
    return BudgetLedger(
        STORE / "usage" / "ledger.json",
        Decimal(budget["hard_limit_usd"]),
        Decimal(budget["released_stage_usd"]),
    )


def load_spec(path: Path) -> dict[str, Any]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    required = {"jira_unit", "prompt", "repository_url", "starting_ref", "base_commit", "reasoning", "max_reservation_usd"}
    if set(spec) != required:
        raise ValueError("CURSOR_JOB_SPEC_FIELDS_INVALID")
    if spec["starting_ref"] != spec["base_commit"] or len(spec["base_commit"]) != 40:
        raise ValueError("CURSOR_EXACT_BASE_IDENTITY_REQUIRED")
    if spec["jira_unit"] != "POST-SUBTASK-202":
        raise ValueError("CURSOR_JIRA_UNIT_NOT_AUTHORIZED")
    if Decimal(str(spec["max_reservation_usd"])) <= 0:
        raise ValueError("CURSOR_POSITIVE_RESERVATION_REQUIRED")
    return spec


def submit(spec_path: Path) -> dict[str, Any]:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    spec = load_spec(spec_path)
    job_id = job_identity(spec)
    agent_id = agent_identity(job_id)
    budget = ledger(policy)
    reservation = Decimal(str(spec["max_reservation_usd"]))
    budget.reserve(job_id, reservation)
    backend = CursorBackend(CursorRunPolicy(reasoning=spec["reasoning"]))
    payload = backend.build_create_payload(
        prompt=spec["prompt"],
        repository_url=spec["repository_url"],
        starting_ref=spec["starting_ref"],
        agent_id=agent_id,
    )
    request_evidence = {
        "schema_version": 1,
        "job_id": job_id,
        "agent_id": agent_id,
        "jira_unit": spec["jira_unit"],
        "base_commit": spec["base_commit"],
        "model": backend.policy.model,
        "reasoning": backend.policy.reasoning,
        "fast": False,
        "work_on_current_branch": False,
        "auto_create_pr": False,
        "reservation_usd": format(reservation, "f"),
        "prompt_sha256": hashlib.sha256(spec["prompt"].encode("utf-8")).hexdigest(),
    }
    write_content_addressed_json(STORE, "requests", request_evidence)
    client = CursorCloudClient(ENV)
    try:
        response = client.request("POST", "/agents", payload)
    except CursorApiError as exc:
        if exc.status != 409:
            budget.release(job_id)
            raise
        response = {"agent": client.request("GET", f"/agents/{agent_id}"), "idempotent_conflict_recovery": True}
    result = {
        **request_evidence,
        "agent": response.get("agent", {}),
        "run": response.get("run", {}),
        "disposition": "RUNNING_CANDIDATE_ONLY",
        "cost_status": "RESERVED_PENDING_PROVIDER_USAGE_AND_SPEND_RECONCILIATION",
        "canonical_write_authority": False,
        "protected_decision_authority": False,
    }
    path, digest = write_content_addressed_json(STORE, "manifests", result)
    return {"status": "SUBMITTED", "agent_id": agent_id, "job_id": job_id, "manifest_path": str(path), "manifest_sha256": digest}


def inspect(agent_id: str, job_id: str) -> dict[str, Any]:
    client = CursorCloudClient(ENV)
    agent = client.request("GET", f"/agents/{agent_id}")
    run_id = str(agent.get("latestRunId", ""))
    if not run_id:
        raise RuntimeError("CURSOR_LATEST_RUN_ID_MISSING")
    run = client.request("GET", f"/agents/{agent_id}/runs/{run_id}")
    usage = client.request("GET", f"/agents/{agent_id}/usage?runId={run_id}")
    result = {
        "schema_version": 1,
        "job_id": job_id,
        "agent_id": agent_id,
        "run_id": run_id,
        "agent": agent,
        "run": run,
        "usage": usage,
        "cost_status": "PROVIDER_TOKEN_USAGE_CAPTURED_COST_RECONCILIATION_PENDING",
        "candidate_only": True,
    }
    path, digest = write_content_addressed_json(STORE, "results", result)
    return {"status": run.get("status"), "agent_id": agent_id, "run_id": run_id, "result_path": str(path), "result_sha256": digest, "git": run.get("git", {})}


def main() -> int:
    parser = argparse.ArgumentParser(description="Governed Cursor Cloud Agent candidate controller")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("submit")
    create.add_argument("spec", type=Path)
    status = sub.add_parser("inspect")
    status.add_argument("agent_id")
    status.add_argument("job_id")
    args = parser.parse_args()
    try:
        result = submit(args.spec) if args.command == "submit" else inspect(args.agent_id, args.job_id)
    except BudgetRejected as exc:
        result = {"status": "REJECTED", "reason": str(exc)}
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
