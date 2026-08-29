"""Independently validate the 2026 shadow forecast temporal-proof audit gate."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.modeling.shadow_forecast_temporal_audit import (  # noqa: E402
    TemporalAuditViolation,
    validate_artifact,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT"))
    args = parser.parse_args()

    if not args.data_root:
        print("SKIP: AGGIE_ANALYTICS_DATA_ROOT is not set, so the population cannot be rebuilt")
        return 0

    try:
        summary = validate_artifact(Path(args.repo_root), Path(args.data_root))
    except TemporalAuditViolation as violation:
        print(f"FAIL: {violation}")
        return 1

    print(json.dumps(summary, indent=2, sort_keys=True))
    print("PASS: the 2026 shadow forecast temporal audit reproduces from the frozen population")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
