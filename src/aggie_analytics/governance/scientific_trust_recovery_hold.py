"""Cycle #25.5 operator-hold receipt construction and fail-closed enforcement.

A present release receipt is not permission to merge, Done, or complete. Each
proposed action must match the release digest, hold identity, action class,
owners, and PR/base/head/tree binding. Scientific truth is not operator-waivable.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

HOLD_CONTRACT_RELATIVE = (
    Path("configs") / "scientific_trust_recovery_hold_contract.json"
)
HOLD_RECEIPT_RELATIVE = (
    Path("artifacts") / "scientific_integrity" / "OPERATOR_HOLD_RECEIPT.json"
)
RELEASE_RECEIPT_RELATIVE = (
    Path("artifacts") / "scientific_integrity" / "OPERATOR_RELEASE_RECEIPT.json"
)
AUXILIARY_REGISTRY_RELATIVE = (
    Path("jira") / "reconciliation" / "BAT_AUXILIARY_ISSUE_REGISTRY.json"
)
HOLD_REQUIRED_SNAPSHOT_RELATIVE = (
    Path("jira") / "reconciliation" / "BAT_HOLD_REQUIRED_ISSUE_SNAPSHOT.json"
)
TRUST_GATE_RELATIVE = (
    Path("artifacts")
    / "scientific_integrity"
    / "all_cycles"
    / "ALL_CYCLE_TRUST_RECOVERY_GATE.json"
)
PROGRESS_LEDGER_RELATIVE = (
    Path("jira") / "reconciliation" / "BAT_AUTHORITY_PROGRESS_COMMENT_LEDGER.json"
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
REQUIRED_AUXILIARY_KEYS = HOLD_OWNERS + ("BAT-401", "BAT-429", "BAT-523")
# BAT-688/689/695 were accepted Done before the active hold; do not rewrite that
# history. Remaining scientific owners stay non-Done until explicit release.
PROHIBITED_DONE_OWNERS = (
    "BAT-690",
    "BAT-691",
    "BAT-692",
    "BAT-693",
    "BAT-694",
    "BAT-696",
)
HISTORICALLY_DONE_OWNERS = ("BAT-688", "BAT-689", "BAT-695")
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
PROHIBITED_PARENT_COMMENT_PATTERNS = (
    re.compile(r"cycle\s*#?\s*25\.5\s+bat-523\s+parent[- ]progress", re.I),
    re.compile(r"CYCLE_25_5_BAT-523_PARENT_PROGRESS", re.I),
    re.compile(r"cycle\s*#?\s*26\s+.*parent[- ]progress", re.I),
    re.compile(r"cycle\s*#?\s*26\s+.*parent[- ]completion", re.I),
    re.compile(r"https?://github\.com/[^/\s]+/[^/\s]+/pull/\d+", re.I),
)
KNOWN_ACTION_CLASSES = {
    "merge",
    "done",
    "parent_progress_comment",
    "completion_claim",
    "diagnostic",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RELEASE_IDENTITY_250A80EE = (
    "250a80ee3dd2dc2d3403e32f2d59270733f0cb4955b3e7046c608fde7988fd2c"
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


def _require_bool(value: Any, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field} must be an actual Boolean")
    return value


def _issue_map(repo_root: Path) -> dict[str, dict[str, Any]]:
    registry = load_json(repo_root / AUXILIARY_REGISTRY_RELATIVE)
    issues = {item["jira_key"]: item for item in registry["issues"]}
    snapshot_path = repo_root / HOLD_REQUIRED_SNAPSHOT_RELATIVE
    if snapshot_path.is_file():
        snapshot = load_json(snapshot_path)
        for item in snapshot.get("issues") or []:
            key = item.get("jira_key")
            if isinstance(key, str) and key not in issues:
                issues[key] = item
    return issues


def _scan_paths(repo_root: Path, relative_paths: Sequence[str]) -> list[str]:
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


def _normalize_merge_ref(merge_ref: str) -> dict[str, Any]:
    text = str(merge_ref).strip()
    pr_match = re.search(r"(?:pull/|#)(\d+)", text)
    sha_match = SHA_RE.search(text.lower())
    return {
        "raw": text,
        "pr_number": int(pr_match.group(1)) if pr_match else None,
        "head_sha": sha_match.group(0) if sha_match else None,
        "scientific_prefix": text.lower().startswith("scientific:"),
    }


def _parent_comment_prohibited(text: str) -> bool:
    return any(pattern.search(text) for pattern in PROHIBITED_PARENT_COMMENT_PATTERNS)


def _release_authorizes(
    release: Mapping[str, Any],
    *,
    action: str,
    owners: Sequence[str],
    pr_number: int | None,
    head_sha: str | None,
    base_sha: str | None,
) -> list[str]:
    findings: list[str] = []
    if release.get("release_identity") != RELEASE_IDENTITY_250A80EE:
        findings.append("HOLD_RELEASE_IDENTITY_UNEXPECTED")
    expected_digest = compute_identity(release, "release_identity")
    if release.get("release_identity") != expected_digest:
        findings.append("HOLD_RELEASE_DIGEST_MISMATCH")
    if (
        release.get("hold_receipt_identity")
        != "9c3ecb3091a41d6b4326ed701fccaddff4ed557251cd808d36e381455f6c24cd"
    ):
        findings.append("HOLD_RELEASE_HOLD_IDENTITY_MISMATCH")
    try:
        explicit = _require_bool(
            release.get("explicit_user_authorization"),
            field="explicit_user_authorization",
        )
    except TypeError:
        findings.append("HOLD_RELEASE_AUTHORIZATION_NOT_BOOLEAN")
        explicit = False
    if not explicit:
        findings.append("HOLD_RELEASE_NOT_EXPLICIT")
    if release.get("authorizing_user") != "KevinSGarrett":
        findings.append("HOLD_RELEASE_AUTHORITY_INVALID")
    binding = release.get("authorization_message_binding") or {}
    if not binding.get("instruction_text_sha256") or not binding.get(
        "instruction_pack_sha256"
    ):
        findings.append("AUTHORIZATION_SOURCE_NOT_VERIFIED")
    authorized_actions = {str(item) for item in release.get("authorizes") or []}
    authorized_pr = release.get("scientific_pr")
    if action == "merge":
        if "merge_scientific_successor_prs_sequentially" not in authorized_actions:
            findings.append("HOLD_RELEASE_ACTION_CLASS_MISMATCH")
        if pr_number is None or int(authorized_pr) != int(pr_number):
            findings.append("HOLD_RELEASE_PR_NOT_IN_SCOPE")
        bound_sha = str(release.get("scientific_green_sha_at_issuance") or "")
        if head_sha and bound_sha and head_sha.lower() != bound_sha.lower():
            findings.append("HOLD_RELEASE_HEAD_CHANGED")
        if base_sha and not SHA_RE.fullmatch(str(base_sha).lower()):
            findings.append("HOLD_RELEASE_BASE_SHA_INVALID")
    elif action == "done":
        if (
            "transition_verified_owners_to_done_only_if_acceptance_actually_met"
            not in authorized_actions
        ):
            findings.append("HOLD_RELEASE_ACTION_CLASS_MISMATCH")
        for owner in owners:
            if owner not in PROHIBITED_DONE_OWNERS:
                findings.append(f"HOLD_RELEASE_UNKNOWN_OWNER:{owner}")
        findings.append("HOLD_DONE_REQUIRES_INDEPENDENT_ACCEPTANCE")
    elif action == "parent_progress_comment":
        if (
            "post_exactly_one_factual_bat_523_cycle_25_5_parent_progress_comment"
            not in authorized_actions
        ):
            findings.append("HOLD_RELEASE_ACTION_CLASS_MISMATCH")
        findings.append("HOLD_CYCLE26_PARENT_COMMENT_FORBIDDEN")
    elif action == "completion_claim":
        findings.append("HOLD_COMPLETION_NOT_IN_RELEASE_SCOPE")
    else:
        findings.append(f"HOLD_UNKNOWN_ACTION:{action}")
    return findings


def validate_hold(
    repo_root: Path,
    *,
    proposed_merges: list[str] | None = None,
    proposed_done_keys: list[str] | None = None,
    proposed_parent_comment: str | None = None,
    proposed_completion_claim: str | None = None,
    proposed_action: str | None = None,
    proposed_pr_number: int | None = None,
    proposed_base_sha: str | None = None,
    proposed_head_sha: str | None = None,
    changed_paths: Sequence[str] | None = None,
) -> list[str]:
    """Return findings. Empty list means the active hold is consistent.

    Diagnostic validation (no proposed mutation) may pass while the hold is
    ACTIVE. Authorization of merge/Done/comment/completion requires action
    context and a scoped release matching that exact action.
    """
    findings: list[str] = []
    contract_path = repo_root / HOLD_CONTRACT_RELATIVE
    receipt_path = repo_root / HOLD_RECEIPT_RELATIVE
    gate_path = repo_root / TRUST_GATE_RELATIVE
    if not contract_path.is_file():
        return ["HOLD_CONTRACT_MISSING"]
    if not receipt_path.is_file():
        return ["HOLD_RECEIPT_MISSING"]
    if not gate_path.is_file():
        findings.append("HOLD_TRUST_GATE_MISSING")
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

    mutating = any(
        [
            proposed_merges,
            proposed_done_keys,
            proposed_parent_comment,
            proposed_completion_claim,
        ]
    )
    if mutating and not proposed_action:
        findings.append("HOLD_ACTION_CONTEXT_MISSING")
    if proposed_action is not None and proposed_action not in KNOWN_ACTION_CLASSES:
        findings.append(f"HOLD_UNKNOWN_ACTION:{proposed_action}")
    # An action request is not a diagnostic merely because its payload is absent.
    if proposed_action == "merge":
        if not proposed_merges:
            findings.append("HOLD_MERGE_REFERENCE_MISSING")
        if (
            isinstance(proposed_pr_number, bool)
            or not isinstance(proposed_pr_number, int)
            or proposed_pr_number <= 0
        ):
            findings.append("HOLD_MERGE_PR_CONTEXT_MISSING")
        if not SHA_RE.fullmatch(str(proposed_head_sha or "")):
            findings.append("HOLD_MERGE_HEAD_CONTEXT_MISSING")
        if not SHA_RE.fullmatch(str(proposed_base_sha or "")):
            findings.append("HOLD_MERGE_BASE_CONTEXT_MISSING")
    if proposed_action == "done" and not proposed_done_keys:
        findings.append("HOLD_DONE_OWNER_CONTEXT_MISSING")

    released = release_receipt_present(repo_root)
    release: dict[str, Any] | None = None
    if released:
        release = load_json(repo_root / RELEASE_RECEIPT_RELATIVE)
        try:
            _require_bool(
                release.get("explicit_user_authorization"),
                field="explicit_user_authorization",
            )
        except TypeError:
            findings.append("HOLD_RELEASE_AUTHORIZATION_NOT_BOOLEAN")

    issues = _issue_map(repo_root)
    for key in REQUIRED_AUXILIARY_KEYS:
        if key not in issues:
            findings.append(f"HOLD_AUXILIARY_REGISTRY_MISSING:{key}")
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
        # Receipt presence is not scoped acceptance. No current protected owner
        # may be recorded Done while this hold is active; historical Done owners
        # are already excluded by PROHIBITED_DONE_OWNERS.
        if item.get("status") == "Done":
            findings.append(f"HOLD_DONE_TRANSITION_WHILE_ACTIVE:{key}")
        if item.get("logical_state") == "DONE":
            findings.append(f"HOLD_LOGICAL_DONE_WHILE_ACTIVE:{key}")

    for key in proposed_done_keys or []:
        if key not in PROHIBITED_DONE_OWNERS and key not in issues:
            findings.append(f"HOLD_UNKNOWN_OWNER:{key}")
        if receipt.get("status") == "ACTIVE":
            if not released or release is None:
                findings.append(f"HOLD_PROPOSED_DONE_WHILE_ACTIVE:{key}")
            else:
                findings.extend(
                    _release_authorizes(
                        release,
                        action="done",
                        owners=[key],
                        pr_number=proposed_pr_number,
                        head_sha=proposed_head_sha,
                        base_sha=proposed_base_sha,
                    )
                )

    if proposed_parent_comment:
        if (
            _parent_comment_prohibited(proposed_parent_comment)
            and receipt.get("status") == "ACTIVE"
        ):
            findings.append("HOLD_PROHIBITED_BAT_523_PARENT_PROGRESS_COMMENT")
        if released and release is not None:
            findings.extend(
                _release_authorizes(
                    release,
                    action="parent_progress_comment",
                    owners=["BAT-523"],
                    pr_number=proposed_pr_number,
                    head_sha=proposed_head_sha,
                    base_sha=proposed_base_sha,
                )
            )

    for merge_ref in proposed_merges or []:
        parsed = _normalize_merge_ref(merge_ref)
        if receipt.get("status") == "ACTIVE":
            if not released or release is None:
                findings.append(f"HOLD_SCIENTIFIC_MERGE_WHILE_ACTIVE:{merge_ref}")
            else:
                findings.extend(
                    _release_authorizes(
                        release,
                        action="merge",
                        owners=list(proposed_done_keys or []),
                        pr_number=proposed_pr_number or parsed["pr_number"],
                        head_sha=proposed_head_sha or parsed["head_sha"],
                        base_sha=proposed_base_sha,
                    )
                )

    if proposed_completion_claim and receipt.get("status") == "ACTIVE":
        findings.append("HOLD_COMPLETION_CLAIM_WHILE_ACTIVE")

    ledger_path = repo_root / PROGRESS_LEDGER_RELATIVE
    if ledger_path.is_file():
        ledger = load_json(ledger_path)
        comments = ledger.get("comments") or []
        if not isinstance(comments, list):
            findings.append("HOLD_PROGRESS_LEDGER_MALFORMED")

    incident = receipt.get("cycle25_hold_incident") or {}
    if incident.get("hold_was_implemented") is not False:
        findings.append("HOLD_CYCLE25_INCIDENT_MUST_RECORD_NON_IMPLEMENTATION")
    merged = set(incident.get("merged_prs_despite_intended_hold") or [])
    if merged != {665, 666, 667} and merged != {"665", "666", "667"}:
        try:
            if {int(item) for item in merged} != {665, 666, 667}:
                findings.append("HOLD_CYCLE25_INCIDENT_PR_SET_INCOMPLETE")
        except (TypeError, ValueError):
            findings.append("HOLD_CYCLE25_INCIDENT_PR_SET_INCOMPLETE")

    scan_paths = [
        str(TRUST_GATE_RELATIVE).replace("\\", "/"),
        "artifacts/scientific_integrity/OPERATOR_HOLD_RECEIPT.json",
    ]
    if changed_paths:
        scan_paths.extend(str(path).replace("\\", "/") for path in changed_paths)
    findings.extend(_scan_paths(repo_root, scan_paths))
    if gate_path.is_file():
        gate = load_json(gate_path)
        if gate.get("scientific_trust_recovered") is True:
            findings.append("HOLD_TRUST_GATE_CLAIMS_RECOVERY")
        if gate.get("cycle_25_5_complete") is True:
            findings.append("HOLD_TRUST_GATE_CLAIMS_COMPLETION")
        if gate.get("week1_forecast_credibility") in {
            "CREDIBLE",
            "RECOMMENDED",
            "PRODUCTION",
        }:
            findings.append("HOLD_WEEK1_CREDIBILITY_CLAIM")
    return findings
