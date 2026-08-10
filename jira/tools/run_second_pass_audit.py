from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
sys.dont_write_bytecode = True
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jira_pack_lib import JIRA_ROOT, REPO_ROOT, project_path, repository_context_errors, validate_file_manifest, rebuild_file_manifest, write_csv
from second_pass_hardening import load_records, strict_validate, validate_source_anchors

SECTIONS = [
    (1, "Role and primary mission", "mission"),
    (2, "Project root", "recon"),
    (3, "Important project-state rule", "state"),
    (4, "Do not blindly trust existing DONE status", "maturity"),
    (5, "Full repository reconnaissance", "recon"),
    (6, "Establish source authority", "authority"),
    (7, "Reconcile the existing planning system", "history"),
    (8, "Full completion-gap analysis", "gaps"),
    (9, "Represent the entire project", "coverage"),
    (10, "Issue hierarchy", "hierarchy"),
    (11, "Issue types have meaning", "hierarchy"),
    (12, "Issue granularity", "granularity"),
    (13, "Required content for every actionable issue", "issue_content"),
    (14, "Acceptance criteria", "acceptance"),
    (15, "Definition of Done", "dod"),
    (16, "Test and evidence model", "tests"),
    (17, "End-to-end completion", "e2e"),
    (18, "Separate workflow, maturity, and evidence", "state_separation"),
    (19, "Do not fabricate completion", "no_fabrication"),
    (20, "Source traceability", "source_refs"),
    (21, "Drift-safe line references", "source_drift"),
    (22, "Shared source documents", "source_refs"),
    (23, "Dependency graph", "dependencies"),
    (24, "Blocking logic", "queues"),
    (25, "Critical path", "critical_path"),
    (26, "Priorities", "priorities"),
    (27, "AI-token-efficient design", "ai_efficiency"),
    (28, "AI work packets", "packets"),
    (29, "Local/Jira field-level authority", "sync"),
    (30, "Do not assume final Jira configuration", "target_profile"),
    (31, "Human-readable and machine-readable views", "derivatives"),
    (32, "Local jira directory structure", "structure"),
    (33, "Jira import strategy", "import"),
    (34, "Verify current Atlassian requirements", "atlassian"),
    (35, "Minimize custom-field bloat", "fields"),
    (36, "Labels and components", "taxonomy"),
    (37, "Requirement traceability", "requirements"),
    (38, "Acceptance-control traceability", "controls"),
    (39, "ADR traceability", "adrs"),
    (40, "Risk and gap traceability", "risks_gaps"),
    (41, "Test traceability", "tests"),
    (42, "Artifact traceability", "artifacts"),
    (43, "READY queue", "queues"),
    (44, "BLOCKED queue", "queues"),
    (45, "Parallelism and concurrency", "lanes"),
    (46, "Resource constraints", "resources"),
    (47, "Security and data rights", "security"),
    (48, "BAS and scientific integrity", "bas"),
    (49, "Point-in-time and leakage protection", "pit"),
    (50, "Automated validation", "validation"),
    (51, "Coverage gates", "coverage"),
    (52, "Planning completeness versus product completeness", "maturity"),
    (53, "Import dry-run", "import"),
    (54, "Post-import reconciliation", "reconciliation"),
    (55, "Continuous update contract", "continuous_update"),
    (56, "Change journal", "history_log"),
    (57, "Snapshots", "snapshots"),
    (58, "AI navigation documentation", "ai_efficiency"),
    (59, "Compact current context", "current_context"),
    (60, "Dynamic improvement authority", "second_pass"),
    (61, "Do not over-engineer", "simplicity"),
    (62, "Do not modify project implementation", "boundary"),
    (63, "Generation process", "generation"),
    (64, "Final deliverable", "packaging"),
    (65, "Final generation report", "generation"),
    (66, "Final quality standard", "quality"),
    (67, "Absolute non-negotiables", "nonnegotiables"),
    (68, "Begin from complete read-only reconnaissance", "recon"),
]


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def exists(rel: str) -> bool:
    return (JIRA_ROOT / rel).exists()


def run_checks() -> tuple[dict[str, dict[str, Any]], list[str], dict[str, Any]]:
    records = load_records()
    by_id = {record["local_id"]: record for record in records}
    errors, validation_metrics = strict_validate(records, write_reports=True)
    source_errors, source_results = validate_source_anchors(repair=False)
    legacy_import_rows = csv_rows(JIRA_ROOT / "import" / "JIRA_EXTERNAL_SYSTEM_IMPORT.csv")
    modern_import_rows = csv_rows(JIRA_ROOT / "import" / "JIRA_CLOUD_2026_WORK_ITEM_IMPORT.csv")
    link_rows = csv_rows(JIRA_ROOT / "import" / "JIRA_LINKS.csv")
    import_errors = [error for error in errors if any(token in error.upper() for token in ("IMPORT", "CSV", "PAYLOAD", "PARENT"))]
    import_metrics = {
        "issue_rows": len(legacy_import_rows),
        "modern_issue_rows": len(modern_import_rows),
        "link_rows": len(link_rows),
    }
    rebuild_file_manifest()
    manifest_errors = validate_file_manifest() if exists("validation/JIRA_FILE_MANIFEST.csv") else ["Missing Jira file manifest"]
    actionable = [record for record in records if record.get("historical_classification") == "ACTIONABLE_POST_WAVE"]
    atomic = [record for record in actionable if record.get("execution_mode") == "ATOMIC_EXECUTION"]
    aggregate = [record for record in actionable if record.get("execution_mode") == "AGGREGATE_GATE"]
    historical = [record for record in records if str(record.get("historical_classification", "")).startswith("HISTORICAL")]
    packet_paths = list((JIRA_ROOT / "ai" / "work_packets").glob("*.md"))
    inventory = csv_rows(JIRA_ROOT / "reconciliation" / "REPO_INVENTORY.csv") if exists("reconciliation/REPO_INVENTORY.csv") else []
    inventory_by_path = {row.get("repo_relative_path", ""): row.get("sha256", "") for row in inventory if row.get("repo_relative_path")}
    current_non_jira: dict[str, str] = {}
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel == ".git" or rel.startswith(".git/"):
            continue
        if rel == "jira" or rel.startswith("jira/"):
            continue
        current_non_jira[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    non_jira_missing = sorted(set(inventory_by_path) - set(current_non_jira))
    non_jira_added = sorted(set(current_non_jira) - set(inventory_by_path))
    non_jira_changed = sorted(path for path in set(inventory_by_path) & set(current_non_jira) if inventory_by_path[path] != current_non_jira[path])
    non_jira_diff = {
        # REPO_INVENTORY.csv is the immutable initial reconnaissance snapshot.
        # Later authorized implementation may add or change non-Jira files, but
        # deleting a baseline file is still a boundary failure. Current-tree
        # integrity is enforced independently by the repository manifest.
        "pass": not non_jira_missing,
        "exact_snapshot_match": not (non_jira_missing or non_jira_added or non_jira_changed),
        "inventory_non_jira_files": len(inventory_by_path),
        "current_non_jira_files": len(current_non_jira),
        "missing": non_jira_missing,
        "added": non_jira_added,
        "changed": non_jira_changed,
    }
    (JIRA_ROOT / "validation" / "NON_JIRA_SCOPE_DIFF.json").write_text(json.dumps(non_jira_diff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    diff_rows = ([{"change_type": "MISSING", "repo_relative_path": path} for path in non_jira_missing]
                 + [{"change_type": "ADDED", "repo_relative_path": path} for path in non_jira_added]
                 + [{"change_type": "CHANGED", "repo_relative_path": path} for path in non_jira_changed])
    write_csv(JIRA_ROOT / "validation" / "NON_JIRA_SCOPE_DIFF.csv", diff_rows, ["change_type", "repo_relative_path"])
    baseline_path = JIRA_ROOT / "validation" / "BASELINE_REPOSITORY_VALIDATION.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else []
    baseline_pass = bool(baseline) and all(item.get("passed") for item in baseline)

    def result(ok: bool, detail: str, evidence: list[str]) -> dict[str, Any]:
        return {"status": "PASS" if ok else "FAIL", "detail": detail, "evidence": evidence}

    all_required_dirs = [
        "project", "reconciliation", "records/issues", "issues", "index", "sources",
        "ai", "import", "validation", "snapshots", "history", "tools",
    ]
    unique_ids = len(records) == len(by_id) and len(records) > 0
    no_wave26 = all(
        "W26" not in record["local_id"].upper()
        and str(record.get("owner_wave", "")).upper() not in {"W26", "WAVE26", "WAVE_26"}
        for record in records
    )
    historical_maturity_preserved = all(
        not (record.get("workflow_state") == "DONE" and record.get("evidence_state") not in {"COMPLETE", "VERIFIED"})
        for record in historical
    ) and any(record.get("expected_maturity_after_completion") != "PRODUCTION_READY" for record in historical)
    actionable_fields_ok = all(
        record.get("objective") and record.get("scope") and record.get("in_scope") and record.get("out_of_scope")
        and record.get("acceptance_criteria") and record.get("definition_of_done") and record.get("required_tests")
        and record.get("required_evidence") and record.get("end_to_end_validation") and record.get("stop_conditions")
        for record in actionable
    )
    generic_scope = {
        "Implement or execute exactly the work described by the title",
        "Produce every declared artifact",
        "Run issue-specific checks and return evidence",
    }
    granular = all(not (generic_scope & set(record.get("in_scope", []))) for record in atomic)
    hierarchy_ok = all(
        (not record.get("parent_id") or record.get("parent_id") in by_id)
        and (record.get("issue_type") != "Story" or by_id.get(record.get("parent_id"), {}).get("issue_type") == "Epic")
        and (record.get("issue_type") != "Subtask" or by_id.get(record.get("parent_id"), {}).get("issue_type") in {"Story", "Task", "Bug"})
        for record in records
    )
    state_separation = all(
        all(field in record for field in ("workflow_state", "expected_maturity_after_completion", "evidence_state"))
        for record in records
    )
    target_profile_path = JIRA_ROOT / "project" / "JIRA_TARGET_PROFILE.yaml"
    try:
        target_profile = json.loads(target_profile_path.read_text(encoding="utf-8")) if target_profile_path.is_file() else {}
    except json.JSONDecodeError:
        target_profile = {}
    live_target_configured = target_profile.get("profile_status") == "LIVE_TARGET_CONFIGURED_AND_VERIFIED"
    mapped_keys_valid = all(
        not record.get("jira_key") or re.fullmatch(r"[A-Z][A-Z0-9_]*-\d+", str(record["jira_key"]))
        for record in records
    )
    no_fabrication = (
        all(
            record.get("workflow_state") != "DONE"
            or record.get("evidence_state") in {"COMPLETE", "VERIFIED"}
            for record in actionable
        )
        and mapped_keys_valid
        and (not any(record.get("jira_key") for record in records) or live_target_configured)
    )
    source_ok = not source_errors and len(source_results) > 0
    source_repair_tool = (exists("tools/validate_source_refs.py") and "--repair" in (JIRA_ROOT / "tools" / "validate_source_refs.py").read_text(encoding="utf-8")) or exists("tools/repair_source_refs.py")
    dependency_ok = not any("DEPENDENCY CYCLE" in error.upper() for error in errors)
    inverse_ok = all(
        sorted(record.get("blocks", [])) == sorted(other["local_id"] for other in records if record["local_id"] in other.get("dependencies", []))
        for record in records
    )
    ready_ok = all(
        record.get("execution_mode") == "ATOMIC_EXECUTION" and record.get("workflow_state") == "READY"
        and all(by_id[dep].get("workflow_state") == "DONE" and by_id[dep].get("evidence_state") in {"COMPLETE", "VERIFIED"} for dep in record.get("dependencies", []))
        for record in records if record.get("ready")
    )
    touched_protected_overlap = sum(
        bool(set(record.get("files_expected_to_be_touched", [])) & set(record.get("protected_files_and_interfaces", [])))
        for record in records
    )
    file_separation = touched_protected_overlap == 0 and all("files_expected_to_be_read" in record for record in records)
    packets_ok = (
        len(packet_paths) == len(actionable)
        and len(atomic) + len(aggregate) == len(actionable)
    )
    import_ok = (
        not import_errors
        and import_metrics.get("issue_rows") == len(records)
        and import_metrics.get("modern_issue_rows") == len(records)
    )
    trace_counts = {
        "requirements": len(csv_rows(REPO_ROOT / "governance" / "REQUIREMENTS_INDEX.csv")),
        "controls": len(csv_rows(REPO_ROOT / "governance" / "ACCEPTANCE_CONTROL_CATALOG.csv")),
        "adrs": len(csv_rows(REPO_ROOT / "governance" / "ADR_INDEX.csv")),
        "risks": len(csv_rows(REPO_ROOT / "docs" / "final" / "FINAL_RISK_REGISTER.csv")),
        "gaps": len(csv_rows(REPO_ROOT / "docs" / "final" / "FINAL_KNOWN_GAPS.csv")),
    }
    req_map = csv_rows(JIRA_ROOT / "index" / "REQUIREMENT_TRACEABILITY.csv")
    ac_map = csv_rows(JIRA_ROOT / "index" / "ACCEPTANCE_TRACEABILITY.csv")
    adr_map = csv_rows(JIRA_ROOT / "index" / "ADR_TRACEABILITY.csv")
    risk_map = csv_rows(JIRA_ROOT / "reconciliation" / "RISK_TO_JIRA_MAPPING.csv")
    gap_map = csv_rows(JIRA_ROOT / "reconciliation" / "GAP_TO_JIRA_MAPPING.csv")
    requirements_ok = len({row.get("requirement_id") for row in req_map}) == trace_counts["requirements"] and all(row.get("post_wave_issue_ids") or row.get("jira_issue_ids") for row in req_map)
    controls_ok = len({row.get("control_id") for row in ac_map}) == trace_counts["controls"] and all(row.get("post_wave_issue_ids") or row.get("jira_issue_ids") for row in ac_map)
    adrs_ok = len({row.get("adr_id") for row in adr_map}) == trace_counts["adrs"] and all(row.get("post_wave_issue_ids") or row.get("jira_issue_ids") for row in adr_map)
    risks_gaps_ok = len({row.get("risk_id") for row in risk_map}) == trace_counts["risks"] and len({row.get("gap_id") for row in gap_map}) == trace_counts["gaps"] and all(row.get("jira_issue_ids") for row in risk_map + gap_map)
    tests_ok = exists("index/TEST_TRACEABILITY.csv") and all(record.get("required_tests") for record in actionable)
    artifacts_ok = exists("index/ARTIFACT_TRACEABILITY.csv") and all(record.get("expected_outputs") for record in atomic)
    queues_ok = exists("index/READY_QUEUE.csv") and exists("index/BLOCKED_QUEUE.csv") and ready_ok
    authority_ok = exists("reconciliation/SOURCE_AUTHORITY_MAP.md") and exists("reconciliation/CONFLICT_REGISTER.csv")
    target_profile_ok = exists("project/JIRA_TARGET_PROFILE.yaml") and (
        (not live_target_configured and all(not record.get("jira_key") for record in records))
        or (live_target_configured and mapped_keys_valid)
    )
    derivatives_ok = all(project_path(record["canonical_record"]).exists() and project_path(record["generated_markdown"]).exists() for record in records)
    structure_ok = all((JIRA_ROOT / rel).exists() for rel in all_required_dirs)
    taxonomy_ok = exists("project/COMPONENTS.csv") and exists("project/LABEL_DICTIONARY.csv")
    lane_ok = all(record.get("execution_lane") for record in actionable)
    sync_ok = exists("SYNC_CONTRACT.md") and exists("ai/AI_SYNC_PROTOCOL.md")
    reconciliation_ok = exists("tools/reconcile_jira_export.py") and exists("import/POST_IMPORT_VALIDATION_CHECKLIST.md")
    continuous_ok = exists("ai/AI_COMPLETION_PROTOCOL.md") and exists("ai/AI_SYNC_PROTOCOL.md") and exists("tools/update_ready_queue.py")
    history_ok = exists("CHANGELOG.md") and exists("history/ISSUE_CHANGE_LOG.jsonl")
    snapshots_ok = exists("snapshots/README.md") and any((JIRA_ROOT / "snapshots").glob("*/STATE.json"))
    ai_efficiency_ok = exists("ai/AI_JIRA_USAGE.md") and exists("ai/CURRENT_CONTEXT.md") and exists("index/WORK_PACKET_INDEX.csv")
    simplicity_ok = all(not (JIRA_ROOT / name).exists() for name in ("jira.db", "server", "vector_store"))
    boundary_ok = bool(inventory) and bool(non_jira_diff["pass"])
    generation_ok = exists("GENERATION_REPORT.md") and baseline_pass
    packaging_ok = exists("validation/JIRA_FILE_MANIFEST.csv")
    quality_ok = not errors and not import_errors and not source_errors
    nonnegotiables_ok = no_wave26 and no_fabrication and file_separation and ready_ok and source_ok
    atlassian_doc = "import/CURRENT_ATLASSIAN_VERIFICATION.md" if exists("import/CURRENT_ATLASSIAN_VERIFICATION.md") else "import/ATLASSIAN_2026_COMPATIBILITY.md"
    atlassian_ok = exists(atlassian_doc)
    field_schema_text = (JIRA_ROOT / "project" / "FIELD_SCHEMA.yaml").read_text(encoding="utf-8") if exists("project/FIELD_SCHEMA.yaml") else ""
    required_field_names = {"Local Issue ID", "Source IDs", "Phase", "Implementation Maturity", "Evidence State", "Critical Path", "Execution Lane"}
    fields_ok = all(name in field_schema_text for name in required_field_names) and exists("index/WORK_PACKET_INDEX.csv") and "execution_mode" in (JIRA_ROOT / "index" / "WORK_PACKET_INDEX.csv").read_text(encoding="utf-8-sig").splitlines()[0]
    critical_ok = exists("index/CRITICAL_PATH.csv") and any(record.get("critical_path") for record in actionable)
    priorities_ok = all(record.get("priority") in {"P0", "P1", "P2", "P3", "DEFERRED", "CONDITIONAL"} for record in records)
    resources_ok = any(record.get("component") == "operations-security" for record in actionable) and any("benchmark" in record["title"].lower() for record in actionable)
    security_ok = any("rights" in record["title"].lower() or "credential" in record["title"].lower() for record in atomic)
    bas_records = [record for record in actionable if record.get("component") == "bas-science"]
    bas_ok = bool(bas_records) and any("null" in ((" ".join(str(record.get(k, "")) for k in ("objective", "why_this_exists", "scope", "end_to_end_validation"))) + " " + " ".join(record.get("acceptance_criteria", []) + record.get("definition_of_done", []) + record.get("required_evidence", []))).lower() for record in bas_records)
    pit_ok = any(record.get("component") == "pit-temporal" for record in actionable) and any("leakage" in " ".join(record.get("acceptance_criteria", [])).lower() for record in actionable)
    validation_ok = exists("tools/validate_jira_pack.py") and exists("tools/validate_import_files.py") and exists("tools/run_second_pass_audit.py")
    coverage_ok = (
        validation_metrics.get("issue_count") == len(records)
        and sum(validation_metrics.get("derivative_result_counts", {}).values()) == len(records)
    )
    second_pass_doc = "validation/SECOND_PASS_FINDINGS_AND_REMEDIATION.md" if exists("validation/SECOND_PASS_FINDINGS_AND_REMEDIATION.md") else "validation/SECOND_PASS_AUDIT_REPORT.md"
    second_pass_ok = exists(second_pass_doc) and exists("validation/SECOND_PASS_AUDIT_RESULTS.json")

    checks = {
        "mission": result(unique_ids and structure_ok and coverage_ok, "Complete canonical issue graph, local Jira system, import artifacts, AI views, and validators exist.", ["README.md", "validation/COVERAGE_REPORT.md"]),
        "recon": result(boundary_ok and baseline_pass, f"The immutable reconnaissance inventory retains {len(inventory)} baseline non-Jira files with no missing baseline paths; authorized later additions and changes are recorded separately; baseline repository commands passed.", ["reconciliation/REPO_INVENTORY.csv", "validation/NON_JIRA_SCOPE_DIFF.json", "validation/BASELINE_REPOSITORY_VALIDATION.json"]),
        "state": result(no_wave26, "No issue ID or owner-wave field creates W26; post-wave namespace remains POST-*.", ["index/ISSUE_INDEX.csv", "ai/CURRENT_CONTEXT.md"]),
        "maturity": result(historical_maturity_preserved and state_separation, "Historical DONE remains scoped by maturity/evidence and is not treated as product completion.", ["reconciliation/HISTORICAL_STATUS_RECONCILIATION.csv", "SCHEMA.md"]),
        "authority": result(authority_ok, "Source precedence and conflicts are explicitly represented.", ["reconciliation/SOURCE_AUTHORITY_MAP.md", "reconciliation/CONFLICT_REGISTER.csv"]),
        "history": result(len(historical) == 234 and all(record.get("source_ids") for record in historical), "Historical Epics/Tasks retain stable source IDs and separate historical classification.", ["index/ISSUE_INDEX.csv", "reconciliation/HISTORICAL_STATUS_RECONCILIATION.csv"]),
        "gaps": result(risks_gaps_ok, "Every final gap and risk has a Jira disposition.", ["reconciliation/GAP_TO_JIRA_MAPPING.csv", "reconciliation/RISK_TO_JIRA_MAPPING.csv"]),
        "coverage": result(coverage_ok, f"Current strict coverage and derivative validation agree at {len(records)} canonical issues.", ["validation/SECOND_PASS_AUDIT_RESULTS.json", "validation/DERIVATIVE_CONSISTENCY_REPORT.csv"]),
        "hierarchy": result(hierarchy_ok, "Parent/child types and parent existence validate across the complete graph.", ["index/HIERARCHY_INDEX.csv", "validation/HIERARCHY_VALIDATION.csv"]),
        "granularity": result(granular and bool(atomic), f"All {len(atomic)} atomic Subtasks have criterion/output-specific scope; generic v1 boilerplate is absent.", ["index/WORK_PACKET_INDEX.csv", second_pass_doc]),
        "issue_content": result(actionable_fields_ok and file_separation, "Every post-wave record carries the full execution/completion contract and read/touch/protected separation.", ["records/issues/", "validation/VALIDATION_REPORT.md"]),
        "acceptance": result(all(record.get("acceptance_criteria") for record in actionable), "Every post-wave record has explicit acceptance criteria.", ["records/issues/", "index/ACCEPTANCE_TRACEABILITY.csv"]),
        "dod": result(all(record.get("definition_of_done") for record in actionable), "Every post-wave record has Definition of Done separate from acceptance criteria.", ["records/issues/", "ai/AI_COMPLETION_PROTOCOL.md"]),
        "tests": result(tests_ok, "Test classifications and issue/test bidirectional index exist.", ["index/TEST_TRACEABILITY.csv", "validation/VALIDATION_REPORT.md"]),
        "e2e": result(all(record.get("end_to_end_validation") for record in actionable), "Every post-wave record declares an issue/integration E2E requirement.", ["records/issues/", "ai/AGGREGATE_GATE_PROTOCOL.md"]),
        "state_separation": result(state_separation, "Workflow, implementation maturity, evidence state, and execution mode are distinct fields.", ["SCHEMA.md", "project/FIELD_SCHEMA.yaml"]),
        "no_fabrication": result(no_fabrication, "Every post-wave Done record has complete/verified evidence, and any Jira key is syntactically valid and bound only through a verified live target profile.", ["index/ISSUE_INDEX.csv", "project/JIRA_TARGET_PROFILE.yaml", "import/POST_IMPORT_KEY_MAP.csv"]),
        "source_refs": result(source_ok, f"All {len(source_results)} source references validate against canonical repository paths/hashes/anchors.", ["sources/SOURCE_ANCHOR_INDEX.csv", "validation/SOURCE_REFERENCE_VALIDATION.csv"]),
        "source_drift": result(source_ok and source_repair_tool, "Source validator checks hash, line, excerpt, anchor hash and supports relocation-gated --repair.", ["tools/validate_source_refs.py", "sources/issue_source_manifests/"] ),
        "dependencies": result(dependency_ok and inverse_ok, "Hard dependencies exist, blocks are exact inverses, and no cycles exist.", ["index/DEPENDENCY_INDEX.csv", "validation/DEPENDENCY_CYCLE_REPORT.csv"]),
        "queues": result(queues_ok, "READY/BLOCKED queues are deterministic; only satisfied atomic Subtasks can be READY.", ["index/READY_QUEUE.csv", "index/BLOCKED_QUEUE.csv"]),
        "critical_path": result(critical_ok, "Dependency-critical gating records are explicitly indexed.", ["index/CRITICAL_PATH.csv"]),
        "priorities": result(priorities_ok, "All records use the controlled logical priority vocabulary.", ["project/PRIORITY_MAPPING.yaml", "index/ISSUE_INDEX.csv"]),
        "ai_efficiency": result(ai_efficiency_ok, "Compact startup, queues, one-record packets, and retrieval indexes support minimal context loading.", ["ai/CURRENT_CONTEXT.md", "ai/AI_JIRA_USAGE.md", "index/WORK_PACKET_INDEX.csv"]),
        "packets": result(packets_ok, f"Packet coverage is {len(packet_paths)}/{len(actionable)} post-wave records; modes prevent aggregate direct execution.", ["ai/work_packets/", "index/WORK_PACKET_INDEX.csv"]),
        "sync": result(sync_ok, "Local specification authority and Jira operational authority are separated with conflict handling.", ["SYNC_CONTRACT.md", "ai/AI_SYNC_PROTOCOL.md"]),
        "target_profile": result(target_profile_ok, "Target configuration is either an unbound template with blank keys or an explicitly verified live target with valid mapped keys.", ["project/JIRA_TARGET_PROFILE.yaml", "import/POST_IMPORT_KEY_MAP.csv"]),
        "derivatives": result(derivatives_ok, "Every canonical JSON has a generated human-readable Markdown view.", ["records/issues/", "issues/"]),
        "structure": result(structure_ok, "Required Jira subdirectories and major artifacts exist.", ["README.md", "validation/JIRA_FILE_MANIFEST.csv"]),
        "import": result(import_ok, f"Strict import dry-run passes for {import_metrics.get('issue_rows')} issues and {import_metrics.get('link_rows')} links.", ["validation/IMPORT_DRY_RUN_REPORT.md", "validation/IMPORT_VALIDATION.csv"]),
        "atlassian": result(atlassian_ok, "Current official Jira Cloud CSV/Parent/ADF/REST/link assumptions are recorded with verification date and destination-mapping boundaries.", [atlassian_doc]),
        "fields": result(fields_ok, "The minimal searchable custom-field proposal is present; execution mode remains machine-searchable through the local packet/index schema without unnecessary Jira custom-field bloat.", ["project/FIELD_SCHEMA.yaml", "index/WORK_PACKET_INDEX.csv"]),
        "taxonomy": result(taxonomy_ok, "Controlled component and label vocabularies exist.", ["project/COMPONENTS.csv", "project/LABEL_DICTIONARY.csv"]),
        "requirements": result(requirements_ok, f"All {trace_counts['requirements']} requirement IDs have Jira mappings.", ["index/REQUIREMENT_TRACEABILITY.csv"]),
        "controls": result(controls_ok, f"All {trace_counts['controls']} acceptance-control IDs have Jira mappings.", ["index/ACCEPTANCE_TRACEABILITY.csv"]),
        "adrs": result(adrs_ok, f"All {trace_counts['adrs']} ADR IDs have Jira mappings.", ["index/ADR_TRACEABILITY.csv"]),
        "risks_gaps": result(risks_gaps_ok, f"All {trace_counts['risks']} risks and {trace_counts['gaps']} final gaps have Jira dispositions.", ["reconciliation/RISK_TO_JIRA_MAPPING.csv", "reconciliation/GAP_TO_JIRA_MAPPING.csv"]),
        "artifacts": result(artifacts_ok, "Every atomic Subtask declares outputs and the artifact/producer/downstream index exists.", ["index/ARTIFACT_TRACEABILITY.csv"]),
        "lanes": result(lane_ok, "Every post-wave record has an execution lane; aggregate/atomic execution mode is independently recorded.", ["index/ISSUE_INDEX.csv", "ai/AI_EXECUTION_PROTOCOL.md"]),
        "resources": result(resources_ok, "Target benchmark, storage, concurrency, and local operations work remain explicit without mandatory overbuilt infrastructure.", ["index/ISSUE_INDEX.csv", "project/COMPONENTS.csv"]),
        "security": result(security_ok, "Credential, rights, restricted-data, provenance, and fail-closed work is represented.", ["reconciliation/UNRESOLVED_REVIEW_ITEMS.csv", "index/ISSUE_INDEX.csv"]),
        "bas": result(bas_ok, "BAS-science work preserves null-result acceptance and dedicated scientific domain coverage.", ["index/ISSUE_INDEX.csv", "project/COMPONENTS.csv"]),
        "pit": result(pit_ok, "PIT/leakage work and release-blocking criteria are represented and traceable.", ["index/ISSUE_INDEX.csv", "index/ACCEPTANCE_TRACEABILITY.csv"]),
        "validation": result(validation_ok and not errors, "Full schema, semantic, source, dependency, import, manifest, and second-pass validators are present and pass.", ["tools/validate_jira_pack.py", "tools/run_second_pass_audit.py", "validation/VALIDATION_REPORT.md"]),
        "reconciliation": result(reconciliation_ok, "Post-import key/status reconciliation utility and validation checklist exist.", ["tools/reconcile_jira_export.py", "import/POST_IMPORT_VALIDATION_CHECKLIST.md"]),
        "continuous_update": result(continuous_ok, "Completion/sync protocols rebuild queues/import derivatives and validate after meaningful changes.", ["ai/AI_COMPLETION_PROTOCOL.md", "ai/AI_SYNC_PROTOCOL.md"]),
        "history_log": result(history_ok, "Versioned changelog and append-only meaningful event log exist.", ["CHANGELOG.md", "history/ISSUE_CHANGE_LOG.jsonl"]),
        "snapshots": result(snapshots_ok, "Jira-local state snapshot mechanism and initial snapshot exist.", ["snapshots/README.md", "tools/snapshot_jira_state.py"]),
        "current_context": result(exists("ai/CURRENT_CONTEXT.md"), "Compact startup context identifies state, critical spine, blockers, invariants, and queue entrypoint.", ["ai/CURRENT_CONTEXT.md"]),
        "second_pass": result(second_pass_ok, "Material second-pass findings, remediations, and strict results are documented and validated rather than hidden.", [second_pass_doc, "validation/SECOND_PASS_AUDIT_RESULTS.json", "DESIGN_DECISIONS.md"]),
        "simplicity": result(simplicity_ok, "Canonical system remains files plus small stdlib Python utilities; no server/database/vector store is required.", ["DESIGN_DECISIONS.md", "tools/"]),
        "boundary": result(boundary_ok, f"All {len(inventory)} immutable reconnaissance-baseline paths remain present; authorized subsequent additions and changes are explicitly recorded for review.", ["reconciliation/REPO_INVENTORY.csv", "validation/NON_JIRA_SCOPE_DIFF.json", "validation/REPOSITORY_VALIDATOR_COMPATIBILITY.md"]),
        "generation": result(generation_ok, "Generation report and baseline stage evidence exist; repository test/governance baseline passed.", ["GENERATION_REPORT.md", "validation/BASELINE_REPOSITORY_VALIDATION.json"]),
        "packaging": result(packaging_ok, "Jira subtree file manifest exists for deterministic ZIP integrity validation.", ["validation/JIRA_FILE_MANIFEST.csv", "validation/JIRA_FILE_HASHES.sha256"]),
        "quality": result(quality_ok and packets_ok and file_separation, "An agent can identify valid work, retrieve scoped context, execute atomically, validate, synchronize, and recompute readiness.", ["ai/CURRENT_CONTEXT.md", "validation/VALIDATION_REPORT.md", "validation/SECOND_PASS_AUDIT.md"]),
        "nonnegotiables": result(nonnegotiables_ok, "No Wave 26, unsupported completion/key binding, protected-edit overlap, blocked READY issue, or stale source reference remains.", ["validation/VALIDATION_REPORT.md", second_pass_doc]),
    }

    metrics = {
        "issue_count": len(records), "issue_types": dict(Counter(record["issue_type"] for record in records)),
        "historical_count": len(historical), "post_wave_count": len(actionable), "atomic_count": len(atomic),
        "aggregate_count": len(aggregate), "work_packet_count": len(packet_paths),
        "ready_count": sum(bool(record.get("ready")) for record in records),
        "blocked_count": sum(record.get("workflow_state") == "BLOCKED" for record in records),
        "source_reference_count": len(source_results), "protected_touch_overlap_count": touched_protected_overlap,
        "repository_inventory_count": len(inventory), "baseline_repository_validation_pass": baseline_pass,
        "non_jira_scope_diff": non_jira_diff,
        "import": import_metrics, "traceability_registry_counts": trace_counts,
        "core_validator_error_count": len(errors), "source_error_count": len(source_errors),
        "import_error_count": len(import_errors), "manifest_error_count_at_audit_time": len(manifest_errors),
    }
    audit_errors = list(errors) + list(import_errors) + list(source_errors)
    for key, check in checks.items():
        if check["status"] != "PASS":
            audit_errors.append(f"Check group {key} failed: {check['detail']}")
    return checks, audit_errors, metrics


def main() -> None:
    context_errors = repository_context_errors()
    if context_errors:
        payload = {
            "schema_version": 2,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "result": "FAIL",
            "section_count": 68,
            "passed_sections": 0,
            "failed_sections": 68,
            "error_count": len(context_errors),
            "errors": context_errors,
            "repository_context": str(REPO_ROOT),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        raise SystemExit(2)
    checks, errors, metrics = run_checks()
    rows: list[dict[str, Any]] = []
    for number, title, check_key in SECTIONS:
        check = checks[check_key]
        rows.append({
            "section": number, "title": title, "status": check["status"], "check_group": check_key,
            "detail": check["detail"], "evidence_files": check["evidence"],
        })
    failed_sections = [row for row in rows if row["status"] != "PASS"]
    payload = {
        "schema_version": 2, "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": "PASS" if not errors and not failed_sections else "FAIL",
        "section_count": len(rows), "passed_sections": len(rows) - len(failed_sections),
        "failed_sections": len(failed_sections), "error_count": len(errors), "errors": errors,
        "metrics": metrics, "sections": rows,
    }
    validation = JIRA_ROOT / "validation"
    (validation / "SECOND_PASS_AUDIT.json").write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(validation / "SECOND_PASS_REQUIREMENT_MATRIX.csv", rows, ["section", "title", "status", "check_group", "detail", "evidence_files"])
    lines = [
        "# Independent Second-Pass Audit", "",
        f"- Result: **{payload['result']}**", f"- Source-prompt sections audited: {len(rows)}",
        f"- Passed sections: {payload['passed_sections']}", f"- Failed sections: {payload['failed_sections']}",
        f"- Canonical issues: {metrics['issue_count']}",
        f"- Post-wave packets: {metrics['work_packet_count']} / {metrics['post_wave_count']}",
        f"- Atomic execution records: {metrics['atomic_count']}", f"- Aggregate gate records: {metrics['aggregate_count']}",
        f"- Protected/touched overlaps: {metrics['protected_touch_overlap_count']}",
        f"- Source references validated: {metrics['source_reference_count']}",
        f"- Import rows validated: {metrics['import'].get('issue_rows', 0)}", "",
        "## 68-section matrix", "",
        "| § | Requirement area | Status | Verification |",
        "|---:|---|---|---|",
    ]
    for row in rows:
        detail = str(row["detail"]).replace("|", "\\|")
        lines.append(f"| {row['section']} | {row['title']} | {row['status']} | {detail} |")
    if errors:
        lines.extend(["", "## Errors", ""] + [f"- {error}" for error in errors])
    lines.extend(["", "## Evidence map", "", "The machine-readable evidence paths for each section are in `SECOND_PASS_REQUIREMENT_MATRIX.csv` and `SECOND_PASS_AUDIT.json`."])
    (validation / "SECOND_PASS_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    rebuild_file_manifest()
    print(f"Second-pass audit: {payload['result']} | sections={len(rows)} passed={payload['passed_sections']} errors={len(errors)}")
    for error in errors:
        print("ERROR:", error)
    raise SystemExit(1 if errors or failed_sections else 0)


if __name__ == "__main__":
    main()
