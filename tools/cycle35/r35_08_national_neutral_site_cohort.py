"""R35-08: the national neutral/unknown-site cohort, through actual
consumer inputs.

Cycle #35 manager follow-up (20260920T224700Z): "deliver the national
neutral/unknown-site cohort through actual consumer inputs. Designated
home/away is separate from home-field advantage; use actual stadium
geography for travel. Missing neutral/site evidence stays unknown, not
automatic home advantage. Keep row-level lineage and uncertainty."

`aggie_analytics.cycle33.neutral.ordinary_home_advantage()` is the
validated, narrow consumer this dimension is built through -- it already
refuses to coerce missing or false neutral-site evidence into a home-
advantage claim: it returns 0.0 only when neutral_site is CONFIRMED True,
and None (not-applicable/unknown) for every other case, including a
confirmed ordinary home game, because the actual home-advantage magnitude
for an ordinary game is a separate feature this function does not compute.
`travel_context()` in the same module was deliberately NOT used here after
directly confirming it raises unconditionally when venue_confirmed=False
(the precondition for calling it at all is an already-confirmed venue,
which this cohort does not have for any game -- see below); it is designed
for attaching travel distance to a single already-bound venue, not for
classifying an entire cohort's neutral-site status.

What is and is not available locally, checked directly rather than
assumed:

* Every national game row already carries its own `neutralSite` boolean
  (CFBD's own designation) -- this needs no new acquisition and covers the
  full 1963-2026 declared range. This is the entire signal this cohort is
  built from. A row whose neutralSite is missing or not a strict boolean
  is NOT dropped: it is kept with neutral_state=UNKNOWN, per "missing
  neutral/site evidence stays unknown."
* A private historical venue-assignment dataset exists
  (pit_state/historical_known_at/.../historical_venue_assignments.parquet,
  10,414 rows) with venue_id/venue_full_name/city/state per game -- but its
  OWN admission_state field reads "DEVELOPMENT_ONLY_HISTORICAL_KNOWN_AT_
  VENUE_ASSIGNMENT" for every row, it covers only 2010-2022 (a fraction of
  the declared range), and it carries no geographic coordinates. It is
  attached here as an explicitly-labeled, non-authoritative enrichment
  layer for context only -- never used to compute ordinary_home_advantage,
  confirm a venue, or promote any row's evidence layer.
* Real stadium coordinates DO exist locally and are now bound. An earlier
  version of this module asserted "no local dataset provides stadium
  latitude/longitude" and reported every travel distance as null. That was
  wrong: CYCLE30_ACQUISITION_LEDGER.json declares a cached CFBD `/venues`
  acquisition (852 venues, 806 with latitude and longitude), and the
  cached `/teams` payloads carry each team's home venue coordinates.
  Travel legs are computed from those where the game's own venue id
  resolves. Coverage is real but partial and era-bound: game rows carry a
  venueId only from 2000 onward (0% before 2000, 82% in the 2000s, 97% in
  the 2010s, 100% in the 2020s), so pre-2000 travel is a genuine
  ACQUISITION gap in the source payloads, not an unimplemented join.
  Team home venues are CURRENT-vintage, so a computed leg is a declared
  reference distance, never point-in-time historical geography, and is
  labelled CURRENT_VINTAGE_TEAM_HOME_VENUE_NOT_PIT.

* Repeated game ids are reconciled by documented acquisition authority,
  not by input order. An earlier version silently kept whichever row was
  read first, so reversing the file order changed the admitted neutral
  designation and the home-advantage result. Identical observations are
  deduplicated with all their provenance retained; a conflict that no
  declared vintage settles stays visible with every competing observation
  and its neutral designation held at UNKNOWN.

Neutral counts here are SOURCE-DESIGNATED. No independent venue
confirmation has been performed, and zero missing raw boolean flags does
not establish zero venue or temporal uncertainty.

Nothing here is PIT-admitted.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle33.neutral import ordinary_home_advantage  # noqa: E402

OUTPUTS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
GAME_SOURCES = (
    OUTPUTS / "CFBD_GAMES_1963_2012.jsonl",
    OUTPUTS / "CFBD_GAMES_TRANCHE.jsonl",
    OUTPUTS / "CFBD_FCS_FCS_GAMES_1963_2012.jsonl",
    OUTPUTS / "CFBD_FCS_FCS_GAMES_TRANCHE.jsonl",
)
TEAM_PREFIX = "SRC-002:TEAM:"
GAME_PREFIX = "SRC-002:GAME:"

#: Development-only, not PIT-admitted, 2010-2022 only, no coordinates.
#: Attached as a disclosed enrichment layer; see module docstring.
VENUE_ENRICHMENT_PARQUET = Path(
    r"C:\BatteredAggieSyndrome.data\pit_state\historical_known_at\sha256"
    r"\b84ef29b9d4b548d82b3797a467982010b591b127fefadeaa2567584290c554b"
    r"\historical_venue_assignments.parquet"
)

#: A real, already-acquired CFBD /venues payload: 852 venues, 806 carrying
#: latitude and longitude. Declared in CYCLE30_ACQUISITION_LEDGER.json as
#: route "/venues", receipt dfc8daff..., retrieved 2026-09-09T18:08:43Z.
#: Its existence is why "no local stadium coordinates" was wrong.
VENUE_COORDINATES = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\venues"
    r"\86af256ba80c8b9961950607800057c188f4aec7034c4ac774f4dcf9475bfc93.json"
)
#: Cached CFBD /teams payloads. Each team carries a `location` block with
#: its CURRENT home venue id and coordinates. Current-vintage: usable as a
#: declared reference point, never as point-in-time historical geography.
TEAM_PAYLOAD_DIR = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\teams")

#: Documented acquisition authority per source file, derived from the real
#: acquisition ledgers rather than assumed. The row counts below match the
#: files exactly, which is how each file was mapped to its ledger:
#:   CFBD_GAMES_1963_2012.jsonl  <- CYCLE30_HISTORICAL_GAMES_LEDGER.json
#:                                  /games?year=, 50 attempts, 42,038 rows
#:   CFBD_GAMES_TRANCHE.jsonl    <- CYCLE30_ACQUISITION_LEDGER.json
#:                                  /games?classification=&year=, 13
#:                                  attempts, 10,067 rows
#: The two FCS-vs-FCS overlay files do not match any located ledger's
#: totals, so their acquisition vintage is UNDECLARED here. An undeclared
#: vintage never outranks a declared one -- that is itself an authority
#: fact, not a gap to paper over.
SOURCE_AUTHORITY: dict[str, dict[str, Any]] = {
    "CFBD_GAMES_1963_2012.jsonl": {
        "route": "/games",
        "parameters": ["year"],
        "declared_vintage_utc": "2026-09-09T18:07:41Z",
        "ledger": "CYCLE30_HISTORICAL_GAMES_LEDGER.json",
        "vintage_declared": True,
    },
    "CFBD_GAMES_TRANCHE.jsonl": {
        "route": "/games",
        "parameters": ["classification", "year"],
        "declared_vintage_utc": "2026-09-09T18:08:43Z",
        "ledger": "CYCLE30_ACQUISITION_LEDGER.json",
        "vintage_declared": True,
    },
    "CFBD_FCS_FCS_GAMES_1963_2012.jsonl": {
        "route": "/games",
        "parameters": ["classification", "year"],
        "declared_vintage_utc": None,
        "ledger": None,
        "vintage_declared": False,
    },
    "CFBD_FCS_FCS_GAMES_TRANCHE.jsonl": {
        "route": "/games",
        "parameters": ["classification", "year"],
        "declared_vintage_utc": None,
        "ledger": None,
        "vintage_declared": False,
    },
}

#: Reconciliation outcomes for a repeated game id.
SINGLE_OBSERVATION = "SINGLE_OBSERVATION"
DEDUPLICATED_IDENTICAL = "DEDUPLICATED_IDENTICAL_OBSERVATIONS"
CONFLICT_RESOLVED_BY_VINTAGE = "CONFLICT_RESOLVED_BY_DECLARED_VINTAGE"
CONFLICT_UNRESOLVED = "CONFLICT_UNRESOLVED_NO_AUTHORITY_BASIS"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_venue_coordinates(path: Path = VENUE_COORDINATES) -> tuple[dict[int, dict], dict]:
    """Real venue coordinates, or an honest empty result with a reason."""

    stats: dict[str, Any] = {"path": str(path), "mounted": path.is_file()}
    if not path.is_file():
        stats["state"] = "VENUE_COORDINATES_NOT_MOUNTED"
        return {}, stats
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_id: dict[int, dict] = {}
    for row in payload:
        if row.get("latitude") is None or row.get("longitude") is None:
            continue
        by_id[int(row["id"])] = {
            "venue_id": row.get("id"),
            "venue_name": row.get("name"),
            "city": row.get("city"),
            "state": row.get("state"),
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
        }
    stats.update(
        {
            "state": "MOUNTED",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "venues_total": len(payload),
            "venues_with_coordinates": len(by_id),
            "declared_route": "/venues",
            "declared_ledger": "CYCLE30_ACQUISITION_LEDGER.json",
            "declared_vintage_utc": "2026-09-09T18:08:43Z",
        }
    )
    return by_id, stats


def load_team_home_venues(directory: Path = TEAM_PAYLOAD_DIR) -> tuple[dict[int, dict], dict]:
    """Each team's CURRENT home venue coordinates.

    This is a current-vintage reference point, not point-in-time historical
    geography: a team's present stadium is not necessarily where it played
    in 1974. Every distance derived from it is labelled accordingly.
    """

    stats: dict[str, Any] = {"path": str(directory), "mounted": directory.is_dir()}
    if not directory.is_dir():
        stats["state"] = "TEAM_PAYLOADS_NOT_MOUNTED"
        return {}, stats
    by_team: dict[int, dict] = {}
    files = sorted(directory.glob("*.json"))
    for item in files:
        try:
            payload = json.loads(item.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        for team in payload if isinstance(payload, list) else []:
            location = team.get("location") or {}
            if location.get("latitude") is None or location.get("longitude") is None:
                continue
            by_team.setdefault(
                int(team["id"]),
                {
                    "home_venue_id": location.get("id"),
                    "home_venue_name": location.get("name"),
                    "latitude": float(location["latitude"]),
                    "longitude": float(location["longitude"]),
                },
            )
    stats.update(
        {
            "state": "MOUNTED",
            "payload_files": len(files),
            "teams_with_home_coordinates": len(by_team),
            "vintage_authority": "CURRENT_VINTAGE_HOME_VENUE_NOT_PIT",
        }
    )
    return by_team, stats


def great_circle_km(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Great-circle distance in kilometres (spherical earth, 6371.0088 km)."""

    import math

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * 6371.0088 * math.asin(math.sqrt(a))


def identity_tuple(raw: dict[str, Any]) -> tuple:
    """The identity a repeated game id must agree on to be a duplicate."""

    return (
        raw.get("homeId"),
        raw.get("awayId"),
        raw.get("season"),
        raw.get("neutralSite") if isinstance(raw.get("neutralSite"), bool) else None,
        raw.get("venueId"),
    )


def reconcile_observations(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Reconcile every observation of one game id.

    Input order previously decided which row was admitted: the first row
    seen won and the rest were counted as SKIPPED_DUPLICATE_GAME_ID, so
    reversing the file order changed the admitted neutral designation and
    the home-advantage result. Resolution is now by documented declared
    vintage, and a conflict that no declared authority settles stays
    visible and unresolved rather than being silently decided.
    """

    distinct: dict[tuple, list[dict[str, Any]]] = {}
    for item in observations:
        distinct.setdefault(identity_tuple(item["raw"]), []).append(item)

    if len(observations) == 1:
        return {
            "state": SINGLE_OBSERVATION,
            "admitted": observations[0],
            "observations": observations,
            "distinct_identities": 1,
        }
    if len(distinct) == 1:
        return {
            "state": DEDUPLICATED_IDENTICAL,
            "admitted": observations[0],
            "observations": observations,
            "distinct_identities": 1,
        }

    dated = [o for o in observations if o["authority"].get("declared_vintage_utc")]
    if dated:
        newest = max(o["authority"]["declared_vintage_utc"] for o in dated)
        winners = [
            o for o in dated if o["authority"]["declared_vintage_utc"] == newest
        ]
        if len({identity_tuple(o["raw"]) for o in winners}) == 1:
            return {
                "state": CONFLICT_RESOLVED_BY_VINTAGE,
                "admitted": winners[0],
                "observations": observations,
                "distinct_identities": len(distinct),
                "resolved_by": f"newest declared acquisition vintage {newest}",
            }
    return {
        "state": CONFLICT_UNRESOLVED,
        "admitted": None,
        "observations": observations,
        "distinct_identities": len(distinct),
        "resolved_by": None,
    }


def resolve_neutral_state(value: Any) -> tuple[bool | None, str]:
    """Strict true/false/unknown, kept visible rather than dropped.

    Mirrors aggie_analytics.cycle33.neutral._resolve_neutral_site's
    true/false/unknown discipline (that helper is private to its module;
    this cohort's own strict, independent check is reimplemented here
    rather than reaching past the leading underscore) -- a raw CFBD
    `neutralSite` value that is not a strict Python bool is UNKNOWN, never
    coerced to False by truthiness.
    """

    if isinstance(value, bool):
        return value, ("TRUE" if value else "FALSE")
    return None, "UNKNOWN"


def load_venue_enrichment(
    parquet_path: Path = VENUE_ENRICHMENT_PARQUET,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """source_game_id -> venue enrichment row, explicitly labeled
    non-authoritative. Absent mount or absent polars are both honest,
    reportable states, not a silent empty result indistinguishable from
    "no venue exists for this game"."""

    stats: dict[str, Any] = {
        "path": str(parquet_path),
        "mounted": parquet_path.is_file(),
    }
    if not parquet_path.is_file():
        stats["state"] = "VENUE_ENRICHMENT_NOT_MOUNTED"
        return {}, stats
    try:
        import polars as pl
    except ImportError:
        stats["state"] = "POLARS_UNAVAILABLE"
        return {}, stats
    frame = pl.read_parquet(parquet_path)
    stats["sha256"] = hashlib.sha256(parquet_path.read_bytes()).hexdigest()
    stats["rows"] = frame.height
    stats["seasons"] = sorted({int(v) for v in frame["season"].to_list()})
    stats["admission_states"] = sorted(set(frame["admission_state"].to_list()))
    stats["state"] = "MOUNTED_DEVELOPMENT_ONLY_NOT_PIT_ADMITTED"
    by_game: dict[str, dict[str, Any]] = {}
    for row in frame.iter_rows(named=True):
        game_id = str(row.get("source_game_id") or "")
        if not game_id:
            continue
        by_game[game_id] = {
            "venue_id": row.get("venue_id"),
            "venue_full_name": row.get("venue_full_name"),
            "venue_address_city": row.get("venue_address_city"),
            "venue_address_state": row.get("venue_address_state"),
            "venue_indoor": row.get("venue_indoor"),
            "admission_state": row.get("admission_state"),
        }
    return by_game, stats


def build_national_cohort(
    game_sources: tuple[Path, ...] = GAME_SOURCES,
    venue_enrichment_parquet: Path = VENUE_ENRICHMENT_PARQUET,
    venue_coordinates_path: Path = VENUE_COORDINATES,
    team_payload_dir: Path = TEAM_PAYLOAD_DIR,
) -> dict[str, Any]:
    venue_enrichment, venue_stats = load_venue_enrichment(venue_enrichment_parquet)
    venue_coords, venue_coord_stats = load_venue_coordinates(venue_coordinates_path)
    team_homes, team_home_stats = load_team_home_venues(team_payload_dir)

    source_stats: list[dict[str, Any]] = []
    state_counts: Counter = Counter()
    neutral_state_counts: Counter = Counter()
    reconciliation_counts: Counter = Counter()
    travel_counts: Counter = Counter()

    # Pass 1: collect every observation with its own provenance.
    observations: dict[str, list[dict[str, Any]]] = {}
    for source in game_sources:
        raw_rows = read_jsonl(source)
        digest = (
            hashlib.sha256(source.read_bytes()).hexdigest() if source.is_file() else None
        )
        authority = dict(
            SOURCE_AUTHORITY.get(
                source.name,
                {
                    "route": None,
                    "parameters": [],
                    "declared_vintage_utc": None,
                    "ledger": None,
                    "vintage_declared": False,
                },
            )
        )
        source_stats.append(
            {
                "path": str(source),
                "exists": source.is_file(),
                "rows": len(raw_rows),
                "sha256": digest,
                "authority": authority,
            }
        )
        for line_number, raw in enumerate(raw_rows, start=1):
            raw_game_id = str(raw.get("id") or "")
            if not raw_game_id:
                state_counts["SKIPPED_NO_GAME_ID"] += 1
                continue
            observations.setdefault(raw_game_id, []).append(
                {
                    "raw": raw,
                    "provenance": {
                        "source_file": source.name,
                        "source_path": str(source),
                        "source_sha256": digest,
                        "locator": f"{source.name}:line:{line_number}",
                    },
                    "authority": authority,
                }
            )

    # Pass 2: reconcile, then emit one row per game id.
    rows: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    seasons_seen: set[int] = set()
    enrichment_matched = 0

    for raw_game_id in sorted(observations):
        items = observations[raw_game_id]
        reconciled = reconcile_observations(items)
        reconciliation_counts[reconciled["state"]] += 1
        state_counts["DUPLICATE_OBSERVATIONS_RECONCILED"] += len(items) - 1

        unresolved = reconciled["state"] == CONFLICT_UNRESOLVED
        admitted = reconciled["admitted"] or items[0]
        raw = admitted["raw"]
        game_id = GAME_PREFIX + raw_game_id

        home_raw, away_raw = raw.get("homeId"), raw.get("awayId")
        if home_raw is None or away_raw is None:
            state_counts["SKIPPED_MISSING_PARTICIPANT_ID"] += 1
            continue

        season = raw.get("season")
        if isinstance(season, int):
            seasons_seen.add(season)

        if unresolved:
            # No declared authority settles which observation is true, so
            # no neutral designation is claimed for this game.
            neutral_site, neutral_state = None, "UNKNOWN"
            conflicts.append(
                {
                    "canonical_game_id": game_id,
                    "distinct_identities": reconciled["distinct_identities"],
                    "competing_observations": [
                        {
                            "provenance": o["provenance"],
                            "authority": o["authority"],
                            "home_id": o["raw"].get("homeId"),
                            "away_id": o["raw"].get("awayId"),
                            "season": o["raw"].get("season"),
                            "neutral_site_raw": o["raw"].get("neutralSite"),
                            "venue_id": o["raw"].get("venueId"),
                        }
                        for o in items
                    ],
                }
            )
        else:
            neutral_site, neutral_state = resolve_neutral_state(raw.get("neutralSite"))

        advantage = ordinary_home_advantage(neutral_site=neutral_site)

        venue_id = raw.get("venueId")
        venue_point = venue_coords.get(int(venue_id)) if isinstance(venue_id, int) else None
        home_point = team_homes.get(int(home_raw)) if home_raw is not None else None
        away_point = team_homes.get(int(away_raw)) if away_raw is not None else None

        def leg(point, _venue=venue_point):
            if _venue is None or point is None:
                return None
            return round(
                great_circle_km(
                    point["latitude"],
                    point["longitude"],
                    _venue["latitude"],
                    _venue["longitude"],
                ),
                3,
            )

        home_km, away_km = leg(home_point), leg(away_point)
        if venue_point is None:
            travel_reason = (
                "GAME_VENUE_ID_ABSENT_IN_SOURCE"
                if venue_id is None
                else "GAME_VENUE_ID_NOT_IN_ACQUIRED_VENUE_COORDINATES"
            )
        elif home_km is None or away_km is None:
            travel_reason = "PARTICIPANT_HOME_VENUE_COORDINATES_UNAVAILABLE"
        else:
            travel_reason = None
        travel_counts[travel_reason or "BOTH_LEGS_COMPUTED"] += 1

        enrichment = venue_enrichment.get(raw_game_id)
        if enrichment is not None:
            enrichment_matched += 1

        neutral_state_counts[neutral_state] += 1
        state_counts["ROW_EMITTED"] += 1
        rows.append(
            {
                "canonical_game_id": game_id,
                "season": season,
                "home_canonical_team_id": TEAM_PREFIX + str(home_raw),
                "away_canonical_team_id": TEAM_PREFIX + str(away_raw),
                "designated_home_team_id": TEAM_PREFIX + str(home_raw),
                "designated_away_team_id": TEAM_PREFIX + str(away_raw),
                "neutral_site": neutral_site,
                "neutral_state": neutral_state,
                "neutral_authority": "SOURCE_DESIGNATED_NOT_INDEPENDENTLY_CONFIRMED",
                "ordinary_home_advantage": advantage,
                "reconciliation_state": reconciled["state"],
                "observation_count": len(items),
                "resolved_by": reconciled.get("resolved_by"),
                "admitted_provenance": admitted["provenance"],
                "admitted_authority": admitted["authority"],
                "all_observation_locators": [o["provenance"]["locator"] for o in items],
                "venue_id": venue_id,
                "venue_point": venue_point,
                "home_travel_km": home_km,
                "away_travel_km": away_km,
                "travel_unavailable_reason": travel_reason,
                "travel_reference_authority": (
                    None if travel_reason else "CURRENT_VINTAGE_TEAM_HOME_VENUE_NOT_PIT"
                ),
                "venue_enrichment": enrichment,
                "venue_enrichment_authority": (
                    "DEVELOPMENT_ONLY_NOT_PIT_ADMITTED"
                    if enrichment is not None
                    else "NOT_AVAILABLE"
                ),
                "pit_admitted": False,
            }
        )

    computed = travel_counts.get("BOTH_LEGS_COMPUTED", 0)
    return {
        "artifact_type": "CYCLE35_R35_08_NATIONAL_NEUTRAL_SITE_COHORT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_game_sources": source_stats,
        "venue_enrichment": venue_stats,
        "venue_coordinates": venue_coord_stats,
        "team_home_venues": team_home_stats,
        "seasons_covered": sorted(seasons_seen),
        "row_count": len(rows),
        "state_counts": dict(state_counts),
        "neutral_state_counts": dict(neutral_state_counts),
        "neutral_counts_are_source_designated": True,
        "reconciliation_counts": dict(reconciliation_counts),
        "unresolved_conflicts": conflicts,
        "unresolved_conflict_count": len(conflicts),
        "venue_enrichment_matched_row_count": enrichment_matched,
        "travel_coverage": {
            "counts": dict(travel_counts),
            "rows_with_both_legs": computed,
            "rows_without_travel": len(rows) - computed,
            "fraction_with_both_legs": round(computed / len(rows), 6) if rows else None,
        },
        "rows": rows,
        "designated_home_away_is_not_home_field_advantage": True,
        "missing_neutral_evidence_stays_unknown_not_home_advantage": True,
        "duplicate_resolution_is_by_declared_authority_not_input_order": True,
        "travel_uses_current_vintage_home_venues_not_pit_geography": True,
        "zero_missing_neutral_flags_is_not_zero_venue_or_temporal_uncertainty": True,
        "venue_enrichment_is_development_only_not_pit_admitted": True,
        "pit_admitted": False,
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = build_national_cohort()
    (out_dir / "R35_08_NATIONAL_NEUTRAL_SITE_COHORT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(
        {
            "row_count": result["row_count"],
            "seasons_covered_min_max": (
                [min(result["seasons_covered"]), max(result["seasons_covered"])]
                if result["seasons_covered"] else None
            ),
            "state_counts": result["state_counts"],
            "neutral_state_counts": result["neutral_state_counts"],
            "venue_enrichment_matched_row_count": result["venue_enrichment_matched_row_count"],
            "venue_enrichment_state": result["venue_enrichment"].get("state"),
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
