"""Synthetic worlds for the BAT-714 history-availability tests (Cycle #42 TP42-A01). Not a test module.

``build_world`` reuses the accepted BAT-713 synthetic archive world (``national_archived_publication_fixture``): its
synthetic population, BAT-711 history and BAT-712 source-time parents built with the accepted producers, and an
archive sidecar captured offline from a fake archive and materialized with the accepted BAT-713 producer. On top of
it this module writes availability input bindings and a contract patched with the synthetic parent identities, and
registers both synthetic issued authorities in-process. ``unit_world`` builds a small hand-made 2019 population with
the accepted BAT-710 query-database writer and its BAT-711 history parent, for exact derivation cases (a parent
excluded prior, a same-date game, an undated contest, a tie, FCS opponents and cold starts). Every value is fictional.
"""
from __future__ import annotations

import contextlib
import copy
import datetime as dt
import gzip
import hashlib
import io
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import national_archived_publication_fixture as afx  # noqa: E402
import national_history_fixture as hfx  # noqa: E402
import national_source_time_fixture as stfx  # noqa: E402

from aggie_analytics.national_history import availability as core  # noqa: E402
from aggie_analytics.national_history import availability_query as aq  # noqa: E402
from aggie_analytics.national_source_time import archive  # noqa: E402

CONTRACT_PATH = ROOT / "configs" / "national_history_availability_2019_contract.json"
BUILDER_PATH = ROOT / "tools" / "build_national_history_availability.py"
VALIDATOR_PATH = ROOT / "tools" / "validate_national_history_availability.py"
#: the synthetic archive control (ncaa:1003) bound: capture 20190908013000 (second precision) as an upper bound
CONTROL_KEY = "ncaa:1003"
CONTROL_BOUND = "2019-09-08T01:30:00.999999Z"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def builder() -> Any:
    return stfx.load_tool(BUILDER_PATH, "bas_history_availability_builder")


def validator() -> Any:
    return stfx.load_tool(VALIDATOR_PATH, "bas_history_availability_validator")


def write(path: Path, data: bytes) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _sqlite_sha(path: Path) -> str:
    return sha(Path(path).read_bytes())


def build_world(base: Path) -> dict[str, Any]:
    """The synthetic archive world plus availability bindings, a patched contract and both authorities."""
    base = Path(base)
    world = afx.build_world(base / "w")
    afx.run_capture(world)
    code, built, err = afx.run_build(world)
    assert code == 0, err
    found = sorted(Path(world["out"]).glob("acquisition/sha256/*/acquisition.json"))
    assert len(found) == 1, found
    archive_db = afx.database_path(built)
    st_world, st_result = world["st_world"], world["st_result"]
    population_db, history_db, st_db = Path(st_world["population_db"]), Path(st_world["history_db"]), \
        Path(world["st_db"])
    pop_manifest = json.loads(aq.manifest_path_for(population_db).read_text(encoding="utf-8"))["identity_document"]
    hist = st_world["history_built"]
    hist_doc = json.loads(aq.manifest_path_for(history_db).read_text(encoding="utf-8"))["identity_document"]
    parent = {
        "population": {"query_db_identity": population_db.parent.name, "sqlite_sha256": _sqlite_sha(population_db),
                       "contract_sha256": pop_manifest["contract_sha256"],
                       "contest_identity": pop_manifest["upstream"]["contest"],
                       "program_season_identity": pop_manifest["upstream"]["program-season"]},
        "history": {"database_identity": hist["database_identity"], "sqlite_sha256": _sqlite_sha(history_db),
                    "content_identity": hist["content_identity"], "contract_sha256": hist_doc["contract_sha256"]},
        "source_time": {"database_identity": st_result["database_identity"], "sqlite_sha256": _sqlite_sha(st_db),
                        "content_identity": st_result["content_identity"],
                        "contract_sha256": st_result["contract_sha256"]},
        "archive": {"database_identity": built["database_identity"], "sqlite_sha256": _sqlite_sha(archive_db),
                    "content_identity": built["content_identity"],
                    "contract_sha256": sha(Path(world["contract"]).read_bytes()),
                    "contract_id": world["contract_doc"]["contract_id"],
                    "tranche_sha256": world["contract_doc"]["scope"]["tranche_sha256"],
                    "acquisition_identity": found[0].parent.name}}
    prep = base / "ap"
    bindings = {"cycle_number": 42, "attempt_number": 1,
                "population_database": {"path": str(population_db), "sha256": parent["population"]["sqlite_sha256"],
                                        "identity": parent["population"]["query_db_identity"]},
                "history_database": {"path": str(history_db), "sha256": parent["history"]["sqlite_sha256"],
                                     "identity": parent["history"]["database_identity"]},
                "source_time_database": {"path": str(st_db), "sha256": parent["source_time"]["sqlite_sha256"],
                                         "identity": parent["source_time"]["database_identity"]},
                "archive_database": {"path": str(archive_db), "sha256": parent["archive"]["sqlite_sha256"],
                                     "identity": parent["archive"]["database_identity"]},
                "archive_contract": {"path": str(world["contract"]), "sha256": parent["archive"]["contract_sha256"]},
                "archive_tranche": {"path": str(world["tranche"]), "sha256": parent["archive"]["tranche_sha256"]},
                "control": {"path": str(world["route"]), "sha256": sha(Path(world["route"]).read_bytes())}}
    bindings_path = write(prep / "INPUT_BINDINGS.json", json.dumps(bindings, indent=2).encode("utf-8"))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    for name, values in parent.items():
        contract["parent_binding"][name].update(values)
    contract["parent_binding"]["input_bindings"]["sha256"] = sha(bindings_path.read_bytes())
    contract_path = write(prep / "contract.json", (json.dumps(contract, indent=2) + "\n").encode("utf-8"))
    authority = {"contract_id": contract["contract_id"], "contract_sha256": sha(contract_path.read_bytes()),
                 "parent": parent}
    spec = {"availability": authority, "archive": json.loads(afx.authority_spec(world))}
    spec_path = write(prep / "authority.json", json.dumps(spec).encode("utf-8"))
    return {"base": base, "archive_world": world, "archive_built": built, "parent": parent,
            "paths": {"population": population_db, "history": history_db, "source_time": st_db,
                      "archive": archive_db},
            "bindings": bindings_path, "contract": contract_path, "contract_doc": contract, "authority": authority,
            "archive_authority": afx.issued_authority(world), "authority_spec": spec_path,
            "out": base / "o" / "canonical" / "national_history_availability_2019",
            "manifests": base / "o" / "manifests" / "national_history_availability_2019"}


@contextlib.contextmanager
def authorities(world: dict[str, Any]) -> Iterator[None]:
    """Both synthetic issued authorities, registered in-process for the duration of the block."""
    with archive.registered_authority(world["archive_authority"]), aq.registered_authority(world["authority"]):
        yield


def run_build(world: dict[str, Any], *extra: str, out: Path | None = None, manifests: Path | None = None,
              contract: Path | None = None, bindings: Path | None = None) -> tuple[int, dict[str, Any] | None, str]:
    argv = ["--contract", str(contract or world["contract"]), "--input-bindings", str(bindings or world["bindings"]),
            "--output-root", str(out or world["out"]), "--manifest-root", str(manifests or world["manifests"]), *extra]
    stdout, stderr = io.StringIO(), io.StringIO()
    with authorities(world), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = builder().main(argv)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


def parent_args(world: dict[str, Any]) -> list[str]:
    p = world["paths"]
    return ["--population-database", str(p["population"]), "--history-database", str(p["history"]),
            "--source-time-database", str(p["source_time"]), "--archive-database", str(p["archive"])]


def query(world: dict[str, Any], database: Path, *argv: str, parents: bool = True,
          register: bool = True) -> tuple[int, dict[str, Any] | None, str]:
    full = ["--database", str(database), *(parent_args(world) if parents else []), *argv]
    stdout, stderr = io.StringIO(), io.StringIO()
    context = authorities(world) if register else contextlib.nullcontext()
    with context, contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = aq.main(full)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


#: ``python -c BOOTSTRAP <spec json> <query argv...>``: registers both synthetic authorities in-process, then runs the
#: query module as ``__main__`` exactly as ``python -m`` does (the module-front delegation path).
BOOTSTRAP = ("import contextlib, json, runpy, sys\n"
             "from aggie_analytics.national_history import availability_query as q\n"
             "from aggie_analytics.national_source_time import archive as a\n"
             "spec = json.loads(sys.argv.pop(1))\n"
             "with contextlib.ExitStack() as stack:\n"
             "    stack.enter_context(q.registered_authority(spec['availability']))\n"
             "    arch = dict(spec['archive'])\n"
             "    data = open(arch.pop('tranche_path'), 'rb').read()\n"
             "    stack.enter_context(a.registered_authority(a.IssuedAuthority(tranche_bytes=data, **arch)))\n"
             "    sys.argv[0] = 'aggie_analytics.national_history.availability_query'\n"
             "    runpy.run_module('aggie_analytics.national_history.availability_query', run_name='__main__',"
             " alter_sys=True)\n")


def child_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), *(x for x in [env.get("PYTHONPATH")] if x)])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def refusal(stderr: str) -> str | None:
    for line in reversed(stderr.strip().splitlines()):
        try:
            return json.loads(line).get("refused")
        except ValueError:
            continue
    return None


def database_path(result: dict[str, Any]) -> Path:
    return Path(result["database"]["data_dir"]) / core.DB_FILE


def read_payload(result: dict[str, Any], name: str) -> list[dict[str, Any]]:
    data = gzip.decompress((Path(result["content"]["data_dir"]) / f"{name}.gz").read_bytes())
    return [json.loads(line) for line in data.decode("utf-8").splitlines()]


def rehashed_copy(world: dict[str, Any], result: dict[str, Any], target: Path, mutate, doc_patch=None) -> Path:
    """A semantically tampered copy of the delivered database with every outer hash, count and identity document
    consistently recomputed under ``target`` (a parallel canonical/manifests tree), so only the consumer's semantic
    re-derivation can refuse it. ``mutate(conn)`` edits the copy; ``doc_patch(document)`` edits the identity document
    consistently with a meta edit."""
    target = Path(target)
    work = target / "work.sqlite"
    work.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(database_path(result), work)
    conn = sqlite3.connect(work)
    mutate(conn)
    conn.commit()
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in core.TABLES}
    conn.close()
    manifest = json.loads(Path(result["database"]["manifest"]).read_text(encoding="utf-8"))
    document = copy.deepcopy(manifest["identity_document"])
    if doc_patch is not None:
        doc_patch(document)
    document["outputs"][core.DB_FILE] = sha(work.read_bytes())
    document["table_counts"] = counts
    identity = sha(core.canonical_json_bytes(document))
    db = target / "canonical" / core.POPULATION / "sha256" / identity / core.DB_FILE
    db.parent.mkdir(parents=True)
    os.replace(work, db)
    m = target / "manifests" / core.POPULATION / "sha256" / identity / "run_manifest.json"
    m.parent.mkdir(parents=True)
    m.write_text(json.dumps({"identity": identity, "identity_document": document}), encoding="utf-8")
    return db


def edit_record(table: str, pick, change):
    """A ``rehashed_copy`` mutation that rewrites the record JSON of the first matching row of ``table``."""
    def mutate(conn: sqlite3.Connection) -> None:
        rows = conn.execute(f"SELECT ord, record FROM {table} ORDER BY ord").fetchall()
        hit = next(((o, json.loads(r)) for o, r in rows if pick(json.loads(r))), None)
        assert hit is not None, f"no {table} row to tamper"
        conn.execute(f"UPDATE {table} SET record = ? WHERE ord = ?",
                     (core.canonical_json_bytes(change(hit[1])).decode("utf-8"), hit[0]))
    return mutate


def edit_meta(key: str, value: str):
    def mutate(conn: sqlite3.Connection) -> None:
        conn.execute("UPDATE meta SET value = ? WHERE key = ?", (value, key))
    return mutate


# --------------------------------------------------------------------------------------------- unit world

def unit_contests() -> list[dict[str, Any]]:
    """A 2019 world with every derivation case: org 1/2/3/5 FBS, 4/6 FCS.

    * ncaa:9001 (08-31) 1-4 FBS-FCS 35-10; ncaa:9002 (08-31) 2-3 a 20-20 tie (both targets' cold starts);
    * ncaa:9003 (09-07) 1-2 and ncaa:9004 (09-07) 3-5 targets; ncaa:9005 (09-07) 5-6 is Echo's same-date game;
    * ncaa:9006 (09-14) 1-3 target; ncaa:9007 (09-21) 2-5 CONFLICT (a parent-excluded prior);
    * ncaa:9008 (09-28) 2-5 target; ncaa:9009 2019-02-30 1-5 undated (excluded); ncaa:9010 (10-05) 5-1 target;
    * ncaa:9011 (10-12) 4-6 FCS-FCS (not in any FBS team's graph)."""
    c = hfx.contest
    return [c("ncaa:9001", 2019, "2019-08-31", "1", "4", 35, 10),
            c("ncaa:9002", 2019, "2019-08-31", "2", "3", 20, 20),
            c("ncaa:9003", 2019, "2019-09-07", "1", "2", 28, 21),
            c("ncaa:9004", 2019, "2019-09-07", "3", "5", 14, 17),
            c("ncaa:9005", 2019, "2019-09-07", "5", "6", 42, 7),
            c("ncaa:9006", 2019, "2019-09-14", "1", "3", 31, 10),
            c("ncaa:9007", 2019, "2019-09-21", "2", "5", None, None, status="MIRROR_DISAGREEMENT",
              competitive=False, disposition="CONFLICT", state="CONFLICT"),
            c("ncaa:9008", 2019, "2019-09-28", "2", "5", 17, 24),
            c("ncaa:9009", 2019, "2019-02-30", "1", "5", 10, 7),
            c("ncaa:9010", 2019, "2019-10-05", "5", "1", 13, 27),
            c("ncaa:9011", 2019, "2019-10-12", "4", "6", 21, 20)]


def unit_world(base: Path, contests: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    base = Path(base)
    rows = contests or unit_contests()
    parent = hfx.build_parent(base, rows)
    contract = hfx.contract_for(parent)
    contract_path = hfx.write_contract(base / "hc.json", contract)
    code, built, err = hfx.run_build(contract_path, parent, base)
    assert code == 0, err
    history_db = Path(built["database"]["data_dir"]) / "national_history.sqlite"
    pconn = sqlite3.connect(Path(parent["database"]).resolve().as_uri() + "?mode=ro", uri=True)
    population_rows, subset = core.read_population(pconn)
    pconn.close()
    hconn = sqlite3.connect(history_db.resolve().as_uri() + "?mode=ro", uri=True)
    targets, views = core.read_history(hconn)
    hconn.close()
    return {"rows": population_rows, "subset": subset, "history_targets": targets, "history_views": views}


QUAL = core.QUALIFIED


def version(capture_id: str, key: str, bound: str | None, states: dict[str, str] | None = None, *,
            state: str = "QUALIFIED", reasons: list[str] | None = None) -> dict[str, Any]:
    fields = {f: QUAL for f in core.FIELDS}
    fields["season"] = "NOT_WITNESSED_IN_VERSION"
    fields.update(states or {})
    clock = {"state": "PRESENT", "latest_utc": bound} if bound else {"state": "INVALID", "latest_utc": None}
    return {"capture_id": capture_id, "contest_key": key, "state": state, "quarantine_reasons": reasons or [],
            "clocks": {"archive_capture": clock}, "field_states": fields}


def disposition(key: str, row: dict[str, Any], name: str, outcome: str = "CAPTURED") -> dict[str, Any]:
    return {"contest_key": key, "disposition": name, "acquisition_outcome": outcome,
            "parent_values": {"season": 2019, "contest_date": row["contest_date"], "a_participant": row["a_key"],
                              "b_participant": row["b_key"], "completion": row["contest_status"],
                              "a_points": row["a_points"], "b_points": row["b_points"]}}


def unit_archive(rows: list[dict[str, Any]]) -> core.ArchiveView:
    """9001: one coherent version (bound 2019-09-01T04:15:00.999999Z); 9002: a pregame partial version then a coherent
    one (2019-09-02T10:00:00.999999Z); 9003: a coherent version plus a qualified version contradicting a score;
    9004: every version quarantined; 9006: no capture; 9007 (parent excluded): coherent; 9008: partial only."""
    by = {r["contest_key"]: r for r in rows}
    pre = {"completion": "NOT_SUPPORTED_BY_VERSION_STATUS", "a_points": "NOT_SUPPORTED_BY_VERSION_STATUS",
           "b_points": "NOT_SUPPORTED_BY_VERSION_STATUS"}
    caps = [version("wb:9001", "ncaa:9001", "2019-09-01T04:15:00.999999Z"),
            version("wb:9002a", "ncaa:9002", "2019-08-31T12:00:00.999999Z", pre),
            version("wb:9002b", "ncaa:9002", "2019-09-02T10:00:00.999999Z"),
            version("wb:9003a", "ncaa:9003", "2019-09-08T09:00:00.999999Z"),
            version("wb:9003b", "ncaa:9003", "2019-09-09T09:00:00.999999Z", {"a_points": "CONFLICTS_WITH_PARENT"}),
            version("wb:9004", "ncaa:9004", "2019-09-08T09:00:00.999999Z", {f: "CAPTURE_NOT_QUALIFIED"
                                                                           for f in core.FIELDS},
                    state="QUARANTINED", reasons=["PARTICIPANT_MAPPING_UNRESOLVED"]),
            version("wb:9007", "ncaa:9007", "2019-09-22T09:00:00.999999Z"),
            version("wb:9008", "ncaa:9008", "2019-09-27T09:00:00.999999Z", pre)]
    disp = [disposition("ncaa:9001", by["ncaa:9001"], "ARCHIVED_VERSION_QUALIFIED_ALL_WITNESSABLE_FIELDS"),
            disposition("ncaa:9002", by["ncaa:9002"], "ARCHIVED_VERSION_QUALIFIED_ALL_WITNESSABLE_FIELDS"),
            disposition("ncaa:9003", by["ncaa:9003"], "ARCHIVED_VERSION_QUALIFIED_ALL_WITNESSABLE_FIELDS"),
            disposition("ncaa:9004", by["ncaa:9004"], "ARCHIVED_VERSION_NOT_QUALIFIED"),
            disposition("ncaa:9006", by["ncaa:9006"], "NO_ARCHIVE_CAPTURE_REPORTED", "NO_ARCHIVE_CAPTURE_REPORTED"),
            disposition("ncaa:9007", by["ncaa:9007"], "ARCHIVED_VERSION_QUALIFIED_ALL_WITNESSABLE_FIELDS"),
            disposition("ncaa:9008", by["ncaa:9008"], "ARCHIVED_VERSION_QUALIFIED_PARTIAL_FIELDS")]
    assertions = [{"capture_id": c["capture_id"], "field": f, "witness": "W_" + f.upper(), "witness_span": [i, i + 2],
                   "literal": "x", "value": "x", "corroboration": "AGREES_WITH_PARENT", "field_state":
                   c["field_states"][f]} for c in caps for i, f in enumerate(core.FIELDS)]
    return core.ArchiveView(disp, caps, assertions)


def at(text: str) -> dt.datetime:
    return core.parse_cutoff(text)
