#!/usr/bin/env python3
"""Materialize Cycle 27 remaining-checkpoint current-contest bindings."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.cycle27_current_contest_checkpoint_binding import (  # noqa: E402
    materialize,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--issued-at-utc", default="")
    args = parser.parse_args()
    repo = Path(args.repo_root)
    now = (
        datetime.fromisoformat(args.issued_at_utc.replace("Z", "+00:00"))
        if args.issued_at_utc
        else datetime.now(timezone.utc)
    )
    census = json.loads(
        (
            repo
            / "artifacts/scientific_integrity/cycle27/COACHING_DATA_AND_CONSUMPTION_CENSUS.json"
        ).read_text(encoding="utf-8")
    )
    payload = materialize(repo_root=repo, census=census, now_utc=now)
    print(payload["binding_identity"])
    print(payload["helper_call_count"], payload["contest_count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
