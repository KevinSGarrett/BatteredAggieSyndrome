"""Materialize append-only Week 1 official-final scoring."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.week1_2026_official_final_scoring_successor import (  # noqa: E402
    Week1OfficialFinalScoringError,
    materialize,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument(
        "--data-root",
        default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", ""),
    )
    parser.add_argument(
        "--execution-time-utc",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    args = parser.parse_args()
    if not args.data_root:
        print(json.dumps({"result": "FAIL", "findings": ["DATA_ROOT_REQUIRED"]}))
        return 1
    try:
        gate = materialize(
            repo_root=Path(args.repo_root),
            data_root=Path(args.data_root),
            issued_at_utc=args.execution_time_utc,
        )
    except Week1OfficialFinalScoringError as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "summary": gate["summary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
