r"""Build the explicit national retrospective reference comparison over the accepted 2016-2023 targets (BAT-423
bounded research contribution, Cycle #56 TP56-A01).

``python -B tools/build_national_retrospective_reference.py
--contract configs/national_retrospective_reference_2016_2023_contract.json
--history-database <data>/canonical/national_history_prefix_2016_2023/sha256/<id>/national_history.sqlite
--population-database <data>/canonical/national_di_population_2016_2025/sha256/<id>/national_population.sqlite
--benchmark-database <data>/canonical/national_retrospective_baseline_2016_2023/sha256/<id>/national_retrospective_baseline.sqlite
--output-root <data>/canonical/national_retrospective_reference_2016_2023
--manifest-root <data>/manifests/national_retrospective_reference_2016_2023``

The builder refuses unless the contract's models, numeric contract, labels, split, scope, slices, calibration, design
columns, Elo parameters and parent identities equal the rules of
:mod:`aggie_analytics.retrospective_baseline.reference` (the reader re-derives exactly the same records, refit
included, before it serves any row), the governing split registry and the three accepted parent contracts in this
checkout carry their bound SHA-256, the history and parent population databases verify and pin, and the accepted C47
benchmark verifies through its own reader with every C47 estimate and label line equal to the reference's copies. It
derives the pool, features, Elo, the 2016-2022 fits, estimates, labels, scores, parameters and the summary, writes the
five payloads and the deterministic SQLite database and materializes both create-only and content addressed: an
existing identity is verified, never rewritten. The materialized database is then opened through the reader's full
verification with the contract's anchors. ``--input-order`` (natural, reverse, shuffle:<seed>), ``--chunk-size``
(targets per checkpoint chunk) with ``--checkpoint-dir`` and ``--stop-after-chunks`` / ``--resume`` exist to prove that
order, chunking and an interrupted build cannot change a byte. No protected or forward outcome, ranking, venue, market,
weather, player or held model output is read; nothing is tuned against 2023.
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
from aggie_analytics.retrospective_baseline import reference as rc  # noqa: E402

PRODUCER = "national_retrospective_reference/1.0.0"
CHECKPOINT_SCHEMA = "BAS-RETROSPECTIVE-REFERENCE-CHECKPOINT-1"
INTERRUPTED_EXIT = 3
PARENT_CONTRACTS = {"history": "configs/national_history_prefix_2016_2023_contract.json",
                    "population": "configs/national_di_population_2016_2025_contract.json",
                    "benchmark": "configs/national_retrospective_baseline_2016_2023_contract.json"}


class BuildRefused(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return bm.sha256_file(path)


def _split_registry_rows() -> dict[str, dict[str, str]]:
    path = REPO_ROOT / Path(*rc.SPLIT["registry_path"].split("/"))
    raw = path.read_bytes()
    if sha256_bytes(raw) != rc.SPLIT["registry_sha256"]:
        raise BuildRefused("CONTRACT_INVALID", "the governing split registry differs from its bound SHA-256")
    return {row["split_id"]: row for row in csv.DictReader(io.StringIO(raw.decode("utf-8")))}


def load_contract(path: Path, parent_contracts: dict[str, Path | None] | None = None
                  ) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """The contract, its SHA-256 and the anchors it binds; refuses any drift from the reader's rules. The bound parent
    contracts are this checkout's accepted ones unless other files are named (owned test fixtures)."""
    raw = Path(path).read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    contract_sha = sha256_bytes(raw)
    problems = []
    for key, value in (("contract_id", rc.CONTRACT_ID), ("population_id", rc.POPULATION), ("labels", rc.LABELS),
                       ("record_labels", rc.RECORD_LABELS), ("split", rc.SPLIT), ("models", rc.MODELS),
                       ("numeric_contract", rc.NUMERIC_CONTRACT), ("scope", rc.SCOPE), ("slices", rc.SLICES),
                       ("calibration", rc.CALIBRATION), ("design_columns", list(rc.COLUMNS)), ("elo", rc.ELO)):
        if bm.canonical_json_bytes(contract.get(key)) != bm.canonical_json_bytes(value):
            problems.append(key)
    payloads = (contract.get("outputs") or {}).get("payloads")
    if payloads != [f"{t}.jsonl.gz" for t in rc.RECORD_TABLES] + ["summary.json"]:
        problems.append("outputs.payloads")
    parent = contract.get("parent") or {}
    for name in ("history", "population", "benchmark"):
        binding = parent.get(name)
        if not isinstance(binding, dict) or sorted(binding) != sorted(rc.ANCHORS[name]):
            problems.append(f"parent.{name}")
            continue
        named = (parent_contracts or {}).get(name)
        contract_path = Path(named) if named else REPO_ROOT / Path(*PARENT_CONTRACTS[name].split("/"))
        if not contract_path.is_file() or sha256_file(contract_path) != binding.get("contract_sha256"):
            problems.append(f"parent.{name}.contract_sha256")
    expected = parent.get("expected")
    if not isinstance(expected, dict) or sorted(expected) != sorted(rc.ANCHORS["expected"]) or \
            not all(bm.is_int(v) for v in expected.values()):
        problems.append("parent.expected")
    try:
        registry = _split_registry_rows()
        seasons = {p["split_id"]: p["seasons"] for p in rc.SPLIT["partitions"]}
        if (registry["SPLIT-DEV-HIST"]["season_end"], registry["SPLIT-DEV-SEL"]["season_start"],
                registry["SPLIT-DEV-SEL"]["season_end"], registry["SPLIT-PROTECTED"]["season_start"],
                registry["SPLIT-PROTECTED"]["season_end"], registry["SPLIT-FORWARD"]["season_start"]) != \
                (str(seasons["SPLIT-DEV-HIST"][-1]), "2023", "2023", "2024", "2025", "2026"):
            problems.append("split.registry_rows")
    except (OSError, KeyError, BuildRefused):
        problems.append("split.registry")
    if problems:
        raise BuildRefused("CONTRACT_INVALID", f"contract differs from the reader's rules on {problems}")
    anchors = {"contract_sha256": contract_sha, "contract_id": contract["contract_id"],
               "history": dict(parent["history"]), "population": dict(parent["population"]),
               "benchmark": dict(parent["benchmark"]), "expected": dict(expected)}
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
    """The record lines of every seasonal table, through the checkpoint when one is used (None when interrupted)."""
    lines = rc.record_lines(derived)
    if checkpoint is None:
        return {table: list(lines[table]) for table in rc.SEASONAL_TABLES}
    done = checkpoint.completed(keys)
    prefix = done[-1]["prefix_sha256"] if done else ""
    index, written = len(done), 0
    while index * chunk_size < len(keys):
        index += 1
        start = (index - 1) * chunk_size
        chunk_keys = keys[start:start + chunk_size]
        blob = gzip.compress(rc.target_chunk(derived, chunk_keys), compresslevel=9, mtime=0)
        prefix = checkpoint.write_chunk(index, chunk_keys, blob, prefix)["prefix_sha256"]
        written += 1
        if stop_after is not None and written >= stop_after and index * chunk_size < len(keys):
            return None
    rows = checkpoint.completed(keys)
    if sum(row["count"] for row in rows) != len(keys):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "the checkpoint does not cover every target")
    out: dict[str, list[str]] = {table: [] for table in rc.SEASONAL_TABLES}
    for row in rows:
        for entry in gzip.decompress(checkpoint.chunk_path(row["index"]).read_bytes()).decode("utf-8").splitlines():
            table, _, line = entry.partition("\t")
            out[table].append(line)
    # chunks are target-major; the payload order is table by table in target order (stable within a target)
    order = {key: i for i, key in enumerate(keys)}
    for table in rc.SEASONAL_TABLES:
        out[table].sort(key=lambda line: order[json.loads(line)["contest_key"]])
    return out


# --------------------------------------------------------------------------------------------- C47 preservation

def verify_benchmark(benchmark_database: Path, history_database: Path, anchors: dict[str, Any],
                     derived: dict[str, Any]) -> dict[str, Any]:
    """The accepted C47 benchmark through its own reader (complete re-derivation), pinned to the contract's benchmark
    binding, with every C47 estimate and label line byte-equal to the reference's copies."""
    try:
        with bm.RetrospectiveBenchmark(Path(benchmark_database), history_database=Path(history_database),
                                       anchors=rc.history_anchors(anchors)) as reader:
            identity, content = reader.database_identity, reader.content_identity
            sqlite_sha = reader.binding["sha256"]
            c47_lines = bm.record_lines(reader.derived)
    except bm.BenchmarkError as exc:
        raise BuildRefused("REFERENCE_C47_BENCHMARK_REFUSED", str(exc)) from exc
    b = anchors["benchmark"]
    if (identity, content, sqlite_sha) != (b["database_identity"], b["content_identity"], b["sqlite_sha256"]):
        raise BuildRefused("REFERENCE_C47_BENCHMARK_MISMATCH", "the benchmark differs from the contract's binding")
    ours = [line for record, line in zip(derived["estimates"], rc.record_lines(derived)["estimates"])
            if record["model_id"] in rc.C47_MODELS]
    if ours != c47_lines["estimates"] or rc.record_lines(derived)["labels"] != c47_lines["labels"]:
        raise BuildRefused("REFERENCE_C47_BYTES_CHANGED", "the reference's C47 estimate or label lines differ")
    old = [json.loads(line)["contest_key"] for line in c47_lines["labels"]]
    new = [t["contest_key"] for t in derived["targets"]]
    overlap = {"old_c47_targets": len(old), "new_reference_targets": len(new),
               "overlap": len(set(old) & set(new)), "only_old": sorted(set(old) - set(new))[:20],
               "only_new": sorted(set(new) - set(old))[:20], "same_order": old == new}
    if overlap["only_old"] or overlap["only_new"] or not overlap["same_order"] or len(set(new)) != len(new):
        raise BuildRefused("REFERENCE_C47_KEY_OVERLAP_INEXACT", f"old/new target keys differ: {overlap}")
    return {"database_identity": identity, "content_identity": content, "sqlite_sha256": sqlite_sha,
            "estimate_lines_equal": len(ours), "label_lines_equal": len(c47_lines["labels"]),
            "key_overlap": overlap}


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


def fit_brief(derived: dict[str, Any]) -> dict[str, Any]:
    fits = derived["fits"]
    return {name: {"state": fit.state, "newton_steps": fit.iterations, "objective": repr(fit.objective),
                   "gradient_or_residual_inf_norm": repr(fit.gradient_inf_norm),
                   "coefficients": [rc.dec12(b) for b in fit.coefficients]}
            for name, fit in (("logistic", fits["logistic"]), ("ridge", fits["ridge"]))} | {
        "scales": [rc.dec12(s) for s in fits["scales"]], "training_targets": fits["training_targets"],
        "used": fits["used"], "excluded": fits["excluded"]}


def build(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    contract, contract_sha, anchors = load_contract(args.contract, {"history": args.history_contract,
                                                                    "population": args.population_contract,
                                                                    "benchmark": args.benchmark_contract})
    if args.chunk_size < 0 or (args.stop_after_chunks is not None and args.stop_after_chunks < 1):
        raise BuildRefused("ARGUMENT_INVALID", "chunk size and stop-after must be positive")
    if (args.resume or args.stop_after_chunks is not None) and not args.checkpoint_dir:
        raise BuildRefused("ARGUMENT_INVALID", "--resume and --stop-after-chunks need --checkpoint-dir")
    if args.checkpoint_dir and args.chunk_size < 1:
        raise BuildRefused("ARGUMENT_INVALID", "--checkpoint-dir needs --chunk-size >= 1")
    try:
        inputs = rc.load_inputs(args.history_database, args.population_database, anchors,
                                input_order=args.input_order)
        derived = rc.derive(inputs, anchors)
    except rc.ReferenceError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    counts = {"targets": len(derived["targets"]), "views": len(derived["features"]),
              "pool": len(inputs["pool"]["rows"]), "training_targets": derived["fits"]["training_targets"],
              "comparison_targets": len(derived["targets"]) - derived["fits"]["training_targets"]}
    if counts != anchors["expected"]:
        raise BuildRefused("REFERENCE_POPULATION_COUNT_MISMATCH", f"{counts} != {anchors['expected']}")
    c47 = verify_benchmark(args.benchmark_database, args.history_database, anchors, derived)
    keys = [t["contest_key"] for t in derived["targets"]]
    checkpoint = None
    if args.checkpoint_dir:
        header = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha,
                  "history_database_identity": inputs["history"]["binding"]["database_identity"],
                  "population_database_identity": inputs["pool"]["binding"]["database_identity"],
                  "payload_schema": rc.PAYLOAD_SCHEMA, "chunk_size": args.chunk_size,
                  "target_key_list_sha256": _keys_sha(keys), "target_count": len(keys),
                  "producer_sha256": sha256_file(Path(__file__)), "reader_sha256": sha256_file(Path(rc.__file__))}
        checkpoint = Checkpoint(Path(args.checkpoint_dir), header, args.chunk_size, args.resume)
    built = build_lines(derived, keys, chunk_size=args.chunk_size, checkpoint=checkpoint,
                        stop_after=args.stop_after_chunks)
    if built is None:
        return {"state": "INTERRUPTED_AT_CHECKPOINT", "checkpoint_dir": str(args.checkpoint_dir),
                "completed_chunks": len(checkpoint.completed(keys)) if checkpoint else 0, "target_count": len(keys)}
    if built != {table: rc.record_lines(derived)[table] for table in rc.SEASONAL_TABLES}:
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpointed records differ from the derivation")
    payloads = rc.payloads(derived)
    document = rc.content_document(contract["contract_id"], contract_sha, anchors, payloads, rc.row_counts(derived),
                                   rc.uncompressed_sha256(derived))
    content_identity = sha256_bytes(bm.canonical_json_bytes(document))
    meta = rc.meta_values(document, content_identity, derived["summary"], anchors)
    with tempfile.TemporaryDirectory(prefix="nrr-") as work:
        db_path = Path(work) / rc.DB_FILE
        table_counts = rc.build_database(db_path, derived, meta)
        database_doc = rc.database_document(contract_sha, content_identity, sha256_file(db_path), table_counts)
        database_identity = sha256_bytes(bm.canonical_json_bytes(database_doc))
        provenance = {"producer": PRODUCER, "producer_path": str(Path(__file__).resolve()),
                      "producer_sha256": sha256_file(Path(__file__)), "reader_path": str(Path(rc.__file__).resolve()),
                      "reader_sha256": sha256_file(Path(rc.__file__)), "argv": list(args.argv),
                      "issued_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
                      "runtime": runtime(), "variant": args.variant, "input_order": args.input_order,
                      "chunk_size": args.chunk_size, "resumed": bool(args.resume), "jira_key": contract.get("jira_key"),
                      "cycle_number": contract.get("cycle_number"), "attempt_number": contract.get("attempt_number"),
                      "history_database": str(args.history_database),
                      "population_database": str(args.population_database),
                      "benchmark_database": str(args.benchmark_database),
                      "content_identity": content_identity, "database_identity": database_identity}
        content = materialize(args.output_root, args.manifest_root, document, dict(payloads), provenance)
        database = materialize(args.output_root, args.manifest_root, database_doc, {rc.DB_FILE: db_path}, provenance)
    materialized_db = Path(database["data_dir"]) / rc.DB_FILE
    try:
        with rc.ReferenceComparison(materialized_db, history_database=args.history_database,
                                    population_database=args.population_database, anchors=anchors) as reader:
            reader_check = {"verified": True, "identity": reader.database_identity,
                            "content_identity": reader.content_identity}
    except rc.ReferenceError as exc:
        raise BuildRefused("MATERIALIZED_REFERENCE_REFUSED_BY_READER", str(exc)) from exc
    production = {k: v for k, v in rc.ANCHORS.items() if k != "contract_sha256"}
    return {"state": content["state"], "content_identity": content_identity, "database_identity": database_identity,
            "content": content, "database": database, "reader_check": reader_check, "c47_preservation": c47,
            "population_counts": counts, "row_counts": document["row_counts"], "table_counts": table_counts,
            "payload_sha256": document["outputs"], "uncompressed_sha256": document["uncompressed_sha256"],
            "database_sha256": database_doc["outputs"], "fits": fit_brief(derived),
            "elo": {k: derived["elo"][k] for k in ("games", "games_by_season", "dates")},
            "summary_population": derived["summary"]["population"], "summary_sha256": meta["summary_sha256"],
            "contract_sha256": contract_sha, "contract_id": contract["contract_id"],
            "anchors_equal_production": {k: v for k, v in anchors.items() if k != "contract_sha256"} == production,
            "contract_pinned_by_reader": contract_sha == rc.ANCHORS["contract_sha256"],
            "history": inputs["history"]["binding"], "population": inputs["pool"]["binding"],
            "parent_rows_read": inputs["pool"]["parent_rows_read"], "input_order": args.input_order,
            "chunk_size": args.chunk_size, "resumed": bool(args.resume), "variant": args.variant,
            "runtime": runtime(), "seconds": round(time.time() - started, 3)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_retrospective_reference", allow_abbrev=False,
                                     description="Build the national retrospective reference comparison 2016-2023.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--history-database", required=True, type=Path)
    parser.add_argument("--population-database", required=True, type=Path)
    parser.add_argument("--benchmark-database", required=True, type=Path)
    parser.add_argument("--history-contract", type=Path, default=None,
                        help="the history contract (default: this checkout's accepted one)")
    parser.add_argument("--population-contract", type=Path, default=None,
                        help="the parent population contract (default: this checkout's accepted one)")
    parser.add_argument("--benchmark-contract", type=Path, default=None,
                        help="the C47 benchmark contract (default: this checkout's accepted one)")
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
    args.argv = ["tools/build_national_retrospective_reference.py", *raw]
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
