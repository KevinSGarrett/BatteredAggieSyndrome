"""Validate the Cycle #25.5 scientific-trust operator hold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.governance.scientific_trust_recovery_hold import (  # noqa: E402
    validate_hold,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--action", default=None)
    parser.add_argument("--pr-number", type=int, default=None)
    parser.add_argument("--head-sha", default=None)
    parser.add_argument("--base-sha", default=None)
    parser.add_argument("--done-key", action="append", default=None)
    parser.add_argument("--merge-ref", action="append", default=None)
    parser.add_argument("--parent-comment", default=None)
    parser.add_argument("--completion-claim", default=None)
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    findings = validate_hold(
        root,
        proposed_action=args.action,
        proposed_pr_number=args.pr_number,
        proposed_head_sha=args.head_sha,
        proposed_base_sha=args.base_sha,
        proposed_done_keys=args.done_key,
        proposed_merges=args.merge_ref,
        proposed_parent_comment=args.parent_comment,
        proposed_completion_claim=args.completion_claim,
    )
    payload = {
        "validator": "scientific_trust_recovery_hold",
        "result": "PASS" if not findings else "FAIL",
        "finding_count": len(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
