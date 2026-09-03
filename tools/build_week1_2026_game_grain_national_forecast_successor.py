"""Materialize the Cycle #26 game-grain national forecast successor."""

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

from aggie_analytics.data.week1_2026_game_grain_national_forecast_successor import (  # noqa: E402
    GameGrainNationalViolation,
    materialize,
)


def main(argv: Sequence[str] | None = None) -> int:
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
    args = parser.parse_args(argv)
    data_root = Path(args.data_root) if args.data_root else None
    if data_root is None:
        print("AGGIE_ANALYTICS_DATA_ROOT is required", file=sys.stderr)
        return 2
    try:
        gate = materialize(
            repo_root=Path(args.repo_root),
            data_root=data_root,
            issued_at_utc=args.execution_time_utc,
        )
    except GameGrainNationalViolation as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "dataset_identity": gate["dataset_identity"],
                "summary": gate["summary"],
                "pair_coherence": gate["pair_coherence"],
                "trust": gate["trust"],
            },
            indent=2,
        )
    )
    return 0 if str(gate["result"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
