"""Materialize Cycle 27 coaching census, staff packets, disagreement, score readiness, and interim pregame report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.cycle27_coaching_reporting import (  # noqa: E402
    FOCUS_AWAY_CANONICAL,
    FOCUS_HOME_CANONICAL,
    load_json,
    materialize as materialize_coaching,
)
from aggie_analytics.data.cycle27_pregame_reporting import (  # noqa: E402
    materialize as materialize_pregame,
)


def _git_head(repo_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", default=r"C:\BatteredAggieSyndrome.data")
    parser.add_argument(
        "--ops-root", default=r"C:\BatteredAggieSyndrome.data\ops\cycle27"
    )
    parser.add_argument(
        "--issued-at-utc",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    args = parser.parse_args()
    repo_root = Path(args.repo_root)
    data_root = Path(args.data_root)
    ops_root = Path(args.ops_root)
    code_head = _git_head(repo_root)
    coaching = materialize_coaching(
        repo_root=repo_root,
        data_root=data_root,
        ops_root=ops_root,
        issued_at_utc=args.issued_at_utc,
        code_head=code_head,
    )
    census = load_json(
        repo_root
        / "artifacts/scientific_integrity/cycle27/COACHING_DATA_AND_CONSUMPTION_CENSUS.json"
    )
    staff_packets = {
        FOCUS_HOME_CANONICAL: load_json(
            repo_root
            / "artifacts/scientific_integrity/cycle27/FOCUS_STAFF_CONTEXT_TEXAS_AM.json"
        ),
        FOCUS_AWAY_CANONICAL: load_json(
            repo_root
            / "artifacts/scientific_integrity/cycle27/FOCUS_STAFF_CONTEXT_MISSOURI_STATE.json"
        ),
    }
    pregame = materialize_pregame(
        repo_root=repo_root,
        data_root=data_root,
        ops_root=ops_root,
        issued_at_utc=args.issued_at_utc,
        coaching_census=census,
        staff_packets=staff_packets,
        code_head=code_head,
    )
    print(
        json.dumps(
            {
                "result": "PASS_CYCLE27_COACHING_AND_PREGAME_REPORTING",
                "issued_at_utc": args.issued_at_utc,
                "code_head": code_head,
                "coaching": coaching,
                "pregame": {
                    "diagnostic_identity": pregame["diagnostic_identity"],
                    "score_readiness_identity": pregame["score_readiness_identity"],
                    "written": pregame["written"],
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
