#!/usr/bin/env python3
"""Prove that read-only commands leave every tracked file untouched.

Usage:
  python tools/validate_tracked_file_purity.py --command "python -m unittest ..." [...]
  python tools/validate_tracked_file_purity.py --line-endings-only

Each --command is run in turn against a full tracked-file fingerprint taken immediately
before it. Any tracked file whose canonical LF bytes move, disappear or appear is reported
as a finding and the validator exits nonzero.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.validation.tracked_file_purity import (  # noqa: E402
    line_ending_findings,
    run_and_compare,
    tracked_paths,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--command",
        action="append",
        default=[],
        help="A read-only command to run and audit. Repeatable.",
    )
    parser.add_argument(
        "--line-endings-only",
        action="store_true",
        help="Only run the committed line-ending contract check.",
    )
    parser.add_argument(
        "--allow-nonzero-exit",
        action="store_true",
        help="Audit purity even when the audited command itself fails.",
    )
    args = parser.parse_args()

    relatives = tracked_paths(REPO_ROOT)
    findings = line_ending_findings(REPO_ROOT, relatives)
    reports: list[dict[str, object]] = []

    if not args.line_endings_only:
        for raw in args.command:
            report = run_and_compare(
                shlex.split(raw),
                repo_root=REPO_ROOT,
                env=os.environ.copy(),
            )
            reports.append(report.as_dict())
            findings.extend(report.findings())
            if report.exit_code != 0 and not args.allow_nonzero_exit:
                findings.append(f"AUDITED_COMMAND_FAILED:{raw}:exit={report.exit_code}")

    payload = {
        "artifact_type": "TRACKED_FILE_PURITY_VALIDATION",
        "findings": sorted(set(findings)),
        "reports": reports,
        "result": "PASS" if not findings else "FAIL",
        "tracked_file_count": len(relatives),
        "validator": "tracked_file_purity",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
