"""Materialize the Cycle #26 R26-22 prior-target pair audit."""

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
if str(REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools"))

from aggie_analytics.data.cycle26_bound_authority_pair_audit import (  # noqa: E402
    BoundAuthorityPairAuditError,
    materialize,
)
from build_national_pit_eligible_slice import load_inputs  # noqa: E402


def _synthetic_inputs() -> tuple[list[dict[str, object]], dict[str, str]]:
    observations = [
        {"canonical_team_id": "tamu", "canonical_game_id": "g1", "season": 2022},
        {"canonical_team_id": "tamu", "canonical_game_id": "g2", "season": 2022},
        {"canonical_team_id": "tamu", "canonical_game_id": "g3", "season": 2022},
    ]
    starts = {
        "g1": "2022-09-03T18:00:00Z",
        "g2": "2022-09-10T18:00:00Z",
        "g3": "2022-09-17T18:00:00Z",
    }
    return observations, starts


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
    parser.add_argument(
        "--synthetic-only",
        action="store_true",
        help="Audit fixture pairs only; do not load the national spine.",
    )
    args = parser.parse_args(argv)
    repo = Path(args.repo_root)
    observations, starts = _synthetic_inputs()
    census_source = "SYNTHETIC_FIXTURE"
    if args.data_root and not args.synthetic_only:
        try:
            inputs = load_inputs(repo, Path(args.data_root))
            observations = list(inputs["observations"])
            starts = dict(inputs["starts"])
            census_source = "NATIONAL_SPINE_MOUNTED"
        except (OSError, KeyError, ValueError, TypeError):
            census_source = "SYNTHETIC_FIXTURE_SPINE_UNAVAILABLE"
    try:
        audit = materialize(
            repo_root=repo,
            observations=observations,
            starts=starts,
            issued_at_utc=args.execution_time_utc,
            census_source=census_source,
        )
    except BoundAuthorityPairAuditError as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "result": audit["result"],
                "gate_identity": audit["gate_identity"],
                "census_source": census_source,
                "admitted_proxy_pairs": audit["census"]["admitted_proxy_pairs"],
                "near_bound_pairs": audit["census"]["near_bound_pairs"],
                "leakage_declared": audit["leakage_declared"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
