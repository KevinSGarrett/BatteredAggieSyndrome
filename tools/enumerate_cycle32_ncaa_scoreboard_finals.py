"""Enumerate every contest on cached NCAA.com Week1 scoreboards.

Does not invent historical NCAA contest captures that are not on disk.
stats.ncaa.org 403 pages remain fail-closed.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.acquisition import (  # noqa: E402
    parse_ncaa_com_scoreboard_contests,
)
from aggie_analytics.cycle30.hashing import sha256_bytes  # noqa: E402
from aggie_analytics.cycle30.scoring import (  # noqa: E402
    ScoringError,
    _bind_scores_from_same_page,
)

RAW = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\ncaa")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
SCOREBOARDS = (
    ("2026/00", RAW / "scoreboard-2026-00.html"),
    ("2026/01", RAW / "scoreboard-2026-01.html"),
    ("2026/02", RAW / "scoreboard-2026-02.html"),
    ("2026/03", RAW / "scoreboard-2026-03.html"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    reconstructed: list[dict[str, Any]] = []
    missing_raw = []
    for week, path in SCOREBOARDS:
        if not path.is_file():
            missing_raw.append(str(path))
            continue
        body = path.read_bytes()
        contests = parse_ncaa_com_scoreboard_contests(body.decode("utf-8", "replace"))
        for contest in contests:
            home = str(contest.get("home_name") or "")
            away = str(contest.get("away_name") or "")
            contest_id = str(contest.get("ncaa_com_contest_id") or "")
            home_points = contest.get("home_points")
            away_points = contest.get("away_points")
            bind_ok = False
            bind_error = None
            if contest.get("terminal_state") != "TERMINAL_STATUS_ESTABLISHED":
                bind_error = "NOT_TERMINAL"
            elif home_points is None or away_points is None:
                bind_error = "MISSING_POINTS"
            else:
                try:
                    _bind_scores_from_same_page(
                        page_text=body.decode("utf-8", "replace"),
                        contest_id=contest_id,
                        home_points=int(home_points),
                        away_points=int(away_points),
                        body=body,
                    )
                    bind_ok = True
                except (ScoringError, TypeError, ValueError) as exc:
                    bind_error = type(exc).__name__
            reconstructed.append(
                {
                    "week": week,
                    "raw_sha256": sha256_bytes(body),
                    "ncaa_com_contest_id": contest_id,
                    "home_name": home,
                    "away_name": away,
                    "home_points": home_points,
                    "away_points": away_points,
                    "terminal_state": contest.get("terminal_state"),
                    "bind_scores_from_same_page": bind_ok,
                    "bind_error": bind_error,
                    "trust_classification": "UNTRUSTED_SHADOW",
                }
            )
    payload = {
        "artifact_type": "CYCLE32_NCAA_SCOREBOARD_FINALS_CENSUS",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "scoreboard_files": [str(path) for _, path in SCOREBOARDS],
        "contests_parsed": len(reconstructed),
        "bind_success": sum(1 for row in reconstructed if row["bind_scores_from_same_page"]),
        "historical_ncaa_contest_captures_beyond_week1_2026": 0,
        "stats_ncaa_org_403_not_admitted": True,
        "broader_historical_official_final_reconstruction": "BLOCKED_RAW_CAPTURE_ABSENT",
        "trust_classification": "UNTRUSTED_SHADOW",
        "missing_raw": missing_raw,
        "rows": reconstructed,
    }
    out = OUT / "science" / "CYCLE32_NCAA_SCOREBOARD_FINALS_CENSUS.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "contests_parsed": payload["contests_parsed"],
                "bind_success": payload["bind_success"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
