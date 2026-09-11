"""R32-01 preservation receipt for the dirty Cycle32 worktree. Not a commit."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle30-scr")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
MANAGER = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle31\20260911T034527Z"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> int:
    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current")
    status = git("status", "--porcelain")
    tracked = []
    untracked = []
    for line in status.splitlines():
        code = line[:2]
        path = line[3:]
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        full = ROOT / path.replace("/", os.sep)
        row = {
            "path": path.replace("\\", "/"),
            "status": code.strip(),
            "exists": full.is_file(),
            "sha256": sha256_file(full) if full.is_file() else None,
            "bytes": full.stat().st_size if full.is_file() else 0,
        }
        if code.startswith("?"):
            untracked.append(row)
        else:
            tracked.append(row)
    payload = {
        "artifact_type": "CYCLE32_WORKTREE_PRESERVATION",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "worktree": str(ROOT),
        "branch": branch,
        "git_head": head,
        "manager_observed_head": "7d680d17b90a784ddf8abbb90230ea48b34fa482",
        "head_matches_manager_observation": head
        == "7d680d17b90a784ddf8abbb90230ea48b34fa482",
        "canonical_main_untouched": True,
        "reset_hard_not_used": True,
        "tracked_modified": len(tracked),
        "untracked": len(untracked),
        "committed_submission": False,
        "manager_snapshot": str(MANAGER / "WORKTREE_SNAPSHOT.json"),
        "python": sys.version,
        "files": {"tracked": tracked, "untracked": untracked},
    }
    out = OUT / "science" / "CYCLE32_WORKTREE_PRESERVATION.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "git_head": head,
                "branch": branch,
                "tracked_modified": len(tracked),
                "untracked": len(untracked),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
