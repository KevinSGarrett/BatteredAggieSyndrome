from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.operations.environment import (  # noqa: E402
    EXTERNAL_OPERATIONAL_RELATIVE_PATHS,
    LOCAL_RUNTIME_RELATIVE_PATHS,
)


EXPECTED_OPERATIONAL_ROOTS = {
    "backups": "backups",
    "packaging": "packaging",
    "reconciliation": "reconciliation",
    "runtime": "runtime",
    "validation": "validation",
    "worktrees": "worktrees",
}
EXPECTED_DISPOSITIONS = {
    "PRESERVE_AUTHORITATIVE",
    "PRESERVE_RECOVERY",
    "ACTIVE_RUNTIME",
    "MOVE_WITH_REFERENCES",
    "DELETE_RECONSTRUCTIBLE",
    "MANUAL_REVIEW_REQUIRED",
}
LEGACY_WORKTREE_ROOT = r"C:\BatteredAggieSyndrome.worktrees"
CANONICAL_WORKTREE_ROOT = r"C:\BatteredAggieSyndrome.data\worktrees"


def validate(root: Path) -> list[str]:
    findings: list[str] = []
    policy = json.loads((root / "configs" / "external_storage_policy.json").read_text(encoding="utf-8"))
    git_policy = json.loads((root / "instructions" / "policies" / "git_policy.json").read_text(encoding="utf-8"))
    if policy.get("standard_operational_roots") != EXPECTED_OPERATIONAL_ROOTS:
        findings.append("external storage policy operational roots differ from the canonical six-root layout")
    if EXTERNAL_OPERATIONAL_RELATIVE_PATHS != EXPECTED_OPERATIONAL_ROOTS:
        findings.append("runtime operational-root resolver differs from the machine policy")
    if LOCAL_RUNTIME_RELATIVE_PATHS.get("backup") != "backups":
        findings.append("future backup alias is not routed to EXTERNAL_DATA_ROOT/backups")
    if set(policy.get("directory_dispositions", [])) != EXPECTED_DISPOSITIONS:
        findings.append("directory disposition vocabulary is incomplete or unexpected")
    if policy.get("bulk_payloads_in_git") is not False:
        findings.append("bulk payload Git boundary is not fail-closed")
    if git_policy.get("worktree_root_windows") != CANONICAL_WORKTREE_ROOT:
        findings.append("Git worktree policy does not use the standardized external root")
    if git_policy.get("worktree_template") != CANONICAL_WORKTREE_ROOT + r"\BAT-123-short-description":
        findings.append("Git worktree template does not use the standardized external root")
    governed_paths = (
        "instructions/START_HERE.md",
        "instructions/10_BRANCH_WORKTREE_AND_COMMIT_POLICY.md",
        "instructions/24_FINAL_VALIDATION_REPORT.md",
        "scripts/new_worktree.ps1",
        "docs/operations/LOCAL_RUNTIME_PATHS.md",
    )
    for relative in governed_paths:
        text = (root / relative).read_text(encoding="utf-8")
        if LEGACY_WORKTREE_ROOT in text:
            findings.append(f"legacy sibling worktree root remains active in {relative}")
    script = (root / "scripts" / "new_worktree.ps1").read_text(encoding="utf-8")
    for required in ("AGGIE_ANALYTICS_DATA_ROOT", 'Join-Path $dataRoot "worktrees"', "git worktree add"):
        if required not in script:
            findings.append(f"new_worktree.ps1 missing enforcement token: {required}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    findings = validate(args.repo_root.resolve())
    if findings:
        print(f"FAIL: {len(findings)} external-storage finding(s)")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("PASS: external storage consolidation and future-path enforcement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
