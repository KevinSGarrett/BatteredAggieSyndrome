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
MATERIAL_PATH_PREFIXES = (
    "src/",
    "tests/",
    "tools/",
    "configs/",
    "artifacts/data_lake/",
    "artifacts/pit/",
    "artifacts/validation/",
)
MATERIAL_PATH_EXACT = {
    "governance/EXPERIMENT_RESULT_EVIDENCE_CONTRACT.csv",
}


def _git_commits(root: Path, revision_range: str) -> list[tuple[str, str]]:
    completed = subprocess.run(
        ["git", "log", "--format=%H%x00%s", revision_range],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git log failed")
    commits: list[tuple[str, str]] = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        commit_sha, separator, subject = line.partition("\x00")
        if not separator:
            raise RuntimeError("git log returned an invalid commit record")
        commits.append((commit_sha, subject.strip()))
    return commits


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


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _git_commit_changed_paths(root: Path, commit_sha: str) -> list[str]:
    completed = subprocess.run(
        ["git", "show", "--name-only", "--pretty=format:", commit_sha],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git show failed")
    paths: list[str] = []
    for raw in completed.stdout.splitlines():
        path = raw.strip().replace("\\", "/")
        if not path:
            continue
        paths.append(path)
    return paths


def _git_commits_unique_to_head(root: Path) -> set[str]:
    completed = subprocess.run(
        ["git", "rev-list", "origin/main..HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git rev-list failed")
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def _touches_material_paths(changed_paths: list[str]) -> bool:
    for path in changed_paths:
        if path in MATERIAL_PATH_EXACT:
            return True
        if any(path.startswith(prefix) for prefix in MATERIAL_PATH_PREFIXES):
            return True
    return False


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
    corrections = classification.get("historical_integration_corrections", [])
    if not isinstance(corrections, list):
        findings.append("COMMIT_CLASSIFICATION_CORRECTIONS_INVALID")
        corrections = []
    correction_shas: set[str] = set()
    for correction in corrections:
        if not isinstance(correction, dict):
            findings.append("COMMIT_CLASSIFICATION_CORRECTION_INVALID")
            continue
        commit_sha = correction.get("commit_sha")
        head_sha = correction.get("head_sha")
        if not isinstance(commit_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
            findings.append("COMMIT_CLASSIFICATION_CORRECTION_SHA_INVALID")
        elif commit_sha in correction_shas:
            findings.append(f"COMMIT_CLASSIFICATION_CORRECTION_DUPLICATE:{commit_sha}")
        else:
            correction_shas.add(commit_sha)
        if not isinstance(head_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", head_sha):
            findings.append("COMMIT_CLASSIFICATION_CORRECTION_HEAD_SHA_INVALID")
        if correction.get("classification") not in {
            classification.get("material_marker"),
            classification.get("process_marker"),
        }:
            findings.append("COMMIT_CLASSIFICATION_CORRECTION_MARKER_INVALID")
        if not isinstance(correction.get("pull_request"), int) or correction["pull_request"] < 1:
            findings.append("COMMIT_CLASSIFICATION_CORRECTION_PR_INVALID")
        if not isinstance(correction.get("reason"), str) or not correction["reason"].strip():
            findings.append("COMMIT_CLASSIFICATION_CORRECTION_REASON_MISSING")

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
        commits = list(reversed(_git_commits(root, f"{baseline}..HEAD")))
    except RuntimeError as exc:
        if not _git_is_shallow(root):
            return [f"EXECUTION_FOCUS_HISTORY_UNAVAILABLE:{exc}"]
        shallow_mode = True
        # Hosted CI intentionally uses a depth-one checkout. Each integration is
        # protected by this validator, so validate the reachable commit there;
        # normal/full clones retain complete baseline-to-HEAD streak validation.
        try:
            commits = list(reversed(_git_commits(root, "HEAD")))
        except RuntimeError as shallow_exc:
            return [f"EXECUTION_FOCUS_SHALLOW_HISTORY_UNAVAILABLE:{shallow_exc}"]

    process_run = 0
    limit = int(classification["max_consecutive_process_only_commits"])
    pr_mode = os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
    enforce_path_classification = shallow_mode or pr_mode or _env_flag(
        "AGGIE_ANALYTICS_ENFORCE_PATH_CLASSIFICATION"
    )
    unique_commits: set[str] = set()
    if enforce_path_classification and pr_mode and not shallow_mode:
        try:
            unique_commits = _git_commits_unique_to_head(root)
        except RuntimeError as exc:
            findings.append(f"EXECUTION_FOCUS_UNIQUE_COMMIT_SET_UNAVAILABLE:{exc}")
            unique_commits = set()
    corrections = {
        row["commit_sha"]: row["classification"].casefold()
        for row in classification.get("historical_integration_corrections", [])
        if isinstance(row, dict)
        and isinstance(row.get("commit_sha"), str)
        and isinstance(row.get("classification"), str)
    }
    for commit_sha, subject in commits:
        if (shallow_mode or os.environ.get("GITHUB_EVENT_NAME") == "pull_request") and re.fullmatch(
            r"Merge [0-9a-f]{40} into [0-9a-f]{40}", subject
        ):
            # GitHub's pull_request checkout synthesizes this depth-one merge
            # commit. The branch-head workflow validates the classified commit;
            # the synthetic test merge is not an integration authored by BAS.
            continue
        lowered = subject.casefold()
        corrected = corrections.get(commit_sha)
        if corrected is not None:
            lowered = corrected
        has_material = material in lowered
        has_process = process in lowered
        if has_material == has_process:
            findings.append(f"COMMIT_CLASSIFICATION_INVALID:{subject}")
            continue
        if enforce_path_classification:
            if pr_mode and not shallow_mode and commit_sha not in unique_commits:
                # PR checks should enforce changed-path classification only for
                # commits introduced by the PR branch, not immutable mainline history.
                pass
            else:
                try:
                    changed_paths = _git_commit_changed_paths(root, commit_sha)
                except RuntimeError as exc:
                    findings.append(f"EXECUTION_FOCUS_CHANGED_PATHS_UNAVAILABLE:{commit_sha}:{exc}")
                    continue
                if has_process and _touches_material_paths(changed_paths):
                    findings.append(f"PROCESS_COMMIT_TOUCHES_MATERIAL_PATHS:{subject}")
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
