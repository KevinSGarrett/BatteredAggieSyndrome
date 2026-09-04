"""CONTROL-07 trusted-control bootstrap PREPARATION evaluator.

This pack is not approval. Hosted CI must keep fetching the checker from the
protected base. FAIL/BLOCKED/malformed/empty payloads cannot be accepted.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.governance.normalized_review_gate import (
    evaluate_latest_head_checks,
)

CONTROL_SURFACES = (
    "tools/validate_codex_scientific_review.py",
    ".github/workflows/codex-scientific-review.yml",
    ".github/CODE_REVIEW_RULES.md",
    ".github/codex/prompts/scientific-review.md",
    "schemas/scientific_review/codex_scientific_review.schema.json",
)
PROMPT_PATH = ".github/codex/prompts/scientific-review.md"
RULES_PATH = ".github/CODE_REVIEW_RULES.md"
UNSUCCESSFUL_VERDICTS = frozenset({"FAIL", "BLOCKED", "BLOCKED_INSUFFICIENT_EVIDENCE"})
ACCEPTED_VERDICT = "PASS"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_protocol(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("this_pack_is_not_approval") is not True:
        raise ValueError("protocol must declare this_pack_is_not_approval")
    if payload.get("bootstrap_status") != "PREPARATION_NOT_APPROVED":
        raise ValueError("bootstrap is not approved")
    return payload


def _fail(findings: Sequence[str], *, schema_valid: bool = False) -> dict[str, Any]:
    return {
        "ok": False,
        "accepted": False,
        "schema_valid": schema_valid,
        "findings": list(findings),
    }


def evaluate_review_payload_acceptance(
    payload: Mapping[str, Any] | None,
    *,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Schema-valid FAIL/BLOCKED still fails acceptance."""
    if not payload:
        return _fail(["CODEX_REVIEW_EMPTY"], schema_valid=False)
    if not isinstance(payload, Mapping):
        return _fail(["CODEX_REVIEW_MALFORMED"], schema_valid=False)
    required = (
        "pr_number",
        "base_sha",
        "head_sha",
        "reviewed_merge_sha",
        "verdict",
        "findings_p0",
        "findings_p1",
        "critical_files_not_reviewed",
        "review_rule_identity",
        "model",
        "reasoning_effort",
    )
    missing = [field for field in required if field not in payload]
    if missing:
        return _fail(
            [f"CODEX_REVIEW_MISSING_FIELD:{field}" for field in missing],
            schema_valid=False,
        )
    verdict = payload.get("verdict")
    p0 = payload.get("findings_p0") or []
    p1 = payload.get("findings_p1") or []
    findings: list[str] = []
    if verdict in UNSUCCESSFUL_VERDICTS:
        findings.append(f"CODEX_REVIEW_UNSUCCESSFUL_VERDICT:{verdict}")
    elif verdict != ACCEPTED_VERDICT:
        findings.append(f"CODEX_REVIEW_UNKNOWN_VERDICT:{verdict}")
    if p0 or p1:
        findings.append("CODEX_REVIEW_UNRESOLVED_P0_P1")
    if payload.get("critical_files_not_reviewed"):
        findings.append("CODEX_REVIEW_PASS_WITH_UNREVIEWED_CRITICAL_FILES")
    bindings = protocol.get("bindings") or {}
    model = (bindings.get("model") or {}).get("trusted_value")
    effort = (bindings.get("effort") or {}).get("trusted_value")
    rule = (bindings.get("rules") or {}).get("review_rule_identity")
    if model and payload.get("model") != model:
        findings.append("CODEX_REVIEW_MODEL_NOT_TRUSTED_METADATA")
    if effort and payload.get("reasoning_effort") != effort:
        findings.append("CODEX_REVIEW_EFFORT_NOT_TRUSTED_METADATA")
    if rule and payload.get("review_rule_identity") != rule:
        findings.append("CODEX_REVIEW_RULE_NOT_TRUSTED_METADATA")
    if (
        protocol.get("this_pack_is_not_approval") is True
        and verdict == ACCEPTED_VERDICT
    ):
        if protocol.get("bootstrap_status") != "APPROVED":
            findings.append("TRUSTED_CONTROL_BOOTSTRAP_BOUNDARY_WITHOUT_APPROVAL")
    accepted = not findings and verdict == ACCEPTED_VERDICT
    return {
        "ok": accepted,
        "accepted": accepted,
        "schema_valid": True,
        "findings": findings,
        "verdict": verdict,
    }


def evaluate_missing_sha_and_failed_rerun(
    *,
    head_sha: str,
    checks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    result = evaluate_latest_head_checks(head_sha=head_sha, checks=checks)
    return {
        "ok": bool(result.get("ok")),
        "accepted": bool(result.get("ok")),
        "findings": list(result.get("findings") or []),
        "observed": result.get("observed"),
    }


def evaluate_changed_control_surfaces(
    *,
    protocol: Mapping[str, Any],
    changed_files: Sequence[str],
    approval_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    changed = {item.replace("\\", "/") for item in changed_files}
    findings: list[str] = []
    prompt_or_rules = {PROMPT_PATH, RULES_PATH} & changed
    control_changed = set(CONTROL_SURFACES) & changed
    approved = (
        approval_receipt is not None
        and approval_receipt.get("bootstrap_approved") is True
        and approval_receipt.get("independent_reviewer")
        and approval_receipt.get("author")
        and approval_receipt.get("independent_reviewer")
        != approval_receipt.get("author")
    )
    if prompt_or_rules and not approved:
        findings.append("TRUSTED_CONTROL_RULES_OR_PROMPT_CHANGED")
    if control_changed and not approved:
        findings.append("TRUSTED_CONTROL_BOOTSTRAP_BOUNDARY_WITHOUT_APPROVAL")
    workflow = ".github/workflows/codex-scientific-review.yml"
    if workflow in changed and not approved:
        findings.append("HOSTED_WORKFLOW_MUST_NOT_TRUST_PR_CHECKER")
    if protocol.get("this_pack_is_not_approval") is not True:
        findings.append("PROTOCOL_MISSING_NOT_APPROVAL_FLAG")
    return {
        "ok": not findings,
        "accepted": not findings,
        "findings": findings,
        "changed_control_surfaces": sorted(control_changed),
    }


def evaluate_unreviewed_critical(payload: Mapping[str, Any]) -> dict[str, Any]:
    missing = list(payload.get("critical_files_not_reviewed") or [])
    findings = []
    if missing:
        findings.append("CODEX_REVIEW_PASS_WITH_UNREVIEWED_CRITICAL_FILES")
    if payload.get("verdict") == ACCEPTED_VERDICT and missing:
        findings.append("UNREVIEWED_CRITICAL_BLOCKS_ACCEPTANCE")
    return {
        "ok": not findings,
        "accepted": not findings,
        "findings": findings,
    }


def bind_current_tree(repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root)
    prompt = root / PROMPT_PATH
    schema = root / "schemas/scientific_review/codex_scientific_review.schema.json"
    rules = root / RULES_PATH
    checker = root / "tools/validate_codex_scientific_review.py"
    workflow = root / ".github/workflows/codex-scientific-review.yml"
    bugbot = root / ".cursor/BUGBOT.md"
    return {
        "prompt": {
            "path": PROMPT_PATH,
            "sha256": sha256_file(prompt),
        },
        "schema": {
            "path": "schemas/scientific_review/codex_scientific_review.schema.json",
            "sha256": sha256_file(schema),
        },
        "rules": {
            "path": RULES_PATH,
            "sha256": sha256_file(rules),
            "review_rule_identity": (
                f"{RULES_PATH} sha256:{sha256_file(rules)};"
                f".cursor/BUGBOT.md sha256:{sha256_file(bugbot)}"
            ),
        },
        "checker": {
            "currently_trusted_hosted_source": "PROTECTED_BASE",
            "protected_base_sha": "55e12a5aad3a7e843204fcba619c3cb3d3d6194d",
            "protected_base_checker_sha256": (
                "214d1cde630c3c487dba2fc9ea976c46452f3b224b31de42bf2f4e4e19db37ac"
            ),
            "proposed_successor_path": "tools/validate_codex_scientific_review.py",
            "proposed_successor_sha256": sha256_file(checker),
            "proposed_successor_not_hosted_authority": True,
            "hosted_workflow_fetches_checker_from_protected_base": True,
        },
        "workflow": {
            "path": ".github/workflows/codex-scientific-review.yml",
            "sha256": sha256_file(workflow),
            "must_not_trust_pr_checker": True,
        },
        "model": {
            "required": True,
            "trusted_value": "gpt-5",
            "workflow_currently_supplies_trusted_model": False,
        },
        "effort": {
            "required": True,
            "trusted_value": "high",
            "workflow_currently_supplies_trusted_effort": False,
        },
    }


def build_protocol_artifact(*, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    bindings = bind_current_tree(repo_root)
    return {
        "artifact_type": "CYCLE27_TRUSTED_CONTROL_CHANGE_PROTOCOL",
        "revision": "C27-CONTROL-07-PREPARATION",
        "issued_at_utc": issued_at_utc,
        "this_pack_is_not_approval": True,
        "bootstrap_status": "PREPARATION_NOT_APPROVED",
        "hold": "ACTIVE",
        "merge_authorized": False,
        "do_not_execute_pr_controlled_checker_as_trusted_hosted_authority": True,
        "hosted_workflow_must_continue_fetching_checker_from_protected_base": True,
        "bindings": bindings,
        "fail_closed": {
            "schema_valid_fail_is_not_acceptance": True,
            "schema_valid_blocked_is_not_acceptance": True,
            "malformed_payload_fails": True,
            "empty_payload_fails": True,
            "missing_sha_fails": True,
            "newer_failed_rerun_beats_older_success": True,
            "changed_rules_or_prompt_without_approval_fails": True,
            "unreviewed_critical_fails": True,
            "bootstrap_boundary_without_approval_fails": True,
        },
        "acceptance_requires": [
            "actual verdict PASS",
            "zero unresolved P0/P1",
            "schema valid",
            "exact identity binding",
            "trusted model/effort/rule identity",
            "independent bootstrap approval for control-surface changes",
        ],
        "authorized_future_checker_change_path": {
            "requires_independent_reviewer_separation": True,
            "author_cannot_approve_own_control_change": True,
            "requires_named_bootstrap_approval_receipt": True,
            "this_protocol_is_not_that_receipt": True,
            "changing_github_workflows_to_trust_pr_checker": (
                "FORBIDDEN_UNTIL_BOOTSTRAP_APPROVAL"
            ),
            "independent_reviewer_role": "GitHub independent required reviewer",
            "implementation_author_role": "CYCLE27_CURSOR_AGENT",
        },
        "control_surfaces": list(CONTROL_SURFACES),
        "note": (
            "PREPARATION only. This artifact binds proposed trusted identities "
            "and fail-closed acceptance rules. It does not approve hosted "
            "bootstrap, hold release, or merge."
        ),
    }
