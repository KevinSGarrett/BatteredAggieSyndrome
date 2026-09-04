#!/usr/bin/env python3
"""Materialize Cycle 27 postgame residual methodology."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.cycle27_postgame_residual_methodology import (  # noqa: E402
    materialize,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--issued-at-utc", default="2026-09-04T18:00:00Z")
    args = parser.parse_args()
    payload = materialize(
        repo_root=Path(args.repo_root), issued_at_utc=args.issued_at_utc
    )
    print(payload["methodology_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
