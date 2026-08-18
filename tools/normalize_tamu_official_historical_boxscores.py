from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.tamu_official_historical_boxscores import default_data_root, normalize_boxscores  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize official Texas A&M 2010-2011 box scores.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--data-root", type=Path, default=default_data_root())
    args = parser.parse_args()
    gate = normalize_boxscores(data_root=args.data_root.resolve(), repo_root=args.repo_root.resolve())
    print(
        json.dumps(
            {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "dataset_identity": gate["dataset_identity"],
                "games_identity": gate["games_identity"],
                "coverage_identity": gate["coverage_identity"],
                "counts": gate["counts"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
