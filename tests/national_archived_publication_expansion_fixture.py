"""Synthetic expansion world for the BAT-715 archive-expansion tests (Cycle #43 TP43-A01). Not a test module.

On top of the accepted BAT-713 synthetic archive world (``national_archived_publication_fixture``: source-time parent,
route control, fake archive) with a four-key retained tranche (1001, 1002, 1005 and the control 1003) this module
finalizes the V1.2 acquisition offline (the retained acquisition), writes a synthetic missing-prior cohort -- ncaa:1002
and ncaa:1005 (also in the tranche), ncaa:1004 and ncaa:1007 (cohort only) -- with its probe timestamps, Cycle 43 style
input bindings and the committed expansion contract patched with the synthetic identities, and adds fake archive answers
for the cohort probes. Every value is fictional.

Cohort scenarios: 1004 has one version inside its probe window; 1007's first version is later than probe 1, so probe 2
finds an earlier version that is replayed too; 1005 has no capture at either probe (as in the retained acquisition);
1002's probe-1 answer names the version the retained acquisition already replayed (20190902100000): no replay.
"""
from __future__ import annotations

import contextlib
import copy
import datetime as dt
import gzip
import hashlib
import io
import json
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import national_archived_publication_fixture as apfx  # noqa: E402

EXPANSION_CONTRACT_PATH = ROOT / "configs" / "national_archived_publication_2019_expansion_contract.json"
#: the retained tranche of the expansion world (a subset of the V1.2 synthetic tranche, in its order)
TRANCHE = [row for row in apfx.TRANCHE if row[0] in ("ncaa:1001", "ncaa:1002", "ncaa:1005", "ncaa:1003")]
#: (cohort key, earliest dependent target date, dependent target keys)
COHORT = [("ncaa:1002", "2019-09-07", ["ncaa:1003"]), ("ncaa:1004", "2019-09-14", ["ncaa:1005"]),
          ("ncaa:1005", "2019-09-21", ["ncaa:1007"]), ("ncaa:1007", "2019-10-05", ["ncaa:9999"])]
COHORT_ROLE = "COHORT_MISSING_PRIOR"
COHORT_STRATUM = "COHORT_2019_09_05_TO_08_TARGET_MISSING_PRIOR"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def probes(prior_date: str, target_date: str) -> list[str]:
    """[one second before the target's conservative boundary (date 00:00 UTC minus 14 h), min(prior + 2 d, that)]."""
    boundary = dt.datetime.fromisoformat(target_date + "T00:00:00+00:00") - dt.timedelta(hours=14)
    first = boundary - dt.timedelta(seconds=1)
    second = min(dt.datetime.fromisoformat(prior_date + "T00:00:00+00:00") + dt.timedelta(days=2), first)
    return [first.strftime("%Y%m%d%H%M%S"), second.strftime("%Y%m%d%H%M%S")]


def cohort_rows(st_db: Path, tranche_keys: set[str]) -> list[dict[str, Any]]:
    import zlib  # noqa: PLC0415
    conn = sqlite3.connect(Path(st_db).resolve().as_uri() + "?mode=ro", uri=True)
    rows = []
    try:
        for key, target_date, targets in COHORT:
            record_text, blob = conn.execute("SELECT record, assertions FROM contests WHERE contest_key = ?",
                                             (key,)).fetchone()
            record = json.loads(record_text)
            values = {}
            for line in zlib.decompress(blob).decode("utf-8").splitlines():
                item = json.loads(line)
                values[item["field"]] = item["parent_value"]
            game = record["cfbd_game_id"]["value"]
            boundary = (dt.datetime.fromisoformat(target_date + "T00:00:00+00:00") - dt.timedelta(hours=14))
            rows.append({"contest_key": key, "contest_date": record["contest_date"], "a_key": record["a_key"],
                         "b_key": record["b_key"], "a_team_name": record["a_team_name"],
                         "b_team_name": record["b_team_name"], "cfbd_game_id": record["cfbd_game_id"],
                         "candidate_espn_url": apfx.game_url(game),
                         "metadata_probe_timestamps": probes(record["contest_date"], target_date),
                         "target_keys": targets,
                         "earliest_target_date_boundary": boundary.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                         "already_in_original_tranche": key in tranche_keys, "namespace_limit": "fixture",
                         "_record": record, "_values": values})
    finally:
        conn.close()
    return rows


def build_expansion_world(base: Path, scenarios: dict[str, Callable[[apfx.FakeArchive, dict[str, Any]], None]]
                          | None = None, *, v12_scenarios: dict | None = None) -> dict[str, Any]:
    """The V1.2 world with its finalized (retained) acquisition, plus the synthetic cohort, bindings and contract."""
    base = Path(base)
    world = apfx.build_world(base / "v", v12_scenarios, TRANCHE)
    retained = apfx.run_capture(world)
    assert retained["state"] == "FINALIZED", retained
    rows = cohort_rows(world["st_db"], {r["contest_key"] for r in world["rows"]})
    public = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    tranche_keys = [r["contest_key"] for r in world["rows"]]
    union = tranche_keys + [r["contest_key"] for r in rows if r["contest_key"] not in set(tranche_keys)]
    cohort = {"cycle_number": 43, "attempt_number": 1, "state": "FIXTURE", "selection": "fixture",
              "targets": [], "selected": public,
              "counts": {"targets": 4, "required_relationships": 4, "required_unique_priors": 4,
                         "new_query_keys": len(public), "keys_already_in_28_tranche": sum(
                             1 for r in public if r["already_in_original_tranche"]),
                         "union_old_and_new": len(union), "with_candidate_url": len(public)},
              "limitations": "fixture"}
    prep = base / "p43"
    cohort_path = apfx.write(prep / "ARCHIVE_COHORT.json", json.dumps(cohort, indent=2).encode("utf-8"))
    v12_bindings = json.loads(Path(world["bindings"]).read_text(encoding="utf-8"))
    bindings = {"cycle_number": 43, "attempt_number": 1, **{k: v12_bindings[k] for k in (
        "source_time_database", "tranche", "control")},
        "prior_archive_acquisition_identity": retained["acquisition_identity"],
        "expansion_cohort": {"path": str(cohort_path), "sha256": sha(cohort_path.read_bytes()),
                             "missing_prior_contests": len(public), "union_archive_contests": len(union)}}
    bindings_path = apfx.write(prep / "INPUT_BINDINGS.json", json.dumps(bindings, indent=2).encode("utf-8"))
    v12 = world["contract_doc"]
    acquisition_doc = json.loads(Path(retained["path"]).read_text(encoding="utf-8"))
    journal_dir = Path(world["out"]) / "acquisition" / "journal" / acquisition_doc["policy_id"]
    contract = json.loads(EXPANSION_CONTRACT_PATH.read_text(encoding="utf-8"))
    contract["parent_binding"]["source_time"] = copy.deepcopy(v12["parent_binding"]["source_time"])
    contract["parent_binding"]["route_control"] = copy.deepcopy(v12["parent_binding"]["route_control"])
    contract["parent_binding"]["source_bindings"]["sha256"] = sha(bindings_path.read_bytes())
    contract["parent_binding"]["retained_acquisition"].update(
        identity=retained["acquisition_identity"], policy_id=acquisition_doc["policy_id"],
        contract_id=acquisition_doc["contract_id"], contract_sha256=sha(Path(world["contract"]).read_bytes()),
        requests=len(acquisition_doc["requests"]), keys=len(acquisition_doc["keys"]),
        journal_files={p.name: sha(p.read_bytes()) for p in sorted(journal_dir.iterdir()) if p.is_file()})
    tby = {r["contest_key"]: r for r in world["rows"]}
    cby = {r["contest_key"]: r for r in rows}
    keys = []
    for key in union:
        t, c = tby.get(key), cby.get(key)
        url = (t or c)["candidate_espn_url"]
        keys.append({"contest_key": key,
                     "selection_sources": [s for s, r in (("TRANCHE_28", t), ("COHORT_70", c)) if r is not None],
                     "selection_role": t["selection_role"] if t else COHORT_ROLE,
                     "stratum": t["stratum"] if t else COHORT_STRATUM, "candidate_url": url,
                     "game_id_literal": url.rsplit("/", 1)[-1],
                     "retained_probe_1_timestamp": t["metadata_probe_timestamp"] if t else None,
                     "expansion_probe_timestamps": c["metadata_probe_timestamps"] if c else None})
    contract["scope"].update(
        tranche_sha256=sha(Path(world["tranche"]).read_bytes()), tranche_count=len(tranche_keys),
        cohort_sha256=sha(cohort_path.read_bytes()), cohort_count=len(public),
        cohort_keys=[r["contest_key"] for r in public], cohort_targets=4, cohort_relationships=4,
        union_count=len(union), overlap_keys=[r["contest_key"] for r in public if r["already_in_original_tranche"]],
        control_contest_key=v12["scope"]["control_contest_key"], keys=keys)
    contract_path = apfx.write(prep / "expansion_contract.json",
                               (json.dumps(contract, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    archive = world["archive"]
    expansion_scenarios(archive, cby)
    for key, scenario in (scenarios or {}).items():
        scenario(archive, cby[key])
    return {**world, "v12_world": world, "retained": retained, "retained_doc": acquisition_doc,
            "cohort": cohort_path, "cohort_rows": rows, "cby": cby, "x_bindings": bindings_path,
            "x_contract": contract_path, "x_contract_doc": contract, "union": union,
            "x_out": base / "x" / "canonical" / "ape", "x_manifests": base / "x" / "manifests" / "ape"}


def page(row: dict[str, Any], **kw: Any) -> bytes:
    record, values = row["_record"], row["_values"]
    return apfx.page_for({"_record": record, "a_points": values["a_points"], "b_points": values["b_points"],
                          "cfbd_game_id": record["cfbd_game_id"], "contest_date": record["contest_date"]}, **kw)


def set_version(archive: apfx.FakeArchive, row: dict[str, Any], probe: str, ts: str, body: bytes | None) -> None:
    game = row["cfbd_game_id"]["value"]
    archive.meta[(game, probe)] = ts
    if body is not None:
        archive.replay[(ts, game)] = (200, apfx.replay_headers(ts, apfx.game_url(game)), body)


def expansion_scenarios(archive: apfx.FakeArchive, cby: dict[str, dict[str, Any]]) -> None:
    r4 = cby["ncaa:1004"]
    p1, p2 = r4["metadata_probe_timestamps"]
    set_version(archive, r4, p1, "20190910020000", page(r4))
    r7 = cby["ncaa:1007"]
    p1, p2 = r7["metadata_probe_timestamps"]
    set_version(archive, r7, p1, "20191010000000", page(r7))
    set_version(archive, r7, p2, "20190922120000", page(r7))
    r5 = cby["ncaa:1005"]
    game5 = r5["cfbd_game_id"]["value"]
    for probe in r5["metadata_probe_timestamps"]:
        archive.meta[(game5, probe)] = None
    r2 = cby["ncaa:1002"]
    p1, _ = r2["metadata_probe_timestamps"]
    archive.meta[(r2["cfbd_game_id"]["value"], p1)] = "20190902100000"


def builder() -> Any:
    return apfx.builder()


EXPANSION_VALIDATOR_PATH = ROOT / "tools" / "validate_national_archived_publication_expansion.py"


def expansion_validator() -> Any:
    return apfx.stfx.load_tool(EXPANSION_VALIDATOR_PATH, "bas_archived_publication_expansion_validator")


def run_capture(world: dict[str, Any], *, transport: Any = None) -> dict[str, Any]:
    """The expansion capture stage offline: retained import, then the cohort acquisition through the fake archive."""
    build = builder()
    contract, _ = build.load_expansion_contract(world["x_contract"])
    control = build.verify_control(contract, world["route"])
    clock = {"t": 0.0}
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        clock["t"] += seconds

    def monotonic() -> float:
        clock["t"] += 0.25
        return clock["t"]

    def now() -> str:
        when = dt.datetime(2026, 10, 5, 21, 0, tzinfo=dt.timezone.utc) + dt.timedelta(seconds=clock["t"])
        return when.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    retained = build.import_retained(contract, world["out"], world["x_out"])
    result = build.capture_expansion(contract, world["x_out"], control, retained["document"],
                                     transport=transport or world["archive"], sleep=sleep, monotonic=monotonic,
                                     now=now, audit=False)
    result["slept"] = slept
    result["retained_import"] = {k: v for k, v in retained.items() if k != "document"}
    return result


def run_build(world: dict[str, Any], *extra: str, out: Path | None = None, manifests: Path | None = None,
              contract: Path | None = None, cohort: Path | None = None, tranche: Path | None = None,
              bindings: Path | None = None) -> tuple[int, dict[str, Any] | None, str]:
    argv = ["--contract", str(contract or world["x_contract"]), "--source-database", str(world["st_db"]),
            "--source-bindings", str(bindings or world["x_bindings"]), "--tranche", str(tranche or world["tranche"]),
            "--cohort", str(cohort or world["cohort"]), "--output-root", str(out or world["x_out"]),
            "--manifest-root", str(manifests or world["x_manifests"]), *extra]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = builder().main(argv)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


def expansion_acquisition(world: dict[str, Any]) -> Path:
    contract = json.loads(Path(world["x_contract"]).read_text(encoding="utf-8"))
    retained = contract["parent_binding"]["retained_acquisition"]["identity"]
    found = [p for p in sorted(Path(world["x_out"]).glob("acquisition/sha256/*/acquisition.json"))
             if p.parent.name != retained]
    assert len(found) == 1, found
    return found[0]


def issued_authority(world: dict[str, Any]) -> Any:
    """The synthetic expansion authority for in-process registration with ``archive.registered_authority``."""
    from aggie_analytics.national_source_time import archive  # noqa: PLC0415

    contract = world["x_contract_doc"]
    route = contract["parent_binding"]["route_control"]
    parent = contract["parent_binding"]["source_time"]
    retained = contract["parent_binding"]["retained_acquisition"]
    return archive.ExpansionAuthority(
        contract_id=contract["contract_id"], contract_sha256=sha(Path(world["x_contract"]).read_bytes()),
        tranche_bytes=Path(world["tranche"]).read_bytes(), tranche_sha256=contract["scope"]["tranche_sha256"],
        cohort_bytes=Path(world["cohort"]).read_bytes(), cohort_sha256=contract["scope"]["cohort_sha256"],
        acquisition_identity=expansion_acquisition(world).parent.name,
        retained_acquisition_identity=retained["identity"], retained_policy_id=retained["policy_id"],
        parent={"source_time": {k: parent[k] for k in ("content_identity", "contract_sha256", "database_identity",
                                                        "sqlite_sha256")}},
        control={"contest_key": route["contest_key"], "payload_sha256": route["raw_payload_sha256"],
                 "raw_receipt_sha256": route["raw_receipt_sha256"], "route_qualification_sha256": route["sha256"]})


def authority_spec(world: dict[str, Any]) -> str:
    authority = issued_authority(world)
    return json.dumps({"contract_id": authority.contract_id, "contract_sha256": authority.contract_sha256,
                       "tranche_path": str(world["tranche"]), "tranche_sha256": authority.tranche_sha256,
                       "cohort_path": str(world["cohort"]), "cohort_sha256": authority.cohort_sha256,
                       "acquisition_identity": authority.acquisition_identity,
                       "retained_acquisition_identity": authority.retained_acquisition_identity,
                       "retained_policy_id": authority.retained_policy_id, "parent": authority.parent,
                       "control": authority.control})


#: ``python -c BOOTSTRAP <authority json> <query argv...>``: registers the synthetic expansion authority in-process,
#: then runs the source-time query module as ``__main__`` exactly as ``python -m`` does.
BOOTSTRAP = ("import json, runpy, sys\n"
             "from aggie_analytics.national_source_time import archive\n"
             "spec = json.loads(sys.argv.pop(1))\n"
             "tranche = open(spec.pop('tranche_path'), 'rb').read()\n"
             "cohort = open(spec.pop('cohort_path'), 'rb').read()\n"
             "with archive.registered_authority(archive.ExpansionAuthority(tranche_bytes=tranche, cohort_bytes=cohort,"
             " **spec)):\n"
             "    sys.argv[0] = 'aggie_analytics.national_source_time.query'\n"
             "    runpy.run_module('aggie_analytics.national_source_time.query', run_name='__main__', alter_sys=True)\n")


def read_payload(result: dict[str, Any], name: str) -> list[dict[str, Any]]:
    data = gzip.decompress((Path(result["content"]["data_dir"]) / f"{name}.gz").read_bytes())
    return [json.loads(line) for line in data.decode("utf-8").splitlines()]


def database_path(result: dict[str, Any]) -> Path:
    return Path(result["database"]["data_dir"]) / "national_archived_publication.sqlite"


def rehouse(world: dict[str, Any], result: dict[str, Any], base: Path, *, mutate_rows=None, mutate_meta=None,
            mutate_raw=None, mutate_document=None, mutate_conn=None) -> Path:
    """Copy the expansion root, tamper with the sidecar and recompute every outer hash (identity document, bytes,
    counts) so that only semantic verification can refuse it. ``mutate_rows(table, record)`` may return "DELETE"."""
    root = base / "canonical" / "ape"
    shutil.copytree(world["x_out"], root)
    (base / "manifests").mkdir(parents=True)
    shutil.copytree(world["x_manifests"], base / "manifests" / "ape")
    db_id = result["database_identity"]
    work = base / "work.sqlite"
    shutil.copyfile(root / "sha256" / db_id / "national_archived_publication.sqlite", work)
    conn = sqlite3.connect(work)
    if mutate_rows:
        for table in ("dispositions", "requests", "captures", "assertions"):
            rows = [(o, json.loads(r)) for o, r in conn.execute(f"SELECT ord, record FROM {table} ORDER BY ord")]
            for ordinal, record in rows:
                changed = mutate_rows(table, record)
                if changed == "DELETE":
                    conn.execute(f"DELETE FROM {table} WHERE ord = ?", (ordinal,))
                elif changed is not None:
                    conn.execute(f"UPDATE {table} SET record = ? WHERE ord = ?",
                                 (json.dumps(changed, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                                  ordinal))
    if mutate_meta:
        for key, value in mutate_meta.items():
            conn.execute("UPDATE meta SET value = ? WHERE key = ?", (value, key))
    if mutate_conn:
        mutate_conn(conn)
    conn.commit()
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("meta", "dispositions", "requests", "captures", "assertions")}
    conn.close()
    if mutate_raw:
        mutate_raw(root)
    manifest = json.loads((base / "manifests" / "ape" / "sha256" / db_id / "run_manifest.json").read_text(
        encoding="utf-8"))
    document = manifest["identity_document"]
    document["outputs"]["national_archived_publication.sqlite"] = sha(work.read_bytes())
    document["table_counts"] = counts
    document["record_counts"] = {name: counts[name.split(".")[0]] for name in document["record_counts"]}
    if mutate_document:
        mutate_document(document)
    identity = sha(json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    target = root / "sha256" / identity / "national_archived_publication.sqlite"
    if target.is_file():
        return target
    target.parent.mkdir(parents=True)
    shutil.move(str(work), target)
    apfx.write(base / "manifests" / "ape" / "sha256" / identity / "run_manifest.json",
               json.dumps({"identity": identity, "identity_document": document}).encode("utf-8"))
    return target
