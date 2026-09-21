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
* No local dataset provides stadium latitude/longitude. Actual travel
  distance is therefore not computed by this cohort at all: every row
  reports home_travel_distance/away_travel_distance as None, honestly,
  rather than inferred from an unconfirmed location. Building it would
  require either real coordinates (not present) or calling
  travel_context() with a fabricated venue_confirmed=True, which the
  module exists specifically to refuse.

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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


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
) -> dict[str, Any]:
    venue_enrichment, venue_stats = load_venue_enrichment(venue_enrichment_parquet)
    source_stats: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    state_counts: Counter = Counter()
    neutral_state_counts: Counter = Counter()
    enrichment_matched = 0
    seasons_seen: set[int] = set()
    seen_game_ids: set[str] = set()

    for source in game_sources:
        raw_rows = read_jsonl(source)
        source_stats.append(
            {
                "path": str(source),
                "exists": source.is_file(),
                "rows": len(raw_rows),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest()
                if source.is_file()
                else None,
            }
        )
        for raw in raw_rows:
            raw_game_id = str(raw.get("id") or "")
            if not raw_game_id:
                state_counts["SKIPPED_NO_GAME_ID"] += 1
                continue
            game_id = GAME_PREFIX + raw_game_id
            if game_id in seen_game_ids:
                state_counts["SKIPPED_DUPLICATE_GAME_ID"] += 1
                continue
            seen_game_ids.add(game_id)

            home_raw = raw.get("homeId")
            away_raw = raw.get("awayId")
            if home_raw is None or away_raw is None:
                state_counts["SKIPPED_MISSING_PARTICIPANT_ID"] += 1
                continue
            home_id = TEAM_PREFIX + str(home_raw)
            away_id = TEAM_PREFIX + str(away_raw)

            season = raw.get("season")
            if isinstance(season, int):
                seasons_seen.add(season)

            neutral_site, neutral_state = resolve_neutral_state(raw.get("neutralSite"))
            advantage = ordinary_home_advantage(neutral_site=neutral_site)

            enrichment = venue_enrichment.get(raw_game_id)
            if enrichment is not None:
                enrichment_matched += 1

            neutral_state_counts[neutral_state] += 1
            state_counts["ROW_EMITTED"] += 1
            rows.append(
                {
                    "canonical_game_id": game_id,
                    "season": season,
                    "home_canonical_team_id": home_id,
                    "away_canonical_team_id": away_id,
                    "designated_home_team_id": home_id,
                    "designated_away_team_id": away_id,
                    "neutral_site": neutral_site,
                    "neutral_state": neutral_state,
                    "ordinary_home_advantage": advantage,
                    "home_travel_distance": None,
                    "away_travel_distance": None,
                    "travel_distance_unavailable_reason": (
                        "NO_LOCAL_STADIUM_COORDINATES"
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

    return {
        "artifact_type": "CYCLE35_R35_08_NATIONAL_NEUTRAL_SITE_COHORT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_game_sources": source_stats,
        "venue_enrichment": venue_stats,
        "seasons_covered": sorted(seasons_seen),
        "row_count": len(rows),
        "state_counts": dict(state_counts),
        "neutral_state_counts": dict(neutral_state_counts),
        "venue_enrichment_matched_row_count": enrichment_matched,
        "rows": rows,
        "designated_home_away_is_not_home_field_advantage": True,
        "missing_neutral_evidence_stays_unknown_not_home_advantage": True,
        "no_local_stadium_coordinates_available_travel_distance_always_unknown": True,
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
