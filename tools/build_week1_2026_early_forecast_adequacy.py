"""Materialize the immutable EARLY_WEEK1 national forecast snapshot."""

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

from aggie_analytics.data.week1_2026_early_forecast_adequacy import (  # noqa: E402
    EarlyForecastViolation,
    build_expected,
    build_gate,
    materialize,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument(
        "--data-root",
        default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", ""),
    )
    parser.add_argument("--execution-time-utc", required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    data_root = Path(args.data_root) if args.data_root else None
    if data_root is None:
        print("AGGIE_ANALYTICS_DATA_ROOT is required", file=sys.stderr)
        return 2

    try:
        if args.validate_only:
            expected = build_expected(
                repo_root=repo_root,
                data_root=data_root,
                issued_at_utc=args.execution_time_utc,
            )
            gate = build_gate(
                repo_root=repo_root,
                data_root=data_root,
                issued_at_utc=args.execution_time_utc,
                expected=expected,
            )
            gate.pop("_payload_bytes", None)
            gate.pop("_manifest_body", None)
            report = {
                "result": "PASS",
                "mode": "VALIDATE_ONLY_NO_WRITES",
                "dataset_identity": gate["dataset_identity"],
                "summary": gate["summary"],
                "pair_coherence": gate["pair_coherence"],
                "focus_contest_report": gate["focus_contest_report"],
                "coverage": gate["coverage"],
            }
        else:
            gate = materialize(
                repo_root=repo_root,
                data_root=data_root,
                issued_at_utc=args.execution_time_utc,
            )
            report = {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "dataset_identity": gate["dataset_identity"],
                "issued_at_utc": gate["issued_at_utc"],
                "payloads": gate["payloads"],
                "summary": gate["summary"],
                "pair_coherence": gate["pair_coherence"],
                "focus_contest_report": gate["focus_contest_report"],
            }
    except EarlyForecastViolation as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
