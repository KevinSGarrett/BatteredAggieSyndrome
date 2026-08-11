from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.temporal.venue_assignment_pit import materialize  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-data-root", type=Path, required=True)
    parser.add_argument("--output-data-root", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--issued-at-utc")
    args = parser.parse_args()
    issued_at = args.issued_at_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result = materialize(
        input_data_root=args.input_data_root.resolve(), output_data_root=(args.output_data_root or args.input_data_root).resolve(),
        repo_root=args.repo_root.resolve(), issued_at_utc=issued_at,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "manifest"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
