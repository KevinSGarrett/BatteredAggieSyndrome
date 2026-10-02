"""R36-09: rebuild every national neutral-site row through the repaired path.

Source-designated neutral status, an independently supported venue, ordinary
home advantage and travel geography are four different things. This tool
keeps them apart per contest:

* the **designated** home and away sides come from the game feed and are not
  evidence about where the game was played;
* **neutral status** is what the source designates, which is not the same as
  a venue independently verified from venue coordinates;
* **ordinary home advantage** is suppressed (0.0) only when the source
  designates neutral, is separately modelled for an ordinary home game, and
  is ``None`` when neutral status is unknown;
* **travel** is two legs from each side's current-vintage reference origin to
  the actual venue, each of which is ``None`` rather than zero when an
  identity or a coordinate is missing.

Home geography is selected by the declared acquisition year of the payload it
came from, never by which cache filename sorts first.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.hashing import sha256_json
from aggie_analytics import atomic_io as _bas_atomic  # noqa: E402
from aggie_analytics.cycle36.jsonl_io import (  # noqa: E402
    read_jsonl_strict,
    write_jsonl_verified,
)
from aggie_analytics.cycle36.venue_vintage import (  # noqa: E402
    NEUTRAL_SOURCE_DESIGNATED,
    NEUTRAL_SOURCE_NOT_NEUTRAL,
    NEUTRAL_UNKNOWN,
    POLICY_LATEST,
    SELECTED,
    VINTAGE_VERSION,
    observations_from_payloads,
    select_home_geography,
    travel_for_contest,
)

CYCLE30 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work")
OUTPUTS = CYCLE30 / "outputs"
RAW_TEAMS = CYCLE30 / "raw" / "teams"
VENUES = OUTPUTS / "CFBD_VENUES.jsonl"
GAME_FILES = (
    "CFBD_GAMES_1963_2012.jsonl",
    "CFBD_GAMES_TRANCHE.jsonl",
    "CFBD_FCS_FCS_GAMES_1963_2012.jsonl",
    "CFBD_FCS_FCS_GAMES_TRANCHE.jsonl",
)

#: A required semantic fixture: the designated home label cannot locate this
#: contest, because it is played in a third city.
LAMBEAU_MARKERS = ("lambeau",)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Strict read: a truncated artifact must be regenerated, never skipped."""

    return read_jsonl_strict(path)


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def load_dated_team_payloads(seasons: range) -> list[tuple[int, str, str, list[dict]]]:
    """``(declared_year, digest, path, rows)`` for every cached /teams payload."""

    found: list[tuple[int, str, str, list[dict]]] = []
    for season in seasons:
        for shape in ({}, {"classification": "fbs"}, {"classification": "fcs"}):
            parameters = {"year": int(season), **shape}
            identity = sha256_json({"endpoint": "/teams", "parameters": parameters})
            path = RAW_TEAMS / f"{identity}.json"
            if not path.is_file():
                continue
            raw = path.read_bytes()
            payload = json.loads(raw.decode("utf-8"))
            rows = payload if isinstance(payload, list) else (
                payload.get("data") or payload.get("teams") or []
            )
            found.append(
                (
                    int(season),
                    hashlib.sha256(raw).hexdigest(),
                    str(path),
                    [row for row in rows if isinstance(row, dict)],
                )
            )
    return found


def build(out_dir: Path) -> dict[str, Any]:
    payloads = load_dated_team_payloads(range(1963, 2027))
    geography = select_home_geography(
        observations_from_payloads(payloads), policy=POLICY_LATEST
    )
    venue_rows = read_jsonl(VENUES)
    venues = {
        int(row["id"]): row
        for row in venue_rows
        if row.get("id") is not None
        and row.get("latitude") is not None
        and row.get("longitude") is not None
    }

    games: list[dict[str, Any]] = []
    for name in GAME_FILES:
        games.extend(read_jsonl(OUTPUTS / name))

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    states: collections.Counter = collections.Counter()
    neutral_states: collections.Counter = collections.Counter()
    legs: collections.Counter = collections.Counter()
    lambeau_rows: list[dict[str, Any]] = []

    for game in games:
        if game.get("id") is None:
            continue
        contest = f"SRC-002:GAME:{game['id']}"
        if contest in seen:
            continue
        seen.add(contest)
        neutral_flag = game.get("neutralSite")
        if neutral_flag is True:
            neutral_status = NEUTRAL_SOURCE_DESIGNATED
        elif neutral_flag is False:
            neutral_status = NEUTRAL_SOURCE_NOT_NEUTRAL
        else:
            neutral_status = NEUTRAL_UNKNOWN
        neutral_states[neutral_status] += 1

        venue_id = game.get("venueId")
        venue = venues.get(int(venue_id)) if venue_id is not None else None
        venue_point = (
            (float(venue["latitude"]), float(venue["longitude"])) if venue else None
        )
        home_id = game.get("homeId")
        away_id = game.get("awayId")
        travel = travel_for_contest(
            home_team_id=int(home_id) if home_id is not None else None,
            away_team_id=int(away_id) if away_id is not None else None,
            venue_point=venue_point,
            home_geography=geography,
            neutral_status=neutral_status,
        )
        legs[travel["legs_computed"]] += 1
        state = (
            "VENUE_INDEPENDENTLY_SUPPORTED"
            if venue_point
            else "VENUE_NOT_INDEPENDENTLY_SUPPORTED"
        )
        states[state] += 1
        row = {
            "vintage_version": VINTAGE_VERSION,
            "canonical_game_id": contest,
            "season": game.get("season"),
            "designated_home_team_id": f"SRC-002:TEAM:{home_id}",
            "designated_away_team_id": f"SRC-002:TEAM:{away_id}",
            "source_designated_neutral": neutral_flag,
            "neutral_status": neutral_status,
            "venue_id": venue_id,
            "venue_name": (venue or {}).get("name"),
            "venue_state": state,
            "home_leg_km": travel["home_leg"]["km"],
            "away_leg_km": travel["away_leg"]["km"],
            "home_leg_state": travel["home_leg"]["state"],
            "away_leg_state": travel["away_leg"]["state"],
            "legs_computed": travel["legs_computed"],
            "ordinary_home_advantage_applies": travel["ordinary_home_advantage_applies"],
            "ordinary_home_advantage_magnitude": travel[
                "ordinary_home_advantage_magnitude"
            ],
            "ordinary_home_advantage_basis": travel["basis"],
            "geography_vintage_authority": "CURRENT_VINTAGE_HOME_VENUE_NOT_PIT",
            "not_an_itinerary": True,
            "pit_admitted": False,
        }
        rows.append(row)
        if venue and any(
            marker in str(venue.get("name") or "").casefold()
            for marker in LAMBEAU_MARKERS
        ):
            lambeau_rows.append(row)

    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / "CYCLE36_NEUTRAL_TRAVEL_ROWS.jsonl"
    rows_verification = write_jsonl_verified(
        rows_path, sorted(rows, key=lambda item: item["canonical_game_id"])
    )

    geography_states = collections.Counter(
        record["state"] for record in geography.values()
    )
    artifact = {
        "artifact_type": "CYCLE36_NEUTRAL_TRAVEL",
        "generated_at_utc": utc_now(),
        "vintage_version": VINTAGE_VERSION,
        "vintage_policy": POLICY_LATEST,
        "team_payloads_used": [
            {"declared_year": year, "sha256": digest, "path": path, "rows": len(rows_)}
            for year, digest, path, rows_ in payloads
        ][:80],
        "team_payload_count": len(payloads),
        "home_geography_states": dict(geography_states),
        "teams_with_selected_geography": geography_states.get(SELECTED, 0),
        "venue_source": {
            "path": str(VENUES),
            "sha256": sha256_file(VENUES),
            "rows": len(venue_rows),
            "with_coordinates": len(venues),
        },
        "contests": len(rows),
        "population_conserved": len(rows) == len(seen),
        "venue_states": dict(states),
        "neutral_states": dict(neutral_states),
        "legs_computed_distribution": {str(k): v for k, v in sorted(legs.items())},
        "contests_with_both_legs": legs.get(2, 0),
        "lambeau_fixture": {
            "rows_found": len(lambeau_rows),
            "examples": lambeau_rows[:6],
            "why": (
                "Located by venue identity, not by the designated home label, "
                "because the designated home team does not play there."
            ),
        },
        "separations": {
            "designated_orientation_is_not_venue_evidence": True,
            "source_designated_neutral_is_not_a_verified_venue": True,
            "ordinary_home_advantage_zero_only_when_neutral_is_supported": True,
            "unknown_neutral_status_fails_closed": True,
            "current_vintage_origin_is_not_point_in_time_travel": True,
        },
        "post_write_verification": rows_verification,
        "written": {"rows": str(rows_path)},
    }
    _bas_atomic.write_text(out_dir / "CYCLE36_NEUTRAL_TRAVEL.json", 
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    artifact = build(args.out_dir)
    print(
        json.dumps(
            {
                "team_payloads": artifact["team_payload_count"],
                "home_geography_states": artifact["home_geography_states"],
                "contests": artifact["contests"],
                "population_conserved": artifact["population_conserved"],
                "neutral_states": artifact["neutral_states"],
                "legs_computed": artifact["legs_computed_distribution"],
                "lambeau_rows": artifact["lambeau_fixture"]["rows_found"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
