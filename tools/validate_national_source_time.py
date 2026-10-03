r"""Independent validator for the national 2016-2023 source-time evidence delivery (BAT-712, Cycle #40 TP40-A01).

``python -B tools/validate_national_source_time.py --contract configs/national_source_time_2016_2023_contract.json
--history-database <bound history sqlite> --population-database <bound population sqlite>
--source-bindings <INPUT_BINDINGS.json> --manifest <manifests/.../sha256/<content id>/run_manifest.json>
--report <new report path>``

Standard library plus ``duckdb`` (Parquet reads). It imports no producer, query or project code. It re-verifies every
binding from the files themselves, enumerates the universe and every relation from the accepted history database with
its own SQL, rereads every page observation, bound NCAA manifest capture, CFBD route row, cycle30 ledger entry, CFBD
request receipt, repository manifest, commit API response and Parquet row, and rebuilds every partition, contest,
capture (with all clocks), lineage row, repository join disposition, assertion and relation. Each delivered record is
compared field by field with its reconstruction by natural key; identities and every database record are recomputed.
Cutoff decisions are recomputed for every universe contest at probe cutoffs and compared with the delivered query
consumer (run as a subprocess), plus assertion and contribution samples. A raw NCAA page sample, coordinated semantic
tamper cases and oracle self-challenges are reported with their limits. The report is a new file written once.
Exit 0 only when every check passes.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import gzip
import hashlib
import html
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

UTCZ = dt.timezone.utc
FIELD_LIST = ["season", "contest_date", "a_participant", "b_participant", "completion", "a_points", "b_points"]
OUTCOME = {"completion", "a_points", "b_points"}
TARGET_ONLY = ["season", "contest_date", "a_participant", "b_participant"]
KINDS = ["NCAA_TEAM_SEASON_PAGE", "CFBD_ROUTE_RESPONSE", "REPOSITORY_VERSION"]
FILES = ["partition.jsonl", "contests.jsonl", "assertions.jsonl", "lineage_rows.jsonl", "repository_rows.jsonl",
         "captures.jsonl", "relations.jsonl"]
PROBE_CUTOFFS = ["2016-08-01T00:00:00Z", "2023-05-06T07:42:42Z", "2026-08-09T18:59:48Z", "2026-08-09T18:59:49Z",
                 "2026-08-13T10:39:56Z", "2026-08-13T05:39:56-05:00", "2026-10-02T00:00:00Z"]


def h_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def h_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            block = stream.read(1 << 20)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def cjson(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class Report:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def check(self, name: str, ok: bool, detail: Any = None) -> bool:
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    @property
    def failed(self) -> list[str]:
        return [c["check"] for c in self.checks if not c["ok"]]


# --------------------------------------------------------------------------------------------- independent clocks

INSTANT = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$")
MINUTE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(Z|[+-]\d{2}:\d{2})$")
NAIVE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$")
USDATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
ISODATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def tz_of(text: str) -> dt.timezone:
    if text == "Z":
        return UTCZ
    offset = dt.timedelta(hours=int(text[1:3]), minutes=int(text[4:6]))
    if int(text[1:3]) > 14 or int(text[4:6]) > 59:
        raise ValueError("offset")
    return dt.timezone(offset if text[0] == "+" else -offset)


def z(value: dt.datetime) -> str:
    return value.astimezone(UTCZ).isoformat(timespec="microseconds").replace("+00:00", "Z")


def calendar_day(text: Any) -> dt.date | None:
    if not isinstance(text, str):
        return None
    try:
        m = USDATE.match(text)
        if m:
            return dt.date(int(m[3]), int(m[1]), int(m[2]))
        m = ISODATE.match(text)
        if m:
            day = dt.date(int(m[1]), int(m[2]), int(m[3]))
            return day if day.isoformat() == text else None
    except ValueError:
        return None
    return None


def expect_clock(literal: Any, role: str | None, document: str | None, pointer: str | None, *,
                 start: Any = None, local_date: bool = False) -> dict[str, Any]:
    """The contract's clock parsing rules, written independently."""
    base = {"state": "PRESENT", "role": role, "literal": literal, "start_literal": start, "zone": None,
            "precision": None, "earliest_utc": None, "latest_utc": None, "evidence_document": document,
            "evidence_pointer": pointer, "reason": None}

    def spelled(v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, bool):
            return "true" if v else "false"
        return repr(v) if isinstance(v, float) else str(v)

    def interval(text: Any) -> tuple[str, str | None, str, str]:
        if not isinstance(text, str):
            raise ValueError("NOT_A_STRING")
        m = INSTANT.match(text)
        if m:
            frac = m[7] or ""
            moment = dt.datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), int(m[6]),
                                 int(frac[1:].ljust(6, "0")) if frac else 0, tzinfo=tz_of(m[8]))
            digits = len(frac) - 1 if frac else 0
            return ("second" if digits == 0 else "millisecond" if digits <= 3 else "microsecond"), m[8], z(moment), \
                z(moment)
        m = MINUTE.match(text)
        if m:
            moment = dt.datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), tzinfo=tz_of(m[6]))
            return "minute", m[6], z(moment), z(moment + dt.timedelta(minutes=1) - dt.timedelta(microseconds=1))
        if local_date and calendar_day(text):
            day = calendar_day(text)
            lo = dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone(dt.timedelta(hours=-4)))
            hi = dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone(dt.timedelta(hours=-10))) + \
                dt.timedelta(days=1) - dt.timedelta(microseconds=1)
            return "date", None, z(lo), z(hi)
        if NAIVE.match(text):
            raise ValueError("NAIVE_TIMESTAMP_REFUSED")
        raise ValueError("TIMESTAMP_MALFORMED")
    try:
        precision, zone, lo, hi = interval(literal)
        if start is not None:
            lo = interval(start)[2]
            if lo > hi:
                base.update(state="INVALID", reason="START_AFTER_COMPLETION", literal=spelled(literal),
                            start_literal=spelled(start))
                return base
    except ValueError as exc:
        base.update(state="ABSENT" if literal is None else "INVALID", literal=spelled(literal),
                    start_literal=spelled(start), reason="LITERAL_ABSENT" if literal is None else str(exc))
        return base
    base.update(zone=zone, precision=precision, earliest_utc=lo, latest_utc=hi)
    return base


def stated(state: str, reason: str, role: str | None = None) -> dict[str, Any]:
    return {"state": state, "role": role, "literal": None, "start_literal": None, "zone": None, "precision": None,
            "earliest_utc": None, "latest_utc": None, "evidence_document": None, "evidence_pointer": None,
            "reason": reason}


def us_local_dates(clock: dict[str, Any]) -> list[str]:
    if clock["state"] != "PRESENT" or clock["precision"] == "date":
        return []
    dates = set()
    for bound in (clock["earliest_utc"], clock["latest_utc"]):
        moment = dt.datetime.fromisoformat(bound.replace("Z", "+00:00"))
        for hours in (4, 10):
            dates.add((moment - dt.timedelta(hours=hours)).date().isoformat())
    return sorted(dates)


def spell(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    return repr(v) if isinstance(v, float) else str(v)


def as_count(v: Any) -> tuple[int | None, str]:
    """Contract value rule for scores/ids: integral spellings normalize, everything else is MALFORMED or NULL."""
    if v is None:
        return None, "NULL"
    if isinstance(v, bool):
        return None, "MALFORMED"
    if isinstance(v, int):
        return (v, "OK") if v >= 0 else (None, "MALFORMED")
    if isinstance(v, float):
        return (int(v), "OK") if v >= 0 and float(int(v)) == v else (None, "MALFORMED")
    if isinstance(v, str) and v == v.strip():
        if re.fullmatch(r"\d{1,12}", v):
            return int(v), "OK"
        m = re.fullmatch(r"(\d{1,12})\.0+", v)
        if m:
            return int(m[1]), "OK"
    return None, "MALFORMED"


# --------------------------------------------------------------------------------------------- bindings

def identity_doc(manifest: Path, expected: str, report: Report, name: str) -> dict[str, Any] | None:
    try:
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        ok = h_bytes(cjson(doc["identity_document"])) == expected == doc.get("identity")
    except Exception as exc:  # noqa: BLE001 - recorded
        report.check(name, False, f"{type(exc).__name__}: {exc}")
        return None
    report.check(name, ok, {"manifest": str(manifest), "expected": expected})
    return doc["identity_document"] if ok else None


def manifest_of(path: Path) -> Path:
    path = path.resolve()
    return path.parents[4] / "manifests" / path.parents[2].name / "sha256" / path.parent.name / "run_manifest.json"


def verify_bindings(contract: dict[str, Any], args: argparse.Namespace, report: Report) -> dict[str, Any]:
    pb = contract["parent_binding"]
    pop, hist = pb["population"], pb["history"]
    pdb, hdb = Path(args.population_database), Path(args.history_database)
    data = pdb.resolve().parents[4]
    report.check("population_file_and_hash", pdb.resolve().parent.name == pop["query_db_identity"] and
                 h_file(pdb) == pop["sqlite_sha256"])
    pdoc = identity_doc(manifest_of(pdb), pop["query_db_identity"], report, "population_manifest_identity") or {}
    report.check("population_manifest_fields", pdoc.get("stage") == "query-db" and
                 pdoc.get("contract_sha256") == pop["contract_sha256"] and
                 (pdoc.get("upstream") or {}).get("contest") == pop["contest_identity"] and
                 (pdoc.get("upstream") or {}).get("program-season") == pop["program_season_identity"])
    stage_dirs = {}
    for stage, ident, files in (("contest", pop["contest_identity"], pop["contest_stage_files"]),
                                ("program-season", pop["program_season_identity"], pop["program_season_stage_files"])):
        folder = pdb.resolve().parents[1] / ident
        sdoc = identity_doc(manifest_of(folder / "x"), ident, report, f"{stage}_stage_identity") or {}
        report.check(f"{stage}_stage_files", sdoc.get("stage") == stage and all(
            (sdoc.get("outputs") or {}).get(n) == s and h_file(folder / n) == s for n, s in files.items()))
        stage_dirs[stage] = folder
    report.check("history_file_and_hash", hdb.resolve().parent.name == hist["database_identity"] and
                 h_file(hdb) == hist["sqlite_sha256"])
    hdoc = identity_doc(manifest_of(hdb), hist["database_identity"], report, "history_manifest_identity") or {}
    report.check("history_manifest_fields", hdoc.get("content_identity") == hist["content_identity"] and
                 hdoc.get("contract_sha256") == hist["contract_sha256"] and
                 (hdoc.get("outputs") or {}).get("national_history.sqlite") == hist["sqlite_sha256"])
    con = sqlite3.connect(f"file:{hdb.resolve().as_posix()}?mode=ro", uri=True)
    hmeta = dict(con.execute("SELECT key, value FROM meta"))
    con.close()
    hparent = json.loads(hmeta.get("parent") or "{}")
    report.check("history_parent_is_bound_population", hparent.get("query_db_identity") == pop["query_db_identity"] and
                 hparent.get("sqlite_sha256") == pop["sqlite_sha256"] and
                 hparent.get("contest_identity") == pop["contest_identity"])
    sb = json.loads(Path(args.source_bindings).read_text(encoding="utf-8"))
    pre_path = Path(sb["source_preflight"]["path"])
    report.check("source_bindings_agree", sb["history_database"]["sha256"] == hist["sqlite_sha256"] and
                 sb["population_database"]["sha256"] == pop["sqlite_sha256"] and
                 sb["parent_delivery_manifest"]["sha256"] == pb["delivery_manifest"]["sha256"] and
                 sb["source_preflight"]["sha256"] == pb["source_bindings"]["cache_preflight_sha256"] ==
                 h_file(pre_path))
    report.check("delivery_manifest_hash", h_file(data / pb["delivery_manifest"]["path"]) ==
                 pb["delivery_manifest"]["sha256"])
    su = contract["source_universe"]
    bad = []
    for v in su["repository_versions"]:
        for rel, sha in ((v["manifest"], v["manifest_sha256"]), (v["payload"], v["payload_sha256"]),
                         (v["commit_api"], v["commit_api_sha256"])):
            if h_file(data / rel) != sha:
                bad.append(rel)
        blob = (data / v["payload"]).read_bytes()
        api = json.loads((data / v["commit_api"]).read_text(encoding="utf-8"))
        entry = [f for f in api["files"] if f["filename"] == v["source_path"]]
        if not entry or entry[0]["sha"] != hashlib.sha1(b"blob " + str(len(blob)).encode() + b"\0" + blob).hexdigest() \
                or api["sha"] != v["commit_sha"]:
            bad.append("blob:" + v["payload"])
    for s, spec in su["cfbd_fbs_route"].items():
        if h_file(data / spec["raw"]) != spec["sha256"] or h_file(data / spec["receipt"]) != spec["receipt_sha256"]:
            bad.append(spec["raw"])
    for s, spec in su["cfbd_fcs_route"].items():
        if h_file(data / spec["raw"]) != spec["sha256"]:
            bad.append(spec["raw"])
    if h_file(data / su["cycle30_ledger"]["path"]) != su["cycle30_ledger"]["sha256"]:
        bad.append("ledger")
    for s, spec in su["ncaa_bound_manifests"].items():
        if h_file(data / spec["manifest"]) != spec["sha256"]:
            bad.append(spec["manifest"])
    report.check("every_source_file_hash_and_git_blob_binding", not bad, bad[:10])
    preflight = json.loads(pre_path.read_text(encoding="utf-8"))
    report.check("repository_versions_equal_cache_preflight",
                 sorted((c["season"], c["payload_sha256"], c["rows"]) for c in preflight["captures"]) ==
                 sorted((v["season"], v["payload_sha256"], v["rows"]) for v in su["repository_versions"]))
    return {"data": data, "stage_dirs": stage_dirs, "universe_sha256": h_bytes(cjson(su))}


# --------------------------------------------------------------------------------------------- expected records

def load_parent(args: argparse.Namespace, ctx: dict[str, Any]) -> dict[str, Any]:
    con = sqlite3.connect(f"file:{Path(args.history_database).resolve().as_posix()}?mode=ro", uri=True)
    targets = con.execute("SELECT contest_key FROM targets ORDER BY ord").fetchall()
    exclusions = {k for (k,) in con.execute("SELECT contest_key FROM exclusions")}
    views = [(k, v, s, d, t, o, json.loads(r)) for k, v, s, d, t, o, r in con.execute(
        "SELECT target_contest_key, view, season, target_date, team_key, opponent_key, record FROM history ORDER BY ord")]
    con.close()
    con = sqlite3.connect(f"file:{Path(args.population_database).resolve().as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    census = [(r["contest_key"], r["season"]) for r in con.execute("SELECT contest_key, season FROM contest")]
    parent = {r["contest_key"]: dict(r) for r in con.execute(
        "SELECT contest_key, ncaa_contest_id, season, term, contest_date, site, contest_status, a_org_id, b_org_id, "
        "a_team_name, b_team_name, a_points, b_points, a_key, b_key, cfbd_game_ids FROM contest "
        "WHERE season BETWEEN 2016 AND 2023")}
    con.close()
    stage = {}
    with gzip.open(ctx["stage_dirs"]["contest"] / "contests.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("season") in range(2016, 2024):
                stage[r["contest_key"]] = r
    pages = defaultdict(list)
    with gzip.open(ctx["stage_dirs"]["program-season"] / "page_observations.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("season") in range(2016, 2024) and r.get("ncaa_contest_id"):
                pages[(r["ncaa_contest_id"], r["season"])].append(r)
    return {"targets": [k for (k,) in targets], "exclusions": exclusions, "views": views, "census": census,
            "parent": parent, "stage": stage, "pages": pages}


class Expected:
    """Independent reconstruction of every delivered record, keyed by natural key."""

    def __init__(self, contract: dict[str, Any], ctx: dict[str, Any], P: dict[str, Any]) -> None:
        self.c, self.ctx, self.P = contract, ctx, P
        self.data = ctx["data"]
        su = contract["source_universe"]
        self.role: dict[str, set[str]] = defaultdict(set)
        for k in P["targets"]:
            self.role[k].add("TARGET")
        for _k, _v, _s, _d, _t, _o, rec in P["views"]:
            for side in ("team_history", "opponent_history"):
                for item in rec[side]["contributing"]:
                    self.role[item["contest_key"]].add("CONTRIBUTOR")
        self.universe = sorted(self.role, key=lambda k: (P["parent"][k]["season"], P["parent"][k]["contest_date"], k))
        self.ncaa: dict[str, list[tuple[str, int, dict[str, Any], int, dict[str, Any]]]] = defaultdict(list)
        for season, spec in su["ncaa_bound_manifests"].items():
            doc = json.loads((self.data / spec["manifest"]).read_text(encoding="utf-8"))
            stamp_count = Counter(c.get("retrieved_at_utc") for c in doc["captures"])
            for i, cap in enumerate(doc["captures"]):
                self.ncaa[cap["raw_sha256"]].append((season, i, cap, stamp_count[cap.get("retrieved_at_utc")], spec))
        self.routes: dict[tuple[str, int], dict[str, list[dict[str, Any]]]] = {}
        self.route_meta: dict[tuple[str, int], dict[str, Any]] = {}
        ledger = json.loads((self.data / su["cycle30_ledger"]["path"]).read_text(encoding="utf-8"))["attempts"]
        self.ledger = ledger
        for season, spec in su["cfbd_fbs_route"].items():
            rows = json.loads((self.data / spec["raw"]).read_text(encoding="utf-8"))
            idx = defaultdict(list)
            for r in rows:
                idx[spell(r.get("id"))].append(r)
            self.routes[("SRC-002", int(season))] = idx
            self.route_meta[("SRC-002", int(season))] = {"spec": spec, "receipt": json.loads(
                (self.data / spec["receipt"]).read_text(encoding="utf-8"))}
        for season, spec in su["cfbd_fcs_route"].items():
            rows = json.loads((self.data / spec["raw"]).read_text(encoding="utf-8"))
            idx = defaultdict(list)
            for r in rows:
                idx[spell(r.get("id"))].append(r)
            self.routes[("CYCLE30_FCS", int(season))] = idx
            self.route_meta[("CYCLE30_FCS", int(season))] = {"spec": spec, "entries": [
                (i, a) for i, a in enumerate(ledger) if a.get("raw_sha256") == spec["sha256"]]}
        self.records: dict[str, dict[tuple, dict[str, Any]]] = {f: {} for f in FILES}
        self.order: dict[str, list[tuple]] = {f: [] for f in FILES}
        self.captures: dict[str, dict[str, Any]] = {}

    def put(self, file: str, key: tuple, record: dict[str, Any]) -> None:
        if key in self.records[file]:
            raise ValueError(f"duplicate expected key {file} {key}")
        self.records[file][key] = record
        self.order[file].append(key)

    # captures --------------------------------------------------------------------------------------------
    def cap_ncaa(self, raw: str) -> dict[str, Any]:
        cid = "ncaa_page:" + raw
        if cid in self.captures:
            return self.captures[cid]
        hits = sorted(self.ncaa.get(raw, []), key=lambda x: (x[0], x[1]))
        na = stated("NOT_APPLICABLE", "NOT_A_REPOSITORY_VERSION")
        pub = stated("ABSENT", "NO_QUALIFIED_INDEPENDENT_PUBLICATION_EVIDENCE")
        cor = stated("ABSENT", "SINGLE_RETAINED_REVISION_NO_CORRECTION_OBSERVED")
        if not hits:
            rec = {"record_type": "capture", "capture_id": cid, "source_kind": "NCAA_TEAM_SEASON_PAGE", "route": None,
                   "season": None, "source_uri": None, "payload_path": None, "payload_sha256": raw,
                   "source_revision": raw, "byte_binding": "NOT_VERIFIED_NO_CAPTURE", "receipt_document": None,
                   "receipt_document_sha256": None, "receipt_pointer": None, "receipt_stamp_shared_by": 0,
                   "time_evidence_class": "NO_RECEIPT",
                   "clocks": {"retrieval": stated("ABSENT", "NCAA_CAPTURE_NOT_IN_BOUND_MANIFEST",
                                                  "RECORDED_POSSESSION_UPPER_BOUND"),
                              "asserted_commit_author": na, "asserted_commit_committer": na,
                              "supported_publication": pub, "correction": cor}}
        else:
            season, i, cap, shared, spec = hits[0]
            stamps = sorted({str(h[2].get("retrieved_at_utc")) for h in hits})
            if len(stamps) > 1:
                retrieval = stated("CONTRADICTORY", "RECEIPT_TIMES_CONTRADICTORY", "RECORDED_POSSESSION_UPPER_BOUND")
                retrieval.update(literal="|".join(stamps), evidence_document=spec["manifest"],
                                 evidence_pointer="|".join(f"/captures/{h[1]}/retrieved_at_utc" for h in hits))
            else:
                retrieval = expect_clock(cap.get("retrieved_at_utc"), "RECORDED_POSSESSION_UPPER_BOUND",
                                         spec["manifest"], f"/captures/{i}/retrieved_at_utc")
            rel = cap.get("raw_relative_path")
            raw_path = self.data / rel if rel else None
            verified = bool(raw_path) and raw_path.name == raw + ".html" and raw_path.is_file() and h_file(raw_path) == raw
            rec = {"record_type": "capture", "capture_id": cid, "source_kind": "NCAA_TEAM_SEASON_PAGE", "route": None,
                   "season": int(season), "source_uri": cap.get("source_uri"), "payload_path": rel,
                   "payload_sha256": raw, "source_revision": raw,
                   "byte_binding": "RAW_SHA256_VERIFIED" if verified else "RAW_BYTES_MISSING_OR_DIFFERENT",
                   "receipt_document": spec["manifest"], "receipt_document_sha256": spec["sha256"],
                   "receipt_pointer": f"/captures/{i}", "receipt_stamp_shared_by": shared,
                   "time_evidence_class": "RECORDED_RETRIEVAL_STAMP_ONLY" if retrieval["state"] == "PRESENT"
                   else "NO_RECEIPT",
                   "clocks": {"retrieval": retrieval, "asserted_commit_author": na, "asserted_commit_committer": na,
                              "supported_publication": pub, "correction": cor}}
        self.captures[cid] = rec
        return rec

    def cap_route(self, route: str, season: int) -> dict[str, Any]:
        meta = self.route_meta[(route, season)]
        spec = meta["spec"]
        cid = f"cfbd_route:{route}:{season}:{spec['sha256']}"
        if cid in self.captures:
            return self.captures[cid]
        clocks = {"asserted_commit_author": stated("NOT_APPLICABLE", "NOT_A_REPOSITORY_VERSION"),
                  "asserted_commit_committer": stated("NOT_APPLICABLE", "NOT_A_REPOSITORY_VERSION"),
                  "supported_publication": stated("ABSENT", "NO_QUALIFIED_INDEPENDENT_PUBLICATION_EVIDENCE"),
                  "correction": stated("ABSENT", "SINGLE_RETAINED_REVISION_NO_CORRECTION_OBSERVED")}
        if route == "SRC-002":
            rcp = meta["receipt"]
            clocks["retrieval"] = expect_clock(rcp.get("retrieved_at_utc"), "EXACT_REQUEST_INTERVAL", spec["receipt"],
                                               "/retrieved_at_utc", start=rcp.get("retrieval_started_at_utc"))
            rec = {"record_type": "capture", "capture_id": cid, "source_kind": "CFBD_ROUTE_RESPONSE", "route": route,
                   "season": season, "source_uri": rcp.get("source_uri"), "payload_path": spec["raw"],
                   "payload_sha256": spec["sha256"], "source_revision": spec["sha256"],
                   "byte_binding": "RESPONSE_SHA256_MATCHES_RECEIPT", "receipt_document": spec["receipt"],
                   "receipt_document_sha256": spec["receipt_sha256"], "receipt_pointer": "",
                   "receipt_stamp_shared_by": 1,
                   "time_evidence_class": "EXACT_REQUEST_RECEIPT_ONLY" if clocks["retrieval"]["state"] == "PRESENT"
                   else "NO_RECEIPT"}
        else:
            entries = meta["entries"]
            led = self.c["source_universe"]["cycle30_ledger"]
            if entries:
                cache = all(a.get("status") == "CACHE_HIT" for _i, a in entries)
                role = "CACHE_HIT_POSSESSION_UPPER_BOUND" if cache else "RECORDED_POSSESSION_UPPER_BOUND"
                stamps = sorted({str(a.get("retrieved_at_utc")) for _i, a in entries})
                if len(stamps) > 1:
                    r = stated("CONTRADICTORY", "RECEIPT_TIMES_CONTRADICTORY", role)
                    r.update(literal="|".join(stamps), evidence_document=led["path"],
                             evidence_pointer="|".join(f"/attempts/{i}/retrieved_at_utc" for i, _a in entries))
                    clocks["retrieval"] = r
                else:
                    clocks["retrieval"] = expect_clock(entries[0][1].get("retrieved_at_utc"), role, led["path"],
                                                       f"/attempts/{entries[0][0]}/retrieved_at_utc")
                shared = sum(1 for a in self.ledger if a.get("retrieved_at_utc") == entries[0][1].get("retrieved_at_utc"))
            else:
                clocks["retrieval"] = stated("ABSENT", "LEDGER_ENTRY_ABSENT", "CACHE_HIT_POSSESSION_UPPER_BOUND")
                shared = 0
            present = clocks["retrieval"]["state"] == "PRESENT"
            rec = {"record_type": "capture", "capture_id": cid, "source_kind": "CFBD_ROUTE_RESPONSE", "route": route,
                   "season": season, "source_uri": f"cfbd:/games?classification=fcs&year={season}",
                   "payload_path": spec["raw"], "payload_sha256": spec["sha256"], "source_revision": spec["sha256"],
                   "byte_binding": "CONTENT_SHA256_MATCHES_LEDGER_RAW_SHA256" if entries else "CONTENT_SHA256_ONLY",
                   "receipt_document": led["path"] if entries else None,
                   "receipt_document_sha256": led["sha256"] if entries else None,
                   "receipt_pointer": f"/attempts/{entries[0][0]}" if entries else None,
                   "receipt_stamp_shared_by": shared,
                   "time_evidence_class": ("CACHE_HIT_RECEIPT_ONLY" if present and clocks["retrieval"]["role"] ==
                                           "CACHE_HIT_POSSESSION_UPPER_BOUND" else
                                           "RECORDED_RETRIEVAL_STAMP_ONLY" if present else "NO_RECEIPT")}
        rec["clocks"] = clocks
        self.captures[cid] = rec
        return rec

    # repository rows --------------------------------------------------------------------------------------
    def repository(self) -> dict[str, list[dict[str, Any]]]:
        import duckdb  # noqa: PLC0415 - Parquet reads only

        su = self.c["source_universe"]
        cfbd = defaultdict(list)
        for k, row in self.P["parent"].items():
            for g in json.loads(row["cfbd_game_ids"] or "[]"):
                cfbd[str(g)].append(k)
        stamps = Counter(json.loads((self.data / v["manifest"]).read_text(encoding="utf-8")).get("acquired_at_utc")
                         for v in su["repository_versions"])
        cols = ["id", "game_id", "season", "start_date", "home_id", "away_id", "home_score", "away_score",
                "status_type_completed", "status_type_name", "neutral_site", "home_location", "away_location"]
        joined: dict[str, list[dict[str, Any]]] = defaultdict(list)
        con = duckdb.connect()
        for v in sorted(su["repository_versions"], key=lambda x: x["season"]):
            man = json.loads((self.data / v["manifest"]).read_text(encoding="utf-8"))
            api = json.loads((self.data / v["commit_api"]).read_text(encoding="utf-8"))
            cid = "repo_version:" + v["capture_id"]
            ret = expect_clock(man.get("acquired_at_utc"), "RECORDED_POSSESSION_UPPER_BOUND", v["manifest"],
                               "/acquired_at_utc")
            self.captures[cid] = {
                "record_type": "capture", "capture_id": cid, "source_kind": "REPOSITORY_VERSION",
                "route": v["repository"], "season": v["season"], "source_uri": man.get("source_url"),
                "payload_path": v["payload"], "payload_sha256": v["payload_sha256"], "source_revision": v["commit_sha"],
                "byte_binding": "GIT_BLOB_SHA1_MATCHES_COMMIT_FILE_ENTRY", "receipt_document": v["manifest"],
                "receipt_document_sha256": v["manifest_sha256"], "receipt_pointer": "",
                "receipt_stamp_shared_by": stamps[man.get("acquired_at_utc")],
                "time_evidence_class": "RECORDED_RETRIEVAL_STAMP_WITH_ASSERTED_COMMIT_TIME"
                if ret["state"] == "PRESENT" else "NO_RECEIPT",
                "clocks": {"retrieval": ret,
                           "asserted_commit_author": expect_clock(api["commit"]["author"]["date"], "SOURCE_ASSERTED",
                                                                  v["commit_api"], "/commit/author/date"),
                           "asserted_commit_committer": expect_clock(api["commit"]["committer"]["date"],
                                                                     "SOURCE_ASSERTED", v["commit_api"],
                                                                     "/commit/committer/date"),
                           "supported_publication": stated("ABSENT", "NO_QUALIFIED_INDEPENDENT_PUBLICATION_EVIDENCE"),
                           "correction": stated("ABSENT", "SINGLE_RETAINED_REVISION_NO_CORRECTION_OBSERVED")}}
            path = (self.data / v["payload"]).as_posix().replace("'", "''")
            rows = con.execute(f"SELECT {', '.join(cols)} FROM read_parquet('{path}')").fetchall()
            if len(rows) != v["rows"]:
                raise ValueError(f"{cid} row count {len(rows)}")
            for i, values in enumerate(rows):
                r = dict(zip(cols, values))
                rec = self._repo_row(cid, v, i, r, cfbd)
                self.put("repository_rows.jsonl", (cid, rec["native_row_key"]), rec)
                if rec["join_state"] == "JOINED":
                    joined[rec["national_contest_key"]].append(rec)
        con.close()
        return joined

    def _repo_row(self, cid: str, v: dict[str, Any], i: int, r: dict[str, Any],
                  cfbd: dict[str, list[str]]) -> dict[str, Any]:
        event = r["game_id"] if r["game_id"] is not None else r["id"]
        clock = expect_clock(r["start_date"], "SOURCE_ASSERTED", v["payload"], f"/rows/{i}/start_date")
        rec = {"record_type": "repository_row", "capture_id": cid, "native_row_key": f"parquet_row:{i}",
               "season": v["season"], "source_revision": v["commit_sha"],
               "identifiers": {"event": {"namespace": "ESPN_EVENT_ID", "value": spell(event)},
                               "home_team": {"namespace": "ESPN_TEAM_ID", "value": spell(r["home_id"])},
                               "away_team": {"namespace": "ESPN_TEAM_ID", "value": spell(r["away_id"])}},
               "literals": {k: spell(val) for k, val in r.items()}, "event_clock": clock, "join_state": None,
               "join_reasons": [], "national_contest_key": None, "candidate_contest_keys": [], "orientation": None,
               "site_note": None}
        eid, est = as_count(event)
        if est != "OK":
            rec.update(join_state="UNJOINED", join_reasons=["UNJOINED_EVENT_ID_MALFORMED"])
            return rec
        cands = sorted(cfbd.get(str(eid), []))
        rec["candidate_contest_keys"] = cands
        if not cands:
            rec.update(join_state="UNJOINED", join_reasons=["UNJOINED_NO_PARENT_CANDIDATE"])
            return rec
        if len(cands) > 1:
            rec.update(join_state="AMBIGUOUS_MULTIPLE_PARENT_CANDIDATES",
                       join_reasons=["AMBIGUOUS_MULTIPLE_PARENT_CANDIDATES"])
            return rec
        key = cands[0]
        par, stg = self.P["parent"][key], self.P["stage"].get(key, {})
        why = []
        season, sst = as_count(r["season"])
        if sst != "OK" or season != par["season"]:
            why.append("CONFLICTING_SEASON")
        home, hst = as_count(r["home_id"])
        away, ast = as_count(r["away_id"])
        a, b = stg.get("a_cfbd_team_id"), stg.get("b_cfbd_team_id")
        side = None
        if a is None or b is None:
            why.append("PARENT_TEAM_ID_UNBOUND")
        elif hst != "OK" or ast != "OK" or home == away or sorted([str(home), str(away)]) != sorted([str(a), str(b)]):
            why.append("CONFLICTING_PARTICIPANT_IDENTITY")
        else:
            side = "A" if str(home) == str(a) else "B"
            if par["site"] in ("HOME_A", "HOME_B"):
                if r["neutral_site"] is False and par["site"][-1] != side:
                    why.append("CONFLICTING_SITE_ORIENTATION")
                elif r["neutral_site"] is True:
                    rec["site_note"] = "SITE_DESIGNATION_DIFFERS_SOURCE_NEUTRAL"
        if not (r["status_type_completed"] is True and par["contest_status"] == "COMPLETED"):
            why.append("CONFLICTING_COMPLETION")
        hs, hss = as_count(r["home_score"])
        aw, aws = as_count(r["away_score"])
        if "MALFORMED" in (hss, aws):
            why.append("SOURCE_VALUE_MALFORMED")
        elif side is not None:
            want = (par["a_points"], par["b_points"]) if side == "A" else (par["b_points"], par["a_points"])
            if hs is None or (hs, aw) != want:
                why.append("CONFLICTING_SCORES")
        if par["contest_date"] not in us_local_dates(clock):
            why.append("DATE_NOT_IN_DECLARED_US_LOCAL_CANDIDATES")
        rec["orientation"] = {"home_side": side} if side else None
        if why:
            rec.update(join_state="CONFLICTING", join_reasons=why)
        else:
            rec.update(national_contest_key=key, join_state="JOINED" if key in self.role else "JOINED_OUTSIDE_UNIVERSE")
        return rec

    # assertions ----------------------------------------------------------------------------------------------
    @staticmethod
    def corr(value: Any, parent: Any, state: str = "OK") -> str:
        if state == "MALFORMED":
            return "SOURCE_VALUE_MALFORMED"
        if value is None:
            return "SOURCE_VALUE_NULL"
        return "AGREES_WITH_PARENT" if value == parent else "CONFLICTS_WITH_PARENT"

    def assertion(self, key: str, cap: dict[str, Any], native: str, field: str, column: str, literal: Any,
                  value: Any, parent: Any, corroboration: str) -> dict[str, Any]:
        return {"record_type": "assertion", "contest_key": key, "capture_id": cap["capture_id"],
                "native_row_key": native, "field": field, "source_revision": cap["source_revision"],
                "source_kind": cap["source_kind"],
                "field_role": "OUTCOME" if field in OUTCOME else "IDENTITY", "source_column": column,
                "literal": spell(literal), "value": value, "parent_value": parent, "corroboration": corroboration}

    def contest(self, key: str, joined: dict[str, list[dict[str, Any]]]) -> None:
        par, stg = self.P["parent"][key], self.P["stage"].get(key, {})
        pv = {"season": par["season"], "contest_date": par["contest_date"], "a_participant": par["a_key"],
              "b_participant": par["b_key"],
              "completion": "COMPLETED" if par["contest_status"] == "COMPLETED" else "NOT_COMPLETED",
              "a_points": par["a_points"], "b_points": par["b_points"]}
        found: list[dict[str, Any]] = []
        lineage: list[dict[str, Any]] = []
        coverage = {k: 0 for k in KINDS}
        missing: list[str] = []
        pages = sorted(self.P["pages"].get((par["ncaa_contest_id"], par["season"]), []),
                       key=lambda p: (p["page_raw_sha256"], p["row_index"]))
        for p in pages:
            cap = self.cap_ncaa(p["page_raw_sha256"])
            native = f"page_row:{p['row_index']}"
            org, opp = spell(p["page_org_id"]), spell(p["opponent_logo_org_id"])
            side = {spell(par["a_org_id"]): "A", spell(par["b_org_id"]): "B"}.get(org)
            lineage.append({"record_type": "lineage_row", "contest_key": key, "capture_id": cap["capture_id"],
                            "native_row_key": native, "source_kind": "NCAA_TEAM_SEASON_PAGE", "route": None,
                            "source_revision": cap["source_revision"],
                            "identifiers": {"event": {"namespace": "NCAA_CONTEST_ID", "value": spell(p["ncaa_contest_id"])},
                                            "page_team": {"namespace": "NCAA_ORG_ID", "value": org},
                                            "opponent": {"namespace": "NCAA_ORG_ID", "value": opp}},
                            "literals": {k: spell(p.get(k)) for k in (
                                "season", "date_text", "result_text", "status", "page_org_id", "page_team_name",
                                "page_team_season_id", "opponent_logo_org_id", "opponent_name", "team_points",
                                "opponent_points", "page_team_marked_away", "neutral_site", "row_index")},
                            "event_clock": expect_clock(p["date_text"], "SOURCE_ASSERTED", cap["payload_path"],
                                                        f"schedule_row/{p['row_index']}/date", local_date=True),
                            "join_state": "PARENT_LINEAGE", "orientation": {"page_team_side": side}})
            coverage["NCAA_TEAM_SEASON_PAGE"] += 1
            if cap["clocks"]["retrieval"]["state"] != "PRESENT" and "NCAA_CAPTURE_RECEIPT_ABSENT" not in missing:
                missing.append("NCAA_CAPTURE_RECEIPT_ABSENT")
            season, sst = as_count(p["season"])
            found.append(self.assertion(key, cap, native, "season", "page.season", p["season"], season, pv["season"],
                                        self.corr(season, pv["season"], sst)))
            day = calendar_day(p["date_text"])
            dates = [day.isoformat()] if day else None
            found.append(self.assertion(key, cap, native, "contest_date", "page.date_text", p["date_text"], dates,
                                        pv["contest_date"],
                                        ("SOURCE_VALUE_MALFORMED" if p["date_text"] is not None and not day else
                                         "SOURCE_VALUE_NULL" if not day else
                                         "AGREES_WITH_PARENT" if dates == [pv["contest_date"]]
                                         else "CONFLICTS_WITH_PARENT")))
            for s in ("a", "b"):
                if side is None:
                    found.append(self.assertion(key, cap, native, f"{s}_participant", "page.page_org_id", org,
                                                f"org:{org}" if org else None, pv[f"{s}_participant"],
                                                "CONFLICTS_WITH_PARENT"))
                    continue
                mine = s.upper() == side
                ident = org if mine else opp
                val = f"org:{ident}" if ident else None
                found.append(self.assertion(key, cap, native, f"{s}_participant",
                                            "page.page_org_id" if mine else "page.opponent_logo_org_id", ident, val,
                                            pv[f"{s}_participant"],
                                            self.corr(val, pv[f"{s}_participant"]) if val else
                                            "NOT_ASSERTED_BY_SOURCE_ROW"))
            done = "COMPLETED" if p["status"] == "COMPLETED" else "NOT_COMPLETED"
            found.append(self.assertion(key, cap, native, "completion", "page.result_text", p["result_text"], done,
                                        pv["completion"], self.corr(done, pv["completion"])))
            for s in ("a", "b"):
                if side is None:
                    found.append(self.assertion(key, cap, native, f"{s}_points", "page.team_points", p["team_points"],
                                                None, pv[f"{s}_points"], "CONFLICTS_WITH_PARENT"))
                    continue
                col = "team_points" if s.upper() == side else "opponent_points"
                val, st = as_count(p[col])
                found.append(self.assertion(key, cap, native, f"{s}_points", "page." + col, p[col], val,
                                            pv[f"{s}_points"], self.corr(val, pv[f"{s}_points"], st)))
        if not pages:
            missing.append("NCAA_PAGE_ROW_ABSENT")
        elif len(pages) == 1:
            missing.append("NCAA_SECOND_MIRROR_ABSENT")
        ids = [spell(g) for g in json.loads(par["cfbd_game_ids"] or "[]")]
        for route in sorted(stg.get("cfbd_routes") or []):
            idx = self.routes.get((route, par["season"]), {})
            games = sorted([g for gid in ids for g in idx.get(gid, [])], key=lambda g: spell(g.get("id")))
            if not games:
                if "CFBD_ROUTE_ROW_ABSENT" not in missing:
                    missing.append("CFBD_ROUTE_ROW_ABSENT")
                continue
            for g in games:
                cap = self.cap_route(route, par["season"])
                native = f"cfbd_game_id:{spell(g.get('id'))}"
                a, b = spell(stg.get("a_cfbd_team_id")), spell(stg.get("b_cfbd_team_id"))
                home, away = spell(g.get("homeId")), spell(g.get("awayId"))
                side = "A" if a and home == a else ("B" if b and home == b else None)
                clock = expect_clock(g.get("startDate"), "SOURCE_ASSERTED", cap["payload_path"],
                                     f"/[id={spell(g.get('id'))}]/startDate")
                lineage.append({"record_type": "lineage_row", "contest_key": key, "capture_id": cap["capture_id"],
                                "native_row_key": native, "source_kind": "CFBD_ROUTE_RESPONSE", "route": route,
                                "source_revision": cap["source_revision"],
                                "identifiers": {"event": {"namespace": "CFBD_GAME_ID", "value": spell(g.get("id"))},
                                                "home_team": {"namespace": "CFBD_TEAM_ID", "value": home},
                                                "away_team": {"namespace": "CFBD_TEAM_ID", "value": away}},
                                "literals": {k: spell(g.get(k)) for k in (
                                    "id", "season", "startDate", "startTimeTBD", "completed", "neutralSite", "homeId",
                                    "homeTeam", "homePoints", "awayId", "awayTeam", "awayPoints")},
                                "event_clock": clock, "join_state": "PARENT_LINEAGE",
                                "orientation": {"home_side": side}})
                coverage["CFBD_ROUTE_RESPONSE"] += 1
                season, sst = as_count(g.get("season"))
                found.append(self.assertion(key, cap, native, "season", "cfbd.season", g.get("season"), season,
                                            pv["season"], self.corr(season, pv["season"], sst)))
                found.append(self._date(key, cap, native, "cfbd.startDate", g.get("startDate"), clock,
                                        pv["contest_date"]))
                for s, bound in (("a", a), ("b", b)):
                    ok = bound is not None and bound in (home, away) and home != away
                    found.append(self.assertion(key, cap, native, f"{s}_participant", "cfbd.homeId|awayId",
                                                f"{home}|{away}", pv[f"{s}_participant"] if ok else None,
                                                pv[f"{s}_participant"],
                                                "AGREES_WITH_PARENT" if ok else "CONFLICTS_WITH_PARENT"))
                done = "COMPLETED" if g.get("completed") is True else "NOT_COMPLETED"
                found.append(self.assertion(key, cap, native, "completion", "cfbd.completed", g.get("completed"),
                                            done, pv["completion"], self.corr(done, pv["completion"])))
                for s in ("a", "b"):
                    if side is None:
                        found.append(self.assertion(key, cap, native, f"{s}_points", "cfbd.homePoints|awayPoints",
                                                    None, None, pv[f"{s}_points"], "CONFLICTS_WITH_PARENT"))
                        continue
                    col = "homePoints" if s.upper() == side else "awayPoints"
                    val, st = as_count(g.get(col))
                    found.append(self.assertion(key, cap, native, f"{s}_points", "cfbd." + col, g.get(col), val,
                                                pv[f"{s}_points"], self.corr(val, pv[f"{s}_points"], st)))
        for rec in sorted(joined.get(key, []), key=lambda r: (r["capture_id"], r["native_row_key"])):
            cap = self.captures[rec["capture_id"]]
            lit, side, native = rec["literals"], rec["orientation"]["home_side"], rec["native_row_key"]
            season, sst = as_count(lit["season"])
            found.append(self.assertion(key, cap, native, "season", "repo.season", lit["season"], season,
                                        pv["season"], self.corr(season, pv["season"], sst)))
            found.append(self._date(key, cap, native, "repo.start_date", lit["start_date"], rec["event_clock"],
                                    pv["contest_date"]))
            for s in ("a", "b"):
                col = "home_id" if s.upper() == side else "away_id"
                found.append(self.assertion(key, cap, native, f"{s}_participant", "repo." + col, lit[col],
                                            pv[f"{s}_participant"], pv[f"{s}_participant"], "AGREES_WITH_PARENT"))
            done = "COMPLETED" if lit["status_type_completed"] == "true" else "NOT_COMPLETED"
            found.append(self.assertion(key, cap, native, "completion", "repo.status_type_completed",
                                        lit["status_type_completed"], done, pv["completion"],
                                        self.corr(done, pv["completion"])))
            for s in ("a", "b"):
                col = "home_score" if s.upper() == side else "away_score"
                val, st = as_count(lit[col])
                found.append(self.assertion(key, cap, native, f"{s}_points", "repo." + col, lit[col], val,
                                            pv[f"{s}_points"], self.corr(val, pv[f"{s}_points"], st)))
            coverage["REPOSITORY_VERSION"] += 1
        seasons = {v["season"] for v in self.c["source_universe"]["repository_versions"]}
        if par["season"] not in seasons:
            missing.append("REPOSITORY_VERSION_ABSENT_FOR_SEASON")
        elif not joined.get(key):
            missing.append("REPOSITORY_VERSION_ROW_NOT_JOINED")
        rank = {k: i for i, k in enumerate(KINDS)}
        frank = {f: i for i, f in enumerate(FIELD_LIST)}
        found.sort(key=lambda x: (rank[x["source_kind"]], x["capture_id"], x["native_row_key"], frank[x["field"]]))
        lineage.sort(key=lambda x: (rank[x["source_kind"]], x["capture_id"], x["native_row_key"]))
        for x in found:
            self.put("assertions.jsonl", (key, x["capture_id"], x["native_row_key"], x["field"], x["source_revision"]), x)
        for x in lineage:
            self.put("lineage_rows.jsonl", (key, x["capture_id"], x["native_row_key"]), x)
        gid = ids[0] if len(ids) == 1 else ("|".join(ids) if ids else None)
        self.put("contests.jsonl", (key,), {
            "record_type": "contest", "contest_key": key, "ncaa_contest_id": par["ncaa_contest_id"],
            "season": par["season"], "term": par["term"], "contest_date": par["contest_date"], "a_key": par["a_key"],
            "b_key": par["b_key"], "a_org_id": par["a_org_id"], "b_org_id": par["b_org_id"],
            "a_team_name": par["a_team_name"], "b_team_name": par["b_team_name"], "parent_site": par["site"],
            "roles": sorted(self.role[key]), "cfbd_game_id": {"namespace": "CFBD_GAME_ID", "value": gid},
            "a_cfbd_team_id": {"namespace": "CFBD_TEAM_ID", "value": spell(stg.get("a_cfbd_team_id"))},
            "b_cfbd_team_id": {"namespace": "CFBD_TEAM_ID", "value": spell(stg.get("b_cfbd_team_id"))},
            "source_coverage": coverage, "missing_evidence": missing, "assertion_count": len(found),
            "season_scope_state": "AUDITED_2016_2023"})

    def _date(self, key: str, cap: dict[str, Any], native: str, column: str, literal: Any, clock: dict[str, Any],
              parent_date: str) -> dict[str, Any]:
        if clock["state"] != "PRESENT":
            return self.assertion(key, cap, native, "contest_date", column, literal, None, parent_date,
                                  "SOURCE_VALUE_NULL" if literal is None else "SOURCE_VALUE_MALFORMED")
        dates = us_local_dates(clock)
        return self.assertion(key, cap, native, "contest_date", column, literal, dates, parent_date,
                              "AGREES_WITH_PARENT" if parent_date in dates else "NOT_CORROBORATED_BY_DECLARED_DATE_BASIS")

    def build(self) -> None:
        joined = self.repository()
        for key in self.universe:
            self.contest(key, joined)
        for key, season in sorted(self.P["census"], key=lambda x: (x[1], x[0])):
            part = "TARGET" if key in set(self.P["targets"]) else ("EXCLUSION" if key in self.P["exclusions"]
                                                                   else "OUT_OF_SCOPE")
            scope = ("IN_SCOPE" if key in self.role else "NOT_REFERENCED_BY_HISTORY_RELATIONS"
                     if season in range(2016, 2024) else "KEY_ONLY_PROTECTED_EXPOSED")
            self.put("partition.jsonl", (key,), {"record_type": "partition", "contest_key": key, "season": season,
                                                 "history_partition": part, "source_time_scope": scope,
                                                 "roles": sorted(self.role.get(key, set()))})
        for k, view, season, date, team, opponent, rec in self.P["views"]:
            self.put("relations.jsonl", ("TARGET_CONTEST", k, view, None, k), {
                "record_type": "relation", "relation_type": "TARGET_CONTEST", "target_contest_key": k, "view": view,
                "side": None, "history_team_key": team, "contributor_contest_key": k, "season": season,
                "target_date": date, "contributor_date": date, "required_fields": TARGET_ONLY})
            for side, block in (("TEAM", "team_history"), ("OPPONENT", "opponent_history")):
                for item in rec[block]["contributing"]:
                    self.put("relations.jsonl", ("CONTRIBUTOR", k, view, side, item["contest_key"]), {
                        "record_type": "relation", "relation_type": "CONTRIBUTOR", "target_contest_key": k,
                        "view": view, "side": side, "history_team_key": rec[block]["team_key"],
                        "contributor_contest_key": item["contest_key"], "season": season, "target_date": date,
                        "contributor_date": item["contest_date"], "required_fields": FIELD_LIST})
        rank = {k: i for i, k in enumerate(KINDS)}
        for cid in sorted(self.captures, key=lambda c: (rank[self.captures[c]["source_kind"]], c)):
            self.put("captures.jsonl", (cid,), self.captures[cid])


NATURAL = {"partition.jsonl": lambda r: (r["contest_key"],), "contests.jsonl": lambda r: (r["contest_key"],),
           "assertions.jsonl": lambda r: (r["contest_key"], r["capture_id"], r["native_row_key"], r["field"],
                                          r["source_revision"]),
           "lineage_rows.jsonl": lambda r: (r["contest_key"], r["capture_id"], r["native_row_key"]),
           "repository_rows.jsonl": lambda r: (r["capture_id"], r["native_row_key"]),
           "captures.jsonl": lambda r: (r["capture_id"],),
           "relations.jsonl": lambda r: (r["relation_type"], r["target_contest_key"], r["view"], r["side"],
                                         r["contributor_contest_key"])}


def compare(expected: Expected, delivered: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    out = {}
    for name in FILES:
        exp = expected.records[name]
        got_keys = [NATURAL[name](r) for r in delivered[name]]
        got = dict(zip(got_keys, delivered[name]))
        missing = [k for k in exp if k not in got]
        extra = [k for k in got if k not in exp]
        diffs = []
        for k, rec in got.items():
            if k in exp and rec != exp[k]:
                fields = sorted(f for f in set(rec) | set(exp[k]) if rec.get(f) != exp[k].get(f))
                diffs.append({"key": list(map(str, k)), "fields": fields})
        out[name] = {"expected": len(exp), "delivered": len(delivered[name]), "duplicates": len(got_keys) - len(got),
                     "missing": len(missing), "extra": len(extra), "differing": len(diffs),
                     "order_matches": got_keys == expected.order[name],
                     "samples": {"missing": [list(map(str, k)) for k in missing[:5]],
                                 "extra": [list(map(str, k)) for k in extra[:5]], "differing": diffs[:5]}}
    return out


def comparison_clean(result: dict[str, Any]) -> bool:
    return all(v["missing"] == v["extra"] == v["differing"] == v["duplicates"] == 0 and v["order_matches"]
               for v in result.values())


# --------------------------------------------------------------------------------------------- decisions

def parse_z(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


def my_cutoff(text: str) -> dt.datetime:
    m = INSTANT.match(text)
    if not m:
        raise ValueError(text)
    frac = m[7] or ""
    return dt.datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), int(m[6]),
                       int(frac[1:].ljust(6, "0")) if frac else 0, tzinfo=tz_of(m[8])).astimezone(UTCZ)


def my_observed(cap: dict[str, Any], cut: dt.datetime) -> str:
    c = cap["clocks"]["retrieval"]
    if c["state"] != "PRESENT":
        return "UNKNOWN"
    lo, hi = parse_z(c["earliest_utc"]), parse_z(c["latest_utc"])
    if hi <= cut:
        return "TRUE"
    if c["role"] == "EXACT_REQUEST_INTERVAL" and lo > cut:
        return "FALSE"
    return "UNKNOWN"


def my_published(observed: str, field: str, date: str, cut: dt.datetime) -> str:
    if observed == "TRUE":
        return "TRUE"
    day = dt.date.fromisoformat(date)
    first = dt.datetime(day.year, day.month, day.day) - dt.timedelta(hours=14)
    if field in OUTCOME and cut < first.replace(tzinfo=UTCZ):
        return "FALSE"
    return "UNKNOWN"


def my_contest_fields(expected: Expected, cut: dt.datetime) -> dict[str, dict[str, Any]]:
    by_contest = defaultdict(list)
    for key, rec in expected.records["assertions.jsonl"].items():
        by_contest[key[0]].append(rec)
    out = {}
    for key in expected.universe:
        date = expected.P["parent"][key]["contest_date"]
        fields = {}
        for f in FIELD_LIST:
            rows = [a for a in by_contest[key] if a["field"] == f]
            agree = [a for a in rows if a["corroboration"] == "AGREES_WITH_PARENT"]
            obs = [my_observed(expected.captures[a["capture_id"]], cut) for a in agree]
            pub = [my_published(o, f, date, cut) for o in obs]

            def agg(states: list[str]) -> str:
                if not states:
                    return "NO_CORROBORATING_ASSERTION"
                return "TRUE" if "TRUE" in states else ("FALSE" if all(s == "FALSE" for s in states) else "UNKNOWN")
            fields[f] = {"assertions": len(rows), "agreeing": len(agree), "conflicting": len(rows) - len(agree),
                         "observed_by_cutoff": agg(obs), "historically_published_by_cutoff": agg(pub)}
        out[key] = fields
    return out


def run_query(db: Path, argv: list[str]) -> tuple[int, Any, str]:
    """Run the delivered consumer as a separate process (its code is never imported here). An inherited PYTHONPATH
    wins; the checkout's src is appended only so a bare source checkout can locate the module."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (env.get("PYTHONPATH"), str(Path(__file__).resolve().parents[1] /
                                                                                 "src")) if p)
    proc = subprocess.run([sys.executable, "-B", "-m", "aggie_analytics.national_source_time.query", "--database",
                           str(db), *argv], capture_output=True, text=True, encoding="utf-8", env=env)
    try:
        doc = json.loads(proc.stdout) if proc.stdout.strip() else None
    except ValueError:
        doc = None
    return proc.returncode, doc, proc.stderr


def decision_checks(expected: Expected, db: Path, report: Report) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    results = {}
    for literal in PROBE_CUTOFFS:
        cut = my_cutoff(literal)
        mine = my_contest_fields(expected, cut)
        code, doc, err = run_query(db, ["--grain", "contest", "--cutoff", literal, "--all"])
        if code != 0 or doc is None:
            report.check(f"query_contest_grain_runs_{literal}", False, err[-500:])
            continue
        theirs = {row["contest"]["contest_key"]: row["fields"] for row in doc["rows"]}
        diffs = [k for k in mine if theirs.get(k) != mine[k]]
        tally = Counter((f, v["observed_by_cutoff"], v["historically_published_by_cutoff"])
                        for fields in mine.values() for f, v in fields.items())
        admitted = sum(1 for row in doc["rows"] if row["pit_admission"]["state"] != "NOT_ADMITTED")
        results[literal] = {"contests": len(mine), "query_rows": len(theirs), "differing": len(diffs),
                            "sample": diffs[:5], "admitted_rows": admitted,
                            "field_decision_tally": {f"{f}|{o}|{p}": n for (f, o, p), n in sorted(tally.items())}}
        report.check(f"contest_decisions_agree_{literal}", not diffs and len(theirs) == len(mine) and not admitted,
                     {"differing": len(diffs), "sample": diffs[:3]})
    summary["contest_grain"] = results
    a = results.get("2026-08-13T10:39:56Z", {}).get("field_decision_tally")
    b = results.get("2026-08-13T05:39:56-05:00", {}).get("field_decision_tally")
    report.check("timezone_equivalent_cutoffs_identical", a is not None and a == b)
    # assertion-grain sample: whole contests across seasons and source mixes, compared row by row
    rng = random.Random(40)
    by_contest: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for kk in expected.order["assertions.jsonl"]:
        by_contest[kk[0]].append(expected.records["assertions.jsonl"][kk])
    unusual = [k for k in expected.universe if any(r["corroboration"] != "AGREES_WITH_PARENT" for r in by_contest[k])]
    sample = sorted(set(rng.sample(expected.universe, min(40, len(expected.universe))) + unusual[:10]))
    bad = []
    for literal in ("2026-08-09T18:59:48Z", "2026-10-02T00:00:00Z"):
        cut = my_cutoff(literal)
        for key in sample:
            code, doc, err = run_query(db, ["--grain", "assertion", "--cutoff", literal, "--contest", key, "--all"])
            want = by_contest[key]
            got = [row["assertion"] for row in (doc or {}).get("rows", [])]
            if code != 0 or got != want:
                bad.append((literal, key, "records"))
                continue
            date = expected.P["parent"][key]["contest_date"]
            for row in doc["rows"]:
                cap = expected.captures[row["assertion"]["capture_id"]]
                o = my_observed(cap, cut)
                if row["decision"]["observed_by_cutoff"] != o or row["decision"]["historically_published_by_cutoff"] \
                        != my_published(o, row["assertion"]["field"], date, cut) or \
                        row["decision"]["pit_admission"]["state"] != "NOT_ADMITTED":
                    bad.append((literal, key, row["assertion"]["field"]))
    summary["assertion_sample"] = {"contests": len(sample), "cutoffs": 2, "differences": bad[:10]}
    report.check("assertion_sample_decisions_agree", not bad, bad[:5])
    # contribution-grain sample over several targets at a historical cutoff
    targets = sorted(rng.sample(expected.P["targets"], min(15, len(expected.P["targets"]))))
    cbad = []
    cut_literal = "2026-08-13T10:39:56Z"
    fields = my_contest_fields(expected, my_cutoff(cut_literal))
    for key in targets:
        code, doc, err = run_query(db, ["--grain", "contribution", "--cutoff", cut_literal, "--contest", key, "--all"])
        want = [r for kk, r in expected.records["relations.jsonl"].items() if kk[1] == key]
        got = [row["relation"] for row in (doc or {}).get("rows", [])]
        if code != 0 or got != want:
            cbad.append((key, "relations"))
            continue
        for row in doc["rows"]:
            rel = row["relation"]
            req = {f: fields[rel["contributor_contest_key"]][f] for f in rel["required_fields"]}
            obs = [v["observed_by_cutoff"] for v in req.values()]
            expect = "TRUE" if obs and all(o == "TRUE" for o in obs) else ("FALSE" if "FALSE" in obs else "UNKNOWN")
            if row["inputs_observed_by_cutoff"] != expect or (rel["relation_type"] == "TARGET_CONTEST" and
                                                              set(row["required_field_decisions"]) & OUTCOME):
                cbad.append((key, rel["contributor_contest_key"]))
    summary["contribution_sample"] = {"targets": len(targets), "differences": cbad[:10]}
    report.check("contribution_sample_decisions_agree_and_target_outcome_excluded", not cbad, cbad[:5])
    return summary


# --------------------------------------------------------------------------------------------- delivered data

def read_delivered(manifest: Path, report: Report, contract: dict[str, Any], expected_parent: dict[str, Any],
                   universe_sha: str, contract_sha: str) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any], Path]:
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    content = doc["identity_document"]
    ident = manifest.parent.name
    report.check("content_identity_recomputed", h_bytes(cjson(content)) == ident == doc["identity"])
    folder = manifest.parents[4] / "canonical" / manifest.parents[2].name / "sha256" / ident
    payload = {}
    semantic_ok = physical_ok = True
    for name in FILES:
        raw = (folder / f"{name}.gz").read_bytes()
        physical_ok &= h_bytes(raw) == content["outputs"].get(f"{name}.gz")
        text = gzip.decompress(raw)
        semantic_ok &= h_bytes(text) == content["semantic_outputs"].get(name)
        lines = text.decode("utf-8").split("\n")
        if lines[-1] != "" or any(not line for line in lines[:-1]):
            report.check(f"{name}_line_format", False)
        payload[name] = [json.loads(line) for line in lines[:-1]]
        for line in lines[:-1]:
            if line.encode("utf-8") != cjson(json.loads(line)):
                report.check(f"{name}_canonical_serialization", False, line[:200])
                break
    report.check("payload_physical_hashes", physical_ok)
    report.check("payload_semantic_hashes", semantic_ok)
    report.check("content_document_binds_contract_parent_universe",
                 content.get("contract_sha256") == contract_sha and content.get("parent") == expected_parent and
                 content.get("source_universe_sha256") == universe_sha and
                 content.get("row_counts") == {n: len(payload[n]) for n in FILES})
    db_ident = doc["provenance"].get("database_identity")
    db_manifest = manifest.parents[1] / db_ident / "run_manifest.json"
    ddoc = json.loads(db_manifest.read_text(encoding="utf-8"))
    report.check("database_identity_recomputed", h_bytes(cjson(ddoc["identity_document"])) == db_ident ==
                 ddoc["identity"] and ddoc["identity_document"]["content_identity"] == ident)
    db = manifest.parents[4] / "canonical" / manifest.parents[2].name / "sha256" / db_ident / "national_source_time.sqlite"
    report.check("database_bytes_hash", h_file(db) == ddoc["identity_document"]["outputs"]["national_source_time.sqlite"])
    con = sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True)
    lines = {"partition.jsonl": [r for (r,) in con.execute("SELECT record FROM partition ORDER BY ord")],
             "contests.jsonl": [r for (r,) in con.execute("SELECT record FROM contests ORDER BY ord")],
             "captures.jsonl": [r for (r,) in con.execute("SELECT record FROM captures ORDER BY ord")],
             "repository_rows.jsonl": [r for (r,) in con.execute("SELECT record FROM repository_rows ORDER BY ord")]}
    blobs = {"assertions.jsonl": [], "lineage_rows.jsonl": [], "relations.jsonl": []}
    counts_ok = True
    for a_n, a_b, l_n, l_b in con.execute("SELECT assertion_count, assertions, lineage_count, lineage FROM contests "
                                          "ORDER BY ord"):
        a = zlib.decompress(a_b).decode("utf-8").splitlines()
        l_ = zlib.decompress(l_b).decode("utf-8").splitlines()
        counts_ok &= len(a) == a_n and len(l_) == l_n
        blobs["assertions.jsonl"] += a
        blobs["lineage_rows.jsonl"] += l_
    for n, b in con.execute("SELECT relation_count, relations FROM relation_groups ORDER BY ord"):
        r = zlib.decompress(b).decode("utf-8").splitlines()
        counts_ok &= len(r) == n
        blobs["relations.jsonl"] += r
    meta = dict(con.execute("SELECT key, value FROM meta"))
    con.close()
    lines.update(blobs)
    same = {n: [json.loads(x) for x in lines[n]] == payload[n] for n in FILES}
    report.check("database_records_equal_payload_lines", all(same.values()) and counts_ok, same)
    report.check("database_meta_binds_identities", meta.get("content_identity") == ident and
                 meta.get("contract_sha256") == contract_sha and json.loads(meta.get("parent")) == expected_parent and
                 json.loads(meta.get("row_labels")) == contract["row_labels"])
    return payload, {"content_identity": ident, "database_identity": db_ident,
                     "database_sha256": ddoc["identity_document"]["outputs"]["national_source_time.sqlite"]}, db


# --------------------------------------------------------------------------------------------- tamper and challenges

def tamper_cases(expected: Expected, delivered: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Coordinated semantic tampers of the delivered records (as if every outer hash were consistently recomputed);
    the reconstruction must reject each one."""
    def first(file: str, pred) -> int:
        return next(i for i, r in enumerate(delivered[file]) if pred(r))
    cases = []

    def run(name: str, mutate) -> None:
        copy_ = {k: list(v) for k, v in delivered.items()}
        try:
            mutate(copy_)
            result = compare(expected, copy_)
            cases.append({"case": name, "rejected": not comparison_clean(result),
                          "detected_in": [n for n, v in result.items() if v["missing"] or v["extra"] or v["differing"]
                                          or v["duplicates"] or not v["order_matches"]]})
        except StopIteration:
            cases.append({"case": name, "rejected": False, "detected_in": [], "note": "no applicable record"})

    def edit(file: str, pred, change) -> Any:
        def mutate(d):
            i = first(file, pred)
            rec = copy.deepcopy(d[file][i])
            change(rec)
            d[file][i] = rec
        return mutate

    run("right_game_wrong_score_field", edit("assertions.jsonl", lambda r: r["field"] == "a_points" and
                                             r["source_kind"] == "REPOSITORY_VERSION",
                                             lambda r: r.update(field="b_points")))
    run("same_participant_wrong_season", edit("assertions.jsonl", lambda r: r["field"] == "season",
                                              lambda r: r.update(value=r["value"] + 1)))
    run("equal_numeric_id_other_namespace_join", edit("repository_rows.jsonl",
                                                      lambda r: "CONFLICTING_PARTICIPANT_IDENTITY" in r["join_reasons"],
                                                      lambda r: r.update(join_state="JOINED", join_reasons=[],
                                                                         national_contest_key=r["candidate_contest_keys"][0])))
    run("switched_home_away", edit("lineage_rows.jsonl", lambda r: r["source_kind"] == "CFBD_ROUTE_RESPONSE",
                                   lambda r: r["orientation"].update(home_side="B" if r["orientation"]["home_side"] == "A"
                                                                     else "A")))
    run("tied_score_ambiguity_resolved_by_position", edit(
        "assertions.jsonl", lambda r: r["field"] == "a_participant" and r["source_kind"] == "REPOSITORY_VERSION",
        lambda r: r.update(source_column="repo.home_id" if r["source_column"] == "repo.away_id" else "repo.away_id")))
    run("duplicate_source_version_conflicting_clocks", lambda d: d["captures.jsonl"].append(
        dict(copy.deepcopy(d["captures.jsonl"][0]), clocks=dict(d["captures.jsonl"][0]["clocks"], retrieval=dict(
            d["captures.jsonl"][0]["clocks"]["retrieval"], literal="2016-08-01T00:00:00Z")))))
    run("exact_bytes_forged_publication_label", edit("captures.jsonl", lambda r: r["source_kind"] == "REPOSITORY_VERSION",
                                                     lambda r: r["clocks"].update(supported_publication=dict(
                                                         r["clocks"]["retrieval"], state="PRESENT",
                                                         role="QUALIFIED_PUBLICATION"))))
    run("git_date_substituted_for_publication", edit(
        "captures.jsonl", lambda r: r["source_kind"] == "REPOSITORY_VERSION",
        lambda r: r["clocks"].update(supported_publication=dict(r["clocks"]["asserted_commit_committer"]))))
    run("current_retrieval_substituted_for_historical_time", edit(
        "captures.jsonl", lambda r: r["source_kind"] == "NCAA_TEAM_SEASON_PAGE",
        lambda r: r["clocks"]["retrieval"].update(literal="2016-09-01T00:00:00Z", earliest_utc="2016-09-01T00:00:00.000000Z",
                                                  latest_utc="2016-09-01T00:00:00.000000Z")))
    run("page_timestamp_from_unrelated_node", lambda d: (lambda i, j: d["captures.jsonl"].__setitem__(i, dict(
        d["captures.jsonl"][i], receipt_pointer=d["captures.jsonl"][j]["receipt_pointer"],
        clocks=d["captures.jsonl"][j]["clocks"]))) (0, 1))
    run("later_correction_passed_as_earlier_version", edit(
        "captures.jsonl", lambda r: r["source_kind"] == "REPOSITORY_VERSION",
        lambda r: r["clocks"].update(correction=dict(r["clocks"]["retrieval"], state="PRESENT",
                                                     role="CORRECTION", literal="2016-12-01T00:00:00Z"))))
    run("null_converted_to_zero", edit("repository_rows.jsonl", lambda r: r["join_state"] == "UNJOINED",
                                       lambda r: r["literals"].update(home_score="0" if r["literals"]["home_score"]
                                                                      != "0" else None)))
    run("future_contributor_inserted", lambda d: d["relations.jsonl"].append(dict(
        d["relations.jsonl"][1], contributor_contest_key=d["relations.jsonl"][-1]["target_contest_key"],
        contributor_date="2099-01-01")))
    run("target_as_own_contributor", lambda d: d["relations.jsonl"].append(dict(
        d["relations.jsonl"][0], relation_type="CONTRIBUTOR", side="TEAM",
        required_fields=FIELD_LIST)))
    run("one_parent_relation_dropped", lambda d: d["relations.jsonl"].pop(first("relations.jsonl", lambda r:
                                                                             r["relation_type"] == "CONTRIBUTOR")))
    run("merged_rehashed_forged_contest_coverage", edit("contests.jsonl", lambda r: "REPOSITORY_VERSION_ABSENT_FOR_SEASON"
                                                        in r["missing_evidence"],
                                                        lambda r: r.update(missing_evidence=[])))
    run("partition_key_scope_expansion_2024", edit("partition.jsonl", lambda r: r["season"] == 2024,
                                                   lambda r: r.update(source_time_scope="IN_SCOPE")))
    run("evidence_class_upgraded", edit("captures.jsonl", lambda r: r["source_kind"] == "NCAA_TEAM_SEASON_PAGE",
                                        lambda r: r.update(time_evidence_class="EXACT_REQUEST_RECEIPT_ONLY")))
    run("conflicting_score_row_forced_joined", edit("repository_rows.jsonl",
                                                    lambda r: "CONFLICTING_SCORES" in r["join_reasons"],
                                                    lambda r: r.update(join_state="JOINED", join_reasons=[])))
    run("assertion_dropped", lambda d: d["assertions.jsonl"].pop(0))
    return cases


def raw_page_sample(expected: Expected, delivered: dict[str, list[dict[str, Any]]], per_season: int = 6) -> dict[str, Any]:
    """Trace sampled lineage rows to the raw NCAA page bytes: the schedule row containing the contest link must carry
    the delivered date text and result text."""
    rng = random.Random(4012)
    by_season = defaultdict(list)
    for r in delivered["lineage_rows.jsonl"]:
        if r["source_kind"] == "NCAA_TEAM_SEASON_PAGE":
            by_season[r["literals"]["season"]].append(r)
    checked, bad = 0, []
    row_re = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
    for season, rows in sorted(by_season.items()):
        for r in rng.sample(rows, min(per_season, len(rows))):
            cap = expected.captures[r["capture_id"]]
            text = (expected.data / cap["payload_path"]).read_bytes().decode("utf-8", errors="replace")
            link = f"/contests/{r['identifiers']['event']['value']}/box_score"
            rows_html = [m for m in row_re.findall(text) if link in m]
            plain = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m))) for m in rows_html]
            ok = any(r["literals"]["date_text"] in p and r["literals"]["result_text"] in p for p in plain)
            checked += 1
            if not ok:
                bad.append({"capture": r["capture_id"], "contest": r["contest_key"]})
    return {"rows_checked": checked, "mismatches": bad, "per_season": per_season,
            "limit": "sampled raw HTML rows only (date and result text inside the row carrying the contest link)"}


def challenges(expected: Expected, delivered: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    repo = delivered["repository_rows.jsonl"]
    caps = {c["capture_id"]: c for c in delivered["captures.jsonl"]}
    out = []
    ns = [r for r in repo if "CONFLICTING_PARTICIPANT_IDENTITY" in r["join_reasons"]]
    out.append({"challenge": "espn_and_cfbd_team_namespaces_differ_somewhere", "as_expected": bool(ns),
                "detail": f"{len(ns)} rows where an ESPN team id differs from the bound CFBD id"})
    dates = [r for r in repo if "DATE_NOT_IN_DECLARED_US_LOCAL_CANDIDATES" in r["join_reasons"]]
    out.append({"challenge": "date_basis_is_not_a_blanket_tolerance", "as_expected": all(
        expected.P["parent"][r["candidate_contest_keys"][0]]["contest_date"] not in us_local_dates(r["event_clock"])
        for r in dates), "detail": [r["literals"]["start_date"] for r in dates]})
    ncaa = [c for c in caps.values() if c["source_kind"] == "NCAA_TEAM_SEASON_PAGE"]
    out.append({"challenge": "ncaa_stamps_are_batch_upper_bounds_not_exact", "as_expected": all(
        c["clocks"]["retrieval"]["role"] == "RECORDED_POSSESSION_UPPER_BOUND" for c in ncaa) and
        max(c["receipt_stamp_shared_by"] for c in ncaa) > 1,
        "detail": {"max_shared": max(c["receipt_stamp_shared_by"] for c in ncaa)}})
    repo_caps = [c for c in caps.values() if c["source_kind"] == "REPOSITORY_VERSION"]
    out.append({"challenge": "asserted_commit_times_precede_own_retrieval_and_follow_each_season",
                "as_expected": all(c["clocks"]["asserted_commit_committer"]["latest_utc"] <
                                   c["clocks"]["retrieval"]["earliest_utc"] and
                                   c["clocks"]["asserted_commit_committer"]["literal"][:4] > str(c["season"])
                                   for c in repo_caps),
                "detail": {c["season"]: c["clocks"]["asserted_commit_committer"]["literal"] for c in repo_caps}})
    out.append({"challenge": "no_supported_publication_clock_anywhere", "as_expected": all(
        c["clocks"]["supported_publication"]["state"] == "ABSENT" for c in caps.values())})
    out.append({"challenge": "2023_contests_record_absent_repository_version", "as_expected": all(
        ("REPOSITORY_VERSION_ABSENT_FOR_SEASON" in c["missing_evidence"]) == (c["season"] == 2023)
        for c in delivered["contests.jsonl"])})
    out.append({"challenge": "2024_2025_keys_are_key_only", "as_expected": all(
        p["source_time_scope"] == "KEY_ONLY_PROTECTED_EXPOSED" for p in delivered["partition.jsonl"]
        if p["season"] in (2024, 2025)) and not any(c["season"] > 2023 for c in delivered["contests.jsonl"])})
    out.append({"challenge": "every_target_view_has_a_target_relation", "as_expected": sum(
        1 for r in delivered["relations.jsonl"] if r["relation_type"] == "TARGET_CONTEST") ==
        len(expected.P["views"])})
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("--contract", "--history-database", "--population-database", "--source-bindings", "--manifest",
                 "--report"):
        parser.add_argument(name, required=True, type=Path)
    args = parser.parse_args(argv)
    if args.report.exists():
        print(json.dumps({"refused": "REPORT_EXISTS"}), file=sys.stderr)
        return 2
    report = Report()
    contract_bytes = args.contract.read_bytes()
    contract = json.loads(contract_bytes)
    contract_sha = h_bytes(contract_bytes)
    report.check("contract_is_evidence_only", contract["authority"]["pit_admission"] ==
                 "NOT_ADMITTED_NO_SEPARATE_PIT_ADMISSION_AUTHORITY" and
                 contract["authority"]["qualified_publication_evidence_classes"] == [] and
                 contract["scope"]["target_seasons"] == list(range(2016, 2024)))
    ctx = verify_bindings(contract, args, report)
    P = load_parent(args, ctx)
    expected = Expected(contract, ctx, P)
    expected.build()
    pb = contract["parent_binding"]
    expected_parent = {"history": {"database_identity": pb["history"]["database_identity"],
                                   "sqlite_sha256": pb["history"]["sqlite_sha256"],
                                   "content_identity": pb["history"]["content_identity"],
                                   "contract_sha256": pb["history"]["contract_sha256"]},
                       "population": {k: pb["population"][k] for k in ("query_db_identity", "sqlite_sha256",
                                                                       "contract_sha256", "contest_identity",
                                                                       "program_season_identity")}}
    delivered, identities, db = read_delivered(args.manifest, report, contract, expected_parent, ctx["universe_sha256"],
                                               contract_sha)
    comparison = compare(expected, delivered)
    report.check("every_record_reconstructed_independently", comparison_clean(comparison),
                 {k: {f: v[f] for f in ("expected", "delivered", "missing", "extra", "differing", "duplicates",
                                        "order_matches")} for k, v in comparison.items()})
    census_keys = {k for k, _s in P["census"]}
    part = delivered["partition.jsonl"]
    report.check("partition_accounts_every_parent_key_once", len(part) == len(census_keys) ==
                 len({p["contest_key"] for p in part}) and {p["contest_key"] for p in part} == census_keys)
    rel = delivered["relations.jsonl"]
    contributing = sum(len(v[6][b]["contributing"]) for v in P["views"] for b in ("team_history", "opponent_history"))
    report.check("every_relation_preserved", sum(1 for r in rel if r["relation_type"] == "CONTRIBUTOR") == contributing
                 and sum(1 for r in rel if r["relation_type"] == "TARGET_CONTEST") == len(P["views"]))
    report.check("every_repository_row_dispositioned",
                 len(delivered["repository_rows.jsonl"]) == contract["parent_binding"]["source_bindings"]["source_rows"]
                 and all(r["join_state"] for r in delivered["repository_rows.jsonl"]))
    decisions = decision_checks(expected, db, report)
    tampers = tamper_cases(expected, delivered)
    report.check("every_tamper_case_rejected", all(t["rejected"] for t in tampers),
                 [t["case"] for t in tampers if not t["rejected"]])
    raw = raw_page_sample(expected, delivered)
    report.check("raw_ncaa_page_sample_agrees", not raw["mismatches"] and raw["rows_checked"] > 0, raw["mismatches"][:5])
    oracle = challenges(expected, delivered)
    report.check("oracle_self_challenges_as_expected", all(c["as_expected"] for c in oracle),
                 [c["challenge"] for c in oracle if not c["as_expected"]])
    repo = delivered["repository_rows.jsonl"]
    counts = {"parent_keys": len(census_keys), "targets": len(P["targets"]), "views": len(P["views"]),
              "universe_contests": len(expected.universe),
              "contributors": sum(1 for k in expected.role if "CONTRIBUTOR" in expected.role[k]),
              "targets_also_contributors": sum(1 for k in expected.role if expected.role[k] == {"TARGET", "CONTRIBUTOR"}),
              "contributor_relations": contributing, "target_relations": len(P["views"]),
              "assertions": len(delivered["assertions.jsonl"]), "lineage_rows": len(delivered["lineage_rows.jsonl"]),
              "captures": len(delivered["captures.jsonl"]), "repository_rows": len(repo),
              "repository_join_states": dict(Counter(r["join_state"] for r in repo)),
              "repository_join_reasons": dict(Counter("+".join(r["join_reasons"]) or "-" for r in repo)),
              "assertion_corroboration": dict(Counter(f"{a['source_kind']}|{a['corroboration']}"
                                                      for a in delivered["assertions.jsonl"])),
              "missing_evidence": dict(Counter("+".join(c["missing_evidence"]) or "-" for c in delivered["contests.jsonl"])),
              "time_evidence_classes": dict(Counter(c["time_evidence_class"] for c in delivered["captures.jsonl"])),
              "partition": dict(Counter(f"{p['history_partition']}|{p['source_time_scope']}" for p in part))}
    result = {"cycle_number": 40, "attempt_number": 1, "jira_key": "BAT-712",
              "tool": "tools/validate_national_source_time.py", "tool_sha256": h_file(Path(__file__)),
              "independence": "standard library plus duckdb; no producer, query or project import; the delivered query "
                              "is only exercised as a subprocess and compared with this tool's own decisions",
              "result": "PASS" if not report.failed else "FAIL", "failed_checks": report.failed,
              "contract_sha256": contract_sha, **identities, "counts": counts, "comparison": comparison,
              "decisions": decisions, "tamper_cases": tampers, "raw_sample": raw, "oracle_challenges": oracle,
              "checks": report.checks,
              "limits": ["publication-time truth is not reconstructed: no qualified publication evidence exists in the "
                         "bounded sources; every TRUE publication decision rests on this system's own 2026 observation",
                         "raw NCAA pages are sampled, not fully re-parsed; parent page_observations are the accepted "
                         "BAT-710 parse bound by raw SHA-256",
                         "repository and CFBD rows are reread in full; their upstream provenance beyond the bound "
                         "bytes and receipts is not audited",
                         "no historical PIT admission, model or forecast is evaluated"],
              "observed_at": dt.datetime.now(UTCZ).isoformat()}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, indent=1, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({"result": result["result"], "failed_checks": report.failed, "counts": {
        k: v for k, v in counts.items() if isinstance(v, int)}}, indent=1))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
