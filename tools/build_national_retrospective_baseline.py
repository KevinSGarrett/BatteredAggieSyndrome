r"""Build the explicit retrospective games-only baseline benchmark over the accepted 2016-2023 national history
(BAT-719, Cycle #47 TP47-A01).

``python -B tools/build_national_retrospective_baseline.py
--contract configs/national_retrospective_baseline_2016_2023_contract.json
--history-database <data>/canonical/national_history_prefix_2016_2023/sha256/<id>/national_history.sqlite
--output-root <data>/canonical/national_retrospective_baseline_2016_2023
--manifest-root <data>/manifests/national_retrospective_baseline_2016_2023``

The builder refuses unless the contract's models, numeric contract, labels, split, scope and identities equal the rules
of :mod:`aggie_analytics.retrospective_baseline.benchmark` (the reader re-derives exactly the same records before it
serves any row), the governing split registry and the accepted history contract in this checkout carry their bound
SHA-256, and the history database verifies and pins to the contract's history binding. It derives features, then
estimates (no label in scope), then labels, scores and the summary, writes the five payloads and the deterministic
SQLite database and materializes both create-only and content addressed: an existing identity is verified, never
rewritten. The materialized database is then opened through the reader's full verification with the contract's
anchors. ``--input-order`` (natural, reverse, shuffle:<seed>), ``--chunk-size`` (targets per checkpoint chunk) with
``--checkpoint-dir`` and ``--stop-after-chunks`` / ``--resume`` exist to prove that order, chunking and an
interrupted build cannot change a byte. Nothing is fitted, tuned or selected; no protected or forward outcome, ranking,
venue or held model output is read.
"""
from __future__ import annotations

import argparse
import csv
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
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.retrospective_baseline import benchmark as bm  # noqa: E402

PRODUCER = "national_retrospective_baseline/1.0.0"
CHECKPOINT_SCHEMA = "BAS-RETROSPECTIVE-BASELINE-CHECKPOINT-1"
INTERRUPTED_EXIT = 3
HISTORY_CONTRACT = "configs/national_history_prefix_2016_2023_contract.json"


class BuildRefused(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return bm.sha256_file(path)


def _split_registry_rows() -> dict[str, dict[str, str]]:
    path = REPO_ROOT / Path(*bm.SPLIT["registry_path"].split("/"))
    raw = path.read_bytes()
    if sha256_bytes(raw) != bm.SPLIT["registry_sha256"]:
        raise BuildRefused("CONTRACT_INVALID", "the governing split registry differs from its bound SHA-256")
    return {row["split_id"]: row for row in csv.DictReader(io.StringIO(raw.decode("utf-8")))}


def load_contract(path: Path, history_contract: Path | None = None) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """The contract, its SHA-256 and the anchors it binds; refuses any drift from the reader's rules. The bound
    history contract is this checkout's accepted one unless another file is named (owned test fixtures)."""
    raw = Path(path).read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    contract_sha = sha256_bytes(raw)
    problems = []
    for key, value in (("contract_id", bm.CONTRACT_ID), ("population_id", bm.POPULATION), ("labels", bm.LABELS),
                       ("record_labels", bm.RECORD_LABELS), ("split", bm.SPLIT), ("models", bm.MODELS),
                       ("numeric_contract", bm.NUMERIC_CONTRACT), ("scope", bm.SCOPE)):
        if bm.canonical_json_bytes(contract.get(key)) != bm.canonical_json_bytes(value):
            problems.append(key)
    payloads = (contract.get("outputs") or {}).get("payloads")
    if payloads != [f"{t}.jsonl.gz" for t in bm.RECORD_TABLES] + ["summary.json"]:
        problems.append("outputs.payloads")
    parent = contract.get("parent") or {}
    history = parent.get("history")
    if not isinstance(history, dict) or sorted(history) != sorted(bm.ANCHORS["history"]):
        problems.append("parent.history")
    history_contract = Path(history_contract) if history_contract else REPO_ROOT / Path(*HISTORY_CONTRACT.split("/"))
    if not history_contract.is_file() or (isinstance(history, dict) and
                                          sha256_file(history_contract) != history.get("contract_sha256")):
        problems.append("parent.history.contract_sha256")
    try:
        registry = _split_registry_rows()
        seasons = {p["split_id"]: p["seasons"] for p in bm.SPLIT["partitions"]}
        if (registry["SPLIT-DEV-HIST"]["season_end"], registry["SPLIT-DEV-SEL"]["season_start"],
                registry["SPLIT-DEV-SEL"]["season_end"], registry["SPLIT-PROTECTED"]["season_start"],
                registry["SPLIT-PROTECTED"]["season_end"], registry["SPLIT-FORWARD"]["season_start"]) != \
                (str(seasons["SPLIT-DEV-HIST"][-1]), "2023", "2023", "2024", "2025", "2026"):
            problems.append("split.registry_rows")
    except (OSError, KeyError, BuildRefused):
        problems.append("split.registry")
    if problems:
        raise BuildRefused("CONTRACT_INVALID", f"contract differs from the reader's rules on {problems}")
    anchors = {"contract_sha256": contract_sha, "contract_id": contract["contract_id"], "history": dict(history)}
    return contract, contract_sha, anchors


# --------------------------------------------------------------------------------------------- checkpoint

def _keys_sha(keys: Sequence[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


class Checkpoint:
    """A hash-chained target checkpoint: each chunk of targets' record lines is written once (deterministic gzip) and
    its ledger row chains the prefix."""

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
        return self.dir / "chunks" / f"chunk_{index:06d}.gz"

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


def build_lines(derived: dict[str, Any], keys: list[str], *, chunk_size: int, checkpoint: Checkpoint | None,
                stop_after: int | None) -> dict[str, list[str]] | None:
    """The record lines of every table, through the checkpoint when one is used (None when interrupted)."""
    if checkpoint is None:
        return bm.record_lines(derived)
    done = checkpoint.completed(keys)
    prefix = done[-1]["prefix_sha256"] if done else ""
    index, written = len(done), 0
    while index * chunk_size < len(keys):
        index += 1
        start = (index - 1) * chunk_size
        chunk_keys = keys[start:start + chunk_size]
        blob = gzip.compress(bm.target_chunk(derived, chunk_keys), compresslevel=9, mtime=0)
        prefix = checkpoint.write_chunk(index, chunk_keys, blob, prefix)["prefix_sha256"]
        written += 1
        if stop_after is not None and written >= stop_after and index * chunk_size < len(keys):
            return None
    rows = checkpoint.completed(keys)
    if sum(row["count"] for row in rows) != len(keys):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "the checkpoint does not cover every target")
    out: dict[str, list[str]] = {table: [] for table in bm.RECORD_TABLES}
    for row in rows:
        for entry in gzip.decompress(checkpoint.chunk_path(row["index"]).read_bytes()).decode("utf-8").splitlines():
            table, _, line = entry.partition("\t")
            out[table].append(line)
    # chunks are target-major; the payload order is table by table in target order
    order = {key: i for i, key in enumerate(keys)}
    for table in bm.RECORD_TABLES:
        out[table].sort(key=lambda line: order[json.loads(line)["contest_key"]])
    return out


# --------------------------------------------------------------------------------------------- materialization

def runtime() -> dict[str, str]:
    return {"implementation": platform.python_implementation(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "zlib": zlib.ZLIB_VERSION}


def materialize(output_root: Path, manifest_root: Path, identity_document: dict[str, Any],
                files: dict[str, Path | bytes], provenance: dict[str, Any]) -> dict[str, Any]:
    """Create-only content-addressed write: verify an existing identity, never overwrite it."""
    identity = sha256_bytes(bm.canonical_json_bytes(identity_document))
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
        # canonical bytes, never Python equality (an integral float count equals its integer there)
        if existing.get("identity") != identity or bm.canonical_json_bytes(existing.get("identity_document")) != \
                bm.canonical_json_bytes(identity_document):
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
    contract, contract_sha, anchors = load_contract(args.contract, args.history_contract)
    if args.chunk_size < 0 or (args.stop_after_chunks is not None and args.stop_after_chunks < 1):
        raise BuildRefused("ARGUMENT_INVALID", "chunk size and stop-after must be positive")
    if (args.resume or args.stop_after_chunks is not None) and not args.checkpoint_dir:
        raise BuildRefused("ARGUMENT_INVALID", "--resume and --stop-after-chunks need --checkpoint-dir")
    if args.checkpoint_dir and args.chunk_size < 1:
        raise BuildRefused("ARGUMENT_INVALID", "--checkpoint-dir needs --chunk-size >= 1")
    try:
        inputs = bm.load_history(args.history_database, anchors, input_order=args.input_order)
        derived = bm.derive(inputs, anchors)
    except bm.BenchmarkError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    keys = [t["contest_key"] for t in derived["targets"]]
    checkpoint = None
    if args.checkpoint_dir:
        header = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha,
                  "history_database_identity": inputs["binding"]["database_identity"],
                  "payload_schema": bm.PAYLOAD_SCHEMA, "chunk_size": args.chunk_size,
                  "target_key_list_sha256": _keys_sha(keys), "target_count": len(keys),
                  "producer_sha256": sha256_file(Path(__file__)), "reader_sha256": sha256_file(Path(bm.__file__))}
        checkpoint = Checkpoint(Path(args.checkpoint_dir), header, args.chunk_size, args.resume)
    built = build_lines(derived, keys, chunk_size=args.chunk_size, checkpoint=checkpoint,
                        stop_after=args.stop_after_chunks)
    if built is None:
        return {"state": "INTERRUPTED_AT_CHECKPOINT", "checkpoint_dir": str(args.checkpoint_dir),
                "completed_chunks": len(checkpoint.completed(keys)) if checkpoint else 0, "target_count": len(keys)}
    if built != bm.record_lines(derived):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpointed records differ from the derivation")
    payloads = bm.payloads(derived)
    document = bm.content_document(contract["contract_id"], contract_sha, anchors, payloads, bm.row_counts(derived),
                                   bm.uncompressed_sha256(derived))
    content_identity = sha256_bytes(bm.canonical_json_bytes(document))
    meta = bm.meta_values(document, content_identity, derived["summary"], anchors)
    with tempfile.TemporaryDirectory(prefix="nrb-") as work:
        db_path = Path(work) / bm.DB_FILE
        table_counts = bm.build_database(db_path, derived, meta)
        database_doc = bm.database_document(contract_sha, content_identity, sha256_file(db_path), table_counts)
        database_identity = sha256_bytes(bm.canonical_json_bytes(database_doc))
        provenance = {"producer": PRODUCER, "producer_path": str(Path(__file__).resolve()),
                      "producer_sha256": sha256_file(Path(__file__)), "reader_path": str(Path(bm.__file__).resolve()),
                      "reader_sha256": sha256_file(Path(bm.__file__)), "argv": list(args.argv),
                      "issued_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
                      "runtime": runtime(), "variant": args.variant, "input_order": args.input_order,
                      "chunk_size": args.chunk_size, "resumed": bool(args.resume), "jira_key": contract.get("jira_key"),
                      "cycle_number": contract.get("cycle_number"), "attempt_number": contract.get("attempt_number"),
                      "history_database": str(args.history_database),
                      "content_identity": content_identity, "database_identity": database_identity}
        content = materialize(args.output_root, args.manifest_root, document, dict(payloads), provenance)
        database = materialize(args.output_root, args.manifest_root, database_doc, {bm.DB_FILE: db_path}, provenance)
    materialized_db = Path(database["data_dir"]) / bm.DB_FILE
    try:
        with bm.RetrospectiveBenchmark(materialized_db, history_database=args.history_database,
                                       anchors=anchors) as reader:
            reader_check = {"verified": True, "identity": reader.database_identity,
                            "content_identity": reader.content_identity}
    except bm.BenchmarkError as exc:
        raise BuildRefused("MATERIALIZED_BENCHMARK_REFUSED_BY_READER", str(exc)) from exc
    production = {k: v for k, v in bm.ANCHORS.items() if k != "contract_sha256"}
    return {"state": content["state"], "content_identity": content_identity, "database_identity": database_identity,
            "content": content, "database": database, "reader_check": reader_check,
            "row_counts": document["row_counts"], "table_counts": table_counts,
            "payload_sha256": document["outputs"], "uncompressed_sha256": document["uncompressed_sha256"],
            "database_sha256": database_doc["outputs"], "summary": derived["summary"],
            "contract_sha256": contract_sha, "contract_id": contract["contract_id"],
            "anchors_equal_production": {k: v for k, v in anchors.items() if k != "contract_sha256"} == production,
            "contract_pinned_by_reader": contract_sha == bm.ANCHORS["contract_sha256"],
            "history": inputs["binding"], "input_order": args.input_order, "chunk_size": args.chunk_size,
            "resumed": bool(args.resume), "variant": args.variant, "runtime": runtime(),
            "seconds": round(time.time() - started, 3)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_retrospective_baseline", allow_abbrev=False,
                                     description="Build the fixed retrospective 2016-2023 baseline benchmark.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--history-database", required=True, type=Path)
    parser.add_argument("--history-contract", type=Path, default=None,
                        help="the history contract the history was built under (default: this checkout's accepted one)")
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
    args.argv = ["tools/build_national_retrospective_baseline.py", *raw]
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
