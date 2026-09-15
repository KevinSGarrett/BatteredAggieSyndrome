"""R33-01 preservation of the Cycle 33 starting stack. Not a commit."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\BatteredAggieSyndrome")
WORKTREE = Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr")
REVIEWED = Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle30-scr")
OUT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs")
EXPECTED_HEAD = "ca8e0a1f4ef3b30e4b50505e98b463daabcd7185"
EXPECTED_BASE = "7d680d17b90a784ddf8abbb90230ea48b34fa482"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = OUT / stamp / "implementation_output" / "science"
    dest.mkdir(parents=True, exist_ok=True)
    worktrees = git(ROOT, "worktree", "list", "--porcelain")
    payload = {
        "artifact_type": "CYCLE33_STARTING_STACK",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "canonical_main": {
            "path": str(ROOT),
            "head": git(ROOT, "rev-parse", "HEAD"),
            "branch": git(ROOT, "branch", "--show-current"),
            "status": git(ROOT, "status", "--porcelain"),
            "not_validation_subject": True,
        },
        "reviewed_cycle32_worktree": {
            "path": str(REVIEWED),
            "head": git(REVIEWED, "rev-parse", "HEAD"),
            "branch": git(REVIEWED, "branch", "--show-current"),
            "status": git(REVIEWED, "status", "--porcelain"),
        },
        "cycle33_worktree": {
            "path": str(WORKTREE),
            "head": git(WORKTREE, "rev-parse", "HEAD"),
            "branch": git(WORKTREE, "branch", "--show-current"),
            "status": git(WORKTREE, "status", "--porcelain"),
        },
        "expected_predecessor_head": EXPECTED_HEAD,
        "expected_predecessor_base": EXPECTED_BASE,
        "head_matches_expected_predecessor": git(WORKTREE, "rev-parse", "HEAD")
        == EXPECTED_HEAD
        or git(REVIEWED, "rev-parse", "HEAD") == EXPECTED_HEAD,
        "worktree_list": worktrees,
        "worktree_count": sum(
            1 for line in worktrees.splitlines() if line.startswith("worktree ")
        ),
        "python": sys.version,
        "operator_hold": "ACTIVE",
        "paid_ai_calls": 0,
    }
    out = dest / "CYCLE33_STARTING_STACK.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "path": str(out),
                "worktree_count": payload["worktree_count"],
                "cycle33_head": payload["cycle33_worktree"]["head"],
            },
            indent=2,
        )
    )
    print(str(dest.parent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
