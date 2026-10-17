"""A tiny national observed-weather evidence world built through the real input formats (BAT-731, Cycle #60 TP60-A01).

Every input the release consumes is written in its retained physical form: the accepted parent population (SQLite
contest table; scores are present and never read), the accepted C48 alias reconciliation (SQLite parent and provider
records), the SRC-002 games capture and its receipt (JSON), four raw NOAA ISD global-hourly station-year CSVs, the
original pilot produced by the accepted original producer code (``aggie_analytics.features.observed_weather_shadow``)
and written as Parquet, its run and capture manifests, the game-coordinate Parquet, the station-candidate CSV, the
acquisition and alias manifests, a format document and parent contracts in a tiny checkout.

Planted classes: a promoted relation; a promoted relation with a field conflict; an unpromoted candidate relation (both
keys kept); an FCS contest outside the FBS route; a nolink canceled contest without an NCAA ID; a December-31 parent
date whose UTC kickoff falls in calendar 2025 and whose earlier observation lies only in the adjacent captured file;
a late-December game without a later observation; duplicate timestamps (the decoded-field ranking and the report-type
tie); an exact clock match; an exactly equidistant before/after pair (earlier wins); sentinels for every scaled field;
suspect, erroneous and NCEI-suspect quality flags; AWOS whole-degree temperatures; calm and variable wind; raw AA
precipitation; a short CSV row; a summary-of-day nearest row without any decoded field; a dome catalog venue; a TBD
provider start; and one original pilot field that disagrees with the raw reconstruction."""
from __future__ import annotations

import contextlib
import copy
import csv
import hashlib
import io
import json
import shutil
import sqlite3
import sys
import zlib
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.features import observed_weather_shadow as original  # noqa: E402
from aggie_analytics.weather_evidence import evidence as we  # noqa: E402

POP = we.POPULATION
CAPTURE_ID = "c" * 64
ACQUISITION_ID = "a" * 64
PILOT_ID = "4" * 64
CLASSIFICATION = "PRELIMINARY_UNPROTECTED_OBSERVED_GAME_TIME_SHADOW_CANDIDATE"
HEADER = ["STATION", "DATE", "SOURCE", "LATITUDE", "LONGITUDE", "ELEVATION", "NAME", "REPORT_TYPE", "CALL_SIGN",
          "QUALITY_CONTROL", "WND", "CIG", "VIS", "TMP", "DEW", "SLP", "AA1", "AA2", "REM"]
S1, S2, S3 = "722430-12960", "722540-13904", "722780-23183"
RIGHTS = {
    source: {"decision_id": f"PRIVATE-RESEARCH-{source}", "lane_disposition": "PRIVATE_RESEARCH_ALLOWED",
             "raw_storage_policy": "ALLOW_IMMUTABLE_RAW_AND_NORMALIZED_DATA_OUTSIDE_GIT",
             "redistribution_policy": "DO_NOT_PUBLISH_OR_REDISTRIBUTE_RAW_THIRD_PARTY_PAYLOADS", "provider": provider,
             "raw_export_allowed": False, "provider_raw_redistribution_permission": "PROHIBITED",
             "derived_export_allowed": False}
    for source, provider in (("SRC-002", "Tiny provider"), ("SRC-015", "Tiny parent"), ("SRC-029", "Tiny NOAA"))}


def builder() -> Any:
    sys.path.insert(0, str(ROOT / "tools"))
    import build_national_observed_weather_evidence as b  # noqa: PLC0415

    return b


def _sha(path: Path) -> str:
    return we.sha256_file(path)


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, sort_keys=True), encoding="utf-8")
    return path


def _pl() -> Any:
    import polars as pl  # noqa: PLC0415 - the test extra's pinned Parquet writer

    return pl


def _row(station: str, date: str, source: str, report: str, wnd: str, vis: str, tmp: str, dew: str, slp: str,
         aa1: str = "", aa2: str = "") -> list[str]:
    return [station.replace("-", ""), date, source, "30.25", "-96.5", "+0100.0", "TINY STATION, US", report, "99999",
            "V020", wnd, "99999,9,9,N", vis, tmp, dew, slp, aa1, aa2, "REM TINY"]


#: The raw station-year rows (in file order). Comments name the planted class each row carries.
RAW = {
    f"2024|{S1}": [
        _row(S1, "2024-09-01T12:00:00", "7", "FM-15", "200,1,N,0040,1", "016093,1,9,9", "+0210,1", "+0110,1",
             "10100,1")[:12],                                                              # short row (malformed)
        _row(S1, "2024-09-07T17:00:00", "7", "FM-15", "180,1,N,0050,1", "016093,1,9,9", "+0250,1", "+0150,1",
             "99999,9"),                                                                   # SLP sentinel
        _row(S1, "2024-09-07T18:00:00", "7", "FM-15", "190,1,N,0060,1", "016093,1,9,9", "+0260,1", "+0150,1",
             "99999,9"),                                                                   # duplicate, 5 fields
        _row(S1, "2024-09-07T18:00:00", "4", "FM-16", "190,1,N,0062,1", "020000,1,9,9", "+0262,1", "+0151,1",
             "10120,1"),                                                                   # duplicate, report tie
        _row(S1, "2024-09-07T18:00:00", "4", "FM-12", "190,1,N,0062,1", "020000,1,9,9", "+0262,1", "+0151,1",
             "10120,1"),                                                                   # duplicate winner
        _row(S1, "2024-09-14T23:00:00", "7", "FM-15", "999,9,V,0030,1", "016093,1,9,9", "+9999,9", "+0180,3",
             "99999,9", aa1="01,0005,9,1"),                         # variable wind, TMP sentinel, erroneous DEW, AA1
        _row(S1, "2024-09-15T00:00:00", "7", "FM-15", "200,2,N,0040,1", "016093,1,9,9", "+0200,1", "+0170,1",
             "10090,1")],                                                                  # suspect wind direction
    f"2024|{S2}": [
        _row(S2, "2024-10-05T15:45:00", "6", "SOD  ", "999,9,9,9999,9", "999999,9,9,9", "+9999,9", "+9999,9",
             "99999,9"),                                                                   # summary of day, nothing
        _row(S2, "2024-10-05T17:00:00", "7", "FM-15", "999,9,C,0000,1", "999999,9,9,9", "+0220,C", "+0120,C",
             "10150,1")],                                                                  # calm, VIS sentinel, AWOS
    f"2024|{S3}": [
        _row(S3, "2024-12-28T17:00:00", "7", "FM-15", "090,1,N,0030,1", "016093,1,9,9", "+0100,1", "+0050,1",
             "10200,1"),
        _row(S3, "2024-12-28T18:00:00", "7", "FM-15", "090,1,N,0035,1", "016093,1,9,9", "+0105,6", "+0055,1",
             "10210,1", aa1="06,0000,9,5")],                                               # NCEI-suspect TMP, AA1
    f"2025|{S3}": [
        _row(S3, "2025-01-01T01:00:00", "7", "FM-15", "100,1,N,0040,1", "016093,1,9,9", "+0080,1", "+0020,1",
             "10220,1"),
        _row(S3, "2025-01-01T02:00:00", "7", "FM-15", "110,1,N,0045,1", "016093,1,9,9", "+0075,1", "+0015,1",
             "10225,1")],
}
#: game id -> (contest, kickoff, home, away, venue id, venue name, dome, station, TBD, neutral)
GAMES = {
    "401000001": ("ncaa:1001", "2024-09-07T18:00:00.000Z", "Alpha", "Bravo", "901", "Alpha Field", False, S1, False,
                  False),
    "401000002": ("ncaa:1002", "2024-09-14T23:30:00.000Z", "Charlie", "Delta", "902", "Bravo Dome", True, S1, True,
                  True),
    "401000003": ("ncaa:1003", "2024-10-05T16:00:00.000Z", "Echo", "Foxtrot", "903", "Charlie Bowl", False, S2, False,
                  False),
    "401000004": ("ncaa:1006", "2025-01-01T00:30:00.000Z", "Golf", "Hotel", "904", "Echo Park", False, S3, False, True),
    "401000005": ("ncaa:1007", "2024-12-28T20:00:00.000Z", "India", "Juliet", "904", "Echo Park", False, S3, False,
                  False),
}
PROVIDER_ORDER = ["401000001", "401000002", "401000003", "401000004", "401000005"]
NOLINK = "nolink:2024:2024-09-28:org:7|org:8"
#: contest key -> (date, site, neutral text, pair, a, b, status, competitive, alias disposition, reason, route,
#: conflicts, provider ordinal or None, promoted)
CONTESTS = {
    "ncaa:1001": ("2024-09-07", "HOME_A", None, "FBS-FBS", 1, 2, "COMPLETED", 1, "RECONCILED_FIELDS_AGREE", None,
                  "IN_FBS_ROUTE", [], 0, True),
    "ncaa:1002": ("2024-09-14", "NEUTRAL", "Bravo Dome", "FBS-FBS", 3, 4, "COMPLETED", 1, "RECONCILED_FIELD_CONFLICT",
                  "FIELD_DISAGREEMENT:neutral_status", "IN_FBS_ROUTE", ["neutral_status"], 1, True),
    "ncaa:1003": ("2024-10-05", "HOME_A", None, "FBS-FCS", 5, 6, "COMPLETED", 1,
                  "CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE", "b:NAME_LINK", "IN_FBS_ROUTE", [], 2, False),
    "ncaa:1004": ("2024-10-12", "HOME_B", None, "FCS-FCS", 9, 10, "COMPLETED", 1, "OUT_OF_ROUTE_NOT_EXPECTED",
                  "NO_FBS_PARTICIPANT_NO_PROVIDER_ROW", "OUTSIDE_FBS_ROUTE", [], None, False),
    NOLINK: ("2024-09-28", "HOME_A", None, "FCS-FCS", 7, 8, "CANCELED", 0, "OUT_OF_ROUTE_NOT_EXPECTED",
             "NO_FBS_PARTICIPANT_NO_PROVIDER_ROW", "OUTSIDE_FBS_ROUTE", [], None, False),
    "ncaa:1006": ("2024-12-31", "NEUTRAL", "Echo Park", "FBS-FBS", 11, 12, "COMPLETED", 1, "RECONCILED_FIELDS_AGREE",
                  None, "IN_FBS_ROUTE", [], 3, True),
    "ncaa:1007": ("2024-12-28", "HOME_A", None, "FBS-FBS", 13, 14, "COMPLETED", 1, "RECONCILED_FIELDS_AGREE", None,
                  "IN_FBS_ROUTE", [], 4, True),
}
CANDIDATES = [  # (season, venue, station, rank, name, lat, lon, elevation text, icao, distance)
    (2024, "901", S1, 1, "TINY ONE", "30.1", "-96.4", "+0101.5", "KTN1", "5.25"),
    (2024, "902", S1, 1, "TINY ONE", "30.1", "-96.4", "+0101.5", "KTN1", "7.5"),
    (2024, "903", S2, 1, "TINY TWO", "31.1", "-97.4", "+0210.0", "KTN2", "11.0"),
    (2024, "904", S3, 1, "TINY THREE", "32.1", "-98.4", "+1739.2", "KTN3", "12.25"),
    (2024, "903", S3, 2, "TINY THREE", "32.1", "-98.4", "+1739.2", "KTN3", "40.0"),     # rank two (never joined)
    (2023, "901", S2, 1, "TINY TWO", "31.1", "-97.4", "+0210.0", "KTN2", "9.0"),       # other season (never joined)
]
PLANTED_DISCREPANCY = ("401000005", "nearest_temperature_c", 11.0)


def build_world(base: Path) -> dict[str, Any]:
    """Every input of the tiny world in its physical form under ``base``; returns paths and planted facts."""
    data, repo = base / "d", base / "r"
    world: dict[str, Any] = {"data_root": data, "repo_root": repo}
    # ---- raw station-year captures
    captures = []
    for key, rows in RAW.items():
        year, station = key.split("|")
        text = io.StringIO()
        writer = csv.writer(text, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerow(HEADER)
        for row in rows:
            writer.writerow(row)
        raw = text.getvalue().encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        path = data / "raw" / "SRC-029" / "isd" / f"{digest}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        captures.append({"calendar_year": int(year), "capture_reuse_state": "NEW_IMMUTABLE_CAPTURE" if year == "2025"
                         else "REUSED_PINNED_2024_COVERAGE_PILOT", "raw_bytes": len(raw),
                         "raw_relative_path": _rel(path, data), "raw_sha256": digest,
                         "request_identity_sha256": hashlib.sha256(f"req:{key}".encode()).hexdigest(),
                         "snapshot_id": f"snap_{digest[:24]}", "source_uri": f"https://example.invalid/{year}/"
                                                                             f"{station.replace('-', '')}.csv",
                         "station_file_id": station.replace("-", ""), "station_id": station})
    capture_manifest = _write_json(data / "m" / "capture_manifest.json", {
        "capture_manifest_identity": CAPTURE_ID, "issued_at_utc": "2026-08-12T09:15:00Z", "captures": captures,
        "total_bytes_referenced": sum(c["raw_bytes"] for c in captures), "capture_count": len(captures)})
    acquisition = _write_json(data / "m" / "acquisition_manifest.json", {
        "dataset_identity": ACQUISITION_ID, "issued_at_utc": "2026-08-12T08:55:00Z",
        "captures": [{"raw_sha256": c["raw_sha256"]} for c in captures if c["calendar_year"] == 2024]})
    # ---- provider capture (scores present, never read) and receipt
    provider = []
    for gid in PROVIDER_ORDER:
        contest, kickoff, home, away, venue_id, venue, _dome, _station, tbd, neutral = GAMES[gid]
        provider.append({"id": int(gid), "season": 2024, "week": 1, "seasonType": "regular", "startDate": kickoff,
                         "startTimeTBD": tbd, "completed": True, "neutralSite": neutral, "venueId": int(venue_id),
                         "venue": venue, "homeTeam": home, "awayTeam": away, "homePoints": 31, "awayPoints": 17,
                         "homeLineScores": [7, 7, 10, 7], "excitementIndex": 3.5})
    provider_path = data / "raw" / "SRC-002" / "games.json"
    provider_path.parent.mkdir(parents=True, exist_ok=True)
    provider_path.write_text(json.dumps(provider), encoding="utf-8")
    receipt = _write_json(data / "m" / "provider_receipt.json", {
        "response_sha256": _sha(provider_path), "capture_known_at_utc": "2026-08-09T16:58:08Z", "row_count": 5})
    # ---- accepted parent population (scores present, never read)
    population = data / "c" / "population.sqlite"
    population.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(population)
    columns = list(we.PARENT_COLUMNS) + ["a_points", "b_points", "mirror_scores_observed"]
    conn.execute(f"CREATE TABLE contest ({', '.join(columns)})")
    rows = []
    for key, (date, site, neutral, pair, a, b, status, competitive, *_rest) in CONTESTS.items():
        a_div, b_div = pair.split("-")
        rows.append({"contest_key": key, "ncaa_contest_id": None if key.startswith("nolink") else key.split(":")[1],
                     "season": 2024, "term": "FALL", "contest_date": date, "contest_status": status,
                     "competitive": competitive, "site": site, "neutral_site_text": neutral,
                     "classification_pair": pair, "a_key": f"org:{a}", "a_team_name": f"Team {a}",
                     "a_division_label": a_div, "a_membership": "DIVISION_I", "b_key": f"org:{b}",
                     "b_team_name": f"Team {b}", "b_division_label": b_div, "b_membership": "DIVISION_I",
                     "disposition": "CANDIDATE_ONLY", "disposition_reason": "SINGLE_SOURCE_UNRECONCILED",
                     "reconciliation_state": "SINGLE_SOURCE_UNRECONCILED", "exposure": "EXPOSED_NOT_PROTECTED",
                     "a_points": 28, "b_points": 21, "mirror_scores_observed": "[28,21]"})
    rows.append({**rows[0], "contest_key": "ncaa:900", "ncaa_contest_id": "900", "season": 2023,
                 "contest_date": "2023-09-02"})
    conn.executemany(f"INSERT INTO contest VALUES ({', '.join('?' for _ in columns)})",
                     [[r[c] for c in columns] for r in rows])
    conn.commit()
    conn.close()
    # ---- accepted C48 alias reconciliation
    alias = data / "c" / "alias.sqlite"
    conn = sqlite3.connect(alias)
    conn.execute("CREATE TABLE parent_reconciliation (ord INTEGER PRIMARY KEY, contest_key TEXT NOT NULL, season "
                 "INTEGER NOT NULL, contest_date TEXT, a_key TEXT, b_key TEXT, disposition TEXT NOT NULL, "
                 "provider_row_key TEXT, record TEXT NOT NULL)")
    conn.execute("CREATE TABLE provider_reconciliation (ord INTEGER PRIMARY KEY, provider_row_key TEXT NOT NULL, season "
                 "INTEGER NOT NULL, row_ordinal INTEGER NOT NULL, provider_game_id TEXT, disposition TEXT NOT NULL, "
                 "contest_key TEXT, record TEXT NOT NULL)")
    capture_sha = _sha(provider_path)
    for ord_, (key, (date, *_x, disp, reason, route, conflicts, ordinal, promoted)) in enumerate(CONTESTS.items()):
        prow = None if ordinal is None else f"src002:2024:{ordinal:04d}"
        gid = None if ordinal is None else PROVIDER_ORDER[ordinal]
        relation = {} if prow is None else {"one_to_one": True, "promoted": promoted, "provider_game_id": gid,
                                            "provider_row_key": prow, "side_map": {"a": "home", "b": "away"}}
        record = {"contest_key": key, "season": 2024, "contest_date": date, "disposition": disp,
                  "disposition_reason": reason, "route_scope": route, "field_conflicts": conflicts,
                  "candidates": {"dated_provider_rows": [prow] if prow else [],
                                 "same_pair_provider_rows": [prow] if prow else []},
                  "relation": relation, "parent": {"a_points": 28, "b_points": 21}}
        conn.execute("INSERT INTO parent_reconciliation VALUES (?, ?, 2024, ?, NULL, NULL, ?, ?, ?)",
                     (ord_, key, date, disp, prow, json.dumps(record)))
    conn.execute("INSERT INTO parent_reconciliation VALUES (99, 'ncaa:900', 2023, '2023-09-02', NULL, NULL, "
                 "'RECONCILED_FIELDS_AGREE', NULL, '{}')")
    by_ordinal = {v[12]: (k, v) for k, v in CONTESTS.items() if v[12] is not None}
    for ordinal, gid in enumerate(PROVIDER_ORDER):
        key, value = by_ordinal[ordinal]
        disp, reason, promoted = value[8], value[9], value[13]
        prow = f"src002:2024:{ordinal:04d}"
        record = {"provider_row_key": prow, "provider_game_id": gid, "row_ordinal": ordinal, "disposition": disp,
                  "disposition_reason": reason, "relation": {"contest_key": key, "one_to_one": True,
                                                             "promoted": promoted},
                  "capture": {"capture_id": "cap_tiny", "sha256": capture_sha}, "provider": {"homePoints": 31}}
        conn.execute("INSERT INTO provider_reconciliation VALUES (?, ?, 2024, ?, ?, ?, ?, ?)",
                     (ordinal, prow, ordinal, gid, disp, key, json.dumps(record)))
    conn.commit()
    conn.close()
    alias_manifest = _write_json(data / "m" / "alias_manifest.json",
                                 {"identity": "e" * 64, "provenance": {"issued_at_utc": "2026-10-09T21:09:23+00:00"}})
    # ---- station candidates and game coordinates
    stations = data / "f" / "station_candidates.csv"
    stations.parent.mkdir(parents=True, exist_ok=True)
    fields = ["season", "venue_id", "station_id", "station_rank", "candidate_identity", "venue_name", "venue_latitude",
              "venue_longitude", "coordinate_effective_time_state", "station_name", "station_country",
              "station_state", "station_icao", "station_latitude", "station_longitude", "station_elevation_m",
              "station_begin", "station_end", "distance_km", "distance_acceptance_state",
              "automatic_station_promotion", "historical_pit_eligible", "training_feature_eligible"]
    with stations.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(fields)
        for season, venue, station, rank, name, lat, lon, elev, icao, distance in CANDIDATES:
            writer.writerow([season, venue, station, rank, "f" * 64, f"Venue {venue}", "30.0", "-96.0",
                             "UNKNOWN_CURRENT_2026_CATALOG_COORDINATE", name, "US", "TX", icao, lat, lon, elev,
                             "1950-01-01", "2026-01-01", distance, "UNSET_REQUIRES_EMPIRICAL_OR_MANUAL_REVIEW", "false",
                             "false", "false"])
    pl = _pl()
    coordinate_rows = []
    for gid, (contest, kickoff, home, away, venue_id, venue, dome, _station, _tbd, _neutral) in GAMES.items():
        for variable in ("temperature_2m", "wind_speed_10m"):
            coordinate_rows.append({"season": 2024, "source_game_id": gid, "canonical_game_id_candidate": f"game_cfbd_{gid}",
                                    "kickoff_at_utc": kickoff, "home_team": home, "away_team": away,
                                    "venue_id_candidate": venue_id, "venue_name_current_catalog": venue,
                                    "venue_dome_current_catalog": dome, "weather_variable": variable})
    coordinate_rows.append({**coordinate_rows[0], "season": 2023, "source_game_id": "401999999"})
    coordinates = data / "q" / "coordinates.parquet"
    coordinates.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(coordinate_rows).write_parquet(coordinates, compression="zstd", statistics=True)
    # ---- the original pilot through the accepted original producer code
    candidate_meta = {(v, s): (n, float(la), float(lo), float(d)) for se, v, s, r, n, la, lo, _e, _i, d in CANDIDATES
                      if se == 2024 and r == 1}
    by_capture = {f"{c['calendar_year']}|{c['station_id']}": c for c in captures}
    pilot_rows = []
    for gid, (contest, kickoff, home, away, venue_id, venue, dome, station, _tbd, _neutral) in GAMES.items():
        year = int(kickoff[:4])
        cap = by_capture[f"{year}|{station}"]
        observations = original.load_best_observations(data / Path(*cap["raw_relative_path"].split("/")),
                                                       original.station_file_id(station), year)
        start = original.parse_utc(kickoff)
        chosen = original.select_temporal_candidates(observations, start)
        before, after, nearest = chosen["before"], chosen["after"], chosen["nearest"]
        name, lat, lon, distance = candidate_meta[(venue_id, station)]
        row = {"schema_version": "1.0.0", "classification": CLASSIFICATION, "football_season": 2024,
               "source_game_id": gid, "canonical_game_id_candidate": f"game_cfbd_{gid}", "kickoff_at_utc": kickoff,
               "home_team": home, "away_team": away, "venue_id": venue_id, "venue_name": venue, "venue_dome": dome,
               "calendar_year": year, "station_id": station, "station_name": name, "station_latitude": lat,
               "station_longitude": lon, "distance_km": distance,
               "station_file_id": original.station_file_id(station), "station_rank": 1,
               "station_acceptance_state": "CANDIDATE_REVIEW_REQUIRED", "station_snapshot_id": cap["snapshot_id"],
               "station_raw_sha256": cap["raw_sha256"],
               "station_request_identity_sha256": cap["request_identity_sha256"],
               "before_observed_at_utc": before["observed_at_utc"] if before else None,
               "before_delta_minutes": (start - original.parse_utc(before["observed_at_utc"])).total_seconds() / 60.0
               if before else None,
               "after_observed_at_utc": after["observed_at_utc"] if after else None,
               "after_delta_minutes": (original.parse_utc(after["observed_at_utc"]) - start).total_seconds() / 60.0
               if after else None,
               "nearest_observation_state": "PRESENT" if nearest else "MISSING",
               "nearest_absolute_delta_minutes": abs((original.parse_utc(nearest["observed_at_utc"]) -
                                                      start).total_seconds()) / 60.0 if nearest else None,
               "observed_weather_substitution": False, "historical_pit_eligible": False,
               "training_feature_eligible": False, "protected_eligible": False,
               "dome_observation_feature_eligible": False}
        for name_, _code in we.OBSERVATION_FIELDS:
            row[f"nearest_{name_}"] = nearest[name_] if nearest else None
        row["row_lineage_sha256"] = original.stable_hash({k: row[k] for k in (
            "source_game_id", "kickoff_at_utc", "station_id", "station_raw_sha256", "nearest_observed_at_utc")})
        pilot_rows.append(row)
    pilot_rows.sort(key=lambda r: (r["kickoff_at_utc"], r["source_game_id"]))
    planted_game, planted_field, planted_value = PLANTED_DISCREPANCY
    for row in pilot_rows:
        if row["source_game_id"] == planted_game:
            world["planted_verified"] = row[planted_field]
            row[planted_field] = planted_value
    dtypes = {"s?": pl.String, "i?": pl.Int64, "f?": pl.Float64, "b?": pl.Boolean}
    schema = {name: dtypes[code] for name, code in we.ORIGINAL_PILOT_FIELDS}
    pilot = data / "p" / "pilot.parquet"
    pilot.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame({name: [r[name] for r in pilot_rows] for name in schema}, schema=schema).write_parquet(
        pilot, compression="zstd", statistics=True)
    run_manifest = _write_json(data / "m" / "pilot_run_manifest.json", {
        "dataset_identity": PILOT_ID, "issued_at_utc": "2026-08-12T09:15:00Z",
        "capture_manifest_identity": CAPTURE_ID, "payload": {"sha256": _sha(pilot), "rows": len(pilot_rows)}})
    fmt = data / "m" / "isd_format.pdf"
    fmt.write_bytes(b"%PDF-1.4 tiny official format document for the fixture\n")
    # ---- a tiny checkout with one parent contract
    (repo / "configs").mkdir(parents=True, exist_ok=True)
    parent_rel = "configs/noaa_isd_game_observation_shadow_contract.json"
    (repo / parent_rel).write_text(json.dumps({"classification": CLASSIFICATION}), encoding="utf-8")
    world.update(captures=captures, capture_manifest=capture_manifest, acquisition=acquisition,
                 provider=provider_path, receipt=receipt, population=population, alias=alias,
                 alias_manifest=alias_manifest, stations=stations, coordinates=coordinates, pilot=pilot,
                 pilot_rows=pilot_rows, run_manifest=run_manifest, format=fmt, parent_contract_rel=parent_rel,
                 coordinate_rows=len(coordinate_rows), station_rows=len(CANDIDATES))
    return world


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _keys_sha(keys: list[str]) -> str:
    return hashlib.sha256("\n".join(keys).encode("utf-8")).hexdigest()


def anchors_for(world: dict[str, Any]) -> dict[str, Any]:
    """The tiny world's pinned authority, shaped exactly like the production anchors (this fixture's own projections
    of its inputs; never the producer's decisions)."""
    data = world["data_root"]
    inputs: dict[str, dict[str, Any]] = {}

    def add(name, path, kind, role, *, rows=None, dataset_identity=None, issued_at_utc=None, source_id=None):
        inputs[name] = {"relative_path": _rel(path, data), "sha256": _sha(path), "bytes": path.stat().st_size,
                        "kind": kind, "role": role, "rows": rows, "dataset_identity": dataset_identity,
                        "issued_at_utc": issued_at_utc, "source_id": source_id}
    add("population_database", world["population"], "SQLITE", "ACCEPTED_PARENT_POPULATION_SEASON_2024_CONTESTS",
        rows=len(CONTESTS), dataset_identity="6" * 64, source_id="SRC-015")
    add("alias_database", world["alias"], "SQLITE", "ACCEPTED_C48_ALIAS_RECONCILIATION_2024_PROVIDER_RELATIONS",
        rows=len(PROVIDER_ORDER), dataset_identity="e" * 64, source_id="SRC-002")
    add("alias_manifest", world["alias_manifest"], "JSON", "ACCEPTED_C48_ALIAS_RECONCILIATION_MANIFEST",
        dataset_identity="e" * 64, issued_at_utc="2026-10-09T21:09:23+00:00", source_id="SRC-002")
    add("provider_games_2024", world["provider"], "JSON", "RETAINED_SRC002_GAMES_FBS_2024_CAPTURE",
        rows=len(PROVIDER_ORDER), issued_at_utc="2026-08-09T16:58:08Z", source_id="SRC-002")
    add("provider_games_2024_receipt", world["receipt"], "JSON", "RETAINED_SRC002_CAPTURE_RECEIPT",
        issued_at_utc="2026-08-09T16:58:08Z", source_id="SRC-002")
    add("pilot_payload", world["pilot"], "PARQUET", "ORIGINAL_OBSERVED_WEATHER_PILOT_920_ROWS",
        rows=len(world["pilot_rows"]), dataset_identity=PILOT_ID, issued_at_utc="2026-08-12T09:15:00Z",
        source_id="SRC-029")
    add("pilot_run_manifest", world["run_manifest"], "JSON", "ORIGINAL_OBSERVED_WEATHER_PILOT_RUN_MANIFEST",
        dataset_identity=PILOT_ID, issued_at_utc="2026-08-12T09:15:00Z", source_id="SRC-029")
    add("pilot_capture_manifest", world["capture_manifest"], "JSON", "ORIGINAL_STATION_YEAR_CAPTURE_MANIFEST",
        rows=len(world["captures"]), dataset_identity=CAPTURE_ID, issued_at_utc="2026-08-12T09:15:00Z",
        source_id="SRC-029")
    add("game_coordinates", world["coordinates"], "PARQUET",
        "ORIGINAL_GAME_COORDINATE_PAYLOAD_GAME_AND_CATALOG_VENUE_FIELDS_ONLY", rows=world["coordinate_rows"],
        dataset_identity="7" * 64)
    add("station_candidates", world["stations"], "CSV", "RANK_ONE_STATION_CANDIDATES_REFERENCE_ONLY",
        rows=world["station_rows"], dataset_identity="8" * 64, source_id="SRC-029")
    add("acquisition_2024", world["acquisition"], "JSON", "ORIGINAL_2024_COVERAGE_PILOT_ACQUISITION_MANIFEST",
        rows=sum(1 for c in world["captures"] if c["calendar_year"] == 2024), dataset_identity=ACQUISITION_ID,
        issued_at_utc="2026-08-12T08:55:00Z", source_id="SRC-029")
    add("isd_format_document", world["format"], "PDF", "OFFICIAL_NOAA_NCEI_ISD_FORMAT_DOCUMENT_2018_01_12",
        source_id="SRC-029")
    raw = {}
    for c in sorted(world["captures"], key=lambda c: (c["calendar_year"], c["station_id"])):
        raw[f"{c['calendar_year']}|{c['station_id']}"] = {
            "relative_path": c["raw_relative_path"], "sha256": c["raw_sha256"], "bytes": c["raw_bytes"],
            **{k: c[k] for k in ("raw_relative_path", "raw_sha256", "raw_bytes", "request_identity_sha256",
                                 "snapshot_id", "source_uri", "station_file_id", "station_id", "calendar_year",
                                 "capture_reuse_state")}}
    parent_contracts = {world["parent_contract_rel"]: _sha(world["repo_root"] / world["parent_contract_rel"])}
    clocks = {"capture_manifest_issued_at_utc": "2026-08-12T09:15:00Z",
              "acquisition_issued_at_utc": "2026-08-12T08:55:00Z",
              "provider_capture_known_at_utc": "2026-08-09T16:58:08Z", "pilot_issued_at_utc": "2026-08-12T09:15:00Z"}
    expected = expected_for(world, inputs, raw, parent_contracts)
    return {"contract_id": we.CONTRACT_ID, "contract_sha256": "0" * 64, "inputs": inputs, "raw": raw,
            "parent_contracts": parent_contracts, "clocks": clocks, "rights": copy.deepcopy(RIGHTS),
            "expected": expected}


def expected_for(world: dict[str, Any], inputs: dict[str, Any], raw: dict[str, Any],
                 parent_contracts: dict[str, str]) -> dict[str, Any]:
    contests = sorted(CONTESTS, key=lambda k: (CONTESTS[k][0], k))
    pilots = world["pilot_rows"]
    originals = [_canonical({name: r[name] for name in we.ORIGINAL_NAMES}) for r in pilots]
    assignment = [f"{r['source_game_id']}|{r['calendar_year']}|{r['station_id']}" for r in pilots]
    clocks_lines, relations = [], []
    for r in pilots:
        gid = r["source_game_id"]
        contest, kickoff, *_x, tbd, _neutral = GAMES[gid]
        ordinal = PROVIDER_ORDER.index(gid)
        promoted = CONTESTS[contest][13]
        clocks_lines.append(f"{gid}|{kickoff}|{tbd}")
        relations.append(f"{gid}|src002:2024:{ordinal:04d}|"
                         f"{'PROMOTED_ONE_TO_ONE' if promoted else 'CANDIDATE_NOT_PROMOTED'}|"
                         f"{contest if promoted else None}|{None if promoted else contest}")
    conn = sqlite3.connect(world["population"])
    conn.row_factory = sqlite3.Row
    parents = {r["contest_key"]: dict(r) for r in conn.execute(
        f"SELECT {', '.join(we.PARENT_COLUMNS)} FROM contest WHERE season = 2024")}
    conn.close()
    parent_lines, relation_lines = [], []
    by_state: dict[str, int] = {}
    for key in contests:
        date, site, neutral, pair, a, b, status, competitive, disp, reason, route, conflicts, ordinal, promoted = \
            CONTESTS[key]
        prow = None if ordinal is None else f"src002:2024:{ordinal:04d}"
        gid = None if ordinal is None else PROVIDER_ORDER[ordinal]
        state = "NO_PROVIDER_ROW" if prow is None else ("PROMOTED_ONE_TO_ONE" if promoted else "CANDIDATE_NOT_PROMOTED")
        by_state[state] = by_state.get(state, 0) + 1
        parent_lines.append(_canonical({c: parents[key][c] for c in we.PARENT_COLUMNS}))
        relation_lines.append(f"{key}|{disp}|{reason}|{route}|{','.join(sorted(conflicts))}|"
                              f"{prow if prow else ''}|{prow}|{gid}|{state}|{prow if promoted else None}|"
                              f"{gid if promoted else None}")
    by_year: dict[str, int] = {}
    by_pair: dict[str, int] = {}
    for key in contests:
        by_year[CONTESTS[key][0][:4]] = by_year.get(CONTESTS[key][0][:4], 0) + 1
        by_pair[CONTESTS[key][3]] = by_pair.get(CONTESTS[key][3], 0) + 1
    pilot_by_year: dict[str, int] = {}
    for r in pilots:
        pilot_by_year[str(r["calendar_year"])] = pilot_by_year.get(str(r["calendar_year"]), 0) + 1
    station_keys = list(raw)
    promoted_count = by_state.get("PROMOTED_ONE_TO_ONE", 0)
    return {
        "contests": len(contests), "pilots": len(pilots), "station_years": len(raw), "provider_rows": len(PROVIDER_ORDER),
        "contests_keys": contests, "contests_keys_sha256": _keys_sha(contests),
        "pilots_keys": [r["source_game_id"] for r in pilots],
        "pilots_keys_sha256": _keys_sha([r["source_game_id"] for r in pilots]),
        "station_years_keys": station_keys, "station_years_keys_sha256": _keys_sha(station_keys),
        "source_witness_keys": [f"INPUT|{n}" for n in inputs] + [f"CONTRACT|{r}" for r in parent_contracts] +
        [f"RAW|{k}" for k in station_keys],
        "acquisition_raw_sha256": sorted(c["raw_sha256"] for c in world["captures"] if c["calendar_year"] == 2024),
        "pilot_originals_sha256": _keys_sha(originals), "pilot_station_year_sha256": _keys_sha(assignment),
        "provider_clock_sha256": _keys_sha(clocks_lines), "pilot_relation_sha256": _keys_sha(relations),
        "contest_parents_sha256": _keys_sha(parent_lines), "contest_relation_sha256": _keys_sha(relation_lines),
        "census": {"contests": len(contests), "pilots": len(pilots), "station_years": len(raw),
                   "promoted_relations": promoted_count,
                   "unpromoted_relations": sum(1 for line in relations if "|PROMOTED_ONE_TO_ONE|" not in line),
                   "parents_without_promoted_weather": len(contests) - promoted_count,
                   "contests_by_relation_state": dict(sorted(by_state.items())),
                   "contests_by_calendar_year": dict(sorted(by_year.items())),
                   "contests_by_classification_pair": dict(sorted(by_pair.items())),
                   "pilots_by_calendar_year": dict(sorted(pilot_by_year.items())),
                   "dome_reference_rows": sum(1 for r in pilots if r["venue_dome"] is True),
                   "provider_start_time_tbd": sum(1 for g in GAMES.values() if g[8]),
                   "raw_bytes": sum(v["bytes"] for v in raw.values())}}


def contract_for(world: dict[str, Any], anchors: dict[str, Any], **patch: Any) -> dict[str, Any]:
    contract = {"schema_version": "1.0.0", "contract_id": we.CONTRACT_ID, "jira_key": "BAT-731", "cycle_number": 60,
                "attempt_number": 1, "population_id": we.POPULATION, "inputs": anchors["inputs"], "raw": anchors["raw"],
                "parent_contracts": anchors["parent_contracts"], "clocks": anchors["clocks"],
                "rights": anchors["rights"], "expected": anchors["expected"], "rules": we.rules_document(),
                "outputs": {"database": we.DB_FILE}}
    contract.update(patch)
    return contract


def write_contract(path: Path, contract: dict[str, Any]) -> Path:
    Path(path).write_text(json.dumps(contract, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return Path(path)


def contract_anchors(path: Path, repo_root: Path) -> dict[str, Any]:
    return builder().load_contract(path, repo_root)[2]


def run_build(contract_path: Path, world: dict[str, Any], out: Path, *extra: str
              ) -> tuple[int, dict[str, Any] | None, str]:
    argv = ["--contract", str(contract_path), "--data-root", str(world["data_root"]),
            "--output-root", str(Path(out) / "canonical" / POP), "--manifest-root", str(Path(out) / "manifests" / POP),
            "--repo-root", str(world["repo_root"]), *extra]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = builder().main(argv)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


def refusal(stderr: str) -> str | None:
    text = stderr.strip()
    return json.loads(text.splitlines()[-1]).get("refused") if text else None


def database_of(result: dict[str, Any]) -> Path:
    return Path(result["release"]["data_dir"]) / we.DB_FILE


def manifest_of(database: Path) -> Path:
    return we.manifest_path_for(Path(database))


def query(anchors: dict[str, Any], database: Path, *argv: str, front: Callable | None = None) -> tuple[int, Any, str]:
    """The query's main() in process with fixture anchors; returns (exit, parsed stdout or None, stderr)."""
    from aggie_analytics.weather_evidence import query as q  # noqa: PLC0415

    tokens = ["--database", str(database), *argv]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = (front or q.main)(tokens, anchors=anchors)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


# --------------------------------------------------------------------------------------------- forged releases

class Forger:
    """Coordinated forgeries of one weather evidence database in owned scratch (adapted from the C59 Forger)."""

    def __init__(self, database: Path, root: Path, anchors: dict[str, Any]) -> None:
        self.database = Path(database)
        self.root = Path(root)
        self.anchors = anchors
        self.manifest = json.loads(manifest_of(self.database).read_text(encoding="utf-8"))

    def tables(self) -> dict[str, list[dict[str, Any]]]:
        conn = sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True)
        out: dict[str, list[dict[str, Any]]] = {t: [] for t, _s in we.BLOCK_LAYOUT}
        for table, blob in conn.execute("SELECT record_table, block FROM blocks ORDER BY ord"):
            out[table] += [json.loads(line) for line in zlib.decompress(blob).decode("utf-8").splitlines()]
        conn.close()
        return out

    def forge(self, name: str, *, records: Callable[[dict[str, list[dict[str, Any]]]], None] | None = None,
              lines: Callable[[dict[str, list[str]]], None] | None = None, meta: dict[str, Any] | None = None,
              document: dict[str, Any] | Callable[[dict[str, Any]], None] | None = None,
              after_blocks: list[tuple[str, tuple]] | None = None, identity_override: str | None = None,
              manifest_patch: dict[str, Any] | None = None, manifest_text: Callable[[str], str] | None = None,
              rehash_content: bool = True, provenance: Any = None) -> Path:
        """Copy, mutate and rehash. ``records`` edits the decoded record lists in place (blocks are rebuilt by
        segment from canonical lines with consistent index columns); ``lines`` edits raw lines per table;
        ``meta`` replaces meta values; ``document`` patches the identity document; ``rehash_content`` (default) also
        rebuilds the content document, the content identity meta claim and the manifest's content members (a
        coordinated rehash); ``after_blocks`` runs after the rebuild; ``manifest_text`` rewrites the manifest text."""
        work = self.root / name / "work.sqlite"
        work.parent.mkdir(parents=True)
        shutil.copyfile(self.database, work)
        conn = sqlite3.connect(work)
        conn.execute("PRAGMA journal_mode = OFF")
        content_doc = copy.deepcopy(self.manifest["content_document"])
        content_identity = self.manifest["content_identity"]
        if records is not None or lines is not None:
            tables = self.tables()
            if records is not None:
                records(tables)
            raw = {t: [we.canonical_line(r) for r in rows] for t, rows in tables.items()}
            if lines is not None:
                lines(raw)
            conn.execute("DELETE FROM blocks")
            grouped: dict[tuple[str, str], list[tuple[str, dict[str, Any]]]] = {}
            last_segment = {table: segment for table, segment in we.BLOCK_LAYOUT}
            for table, table_lines in raw.items():
                for line in table_lines:
                    try:
                        value = json.loads(line)
                    except (ValueError, RecursionError):
                        value = {}
                    value = value if isinstance(value, dict) else {}
                    seg = "GLOBAL" if table == "census" else we.segment_of_untrusted(table, value)
                    if (table, seg) not in we.BLOCK_LAYOUT:
                        seg = last_segment[table]
                    grouped.setdefault((table, seg), []).append((line, value))
            for ord_, (table, segment) in enumerate(we.BLOCK_LAYOUT):
                chosen = [line for line, _v in grouped.get((table, segment), [])]
                parsed = [v for _l, v in grouped.get((table, segment), [])]
                data = "".join(l + "\n" for l in chosen).encode("utf-8")
                conn.execute("INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (ord_, table, segment, len(chosen),
                              we.record_key(table, parsed[0]) if parsed else None,
                              we.record_key(table, parsed[-1]) if parsed else None,
                              we.sha256_bytes(data), zlib.compress(data, 9)))
            if rehash_content:
                derived = {t: [json.loads(l) for l in raw[t]] for t in we.RECORD_TABLES}
                derived["census"] = json.loads(raw["census"][0])
                derived["lines"] = raw
                content_doc = we.content_document(self.anchors, derived)
                content_identity = we.sha256_bytes(we.canonical_json_bytes(content_doc))
                for key, value in we.meta_values(self.anchors, content_identity, derived).items():
                    conn.execute("UPDATE meta SET value = ? WHERE key = ?", (value, key))
        for key, value in (meta or {}).items():
            text = value if isinstance(value, str) else we.canonical_line(value)
            if conn.execute("UPDATE meta SET value = ? WHERE key = ?", (text, key)).rowcount != 1:
                raise AssertionError(f"meta forgery {key} changed nothing")
        for sql, params in after_blocks or []:
            if conn.execute(sql, params).rowcount < 1:
                raise AssertionError(f"block forgery changed nothing: {sql}")
        conn.commit()
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in we.TABLES}
        conn.close()
        doc = copy.deepcopy(self.manifest["identity_document"])
        doc["outputs"] = {we.DB_FILE: we.sha256_file(work)}
        doc["table_counts"] = counts
        doc["content_identity"] = content_identity
        if callable(document):
            document(doc)
        else:
            doc.update(document or {})
        identity = identity_override or we.sha256_bytes(we.canonical_json_bytes(doc))
        target = self.root / name / "canonical" / POP / "sha256" / identity / we.DB_FILE
        target.parent.mkdir(parents=True)
        shutil.move(str(work), str(target))
        man = self.root / name / "manifests" / POP / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        body = {"identity": identity, "identity_document": doc, "content_identity": content_identity,
                "content_document": content_doc, "provenance": provenance if provenance is not None else
                {"forgery": name}}
        body.update(manifest_patch or {})
        text = json.dumps(body)
        if manifest_text is not None:
            text = manifest_text(text)
        man.write_text(text, encoding="utf-8")
        return target
