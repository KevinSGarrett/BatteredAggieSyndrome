from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    GATE_RELATIVE,
    materialize,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile the national capture foundation and materialize the normalized game successor"
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(
            os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--issued-at-utc", default=None)
    args = parser.parse_args()

    issued_at = args.issued_at_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = materialize(
        data_root=args.data_root.resolve(),
        repo_root=args.repo_root.resolve(),
        issued_at_utc=issued_at,
    )
    gate = result["gate"]
    print(
        json.dumps(
            {
                "gate_path": GATE_RELATIVE,
                "result": gate["result"],
                "dataset_identity": gate["dataset_identity"],
                "gate_identity": gate["gate_identity"],
                "capture_inventory": gate["capture_inventory"],
                "eligibility_census": gate["eligibility_census"],
                "normalized_rows": gate["normalized_inventory"]["rows"],
                "gap_002_state": gate["gap_002"]["state"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
