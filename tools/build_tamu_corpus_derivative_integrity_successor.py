"""Materialize the Cycle #26 corpus derivative-integrity successor."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_corpus_derivative_integrity_successor import (  # noqa: E402
    CorpusIntegritySuccessorError,
    materialize,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument(
        "--data-root",
        default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", ""),
    )
    parser.add_argument(
        "--execution-time-utc",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    args = parser.parse_args(argv)
    data_root = Path(args.data_root) if args.data_root else None
    try:
        gate = materialize(
            repo_root=Path(args.repo_root),
            data_root=data_root,
            issued_at_utc=args.execution_time_utc,
        )
    except CorpusIntegritySuccessorError as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1
    census = gate["census"]
    print(
        json.dumps(
            {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "stale_domains": census["child_counts"]["stale_domain_count"],
                "placeholder_files": census["placeholders"]["unresolved_count"],
                "mounted": census["mounted_children"].get("mounted"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
