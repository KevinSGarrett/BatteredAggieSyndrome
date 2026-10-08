"""BAT-718 (Cycle #46 — Attempt #1, TP46-A01): the explicit cached-source reconciliation sidecar on tiny owned fixtures.

Every fixture is real: a parent query database built and materialized by the accepted parent builder, a gzip crosswalk
with the parent's program-season header, a canonical registry CSV, two provider captures with their receipts and the
committed contract with only its parent and input bindings replaced. The producer is the repository builder and the
consumer is the installed query module (``main`` and its verified handle); forgeries are coordinated -- the sidecar
bytes, table counts, identity document, identity directory and manifest are all rewritten consistently -- so each one
must be refused by its own semantic rule, never by a stale outer hash.

Two tests use only accepted behaviour and pass on the unfixed base (BEFORE_REPRODUCTION): the default grains keep
their exact key sets, and the long-location helper clears 300 characters from every local root length.
"""
from __future__ import annotations

import contextlib
import copy
import gzip
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data import national_di_population as pop  # noqa: E402
from aggie_analytics.national_population import query  # noqa: E402

WINDOWS = os.name == "nt"
EXT = "\\\\?\\"
PARENT_CONTRACT_SHA = "3b27a454269127806b4930466dcb7c11de089a9479ccc41b7b2500dc606dc903"
M1, M2 = "1" * 64, "2" * 64
POPULATION = "national_population_reconciliation_2024_2025"
DB_NAME = "national_population_reconciliation.sqlite"
CONTRACT = ROOT / "configs" / "national_population_reconciliation_2024_2025_contract.json"
BUILDER = ROOT / "tools" / "build_national_population_reconciliation.py"

#: org -> (name, {season: division label}, provider team id, provider display name, {season: provider class}, rule)
TEAMS = {
    "100": ("Alpha St.", {2024: "FBS", 2025: "FBS"}, "9001", "Alpha State", {2024: "fbs", 2025: "fbs"},
            "NAME_CONFIRMED_BY_SCHEDULE"),
    "200": ("Beta", {2024: "FBS", 2025: "FBS"}, "9002", "Beta", {2024: "fbs", 2025: "fbs"}, "NAME_CONFIRMED_BY_SCHEDULE"),
    "415": ("Miami (FL)", {2024: "FBS", 2025: "FBS"}, "9003", "Miami", {2024: "fbs", 2025: "fbs"},
            "NAME_CONFIRMED_BY_SCHEDULE"),
    "657": ("Southern California", {2024: "FBS", 2025: "FBS"}, "9004", "USC", {2024: "fbs", 2025: "fbs"},
            "SCHEDULE_FINGERPRINT_ONLY"),
    "300": ("Gamma", {2024: "FCS", 2025: "FCS"}, "9005", "Gamma", {2024: "fcs", 2025: "fcs"}, "NAME_CONFIRMED_BY_SCHEDULE"),
    "400": ("Delta", {2024: "FCS", 2025: "FCS"}, "9006", "Delta", {2024: "fcs", 2025: "fcs"}, "NAME_CONFIRMED_BY_SCHEDULE"),
    "30": ("Epsilon", {2024: "FBS", 2025: "FBS"}, "9007", "Epsilon", {2024: "fbs", 2025: "fbs"}, "NAME_CONFIRMED_BY_SCHEDULE"),
    "700": ("Phi", {2024: "FCS", 2025: "FCS"}, "9008", "Phi", {2024: "fcs", 2025: "fcs"}, "NAME_CONFIRMED_BY_SCHEDULE"),
    "500": ("Theta", {2024: "FCS", 2025: "FBS"}, "9009", "Theta", {2024: "fbs", 2025: "fbs"}, "NAME_CONFIRMED_BY_SCHEDULE"),
    "600": ("Xi", {2024: "DII", 2025: "DII"}, None, None, {}, None),
}
EXTERNAL = (None, "Ex School")


def long_root(base: str) -> str:
    """A directory whose sidecar file lies beyond 300 characters from any local root (bare drive to hosted temp)."""
    return os.path.join(base, "long " + "x" * 120, "deeper # % é ' " + "y" * 120, "tail " + "z" * 40)


def native(path: str | Path) -> str:
    text = os.path.abspath(str(path)) if not str(path).startswith(EXT) else str(path)
    return EXT + text if WINDOWS and not text.startswith(EXT) else text


def contest(key, season, date, a, b, site="HOME_A", a_pts=21, b_pts=14, status="COMPLETED"):
    def side(org):
        if org is None:
            return {"org_id": None, "team_season_id": None, "team_name": EXTERNAL[1], "division_label": "NON_NCAA",
                    "membership": "NON_NCAA", "key": "ext:ex school"}
        label = TEAMS[org][1].get(season, TEAMS[org][1][2024])
        return {"org_id": org, "team_season_id": f"ts{org}{season}", "team_name": TEAMS[org][0], "division_label": label,
                "membership": "DIVISION_I" if label in ("FBS", "FCS") else "OUTSIDE_DIVISION_I", "key": f"org:{org}"}
    sa, sb = side(a), side(b)
    row = {"contest_key": key, "ncaa_contest_id": key.split(":", 1)[1] if key.startswith("ncaa:") else None,
           "season": season, "term": "FALL", "contest_date": date, "contest_dates_observed": [date], "site": site,
           "neutral_site_text": "Somewhere, ST" if site == "NEUTRAL" else None, "contest_status": status,
           "competitive": status == "COMPLETED", "classification_pair": "-".join(sorted((sa["division_label"],
                                                                                         sb["division_label"]))),
           "mirror_observation_count": 2, "source": "NCAA_GRAPH", "cfbd_game_ids": [],
           "reconciliation_state": "SINGLE_SOURCE_UNRECONCILED" if season >= 2024 else "RECONCILED_2016_2023",
           "disposition": "CANDIDATE_ONLY", "disposition_reason": "SINGLE_SOURCE_UNRECONCILED",
           "exposure": "EXPOSED_NOT_PROTECTED", "conflict_fields": [], "flags": [], "event_labels": [],
           "a_points": a_pts if status == "COMPLETED" else None, "b_points": b_pts if status == "COMPLETED" else None}
    for prefix, s in (("a", sa), ("b", sb)):
        for field in ("org_id", "team_season_id", "team_name", "division_label", "membership", "key"):
            row[f"{prefix}_{field}"] = s[field]
    return row


PARENTS = [
    contest("ncaa:900", 2023, "2023-09-02", "100", "200"),
    contest("ncaa:1001", 2024, "2024-08-31", "100", "200", "HOME_A", 21, 14),
    contest("ncaa:1002", 2024, "2024-09-07", "415", "200", "HOME_A", 30, 20),
    contest("ncaa:1003", 2024, "2024-09-13", "100", "415", "HOME_A", 17, 10),
    contest("ncaa:1004", 2024, "2024-09-21", "200", "100", "HOME_A", 28, 24),
    contest("ncaa:1005", 2024, "2024-10-05", "100", "200", "HOME_A", 10, 20),
    contest("ncaa:1006", 2024, "2024-10-12", "415", "100", "NEUTRAL", 31, 28),
    contest("nolink:2024:2024-10-19:org:100|org:200", 2024, "2024-10-19", "100", "200", "HOME_A", status="CANCELED"),
    contest("ncaa:1008", 2024, "2024-10-26", "200", "415", "HOME_A", 14, 13),
    contest("ncaa:1009", 2024, "2025-01-02", "100", "415", "NEUTRAL", 35, 34),
    contest("ncaa:1010", 2024, "2024-11-02", "657", "100", "HOME_A", 24, 21),
    contest("ncaa:1011", 2024, "2024-11-09", "300", "400", "HOME_A", 7, 3),
    contest("ncaa:1012", 2024, "2024-11-16", "100", "600", "HOME_A", 56, 0),
    contest("ncaa:1013", 2024, "2024-11-23", "200", "500", "HOME_A", 40, 10),
    contest("ncaa:1014", 2024, "2024-11-30", "415", "30", "HOME_A", 20, 17),
    contest("ncaa:1015", 2024, "2024-09-28", "30", "200", "HOME_A", 3, 0),
    contest("ncaa:1016", 2024, "2024-09-29", "30", "200", "HOME_A", 6, 0),
    contest("ncaa:1017", 2024, "2024-12-07", "415", "200", "HOME_A", 9, 7),
    contest("ncaa:1018", 2024, "2024-12-14", "100", "415", "HOME_A", 7, 3),
    contest("ncaa:1019", 2024, "2024-09-21", "300", None, "HOME_A", 52, 0),
    contest("ncaa:1020", 2024, "2024-09-14", "500", "100", "HOME_B", 13, 45),
    contest("ncaa:2001", 2025, "2025-08-30", "100", "200", "HOME_A", 27, 24),
    contest("ncaa:2002", 2025, "2025-09-06", "300", "700", "HOME_A", 14, 10),
    contest("ncaa:2003", 2025, "2025-09-13", "500", "200", "HOME_A", 21, 20),
]


def game(gid, season, start, home, away, home_pts, away_pts, *, neutral=False, completed=True, season_type="regular",
         tbd=False, season_field=None, home_class=None, away_class=None):
    def team(org):  # "zeta": provider team 30, a different team from NCAA organization 30 (never equated)
        return TEAMS[org][2] if org in TEAMS else "30"
    def name(org):
        return TEAMS[org][3] if org in TEAMS else "Zeta Provider"
    def cls(org):
        return TEAMS[org][4][season] if org in TEAMS else "fbs"
    return {"id": gid, "season": season if season_field is None else season_field, "week": 1, "seasonType": season_type,
            "startDate": start, "startTimeTBD": tbd, "completed": completed, "neutralSite": neutral,
            "conferenceGame": False, "attendance": 1234, "venueId": 1, "venue": "A Stadium",
            "homeId": int(team(home)), "homeTeam": name(home), "homeClassification": home_class or cls(home),
            "homeConference": "X", "homePoints": home_pts, "homeLineScores": [0, 0, 0, home_pts or 0],
            "homePostgameWinProbability": 0.75, "homePregameElo": 1500.5, "homePostgameElo": 1510,
            "awayId": int(team(away)), "awayTeam": name(away), "awayClassification": away_class or cls(away),
            "awayConference": "Y", "awayPoints": away_pts, "awayLineScores": [0, 0, 0, away_pts or 0],
            "awayPostgameWinProbability": 0.25, "awayPregameElo": 1490, "awayPostgameElo": 1480,
            "excitementIndex": 1.5, "highlights": "", "notes": None, "playoff": None}


PROVIDER = {
    2024: [
        game(1, 2024, "2024-08-31T23:30:00.000Z", "100", "200", 21, 14),
        game(2, 2024, "2024-09-07T16:00:00.000Z", "415", "200", 30, 20),
        game(3, 2024, "2024-09-14T01:30:00.000Z", "100", "415", 17, 10),          # UTC rollover: local 2024-09-13
        game(4, 2024, "2024-09-21T19:00:00.000Z", "200", "100", 28, 27),          # score conflict
        game(5, 2024, "2024-10-05T19:00:00.000Z", "200", "100", 20, 10),          # provider home is parent b
        game(6, 2024, "2024-10-12T19:00:00.000Z", "100", "415", 28, 31, neutral=True),
        game(7, 2024, "2024-10-19T19:00:00.000Z", "100", "200", None, None, completed=False),
        game(8, 2024, "2024-10-26T19:00:00.000Z", "200", "415", 14, 13, neutral=True),   # relocated home
        game(9, 2024, "2025-01-02T20:00:00.000Z", "100", "415", 35, 34, neutral=True, season_type="postseason"),
        game(10, 2024, "2024-11-02T19:00:00.000Z", "657", "100", 24, 21),        # unsupported alias
        game(11, 2024, "2024-12-03T00:00:00.000Z", "415", "30", 20, 17),          # local 2024-12-02, parent 11-30
        game(12, 2024, "2024-09-29T04:30:00.000Z", "30", "200", 3, 0),            # local 09-28 and 09-29: ambiguous
        game(13, 2024, "2024-12-07T19:00:00.000Z", "415", "200", 9, 7),
        game(13, 2024, "2024-12-07T19:00:00.000Z", "415", "200", 9, 7),           # duplicated provider game id
        game(15, 2024, "2024-12-14T19:00:00.000Z", "100", "415", True, 3),        # boolean score
        game(16, 2024, "2024-09-14T19:00:00.000Z", "100", "500", 45, 13),         # transition class conflict
        game(17, 2024, "2024-12-21T19:00:00.000Z", "100", "zeta", 50, 0),         # provider team 30 never bound
        game(18, 2024, "2024-12-28T19:00:00.000Z", "100", "400", 63, 7),          # no parent contest
        game(19, 2024, "2024-12-20T19:00:00.000Z", "100", "200", 1, 0, season_field=2023),
        game(20, 2024, "2024-12-01 12:00", "100", "200", 2, 0),                   # not a UTC instant
    ],
    2025: [
        game(101, 2025, "2025-08-30T23:00:00.000Z", "100", "200", 27, 24),
        game(102, 2025, "2025-09-13T19:00:00.000Z", "500", "200", 21, 20),
        game(103, 2025, "2025-10-04T19:00:00.000Z", "200", "400", 31, 3),
    ],
}


def write_gzip_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows).encode("utf-8")
    with path.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
        gz.write(payload)


def registry_rows() -> list[dict]:
    rows = []
    for org, (_n, _l, pid, pname, _c, _r) in sorted(TEAMS.items()):
        if pid is None:
            continue
        canonical = f"team_{pid}"
        rows.append({"record_type": "ENTITY", "entity_type": "team", "record_id": f"ent_{pid}", "canonical_id": canonical,
                     "identity_key": f"TEAM|SRC-002|{pid}", "resolution_state": "AUTO_ACCEPTED_VERIFIED"})
        rows.append({"record_type": "ALIAS", "entity_type": "team", "record_id": f"obs_{pid}_name", "canonical_id": canonical,
                     "resolution_state": "AUTO_ACCEPTED_VERIFIED", "alias": pname, "effective_from": "2021-01-01",
                     "effective_to_exclusive": "2026-01-01", "source_system_id": "SRC-002"})
    rows += [
        {"record_type": "ALIAS", "entity_type": "team", "record_id": "obs_miami_ncaa", "canonical_id": "team_9003",
         "resolution_state": "AUTO_ACCEPTED_VERIFIED", "alias": "Miami (FL)", "effective_from": "2021-01-01",
         "effective_to_exclusive": "2026-01-01", "source_system_id": "SRC-001"},
        {"record_type": "ALIAS", "entity_type": "team", "record_id": "obs_usc_old", "canonical_id": "team_9004",
         "resolution_state": "AUTO_ACCEPTED_VERIFIED", "alias": "Southern California", "effective_from": "1990-01-01",
         "effective_to_exclusive": "2000-01-01", "source_system_id": "SRC-001"},
        {"record_type": "ALIAS", "entity_type": "team", "record_id": "obs_usc_review", "canonical_id": "team_9004",
         "resolution_state": "REVIEW_REQUIRED", "alias": "Southern California", "effective_from": "2021-01-01",
         "effective_to_exclusive": "2026-01-01", "source_system_id": "SRC-001"},
        {"record_type": "ALIAS", "entity_type": "conference", "record_id": "obs_conf", "canonical_id": "conf_1",
         "resolution_state": "AUTO_ACCEPTED_VERIFIED", "alias": "Alpha St.", "effective_from": "2021-01-01",
         "effective_to_exclusive": "2026-01-01", "source_system_id": "SRC-002"},
    ]
    return rows


REGISTRY_COLUMNS = ["schema_version", "record_type", "entity_type", "record_id", "canonical_id", "identity_key",
                    "resolution_state", "alias", "effective_from", "effective_to_exclusive", "source_system_id"]


def write_registry(path: Path) -> None:
    import csv  # noqa: PLC0415
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTRY_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in registry_rows():
            writer.writerow({"schema_version": "1.0.0", **row})


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_inputs(base: Path, parents: list[dict] | None = None) -> dict:
    """Materialize the fixture parent and every cached input under ``base``; return the contract bindings."""
    rows = parents if parents is not None else PARENTS
    cells = []
    for org, (name, labels, _p, _n, _c, _r) in sorted(TEAMS.items()):
        for season, label in labels.items():
            cells.append({"cell_key": f"org:{org}:{season}", "season": season, "ncaa_org_id": org, "team_name": name,
                          "ncaa_team_season_id": f"ts{org}{season}", "division_code_observed": "11",
                          "division_label": label, "division_authority": "GRAPH_PAGE", "disposition": "VERIFIED_PRESENT",
                          "in_division_i_population": label in ("FBS", "FCS"), "expected_sources": ["E1"], "flags": [],
                          "observations": {}})
    data = pop.build_query_database(contract_sha256=PARENT_CONTRACT_SHA, m1_identity=M1, m2_identity=M2, cells=cells,
                                    contests=rows, orientations=[],
                                    subsets={"FBS_ESTIMAND_SUBSET": [], "FCS_SUBSET": []}, schedule=[])
    result = pop.materialize(canonical_root=base / "canonical" / "p", manifest_root=base / "manifests" / "p",
                             stage="query-db", contract_sha256=PARENT_CONTRACT_SHA, inputs={},
                             upstream={"program-season": M1, "contest": M2}, files={pop.DB_FILE_NAME: data},
                             manifest_extra={})
    parent_db = Path(result["data_dir"]) / pop.DB_FILE_NAME
    bindings = [{"_header": {"contract_sha256": PARENT_CONTRACT_SHA, "schema": "BAS-NATIONAL-DI-POPULATION-1",
                             "stage": "program-season"}}]
    for org, (_n, _l, pid, _pn, _c, rule) in sorted(TEAMS.items()):
        bindings.append({"org_id": org, "cfbd_team_id": pid, "rule": rule,
                         "reason": None if pid else "NO_SCHEDULE_EVIDENCE"})
    write_gzip_jsonl(base / "canonical" / "p" / "sha256" / M1 / "identity_bindings.jsonl.gz", bindings)
    write_registry(base / "canonical" / "reg" / "canonical_core_registry.csv")
    captures = []
    for season, games in PROVIDER.items():
        raw = json.dumps(games).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        rel = f"raw/SRC-002/games/sha256_{digest}.json"
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
        (base / rel).write_bytes(raw)
        receipt = {"response_sha256": digest, "row_count": len(games), "capture_id": f"cap_fixture_{season}",
                   "source_id": "SRC-002", "path": "/games", "parameters": {"classification": "fbs", "year": str(season)},
                   "immutable_path": rel, "http_status": 200, "result": "SUCCESS",
                   "upstream_lineage": "CFBD_AGGREGATED_OR_DERIVED_RECORD; NOT_AN_INDEPENDENT_CONFIRMATION_OF_ITS_UPSTREAM_SOURCE"}
        receipt_rel = f"manifests/captures/SRC-002/cap_fixture_{season}.json"
        (base / receipt_rel).parent.mkdir(parents=True, exist_ok=True)
        (base / receipt_rel).write_text(json.dumps(receipt, indent=1), encoding="utf-8")
        captures.append({"season": season, "relative_path": rel, "sha256": digest, "rows": len(games),
                         "receipt_relative_path": receipt_rel, "receipt_sha256": sha(base / receipt_rel),
                         "capture_id": f"cap_fixture_{season}", "source_id": "SRC-002", "route_path": "/games",
                         "route_parameters": {"classification": "fbs", "year": str(season)}})
    counts: dict[str, int] = {}
    for row in rows:
        if row["season"] in (2024, 2025):
            counts[str(row["season"])] = counts.get(str(row["season"]), 0) + 1
    parent = {"query_db_identity": parent_db.parent.name, "sqlite_sha256": sha(parent_db),
              "contract_sha256": PARENT_CONTRACT_SHA, "schema_version": pop.DB_SCHEMA_VERSION, "contest_identity": M2,
              "program_season_identity": M1, "expected_contests": counts}
    inputs = {"identity_bindings": {"relative_path": f"canonical/p/sha256/{M1}/identity_bindings.jsonl.gz",
                                    "sha256": sha(base / "canonical" / "p" / "sha256" / M1 / "identity_bindings.jsonl.gz")},
              "registry": {"relative_path": "canonical/reg/canonical_core_registry.csv",
                           "sha256": sha(base / "canonical" / "reg" / "canonical_core_registry.csv")},
              "provider_captures": captures}
    return {"parent_db": parent_db, "parent": parent, "inputs": inputs}


def load_builder():
    spec = importlib.util.spec_from_file_location("build_national_population_reconciliation_fixture", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_contract(path: Path, fixture: dict) -> dict:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    contract["parent"] = fixture["parent"]
    contract["inputs"] = fixture["inputs"]
    contract["content_scope"] = query.reconciliation_scope(fixture)
    path.write_text(json.dumps(contract, indent=1), encoding="utf-8")
    return {"contract_sha256": sha(path), "parent": fixture["parent"], "inputs": fixture["inputs"]}


def build_sidecar(builder, contract: Path, parent_db: Path, out: Path, *extra: str) -> tuple[int, dict, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = builder.main(["--contract", str(contract), "--parent-database", str(parent_db),
                             "--output-root", str(out / "canonical" / POPULATION),
                             "--manifest-root", str(out / "manifests" / POPULATION), *extra])
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else {}), stderr.getvalue()


class Fixture(unittest.TestCase):
    """One fixture per class: parent, inputs, contract and a canonical sidecar build (read only for the tests)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.setup_error = None
        try:
            cls.base = Path(cls._tmp.name) / "d"
            cls.fixture = build_inputs(cls.base)
            cls.parent_db = cls.fixture["parent_db"]
            cls.contract = Path(cls._tmp.name) / "contract.json"
            cls.anchors = write_contract(cls.contract, cls.fixture)
            cls.builder = load_builder()
            code, cls.built, err = build_sidecar(cls.builder, cls.contract, cls.parent_db, cls.base)
            if code != 0:
                raise AssertionError(f"fixture build refused: {err}")
            cls.sidecar = Path(cls.built["database"]["data_dir"]) / DB_NAME
        except Exception as exc:  # noqa: BLE001 - each test then fails on its own identity (unfixed-base proof)
            cls.setup_error = f"{type(exc).__name__}: {exc}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        if self.setup_error:
            self.fail(f"fixture unavailable: {self.setup_error}")

    def open(self, sidecar: Path | None = None, *, parent_db: Path | None = None, anchors: dict | None = None,
             **kwargs) -> query.ReconciliationSidecar:
        parent_path = parent_db or self.parent_db
        parent = query.NationalPopulationDatabase(parent_path)
        try:
            return query.ReconciliationSidecar(sidecar or self.sidecar, parent=parent, parent_database=parent_path,
                                               anchors=anchors or self.anchors, **kwargs)
        finally:
            parent.close()

    def refused(self, code: str, sidecar: Path | None = None, **kwargs) -> None:
        with self.assertRaises(query.NationalQueryError) as ctx:
            self.open(sidecar, **kwargs).close()
        self.assertEqual(ctx.exception.code, code, str(ctx.exception))

    def run_main(self, *args: str, anchors: dict | None = None) -> tuple[int, dict | None, str]:
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(query, "RECONCILIATION_ANCHORS", anchors or self.anchors), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = query.main(["--database", str(self.parent_db), *args])
            except SystemExit as exc:
                code = exc.code
        text = out.getvalue()
        return code, (json.loads(text) if text.strip() else None), err.getvalue()


class AcceptedDefaultTests(unittest.TestCase):
    """Accepted behaviour only (BEFORE_REPRODUCTION positives on the unfixed base)."""

    def test_default_grains_keep_their_exact_key_sets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = build_inputs(Path(tmp) / "d")
            for grain, keys in (("contest", {"contract_sha256", "database_identity", "filters", "grain", "limit", "offset",
                                             "returned", "rows", "season_scope_state", "total"}),
                                ("program-season", {"contract_sha256", "database_identity", "filters", "grain", "limit",
                                                    "offset", "returned", "rows", "season_scope_state", "total"})):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = query.main(["--database", str(fixture["parent_db"]), "--grain", grain, "--season", "2024"])
                self.assertEqual(code, 0)
                result = json.loads(out.getvalue())
                self.assertEqual(set(result), keys)
                self.assertEqual({r["reconciliation_state"] for r in result["rows"]} if grain == "contest" else set(),
                                 {"SINGLE_SOURCE_UNRECONCILED"} if grain == "contest" else set())

    def test_the_long_location_clears_300_characters_from_every_local_root(self) -> None:
        tail = os.path.join("canonical", POPULATION, "sha256", "f" * 64, DB_NAME)
        for length in range(3, 101):
            base = "C:\\" + "r" * (length - 3)
            with self.subTest(root_length=length):
                far = os.path.join(long_root(base), tail)
                self.assertGreater(len(far), 300)
                self.assertTrue(all(len(part) <= 255 for part in far.split(os.sep)))
        for named in ("C:\\", "D:\\a\\_temp\\tmpabcdefgh"):
            self.assertGreater(len(os.path.join(long_root(named), tail)), 300)


class DerivationTests(Fixture):
    def records(self) -> tuple[dict, dict]:
        with self.open() as handle:
            parents = {r["contest_key"]: r for r in handle.records["parent-reconciliation"]}
            providers = {r["provider_row_key"]: r for r in handle.records["provider-reconciliation"]}
        return parents, providers

    def test_every_parent_contest_and_provider_row_is_accounted_once_in_both_directions(self) -> None:
        parents, providers = self.records()
        expected_parents = sorted(c["contest_key"] for c in PARENTS if c["season"] in (2024, 2025))
        self.assertEqual(sorted(parents), expected_parents)
        self.assertNotIn("ncaa:900", parents)  # 2023 is reconciled in the parent itself, not here
        expected_rows = sorted(f"src002:{s}:{i:04d}" for s, games in PROVIDER.items() for i in range(len(games)))
        self.assertEqual(sorted(providers), expected_rows)
        for key, record in parents.items():
            if record["relation"]:
                linked = providers[record["relation"]["provider_row_key"]]
                self.assertEqual(linked["relation"]["contest_key"], key)
                self.assertEqual(linked["disposition"], record["disposition"])
        for key, record in providers.items():
            if record["relation"]:
                self.assertEqual(parents[record["relation"]["contest_key"]]["relation"]["provider_row_key"], key)

    def test_dispositions_follow_the_contract_rules(self) -> None:
        parents, providers = self.records()
        expect = {
            "ncaa:1001": "RECONCILED_FIELDS_AGREE", "ncaa:1002": "RECONCILED_FIELDS_AGREE",
            "ncaa:1003": "RECONCILED_FIELDS_AGREE", "ncaa:1004": "RECONCILED_FIELD_CONFLICT",
            "ncaa:1005": "RECONCILED_FIELD_CONFLICT", "ncaa:1006": "RECONCILED_FIELDS_AGREE",
            "nolink:2024:2024-10-19:org:100|org:200": "RECONCILED_FIELDS_AGREE",
            "ncaa:1008": "RECONCILED_FIELD_CONFLICT", "ncaa:1009": "RECONCILED_FIELDS_AGREE",
            "ncaa:1010": "CANDIDATE_PARTICIPANT_EVIDENCE_INCOMPLETE", "ncaa:1011": "OUT_OF_ROUTE_NOT_EXPECTED",
            "ncaa:1012": "UNMATCHED_PARTICIPANT_UNBOUND", "ncaa:1013": "UNMATCHED_IN_ROUTE_PROVIDER_ROW_ABSENT",
            "ncaa:1014": "UNMATCHED_DATE_OUTSIDE_LOCAL_CANDIDATES", "ncaa:1015": "AMBIGUOUS_PROVIDER_CANDIDATES",
            "ncaa:1016": "AMBIGUOUS_PROVIDER_CANDIDATES", "ncaa:1017": "AMBIGUOUS_PROVIDER_CANDIDATES",
            "ncaa:1018": "RECONCILED_FIELDS_AGREE", "ncaa:1019": "OUT_OF_ROUTE_NOT_EXPECTED",
            "ncaa:1020": "RECONCILED_FIELD_CONFLICT", "ncaa:2001": "RECONCILED_FIELDS_AGREE",
            "ncaa:2002": "OUT_OF_ROUTE_NOT_EXPECTED", "ncaa:2003": "RECONCILED_FIELDS_AGREE"}
        self.assertEqual({k: v["disposition"] for k, v in parents.items()}, expect)
        by_id = {}
        for record in providers.values():
            by_id.setdefault(record["provider"]["id"], []).append(record["disposition"])
        self.assertEqual(by_id[11], ["UNMATCHED_DATE_OUTSIDE_LOCAL_CANDIDATES"])
        self.assertEqual(by_id[12], ["AMBIGUOUS_PARENT_CANDIDATES"])
        self.assertEqual(by_id[13], ["DUPLICATE_PROVIDER_GAME_ID", "DUPLICATE_PROVIDER_GAME_ID"])
        self.assertEqual(by_id[17], ["UNMATCHED_PARTICIPANT_UNBOUND"])
        self.assertEqual(by_id[18], ["UNMATCHED_PARENT_CONTEST_ABSENT"])
        self.assertEqual(by_id[19], ["PROVIDER_SEASON_MISMATCH"])
        self.assertEqual(by_id[20], ["INVALID_PROVIDER_ROW"])
        self.assertEqual(by_id[103], ["UNMATCHED_PARENT_CONTEST_ABSENT"])
        self.assertEqual(parents["ncaa:1015"]["disposition_reason"], "PROVIDER_ROW_HAS_MULTIPLE_DATED_PARENTS")
        self.assertEqual(parents["ncaa:1017"]["disposition_reason"], "DUPLICATE_PROVIDER_GAME_ID")

    def test_utc_rollover_postseason_and_same_pair_rematches_bind_by_local_date(self) -> None:
        parents, _providers = self.records()
        rollover = parents["ncaa:1003"]["comparisons"]["date"]
        self.assertEqual(rollover["provider_start_utc"], "2024-09-14T01:30:00.000Z")
        self.assertEqual(rollover["provider_candidate_local_dates"], ["2024-09-13"])
        post = parents["ncaa:1009"]
        self.assertEqual((post["season"], post["contest_date"]), (2024, "2025-01-02"))
        self.assertEqual(post["relation"]["provider_game_id"], "9")
        same_pair = [k for k, r in parents.items() if r["season"] == 2024 and r["parent"]["a_org_id"] in ("100", "200")
                     and r["parent"]["b_org_id"] in ("100", "200")]
        self.assertEqual(len(same_pair), 4)
        self.assertEqual(len({parents[k]["relation"]["provider_row_key"] for k in same_pair}), 4)
        ambiguous = parents["ncaa:1015"]["candidates"]["dated_provider_rows"]
        self.assertEqual(ambiguous, parents["ncaa:1016"]["candidates"]["dated_provider_rows"])

    def test_fields_compare_at_their_own_authority_and_never_mask_a_conflict(self) -> None:
        parents, _providers = self.records()
        score = parents["ncaa:1004"]
        self.assertEqual(score["field_conflicts"], ["score"])
        self.assertEqual(score["comparisons"]["score"]["parent"], [28, 24])
        self.assertEqual(score["comparisons"]["score"]["provider_oriented"], [28, 27])
        swapped = parents["ncaa:1005"]["comparisons"]
        self.assertEqual(swapped["score"]["result"], "AGREE")  # oriented by bound ids, not by provider order
        self.assertEqual(swapped["home_orientation"]["result"], "DISAGREE")
        neutral = parents["ncaa:1006"]["comparisons"]
        self.assertEqual((neutral["neutral_status"]["result"], neutral["home_orientation"]["result"]),
                         ("AGREE", "NOT_COMPARABLE_PARENT_NEUTRAL_NO_DESIGNATION"))
        canceled = parents["nolink:2024:2024-10-19:org:100|org:200"]["comparisons"]
        self.assertEqual((canceled["completion"]["result"], canceled["score"]["result"]),
                         ("AGREE", "NOT_COMPARABLE_BOTH_MISSING"))
        self.assertEqual(canceled["score"]["parent"], [None, None])  # unknown, never zero
        relocated = parents["ncaa:1008"]
        self.assertEqual(relocated["field_conflicts"], ["neutral_status"])
        self.assertEqual(relocated["comparisons"]["home_orientation"]["result"],
                         "NOT_COMPARABLE_PROVIDER_NEUTRAL_DESIGNATION")
        boolean = parents["ncaa:1018"]["comparisons"]["score"]
        self.assertEqual(boolean["result"], "NOT_COMPARABLE_PROVIDER_INVALID")
        self.assertEqual(boolean["provider_oriented"], [True, 3])
        transition = parents["ncaa:1020"]
        self.assertEqual(transition["field_conflicts"], ["classification_a"])
        self.assertEqual(transition["comparisons"]["classification_a"], {"parent": "FCS", "provider": "fbs",
                                                                          "result": "DISAGREE"})
        self.assertEqual(parents["ncaa:2003"]["comparisons"]["classification_a"]["result"], "AGREE")

    def test_participants_need_crosswalk_program_season_and_documented_names(self) -> None:
        parents, providers = self.records()
        miami = parents["ncaa:1002"]["participants"]["a"]
        self.assertEqual(miami["name_link"]["state"], "SEASON_ALIAS_DOCUMENTED")
        self.assertEqual(miami["name_link"]["alias_record_ids"], ["obs_miami_ncaa"])
        usc = parents["ncaa:1010"]
        self.assertEqual(usc["participants"]["a"]["name_link"]["state"], "NO_DOCUMENTED_NAME_LINK")
        self.assertEqual(usc["participants"]["a"]["name_link"]["alias_outside_season_record_ids"], ["obs_usc_old"])
        self.assertEqual(usc["disposition_reason"], "a:NAME_LINK")
        self.assertFalse(usc["relation"]["promoted"])
        self.assertIsNotNone(usc["comparisons"])  # recorded, never promoted
        unbound = parents["ncaa:1012"]["participants"]["b"]["crosswalk"]
        self.assertEqual(unbound["state"], "UNBOUND")
        external = parents["ncaa:1019"]["participants"]["b"]
        self.assertEqual(external["program_season"]["state"], "NOT_APPLICABLE_NO_ORGANIZATION")
        zeta = next(r for r in providers.values() if r["provider"]["id"] == 17)
        self.assertEqual(zeta["participants"]["away"]["provider_team_id"], "30")
        self.assertEqual(zeta["participants"]["away"]["crosswalk"]["state"], "UNBOUND")  # never NCAA org 30

    def test_provider_records_promote_only_game_facts_and_bind_raw_rows(self) -> None:
        _parents, providers = self.records()
        first = providers["src002:2024:0000"]
        self.assertEqual(sorted(first["provider"]), sorted(query.PROVIDER_FACT_FIELDS))
        raw = PROVIDER[2024][0]
        self.assertEqual(first["raw_row_sha256"], hashlib.sha256(query.canonical_json_bytes(raw)).hexdigest())
        self.assertNotIn("homePregameElo", json.dumps(first))
        self.assertEqual(first["capture"]["sha256"], self.anchors["inputs"]["provider_captures"][0]["sha256"])

    def test_the_reader_and_the_payloads_agree_with_the_summary(self) -> None:
        with self.open() as handle:
            summary = handle.summary
        self.assertEqual(summary["parent"]["total"], 23)
        self.assertEqual(summary["provider"]["total"], 23)
        self.assertEqual(summary["parent"]["by_season"], {"2024": 20, "2025": 3})
        content = Path(self.built["content"]["data_dir"])
        self.assertEqual(json.loads((content / "summary.json").read_text(encoding="utf-8")), summary)
        self.assertEqual((content / "parent_reconciliation.jsonl").read_bytes().count(b"\n"), 23)


class DeterminismTests(Fixture):
    def test_orders_chunks_and_a_resumed_build_give_identical_bytes(self) -> None:
        reference = (self.built["content_identity"], self.built["database_sha256"])
        work = Path(self._tmp.name)
        variants = [("reverse", ["--input-order", "reverse"]), ("shuffle", ["--input-order", "shuffle:11"]),
                    ("chunk2", ["--chunk-size", "2", "--checkpoint-dir", str(work / "ck2")]),
                    ("chunk5", ["--chunk-size", "5", "--checkpoint-dir", str(work / "ck5")])]
        for name, extra in variants:
            with self.subTest(variant=name):
                code, built, err = build_sidecar(self.builder, self.contract, self.parent_db, work / f"v-{name}", *extra)
                self.assertEqual(code, 0, err)
                self.assertEqual((built["content_identity"], built["database_sha256"]), reference)
        checkpoint = work / "ck3"
        code, first, _ = build_sidecar(self.builder, self.contract, self.parent_db, work / "v-resume", "--chunk-size", "3",
                                       "--checkpoint-dir", str(checkpoint), "--stop-after-chunks", "4")
        self.assertEqual((code, first["state"]), (3, "INTERRUPTED_AT_CHECKPOINT"))
        self.assertFalse((work / "v-resume").exists())
        code, resumed, err = build_sidecar(self.builder, self.contract, self.parent_db, work / "v-resume", "--chunk-size",
                                           "3", "--checkpoint-dir", str(checkpoint), "--resume")
        self.assertEqual(code, 0, err)
        self.assertEqual((resumed["content_identity"], resumed["database_sha256"]), reference)

    def test_materialization_is_create_only(self) -> None:
        code, again, _ = build_sidecar(self.builder, self.contract, self.parent_db, self.base)
        self.assertEqual((code, again["state"], again["database"]["state"]),
                         (0, "ALREADY_PRESENT_IDENTICAL", "ALREADY_PRESENT_IDENTICAL"))
        work = Path(self._tmp.name) / "collide"
        shutil.copytree(self.base / "canonical" / POPULATION, work / "canonical" / POPULATION)
        target = work / "canonical" / POPULATION / "sha256" / self.built["content_identity"] / "summary.json"
        target.write_bytes(target.read_bytes() + b" ")
        code, _built, err = build_sidecar(self.builder, self.contract, self.parent_db, work)
        self.assertEqual(code, 2)
        self.assertIn("REFUSED_IMMUTABLE_COLLISION", err)

    def test_a_contract_with_other_rules_or_a_forked_checkpoint_is_refused(self) -> None:
        work = Path(self._tmp.name)
        bad = json.loads(self.contract.read_text(encoding="utf-8"))
        bad["parameters"]["provider_local_offset_hours"] = [0]
        (work / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
        code, _b, err = build_sidecar(self.builder, work / "bad.json", self.parent_db, work / "v-bad")
        self.assertEqual(code, 2)
        self.assertIn("CONTRACT_INVALID", err)
        checkpoint = work / "ck-fork"
        build_sidecar(self.builder, self.contract, self.parent_db, work / "v-fork", "--chunk-size", "4",
                      "--checkpoint-dir", str(checkpoint), "--stop-after-chunks", "2")
        chunk = checkpoint / "chunks" / "chunk_000001.jsonl"
        chunk.write_bytes(chunk.read_bytes().replace(b"RECONCILED", b"RECONCILEX", 1))
        code, _b, err = build_sidecar(self.builder, self.contract, self.parent_db, work / "v-fork", "--chunk-size", "4",
                                      "--checkpoint-dir", str(checkpoint), "--resume")
        self.assertEqual(code, 2)
        self.assertIn("REFUSED_ALTERED_PREFIX", err)


class ConsumerTests(Fixture):
    def test_both_grains_serve_verified_records_with_exact_paging(self) -> None:
        for grain in query.RECONCILIATION_GRAINS:
            code, everything, err = self.run_main("--grain", grain, "--reconciliation", str(self.sidecar), "--all")
            self.assertEqual(code, 0, err)
            self.assertEqual(everything["total"], 23)
            self.assertEqual(everything["pit_eligibility"], "PIT_ELIGIBILITY_NOT_ESTABLISHED")
            self.assertEqual(everything["reconciliation_identity"], self.sidecar.parent.name)
            seen, offset = [], 0
            while True:
                code, page, _ = self.run_main("--grain", grain, "--reconciliation", str(self.sidecar), "--limit", "4",
                                              "--offset", str(offset))
                seen.extend(page["rows"])
                if page["next_offset"] is None:
                    break
                offset = page["next_offset"]
            self.assertEqual(seen, everything["rows"])

    def test_filters_and_denominators(self) -> None:
        code, result, _ = self.run_main("--grain", "parent-reconciliation", "--reconciliation", str(self.sidecar),
                                        "--season", "2024", "--team", "Miami (FL)", "--all")
        self.assertEqual(code, 0)
        self.assertEqual({r["contest_key"] for r in result["rows"]},
                         {"ncaa:1002", "ncaa:1003", "ncaa:1006", "ncaa:1008", "ncaa:1009", "ncaa:1014", "ncaa:1017",
                          "ncaa:1018"})
        self.assertEqual(result["collection_denominators"]["total"], 23)
        self.assertEqual(sum(result["filtered_by_disposition"].values()), result["total"])
        code, result, _ = self.run_main("--grain", "provider-reconciliation", "--reconciliation", str(self.sidecar),
                                        "--contest", "1004")
        self.assertEqual([r["provider"]["id"] for r in result["rows"]], [4])
        code, result, _ = self.run_main("--grain", "parent-reconciliation", "--reconciliation", str(self.sidecar),
                                        "--contest", "cfbd:9", "--team", "org:415")
        self.assertEqual([r["contest_key"] for r in result["rows"]], ["ncaa:1009"])
        code, result, _ = self.run_main("--grain", "provider-reconciliation", "--reconciliation", str(self.sidecar),
                                        "--disposition", "DUPLICATE_PROVIDER_GAME_ID")
        self.assertEqual(result["total"], 2)
        code, result, _ = self.run_main("--grain", "parent-reconciliation", "--reconciliation", str(self.sidecar),
                                        "--season", "2019")
        self.assertEqual((code, result["season_scope_state"], result["rows"]),
                         (0, "OUTSIDE_RECONCILIATION_SIDECAR_SCOPE", []))

    def test_selection_and_filter_refusals(self) -> None:
        cases = [
            (("--grain", "parent-reconciliation"), "RECONCILIATION_NOT_SELECTED"),
            (("--grain", "contest", "--contest", "ncaa:1001"), "RECONCILIATION_NOT_SELECTED"),
            (("--grain", "contest", "--reconciliation", str(self.sidecar)), "RECONCILIATION_GRAIN_REQUIRED"),
            (("--grain", "parent-reconciliation", "--reconciliation", str(self.sidecar), "--division", "FBS"),
             "FILTER_NOT_APPLICABLE"),
            (("--grain", "parent-reconciliation", "--reconciliation", str(self.sidecar), "--disposition", "VERIFIED"),
             "DISPOSITION_UNKNOWN"),
            (("--grain", "provider-reconciliation", "--reconciliation", str(self.sidecar), "--disposition",
              "OUT_OF_ROUTE_NOT_EXPECTED"), "DISPOSITION_UNKNOWN"),
            (("--grain", "parent-reconciliation", "--reconciliation", str(self.sidecar), "--require-pit"),
             "PIT_ELIGIBILITY_NOT_ESTABLISHED"),
            (("--grain", "contest", "--require-pit"), "PIT_ELIGIBILITY_NOT_ESTABLISHED"),
            (("--grain", "parent-reconciliation", "--reconciliation", str(self.sidecar), "--offset", "-1"),
             "NEGATIVE_OFFSET"),
            (("--grain", "parent-reconciliation", "--reconciliation", str(self.sidecar),
              "--expect-reconciliation-identity", "0" * 64), "STALE_RECONCILIATION_IDENTITY"),
        ]
        for argv, code in cases:
            with self.subTest(argv=argv):
                exit_code, _result, err = self.run_main(*argv)
                self.assertEqual(exit_code, 2)
                self.assertEqual(json.loads(err.strip().splitlines()[-1])["refused"], code)

    def test_the_sidecar_connection_is_read_only(self) -> None:
        with self.open() as handle:
            with self.assertRaises(sqlite3.OperationalError):
                handle.conn.execute("DELETE FROM parent_reconciliation")

    def test_short_and_long_extended_locations_serve_the_same_rows(self) -> None:
        if not WINDOWS:
            self.skipTest("extended-length spellings are Windows locations")
        holder = tempfile.TemporaryDirectory()
        tmp = os.path.realpath(holder.name)
        try:
            self._serve_far(tmp)
        finally:  # a tree beyond 260 characters is removable only through the verbatim spelling
            shutil.rmtree(native(tmp))
            holder.cleanup()

    def _serve_far(self, tmp: str) -> None:
        far_root = long_root(tmp)
        identity = self.sidecar.parent.name
        for kind in ("canonical", "manifests"):
            source = self.base / kind / POPULATION / "sha256" / identity
            for name in os.listdir(source):
                target = native(os.path.join(far_root, kind, POPULATION, "sha256", identity, name))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copyfile(source / name, target)
        far = native(os.path.join(far_root, "canonical", POPULATION, "sha256", identity, DB_NAME))
        self.assertGreater(len(far), 300)
        with self.open() as near, self.open(Path(far)) as distant:
            self.assertEqual(near.records, distant.records)
        with self.open(Path(native(self.sidecar))) as again:
            self.assertEqual(again.content_identity, self.built["content_identity"])
        # built verbatim: os.path.abspath would strip the trailing dot and name the normalized twin instead
        dotted = EXT + os.path.join(tmp, "dot.", "canonical", POPULATION, "sha256", identity, DB_NAME)
        with self.assertRaises(query.NationalQueryError) as ctx:
            self.open(Path(dotted)).close()
        self.assertEqual(ctx.exception.code, "DATABASE_LOCATION_NOT_LITERAL")


class ForgeryTests(Fixture):
    """Coordinated forgeries: bytes, counts, identity document, identity directory and manifest all consistent."""

    def setUp(self) -> None:
        super().setUp()
        self._work = tempfile.TemporaryDirectory()
        self.work = Path(self._work.name)

    def tearDown(self) -> None:
        self._work.cleanup()

    def forge(self, statements: list[tuple[str, tuple]], document: dict | None = None) -> Path:
        copy_path = self.work / "copy.sqlite"
        shutil.copyfile(self.sidecar, copy_path)
        conn = sqlite3.connect(copy_path)
        for sql, params in statements:
            changed = conn.execute(sql, params).rowcount
            if not sql.lstrip().upper().startswith("CREATE"):
                self.assertGreater(changed, 0, sql)  # a forgery that changes nothing proves nothing
        conn.commit()
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in query.RECONCILIATION_TABLES}
        conn.close()
        manifest = json.loads((self.base / "manifests" / POPULATION / "sha256" / self.sidecar.parent.name /
                               "run_manifest.json").read_text(encoding="utf-8"))
        doc = copy.deepcopy(manifest["identity_document"])
        doc["outputs"] = {DB_NAME: sha(copy_path)}
        doc["table_counts"] = counts
        doc.update(document or {})
        identity = hashlib.sha256(query.canonical_json_bytes(doc)).hexdigest()
        self.assertNotEqual(identity, self.sidecar.parent.name)
        target = self.work / "canonical" / POPULATION / "sha256" / identity / DB_NAME
        target.parent.mkdir(parents=True)
        shutil.copyfile(copy_path, target)
        man = self.work / "manifests" / POPULATION / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        man.write_text(json.dumps({"identity": identity, "identity_document": doc, "provenance": {}}), encoding="utf-8")
        return target

    def record_update(self, table: str, key_column: str, key: str, mutate) -> tuple[str, tuple]:
        conn = sqlite3.connect(self.sidecar.as_uri() + "?mode=ro", uri=True)
        text = conn.execute(f"SELECT record FROM {table} WHERE {key_column} = ?", (key,)).fetchone()[0]
        conn.close()
        record = json.loads(text)
        mutate(record)
        return (f"UPDATE {table} SET record = ? WHERE {key_column} = ?", (query.reconciliation_line(record), key))

    def meta_update(self, key: str, value) -> tuple[str, tuple]:
        return ("UPDATE meta SET value = ? WHERE key = ?", (value if isinstance(value, str) else
                                                            json.dumps(value, sort_keys=True, separators=(",", ":")), key))

    def test_omitted_duplicated_extra_and_reordered_rows_refuse_for_their_cause(self) -> None:
        self.refused("RECONCILIATION_PARENT_ROW_MISSING",
                     self.forge([("DELETE FROM parent_reconciliation WHERE contest_key = ?", ("ncaa:1011",))]))
        self.refused("RECONCILIATION_PROVIDER_ROW_MISSING",
                     self.forge([("DELETE FROM provider_reconciliation WHERE provider_row_key = ?", ("src002:2024:0017",))]))
        self.refused("RECONCILIATION_DUPLICATE_ROW", self.forge([(
            "INSERT INTO parent_reconciliation SELECT 999, contest_key, season, contest_date, a_key, b_key, disposition, "
            "provider_row_key, record FROM parent_reconciliation WHERE contest_key = ?", ("ncaa:1001",))]))
        self.refused("RECONCILIATION_PROVIDER_ROW_EXTRA", self.forge([(
            "INSERT INTO provider_reconciliation SELECT 999, 'src002:2024:0999', season, 999, provider_game_id, "
            "disposition, contest_key, record FROM provider_reconciliation WHERE ord = 0", ())]))
        self.refused("RECONCILIATION_ORDER_MISMATCH", self.forge([
            ("UPDATE parent_reconciliation SET ord = 1000 WHERE ord = 0", ()),
            ("UPDATE parent_reconciliation SET ord = 0 WHERE ord = 1", ()),
            ("UPDATE parent_reconciliation SET ord = 1 WHERE ord = 1000", ())]))

    def test_semantic_record_forgeries_refuse_for_their_cause(self) -> None:
        def drop_link(r):
            r["relation"] = None
        self.refused("RECONCILIATION_RELATION_MISMATCH", self.forge([
            self.record_update("provider_reconciliation", "provider_row_key", "src002:2024:0000", drop_link)]))

        def swap_scores(r):
            r["comparisons"]["score"]["provider_oriented"].reverse()
        self.refused("RECONCILIATION_FIELD_MISMATCH", self.forge([
            self.record_update("parent_reconciliation", "contest_key", "ncaa:1001", swap_scores)]))

        def forge_binding(r):
            r["participants"]["b"]["crosswalk"] = {"state": "BOUND", "provider_team_id": "9999",
                                                   "rule": "NAME_CONFIRMED_BY_SCHEDULE", "reason": None}
        self.refused("RECONCILIATION_PARTICIPANT_MISMATCH", self.forge([
            self.record_update("parent_reconciliation", "contest_key", "ncaa:1012", forge_binding)]))

        def promote(r):
            r["disposition"] = "RECONCILED_FIELDS_AGREE"
        self.refused("RECONCILIATION_DISPOSITION_MISMATCH", self.forge([
            self.record_update("parent_reconciliation", "contest_key", "ncaa:1004", promote)]))

        def mask_conflict(r):
            r["field_conflicts"] = []
            r["disposition"], r["disposition_reason"] = "RECONCILED_FIELDS_AGREE", None
        self.refused("RECONCILIATION_FIELD_MISMATCH", self.forge([
            self.record_update("parent_reconciliation", "contest_key", "ncaa:1004", mask_conflict)]))

        def swap_parent_teams(r):
            p = r["parent"]
            for f in ("org_id", "team_name", "points", "key"):
                p[f"a_{f}"], p[f"b_{f}"] = p[f"b_{f}"], p[f"a_{f}"]
        self.refused("RECONCILIATION_SOURCE_FIELD_MISMATCH", self.forge([
            self.record_update("parent_reconciliation", "contest_key", "ncaa:2001", swap_parent_teams)]))
        self.refused("RECONCILIATION_INDEX_MISMATCH", self.forge([
            ("UPDATE parent_reconciliation SET disposition = 'RECONCILED_FIELDS_AGREE' WHERE contest_key = ?",
             ("ncaa:1004",))]))

    def test_rehashed_summary_content_scope_pit_contract_parent_and_source_claims_refuse(self) -> None:
        conn = sqlite3.connect(self.sidecar.as_uri() + "?mode=ro", uri=True)
        meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
        conn.close()
        summary = json.loads(meta["summary"])
        summary["parent"]["by_disposition"]["RECONCILED_FIELDS_AGREE"] += 1
        self.refused("RECONCILIATION_SUMMARY_MISMATCH", self.forge([self.meta_update("summary", summary)]))
        forged_identity = "e" * 64
        self.refused("RECONCILIATION_CONTENT_IDENTITY_MISMATCH",
                     self.forge([self.meta_update("content_identity", forged_identity)],
                                {"content_identity": forged_identity}))
        scope = json.loads(meta["scope"])
        scope["seasons"] = list(range(2016, 2026))
        self.refused("RECONCILIATION_SCOPE_CLAIM_INVALID", self.forge([self.meta_update("scope", scope)]))
        labels = json.loads(meta["labels"])
        labels["pit_eligibility"] = "PIT_ELIGIBLE"
        self.refused("RECONCILIATION_PIT_CLAIM_INVALID", self.forge([self.meta_update("labels", labels)]))
        parent = json.loads(meta["parent"])
        parent["query_db_identity"] = "a" * 64
        self.refused("RECONCILIATION_PARENT_MISMATCH", self.forge([self.meta_update("parent", parent)]))
        inputs = json.loads(meta["inputs"])
        inputs["provider_captures"][0]["sha256"] = "b" * 64
        self.refused("RECONCILIATION_SOURCE_MISMATCH", self.forge([self.meta_update("inputs", inputs)]))
        self.refused("RECONCILIATION_CONTRACT_MISMATCH", self.forge([], {"contract_sha256": "c" * 64}))
        self.refused("RECONCILIATION_SCHEMA_UNSUPPORTED",
                     self.forge([("UPDATE meta SET value = ? WHERE key = 'schema_version'", ("OTHER-DB-1",))]))
        self.refused("RECONCILIATION_SCHEMA_UNSUPPORTED", self.forge([("CREATE TABLE extra (x TEXT)", ())]))
        self.refused("RECONCILIATION_META_MISMATCH", self.forge([("INSERT INTO meta VALUES ('summary', 'x')", ())]))

    def test_outer_identity_refusals(self) -> None:
        tampered = self.work / "t" / "canonical" / POPULATION / "sha256" / self.sidecar.parent.name / DB_NAME
        tampered.parent.mkdir(parents=True)
        data = bytearray(self.sidecar.read_bytes())
        data[-100] ^= 1
        tampered.write_bytes(bytes(data))
        man = self.work / "t" / "manifests" / POPULATION / "sha256" / self.sidecar.parent.name
        man.mkdir(parents=True)
        shutil.copyfile(self.base / "manifests" / POPULATION / "sha256" / self.sidecar.parent.name / "run_manifest.json",
                        man / "run_manifest.json")
        self.refused("RECONCILIATION_DATABASE_TAMPERED", tampered)
        (man / "run_manifest.json").write_text(json.dumps({"identity": "x", "identity_document": {"stage": "x"}}),
                                               encoding="utf-8")
        self.refused("RECONCILIATION_IDENTITY_MISMATCH", tampered)
        (man / "run_manifest.json").unlink()
        self.refused("RECONCILIATION_MANIFEST_MISSING", tampered)
        moved = self.work / "elsewhere" / DB_NAME
        moved.parent.mkdir()
        shutil.copyfile(self.sidecar, moved)
        self.refused("RECONCILIATION_LOCATION_INVALID", moved)
        self.refused("RECONCILIATION_CONTRACT_MISMATCH", anchors={**self.anchors, "contract_sha256": "d" * 64})

    def test_altered_inputs_or_another_parent_refuse(self) -> None:
        shutil.copytree(self.base, self.work / "d")
        parent_db = self.work / "d" / self.parent_db.relative_to(self.base)
        capture = self.work / "d" / self.anchors["inputs"]["provider_captures"][0]["relative_path"]
        original = capture.read_bytes()
        capture.write_bytes(original.replace(b'"homePoints": 21', b'"homePoints": 22', 1))
        self.refused("RECONCILIATION_SOURCE_BYTES_MISMATCH", parent_db=parent_db)
        capture.write_bytes(original)
        receipt = self.work / "d" / self.anchors["inputs"]["provider_captures"][0]["receipt_relative_path"]
        receipt_doc = json.loads(receipt.read_text(encoding="utf-8"))
        receipt_doc["row_count"] += 1
        receipt.write_text(json.dumps(receipt_doc), encoding="utf-8")
        self.refused("RECONCILIATION_RECEIPT_MISMATCH", parent_db=parent_db)
        # a receipt re-pinned by hash must still name its capture's bytes, rows, id, route and success
        anchors = copy.deepcopy(self.anchors)
        anchors["inputs"]["provider_captures"][0]["receipt_sha256"] = sha(receipt)
        with self.assertRaises(query.NationalQueryError) as ctx:
            query.load_reconciliation_inputs(self.work / "d", anchors)
        self.assertEqual(ctx.exception.code, "RECONCILIATION_RECEIPT_MISMATCH")
        self.assertIn("row_count", str(ctx.exception))
        bindings = self.work / "d" / self.anchors["inputs"]["identity_bindings"]["relative_path"]
        bindings.unlink()
        self.refused("RECONCILIATION_INPUT_MISSING", parent_db=parent_db)
        other = build_inputs(self.work / "o", PARENTS[:-1])
        self.refused("RECONCILIATION_PARENT_MISMATCH", parent_db=other["parent_db"])


if __name__ == "__main__":
    unittest.main()
