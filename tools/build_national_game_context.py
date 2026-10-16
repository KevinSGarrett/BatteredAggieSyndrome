r"""Build the explicit national 2023 game-context release over the 788 accepted targets (BAT-729 bounded context
contribution, Cycle #58 TP58-A01).

``python -B tools/build_national_game_context.py
--contract configs/national_game_context_2023_contract.json
--data-root <data>
--output-root <data>/canonical/national_game_context_2023
--manifest-root <data>/manifests/national_game_context_2023``

The builder refuses unless the contract's rules, labels, inputs, source clocks, expected complete key list and outputs
equal the rules of :mod:`aggie_analytics.game_context.context` (the reader re-derives exactly the same records before
it serves any row), every pinned input verifies under the named data root, every source clock equals its retained
acquisition receipt (the SRC-002 capture manifest and the C30 acquisition ledger rows, read here only), and the C56
reference verifies through its own accepted reader (``--verify-reference``; complete re-derivation and refit) with its
2023 score lines byte-equal to the lines the context consumes. It derives the contest, team, witness, strata and census
records, writes the five payloads and the deterministic SQLite database and materializes both create-only and content
addressed: an existing identity is verified, never rewritten. The materialized database is then opened through the
reader's full verification with the contract's anchors. ``--input-order`` (natural, reverse, shuffle:<seed>),
``--chunk-size`` (targets per checkpoint chunk) with ``--checkpoint-dir`` and ``--stop-after-chunks`` / ``--resume``
exist to prove that order, chunking and an interrupted build cannot change a byte. No source request, refit, tuning or
activation is made.

Adapted from the accepted Cycle 56 builder ``tools/build_national_retrospective_reference.py`` (its checkpoint,
order, materialization and receipt machinery); the derivation is the context module's.
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

from aggie_analytics.game_context import context as gc  # noqa: E402

PRODUCER = "national_game_context_2023/1.0.0"
CHECKPOINT_SCHEMA = "BAS-GAME-CONTEXT-CHECKPOINT-1"
INTERRUPTED_EXIT = 3


class BuildRefused(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return gc.sha256_file(path)


def load_contract(path: Path) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """The contract, its SHA-256 and the anchors it binds; refuses any drift from the reader's rules."""
    raw = Path(path).read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    contract_sha = sha256_bytes(raw)
    problems = []
    for key, value in (("contract_id", gc.CONTRACT_ID), ("population_id", gc.POPULATION),
                       ("rules", gc.rules_document())):
        if gc.canonical_json_bytes(contract.get(key)) != gc.canonical_json_bytes(value):
            problems.append(key)
    if (contract.get("outputs") or {}).get("payloads") != gc.LAYOUT["payloads"]:
        problems.append("outputs.payloads")
    inputs = contract.get("inputs")
    if not isinstance(inputs, dict) or sorted(inputs) != sorted(gc.INPUT_NAMES) or \
            any(not isinstance(inputs[n], dict) or sorted(inputs[n]) != sorted(gc.ANCHORS["inputs"][n])
                for n in gc.INPUT_NAMES):
        problems.append("inputs")
    clocks = contract.get("source_clocks")
    if not isinstance(clocks, dict) or sorted(clocks) != sorted(gc.CLOCK_SOURCES) or \
            any(not isinstance(clocks[n], dict) or sorted(clocks[n]) != sorted(gc.ANCHORS["source_clocks"][n])
                for n in gc.CLOCK_SOURCES):
        problems.append("source_clocks")
    expected = contract.get("expected")
    want = sorted(list(gc.ANCHORS["expected"]) + ["target_keys", "key_source"])
    if not isinstance(expected, dict) or sorted(expected) != want or \
            not all(gc.is_int(expected[k]) for k in ("contests", "team_views", "witnesses", "strata_rows")):
        problems.append("expected")
    elif not isinstance(expected["target_keys"], list) or \
            gc.target_keys_sha256(expected["target_keys"]) != expected["target_keys_sha256"] or \
            len(expected["target_keys"]) != expected["contests"]:
        problems.append("expected.target_keys")
    if problems:
        raise BuildRefused("CONTRACT_INVALID", f"contract differs from the reader's rules on {problems}")
    anchors = {"contract_id": contract["contract_id"], "contract_sha256": contract_sha,
               "inputs": {n: dict(inputs[n]) for n in gc.INPUT_NAMES},
               "source_clocks": {n: clocks[n] for n in gc.CLOCK_SOURCES},
               "expected": {k: expected[k] for k in gc.ANCHORS["expected"]}}
    return contract, contract_sha, anchors


def verify_source_clocks(data_root: Path, anchors: dict[str, Any]) -> dict[str, Any]:
    """Every pinned source clock against its retained receipt (read only; never a source request)."""
    out: dict[str, Any] = {}
    for name in gc.CLOCK_SOURCES:
        clock = anchors["source_clocks"][name]
        receipt_path = Path(data_root) / Path(*clock["receipt_relative_path"].split("/"))
        if not receipt_path.is_file() or sha256_file(receipt_path) != clock["receipt_sha256"]:
            raise BuildRefused("CONTEXT_SOURCE_RECEIPT_MISMATCH", f"{name}: the receipt bytes differ from the pin")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        input_sha = anchors["inputs"][name]["sha256"]
        if clock["response_sha256"] != input_sha:
            raise BuildRefused("CONTEXT_SOURCE_RECEIPT_MISMATCH", f"{name}: the clock names other response bytes")
        if "ledger_attempts" in clock:
            rows = [receipt["attempts"][i] for i in clock["ledger_attempts"]]
            facts = [(r.get("route"), r.get("parameters"), r.get("raw_sha256"), r.get("retrieved_at_utc"),
                      r.get("status"), r.get("http_status"), r.get("row_count")) for r in rows]
            want = [(clock["route"], p, input_sha, clock["retrieved_at_utc"], clock["status"], clock["http_status"],
                     clock["row_count"]) for p in clock["parameters"]]
            matching = [i for i, r in enumerate(receipt["attempts"]) if r.get("raw_sha256") == input_sha]
            if facts != want or matching != clock["ledger_attempts"]:
                raise BuildRefused("CONTEXT_SOURCE_RECEIPT_MISMATCH", f"{name}: the ledger rows differ from the clock")
        else:
            facts = {k: receipt.get(k) for k in ("capture_id", "request_id", "source_uri", "parameters",
                                                  "http_status", "result", "response_sha256", "row_count",
                                                  "retrieved_at_utc")}
            want = {k: clock[k] for k in ("capture_id", "request_id", "source_uri", "parameters", "http_status",
                                          "response_sha256", "row_count", "retrieved_at_utc")}
            want["result"] = clock["status"]
            if facts != want or receipt.get("immutable_path") != anchors["inputs"][name]["relative_path"]:
                raise BuildRefused("CONTEXT_SOURCE_RECEIPT_MISMATCH", f"{name}: the capture differs from the clock")
        out[name] = {"receipt": str(receipt_path), "receipt_sha256": clock["receipt_sha256"],
                     "retrieved_at_utc": clock["retrieved_at_utc"], "verified": True}
    return out


def verify_reference(inputs: dict[str, Any], anchors: dict[str, Any], derived: dict[str, Any]) -> dict[str, Any]:
    """The accepted C56 reference through its own reader (complete re-derivation and refit under the reader's own
    production anchors), pinned to the contract's reference binding, with every 2023 score line byte-equal to the lines
    this context consumes."""
    from aggie_analytics.retrospective_baseline import reference as rc  # noqa: PLC0415 - build-time only

    spec = anchors["inputs"]["reference"]
    try:
        with rc.ReferenceComparison(inputs["paths"]["reference"], history_database=inputs["paths"]["history"],
                                    population_database=inputs["paths"]["population"]) as reader:
            identity, content = reader.database_identity, reader.content_identity
            lines = [line for record, line in zip(reader.derived["scores"], rc.record_lines(reader.derived)["scores"])
                     if record["season"] == gc.SEASON]
            models = list(rc.MODEL_IDS)
            margin = list(rc.MARGIN_MODELS)
    except rc.ReferenceError as exc:
        raise BuildRefused("CONTEXT_REFERENCE_REFUSED", str(exc)) from exc
    if (identity, content) != (spec["database_identity"], spec["content_identity"]):
        raise BuildRefused("CONTEXT_REFERENCE_MISMATCH", "the reference differs from the contract's binding")
    consumed = sorted(line for line, _r in derived["scores"].values())
    if sorted(lines) != consumed:
        raise BuildRefused("CONTEXT_REFERENCE_BYTES_CHANGED", "the consumed 2023 score lines differ from the reader's")
    if models != list(gc.MODEL_IDS) or margin != list(gc.MARGIN_MODELS):
        raise BuildRefused("CONTEXT_REFERENCE_MODELS_CHANGED", "the reference models differ from the context's")
    return {"database_identity": identity, "content_identity": content, "score_lines_equal": len(lines),
            "models": models, "margin_models": margin, "verified_by": "ReferenceComparison (re-derivation and refit)"}


# --------------------------------------------------------------------------------------------- checkpoint

def _keys_sha(keys: Sequence[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


class Checkpoint:
    """A hash-chained target checkpoint: each chunk of targets' record lines is written once (deterministic gzip) and
    its ledger row chains the prefix (the accepted C56 builder's checkpoint, unchanged)."""

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
    """The record lines of every per-target table, through the checkpoint when one is used (None when interrupted).
    The global source-receipt witnesses follow the per-target witnesses unchanged."""
    lines = gc.record_lines(derived)
    if checkpoint is None:
        return {table: list(lines[table]) for table in gc.TARGET_TABLES}
    done = checkpoint.completed(keys)
    prefix = done[-1]["prefix_sha256"] if done else ""
    index, written = len(done), 0
    while index * chunk_size < len(keys):
        index += 1
        start = (index - 1) * chunk_size
        chunk_keys = keys[start:start + chunk_size]
        blob = gzip.compress(gc.target_chunk(derived, chunk_keys), compresslevel=9, mtime=0)
        prefix = checkpoint.write_chunk(index, chunk_keys, blob, prefix)["prefix_sha256"]
        written += 1
        if stop_after is not None and written >= stop_after and index * chunk_size < len(keys):
            return None
    rows = checkpoint.completed(keys)
    if sum(row["count"] for row in rows) != len(keys):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "the checkpoint does not cover every target")
    out: dict[str, list[str]] = {table: [] for table in gc.TARGET_TABLES}
    for row in rows:
        for entry in gzip.decompress(checkpoint.chunk_path(row["index"]).read_bytes()).decode("utf-8").splitlines():
            table, _, line = entry.partition("\t")
            out[table].append(line)
    # chunks are target-major; the payload order is table by table in target order (stable within a target)
    order = {key: i for i, key in enumerate(keys)}
    for table in gc.TARGET_TABLES:
        out[table].sort(key=lambda line: order[json.loads(line)["contest_key"]])
    out["witnesses"] += [line for record, line in zip(derived["witnesses"], lines["witnesses"])
                         if record["contest_key"] is None]
    return out


# --------------------------------------------------------------------------------------------- materialization

def runtime() -> dict[str, str]:
    return {"implementation": platform.python_implementation(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "zlib": zlib.ZLIB_VERSION}


def materialize(output_root: Path, manifest_root: Path, identity_document: dict[str, Any],
                files: dict[str, Path | bytes], provenance: dict[str, Any]) -> dict[str, Any]:
    """Create-only content-addressed write: verify an existing identity, never overwrite it."""
    identity = sha256_bytes(gc.canonical_json_bytes(identity_document))
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
        if existing.get("identity") != identity or gc.canonical_json_bytes(existing.get("identity_document")) != \
                gc.canonical_json_bytes(identity_document):
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
    clocks = verify_source_clocks(args.data_root, anchors)
    try:
        inputs = gc.load_inputs(args.data_root, anchors, input_order=args.input_order)
        derived = gc.derive(inputs, anchors)
    except gc.ContextError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    keys = list(derived["keys"])
    if keys != contract["expected"]["target_keys"]:
        raise BuildRefused("CONTEXT_TARGET_KEYS_MISMATCH", "the derived target keys differ from the contract's list")
    reference = (verify_reference(inputs, anchors, derived) if args.verify_reference
                 else {"verified_by": "NOT_REQUESTED (the pinned SHA-256 and block index only)"})
    checkpoint = None
    if args.checkpoint_dir:
        header = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha,
                  "inputs_sha256": {n: anchors["inputs"][n]["sha256"] for n in gc.INPUT_NAMES},
                  "payload_schema": gc.PAYLOAD_SCHEMA, "chunk_size": args.chunk_size,
                  "target_key_list_sha256": _keys_sha(keys), "target_count": len(keys),
                  "producer_sha256": sha256_file(Path(__file__)), "reader_sha256": sha256_file(Path(gc.__file__))}
        checkpoint = Checkpoint(Path(args.checkpoint_dir), header, args.chunk_size, args.resume)
    built = build_lines(derived, keys, chunk_size=args.chunk_size, checkpoint=checkpoint,
                        stop_after=args.stop_after_chunks)
    if built is None:
        return {"state": "INTERRUPTED_AT_CHECKPOINT", "checkpoint_dir": str(args.checkpoint_dir),
                "completed_chunks": len(checkpoint.completed(keys)) if checkpoint else 0, "target_count": len(keys)}
    if built != {table: gc.record_lines(derived)[table] for table in gc.TARGET_TABLES}:
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpointed records differ from the derivation")
    payloads = gc.payloads(derived)
    document = gc.content_document(contract_sha, anchors, payloads, gc.row_counts(derived),
                                   gc.uncompressed_sha256(derived))
    content_identity = sha256_bytes(gc.canonical_json_bytes(document))
    meta = gc.meta_values(document, content_identity, derived["census"], anchors)
    with tempfile.TemporaryDirectory(prefix="ngc-") as work:
        db_path = Path(work) / gc.DB_FILE
        table_counts = gc.build_database(db_path, derived, meta)
        database_doc = gc.database_document(contract_sha, content_identity, sha256_file(db_path), table_counts)
        database_identity = sha256_bytes(gc.canonical_json_bytes(database_doc))
        provenance = {"producer": PRODUCER, "producer_path": str(Path(__file__).resolve()),
                      "producer_sha256": sha256_file(Path(__file__)), "reader_path": str(Path(gc.__file__).resolve()),
                      "reader_sha256": sha256_file(Path(gc.__file__)), "argv": list(args.argv),
                      "issued_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
                      "runtime": runtime(), "variant": args.variant, "input_order": args.input_order,
                      "chunk_size": args.chunk_size, "resumed": bool(args.resume), "jira_key": contract.get("jira_key"),
                      "cycle_number": contract.get("cycle_number"), "attempt_number": contract.get("attempt_number"),
                      "data_root": str(args.data_root), "content_identity": content_identity,
                      "database_identity": database_identity}
        content = materialize(args.output_root, args.manifest_root, document, dict(payloads), provenance)
        database = materialize(args.output_root, args.manifest_root, database_doc, {gc.DB_FILE: db_path}, provenance)
    materialized_db = Path(database["data_dir"]) / gc.DB_FILE
    try:
        with gc.GameContext(materialized_db, data_root=args.data_root, anchors=anchors) as reader:
            reader_check = {"verified": True, "identity": reader.database_identity,
                            "content_identity": reader.content_identity}
    except gc.ContextError as exc:
        raise BuildRefused("MATERIALIZED_CONTEXT_REFUSED_BY_READER", str(exc)) from exc
    production = {k: v for k, v in gc.ANCHORS.items() if k != "contract_sha256"}
    return {"state": content["state"], "content_identity": content_identity, "database_identity": database_identity,
            "content": content, "database": database, "reader_check": reader_check, "reference": reference,
            "source_clocks": clocks, "census": derived["census"], "row_counts": document["row_counts"],
            "table_counts": table_counts, "payload_sha256": document["outputs"],
            "uncompressed_sha256": document["uncompressed_sha256"], "database_sha256": database_doc["outputs"],
            "census_sha256": meta["census_sha256"], "rules_sha256": gc.rules_sha256(),
            "contract_sha256": contract_sha, "contract_id": contract["contract_id"],
            "anchors_equal_production": {k: v for k, v in anchors.items() if k != "contract_sha256"} == production,
            "contract_pinned_by_reader": contract_sha == gc.ANCHORS["contract_sha256"],
            "inputs": {n: {"sha256": anchors["inputs"][n]["sha256"], "path": str(inputs["paths"][n])}
                       for n in gc.INPUT_NAMES},
            "input_order": args.input_order, "chunk_size": args.chunk_size, "resumed": bool(args.resume),
            "variant": args.variant, "runtime": runtime(), "seconds": round(time.time() - started, 3)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_game_context", allow_abbrev=False,
                                     description="Build the national 2023 game-context release.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path,
                        help="the data root holding every pinned input at the contract's relative locators")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--manifest-root", required=True, type=Path)
    parser.add_argument("--verify-reference", action="store_true",
                        help="also verify the C56 reference through its own accepted reader (complete re-derivation)")
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
    args.argv = ["tools/build_national_game_context.py", *raw]
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
