"""Validate all-cycle inventory, claim registry, DAG, and trust gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.governance.scientific_dependency_graph import (  # noqa: E402
    circular_authority_from_edges,
    directed_cycles,
)

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
        findings.append(f"UNMAPPED_COUNT_MISMATCH:{recorded_unmapped}:{len(unmapped)}")
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
    path_token_rows = [
        item
        for item in artifacts
        if item.get("mapping_note") == "PATH_TOKEN"
        and item.get("authority_bearing") is True
    ]
    if path_token_rows:
        findings.append(
            f"PATH_TOKEN_STILL_USED_AS_ORIGIN_AUTHORITY:{len(path_token_rows)}"
        )
    census_roots = inventory.get("census_roots") or []
    required_roots = {
        "artifacts",
        "configs",
        "governance",
        "schemas",
        "src/aggie_analytics",
        "tools",
    }
    if set(census_roots) != required_roots:
        findings.append(f"CENSUS_ROOTS_INCOMPLETE:{census_roots}")
    protected_split = [
        item
        for item in artifacts
        if item.get("path") == "governance/PROTECTED_SPLIT_REGISTRY.csv"
    ]
    if not protected_split:
        findings.append("PROTECTED_SPLIT_REGISTRY_NOT_INVENTORIED")
    required_inside_roots = (
        "configs/judging_rule_seal.json",
        "governance/BAS_EVALUATION_PROTOCOL.csv",
        "governance/BAS_ANTI_CIRCULARITY_RULES.csv",
        "artifacts/data_lake/historical_known_at_authority_replay.json",
        "artifacts/data_lake/immutability_and_correction_test.json",
        "schemas/experiments/judging_rule_seal.json",
        "schemas/models/joint_score_distribution.json",
        "src/aggie_analytics/data/week1_2026_forecast_input_binding_successor.py",
        "src/aggie_analytics/validation/protected_split_authority.py",
    )
    inventoried = {item.get("path") for item in artifacts}
    for required in required_inside_roots:
        if required not in inventoried:
            findings.append(f"CENSUS_OMITTED_TOKENLESS_AUTHORITY:{required}")
    producer_row = next(
        (
            item
            for item in artifacts
            if item.get("path")
            == "src/aggie_analytics/data/week1_2026_forecast_input_binding_successor.py"
        ),
        None,
    )
    if producer_row and producer_row.get("scientific_claim_or_role") in {
        None,
        "",
        "NON_SCIENTIFIC_OR_PROCESS",
    }:
        findings.append("SOURCE_MODULE_ROLE_NOT_SCIENTIFIC")
    if (
        "token or filename filters are not inclusion authority"
        not in completeness_rule.lower()
    ):
        findings.append("COMPLETENESS_RULE_STILL_ALLOWS_TOKEN_OMISSION")
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
    else:
        computed_circular = circular_authority_from_edges(dag.get("edges") or [])
        claimed_circular = dag.get("circular_authority") is True
        if computed_circular and not claimed_circular:
            findings.append("DAG_CIRCULAR_AUTHORITY_FALSE_WITH_CYCLE")
        if not computed_circular and claimed_circular:
            findings.append("DAG_CIRCULAR_AUTHORITY_TRUE_WITHOUT_CYCLE")
        if directed_cycles([{"from": "A", "to": "B"}, {"from": "B", "to": "A"}]) == []:
            findings.append("DAG_CYCLE_DETECTOR_FAILED_SELF_CHECK")
    matrix_cycles = {int(item["cycle_number"]) for item in matrix.get("cycles") or []}
    if matrix_cycles != set(REQUIRED_CYCLES):
        findings.append("THREE_PASS_MATRIX_INCOMPLETE")
    allowed_pass_states = {
        "COMPLETE",
        "PARTIAL",
        "BLOCKED_INSUFFICIENT_EVIDENCE",
        "FAIL",
        "NOT_AUDITED_YET",
    }
    for item in matrix.get("cycles") or []:
        passes = item.get("passes") or {}
        for name in ("pass_one", "pass_two", "pass_three"):
            state = passes.get(name)
            if state not in allowed_pass_states:
                findings.append(
                    f"THREE_PASS_STATE_INVALID:{item.get('cycle_number')}:{name}:{state}"
                )
        # Category-search-only pass three cannot be COMPLETE.
        if passes.get("pass_three") == "COMPLETE":
            findings.append(
                f"PASS_THREE_CATEGORY_SEARCH_CANNOT_BE_COMPLETE:{item.get('cycle_number')}"
            )
        complete = all(
            passes.get(name)
            in {"COMPLETE", "PARTIAL", "BLOCKED_INSUFFICIENT_EVIDENCE", "FAIL"}
            for name in ("pass_one", "pass_two", "pass_three")
        )
        if item.get("cycle_disposition") == "SEMANTICALLY_AUDITED" and not complete:
            findings.append(
                f"SEMANTIC_LABEL_BEFORE_THREE_PASSES:{item.get('cycle_number')}"
            )
        if item.get("cycle_disposition") == "SEMANTICALLY_AUDITED" and (
            passes.get("pass_two") in {"BLOCKED_INSUFFICIENT_EVIDENCE", "FAIL", "PARTIAL"}
            or passes.get("pass_three") != "COMPLETE"
        ):
            findings.append(
                f"SEMANTICALLY_AUDITED_WITH_BLOCKED_OR_PARTIAL_PASSES:{item.get('cycle_number')}"
            )
    # Per-cycle audits must not claim COMPLETE pass-three under category-search limitation.
    for cycle in REQUIRED_CYCLES:
        audit_path = base / f"CYCLE_{cycle:02d}_SCIENTIFIC_AUDIT.json"
        if not audit_path.is_file():
            continue
        audit = _load(audit_path)
        p3 = audit.get("pass_three_adversarial") or {}
        limitation = str(p3.get("limitation") or "").lower()
        if p3.get("status") == "COMPLETE" and "category search" in limitation:
            findings.append(f"AUDIT_PASS_THREE_FALSE_COMPLETE:{cycle:02d}")
    if not (claims.get("claims") or []):
        findings.append("CLAIM_REGISTRY_EMPTY")
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
