r"""Build the explicit cached-source reconciliation sidecar of the accepted 2024-2025 national population (BAT-718,
Cycle #46 TP46-A01).

``python -B tools/build_national_population_reconciliation.py
--contract configs/national_population_reconciliation_2024_2025_contract.json
--parent-database <data>/canonical/national_di_population_2016_2025/sha256/<id>/national_population.sqlite
--output-root <data>/canonical/national_population_reconciliation_2024_2025
--manifest-root <data>/manifests/national_population_reconciliation_2024_2025``

The builder refuses unless the contract's parameters and labels equal the reader's rules and its parent contract
reference is the accepted parent contract with the same name normalization and date basis. It verifies the bound parent
and every bound cached input (read under ``--input-root``, by default the parent's data root), derives the records with
the reconciliation rules of :mod:`aggie_analytics.national_population.query` (the reader re-derives exactly the same
records before it serves any row), writes the payloads and the deterministic SQLite database and materializes both
create-only and content addressed: an existing identity is verified, never rewritten. The materialized database is then
opened through the reader's full verification with the contract's anchors. ``--input-order`` (natural, reverse,
shuffle:<seed>), ``--chunk-size`` with ``--checkpoint-dir`` and ``--stop-after-chunks`` / ``--resume`` exist to prove
that order, chunking and an interrupted build cannot change a byte.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import platform
import sqlite3
import sys
import tempfile
import time
import zlib
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.national_population import query  # noqa: E402

PRODUCER = "national_population_reconciliation/1.0.0"
CONTRACT_ID_PREFIX = "BAT-718-NATIONAL-POPULATION-RECONCILIATION-2024-2025-"
CHECKPOINT_SCHEMA = "BAS-NATIONAL-POPULATION-RECONCILIATION-CHECKPOINT-1"
INTERRUPTED_EXIT = 3


class BuildRefused(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_contract(path: Path) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """The contract, its SHA-256 and the anchors it binds; refuses any drift from the reader's rules."""
    raw = Path(path).read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    contract_sha = sha256_bytes(raw)
    problems = []
    if not str(contract.get("contract_id", "")).startswith(CONTRACT_ID_PREFIX):
        problems.append("contract_id")
    if contract.get("population_id") != query.RECONCILIATION_POPULATION:
        problems.append("population_id")
    if contract.get("seasons") != list(query.RECONCILIATION_SEASONS):
        problems.append("seasons")
    if contract.get("parameters") != query.RECONCILIATION_PARAMETERS:
        problems.append("parameters")
    if contract.get("labels") != query.RECONCILIATION_LABELS:
        problems.append("labels")
    parent_contract = contract.get("parent_contract") or {}
    parent_contract_path = REPO_ROOT / Path(*str(parent_contract.get("repository_path", "")).split("/"))
    if not parent_contract_path.is_file() or sha256_file(parent_contract_path) != parent_contract.get("sha256") or \
            parent_contract.get("sha256") != (contract.get("parent") or {}).get("contract_sha256"):
        problems.append("parent_contract")
    else:
        accepted = json.loads(parent_contract_path.read_text(encoding="utf-8"))
        resolution = accepted["reconciliation"]["participant_resolution"]
        if resolution["token_expansions"] != query.RECONCILIATION_TOKEN_EXPANSIONS or \
                accepted["parameters"]["cfbd_local_offset_hours"] != list(query.RECONCILIATION_LOCAL_OFFSET_HOURS):
            problems.append("parent_contract_rules")
    anchors = {"contract_sha256": contract_sha, "contract_id": contract.get("contract_id"),
               "parent": contract.get("parent"), "inputs": contract.get("inputs")}
    if not problems and contract.get("content_scope") != query.reconciliation_scope(anchors):
        problems.append("content_scope")
    if problems:
        raise BuildRefused("CONTRACT_INVALID", f"contract differs from the reader's rules on {problems}")
    return contract, contract_sha, anchors


# --------------------------------------------------------------------------------------------- checkpoint

def _keys_sha(keys: Sequence[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


class Checkpoint:
    """A hash-chained record checkpoint: each chunk of record lines is written once, its ledger row chains the prefix."""

    def __init__(self, directory: Path, header: dict[str, Any], chunk_size: int, resume: bool) -> None:
        self.dir = Path(directory)
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

    def completed(self, keys: list[str]) -> list[dict[str, Any]]:
        """Verify the ledger, every chunk file and the chained key prefix; return the completed chunk rows."""
        if not self.ledger.is_file():
            return []
        lines = self.ledger.read_text(encoding="utf-8").split("\n")
        rows = [json.loads(line) for line in lines[:-1] if line]  # a torn, unterminated last line is not complete
        prefix = ""
        for expected_index, row in enumerate(rows, start=1):
            start = (expected_index - 1) * self.chunk_size
            chunk_keys = keys[start:start + self.chunk_size]
            path = self.chunk_path(expected_index)
            if row.get("index") != expected_index or row.get("count") != len(chunk_keys) or not chunk_keys or \
                    row.get("keys_sha256") != _keys_sha(chunk_keys) or row.get("first_key") != chunk_keys[0] or \
                    row.get("last_key") != chunk_keys[-1]:
                raise BuildRefused("REFUSED_ALTERED_PREFIX", f"ledger row {expected_index} does not match the key prefix")
            if not path.is_file() or sha256_file(path) != row.get("chunk_sha256"):
                raise BuildRefused("REFUSED_ALTERED_PREFIX", f"chunk {expected_index} bytes differ from the ledger")
            prefix = sha256_bytes((prefix + row["chunk_sha256"]).encode("ascii"))
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
        chunk_sha = sha256_bytes(blob)
        row = {"index": index, "count": len(keys), "first_key": keys[0], "last_key": keys[-1],
               "keys_sha256": _keys_sha(keys), "chunk_sha256": chunk_sha,
               "prefix_sha256": sha256_bytes((previous_prefix + chunk_sha).encode("ascii"))}
        with self.ledger.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return row


def record_stream(derived: dict[str, Any]) -> tuple[list[str], list[bytes]]:
    """Every record key and canonical line, parent records first, both in contract order."""
    keys, lines = [], []
    for record in derived["parent_records"]:
        keys.append("parent|" + record["contest_key"])
        lines.append((query.reconciliation_line(record) + "\n").encode("utf-8"))
    for record in derived["provider_records"]:
        keys.append("provider|" + record["provider_row_key"])
        lines.append((query.reconciliation_line(record) + "\n").encode("utf-8"))
    return keys, lines


def build_lines(keys: list[str], lines: list[bytes], *, chunk_size: int, checkpoint: Checkpoint | None,
                stop_after: int | None) -> list[bytes] | None:
    if checkpoint is None:
        return lines
    done = checkpoint.completed(keys)
    prefix = done[-1]["prefix_sha256"] if done else ""
    index, written = len(done), 0
    while index * chunk_size < len(keys):
        index += 1
        start = (index - 1) * chunk_size
        blob = b"".join(lines[start:start + chunk_size])
        prefix = checkpoint.write_chunk(index, keys[start:start + chunk_size], blob, prefix)["prefix_sha256"]
        written += 1
        if stop_after is not None and written >= stop_after and index * chunk_size < len(keys):
            return None
    rows = checkpoint.completed(keys)
    if sum(row["count"] for row in rows) != len(keys):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "the checkpoint does not cover every record")
    out: list[bytes] = []
    for row in rows:
        out.extend(checkpoint.chunk_path(row["index"]).read_bytes().splitlines(keepends=True))
    return out


# --------------------------------------------------------------------------------------------- database

def build_database(path: Path, derived: dict[str, Any], meta: dict[str, str]) -> dict[str, int]:
    rows = query.reconciliation_table_rows(derived)
    tables = [ddl for kind, _name, ddl in query.RECONCILIATION_DDL if kind == "table"]
    indexes = [ddl for kind, _name, ddl in query.RECONCILIATION_DDL if kind == "index"]
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA page_size = 4096")
        conn.execute("PRAGMA journal_mode = OFF")
        for ddl in tables:
            conn.execute(ddl)
        conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", sorted(meta.items()))
        conn.executemany("INSERT INTO parent_reconciliation VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         rows["parent_reconciliation"])
        conn.executemany("INSERT INTO provider_reconciliation VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         rows["provider_reconciliation"])
        for ddl in indexes:
            conn.execute(ddl)
        conn.commit()
        counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                  for table in query.RECONCILIATION_TABLES}
    finally:
        conn.close()
    return counts


# --------------------------------------------------------------------------------------------- materialization

def runtime() -> dict[str, str]:
    return {"implementation": platform.python_implementation(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "zlib": zlib.ZLIB_VERSION}


def materialize(output_root: Path, manifest_root: Path, identity_document: dict[str, Any],
                files: dict[str, Path | bytes], provenance: dict[str, Any]) -> dict[str, Any]:
    """Create-only content-addressed write: verify an existing identity, never overwrite it."""
    identity = sha256_bytes(query.canonical_json_bytes(identity_document))
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
        # MF46A01-03: canonical bytes, never Python equality (an integral float count equals its integer there)
        if existing.get("identity") != identity or query.canonical_json_bytes(existing.get("identity_document")) != \
                query.canonical_json_bytes(identity_document):
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
    contract, contract_sha, anchors = load_contract(args.contract)
    if args.chunk_size < 0 or (args.stop_after_chunks is not None and args.stop_after_chunks < 1):
        raise BuildRefused("ARGUMENT_INVALID", "chunk size and stop-after must be positive")
    if (args.resume or args.stop_after_chunks is not None) and not args.checkpoint_dir:
        raise BuildRefused("ARGUMENT_INVALID", "--resume and --stop-after-chunks need --checkpoint-dir")
    if args.checkpoint_dir and args.chunk_size < 1:
        raise BuildRefused("ARGUMENT_INVALID", "--checkpoint-dir needs --chunk-size >= 1")
    try:
        with query.NationalPopulationDatabase(args.parent_database, manifest=args.parent_manifest) as parent:
            query.verify_reconciliation_parent(parent, anchors)
            input_root = Path(args.input_root) if args.input_root else query.reconciliation_data_root(args.parent_database)
            inputs = query.load_reconciliation_inputs(input_root, anchors)
            parent_rows = query.read_reconciliation_parent(parent.conn)
            parent_binding = dict(parent.binding)
    except query.NationalQueryError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    counts = {}
    for contest in parent_rows["contests"]:
        counts[str(contest["season"])] = counts.get(str(contest["season"]), 0) + 1
    if counts != anchors["parent"]["expected_contests"]:
        raise BuildRefused("PARENT_COLLECTION_MISMATCH", f"parent contests {counts} != {anchors['parent']['expected_contests']}")
    try:
        derived = query.derive_reconciliation(parent_rows, inputs, input_order=args.input_order)
    except query.NationalQueryError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    if len(derived["parent_records"]) != sum(anchors["parent"]["expected_contests"].values()) or \
            len(derived["provider_records"]) != sum(c["rows"] for c in anchors["inputs"]["provider_captures"]):
        raise BuildRefused("CENSUS_INCOMPLETE", "records do not account for every input row exactly once")
    keys, lines = record_stream(derived)
    checkpoint = None
    if args.checkpoint_dir:
        header = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha,
                  "parent_query_db_identity": parent_binding["database_identity"],
                  "payload_schema": query.RECONCILIATION_PAYLOAD_SCHEMA, "chunk_size": args.chunk_size,
                  "record_key_list_sha256": _keys_sha(keys), "record_count": len(keys),
                  "producer_sha256": sha256_file(Path(__file__)),
                  "reader_sha256": sha256_file(Path(query.__file__))}
        checkpoint = Checkpoint(Path(args.checkpoint_dir), header, args.chunk_size, args.resume)
    built = build_lines(keys, lines, chunk_size=args.chunk_size, checkpoint=checkpoint,
                        stop_after=args.stop_after_chunks)
    if built is None:
        return {"state": "INTERRUPTED_AT_CHECKPOINT", "checkpoint_dir": str(args.checkpoint_dir),
                "completed_chunks": len(checkpoint.completed(keys)) if checkpoint else 0, "record_count": len(keys)}
    n_parent = len(derived["parent_records"])
    payloads = {"parent_reconciliation.jsonl": b"".join(built[:n_parent]),
                "provider_reconciliation.jsonl": b"".join(built[n_parent:]),
                "summary.json": (query.reconciliation_line(derived["summary"]) + "\n").encode("utf-8")}
    if payloads != query.reconciliation_payloads(derived):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpointed records differ from the derivation")
    content_document = query.reconciliation_content_document(contract["contract_id"], contract_sha, anchors, payloads)
    content_identity = sha256_bytes(query.canonical_json_bytes(content_document))
    meta = query.reconciliation_meta(content_document, content_identity, derived["summary"])
    with tempfile.TemporaryDirectory(prefix="npr-") as work:
        db_path = Path(work) / query.RECONCILIATION_DB_FILE
        table_counts = build_database(db_path, derived, meta)
        database_document = query.reconciliation_database_document(contract_sha, content_identity,
                                                                    sha256_file(db_path), table_counts)
        database_identity = sha256_bytes(query.canonical_json_bytes(database_document))
        provenance = {"producer": PRODUCER, "producer_path": str(Path(__file__).resolve()),
                      "producer_sha256": sha256_file(Path(__file__)), "reader_path": str(Path(query.__file__).resolve()),
                      "reader_sha256": sha256_file(Path(query.__file__)), "argv": list(args.argv),
                      "issued_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
                      "runtime": runtime(), "variant": args.variant, "input_order": args.input_order,
                      "chunk_size": args.chunk_size, "resumed": bool(args.resume), "jira_key": contract.get("jira_key"),
                      "cycle_number": contract.get("cycle_number"), "attempt_number": contract.get("attempt_number"),
                      "parent_manifest": parent_binding["manifest"], "input_root": str(input_root),
                      "content_identity": content_identity, "database_identity": database_identity}
        content = materialize(args.output_root, args.manifest_root, content_document, dict(payloads), provenance)
        database = materialize(args.output_root, args.manifest_root, database_document,
                               {query.RECONCILIATION_DB_FILE: db_path}, provenance)
    materialized_db = Path(database["data_dir"]) / query.RECONCILIATION_DB_FILE
    try:
        with query.NationalPopulationDatabase(args.parent_database, manifest=args.parent_manifest) as parent:
            with query.ReconciliationSidecar(materialized_db, parent=parent, parent_database=args.parent_database,
                                             anchors=anchors) as sidecar:
                reader_check = {"verified": True, "identity": sidecar.binding["identity"],
                                "content_identity": sidecar.content_identity}
    except query.NationalQueryError as exc:
        raise BuildRefused("MATERIALIZED_SIDECAR_REFUSED_BY_READER", str(exc)) from exc
    production = {k: v for k, v in query.RECONCILIATION_ANCHORS.items() if k != "contract_sha256"}
    return {"state": content["state"], "content_identity": content_identity, "database_identity": database_identity,
            "content": content, "database": database, "reader_check": reader_check,
            "row_counts": content_document["row_counts"], "table_counts": table_counts,
            "payload_sha256": content_document["outputs"], "database_sha256": database_document["outputs"],
            "summary": derived["summary"], "contract_sha256": contract_sha, "contract_id": contract["contract_id"],
            "anchors_equal_production": {k: v for k, v in anchors.items() if k != "contract_sha256"} == production,
            "contract_pinned_by_reader": contract_sha == query.RECONCILIATION_ANCHORS["contract_sha256"],
            "parent": {"identity": parent_binding["database_identity"], "sqlite_sha256": parent_binding["database_sha256"]},
            "input_root": str(input_root), "input_order": args.input_order, "chunk_size": args.chunk_size,
            "resumed": bool(args.resume), "variant": args.variant, "runtime": runtime(),
            "seconds": round(time.time() - started, 3)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_population_reconciliation", allow_abbrev=False,
                                     description="Build the 2024-2025 cached-source population reconciliation sidecar.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--parent-database", required=True, type=Path)
    parser.add_argument("--parent-manifest", type=Path, default=None)
    parser.add_argument("--input-root", type=Path, default=None)
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
    args.argv = ["tools/build_national_population_reconciliation.py", *raw]
    try:
        result = build(args)
    except BuildRefused as exc:
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
