r"""Build the archive-supported 2019 prior-game history availability projection (BAT-714, Cycle #42 TP42-A01).

``python -B tools/build_national_history_availability.py --contract
configs/national_history_availability_2019_contract.json --input-bindings <INPUT_BINDINGS.json>
--output-root <data>/canonical/national_history_availability_2019
--manifest-root <data>/manifests/national_history_availability_2019``

Offline, standard library plus the shared core ``aggie_analytics.national_history.availability`` and the accepted
parent readers. The producer checks the contract (closed schemas, labels, parent binding), the bindings document (its
sha256, every bound path, sha256 and identity), then verifies every parent with its accepted reader at the bound
identity -- the population and history databases, the source-time database and, through the accepted
``ArchiveEvidence`` reader, the V1.2 archive sidecar re-derived from its raw bytes and receipts -- before reading any
row. It derives every 2019 target, view, expected prior relationship, prior-evidence record and field-witness row,
reconciled in both directions with the history parent, and writes, create-only and content addressed:

* ``targets.jsonl.gz``, ``views.jsonl.gz``, ``relationships.jsonl.gz``, ``evidence.jsonl.gz``, ``witnesses.jsonl.gz``
  (canonical JSONL, gzip with mtime 0) under ``<output-root>/sha256/<content identity>/``;
* ``national_history_availability.sqlite`` (deterministic, read-only query database) under
  ``<output-root>/sha256/<database identity>/``;
* one run manifest per identity under ``<manifest-root>/sha256/<identity>/run_manifest.json``.

Nothing is overwritten or activated. ``--chunk-size`` with ``--checkpoint-dir`` builds through a hash-chained
checkpoint that ``--resume`` verifies; ``--stop-after-chunks`` simulates an interruption (exit 3). Every row is
NOT_ADMITTED evidence: no PIT admission, no forecast, no training row.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import gzip
import hashlib
import io
import json
import os
import platform
import sqlite3
import sys
import tempfile
import time
import zlib
from pathlib import Path
from typing import Any, Iterable, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.national_history import availability as core  # noqa: E402

PRODUCER = "national_history_availability/1.0.0"
CHECKPOINT_SCHEMA = "BAS-NATIONAL-HISTORY-AVAILABILITY-CHECKPOINT-1"
INTERRUPTED_EXIT = 3
BINDING_NAMES = {"population": "population_database", "history": "history_database",
                 "source_time": "source_time_database", "archive": "archive_database"}
IDENTITY_FIELD = {"population": "query_db_identity", "history": "database_identity",
                  "source_time": "database_identity", "archive": "database_identity"}


class BuildRefused(core.AvailabilityError):
    """A refused build; ``code`` is a stable machine-readable reason."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------------------------- contract and bindings

def load_contract(path: Path) -> tuple[dict[str, Any], str]:
    raw = Path(path).read_bytes()
    try:
        contract = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BuildRefused("CONTRACT_INVALID", str(exc)) from exc
    if contract.get("schema_version") != core.CONTRACT_SCHEMA or contract.get("contract_id") not in core.PROFILES:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN",
                           f"schema {contract.get('schema_version')!r} id {contract.get('contract_id')!r}")
    if contract.get("population_id") != core.profile(contract["contract_id"])["population"]:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", f"population {contract.get('population_id')!r}")
    if contract.get("row_labels") != core.ROW_LABELS:
        raise BuildRefused("FORGED_AUTHORITY_LABEL", f"row_labels {contract.get('row_labels')!r}")
    authority = contract.get("authority") or {}
    if authority.get("require_pit") != "REFUSED_NOT_ADMITTED" or \
            authority.get("model_admission") != "REFUSED_NOT_ADMITTED":
        raise BuildRefused("FORGED_AUTHORITY_LABEL", "require_pit and model_admission must be refused")
    scope = contract.get("scope") or {}
    if scope.get("season") != core.SEASON or scope.get("target_subset") != core.SUBSET:
        raise BuildRefused("CONTRACT_INVALID", f"scope season {scope.get('season')!r} subset {scope.get('target_subset')!r}")
    payloads = contract.get("payloads") or {}
    if payloads.get("schema_version") != core.PAYLOAD_SCHEMA:
        raise BuildRefused("CONTRACT_SCHEMA_UNKNOWN", "payload schema differs")
    declared = payloads.get("record_fields")
    expected = {**{k: list(v) for k, v in core.RECORD_FIELDS.items()},
                **{k: list(v) for k, v in core.NESTED_FIELDS.items()}}
    if declared != expected:
        raise BuildRefused("CONTRACT_INVALID", "payloads.record_fields differ from the producer's closed schemas")
    if (contract.get("evidence") or {}).get("fields") != list(core.FIELDS):
        raise BuildRefused("CONTRACT_INVALID", "evidence.fields differ from the six witnessable fields")
    binding = contract.get("parent_binding") or {}
    for name, keys in core.profile(contract["contract_id"])["parent_keys"].items():
        for key in keys:
            if not isinstance((binding.get(name) or {}).get(key), str) or not binding[name][key]:
                raise BuildRefused("CONTRACT_INVALID", f"parent_binding.{name}.{key} missing")
    if not isinstance((binding.get("input_bindings") or {}).get("sha256"), str):
        raise BuildRefused("CONTRACT_INVALID", "parent_binding.input_bindings.sha256 missing")
    return contract, core.sha256_bytes(raw)


def load_bindings(path: Path, contract: dict[str, Any]) -> dict[str, Path]:
    """The manager's bindings document must hash to the contract value and name exactly the bound parents."""
    raw = Path(path).read_bytes()
    pb = contract["parent_binding"]
    if core.sha256_bytes(raw) != pb["input_bindings"]["sha256"]:
        raise BuildRefused("PARENT_BINDING_MISMATCH", "the bindings document does not hash to the contract value")
    try:
        bindings = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise BuildRefused("PARENT_BINDING_MISMATCH", f"bindings unreadable: {exc}") from exc
    paths: dict[str, Path] = {}
    for name, entry in BINDING_NAMES.items():
        item = bindings.get(entry) or {}
        want = pb[name]
        db = Path(str(item.get("path") or ""))
        if not db.is_file():
            raise BuildRefused("PARENT_BINDING_MISMATCH", f"{entry} is not a file: {db}")
        if item.get("sha256") != want["sqlite_sha256"] or item.get("identity") != want[IDENTITY_FIELD[name]] or \
                db.resolve().parent.name != want[IDENTITY_FIELD[name]]:
            raise BuildRefused("PARENT_BINDING_MISMATCH", f"{entry} sha256/identity differ from the contract")
        if sha256_file(db) != want["sqlite_sha256"]:
            raise BuildRefused("PARENT_BINDING_MISMATCH", f"{entry} bytes hash differently")
        paths[name] = db
    contract_item = bindings.get("archive_contract") or {}
    if contract_item.get("sha256") != pb["archive"]["contract_sha256"] or \
            not Path(str(contract_item.get("path") or "")).is_file() or \
            sha256_file(Path(contract_item["path"])) != pb["archive"]["contract_sha256"]:
        raise BuildRefused("PARENT_BINDING_MISMATCH", "archive contract binding differs")
    tranche = bindings.get("archive_tranche") or {}
    if tranche.get("sha256") != pb["archive"]["tranche_sha256"] or \
            not Path(str(tranche.get("path") or "")).is_file() or \
            sha256_file(Path(tranche["path"])) != pb["archive"]["tranche_sha256"]:
        raise BuildRefused("PARENT_BINDING_MISMATCH", "archive tranche binding differs")
    if "cohort_sha256" in pb["archive"]:
        cohort = bindings.get("archive_cohort") or {}
        if cohort.get("sha256") != pb["archive"]["cohort_sha256"] or \
                not Path(str(cohort.get("path") or "")).is_file() or \
                sha256_file(Path(cohort["path"])) != pb["archive"]["cohort_sha256"]:
            raise BuildRefused("PARENT_BINDING_MISMATCH", "archive cohort binding differs")
    return paths


# --------------------------------------------------------------------------------------------- checkpoint

def _keys_sha(keys: Sequence[str]) -> str:
    return core.sha256_bytes("\n".join(keys).encode("utf-8"))


class Checkpoint:
    def __init__(self, directory: Path, header: dict[str, Any], chunk_size: int, resume: bool) -> None:
        self.dir = Path(directory)
        self.header = header
        self.chunk_size = chunk_size
        self.ledger = self.dir / "checkpoint.ledger.jsonl"
        header_path = self.dir / "checkpoint.json"
        if resume:
            if not header_path.is_file():
                raise BuildRefused("REFUSED_STALE_CHECKPOINT", f"no checkpoint header in {self.dir}")
            stored = json.loads(header_path.read_text(encoding="utf-8"))
            differing = sorted(k for k in set(stored) | set(header) if stored.get(k) != header.get(k))
            if differing:
                raise BuildRefused("REFUSED_STALE_CHECKPOINT", f"checkpoint binds different {differing}")
        else:
            if self.dir.exists() and any(self.dir.iterdir()):
                raise BuildRefused("CHECKPOINT_EXISTS", f"{self.dir} is not empty; use --resume")
            (self.dir / "chunks").mkdir(parents=True, exist_ok=True)
            with header_path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(header, sort_keys=True, indent=1) + "\n")

    def chunk_path(self, index: int) -> Path:
        return self.dir / "chunks" / f"chunk_{index:06d}.jsonl"

    def completed(self, target_keys: list[str]) -> list[dict[str, Any]]:
        """Verify the ledger, every chunk file and the chained key prefix; return the completed chunk rows."""
        if not self.ledger.is_file():
            return []
        lines = self.ledger.read_text(encoding="utf-8").split("\n")
        rows = [json.loads(line) for line in lines[:-1] if line]  # a torn, unterminated last line is not complete
        prefix = ""
        for expected_index, row in enumerate(rows, start=1):
            start = (expected_index - 1) * self.chunk_size
            keys = target_keys[start:start + self.chunk_size]
            path = self.chunk_path(expected_index)
            if row.get("index") != expected_index or row.get("count") != len(keys) or \
                    row.get("keys_sha256") != _keys_sha(keys) or not keys or \
                    row.get("first_key") != keys[0] or row.get("last_key") != keys[-1]:
                raise BuildRefused("REFUSED_ALTERED_PREFIX", f"ledger row {expected_index} does not match the key prefix")
            if not path.is_file() or sha256_file(path) != row.get("chunk_sha256"):
                raise BuildRefused("REFUSED_ALTERED_PREFIX", f"chunk {expected_index} bytes differ from the ledger")
            prefix = core.sha256_bytes((prefix + row["chunk_sha256"]).encode("ascii"))
            if row.get("prefix_sha256") != prefix:
                raise BuildRefused("REFUSED_ALTERED_PREFIX", f"chained prefix breaks at chunk {expected_index}")
        return rows

    def write_chunk(self, index: int, keys: list[str], blob: bytes, previous_prefix: str) -> dict[str, Any]:
        path = self.chunk_path(index)
        if path.exists():  # written before an interruption but never recorded in the ledger
            if path.read_bytes() != blob:
                raise BuildRefused("REFUSED_FORKED_CHECKPOINT", f"unrecorded chunk {index} differs from the rebuild")
        else:
            temporary = path.with_suffix(".partial")
            if temporary.exists():
                raise BuildRefused("REFUSED_FORKED_CHECKPOINT", f"partial chunk {index} present")
            with temporary.open("xb") as handle:
                handle.write(blob)
            os.replace(temporary, path)
        chunk_sha = core.sha256_bytes(blob)
        row = {"index": index, "count": len(keys), "first_key": keys[0], "last_key": keys[-1],
               "keys_sha256": _keys_sha(keys), "chunk_sha256": chunk_sha,
               "prefix_sha256": core.sha256_bytes((previous_prefix + chunk_sha).encode("ascii"))}
        with self.ledger.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return row


def build_bundles(projection: core.Projection, *, chunk_size: int, checkpoint: Checkpoint | None,
                  stop_after: int | None) -> bytes | None:
    targets = projection.targets
    if checkpoint is None:
        return b"".join(projection.bundle(row) for row in targets)
    size = chunk_size
    done = checkpoint.completed(projection.target_keys)
    prefix = done[-1]["prefix_sha256"] if done else ""
    written = 0
    index = len(done)
    while index * size < len(targets):
        index += 1
        rows = targets[(index - 1) * size:index * size]
        blob = b"".join(projection.bundle(row) for row in rows)
        prefix = checkpoint.write_chunk(index, [row["contest_key"] for row in rows], blob, prefix)["prefix_sha256"]
        written += 1
        if stop_after is not None and written >= stop_after and index * size < len(targets):
            return None
    rows = checkpoint.completed(projection.target_keys)
    if sum(row["count"] for row in rows) != len(targets):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpoint does not cover every target")
    return b"".join(checkpoint.chunk_path(row["index"]).read_bytes() for row in rows)


# --------------------------------------------------------------------------------------------- database

def build_database(path: Path, payloads: dict[str, bytes], meta: dict[str, str]) -> dict[str, int]:
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA page_size = 4096")
        conn.execute("PRAGMA journal_mode = OFF")
        conn.executescript(
            "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
            "CREATE TABLE targets (ord INTEGER PRIMARY KEY, contest_key TEXT NOT NULL UNIQUE, contest_date TEXT NOT NULL,"
            " a_key TEXT NOT NULL, b_key TEXT NOT NULL, record TEXT NOT NULL);"
            "CREATE TABLE views (ord INTEGER PRIMARY KEY, target_contest_key TEXT NOT NULL, view TEXT NOT NULL,"
            " target_date TEXT NOT NULL, team_key TEXT NOT NULL, opponent_key TEXT NOT NULL, record TEXT NOT NULL,"
            " UNIQUE (target_contest_key, view));"
            "CREATE TABLE relationships (ord INTEGER PRIMARY KEY, target_contest_key TEXT NOT NULL, view TEXT NOT NULL,"
            " team_key TEXT NOT NULL, prior_contest_key TEXT NOT NULL, record TEXT NOT NULL,"
            " UNIQUE (target_contest_key, view, prior_contest_key));"
            "CREATE TABLE evidence (ord INTEGER PRIMARY KEY, contest_key TEXT NOT NULL UNIQUE, record TEXT NOT NULL);"
            "CREATE TABLE witnesses (ord INTEGER PRIMARY KEY, contest_key TEXT NOT NULL, capture_id TEXT NOT NULL,"
            " field TEXT NOT NULL, witness TEXT NOT NULL, span_start INTEGER NOT NULL, record TEXT NOT NULL,"
            " UNIQUE (capture_id, field, witness, span_start));")
        conn.executemany("INSERT INTO meta VALUES (?, ?)", sorted(meta.items()))

        def records(name: str) -> Iterable[tuple[int, dict[str, Any], str]]:
            for index, line in enumerate(payloads[name].decode("utf-8").splitlines()):
                yield index, json.loads(line), line
        conn.executemany("INSERT INTO targets VALUES (?, ?, ?, ?, ?, ?)",
                         [(i, r["contest_key"], r["contest_date"], r["a_key"], r["b_key"], line)
                          for i, r, line in records("targets.jsonl")])
        conn.executemany("INSERT INTO views VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [(i, r["target_contest_key"], r["view"], r["target_date"], r["team_key"], r["opponent_key"],
                           line) for i, r, line in records("views.jsonl")])
        conn.executemany("INSERT INTO relationships VALUES (?, ?, ?, ?, ?, ?)",
                         [(i, r["target_contest_key"], r["view"], r["team_key"], r["prior_contest_key"], line)
                          for i, r, line in records("relationships.jsonl")])
        conn.executemany("INSERT INTO evidence VALUES (?, ?, ?)",
                         [(i, r["contest_key"], line) for i, r, line in records("evidence.jsonl")])
        conn.executemany("INSERT INTO witnesses VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [(i, r["contest_key"], r["capture_id"], r["field"], r["witness"], r["witness_span"][0], line)
                          for i, r, line in records("witnesses.jsonl")])
        conn.executescript(
            "CREATE INDEX ix_targets_a ON targets (a_key, ord);"
            "CREATE INDEX ix_targets_b ON targets (b_key, ord);"
            "CREATE INDEX ix_views_team ON views (team_key, ord);"
            "CREATE INDEX ix_relationships_target ON relationships (target_contest_key, view, ord);"
            "CREATE INDEX ix_relationships_team ON relationships (team_key, ord);"
            "CREATE INDEX ix_witnesses_contest ON witnesses (contest_key, ord);")
        conn.commit()
        counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in core.TABLES}
    finally:
        conn.close()
    return counts


# --------------------------------------------------------------------------------------------- materialization

def runtime() -> dict[str, str]:
    return {"implementation": platform.python_implementation(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "zlib": zlib.ZLIB_VERSION}


def gzip_bytes(data: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0, compresslevel=9) as stream:
        stream.write(data)
    return buffer.getvalue()


def materialize(output_root: Path, manifest_root: Path, identity_document: dict[str, Any],
                files: dict[str, Path | bytes], provenance: dict[str, Any]) -> dict[str, Any]:
    """Create-only content-addressed write: verify an existing identity, never overwrite it."""
    identity = core.sha256_bytes(core.canonical_json_bytes(identity_document))
    target = Path(output_root) / "sha256" / identity
    manifest = Path(manifest_root) / "sha256" / identity / "run_manifest.json"
    declared = identity_document["outputs"]
    state = "MATERIALIZED"
    if target.exists():
        present = sorted(p.name for p in target.iterdir())
        if present != sorted(declared) or any(sha256_file(target / name) != sha for name, sha in declared.items()):
            raise BuildRefused("REFUSED_IMMUTABLE_COLLISION", f"{target} exists with different content")
        state = "ALREADY_PRESENT_IDENTICAL"
    else:
        temporary = Path(output_root) / "sha256" / f".tmp-{identity[:16]}-{os.getpid()}-{time.time_ns()}"
        temporary.mkdir(parents=True)
        for name, source in files.items():
            data = source if isinstance(source, bytes) else Path(source).read_bytes()
            with (temporary / name).open("xb") as handle:
                handle.write(data)
            if sha256_file(temporary / name) != declared[name]:
                raise BuildRefused("WRITE_VERIFY_FAILED", name)
        os.rename(temporary, target)
    if manifest.exists():
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        if existing.get("identity") != identity or existing.get("identity_document") != identity_document:
            raise BuildRefused("REFUSED_IMMUTABLE_COLLISION", f"{manifest} names a different identity")
        manifest_state = "ALREADY_PRESENT"
    else:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"identity": identity, "identity_document": identity_document,
                                     "provenance": provenance}, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        manifest_state = "WRITTEN"
    return {"identity": identity, "state": state, "data_dir": str(target), "manifest": str(manifest),
            "manifest_state": manifest_state}


def build(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    contract, contract_sha = load_contract(args.contract)
    if args.chunk_size < 0 or (args.stop_after_chunks is not None and args.stop_after_chunks < 1):
        raise BuildRefused("ARGUMENT_INVALID", "chunk size and stop-after must be positive")
    if (args.resume or args.stop_after_chunks is not None) and not args.checkpoint_dir:
        raise BuildRefused("ARGUMENT_INVALID", "--resume and --stop-after-chunks need --checkpoint-dir")
    if args.checkpoint_dir and args.chunk_size < 1:
        raise BuildRefused("ARGUMENT_INVALID", "--checkpoint-dir needs --chunk-size >= 1")
    paths = load_bindings(args.input_bindings, contract)
    expected = {name: {k: contract["parent_binding"][name][k] for k in keys}
                for name, keys in core.profile(contract["contract_id"])["parent_keys"].items()}
    opened = core.open_parents(paths, expected)
    projection = core.Projection(opened["population_rows"], opened["subset"], opened["history_targets"],
                                 opened["history_views"], opened["archive"], input_order=args.input_order)
    evidence_bytes, witness_bytes = projection.census_bytes()
    checkpoint = None
    parent = opened["parent"]
    if args.checkpoint_dir:
        header = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha, "parent": parent,
                  "payload_schema": core.PAYLOAD_SCHEMA, "chunk_size": args.chunk_size,
                  "target_key_list_sha256": _keys_sha(projection.target_keys),
                  "target_count": len(projection.target_keys),
                  "census_sha256": core.sha256_bytes(evidence_bytes + witness_bytes),
                  "producer_sha256": sha256_file(Path(__file__)), "core_sha256": sha256_file(Path(core.__file__))}
        checkpoint = Checkpoint(Path(args.checkpoint_dir), header, args.chunk_size, args.resume)
    blob = build_bundles(projection, chunk_size=args.chunk_size, checkpoint=checkpoint,
                         stop_after=args.stop_after_chunks)
    if blob is None:
        return {"state": "INTERRUPTED_AT_CHECKPOINT", "checkpoint_dir": str(args.checkpoint_dir),
                "completed_chunks": len(checkpoint.completed(projection.target_keys)) if checkpoint else 0,
                "target_count": len(projection.target_keys)}
    payloads = core.payloads_from(blob, evidence_bytes, witness_bytes)
    counts = {name: payloads[name].count(b"\n") for name in core.PAYLOAD_FILES}
    if counts["views.jsonl"] != 2 * counts["targets.jsonl"]:
        raise BuildRefused("CENSUS_INCOMPLETE", "views do not number two per target")
    packed = {f"{name}.gz": gzip_bytes(payloads[name]) for name in core.PAYLOAD_FILES}
    content_document = {"schema": core.CONTENT_SCHEMA, "stage": "history-availability-content",
                        "population": core.profile(contract["contract_id"])["population"],
                        "contract_id": contract["contract_id"], "contract_sha256": contract_sha, "parent": parent,
                        "payload_schema": core.PAYLOAD_SCHEMA,
                        "payload_encoding": core.PAYLOAD_ENCODING,
                        "semantic_outputs": {name: core.sha256_bytes(payloads[name]) for name in core.PAYLOAD_FILES},
                        "outputs": {name: core.sha256_bytes(data) for name, data in packed.items()},
                        "row_counts": counts}
    content_identity = core.sha256_bytes(core.canonical_json_bytes(content_document))
    with tempfile.TemporaryDirectory(prefix="nha-") as work:
        return _finish(args, contract, contract_sha, parent, content_document, content_identity, payloads, packed,
                       counts, Path(work) / core.DB_FILE, started, projection)


def _finish(args: argparse.Namespace, contract: dict[str, Any], contract_sha: str, parent: dict[str, Any],
            content_document: dict[str, Any], content_identity: str, payloads: dict[str, bytes],
            packed: dict[str, bytes], counts: dict[str, int], db_path: Path, started: float,
            projection: core.Projection) -> dict[str, Any]:
    meta = {"schema_version": core.DB_SCHEMA, "contract_id": contract["contract_id"], "contract_sha256": contract_sha,
            "content_identity": content_identity, "payload_schema": core.PAYLOAD_SCHEMA,
            "payload_sha256": json.dumps(content_document["semantic_outputs"], sort_keys=True),
            "row_counts": json.dumps(counts, sort_keys=True), "parent": json.dumps(parent, sort_keys=True),
            "row_labels": json.dumps(core.ROW_LABELS, sort_keys=True), "season": str(core.SEASON),
            "prior_rule": core.PRIOR_RULE, "support_rule": core.SUPPORT_RULE,
            "cross_version_rule": core.CROSS_VERSION_RULE}
    table_counts = build_database(db_path, payloads, meta)
    database_document = {"schema": core.DATABASE_SCHEMA, "stage": "history-availability-database",
                         "population": core.profile(contract["contract_id"])["population"],
                         "contract_sha256": contract_sha, "content_identity": content_identity, "parent": parent,
                         "db_schema_version": core.DB_SCHEMA,
                         "outputs": {core.DB_FILE: sha256_file(db_path)}, "table_counts": table_counts}
    database_identity = core.sha256_bytes(core.canonical_json_bytes(database_document))
    provenance = {"producer": PRODUCER, "producer_path": str(Path(__file__).resolve()),
                  "producer_sha256": sha256_file(Path(__file__)), "core_path": str(Path(core.__file__).resolve()),
                  "core_sha256": sha256_file(Path(core.__file__)), "argv": list(args.argv),
                  "issued_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
                  "runtime": runtime(), "variant": args.variant, "input_order": args.input_order,
                  "chunk_size": args.chunk_size, "resumed": bool(args.resume),
                  "jira_key": contract.get("jira_key"), "cycle_number": contract.get("cycle_number"),
                  "attempt_number": contract.get("attempt_number"), "database_identity": database_identity,
                  "database_manifest": f"sha256/{database_identity}/run_manifest.json"}
    output_root, manifest_root = Path(args.output_root), Path(args.manifest_root)
    content = materialize(output_root, manifest_root, content_document, dict(packed), provenance)
    database = materialize(output_root, manifest_root, database_document, {core.DB_FILE: db_path},
                           {**provenance, "content_identity": content_identity})
    relationships = [json.loads(line) for line in payloads["relationships.jsonl"].splitlines()]
    evidence = [json.loads(line) for line in payloads["evidence.jsonl"].splitlines()]
    tallies = {"relationship_classes": {}, "evidence_classes": {}}
    for rel in relationships:
        tallies["relationship_classes"][rel["relationship_class"]] = \
            tallies["relationship_classes"].get(rel["relationship_class"], 0) + 1
    for item in evidence:
        cls = item["archive"]["evidence_class"]
        tallies["evidence_classes"][cls] = tallies["evidence_classes"].get(cls, 0) + 1
    return {"state": content["state"], "database_state": database["state"], "content_identity": content_identity,
            "database_identity": database_identity, "content": content, "database": database, "row_counts": counts,
            "table_counts": table_counts, "semantic_sha256": content_document["semantic_outputs"],
            "payload_sha256": content_document["outputs"], "database_sha256": database_document["outputs"][core.DB_FILE],
            "contract_sha256": contract_sha, "parent": parent, "tallies": tallies,
            "input_order": args.input_order, "chunk_size": args.chunk_size, "variant": args.variant,
            "runtime": runtime(), "seconds": round(time.time() - started, 3)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_history_availability", allow_abbrev=False,
                                     description="Build the archive-supported 2019 prior-game history availability "
                                                 "projection (evidence only; NOT_ADMITTED).")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--input-bindings", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--manifest-root", required=True, type=Path)
    parser.add_argument("--input-order", default="natural")
    parser.add_argument("--chunk-size", type=int, default=0)
    parser.add_argument("--checkpoint-dir", type=Path, default=None)
    parser.add_argument("--stop-after-chunks", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--variant", default="CANONICAL")
    parser.add_argument("--receipt", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(raw)
    args.argv = ["tools/build_national_history_availability.py", *raw]
    try:
        result = build(args)
    except core.AvailabilityError as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    text = json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if args.receipt is not None:
        with Path(args.receipt).open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    sys.stdout.write(text)
    return INTERRUPTED_EXIT if result["state"] == "INTERRUPTED_AT_CHECKPOINT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
