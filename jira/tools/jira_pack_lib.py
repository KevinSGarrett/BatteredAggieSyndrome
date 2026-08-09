from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
sys.dont_write_bytecode = True
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

JIRA_ROOT = Path(__file__).resolve().parents[1]

def _configured_repo_root() -> Path:
    raw = os.environ.get("BAS_JIRA_REPO_ROOT") or os.environ.get("BAS_REPO_ROOT")
    if not raw:
        for index, argument in enumerate(sys.argv):
            if argument == "--repo-root" and index + 1 < len(sys.argv):
                raw = sys.argv[index + 1]
                break
            if argument.startswith("--repo-root="):
                raw = argument.split("=", 1)[1]
                break
    return Path(raw).expanduser().resolve() if raw else JIRA_ROOT.parent

REPO_ROOT = _configured_repo_root()
RECORD_ROOT = JIRA_ROOT / "records" / "issues"

def project_path(value: str | Path) -> Path:
    relative = Path(value)
    if relative.parts and relative.parts[0].lower() == "jira":
        return JIRA_ROOT.joinpath(*relative.parts[1:])
    return REPO_ROOT / relative

def repository_context_errors() -> list[str]:
    required = [
        "governance/REQUIREMENTS_INDEX.csv",
        "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
        "governance/ADR_INDEX.csv",
        "docs/final/FINAL_RISK_REGISTER.csv",
        "docs/final/FINAL_KNOWN_GAPS.csv",
    ]
    missing = [item for item in required if not project_path(item).is_file()]
    if not missing:
        return []
    return [
        "Authoritative repository context is unavailable. Install this jira/ directory beneath the BAS repository root "
        "or rerun with --repo-root <path-to-BatteredAggieSyndrome>. Missing sentinels: " + ", ".join(missing)
    ]
SCHEMA_VERSION = 2
MANIFEST_EXCLUDES = {
    "validation/JIRA_FILE_MANIFEST.csv",
    "validation/JIRA_FILE_HASHES.sha256",
}
ACTIONABLE_REQUIRED_FIELDS = [
    "local_id", "jira_key", "import_id", "issue_type", "title", "parent_id", "epic_id", "phase",
    "workflow_state", "historical_classification", "priority", "critical_path", "owner_wave", "source_ids",
    "objective", "why_this_exists", "scope", "in_scope", "out_of_scope", "prerequisites", "dependencies",
    "blocks", "files_expected_to_be_read", "files_expected_to_be_touched", "protected_files_and_interfaces",
    "expected_outputs", "requirement_ids", "acceptance_control_ids", "adr_ids", "risk_ids", "gap_ids",
    "acceptance_criteria", "definition_of_done", "required_tests", "required_evidence", "end_to_end_validation",
    "maturity_before", "expected_maturity_after_completion", "evidence_state", "risk_failure_conditions",
    "stop_conditions", "source_refs", "labels", "component", "execution_lane", "execution_mode",
    "ready", "blocked_reason", "unblock_condition", "ai_context_notes", "canonical_record", "generated_markdown",
]
REQUIRED_IMPORT_FIELDS = [
    "Issue type", "Issue key", "Issue ID", "Summary", "Parent", "Description", "Status", "Priority",
    "Labels", "Component", "Local Issue ID", "Source IDs", "Phase", "Logical Workflow State",
    "Implementation Maturity", "Evidence State", "Owner Historical Wave", "Critical Path", "Execution Lane",
    "Execution Mode",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def norm_space(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def load_records() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted(RECORD_ROOT.rglob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        record["__path"] = path
        out.append(record)
    return out


def save_record(record: dict[str, Any]) -> None:
    path = record.get("__path")
    if not path:
        path = project_path(record["canonical_record"])
    payload = {key: value for key, value in record.items() if key != "__path"}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    record["__path"] = Path(path)


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str] | None = None) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            clean: dict[str, Any] = {}
            for key in fields:
                value = row.get(key, "")
                if isinstance(value, bool):
                    value = "true" if value else "false"
                elif isinstance(value, (list, tuple, set)):
                    value = ";".join(str(item) for item in value)
                elif isinstance(value, dict):
                    value = json.dumps(value, sort_keys=True, ensure_ascii=False)
                elif value is None:
                    value = ""
                clean[key] = value
            writer.writerow(clean)


def write_jsonl(path: Path, rows: Iterable[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def rebuild_file_manifest() -> int:
    rows: list[dict[str, Any]] = []
    for path in sorted(JIRA_ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(JIRA_ROOT).as_posix()
        if rel in MANIFEST_EXCLUDES or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        data = path.read_bytes()
        rows.append({"path": rel, "bytes": len(data), "sha256": sha256_bytes(data)})
    write_csv(JIRA_ROOT / "validation" / "JIRA_FILE_MANIFEST.csv", rows, ["path", "bytes", "sha256"])
    (JIRA_ROOT / "validation" / "JIRA_FILE_HASHES.sha256").write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in rows), encoding="utf-8"
    )
    return len(rows)


def validate_file_manifest() -> list[str]:
    errors: list[str] = []
    manifest = JIRA_ROOT / "validation" / "JIRA_FILE_MANIFEST.csv"
    if not manifest.exists():
        return ["Missing validation/JIRA_FILE_MANIFEST.csv"]
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    represented: set[str] = set()
    for row in rows:
        rel = row.get("path", "")
        represented.add(rel)
        path = JIRA_ROOT / rel
        if not path.exists():
            errors.append(f"Manifested file missing: {rel}")
            continue
        if int(row.get("bytes", -1)) != path.stat().st_size:
            errors.append(f"Manifest size mismatch: {rel}")
        if row.get("sha256") != sha256_bytes(path.read_bytes()):
            errors.append(f"Manifest hash mismatch: {rel}")
    expected = {
        path.relative_to(JIRA_ROOT).as_posix()
        for path in JIRA_ROOT.rglob("*")
        if path.is_file()
        and path.relative_to(JIRA_ROOT).as_posix() not in MANIFEST_EXCLUDES
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }
    for rel in sorted(expected - represented):
        errors.append(f"Unrepresented Jira file: {rel}")
    for rel in sorted(represented - expected):
        errors.append(f"Manifest contains unexpected file: {rel}")
    return errors


def status_for_import(logical: str) -> str:
    return {
        "DONE": "Done", "CANCELLED": "Done", "IN_PROGRESS": "In Progress", "REVIEW": "In Progress",
        "VALIDATION": "In Progress", "EVIDENCE_PENDING": "In Progress",
    }.get(logical, "To Do")


def priority_for_import(priority: str) -> str:
    return {
        "P0": "Highest", "P1": "High", "P2": "Medium", "P3": "Low", "DEFERRED": "Low", "CONDITIONAL": "Low",
    }.get(priority, "Medium")


def jira_issue_type(issue_type: str) -> str:
    return "Sub-task" if issue_type == "Subtask" else issue_type


def _bullets(values: Iterable[Any]) -> str:
    vals = [str(value).strip() for value in values if str(value).strip()]
    return "\n".join(f"- {value}" for value in vals) if vals else "- None."


def _numbers(values: Iterable[Any]) -> str:
    vals = [str(value).strip() for value in values if str(value).strip()]
    return "\n".join(f"{index}. {value}" for index, value in enumerate(vals, 1)) if vals else "1. None."


def description(record: dict[str, Any]) -> str:
    tests = [
        f"{test.get('classification', '')}: {test.get('path', '')} — {test.get('expectation', '')}"
        for test in record.get("required_tests", [])
    ]
    return f"""Local ID: {record['local_id']}
Execution mode: {record.get('execution_mode', '')}

Objective
{record.get('objective', '')}

Why this exists
{record.get('why_this_exists', '')}

Scope
{record.get('scope', '')}

In Scope
{_bullets(record.get('in_scope', []))}

Out of Scope
{_bullets(record.get('out_of_scope', []))}

Prerequisites
{_bullets(record.get('prerequisites', []))}

Hard Dependencies
{_bullets(record.get('dependencies', []))}

Read-Only Context / Expected Inputs
{_bullets(record.get('files_expected_to_be_read', []))}

Expected Files / Components To Be Touched
{_bullets(record.get('files_expected_to_be_touched', []))}

Protected Files / Interfaces
{_bullets(record.get('protected_files_and_interfaces', []))}

Expected Outputs
{_bullets(record.get('expected_outputs', []))}

Acceptance Criteria
{_numbers(record.get('acceptance_criteria', []))}

Definition of Done
{_numbers(record.get('definition_of_done', []))}

Required Tests
{_bullets(tests)}

Required Evidence
{_bullets(record.get('required_evidence', []))}

End-to-End Validation
{record.get('end_to_end_validation', '')}

Stop Conditions
{_bullets(record.get('stop_conditions', []))}

Source References
{_bullets(record.get('source_refs', []))}
"""


def _text_node(text: Any, *, strong: bool = False, code: bool = False) -> dict[str, Any]:
    node: dict[str, Any] = {"type": "text", "text": str(text)}
    marks: list[dict[str, str]] = []
    if strong:
        marks.append({"type": "strong"})
    if code:
        marks.append({"type": "code"})
    if marks:
        node["marks"] = marks
    return node


def _paragraph(*nodes: dict[str, Any]) -> dict[str, Any]:
    return {"type": "paragraph", "content": list(nodes)}


def _heading(level: int, text: str) -> dict[str, Any]:
    return {"type": "heading", "attrs": {"level": level}, "content": [_text_node(text)]}


def _list_node(values: Iterable[Any], *, ordered: bool = False) -> dict[str, Any] | None:
    vals = [str(value).strip() for value in values if str(value).strip()]
    if not vals:
        vals = ["None."]
    items = [
        {"type": "listItem", "content": [_paragraph(_text_node(value))]}
        for value in vals
    ]
    node: dict[str, Any] = {"type": "orderedList" if ordered else "bulletList", "content": items}
    if ordered:
        node["attrs"] = {"order": 1}
    return node


def issue_description_adf(record: dict[str, Any]) -> dict[str, Any]:
    content: list[dict[str, Any]] = [
        _paragraph(_text_node("Local ID: ", strong=True), _text_node(record["local_id"], code=True)),
        _paragraph(_text_node("Execution mode: ", strong=True), _text_node(record.get("execution_mode", ""), code=True)),
    ]

    def section(title: str, body: Any, *, ordered: bool = False, is_list: bool = False) -> None:
        content.append(_heading(2, title))
        if is_list:
            content.append(_list_node(body, ordered=ordered) or _paragraph())
        else:
            content.append(_paragraph(_text_node(body or "None.")))

    section("Objective", record.get("objective", ""))
    section("Why This Exists", record.get("why_this_exists", ""))
    section("Scope", record.get("scope", ""))
    section("In Scope", record.get("in_scope", []), is_list=True)
    section("Out of Scope", record.get("out_of_scope", []), is_list=True)
    section("Prerequisites", record.get("prerequisites", []), is_list=True)
    section("Hard Dependencies", record.get("dependencies", []), is_list=True)
    section("Read-Only Context / Expected Inputs", record.get("files_expected_to_be_read", []), is_list=True)
    section("Expected Files / Components To Be Touched", record.get("files_expected_to_be_touched", []), is_list=True)
    section("Protected Files / Interfaces", record.get("protected_files_and_interfaces", []), is_list=True)
    section("Expected Outputs / Artifacts", record.get("expected_outputs", []), is_list=True)
    section("Acceptance Criteria", record.get("acceptance_criteria", []), is_list=True, ordered=True)
    section("Definition of Done", record.get("definition_of_done", []), is_list=True, ordered=True)
    tests = [
        f"{test.get('classification', '')}: {test.get('path', '')} — {test.get('expectation', '')}"
        for test in record.get("required_tests", [])
    ]
    section("Required Tests", tests, is_list=True)
    section("Required Evidence", record.get("required_evidence", []), is_list=True)
    section("End-to-End Validation", record.get("end_to_end_validation", ""))
    section("Expected Maturity After Completion", record.get("expected_maturity_after_completion", ""))
    section("Risk / Failure Conditions", record.get("risk_failure_conditions", []), is_list=True)
    section("Stop Conditions", record.get("stop_conditions", []), is_list=True)
    section("Source References", record.get("source_refs", []), is_list=True)
    return {"version": 1, "type": "doc", "content": content}


def recompute_ready(records: list[dict[str, Any]]) -> None:
    by_id = {record["local_id"]: record for record in records}
    for record in records:
        record["blocks"] = []
    for record in records:
        for dependency in record.get("dependencies", []):
            if dependency in by_id and dependency != record["local_id"]:
                by_id[dependency]["blocks"].append(record["local_id"])
    for record in records:
        record["blocks"] = sorted(set(record.get("blocks", [])))

    for record in records:
        if str(record.get("historical_classification", "")).startswith("HISTORICAL"):
            record["ready"] = False
            continue
        if record.get("workflow_state") in {"DONE", "CANCELLED"}:
            record["ready"] = False
            continue
        labels = set(record.get("labels", []))
        if record.get("workflow_state") == "DEFERRED" or "deferred" in labels or "conditional" in labels:
            record["workflow_state"] = "DEFERRED"
            record["ready"] = False
            record["blocked_reason"] = record.get("blocked_reason") or "DEFERRED_OR_CONDITIONAL_BY_FINAL_HANDOFF"
            record["unblock_condition"] = record.get("unblock_condition") or "Documented admission/replanning approval plus all prerequisites."
            continue
        if record.get("execution_mode") != "ATOMIC_EXECUTION" or record.get("issue_type") != "Subtask":
            record["ready"] = False
            if record.get("workflow_state") not in {"IN_PROGRESS", "REVIEW", "VALIDATION", "EVIDENCE_PENDING"}:
                record["workflow_state"] = "BACKLOG"
            continue
        external = str(record.get("blocked_reason", ""))
        if external and not external.startswith("UNSATISFIED_HARD_DEPENDENCIES"):
            record["workflow_state"] = "BLOCKED"
            record["ready"] = False
            continue
        unsatisfied: list[str] = []
        for dependency in record.get("dependencies", []):
            upstream = by_id.get(dependency)
            if not upstream or upstream.get("workflow_state") != "DONE" or upstream.get("evidence_state") not in {"COMPLETE", "VERIFIED"}:
                unsatisfied.append(dependency)
        if unsatisfied:
            record["workflow_state"] = "BLOCKED"
            record["ready"] = False
            record["blocked_reason"] = "UNSATISFIED_HARD_DEPENDENCIES: " + ";".join(unsatisfied)
            record["unblock_condition"] = "Complete and verify all hard dependencies at required maturity/evidence."
        elif record.get("workflow_state") not in {"IN_PROGRESS", "REVIEW", "VALIDATION", "EVIDENCE_PENDING"}:
            record["workflow_state"] = "READY"
            record["ready"] = True
            record["blocked_reason"] = ""
            record["unblock_condition"] = ""


def build_indexes(records: list[dict[str, Any]]) -> None:
    by_id = {record["local_id"]: record for record in records}
    issue_rows: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: item["local_id"]):
        issue_rows.append({
            "local_id": record["local_id"], "jira_key": record.get("jira_key", ""), "import_id": record.get("import_id", ""),
            "issue_type": record["issue_type"], "summary": record["title"], "parent": record.get("parent_id", ""),
            "epic": record.get("epic_id", ""), "phase": record.get("phase", ""), "priority": record.get("priority", ""),
            "workflow_state": record.get("workflow_state", ""), "maturity_before": record.get("maturity_before", ""),
            "maturity_after": record.get("expected_maturity_after_completion", ""), "evidence_state": record.get("evidence_state", ""),
            "ready": record.get("ready", False), "blocked_by": record.get("dependencies", []),
            "critical_path": record.get("critical_path", False), "component": record.get("component", ""),
            "execution_lane": record.get("execution_lane", ""), "execution_mode": record.get("execution_mode", ""),
            "historical_classification": record.get("historical_classification", ""), "owner_wave": record.get("owner_wave", ""),
            "read_file_count": len(record.get("files_expected_to_be_read", [])),
            "touch_file_count": len(record.get("files_expected_to_be_touched", [])),
            "source_ids": record.get("source_ids", []), "primary_source_refs": record.get("source_refs", [])[:8],
            "canonical_record": record.get("canonical_record", ""), "generated_markdown": record.get("generated_markdown", ""),
        })
    write_csv(JIRA_ROOT / "index" / "ISSUE_INDEX.csv", issue_rows)

    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    ready = sorted(
        [record for record in records if record.get("ready")],
        key=lambda record: (
            priority_order.get(record.get("priority"), 9), not record.get("critical_path"),
            -len(record.get("blocks", [])), record["local_id"],
        ),
    )
    write_csv(JIRA_ROOT / "index" / "READY_QUEUE.csv", [{
        "rank": rank, "local_id": record["local_id"], "summary": record["title"], "priority": record.get("priority", ""),
        "critical_path": record.get("critical_path", False), "dependency_unlock_count": len(record.get("blocks", [])),
        "execution_lane": record.get("execution_lane", ""), "execution_mode": record.get("execution_mode", ""),
        "component": record.get("component", ""), "parent": record.get("parent_id", ""),
        "dependencies": record.get("dependencies", []), "source_refs": record.get("source_refs", [])[:8],
        "canonical_record": record.get("canonical_record", ""),
    } for rank, record in enumerate(ready, 1)])

    blocked = sorted(
        [record for record in records if record.get("workflow_state") == "BLOCKED"],
        key=lambda record: (priority_order.get(record.get("priority"), 9), record["local_id"]),
    )
    write_csv(JIRA_ROOT / "index" / "BLOCKED_QUEUE.csv", [{
        "issue_id": record["local_id"], "summary": record["title"], "reason": record.get("blocked_reason", ""),
        "blocking_issue": [
            dependency for dependency in record.get("dependencies", [])
            if by_id.get(dependency, {}).get("workflow_state") != "DONE"
        ],
        "blocking_evidence": [
            by_id.get(dependency, {}).get("evidence_state", "MISSING") for dependency in record.get("dependencies", [])
            if by_id.get(dependency, {}).get("workflow_state") != "DONE"
        ],
        "unblock_condition": record.get("unblock_condition", ""), "priority": record.get("priority", ""),
        "downstream_impact": len(record.get("blocks", [])), "critical_path": record.get("critical_path", False),
        "execution_lane": record.get("execution_lane", ""), "execution_mode": record.get("execution_mode", ""),
    } for record in blocked])

    dependency_rows: list[dict[str, Any]] = []
    for record in records:
        if record.get("parent_id"):
            dependency_rows.append({
                "source_id": record["parent_id"], "target_id": record["local_id"], "relationship": "PARENT_CHILD",
                "hard": False, "source_basis": "Canonical hierarchy",
            })
        for dependency in record.get("dependencies", []):
            dependency_rows.append({
                "source_id": dependency, "target_id": record["local_id"], "relationship": "BLOCKS",
                "hard": True, "source_basis": "Issue dependency contract",
            })
        for related in record.get("related_to", []):
            dependency_rows.append({
                "source_id": record["local_id"], "target_id": related, "relationship": "RELATES_TO",
                "hard": False, "source_basis": "Historical/post-wave reconciliation",
            })
    write_csv(JIRA_ROOT / "index" / "DEPENDENCY_INDEX.csv", dependency_rows)
    write_csv(JIRA_ROOT / "index" / "HIERARCHY_INDEX.csv", [{
        "local_id": record["local_id"], "issue_type": record["issue_type"], "parent_id": record.get("parent_id", ""),
        "epic_id": record.get("epic_id", ""), "depth": 0 if record["issue_type"] == "Epic" else 1 if record["issue_type"] in {"Story", "Task", "Bug"} else 2,
        "import_id": record.get("import_id", ""), "parent_import_id": by_id.get(record.get("parent_id", ""), {}).get("import_id", ""),
    } for record in sorted(records, key=lambda item: item.get("import_id", 0))])

    tests: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    packets: list[dict[str, Any]] = []
    for record in records:
        for test in record.get("required_tests", []):
            tests.append({
                "test_path": test.get("path", ""), "classification": test.get("classification", ""),
                "issue_id": record["local_id"], "issue_type": record["issue_type"], "expectation": test.get("expectation", ""),
            })
        for artifact in record.get("expected_outputs", []):
            artifacts.append({
                "artifact_path_or_name": artifact, "producer_issue_id": record["local_id"], "issue_type": record["issue_type"],
                "required_for_completion": True, "expected_maturity": record.get("expected_maturity_after_completion", ""),
                "downstream_issue_ids": record.get("blocks", []), "evidence_state": record.get("evidence_state", ""),
            })
        if record.get("historical_classification") == "ACTIONABLE_POST_WAVE":
            packets.append({
                "local_id": record["local_id"], "issue_type": record["issue_type"],
                "execution_mode": record.get("execution_mode", ""), "ready": record.get("ready", False),
                "packet_path": f"jira/ai/work_packets/{record['local_id']}.md",
                "directly_executable": record.get("execution_mode") == "ATOMIC_EXECUTION",
            })
    write_csv(JIRA_ROOT / "index" / "TEST_TRACEABILITY.csv", tests)
    write_csv(JIRA_ROOT / "index" / "ARTIFACT_TRACEABILITY.csv", artifacts)
    write_csv(JIRA_ROOT / "index" / "WORK_PACKET_INDEX.csv", packets)

    compact = "# Compact READY Queue\n\n" + (
        "\n".join(
            f"{rank}. `{record['local_id']}` | {record.get('priority')} | "
            f"{'CRITICAL' if record.get('critical_path') else 'normal'} | {record.get('execution_lane')} | {record.get('title')}"
            for rank, record in enumerate(ready, 1)
        ) or "No issues are currently READY."
    ) + "\n"
    (JIRA_ROOT / "ai" / "READY_QUEUE_COMPACT.md").write_text(compact, encoding="utf-8")


def build_import_files(records: list[dict[str, Any]]) -> dict[str, int]:
    by_id = {record["local_id"]: record for record in records}
    ordered = sorted(records, key=lambda record: int(record.get("import_id", 0)))
    rows: list[dict[str, Any]] = []
    for record in ordered:
        labels = list(dict.fromkeys(record.get("labels", []) + ["local-id-" + record["local_id"].lower()]))
        rows.append({
            "Issue type": jira_issue_type(record["issue_type"]), "Issue key": record.get("jira_key", ""),
            "Issue ID": record.get("import_id", ""), "Summary": record["title"],
            "Parent": by_id.get(record.get("parent_id", ""), {}).get("import_id", ""),
            "Description": description(record), "Status": status_for_import(record.get("workflow_state", "")),
            "Priority": priority_for_import(record.get("priority", "")), "Labels": labels,
            "Component": record.get("component", ""), "Local Issue ID": record["local_id"],
            "Source IDs": record.get("source_ids", []), "Phase": record.get("phase", ""),
            "Logical Workflow State": record.get("workflow_state", ""),
            "Implementation Maturity": record.get("expected_maturity_after_completion", ""),
            "Evidence State": record.get("evidence_state", ""), "Owner Historical Wave": record.get("owner_wave", ""),
            "Critical Path": record.get("critical_path", False), "Execution Lane": record.get("execution_lane", ""),
            "Execution Mode": record.get("execution_mode", ""),
        })
    subsets = {
        "JIRA_ISSUES_MASTER.csv": rows,
        "JIRA_EXTERNAL_SYSTEM_IMPORT.csv": rows,
        "JIRA_HIERARCHY_STAGE_1.csv": [row for row in rows if row["Issue type"] == "Epic"],
        "JIRA_HIERARCHY_STAGE_2.csv": [row for row in rows if row["Issue type"] in {"Story", "Task", "Bug"}],
        "JIRA_HIERARCHY_STAGE_3.csv": [row for row in rows if row["Issue type"] == "Sub-task"],
    }
    for name, subset in subsets.items():
        write_csv(JIRA_ROOT / "import" / name, subset, REQUIRED_IMPORT_FIELDS)

    link_rows: list[dict[str, Any]] = []
    for record in ordered:
        for dependency in record.get("dependencies", []):
            link_rows.append({
                "source_local_id": dependency, "relationship": "BLOCKS", "target_local_id": record["local_id"],
                "source_jira_key": f"{{{{JIRA_KEY:{dependency}}}}}",
                "target_jira_key": f"{{{{JIRA_KEY:{record['local_id']}}}}}",
                "target_link_type_name": "Blocks", "status": "PENDING_POST_IMPORT_KEY_MAP",
            })
        for related in record.get("related_to", []):
            link_rows.append({
                "source_local_id": record["local_id"], "relationship": "RELATES_TO", "target_local_id": related,
                "source_jira_key": f"{{{{JIRA_KEY:{record['local_id']}}}}}",
                "target_jira_key": f"{{{{JIRA_KEY:{related}}}}}",
                "target_link_type_name": "Relates", "status": "PENDING_POST_IMPORT_KEY_MAP",
            })
    link_rows = sorted(
        {(
            row["source_local_id"], row["relationship"], row["target_local_id"]
        ): row for row in link_rows}.values(),
        key=lambda row: (row["relationship"], row["source_local_id"], row["target_local_id"]),
    )
    write_csv(JIRA_ROOT / "import" / "JIRA_LINKS.csv", link_rows)
    write_jsonl(JIRA_ROOT / "import" / "JIRA_LINKS.jsonl", link_rows)

    create_payloads: list[dict[str, Any]] = []
    for record in ordered:
        fields: dict[str, Any] = {
            "project": {"key": "{{PROJECT_KEY}}"},
            "issuetype": {"name": f"{{{{ISSUE_TYPE:{record['issue_type']}}}}}"},
            "summary": record["title"],
            "description": issue_description_adf(record),
            "labels": list(dict.fromkeys(record.get("labels", []) + ["local-id-" + record["local_id"].lower()])),
        }
        if record.get("parent_id"):
            fields["parent"] = {"key": f"{{{{JIRA_KEY:{record['parent_id']}}}}}"}
        create_payloads.append({
            "local_id": record["local_id"], "method": "POST", "endpoint": "/rest/api/3/issue",
            "payload_template": {"fields": fields},
            "logical_fields_requiring_target_custom_field_ids": {
                "Local Issue ID": record["local_id"], "Source IDs": ";".join(record.get("source_ids", [])),
                "Phase": record.get("phase", ""), "Logical Workflow State": record.get("workflow_state", ""),
                "Implementation Maturity": record.get("expected_maturity_after_completion", ""),
                "Evidence State": record.get("evidence_state", ""), "Owner Historical Wave": record.get("owner_wave", ""),
                "Critical Path": record.get("critical_path", False), "Execution Lane": record.get("execution_lane", ""),
                "Execution Mode": record.get("execution_mode", ""),
            },
            "execution_status": "TEMPLATE_ONLY_REQUIRES_TARGET_PROFILE_AND_PARENT_KEY_MAP",
        })
    write_jsonl(JIRA_ROOT / "import" / "JIRA_API_CREATE_PAYLOADS.jsonl", create_payloads)

    link_payloads: list[dict[str, Any]] = []
    for row in link_rows:
        link_name = "Blocks" if row["relationship"] == "BLOCKS" else "Relates"
        link_payloads.append({
            "method": "POST", "endpoint": "/rest/api/3/issueLink",
            "source_local_id": row["source_local_id"], "target_local_id": row["target_local_id"],
            "payload_template": {
                "type": {"name": f"{{{{LINK_TYPE:{link_name}}}}}"},
                "outwardIssue": {"key": row["source_jira_key"]},
                "inwardIssue": {"key": row["target_jira_key"]},
            },
            "execution_status": "TEMPLATE_ONLY_REQUIRES_POST_IMPORT_KEY_MAP_AND_LINK_TYPE_DISCOVERY",
        })
    write_jsonl(JIRA_ROOT / "import" / "JIRA_API_LINK_PAYLOADS.jsonl", link_payloads)

    # Keep the reusable template blank even after live Jira reconciliation; store assigned values separately.
    key_map_template = [{
        "local_id": record["local_id"], "import_id": record.get("import_id", ""),
        "jira_key": "", "jira_issue_id": "", "verified": False,
    } for record in ordered]
    write_csv(JIRA_ROOT / "import" / "POST_IMPORT_KEY_MAP_TEMPLATE.csv", key_map_template)
    reconciled_key_map = [{
        "local_id": record["local_id"], "import_id": record.get("import_id", ""),
        "jira_key": record.get("jira_key", ""),
        "jira_issue_id": record.get("operational_jira", {}).get("jira_issue_id", ""),
        "verified": bool(record.get("jira_key")),
        "last_synced_at": record.get("operational_jira", {}).get("last_synced_at", ""),
    } for record in ordered]
    write_csv(
        JIRA_ROOT / "import" / "POST_IMPORT_KEY_MAP.csv",
        reconciled_key_map,
        ["local_id", "import_id", "jira_key", "jira_issue_id", "verified", "last_synced_at"],
    )
    return {
        "issue_rows": len(rows), "link_rows": len(link_rows),
        "create_payloads": len(create_payloads), "link_payloads": len(link_payloads),
    }


def cycles(records: list[dict[str, Any]]) -> list[list[str]]:
    graph = {record["local_id"]: list(record.get("dependencies", [])) for record in records}
    state = {node: 0 for node in graph}
    stack: list[str] = []
    out: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for dependency in graph.get(node, []):
            if dependency not in graph:
                continue
            if state[dependency] == 0:
                visit(dependency)
            elif state[dependency] == 1:
                cycle = stack[stack.index(dependency):] + [dependency]
                key = tuple(sorted(cycle[:-1]))
                if key not in seen:
                    seen.add(key)
                    out.append(cycle)
        stack.pop()
        state[node] = 2

    for node in graph:
        if state[node] == 0:
            visit(node)
    return out


def _source_rows() -> list[dict[str, str]]:
    path = JIRA_ROOT / "sources" / "SOURCE_ANCHOR_INDEX.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _line_excerpt(lines: list[str], start: int, end: int, max_chars: int = 320) -> str:
    text = " ".join(line.strip() for line in lines[max(0, start - 1):min(end, len(lines))] if line.strip())
    return norm_space(text)[:max_chars]


def _heading_ranges(lines: list[str]) -> list[tuple[int, int, str, int]]:
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines, 1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2).strip()))
    ranges: list[tuple[int, int, str, int]] = []
    for position, (start, level, title) in enumerate(headings):
        end = len(lines)
        for next_start, next_level, _ in headings[position + 1:]:
            if next_level <= level:
                end = next_start - 1
                break
        ranges.append((start, end, title, level))
    return ranges


def relocate_source_anchor(row: dict[str, str], lines: list[str]) -> tuple[int, int, str] | None:
    heading = norm_space(row.get("heading", "")).lower()
    if heading:
        for start, end, title, _ in _heading_ranges(lines):
            if heading == norm_space(title).lower() or heading in norm_space(title).lower():
                return start, end, title
    needle = norm_space(row.get("anchor_excerpt", ""))
    if not needle:
        return None
    # Exact single-line relocation first (common for CSV registries).
    for index, line in enumerate(lines, 1):
        if norm_space(line) == needle:
            return index, index, ""
    # Search normalized rolling windows and retain the smallest line range containing the anchor.
    target_len = len(needle)
    for start in range(1, len(lines) + 1):
        chunks: list[str] = []
        for end in range(start, min(len(lines), start + 160) + 1):
            if lines[end - 1].strip():
                chunks.append(lines[end - 1].strip())
            current = norm_space(" ".join(chunks))
            if needle in current:
                return start, end, ""
            if len(current) > target_len + 1200:
                break
    return None


def _update_source_derivatives(updated: dict[str, dict[str, str]]) -> None:
    if not updated:
        return
    for manifest in (JIRA_ROOT / "sources" / "issue_source_manifests").glob("*.json"):
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        changed = False
        for index, ref in enumerate(payload.get("source_refs", [])):
            rid = ref.get("source_ref_id")
            if rid in updated:
                payload["source_refs"][index] = dict(updated[rid])
                for key in ("start_line", "end_line"):
                    payload["source_refs"][index][key] = int(payload["source_refs"][index][key])
                changed = True
        if changed:
            payload["schema_version"] = SCHEMA_VERSION
            manifest.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    for index_name in ["SOURCE_REFERENCE_INDEX.csv"]:
        index_path = JIRA_ROOT / "index" / index_name
        if not index_path.exists():
            continue
        with index_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
            fields = list(handle.fieldnames or [])
        changed = False
        for row in rows:
            rid = row.get("source_ref_id", "")
            if rid in updated:
                for key, value in updated[rid].items():
                    if key in fields:
                        row[key] = value
                changed = True
        if changed:
            write_csv(index_path, rows, fields)


def validate_source_references(*, repair: bool = False) -> tuple[list[str], list[dict[str, Any]], int]:
    errors: list[str] = []
    results: list[dict[str, Any]] = []
    rows = _source_rows()
    if not rows:
        return ["Missing or empty sources/SOURCE_ANCHOR_INDEX.csv"], results, 0
    updated: dict[str, dict[str, str]] = {}
    repaired = 0
    for row in rows:
        rid = row.get("source_ref_id", "")
        rel = row.get("repo_relative_path", "")
        path = project_path(rel)
        result: dict[str, Any] = {"source_ref_id": rid, "path": rel, "valid": False, "status": "UNKNOWN", "relocated": False}
        if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
            errors.append(f"{rid}: noncanonical repository-relative path {rel!r}")
            result["status"] = "INVALID_PATH"
            results.append(result)
            continue
        if not path.exists():
            errors.append(f"{rid}: source missing {rel}")
            result["status"] = "MISSING"
            results.append(result)
            continue
        data = path.read_bytes()
        current_hash = sha256_bytes(data)
        try:
            lines = data.decode("utf-8-sig").splitlines()
        except UnicodeDecodeError:
            lines = []
        try:
            start = int(row.get("start_line", "0"))
            end = int(row.get("end_line", "0"))
        except ValueError:
            start = end = 0
        line_range_valid = bool(lines) and 1 <= start <= end <= len(lines)
        current_excerpt = _line_excerpt(lines, start, end) if line_range_valid else ""
        anchor_hash_valid = bool(current_excerpt) and sha256_text(current_excerpt) == row.get("anchor_hash", "")
        excerpt_valid = bool(current_excerpt) and current_excerpt == row.get("anchor_excerpt", "")
        file_hash_valid = current_hash == row.get("document_sha256", "")
        if file_hash_valid and line_range_valid and anchor_hash_valid and excerpt_valid:
            result.update({"valid": True, "status": "VALID"})
            results.append(result)
            continue

        relocation = relocate_source_anchor(row, lines) if lines else None
        if relocation:
            new_start, new_end, new_heading = relocation
            new_excerpt = _line_excerpt(lines, new_start, new_end)
            result.update({"relocated": True, "relocated_start_line": new_start, "relocated_end_line": new_end})
            if repair:
                row["document_sha256"] = current_hash
                row["start_line"] = str(new_start)
                row["end_line"] = str(new_end)
                row["heading"] = new_heading or row.get("heading", "")
                row["anchor_excerpt"] = new_excerpt
                row["anchor_hash"] = sha256_text(new_excerpt) if new_excerpt else ""
                row["last_verified"] = datetime.now(timezone.utc).date().isoformat()
                updated[rid] = dict(row)
                repaired += 1
                result.update({"valid": True, "status": "REPAIRED"})
            else:
                result["status"] = "RELOCATABLE_DRIFT"
                errors.append(f"{rid}: source/hash/line drift in {rel}; anchor relocates to lines {new_start}-{new_end}; rerun with --repair")
        else:
            result["status"] = "UNRESOLVABLE_DRIFT"
            errors.append(f"{rid}: source/hash/anchor drift cannot be relocated in {rel}")
        results.append(result)
    if repair and updated:
        fields = [
            "source_ref_id", "repo_relative_path", "windows_absolute_path", "document_sha256", "heading",
            "start_line", "end_line", "anchor_excerpt", "anchor_hash", "source_type", "authority_level",
            "why_relevant", "last_verified",
        ]
        write_csv(JIRA_ROOT / "sources" / "SOURCE_ANCHOR_INDEX.csv", rows, fields)
        _update_source_derivatives(updated)
    return errors, results, repaired


def _read_csv_strict(path: Path) -> tuple[list[str], list[dict[str, str]], list[str]]:
    errors: list[str] = []
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [], [], [f"{path.name}: not strict UTF-8: {exc}"]
    if "\x00" in text:
        errors.append(f"{path.name}: contains NUL byte")
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fields = list(reader.fieldnames or [])
    except csv.Error as exc:
        return [], [], [f"{path.name}: CSV parse error: {exc}"]
    return fields, rows, errors


def _walk_adf(node: Any, errors: list[str], context: str) -> None:
    if not isinstance(node, dict):
        errors.append(f"{context}: ADF node is not object")
        return
    node_type = node.get("type")
    allowed = {"doc", "paragraph", "heading", "bulletList", "orderedList", "listItem", "text"}
    if node_type not in allowed:
        errors.append(f"{context}: unsupported ADF node type {node_type!r}")
    if node_type == "text":
        if not isinstance(node.get("text"), str):
            errors.append(f"{context}: ADF text node missing text")
        if str(node.get("text", "")).startswith("## ") or str(node.get("text", "")).startswith("**Local"):
            errors.append(f"{context}: literal Markdown marker embedded in ADF text")
    for child in node.get("content", []) or []:
        _walk_adf(child, errors, context)


def validate_import_files(records: list[dict[str, Any]] | None = None) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    records = records or load_records()
    by_id = {record["local_id"]: record for record in records}
    import_dir = JIRA_ROOT / "import"
    required_files = [
        "JIRA_ISSUES_MASTER.csv", "JIRA_EXTERNAL_SYSTEM_IMPORT.csv", "JIRA_HIERARCHY_STAGE_1.csv",
        "JIRA_HIERARCHY_STAGE_2.csv", "JIRA_HIERARCHY_STAGE_3.csv", "JIRA_LINKS.csv", "JIRA_LINKS.jsonl",
        "JIRA_API_CREATE_PAYLOADS.jsonl", "JIRA_API_LINK_PAYLOADS.jsonl", "POST_IMPORT_KEY_MAP_TEMPLATE.csv",
    ]
    for name in required_files:
        if not (import_dir / name).exists():
            errors.append(f"Missing import artifact {name}")
    if errors:
        return errors, {"issue_rows": 0, "link_rows": 0, "create_payloads": 0, "link_payloads": 0}

    master_fields, master, master_errors = _read_csv_strict(import_dir / "JIRA_ISSUES_MASTER.csv")
    ext_fields, external, ext_errors = _read_csv_strict(import_dir / "JIRA_EXTERNAL_SYSTEM_IMPORT.csv")
    errors.extend(master_errors + ext_errors)
    if master_fields != REQUIRED_IMPORT_FIELDS:
        errors.append(f"JIRA_ISSUES_MASTER.csv headers differ from required ordered schema: {master_fields}")
    if ext_fields != REQUIRED_IMPORT_FIELDS:
        errors.append(f"JIRA_EXTERNAL_SYSTEM_IMPORT.csv headers differ from required ordered schema: {ext_fields}")
    if master != external:
        errors.append("Master and external-system import CSV rows are not identical")
    if len(external) != len(records):
        errors.append(f"External import rows {len(external)} != canonical records {len(records)}")

    local_ids = [row.get("Local Issue ID", "") for row in external]
    issue_ids = [row.get("Issue ID", "") for row in external]
    if len(local_ids) != len(set(local_ids)):
        errors.append("Duplicate Local Issue ID in import CSV")
    if len(issue_ids) != len(set(issue_ids)):
        errors.append("Duplicate Issue ID in import CSV")
    if set(local_ids) != set(by_id):
        errors.append("Import Local Issue ID set differs from canonical record set")
    if any(row.get("Issue key") for row in external):
        errors.append("One or more Jira issue keys were prefilled before destination import/reconciliation")
    if any(not row.get("Summary") for row in external):
        errors.append("Blank Summary in import CSV")
    if any(not str(value).isdigit() for value in issue_ids):
        errors.append("Import Issue ID must be numeric for every row")

    import_id_to_row = {row.get("Issue ID", ""): row for row in external}
    order_index = {row.get("Issue ID", ""): index for index, row in enumerate(external)}
    type_rank = {"Epic": 0, "Story": 1, "Task": 1, "Bug": 1, "Sub-task": 2}
    ranks = [type_rank.get(row.get("Issue type", ""), 99) for row in external]
    if ranks != sorted(ranks):
        errors.append("Import rows are not ordered Epics → standard items → Sub-tasks")
    for row in external:
        parent = row.get("Parent", "")
        if not parent:
            continue
        if parent not in import_id_to_row:
            errors.append(f"{row.get('Local Issue ID')}: Parent import ID {parent} does not exist")
            continue
        if order_index[parent] >= order_index[row.get("Issue ID", "")]:
            errors.append(f"{row.get('Local Issue ID')}: parent row does not precede child")
        parent_type = import_id_to_row[parent].get("Issue type")
        if row.get("Issue type") in {"Story", "Task", "Bug"} and parent_type != "Epic":
            errors.append(f"{row.get('Local Issue ID')}: standard item parent is not Epic")
        if row.get("Issue type") == "Sub-task" and parent_type not in {"Story", "Task", "Bug"}:
            errors.append(f"{row.get('Local Issue ID')}: Sub-task parent type invalid")
        record = by_id.get(row.get("Local Issue ID", ""), {})
        expected_parent = by_id.get(record.get("parent_id", ""), {}).get("import_id", "")
        if str(expected_parent) != parent:
            errors.append(f"{row.get('Local Issue ID')}: Parent value differs from canonical hierarchy")
    required_description_sections = [
        "Objective", "Acceptance Criteria", "Definition of Done", "Required Tests", "Required Evidence", "Stop Conditions", "Source References",
    ]
    for row in external:
        description_text = row.get("Description", "")
        for section in required_description_sections:
            if section not in description_text:
                errors.append(f"{row.get('Local Issue ID')}: import Description missing {section}")

    stage_rows: list[dict[str, str]] = []
    expected_stage_types = [
        ("JIRA_HIERARCHY_STAGE_1.csv", {"Epic"}),
        ("JIRA_HIERARCHY_STAGE_2.csv", {"Story", "Task", "Bug"}),
        ("JIRA_HIERARCHY_STAGE_3.csv", {"Sub-task"}),
    ]
    for name, allowed_types in expected_stage_types:
        fields, rows, csv_errors = _read_csv_strict(import_dir / name)
        errors.extend(csv_errors)
        if fields != REQUIRED_IMPORT_FIELDS:
            errors.append(f"{name}: header mismatch")
        if any(row.get("Issue type") not in allowed_types for row in rows):
            errors.append(f"{name}: contains wrong issue type")
        stage_rows.extend(rows)
    if stage_rows != external:
        errors.append("Concatenated hierarchy stage CSVs do not exactly reproduce ordered master import rows")

    link_fields, link_rows, link_csv_errors = _read_csv_strict(import_dir / "JIRA_LINKS.csv")
    errors.extend(link_csv_errors)
    link_keys: set[tuple[str, str, str]] = set()
    for row in link_rows:
        key = (row.get("source_local_id", ""), row.get("relationship", ""), row.get("target_local_id", ""))
        if key in link_keys:
            errors.append(f"Duplicate link row {key}")
        link_keys.add(key)
        if key[0] not in by_id or key[2] not in by_id:
            errors.append(f"Link endpoint not found {key}")
        if key[1] not in {"BLOCKS", "RELATES_TO"}:
            errors.append(f"Unsupported link relationship {key[1]}")
        if key[1] == "BLOCKS" and key[0] not in by_id.get(key[2], {}).get("dependencies", []):
            errors.append(f"BLOCKS link direction differs from canonical dependency: {key}")
    expected_links = {
        (dependency, "BLOCKS", record["local_id"])
        for record in records for dependency in record.get("dependencies", [])
    } | {
        (record["local_id"], "RELATES_TO", related)
        for record in records for related in record.get("related_to", [])
    }
    if link_keys != expected_links:
        missing = expected_links - link_keys
        extra = link_keys - expected_links
        if missing:
            errors.append(f"Missing canonical links: {len(missing)}")
        if extra:
            errors.append(f"Unexpected links: {len(extra)}")

    def read_jsonl(name: str) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for line_number, line in enumerate((import_dir / name).read_text(encoding="utf-8").splitlines(), 1):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{name}:{line_number}: invalid JSONL: {exc}")
                continue
            if not isinstance(payload, dict):
                errors.append(f"{name}:{line_number}: payload is not object")
                continue
            payloads.append(payload)
        return payloads

    link_json = read_jsonl("JIRA_LINKS.jsonl")
    if link_json != link_rows:
        errors.append("JIRA_LINKS.jsonl does not match JIRA_LINKS.csv")
    creates = read_jsonl("JIRA_API_CREATE_PAYLOADS.jsonl")
    if len(creates) != len(records):
        errors.append(f"API create payload count {len(creates)} != records {len(records)}")
    seen_payload_ids: set[str] = set()
    for entry in creates:
        local_id = entry.get("local_id", "")
        seen_payload_ids.add(local_id)
        if entry.get("method") != "POST" or entry.get("endpoint") != "/rest/api/3/issue":
            errors.append(f"{local_id}: invalid create method/endpoint")
        fields = entry.get("payload_template", {}).get("fields", {})
        if fields.get("project", {}).get("key") != "{{PROJECT_KEY}}":
            errors.append(f"{local_id}: project key placeholder missing")
        if not fields.get("summary"):
            errors.append(f"{local_id}: API summary missing")
        expected_parent = by_id.get(local_id, {}).get("parent_id", "")
        actual_parent = fields.get("parent", {}).get("key", "")
        if expected_parent and actual_parent != f"{{{{JIRA_KEY:{expected_parent}}}}}":
            errors.append(f"{local_id}: API parent placeholder mismatch")
        if not expected_parent and actual_parent:
            errors.append(f"{local_id}: API payload has unexpected parent")
        adf = fields.get("description")
        if not isinstance(adf, dict) or adf.get("type") != "doc" or adf.get("version") != 1:
            errors.append(f"{local_id}: invalid ADF document root")
        else:
            _walk_adf(adf, errors, local_id)
    if seen_payload_ids != set(by_id):
        errors.append("API create payload Local ID set differs from records")

    link_payloads = read_jsonl("JIRA_API_LINK_PAYLOADS.jsonl")
    if len(link_payloads) != len(link_rows):
        errors.append(f"API link payload count {len(link_payloads)} != link rows {len(link_rows)}")
    for entry in link_payloads:
        if entry.get("method") != "POST" or entry.get("endpoint") != "/rest/api/3/issueLink":
            errors.append("Invalid issue-link method/endpoint")
        payload = entry.get("payload_template", {})
        if not payload.get("type", {}).get("name") or not payload.get("outwardIssue", {}).get("key") or not payload.get("inwardIssue", {}).get("key"):
            errors.append("Issue-link payload missing type/outward/inward issue")

    key_fields, key_rows, key_errors = _read_csv_strict(import_dir / "POST_IMPORT_KEY_MAP_TEMPLATE.csv")
    errors.extend(key_errors)
    if len(key_rows) != len(records):
        errors.append("Post-import key-map template row count mismatch")
    if any(row.get("jira_key") or row.get("jira_issue_id") for row in key_rows):
        errors.append("Post-import key-map template contains fabricated destination keys/IDs")
    if {row.get("local_id") for row in key_rows} != set(by_id):
        errors.append("Post-import key-map Local IDs differ from records")

    reconciled_path = import_dir / "POST_IMPORT_KEY_MAP.csv"
    reconciled_fields, reconciled_rows, reconciled_errors = _read_csv_strict(reconciled_path)
    errors.extend(reconciled_errors)
    if len(reconciled_rows) != len(records):
        errors.append("Reconciled post-import key-map row count mismatch")
    if {row.get("local_id") for row in reconciled_rows} != set(by_id):
        errors.append("Reconciled post-import key-map Local IDs differ from records")
    reconciled_by_id = {row.get("local_id"): row for row in reconciled_rows}
    for local_id, record in by_id.items():
        row = reconciled_by_id.get(local_id, {})
        key = row.get("jira_key", "")
        if key and not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", key):
            errors.append(f"Reconciled post-import key-map has invalid Jira key for {local_id}: {key}")
        if key != str(record.get("jira_key", "")):
            errors.append(f"Reconciled post-import key-map disagrees with canonical record for {local_id}")

    metrics = {
        "issue_rows": len(external), "stage_rows": len(stage_rows), "link_rows": len(link_rows),
        "create_payloads": len(creates), "link_payloads": len(link_payloads), "key_map_rows": len(key_rows),
        "reconciled_key_map_rows": len(reconciled_rows),
        "error_count": len(errors), "valid": not errors,
    }
    return errors, metrics


def _validate_traceability(errors: list[str], records: list[dict[str, Any]]) -> None:
    trace_specs = [
        ("governance/REQUIREMENTS_INDEX.csv", "requirement_id", "index/REQUIREMENT_TRACEABILITY.csv", "requirement_id"),
        ("governance/ACCEPTANCE_CONTROL_CATALOG.csv", "control_id", "index/ACCEPTANCE_TRACEABILITY.csv", "control_id"),
        ("governance/ADR_INDEX.csv", "adr_id", "index/ADR_TRACEABILITY.csv", "adr_id"),
        ("docs/final/FINAL_RISK_REGISTER.csv", "risk_id", "reconciliation/RISK_TO_JIRA_MAPPING.csv", "risk_id"),
        ("docs/final/FINAL_KNOWN_GAPS.csv", "gap_id", "reconciliation/GAP_TO_JIRA_MAPPING.csv", "gap_id"),
    ]
    for source_rel, source_field, mapping_rel, mapping_field in trace_specs:
        source_path = project_path(source_rel)
        mapping_path = JIRA_ROOT / mapping_rel
        if not source_path.exists():
            errors.append(f"Missing source registry {source_rel}")
            continue
        if not mapping_path.exists():
            errors.append(f"Missing traceability mapping {mapping_rel}")
            continue
        with source_path.open(encoding="utf-8-sig", newline="") as handle:
            source_ids = {row[source_field] for row in csv.DictReader(handle) if row.get(source_field)}
        with mapping_path.open(encoding="utf-8", newline="") as handle:
            mapping_rows = list(csv.DictReader(handle))
        mapped_ids = {row.get(mapping_field, "") for row in mapping_rows if row.get(mapping_field)}
        missing = source_ids - mapped_ids
        if missing:
            errors.append(f"{mapping_rel}: missing registry IDs {','.join(sorted(missing)[:20])}")
        for row in mapping_rows:
            values = row.get("jira_issue_ids", "") or row.get("post_wave_issue_ids", "") or row.get("jira_issue_id", "")
            if row.get(mapping_field) in source_ids and not values:
                errors.append(f"{mapping_rel}: {row.get(mapping_field)} has no Jira disposition")


def validate(write_reports: bool = True) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    records = load_records()
    ids = [record.get("local_id", "") for record in records]
    by_id = {record.get("local_id", ""): record for record in records}
    if not records:
        errors.append("No canonical issue records found")
    if len(ids) != len(set(ids)):
        errors.append("Duplicate local issue IDs")
    if any(not local_id for local_id in ids):
        errors.append("Blank local issue ID")

    forbidden_generic_scope = {
        "Implement or execute exactly the work described by the title",
        "Produce every declared artifact",
        "Run issue-specific checks and return evidence",
    }
    for record in records:
        local_id = record.get("local_id", "?")
        missing_fields = [field for field in ACTIONABLE_REQUIRED_FIELDS if field not in record]
        if missing_fields:
            errors.append(f"{local_id}: missing fields {missing_fields}")
        if int(record.get("schema_version", 0)) != SCHEMA_VERSION:
            errors.append(f"{local_id}: schema_version is not {SCHEMA_VERSION}")
        parent = record.get("parent_id", "")
        epic = record.get("epic_id", "")
        if parent and parent not in by_id:
            errors.append(f"{local_id}: missing parent {parent}")
        if epic and epic not in by_id:
            errors.append(f"{local_id}: missing Epic {epic}")
        if record.get("issue_type") == "Epic" and parent:
            errors.append(f"{local_id}: Epic must not have parent")
        if record.get("issue_type") == "Story" and by_id.get(parent, {}).get("issue_type") != "Epic":
            errors.append(f"{local_id}: Story parent is not Epic")
        if record.get("issue_type") in {"Task", "Bug"} and parent and by_id.get(parent, {}).get("issue_type") != "Epic":
            errors.append(f"{local_id}: Task/Bug parent is not Epic")
        if record.get("issue_type") == "Subtask" and by_id.get(parent, {}).get("issue_type") not in {"Story", "Task", "Bug"}:
            errors.append(f"{local_id}: Subtask parent invalid")
        for dependency in record.get("dependencies", []):
            if dependency not in by_id:
                errors.append(f"{local_id}: missing dependency {dependency}")
            if dependency == local_id:
                errors.append(f"{local_id}: self dependency")
        expected_inverse = sorted(other["local_id"] for other in records if local_id in other.get("dependencies", []))
        if sorted(record.get("blocks", [])) != expected_inverse:
            errors.append(f"{local_id}: blocks is not exact inverse of dependencies")

        classification = record.get("historical_classification", "")
        if classification == "ACTIONABLE_POST_WAVE":
            for field in [
                "objective", "why_this_exists", "scope", "in_scope", "out_of_scope", "acceptance_criteria",
                "definition_of_done", "required_tests", "required_evidence", "end_to_end_validation",
                "risk_failure_conditions", "stop_conditions", "source_refs", "labels", "component",
                "execution_lane", "execution_mode", "ai_context_notes",
            ]:
                if not record.get(field):
                    errors.append(f"{local_id}: actionable field {field} is blank")
            packet = JIRA_ROOT / "ai" / "work_packets" / f"{local_id}.md"
            if not packet.exists():
                errors.append(f"{local_id}: missing AI work packet")
            mode = record.get("execution_mode")
            if record.get("issue_type") == "Subtask" and mode != "ATOMIC_EXECUTION":
                errors.append(f"{local_id}: post-wave Subtask must be ATOMIC_EXECUTION")
            if record.get("issue_type") in {"Epic", "Story"} and mode != "AGGREGATE_GATE":
                errors.append(f"{local_id}: post-wave Epic/Story must be AGGREGATE_GATE")
            if forbidden_generic_scope & set(record.get("in_scope", [])):
                errors.append(f"{local_id}: retains prohibited generic in-scope boilerplate")
            if record.get("issue_type") == "Subtask" and not record.get("expected_outputs"):
                errors.append(f"{local_id}: executable Subtask has no expected outputs")
        elif not str(record.get("execution_mode", "")).startswith("HISTORICAL"):
            errors.append(f"{local_id}: historical record must use a HISTORICAL execution mode")

        touched = set(record.get("files_expected_to_be_touched", []))
        protected = set(record.get("protected_files_and_interfaces", []))
        overlap = touched & protected
        if overlap:
            errors.append(f"{local_id}: protected/touched overlap {sorted(overlap)}")
        for field in ["files_expected_to_be_read", "files_expected_to_be_touched", "protected_files_and_interfaces"]:
            values = record.get(field, [])
            if len(values) != len(set(values)):
                errors.append(f"{local_id}: duplicate paths in {field}")
            for value in values:
                value_str = str(value)
                if re.match(r"^[A-Za-z]:[\\/]", value_str) or value_str.startswith("/"):
                    errors.append(f"{local_id}: absolute path in {field}: {value_str}")
                if ".." in Path(value_str).parts:
                    errors.append(f"{local_id}: parent traversal in {field}: {value_str}")
        if record.get("jira_key") and not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", str(record.get("jira_key"))):
            errors.append(f"{local_id}: invalid reconciled Jira key format")
        if "W26" in local_id.upper() or str(record.get("owner_wave", "")).upper() in {"W26", "WAVE26", "WAVE_26"}:
            errors.append(f"{local_id}: fabricated Wave 26 identity")
        if record.get("workflow_state") == "DONE" and record.get("evidence_state") not in {"COMPLETE", "VERIFIED"}:
            errors.append(f"{local_id}: Done without complete/verified evidence")
        if record.get("ready"):
            if record.get("issue_type") != "Subtask" or record.get("execution_mode") != "ATOMIC_EXECUTION":
                errors.append(f"{local_id}: non-atomic issue marked READY")
            if record.get("workflow_state") != "READY" or record.get("blocked_reason"):
                errors.append(f"{local_id}: READY metadata inconsistent")
            if "conditional" in record.get("labels", []) or "deferred" in record.get("labels", []):
                errors.append(f"{local_id}: conditional/deferred issue marked READY")
            for dependency in record.get("dependencies", []):
                upstream = by_id.get(dependency, {})
                if upstream.get("workflow_state") != "DONE" or upstream.get("evidence_state") not in {"COMPLETE", "VERIFIED"}:
                    errors.append(f"{local_id}: READY with unsatisfied dependency {dependency}")
        for test in record.get("required_tests", []):
            if not test.get("classification") or not test.get("expectation"):
                errors.append(f"{local_id}: malformed test requirement")
            if test.get("classification") == "EXISTING_AUTOMATED_TEST" and test.get("path") and not project_path(test["path"]).exists():
                errors.append(f"{local_id}: declared existing test missing {test['path']}")
        canonical = project_path(record.get("canonical_record", ""))
        markdown = project_path(record.get("generated_markdown", ""))
        if not canonical.exists():
            errors.append(f"{local_id}: canonical record path missing")
        if not markdown.exists():
            errors.append(f"{local_id}: generated Markdown path missing")

    dependency_cycles = cycles(records)
    if dependency_cycles:
        errors.extend("Dependency cycle: " + " -> ".join(cycle) for cycle in dependency_cycles)

    source_errors, source_results, _ = validate_source_references(repair=False)
    errors.extend(source_errors)
    refs = {row["source_ref_id"]: row for row in _source_rows()}
    for record in records:
        local_id = record["local_id"]
        for rid in record.get("source_refs", []):
            if rid not in refs:
                errors.append(f"{local_id}: unknown source ref {rid}")
        manifest = JIRA_ROOT / "sources" / "issue_source_manifests" / f"{local_id}.json"
        if not manifest.exists():
            errors.append(f"{local_id}: missing source manifest")
        else:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            if payload.get("issue_id") != local_id:
                errors.append(f"{local_id}: source manifest issue_id mismatch")
            manifest_refs = [item.get("source_ref_id") for item in payload.get("source_refs", [])]
            if manifest_refs != record.get("source_refs", []):
                errors.append(f"{local_id}: source manifest refs differ from canonical record")

    _validate_traceability(errors, records)
    import_errors, import_metrics = validate_import_files(records)
    errors.extend(import_errors)

    pycache = [
        path.relative_to(JIRA_ROOT).as_posix() for path in JIRA_ROOT.rglob("*")
        if "__pycache__" in path.parts or path.suffix == ".pyc"
    ]
    if pycache:
        errors.append(f"Python bytecode/cache artifacts present: {len(pycache)}")

    counts = Counter(record.get("issue_type") for record in records)
    states = Counter(record.get("workflow_state") for record in records)
    priorities = Counter(record.get("priority") for record in records)
    modes = Counter(record.get("execution_mode") for record in records)
    metrics: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "valid": not errors,
        "error_count": len(errors), "warning_count": len(warnings), "errors": errors, "warnings": warnings,
        "issue_count": len(records), "issue_types": dict(counts), "workflow_states": dict(states),
        "priorities": dict(priorities), "execution_modes": dict(modes),
        "ready_count": sum(bool(record.get("ready")) for record in records),
        "dependency_cycles": len(dependency_cycles), "source_reference_count": len(refs),
        "valid_source_references": sum(bool(result.get("valid")) for result in source_results),
        "import": import_metrics,
        "work_packet_count": sum(1 for path in (JIRA_ROOT / "ai" / "work_packets").glob("*.md")),
        "protected_touch_overlap_count": sum(
            bool(set(record.get("files_expected_to_be_touched", [])) & set(record.get("protected_files_and_interfaces", [])))
            for record in records
        ),
    }
    if write_reports:
        validation = JIRA_ROOT / "validation"
        validation.mkdir(parents=True, exist_ok=True)
        (validation / "VALIDATION_RESULTS.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        report = [
            "# Jira Pack Validation", "", f"- Result: **{'PASS' if not errors else 'FAIL'}**",
            f"- Issues: {len(records)}", f"- Errors: {len(errors)}", f"- Warnings: {len(warnings)}",
            f"- Dependency cycles: {len(dependency_cycles)}", f"- Source references: {len(refs)}",
            f"- Work packets: {metrics['work_packet_count']}",
            f"- Protected/touched overlaps: {metrics['protected_touch_overlap_count']}",
            f"- Import rows: {import_metrics.get('issue_rows', 0)}", "",
        ]
        if errors:
            report.extend(["## Errors", ""] + [f"- {error}" for error in errors] + [""])
        if warnings:
            report.extend(["## Warnings", ""] + [f"- {warning}" for warning in warnings] + [""])
        (validation / "VALIDATION_REPORT.md").write_text("\n".join(report), encoding="utf-8")
        write_csv(validation / "DEPENDENCY_CYCLE_REPORT.csv", [
            {"cycle_id": index, "cycle": " -> ".join(cycle)} for index, cycle in enumerate(dependency_cycles, 1)
        ])
        write_csv(validation / "ORPHAN_REPORT.csv", [
            {"issue_id": record["local_id"], "missing_parent": record.get("parent_id", "")}
            for record in records if record.get("parent_id") and record.get("parent_id") not in by_id
        ])
        write_csv(validation / "SOURCE_REFERENCE_VALIDATION.csv", source_results)
        write_csv(validation / "HIERARCHY_VALIDATION.csv", [{
            "issue_id": record["local_id"], "issue_type": record["issue_type"],
            "parent_id": record.get("parent_id", ""),
            "valid": not record.get("parent_id") or record.get("parent_id") in by_id,
        } for record in records])
        write_csv(validation / "IMPORT_VALIDATION.csv", [{
            "artifact": "JIRA_EXTERNAL_SYSTEM_IMPORT.csv", "row_count": import_metrics.get("issue_rows", 0),
            "expected": len(records), "valid": not import_errors,
        }])
    return errors, metrics
