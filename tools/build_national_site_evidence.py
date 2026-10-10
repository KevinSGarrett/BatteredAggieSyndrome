r"""Build the explicit official-site evidence sidecar of the accepted 2024-2025 alias successor (BAT-721, Cycle #49
TP49-A01).

``python -B tools/build_national_site_evidence.py
--contract configs/national_site_evidence_2024_2025_contract.json
--parent-database <data>/canonical/national_di_population_2016_2025/sha256/<id>/national_population.sqlite
--reconciliation <data>/canonical/national_reconciliation_aliases_2024_2025/sha256/<id>/national_reconciliation_aliases.sqlite
--evidence-source <directory holding site_evidence_sources.json and the <sha256>.gz document bodies>
--output-root <data>/canonical/national_site_evidence_2024_2025
--manifest-root <data>/manifests/national_site_evidence_2024_2025``

The builder refuses unless the contract's parameters and labels equal the reader's rules and its predecessor is exactly
the committed alias successor contract (SHA-256 and contract id, loaded and checked by the accepted alias builder). It
materializes the pinned site evidence bundle create-only (the bundle identity and sources SHA-256 the contract pins),
verifies the alias successor completely with the reader (parent, cached inputs, alias evidence and every record), requires
its site disagreements to be exactly the contract's universe, verifies every retained body and receipt, derives the
records with :mod:`aggie_analytics.national_population.query` (the reader re-derives exactly the same records before it
serves any row) and materializes the payloads and the deterministic SQLite database create-only and content addressed.
The materialized database is then opened through the reader's full verification. ``--input-order``, ``--chunk-size``
with ``--checkpoint-dir`` and ``--stop-after-chunks`` / ``--resume`` prove that order, chunking and an interrupted build
cannot change a byte. The accepted V1 builder's checkpoint and create-only materialization are reused unchanged.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(REPO_ROOT / "src"), str(REPO_ROOT)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from aggie_analytics.national_population import query  # noqa: E402
from tools import build_national_population_reconciliation as v1  # noqa: E402
from tools import build_national_reconciliation_aliases as aliases  # noqa: E402

PRODUCER = "national_site_evidence/1.0.0"
CONTRACT_ID_PREFIX = "BAT-721-NATIONAL-SITE-EVIDENCE-2024-2025-"
CHECKPOINT_SCHEMA = "BAS-NATIONAL-SITE-EVIDENCE-CHECKPOINT-1"
INTERRUPTED_EXIT = 3
PREDECESSOR_CONTRACT = REPO_ROOT / "configs" / "national_reconciliation_aliases_2024_2025_contract.json"
V1_CONTRACT = REPO_ROOT / "configs" / "national_population_reconciliation_2024_2025_contract.json"
BuildRefused = v1.BuildRefused


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_contract(path: Path, predecessor_contract: Path = PREDECESSOR_CONTRACT, v1_contract: Path = V1_CONTRACT
                  ) -> tuple[dict[str, Any], str, dict[str, Any], dict[str, Any]]:
    """The site-evidence contract, its SHA-256, the anchors it binds and the predecessor's anchors; refuses any drift
    from the reader's rules."""
    raw = Path(path).read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    contract_sha = sha256_bytes(raw)
    problems = []
    if not str(contract.get("contract_id", "")).startswith(CONTRACT_ID_PREFIX):
        problems.append("contract_id")
    if contract.get("population_id") != query.SITE_EVIDENCE_POPULATION:
        problems.append("population_id")
    if contract.get("seasons") != list(query.RECONCILIATION_SEASONS):
        problems.append("seasons")
    if contract.get("parameters") != query.SITE_PARAMETERS:
        problems.append("parameters")
    if contract.get("labels") != query.SITE_LABELS:
        problems.append("labels")
    try:
        alias_contract, alias_sha, alias_anchors = aliases.load_contract(predecessor_contract, v1_contract)
    except BuildRefused as exc:
        raise BuildRefused("CONTRACT_INVALID", f"the predecessor contract is not a valid alias contract: {exc}") from exc
    predecessor = contract.get("predecessor") or {}
    if set(predecessor) != {"population_id", "contract_sha256", "contract_id", "content_identity",
                            "database_identity"} or \
            predecessor.get("population_id") != query.ALIAS_SUCCESSOR_POPULATION or \
            predecessor.get("contract_sha256") != alias_sha or \
            predecessor.get("contract_id") != alias_contract.get("contract_id") or \
            not all(isinstance(predecessor.get(k), str) and query.IDENTITY_RE.match(predecessor[k])
                    for k in ("content_identity", "database_identity")):
        problems.append("predecessor")
    universe = contract.get("universe") or {}
    keys = universe.get("keys") if isinstance(universe, dict) else None
    if not isinstance(universe, dict) or set(universe) != {"keys"} or not isinstance(keys, list) or not keys or \
            not all(isinstance(k, str) and query.CONTEST_KEY_RE.match(k) for k in keys) or len(set(keys)) != len(keys):
        problems.append("universe")
    pins = contract.get("evidence") or {}
    if set(pins) != {"bundle_identity", "sources_sha256"} or \
            not all(isinstance(v, str) and query.IDENTITY_RE.match(v) for v in pins.values()):
        problems.append("evidence")
    anchors = {"contract_sha256": contract_sha, "contract_id": contract.get("contract_id"),
               "predecessor": {k: predecessor.get(k) for k in ("population_id", "contract_sha256", "contract_id",
                                                              "content_identity", "database_identity")},
               "universe": {"keys": list(keys or [])}, "evidence": pins}
    if not problems and contract.get("content_scope") != query.site_scope(anchors):
        problems.append("content_scope")
    if problems:
        raise BuildRefused("CONTRACT_INVALID", f"contract differs from the reader's rules on {problems}")
    return contract, contract_sha, anchors, alias_anchors


def materialize_evidence(source: Path, output_root: Path, manifest_root: Path, anchors: dict[str, Any],
                         provenance: dict[str, Any]) -> dict[str, Any]:
    """The pinned site evidence bundle (every file of ``source``), create-only and content addressed."""
    if not Path(source).is_dir():
        raise BuildRefused("EVIDENCE_SOURCE_MISSING", f"{source} is not a directory")
    files = {p.name: p.read_bytes() for p in sorted(Path(source).iterdir()) if p.is_file()}
    others = sorted(p.name for p in Path(source).iterdir() if not p.is_file())
    if others:
        raise BuildRefused("EVIDENCE_SOURCE_INVALID", f"{source} holds non-file entries {others[:3]}")
    outputs = {name: sha256_bytes(data) for name, data in files.items()}
    document = query.site_bundle_document(outputs.get(query.SITE_SOURCES_FILE), outputs)
    identity = sha256_bytes(query.canonical_json_bytes(document))
    pins = anchors["evidence"]
    if identity != pins["bundle_identity"] or outputs.get(query.SITE_SOURCES_FILE) != pins["sources_sha256"]:
        raise BuildRefused("EVIDENCE_NOT_PINNED", f"the evidence source forms bundle {identity}, the contract pins "
                                                  f"{pins['bundle_identity']}")
    return v1.materialize(output_root, manifest_root, document, dict(files), provenance)


def record_stream(derived: dict[str, Any]) -> tuple[list[str], list[bytes]]:
    """Every record key and canonical line: site-evidence records, then source records, each in contract order."""
    keys, lines = [], []
    for record in derived["records"]:
        keys.append("site|" + record["contest_key"])
        lines.append((query.reconciliation_line(record) + "\n").encode("utf-8"))
    for record in derived["sources"]:
        keys.append("source|" + record["source_key"])
        lines.append((query.reconciliation_line(record) + "\n").encode("utf-8"))
    return keys, lines


def build_database(path: Path, derived: dict[str, Any], meta: dict[str, str]) -> dict[str, int]:
    rows = query.site_table_rows(derived)
    tables = [ddl for kind, _name, ddl in query.SITE_DDL if kind == "table"]
    indexes = [ddl for kind, _name, ddl in query.SITE_DDL if kind == "index"]
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA page_size = 4096")
        conn.execute("PRAGMA journal_mode = OFF")
        for ddl in tables:
            conn.execute(ddl)
        conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", sorted(meta.items()))
        conn.executemany("INSERT INTO site_evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows["site_evidence"])
        conn.executemany("INSERT INTO site_source VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows["site_source"])
        for ddl in indexes:
            conn.execute(ddl)
        conn.commit()
        counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in query.SITE_TABLES}
    finally:
        conn.close()
    return counts


def build(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    contract, contract_sha, anchors, alias_anchors = load_contract(args.contract, args.predecessor_contract,
                                                                   args.v1_contract)
    if args.chunk_size < 0 or (args.stop_after_chunks is not None and args.stop_after_chunks < 1):
        raise BuildRefused("ARGUMENT_INVALID", "chunk size and stop-after must be positive")
    if (args.resume or args.stop_after_chunks is not None) and not args.checkpoint_dir:
        raise BuildRefused("ARGUMENT_INVALID", "--resume and --stop-after-chunks need --checkpoint-dir")
    if args.checkpoint_dir and args.chunk_size < 1:
        raise BuildRefused("ARGUMENT_INVALID", "--checkpoint-dir needs --chunk-size >= 1")
    base_provenance = {"producer": PRODUCER, "producer_sha256": v1.sha256_file(Path(__file__)),
                       "reader_sha256": v1.sha256_file(Path(query.__file__)), "argv": list(args.argv),
                       "jira_key": contract.get("jira_key"), "cycle_number": contract.get("cycle_number"),
                       "attempt_number": contract.get("attempt_number"), "variant": args.variant}
    evidence_state = materialize_evidence(args.evidence_source, args.output_root, args.manifest_root, anchors,
                                          {**base_provenance, "stage": "site-evidence-bundle",
                                           "evidence_source": str(Path(args.evidence_source).resolve())})
    try:
        with query.NationalPopulationDatabase(args.parent_database, manifest=args.parent_manifest) as parent:
            with query.AliasReconciliationSuccessor(args.reconciliation, parent=parent,
                                                    parent_database=args.parent_database,
                                                    anchors=alias_anchors) as predecessor:
                observed = {"population_id": query.ALIAS_SUCCESSOR_POPULATION,
                            "contract_sha256": alias_anchors["contract_sha256"],
                            "contract_id": alias_anchors["contract_id"],
                            "content_identity": predecessor.content_identity,
                            "database_identity": predecessor.database_identity}
                parent_records = predecessor.records["parent-reconciliation"]
                parent_binding = dict(parent.binding)
        if observed != anchors["predecessor"]:
            raise BuildRefused("PREDECESSOR_MISMATCH", f"the selected alias successor {observed} is not the contract's")
        bundle = query.load_site_bundle(Path(args.output_root), anchors)
        sources = query.verify_site_sources(bundle)
        universe = [r["contest_key"] for r in query.site_universe(parent_records)]
        if universe != anchors["universe"]["keys"]:
            raise BuildRefused("SITE_EVIDENCE_UNIVERSE_MISMATCH",
                               f"the predecessor's {len(universe)} site disagreements differ from the contract's "
                               f"{len(anchors['universe']['keys'])}")
        derived = query.derive_site_evidence(parent_records, sources, input_order=args.input_order)
    except query.NationalQueryError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    if len(derived["records"]) != len(anchors["universe"]["keys"]) or \
            len(derived["sources"]) != len(sources["attempts"]):
        raise BuildRefused("CENSUS_INCOMPLETE", "records do not account for every contest and attempt exactly once")
    keys, lines = record_stream(derived)
    checkpoint = None
    if args.checkpoint_dir:
        header = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha,
                  "predecessor_database_identity": anchors["predecessor"]["database_identity"],
                  "evidence": anchors["evidence"], "payload_schema": query.SITE_PAYLOAD_SCHEMA,
                  "chunk_size": args.chunk_size, "record_key_list_sha256": v1._keys_sha(keys),
                  "record_count": len(keys), "producer_sha256": v1.sha256_file(Path(__file__)),
                  "reader_sha256": v1.sha256_file(Path(query.__file__))}
        checkpoint = v1.Checkpoint(Path(args.checkpoint_dir), header, args.chunk_size, args.resume)
    built = v1.build_lines(keys, lines, chunk_size=args.chunk_size, checkpoint=checkpoint,
                           stop_after=args.stop_after_chunks)
    if built is None:
        return {"state": "INTERRUPTED_AT_CHECKPOINT", "checkpoint_dir": str(args.checkpoint_dir),
                "completed_chunks": len(checkpoint.completed(keys)) if checkpoint else 0, "record_count": len(keys),
                "evidence": evidence_state}
    n_records = len(derived["records"])
    payloads = {"site_evidence.jsonl": b"".join(built[:n_records]), "site_sources.jsonl": b"".join(built[n_records:]),
                "summary.json": (query.reconciliation_line(derived["summary"]) + "\n").encode("utf-8")}
    if payloads != query.site_payloads(derived):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpointed records differ from the derivation")
    content_document = query.site_content_document(contract["contract_id"], contract_sha, anchors, payloads)
    content_identity = sha256_bytes(query.canonical_json_bytes(content_document))
    meta = query.site_meta(content_document, content_identity, derived["summary"])
    with tempfile.TemporaryDirectory(prefix="nse-") as work:
        db_path = Path(work) / query.SITE_DB_FILE
        table_counts = build_database(db_path, derived, meta)
        database_document = query.site_database_document(contract_sha, content_identity, v1.sha256_file(db_path),
                                                         table_counts)
        database_identity = sha256_bytes(query.canonical_json_bytes(database_document))
        provenance = {**base_provenance, "producer_path": str(Path(__file__).resolve()),
                      "reader_path": str(Path(query.__file__).resolve()),
                      "issued_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
                      "runtime": v1.runtime(), "input_order": args.input_order, "chunk_size": args.chunk_size,
                      "resumed": bool(args.resume), "parent_manifest": parent_binding["manifest"],
                      "predecessor": anchors["predecessor"], "evidence_bundle": evidence_state["identity"],
                      "content_identity": content_identity, "database_identity": database_identity}
        content = v1.materialize(args.output_root, args.manifest_root, content_document, dict(payloads), provenance)
        database = v1.materialize(args.output_root, args.manifest_root, database_document,
                                  {query.SITE_DB_FILE: db_path}, provenance)
    materialized_db = Path(database["data_dir"]) / query.SITE_DB_FILE
    try:
        with query.NationalPopulationDatabase(args.parent_database, manifest=args.parent_manifest) as parent:
            with query.AliasReconciliationSuccessor(args.reconciliation, parent=parent,
                                                    parent_database=args.parent_database,
                                                    anchors=alias_anchors) as predecessor:
                with query.SiteEvidenceSidecar(materialized_db, predecessor=predecessor, anchors=anchors) as sidecar:
                    reader_check = {"verified": True, "identity": sidecar.binding["identity"],
                                    "content_identity": sidecar.content_identity,
                                    "site_records_verified": len(sidecar.records),
                                    "source_records_verified": len(sidecar.sources)}
    except query.NationalQueryError as exc:
        raise BuildRefused("MATERIALIZED_SIDECAR_REFUSED_BY_READER", str(exc)) from exc
    production = query.SITE_EVIDENCE_ANCHORS or {}
    return {"state": content["state"], "content_identity": content_identity, "database_identity": database_identity,
            "evidence": evidence_state, "content": content, "database": database, "reader_check": reader_check,
            "row_counts": content_document["row_counts"], "table_counts": table_counts,
            "payload_sha256": content_document["outputs"], "database_sha256": database_document["outputs"],
            "summary": derived["summary"], "universe": anchors["universe"]["keys"], "contract_sha256": contract_sha,
            "contract_id": contract["contract_id"], "predecessor": anchors["predecessor"],
            "anchors_equal_production": {k: v for k, v in anchors.items() if k != "contract_sha256"} ==
            {k: v for k, v in production.items() if k != "contract_sha256"},
            "contract_pinned_by_reader": contract_sha == production.get("contract_sha256"),
            "parent": {"identity": parent_binding["database_identity"],
                       "sqlite_sha256": parent_binding["database_sha256"]},
            "input_order": args.input_order, "chunk_size": args.chunk_size, "resumed": bool(args.resume),
            "variant": args.variant, "runtime": v1.runtime(), "seconds": round(time.time() - started, 3)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_site_evidence", allow_abbrev=False,
                                     description="Build the 2024-2025 official-site evidence sidecar.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--predecessor-contract", type=Path, default=PREDECESSOR_CONTRACT)
    parser.add_argument("--v1-contract", type=Path, default=V1_CONTRACT)
    parser.add_argument("--parent-database", required=True, type=Path)
    parser.add_argument("--parent-manifest", type=Path, default=None)
    parser.add_argument("--reconciliation", required=True, type=Path)
    parser.add_argument("--evidence-source", required=True, type=Path)
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
    args.argv = ["tools/build_national_site_evidence.py", *raw]
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
