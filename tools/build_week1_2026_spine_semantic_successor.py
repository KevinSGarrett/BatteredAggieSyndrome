"""Materialize the Cycle #24 Week 1 2026 spine semantic successor.

The producer reads the pinned Cycle #23 predecessor gates, splits the composite
venue/site domain, classifies each prior state exactly, maps partial coverage to a
terminal forecast-time abstention, emits unambiguous cell counters, and writes the
correction records. The predecessor artifacts are bound, never rewritten.

The only network access permitted here is none: every input is already committed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.week1_2026_spine_semantic_successor import (  # noqa: E402
    GATE_RELATIVE,
    SemanticSuccessorViolation,
    build_expected,
    load_inputs,
    materialize,
    validate_artifact,
)


def parse_execution_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument(
        "--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", "")
    )
    parser.add_argument(
        "--execution-time-utc",
        default=None,
        help="Pin the issuance instant so a rebuild reproduces the committed gate.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Rebuild every surface in memory and re-validate without writing.",
    )
    args = parser.parse_args(argv)
    if not args.data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT is required", file=sys.stderr)
        return 2

    repo_root = Path(args.repo_root)
    data_root = Path(args.data_root)

    try:
        if args.validate_only:
            expected = build_expected(repo_root=repo_root, data_root=data_root)
            report: dict[str, Any] = {
                "result": "PASS",
                "mode": "VALIDATE_ONLY_NO_WRITES",
                "dataset_identity": expected["dataset_identity"],
                "summary": expected["summary"],
                "focus_contest_report": expected["focus_contest_report"],
                "writes_performed": "NONE",
            }
            if (repo_root / GATE_RELATIVE).is_file():
                report["artifact_validation"] = validate_artifact(
                    repo_root=repo_root, data_root=data_root
                )
            print(json.dumps(report, indent=2))
            return 0

        inputs = load_inputs(repo_root, data_root)
        expected = build_expected(
            repo_root=repo_root, data_root=data_root, inputs=inputs
        )
        outcome = materialize(
            repo_root=repo_root,
            data_root=data_root,
            execution_time=parse_execution_time(args.execution_time_utc),
            expected=expected,
        )
    except SemanticSuccessorViolation as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1

    gate = outcome["gate"]
    print(
        json.dumps(
            {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "dataset_identity": gate["dataset_identity"],
                "execution_time_utc": gate["execution_time_utc"],
                "payloads": [
                    {"name": item["name"], "rows": item["rows"]}
                    for item in gate["payloads"]
                ],
                "summary": gate["summary"],
                "focus_contest_report": gate["focus_contest_report"],
                "forecast_produced": False,
                "network_access": "NONE",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
