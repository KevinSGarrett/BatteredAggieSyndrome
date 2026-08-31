"""Materialize the Cycle #24 frozen 2026 opening strength priors.

The producer replays Elo chronologically over allowed through-2023 evidence with
the previously frozen hyperparameters, applies the predeclared Week Zero batch
update only after every contest in the batch carries an official final capture,
and abstains for any team without enough allowed history instead of substituting
a default rating. No network access occurs here.
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

from aggie_analytics.data.week1_2026_frozen_strength_prior import (  # noqa: E402
    GATE_RELATIVE,
    FrozenPriorViolation,
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
    parser.add_argument("--execution-time-utc", default=None)
    parser.add_argument("--validate-only", action="store_true")
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
    except FrozenPriorViolation as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1

    gate = outcome["gate"]
    print(
        json.dumps(
            {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "dataset_identity": gate["dataset_identity"],
                "issued_at_utc": gate["issued_at_utc"],
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
