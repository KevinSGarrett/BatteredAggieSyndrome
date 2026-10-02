"""Validate the PR review finding ledger."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.governance.scientific_trust_recovery_hold import (  # noqa: E402
    compute_identity,
)

ALLOWED_DISPOSITIONS = {
    "CONFIRMED_FIXED",
    "FALSE_POSITIVE_PROVEN",
    "DUPLICATE",
    "BLOCKED",
    "ACCEPTED_RISK_USER_APPROVED",
    "OPEN",
    "OPEN_CONTAINED",
}
CURSOR_CANNOT_SOLELY_APPROVE = {"FALSE_POSITIVE_PROVEN", "ACCEPTED_RISK_USER_APPROVED"}
PLACEHOLDER_EVIDENCE = {"", "none", "n/a", "null", "tbd", "placeholder"}
P0_P1 = {"P0", "P1"}


def _norm_actor(value: Any) -> str:
    return str(value or "").strip().casefold()


def _is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    return str(value).strip().casefold() in PLACEHOLDER_EVIDENCE


def validate(payload: dict[str, Any], *, require_merge_acceptance: bool = False) -> list[str]:
    findings: list[str] = []
    if "ledger_identity" not in payload:
        findings.append("LEDGER_IDENTITY_MISSING")
    else:
        expected = compute_identity(payload, "ledger_identity")
        if payload.get("ledger_identity") != expected:
            findings.append("LEDGER_IDENTITY_MISMATCH")
    rows = payload.get("findings") or []
    if rows is None:
        findings.append("LEDGER_FINDINGS_NULL")
        rows = []
    if not rows and payload.get("independently_verified_zero_applicable_findings") is not True:
        if require_merge_acceptance:
            findings.append("LEDGER_EMPTY_WITHOUT_ZERO_FINDING_PROOF")
    required = (
        "reviewer",
        "reviewed_sha",
        "finding",
        "severity",
        "affected_files",
        "implementation_response",
        "disposition",
        "evidence",
        "regression_test",
        "follow_up_review_identity",
        "final_authority",
    )
    for index, row in enumerate(rows):
        for field in required:
            if field not in row:
                findings.append(f"LEDGER_MISSING_FIELD:{index}:{field}")
        disposition = row.get("disposition")
        if disposition not in ALLOWED_DISPOSITIONS:
            findings.append(f"LEDGER_ILLEGAL_DISPOSITION:{index}:{disposition}")
        severity = row.get("severity")
        reviewer = _norm_actor(row.get("reviewer"))
        implementer = _norm_actor(row.get("implementing_author") or row.get("implementation_response"))
        adjudicator = _norm_actor(row.get("adjudicator") or row.get("final_authority"))
        authority = _norm_actor(row.get("final_authority"))
        if _is_placeholder(row.get("evidence")) or _is_placeholder(row.get("follow_up_review_identity")):
            findings.append(f"LEDGER_PLACEHOLDER_EVIDENCE:{index}")
        if _is_placeholder(row.get("reviewed_sha")):
            findings.append(f"LEDGER_STALE_OR_NULL_HEAD:{index}")
        if (
            disposition in CURSOR_CANNOT_SOLELY_APPROVE
            and severity in P0_P1
            and reviewer == "cursor"
            and authority == "cursor"
        ):
            findings.append(f"LEDGER_CURSOR_SELF_APPROVAL_FORBIDDEN:{index}")
        if (
            disposition in CURSOR_CANNOT_SOLELY_APPROVE
            and severity in P0_P1
            and implementer
            and adjudicator
            and implementer == adjudicator
        ):
            findings.append(f"LEDGER_AUTHOR_SELF_ADJUDICATION:{index}")
        if (
            require_merge_acceptance
            and severity in P0_P1
            and disposition in {"OPEN", "BLOCKED"}
            and row.get("contained") is not True
        ):
            findings.append(f"LEDGER_UNCONTAINED_P0_P1:{index}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--require-merge-acceptance", action="store_true")
    args = parser.parse_args(argv)
    path = (
        Path(args.repo_root).resolve()
        / "artifacts"
        / "scientific_integrity"
        / "PR_REVIEW_FINDING_LEDGER.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    findings = validate(payload, require_merge_acceptance=args.require_merge_acceptance)
    print(
        json.dumps(
            {
                "validator": "pr_review_finding_ledger",
                "result": "PASS" if not findings else "FAIL",
                "findings": findings,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
