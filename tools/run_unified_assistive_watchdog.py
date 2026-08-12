from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.watchdog import ReadOnlyWatchdog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(r"C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3\state\orchestrator.sqlite3"),
    )
    parser.add_argument("--heartbeat-max-age-seconds", type=int, default=90)
    args = parser.parse_args()
    report = ReadOnlyWatchdog(args.database, args.heartbeat_max_age_seconds).inspect()
    print(json.dumps(report, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
