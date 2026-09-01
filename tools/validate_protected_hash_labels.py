"""Fail-closed validator for distinct protected-hash labels."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.validation.protected_hash_labels import (  # noqa: E402
    validate_protected_hash_labels,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    findings = validate_protected_hash_labels(args.repo_root.resolve())
    if findings:
        print(json.dumps({"result": "FAIL", "findings": findings}, indent=2))
        return 1
    print(json.dumps({"result": "PASS", "findings": []}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
