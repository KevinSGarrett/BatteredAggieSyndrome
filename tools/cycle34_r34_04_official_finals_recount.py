"""Cycle34 R34-04: recount official final observations/contests using the
repaired official_finals.py logic, against the real raw NCAA.com scoreboard
captures the predecessor's own reconstruction cited.

READ-ONLY against the raw capture files. Output goes ONLY to a new path
under C:\\BatteredAggieSyndrome.data\\ops\\cycle34\\. Brand-new script; does
not modify or retrofit any existing tools/*.py file.

Input: the 8 real raw NCAA.com scoreboard HTML captures referenced by the
predecessor's own CYCLE33_OFFICIAL_FINALS_SUCCESSOR.json
(C:\\BatteredAggieSyndrome.data\\ops\\cycle30_work\\raw\\ncaa\\scoreboard*-2026-0{0,1,2,3}.html,
FBS + FCS each), parsed via the EXISTING, ALREADY-REPAIRED-ELSEWHERE-UNTOUCHED
`parse_ncaa_com_scoreboard_contests` function in cycle30/acquisition.py (not
retrofit -- reused as-is; this script only adds the glue to call it and feed
its output into the repaired official_finals.competing_observations).

Known scope limit (recorded honestly, not hidden): `parse_ncaa_com_scoreboard_contests`
does not attach `home_canonical_team_id`/`away_canonical_team_id` -- that
requires a separate `bind_participants` step this script does not perform.
The MR33-03 canonical-ID-conflict fix therefore cannot be exercised against
this specific real dataset in this pass; this run instead recounts using
name-based conflict detection only (which the repair also improved -- see
official_finals.py's `names` set) and reports that limitation explicitly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle30.acquisition import parse_ncaa_com_scoreboard_contests  # noqa: E402
from aggie_analytics.cycle33.official_finals import competing_observations  # noqa: E402

RAW_ROOT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\ncaa")
SCOREBOARD_FILES = [
    "scoreboard-2026-00.html",
    "scoreboard-fcs-2026-00.html",
    "scoreboard-2026-01.html",
    "scoreboard-fcs-2026-01.html",
    "scoreboard-2026-02.html",
    "scoreboard-fcs-2026-02.html",
    "scoreboard-2026-03.html",
    "scoreboard-fcs-2026-03.html",
]
OUTPUT_DIR = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle34\20260919T_R34_receipts\pipeline_output"
)
OUTPUT_PATH = OUTPUT_DIR / "R34_04_OFFICIAL_FINALS_RECOUNT.json"


def run() -> dict:
    missing = [f for f in SCOREBOARD_FILES if not (RAW_ROOT / f).is_file()]
    if missing:
        raise SystemExit(f"missing raw scoreboard captures (read-only check): {missing}")

    observations: list[dict] = []
    per_file_counts: dict[str, int] = {}
    for filename in SCOREBOARD_FILES:
        path = RAW_ROOT / filename
        text = path.read_text(encoding="utf-8", errors="replace")
        rows = parse_ncaa_com_scoreboard_contests(text)
        per_file_counts[filename] = len(rows)
        observations.extend(rows)

    grouped = competing_observations(observations)

    result = {
        "artifact_type": "CYCLE34_R34_04_OFFICIAL_FINALS_RECOUNT",
        "read_only_inputs": [str(RAW_ROOT / f) for f in SCOREBOARD_FILES],
        "per_file_observation_counts": per_file_counts,
        "total_observations_parsed": len(observations),
        "unique_contest_count": grouped["unique_contest_count"],
        "admitted_unique_games": len(grouped["admitted_unique_games"]),
        "quarantined_conflicts": len(grouped["quarantined_conflicts"]),
        "nonfinal_contests": len(grouped.get("nonfinal_contests") or []),
        "unlabeled_observation_count": grouped.get("unlabeled_observation_count"),
        "historical_recorded": {
            "observation_count": 770,
            "unique_contest_count": 468,
            "admitted_unique_games": 290,
            "quarantined_conflicts": 0,
            "nonfinal_contests": 178,
        },
        "known_scope_limit": (
            "parse_ncaa_com_scoreboard_contests does not attach canonical team IDs; "
            "this recount exercises name-based conflict detection (also repaired this "
            "cycle) but not the MR33-03 canonical-ID-conflict path specifically -- "
            "bind_participants (a separate existing function) would be needed for that, "
            "not run this pass"
        ),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
