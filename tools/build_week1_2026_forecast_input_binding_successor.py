"""Materialize the Cycle #25 forecast-input binding successor and Cycle #24 review."""

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

from aggie_analytics.data.week1_2026_forecast_input_binding_successor import (  # noqa: E402
    GATE_RELATIVE,
    BindingSuccessorViolation,
    build_expected,
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
                "freeze_identity": expected["freeze"]["freeze_identity"],
                "summary": expected["summary"],
                "writes_performed": "NONE",
            }
            if (repo_root / GATE_RELATIVE).is_file():
                report["artifact_validation"] = validate_artifact(
                    repo_root=repo_root, data_root=data_root
                )
            print(json.dumps(report, indent=2))
            return 0
        expected = build_expected(repo_root=repo_root, data_root=data_root)
        outcome = materialize(
            repo_root=repo_root,
            data_root=data_root,
            execution_time=parse_execution_time(args.execution_time_utc),
            expected=expected,
        )
        print(
            json.dumps(
                {
                    "result": "PASS",
                    "review_gate_identity": outcome["review_gate"]["gate_identity"],
                    "successor_gate_identity": outcome["successor_gate"][
                        "gate_identity"
                    ],
                    "freeze_identity": outcome["successor_gate"][
                        "pre_market_model_freeze"
                    ]["freeze_identity"],
                    "dataset_identity": outcome["successor_gate"]["dataset_identity"],
                    "summary": outcome["successor_gate"]["summary"],
                },
                indent=2,
            )
        )
        return 0
    except BindingSuccessorViolation as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
