"""Tiny owned worlds and coordinated forgeries for the BAT-729 national 2023 game-context tests (Cycle #58 TP58-A01).

Not a test module (no ``test`` prefix). Every world is real: the parent population, history prefix, C47 benchmark and
C56 reference are built by the accepted builders (``retrospective_reference_fixture``), then the retained raw provider
inputs (2023 games, team locations, venues), the C38-shaped identity bindings and the acquisition receipts are written
for that world's 2023 targets, and the context is built by the repository builder under the committed context contract
whose inputs, source clocks and expected keys name the fixture's files. The world plants every qualification class:
a cold start, a same-date latest-prior tie, a neutral site, a provider/parent site disagreement, a start claim outside
the parent date window, a documented game absent from the capture, an unusable team origin and a home game played away
from the home team's reference location. Forged releases are coordinated: database bytes, table counts, identity
documents, identity directories and manifests are rewritten consistently, so each must be refused by its own semantic
rule, never by a stale outer hash.
"""
from __future__ import annotations

import contextlib
import copy
import gzip
import hashlib
import io
import json
import os
import shutil
import sqlite3
import sys
import zlib
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import national_history_fixture as hx  # noqa: E402
import retrospective_reference_fixture as rfx  # noqa: E402
from aggie_analytics.game_context import context as gc  # noqa: E402

CONTRACT_PATH = ROOT / "configs" / "national_game_context_2023_contract.json"
BUILDER_PATH = ROOT / "tools" / "build_national_game_context.py"
POP = gc.POPULATION
#: org id -> provider (CFBD) team id: deliberately never the numeric org id.
CFBD = {"1": "2001", "2": "2002", "3": "2003", "5": "2005", "697": "2697", "8": "2008", "4": "2004", "6": "2006"}
#: org id -> later-observed reference location (venue id, latitude, longitude); Hotel's coordinate is unusable.
LOCATIONS = {"1": (101, 30.0, -97.0), "2": (102, 33.0, -84.0), "3": (103, 40.0, -105.0), "5": (105, 47.6, -122.3),
             "697": (697, 30.6101, -96.3403), "8": (108, None, -80.0), "4": (104, 35.0, -90.0), "6": (106, 41.0, -74.0)}
NEUTRAL_VENUE = (900, 51.4775, -0.0)


def builder() -> Any:
    return hx.load_tool(BUILDER_PATH, "bas_game_context_builder")


def world_contests() -> list[dict[str, Any]]:
    """The accepted C56 fixture world with two 2023 changes: Echo (org 5) loses its 2023 week-0 game (a cold start at
    its first target) and Alpha (org 1) plays a second week-0 game on the same date (a latest-prior tie)."""
    rows = rfx.world_contests()
    week0 = [r for r in rows if r["season"] == 2023 and r["contest_date"] < "2023-09-01" and
             r["a_key"] == "org:5"]
    rows = [r for r in rows if r not in week0]
    first_alpha = next(r for r in rows if r["season"] == 2023 and r["contest_date"] < "2023-09-01" and
                       r["a_key"] == "org:1")
    rows.append(rfx.contest("ncaa:9001", 2023, first_alpha["contest_date"], "1", "6", 31, 7))
    return rows


def _rel(path: Path, root: Path) -> str:
    return Path(os.path.relpath(path, root)).as_posix()


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1) + "\n", encoding="utf-8", newline="\n")
    return path


def build_world(base: Path) -> dict[str, Any]:
    """The accepted builders' world plus the retained-input stand-ins under one data root (``base``)."""
    base = Path(base)
    world = rfx.build_world(base, world_contests())
    ref_contract = rfx.write_contract(base / "rc.json", rfx.contract_for(world))
    code, ref, stderr = rfx.run_build(ref_contract, world, base)
    if code != 0:
        raise AssertionError(f"accepted reference builder refused the fixture: {stderr}")
    world.update(reference_contract=ref_contract, reference_db=rfx.database_of(ref), reference=ref)
    conn = sqlite3.connect(Path(world["history_db"]).as_uri() + "?mode=ro", uri=True)
    targets = [json.loads(r[0]) for r in conn.execute("SELECT record FROM targets WHERE season = 2023 ORDER BY ord")]
    history_meta = dict(conn.execute("SELECT key, value FROM meta"))
    conn.close()
    world["targets"] = targets
    world["history_meta"] = history_meta
    raw = base / "raw"
    # ---- C38-shaped identity bindings (one SCHEDULE_FINGERPRINT_ONLY rule; FCS orgs bound too)
    lines = [json.dumps({"_header": {"contract_sha256": world["parent"]["contract_sha256"],
                                     "schema": "BAS-NATIONAL-DI-POPULATION-1", "stage": "program-season"}})]
    for org, cfbd in sorted(CFBD.items()):
        lines.append(json.dumps({"org_id": org, "cfbd_team_id": cfbd, "n_games": 9, "name_candidates": [cfbd],
                                 "rule": "SCHEDULE_FINGERPRINT_ONLY" if org == "3" else "NAME_CONFIRMED_BY_SCHEDULE",
                                 "reason": None, "best_fingerprint": [cfbd, 9], "candidate_fingerprints": {cfbd: 9},
                                 "runner_up_fingerprint": 0}))
    bindings = raw / "bindings" / "identity_bindings.jsonl.gz"
    bindings.parent.mkdir(parents=True, exist_ok=True)
    bindings.write_bytes(gzip.compress(("\n".join(lines) + "\n").encode("utf-8"), mtime=0))
    # ---- provider games: one per 2023 target with the planted classes
    games, venues = [], [{"id": v[0], "name": f"Venue {v[0]}", "latitude": v[1], "longitude": v[2]}
                         for v in sorted(set(LOCATIONS.values())) if v[1] is not None]
    venues.append({"id": 108, "name": "Venue 108", "latitude": 26.0, "longitude": -80.0})
    venues.append({"id": NEUTRAL_VENUE[0], "name": "Fixture Bowl Stadium", "latitude": NEUTRAL_VENUE[1],
                   "longitude": NEUTRAL_VENUE[2]})
    venues.append({"id": 950, "name": "Off Campus Dome", "latitude": 29.4, "longitude": -98.5})
    plan = {}
    nonneutral = [t for t in targets if t["parent_site"] != "NEUTRAL" and "8" not in (t["a_org_id"], t["b_org_id"])]
    plan[nonneutral[1]["contest_key"]] = "SITE_DISAGREE"
    plan[nonneutral[2]["contest_key"]] = "START_OUTSIDE_WINDOW"
    plan[nonneutral[3]["contest_key"]] = "ABSENT"
    plan[nonneutral[4]["contest_key"]] = "OFF_CAMPUS_HOME"
    world["plan"] = plan
    for t in targets:
        kind = plan.get(t["contest_key"])
        if kind == "ABSENT":
            continue
        a, b = t["a_org_id"], t["b_org_id"]
        home, away = (b, a) if t["parent_site"] == "HOME_B" else (a, b)
        neutral = t["parent_site"] == "NEUTRAL"
        venue = NEUTRAL_VENUE[0] if neutral else 950 if kind == "OFF_CAMPUS_HOME" else LOCATIONS[home][0]
        start = t["contest_date"] + ("T23:30:00.000Z" if kind != "START_OUTSIDE_WINDOW" else "T00:00:00.000Z")
        if kind == "START_OUTSIDE_WINDOW":
            start = "2023-01-01T00:00:00.000Z"
        games.append({"id": int(t["cfbd_game_ids"][0]), "season": 2023, "week": 1, "seasonType": "regular",
                      "startDate": start, "startTimeTBD": False,
                      "neutralSite": True if kind == "SITE_DISAGREE" else neutral, "conferenceGame": False,
                      "attendance": 1000, "venueId": venue, "venue": f"Venue {venue}" if venue != NEUTRAL_VENUE[0]
                      else "Fixture Bowl Stadium", "homeId": int(CFBD[home]), "homeTeam": home,
                      "homeClassification": "fbs", "awayId": int(CFBD[away]), "awayTeam": away,
                      "awayClassification": "fbs", "homePoints": 1, "awayPoints": 0, "notes": None})
    games.append({"id": 99999, "season": 2023, "week": 9, "seasonType": "regular", "startDate": "2023-11-01T18:00:00Z",
                  "startTimeTBD": True, "neutralSite": False, "venueId": 101, "venue": "Venue 101", "homeId": 2001,
                  "awayId": 2004, "notes": "a provider row no accepted target documents"})
    teams = [{"id": int(CFBD[org]), "school": rfx.TEAMS.get(org, (org,))[0], "classification": "fbs",
              "location": {"id": LOCATIONS[org][0], "name": f"Home {org}", "latitude": LOCATIONS[org][1],
                           "longitude": LOCATIONS[org][2], "timezone": "America/Chicago"}}
             for org in sorted(CFBD)]
    games_path = _write_json(raw / "games" / "games_2023.json", games)
    teams_path = _write_json(raw / "teams" / "teams_2023.json", teams)
    venues_path = _write_json(raw / "venues" / "venues.json", venues)
    # ---- receipts
    capture = _write_json(raw / "receipts" / "capture.json", {
        "capture_id": "cap_fixture", "request_id": "req_fixture",
        "source_uri": "https://api.collegefootballdata.com/games?classification=fbs&year=2023",
        "parameters": {"classification": "fbs", "year": "2023"}, "http_status": 200, "result": "SUCCESS",
        "response_sha256": _sha(games_path), "row_count": len(games), "retrieved_at_utc": "2026-08-09T16:57:56Z",
        "immutable_path": _rel(games_path, base)})
    ledger = _write_json(raw / "receipts" / "ledger.json", {"attempts": [
        {"route": "/venues", "parameters": {}, "raw_sha256": _sha(venues_path), "retrieved_at_utc": "2026-09-09T18:08:43Z",
         "status": "CACHE_HIT", "http_status": 200, "row_count": len(venues)},
        {"route": "/teams", "parameters": {"classification": "fbs", "year": 2023}, "raw_sha256": _sha(teams_path),
         "retrieved_at_utc": "2026-09-09T18:08:44Z", "status": "CACHE_HIT", "http_status": 200,
         "row_count": len(teams)},
        {"route": "/teams", "parameters": {"classification": "fcs", "year": 2023}, "raw_sha256": _sha(teams_path),
         "retrieved_at_utc": "2026-09-09T18:08:44Z", "status": "CACHE_HIT", "http_status": 200,
         "row_count": len(teams)}]})
    world.update(data_root=base, bindings=bindings, games=games_path, teams=teams_path, venues=venues_path,
                 capture=capture, ledger=ledger)
    return world


def anchors_for(world: dict[str, Any]) -> dict[str, Any]:
    """The fixture's anchors: every input's relative locator and SHA-256, its clocks and expected keys (the committed
    contract's rules are unchanged)."""
    base = world["data_root"]
    a = copy.deepcopy(gc.ANCHORS)
    hm = world["history_meta"]
    ref_db = Path(world["reference_db"])
    conn = sqlite3.connect(ref_db.as_uri() + "?mode=ro", uri=True)
    rmeta = dict(conn.execute("SELECT key, value FROM meta"))
    conn.close()
    a["inputs"] = {
        "history": {"relative_path": _rel(world["history_db"], base), "sha256": _sha(world["history_db"]),
                    "database_identity": Path(world["history_db"]).parent.name,
                    "content_identity": hm["content_identity"], "contract_sha256": hm["contract_sha256"]},
        "population": {"relative_path": _rel(world["parent"]["database"], base),
                       "sha256": world["parent"]["sqlite_sha256"], "database_identity": world["parent"]["identity"],
                       "contract_sha256": world["parent"]["contract_sha256"]},
        "identity_bindings": {"relative_path": _rel(world["bindings"], base), "sha256": _sha(world["bindings"]),
                              "header_contract_sha256": world["parent"]["contract_sha256"]},
        "provider_games": {"relative_path": _rel(world["games"], base), "sha256": _sha(world["games"])},
        "provider_teams": {"relative_path": _rel(world["teams"], base), "sha256": _sha(world["teams"])},
        "venue_reference": {"relative_path": _rel(world["venues"], base), "sha256": _sha(world["venues"])},
        "reference": {"relative_path": _rel(ref_db, base), "sha256": _sha(ref_db), "database_identity": ref_db.parent.name,
                      "content_identity": rmeta["content_identity"], "contract_sha256": rmeta["contract_sha256"]},
    }
    clocks = a["source_clocks"]
    clocks["provider_games"].update(receipt_relative_path=_rel(world["capture"], base), receipt_sha256=_sha(world["capture"]),
                                    capture_id="cap_fixture", request_id="req_fixture",
                                    response_sha256=_sha(world["games"]),
                                    row_count=len(json.loads(Path(world["games"]).read_text(encoding="utf-8"))))
    for name, attempts in (("provider_teams", [1, 2]), ("venue_reference", [0])):
        path = world["teams"] if name == "provider_teams" else world["venues"]
        clocks[name].update(receipt_relative_path=_rel(world["ledger"], base), receipt_sha256=_sha(world["ledger"]),
                            ledger_attempts=attempts, response_sha256=_sha(path),
                            row_count=len(json.loads(Path(path).read_text(encoding="utf-8"))))
    keys = [t["contest_key"] for t in world["targets"]]
    a["expected"] = {"contests": len(keys), "team_views": 2 * len(keys), "witnesses": 15 * len(keys) + 3,
                     "strata_rows": 70, "target_keys_sha256": gc.target_keys_sha256(keys)}
    return a


def contract_for(world: dict[str, Any], anchors: dict[str, Any] | None = None, **patch: Any) -> dict[str, Any]:
    """The committed context contract with only its inputs, clocks and expected keys replaced by the fixture's."""
    a = anchors or anchors_for(world)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract["inputs"] = a["inputs"]
    contract["source_clocks"] = a["source_clocks"]
    contract["expected"] = {**a["expected"], "target_keys": [t["contest_key"] for t in world["targets"]],
                            "key_source": contract["expected"]["key_source"]}
    for dotted, value in patch.items():
        node = contract
        parts = dotted.split("__")
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = value
    return contract


def write_contract(path: Path, contract: dict[str, Any]) -> Path:
    Path(path).write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return Path(path)


def contract_anchors(path: Path) -> dict[str, Any]:
    return builder().load_contract(path)[2]


def run_build(contract_path: Path, world: dict[str, Any], out: Path, *extra: str
              ) -> tuple[int, dict[str, Any] | None, str]:
    argv = ["--contract", str(contract_path), "--data-root", str(world["data_root"]),
            "--output-root", str(Path(out) / "canonical" / POP), "--manifest-root", str(Path(out) / "manifests" / POP),
            *extra]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = builder().main(argv)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


def refusal(stderr: str) -> str | None:
    return hx.refusal(stderr)


def database_of(result: dict[str, Any]) -> Path:
    return Path(result["database"]["data_dir"]) / gc.DB_FILE


def query(world: dict[str, Any], anchors: dict[str, Any], database: Path, *argv: str, front: Callable | None = None,
          data_root: Path | None = None) -> tuple[int, Any, str]:
    """The query's main() in process with fixture anchors; returns (exit, parsed stdout or None, stderr)."""
    from aggie_analytics.game_context import query as q  # noqa: PLC0415
    tokens = ["--database", str(database), "--data-root", str(data_root or world["data_root"]), *argv]
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
    """Coordinated forgeries of one context database in owned scratch."""

    def __init__(self, database: Path, root: Path) -> None:
        self.database = Path(database)
        self.root = Path(root)
        identity = self.database.parent.name
        population_root = self.database.parent.parent.parent
        self.manifest = json.loads((population_root.parent.parent / "manifests" / population_root.name / "sha256" /
                                    identity / "run_manifest.json").read_text(encoding="utf-8"))

    def tables(self) -> dict[str, list[dict[str, Any]]]:
        conn = sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True)
        out: dict[str, list[dict[str, Any]]] = {t: [] for t, _s in gc.BLOCK_LAYOUT}
        for table, blob in conn.execute("SELECT record_table, block FROM blocks ORDER BY ord"):
            out[table] += [json.loads(line) for line in zlib.decompress(blob).decode("utf-8").splitlines()]
        conn.close()
        return out

    def forge(self, name: str, *, records: Callable[[dict[str, list[dict[str, Any]]]], None] | None = None,
              lines: Callable[[dict[str, list[str]]], None] | None = None, meta: dict[str, Any] | None = None,
              document: dict[str, Any] | Callable[[dict[str, Any]], None] | None = None,
              after_blocks: list[tuple[str, tuple]] | None = None, identity_override: str | None = None,
              manifest_patch: dict[str, Any] | None = None) -> Path:
        """Copy, mutate and rehash. ``records`` edits the decoded record lists in place (blocks are rebuilt from
        canonical lines with consistent index columns); ``lines`` edits raw lines; ``meta`` replaces meta values;
        ``document`` patches the identity document; ``after_blocks`` runs after the rebuild."""
        work = self.root / name / "work.sqlite"
        work.parent.mkdir(parents=True)
        shutil.copyfile(self.database, work)
        conn = sqlite3.connect(work)
        conn.execute("PRAGMA journal_mode = OFF")
        if records is not None or lines is not None:
            tables = self.tables()
            if records is not None:
                records(tables)
            raw = {t: [gc.canonical_line(r) for r in rows] for t, rows in tables.items()}
            if lines is not None:
                lines(raw)
            conn.execute("DELETE FROM blocks")
            for ord_, (table, segment) in enumerate(gc.BLOCK_LAYOUT):
                chosen = raw[table]
                parsed = []
                for line in chosen:
                    try:
                        value = json.loads(line)
                    except ValueError:
                        value = {}
                    parsed.append(value if isinstance(value, dict) else {})
                data = "".join(l + "\n" for l in chosen).encode("utf-8")
                conn.execute("INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (ord_, table, segment, len(chosen),
                              gc.record_key(table, parsed[0]) if parsed else None,
                              gc.record_key(table, parsed[-1]) if parsed else None,
                              gc.sha256_bytes(data), zlib.compress(data, 9)))
        for key, value in (meta or {}).items():
            text = value if isinstance(value, str) else gc.canonical_line(value)
            if conn.execute("UPDATE meta SET value = ? WHERE key = ?", (text, key)).rowcount != 1:
                raise AssertionError(f"meta forgery {key} changed nothing")
        for sql, params in after_blocks or []:
            if conn.execute(sql, params).rowcount < 1:
                raise AssertionError(f"block forgery changed nothing: {sql}")
        conn.commit()
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in gc.TABLES}
        conn.close()
        doc = copy.deepcopy(self.manifest["identity_document"])
        doc["outputs"] = {gc.DB_FILE: gc.sha256_file(work)}
        doc["table_counts"] = counts
        if callable(document):
            document(doc)
        else:
            doc.update(document or {})
        identity = identity_override or gc.sha256_bytes(gc.canonical_json_bytes(doc))
        target = self.root / name / "canonical" / POP / "sha256" / identity / gc.DB_FILE
        target.parent.mkdir(parents=True)
        shutil.move(str(work), str(target))
        man = self.root / name / "manifests" / POP / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        body = {"identity": identity, "identity_document": doc, "provenance": {"forgery": name}}
        body.update(manifest_patch or {})
        man.write_text(json.dumps(body), encoding="utf-8")
        return target
