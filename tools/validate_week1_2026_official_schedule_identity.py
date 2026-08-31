"""Independently revalidate the Week 1 2026 schedule and identity gate.

The validator never calls the network and never writes: it rehashes the immutable
captures, reparses them, rebuilds every row, and compares the reconstruction to
the committed gate and the external payloads.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.week1_2026_official_schedule_identity import (  # noqa: E402
    CONTEST_PAYLOAD_NAME,
    GATE_RELATIVE,
    PARTICIPANT_PAYLOAD_NAME,
    Week1ScheduleIdentityViolation,
    build_contest_rows,
    build_participant_rows,
    read_jsonl,
    validate_artifact,
)

sys.path.insert(0, str(REPO_ROOT / "tools"))

from build_week1_2026_official_schedule_identity import load_inputs  # noqa: E402


def reconstruct(repo_root: Path, data_root: Path) -> list[str]:
    """Rebuild the payloads from raw captures and compare them byte-for-byte."""

    findings: list[str] = []
    inputs = load_inputs(repo_root, data_root)
    contests = build_contest_rows(
        contract=inputs["contract"],
        captures=inputs["captures"],
        documents=inputs["documents"],
        predecessor=inputs["predecessor"],
        authority=inputs["authority"],
    )
    participants = build_participant_rows(contests)

    gate = json.loads((repo_root / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
    manifest = json.loads(
        (data_root / gate["manifest"]["relative_path"]).read_text(encoding="utf-8-sig")
    )
    published = {
        payload["name"]: read_jsonl(data_root / payload["relative_path"])
        for payload in manifest["payloads"]
    }
    for name, rebuilt in (
        (CONTEST_PAYLOAD_NAME, contests),
        (PARTICIPANT_PAYLOAD_NAME, participants),
    ):
        if published.get(name) != rebuilt:
            findings.append(f"independent reconstruction disagrees with the published {name}")
    for entry in gate["bound_predecessors"].items():
        if not entry[1]:
            findings.append(f"gate bound an empty predecessor identity: {entry[0]}")
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", ""))
    args = parser.parse_args(argv)
    if not args.data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT is required", file=sys.stderr)
        return 2
    repo_root = Path(args.repo_root)
    data_root = Path(args.data_root)
    try:
        report = validate_artifact(repo_root=repo_root, data_root=data_root)
        report["findings"] = list(report["findings"]) + reconstruct(repo_root, data_root)
    except Week1ScheduleIdentityViolation as exc:
        report = {"result": "FAIL", "findings": [f"week 1 schedule identity violation: {exc}"]}
    report["result"] = "PASS" if not report["findings"] else "FAIL"
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
