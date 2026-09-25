"""Materialize the Week 1 fitted-path temporal-authority successor."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.week1_2026_fitted_path_temporal_authority import (  # noqa: E402
    FittedPathTemporalAuthorityError,
    materialize,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument(
        "--execution-time-utc",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    args = parser.parse_args()
    try:
        gate = materialize(
            repo_root=Path(args.repo_root),
            issued_at_utc=args.execution_time_utc,
        )
    except FittedPathTemporalAuthorityError as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "primary_trust_recovery": gate["assessment"]["primary_trust_recovery"],
                "proven_pit_training_row_count": gate["assessment"][
                    "proven_pit_training_row_count"
                ],
                "training_row_count": gate["assessment"]["training_row_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
