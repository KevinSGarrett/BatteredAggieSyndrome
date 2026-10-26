r"""Build the national frozen shallow-tree comparison release 2016-2023 (BAT-736, Cycle #65 TP65-A01).

The builder reads only the exact accepted C56 parent database (literal local spelling, layout and full SHA-256 checked
before any parse; never written), derives the canonical games, features and labels from its witness collections, fits
exactly the two frozen HistGradientBoosting definitions on the 10,174 oriented rows of the 5,087 decisive 2016-2022
games (``fit_models``: the only place that imports the build-only backend, lazily, under the pinned offline runtime),
exports both ensembles as typed plain-data trees, derives every raw witness by the stdlib traversal and requires the
backend's ``predict_proba`` to agree within 1e-12, derives every estimate, score and summary, writes one deterministic
SQLite file with the parent snapshot as a BLOB and materializes it create-only (an identical rebuild is
ALREADY_PRESENT_IDENTICAL; differing bytes are REFUSED_IMMUTABLE_COLLISION). Order, chunk and interrupt/resume variants
reproduce every byte. ``make_contract`` generates the committed contract from the module's frozen rules and the parent
alone (no fit). Nothing here makes a network request or reads a protected season.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import gzip
import json
import os
import platform
import random
import sqlite3
import sys
import tempfile
import time
import zlib
from pathlib import Path
from typing import Any, Callable, Sequence

from aggie_analytics import readonly_sqlite
from aggie_analytics.retrospective_baseline import boosting_comparison as bc

PRODUCER = "national_shallow_boosting_comparison_2016_2023/1.0.0"
CHECKPOINT_SCHEMA = "BAS-SHALLOW-BOOSTING-COMPARISON-CHECKPOINT-1"
CONTRACT_SCHEMA = "BAS-SHALLOW-BOOSTING-COMPARISON-CONTRACT-1"
INTERRUPTED_EXIT = 3
ANCHOR_KEYS = ("parent", "expected", "frozen_at_utc")
BACKEND_VERSIONS = {"sklearn": "1.9.0", "numpy": "2.5.1", "scipy": "1.18.0", "joblib": "1.5.3",
                    "threadpoolctl": "3.6.0"}
AGREEMENT_RULE = ("build-only: the backend predict_proba of every oriented view agrees with the stdlib traversal q "
                  "within absolute 1e-12, and every repeated execution of the same definition exports identical bytes; "
                  "a reader cannot recompute the backend and never imports it")


class BuildRefused(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _refuse(code: str, message: str) -> None:
    raise BuildRefused(code, message)


def _wrapped(exc: bc.BoostingError) -> BuildRefused:
    """The build refusal of a reader-rule refusal: the same code and its message (without the repeated code)."""
    text = str(exc)
    prefix = f"{exc.code}: "
    return BuildRefused(exc.code, text[len(prefix):] if text.startswith(prefix) else text)


sha256_bytes = bc.sha256_bytes
sha256_file = bc.sha256_file


# --------------------------------------------------------------------------------------------- the parent input

def load_parent(path: Path, pin: dict[str, Any] | None = None, *, expect_sha256: str | None = None) -> bytes:
    """The exact parent bytes after the copy precondition: literal local spelling, existence, the accepted layout and
    the full SHA-256 (of the pin, or the expected value given to the contract generator)."""
    try:
        literal = readonly_sqlite.literal_path(path)
    except readonly_sqlite.DatabaseLocationError as exc:
        raise BuildRefused("PARENT_LOCATION_UNSUPPORTED", exc.detail) from None
    absolute = Path(bc.native_location(literal)) if os.name == "nt" else Path(literal)
    if not bc.io_path(absolute).is_file():
        _refuse("PARENT_MISSING", "no parent database at the given location")
    if absolute.name != bc.PARENT_DB_FILE or absolute.parent.parent.name != "sha256" or \
            absolute.parent.parent.parent.name != bc.PARENT_POPULATION:
        _refuse("PARENT_LOCATION_INVALID", f"the parent must sit at <root>/{bc.PARENT_POPULATION}/sha256/<id>/"
                                           f"{bc.PARENT_DB_FILE}")
    data = bc.io_path(absolute).read_bytes()
    want = expect_sha256 if pin is None else pin["sqlite_sha256"]
    if want is None or sha256_bytes(data) != want:
        _refuse("PARENT_TAMPERED", "the parent bytes differ from the pinned SHA-256")
    if pin is not None and (len(data) != pin["bytes"] or absolute.parent.name != pin["database_identity"]):
        _refuse("PARENT_TAMPERED", "the parent byte count or identity directory differs from the pin")
    return data


def parent_pin(data: bytes, identity: str) -> dict[str, Any]:
    """The parent pin generated from the exact parent bytes (never retyped): byte count, SHA-256, identities, schema,
    contract, record counts, total decompressed bytes and the five model digests."""
    meta, records, total = _raw_parent(data)
    counts = {t: len(records[t]) for t in bc.PARENT_RECORD_TABLES}
    return {"population": bc.PARENT_POPULATION, "database_identity": identity,
            "content_identity": meta["content_identity"], "sqlite_sha256": sha256_bytes(data), "bytes": len(data),
            "schema_version": meta["schema_version"], "contract_id": meta["contract_id"],
            "contract_sha256": meta["contract_sha256"], "record_counts": counts, "blocks": len(bc.PARENT_BLOCK_LAYOUT),
            "total_decompressed_bytes": total,
            "model_sha256": {r["model_id"]: r["model_sha256"] for r in records["parameters"]}}


def _raw_parent(data: bytes) -> tuple[dict[str, str], dict[str, list[dict[str, Any]]], int]:
    conn = sqlite3.connect(":memory:")
    try:
        conn.deserialize(data)
        conn.execute("PRAGMA query_only = ON")
        meta = {k: v for k, v in conn.execute("SELECT key, value FROM meta")}
        records: dict[str, list[dict[str, Any]]] = {t: [] for t in bc.PARENT_RECORD_TABLES}
        total = 0
        for table, blob in conn.execute("SELECT record_table, block FROM blocks ORDER BY ord"):
            raw = zlib.decompress(blob)
            total += len(raw)
            records[table] += [json.loads(line) for line in raw.decode("utf-8").split("\n")[:-1]]
    finally:
        conn.close()
    return meta, records, total


def _ordered(items: list[Any], order: str) -> list[Any]:
    if order == "natural":
        return list(items)
    if order == "reverse":
        return list(reversed(items))
    if order.startswith("shuffle:") and order[8:].isdigit():
        out = list(items)
        random.Random(int(order[8:])).shuffle(out)
        return out
    _refuse("INPUT_ORDER_INVALID", "input order must be natural, reverse or shuffle:<seed>")
    return []


def parent_games(data: bytes, pin: dict[str, Any], input_order: str = "natural") -> tuple[dict[str, Any], list]:
    """The verified parent and its canonical games; the input order variant permutes the parent's record lists before
    derivation (the canonical order never depends on it)."""
    try:
        parent = bc.read_parent(data, pin)
        bc._check_parent_witnesses(parent, pin)
        for table in ("features", "labels", "scores"):
            pairs = _ordered(list(zip(parent["records"][table], parent["lines"][table])), input_order)
            parent["records"][table] = [r for r, _l in pairs]
            parent["lines"][table] = [line for _r, line in pairs]
        games = bc.games_from_parent(parent)
    except bc.BoostingError as exc:
        raise _wrapped(exc) from None
    return parent, games


# --------------------------------------------------------------------------------------------- the contract

def make_contract(parent_database: Path, frozen_at_utc: str, *, expect_parent_sha256: str, cycle_number: int = 65,
                  attempt_number: int = 1, jira_key: str = "BAT-736") -> dict[str, Any]:
    """The committed contract: the frozen rules, the parent pin and the expected key inventory, from the parent alone
    (no fit, no estimate, no score recomputation)."""
    data = load_parent(parent_database, expect_sha256=expect_parent_sha256)
    identity = Path(bc.native_location(readonly_sqlite.literal_path(parent_database))).parent.name
    pin = parent_pin(data, identity)
    _parent, games = parent_games(data, pin)
    return {"schema": CONTRACT_SCHEMA, "contract_id": bc.CONTRACT_ID, "population_id": bc.POPULATION,
            "jira_key": jira_key, "cycle_number": cycle_number, "attempt_number": attempt_number,
            "frozen_at_utc": frozen_at_utc, "rules": bc.rules_document(), "rules_sha256": bc.rules_sha256(),
            "parent": pin, "expected": bc.expected_inventory(games)}


def contract_bytes(contract: dict[str, Any]) -> bytes:
    return (json.dumps(contract, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def load_contract(path: Path) -> tuple[dict[str, Any], str, dict[str, Any]]:
    raw = Path(path).read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    contract_sha = sha256_bytes(raw)
    if contract.get("schema") != CONTRACT_SCHEMA or contract.get("contract_id") != bc.CONTRACT_ID:
        _refuse("CONTRACT_INVALID", "not the shallow-tree comparison contract")
    if bc.canonical_json_bytes(contract.get("rules")) != bc.canonical_json_bytes(bc.rules_document()) or \
            contract.get("rules_sha256") != bc.rules_sha256():
        _refuse("CONTRACT_RULES_DRIFT", "the contract rules differ from the module's frozen rules")
    anchors = {"contract_id": contract["contract_id"], "contract_sha256": contract_sha,
               **{k: contract[k] for k in ANCHOR_KEYS}}
    return contract, contract_sha, anchors


# --------------------------------------------------------------------------------------------- the build-only fit

def export_model(model: Any, model_id: str) -> dict[str, Any]:
    """The typed plain-data export of one fitted backend ensemble (TREE_EXPORT): refused unless it is binary, has
    exactly max_iter single-tree stages and no categorical bitset."""
    params = bc.TREE_PARAMS[model_id]
    if [int(c) for c in model.classes_.tolist()] != [0, 1] or int(model.n_iter_) != params["max_iter"] or \
            len(model._predictors) != params["max_iter"] or tuple(model._baseline_prediction.shape) != (1, 1):
        _refuse("FIT_EXPORT_INVALID", f"{model_id}: not a binary ensemble of {params['max_iter']} stages")
    stages = []
    for stage in model._predictors:
        if len(stage) != 1:
            _refuse("FIT_EXPORT_INVALID", f"{model_id}: a stage holds more than one tree")
        tree = stage[0]
        if tree.binned_left_cat_bitsets.size or tree.raw_left_cat_bitsets.size:
            _refuse("FIT_EXPORT_INVALID", f"{model_id}: a categorical bitset is present")
        nodes = []
        for node in tree.nodes:
            record = {}
            for name, code in bc.NODE_FIELDS.items():
                raw = node[name].item()
                if code == "f":
                    record[name] = float(raw)
                elif code == "b":
                    if int(raw) not in (0, 1):
                        _refuse("FIT_EXPORT_INVALID", f"{model_id}: flag {name} is not 0 or 1")
                    record[name] = bool(int(raw))
                else:
                    record[name] = int(raw)
            nodes.append(record)
        stages.append(nodes)
    return {"baseline": float(model._baseline_prediction[0, 0]), "stages": stages}


def fit_models(rows: list[tuple[list[float], int, float]], views: list[list[float]], *, repeats: int = 2
               ) -> dict[str, dict[str, Any]]:
    """Fit each frozen definition ``repeats`` times on the training rows (identical exports required) and measure the
    backend's agreement with the stdlib traversal on every oriented view. The only backend import, lazily."""
    import numpy as np  # noqa: PLC0415 - build-only backend
    import scipy  # noqa: PLC0415
    import joblib  # noqa: PLC0415
    import threadpoolctl  # noqa: PLC0415
    import sklearn  # noqa: PLC0415
    from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: PLC0415

    observed = {"sklearn": sklearn.__version__, "numpy": np.__version__, "scipy": scipy.__version__,
                "joblib": joblib.__version__, "threadpoolctl": threadpoolctl.__version__}
    if observed != BACKEND_VERSIONS:
        _refuse("BACKEND_VERSION_MISMATCH", f"backend versions {observed} differ from {BACKEND_VERSIONS}")
    if repeats < 1:
        _refuse("ARGUMENT_INVALID", "at least one fit execution per definition")
    x = np.array([r[0] for r in rows], dtype=np.float64)
    y = np.array([r[1] for r in rows], dtype=np.int64)
    w = np.array([r[2] for r in rows], dtype=np.float64)
    probe = np.array(views, dtype=np.float64)
    out = {}
    for model_id in bc.TREE_MODELS:
        exports, probabilities = [], []
        for _ in range(repeats):
            model = HistGradientBoostingClassifier(**bc.TREE_PARAMS[model_id])
            if model.get_params() != bc.TREE_PARAMS[model_id]:
                _refuse("FIT_PARAMS_DRIFT", f"{model_id}: the backend constructor options differ from the definition")
            model.fit(x, y, sample_weight=w)
            exports.append(export_model(model, model_id))
            probabilities.append([float(p) for p in model.predict_proba(probe)[:, 1]])
        first = bc.canonical_json_bytes(exports[0])
        if any(bc.canonical_json_bytes(e) != first for e in exports) or any(p != probabilities[0]
                                                                         for p in probabilities):
            _refuse("FIT_NOT_DETERMINISTIC", f"{model_id}: repeated executions of the same definition differ")
        out[model_id] = {"export": exports[0], "backend_q": probabilities[0], "executions": repeats}
    return out


def agreement(model_id: str, fitted: dict[str, Any], views: list[list[float]]) -> dict[str, Any]:
    baseline, compiled, _counts = bc.compile_trees(model_id, fitted["export"]["baseline"], fitted["export"]["stages"])
    worst = 0.0
    for x, backend in zip(views, fitted["backend_q"]):
        _z, q = bc.traverse(baseline, compiled, x)
        worst = max(worst, abs(q - backend))
    if not worst <= 1e-12:
        _refuse("BACKEND_DISAGREEMENT", f"{model_id}: backend and stdlib probabilities differ by {worst!r}")
    return {"state": "BUILD_ONLY_BACKEND_AGREEMENT_ATTESTATION_NOT_READER_VERIFIED", "views": len(views),
            "max_abs_difference_repr": repr(worst), "tolerance_repr": "1e-12", "repeat_fits": fitted["executions"],
            "repeat_exports_identical": True, "rule": AGREEMENT_RULE}


FitFunction = Callable[[list[tuple[list[float], int, float]], list[list[float]]], dict[str, dict[str, Any]]]


def derive_release(games: list[dict[str, Any]], fitter: FitFunction) -> tuple[dict[str, Any], dict[str, Any]]:
    """Every record of the release from the canonical games and the frozen fits."""
    rows = bc.training_rows(games)
    views = [x for g in games for x in (g["x_a"], g["x_b"])]
    fitted = fitter(rows, views)
    if sorted(fitted) != sorted(bc.TREE_MODELS):
        _refuse("FIT_EXPORT_INVALID", "the fit did not return exactly the two frozen definitions")
    census = bc.training_census(games)
    try:
        parameters = [bc.parameter_record(m, fitted[m]["export"], census, agreement(m, fitted[m], views))
                      for m in bc.TREE_MODELS]
        witnesses = bc.witness_texts(bc.raw_witnesses(games, parameters))
        derived = bc.derive(games, parameters, witnesses)
    except bc.BoostingError as exc:
        raise _wrapped(exc) from None
    executions = {m: fitted[m]["executions"] for m in bc.TREE_MODELS}
    return derived, {"fit_executions": executions, "training": census,
                     "export_sha256": {p["model_id"]: p["export_sha256"] for p in parameters}}


# --------------------------------------------------------------------------------------------- checkpoint

def _keys_sha(keys: Sequence[str]) -> str:
    return sha256_bytes("\n".join(keys).encode("utf-8"))


class Checkpoint:
    """A hash-chained game checkpoint: each chunk of canonical games' record lines is written once (deterministic
    gzip) and its ledger row chains the prefix (the accepted C64 builder's checkpoint, unchanged but for the schema)."""

    def __init__(self, directory: Path, header: dict[str, Any], chunk_size: int, resume: bool) -> None:
        self.dir = Path(directory)
        self.chunk_size = chunk_size
        self.ledger = self.dir / "checkpoint.ledger.jsonl"
        header_path = self.dir / "checkpoint.json"
        if resume:
            if not header_path.is_file():
                raise BuildRefused("REFUSED_STALE_CHECKPOINT", "no checkpoint header in the checkpoint directory")
            stored = json.loads(header_path.read_text(encoding="utf-8"))
            differing = sorted(k for k in set(stored) | set(header) if stored.get(k) != header.get(k))
            if differing:
                raise BuildRefused("REFUSED_STALE_CHECKPOINT", f"checkpoint binds different {differing}")
        else:
            if self.dir.exists() and any(self.dir.iterdir()):
                raise BuildRefused("CHECKPOINT_EXISTS", "the checkpoint directory is not empty; use --resume")
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


def build_lines(derived: dict[str, Any], keys: list[str], *, chunk_size: int, checkpoint: Checkpoint | None,
                stop_after: int | None) -> dict[tuple[str, str], list[str]] | None:
    """The record lines of every block, through the game checkpoint when one is used (None when interrupted). The global
    parameter and summary blocks follow unchanged."""
    lines = bc.record_lines(derived)
    blocks = {(table, segment): list(block) for table, segment, _records, block in bc.block_lines(derived, lines)}
    if checkpoint is None:
        return blocks
    done = checkpoint.completed(keys)
    prefix = done[-1]["prefix_sha256"] if done else ""
    index, written = len(done), 0
    while index * chunk_size < len(keys):
        index += 1
        start = (index - 1) * chunk_size
        chunk_keys = keys[start:start + chunk_size]
        blob = gzip.compress(bc.game_chunk(derived, chunk_keys, lines), compresslevel=9, mtime=0)
        prefix = checkpoint.write_chunk(index, chunk_keys, blob, prefix)["prefix_sha256"]
        written += 1
        if stop_after is not None and written >= stop_after and index * chunk_size < len(keys):
            return None
    rows = checkpoint.completed(keys)
    if sum(row["count"] for row in rows) != len(keys):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "the checkpoint does not cover every game")
    out: dict[tuple[str, str], list[str]] = {key: [] for key in blocks if key[1] != "GLOBAL"}
    for row in rows:
        for entry in gzip.decompress(checkpoint.chunk_path(row["index"]).read_bytes()).decode("utf-8").splitlines():
            if not entry:
                continue
            table, segment, line = entry.split("\t", 2)
            out[(table, segment)].append(line)
    for key, block in blocks.items():
        if key[1] == "GLOBAL":
            out[key] = block
    return out


# --------------------------------------------------------------------------------------------- materialization

def runtime() -> dict[str, str]:
    return {"implementation": platform.python_implementation(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "zlib": zlib.ZLIB_VERSION}


def materialize(output_root: Path, manifest_root: Path, identity_document: dict[str, Any], db_path: Path,
                content_identity: str, content_doc: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    """Create-only content-addressed write: verify an existing identity, never overwrite it."""
    identity = sha256_bytes(bc.canonical_json_bytes(identity_document))
    target = Path(output_root) / "sha256" / identity
    manifest = Path(manifest_root) / "sha256" / identity / "run_manifest.json"
    declared = identity_document["outputs"]
    state = "MATERIALIZED"
    if target.exists():
        present = sorted(p.name for p in target.iterdir())
        if present != sorted(declared) or any(sha256_file(target / name) != sha for name, sha in declared.items()):
            raise BuildRefused("REFUSED_IMMUTABLE_COLLISION", "the identity directory exists with different content")
        state = "ALREADY_PRESENT_IDENTICAL"
    else:
        temporary = Path(output_root) / "sha256" / f".tmp-{identity[:16]}-{os.getpid()}-{time.time_ns()}"
        temporary.mkdir(parents=True)
        data = Path(db_path).read_bytes()
        with (temporary / bc.DB_FILE).open("xb") as handle:
            handle.write(data)
        if sha256_file(temporary / bc.DB_FILE) != declared[bc.DB_FILE]:
            raise BuildRefused("WRITE_VERIFY_FAILED", bc.DB_FILE)
        os.rename(temporary, target)
    if manifest.exists():
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        # canonical bytes, never Python equality (an integral float count equals its integer there)
        if existing.get("identity") != identity or \
                bc.canonical_json_bytes(existing.get("identity_document")) != bc.canonical_json_bytes(identity_document) \
                or bc.canonical_json_bytes(existing.get("content_document")) != bc.canonical_json_bytes(content_doc):
            raise BuildRefused("REFUSED_IMMUTABLE_COLLISION", "the run manifest names a different identity")
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


def build(args: argparse.Namespace, fitter: FitFunction | None = None) -> dict[str, Any]:
    started = time.time()
    contract, contract_sha, anchors = load_contract(args.contract)
    if args.chunk_size < 0 or (args.stop_after_chunks is not None and args.stop_after_chunks < 1):
        raise BuildRefused("ARGUMENT_INVALID", "chunk size and stop-after must be positive")
    if (args.resume or args.stop_after_chunks is not None) and not args.checkpoint_dir:
        raise BuildRefused("ARGUMENT_INVALID", "--resume and --stop-after-chunks need --checkpoint-dir")
    if args.checkpoint_dir and args.chunk_size < 1:
        raise BuildRefused("ARGUMENT_INVALID", "--checkpoint-dir needs --chunk-size >= 1")
    data = load_parent(args.parent_database, anchors["parent"])
    parent, games = parent_games(data, anchors["parent"], args.input_order)
    inventory = bc.expected_inventory(games)
    if bc.canonical_json_bytes(inventory) != bc.canonical_json_bytes(anchors["expected"]):
        _refuse("REFUSED_POPULATION_DRIFT", "the parent's key inventory differs from the contract's expected inventory")
    fit = fitter or (lambda rows, views: fit_models(rows, views, repeats=args.repeat_fits))
    derived, fit_summary = derive_release(games, fit)
    keys = [g["contest_key"] for g in games]
    checkpoint = None
    if args.checkpoint_dir:
        header = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha,
                  "parent_sha256": anchors["parent"]["sqlite_sha256"], "export_sha256": fit_summary["export_sha256"],
                  "chunk_size": args.chunk_size, "game_list_sha256": _keys_sha(keys), "game_count": len(keys),
                  "producer_sha256": sha256_file(Path(__file__)), "module_sha256": sha256_file(Path(bc.__file__))}
        checkpoint = Checkpoint(Path(args.checkpoint_dir), header, args.chunk_size, args.resume)
    built = build_lines(derived, keys, chunk_size=args.chunk_size, checkpoint=checkpoint,
                        stop_after=args.stop_after_chunks)
    if built is None:
        return {"state": "INTERRUPTED_AT_CHECKPOINT", "checkpoint_dir": str(args.checkpoint_dir),
                "completed_chunks": len(checkpoint.completed(keys)) if checkpoint else 0, "game_count": len(keys),
                "fit": fit_summary}
    lines = bc.record_lines(derived)
    if built != {(t, s): list(block) for t, s, _r, block in bc.block_lines(derived, lines)}:
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpointed records differ from the derivation")
    document = bc.content_document(anchors, derived, lines)
    content_identity = sha256_bytes(bc.canonical_json_bytes(document))
    meta = bc.meta_values(anchors, content_identity, derived, lines)
    work_parent = Path(args.work_root) if args.work_root else None
    with tempfile.TemporaryDirectory(prefix="sbc-", dir=work_parent) as work:
        db_path = Path(work) / bc.DB_FILE
        table_counts = bc.build_database(db_path, derived, meta, data, built)
        database_doc = bc.database_document(contract_sha, content_identity, sha256_file(db_path), table_counts)
        database_identity = sha256_bytes(bc.canonical_json_bytes(database_doc))
        provenance = {"producer": PRODUCER, "producer_path": str(Path(__file__).resolve()),
                      "producer_sha256": sha256_file(Path(__file__)), "module_path": str(Path(bc.__file__).resolve()),
                      "module_sha256": sha256_file(Path(bc.__file__)), "argv": list(args.argv),
                      "issued_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
                      "runtime": runtime(), "variant": args.variant, "input_order": args.input_order,
                      "chunk_size": args.chunk_size, "resumed": bool(args.resume), "jira_key": contract.get("jira_key"),
                      "cycle_number": contract.get("cycle_number"), "attempt_number": contract.get("attempt_number"),
                      "fit_executions": fit_summary["fit_executions"], "content_identity": content_identity,
                      "database_identity": database_identity}
        result = materialize(args.output_root, args.manifest_root, database_doc, db_path, content_identity, document,
                             provenance)
    materialized_db = Path(result["data_dir"]) / bc.DB_FILE
    try:
        with bc.BoostingComparison(materialized_db, manifest=Path(result["manifest"]),
                                   anchors={**anchors, "profile": None}) as reader:
            reader_check = {"verified": True, "identity": reader.database_identity,
                            "content_identity": reader.content_identity, "trees_traversed": True}
    except bc.BoostingError as exc:
        raise BuildRefused("MATERIALIZED_RELEASE_REFUSED_BY_READER", str(exc)) from None
    production = {k: bc.ANCHORS.get(k) for k in ANCHOR_KEYS}
    profile = bc.BOOSTING_PROFILE
    return {"state": result["state"], "content_identity": content_identity, "database_identity": database_identity,
            "release": result, "reader_check": reader_check, "expected_inventory": inventory, "fit": fit_summary,
            "row_counts": document["row_counts"], "table_counts": table_counts,
            "database_sha256": database_doc["outputs"][bc.DB_FILE], "database_bytes": materialized_db.stat().st_size,
            "lines_sha256": document["lines_sha256"], "rules_sha256": bc.rules_sha256(),
            "contract_sha256": contract_sha, "contract_id": contract["contract_id"],
            "anchors_equal_production": {k: anchors[k] for k in ANCHOR_KEYS} == production,
            "contract_pinned_by_reader": contract_sha == bc.ANCHORS.get("contract_sha256"),
            "profile_pinned": profile,
            "profile_reproduced": profile is not None and
            (profile.get("content_identity"), profile.get("database_identity")) == (content_identity, database_identity),
            "parent": {"sqlite_sha256": anchors["parent"]["sqlite_sha256"],
                       "database_identity": anchors["parent"]["database_identity"]},
            "input_order": args.input_order, "chunk_size": args.chunk_size, "resumed": bool(args.resume),
            "variant": args.variant, "runtime": runtime(), "seconds": round(time.time() - started, 3)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_shallow_boosting_comparison", allow_abbrev=False,
                                     description="Build the national frozen shallow-tree comparison release 2016-2023.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--parent-database", required=True, type=Path,
                        help="the exact accepted C56 national_retrospective_reference.sqlite (read only)")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--manifest-root", required=True, type=Path)
    parser.add_argument("--input-order", default="natural")
    parser.add_argument("--chunk-size", type=int, default=0)
    parser.add_argument("--checkpoint-dir", type=Path, default=None)
    parser.add_argument("--stop-after-chunks", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--repeat-fits", type=int, default=2,
                        help="identical executions of each frozen definition (determinism proof; counted)")
    parser.add_argument("--work-root", type=Path, default=None,
                        help="parent directory of the temporary database (default: the system temporary root)")
    parser.add_argument("--variant", default="CANONICAL")
    parser.add_argument("--receipt", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None, fitter: FitFunction | None = None, *,
         program: str = "tools/cycle65/build_national_shallow_boosting_comparison.py") -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(raw)
    args.argv = [program, *raw]
    try:
        result = build(args, fitter)
    except BuildRefused as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    text = json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if args.receipt is not None:
        with Path(args.receipt).open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    sys.stdout.write(text)
    return INTERRUPTED_EXIT if result["state"] == "INTERRUPTED_AT_CHECKPOINT" else 0
