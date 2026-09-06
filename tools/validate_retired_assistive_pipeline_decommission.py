"""Prove Fort Knox/retired assistive pipeline has no active authority."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle28.decommission import validate_retired_assistive_decommission


def validate(root: Path) -> list[str]:
    return validate_retired_assistive_decommission(root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    findings = validate(args.repo_root.resolve())
    payload = {
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "retired_pipeline_active_authority": bool(findings),
    }
    print(json.dumps(payload, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
