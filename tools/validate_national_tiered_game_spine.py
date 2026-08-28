from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.national_tiered_game_spine import validate_artifact  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently validate the tiered national game spine gate"
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(
            os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--schema-only", action="store_true")
    args = parser.parse_args()

    try:
        report = validate_artifact(
            data_root=args.data_root.resolve(),
            repo_root=args.repo_root.resolve(),
            require_rebuild=not args.schema_only,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
