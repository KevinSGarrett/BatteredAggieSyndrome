"""Recover one unbilled Cursor-create 429 after independently verified capacity cleanup."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .controller_state import (
    CURSOR_CAPACITY_RECOVERABLE_ERROR,
    ControllerState,
)
from .cursor_backend import CursorCloudClient
from .orchestration import write_content_addressed_json


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _list_agents(client: CursorCloudClient) -> list[dict[str, object]]:
    agents: list[dict[str, object]] = []
    cursor: str | None = None
    for _ in range(100):
        path = "/agents?limit=100"
        if cursor:
            path += "&cursor=" + urllib.parse.quote(cursor, safe="")
        payload = client.request("GET", path)
        page = payload.get("items", [])
        if not isinstance(page, list):
            raise RuntimeError("CURSOR_AGENT_CATALOG_ITEMS_INVALID")
        agents.extend(item for item in page if isinstance(item, dict))
        next_cursor = payload.get("nextCursor")
        if not next_cursor:
            return agents
        cursor = str(next_cursor)
    raise RuntimeError("CURSOR_AGENT_CATALOG_PAGINATION_BOUND_EXCEEDED")


def _failed_unit_snapshot(database: Path, work_unit_id: str) -> dict[str, object]:
    connection = sqlite3.connect(
        f"file:{database.as_posix()}?mode=ro", uri=True, timeout=10
    )
    connection.row_factory = sqlite3.Row
    try:
        unit = connection.execute(
            "SELECT work_unit_id,current_state,identity_sha256,jira_identity,version "
            "FROM work_units WHERE work_unit_id=?",
            (work_unit_id,),
        ).fetchone()
        if unit is None:
            raise KeyError(work_unit_id)
        attempt = connection.execute(
            "SELECT attempt_id,provider,state,error_code,started_at,completed_at "
            "FROM dispatch_attempts WHERE work_unit_id=? "
            "ORDER BY started_at DESC,attempt_id DESC LIMIT 1",
            (work_unit_id,),
        ).fetchone()
        if attempt is None:
            raise RuntimeError("CURSOR_CAPACITY_RECOVERY_ATTEMPT_MISSING")
        provider_runs = connection.execute(
            "SELECT COUNT(*) FROM provider_runs WHERE attempt_id=?",
            (attempt["attempt_id"],),
        ).fetchone()[0]
        open_leases = connection.execute(
            "SELECT COUNT(*) FROM work_leases WHERE work_unit_id=? AND status!='CLOSED'",
            (work_unit_id,),
        ).fetchone()[0]
        return {
            "unit": dict(unit),
            "latest_attempt": dict(attempt),
            "provider_run_count": int(provider_runs),
            "open_lease_count": int(open_leases),
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-unit-id", required=True)
    parser.add_argument("--pre-archive-report", type=Path, required=True)
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path(r"C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3"),
    )
    parser.add_argument(
        "--cursor-root",
        type=Path,
        default=Path(r"C:\BatteredAggieSyndrome.data\assistive\cursor"),
    )
    parser.add_argument(
        "--authoritative-env",
        type=Path,
        default=Path(r"C:\BatteredAggieSyndrome\.env"),
    )
    parser.add_argument("--maximum-active-agents", type=int, default=0)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.maximum_active_agents < 0:
        raise SystemExit("maximum-active-agents must be nonnegative")
    pre_archive = json.loads(args.pre_archive_report.read_text(encoding="utf-8"))
    if pre_archive.get("artifact_type") != "CURSOR_AGENT_LIFECYCLE_PRE_ARCHIVE_RECONCILIATION":
        raise RuntimeError("CURSOR_PRE_ARCHIVE_REPORT_TYPE_INVALID")
    if int(pre_archive.get("blocked_count", -1)) != 0:
        raise RuntimeError("CURSOR_PRE_ARCHIVE_REPORT_CONTAINS_BLOCKED_AGENTS")

    database = args.runtime_root / "state" / "orchestrator.sqlite3"
    snapshot = _failed_unit_snapshot(database, args.work_unit_id)
    attempt = snapshot["latest_attempt"]
    if (
        snapshot["unit"]["current_state"] != "FAILED"
        or attempt["provider"] != "cursor"
        or attempt["state"] != "FAILED"
        or attempt["error_code"] != CURSOR_CAPACITY_RECOVERABLE_ERROR
        or snapshot["provider_run_count"] != 0
        or snapshot["open_lease_count"] != 0
    ):
        raise RuntimeError("CURSOR_CAPACITY_RECOVERY_SNAPSHOT_INELIGIBLE")

    agents = _list_agents(CursorCloudClient(args.authoritative_env, timeout_seconds=60))
    statuses = Counter(str(agent.get("status")) for agent in agents)
    active = sorted(
        str(agent.get("id")) for agent in agents if agent.get("status") == "ACTIVE"
    )
    if len(active) > args.maximum_active_agents:
        raise RuntimeError("CURSOR_CAPACITY_RECOVERY_ACTIVE_AGENT_BOUND_EXCEEDED")

    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    evidence = {
        "schema_version": 1,
        "artifact_type": "CURSOR_CAPACITY_RECOVERY_ADMISSION",
        "created_at_utc": created_at,
        "work_unit_id": args.work_unit_id,
        "pre_archive_report_path": str(args.pre_archive_report.resolve()),
        "pre_archive_report_sha256": _sha256(args.pre_archive_report),
        "remote_agent_count": len(agents),
        "remote_agent_status_counts": dict(sorted(statuses.items())),
        "active_agent_ids": active,
        "maximum_active_agents": args.maximum_active_agents,
        "failed_unit_snapshot": snapshot,
        "recovery_disposition": (
            "APPLY_OPERATOR_VERIFIED_NONBILLABLE_RETRY"
            if args.apply
            else "DRY_RUN_ELIGIBLE"
        ),
    }
    evidence_path, evidence_sha256 = write_content_addressed_json(
        args.cursor_root,
        "lifecycle_cleanup/capacity_recovery",
        evidence,
    )
    retry_id = None
    if args.apply:
        retry_id = ControllerState(database).recover_cursor_capacity_failure(
            work_unit_id=args.work_unit_id,
            recovery_evidence_sha256=evidence_sha256,
            actor="CURSOR_CAPACITY_RECOVERY_OPERATOR",
        )
    print(
        json.dumps(
            {
                "applied": args.apply,
                "evidence_path": str(evidence_path),
                "evidence_sha256": evidence_sha256,
                "retry_id": retry_id,
                "remote_agent_status_counts": dict(sorted(statuses.items())),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
