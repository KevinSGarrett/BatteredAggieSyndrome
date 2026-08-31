"""Independently validate the Cycle #24 Week 1 2026 current-authority enrichment.

The validator reconstructs every authority surface from the pinned captures and
refuses the committed gate when any authority claim is not earned: an unconfirmed
kickoff presented as confirmed, an entity resolved without a season team
identifier link, a poll row left unbound, a venue identity inferred from site
orientation, admitted coordinates without a coordinate authority, or weather
promoted to model input.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.week1_2026_authority_enrichment import (  # noqa: E402
    GATE_RELATIVE,
    AuthorityEnrichmentViolation,
    validate_artifact,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument(
        "--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", "")
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Check gate identity and invariants without rebuilding from captures.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    if not (repo_root / GATE_RELATIVE).is_file():
        print(
            json.dumps(
                {"result": "FAIL", "findings": [f"missing gate: {GATE_RELATIVE}"]},
                indent=2,
            )
        )
        return 1
    if not args.schema_only and not args.data_root:
        print(
            "AGGIE_ANALYTICS_DATA_ROOT is required for an independent rebuild",
            file=sys.stderr,
        )
        return 2

    try:
        report = validate_artifact(
            repo_root=repo_root,
            data_root=Path(args.data_root) if args.data_root else repo_root,
            require_rebuild=not args.schema_only,
        )
    except AuthorityEnrichmentViolation as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
