"""A tiny national personnel evidence world built through the real input formats (BAT-730, Cycle #59 TP59-A01).

Every input the release consumes is written in its retained physical form: the membership parent, its quarantine and
the candidate season files (Parquet with the parents' exact columns), raw roster and player-stat captures with their
capture manifests, the player event metric parent, the retained original returning-production research (produced by
the accepted original research code, ``aggie_analytics.features.returning_production``), the accepted parent
population (SQLite), the C38 identity bindings (gzip JSON lines) and a BAT-387 core registry (CSV), plus one parent
contract in a tiny checkout. Planted classes: a multi-team player-season, duplicate nonadmitted source keys, every
exclusion disposition, a qualified chain without roster rows (FCS), a binding that is not accepted, a CFBD ID without an
SRC-002 entity next to an SRC-001 SOURCE_MAPPING row with the same numeric key (never joined), an entity that is not an
accepted assignment, two entities for one CFBD ID, two programs sharing one canonical team in a season, a program
without any binding row, a division conflict, a DII opponent outside the census, a roster team without a census
program, a missing category/stat pair, a signed-yardage ratio above 1, a zero signed denominator, the partial 2020
metric season and the 2015 (prior 2014) transition outside the census."""
from __future__ import annotations

import contextlib
import copy
import csv
import gzip
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

from aggie_analytics.personnel_evidence import evidence as pe  # noqa: E402

POP = pe.POPULATION
KNOWN = pe.SOURCE_KNOWN_AT
COMMIT = pe.SOURCE_COMMIT
SCHEMA_SHA = "b" * 64
METRIC_SCHEMA_SHA = "c" * 64
POPULATION_CONTRACT = "d" * 64
ROSTER_ID = "1" * 64
METRIC_ID = "2" * 64
CANDIDATE_ID = "3" * 64
METRIC_CANDIDATE_ID = "4" * 64
RETURNING_ID = "5" * 64
POPULATION_ID = "6" * 64


def builder() -> Any:
    sys.path.insert(0, str(ROOT / "tools"))
    import build_national_personnel_evidence as b  # noqa: PLC0415

    return b


def _h(text: str, n: int = 32) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def team(name: str) -> str:
    return "team_" + _h("team:" + name)


def player(n: int) -> str:
    return "player_" + _h(f"player:{n}")


def _sha(path: Path) -> str:
    return pe.sha256_file(path)


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, sort_keys=True), encoding="utf-8")
    return path


def _pl() -> Any:
    import polars as pl  # noqa: PLC0415 - the test extra's pinned Parquet writer

    return pl


def _write_parquet(path: Path, rows: list[dict[str, Any]], fields: tuple[str, ...], schema: dict[str, Any]) -> Path:
    pl = _pl()
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pl.DataFrame({f: [r[f] for r in rows] for f in fields}, schema={f: schema[f] for f in fields})
    frame.write_parquet(path, compression="zstd", statistics=True)
    return path


TEAMS = {  # canonical label -> (canonical team id, cfbd id or None)
    "Alpha": (team("Alpha"), "1001"), "Bravo": (team("Bravo"), "1002"), "Charlie": (team("Charlie"), "1003"),
    "Delta": (team("Delta"), "1099"), "Echo": (team("Echo"), "2001"), "Foxtrot": (team("Foxtrot"), "2004"),
    "Golf": (team("Golf"), "2007"),
}
#: org id -> (division per contest, binding rule, cfbd id, binding reason)
ORGS = {
    "101": ("FBS", "NAME_CONFIRMED_BY_SCHEDULE", "1001", None),
    "102": ("FBS", "SCHEDULE_FINGERPRINT_ONLY", "1002", None),
    "103": ("FBS", "NAME_CONFIRMED_BY_SCHEDULE", "1003", None),
    "201": ("FCS", "NAME_CONFIRMED_BY_SCHEDULE", "2001", None),
    "202": ("FCS", None, None, "NO_SCHEDULE_EVIDENCE"),
    "203": ("FCS", "NAME_CONFIRMED_BY_SCHEDULE", "2003", None),
    "204": ("FCS", "NAME_CONFIRMED_BY_SCHEDULE", "2004", None),
    "205": ("FCS", "SCHEDULE_FINGERPRINT_ONLY", "2004", None),
    "206": ("FCS", None, None, None),
    "207": ("FCS", "NAME_CONFIRMED_BY_SCHEDULE", "2007", None),
    "208": ("FCS", "NAME_CONFIRMED_BY_SCHEDULE", "2008", None),
    "209": ("FCS", "NAME_CONFIRMED_BY_SCHEDULE", "2009", None),
    "301": ("DII", None, None, "NO_NAME_CANDIDATE_AND_FINGERPRINT_BELOW_THRESHOLD"),
}
ROSTER_SEASONS = (2014, 2015, 2016, 2019, 2020, 2021)
METRIC_SEASONS = (2014, 2015, 2019, 2020)


def _roster_plan() -> dict[int, dict[str, list[int]]]:
    """season -> team label -> player numbers (players overlap across seasons to make returning sets)."""
    plan: dict[int, dict[str, list[int]]] = {}
    plan[2014] = {"Alpha": [1, 2, 3, 4, 5], "Bravo": [20, 21, 22]}
    plan[2015] = {"Alpha": [1, 2, 3, 6, 7], "Bravo": [20, 21, 23, 24], "Delta": [40, 41]}
    plan[2016] = {"Alpha": [1, 2, 6, 8], "Bravo": [20, 23, 25], "Charlie": [1, 30, 31], "Delta": [40, 42]}
    plan[2019] = {"Alpha": [50, 51, 52, 53], "Bravo": [60, 61, 62]}
    plan[2020] = {"Alpha": [50, 51, 54], "Bravo": [60, 63]}
    plan[2021] = {"Alpha": [50, 54, 55], "Bravo": [60, 61, 63, 64]}
    return plan


def _metric_plan() -> list[tuple[int, str, int, str, str, int]]:
    """(season, team label, player, category, stat, value): signed yardage above 1 (Alpha 2014 rushing YDS), a missing
    pair (Bravo 2015 interceptions INT), a zero signed denominator (Alpha 2019 passing YDS) and the partial 2020."""
    rows: list[tuple[int, str, int, str, str, int]] = []
    for season, label, players in ((2014, "Alpha", [1, 2, 3, 4, 5]), (2014, "Bravo", [20, 21, 22]),
                                   (2015, "Alpha", [1, 2, 3, 6, 7]), (2015, "Bravo", [20, 21, 23, 24]),
                                   (2019, "Alpha", [50, 51, 52, 53]), (2019, "Bravo", [60, 61, 62]),
                                   (2020, "Alpha", [50, 51, 54]), (2020, "Bravo", [60, 63])):
        for i, p in enumerate(players):
            rows.append((season, label, p, "receiving", "REC", 2 + i))
            rows.append((season, label, p, "receiving", "YDS", 20 + 7 * i))
            rows.append((season, label, p, "rushing", "CAR", 3 + i))
            if not (season == 2015 and label == "Bravo"):
                rows.append((season, label, p, "interceptions", "INT", i % 2))
            if season == 2019 and label == "Alpha":
                rows.append((season, label, p, "passing", "YDS", 10 if i % 2 == 0 else -10))
            else:
                rows.append((season, label, p, "passing", "YDS", 100 + 10 * i))
            if season == 2014 and label == "Alpha" and p == 4:
                rows.append((season, label, p, "rushing", "YDS", -30))
            else:
                rows.append((season, label, p, "rushing", "YDS", 15 + i))
    return rows


def build_world(base: Path) -> dict[str, Any]:
    """Write every input under ``base/data`` (and one parent contract under ``base/repo``); return the world."""
    pl = _pl()
    data = Path(base) / "data"
    repo = Path(base) / "repo"
    data.mkdir(parents=True)
    contract_rel = "configs/tiny_parent_contract.json"
    _write_json(repo / contract_rel, {"tiny": "parent contract"})
    plan = _roster_plan()
    athlete = {}
    candidates_by_season: dict[int, list[dict[str, Any]]] = {}
    roster_captures, metric_captures = [], []
    obs_counter = [0]

    def obs() -> str:
        obs_counter[0] += 1
        return "hist_roster_" + _h(f"obs:{obs_counter[0]}", 24)

    raw_root = data / "raw" / "historical_known_at" / "github" / "sha256"
    cap_root = data / "manifests" / "historical_known_at" / "captures"
    roster_schema = {"athlete_id": pl.String, "first_name": pl.String, "last_name": pl.String, "team": pl.String,
                     "weight": pl.Int32, "height": pl.Int32, "jersey": pl.Int32, "year": pl.Int32,
                     "position": pl.String, "season": pl.Int32}
    roster_fields = tuple(roster_schema)
    for season in ROSTER_SEASONS:
        rows: list[dict[str, Any]] = []
        for label, players in plan[season].items():
            for p in players:
                athlete.setdefault(p, str(100000 + p))
                rows.append({"kind": "ADMITTED", "label": label, "player": p})
        # nonadmitted rows of every disposition, duplicates and an admitted athlete repeated
        extra = [("CANDIDATE_VERSIONED_REPOSITORY_ROSTER_SOURCE_LEVEL_ONLY", "Murray State", 900 + season, None),
                 ("CANDIDATE_VERSIONED_REPOSITORY_ROSTER_SOURCE_LEVEL_ONLY", "Murray State", 900 + season, None),
                 ("QUARANTINE_CANONICAL_ROSTER_MEMBERSHIP_AMBIGUOUS", "Alpha", 950, "Alpha"),
                 ("QUARANTINE_CURRENT_ROSTER_ATHLETE_NAME_CONFLICT", "Bravo", 960 + season, None),
                 ("QUARANTINE_CURRENT_ROSTER_MATCH_AMBIGUOUS", "Delta", 970, None),
                 ("QUARANTINE_INVALID_VERSIONED_ROSTER_CORE", "Unknown", 980, None)]
        for disposition, label, number, canonical in extra:
            rows.append({"kind": disposition, "label": label, "player": number, "canonical": canonical})
        if season == 2016:
            rows.append({"kind": "CANDIDATE_VERSIONED_REPOSITORY_ROSTER_SOURCE_LEVEL_ONLY", "label": "Alpha",
                         "player": 1, "canonical": None})
        raw = []
        for i, row in enumerate(rows):
            number = row["player"]
            raw.append({"athlete_id": athlete.get(number, str(100000 + number)), "first_name": f"First{number}",
                        "last_name": f"Last{number}", "team": row["label"], "weight": None if i % 3 == 0 else 200 + i,
                        "height": 70 + (i % 5), "jersey": None if i % 4 == 0 else i, "year": None if season == 2014
                        else 1 + (i % 4), "position": None if i % 5 == 0 else "WR", "season": season})
        tmp = raw_root / "tmp.parquet"
        _write_parquet(tmp, raw, roster_fields, roster_schema)
        payload_sha = _sha(tmp)
        raw_path = raw_root / payload_sha / "payload.parquet"
        raw_path.parent.mkdir(parents=True)
        tmp.replace(raw_path)
        capture_id = _h(f"rostercap:{season}", 64)
        acquired = "2026-08-10T14:35:00Z"
        cap = _write_json(cap_root / f"{capture_id}.json", {
            "capture_id": capture_id, "season": season, "commit_sha": COMMIT, "commit_committer_date": KNOWN,
            "acquired_at_utc": acquired, "source_path": f"cfb/roster/parquet/roster_{season}.parquet",
            "repository": pe.SOURCE_REPOSITORY, "domain": "roster",
            "payload": {"sha256": payload_sha, "logical_path": "<external-data-root>\\" +
                        _rel(raw_path, data).replace("/", "\\"), "bytes": raw_path.stat().st_size}})
        roster_captures.append({"season": season, "capture_id": capture_id, "payload_sha256": payload_sha,
                                "commit_sha": COMMIT, "committer_utc": KNOWN, "acquired_at_utc": acquired,
                                "source_path": f"cfb/roster/parquet/roster_{season}.parquet",
                                "repository": pe.SOURCE_REPOSITORY, "manifest_input": f"roster_capture_{season}",
                                "payload_input": f"roster_raw_{season}", "_manifest": cap, "_raw": raw_path})
        cand = []
        for i, (row, rawrow) in enumerate(zip(rows, raw)):
            admitted = row["kind"] == "ADMITTED"
            label = row["label"]
            canonical_team = TEAMS[label][0] if admitted else (TEAMS[row["canonical"]][0] if row.get("canonical")
                                                                else None)
            canonical_player = player(row["player"]) if admitted or row.get("canonical") else None
            if row["kind"] == "QUARANTINE_CURRENT_ROSTER_ATHLETE_NAME_CONFLICT":
                canonical_player = player(row["player"])
            record = {
                "schema_version": "1.0.0", "observation_id": obs(), "source_row_number": i,
                "athlete_id": rawrow["athlete_id"], "athlete_id_occurrence": 0,
                "canonical_player_id": canonical_player,
                "canonical_membership_player_id": canonical_player if (admitted or row.get("canonical")) else None,
                "canonical_team_id": canonical_team, "canonical_team_label": label if canonical_team else None,
                "canonical_membership_resolution_state": "AUTO_ACCEPTED_VERIFIED" if canonical_team else None,
                "first_name": rawrow["first_name"], "last_name": rawrow["last_name"], "team": rawrow["team"],
                "weight": rawrow["weight"], "height": rawrow["height"], "jersey": rawrow["jersey"],
                "class_year": rawrow["year"], "position": rawrow["position"], "home_city": None if i % 2 else "Town",
                "home_state": None if i % 2 else "TX", "home_country": None if i % 2 else "USA",
                "home_latitude": "30.1", "home_longitude": "-96.3", "home_county_fips": "48041",
                "recruit_ids_json": "[0]", "headshot_url": f"https://example.invalid/{rawrow['athlete_id']}.png",
                "season": season, "source_capture_id": capture_id, "source_payload_sha256": payload_sha,
                "source_commit_sha": COMMIT, "source_known_at_utc": KNOWN, "source_schema_sha256": SCHEMA_SHA,
                "source_record_evidence_sha256": _h(f"evidence:{season}:{i}", 64), "current_cfbd_id_match": False,
                "current_cfbd_name_match": False, "current_cfbd_match_count": 0, "current_cfbd_name_match_count": 0,
                "current_cfbd_team_name_match_count": 0, "current_cfbd_match_ambiguous": False,
                "current_cfbd_capture_id": None, "current_cfbd_payload_sha256": None,
                "current_cfbd_request_sha256": None, "current_first_name": "Current" if i == 1 else None,
                "current_last_name": None, "current_team": None, "current_weight": None, "current_height": None,
                "current_jersey": None, "current_class_year": None, "current_position": None,
                "team_label_exact_match": admitted, "canonical_membership_option_count": 1 if admitted else 0,
                "canonical_membership_exact_team_option_count": 1 if admitted else 0,
                "canonical_membership_ambiguous": False, "upstream_independence":
                    "NOT_CLAIMED_SHARED_ESPN_DERIVATION_POSSIBLE",
                "admission_state": "CANDIDATE_NOT_ADMITTED", "reconciliation_disposition":
                    pe.ELIGIBLE_DISPOSITION if admitted else row["kind"],
                "downstream_pit_contract": "REQUIRES_ROSTER_DOMAIN_GATE", "row_lineage_sha256": _h(f"lin:{season}:{i}",
                                                                                                 64)}
            cand.append(record)
        candidates_by_season[season] = cand
    cschema = {f: pl.String for f in pe.CANDIDATE_FIELDS}
    for f in ("source_row_number", "athlete_id_occurrence", "weight", "height", "jersey", "class_year", "season",
              "current_cfbd_match_count", "current_cfbd_name_match_count", "current_cfbd_team_name_match_count",
              "current_weight", "current_height", "current_jersey", "current_class_year",
              "canonical_membership_option_count", "canonical_membership_exact_team_option_count"):
        cschema[f] = pl.Int64
    for f in ("current_cfbd_id_match", "current_cfbd_name_match", "current_cfbd_match_ambiguous",
              "team_label_exact_match", "canonical_membership_ambiguous"):
        cschema[f] = pl.Boolean
    cand_root = data / "quarantine" / "historical_known_at" / "sha256" / CANDIDATE_ID / "rosters"
    candidate_files = {}
    for season, rows in candidates_by_season.items():
        schema = dict(cschema)
        if season == 2014:
            schema["class_year"] = pl.Null
        candidate_files[season] = _write_parquet(cand_root / f"season={season}" / "candidate_roster_rows.parquet",
                                                 rows, pe.CANDIDATE_FIELDS, schema)
    all_candidates = [r for s in ROSTER_SEASONS for r in candidates_by_season[s]]
    admitted = [r for r in all_candidates if r["reconciliation_disposition"] == pe.ELIGIBLE_DISPOSITION]
    members = []
    for r in admitted:
        m = {f: r[f] for f in pe.ADMITTED_FIELDS}
        m.update(pe.MEMBERSHIP_STATES)
        members.append(m)
    members.sort(key=lambda m: (m["season"], m["canonical_player_id"], m["canonical_team_id"], m["observation_id"]))
    mschema = {f: pl.String for f in pe.MEMBERSHIP_PARENT_FIELDS}
    for f in ("class_year", "jersey", "height", "weight", "season"):
        mschema[f] = pl.Int64
    for f in ("season_roster_membership", "game_time_availability", "depth_or_starter_status", "protected_eligible"):
        mschema[f] = pl.Boolean
    roster_payload = _write_parquet(data / "pit_state" / "historical_known_at" / "sha256" / ROSTER_ID /
                                    "historical_roster_memberships.parquet", members, pe.MEMBERSHIP_PARENT_FIELDS,
                                    mschema)
    quarantine = sorted((r for r in all_candidates if r["reconciliation_disposition"] != pe.ELIGIBLE_DISPOSITION),
                        key=lambda r: (r["season"], r["observation_id"]))
    nonadmitted = _write_parquet(data / "quarantine" / "historical_known_at" / "sha256" / ROSTER_ID /
                                 "historical_roster_membership_nonadmitted.parquet", quarantine, pe.CANDIDATE_FIELDS,
                                 cschema)
    roster_manifest = _write_json(data / "manifests" / "historical_known_at" / "sha256" / ROSTER_ID /
                                  "historical_roster_membership_pit_manifest.json",
                                  {"dataset_identity": ROSTER_ID, "issued_at_utc": "2026-08-11T17:50:00Z"})
    candidate_manifest = _write_json(data / "manifests" / "historical_known_at" / "sha256" / CANDIDATE_ID /
                                     "roster_history_reconciliation.json",
                                     {"dataset_identity": CANDIDATE_ID, "issued_at_utc": "2026-08-10T14:34:03Z"})
    # player metrics, their raw captures and manifests
    metric_rows = []
    player_stats_schema = {"game_id": pl.Int32, "season": pl.Int32, "reception_player_id": pl.Int32,
                           "reception_yds": pl.Int32}
    for season in METRIC_SEASONS:
        tmp = raw_root / "tmpm.parquet"
        _write_parquet(tmp, [{"game_id": 1, "season": season, "reception_player_id": 1, "reception_yds": 5}],
                       tuple(player_stats_schema), player_stats_schema)
        payload_sha = _sha(tmp)
        raw_path = raw_root / payload_sha / "payload.parquet"
        raw_path.parent.mkdir(parents=True)
        tmp.replace(raw_path)
        capture_id = _h(f"metriccap:{season}", 64)
        acquired = "2026-08-10T14:52:13Z"
        cap = _write_json(cap_root / f"{capture_id}.json", {
            "capture_id": capture_id, "season": season, "commit_sha": COMMIT, "commit_committer_date": KNOWN,
            "acquired_at_utc": acquired, "source_path": f"player_stats/parquet/player_stats_{season}.parquet",
            "repository": pe.SOURCE_REPOSITORY, "domain": "player_stats",
            "payload": {"sha256": payload_sha, "logical_path": "<external-data-root>\\" +
                        _rel(raw_path, data).replace("/", "\\"), "bytes": raw_path.stat().st_size}})
        metric_captures.append({"season": season, "capture_id": capture_id, "payload_sha256": payload_sha,
                                "commit_sha": COMMIT, "committer_utc": KNOWN, "acquired_at_utc": acquired,
                                "source_path": f"player_stats/parquet/player_stats_{season}.parquet",
                                "repository": pe.SOURCE_REPOSITORY, "manifest_input": f"metric_capture_{season}",
                                "payload_input": f"metric_raw_{season}", "_manifest": cap, "_raw": raw_path})
    capture_of = {c["season"]: c for c in metric_captures}
    for n, (season, label, p, category, stat, value) in enumerate(_metric_plan()):
        c = capture_of[season]
        metric_rows.append({
            "observation_id": "hist_player_metric_" + _h(f"m:{n}", 24), "season": season, "game_id": 400000 + n,
            "canonical_game_id": "game_" + _h(f"g:{n}"), "player_id": athlete.get(p, str(100000 + p)),
            "canonical_player_id": player(p), "canonical_membership_player_id": player(p),
            "canonical_team_id": TEAMS[label][0], "canonical_team_label": label, "category": category,
            "stat_type": stat, "aggregation": "COUNT" if stat in ("REC", "CAR") else "SUM", "source_value": value,
            "source_event_rows": 1 + (n % 3), "source_capture_id": c["capture_id"],
            "source_payload_sha256": c["payload_sha256"], "source_commit_sha": COMMIT, "source_known_at_utc": KNOWN,
            "source_schema_sha256": METRIC_SCHEMA_SHA, "source_aggregate_evidence_sha256": _h(f"agg:{n}", 64),
            "current_capture_id": "cap_x", "current_payload_sha256": "e" * 64, "current_request_sha256": "f" * 64,
            "upstream_independence": "NOT_CLAIMED_SHARED_ESPN_DERIVATION_POSSIBLE",
            "reconciliation_disposition": pe.METRIC_DISPOSITION, "row_lineage_sha256": _h(f"mlin:{n}", 64),
            "admission_state": pe.METRIC_ADMISSION_STATE, "official_player_box_complete": False,
            "partial_source_season": season in pe.PARTIAL_METRIC_SEASONS, "protected_eligible": False})
    meschema = {f: pl.String for f in pe.METRIC_FIELDS}
    for f in ("season", "game_id", "source_value", "source_event_rows"):
        meschema[f] = pl.Int64
    for f in ("official_player_box_complete", "partial_source_season", "protected_eligible"):
        meschema[f] = pl.Boolean
    metric_payload = _write_parquet(data / "pit_state" / "historical_known_at" / "sha256" / METRIC_ID /
                                    "player_event_metrics.parquet", metric_rows, pe.METRIC_FIELDS, meschema)
    metric_manifest = _write_json(data / "manifests" / "historical_known_at" / "sha256" / METRIC_ID /
                                  "player_event_metric_pit_manifest.json",
                                  {"dataset_identity": METRIC_ID, "issued_at_utc": "2026-08-11T14:05:00Z"})
    metric_candidate_manifest = _write_json(data / "manifests" / "historical_known_at" / "sha256" / METRIC_CANDIDATE_ID
                                            / "player_event_metric_reconciliation.json",
                                            {"dataset_identity": METRIC_CANDIDATE_ID,
                                             "issued_at_utc": "2026-08-10T15:00:00Z"})
    # the retained original research, produced by the accepted original research code
    from aggie_analytics.features import returning_production as rp  # noqa: PLC0415

    features, components, coverage = rp.calculate_transition_records(
        [dict(m) for m in members], [dict(r) for r in metric_rows], list(pe.TARGET_SEASONS),
        pe.RETURNING_CLASSIFICATION, set(pe.PARTIAL_METRIC_SEASONS))
    ret_root = data / "features" / "returning_production_research" / "sha256" / RETURNING_ID
    files = {}
    for name, records, fields, file in (("returning_transitions", features, pe.ORIGINAL_TRANSITION_FIELDS,
                                         "team_season_transition_features.parquet"),
                                        ("returning_components", components, pe.ORIGINAL_COMPONENT_FIELDS,
                                         "returning_production_components.parquet"),
                                        ("returning_coverage", coverage, pe.ORIGINAL_COVERAGE_FIELDS,
                                         "transition_coverage.parquet")):
        ret_root.mkdir(parents=True, exist_ok=True)
        pl.DataFrame(records).select(list(fields)).write_parquet(ret_root / file, compression="zstd", statistics=True)
        files[name] = ret_root / file
    returning_manifest = _write_json(data / "manifests" / "returning_production_research" / "sha256" / RETURNING_ID /
                                     "run_manifest.json", {"dataset_identity": RETURNING_ID,
                                                           "issued_at_utc": "2026-08-12T08:05:00Z"})
    # the accepted parent population, identity bindings and core registry
    pop_path = data / "canonical" / "national_di_population_2016_2025" / "sha256" / POPULATION_ID / \
        "national_population.sqlite"
    pop_path.parent.mkdir(parents=True)
    conn = sqlite3.connect(pop_path)
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO meta VALUES ('contract_sha256', ?)", (POPULATION_CONTRACT,))
    conn.execute(f"CREATE TABLE contest ({', '.join(pe.PARENT_CONTEST_COLUMNS)})")
    contests = []
    n = 0
    for season in (2016, 2020, 2021):
        pairs = [("101", "102"), ("101", "201"), ("102", "202"), ("103", "203"), ("204", "205"), ("206", "301"),
                 ("207", "208"), ("209", "101"), ("201", "207")] if season == 2016 else [("101", "102"),
                                                                                         ("201", "207")]
        for a, b in pairs:
            n += 1
            div_a = ORGS[a][0] if not (a == "207" and season == 2016) else "FBS"
            div_b = ORGS[b][0]
            contests.append((f"ncaa:{5000 + n}", season, f"{season}-09-{n:02d}", "VERIFIED_PRESENT" if n % 3 else
                             "CANDIDATE_ONLY", f"org:{a}", a, f"Org {a}", div_a, f"org:{b}", b, f"Org {b}", div_b))
    conn.executemany(f"INSERT INTO contest VALUES ({', '.join('?' * len(pe.PARENT_CONTEST_COLUMNS))})", contests)
    conn.commit()
    conn.close()
    bindings = [{"_header": {"contract_sha256": POPULATION_CONTRACT, "schema": "BAS-NATIONAL-DI-POPULATION-1"}}]
    for org, (_div, rule, cfbd, reason) in ORGS.items():
        if org == "206":
            continue
        bindings.append({"org_id": org, "cfbd_team_id": cfbd, "rule": rule, "reason": reason})
    bind_path = data / "canonical" / "national_di_population_2016_2025" / "sha256" / ("7" * 64) / \
        "identity_bindings.jsonl.gz"
    bind_path.parent.mkdir(parents=True)
    bind_path.write_bytes(gzip.compress("".join(json.dumps(b, sort_keys=True) + "\n" for b in bindings).encode("utf-8"),
                                        mtime=0))
    columns = ["record_type", "entity_type", "record_id", "canonical_id", "identity_key", "source_system_id",
               "source_entity_key", "mapping_method", "resolution_state", "alias"]
    entity_rows = []
    for label, (tid, cfbd) in TEAMS.items():
        entity_rows.append(["ENTITY", "team", tid, tid, f"TEAM|SRC-002|{cfbd}", "SRC-002", cfbd,
                            "INTERNAL_ASSIGNMENT_LEDGER_FROM_VERIFIED_SOURCE_IDENTITY", "AUTO_ACCEPTED_VERIFIED", ""])
    entity_rows.append(["SOURCE_MAPPING", "team", "obs_decoy", team("Decoy"), "", "SRC-001", "2003",
                        "SOURCE_ID_MAPPING", "AUTO_ACCEPTED_VERIFIED", ""])
    entity_rows.append(["ENTITY", "team", team("Hotel"), team("Hotel"), "TEAM|SRC-002|2008", "SRC-002", "2008",
                        "MANUAL_REVIEW", "REVIEW_REQUIRED", ""])
    for k in (1, 2):
        entity_rows.append(["ENTITY", "team", team(f"India{k}"), team(f"India{k}"), "TEAM|SRC-002|2009", "SRC-002",
                            "2009", "INTERNAL_ASSIGNMENT_LEDGER_FROM_VERIFIED_SOURCE_IDENTITY",
                            "AUTO_ACCEPTED_VERIFIED", ""])
    entity_rows.append(["ALIAS", "team", "obs_alias", team("Alpha"), "", "SRC-002", "", "COMPOSITE_CONTEXT",
                        "REVIEW_REQUIRED", "Alpha"])
    core_path = data / "canonical" / "BAT-387" / "sha256" / ("8" * 64) / "canonical_core_registry.csv"
    core_path.parent.mkdir(parents=True)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(entity_rows)
    core_path.write_bytes(buffer.getvalue().encode("utf-8"))
    return {"base": Path(base), "data_root": data, "repo_root": repo, "parent_contract_rel": contract_rel,
            "roster_payload": roster_payload, "nonadmitted": nonadmitted, "candidate_files": candidate_files,
            "roster_manifest": roster_manifest, "candidate_manifest": candidate_manifest,
            "metric_payload": metric_payload, "metric_manifest": metric_manifest,
            "metric_candidate_manifest": metric_candidate_manifest, "returning_files": files,
            "returning_manifest": returning_manifest, "population": pop_path, "bindings": bind_path,
            "core": core_path, "roster_captures": roster_captures, "metric_captures": metric_captures,
            "members": members, "quarantine": quarantine, "metric_rows": metric_rows, "original_features": features,
            "original_components": components, "original_coverage": coverage, "core_rows": len(entity_rows),
            "binding_rows": len(bindings) - 1}


def anchors_for(world: dict[str, Any]) -> dict[str, Any]:
    """The tiny world's pinned authority, shaped exactly like the production anchors."""
    data = world["data_root"]
    inputs: dict[str, dict[str, Any]] = {}

    def add(name: str, path: Path, kind: str, role: str, rights: list[str], supports: list[str], *, season=None,
            dataset_identity=None, issued_at_utc=None, rows=None, extra=None) -> None:
        if rows is None and kind == "PARQUET":
            rows = _pl().read_parquet(path).height
        inputs[name] = {"relative_path": _rel(path, data), "sha256": _sha(path), "bytes": path.stat().st_size,
                        "kind": kind, "role": role, "rows": rows, "season": season,
                        "dataset_identity": dataset_identity, "issued_at_utc": issued_at_utc,
                        "rights_source_ids": rights, "supports": supports, **(extra or {})}

    add("roster_payload", world["roster_payload"], "PARQUET", "ADMITTED_SEASON_ROSTER_MEMBERSHIP_PARENT", ["SRC-001"],
        ["roster-membership"], dataset_identity=ROSTER_ID)
    add("roster_manifest", world["roster_manifest"], "JSON", "ROSTER_MEMBERSHIP_PARENT_MANIFEST", ["SRC-001"],
        ["roster-membership"], dataset_identity=ROSTER_ID, issued_at_utc="2026-08-11T17:50:00Z")
    add("nonadmitted", world["nonadmitted"], "PARQUET", "NONADMITTED_ROSTER_QUARANTINE", ["SRC-001"],
        ["roster-exclusion"], dataset_identity=ROSTER_ID)
    add("candidate_manifest", world["candidate_manifest"], "JSON", "CANDIDATE_ROSTER_RECONCILIATION_MANIFEST",
        ["SRC-001"], ["roster-membership"], dataset_identity=CANDIDATE_ID, issued_at_utc="2026-08-10T14:34:03Z")
    for season, path in sorted(world["candidate_files"].items()):
        add(f"candidate_rosters_{season}", path, "PARQUET", "CANDIDATE_ROSTER_ROWS_WITH_RAW_SOURCE_ROW_NUMBERS",
            ["SRC-001"], ["roster-membership"], season=season, dataset_identity=CANDIDATE_ID)
    add("metric_payload", world["metric_payload"], "PARQUET", "ADMITTED_PLAYER_EVENT_METRIC_PARENT", ["SRC-001"],
        ["returning-component"], dataset_identity=METRIC_ID)
    add("metric_manifest", world["metric_manifest"], "JSON", "PLAYER_EVENT_METRIC_PARENT_MANIFEST", ["SRC-001"],
        ["returning-component"], dataset_identity=METRIC_ID, issued_at_utc="2026-08-11T14:05:00Z")
    add("metric_candidate_manifest", world["metric_candidate_manifest"], "JSON",
        "CANDIDATE_PLAYER_METRIC_RECONCILIATION_MANIFEST", ["SRC-001"], ["returning-component"],
        dataset_identity=METRIC_CANDIDATE_ID, issued_at_utc="2026-08-10T15:00:00Z")
    for name in ("returning_transitions", "returning_components", "returning_coverage"):
        add(name, world["returning_files"][name], "PARQUET", "ORIGINAL_" + name.upper(), ["SRC-001"],
            ["returning-summary"], dataset_identity=RETURNING_ID)
    add("returning_manifest", world["returning_manifest"], "JSON", "ORIGINAL_RETURNING_RESEARCH_MANIFEST", ["SRC-001"],
        ["returning-summary"], dataset_identity=RETURNING_ID, issued_at_utc="2026-08-12T08:05:00Z")
    add("population", world["population"], "SQLITE", "ACCEPTED_PARENT_POPULATION_2016_2022_CONTESTS",
        ["SRC-015", "SRC-002"], ["program-season-coverage"], dataset_identity=POPULATION_ID,
        extra={"contract_sha256": POPULATION_CONTRACT})
    add("identity_bindings", world["bindings"], "JSONL_GZ", "C38_ORG_TO_CFBD_IDENTITY_BINDINGS",
        ["SRC-015", "SRC-002"], ["program-season-coverage"], rows=world["binding_rows"],
        extra={"contract_sha256": POPULATION_CONTRACT})
    add("core_registry", world["core"], "CSV", "BAT387_CORE_REGISTRY_SRC002_TEAM_ENTITIES", ["SRC-002", "SRC-001"],
        ["program-season-coverage"], rows=world["core_rows"])
    captures: dict[str, list[dict[str, Any]]] = {"ROSTER": [], "METRIC": []}
    for kind, items, prefix in (("ROSTER", world["roster_captures"], "roster"),
                                ("METRIC", world["metric_captures"], "metric")):
        for c in items:
            add(f"{prefix}_capture_{c['season']}", c["_manifest"], "JSON", f"RAW_{kind}_CAPTURE_MANIFEST",
                ["SRC-001"], ["roster-membership"], season=c["season"])
            add(f"{prefix}_raw_{c['season']}", c["_raw"], "PARQUET", f"RAW_{kind}_SOURCE_PAYLOAD", ["SRC-001"],
                ["roster-membership"], season=c["season"])
            captures[kind].append({k: v for k, v in c.items() if not k.startswith("_")})
    expected = expected_for(world, inputs)
    return {"contract_id": pe.CONTRACT_ID, "contract_sha256": "0" * 64, "inputs": inputs, "captures": captures,
            "parent_contracts": {world["parent_contract_rel"]: _sha(world["repo_root"] / world["parent_contract_rel"])},
            "expected": expected}


def expected_for(world: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    members = world["members"]
    quarantine = world["quarantine"]
    programs = set()
    conn = sqlite3.connect(world["population"])
    for season, a, ad, b, bd in conn.execute("SELECT season, a_key, a_division_label, b_key, b_division_label FROM "
                                             "contest"):
        for key, division in ((a, ad), (b, bd)):
            if division in pe.CENSUS_DIVISIONS:
                programs.add((season, key))
    conn.close()
    program_keys = [f"{s}|{k}" for s, k in sorted(programs, key=lambda x: (x[0], int(x[1].split(":")[1])))]
    summary_keys = [f"{f['target_season']}|{f['canonical_team_id']}" for f in sorted(
        world["original_features"], key=lambda f: (f["target_season"], f["canonical_team_id"]))]
    component_keys = [f"{c['target_season']}|{c['canonical_team_id']}|{c['category']}|{c['stat_type']}" for c in sorted(
        world["original_components"], key=lambda c: (c["target_season"], c["canonical_team_id"], c["category"],
                                                     c["stat_type"]))]
    membership_keys = [m["observation_id"] for m in members]
    exclusion_keys = [q["observation_id"] for q in quarantine]
    witness_keys = [f"INPUT|{n}" for n in inputs] + [f"CONTRACT|{world['parent_contract_rel']}"]
    return {"memberships": len(membership_keys), "exclusions": len(exclusion_keys), "program_seasons": len(program_keys),
            "summaries": len(summary_keys), "components": len(component_keys), "witnesses": len(witness_keys),
            "coverage_rows": 8,
            "signed_ratios_outside_unit_interval": sum(1 for c in world["original_components"]
                                                       if c["outside_unit_interval"]),
            "memberships_keys_sha256": pe.keys_sha256(membership_keys),
            "exclusions_keys_sha256": pe.keys_sha256(exclusion_keys),
            "program_seasons_keys_sha256": pe.keys_sha256(program_keys),
            "summaries_keys_sha256": pe.keys_sha256(summary_keys),
            "components_keys_sha256": pe.keys_sha256(component_keys),
            "witnesses_keys_sha256": pe.keys_sha256(witness_keys),
            "program_seasons_keys": program_keys, "summaries_keys": summary_keys}


def contract_for(world: dict[str, Any], anchors: dict[str, Any], **patch: Any) -> dict[str, Any]:
    contract = {"schema_version": "1.0.0", "contract_id": pe.CONTRACT_ID, "jira_key": "BAT-730", "cycle_number": 59,
                "attempt_number": 1, "population_id": pe.POPULATION, "inputs": anchors["inputs"],
                "captures": anchors["captures"], "parent_contracts": anchors["parent_contracts"],
                "expected": anchors["expected"], "rules": pe.rules_document(),
                "outputs": {"database": pe.DB_FILE}}
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
    return Path(result["release"]["data_dir"]) / pe.DB_FILE


def manifest_of(database: Path) -> Path:
    return pe.manifest_path_for(Path(database))


def query(anchors: dict[str, Any], database: Path, *argv: str, front: Callable | None = None) -> tuple[int, Any, str]:
    """The query's main() in process with fixture anchors; returns (exit, parsed stdout or None, stderr)."""
    from aggie_analytics.personnel_evidence import query as q  # noqa: PLC0415

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
    """Coordinated forgeries of one personnel evidence database in owned scratch."""

    def __init__(self, database: Path, root: Path, anchors: dict[str, Any]) -> None:
        self.database = Path(database)
        self.root = Path(root)
        self.anchors = anchors
        self.manifest = json.loads(manifest_of(self.database).read_text(encoding="utf-8"))

    def tables(self) -> dict[str, list[dict[str, Any]]]:
        conn = sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True)
        out: dict[str, list[dict[str, Any]]] = {t: [] for t, _s in pe.BLOCK_LAYOUT}
        for table, blob in conn.execute("SELECT record_table, block FROM blocks ORDER BY ord"):
            out[table] += [json.loads(line) for line in zlib.decompress(blob).decode("utf-8").splitlines()]
        conn.close()
        return out

    def forge(self, name: str, *, records: Callable[[dict[str, list[dict[str, Any]]]], None] | None = None,
              lines: Callable[[dict[str, list[str]]], None] | None = None, meta: dict[str, Any] | None = None,
              document: dict[str, Any] | Callable[[dict[str, Any]], None] | None = None,
              after_blocks: list[tuple[str, tuple]] | None = None, identity_override: str | None = None,
              manifest_patch: dict[str, Any] | None = None, manifest_text: Callable[[str], str] | None = None,
              rehash_content: bool = False, provenance: Any = None) -> Path:
        """Copy, mutate and rehash. ``records`` edits the decoded record lists in place (blocks are rebuilt by
        segment from canonical lines with consistent index columns); ``lines`` edits raw lines per table;
        ``meta`` replaces meta values; ``document`` patches the identity document; ``rehash_content`` also rebuilds
        the content document, the content identity meta claim and the manifest's content members (a coordinated
        rehash); ``after_blocks`` runs after the rebuild; ``manifest_text`` rewrites the manifest's final JSON text."""
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
            raw = {t: [pe.canonical_line(r) for r in rows] for t, rows in tables.items()}
            if lines is not None:
                lines(raw)
            conn.execute("DELETE FROM blocks")
            grouped: dict[tuple[str, str], list[tuple[str, dict[str, Any]]]] = {}
            last_segment = {table: segment for table, segment in pe.BLOCK_LAYOUT}
            for table, table_lines in raw.items():
                for line in table_lines:
                    try:
                        value = json.loads(line)
                    except (ValueError, RecursionError):
                        value = {}
                    value = value if isinstance(value, dict) else {}
                    seg = "GLOBAL" if table == "census" else pe.segment_of_untrusted(table, value)
                    if (table, seg) not in pe.BLOCK_LAYOUT:
                        seg = last_segment[table]
                    grouped.setdefault((table, seg), []).append((line, value))
            for ord_, (table, segment) in enumerate(pe.BLOCK_LAYOUT):
                chosen = [line for line, _v in grouped.get((table, segment), [])]
                parsed = [v for _l, v in grouped.get((table, segment), [])]
                data = "".join(l + "\n" for l in chosen).encode("utf-8")
                conn.execute("INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (ord_, table, segment, len(chosen),
                              pe.record_key(table, parsed[0]) if parsed else None,
                              pe.record_key(table, parsed[-1]) if parsed else None,
                              pe.sha256_bytes(data), zlib.compress(data, 9)))
            if rehash_content:
                derived = {t: [json.loads(l) for l in raw[t]] for t in pe.RECORD_TABLES}
                derived["census"] = json.loads(raw["census"][0])
                derived["lines"] = raw
                content_doc = pe.content_document(self.anchors, derived)
                content_identity = pe.sha256_bytes(pe.canonical_json_bytes(content_doc))
                for key, value in pe.meta_values(self.anchors, content_identity, derived).items():
                    conn.execute("UPDATE meta SET value = ? WHERE key = ?", (value, key))
        for key, value in (meta or {}).items():
            text = value if isinstance(value, str) else pe.canonical_line(value)
            if conn.execute("UPDATE meta SET value = ? WHERE key = ?", (text, key)).rowcount != 1:
                raise AssertionError(f"meta forgery {key} changed nothing")
        for sql, params in after_blocks or []:
            if conn.execute(sql, params).rowcount < 1:
                raise AssertionError(f"block forgery changed nothing: {sql}")
        conn.commit()
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in pe.TABLES}
        conn.close()
        doc = copy.deepcopy(self.manifest["identity_document"])
        doc["outputs"] = {pe.DB_FILE: pe.sha256_file(work)}
        doc["table_counts"] = counts
        doc["content_identity"] = content_identity
        if callable(document):
            document(doc)
        else:
            doc.update(document or {})
        identity = identity_override or pe.sha256_bytes(pe.canonical_json_bytes(doc))
        target = self.root / name / "canonical" / POP / "sha256" / identity / pe.DB_FILE
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
