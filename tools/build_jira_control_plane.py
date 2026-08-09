from __future__ import annotations

"""Rebuild every Jira derivative from canonical local issue JSON."""

import argparse
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    script = repo / "jira/tools/rebuild_all_derivatives.py"
    return subprocess.run([sys.executable, "-B", str(script), "--repo-root", str(repo)], cwd=repo, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
