from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
JIRA_ROOT = ROOT / "jira"
ISSUES_CSV = JIRA_ROOT / "import" / "JIRA_ISSUES_MASTER.csv"
RECORDS_ROOT = JIRA_ROOT / "records" / "issues"
AUDIT_CSV = JIRA_ROOT / "validation" / "HISTORICAL_DONE_EVIDENCE_AUDIT.csv"
AUDIT_JSON = JIRA_ROOT / "validation" / "HISTORICAL_DONE_EVIDENCE_AUDIT.json"
POLICY_JSON = JIRA_ROOT / "project" / "HISTORICAL_COMPLETION_ASSURANCE_POLICY.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def concrete_paths(record: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    tick = chr(96)
    for raw in record.get("expected_outputs", []) + record.get("required_evidence", []):
        text = str(raw)
        candidates = re.findall(tick + "([^" + tick + "]+)" + tick, text)
        if not candidates and ("/" in text or re.search(r"\.[A-Za-z0-9]{1,8}$", text)):
            candidates = [text]
        for candidate in candidates:
            value = candidate.strip().replace("\\", "/")
            if not value or value.lower().startswith(("http:", "https:")):
                continue
            if any(character in value for character in "*?{}"):
                continue
            # A slash or a conventional extension is required so symbolic design-output names
            # are not falsely treated as filesystem paths.
            if "/" in value or re.search(r"\.[A-Za-z0-9]{1,8}$", value):
                result.add(value)
    return result


def main() -> int:
    with ISSUES_CSV.open(encoding="utf-8-sig", newline="") as handle:
        done_rows = [row for row in csv.DictReader(handle) if row["Status"] == "Done"]
    done_by_id = {row["Local Issue ID"]: row for row in done_rows}
    records: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in RECORDS_ROOT.rglob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        local_id = record.get("local_id", "")
        if local_id in done_by_id:
            records[local_id] = (path, record)
    if len(done_rows) != 221 or len(records) != 221:
        raise RuntimeError(f"Expected 221 Done rows/records, got rows={len(done_rows)} records={len(records)}")

    audit_rows: list[dict[str, Any]] = []
    all_test_paths: set[str] = set()
    for local_id in sorted(done_by_id):
        source_row = done_by_id[local_id]
        record_path, record = records[local_id]
        manifest_path = str(record.get("evidence_manifest_path", "")).strip()
        manifest_exists = bool(manifest_path) and (ROOT / manifest_path).is_file()
        completion_contract = record.get("completion_evidence_contract") or {}
        required_tests = record.get("required_tests") or []
        test_paths = [str(test.get("path", "")).strip() for test in required_tests if test.get("path")]
        all_test_paths.update(test_paths)
        missing_test_definitions = [path for path in test_paths if not (ROOT / path).is_file()]
        artifact_paths = sorted(concrete_paths(record))
        missing_artifacts = [path for path in artifact_paths if not (ROOT / path).exists()]
        reasons: list[str] = []
        if not completion_contract:
            reasons.append("EMPTY_COMPLETION_EVIDENCE_CONTRACT")
        if not manifest_path:
            reasons.append("NO_EVIDENCE_MANIFEST_DECLARED")
        elif not manifest_exists:
            reasons.append("DECLARED_EVIDENCE_MANIFEST_MISSING")
        if missing_artifacts:
            reasons.append("CONCRETE_REQUIRED_ARTIFACTS_MISSING")
        if missing_test_definitions:
            reasons.append("REQUIRED_TEST_DEFINITIONS_MISSING")
        # A test definition is not a retained passing run. Without a manifest there is no
        # per-issue execution record even when the test file exists.
        if test_paths and not manifest_exists:
            reasons.append("NO_RETAINED_PER_ISSUE_TEST_RESULTS")
        proven_done = not reasons
        audit_rows.append(
            {
                "local_id": local_id,
                "jira_key": source_row["Issue key"],
                "issue_type": source_row["Issue type"],
                "summary": source_row["Summary"],
                "owner_historical_wave": source_row["Owner Historical Wave"],
                "historical_classification": record.get("historical_classification", ""),
                "execution_mode": record.get("execution_mode", ""),
                "implementation_maturity": source_row["Implementation Maturity"],
                "source_evidence_state": source_row["Evidence State"],
                "evidence_manifest_declared": bool(manifest_path),
                "evidence_manifest_exists": manifest_exists,
                "completion_evidence_contract_present": bool(completion_contract),
                "required_evidence_entry_count": len(record.get("required_evidence") or []),
                "concrete_artifact_count": len(artifact_paths),
                "missing_concrete_artifact_count": len(missing_artifacts),
                "missing_concrete_artifacts": ";".join(missing_artifacts),
                "required_test_count": len(test_paths),
                "missing_test_definition_count": len(missing_test_definitions),
                "verdict": "PROVEN_DONE" if proven_done else "NOT_PROVEN_DONE",
                "recommended_jira_status": "Done" if proven_done else "To Do",
                "recommended_operational_evidence_state": "VERIFIED" if proven_done else "PARTIAL",
                "decision_reasons": ";".join(reasons),
            }
        )

    fields = list(audit_rows[0])
    AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(audit_rows)

    verdict_counts = Counter(row["verdict"] for row in audit_rows)
    report = {
        "schema_version": 1,
        "audited_at": utc_now(),
        "result": "PASS",
        "standard": {
            "name": "EVIDENCE_BACKED_OPERATIONAL_DONE_V1",
            "requirements": [
                "A populated completion_evidence_contract defines the exact completion claim.",
                "A declared, existing evidence manifest retains artifact hashes and test/acceptance results.",
                "Every concrete required artifact reference resolves.",
                "Every required test definition exists and its passing run is retained by the evidence manifest.",
            ],
            "historical_status_rule": (
                "Historical WBS completion is preserved as provenance but cannot by itself set the live operational Jira status to Done."
            ),
        },
        "reviewed_issue_count": len(audit_rows),
        "verdict_counts": dict(verdict_counts),
        "source_classification_counts": dict(Counter(row["historical_classification"] for row in audit_rows)),
        "execution_mode_counts": dict(Counter(row["execution_mode"] for row in audit_rows)),
        "maturity_counts": dict(Counter(row["implementation_maturity"] for row in audit_rows)),
        "populated_evidence_manifest_count": sum(row["evidence_manifest_declared"] for row in audit_rows),
        "populated_completion_contract_count": sum(
            row["completion_evidence_contract_present"] for row in audit_rows
        ),
        "issues_with_missing_concrete_artifacts": sum(
            row["missing_concrete_artifact_count"] > 0 for row in audit_rows
        ),
        "unique_required_test_paths": len(all_test_paths),
        "missing_required_test_definition_paths": sorted(
            path for path in all_test_paths if not (ROOT / path).is_file()
        ),
        "audit_csv": str(AUDIT_CSV.relative_to(ROOT)),
    }
    write_json(AUDIT_JSON, report)

    unproven_ids = [row["local_id"] for row in audit_rows if row["verdict"] == "NOT_PROVEN_DONE"]
    policy = {
        "schema_version": 1,
        "created_at": report["audited_at"],
        "standard": report["standard"]["name"],
        "purpose": "Keep historical source completion provenance separate from live operational completion assurance.",
        "jira_operational_override": {
            "status": "To Do",
            "evidence_state": "PARTIAL",
            "add_labels": ["completion-not-proven", "historical-traceability-only"],
        },
        "preserve": [
            "Canonical historical workflow state and original WBS provenance",
            "Historical classification, wave, maturity scope, source references, and post-wave mappings",
        ],
        "issue_count": len(unproven_ids),
        "local_issue_ids": unproven_ids,
        "audit_json": str(AUDIT_JSON.relative_to(ROOT)),
        "audit_csv": str(AUDIT_CSV.relative_to(ROOT)),
    }
    write_json(POLICY_JSON, policy)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
