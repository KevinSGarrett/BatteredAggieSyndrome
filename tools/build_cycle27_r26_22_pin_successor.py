"""Materialize the Cycle #27 R26-22 semantic pin successor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.cycle27_r26_22_pin_successor import materialize  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--issued-at-utc", default="2026-09-04T16:45:00Z")
    args = parser.parse_args()
    disposition = materialize(
        repo_root=Path(args.repo_root), issued_at_utc=args.issued_at_utc
    )
    print(disposition["disposition_identity"])
    print(disposition["pair_audit_gate_identity"])
    print(disposition["r26_22_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
