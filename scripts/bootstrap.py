from __future__ import annotations

import argparse
import subprocess
import sys
import venv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the local development virtual environment.")
    parser.add_argument("--skip-install", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    preferred = (3, 12)
    if sys.version_info[:2] != preferred:
        print(f"NOTE: preferred local interpreter is Python 3.12; current is {sys.version_info.major}.{sys.version_info.minor}.")
    env = root / ".venv"
    if not env.exists():
        venv.EnvBuilder(with_pip=True).create(env)
    if args.skip_install:
        print(f"Environment ready at {env}; install skipped.")
        return 0
    python = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "-e", str(root)], check=True)
    print(f"Environment ready at {env}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
