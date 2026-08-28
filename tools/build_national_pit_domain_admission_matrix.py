"""Build the national domain coverage and point-in-time admission matrix."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data import national_pit_domain_admission_matrix as matrix  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--repo-root", default=REPO_ROOT, type=Path)
    parser.add_argument(
        "--issued-at-utc",
        default=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    args = parser.parse_args(argv)

    result = matrix.materialize(
        data_root=args.data_root.resolve(),
        repo_root=args.repo_root.resolve(),
        issued_at_utc=args.issued_at_utc,
    )
    gate = result["gate"]
    print(
        json.dumps(
            {
                "result": gate["result"],
                "dataset_identity": gate["dataset_identity"],
                "gate_identity": gate["gate_identity"],
                "population": gate["population"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
