"""Independently validate the national expectation baseline and peer cohort gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.modeling import national_expectation_baselines as baselines  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("."))
    parser.add_argument("--repo-root", default=REPO_ROOT, type=Path)
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="validate authority and structure without rebuilding the evaluation.",
    )
    args = parser.parse_args(argv)

    result = baselines.validate_artifact(
        data_root=args.data_root.resolve(),
        repo_root=args.repo_root.resolve(),
        require_rebuild=not args.schema_only,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
