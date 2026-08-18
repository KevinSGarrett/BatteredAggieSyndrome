from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_ncaa_team_season_evidence import materialize  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize bounded 2010-2011 Texas A&M NCAA team-season evidence."
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")),
    )
    parser.add_argument(
        "--issued-at-utc",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    parser.add_argument("--no-live", action="store_true")
    args = parser.parse_args()
    result = materialize(
        data_root=args.data_root.resolve(),
        repo_root=args.repo_root.resolve(),
        issued_at_utc=args.issued_at_utc,
        allow_live=not args.no_live,
    )
    print(json.dumps({"gate": result["gate"], "payload": result["payload"]}, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
