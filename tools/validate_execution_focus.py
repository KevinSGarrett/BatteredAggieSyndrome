"""Validate the BAS material-progress and integration-focus contract."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "instructions" / "policies" / "execution_focus_policy.json"
INSTRUCTION_PATH = ROOT / "instructions" / "06_TASK_EXECUTION_AND_MEANINGFUL_PROGRESS.md"


def _git_subjects(root: Path, revision_range: str) -> list[str]:
    completed = subprocess.run(
        ["git", "log", "--format=%s", revision_range],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git log failed")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _git_is_shallow(root: Path) -> bool:
    completed = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.returncode == 0 and completed.stdout.strip() == "true"


def _validate_policy(policy: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if policy.get("schema_version") != 2 or policy.get("policy_id") != "BAS-EXECUTION-FOCUS-V1":
        findings.append("EXECUTION_FOCUS_POLICY_IDENTITY_INVALID")
    classification = policy.get("commit_classification", {})
    if classification.get("required_after_effective_commit") is not True:
        findings.append("COMMIT_CLASSIFICATION_NOT_REQUIRED")
    if classification.get("material_marker") != "[material]":
        findings.append("MATERIAL_MARKER_INVALID")
    if classification.get("process_marker") != "[process]":
        findings.append("PROCESS_MARKER_INVALID")
    if classification.get("max_consecutive_process_only_commits") != 1:
        findings.append("PROCESS_ONLY_COMMIT_LIMIT_INVALID")

    integration = policy.get("integration", {})
    required_false = (
        "companion_jira_sync_only_pr_allowed",
        "live_comment_or_operational_status_requires_tracked_mirror_change",
    )
    for key in required_false:
        if integration.get(key) is not False:
            findings.append(f"INTEGRATION_BOOLEAN_MUST_BE_FALSE:{key}")
    if integration.get("one_pr_per_coherent_milestone") is not True:
        findings.append("COHERENT_MILESTONE_PR_RULE_MISSING")
    if integration.get("read_only_live_verification_is_default_when_no_canonical_change") is not True:
        findings.append("READ_ONLY_JIRA_VERIFICATION_NOT_DEFAULT")

    execution = policy.get("execution", {})
    if execution.get("primary_material_lane_limit") != 1:
        findings.append("PRIMARY_MATERIAL_LANE_LIMIT_INVALID")
    if execution.get("default_to_micro_tranches") is not False:
        findings.append("MICRO_TRANCHE_DEFAULT_MUST_BE_FALSE")
    if execution.get("full_suite_at_micro_checkpoint") is not False:
        findings.append("MICRO_CHECKPOINT_FULL_SUITE_MUST_BE_FALSE")
    if execution.get("full_suite_at_pr_readiness_or_material_integration") is not True:
        findings.append("MATERIAL_BOUNDARY_FULL_SUITE_RULE_MISSING")
    if execution.get("housekeeping_requires_direct_unblock_or_safety_reason") is not True:
        findings.append("HOUSEKEEPING_GATE_MISSING")
    if execution.get("new_jira_issue_requires_distinct_independent_definition_of_done") is not True:
        findings.append("JIRA_GRANULARITY_GATE_MISSING")

    reporting = policy.get("reporting", {})
    if reporting.get("material_delta_first") is not True:
        findings.append("MATERIAL_DELTA_FIRST_REPORTING_MISSING")
    if reporting.get("process_activity_must_not_be_reported_as_material_progress") is not True:
        findings.append("PROCESS_ACTIVITY_SEPARATION_MISSING")
    return findings


def _validate_history(root: Path, policy: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    baseline = policy.get("effective_from_commit")
    if not isinstance(baseline, str) or len(baseline) != 40:
        return ["EXECUTION_FOCUS_BASELINE_INVALID"]
    classification = policy["commit_classification"]
    material = classification["material_marker"].casefold()
    process = classification["process_marker"].casefold()
    shallow_mode = False
    try:
        subjects = list(reversed(_git_subjects(root, f"{baseline}..HEAD")))
    except RuntimeError as exc:
        if not _git_is_shallow(root):
            return [f"EXECUTION_FOCUS_HISTORY_UNAVAILABLE:{exc}"]
        shallow_mode = True
        # Hosted CI intentionally uses a depth-one checkout. Each integration is
        # protected by this validator, so validate the reachable commit there;
        # normal/full clones retain complete baseline-to-HEAD streak validation.
        try:
            subjects = list(reversed(_git_subjects(root, "HEAD")))
        except RuntimeError as shallow_exc:
            return [f"EXECUTION_FOCUS_SHALLOW_HISTORY_UNAVAILABLE:{shallow_exc}"]

    process_run = 0
    limit = int(classification["max_consecutive_process_only_commits"])
    for subject in subjects:
        if (shallow_mode or os.environ.get("GITHUB_EVENT_NAME") == "pull_request") and re.fullmatch(
            r"Merge [0-9a-f]{40} into [0-9a-f]{40}", subject
        ):
            # GitHub's pull_request checkout synthesizes this depth-one merge
            # commit. The branch-head workflow validates the classified commit;
            # the synthetic test merge is not an integration authored by BAS.
            continue
        lowered = subject.casefold()
        has_material = material in lowered
        has_process = process in lowered
        if has_material == has_process:
            findings.append(f"COMMIT_CLASSIFICATION_INVALID:{subject}")
            continue
        if has_process:
            process_run += 1
            if process_run > limit:
                findings.append(f"CONSECUTIVE_PROCESS_ONLY_LIMIT_EXCEEDED:{subject}")
        else:
            process_run = 0
    return findings


def validate(root: Path = ROOT) -> list[str]:
    try:
        policy = json.loads((root / POLICY_PATH.relative_to(ROOT)).read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"EXECUTION_FOCUS_POLICY_UNREADABLE:{type(exc).__name__}"]
    findings = _validate_policy(policy)
    instruction = (root / INSTRUCTION_PATH.relative_to(ROOT)).read_text(encoding="utf-8")
    for marker in (
        "## 4.1 Material-milestone interlock",
        "companion Jira-sync-only PR",
        "[material]",
        "[process]",
    ):
        if marker not in instruction:
            findings.append(f"EXECUTION_FOCUS_INSTRUCTION_MARKER_MISSING:{marker}")
    findings.extend(_validate_history(root, policy))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate execution focus and material-progress discipline.")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    findings = validate(args.repo_root.resolve())
    if findings:
        print(f"FAIL: execution focus ({len(findings)} finding(s))")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("PASS: execution focus, process-only streak, and material-progress integration policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
