"""Tiny owned worlds and coordinated forgeries for the BAT-423 national retrospective reference tests (Cycle #56
TP56-A01).

Not a test module (no ``test`` prefix). Every world is real: the parent is built by the accepted BAT-710 population
builder under a fixture parent contract whose SHA-256 the parent carries, the history by the accepted BAT-711 history
builder, the C47 benchmark by the accepted BAT-719 builder, then the reference by the repository builder with the
committed research contract whose parent bindings name those fixtures. Forged references are coordinated: database
bytes, table counts, identity documents, identity directories and manifests are rewritten consistently, so each must be
refused by its own semantic rule, never by a stale outer hash.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import random
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
import retrospective_baseline_fixture as bx  # noqa: E402
from aggie_analytics.data import national_di_population as pop  # noqa: E402
from aggie_analytics.retrospective_baseline import benchmark as bm  # noqa: E402
from aggie_analytics.retrospective_baseline import reference as rc  # noqa: E402

CONTRACT_PATH = ROOT / "configs" / "national_retrospective_reference_2016_2023_contract.json"
BUILDER_PATH = ROOT / "tools" / "build_national_retrospective_reference.py"
POP = rc.POPULATION

#: org id -> (display name, division label); Texas A&M is org 697 as in the accepted national population.
TEAMS = {"1": ("Alpha", "FBS"), "2": ("Bravo", "FBS"), "3": ("Charlie St.", "FBS"), "5": ("Echo", "FBS"),
         "697": ("Texas A&M", "FBS"), "8": ("Hotel", "FBS"), "4": ("Delta", "FCS"), "6": ("Foxtrot", "FCS"),
         "9": ("Golf", "DII")}
FBS = ("1", "2", "3", "5", "697", "8")


def builder() -> Any:
    return hx.load_tool(BUILDER_PATH, "bas_retrospective_reference_builder")


def contest(key: str, season: int, date: str, a: str, b: str, a_pts: Any, b_pts: Any, *, term: str = "FALL",
            site: str = "HOME_A", status: str = "COMPLETED", competitive: bool = True,
            disposition: str = "VERIFIED_PRESENT", state: str = "RECONCILED_2016_2023", a_name: str | None = None,
            b_label: str | None = None) -> dict[str, Any]:
    """A parent contest row in the accepted BAT-710 shape (a non-NCAA opponent keeps an ``ext:`` key)."""
    a_label = TEAMS[a][1]
    b_label = b_label or (TEAMS[b][1] if b in TEAMS else "NON_NCAA")
    return {"contest_key": key, "ncaa_contest_id": key.split(":", 1)[1], "season": season, "term": term,
            "contest_date": date, "site": site, "neutral_site_text": "Fixture Bowl" if site == "NEUTRAL" else None,
            "contest_status": status, "competitive": competitive, "a_org_id": a, "a_team_season_id": f"ts{a}-{season}",
            "a_team_name": a_name or TEAMS[a][0], "a_division_label": a_label, "a_membership": "DIVISION_I",
            "a_points": a_pts, "b_org_id": b if b in TEAMS else None, "b_team_season_id": f"ts{b}-{season}",
            "b_team_name": TEAMS[b][0] if b in TEAMS else b, "b_division_label": b_label,
            "b_membership": "DIVISION_I" if b in TEAMS else "NON_NCAA", "b_points": b_pts,
            "classification_pair": "-".join(sorted((a_label, b_label))), "mirror_observation_count": 2,
            "source": "NCAA_GRAPH", "cfbd_game_ids": [f"9{key.split(':')[1]}"], "reconciliation_state": state,
            "disposition": disposition, "disposition_reason": None, "exposure": "X", "conflict_fields": [],
            "flags": [], "event_labels": [], "a_key": f"org:{a}", "b_key": f"org:{b}" if b in TEAMS else f"ext:{b}",
            "contest_dates_observed": [date], "mirror_scores_observed": None, "contest_statuses_observed": None,
            "cfbd_observation": None}


def world_contests() -> list[dict[str, Any]]:
    """Positive classes of TP56 sections 2-4 in one synthetic national world: several weeks of FBS games in training
    seasons 2021-2022 and the comparison season 2023, FCS and outside-division priors, a prior tie, a renamed program,
    same-date games, cold starts, Texas A&M in every season, a neutral site, the 2020 academic year with spring games,
    excluded contests and protected 2024/2025 rows."""
    rng = random.Random(56)
    rows: list[dict[str, Any]] = []
    number = 1000
    for season in (2021, 2022, 2023):
        # week 0: FBS against FCS / outside opponents (prior pool games, not targets)
        for i, team in enumerate(FBS):
            number += 1
            opponent = ("4", "6", "9")[i % 3]
            rows.append(contest(f"ncaa:{number}", season, f"{season}-08-2{i % 3 + 6}", team, opponent,
                                rng.randint(21, 49), rng.randint(0, 20)))
        number += 1
        rows.append(contest(f"ncaa:{number}", season, f"{season}-08-29", "8", "West Tech", 45, 0))  # non-NCAA: excluded
        teams = list(FBS)
        for week in range(5):
            rng.shuffle(teams)
            day = f"{season}-09-{week * 7 + 2:02d}"
            for j in range(0, len(teams), 2):
                number += 1
                a, b = teams[j], teams[j + 1]
                a_pts, b_pts = rng.randint(3, 45), rng.randint(3, 45)
                if a_pts == b_pts:
                    a_pts += 3
                if (season, week, j) == (2022, 2, 2):
                    a_pts = b_pts = 20  # an FBS tie target: half a win in later priors, UNSCORED for probabilities
                rows.append(contest(f"ncaa:{number}", season, day, a, b, a_pts, b_pts,
                                    site="NEUTRAL" if (week, j) == (2, 0) else "HOME_A",
                                    a_name="Charlie State" if (a == "3" and week == 3) else None))
        number += 1
        rows.append(contest(f"ncaa:{number}", season, f"{season}-10-15", "4", "6", 17, 17))  # a prior-pool tie (FCS)
        number += 1
        rows.append(contest(f"ncaa:{number}", season, f"{season}-10-22", "1", "2", None, None, status="CANCELED",
                            competitive=False, disposition="CANDIDATE_ONLY", state="NOT_RECONCILED_NON_COMPETITIVE"))
    rows += [
        contest("ncaa:201", 2020, "2020-10-03", "1", "2", 21, 14),
        contest("ncaa:202", 2020, "2021-01-02", "697", "5", 28, 27),
        contest("ncaa:203", 2020, "2021-03-06", "4", "6", 14, 10, term="SPRING"),
        contest("ncaa:204", 2020, "2021-03-13", "1", "4", 38, 3, term="SPRING"),
        contest("ncaa:205", 2020, "2021-04-03", "1", "697", 24, 23, term="SPRING"),
        contest("ncaa:401", 2024, "2024-08-31", "1", "2", 31, 30, disposition="CANDIDATE_ONLY",
                state="SINGLE_SOURCE_UNRECONCILED"),
        contest("ncaa:402", 2025, "2025-08-30", "697", "5", 14, 13, disposition="CANDIDATE_ONLY",
                state="SINGLE_SOURCE_UNRECONCILED"),
    ]
    return rows


def build_parent(base: Path, contests: list[dict[str, Any]], contract_path: Path) -> dict[str, Any]:
    """The accepted BAT-710 builder under a fixture parent contract whose SHA-256 the parent carries."""
    contract_path.write_text(json.dumps({"fixture": "BAT-423 reference test parent contract"}) + "\n",
                             encoding="utf-8", newline="\n")
    contract_sha = pop.sha256_file(contract_path)
    data = pop.build_query_database(contract_sha256=contract_sha, m1_identity=hx.M1, m2_identity=hx.M2, cells=[],
                                    contests=contests, orientations=[], subsets=hx.subsets_for(contests), schedule=[])
    result = pop.materialize(canonical_root=Path(base) / "canonical" / "p", manifest_root=Path(base) / "manifests" / "p",
                             stage="query-db", contract_sha256=contract_sha, inputs={},
                             upstream={"program-season": hx.M1, "contest": hx.M2}, files={pop.DB_FILE_NAME: data},
                             manifest_extra={})
    db = Path(result["data_dir"]) / pop.DB_FILE_NAME
    return {"database": db, "manifest": Path(result["manifest"]), "identity": result["identity"],
            "sqlite_sha256": pop.sha256_file(db), "contract": contract_path, "contract_sha256": contract_sha}


def build_world(base: Path, contests: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Parent, history and C47 benchmark built by the accepted builders under ``base``."""
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    rows = world_contests() if contests is None else contests
    parent = build_parent(base, rows, base / "pc.json")
    history_contract = hx.contract_for(parent)
    history_contract["parent_binding"]["contract_sha256"] = parent["contract_sha256"]
    history_contract_path = hx.write_contract(base / "hc.json", history_contract)
    code, result, stderr = hx.run_build(history_contract_path, parent, base)
    if code != 0:
        raise AssertionError(f"accepted history builder refused the fixture: {stderr}")
    history_db = Path(result["database"]["data_dir"]) / "national_history.sqlite"
    world = {"base": base, "parent": parent, "history_contract": history_contract_path, "history_db": history_db,
             "contests": rows}
    bench_contract = bx.write_contract(base / "bc.json", bx.contract_for(world))
    code, bench, stderr = bx.run_build(bench_contract, world, base)
    if code != 0:
        raise AssertionError(f"accepted C47 builder refused the fixture: {stderr}")
    world.update(benchmark_contract=bench_contract, benchmark_db=bx.database_of(bench), benchmark=bench)
    return world


def contract_for(world: dict[str, Any], **patch: Any) -> dict[str, Any]:
    """The committed research contract with only its parent bindings replaced by the fixture's (plus patches)."""
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    history = bx.history_binding(world["history_db"], world["history_contract"])
    with bm.RetrospectiveBenchmark(world["benchmark_db"], history_database=world["history_db"],
                                   anchors=bx.anchors_for(world["benchmark_contract"], world)) as reader:
        bench = {"contract_id": bm.CONTRACT_ID, "contract_sha256": bm.sha256_file(world["benchmark_contract"]),
                 "database_identity": reader.database_identity, "sqlite_sha256": reader.binding["sha256"],
                 "content_identity": reader.content_identity}
        targets = reader.derived["targets"]
    population = {"contract_id": rc.ANCHORS["population"]["contract_id"],
                  "contract_sha256": world["parent"]["contract_sha256"],
                  "database_identity": world["parent"]["identity"], "sqlite_sha256": world["parent"]["sqlite_sha256"],
                  "contest_identity": hx.M2, "program_season_identity": hx.M1}
    pool = sum(1 for c in world["contests"] if 2016 <= c["season"] <= 2023 and not rc.predicate_failures(
        {**c, "reconciliation_state": c["reconciliation_state"], "competitive": int(c["competitive"]),
         "contest_dates_observed": json.dumps(c["contest_dates_observed"])}))
    training = sum(1 for t in targets if t["season"] in rc.TRAINING_SEASONS)
    contract["parent"]["history"] = history
    contract["parent"]["population"] = population
    contract["parent"]["benchmark"] = bench
    contract["parent"]["expected"] = {"targets": len(targets), "views": 2 * len(targets), "pool": pool,
                                      "training_targets": training, "comparison_targets": len(targets) - training}
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


def anchors_for(contract_path: Path, world: dict[str, Any]) -> dict[str, Any]:
    return builder().load_contract(contract_path, parent_contracts(world))[2]


def parent_contracts(world: dict[str, Any]) -> dict[str, Path]:
    return {"history": world["history_contract"], "population": world["parent"]["contract"],
            "benchmark": world["benchmark_contract"]}


def run_build(contract_path: Path, world: dict[str, Any], out: Path, *extra: str
              ) -> tuple[int, dict[str, Any] | None, str]:
    argv = ["--contract", str(contract_path), "--history-database", str(world["history_db"]),
            "--population-database", str(world["parent"]["database"]),
            "--benchmark-database", str(world["benchmark_db"]),
            "--history-contract", str(world["history_contract"]),
            "--population-contract", str(world["parent"]["contract"]),
            "--benchmark-contract", str(world["benchmark_contract"]),
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
    return Path(result["database"]["data_dir"]) / rc.DB_FILE


def query(world: dict[str, Any], anchors: dict[str, Any], database: Path, *argv: str, front: Callable | None = None
          ) -> tuple[int, Any, str]:
    """The query's main() in process with fixture anchors; returns (exit, parsed stdout or None, stderr)."""
    from aggie_analytics.retrospective_baseline import query as q  # noqa: PLC0415
    tokens = ["--reference-comparison", str(database), "--history-database", str(world["history_db"]),
              "--population-database", str(world["parent"]["database"]), *argv]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = (front or q.main)(tokens, reference_anchors=anchors)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


# --------------------------------------------------------------------------------------------- forged references

class Forger:
    """Coordinated forgeries of one reference database in owned scratch."""

    def __init__(self, database: Path, root: Path) -> None:
        self.database = Path(database)
        self.root = Path(root)
        identity = self.database.parent.name
        population_root = self.database.parent.parent.parent
        self.manifest = json.loads((population_root.parent.parent / "manifests" / population_root.name / "sha256" /
                                    identity / "run_manifest.json").read_text(encoding="utf-8"))

    def tables(self) -> dict[str, list[dict[str, Any]]]:
        conn = sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True)
        out: dict[str, list[dict[str, Any]]] = {t: [] for t in (*rc.RECORD_TABLES, "summary")}
        for table, blob in conn.execute("SELECT record_table, block FROM blocks ORDER BY ord"):
            out[table] += [json.loads(line) for line in zlib.decompress(blob).decode("utf-8").splitlines()]
        conn.close()
        return out

    def forge(self, name: str, *, records: Callable[[dict[str, list[dict[str, Any]]]], None] | None = None,
              lines: Callable[[dict[str, list[str]]], None] | None = None, meta: dict[str, Any] | None = None,
              document: dict[str, Any] | Callable[[dict[str, Any]], None] | None = None,
              after_blocks: list[tuple[str, tuple]] | None = None) -> Path:
        """Copy, mutate and rehash. ``records`` edits the decoded record lists in place (blocks are rebuilt from
        canonical lines with consistent index columns); ``lines`` edits raw lines (float/boolean spellings); ``meta``
        replaces meta values; ``document`` patches the identity document; ``after_blocks`` runs after the rebuild."""
        work = self.root / name / "work.sqlite"
        work.parent.mkdir(parents=True)
        shutil.copyfile(self.database, work)
        conn = sqlite3.connect(work)
        conn.execute("PRAGMA journal_mode = OFF")
        if records is not None or lines is not None:
            tables = self.tables()
            if records is not None:
                records(tables)
            raw = {t: [bm.canonical_line(r) for r in rows] for t, rows in tables.items()}
            if lines is not None:
                lines(raw)
            conn.execute("DELETE FROM blocks")
            ord_ = 0
            for table, segment in rc.BLOCK_LAYOUT:
                pairs = [(json.loads(line), line) for line in raw[table]]
                if table in rc.SEASONAL_TABLES:
                    pairs = [(r, l) for r, l in pairs if str(r.get("season")) == segment]
                data = "".join(l + "\n" for _r, l in pairs).encode("utf-8")
                conn.execute("INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (ord_, table, segment, len(pairs),
                              rc.record_key(table, pairs[0][0]) if pairs else None,
                              rc.record_key(table, pairs[-1][0]) if pairs else None,
                              bm.sha256_bytes(data), zlib.compress(data, 9)))
                ord_ += 1
        for key, value in (meta or {}).items():
            text = value if isinstance(value, str) else bm.canonical_line(value)
            if conn.execute("UPDATE meta SET value = ? WHERE key = ?", (text, key)).rowcount != 1:
                raise AssertionError(f"meta forgery {key} changed nothing")
        for sql, params in after_blocks or []:
            if conn.execute(sql, params).rowcount < 1:
                raise AssertionError(f"block forgery changed nothing: {sql}")
        conn.commit()
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in rc.TABLES}
        conn.close()
        doc = copy.deepcopy(self.manifest["identity_document"])
        doc["outputs"] = {rc.DB_FILE: bm.sha256_file(work)}
        doc["table_counts"] = counts
        if callable(document):
            document(doc)
        else:
            doc.update(document or {})
        identity = bm.sha256_bytes(bm.canonical_json_bytes(doc))
        target = self.root / name / "canonical" / POP / "sha256" / identity / rc.DB_FILE
        target.parent.mkdir(parents=True)
        shutil.move(str(work), str(target))
        man = self.root / name / "manifests" / POP / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        man.write_text(json.dumps({"identity": identity, "identity_document": doc,
                                   "provenance": {"forgery": name}}), encoding="utf-8")
        return target
