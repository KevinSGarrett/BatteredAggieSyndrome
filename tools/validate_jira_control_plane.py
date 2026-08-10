from __future__ import annotations

"""Validate the canonical local Jira mirror and its live-target binding metadata."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def validate(repo_root: Path, *, require_live: bool = False) -> list[str]:
    repo = repo_root.resolve()
    findings: list[str] = []
    required = [
        "jira/project/JIRA_TARGET_PROFILE.yaml",
        "jira/reconciliation/BAT_LIVE_IMPORT_LEDGER.json",
        "jira/index/READY_QUEUE.csv",
        "jira/index/BLOCKED_QUEUE.csv",
        "jira/history/ISSUE_CHANGE_LOG.jsonl",
        "jira/tools/validate_second_pass.py",
    ]
    for rel in required:
        if not (repo / rel).is_file():
            findings.append(f"missing:{rel}")
    profile_path = repo / "jira/project/JIRA_TARGET_PROFILE.yaml"
    if profile_path.is_file():
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
        except Exception as exc:
            findings.append(f"profile_invalid:{type(exc).__name__}")
            profile = {}
        if profile.get("project_key") != "BAT" or profile.get("jira_base_url") != "https://kevinsgarrett.atlassian.net":
            findings.append("profile_target_mismatch")
        if require_live and (
            profile.get("profile_status") != "LIVE_TARGET_CONFIGURED_AND_VERIFIED"
            or not profile.get("last_live_verification")
            or int(profile.get("live_counts", {}).get("issues", 0)) <= 0
        ):
            findings.append("live_profile_not_verified")
        pending_ids = profile.get("local_sync", {}).get("pending_issue_ids", [])
        if not isinstance(pending_ids, list) or any(not isinstance(item, str) or not item for item in pending_ids):
            findings.append("pending_local_sync_invalid")
        elif pending_ids:
            canonical_by_id = {}
            for record_path in (repo / "jira" / "records" / "issues").rglob("*.json"):
                record = json.loads(record_path.read_text(encoding="utf-8"))
                canonical_by_id[record.get("local_id")] = record
            for local_id in pending_ids:
                record = canonical_by_id.get(local_id)
                if record is None:
                    findings.append(f"pending_local_sync_missing:{local_id}")
                elif record.get("jira_key"):
                    findings.append(f"pending_local_sync_already_bound:{local_id}")
    validator = repo / "jira/tools/validate_second_pass.py"
    if validator.is_file():
        completed = subprocess.run(
            [sys.executable, "-B", str(validator), "--repo-root", str(repo)],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode:
            summary = (completed.stdout + "\n" + completed.stderr).strip().replace("\n", " ")[:1000]
            findings.append(f"second_pass_failed:{completed.returncode}:{summary}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--require-live", action="store_true")
    args = parser.parse_args()
    findings = validate(args.repo_root, require_live=args.require_live)
    result = {"validator": "jira_control_plane", "strict": args.strict, "require_live": args.require_live, "result": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
