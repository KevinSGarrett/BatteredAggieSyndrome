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

from aggie_analytics.experimentation.development_2023_labeled_replay import (  # noqa: E402
    materialize,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize the 2023-only labeled development matrix and walk-forward."
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")),
    )
    parser.add_argument("--output-data-root", type=Path)
    parser.add_argument(
        "--issued-at-utc",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    args = parser.parse_args()
    result = materialize(
        data_root=args.data_root.resolve(),
        repo_root=args.repo_root.resolve(),
        issued_at_utc=args.issued_at_utc,
        output_data_root=(args.output_data_root or args.data_root).resolve(),
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
