"""Synthetic national world for the BAT-712 source-time tests (Cycle #40 TP40-A01). Not a test module.

The parent population is materialized with the accepted BAT-710 builder (stage roots for page observations and
contests, then the query database), the history prefix with the accepted BAT-711 producer, and every bounded source
kind is written with the same layout and receipt shapes as the real lake: NCAA team-season pages bound by discovery
manifests (batch stamps, one missing receipt, one contradictory receipt), CFBD FBS route responses with per-request
receipts, CFBD FCS route responses with cache-hit ledger entries and two repository versions (an integer-typed 2019
Parquet and a string-typed 2020 Parquet) with commit responses binding their git blobs. Every value here is fictional;
nothing is real evidence. Short directory names keep Windows paths short.
"""
from __future__ import annotations

import contextlib
import copy
import gzip
import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from aggie_analytics.data import national_di_population as pop  # noqa: E402
import national_history_fixture as hfx  # noqa: E402

CONTRACT_PATH = ROOT / "configs" / "national_source_time_2016_2023_contract.json"
BUILDER_PATH = ROOT / "tools" / "build_national_source_time.py"
VALIDATOR_PATH = ROOT / "tools" / "validate_national_source_time.py"
PARENT_CONTRACT_SHA = hfx.PARENT_CONTRACT_SHA
#: org -> (CFBD team id bound by the parent, ESPN team id used by the repository); Echo's ids differ (namespace case)
IDS = {"1": ("101", "101"), "2": ("102", "102"), "3": ("103", "103"), "4": ("104", "104"), "5": ("105", "99105"),
       "6": ("106", "106")}
FCS = {"4", "6"}
NCAA_STAMP, EARLY_STAMP = "2026-08-13T10:39:56Z", "2026-08-12T04:59:49Z"
FBS_RECEIPTS = {2019: ("2026-08-09T18:59:48Z", "2026-08-09T18:59:49Z"), 2020: ("2026-08-09T16:57:37Z",
                                                                              "2026-08-09T16:57:39Z"),
                2023: ("2026-08-09T16:57:55Z", "2026-08-09T16:57:56Z")}
FCS_STAMP = "2026-09-09T18:08:43Z"
REPO_ACQUIRED = {2019: "2026-08-10T13:05:00Z", 2020: "2026-08-10T12:24:00Z"}
REPO_COMMIT = {2019: "2023-05-06T05:13:36Z", 2020: "2023-05-06T05:14:19Z"}


def load_tool(path: Path, name: str) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def builder() -> Any:
    return load_tool(BUILDER_PATH, "bas_source_time_builder")


def validator() -> Any:
    return load_tool(VALIDATOR_PATH, "bas_source_time_validator")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def contests() -> list[dict[str, Any]]:
    c = hfx.contest
    rows = [
        # 2019: FBS-FCS in both routes, a tie, a neutral site, the namespace case, a score conflict, a date outside the
        # declared US-local basis, an FCS-FCS contributor, a game with a missing page receipt and no repository row.
        c("ncaa:1001", 2019, "2019-08-31", "1", "4", 35, 10),
        c("ncaa:1002", 2019, "2019-08-31", "2", "3", 20, 20),
        c("ncaa:1008", 2019, "2019-09-07", "4", "6", 27, 24),
        c("ncaa:1003", 2019, "2019-09-07", "1", "2", 28, 21, site="NEUTRAL"),
        c("ncaa:1004", 2019, "2019-09-07", "3", "5", 14, 17),
        c("ncaa:1005", 2019, "2019-09-14", "3", "1", 10, 31),
        c("ncaa:1006", 2019, "2019-09-14", "2", "4", 24, 3),
        c("ncaa:1007", 2019, "2019-09-21", "1", "5", 24, 3),
        c("ncaa:1009", 2019, "2019-10-05", "6", "4", 10, 14),
        c("ncaa:1010", 2019, "2019-10-12", "1", "2", None, None, status="MIRROR_DISAGREEMENT", competitive=False,
          disposition="CONFLICT", state="CONFLICT"),
        c("ncaa:1011", 2019, "2019-10-12", "1", "2", None, None, status="MIRROR_DISAGREEMENT", competitive=False,
          disposition="CONFLICT", state="CONFLICT"),
        # 2020-21 academic year: a fall game, spring games under season 2020, one malformed repository score.
        c("ncaa:2001", 2020, "2020-10-03", "1", "2", 21, 14),
        c("ncaa:2002", 2020, "2021-03-06", "1", "3", 17, 13, term="SPRING"),
        c("ncaa:2003", 2020, "2021-03-13", "2", "3", 3, 7, term="SPRING"),
        # 2023: renamed program, no repository version for the season.
        c("ncaa:3001", 2023, "2023-09-02", "3", "1", 10, 24, a_name="Charlie State"),
        c("ncaa:3002", 2023, "2023-09-09", "1", "2", 30, 27),
        # Protected/exposed season: key-only.
        c("ncaa:4001", 2024, "2024-08-31", "1", "2", 31, 30, disposition="CANDIDATE_ONLY",
          state="SINGLE_SOURCE_UNRECONCILED"),
    ]
    for row in rows:
        row["cfbd_game_ids"] = [f"9{row['contest_key'].split(':')[1]}"]
    for row in rows:
        if row["contest_key"] == "ncaa:1011":
            row["cfbd_game_ids"] = ["91010"]  # two parent contests share one CFBD id (ambiguous candidate)
    return rows


def routes_for(row: dict[str, Any]) -> list[str]:
    fcs = row["a_org_id"] in FCS or row["b_org_id"] in FCS
    fbs = row["a_org_id"] not in FCS or row["b_org_id"] not in FCS
    return sorted((["CYCLE30_FCS"] if fcs else []) + (["SRC-002"] if fbs else []))


def page_html(team: str, season: int, games: list[dict[str, Any]]) -> bytes:
    rows = "".join(f'<tr><td>{g["date_text"]}</td><td><a href="/teams/{g["opponent_logo_org_id"]}">'
                   f'{g["opponent_name"]}</a></td><td><a href="/contests/{g["ncaa_contest_id"]}/box_score">'
                   f'{g["result_text"]}</a></td></tr>' for g in games)
    return (f"<html><body><h1>Fixture team {team} {season} (fictional)</h1><table><tbody>{rows}</tbody></table>"
            f"</body></html>").encode("utf-8")


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def jbytes(value: Any) -> bytes:
    return (json.dumps(value, indent=1, sort_keys=True) + "\n").encode("utf-8")


def gz_lines(records: list[dict[str, Any]], header: dict[str, Any]) -> bytes:
    text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in [{"_header": header}] + records)
    return gzip.compress(text.encode("utf-8"), mtime=0)


def build_world(base: Path) -> dict[str, Any]:
    """Write the whole synthetic lake under ``base`` and return paths, identities and the patched contract."""
    import polars as pl  # noqa: PLC0415

    base = Path(base)
    rows = contests()
    in_range = [r for r in rows if 2016 <= r["season"] <= 2023]
    # ---- NCAA pages: one page per (team, season); every 2016-2023 contest is on both participants' pages.
    pages: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in in_range:
        for side, other in (("a", "b"), ("b", "a")):
            team, opp = row[f"{side}_org_id"], row[f"{other}_org_id"]
            mine, theirs = row[f"{side}_points"], row[f"{other}_points"]
            result = None if mine is None else ("W" if mine > theirs else "L" if mine < theirs else "T") + \
                f" {mine}-{theirs}"
            month, day, year = row["contest_date"][5:7], row["contest_date"][8:10], row["contest_date"][:4]
            pages.setdefault((team, row["season"]), []).append({
                "season": row["season"], "ncaa_contest_id": row["ncaa_contest_id"], "date": row["contest_date"],
                "date_text": f"{month}/{day}/{year}", "result_text": result,
                "status": "COMPLETED" if mine is not None else "MIRROR_DISAGREEMENT", "page_org_id": team,
                "page_team_name": row[f"{side}_team_name"], "page_team_season_id": f"ts{team}-{row['season']}",
                "opponent_logo_org_id": opp, "opponent_name": row[f"{other}_team_name"], "team_points": mine,
                "opponent_points": theirs, "page_team_marked_away": side == "b" and row["site"] == "HOME_A",
                "neutral_site": "Fixture Bowl" if row["site"] == "NEUTRAL" else None, "event_label": None,
                "flags": []})
    observations, captures_by_season = [], {}
    for (team, season), games in sorted(pages.items()):
        for index, game in enumerate(games):
            game["row_index"] = index
        raw = page_html(team, season, games)
        raw_sha = sha(raw)
        write(base / "raw" / "SRC-015" / "ncaa_team_season_discovery" / f"{raw_sha}.html", raw)
        for game in games:
            observations.append(dict(game, page_raw_sha256=raw_sha))
        if (team, season) == ("5", 2019):
            continue  # Echo's 2019 page bytes exist but no bound manifest names them (receipt absent)
        stamp = EARLY_STAMP if team == "6" else NCAA_STAMP
        capture = {"team_season_id": f"ts{team}-{season}", "raw_sha256": raw_sha, "retrieved_at_utc": stamp,
                   "raw_relative_path": f"raw/SRC-015/ncaa_team_season_discovery/{raw_sha}.html",
                   "source_uri": f"https://example.invalid/fixture/teams/{team}/{season}", "snapshot_id": "fixture"}
        captures_by_season.setdefault(season, []).append(capture)
        if (team, season) == ("2", 2020):  # the same bytes named twice with different stamps (contradictory)
            captures_by_season[season].append(dict(capture, retrieved_at_utc=EARLY_STAMP,
                                                   team_season_id=f"ts{team}-{season}-dup"))
    ncaa = {}
    for season, caps in sorted(captures_by_season.items()):
        identity = sha(f"fixture-ncaa-{season}".encode())
        document = {"discovery_identity": identity, "season": season, "state": "COMPLETE_GRAPH_EXHAUSTED",
                    "issued_at_utc": NCAA_STAMP, "captures": caps, "failures": [],
                    "team_page_capture_count": len(caps)}
        rel = f"manifests/acquisition/fx/discovery/{season}/sha256/{identity}/ncaa_team_graph_discovery_manifest.json"
        data = jbytes(document)
        write(base / rel, data)
        ncaa[str(season)] = {"manifest": rel, "identity": identity, "sha256": sha(data), "captures": len(caps)}
    # ---- CFBD routes
    fbs_rows: dict[int, list[dict[str, Any]]] = {}
    fcs_rows: dict[int, list[dict[str, Any]]] = {}
    starts = {"ncaa:1001": "2019-08-31T23:30:00.000Z"}
    for row in in_range:
        if row["contest_status"] != "COMPLETED":
            continue
        home, away = ("b", "a") if row["site"] == "HOME_B" else ("a", "b")
        game = {"id": int(row["cfbd_game_ids"][0]), "season": row["season"], "week": 1, "seasonType": "regular",
                "startDate": starts.get(row["contest_key"], row["contest_date"] + "T19:00:00.000Z"),
                "startTimeTBD": False, "completed": True, "neutralSite": row["site"] == "NEUTRAL",
                "homeId": int(IDS[row[f"{home}_org_id"]][0]), "homeTeam": row[f"{home}_team_name"],
                "homePoints": row[f"{home}_points"], "awayId": int(IDS[row[f"{away}_org_id"]][0]),
                "awayTeam": row[f"{away}_team_name"], "awayPoints": row[f"{away}_points"]}
        for route in routes_for(row):
            (fbs_rows if route == "SRC-002" else fcs_rows).setdefault(row["season"], []).append(game)
    fbs, fcs, attempts = {}, {}, []
    for season in (2019, 2020, 2023):
        raw = json.dumps(fbs_rows.get(season, [])).encode("utf-8")
        h = sha(raw)
        raw_rel = f"raw/SRC-002/games/sha256_{h}.json"
        write(base / raw_rel, raw)
        started, done = FBS_RECEIPTS[season]
        receipt = {"response_sha256": h, "immutable_path": raw_rel, "retrieval_started_at_utc": started,
                   "retrieved_at_utc": done, "source_uri": f"https://example.invalid/games?classification=fbs&year={season}",
                   "result": "SUCCESS"}
        receipt_rel = f"manifests/acquisition/fx/requests/req_{season}.json"
        rdata = jbytes(receipt)
        write(base / receipt_rel, rdata)
        fbs[str(season)] = {"raw": raw_rel, "sha256": h, "receipt": receipt_rel, "receipt_sha256": sha(rdata)}
        raw = json.dumps(fcs_rows.get(season, [])).encode("utf-8")
        h = sha(raw)
        raw_rel = f"ops/cycle30_work/raw/games/fcs{season}.json"
        write(base / raw_rel, raw)
        fcs[str(season)] = {"raw": raw_rel, "sha256": h}
        attempts.append({"raw_sha256": h, "retrieved_at_utc": FCS_STAMP, "status": "CACHE_HIT", "route": "/games",
                         "parameters": {"classification": "fcs", "year": season}})
    ledger = jbytes({"artifact_class": "FIXTURE", "attempts": attempts})
    write(base / "ops/cycle30_work/outputs/CYCLE30_ACQUISITION_LEDGER.json", ledger)
    # ---- repository versions (2019 integer-typed, 2020 string-typed)
    by_key = {r["contest_key"]: r for r in rows}

    def repo_row(key: str, **patch: Any) -> dict[str, Any]:
        row = by_key[key]
        home, away = ("b", "a") if row["site"] == "HOME_B" else ("a", "b")
        out = {"id": int(row["cfbd_game_ids"][0]), "game_id": int(row["cfbd_game_ids"][0]), "season": row["season"],
               "start_date": row["contest_date"] + "T19:00Z", "home_id": int(IDS[row[f"{home}_org_id"]][1]),
               "away_id": int(IDS[row[f"{away}_org_id"]][1]), "home_score": row[f"{home}_points"],
               "away_score": row[f"{away}_points"], "status_type_completed": True, "status_type_name": "STATUS_FINAL",
               "neutral_site": row["site"] == "NEUTRAL", "home_location": row[f"{home}_team_name"],
               "away_location": row[f"{away}_team_name"]}
        out.update(patch)
        return out
    r2019 = [repo_row("ncaa:1001", start_date="2019-08-31T23:30Z"), repo_row("ncaa:1002", neutral_site=True),
             repo_row("ncaa:1008"),
             repo_row("ncaa:1003", home_id=102, away_id=101, home_score=21, away_score=28, neutral_site=True,
                      home_location="Bravo", away_location="Alpha"),
             repo_row("ncaa:1004"), repo_row("ncaa:1005", home_score=11),
             repo_row("ncaa:1006", start_date="2019-09-13T23:00Z"), repo_row("ncaa:1009"),
             dict(repo_row("ncaa:1003"), id=91010, game_id=91010, start_date="2019-10-12T19:00Z"),
             dict(repo_row("ncaa:1003"), id=99999, game_id=99999, status_type_completed=False,
                  status_type_name="STATUS_POSTPONED", home_score=None, away_score=None)]
    r2020 = [repo_row("ncaa:2001"), repo_row("ncaa:2002"), dict(repo_row("ncaa:2003"), home_score="3a"),
             dict(repo_row("ncaa:2001"), id=98999, game_id=98999, status_type_completed=False,
                  status_type_name="STATUS_POSTPONED", home_score=0, away_score=0)]
    versions = []
    for season, items in ((2019, r2019), (2020, r2020)):
        if season == 2020:
            items = [{k: (None if v is None else (str(v) if k in ("id", "home_id", "away_id", "home_score",
                                                                  "away_score") else (float(v) if k in (
                                                                      "game_id", "season") else v)))
                      for k, v in item.items()} for item in items]
        frame = pl.DataFrame(items)
        buffer = io.BytesIO()
        frame.write_parquet(buffer, statistics=False)
        payload = buffer.getvalue()
        payload_sha = sha(payload)
        payload_rel = f"raw/historical_known_at/github/sha256/{payload_sha}/payload.parquet"
        write(base / payload_rel, payload)
        commit_sha = hashlib.sha1(f"fixture-commit-{season}".encode()).hexdigest()
        source_path = f"cfb/schedules/parquet/cfb_schedule_{season}.parquet"
        api = {"sha": commit_sha, "commit": {"author": {"date": REPO_COMMIT[season]},
                                             "committer": {"date": REPO_COMMIT[season]}},
               "files": [{"filename": source_path, "sha": git_blob(payload), "status": "added"}]}
        api_data = jbytes(api)
        api_sha = sha(api_data)
        api_rel = f"raw/historical_known_at/github/sha256/{api_sha}/commit.json"
        write(base / api_rel, api_data)
        capture_id = sha(f"fixture-capture-{season}".encode())
        manifest = {"capture_id": capture_id, "commit_sha": commit_sha, "season": season, "source_path": source_path,
                    "acquired_at_utc": REPO_ACQUIRED[season], "payload": {"sha256": payload_sha},
                    "commit_api_capture": {"api_sha256": api_sha},
                    "source_url": f"https://example.invalid/fixture/{commit_sha}/{source_path}"}
        man_data = jbytes(manifest)
        man_rel = f"manifests/historical_known_at/captures/{capture_id}.json"
        write(base / man_rel, man_data)
        versions.append({"season": season, "capture_id": capture_id, "manifest": man_rel,
                         "manifest_sha256": sha(man_data), "repository": "fixture/cfbfastR-data",
                         "commit_sha": commit_sha, "source_path": source_path, "payload": payload_rel,
                         "payload_sha256": payload_sha, "commit_api": api_rel, "commit_api_sha256": api_sha,
                         "rows": len(items)})
    # ---- parent population: program-season stage (page observations), contest stage, query database
    contest_stage = []
    for row in rows:
        a_id, b_id = IDS[row["a_org_id"]][0], IDS[row["b_org_id"]][0]
        contest_stage.append(dict(row, a_cfbd_team_id=a_id, b_cfbd_team_id=b_id, cfbd_routes=routes_for(row)))
    canonical_root, manifest_root = base / "canonical" / "p", base / "manifests" / "p"
    m1 = pop.materialize(canonical_root=canonical_root, manifest_root=manifest_root, stage="program-season",
                         contract_sha256=PARENT_CONTRACT_SHA, inputs={"bound_manifests": ncaa}, upstream={},
                         files={"page_observations.jsonl.gz": gz_lines(observations, {"stage": "program-season"})},
                         manifest_extra={})
    m2 = pop.materialize(canonical_root=canonical_root, manifest_root=manifest_root, stage="contest",
                         contract_sha256=PARENT_CONTRACT_SHA, inputs={}, upstream={"program-season": m1["identity"]},
                         files={"contests.jsonl.gz": gz_lines(contest_stage, {"stage": "contest"})}, manifest_extra={})
    data = pop.build_query_database(contract_sha256=PARENT_CONTRACT_SHA, m1_identity=m1["identity"],
                                    m2_identity=m2["identity"], cells=[], contests=rows, orientations=[],
                                    subsets=hfx.subsets_for(rows), schedule=[])
    q = pop.materialize(canonical_root=canonical_root, manifest_root=manifest_root, stage="query-db",
                        contract_sha256=PARENT_CONTRACT_SHA, inputs={},
                        upstream={"program-season": m1["identity"], "contest": m2["identity"]},
                        files={pop.DB_FILE_NAME: data}, manifest_extra={})
    population_db = Path(q["data_dir"]) / pop.DB_FILE_NAME
    parent = {"database": population_db, "manifest": Path(q["manifest"]), "identity": q["identity"],
              "sqlite_sha256": pop.sha256_file(population_db)}
    # ---- history prefix with the accepted BAT-711 producer
    history_contract = hfx.contract_for(parent)
    history_contract["parent_binding"].update({"contest_identity": m2["identity"],
                                               "program_season_identity": m1["identity"]})
    history_contract_path = hfx.write_contract(base / "hc.json", history_contract)
    code, built, err = hfx.run_build(history_contract_path, parent, base)
    if code != 0:
        raise RuntimeError(f"history fixture build failed: {err}")
    history_db = Path(built["database"]["data_dir"]) / "national_history.sqlite"
    # ---- bindings
    delivery = write(base / "ops/cycle39/attempt01/DATA_DELIVERY_MANIFEST.json", jbytes({"fixture": True}))
    preflight = {"captures": [{"season": v["season"], "payload_sha256": v["payload_sha256"],
                               "api_sha256": v["commit_api_sha256"], "rows": v["rows"]} for v in versions]}
    preflight_path = write(base / "ops/pre.json", jbytes(preflight))
    bindings = {"history_database": {"path": str(history_db), "sha256": pop.sha256_file(history_db),
                                     "identity": built["database_identity"]},
                "population_database": {"path": str(population_db), "sha256": parent["sqlite_sha256"],
                                        "identity": parent["identity"]},
                "parent_delivery_manifest": {"path": str(delivery), "sha256": pop.sha256_file(delivery)},
                "source_preflight": {"path": str(preflight_path), "sha256": pop.sha256_file(preflight_path),
                                     "captures": len(versions), "source_rows": sum(v["rows"] for v in versions)}}
    bindings_path = write(base / "ops/ib.json", jbytes(bindings))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    pb = contract["parent_binding"]
    pb["history"].update({"contract_sha256": sha(history_contract_path.read_bytes()),
                          "content_identity": built["content_identity"], "database_identity": built["database_identity"],
                          "sqlite_sha256": pop.sha256_file(history_db),
                          "row_counts": {"targets": built["row_counts"]["targets.jsonl"],
                                         "history": built["row_counts"]["history.jsonl"],
                                         "exclusions": built["row_counts"]["exclusions.jsonl"],
                                         "out_of_scope": built["row_counts"]["out_of_scope.jsonl"]}})
    pb["population"].update({"contract_sha256": PARENT_CONTRACT_SHA, "query_db_identity": parent["identity"],
                             "sqlite_sha256": parent["sqlite_sha256"], "contest_identity": m2["identity"],
                             "program_season_identity": m1["identity"],
                             "contest_stage_files": {"contests.jsonl.gz": pop.sha256_file(
                                 Path(m2["data_dir"]) / "contests.jsonl.gz")},
                             "program_season_stage_files": {"page_observations.jsonl.gz": pop.sha256_file(
                                 Path(m1["data_dir"]) / "page_observations.jsonl.gz")},
                             "parent_contest_rows": len(rows)})
    pb["delivery_manifest"] = {"path": "ops/cycle39/attempt01/DATA_DELIVERY_MANIFEST.json",
                               "sha256": pop.sha256_file(delivery)}
    pb["source_bindings"].update({"cache_preflight_sha256": pop.sha256_file(preflight_path),
                                  "captures": len(versions), "source_rows": sum(v["rows"] for v in versions)})
    su = contract["source_universe"]
    su.update({"repository_versions": versions, "cfbd_fbs_route": fbs, "cfbd_fcs_route": fcs,
               "cycle30_ledger": {"path": "ops/cycle30_work/outputs/CYCLE30_ACQUISITION_LEDGER.json",
                                  "sha256": sha(ledger)},
               "ncaa_bound_manifests": ncaa})
    contract["scope"]["repository_version_seasons"] = [2019, 2020]
    contract_path = write(base / "stc.json", (json.dumps(contract, indent=2) + "\n").encode("utf-8"))
    return {"base": base, "contract": contract_path, "contract_doc": contract, "history_db": history_db,
            "population_db": population_db, "bindings": bindings_path, "history_built": built,
            "versions": versions, "rows": rows}


def patched_contract(world: dict[str, Any], path: Path, mutate) -> Path:
    contract = copy.deepcopy(world["contract_doc"])
    mutate(contract)
    return write(Path(path), (json.dumps(contract, indent=2) + "\n").encode("utf-8"))


def run_build(world: dict[str, Any], out: Path, *extra: str, contract: Path | None = None,
              history_db: Path | None = None, population_db: Path | None = None,
              bindings: Path | None = None) -> tuple[int, dict[str, Any] | None, str]:
    argv = ["--contract", str(contract or world["contract"]), "--history-database", str(history_db or world["history_db"]),
            "--population-database", str(population_db or world["population_db"]),
            "--source-bindings", str(bindings or world["bindings"]),
            "--output-root", str(Path(out) / "canonical" / "st"), "--manifest-root",
            str(Path(out) / "manifests" / "st"), *extra]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = builder().main(argv)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


def refusal(stderr: str) -> str | None:
    return hfx.refusal(stderr)


def read_payload(result: dict[str, Any], name: str) -> list[dict[str, Any]]:
    data = gzip.decompress((Path(result["content"]["data_dir"]) / f"{name}.gz").read_bytes())
    return [json.loads(line) for line in data.decode("utf-8").splitlines()]


def database_path(result: dict[str, Any]) -> Path:
    return Path(result["database"]["data_dir"]) / "national_source_time.sqlite"
