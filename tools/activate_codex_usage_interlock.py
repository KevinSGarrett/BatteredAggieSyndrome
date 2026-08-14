from __future__ import annotations

"""Install and verify the versioned local Git interlock hook."""

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.repo_root.resolve(strict=True)
    hook = root / ".githooks/pre-commit"
    if not hook.is_file():
        raise SystemExit("INTERLOCK_HOOK_MISSING")
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=root, check=True)
    configured = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if configured != ".githooks":
        raise SystemExit("INTERLOCK_HOOK_CONFIGURATION_MISMATCH")
    report = {
        "result": "PASS",
        "repo_root": str(root),
        "hooks_path": configured,
        "hook": str(hook),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
