from __future__ import annotations

"""Produce a redacted, read-only audit of repository, Git, Jira, and instruction identity."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

sys.dont_write_bytecode = True


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run(repo: Path, args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(args, cwd=repo, text=True, capture_output=True, check=False)
    text = completed.stdout.strip()
    return {"exit_code": completed.returncode, "stdout": text[:20000], "stderr_type": "PRESENT" if completed.stderr.strip() else "NONE"}


def _sanitize_url(value: str) -> str:
    value = value.strip()
    if not value:
        return value
    if re.match(r"^[^@\s]+@[^:]+:.+$", value):
        return re.sub(r"^[^@\s]+@", "", value)
    try:
        parts = urlsplit(value)
    except ValueError:
        return "REDACTED_INVALID_URL"
    host = parts.hostname or ""
    if parts.port:
        host += f":{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


def _env_aliases(repo: Path) -> dict[str, str]:
    names = {"CFBD_API_KEY", "JIRA_API_KEY", "JIRA_EMAIL", "GITHUB_TOKEN", "AGGIE_ANALYTICS_DATA_ROOT"}
    present = {name: bool(os.environ.get(name)) for name in names}
    env_path = repo / ".env"
    if env_path.is_file():
        for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key = line.split("=", 1)[0].strip()
                if key in names:
                    present[key] = True
    return {name: "PRESENT_REDACTED" if present[name] else "ABSENT" for name in sorted(names)}


def audit(repo_root: Path) -> dict[str, Any]:
    repo = repo_root.resolve()
    git_dir = repo / ".git"
    git: dict[str, Any] = {"metadata_present": git_dir.exists(), "classification": "NO_LOCAL_GIT_HISTORY"}
    if git_dir.exists():
        top = _run(repo, ["git", "rev-parse", "--show-toplevel"])
        status = _run(repo, ["git", "status", "--short", "--branch"])
        head = _run(repo, ["git", "rev-parse", "HEAD"])
        branches = _run(repo, ["git", "branch", "--all", "--verbose", "--no-abbrev"])
        worktrees = _run(repo, ["git", "worktree", "list", "--porcelain"])
        remote_result = _run(repo, ["git", "remote", "get-url", "origin"])
        git = {
            "metadata_present": True,
            "classification": "LOCAL_GIT_PRESENT" if top["exit_code"] == 0 else "GIT_METADATA_INVALID",
            "top_level": top["stdout"],
            "status": status,
            "head": head["stdout"] if head["exit_code"] == 0 else "UNBORN",
            "branches": branches,
            "worktrees": worktrees,
            "origin": _sanitize_url(remote_result["stdout"]) if remote_result["exit_code"] == 0 else "UNCONFIGURED",
        }
    profile_path = repo / "jira/project/JIRA_TARGET_PROFILE.yaml"
    profile: dict[str, Any] = {}
    if profile_path.is_file():
        try:
            raw = json.loads(profile_path.read_text(encoding="utf-8"))
            profile = {
                "profile_status": raw.get("profile_status"),
                "jira_base_url": _sanitize_url(str(raw.get("jira_base_url", ""))),
                "project_key": raw.get("project_key"),
                "project_id": raw.get("project_id"),
                "board_id": raw.get("board_id"),
                "last_live_verification": raw.get("last_live_verification"),
                "live_counts": raw.get("live_counts", {}),
            }
        except Exception as exc:
            profile = {"profile_status": "INVALID", "error_type": type(exc).__name__}
    manifest_path = repo / "instructions/manifest.json"
    return {
        "schema_version": "1.0.0",
        "audit_type": "control_plane_read_only_redacted",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo),
        "repo_root_exists": repo.is_dir(),
        "git": git,
        "jira": profile,
        "instructions": {
            "manifest_present": manifest_path.is_file(),
            "manifest_sha256": _sha(manifest_path) if manifest_path.is_file() else None,
            "entrypoint_present": (repo / "instructions/START_HERE.md").is_file(),
        },
        "environment_aliases": _env_aliases(repo),
        "redaction": {"secret_values_included": False, "authorization_headers_included": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.repo_root)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else args.repo_root.resolve() / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + ".tmp")
        temporary.write_text(encoded, encoding="utf-8", newline="\n")
        os.replace(temporary, output)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
