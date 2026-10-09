"""Tiny owned worlds and coordinated forgeries for the BAT-719 retrospective benchmark tests (Cycle #47 TP47-A01).

Not a test module (no ``test`` prefix). Every world is real: the parent is built by the accepted BAT-710 population
builder and the history by the accepted BAT-711 history-prefix builder (``national_history_fixture``), then the
benchmark by the repository builder with the committed contract whose history binding names that fixture history.
Forged history inputs and forged benchmarks are coordinated: database bytes, table counts, identity documents,
identity directories and manifests are all rewritten consistently, so each must be refused by its own semantic rule,
never by a stale outer hash.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
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
from aggie_analytics.retrospective_baseline import benchmark as bm  # noqa: E402

CONTRACT_PATH = ROOT / "configs" / "national_retrospective_baseline_2016_2023_contract.json"
BUILDER_PATH = ROOT / "tools" / "build_national_retrospective_baseline.py"
POP = bm.POPULATION


def builder() -> Any:
    return hx.load_tool(BUILDER_PATH, "bas_retrospective_baseline_builder")


def canonical(value: Any) -> str:
    return bm.canonical_line(value)


def build_world(base: Path, contests: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """A parent and an accepted history built by the accepted builders under ``base``."""
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    parent = hx.build_parent(base, contests)
    history_contract = hx.write_contract(base / "hc.json", hx.contract_for(parent))
    code, result, stderr = hx.run_build(history_contract, parent, base)
    if code != 0:
        raise AssertionError(f"accepted history builder refused the fixture: {stderr}")
    history_db = Path(result["database"]["data_dir"]) / "national_history.sqlite"
    return {"base": base, "parent": parent, "history_contract": history_contract, "history_db": history_db,
            "history": result}


def history_binding(history_db: Path, history_contract: Path) -> dict[str, Any]:
    """The binding of an (accepted or rehashed fixture) history database, read from its own verified bytes."""
    from aggie_analytics.national_history import query as hq  # noqa: PLC0415
    with hq.NationalHistoryDatabase(Path(history_db)) as handle:
        meta, binding = dict(handle.meta), dict(handle.binding)
        counts: dict[str, int] = {}
        for (season,) in handle.conn.execute("SELECT season FROM targets"):
            counts[str(season)] = counts.get(str(season), 0) + 1
    payload = json.loads(meta["payload_sha256"])
    content = Path(history_db).resolve().parent.parent / binding["content_identity"] / "out_of_scope.jsonl"
    rows = len(content.read_text(encoding="utf-8").splitlines())
    return {"contract_id": meta["contract_id"], "contract_sha256": bm.sha256_file(history_contract),
            "database_identity": binding["database_identity"], "sqlite_sha256": binding["database_sha256"],
            "content_identity": binding["content_identity"], "out_of_scope_sha256": payload["out_of_scope.jsonl"],
            "out_of_scope_rows": rows, "expected_targets": dict(sorted(counts.items()))}


def contract_for(world: dict[str, Any], **patch: Any) -> dict[str, Any]:
    """The committed contract with only its history binding replaced by the fixture's (plus optional patches)."""
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract["parent"]["history"] = history_binding(world["history_db"], world["history_contract"])
    for dotted, value in patch.items():
        node = contract
        parts = dotted.split("__")
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = value
    return contract


def write_contract(path: Path, contract: dict[str, Any]) -> Path:
    Path(path).write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return Path(path)


def anchors_for(contract_path: Path, world: dict[str, Any]) -> dict[str, Any]:
    return builder().load_contract(contract_path, world["history_contract"])[2]


def run_build(contract_path: Path, world: dict[str, Any], out: Path, *extra: str
              ) -> tuple[int, dict[str, Any] | None, str]:
    argv = ["--contract", str(contract_path), "--history-database", str(world["history_db"]),
            "--history-contract", str(world["history_contract"]),
            "--output-root", str(Path(out) / "canonical" / POP), "--manifest-root", str(Path(out) / "manifests" / POP),
            *extra]
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = builder().main(argv)
        except SystemExit as exc:
            code = exc.code
    text = stdout.getvalue()
    return code, (json.loads(text) if text.strip() else None), stderr.getvalue()


def refusal(stderr: str) -> str | None:
    return hx.refusal(stderr)


def database_of(result: dict[str, Any]) -> Path:
    return Path(result["database"]["data_dir"]) / bm.DB_FILE


# --------------------------------------------------------------------------------------------- forged history inputs

def rehash_history(history_db: Path, out: Path, name: str, statements: list[tuple[str, tuple]]) -> Path:
    """A self-consistent copy of a history database with ``statements`` applied: new bytes, table counts, identity
    document, identity directory and manifest (the content identity and its out-of-scope payload are unchanged and
    copied beside it)."""
    history_db = Path(history_db)
    work = Path(out) / name / "work.sqlite"
    work.parent.mkdir(parents=True)
    shutil.copyfile(history_db, work)
    conn = sqlite3.connect(work)
    conn.execute("PRAGMA journal_mode = OFF")
    for sql, params in statements:
        if conn.execute(sql, params).rowcount < 1 and not sql.lstrip().upper().startswith("CREATE"):
            raise AssertionError(f"history forgery {name} changed nothing: {sql}")
    conn.commit()
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("meta", "targets", "history", "exclusions", "target_labels")}
    conn.close()
    population_root = history_db.resolve().parent.parent.parent
    manifest = population_root.parent.parent / "manifests" / population_root.name / "sha256" / \
        history_db.resolve().parent.name / "run_manifest.json"
    doc = json.loads(manifest.read_text(encoding="utf-8"))["identity_document"]
    doc["outputs"] = {"national_history.sqlite": bm.sha256_file(work)}
    doc["table_counts"] = counts
    identity = bm.sha256_bytes(bm.canonical_json_bytes(doc))
    target = Path(out) / name / "canonical" / "h" / "sha256" / identity / "national_history.sqlite"
    target.parent.mkdir(parents=True)
    shutil.move(str(work), str(target))
    content_id = doc["content_identity"]
    shutil.copytree(history_db.resolve().parent.parent / content_id, Path(out) / name / "canonical" / "h" / "sha256" /
                    content_id)
    man = Path(out) / name / "manifests" / "h" / "sha256" / identity / "run_manifest.json"
    man.parent.mkdir(parents=True)
    man.write_text(json.dumps({"identity": identity, "identity_document": doc}), encoding="utf-8")
    return target


def history_record(history_db: Path, table: str, where: str, key_column: str = "ord") -> tuple[Any, dict[str, Any]]:
    conn = sqlite3.connect(Path(history_db).as_uri() + "?mode=ro", uri=True)
    key, text = conn.execute(f"SELECT {key_column}, record FROM {table} WHERE {where} ORDER BY ord LIMIT 1").fetchone()
    conn.close()
    return key, json.loads(text)


# --------------------------------------------------------------------------------------------- forged benchmarks

class Forger:
    """Coordinated forgeries of one benchmark database in owned scratch."""

    def __init__(self, database: Path, root: Path) -> None:
        self.database = Path(database)
        self.root = Path(root)
        identity = self.database.parent.name
        population_root = self.database.parent.parent.parent
        self.manifest = json.loads((population_root.parent.parent / "manifests" / population_root.name / "sha256" /
                                    identity / "run_manifest.json").read_text(encoding="utf-8"))

    def tables(self) -> dict[str, list[dict[str, Any]]]:
        conn = sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True)
        out: dict[str, list[dict[str, Any]]] = {t: [] for t in bm.RECORD_TABLES}
        for table, blob in conn.execute("SELECT record_table, block FROM blocks ORDER BY ord"):
            out[table] += [json.loads(line) for line in zlib.decompress(blob).decode("utf-8").splitlines()]
        conn.close()
        return out

    def forge(self, name: str, *, records: Callable[[dict[str, list[dict[str, Any]]]], None] | None = None,
              meta: dict[str, Any] | None = None, statements: list[str] | None = None,
              document: dict[str, Any] | Callable[[dict[str, Any]], None] | None = None,
              after_blocks: list[tuple[str, tuple]] | None = None) -> Path:
        """Copy, mutate and rehash; ``records`` edits the record lists in place (blocks are rebuilt from them with
        consistent index columns), ``meta`` replaces meta values (JSON values are written canonically), ``document``
        patches the identity document, ``after_blocks`` runs after the blocks are rebuilt (index-column forgeries)."""
        work = self.root / name / "work.sqlite"
        work.parent.mkdir(parents=True)
        shutil.copyfile(self.database, work)
        conn = sqlite3.connect(work)
        conn.execute("PRAGMA journal_mode = OFF")
        if records is not None:
            tables = self.tables()
            records(tables)
            conn.execute("DELETE FROM blocks")
            ord_ = 0
            for table in bm.RECORD_TABLES:
                seasons = sorted({r.get("season") for r in tables[table]} | set(bm.TARGET_SEASONS),
                                 key=lambda s: (not isinstance(s, int), s if isinstance(s, int) else 0))
                for season in seasons:
                    chosen = [r for r in tables[table] if r.get("season") == season]
                    if not chosen and season not in bm.TARGET_SEASONS:
                        continue
                    lines = "".join(canonical(r) + "\n" for r in chosen).encode("utf-8")
                    conn.execute("INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                 (ord_, table, season, len(chosen),
                                  bm.record_key(table, chosen[0]) if chosen else None,
                                  bm.record_key(table, chosen[-1]) if chosen else None,
                                  bm.sha256_bytes(lines), zlib.compress(lines, 9)))
                    ord_ += 1
        for key, value in (meta or {}).items():
            text = value if isinstance(value, str) else canonical(value)
            if conn.execute("UPDATE meta SET value = ? WHERE key = ?", (text, key)).rowcount != 1:
                raise AssertionError(f"meta forgery {key} changed nothing")
        for sql in statements or []:
            conn.execute(sql)
        for sql, params in after_blocks or []:
            if conn.execute(sql, params).rowcount < 1:
                raise AssertionError(f"block forgery changed nothing: {sql}")
        conn.commit()
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in bm.TABLES}
        conn.close()
        doc = copy.deepcopy(self.manifest["identity_document"])
        doc["outputs"] = {bm.DB_FILE: bm.sha256_file(work)}
        doc["table_counts"] = counts
        if callable(document):
            document(doc)
        else:
            doc.update(document or {})
        identity = bm.sha256_bytes(bm.canonical_json_bytes(doc))
        target = self.root / name / "canonical" / POP / "sha256" / identity / bm.DB_FILE
        target.parent.mkdir(parents=True)
        shutil.move(str(work), str(target))
        man = self.root / name / "manifests" / POP / "sha256" / identity / "run_manifest.json"
        man.parent.mkdir(parents=True)
        man.write_text(json.dumps({"identity": identity, "identity_document": doc,
                                   "provenance": {"forgery": name}}), encoding="utf-8")
        return target

    def meta_value(self, key: str) -> Any:
        conn = sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True)
        value = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()[0]
        conn.close()
        return json.loads(value) if value[:1] in "{[" else value
