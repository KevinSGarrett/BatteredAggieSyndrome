"""Query demonstrations for Cycle 33 research consumers."""

from __future__ import annotations

import json
from pathlib import Path

from aggie_analytics.cycle33.query import coach_career, connect, team_staff, unresolved_roles

DB = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science\cycle33_user_coaches.sqlite"
)
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science\CYCLE33_QUERY_DEMONSTRATIONS.json"
)


def slim(rows: list[dict], limit: int = 12) -> list[dict]:
    keep = (
        "team",
        "season",
        "role_column",
        "person",
        "source_title",
        "disposition",
        "subdivision",
        "verified",
        "pit_admitted",
    )
    out = []
    for row in rows[:limit]:
        out.append({key: row.get(key) for key in keep})
    return out


def main() -> int:
    conn = connect(DB)
    try:
        air_force = team_staff(conn, team="Air Force", season="2018")
        lehigh = team_staff(conn, team="Lehigh", season="2026")
        troy = coach_career(conn, person="Troy Calhoun")
        unresolved = unresolved_roles(conn)
        payload = {
            "artifact_type": "CYCLE33_QUERY_DEMONSTRATIONS",
            "database": str(DB),
            "no_private_default_path": True,
            "historical_fbs": {
                "team": "Air Force",
                "season": "2018",
                "row_count": len(air_force),
                "people": sorted({row.get("person") for row in air_force if row.get("person")}),
                "sample": slim(air_force),
            },
            "current_fcs": {
                "team": "Lehigh",
                "season": "2026",
                "row_count": len(lehigh),
                "people": sorted({row.get("person") for row in lehigh if row.get("person")}),
                "sample": slim(lehigh),
            },
            "multi_school_or_multi_season_career": {
                "person": "Troy Calhoun",
                "row_count": len(troy),
                "seasons": sorted({str(row.get("season")) for row in troy}),
                "teams": sorted({str(row.get("team")) for row in troy}),
            },
            "unresolved_not_omitted": {
                "row_count": len(unresolved),
                "sample": slim(unresolved),
            },
            "pit_admitted": False,
            "not_market_or_model_promotion": True,
        }
    finally:
        conn.close()
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "air_force_2018": payload["historical_fbs"]["row_count"],
                "lehigh_2026": payload["current_fcs"]["row_count"],
                "troy_calhoun": payload["multi_school_or_multi_season_career"]["row_count"],
                "unresolved": payload["unresolved_not_omitted"]["row_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
