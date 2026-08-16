"""Select resumable and dependency-ready Jira work from canonical records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

PRIORITY = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "DEFERRED": 9}


def load_records(repo_root: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    root = repo_root / "jira/records/issues"
    for path in sorted(root.rglob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        local_id = record.get("local_id")
        if local_id:
            record["_record_path"] = path.relative_to(repo_root).as_posix()
            records[str(local_id)] = record
    return records


def select(repo_root: Path) -> list[dict[str, Any]]:
    records = load_records(repo_root.resolve())
    selected: list[dict[str, Any]] = []
    for record in records.values():
        if record.get("execution_mode") != "ATOMIC_EXECUTION":
            continue
        dependencies = [str(value) for value in record.get("dependencies", [])]
        if any(records.get(dep, {}).get("workflow_state") != "DONE" for dep in dependencies):
            continue
        operational = record.get("operational_jira", {}) or {}
        status = operational.get("status_raw", "")
        workflow_state = str(record.get("workflow_state", ""))
        resumable = workflow_state == "IN_PROGRESS" and status == "In Progress"
        ready = workflow_state == "READY" and record.get("ready") is True and status in {"", "To Do"}
        if not (resumable or ready):
            continue
        selected.append({
            "local_id": record.get("local_id"),
            "jira_key": record.get("jira_key", ""),
            "priority": record.get("priority", "DEFERRED"),
            "critical_path": bool(record.get("critical_path")),
            "objective": record.get("objective", ""),
            "execution_lane": record.get("execution_lane", ""),
            "dependencies": dependencies,
            "record_path": record.get("_record_path"),
            "work_packet_path": record.get("work_packet_path", ""),
            "selection_class": "RESUME_IN_PROGRESS" if resumable else "READY_NEW_WORK",
        })
    selected.sort(
        key=lambda item: (
            item["selection_class"] != "RESUME_IN_PROGRESS",
            PRIORITY.get(str(item["priority"]), 8),
            not item["critical_path"],
            str(item["local_id"]),
        )
    )
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    items = select(args.repo_root)[: max(0, args.limit)]
    if args.format == "json":
        print(json.dumps({"count": len(items), "items": items}, indent=2, sort_keys=True))
    else:
        print("# Resumable and dependency-ready Jira work\n")
        if not items:
            print("No dependency-ready atomic work is currently available.")
        for index, item in enumerate(items, 1):
            print(
                f"{index}. **{item['jira_key']} / {item['local_id']}** — "
                f"{item['selection_class']} — {item['priority']} — {item['objective']}"
            )
            print(f"   - Record: `{item['record_path']}`")
            print(f"   - Work packet: `{item['work_packet_path']}`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
