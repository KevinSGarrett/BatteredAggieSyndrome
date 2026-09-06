"""Materialize the Cycle #27 ridge interval-label successor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.cycle27_ridge_interval_label_successor import materialize  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", default=r"C:\BatteredAggieSyndrome.data")
    parser.add_argument("--issued-at-utc", default="2026-09-04T16:45:00Z")
    args = parser.parse_args()
    gate = materialize(
        repo_root=Path(args.repo_root),
        data_root=Path(args.data_root),
        issued_at_utc=args.issued_at_utc,
    )
    print(gate["gate_identity"])
    print(gate["dataset_identity"])
    print(gate["ridge_row_count"])
    print(gate["retrospective_diagnostic_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
