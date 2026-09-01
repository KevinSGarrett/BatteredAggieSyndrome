"""Cycle #25.5 operator-hold receipt construction and fail-closed enforcement."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

HOLD_CONTRACT_RELATIVE = Path("configs") / "scientific_trust_recovery_hold_contract.json"
HOLD_RECEIPT_RELATIVE = Path("artifacts") / "scientific_integrity" / "OPERATOR_HOLD_RECEIPT.json"
RELEASE_RECEIPT_RELATIVE = (
    Path("artifacts") / "scientific_integrity" / "OPERATOR_RELEASE_RECEIPT.json"
)
AUXILIARY_REGISTRY_RELATIVE = (
    Path("jira") / "reconciliation" / "BAT_AUXILIARY_ISSUE_REGISTRY.json"
)
TRUST_GATE_RELATIVE = (
    Path("artifacts")
    / "scientific_integrity"
    / "all_cycles"
    / "ALL_CYCLE_TRUST_RECOVERY_GATE.json"
)
STARTING_SHA = "c1c310da6bcae25641977fe409e3034b8c08010a"
HOLD_OWNERS = (
    "BAT-688",
    "BAT-689",
    "BAT-690",
    "BAT-691",
    "BAT-692",
    "BAT-693",
    "BAT-694",
    "BAT-695",
    "BAT-696",
)
PROHIBITED_DONE_OWNERS = HOLD_OWNERS
FORBIDDEN_CREDIBILITY_TOKENS = (
    "production-ready",
    "production ready",
    "champion selected",
    "bas predicted score",
    "aggie excess effect",
    "cycle #25.5 complete",
    "scientific trust recovered",
    "recommended forecast",
    "credible week 1 forecast",
)
PROHIBITED_PARENT_COMMENT_MARKERS = (
    "CYCLE_25_5_BAT-523_PARENT_PROGRESS",
    "Cycle #25.5 BAT-523 parent-progress",
)


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def compute_identity(payload: Mapping[str, Any], identity_field: str) -> str:
    mutable = dict(payload)
    mutable.pop(identity_field, None)
    return hashlib.sha256(canonical_json(mutable)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def bind_identity(payload: dict[str, Any], identity_field: str) -> dict[str, Any]:
    bound = dict(payload)
    bound[identity_field] = compute_identity(bound, identity_field)
    return bound


def load_contract(repo_root: Path) -> dict[str, Any]:
    return load_json(repo_root / HOLD_CONTRACT_RELATIVE)


def load_receipt(repo_root: Path) -> dict[str, Any]:
    return load_json(repo_root / HOLD_RECEIPT_RELATIVE)


def release_receipt_present(repo_root: Path) -> bool:
    return (repo_root / RELEASE_RECEIPT_RELATIVE).is_file()


def _issue_map(repo_root: Path) -> dict[str, dict[str, Any]]:
    registry = load_json(repo_root / AUXILIARY_REGISTRY_RELATIVE)
    return {item["jira_key"]: item for item in registry["issues"]}


def _scan_text_files(repo_root: Path, relative_paths: list[str]) -> list[str]:
    findings: list[str] = []
    for relative in relative_paths:
        path = repo_root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_CREDIBILITY_TOKENS:
            if token in text:
                findings.append(f"HOLD_CREDIBILITY_CLAIM:{relative}:{token}")
    return findings


def validate_hold(
    repo_root: Path,
    *,
    proposed_merges: list[str] | None = None,
    proposed_done_keys: list[str] | None = None,
    proposed_parent_comment: str | None = None,
    proposed_completion_claim: str | None = None,
) -> list[str]:
    """Return findings. Empty list means the active hold is consistent with local evidence."""
    findings: list[str] = []
    contract_path = repo_root / HOLD_CONTRACT_RELATIVE
    receipt_path = repo_root / HOLD_RECEIPT_RELATIVE
    if not contract_path.is_file():
        return ["HOLD_CONTRACT_MISSING"]
    if not receipt_path.is_file():
        return ["HOLD_RECEIPT_MISSING"]
    contract = load_contract(repo_root)
    receipt = load_receipt(repo_root)
    expected_receipt_identity = compute_identity(receipt, "receipt_identity")
    if receipt.get("receipt_identity") != expected_receipt_identity:
        findings.append("HOLD_RECEIPT_IDENTITY_MISMATCH")
    if receipt.get("status") != "ACTIVE":
        findings.append(f"HOLD_STATUS_NOT_ACTIVE:{receipt.get('status')}")
    if receipt.get("audited_starting_sha") != STARTING_SHA:
        findings.append("HOLD_STARTING_SHA_MISMATCH")
    if contract.get("audited_starting_sha") != STARTING_SHA:
        findings.append("HOLD_CONTRACT_STARTING_SHA_MISMATCH")
    if receipt.get("hold_id") != contract.get("hold_id"):
        findings.append("HOLD_ID_CONTRACT_MISMATCH")
    released = release_receipt_present(repo_root)
    if released:
        release = load_json(repo_root / RELEASE_RECEIPT_RELATIVE)
        if release.get("authorizing_user") != "KevinSGarrett":
            findings.append("HOLD_RELEASE_AUTHORITY_INVALID")
        if not release.get("explicit_user_authorization"):
            findings.append("HOLD_RELEASE_NOT_EXPLICIT")

    issues = _issue_map(repo_root)
    bat_523 = issues.get("BAT-523")
    if not bat_523 or bat_523.get("status") != "In Progress":
        findings.append("HOLD_BAT_523_NOT_IN_PROGRESS")
    bat_401 = issues.get("BAT-401")
    if bat_401 and bat_401.get("status") != "Done":
        findings.append("HOLD_BAT_401_MUST_REMAIN_DONE")
    bat_429 = issues.get("BAT-429")
    if bat_429 and bat_429.get("status") not in {"To Do", "Blocked"}:
        if bat_429.get("status") == "Done":
            findings.append("HOLD_BAT_429_DONE_WITHOUT_PREDECESSOR_ACCEPTANCE")

    for key in PROHIBITED_DONE_OWNERS:
        item = issues.get(key)
        if not item:
            findings.append(f"HOLD_OWNER_MISSING_FROM_REGISTRY:{key}")
            continue
        if item.get("status") == "Done" and not released:
            findings.append(f"HOLD_DONE_TRANSITION_WHILE_ACTIVE:{key}")
        if item.get("logical_state") == "DONE" and not released:
            findings.append(f"HOLD_LOGICAL_DONE_WHILE_ACTIVE:{key}")

    for key in proposed_done_keys or []:
        if key in PROHIBITED_DONE_OWNERS and not released:
            findings.append(f"HOLD_PROPOSED_DONE_WHILE_ACTIVE:{key}")

    for marker in PROHIBITED_PARENT_COMMENT_MARKERS:
        if proposed_parent_comment and marker.lower() in proposed_parent_comment.lower():
            if not released:
                findings.append("HOLD_PROHIBITED_BAT_523_PARENT_PROGRESS_COMMENT")

    for merge_ref in proposed_merges or []:
        if merge_ref.startswith("scientific:") and not released:
            findings.append(f"HOLD_SCIENTIFIC_MERGE_WHILE_ACTIVE:{merge_ref}")

    if proposed_completion_claim and not released:
        findings.append("HOLD_COMPLETION_CLAIM_WHILE_ACTIVE")

    incident = receipt.get("cycle25_hold_incident") or {}
    if incident.get("hold_was_implemented") is not False:
        findings.append("HOLD_CYCLE25_INCIDENT_MUST_RECORD_NON_IMPLEMENTATION")
    merged = set(incident.get("merged_prs_despite_intended_hold") or [])
    if merged != {665, 666, 667} and merged != {"665", "666", "667"}:
        if {int(item) for item in merged} != {665, 666, 667}:
            findings.append("HOLD_CYCLE25_INCIDENT_PR_SET_INCOMPLETE")

    scan_paths = [
        str(TRUST_GATE_RELATIVE).replace("\\", "/"),
        "artifacts/scientific_integrity/OPERATOR_HOLD_RECEIPT.json",
    ]
    findings.extend(_scan_text_files(repo_root, scan_paths))
    gate_path = repo_root / TRUST_GATE_RELATIVE
    if gate_path.is_file():
        gate = load_json(gate_path)
        if gate.get("scientific_trust_recovered") is True:
            findings.append("HOLD_TRUST_GATE_CLAIMS_RECOVERY")
        if gate.get("cycle_25_5_complete") is True and not released:
            findings.append("HOLD_TRUST_GATE_CLAIMS_COMPLETION")
        if gate.get("week1_forecast_credibility") in {
            "CREDIBLE",
            "RECOMMENDED",
            "PRODUCTION",
        }:
            findings.append("HOLD_WEEK1_CREDIBILITY_CLAIM")
    return findings
