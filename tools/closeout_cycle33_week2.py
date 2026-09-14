"""Actual-clock Week 2 closeout. Does not arm captures or invent forecasts."""

from __future__ import annotations

import json
from pathlib import Path

from aggie_analytics.cycle33.week2 import historical_tamu_asu_row, utc_now

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z\implementation_output\science"
)
LEASE_ROOTS = [
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle29_work\leases"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle27\leases"),
]


def main() -> int:
    now = utc_now()
    tamu = historical_tamu_asu_row(now)
    leases = []
    for root in LEASE_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("lease.json"):
            leases.append(
                {
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "inspected": True,
                    "kill_by_pid_forbidden": True,
                }
            )
    payload = {
        "artifact_type": "CYCLE33_WEEK2_CLOSEOUT",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "clock_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tamu_asu_september_12": tamu,
        "rearm_forbidden": True,
        "invented_forecast": False,
        "leases_inspected": leases,
        "new_scheduler_installed": False,
        "week2_outcomes_do_not_tune_or_select": True,
        "forecast_classification": "UNTRUSTED_SHADOW",
        "predecessor_official_reconstruction": {
            "path": r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output\science\CYCLE32_NCAA_SCOREBOARD_FINALS_CENSUS.json",
            "observation_count": 198,
            "distinct_contest_ids": 99,
            "week_labels": ["2026/00"],
            "observation_count_is_not_unique_game_count": True,
            "requested_week_is_not_source_week": True,
        },
        "national_week2_contest_census": "INCOMPLETE_PENDING_OFFICIAL_SCHEDULE_REFRESH",
        "thursday_friday_already_played": "NOT_YET_CENSUS_FROM_OFFICIAL_AUTHORITY",
        "neutral_postponed_cancelled": "NOT_YET_CENSUS_FROM_OFFICIAL_AUTHORITY",
        "owner": "BAT-705",
        "no_missouri_state_identity_reuse": True,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "CYCLE33_WEEK2_CLOSEOUT.json"
    dest.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(dest), "t24h": tamu["t24h_disposition"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
