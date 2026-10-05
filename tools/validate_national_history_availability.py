r"""Independent validator for the 2019 history-availability projection (BAT-714, Cycle #42 TP42-A01).

``python -B tools/validate_national_history_availability.py --contract
configs/national_history_availability_2019_contract.json --input-bindings <INPUT_BINDINGS.json>
--manifest <manifests/national_history_availability_2019/sha256/<content id>/run_manifest.json> --report <new path>``

Standard library only. It imports no producer, query, core or project code. The archive truth comes from the accepted
Cycle 41 independent oracle (``tools/validate_national_archived_publication.py``), loaded by path only after its bytes
hash to the value the contract binds (the file at the accepted base); that oracle rebuilds every archived version,
field state and upper bound from raw bytes and receipts without producer code. Zero new archive coverage is claimed.

From the files themselves this tool re-verifies the contract and every parent binding (bindings document, file
hashes, run-manifest identity documents); enumerates the 2019 targets and every expected prior relationship from the
population database with its own SQL and its own predicate code; checks those against the history parent's targets,
contributing contests and excluded inputs; reconstructs each referenced prior contest's evidence class, coherent
versions and bounds from the oracle's records with its own coherent-version rule; rebuilds every expected record and
compares the delivered payloads and database rows field by field by natural key; recomputes both identity documents;
derives the expected content identity from the contract and its own reconstructed records (never from a delivered
document) and requires the delivered content identity, the database meta's restated content declaration and the
binding of every consumer response to equal it; recomputes every view's aggregates and every relationship decision at
probe cutoffs (including each target date's conservative boundary) and compares them with the delivered query
consumer run as a subprocess; and runs coordinated
semantic tamper cases (as if every outer hash were recomputed) and oracle self-challenges, reporting each case's
detected class. The report is a new file written once. Exit 0 only when every check passes.

BAT-715 expansion (Cycle #43 TP43-A01): for the explicit expansion contract
(``configs/national_history_availability_2019_expansion_contract.json``) the same checks run over the 97-key archive
expansion sidecar. Its archive binding adds the cohort and the retained acquisition; the bindings document must also
name the cohort, the archive's own source bindings, the retained V1.2 contract and root; and the archive truth comes
from the expansion oracle the contract binds by sha256 (``tools/validate_national_archived_publication_expansion.py``,
which itself loads the accepted C41 oracle only after its bytes hash to the accepted value). The V1.0 path is unchanged.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import gzip
import hashlib
import importlib.util
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

UTC = dt.timezone.utc
SIX = ["contest_date", "a_participant", "b_participant", "completion", "a_points", "b_points"]
QUAL = "QUALIFIED_AGREES_WITH_PARENT"
CONTRA = {"CONFLICTS_WITH_PARENT", "CONTRADICTORY_WITHIN_VERSION"}
NAMES = ["targets.jsonl", "views.jsonl", "relationships.jsonl", "evidence.jsonl", "witnesses.jsonl"]
TABLE_OF = {"targets.jsonl": "targets", "views.jsonl": "views", "relationships.jsonl": "relationships",
            "evidence.jsonl": "evidence", "witnesses.jsonl": "witnesses"}
PARENT_FILE = {"population": ("national_di_population_2016_2025", "national_population.sqlite", "query_db_identity"),
               "history": ("national_history_prefix_2016_2023", "national_history.sqlite", "database_identity"),
               "source_time": ("national_source_time_2016_2023", "national_source_time.sqlite", "database_identity"),
               "archive": ("national_archived_publication_2019", "national_archived_publication.sqlite",
                           "database_identity")}
BIND_KEY = {"population": "population_database", "history": "history_database", "source_time": "source_time_database",
            "archive": "archive_database"}
#: The defined content identity document (contract identity_scheme.content_identity) as this tool restates it: the
#: schema and stage labels, the label of the contract's payloads.encoding rule (canonical JSONL stored as gzip with
#: mtime 0 and no file name) and the identity fields of each bound parent (the contract binding without its location,
#: schema, role, path and verification descriptors).
CONTENT_SCHEMA = "BAS-NATIONAL-HISTORY-AVAILABILITY-CONTENT-1"
CONTENT_STAGE = "history-availability-content"
PAYLOAD_ENCODING = "GZIP_MTIME_0_OF_CANONICAL_JSONL"
PARENT_IDENTITY_FIELDS = {
    "population": ("query_db_identity", "sqlite_sha256", "contract_sha256", "contest_identity", "program_season_identity"),
    "history": ("database_identity", "sqlite_sha256", "content_identity", "contract_sha256"),
    "source_time": ("database_identity", "sqlite_sha256", "content_identity", "contract_sha256"),
    "archive": ("database_identity", "sqlite_sha256", "content_identity", "contract_sha256", "contract_id",
                "tranche_sha256", "acquisition_identity")}
#: BAT-715 expansion: its own contract and population over the 97-key archive expansion sidecar.
EXPANSION_CONTRACT_ID = "BAT-715-NATIONAL-HISTORY-AVAILABILITY-2019-EXPANSION-V1.0"
EXPANSION_POPULATION = "national_history_availability_2019_expansion"
EXPANSION_ARCHIVE_FIELDS = PARENT_IDENTITY_FIELDS["archive"] + ("cohort_sha256", "retained_acquisition_identity")
#: ``python -c CONSUMER_BOOTSTRAP <spec json> <query argv...>``: registers a synthetic world's availability and archive
#: authorities inside the consumer process only (this tool never imports the consumer) and runs the query module as
#: ``__main__``. Used only by synthetic tests through --consumer-authority; real runs use ``python -m``.
CONSUMER_BOOTSTRAP = ("import contextlib, json, runpy, sys\n"
                      "from aggie_analytics.national_history import availability_query as q\n"
                      "from aggie_analytics.national_source_time import archive as a\n"
                      "spec = json.loads(sys.argv.pop(1))\n"
                      "with contextlib.ExitStack() as stack:\n"
                      "    stack.enter_context(q.registered_authority(spec['availability']))\n"
                      "    if spec.get('archive'):\n"
                      "        arch = dict(spec['archive'])\n"
                      "        data = open(arch.pop('tranche_path'), 'rb').read()\n"
                      "        if 'cohort_path' in arch:\n"
                      "            cohort = open(arch.pop('cohort_path'), 'rb').read()\n"
                      "            auth = a.ExpansionAuthority(tranche_bytes=data, cohort_bytes=cohort, **arch)\n"
                      "        else:\n"
                      "            auth = a.IssuedAuthority(tranche_bytes=data, **arch)\n"
                      "        stack.enter_context(a.registered_authority(auth))\n"
                      "    sys.argv[0] = 'aggie_analytics.national_history.availability_query'\n"
                      "    runpy.run_module('aggie_analytics.national_history.availability_query', run_name='__main__',"
                      " alter_sys=True)\n")


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


def cj(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def ro(path: Path) -> sqlite3.Connection:
    # absolute, not resolved: resolve() may return a Windows extended-length path (\\?\ prefix), not a valid SQLite URI
    text = os.path.abspath(path)
    if text.startswith("\\\\?\\"):
        text = text[4:]
    return sqlite3.connect("file:" + text.replace("\\", "/") + "?mode=ro", uri=True)


class Report:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def check(self, name: str, ok: bool, detail: Any = None) -> bool:
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    def failed(self) -> list[str]:
        return [c["check"] for c in self.checks if not c["ok"]]


# --------------------------------------------------------------------------------------------- time

def day_ok(text: Any) -> bool:
    if not isinstance(text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return False
    try:
        return dt.date.fromisoformat(text).isoformat() == text
    except ValueError:
        return False


def first_instant(day: str) -> dt.datetime:
    """00:00 at UTC+14 of a calendar date, as a UTC instant (the conservative earliest instant of that date)."""
    y, m, d = (int(x) for x in day.split("-"))
    return dt.datetime(y, m, d, tzinfo=dt.timezone(dt.timedelta(hours=14))).astimezone(UTC)


def z(when: dt.datetime) -> str:
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def when_of(bound: str) -> dt.datetime:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.(\d{6})Z", bound)
    return dt.datetime(*(int(m.group(i)) for i in range(1, 8)), tzinfo=UTC)


def cutoff_of(text: str) -> dt.datetime:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})", text)
    if not m:
        raise ValueError(text)
    zone = m.group(8)
    offset = dt.timedelta(0) if zone == "Z" else (1 if zone[0] == "+" else -1) * dt.timedelta(
        hours=int(zone[1:3]), minutes=int(zone[4:6]))
    micro = int((m.group(7) or ".0")[1:].ljust(6, "0"))
    return dt.datetime(*(int(m.group(i)) for i in range(1, 7)), micro, tzinfo=dt.timezone(offset)).astimezone(UTC)


# --------------------------------------------------------------------------------------------- bindings

def is_expansion(contract: dict[str, Any]) -> bool:
    return contract.get("contract_id") == EXPANSION_CONTRACT_ID


def identity_fields(contract: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    """The parent identity fields the content document restates (the expansion's archive binding adds two)."""
    if is_expansion(contract):
        return {**PARENT_IDENTITY_FIELDS, "archive": EXPANSION_ARCHIVE_FIELDS}
    return PARENT_IDENTITY_FIELDS


def manifest_for(db: Path) -> Path:
    root = Path(db).resolve().parent.parent.parent
    return root.parent.parent / "manifests" / root.name / "sha256" / Path(db).resolve().parent.name / "run_manifest.json"


def parent_documents(paths: dict[str, Path], binding: dict[str, Any], report: Report) -> dict[str, dict[str, Any]]:
    """Own re-verification of each parent: directory identity = sha256(identity document) = bound identity; the
    document names the file's own bytes; the contract/content identities equal the binding."""
    docs = {}
    for name, (population, filename, ident_key) in PARENT_FILE.items():
        db = paths[name]
        manifest = json.loads(manifest_for(db).read_text(encoding="utf-8"))
        doc = manifest["identity_document"]
        want = binding[name]
        sha = h_file(db)
        ok = (h_bytes(cj(doc)) == db.resolve().parent.name == manifest["identity"] == want[ident_key]
              and db.name == filename and db.resolve().parent.parent.name == "sha256"
              and (doc.get("outputs") or {}).get(filename) == sha == want["sqlite_sha256"]
              and doc.get("contract_sha256") == want["contract_sha256"])
        if name != "population":
            ok &= doc.get("content_identity") == want["content_identity"]
        else:
            up = doc.get("upstream") or {}
            ok &= (up.get("contest"), up.get("program-season")) == (want["contest_identity"],
                                                                    want["program_season_identity"])
        report.check(f"parent_{name}_identity_document_and_bytes_bound", ok, {"identity": manifest["identity"]})
        docs[name] = doc
    return docs


def verify_bindings(contract: dict[str, Any], path: Path, report: Report) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    pb = contract["parent_binding"]
    doc = json.loads(raw.decode("utf-8"))
    paths = {name: Path(doc[BIND_KEY[name]]["path"]) for name in PARENT_FILE}
    ok = h_bytes(raw) == pb["input_bindings"]["sha256"]
    for name, (_pop, _file, ident_key) in PARENT_FILE.items():
        item = doc[BIND_KEY[name]]
        ok &= item["sha256"] == pb[name]["sqlite_sha256"] and item["identity"] == pb[name][ident_key]
    ok &= doc["archive_contract"]["sha256"] == pb["archive"]["contract_sha256"] == h_file(
        Path(doc["archive_contract"]["path"]))
    ok &= doc["archive_tranche"]["sha256"] == pb["archive"]["tranche_sha256"] == h_file(
        Path(doc["archive_tranche"]["path"]))
    extra: dict[str, Any] = {}
    if is_expansion(contract):
        archive_contract = json.loads(Path(doc["archive_contract"]["path"]).read_text(encoding="utf-8"))
        apb = archive_contract["parent_binding"]
        ok &= doc["archive_cohort"]["sha256"] == pb["archive"]["cohort_sha256"] == h_file(
            Path(doc["archive_cohort"]["path"])) == archive_contract["scope"]["cohort_sha256"]
        ok &= doc["archive_source_bindings"]["sha256"] == apb["source_bindings"]["sha256"] == h_file(
            Path(doc["archive_source_bindings"]["path"]))
        ok &= doc["archive_retained_contract"]["sha256"] == apb["retained_acquisition"]["contract_sha256"] == h_file(
            Path(doc["archive_retained_contract"]["path"]))
        ok &= apb["retained_acquisition"]["identity"] == pb["archive"]["retained_acquisition_identity"] and \
            Path(doc["archive_retained_root"]["path"]).is_dir()
        extra = {"cohort": Path(doc["archive_cohort"]["path"]),
                 "archive_source_bindings": Path(doc["archive_source_bindings"]["path"]),
                 "retained_contract": Path(doc["archive_retained_contract"]["path"]),
                 "retained_root": Path(doc["archive_retained_root"]["path"])}
    report.check("bindings_document_bound_to_contract", ok, {"sha256": h_bytes(raw)})
    return {"paths": paths, "archive_contract": Path(doc["archive_contract"]["path"]),
            "tranche": Path(doc["archive_tranche"]["path"]), "control": Path(doc["control"]["path"]),
            "document": doc, "expansion": is_expansion(contract), **extra}


# --------------------------------------------------------------------------------------------- own population graph

def failing(row: dict[str, Any]) -> list[str]:
    """The Cycle 39 predicates written out again from the contract text (not the producer's code)."""
    checks: list[tuple[bool, str]] = [
        (row["disposition"] == "VERIFIED_PRESENT", "DISPOSITION_NOT_VERIFIED_PRESENT"),
        (row["reconciliation_state"] == "RECONCILED_2016_2023", "RECONCILIATION_NOT_RECONCILED_2016_2023"),
        (row["contest_status"] == "COMPLETED", "STATUS_NOT_COMPLETED"),
        (isinstance(row["competitive"], int) and not isinstance(row["competitive"], bool) and row["competitive"] == 1,
         "NOT_COMPETITIVE")]
    out = [reason for ok, reason in checks if not ok]
    if not day_ok(row["contest_date"]):
        out.append("DATE_INVALID")
    elif row["contest_dates_observed"] is not None:
        seen = row["contest_dates_observed"]
        try:
            seen = json.loads(seen) if isinstance(seen, str) else seen
        except ValueError:
            seen = None
        if not (isinstance(seen, list) and set(seen) == {row["contest_date"]}):
            out.append("DATE_NOT_SINGLE")
    stable = all(isinstance(row[f"{s}_key"], str) and re.fullmatch(r"org:[0-9]+", row[f"{s}_key"]) is not None
                 and row[f"{s}_key"][4:] == str(row[f"{s}_org_id"]) for s in "ab")
    if not stable:
        out.append("ORG_KEY_NOT_STABLE")
    if row["a_key"] == row["b_key"]:
        out.append("ORG_KEYS_NOT_DISTINCT")
    pts = [row["a_points"], row["b_points"]]
    if None in pts:
        out.append("SCORE_MISSING")
    if any(p is not None and (isinstance(p, bool) or not isinstance(p, int) or p < 0) for p in pts):
        out.append("SCORE_NOT_NONNEGATIVE_INTEGER")
    return out


def population_2019(db: Path) -> tuple[dict[str, dict[str, Any]], set[str], int]:
    conn = ro(db)
    conn.row_factory = sqlite3.Row
    rows = {r["contest_key"]: dict(r) for r in conn.execute("SELECT * FROM contest WHERE season = 2019")}
    subset = {r[0] for r in conn.execute("SELECT contest_key FROM subset_membership WHERE subset = "
                                         "'FBS_ESTIMAND_SUBSET'") if r[0] in rows}
    total = conn.execute("SELECT COUNT(*) FROM contest").fetchone()[0]
    conn.close()
    return rows, subset, total


def own_graph(rows: dict[str, dict[str, Any]], subset: set[str]) -> dict[str, Any]:
    """Targets and, for every view, every same-season contest of the team partitioned by date against the target
    (brute force over all 2019 rows, no index)."""
    reasons = {k: failing(r) for k, r in rows.items()}
    targets = sorted((r for k, r in rows.items() if k in subset and not reasons[k]),
                     key=lambda r: (r["contest_date"], r["contest_key"]))
    views = {}
    for t in targets:
        for view, me, them in (("A", "a", "b"), ("B", "b", "a")):
            team = t[f"{me}_key"]
            prior, same, undated, later = [], [], [], 0
            for k, r in rows.items():
                if k == t["contest_key"] or team not in (r["a_key"], r["b_key"]):
                    continue
                side = "A" if r["a_key"] == team else "B"
                opp = r["b_key"] if side == "A" else r["a_key"]
                if not day_ok(r["contest_date"]):
                    undated.append((k, r, opp))
                elif r["contest_date"] < t["contest_date"]:
                    prior.append((k, r, side, opp))
                elif r["contest_date"] == t["contest_date"]:
                    same.append((k, r, opp))
                else:
                    later += 1
            prior.sort(key=lambda x: (x[1]["contest_date"], x[0]))
            views[(t["contest_key"], view)] = {"target": t, "team": team, "opponent": t[f"{them}_key"], "me": me,
                                               "them": them, "prior": prior, "same": sorted(same, key=lambda x: x[0]),
                                               "undated": sorted(undated, key=lambda x: x[0]), "later": later}
    return {"reasons": reasons, "targets": targets, "views": views}


def history_agreement(history_db: Path, graph: dict[str, Any], report: Report) -> None:
    conn = ro(history_db)
    targets = {json.loads(r)["contest_key"]: json.loads(r) for (r,) in conn.execute(
        "SELECT record FROM targets WHERE season = 2019")}
    views = {}
    for (r,) in conn.execute("SELECT record FROM history WHERE season = 2019"):
        rec = json.loads(r)
        views[(rec["target_contest_key"], rec["view"])] = rec
    conn.close()
    mine = {t["contest_key"] for t in graph["targets"]}
    report.check("history_parent_targets_equal_population_derivation", set(targets) == mine,
                 {"population": len(mine), "history": len(targets)})
    bad = []
    for key, v in graph["views"].items():
        rec = views.get(key)
        other = views.get((key[0], "B" if key[1] == "A" else "A"))
        if rec is None or other is None:
            bad.append(key)
            continue
        reasons = graph["reasons"]
        contributing = [{"contest_key": k, "contest_date": r["contest_date"], "side": s, "opponent_key": o,
                         "opponent_division_label": r["b_division_label" if s == "A" else "a_division_label"],
                         "points_for": r["a_points" if s == "A" else "b_points"],
                         "points_against": r["b_points" if s == "A" else "a_points"],
                         "result": "W" if r["a_points" if s == "A" else "b_points"] > r["b_points" if s == "A" else
                                                                                        "a_points"] else
                         ("L" if r["a_points" if s == "A" else "b_points"] < r["b_points" if s == "A" else "a_points"]
                          else "T")}
                        for k, r, s, o in v["prior"] if not reasons[k]]
        excluded = [{"contest_key": k, "contest_date": r["contest_date"], "opponent_key": o, "reasons": reasons[k]}
                    for k, r, _s, o in v["prior"] if reasons[k]]
        excluded += [{"contest_key": k, "contest_date": r["contest_date"], "opponent_key": o,
                      "reasons": reasons[k] + ["SAME_DATE_NOT_STRICTLY_EARLIER"]} for k, r, o in v["same"]]
        excluded += [{"contest_key": k, "contest_date": r["contest_date"], "opponent_key": o, "reasons": reasons[k]}
                     for k, r, o in v["undated"]]
        excluded.sort(key=lambda x: (x["contest_date"] if day_ok(x["contest_date"]) else "", x["contest_key"]))
        for block in (rec["team_history"], other["opponent_history"]):
            if block["contributing"] != contributing or block["excluded_inputs"] != excluded or \
                    block["team_key"] != v["team"]:
                bad.append(key)
    report.check("history_parent_views_equal_population_derivation_both_directions", not bad,
                 {"views": len(graph["views"]), "differing": [list(k) for k in bad[:5]]})


# --------------------------------------------------------------------------------------------- archive truth

def load_oracle(path: Path, sha: str) -> Any:
    if h_file(path) != sha:
        raise SystemExit(f"archive oracle bytes differ from the bound sha256 {sha}")
    spec = importlib.util.spec_from_file_location("bas_c41_independent_archive_oracle", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archive_truth(oracle: Any, bound: dict[str, Any], report: Report) -> dict[str, Any]:
    """The accepted C41 oracle's reconstruction of every archived version from raw bytes, checked against the
    delivered archive sidecar (zero new archive coverage)."""
    contract41 = json.loads(bound["archive_contract"].read_text(encoding="utf-8"))
    archive_db = bound["paths"]["archive"]
    if bound.get("expansion"):
        # BAT-715: the expansion oracle re-verifies both acquisitions, the 97-key union and the retained copy.
        args41 = argparse.Namespace(source_database=bound["paths"]["source_time"],
                                    source_bindings=bound["archive_source_bindings"], tranche=bound["tranche"],
                                    cohort=bound["cohort"], retained_root=bound["retained_root"],
                                    retained_contract=bound["retained_contract"])
    else:
        c41_bindings = bound["control"].parent / "INPUT_BINDINGS.json"
        args41 = argparse.Namespace(source_database=bound["paths"]["source_time"], source_bindings=c41_bindings,
                                    tranche=bound["tranche"])
    r41 = oracle.Report()
    ctx = oracle.verify_inputs(contract41, args41, r41)
    db_manifest = json.loads(manifest_for(archive_db).read_text(encoding="utf-8"))
    content_id = db_manifest["identity_document"]["content_identity"]
    content_manifest = manifest_for(archive_db).parent.parent / content_id / "run_manifest.json"
    ctx["out"] = archive_db.resolve().parent.parent.parent
    content41 = json.loads(content_manifest.read_text(encoding="utf-8"))["identity_document"]
    oracle.verify_acquisition(contract41, ctx, content41, r41)
    delivered41 = oracle.read_delivered(content_manifest, ctx, r41)
    expected = oracle.Expected(contract41, ctx)
    expected.build()
    result = oracle.compare(expected, delivered41["records"])
    r41.check("every_record_reconstructed_independently", oracle.clean(result), result)
    failed = r41.failed()
    report.check("archive_expansion_parent_independently_reconstructed_by_the_bound_expansion_oracle"
                 if bound.get("expansion") else "archive_parent_independently_reconstructed_by_the_c41_oracle",
                 not failed and
                 delivered41["database_identity"] == archive_db.resolve().parent.name,
                 {"oracle_checks": len(r41.checks), "failed": failed,
                  "captures": len(expected.records["captures.jsonl"]),
                  "assertions": len(expected.records["assertions.jsonl"])})
    caps: dict[str, list[dict[str, Any]]] = {}
    for c in expected.records["captures.jsonl"]:
        caps.setdefault(c["contest_key"], []).append(c)
    asr: dict[str, list[dict[str, Any]]] = {}
    for a in expected.records["assertions.jsonl"]:
        asr.setdefault(a["capture_id"], []).append(a)
    return {"dispositions": {d["contest_key"]: d for d in expected.records["dispositions.jsonl"]},
            "captures": caps, "assertions": asr}


def own_evidence_archive(key: str, truth: dict[str, Any]) -> dict[str, Any]:
    disp = truth["dispositions"].get(key)
    if disp is None:
        return {"in_tranche": False, "archive_disposition": None, "acquisition_outcome": None,
                "parent_values_agree": None, "versions": [], "coherent_capture_ids": [],
                "coherent_upper_bound_utc": None, "contradicting_capture_ids": [],
                "field_earliest_qualified_upper_bound_utc": dict.fromkeys(SIX), "evidence_class":
                "NOT_IN_ARCHIVE_TRANCHE", "evidence_reason": "CONTEST_OUTSIDE_THE_ARCHIVE_TRANCHE"}
    versions = []
    for c in truth["captures"].get(key, []):
        clock = c["clocks"]["archive_capture"]
        versions.append({"capture_id": c["capture_id"], "state": c["state"],
                         "quarantine_reasons": list(c["quarantine_reasons"]),
                         "upper_bound_utc": clock["latest_utc"] if clock["state"] == "PRESENT" else None,
                         "field_states": {f: c["field_states"][f] for f in SIX}})
    good = [v for v in versions if v["state"] == "QUALIFIED"]
    clash = [v for v in good if CONTRA & {v["field_states"][f] for f in SIX}]
    whole = [v for v in good if v["upper_bound_utc"] and all(v["field_states"][f] == QUAL for f in SIX)]
    earliest = {f: min((v["upper_bound_utc"] for v in good if v["field_states"][f] == QUAL and v["upper_bound_utc"]),
                       default=None) for f in SIX}
    if not versions:
        cls, why = "ARCHIVE_NO_CAPTURE", "ARCHIVE_DISPOSITION:" + disp["disposition"]
    elif not good:
        cls, why = "ARCHIVE_ALL_VERSIONS_QUARANTINED", "QUARANTINED:" + ",".join(
            sorted({q for v in versions for q in v["quarantine_reasons"]}))
    elif clash:
        cls = "ARCHIVE_VERSION_CONTRADICTS_PARENT"
        why = "CONTRADICTING_VERSIONS:" + ",".join(
            v["capture_id"] + "[" + "/".join(f for f in SIX if v["field_states"][f] in CONTRA) + "]" for v in clash)
    elif whole:
        cls, why = "ARCHIVE_COHERENT_VERSION", "ONE_VERSION_QUALIFIES_ALL_SIX_FIELDS"
    else:
        never = [f for f in SIX if earliest[f] is None]
        cls = "ARCHIVE_PARTIAL_FIELDS_NO_COHERENT_VERSION"
        why = ("FIELDS_NEVER_QUALIFIED_IN_ANY_VERSION:" + "/".join(never)) if never else \
            "EVERY_FIELD_QUALIFIED_ONLY_IN_DIFFERENT_VERSIONS_NOT_COMBINED"
    coherent = cls == "ARCHIVE_COHERENT_VERSION"
    return {"in_tranche": True, "archive_disposition": disp["disposition"],
            "acquisition_outcome": disp["acquisition_outcome"], "parent_values_agree": None, "versions": versions,
            "coherent_capture_ids": [v["capture_id"] for v in whole] if coherent else [],
            "coherent_upper_bound_utc": min(v["upper_bound_utc"] for v in whole) if coherent else None,
            "contradicting_capture_ids": [v["capture_id"] for v in clash],
            "field_earliest_qualified_upper_bound_utc": earliest, "evidence_class": cls, "evidence_reason": why}


# --------------------------------------------------------------------------------------------- own expected records

def labels(contract: dict[str, Any]) -> dict[str, str]:
    return dict(contract["row_labels"])


def own_records(contract: dict[str, Any], graph: dict[str, Any], rows: dict[str, dict[str, Any]],
                truth: dict[str, Any], report: Report) -> dict[str, list[dict[str, Any]]]:
    lab = labels(contract)
    reasons = graph["reasons"]
    out: dict[str, list[dict[str, Any]]] = {n: [] for n in NAMES}
    used: set[str] = set()
    for t in graph["targets"]:
        out["targets.jsonl"].append({
            "record_type": "target", "contest_key": t["contest_key"], "ncaa_contest_id": t["ncaa_contest_id"],
            "season": 2019, "term": t["term"], "contest_date": t["contest_date"], "a_key": t["a_key"],
            "b_key": t["b_key"], "a_org_id": t["a_org_id"], "b_org_id": t["b_org_id"], "a_team_name": t["a_team_name"],
            "b_team_name": t["b_team_name"], "a_division_label": t["a_division_label"],
            "b_division_label": t["b_division_label"], "classification_pair": t["classification_pair"],
            "parent_site": t["site"], "neutral_site_text": t["neutral_site_text"],
            "conservative_date_boundary_utc": z(first_instant(t["contest_date"])), "views": ["A", "B"], **lab})
        for view in ("A", "B"):
            v = graph["views"][(t["contest_key"], view)]
            rels = []
            for k, r, side, opp in v["prior"]:
                used.add(k)
                pool = not reasons[k]
                mine, theirs = ("a", "b") if side == "A" else ("b", "a")
                result = None
                if pool:
                    pf, pa = r[f"{mine}_points"], r[f"{theirs}_points"]
                    result = {"points_for": pf, "points_against": pa,
                              "result": "W" if pf > pa else "L" if pf < pa else "T"}
                rels.append({"record_type": "relationship", "target_contest_key": t["contest_key"], "view": view,
                             "season": 2019, "target_date": t["contest_date"], "team_key": v["team"],
                             "current_opponent_key": v["opponent"], "prior_contest_key": k,
                             "prior_contest_date": r["contest_date"], "prior_side": side, "prior_opponent_key": opp,
                             "prior_opponent_division_label": r[f"{theirs}_division_label"],
                             "prior_classification_pair": r["classification_pair"],
                             "relationship_class": "HISTORY_POOL_PRIOR" if pool else "PARENT_EXCLUDED_PRIOR",
                             "parent_exclusion_reasons": list(reasons[k]), "parent_result": result, **lab})
            pool_n = sum(1 for x in rels if x["relationship_class"] == "HISTORY_POOL_PRIOR")
            me, them = v["me"], v["them"]
            out["views.jsonl"].append({
                "record_type": "view", "target_contest_key": t["contest_key"], "view": view, "season": 2019,
                "target_date": t["contest_date"], "prior_rule": "SAME_SEASON_VALID_DATE_STRICTLY_BEFORE_TARGET_DATE",
                "team_key": v["team"], "team_org_id": t[f"{me}_org_id"], "team_name": t[f"{me}_team_name"],
                "team_division_label": t[f"{me}_division_label"], "opponent_key": v["opponent"],
                "opponent_org_id": t[f"{them}_org_id"], "opponent_name": t[f"{them}_team_name"],
                "opponent_division_label": t[f"{them}_division_label"], "expected_prior_relationships": len(rels),
                "history_pool_priors": pool_n, "parent_excluded_priors": len(rels) - pool_n,
                "relationship_contest_keys": [x["prior_contest_key"] for x in rels],
                "same_date_excluded": [{"contest_key": k, "contest_date": r["contest_date"], "opponent_key": o,
                                        "reasons": reasons[k] + ["SAME_DATE_NOT_STRICTLY_EARLIER"]}
                                       for k, r, o in v["same"]],
                "undated_excluded": [{"contest_key": k, "contest_date": r["contest_date"], "opponent_key": o,
                                      "reasons": list(reasons[k])} for k, r, o in v["undated"]],
                "later_contests_excluded": v["later"],
                "history_state": "HAS_EXPECTED_PRIORS" if rels else "COLD_START_NO_EXPECTED_PRIORS", **lab})
            out["relationships.jsonl"].extend(rels)
    disagreements = []
    for k in sorted(used, key=lambda key: (rows[key]["contest_date"], key)):
        r = rows[k]
        pool = not reasons[k]
        values = {"contest_date": r["contest_date"], "a_participant": r["a_key"], "b_participant": r["b_key"],
                  "completion": r["contest_status"], "a_points": r["a_points"], "b_points": r["b_points"]} if pool \
            else None
        arch = own_evidence_archive(k, truth)
        if arch["in_tranche"] and pool:
            stated = truth["dispositions"][k]["parent_values"]
            agree = all(stated[f] == values[f] for f in SIX) and stated["season"] == 2019
            arch["parent_values_agree"] = agree
            if not agree:
                disagreements.append(k)
        out["evidence.jsonl"].append({
            "record_type": "prior_evidence", "contest_key": k, "season": 2019, "contest_date": r["contest_date"],
            "a_key": r["a_key"], "b_key": r["b_key"], "classification_pair": r["classification_pair"],
            "history_pool_member": pool, "parent_exclusion_reasons": list(reasons[k]), "parent_values": values,
            "earliest_event_instant_utc": z(first_instant(r["contest_date"])), "archive": arch, **lab})
        for v in arch["versions"]:
            for a in truth["assertions"].get(v["capture_id"], []):
                if a["field"] in SIX:
                    out["witnesses.jsonl"].append({
                        "record_type": "field_witness", "contest_key": k, "capture_id": v["capture_id"],
                        "capture_state": v["state"], "upper_bound_utc": v["upper_bound_utc"], "field": a["field"],
                        "witness": a["witness"], "witness_span": list(a["witness_span"]), "literal": a["literal"],
                        "value": a["value"], "corroboration": a["corroboration"], "field_state": a["field_state"],
                        **lab})
    report.check("archive_parent_values_equal_population_for_every_tranche_prior", not disagreements, disagreements)
    return out


# --------------------------------------------------------------------------------------------- delivered

def delivered(manifest: Path, report: Report) -> dict[str, Any]:
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    content = doc["identity_document"]
    identity = h_bytes(cj(content))
    report.check("content_identity_recomputes", identity == doc["identity"] == manifest.parent.name)
    data_dir = manifest.parent.parent.parent.parent.parent / "canonical" / manifest.parent.parent.parent.name / \
        "sha256" / identity
    lines: dict[str, bytes] = {}
    for name in NAMES:
        packed = (data_dir / f"{name}.gz").read_bytes()
        raw = gzip.decompress(packed)
        report.check(f"payload_{name}_stored_and_semantic_hashes", h_bytes(packed) == content["outputs"][f"{name}.gz"]
                     and h_bytes(raw) == content["semantic_outputs"][name] and
                     raw.count(b"\n") == content["row_counts"][name])
        lines[name] = raw
    db_id = doc["provenance"]["database_identity"]
    db_doc_full = json.loads((manifest.parent.parent / db_id / "run_manifest.json").read_text(encoding="utf-8"))
    db_doc = db_doc_full["identity_document"]
    db_path = data_dir.parent / db_id / "national_history_availability.sqlite"
    report.check("database_identity_recomputes", h_bytes(cj(db_doc)) == db_id == db_doc_full["identity"] and
                 db_doc["content_identity"] == identity and h_file(db_path) == db_doc["outputs"][db_path.name] and
                 db_doc["parent"] == content["parent"] and db_doc["contract_sha256"] == content["contract_sha256"])
    conn = ro(db_path)
    rows = {n: b"".join(r[0].encode("utf-8") + b"\n" for r in conn.execute(
        f"SELECT record FROM {TABLE_OF[n]} ORDER BY ord")) for n in NAMES}
    meta = dict(conn.execute("SELECT key, value FROM meta"))
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in
              ("meta", "targets", "views", "relationships", "evidence", "witnesses")}
    conn.close()
    report.check("database_rows_equal_payload_lines", all(rows[n] == lines[n] for n in NAMES))
    report.check("database_meta_and_counts_bind_content", meta.get("content_identity") == identity and
                 json.loads(meta["parent"]) == content["parent"] and counts == db_doc["table_counts"] and
                 json.loads(meta["row_labels"]) is not None)
    return {"content": content, "content_identity": identity, "database_identity": db_id, "database": db_path,
            "meta": meta, "records": {n: [json.loads(x) for x in lines[n].splitlines()] for n in NAMES}}


def gzip_mtime0(data: bytes) -> bytes:
    out = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=out, mtime=0, compresslevel=9) as stream:
        stream.write(data)
    return out.getvalue()


def expected_content(contract: dict[str, Any], contract_sha: str, expected: dict[str, list[dict]]) -> dict[str, Any]:
    """The content identity document and identity this tool expects, from the contract and its own reconstructed records
    (canonical JSONL in payload order); nothing is copied from the delivered documents."""
    lines = {n: b"".join(cj(r) + b"\n" for r in expected[n]) for n in NAMES}
    document = {"schema": CONTENT_SCHEMA, "stage": CONTENT_STAGE, "population": contract["population_id"],
                "contract_id": contract["contract_id"], "contract_sha256": contract_sha,
                "parent": {n: {k: contract["parent_binding"][n][k] for k in keys}
                           for n, keys in identity_fields(contract).items()},
                "payload_schema": contract["payloads"]["schema_version"], "payload_encoding": PAYLOAD_ENCODING,
                "semantic_outputs": {n: h_bytes(lines[n]) for n in NAMES},
                "outputs": {f"{n}.gz": h_bytes(gzip_mtime0(lines[n])) for n in NAMES},
                "row_counts": {n: len(expected[n]) for n in NAMES}}
    return {"document": document, "identity": h_bytes(cj(document))}


def meta_json(value: Any) -> Any:
    try:
        return json.loads(value) if isinstance(value, str) else value
    except ValueError:
        return value


def content_binding_challenges(own: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Content-binding claims the oracle must tell from its own expected identity: genuine agrees; invented, missing,
    another real identity and a self-consistent alternative document (its own hash claimed) are detected."""
    alternative = dict(own["document"], payload_schema=own["document"]["payload_schema"] + "-ADMITTED")
    claims = [("genuine_recomputed", own["identity"], False), ("invented", "f" * 64, True), ("missing", None, True),
              ("another_real_identity", contract["parent_binding"]["archive"]["content_identity"], True),
              ("self_consistent_alternative_document", h_bytes(cj(alternative)), True)]
    return [{"challenge": name, "claim": claim, "detected": claim != own["identity"],
             "as_expected": (claim != own["identity"]) == should} for name, claim, should in claims]


NATURAL: dict[str, Callable[[dict[str, Any]], tuple]] = {
    "targets.jsonl": lambda r: (r.get("contest_key"),),
    "views.jsonl": lambda r: (r.get("target_contest_key"), r.get("view")),
    "relationships.jsonl": lambda r: (r.get("target_contest_key"), r.get("view"), r.get("prior_contest_key")),
    "evidence.jsonl": lambda r: (r.get("contest_key"),),
    "witnesses.jsonl": lambda r: (r.get("capture_id"), r.get("field"), r.get("witness"),
                                  tuple(r.get("witness_span") or ())),
}


def compare(expected: dict[str, list[dict]], got: dict[str, list[dict]]) -> dict[str, Any]:
    out = {}
    for name in NAMES:
        key = NATURAL[name]
        want = {}
        for r in expected[name]:
            want.setdefault(key(r), []).append(r)
        have = {}
        for r in got[name]:
            have.setdefault(key(r), []).append(r)
        missing = sorted(set(want) - set(have))
        extra = sorted(set(have) - set(want))
        dup = sorted(k for k, v in have.items() if len(v) > 1)
        fields: dict[str, int] = {}
        first = []
        for k in set(want) & set(have):
            a, b = want[k][0], have[k][0]
            if cj(a) != cj(b):
                diff = sorted(f for f in set(a) | set(b) if cj(a.get(f)) != cj(b.get(f)))
                for f in diff:
                    fields[f] = fields.get(f, 0) + 1
                if len(first) < 5:
                    first.append({"key": list(k), "fields": diff[:8]})
        order_ok = [key(r) for r in got[name]] == [key(r) for r in expected[name]]
        out[name] = {"expected": len(expected[name]), "delivered": len(got[name]), "missing": len(missing),
                     "extra": len(extra), "duplicated": len(dup), "field_mismatch_counts": fields,
                     "order_equal": order_ok, "first": first, "missing_head": [list(k) for k in missing[:3]],
                     "extra_head": [list(k) for k in extra[:3]]}
    return out


def clean(result: dict[str, Any]) -> bool:
    return all(v["missing"] == v["extra"] == v["duplicated"] == 0 and not v["field_mismatch_counts"] and
               v["order_equal"] and v["expected"] == v["delivered"] for v in result.values())


# --------------------------------------------------------------------------------------------- own decisions

def my_decide(rel: dict[str, Any], ev: dict[str, Any], cut: dt.datetime, contract: dict[str, Any]) -> dict[str, Any]:
    reasons = contract["cutoff"]["decision_reasons"]
    if rel["relationship_class"] == "PARENT_EXCLUDED_PRIOR":
        return {"support_state": "EXCLUDED_FROM_HISTORY_POOL", "result_published_by_cutoff": None,
                "reason_class": "PARENT_EXCLUDED_PRIOR",
                "reason": "PARENT_EXCLUDED:" + ",".join(rel["parent_exclusion_reasons"]), "supporting_capture_ids": []}
    a = ev["archive"]
    if a["evidence_class"] != "ARCHIVE_COHERENT_VERSION":
        return {"support_state": "UNSUPPORTED", "result_published_by_cutoff":
                "UNKNOWN" if a["evidence_class"] == "ARCHIVE_VERSION_CONTRADICTS_PARENT" else
                "NO_QUALIFIED_ARCHIVE_ASSERTION", "reason_class": a["evidence_class"], "reason": a["evidence_reason"],
                "supporting_capture_ids": []}
    ok = [v["capture_id"] for v in a["versions"] if v["capture_id"] in a["coherent_capture_ids"] and
          when_of(v["upper_bound_utc"]) <= cut]
    if ok:
        cls, why, pub = reasons["SUPPORTED"]
        return {"support_state": "SUPPORTED", "result_published_by_cutoff": pub, "reason_class": cls, "reason": why,
                "supporting_capture_ids": ok}
    key = "OUTCOME_CANNOT_EXIST_BEFORE_PRIOR_EVENT_DATE" if cut < first_instant(rel["prior_contest_date"]) else \
        "ARCHIVE_UPPER_BOUND_AFTER_CUTOFF"
    cls, why, pub = reasons[key]
    return {"support_state": "UNSUPPORTED", "result_published_by_cutoff": pub, "reason_class": cls, "reason": why,
            "supporting_capture_ids": []}


def my_summary(team: str, rels: list[dict[str, Any]], evidence: dict[str, dict], cut: dt.datetime,
               contract: dict[str, Any]) -> dict[str, Any]:
    agg = contract["aggregates"]
    decided = [(r, my_decide(r, evidence[r["prior_contest_key"]], cut, contract)) for r in rels]
    sup = [r for r, d in decided if d["support_state"] == "SUPPORTED"]
    pool = sum(1 for r in rels if r["relationship_class"] == "HISTORY_POOL_PRIOR")
    by = dict.fromkeys(agg["unsupported_reason_classes"], 0)
    for _r, d in decided:
        if d["support_state"] == "UNSUPPORTED":
            by[d["reason_class"]] += 1
    res = [r["parent_result"] for r in sup]
    pf, pa, n = sum(x["points_for"] for x in res), sum(x["points_against"] for x in res), len(res)
    wins = sum(x["result"] == "W" for x in res)

    def frac(num: int) -> dict[str, int] | None:
        return {"numerator": num, "denominator": n} if n else None
    state = ("COLD_START_NO_EXPECTED_PRIORS" if not rels else "ALL_EXPECTED_PRIORS_SUPPORTED" if n == len(rels) else
             "NO_SUPPORTED_PRIORS" if n == 0 else "PARTIAL_SUPPORTED_SUBSET")
    return {"team_key": team, "expected_prior_relationships": len(rels), "history_pool_priors": pool,
            "parent_excluded_priors": len(rels) - pool, "supported_priors": n, "unsupported_priors": pool - n,
            "unsupported_by_reason_class": by, "completeness_state": state,
            "supported_subset_is_complete_history": n == len(rels),
            "supported_subset": {"games": n, "wins": wins, "losses": sum(x["result"] == "L" for x in res),
                                 "ties": sum(x["result"] == "T" for x in res), "points_for_total": pf,
                                 "points_against_total": pa, "margin_total": pf - pa, "win_rate": frac(wins),
                                 "points_for_mean": frac(pf), "points_against_mean": frac(pa),
                                 "margin_mean": frac(pf - pa), "contributing_contest_keys":
                                 [r["prior_contest_key"] for r in sup],
                                 "rate_scope": "SUPPORTED_SUBSET_ONLY_NOT_FULL_HISTORY", "imputation": "NONE"}}


def my_position(day: str, cut: dt.datetime, contract: dict[str, Any]) -> dict[str, Any]:
    boundary = first_instant(day)
    c = contract["cutoff"]
    return {"conservative_date_boundary_utc": z(boundary), "position": c["positions"][0 if cut < boundary else 1],
            "boundary_basis": c["boundary_basis"], "use": c["use"], "pregame_claim": False,
            "pit_admission": "NOT_ADMITTED"}


def run_consumer(args: argparse.Namespace, bound: dict[str, Any], db: Path, argv: list[str]) -> tuple[int, Any, str]:
    parents = ["--population-database", str(bound["paths"]["population"]), "--history-database",
               str(bound["paths"]["history"]), "--source-time-database", str(bound["paths"]["source_time"]),
               "--archive-database", str(bound["paths"]["archive"])]
    full = ["--database", str(db), *parents, *argv]
    if args.consumer_authority:
        spec = Path(args.consumer_authority).read_text(encoding="utf-8")
        cmd = [sys.executable, "-B", "-c", CONSUMER_BOOTSTRAP, spec, *full]
    else:
        cmd = [sys.executable, "-B", "-m", "aggie_analytics.national_history.availability_query", *full]
    env = dict(os.environ)
    if args.consumer_source_root:
        env["PYTHONPATH"] = os.pathsep.join([str(args.consumer_source_root), *[p for p in [env.get("PYTHONPATH")] if p]])
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False, env=env)
    return proc.returncode, (json.loads(proc.stdout) if proc.stdout.strip() else None), proc.stderr


def consumer_checks(args: argparse.Namespace, contract: dict[str, Any], bound: dict[str, Any], dl: dict[str, Any],
                    expected: dict[str, list[dict]], report: Report, own_identity: str) -> dict[str, Any]:
    evidence = {e["contest_key"]: e for e in expected["evidence.jsonl"]}
    by_view: dict[tuple[str, str], list[dict]] = {}
    for r in expected["relationships.jsonl"]:
        by_view.setdefault((r["target_contest_key"], r["view"]), []).append(r)
    team = {(v["target_contest_key"], v["view"]): v["team_key"] for v in expected["views.jsonl"]}
    probes = list(contract.get("validator", {}).get("probe_cutoffs") or [])
    dates = sorted({t["contest_date"] for t in expected["targets.jsonl"]})
    out: dict[str, Any] = {"global": {}, "per_date_boundary": {}, "relationship_decisions": {}}
    mismatched: list[Any] = []

    def compare_views(cutoff: str, rows: list[dict], keep: Callable[[dict], bool]) -> int:
        cut = cutoff_of(cutoff)
        n = 0
        for row in rows:
            v = row["view"]
            if not keep(v):
                continue
            k, other = (v["target_contest_key"], v["view"]), (v["target_contest_key"], "B" if v["view"] == "A" else "A")
            want_team = my_summary(team[k], by_view.get(k, []), evidence, cut, contract)
            want_opp = my_summary(team[other], by_view.get(other, []), evidence, cut, contract)
            if row["team_history"] != want_team or row["opponent_history"] != want_opp or \
                    row["cutoff_position"] != my_position(v["target_date"], cut, contract) or \
                    row["opponent_history"]["team_key"] != v["opponent_key"]:
                mismatched.append([cutoff, list(k)])
            n += 1
        return n
    served: list[dict[str, Any]] = []
    for cutoff in probes:
        code, doc, err = run_consumer(args, bound, dl["database"], ["--grain", "history", "--all", "--cutoff", cutoff])
        if code != 0:
            mismatched.append([cutoff, "exit", code, err[-300:]])
            continue
        served.append(doc.get("binding") or {})
        n = compare_views(cutoff, doc["rows"], lambda v: True)
        out["global"][cutoff] = {"views_compared": n, "total": doc["total"]}
    census = 0
    for day in dates:
        cutoff = z(first_instant(day))
        code, doc, err = run_consumer(args, bound, dl["database"], ["--grain", "history", "--all", "--cutoff", cutoff])
        if code != 0:
            mismatched.append([cutoff, "exit", code, err[-300:]])
            continue
        served.append(doc.get("binding") or {})
        n = compare_views(cutoff, doc["rows"], lambda v, d=day: v["target_date"] == d)
        supported = sum(row["team_history"]["supported_priors"] for row in doc["rows"] if row["view"]["target_date"] == day)
        census += supported
        out["per_date_boundary"][day] = {"views_compared": n, "supported_team_priors": supported}
    out["supported_at_each_target_conservative_boundary"] = census
    rel_probe = (contract.get("validator", {}).get("relationship_probe_cutoffs") or probes[:1])
    for cutoff in rel_probe:
        code, doc, err = run_consumer(args, bound, dl["database"], ["--grain", "relationship", "--all", "--cutoff",
                                                                    cutoff])
        if code != 0:
            mismatched.append([cutoff, "relationship exit", code, err[-300:]])
            continue
        served.append(doc.get("binding") or {})
        cut = cutoff_of(cutoff)
        bad = 0
        for row, rel in zip(doc["rows"], expected["relationships.jsonl"]):
            want = my_decide(rel, evidence[rel["prior_contest_key"]], cut, contract)
            got = {k: row["decision"][k] for k in contract["cutoff"]["decision_fields"]}
            if row["relationship"] != rel or got != want:
                bad += 1
        bad += abs(len(doc["rows"]) - len(expected["relationships.jsonl"]))
        out["relationship_decisions"][cutoff] = {"rows": len(doc["rows"]), "mismatched": bad}
        if bad:
            mismatched.append([cutoff, "relationship decisions", bad])
    report.check("consumer_views_and_decisions_equal_own_recomputation", not mismatched and bool(out["global"]),
                 {"mismatched": mismatched[:10], "probes": len(probes), "dates": len(dates)})
    wrong = [b for b in served if b.get("content_identity") != own_identity or
             b.get("database_identity") != dl["database_identity"]]
    out["served_bindings"] = {"responses": len(served), "content_identities": sorted({str(b.get("content_identity"))
                                                                                        for b in served})}
    report.check("consumer_binding_content_identity_equals_independent_digest", bool(served) and not wrong,
                 {"responses": len(served), "differing": wrong[:3], "expected": own_identity})
    return out


# --------------------------------------------------------------------------------------------- tampers

def tamper_cases(expected: dict[str, list[dict]], dl: dict[str, Any]) -> list[dict[str, Any]]:
    """Coordinated semantic changes to copies of the delivered records, as if every outer hash and count were
    recomputed; each must be detected by the field-by-field comparison in its intended payload and field."""
    base = dl["records"]
    cases: list[dict[str, Any]] = []

    def run(name: str, payload: str, field: str | None, mutate: Callable[[dict[str, list[dict]]], bool]) -> None:
        records = copy.deepcopy(base)
        applied = mutate(records)
        result = compare(expected, records) if applied else None
        hit = None
        if result is not None:
            r = result[payload]
            if field is None:
                hit = r["missing"] + r["extra"] + r["duplicated"] > 0 or not r["order_equal"]
            else:
                hit = r["field_mismatch_counts"].get(field, 0) > 0
        cases.append({"case": name, "applied": applied, "payload": payload, "intended_field": field,
                      "rejected_for_intended_cause": bool(hit), "rejected": bool(result is not None and not clean(result))})

    def pick(records: dict[str, list[dict]], pred: Callable[[dict], bool], name: str = "relationships.jsonl"):
        return next((r for r in records[name] if pred(r)), None)

    pool = lambda r: r["relationship_class"] == "HISTORY_POOL_PRIOR"  # noqa: E731
    run("relationship_omitted", "relationships.jsonl", None,
        lambda d: bool(d["relationships.jsonl"].pop(next(i for i, r in enumerate(d["relationships.jsonl"]) if pool(r)))))
    run("relationship_duplicated", "relationships.jsonl", None,
        lambda d: d["relationships.jsonl"].insert(0, copy.deepcopy(d["relationships.jsonl"][0])) is None)

    def wrong_child(d: dict[str, list[dict]]) -> bool:
        r = pick(d, lambda x: pool(x) and x["prior_contest_key"] != x["target_contest_key"])
        others = [e["contest_key"] for e in d["evidence.jsonl"] if e["contest_key"] != r["prior_contest_key"]]
        r["prior_contest_key"] = others[0]
        return True
    run("valid_parent_wrong_child", "relationships.jsonl", None, wrong_child)

    def swapped(d: dict[str, list[dict]]) -> bool:
        r = pick(d, lambda x: pool(x) and x["parent_result"]["points_for"] != x["parent_result"]["points_against"])
        pr = r["parent_result"]
        r["prior_side"] = "B" if r["prior_side"] == "A" else "A"
        pr["points_for"], pr["points_against"] = pr["points_against"], pr["points_for"]
        pr["result"] = {"W": "L", "L": "W", "T": "T"}[pr["result"]]
        return True
    run("swapped_team_score_orientation", "relationships.jsonl", "parent_result", swapped)

    def reintroduce(later: bool) -> Callable[[dict[str, list[dict]]], bool]:
        def mutate(d: dict[str, list[dict]]) -> bool:
            r = copy.deepcopy(pick(d, pool))
            r["prior_contest_key"] = r["target_contest_key"] if not later else "ncaa:999999999"
            r["prior_contest_date"] = r["target_date"] if not later else "2019-12-31"
            d["relationships.jsonl"].append(r)
            return True
        return mutate
    run("same_day_target_reintroduced", "relationships.jsonl", None, reintroduce(False))
    run("future_game_reintroduced", "relationships.jsonl", None, reintroduce(True))

    def date_changed(d: dict[str, list[dict]]) -> bool:
        r = pick(d, pool)
        r["prior_contest_date"] = "2019-01-01"
        return True
    run("prior_date_changed", "relationships.jsonl", "prior_contest_date", date_changed)

    def target_date(d: dict[str, list[dict]]) -> bool:
        d["targets.jsonl"][0]["contest_date"] = "2019-01-02"
        return True
    run("target_date_changed", "targets.jsonl", "contest_date", target_date)

    def field_missing(d: dict[str, list[dict]]) -> bool:
        del pick(d, pool)["parent_result"]
        return True
    run("whole_field_missing", "relationships.jsonl", "parent_result", field_missing)

    def evidence_edit(cls: str, change: Callable[[dict], None]) -> Callable[[dict[str, list[dict]]], bool]:
        def mutate(d: dict[str, list[dict]]) -> bool:
            e = pick(d, lambda x: x["archive"]["evidence_class"] == cls, "evidence.jsonl")
            if e is None:
                return False
            change(e["archive"])
            return True
        return mutate

    def promote(a: dict) -> None:
        bounds = [b for b in a["field_earliest_qualified_upper_bound_utc"].values() if b]
        a["evidence_class"] = "ARCHIVE_COHERENT_VERSION"
        a["evidence_reason"] = "ONE_VERSION_QUALIFIES_ALL_SIX_FIELDS"
        a["coherent_capture_ids"] = [a["versions"][-1]["capture_id"]]
        a["coherent_upper_bound_utc"] = max(bounds) if bounds else a["versions"][-1]["upper_bound_utc"]
    run("old_and_corrected_versions_mixed", "evidence.jsonl", "archive",
        evidence_edit("ARCHIVE_PARTIAL_FIELDS_NO_COHERENT_VERSION", promote))

    def scores_from_parent(a: dict) -> None:
        for v in a["versions"]:
            for f in ("completion", "a_points", "b_points"):
                v["field_states"][f] = "QUALIFIED_AGREES_WITH_PARENT"
    run("unsupported_score_supplied_from_parent", "evidence.jsonl", "archive",
        evidence_edit("ARCHIVE_PARTIAL_FIELDS_NO_COHERENT_VERSION", scores_from_parent))

    def no_capture_promoted(a: dict) -> None:
        a["versions"] = [{"capture_id": "wayback:20190101000000:" + "0" * 64, "state": "QUALIFIED",
                          "quarantine_reasons": [], "upper_bound_utc": "2019-01-01T00:00:00.999999Z",
                          "field_states": dict.fromkeys(SIX, QUAL)}]
        promote(a)
    run("missing_capture_promoted", "evidence.jsonl", "archive", evidence_edit("ARCHIVE_NO_CAPTURE", no_capture_promoted))

    def precision(a: dict) -> None:
        bound = when_of(a["coherent_upper_bound_utc"]) - dt.timedelta(microseconds=1)
        a["coherent_upper_bound_utc"] = z(bound)
    run("coherent_bound_moved_one_microsecond", "evidence.jsonl", "archive",
        evidence_edit("ARCHIVE_COHERENT_VERSION", precision))

    def forged_reason(a: dict) -> None:
        a["evidence_reason"] = "ONE_VERSION_QUALIFIES_ALL_SIX_FIELDS"
    run("forged_reason_label", "evidence.jsonl", "archive", evidence_edit("NOT_IN_ARCHIVE_TRANCHE", forged_reason))

    def excluded_promoted(d: dict[str, list[dict]]) -> bool:
        r = pick(d, lambda x: x["relationship_class"] == "PARENT_EXCLUDED_PRIOR")
        if r is None:
            return False
        r["relationship_class"] = "HISTORY_POOL_PRIOR"
        r["parent_exclusion_reasons"] = []
        return True
    run("parent_excluded_prior_promoted", "relationships.jsonl", "relationship_class", excluded_promoted)

    def counts(d: dict[str, list[dict]]) -> bool:
        v = d["views.jsonl"][0]
        v["history_pool_priors"] += 1
        v["expected_prior_relationships"] += 1
        return True
    run("altered_view_counts", "views.jsonl", "history_pool_priors", counts)

    def cold_start(d: dict[str, list[dict]]) -> bool:
        v = pick(d, lambda x: x["expected_prior_relationships"] > 0, "views.jsonl")
        v["history_state"] = "COLD_START_NO_EXPECTED_PRIORS"
        return True
    run("forged_completeness_state", "views.jsonl", "history_state", cold_start)

    def pit(d: dict[str, list[dict]]) -> bool:
        d["relationships.jsonl"][0]["pit_admission"] = "ADMITTED"
        return True
    run("forged_pit_label", "relationships.jsonl", "pit_admission", pit)

    def witness(d: dict[str, list[dict]]) -> bool:
        if not d["witnesses.jsonl"]:
            return False
        w = d["witnesses.jsonl"][0]
        w["field_state"] = "QUALIFIED_AGREES_WITH_PARENT" if w["field_state"] != QUAL else "CONFLICTS_WITH_PARENT"
        return True
    run("forged_witness_state", "witnesses.jsonl", "field_state", witness)

    def stale(d: dict[str, list[dict]]) -> bool:
        d["evidence.jsonl"][0]["earliest_event_instant_utc"] = "2019-01-01T00:00:00.000000Z"
        return True
    run("changed_event_boundary", "evidence.jsonl", "earliest_event_instant_utc", stale)
    return cases


def challenges(expected: dict[str, list[dict]], graph: dict[str, Any], rows: dict[str, dict], truth: dict[str, Any],
               contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Challenge this oracle's own rules: wrong rules must change results where the data can show it."""
    out = []
    evidence = {e["contest_key"]: e for e in expected["evidence.jsonl"]}
    rels = expected["relationships.jsonl"]
    late = cutoff_of("2026-10-05T00:00:00Z")
    supported = sum(1 for r in rels if my_decide(r, evidence[r["prior_contest_key"]], late, contract)["support_state"]
                    == "SUPPORTED")
    combined = 0
    for r in rels:
        a = evidence[r["prior_contest_key"]]["archive"]
        if r["relationship_class"] == "HISTORY_POOL_PRIOR" and a["in_tranche"] and \
                all(a["field_earliest_qualified_upper_bound_utc"][f] for f in SIX):
            combined += 1
    out.append({"challenge": "cross_version_combination_would_change_support_where_versions_split",
                "own_rule_supported_at_late_cutoff": supported, "combined_rule_supported": combined,
                "as_expected": combined >= supported,
                "note": "equal counts mean no tranche key has its fields split across versions"})
    same_day = sum(len(v["same"]) for v in graph["views"].values())
    out.append({"challenge": "same_day_contests_are_never_relationships", "same_day_listed": same_day,
                "as_expected": all(r["prior_contest_date"] < r["target_date"] for r in rels)})
    offset = cutoff_of("2019-09-01T21:00:50.999999-04:00")
    out.append({"challenge": "offset_cutoff_compared_as_instant_not_text",
                "as_expected": offset == cutoff_of("2019-09-02T01:00:50.999999Z") and
                "2019-09-01T21:00:50.999999-04:00" < "2019-09-02T01:00:50.999999Z"})
    fcs = sum(1 for r in rels if r["prior_opponent_division_label"] != "FBS")
    out.append({"challenge": "fcs_and_outside_opponents_kept_in_the_expected_graph", "non_fbs_opponent_priors": fcs,
                "as_expected": fcs > 0})
    tranche_refs = sum(1 for r in rels if evidence[r["prior_contest_key"]]["archive"]["in_tranche"])
    from_graph = sum(len(v["prior"]) for v in graph["views"].values())
    out.append({"challenge": "archive_tranche_is_numerator_not_denominator", "relationships": len(rels),
                "expected_from_population_graph_without_archive": from_graph, "referencing_tranche": tranche_refs,
                "as_expected": len(rels) == from_graph and tranche_refs <= len(rels)})
    return out


# --------------------------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("contract", "input-bindings", "manifest", "report"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--consumer-authority", type=Path, default=None,
                        help="test hook: a synthetic authority the consumer subprocess registers for itself")
    parser.add_argument("--skip-consumer", action="store_true", help="test hook: no consumer subprocess")
    parser.add_argument("--consumer-source-root", type=Path, default=None,
                        help="a source root prepended to the consumer subprocess PYTHONPATH (the lane sets it already)")
    args = parser.parse_args(argv)
    if args.report.exists():
        raise SystemExit("the report path already exists (written once)")
    report = Report()
    raw = args.contract.read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    contract_sha = h_bytes(raw)
    oracle_spec = contract["validator"]["archive_oracle"]
    oracle_path = Path(__file__).resolve().parents[1] / oracle_spec["module"]
    report.check("contract_closed_schema_and_labels", (contract["contract_id"].startswith("BAT-714-") or (
        is_expansion(contract) and contract["population_id"] == EXPANSION_POPULATION)) and
                 set(contract["row_labels"].values()) >= {"NOT_ADMITTED", "NOT_ELIGIBLE_NOT_ADMITTED"} and
                 contract["evidence"]["fields"] == SIX and contract["scope"]["season"] == 2019)
    bound = verify_bindings(contract, args.input_bindings, report)
    parent_documents(bound["paths"], contract["parent_binding"], report)
    oracle = load_oracle(oracle_path, oracle_spec["sha256"])
    report.check("archive_oracle_bytes_equal_the_bound_accepted_oracle", h_file(oracle_path) == oracle_spec["sha256"])
    rows, subset, parent_rows = population_2019(bound["paths"]["population"])
    report.check("subset_equals_both_fbs_for_every_2019_row", all(
        (k in subset) == (r["a_division_label"] == "FBS" and r["b_division_label"] == "FBS") for k, r in rows.items()))
    graph = own_graph(rows, subset)
    history_agreement(bound["paths"]["history"], graph, report)
    truth = archive_truth(oracle, bound, report)
    expected = own_records(contract, graph, rows, truth, report)
    dl = delivered(args.manifest, report)
    report.check("content_binds_contract_and_parents", dl["content"]["contract_sha256"] == contract_sha and
                 all(dl["content"]["parent"][n][k] == contract["parent_binding"][n][k]
                     for n in PARENT_FILE for k in dl["content"]["parent"][n]) and
                 dl["content"]["contract_id"] == contract["contract_id"])
    result = compare(expected, dl["records"])
    report.check("every_delivered_record_equals_independent_reconstruction", clean(result), result)
    report.check("labels_on_every_record", all(all(r.get(k) == v for k, v in contract["row_labels"].items())
                                                for n in NAMES for r in dl["records"][n]))
    own = expected_content(contract, contract_sha, expected)
    report.check("content_identity_equals_independent_expected_digest", dl["content_identity"] == own["identity"],
                 {"expected": own["identity"], "delivered": dl["content_identity"],
                  "differing_fields": sorted(k for k in set(own["document"]) | set(dl["content"])
                                             if own["document"].get(k) != dl["content"].get(k))})
    declared = {"content_identity": dl["meta"].get("content_identity"),
                "payload_schema": dl["meta"].get("payload_schema"),
                "payload_sha256": meta_json(dl["meta"].get("payload_sha256")),
                "row_counts": meta_json(dl["meta"].get("row_counts"))}
    defined = {"content_identity": own["identity"], "payload_schema": own["document"]["payload_schema"],
               "payload_sha256": own["document"]["semantic_outputs"], "row_counts": own["document"]["row_counts"]}
    report.check("database_meta_restates_the_independent_content_document", declared == defined,
                 sorted(k for k in defined if declared[k] != defined[k]))
    binding_challenges = content_binding_challenges(own, contract)
    report.check("content_binding_claims_told_apart_from_the_expected_identity",
                 all(c["as_expected"] for c in binding_challenges),
                 [c["challenge"] for c in binding_challenges if not c["as_expected"]])
    decisions = {"skipped": True} if args.skip_consumer else consumer_checks(args, contract, bound, dl, expected, report,
                                                                             own["identity"])
    tampers = tamper_cases(expected, dl)
    applied = [t for t in tampers if t["applied"]]
    report.check("every_applicable_tamper_rejected_for_its_intended_cause", len(applied) >= 15 and all(
        t["rejected_for_intended_cause"] for t in applied),
        {"applied": len(applied), "not_applicable": [t["case"] for t in tampers if not t["applied"]],
         "missed": [t["case"] for t in applied if not t["rejected_for_intended_cause"]]})
    oracle_challenges = challenges(expected, graph, rows, truth, contract)
    report.check("oracle_self_challenges_as_expected", all(c["as_expected"] for c in oracle_challenges),
                 [c["challenge"] for c in oracle_challenges if not c["as_expected"]])
    rels = expected["relationships.jsonl"]
    tally: dict[str, int] = {}
    for e in expected["evidence.jsonl"]:
        tally[e["archive"]["evidence_class"]] = tally.get(e["archive"]["evidence_class"], 0) + 1
    views = expected["views.jsonl"]
    tranche = {e["contest_key"] for e in expected["evidence.jsonl"] if e["archive"]["in_tranche"]}
    failed = report.failed()
    doc = {"tool": "tools/validate_national_history_availability.py", "tool_sha256": h_file(Path(__file__)),
           "result": "PASS" if not failed else "FAIL", "failed_checks": failed, "checks": report.checks,
           "contract_sha256": contract_sha, "content_identity": dl["content_identity"],
           "database_identity": dl["database_identity"],
           "content_binding": {"expected_identity": own["identity"], "expected_document": own["document"],
                               "challenges": binding_challenges},
           "counts": {"population_rows_total": parent_rows, "population_rows_2019": len(rows),
                      "targets": len(expected["targets.jsonl"]), "views": len(views), "relationships": len(rels),
                      "history_pool_relationships": sum(r["relationship_class"] == "HISTORY_POOL_PRIOR" for r in rels),
                      "parent_excluded_relationships": sum(r["relationship_class"] == "PARENT_EXCLUDED_PRIOR"
                                                           for r in rels),
                      "cold_start_views": sum(v["history_state"] == "COLD_START_NO_EXPECTED_PRIORS" for v in views),
                      "views_with_parent_excluded_priors": sum(v["parent_excluded_priors"] > 0 for v in views),
                      "same_date_exclusions": sum(len(v["same_date_excluded"]) for v in views),
                      "undated_exclusions": sum(len(v["undated_excluded"]) for v in views),
                      "later_contests_excluded": sum(v["later_contests_excluded"] for v in views),
                      "non_fbs_opponent_relationships": sum(r["prior_opponent_division_label"] != "FBS" for r in rels),
                      "distinct_prior_contests": len(expected["evidence.jsonl"]), "evidence_classes": tally,
                      "witness_rows": len(expected["witnesses.jsonl"]),
                      "relationships_referencing_tranche": sum(r["prior_contest_key"] in tranche for r in rels),
                      "archive_keys": len(truth["dispositions"])},
           "comparison": result, "decisions": decisions, "tamper_cases": tampers,
           "oracle_challenges": oracle_challenges,
           "independence": "standard library only; no producer, query, core or project import; archive truth from the "
                           "accepted C41 independent oracle loaded by bound sha256; the consumer runs only as a "
                           "subprocess and is compared with this tool's own decisions",
           "limits": [("2019 FBS targets only; the archive evidence is the 97-contest expansion union (28-key "
                       "tranche plus the 70-key missing-prior cohort) and is not national coverage")
                      if bound.get("expansion") else
                      "2019 FBS targets only; the archive tranche is 28 contests and is not national coverage",
                      "archive captures are upper bounds for the exact witnessed versions, never first publication",
                      ("the archive truth comes from the bound expansion oracle over the accepted C41 oracle; archive "
                       "coverage is exactly the expansion sidecar's") if bound.get("expansion") else
                      "the archive truth reuses the accepted C41 oracle: zero new archive coverage is claimed",
                      "a coordinated forgery that rewrites parents and every hash is detectable only against the "
                      "committed contract/parent identities"],
           "observed_at": dt.datetime.now(UTC).isoformat()}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"result": doc["result"], "failed_checks": failed, "counts": doc["counts"]}, indent=1))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
