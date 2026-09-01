"""Materialize the Cycle #25 EARLY_MARKET benchmark and forecast-adequacy gate."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.week1_2026_market_benchmark_and_adequacy import (  # noqa: E402
    MarketBenchmarkViolation,
    materialize,
    validate_artifact,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument(
        "--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", "")
    )
    parser.add_argument("--captured-at-utc", default=None)
    parser.add_argument("--live-acquire", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT is required", file=sys.stderr)
        return 2
    captured = args.captured_at_utc or datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    repo_root = Path(args.repo_root)
    data_root = Path(args.data_root)
    try:
        if args.validate_only:
            report = validate_artifact(repo_root=repo_root, data_root=data_root)
            print(json.dumps(report, indent=2))
            return 0
        outcome = materialize(
            repo_root=repo_root,
            data_root=data_root,
            captured_at_utc=captured,
            live_acquire=bool(args.live_acquire),
        )
        print(
            json.dumps(
                {
                    "result": "PASS",
                    "gate_identity": outcome["gate"]["gate_identity"],
                    "dataset_identity": outcome["gate"]["dataset_identity"],
                    "freeze_identity": outcome["gate"][
                        "pre_market_model_freeze_identity"
                    ],
                    "cfbd_disposition": outcome["gate"]["cfbd"]["disposition"],
                    "national": outcome["gate"]["national"],
                    "writes_to_git_raw_bulk": False,
                },
                indent=2,
            )
        )
        return 0
    except MarketBenchmarkViolation as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
