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
}
CURSOR_CANNOT_SOLELY_APPROVE = {"FALSE_POSITIVE_PROVEN", "ACCEPTED_RISK_USER_APPROVED"}


def validate(payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if "ledger_identity" in payload:
        expected = compute_identity(payload, "ledger_identity")
        if payload.get("ledger_identity") != expected:
            findings.append("LEDGER_IDENTITY_MISMATCH")
    rows = payload.get("findings") or []
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
        reviewer = row.get("reviewer")
        authority = row.get("final_authority")
        if (
            disposition in CURSOR_CANNOT_SOLELY_APPROVE
            and severity in {"P0", "P1"}
            and reviewer == "Cursor"
            and authority == "Cursor"
        ):
            findings.append(f"LEDGER_CURSOR_SELF_APPROVAL_FORBIDDEN:{index}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    path = (
        Path(args.repo_root).resolve()
        / "artifacts"
        / "scientific_integrity"
        / "PR_REVIEW_FINDING_LEDGER.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    findings = validate(payload)
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
