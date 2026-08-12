from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROW_RE = re.compile(r"^(BUD|CPU|CTL|CUR|INV|JIR|LOC|OAI|OPS|OR|REV|SCH|SOAK|UTL)-\d{3}$")
EXPECTED_FAMILIES = {
    "BUD": 8, "CPU": 18, "CTL": 22, "CUR": 16, "INV": 13, "JIR": 18,
    "LOC": 22, "OAI": 12, "OPS": 13, "OR": 12, "REV": 10, "SCH": 13,
    "SOAK": 15, "UTL": 12,
}
EXPECTED_PACKAGE_HASHES = {
    "MAIN_SESSION_START_HERE.md": "d1576960f748072350b98925eb4f879a8a4d44237b285f2896e69da44d3403e3",
    "UNIFIED_ASSISTIVE_EXECUTION_ENFORCEMENT_MASTER_DIRECTIVE.md": "7e7d927a3e3a3efd43705a4f2dc64ff9e593cde5085fb271a6276bd8194a1813",
    "OPERATIONAL_ACCEPTANCE_AND_UTILIZATION_MATRIX.md": "bd0142e8df4f25bd0b8733221c232cd3009786aad4f393a71154c9f2ade61111",
    "SECOND_PASS_ASSURANCE_REPORT.md": "935e023ffb73f4d2f44bb4b744d57444af2fe41d80ee31d0c915e1627ac28826",
    "PACKAGE_MANIFEST.json": "9e9e35032c69029b100c85fa15d53beb66cbbee0a6b36641758d97e43588a243",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        type=Path,
        default=ROOT / "configs/unified_assistive_acceptance_ownership.json",
    )
    args = parser.parse_args()
    findings: list[str] = []
    if not args.registry.is_file():
        print("FAIL: acceptance ownership registry missing")
        return 1
    payload = json.loads(args.registry.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    ids = [row.get("id", "") for row in rows]
    if len(rows) != 204:
        findings.append(f"MANDATORY_ROW_COUNT:{len(rows)}")
    if len(ids) != len(set(ids)):
        findings.append("DUPLICATE_ROW_ID")
    if any(not ROW_RE.fullmatch(row_id) for row_id in ids):
        findings.append("INVALID_ROW_ID")
    counts = Counter(row.get("family") for row in rows)
    if dict(sorted(counts.items())) != EXPECTED_FAMILIES:
        findings.append("FAMILY_COUNTS_MISMATCH")
    for row in rows:
        if row.get("mandatory") is not True:
            findings.append(f"ROW_NOT_MANDATORY:{row.get('id')}")
        if not row.get("primary_local_id") or not row.get("primary_jira_key"):
            findings.append(f"ROW_OWNER_MISSING:{row.get('id')}")
        if not all(row.get(name) for name in ("requirement", "exact_acceptance_condition", "required_evidence")):
            findings.append(f"ROW_CONTRACT_INCOMPLETE:{row.get('id')}")
    owners = payload.get("owner_records", {})
    for row in rows:
        owner = owners.get(row.get("primary_local_id"), {})
        if owner.get("jira_key") != row.get("primary_jira_key"):
            findings.append(f"ROW_OWNER_CONFLICT:{row.get('id')}")
    identities = payload.get("package_identities", {})
    for name, digest in EXPECTED_PACKAGE_HASHES.items():
        if identities.get(name, {}).get("sha256") != digest:
            findings.append(f"PACKAGE_IDENTITY_MISMATCH:{name}")
    if payload.get("allowed_results") != ["PASS", "FAIL", "BLOCKED", "INCOMPLETE"]:
        findings.append("RESULT_SEMANTICS_INVALID")
    if payload.get("exit_zero_only_for") != "PASS":
        findings.append("EXIT_SEMANTICS_INVALID")
    if findings:
        print(f"FAIL: {len(findings)} unified acceptance ownership finding(s)")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("PASS: 204 mandatory unified acceptance rows have one canonical/live Jira owner and exact evidence contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
