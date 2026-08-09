from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

from jira_pack_lib import JIRA_ROOT, load_records, recompute_ready, save_record
from rebuild_all_derivatives import rebuild_derivatives
from second_pass_hardening import import_lib, strict_validate

ALLOWED_LOGICAL_STATES = {
    "BACKLOG", "READY", "IN_PROGRESS", "BLOCKED", "REVIEW", "VALIDATION",
    "EVIDENCE_PENDING", "DONE", "DEFERRED", "CANCELLED",
}


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def logical_status(raw: str) -> str:
    mapping = {
        "backlog": "BACKLOG", "todo": "BACKLOG", "open": "BACKLOG",
        "ready": "READY", "selectedfordevelopment": "READY",
        "inprogress": "IN_PROGRESS", "review": "REVIEW", "inreview": "REVIEW",
        "validation": "VALIDATION", "evidencepending": "EVIDENCE_PENDING",
        "blocked": "BLOCKED", "done": "DONE", "closed": "DONE", "resolved": "DONE",
        "deferred": "DEFERRED", "cancelled": "CANCELLED", "canceled": "CANCELLED",
    }
    return mapping.get(norm(raw), "")


def write_conflicts(rows: list[dict[str, str]]) -> None:
    path = JIRA_ROOT / "reconciliation" / "SYNC_CONFLICTS.csv"
    fields = ["local_id", "field", "jira_value", "local_value", "resolution"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile a Jira CSV export into safety-normalized local operational fields using Local Issue ID."
    )
    parser.add_argument("export_csv", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=None, help="Authoritative BAS repository root when the Jira pack is extracted separately.")
    args = parser.parse_args()

    with args.export_csv.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        names = {norm(name): name for name in (reader.fieldnames or [])}

    local_col = names.get("localissueid") or names.get("localid")
    key_col = names.get("issuekey") or names.get("key")
    logical_col = names.get("logicalworkflowstate")
    status_col = names.get("status")
    assignee_col = names.get("assignee") or names.get("assigneeemail")
    sprint_col = names.get("sprint")
    updated_col = names.get("updated") or names.get("updatedat")
    issue_id_col = names.get("issueid") or names.get("jiraworkitemid") or names.get("workitemid")
    if not local_col or not key_col:
        print("ERROR: Export must contain Local Issue ID and Issue key columns", file=sys.stderr)
        return 1

    records = load_records()
    by_id = {record["local_id"]: record for record in records}
    original_snapshots = {
        Path(record["__path"]): Path(record["__path"]).read_bytes()
        for record in records
    }
    before_state = {
        record["local_id"]: {
            "jira_key": record.get("jira_key", ""),
            "workflow_state": record.get("workflow_state", ""),
            "ready": record.get("ready", False),
            "operational_jira": record.get("operational_jira", {}),
        }
        for record in records
    }

    errors: list[str] = []
    conflicts: list[dict[str, str]] = []
    requested_states: dict[str, str] = {}
    now = datetime.now(timezone.utc).isoformat()

    for row in rows:
        local_id = row.get(local_col, "").strip()
        if not local_id:
            continue
        record = by_id.get(local_id)
        if record is None:
            errors.append(f"Unknown Local Issue ID {local_id}")
            continue

        incoming_key = row.get(key_col, "").strip()
        existing_key = str(record.get("jira_key", ""))
        if not incoming_key:
            conflicts.append({
                "local_id": local_id, "field": "Issue key", "jira_value": "", "local_value": existing_key,
                "resolution": "BLANK_KEY_NOT_APPLIED",
            })
        elif not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", incoming_key):
            errors.append(f"{local_id}: invalid Jira issue key format {incoming_key!r}")
        elif existing_key and existing_key != incoming_key:
            conflicts.append({
                "local_id": local_id, "field": "Issue key", "jira_value": incoming_key, "local_value": existing_key,
                "resolution": "EXISTING_KEY_MISMATCH_REQUIRES_MANUAL_REVIEW",
            })
        else:
            record["jira_key"] = incoming_key

        raw_status = row.get(status_col, "").strip() if status_col else ""
        requested_logical = row.get(logical_col, "").strip().upper() if logical_col else ""
        mapped = requested_logical or logical_status(raw_status)
        if mapped and mapped not in ALLOWED_LOGICAL_STATES:
            conflicts.append({
                "local_id": local_id, "field": "Logical Workflow State", "jira_value": mapped,
                "local_value": str(record.get("workflow_state", "")),
                "resolution": "UNKNOWN_LOGICAL_STATE_NOT_APPLIED",
            })
            mapped = ""
        if raw_status and not mapped:
            conflicts.append({
                "local_id": local_id, "field": "Status", "jira_value": raw_status,
                "local_value": str(record.get("workflow_state", "")),
                "resolution": "RAW_STATUS_RECORDED_LOGICAL_STATE_NOT_OVERWRITTEN",
            })
        elif mapped == "DONE" and record.get("evidence_state") not in {"COMPLETE", "VERIFIED"}:
            conflicts.append({
                "local_id": local_id, "field": "Status", "jira_value": raw_status or mapped,
                "local_value": str(record.get("workflow_state", "")),
                "resolution": "DONE_REJECTED_UNTIL_LOCAL_EVIDENCE_IS_COMPLETE_OR_VERIFIED",
            })
        elif mapped:
            record["workflow_state"] = mapped
            requested_states[local_id] = mapped

        operational = dict(record.get("operational_jira", {}))
        operational.update({
            "status_raw": raw_status,
            "assignee": row.get(assignee_col, "").strip() if assignee_col else "",
            "sprint": row.get(sprint_col, "").strip() if sprint_col else "",
            "jira_updated_at": row.get(updated_col, "").strip() if updated_col else "",
            "jira_issue_id": row.get(issue_id_col, "").strip() if issue_id_col else operational.get("jira_issue_id", ""),
            "last_synced_at": now,
            "source_export": str(args.export_csv.resolve()),
        })
        record["operational_jira"] = operational

    if errors:
        for error in errors:
            print("ERROR:", error, file=sys.stderr)
        return 1

    recompute_ready(records)
    for local_id, requested in requested_states.items():
        actual = str(by_id[local_id].get("workflow_state", ""))
        if requested != actual:
            conflicts.append({
                "local_id": local_id,
                "field": "Logical Workflow State",
                "jira_value": requested,
                "local_value": actual,
                "resolution": "LOCAL_DEPENDENCY_EVIDENCE_GATE_OVERRIDES_UNSAFE_JIRA_STATE",
            })

    changes: list[dict[str, object]] = []
    for record in records:
        after = {
            "jira_key": record.get("jira_key", ""),
            "workflow_state": record.get("workflow_state", ""),
            "ready": record.get("ready", False),
            "operational_jira": record.get("operational_jira", {}),
        }
        before = before_state[record["local_id"]]
        if before != after:
            changes.append({"local_id": record["local_id"], "before": before, "after": after})

    if args.dry_run:
        print(json.dumps({
            "result": "DRY_RUN_PASS",
            "rows": len(rows),
            "changes": len(changes),
            "conflicts": conflicts,
        }, indent=2, sort_keys=True))
        return 0

    try:
        for record in records:
            save_record(record)
        rebuild_derivatives(write_manifest=False)
        validation_errors, validation_metrics = strict_validate(load_records(), write_reports=True)
        if validation_errors:
            raise RuntimeError(
                "Reconciled state failed strict validation: " + "; ".join(validation_errors[:25])
            )
    except Exception as exc:
        for path, data in original_snapshots.items():
            path.write_bytes(data)
        rebuild_derivatives(write_manifest=True)
        print(f"ERROR: reconciliation rolled back: {exc}", file=sys.stderr)
        return 1

    write_conflicts(conflicts)
    log = JIRA_ROOT / "history" / "ISSUE_CHANGE_LOG.jsonl"
    with log.open("a", encoding="utf-8") as handle:
        for change in changes:
            event = dict(change)
            event.update({
                "timestamp": now,
                "event": "JIRA_EXPORT_RECONCILED",
                "actor": "reconcile_jira_export.py",
                "source_export": str(args.export_csv.resolve()),
            })
            handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
    import_lib().rebuild_file_manifest()

    print(json.dumps({
        "result": "PASS",
        "rows": len(rows),
        "changed_issues": len(changes),
        "conflict_count": len(conflicts),
        "strict_validation": validation_metrics.get("result", "PASS"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
