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

from aggie_analytics.data.tamu_season_reconciliation import materialize  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize 2010-2011 TAMU season-level reconciliation.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")),
    )
    parser.add_argument("--issued-at-utc", default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    args = parser.parse_args()
    result = materialize(data_root=args.data_root.resolve(), repo_root=args.repo_root.resolve(), issued_at_utc=args.issued_at_utc)
    print(json.dumps({"gate_identity": result["gate"]["gate_identity"], "payload": result["payload"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
