"""Validate protected-exposure classification and inactive replacement protocol."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.protected_evaluation_replacement_protocol import (  # noqa: E402
    LANE_DECISION,
    replacement_protocol,
)


def validate(repo_root: Path) -> list[str]:
    findings: list[str] = []
    protocol_path = (
        repo_root
        / "artifacts"
        / "scientific_integrity"
        / "PROTECTED_EVALUATION_REPLACEMENT_PROTOCOL.json"
    )
    if not protocol_path.is_file():
        return ["PROTECTED_REPLACEMENT_PROTOCOL_MISSING"]
    payload = json.loads(protocol_path.read_text(encoding="utf-8"))
    expected = replacement_protocol(user_approved_activation=False)
    if payload.get("lane_decision") != LANE_DECISION:
        findings.append("PROTECTED_LANE_NOT_RETAINED_BLOCKED")
    if payload.get("exposed_seasons", {}).get("blind") is True:
        findings.append("EXPOSED_SEASONS_LABELED_BLIND")
    if payload.get("exposed_seasons", {}).get("sealed") is True:
        findings.append("EXPOSED_SEASONS_LABELED_SEALED")
    if payload.get("user_approved_activation") is True:
        findings.append("PROTECTED_REPLACEMENT_ACTIVATED_WITHOUT_USER_APPROVAL")
    if payload.get("protocol_status") != expected["protocol_status"]:
        findings.append("PROTECTED_PROTOCOL_STATUS_DRIFT")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    findings = validate(Path(args.repo_root).resolve())
    print(
        json.dumps(
            {
                "validator": "protected_evaluation_replacement",
                "result": "PASS" if not findings else "FAIL",
                "findings": findings,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
