r"""Build the explicit alias successor of the accepted 2024-2025 national population reconciliation (BAT-720, Cycle #48
TP48-A01).

``python -B tools/build_national_reconciliation_aliases.py
--contract configs/national_reconciliation_aliases_2024_2025_contract.json
--parent-database <data>/canonical/national_di_population_2016_2025/sha256/<id>/national_population.sqlite
--evidence-source <directory holding alias_assertions.json and the <sha256>.gz document bodies>
--output-root <data>/canonical/national_reconciliation_aliases_2024_2025
--manifest-root <data>/manifests/national_reconciliation_aliases_2024_2025``

The builder refuses unless the contract's parameters and labels equal the reader's rules, its parent contract is the
accepted parent contract with the same name normalization and date basis, and its predecessor is exactly the accepted
V1 contract (same SHA-256, contract id, parent and cached inputs). It materializes the pinned alias evidence bundle
create-only (the bundle identity and assertions SHA-256 the contract pins), verifies every bound cached input and every
alias assertion with the reader's own rules, requires the contract's declared alias universe to equal the verified
one, derives the complete records with :mod:`aggie_analytics.national_population.query` (the reader re-derives exactly
the same records before it serves any row), and materializes the payloads and the deterministic SQLite database
create-only and content addressed. The materialized database is then opened through the reader's full verification.
``--input-order``, ``--chunk-size`` with ``--checkpoint-dir`` and ``--stop-after-chunks`` / ``--resume`` prove that
order, chunking and an interrupted build cannot change a byte. The accepted V1 builder's checkpoint and create-only
materialization are reused unchanged.
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

PRODUCER = "national_reconciliation_aliases/1.0.0"
CONTRACT_ID_PREFIX = "BAT-720-NATIONAL-RECONCILIATION-ALIASES-2024-2025-"
CHECKPOINT_SCHEMA = "BAS-NATIONAL-RECONCILIATION-ALIASES-CHECKPOINT-1"
INTERRUPTED_EXIT = 3
PREDECESSOR_CONTRACT = REPO_ROOT / "configs" / "national_population_reconciliation_2024_2025_contract.json"
BuildRefused = v1.BuildRefused


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_contract(path: Path, predecessor_contract: Path = PREDECESSOR_CONTRACT
                  ) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """The successor contract, its SHA-256 and the anchors it binds; refuses any drift from the reader's rules."""
    raw = Path(path).read_bytes()
    contract = json.loads(raw.decode("utf-8"))
    contract_sha = sha256_bytes(raw)
    problems = []
    if not str(contract.get("contract_id", "")).startswith(CONTRACT_ID_PREFIX):
        problems.append("contract_id")
    if contract.get("population_id") != query.ALIAS_SUCCESSOR_POPULATION:
        problems.append("population_id")
    if contract.get("seasons") != list(query.RECONCILIATION_SEASONS):
        problems.append("seasons")
    if contract.get("parameters") != query.ALIAS_PARAMETERS:
        problems.append("parameters")
    if contract.get("labels") != query.ALIAS_LABELS:
        problems.append("labels")
    parent_contract = contract.get("parent_contract") or {}
    parent_contract_path = REPO_ROOT / Path(*str(parent_contract.get("repository_path", "")).split("/"))
    if not parent_contract_path.is_file() or v1.sha256_file(parent_contract_path) != parent_contract.get("sha256") or \
            parent_contract.get("sha256") != (contract.get("parent") or {}).get("contract_sha256"):
        problems.append("parent_contract")
    else:
        accepted = json.loads(parent_contract_path.read_text(encoding="utf-8"))
        resolution = accepted["reconciliation"]["participant_resolution"]
        if resolution["token_expansions"] != query.RECONCILIATION_TOKEN_EXPANSIONS or \
                accepted["parameters"]["cfbd_local_offset_hours"] != list(query.RECONCILIATION_LOCAL_OFFSET_HOURS):
            problems.append("parent_contract_rules")
    predecessor = contract.get("predecessor") or {}
    predecessor_raw = Path(predecessor_contract).read_bytes() if Path(predecessor_contract).is_file() else b""
    previous = json.loads(predecessor_raw.decode("utf-8")) if predecessor_raw else {}
    if predecessor.get("population_id") != query.RECONCILIATION_POPULATION or \
            predecessor.get("contract_sha256") != sha256_bytes(predecessor_raw) or \
            predecessor.get("contract_id") != previous.get("contract_id") or \
            (contract.get("parent"), contract.get("inputs")) != (previous.get("parent"), previous.get("inputs")) or \
            not all(isinstance(predecessor.get(k), str) and query.IDENTITY_RE.match(predecessor[k])
                    for k in ("content_identity", "database_identity")):
        problems.append("predecessor")
    pins = contract.get("alias_evidence") or {}
    if set(pins) != {"bundle_identity", "assertions_sha256"} or \
            not all(isinstance(v, str) and query.IDENTITY_RE.match(v) for v in pins.values()):
        problems.append("alias_evidence")
    anchors = {"contract_sha256": contract_sha, "contract_id": contract.get("contract_id"),
               "parent": contract.get("parent"), "inputs": contract.get("inputs"), "alias_evidence": pins,
               "predecessor": {k: predecessor.get(k) for k in ("population_id", "contract_sha256", "contract_id",
                                                              "content_identity", "database_identity")}}
    if not problems and contract.get("content_scope") != query.alias_scope(anchors):
        problems.append("content_scope")
    if not isinstance(contract.get("alias_universe"), list):
        problems.append("alias_universe")
    if problems:
        raise BuildRefused("CONTRACT_INVALID", f"contract differs from the reader's rules on {problems}")
    return contract, contract_sha, anchors


def materialize_evidence(source: Path, output_root: Path, manifest_root: Path, anchors: dict[str, Any],
                         provenance: dict[str, Any]) -> dict[str, Any]:
    """The pinned evidence bundle (every file of ``source``), create-only and content addressed."""
    if not Path(source).is_dir():
        raise BuildRefused("EVIDENCE_SOURCE_MISSING", f"{source} is not a directory")
    files = {p.name: p.read_bytes() for p in sorted(Path(source).iterdir()) if p.is_file()}
    others = sorted(p.name for p in Path(source).iterdir() if not p.is_file())
    if others:
        raise BuildRefused("EVIDENCE_SOURCE_INVALID", f"{source} holds non-file entries {others[:3]}")
    outputs = {name: sha256_bytes(data) for name, data in files.items()}
    document = query.alias_evidence_document(outputs.get(query.ALIAS_ASSERTIONS_FILE), outputs)
    identity = sha256_bytes(query.canonical_json_bytes(document))
    pins = anchors["alias_evidence"]
    if identity != pins["bundle_identity"] or outputs.get(query.ALIAS_ASSERTIONS_FILE) != pins["assertions_sha256"]:
        raise BuildRefused("EVIDENCE_NOT_PINNED", f"the evidence source forms bundle {identity}, the contract pins "
                                                  f"{pins['bundle_identity']}")
    return v1.materialize(output_root, manifest_root, document, dict(files), provenance)


def record_stream(derived: dict[str, Any], aliases: dict[str, Any]) -> tuple[list[str], list[bytes]]:
    """Every record key and canonical line: parent, provider and alias-disposition records, each in contract order."""
    keys, lines = v1.record_stream(derived)
    for record in query.alias_disposition_records(derived, aliases):
        keys.append("alias|" + record["key"])
        lines.append((query.reconciliation_line(record) + "\n").encode("utf-8"))
    return keys, lines


def build_database(path: Path, derived: dict[str, Any], aliases: dict[str, Any], meta: dict[str, str]) -> dict[str, int]:
    rows = query.alias_table_rows(derived, aliases)
    tables = [ddl for kind, _name, ddl in query.ALIAS_DDL if kind == "table"]
    indexes = [ddl for kind, _name, ddl in query.ALIAS_DDL if kind == "index"]
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
        conn.executemany("INSERT INTO alias_disposition VALUES (?, ?, ?, ?, ?, ?, ?)", rows["alias_disposition"])
        for ddl in indexes:
            conn.execute(ddl)
        conn.commit()
        counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in query.ALIAS_TABLES}
    finally:
        conn.close()
    return counts


def build(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    contract, contract_sha, anchors = load_contract(args.contract, args.predecessor_contract)
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
                                          {**base_provenance, "stage": "alias-evidence",
                                           "evidence_source": str(Path(args.evidence_source).resolve())})
    try:
        with query.NationalPopulationDatabase(args.parent_database, manifest=args.parent_manifest) as parent:
            query.verify_reconciliation_parent(parent, anchors)
            input_root = Path(args.input_root) if args.input_root else query.reconciliation_data_root(args.parent_database)
            inputs = query.load_reconciliation_inputs(input_root, anchors)
            parent_rows = query.read_reconciliation_parent(parent.conn)
            parent_binding = dict(parent.binding)
        evidence = query.load_alias_evidence(Path(args.output_root), anchors)
        aliases = query.verify_alias_assertions(evidence)
    except query.NationalQueryError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    if query.canonical_json_bytes(contract["alias_universe"]) != query.canonical_json_bytes(aliases["rows"]):
        raise BuildRefused("ALIAS_UNIVERSE_NOT_DECLARED", "the contract's alias universe differs from the evidence")
    counts: dict[str, int] = {}
    for contest in parent_rows["contests"]:
        counts[str(contest["season"])] = counts.get(str(contest["season"]), 0) + 1
    if counts != anchors["parent"]["expected_contests"]:
        raise BuildRefused("PARENT_COLLECTION_MISMATCH", f"parent contests {counts} != {anchors['parent']['expected_contests']}")
    try:
        derived = query.derive_reconciliation(parent_rows, inputs, input_order=args.input_order, aliases=aliases)
    except query.NationalQueryError as exc:
        raise BuildRefused(exc.code, str(exc)) from exc
    if len(derived["parent_records"]) != sum(anchors["parent"]["expected_contests"].values()) or \
            len(derived["provider_records"]) != sum(c["rows"] for c in anchors["inputs"]["provider_captures"]):
        raise BuildRefused("CENSUS_INCOMPLETE", "records do not account for every input row exactly once")
    keys, lines = record_stream(derived, aliases)
    checkpoint = None
    if args.checkpoint_dir:
        header = {"schema": CHECKPOINT_SCHEMA, "contract_sha256": contract_sha,
                  "parent_query_db_identity": parent_binding["database_identity"],
                  "alias_evidence": anchors["alias_evidence"], "payload_schema": query.ALIAS_PAYLOAD_SCHEMA,
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
    n_parent, n_provider = len(derived["parent_records"]), len(derived["provider_records"])
    payloads = {"parent_reconciliation.jsonl": b"".join(built[:n_parent]),
                "provider_reconciliation.jsonl": b"".join(built[n_parent:n_parent + n_provider]),
                "alias_dispositions.jsonl": b"".join(built[n_parent + n_provider:]),
                "summary.json": (query.reconciliation_line(derived["summary"]) + "\n").encode("utf-8")}
    if payloads != query.alias_payloads(derived, aliases):
        raise BuildRefused("REFUSED_ALTERED_PREFIX", "checkpointed records differ from the derivation")
    content_document = query.alias_content_document(contract["contract_id"], contract_sha, anchors, payloads)
    content_identity = sha256_bytes(query.canonical_json_bytes(content_document))
    meta = query.alias_meta(content_document, content_identity, derived["summary"])
    with tempfile.TemporaryDirectory(prefix="nra-") as work:
        db_path = Path(work) / query.ALIAS_DB_FILE
        table_counts = build_database(db_path, derived, aliases, meta)
        database_document = query.alias_database_document(contract_sha, content_identity, v1.sha256_file(db_path),
                                                          table_counts)
        database_identity = sha256_bytes(query.canonical_json_bytes(database_document))
        provenance = {**base_provenance, "producer_path": str(Path(__file__).resolve()),
                      "reader_path": str(Path(query.__file__).resolve()),
                      "issued_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
                      "runtime": v1.runtime(), "input_order": args.input_order, "chunk_size": args.chunk_size,
                      "resumed": bool(args.resume), "parent_manifest": parent_binding["manifest"],
                      "input_root": str(input_root), "evidence_bundle": evidence_state["identity"],
                      "content_identity": content_identity, "database_identity": database_identity}
        content = v1.materialize(args.output_root, args.manifest_root, content_document, dict(payloads), provenance)
        database = v1.materialize(args.output_root, args.manifest_root, database_document,
                                  {query.ALIAS_DB_FILE: db_path}, provenance)
    materialized_db = Path(database["data_dir"]) / query.ALIAS_DB_FILE
    try:
        with query.NationalPopulationDatabase(args.parent_database, manifest=args.parent_manifest) as parent:
            with query.AliasReconciliationSuccessor(materialized_db, parent=parent,
                                                    parent_database=args.parent_database,
                                                    anchors=anchors) as successor:
                reader_check = {"verified": True, "identity": successor.binding["identity"],
                                "content_identity": successor.content_identity,
                                "assertions_verified": len(successor.aliases["assertions"])}
    except query.NationalQueryError as exc:
        raise BuildRefused("MATERIALIZED_SUCCESSOR_REFUSED_BY_READER", str(exc)) from exc
    production = query.ALIAS_ANCHORS or {}
    return {"state": content["state"], "content_identity": content_identity, "database_identity": database_identity,
            "evidence": evidence_state, "content": content, "database": database, "reader_check": reader_check,
            "row_counts": content_document["row_counts"], "table_counts": table_counts,
            "payload_sha256": content_document["outputs"], "database_sha256": database_document["outputs"],
            "summary": derived["summary"], "alias_universe": aliases["rows"], "contract_sha256": contract_sha,
            "contract_id": contract["contract_id"],
            "anchors_equal_production": {k: v for k, v in anchors.items() if k != "contract_sha256"} ==
            {k: v for k, v in production.items() if k != "contract_sha256"},
            "contract_pinned_by_reader": contract_sha == production.get("contract_sha256"),
            "parent": {"identity": parent_binding["database_identity"], "sqlite_sha256": parent_binding["database_sha256"]},
            "input_root": str(input_root), "input_order": args.input_order, "chunk_size": args.chunk_size,
            "resumed": bool(args.resume), "variant": args.variant, "runtime": v1.runtime(),
            "seconds": round(time.time() - started, 3)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="build_national_reconciliation_aliases", allow_abbrev=False,
                                     description="Build the 2024-2025 alias successor of the population reconciliation.")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--predecessor-contract", type=Path, default=PREDECESSOR_CONTRACT)
    parser.add_argument("--parent-database", required=True, type=Path)
    parser.add_argument("--parent-manifest", type=Path, default=None)
    parser.add_argument("--input-root", type=Path, default=None)
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
    args.argv = ["tools/build_national_reconciliation_aliases.py", *raw]
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
