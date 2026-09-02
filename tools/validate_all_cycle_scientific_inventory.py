"""Validate all-cycle inventory, claim registry, DAG, and trust gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_CYCLES = list(range(1, 26))
ALLOWED_CLASSIFICATIONS = {
    "UNREVIEWED",
    "REPRODUCIBLE_ONLY",
    "INDEPENDENTLY_RECONSTRUCTED_SAME_SPECIFICATION",
    "SEMANTICALLY_AUDITED",
    "CROSS_OUTPUT_COHERENT",
    "EXTERNALLY_BENCHMARKED",
    "FAIL",
    "BLOCKED_INSUFFICIENT_EVIDENCE",
}
HIGH_TRUST = {
    "SEMANTICALLY_AUDITED",
    "CROSS_OUTPUT_COHERENT",
    "EXTERNALLY_BENCHMARKED",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(repo_root: Path) -> list[str]:
    findings: list[str] = []
    base = repo_root / "artifacts" / "scientific_integrity" / "all_cycles"
    inventory_path = base / "ALL_CYCLE_ARTIFACT_INVENTORY.json"
    claims_path = base / "ALL_CYCLE_CLAIM_REGISTRY.json"
    dag_path = base / "ALL_CYCLE_DEPENDENCY_DAG.json"
    matrix_path = base / "ALL_CYCLE_THREE_PASS_AUDIT_MATRIX.json"
    findings_path = base / "ALL_CYCLE_FINDINGS.json"
    fp_path = base / "ALL_CYCLE_FALSE_POSITIVE_REJECTIONS.json"
    successors_path = base / "ALL_CYCLE_AFFECTED_SUCCESSORS.json"
    gate_path = base / "ALL_CYCLE_TRUST_RECOVERY_GATE.json"
    required = [
        inventory_path,
        claims_path,
        dag_path,
        matrix_path,
        findings_path,
        fp_path,
        successors_path,
        gate_path,
    ]
    for path in required:
        if not path.is_file():
            findings.append(f"MISSING:{path.as_posix()}")
    if findings:
        return findings
    inventory = _load(inventory_path)
    claims = _load(claims_path)
    dag = _load(dag_path)
    matrix = _load(matrix_path)
    gate = _load(gate_path)
    cycles = inventory.get("cycles") or []
    cycle_ids = [int(item["cycle_number"]) for item in cycles]
    if cycle_ids != REQUIRED_CYCLES:
        findings.append(f"CYCLE_ENUMERATION_INCOMPLETE:{cycle_ids}")
    for cycle in REQUIRED_CYCLES:
        audit_path = base / f"CYCLE_{cycle:02d}_SCIENTIFIC_AUDIT.json"
        if not audit_path.is_file():
            findings.append(f"MISSING_CYCLE_AUDIT:{cycle:02d}")
    artifacts = inventory.get("artifacts") or []
    if not artifacts:
        findings.append("INVENTORY_EMPTY")
    guessed_cycle_one = [
        item
        for item in artifacts
        if item.get("authority_bearing") is True
        and "DEFAULT" in str(item.get("mapping_note") or "")
    ]
    if guessed_cycle_one:
        findings.append(f"GUESSED_CYCLE_ONE_MAPPING:{len(guessed_cycle_one)}")
    allowed_unmapped_notes = {
        "GIT_FIRST_ADD_NOT_FOUND",
        "GIT_FIRST_ADD_AMBIGUOUS_CYCLE",
        "GIT_FIRST_ADD_BEFORE_CYCLE_1",
        "GIT_FIRST_ADD_AFTER_CYCLE_25",
        "GIT_FIRST_ADD_OUTSIDE_DECLARED_RANGES",
    }
    for item in artifacts:
        note = str(item.get("mapping_note") or "")
        cycle = item.get("originating_cycle")
        if note == "GIT_FIRST_ADD":
            if not isinstance(cycle, int):
                findings.append(f"GIT_FIRST_ADD_WITHOUT_CYCLE:{item.get('path')}")
            continue
        if cycle in (None, "", 0, "UNMAPPED"):
            if note not in allowed_unmapped_notes:
                findings.append(
                    f"UNMAPPED_MAPPING_NOTE_INVALID:{item.get('path')}:{note}"
                )
    unmapped = [
        item
        for item in artifacts
        if item.get("originating_cycle") in (None, "", 0, "UNMAPPED")
        and item.get("authority_bearing") is True
    ]
    recorded_unmapped = inventory.get("unmapped_authority_count")
    if recorded_unmapped != len(unmapped):
        findings.append(
            f"UNMAPPED_COUNT_MISMATCH:{recorded_unmapped}:{len(unmapped)}"
        )
    if unmapped and gate.get("scientific_trust_recovered") is True:
        findings.append(f"UNMAPPED_AUTHORITY_ARTIFACTS:{len(unmapped)}")
    if unmapped and gate.get("inventory_completeness") not in {
        "BLOCKED_INSUFFICIENT_EVIDENCE",
        "INCOMPLETE_UNMAPPED_AUTHORITY",
    }:
        findings.append("UNMAPPED_AUTHORITY_NOT_RECORDED_ON_TRUST_GATE")
    completeness_rule = str(inventory.get("completeness_rule") or "")
    if unmapped and "not that mapping is complete" not in completeness_rule.lower():
        findings.append("COMPLETENESS_RULE_IMPLIES_VALIDATOR_PASS_IS_COMPLETE")
    after_cycle_token = [
        item
        for item in artifacts
        if item.get("mapping_note") == "PATH_TOKEN"
        and str(item.get("path") or "").endswith(
            "POST-TASK-ALL-CYCLE-SCIENTIFIC-CLAIM-REGISTRY-001.json"
        )
    ]
    if after_cycle_token:
        findings.append("PATH_TOKEN_OVERRIDES_AFTER_CYCLE_25_FIRST_ADD")
    protected_token = [
        item
        for item in artifacts
        if item.get("path") == "artifacts/pit/protected_replay_dry_run.json"
        and item.get("mapping_note") == "PATH_TOKEN"
        and item.get("originating_cycle") == 17
    ]
    if protected_token:
        findings.append("PATH_TOKEN_OVERRIDES_UNIQUE_GIT_FIRST_ADD")
    claim_rows = claims.get("claims") or []
    for row in claim_rows:
        classification = row.get("trust_classification")
        if classification not in ALLOWED_CLASSIFICATIONS:
            findings.append(
                f"ILLEGAL_CLAIM_CLASS:{row.get('claim_id')}:{classification}"
            )
        validator_class = row.get("validator_class")
        if (
            classification in HIGH_TRUST
            and validator_class != "INDEPENDENT_SEMANTIC_REFERENCE"
        ):
            findings.append(
                f"HIGH_TRUST_WITHOUT_INDEPENDENT_REFERENCE:{row.get('claim_id')}"
            )
    if not (dag.get("nodes") and dag.get("edges") is not None):
        findings.append("DAG_INCOMPLETE")
    matrix_cycles = {
        int(item["cycle_number"]) for item in matrix.get("cycles") or []
    }
    if matrix_cycles != set(REQUIRED_CYCLES):
        findings.append("THREE_PASS_MATRIX_INCOMPLETE")
    for item in matrix.get("cycles") or []:
        passes = item.get("passes") or {}
        complete = all(
            passes.get(name) in {"COMPLETE", "BLOCKED_INSUFFICIENT_EVIDENCE", "FAIL"}
            for name in ("pass_one", "pass_two", "pass_three")
        )
        if item.get("cycle_disposition") == "SEMANTICALLY_AUDITED" and not complete:
            findings.append(
                f"SEMANTIC_LABEL_BEFORE_THREE_PASSES:{item.get('cycle_number')}"
            )
    if gate.get("scientific_trust_recovered") is True:
        findings.append("TRUST_GATE_MUST_NOT_CLAIM_RECOVERY_WHILE_HOLD_ACTIVE")
    if gate.get("missing_evidence_is_blocked_not_pass") is not True:
        findings.append("TRUST_GATE_MISSING_EVIDENCE_POLICY_INVALID")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    findings = validate(root)
    print(
        json.dumps(
            {
                "validator": "all_cycle_scientific_inventory",
                "result": "PASS" if not findings else "FAIL",
                "finding_count": len(findings),
                "findings": findings,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
