r"""Build the explicit national personnel evidence release 2004-2022 (BAT-730 bounded personnel contribution, Cycle #59
TP59-A01).

``python -B tools/build_national_personnel_evidence.py
--contract configs/national_personnel_evidence_2004_2022_contract.json
--data-root <data>
--output-root <data>/canonical/national_personnel_evidence_2004_2022
--manifest-root <data>/manifests/national_personnel_evidence_2004_2022``

The builder refuses unless the contract's rules, labels, inputs, captures, parent contracts, expected collections and
outputs equal the rules and pinned authority of :mod:`aggie_analytics.personnel_evidence.evidence`, every parent contract
in this checkout hashes to its pin, and every pinned input verifies under the named data root (Parquet decoded only by
the pinned Polars). It derives every record of the six grains and the census, writes the deterministic SQLite database
and materializes it create-only and content addressed: an existing identity is verified, never rewritten, and differing
bytes at an existing identity are refused. The materialized database is then opened through the reader's full
verification with the contract's anchors. ``--input-order`` (natural, reverse, shuffle:<seed>), ``--chunk-size``
(seasons per checkpoint chunk) with ``--checkpoint-dir`` and ``--stop-after-chunks`` / ``--resume`` exist to prove that
order, chunking and an interrupted build cannot change a byte. No source request, model fit, activation or admission is
made.

Adapted from the accepted Cycle 58 builder ``tools/build_national_game_context.py`` (its checkpoint, order,
materialization and receipt machinery; the checkpoint unit here is one season); the derivation is the personnel module's.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import gzip
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

from aggie_analytics.personnel_evidence import evidence as pe  # noqa: E402

PRODUCER = "national_personnel_evidence_2004_2022/1.0.0"
CHECKPOINT_SCHEMA = "BAS-PERSONNEL-EVIDENCE-CHECKPOINT-1"
INTERRUPTED_EXIT = 3
ANCHOR_KEYS = ("inputs", "captures", "parent_contracts", "expected")


class BuildRefused(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return pe.sha256_file(path)


def load_contract(path: Path, repo_root: Path) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """The contract, its SHA-256 and the anchors it binds; refuses any drift from the module's rules and pinned
    authority, and any parent contract of this checkout that differs from its pin."""
    raw = Path(path).read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    contract_sha = sha256_bytes(raw)
    problems = []
    for key, value in (("contract_id", pe.CONTRACT_ID), ("population_id", pe.POPULATION),
                       ("rules", pe.rules_document())):
        if pe.canonical_json_bytes(contract.get(key)) != pe.canonical_json_bytes(value):
            problems.append(key)
    if (contract.get("outputs") or {}).get("database") != pe.DB_FILE:
        problems.append("outputs.database")
    for key in ANCHOR_KEYS:
        if not isinstance(contract.get(key), dict):
            problems.append(key)
    if problems:
        raise BuildRefused("CONTRACT_INVALID", f"contract differs from the module's rules on {problems}")
    for rel, want in contract["parent_contracts"].items():
        local = Path(repo_root) / Path(*rel.split("/"))
        if not local.is_file() or sha256_file(local) != want:
            raise BuildRefused("PARENT_CONTRACT_MISMATCH", f"{rel}: the checkout's bytes differ from the pin")
    anchors = {"contract_id": contract["contract_id"], "contract_sha256": contract_sha,
               **{key: contract[key] for key in ANCHOR_KEYS}}
    return contract, contract_sha, anchors


# --------------------------------------------------------------------------------------------- checkpoint

def _keys_sha(keys: Sequence[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


class Checkpoint:
    """A hash-chained season checkpoint: each chunk of seasons' record lines is written once (deterministic gzip) and its
    ledger row chains the prefix (the accepted C58/C56 builder's checkpoint, unchanged but for the unit)."""

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


def build_lines(derived: dict[str, Any], seasons: list[str], *, chunk_size: int, checkpoint: Checkpoint | None,
                stop_after: int | None) -> dict[tuple[str, str], list[str]] | None:
    """The record lines of every per-season block, through the checkpoint when one is used (None when interrupted).
    The global witness and census blocks follow unchanged."""
    blocks = {(table, segment): list(lines) for table, segment, _records, lines in pe.block_lines(derived)}
    if checkpoint is None:
        return blocks
    done = checkpoint.completed(seasons)
    prefix = done[-1]["prefix_sha256"] if done else ""
    index, written = len(done), 0
    while index * chunk_size < len(seasons):
        index += 1
        start = (index - 1) * chunk_size
        chunk_keys = seasons[start:start + chunk_size]
        blob = gzip.compress(pe.season_chunk(derived, [int(s) for s in chunk_keys]), compresslevel=9, mtime=0)
        prefix = checkpoint.write_chunk(index, chunk_keys, blob, prefix)["prefix_sha256"]
        written += 1
        if stop_after is not None and written >= stop_after and index * chunk_size < len(seasons):
            return None
    rows = checkpoint.completed(seasons)
    if sum(row["count"] for row in rows) != len(seasons):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "the checkpoint does not cover every season")
    out: dict[tuple[str, str], list[str]] = {key: [] for key in blocks if key[1] != "GLOBAL"}
    for row in rows:
        for entry in gzip.decompress(checkpoint.chunk_path(row["index"]).read_bytes()).decode("utf-8").splitlines():
            if not entry:
                continue  # a season without records in any block
            table, segment, line = entry.split("\t", 2)
            out[(table, segment)].append(line)
    for key, lines in blocks.items():
        if key[1] == "GLOBAL":
            out[key] = lines
    return out


# --------------------------------------------------------------------------------------------- materialization

def runtime() -> dict[str, str]:
    return {"implementation": platform.python_implementation(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "zlib": zlib.ZLIB_VERSION}


def materialize(output_root: Path, manifest_root: Path, identity_document: dict[str, Any], db_path: Path,
                content_identity: str, content_doc: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    """Create-only content-addressed write: verify an existing identity, never overwrite it."""
    identity = sha256_bytes(pe.canonical_json_bytes(identity_document))
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
        data = Path(db_path).read_bytes()
        with (temporary / pe.DB_FILE).open("xb") as handle:
            handle.write(data)
        if sha256_file(temporary / pe.DB_FILE) != declared[pe.DB_FILE]:
            raise BuildRefused("WRITE_VERIFY_FAILED", pe.DB_FILE)
        os.rename(temporary, target)
    if manifest.exists():
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        # canonical bytes, never Python equality (an integral float count equals its integer there)
        if existing.get("identity") != identity or \
                pe.canonical_json_bytes(existing.get("identity_document")) != pe.canonical_json_bytes(identity_document) \
                or pe.canonical_json_bytes(existing.get("content_document")) != pe.canonical_json_bytes(content_doc):
            raise BuildRefused("REFUSED_IMMUTABLE_COLLISION", f"{manifest} names a different identity")
        manifest_state = "ALREADY_PRESENT"
    else:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"identity": identity, "identity_document": identity_document,
                                     "content_identity": content_identity, "content_document": content_doc,
                                     "provenance": provenance}, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        manifest_state = "WRITTEN"
    return {"identity": identity, "state": state, "data_dir": str(target), "manifest": str(manifest),
            "manifest_state": manifest_state}


def build(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    contract, contract_sha, anchors = load_contract(args.contract, args.repo_root)
    if args.chunk_size < 0 or (args.stop_after_chunks is not None and args.stop_after_chunks < 1):
        raise BuildRefused("ARGUMENT_INVALID", "chunk size and stop-after must be positive")
    if (args.resume or args.stop_after_chunks is not None) and not args.checkpoint_dir:
        raise BuildRefused("ARGUMENT_INVALID", "--resume and --stop-after-chunks need --checkpoint-dir")
    if args.checkpoint_dir and args.chunk_size < 1:
        raise BuildRefused("ARGUMENT_INVALID", "--checkpoint-dir needs --chunk-size >= 1")
    try:
        inputs = pe.load_inputs(args.data_root, anchors, input_order=args.input_order)
        derived = pe.derive(inputs, anchors)
    except pe.PersonnelError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    seasons = [str(s) for s in pe.ROSTER_SEASONS]
    checkpoint = None
    if args.checkpoint_dir:
        header = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha,
                  "inputs_sha256": {n: anchors["inputs"][n]["sha256"] for n in anchors["inputs"]},
                  "payload_schema": pe.PAYLOAD_SCHEMA, "chunk_size": args.chunk_size,
                  "season_list_sha256": _keys_sha(seasons), "season_count": len(seasons),
                  "producer_sha256": sha256_file(Path(__file__)), "module_sha256": sha256_file(Path(pe.__file__))}
        checkpoint = Checkpoint(Path(args.checkpoint_dir), header, args.chunk_size, args.resume)
    built = build_lines(derived, seasons, chunk_size=args.chunk_size, checkpoint=checkpoint,
                        stop_after=args.stop_after_chunks)
    if built is None:
        return {"state": "INTERRUPTED_AT_CHECKPOINT", "checkpoint_dir": str(args.checkpoint_dir),
                "completed_chunks": len(checkpoint.completed(seasons)) if checkpoint else 0,
                "season_count": len(seasons)}
    if built != {(t, s): list(lines) for t, s, _r, lines in pe.block_lines(derived)}:
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpointed records differ from the derivation")
    document = pe.content_document(anchors, derived)
    content_identity = sha256_bytes(pe.canonical_json_bytes(document))
    meta = pe.meta_values(anchors, content_identity, derived)
    work_parent = Path(args.work_root) if args.work_root else None
    with tempfile.TemporaryDirectory(prefix="npe-", dir=work_parent) as work:
        db_path = Path(work) / pe.DB_FILE
        table_counts = pe.build_database(db_path, derived, meta)
        database_doc = pe.database_document(contract_sha, content_identity, sha256_file(db_path), table_counts)
        database_identity = sha256_bytes(pe.canonical_json_bytes(database_doc))
        provenance = {"producer": PRODUCER, "producer_path": str(Path(__file__).resolve()),
                      "producer_sha256": sha256_file(Path(__file__)), "module_path": str(Path(pe.__file__).resolve()),
                      "module_sha256": sha256_file(Path(pe.__file__)), "argv": list(args.argv),
                      "issued_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
                      "runtime": runtime(), "decoder": "polars " + pe._polars().__version__,
                      "variant": args.variant, "input_order": args.input_order, "chunk_size": args.chunk_size,
                      "resumed": bool(args.resume), "jira_key": contract.get("jira_key"),
                      "cycle_number": contract.get("cycle_number"), "attempt_number": contract.get("attempt_number"),
                      "data_root": str(args.data_root), "content_identity": content_identity,
                      "database_identity": database_identity}
        result = materialize(args.output_root, args.manifest_root, database_doc, db_path, content_identity, document,
                             provenance)
    materialized_db = Path(result["data_dir"]) / pe.DB_FILE
    try:
        with pe.PersonnelEvidence(materialized_db, manifest=Path(result["manifest"]), anchors=anchors) as reader:
            reader_check = {"verified": True, "identity": reader.database_identity,
                            "content_identity": reader.content_identity}
    except pe.PersonnelError as exc:
        raise BuildRefused("MATERIALIZED_RELEASE_REFUSED_BY_READER", str(exc)) from exc
    production = {k: pe.ANCHORS[k] for k in ANCHOR_KEYS}
    return {"state": result["state"], "content_identity": content_identity, "database_identity": database_identity,
            "release": result, "reader_check": reader_check, "census": derived["census"],
            "row_counts": document["row_counts"], "table_counts": table_counts,
            "database_sha256": database_doc["outputs"][pe.DB_FILE], "database_bytes": materialized_db.stat().st_size,
            "lines_sha256": document["lines_sha256"], "census_sha256": meta["census_sha256"],
            "rules_sha256": pe.rules_sha256(), "contract_sha256": contract_sha, "contract_id": contract["contract_id"],
            "anchors_equal_production": {k: anchors[k] for k in ANCHOR_KEYS} == production,
            "contract_pinned_by_reader": contract_sha == pe.ANCHORS["contract_sha256"],
            "profile_pinned": pe.PERSONNEL_PROFILE,
            "profile_reproduced": pe.PERSONNEL_PROFILE is not None and
            (pe.PERSONNEL_PROFILE.get("content_identity"), pe.PERSONNEL_PROFILE.get("database_identity")) ==
            (content_identity, database_identity),
            "inputs": {n: {"sha256": anchors["inputs"][n]["sha256"], "path": str(inputs["paths"][n])}
                       for n in anchors["inputs"]},
            "input_order": args.input_order, "chunk_size": args.chunk_size, "resumed": bool(args.resume),
            "variant": args.variant, "runtime": runtime(), "seconds": round(time.time() - started, 3)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_personnel_evidence", allow_abbrev=False,
                                     description="Build the national personnel evidence release 2004-2022.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path,
                        help="the data root holding every pinned input at the contract's relative locators")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--manifest-root", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT,
                        help="the checkout whose parent contracts the contract pins (default: this checkout)")
    parser.add_argument("--input-order", default="natural")
    parser.add_argument("--chunk-size", type=int, default=0)
    parser.add_argument("--checkpoint-dir", type=Path, default=None)
    parser.add_argument("--stop-after-chunks", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--work-root", type=Path, default=None,
                        help="parent directory of the temporary database (default: the system temporary root)")
    parser.add_argument("--variant", default="CANONICAL")
    parser.add_argument("--receipt", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(raw)
    args.argv = ["tools/build_national_personnel_evidence.py", *raw]
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
