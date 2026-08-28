"""Independently validate the nationally scoped chronological development matrix."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data import national_chronological_development_matrix as matrix  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT"))
    parser.add_argument("--repo-root", default=REPO_ROOT, type=Path)
    parser.add_argument("--schema-only", action="store_true")
    args = parser.parse_args(argv)

    if not args.schema_only and not args.data_root:
        print("FAIL: AGGIE_ANALYTICS_DATA_ROOT_REQUIRED")
        return 1

    try:
        result = matrix.validate_artifact(
            data_root=Path(args.data_root).resolve() if args.data_root else REPO_ROOT,
            repo_root=args.repo_root.resolve(),
            require_rebuild=not args.schema_only,
        )
    except (ValueError, FileNotFoundError, KeyError) as error:
        print(f"FAIL: {error}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
