from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.features.postgame_collapse_taxonomy import materialize  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-data-root", type=Path, required=True)
    parser.add_argument("--output-data-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--issued-at-utc", required=True)
    args = parser.parse_args()
    result = materialize(input_data_root=args.input_data_root, output_data_root=args.output_data_root, repo_root=args.repo_root, issued_at_utc=args.issued_at_utc)
    print(json.dumps({key: value for key, value in result.items() if key != "manifest"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
