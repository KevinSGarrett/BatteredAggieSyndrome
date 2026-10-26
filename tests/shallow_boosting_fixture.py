"""Tiny owned worlds and coordinated forgeries for the BAT-736 national shallow-tree comparison tests (Cycle #65
TP65-A01).

Not a test module (no ``test`` prefix). Every world is real: the parent population, history prefix, C47 benchmark and
C56 reference are built by the accepted builders (``retrospective_reference_fixture``), so the embedded parent is a
genuine C56-format database with its own witness collections (a tie target, Texas A&M games, cold starts, the 2020
academic year and protected 2024/2025 rows the parent never selects). The contract is generated from that parent by the
repository generator (no fit). The test runtime has no modeling backend: :func:`synthetic_fitter` stands in for the
build-only fit with deterministic invented trees (never fitted to any data) whose backend probabilities are their own
stdlib traversal, so every build, export, traversal, served pair, score and summary rule is exercised on genuine parent
witnesses without a backend. Forged releases are coordinated: database bytes, table counts, identity documents, identity
directories and manifests are rewritten consistently, so each must be refused by its own semantic rule, never by a
stale outer hash. Nothing here is real data.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import random
import shutil
import sqlite3
import sys
import zlib
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import national_history_fixture as hx  # noqa: E402
import retrospective_reference_fixture as rfx  # noqa: E402
from aggie_analytics.retrospective_baseline import boosting_build as bb  # noqa: E402
from aggie_analytics.retrospective_baseline import boosting_comparison as bc  # noqa: E402

POP = bc.POPULATION
FROZEN_AT = "2026-10-24T00:00:00Z"
THRESHOLDS = (-3.0, -1.5, -0.5, -0.125, 0.0, 0.25, 0.75, 1.0, 2.5, 6.0)


def build_world(base: Path) -> dict[str, Any]:
    """The accepted builders' world (population, history, C47 benchmark and C56 reference) under ``base``."""
    base = Path(base)
    world = rfx.build_world(base, rfx.world_contests())
    ref_contract = rfx.write_contract(base / "rc.json", rfx.contract_for(world))
    code, ref, stderr = rfx.run_build(ref_contract, world, base)
    if code != 0:
        raise AssertionError(f"accepted reference builder refused the fixture: {stderr}")
    world.update(reference_contract=ref_contract, reference_db=rfx.database_of(ref), reference=ref)
    return world


def contract_for(world: dict[str, Any]) -> dict[str, Any]:
    return bb.make_contract(world["reference_db"], FROZEN_AT,
                            expect_parent_sha256=bc.sha256_file(world["reference_db"]))


def write_contract(path: Path, contract: dict[str, Any]) -> Path:
    Path(path).write_bytes(bb.contract_bytes(contract))
    return Path(path)


def contract_anchors(path: Path) -> dict[str, Any]:
    return bb.load_contract(path)[2]


def synthetic_export(model_id: str, seed: int = 0) -> dict[str, Any]:
    """Deterministic invented trees in the exact export schema (never fitted to any data): 100 stages, each a random
    tree within the model's depth and leaf bounds, preorder indexed."""
    params = bc.TREE_PARAMS[model_id]
    rng = random.Random(f"{model_id}:{seed}")
    stages = []
    for _ in range(params["max_iter"]):
        nodes: list[dict[str, Any]] = []
        leaves = [0]

        def grow(depth: int) -> int:
            index = len(nodes)
            nodes.append({})
            internal = depth < params["max_depth"] and leaves[0] + 2 <= params["max_leaf_nodes"] and \
                (depth == 0 or rng.random() < 0.7)
            if internal:
                leaves[0] += 1
                left = grow(depth + 1)
                right = grow(depth + 1)
                nodes[index] = {"value": 0.0, "count": 40 - depth, "feature_idx": rng.randrange(len(bc.COLUMNS)),
                                "num_threshold": rng.choice(THRESHOLDS), "missing_go_to_left": rng.random() < 0.5,
                                "left": left, "right": right, "gain": round(rng.uniform(0.01, 3.0), 6),
                                "depth": depth, "is_leaf": False, "bin_threshold": rng.randrange(256),
                                "is_categorical": False, "bitset_idx": 0}
            else:
                nodes[index] = {"value": round(rng.uniform(-0.06, 0.06), 9), "count": 20, "feature_idx": 0,
                                "num_threshold": 0.0, "missing_go_to_left": False, "left": 0, "right": 0,
                                "gain": -1.0, "depth": depth, "is_leaf": True, "bin_threshold": 0,
                                "is_categorical": False, "bitset_idx": 0}
            return index

        leaves[0] = 1
        grow(0)
        stages.append(nodes)
    return {"baseline": 0.0, "stages": stages}


def synthetic_fitter(rows: list[tuple[list[float], int, float]], views: list[list[float]],
                     seed: int = 0) -> dict[str, dict[str, Any]]:
    """The test stand-in for the build-only backend: invented exports and their own traversal as backend q."""
    out = {}
    for model_id in bc.TREE_MODELS:
        export = synthetic_export(model_id, seed)
        baseline, compiled, _counts = bc.compile_trees(model_id, export["baseline"], export["stages"])
        out[model_id] = {"export": export, "backend_q": [bc.traverse(baseline, compiled, x)[1] for x in views],
                         "executions": 1}
    return out


def run_build(contract_path: Path, world: dict[str, Any], out: Path, *extra: str,
              fitter: Callable[..., dict[str, dict[str, Any]]] | None = synthetic_fitter
              ) -> tuple[int, dict[str, Any] | None, str]:
    argv = ["--contract", str(contract_path), "--parent-database", str(world["reference_db"]),
            "--output-root", str(Path(out) / "canonical" / POP), "--manifest-root", str(Path(out) / "manifests" / POP),
            *extra]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = bb.main(argv, fitter)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


def refusal(stderr: str) -> str | None:
    return hx.refusal(stderr)


def database_of(result: dict[str, Any]) -> Path:
    return Path(result["release"]["data_dir"]) / bc.DB_FILE


def query(anchors: dict[str, Any], database: Path | str, *argv: str, front: Callable | None = None
          ) -> tuple[int, Any, str]:
    """The query's main() in process with fixture anchors; returns (exit, parsed stdout or None, stderr)."""
    from aggie_analytics.retrospective_baseline import query as q  # noqa: PLC0415
    tokens = ["--boosting-comparison", str(database), *argv]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = (front or q.main)(tokens, boosting_anchors=anchors)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


# --------------------------------------------------------------------------------------------- forged releases

class Forger:
    """Coordinated forgeries of one comparison database in owned scratch."""

    def __init__(self, database: Path, root: Path) -> None:
        self.database = Path(database)
        self.root = Path(root)
        self.manifest = json.loads(bc.manifest_path_for(self.database).read_text(encoding="utf-8"))

    def tables(self) -> dict[str, list[dict[str, Any]]]:
        conn = sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True)
        out: dict[str, list[dict[str, Any]]] = {t: [] for t in bc.RECORD_TABLES}
        for table, blob in conn.execute("SELECT record_table, block FROM blocks ORDER BY ord"):
            out[table] += [json.loads(line) for line in zlib.decompress(blob).decode("utf-8").splitlines()]
        conn.close()
        return out

    def forge(self, name: str, *, records: Callable[[dict[str, list[dict[str, Any]]]], None] | None = None,
              lines: Callable[[dict[str, list[str]]], None] | None = None, meta: dict[str, Any] | None = None,
              document: dict[str, Any] | Callable[[dict[str, Any]], None] | None = None,
              after_blocks: list[tuple[str, tuple]] | None = None, identity_override: str | None = None,
              manifest_patch: dict[str, Any] | None = None, rehash_content: bool = False,
              anchors: dict[str, Any] | None = None) -> Path:
        """Copy, mutate and rehash. ``records`` edits the decoded record lists in place (blocks are rebuilt from
        canonical lines with consistent index columns); ``lines`` edits raw lines; ``meta`` replaces meta values;
        ``document`` patches the identity document; ``after_blocks`` runs SQL after the rebuild. ``rehash_content``
        (with ``anchors``) also rebuilds the content document, the content identity and every meta claim from the
        forged records: a fully coordinated value forgery that only its own semantic rule or a pinned profile can
        refuse."""
        work = self.root / name / "work.sqlite"
        work.parent.mkdir(parents=True)
        shutil.copyfile(self.database, work)
        conn = sqlite3.connect(work)
        conn.execute("PRAGMA journal_mode = OFF")
        content_doc = copy.deepcopy(self.manifest["content_document"])
        content_identity = self.manifest["content_identity"]
        if records is not None or lines is not None:
            tables = self.tables()
            if records is not None:
                records(tables)
            raw = {t: [bc.canonical_line(r) for r in rows] for t, rows in tables.items()}
            # a raw line keeps the block of the record it replaces (an undecodable line has no season of its own)
            segments = {t: [str(r["season"]) if t in bc.SEASONAL_TABLES and isinstance(r.get("season"), int)
                            else "GLOBAL" for r in rows] for t, rows in tables.items()}
            if lines is not None:
                lines(raw)
            conn.execute("DELETE FROM blocks")
            grouped: dict[tuple[str, str], list[str]] = {}
            for table, rows in raw.items():
                for index, line in enumerate(rows):
                    segment = segments[table][index] if index < len(segments[table]) else "GLOBAL"
                    grouped.setdefault((table, segment), []).append(line)
            for ord_, (table, segment) in enumerate(bc.BLOCK_LAYOUT):
                chosen = grouped.get((table, segment), [])
                parsed = []
                for line in chosen:
                    try:
                        value = json.loads(line)
                    except (ValueError, RecursionError):
                        value = {}
                    parsed.append(value if isinstance(value, dict) else {})
                data = "".join(line + "\n" for line in chosen).encode("utf-8")
                conn.execute("INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (ord_, table, segment, len(chosen),
                              bc.record_key(table, parsed[0]) if parsed else None,
                              bc.record_key(table, parsed[-1]) if parsed else None,
                              bc.sha256_bytes(data), zlib.compress(data, 9)))
            if rehash_content:
                derived = {t: [json.loads(line) for line in raw[t]] for t in bc.RECORD_TABLES}
                content_doc = bc.content_document(anchors, derived, raw)
                content_identity = bc.sha256_bytes(bc.canonical_json_bytes(content_doc))
                for key, value in bc.meta_values(anchors, content_identity, derived, raw).items():
                    conn.execute("UPDATE meta SET value = ? WHERE key = ?", (value, key))
        for key, value in (meta or {}).items():
            text = value if isinstance(value, str) else bc.canonical_line(value)
            if conn.execute("UPDATE meta SET value = ? WHERE key = ?", (text, key)).rowcount != 1:
                raise AssertionError(f"meta forgery {key} changed nothing")
        for sql, params in after_blocks or []:
            if conn.execute(sql, params).rowcount < 1:
                raise AssertionError(f"block forgery changed nothing: {sql}")
        conn.commit()
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in bc.TABLES}
        conn.close()
        doc = copy.deepcopy(self.manifest["identity_document"])
        doc["outputs"] = {bc.DB_FILE: bc.sha256_file(work)}
        doc["table_counts"] = counts
        doc["content_identity"] = content_identity
        if callable(document):
            document(doc)
        else:
            doc.update(document or {})
        identity = identity_override or bc.sha256_bytes(bc.canonical_json_bytes(doc))
        target = self.root / name / "canonical" / POP / "sha256" / identity / bc.DB_FILE
        target.parent.mkdir(parents=True)
        shutil.move(str(work), str(target))
        man = self.root / name / "manifests" / POP / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        body = {"identity": identity, "identity_document": doc, "content_identity": content_identity,
                "content_document": content_doc, "provenance": {"forgery": name}}
        body.update(manifest_patch or {})
        man.write_text(json.dumps(body), encoding="utf-8")
        return target
