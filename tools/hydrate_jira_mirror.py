from __future__ import annotations

"""Reconcile a redacted Jira CSV export into the canonical local mirror."""

import argparse
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_csv", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    script = repo / "jira/tools/reconcile_jira_export.py"
    command = [sys.executable, "-B", str(script), "--repo-root", str(repo)]
    if args.dry_run:
        command.append("--dry-run")
    command.append(str(args.export_csv.resolve()))
    return subprocess.run(command, cwd=repo, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
