r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-09: rebuild every cached national contest through the repaired site
labelling, with source confirmation from a second publisher and both
travel legs, and draw the independent sample the acceptance requires.

Inputs are the cached files the Cycle 36 build read -- the game feed, the
provider venue index, the dated /teams payloads -- plus the cached
encyclopedia revisions, whose team-season schedule tables are the second
publisher. No network request is made.

What changed from Cycle 36 (MF36-14, MR35R-09, TP37-09):

* a venue id that resolves in the provider's own index is labelled
  ``PROVIDER_VENUE_INDEX_MATCH_NOT_INDEPENDENT``; ``INDEPENDENTLY_CONFIRMED``
  needs the second publisher to agree on the date and the site city;
* a game id carried by more than one feed file is compared field by field;
  identical copies collapse, and copies that disagree on site, date,
  designation or neutral flag are kept as a conflict with no site selected,
  instead of the first file winning;
* each leg carries a time-zone shift at kickoff and the elevation change,
  and each side's rest days are read from the same feed;
* a team whose home venue differs across declared vintages is reported as
  relocated; its origin is the declared latest vintage and says so.

Rows go to the evidence root; the summary counts every state by neutral
status and by FBS/FCS; the sample is stratified and deterministic.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
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
from aggie_analytics.cycle36.venue_vintage import (  # noqa: E402
    POLICY_LATEST,
    SELECTED,
    observations_from_payloads,
    select_home_geography,
)
from aggie_analytics.cycle37 import contest_site as site  # noqa: E402

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
CYCLE30 = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle30_work")
OUTPUTS = CYCLE30 / "outputs"
RAW_TEAMS = CYCLE30 / "raw" / "teams"
WIKIMEDIA = CYCLE30 / "raw" / "wikimedia"
VENUES = OUTPUTS / "CFBD_VENUES.jsonl"
GAME_FILES = ("CFBD_GAMES_1963_2012.jsonl", "CFBD_GAMES_TRANCHE.jsonl",
              "CFBD_FCS_FCS_GAMES_1963_2012.jsonl", "CFBD_FCS_FCS_GAMES_TRANCHE.jsonl")
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
VALIDATION = Path(r"C:/BatteredAggieSyndrome.validation/c37r-171601")

#: Fields on which two copies of one game must agree to be the same reading.
SITE_FIELDS = ("venueId", "neutralSite", "startDate", "homeId", "awayId", "season")
TITLE = re.compile(r"^(\d{4}) (.+) football team$")
#: The sample crosses neutral status, classification and venue support, so
#: every check (distance, time zone, confirmation) is exercised in every
#: neutral/classification cell that has contests of that kind. Stratifying
#: on neutral status and classification alone drew mostly contests with no
#: venue id, where the distance checks would have been vacuous.
SAMPLE_PER_STRATUM = 5


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError as error:
                    raise SystemExit(f"{path}:{number} is not JSON ({error}); regenerate, do not skip") from error
    return rows


# -------------------------------------------------------------- the inputs
def load_games() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """One reading per game id, or a declared conflict. File order decides nothing."""

    copies: dict[Any, list[tuple[str, dict[str, Any]]]] = collections.defaultdict(list)
    for name in GAME_FILES:
        for row in read_jsonl(OUTPUTS / name):
            if row.get("id") is not None:
                copies[row["id"]].append((name, row))
    games, conflicts = [], []
    duplicate_identical = 0
    for game_id in sorted(copies, key=str):
        readings = copies[game_id]
        distinct = {tuple(json.dumps(r.get(f), sort_keys=True) for f in SITE_FIELDS) for _, r in readings}
        if len(distinct) == 1:
            duplicate_identical += len(readings) - 1
            games.append(readings[0][1])
        else:
            conflicts.append({"game_id": game_id, "files": [n for n, _ in readings],
                              "readings": [{f: r.get(f) for f in SITE_FIELDS} for _, r in readings]})
    return games, {"files": {n: sha256_file(OUTPUTS / n) for n in GAME_FILES},
                   "unique_games": len(games), "identical_duplicate_copies": duplicate_identical,
                   "conflicting_game_ids": len(conflicts), "conflicts": conflicts[:200]}


def load_venues() -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    rows = read_jsonl(VENUES)
    by_id: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        if row.get("id") is not None:
            by_id[int(row["id"])].append(row)
    venues, conflicting = {}, []
    for venue_id, readings in by_id.items():
        if len({json.dumps(r, sort_keys=True) for r in readings}) == 1:
            venues[venue_id] = readings[0]
        else:
            conflicting.append(venue_id)
    return venues, {"path": str(VENUES), "sha256": sha256_file(VENUES), "rows": len(rows),
                    "with_coordinates": sum(1 for v in venues.values() if v.get("latitude") is not None),
                    "with_timezone": sum(1 for v in venues.values() if v.get("timezone")),
                    "conflicting_venue_ids": sorted(conflicting)}


def load_team_payloads() -> list[tuple[int, str, str, list[dict[str, Any]]]]:
    found = []
    for season in range(1963, 2027):
        for shape in ({}, {"classification": "fbs"}, {"classification": "fcs"}):
            identity = sha256_json({"endpoint": "/teams", "parameters": {"year": season, **shape}})
            path = RAW_TEAMS / f"{identity}.json"
            if path.is_file():
                raw = path.read_bytes()
                payload = json.loads(raw.decode("utf-8"))
                rows = payload if isinstance(payload, list) else (payload.get("data") or payload.get("teams") or [])
                found.append((season, hashlib.sha256(raw).hexdigest(), str(path),
                              [r for r in rows if isinstance(r, dict)]))
    return found


def origins(payloads: list[tuple[int, str, str, list[dict[str, Any]]]]
            ) -> tuple[dict[int, site.Origin], dict[str, Any], dict[int, list]]:
    geography = select_home_geography(observations_from_payloads(payloads), policy=POLICY_LATEST)
    located: dict[tuple[str, int], dict[str, Any]] = {}
    venues_by_team: dict[int, set] = collections.defaultdict(set)
    for year, _, path, rows in payloads:
        for row in rows:
            if row.get("id") is None:
                continue
            located[(path, int(row["id"]))] = row.get("location") or {}
            if (row.get("location") or {}).get("id") is not None:
                venues_by_team[int(row["id"])].add((year, row["location"]["id"]))
    out: dict[int, site.Origin] = {}
    states = collections.Counter()
    for team_id, record in geography.items():
        states[record["state"]] += 1
        if record["state"] != SELECTED:
            continue
        location = located.get((record["payload_path"], team_id), {})
        out[team_id] = site.Origin(latitude=record["latitude"], longitude=record["longitude"],
                                   timezone=location.get("timezone"), venue_id=record["home_venue_id"])
    relocated = {}
    for team_id, pairs in venues_by_team.items():
        ids = {venue for _, venue in pairs}
        if len(ids) > 1:
            relocated[team_id] = sorted({(year, venue) for year, venue in pairs})
    return out, {"teams": len(geography), "states": dict(states), "relocated_teams": len(relocated),
                 "relocated": {str(k): v[:12] for k, v in sorted(relocated.items())[:60]}}, relocated


def wiki_index(cache: Path) -> dict[str, list[dict[str, Any]]]:
    """Folded team-season title -> cached revisions. Built once, then reused."""

    files = sorted(os.listdir(WIKIMEDIA))
    stamp = hashlib.sha256("\n".join(files).encode("utf-8")).hexdigest()
    if cache.is_file():
        data = json.loads(cache.read_text(encoding="utf-8"))
        if data.get("listing_sha256") == stamp:
            return data["titles"]
    titles: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for name in files:
        try:
            payload = json.loads((WIKIMEDIA / name).read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        pages = ((payload or {}).get("query") or {}).get("pages") if isinstance(payload, dict) else None
        if isinstance(pages, dict):
            pages = list(pages.values())
        for page in pages or []:
            title = str(page.get("title") or "")
            if TITLE.match(title) and page.get("revisions"):
                revision = page["revisions"][0]
                titles[site.fold(title)].append({"file": name, "title": title, "revid": revision.get("revid"),
                                                 "timestamp": revision.get("timestamp")})
    cache.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(cache, json.dumps({"listing_sha256": stamp, "titles": titles}) + "\n", encoding="utf-8")
    return titles


def schedule_entries(record: dict[str, Any]) -> list[dict[str, Any]]:
    payload = json.loads((WIKIMEDIA / record["file"]).read_text(encoding="utf-8"))
    pages = payload["query"]["pages"]
    page = pages[0] if isinstance(pages, list) else next(iter(pages.values()))
    slot = page["revisions"][0]["slots"]["main"]
    return site.parse_schedule_entries(slot.get("*") or slot.get("content") or "")


# ------------------------------------------------------------------- build
def build(out_dir: Path) -> dict[str, Any]:
    games, game_meta = load_games()
    venues, venue_meta = load_venues()
    payloads = load_team_payloads()
    team_origin, origin_meta, relocated = origins(payloads)
    names: dict[tuple[int, int], tuple[str, str]] = {}
    for year, _, _, rows in payloads:
        for row in rows:
            if row.get("id") is not None and row.get("school") and row.get("mascot"):
                names[(year, int(row["id"]))] = (row["school"], row["mascot"])
    titles = wiki_index(VALIDATION / "r37_09" / "WIKI_TEAM_SEASON_INDEX.json")
    previous = site.previous_contests(games)
    entry_cache: dict[str, list[dict[str, Any]] | None] = {}

    def page_entries(season: int, team_id: Any) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
        if team_id is None:
            return None, None
        name = names.get((season, int(team_id)))
        if name is None:
            return None, None
        key = site.fold(f"{season} {name[0]} {name[1]} football team")
        records = titles.get(key) or []
        if len(records) != 1:
            return None, ({"title_key": key, "revisions": len(records)} if records else None)
        record = records[0]
        if record["file"] not in entry_cache:
            entry_cache[record["file"]] = schedule_entries(record)
        return entry_cache[record["file"]], record

    rows_path = out_dir / "R37_09_CONTEST_SITE_ROWS.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    designation_checks = collections.Counter()
    sample_pool: dict[tuple[str, str], list[tuple[str, dict[str, Any]]]] = collections.defaultdict(list)
    lambeau = []
    with _bas_atomic.open_write(rows_path, "w", encoding="utf-8", newline="\n") as sink:
        for game in games:
            venue = venues.get(int(game["venueId"])) if game.get("venueId") is not None else None
            season = int(game.get("season") or 0)
            entries, page = page_entries(season, game.get("homeId"))
            side_checked = "HOME_TEAM_PAGE"
            if entries is None:
                entries, page = page_entries(season, game.get("awayId"))
                side_checked = "AWAY_TEAM_PAGE" if entries is not None else None
            confirmation = site.confirm_contest(season=season, start_utc=game.get("startDate"),
                                                venue=venue, entries=entries)
            if page:
                confirmation["secondary_revision"] = {k: page.get(k) for k in ("title", "revid", "timestamp", "file")}
                confirmation["secondary_side"] = side_checked
            home = team_origin.get(int(game["homeId"])) if game.get("homeId") is not None else None
            away = team_origin.get(int(game["awayId"])) if game.get("awayId") is not None else None
            row = site.contest_row(game=game, venue=venue, home=home, away=away,
                                   confirmation=confirmation, previous=previous)
            for side, team in (("home", game.get("homeId")), ("away", game.get("awayId"))):
                if team is not None and int(team) in relocated:
                    row[f"{side}_origin_relocated_across_vintages"] = True
            row["venue_elevation_m"] = (venue or {}).get("elevation")
            if "secondary_away" in confirmation:
                expected_away = side_checked == "AWAY_TEAM_PAGE"
                agrees = (confirmation["secondary_neutral"] or confirmation["secondary_away"] == expected_away)
                row["secondary_designation_agrees"] = agrees
                designation_checks["agrees" if agrees else "disagrees"] += 1
                if game.get("neutralSite") in (True, False) and                         confirmation["secondary_neutral"] != game.get("neutralSite"):
                    row["secondary_neutral_disagrees"] = True
                    designation_checks["neutral_disagrees"] += 1
            sink.write(json.dumps(row, sort_keys=True, default=str) + "\n")

            klass = str(game.get("homeClassification") or "unknown")
            counts["neutral_by_classification"][f"{row['neutral_status']}|{klass}"] += 1
            counts["venue_support"][row["venue_support"]] += 1
            counts["confirmation"][confirmation["state"]] += 1
            counts["legs"][row["legs_computed"]] += 1
            counts["tz_shift_known_legs"][sum(1 for leg in (row["home_leg"], row["away_leg"])
                                              if leg.get("tz_shift_hours") is not None)] += 1
            if row["same_team_both_sides"]:
                counts["anomalies"]["same_team_both_sides"] += 1
            key = hashlib.sha256(row["canonical_game_id"].encode()).hexdigest()
            stratum = (row["neutral_status"], "fbs" if klass == "fbs" else "fcs" if klass == "fcs" else "other",
                       row["venue_support"])
            sample_pool[stratum].append((key, row))
            if row.get("home_origin_relocated_across_vintages") or row.get("away_origin_relocated_across_vintages"):
                sample_pool[("ANOMALY", "RELOCATED_ORIGIN", "any")].append((key, row))
            if row.get("secondary_neutral_disagrees"):
                sample_pool[("ANOMALY", "SECONDARY_NEUTRAL_DISAGREES", "any")].append((key, row))
            if row["same_team_both_sides"]:
                sample_pool[("ANOMALY", "SAME_TEAM_BOTH_SIDES", "any")].append((key, row))
            if "lambeau" in str((venue or {}).get("name") or "").casefold():
                lambeau.append(row)

    sample = []
    for stratum in sorted(sample_pool):
        picked = sorted(sample_pool[stratum], key=lambda item: item[0])[:SAMPLE_PER_STRATUM]
        sample.extend({"stratum": list(stratum), **row} for _, row in picked)
    sample.extend({"stratum": ["MOTIVATING_CASE_FOUND_BY_VENUE_NAME", "any", "any"], **row} for row in lambeau
                  if row["canonical_game_id"] not in {s["canonical_game_id"] for s in sample})
    sample_path = out_dir / "R37_09_INDEPENDENT_SAMPLE.jsonl"
    with _bas_atomic.open_write(sample_path, "w", encoding="utf-8", newline="\n") as sink:
        for row in sample:
            sink.write(json.dumps(row, sort_keys=True, default=str) + "\n")

    return {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-09",
        "site_version": site.SITE_VERSION, "predecessor_version": site.PREDECESSOR_SITE_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "games": game_meta, "venues": venue_meta, "origins": origin_meta,
        "wiki_team_season_pages": sum(len(v) for v in titles.values()),
        "counts": {k: dict(v) for k, v in counts.items()},
        "secondary_designation_checks": dict(designation_checks),
        "rows": {"path": str(rows_path), "sha256": sha256_file(rows_path), "count": len(games)},
        "sample": {"path": str(sample_path), "sha256": sha256_file(sample_path), "count": len(sample),
                   "strata_population": {"|".join(k): len(v) for k, v in sorted(sample_pool.items())},
                   "empty_required_strata": [
                       f"{n}|{c}" for n in (site.NEUTRAL_TRUE, site.NEUTRAL_FALSE, site.NEUTRAL_UNKNOWN)
                       for c in ("fbs", "fcs")
                       if not any(k[0] == n and k[1] == c for k in sample_pool)],
                   "per_stratum": SAMPLE_PER_STRATUM},
        "motivating_case": {"found_by": "venue name in the provider index, not a hardcoded contest",
                            "rows": [{k: r[k] for k in ("canonical_game_id", "season", "neutral_status",
                                                         "venue_name", "venue_support", "legs_computed")}
                                     for r in lambeau]},
        "boundaries": [
            "Geometry is the current vintage of the provider index and of team payloads: development-only, "
            "not point-in-time, and every row says so.",
            "A secondary-source confirmation is independent of the game feed; it is a later encyclopedia "
            "revision, not an official or contemporaneous record.",
            "Unknown neutral status stays unknown; no missing flag becomes false.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=ATTEMPT / "evidence" / "repairs")
    args = parser.parse_args(argv)
    receipt = build(args.out_dir)
    _bas_atomic.write_text(args.out_dir / "R37_09_CONTEST_SITE.json", json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                                                          encoding="utf-8")
    print("games:", receipt["games"]["unique_games"], "| conflicts:", receipt["games"]["conflicting_game_ids"],
          "| identical duplicates:", receipt["games"]["identical_duplicate_copies"])
    for key, value in receipt["counts"].items():
        print(f"{key}: {value}")
    print("designation checks:", receipt["secondary_designation_checks"])
    print("sample:", receipt["sample"]["count"], "| lambeau:", receipt["motivating_case"]["rows"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
