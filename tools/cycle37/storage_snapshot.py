r"""Cycle #37 — Attempt #6 — immutable evidence snapshots of a mutable storage ledger (MF37A05-03).

    storage_snapshot.py freeze --ledger L --out SNAPSHOT.json --label TEXT --scope TEXT
    storage_snapshot.py verify --ledger L --snapshot SNAPSHOT.json [--allow-post-snapshot PREFIX ...]
    storage_snapshot.py open-final --snapshot SNAPSHOT.json --ledger FINAL.jsonl --root R [--root R ...]

Attempt 5 sealed the live storage ledger's hash as evidence while every lane, the final packet's own included,
still appended its reservation to that ledger, so the final packet could not pass and one reservation was left
open to keep the sealed hash from changing. The separation here:

* the **operational ledger** (``tools/cycle37/storage_admission.py``, unchanged) keeps admitting and measuring
  every allocation of the attempt's material work; it is mutable by design;
* ``freeze`` writes an **immutable snapshot** of that ledger once every reservation is closed: the record count
  (sequence), the hash-chain head (the SHA-256 of the last record line, which every later record chains to), the
  SHA-256 of the ledger bytes, the measured state, the INIT configuration with its predecessor references, and an
  exact scope. The file is create-only and carries its own ``content_sha256``. The snapshot -- never the ledger --
  is what a packet seals as evidence;
* ``verify`` re-reads the ledger and proves the snapshot is a hash-stable prefix of it: the chain still validates,
  the N-th record line still hashes to the recorded head, the first N lines still hash to the recorded digest, the
  snapshot's own content hash holds. A tampered or truncated snapshot, a wrong sequence or head, a rewritten
  prefix, and -- unless a caller declares them -- any record appended to the operational ledger after the freeze
  are refused, each for its own cause;
* ``open-final`` starts a **separate final-output ledger** from the snapshot: its budget is exactly the headroom
  the snapshot recorded, so cumulative accounting continues across the boundary, and its INIT names the snapshot.
  Final verification reserves its output allowance there and writes its own separately scoped receipts; the
  operational ledger is not written again.

Nothing here deletes, rewrites or re-baselines a ledger; a predecessor ledger sealed with an open reservation is
a recorded historical condition, not something this tool reconciles.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import storage_admission as sa  # noqa: E402

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 6
TOOL_VERSION = "BAS-C37A06-STORAGE-SNAPSHOT-v1"
SNAPSHOT_SCHEMA = "BAS-STORAGE-EVIDENCE-SNAPSHOT-1"

REFUSED_OPEN_RESERVATIONS = "REFUSED_SNAPSHOT_OPEN_RESERVATIONS"
REFUSED_MALFORMED = "REFUSED_SNAPSHOT_TRUNCATED_OR_MALFORMED"
REFUSED_TAMPERED = "REFUSED_SNAPSHOT_CONTENT_TAMPERED"
REFUSED_LEDGER = "REFUSED_SNAPSHOT_LEDGER_UNREADABLE_OR_CHAIN_BROKEN"
REFUSED_SEQUENCE = "REFUSED_SNAPSHOT_WRONG_LEDGER_SEQUENCE_OR_HEAD"
REFUSED_PREFIX = "REFUSED_SNAPSHOT_LEDGER_PREFIX_REWRITTEN"
REFUSED_POST_SNAPSHOT = "REFUSED_SNAPSHOT_OPERATIONAL_RECORDS_AFTER_FREEZE"
REFUSED_WRONG_LEDGER = "REFUSED_SNAPSHOT_NAMES_ANOTHER_LEDGER"
REFUSED_EXISTS = "REFUSED_SNAPSHOT_TARGET_EXISTS"


class SnapshotRefused(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def tool_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _lines(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _content_digest(document: dict[str, Any]) -> str:
    body = {key: value for key, value in document.items() if key != "content_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                                     default=str).encode("utf-8")).hexdigest()


def _prefix_digest(lines: list[str]) -> str:
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _predecessor(init: dict[str, Any]) -> Any:
    note = init.get("note")
    try:
        parsed = json.loads(note) if isinstance(note, str) and note.startswith("{") else None
    except ValueError:
        parsed = None
    return (parsed or {}).get("predecessor") if isinstance(parsed, dict) else None


# ----------------------------------------------------------------------------------------------- freeze


def freeze(ledger_path: Path | str, out: Path | str, *, label: str, scope: str) -> dict[str, Any]:
    """Write the immutable snapshot of a fully reconciled ledger; refuse an open reservation or an existing target."""

    ledger = sa.Ledger(ledger_path)
    out = Path(out)
    if out.exists():
        raise SnapshotRefused(REFUSED_EXISTS, f"{out} exists; a snapshot is written once and never rewritten")
    try:
        rows = ledger.records()
    except sa.LedgerError as error:
        raise SnapshotRefused(REFUSED_LEDGER, str(error)) from error
    open_rows = ledger.open_reservations(rows)
    if open_rows:
        raise SnapshotRefused(REFUSED_OPEN_RESERVATIONS, (
            f"{len(open_rows)} reservation(s) are still open; close every material reservation before freezing: "
            f"{sorted((token, row.get('operation')) for token, row in open_rows.items())[:5]}"))
    lines = _lines(ledger.path)
    status = ledger.status()
    init = ledger.config(rows)
    document: dict[str, Any] = {
        "schema": SNAPSHOT_SCHEMA, "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "tool_version": TOOL_VERSION, "tool_sha256": tool_sha256(), "frozen_at": utc_now(), "scope": scope,
        "ledger": {"path": str(ledger.path), "records": len(rows), "last_seq": rows[-1]["seq"],
                   "head_record_sha256": sa._digest(lines[-1]), "prefix_sha256": _prefix_digest(lines),
                   "file_sha256": hashlib.sha256(ledger.path.read_bytes()).hexdigest(),
                   "admission_tool_sha256": init.get("tool_sha256"),
                   "chain_rule": "record k carries previous_record_sha256 = sha256 of record line k-1"},
        "configuration": {"budget_bytes": init["budget_bytes"], "reserve_bytes": init["reserve_bytes"],
                          "owned_roots": init.get("owned_roots"), "shared_roots": init.get("shared_roots"),
                          "predecessor": _predecessor(init)},
        "measured": {key: status.get(key) for key in ("added_bytes", "headroom_bytes", "free_bytes", "refused",
                                                      "underestimated", "roots")},
        "bounded_stop": status.get("bounded_stop"), "open_reservations": {},
        "reservations": {"admitted": sum(1 for r in rows if r["kind"] == "RESERVE" and r["decision"] == "ADMITTED"),
                         "reconciled": sum(1 for r in rows if r["kind"] == "RECONCILE"),
                         "orphan_closed": sum(1 for r in rows if r["kind"] == "ORPHAN_CLOSED")},
        "rule": ("Immutable once written. A packet seals this file, never the ledger. Verification proves the ledger "
                 "still begins with exactly these records; records appended after the freeze belong to work this "
                 "snapshot does not cover and are refused unless the verifier's caller declares them."),
    }
    document["content_sha256"] = _content_digest(document)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    return document


# ----------------------------------------------------------------------------------------------- verify


def load_snapshot(path: Path | str) -> dict[str, Any]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SnapshotRefused(REFUSED_MALFORMED, f"{path}: {error}") from error
    if not isinstance(document, dict) or document.get("schema") != SNAPSHOT_SCHEMA or "content_sha256" not in document:
        raise SnapshotRefused(REFUSED_MALFORMED, f"{path} is not a {SNAPSHOT_SCHEMA} document")
    if _content_digest(document) != document["content_sha256"]:
        raise SnapshotRefused(REFUSED_TAMPERED, f"{path}: content hashes to {_content_digest(document)}, not the "
                                                f"recorded {document['content_sha256']}")
    return document


def verify(ledger_path: Path | str, snapshot_path: Path | str, *,
           allow_post_snapshot: tuple[str, ...] = ()) -> dict[str, Any]:
    """Prove the snapshot is a hash-stable prefix of the ledger as it is now. Raises :class:`SnapshotRefused`."""

    document = load_snapshot(snapshot_path)
    ledger = sa.Ledger(ledger_path)
    recorded = document["ledger"]
    if Path(recorded["path"]).resolve() != ledger.path.resolve():
        raise SnapshotRefused(REFUSED_WRONG_LEDGER, f"the snapshot names {recorded['path']}, not {ledger.path}")
    try:
        rows = ledger.records()
    except sa.LedgerError as error:
        raise SnapshotRefused(REFUSED_LEDGER, str(error)) from error
    lines = _lines(ledger.path)
    count = int(recorded["records"])
    if count < 1 or count > len(lines) or len(rows) != len(lines):
        raise SnapshotRefused(REFUSED_SEQUENCE, (
            f"the snapshot records {count} ledger record(s); the ledger now has {len(lines)} line(s) and "
            f"{len(rows)} chained record(s)"))
    if sa._digest(lines[count - 1]) != recorded["head_record_sha256"] or rows[count - 1]["seq"] != recorded["last_seq"]:
        raise SnapshotRefused(REFUSED_SEQUENCE, (
            f"record {count} now hashes to {sa._digest(lines[count - 1])} (seq {rows[count - 1]['seq']}); the "
            f"snapshot recorded head {recorded['head_record_sha256']} (seq {recorded['last_seq']})"))
    if _prefix_digest(lines[:count]) != recorded["prefix_sha256"]:
        raise SnapshotRefused(REFUSED_PREFIX, "the first records of the ledger no longer hash to the snapshot's prefix")
    after = rows[count:]
    undeclared = [row for row in after if not any(str(row.get("operation", "")).startswith(prefix)
                                                  for prefix in allow_post_snapshot)]
    if undeclared:
        raise SnapshotRefused(REFUSED_POST_SNAPSHOT, (
            f"{len(undeclared)} record(s) were appended to the operational ledger after the freeze and are not "
            f"declared final-output work: {[(r['seq'], r['kind'], r.get('operation')) for r in undeclared[:5]]}"))
    return {"result": "PASS", "snapshot": str(snapshot_path), "content_sha256": document["content_sha256"],
            "ledger": str(ledger.path), "records_at_freeze": count, "records_now": len(rows),
            "head_record_sha256": recorded["head_record_sha256"], "post_snapshot_records": len(after),
            "post_snapshot_declared": [(r["seq"], r["kind"], r.get("operation")) for r in after],
            "open_reservations_at_freeze": 0, "bounded_stop_at_freeze": document.get("bounded_stop"),
            "measured_at_freeze": document.get("measured")}


# ----------------------------------------------------------------------------------------------- final ledger


def open_successor(snapshot_path: Path | str, ledger_path: Path | str, roots: list[str], *, kind: str, scope: str,
                   shared: list[str] = (), reserve_bytes: int | None = None, note: str = "") -> dict[str, Any]:
    """Start a ledger that continues a frozen one: its budget is exactly the headroom the snapshot recorded, so the
    attempt's cumulative ceiling is unchanged, and its INIT names the snapshot (content hash, ledger head, bounded
    stop). The frozen ledger is never written again; nothing is reset or re-baselined in it."""

    document = load_snapshot(snapshot_path)
    headroom = int(document["measured"]["headroom_bytes"])
    if headroom <= 0:
        raise SnapshotRefused(REFUSED_SEQUENCE, f"the snapshot records no headroom ({headroom} bytes); nothing can be "
                                                "reserved after it")
    reference = json.dumps({
        "label": f"Cycle #{CYCLE_NUMBER} — Attempt #{ATTEMPT_NUMBER} — {kind}",
        "scope": scope,
        "continues_snapshot": {"path": str(Path(snapshot_path)), "content_sha256": document["content_sha256"],
                               "ledger": document["ledger"]["path"], "records": document["ledger"]["records"],
                               "head_record_sha256": document["ledger"]["head_record_sha256"],
                               "added_bytes": document["measured"]["added_bytes"],
                               "budget_bytes": document["configuration"]["budget_bytes"],
                               "bounded_stop": document.get("bounded_stop"),
                               "predecessor": document["configuration"].get("predecessor")},
        "budget_rule": "budget = the frozen ledger's headroom, so the attempt's cumulative ceiling is unchanged",
        "note": note}, ensure_ascii=False)
    ledger = sa.Ledger(ledger_path)
    reserve = int(document["configuration"]["reserve_bytes"]) if reserve_bytes is None else int(reserve_bytes)
    return ledger.init(budget_bytes=headroom, reserve_bytes=reserve, roots=roots, shared=list(shared), note=reference)


def open_final(snapshot_path: Path | str, ledger_path: Path | str, roots: list[str], *,
               reserve_bytes: int | None = None, note: str = "") -> dict[str, Any]:
    """Start the separate final-output ledger whose budget is exactly the headroom the snapshot recorded."""

    return open_successor(snapshot_path, ledger_path, roots, kind="final-output ledger",
                          scope=("final packet builds, seal and the FINAL_PACKET lane's own outputs, after the "
                                 "operational snapshot"), reserve_bytes=reserve_bytes, note=note)


# ----------------------------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    frozen = sub.add_parser("freeze")
    frozen.add_argument("--ledger", type=Path, required=True)
    frozen.add_argument("--out", type=Path, required=True)
    frozen.add_argument("--label", required=True)
    frozen.add_argument("--scope", required=True)
    checked = sub.add_parser("verify")
    checked.add_argument("--ledger", type=Path, required=True)
    checked.add_argument("--snapshot", type=Path, required=True)
    checked.add_argument("--allow-post-snapshot", action="append", default=[])
    final = sub.add_parser("open-final")
    final.add_argument("--snapshot", type=Path, required=True)
    final.add_argument("--ledger", type=Path, required=True)
    final.add_argument("--root", action="append", required=True)
    final.add_argument("--reserve-bytes", type=int, default=None)
    final.add_argument("--note", default="")
    successor = sub.add_parser("open-successor")
    successor.add_argument("--snapshot", type=Path, required=True)
    successor.add_argument("--ledger", type=Path, required=True)
    successor.add_argument("--root", action="append", required=True)
    successor.add_argument("--shared", action="append", default=[])
    successor.add_argument("--kind", required=True)
    successor.add_argument("--scope", required=True)
    successor.add_argument("--note", default="")
    args = parser.parse_args(argv)
    try:
        if args.mode == "freeze":
            result = freeze(args.ledger, args.out, label=args.label, scope=args.scope)
        elif args.mode == "verify":
            result = verify(args.ledger, args.snapshot, allow_post_snapshot=tuple(args.allow_post_snapshot))
        elif args.mode == "open-successor":
            result = open_successor(args.snapshot, args.ledger, args.root, kind=args.kind, scope=args.scope,
                                    shared=args.shared, note=args.note)
        else:
            result = open_final(args.snapshot, args.ledger, args.root, reserve_bytes=args.reserve_bytes, note=args.note)
    except SnapshotRefused as refused:
        print(json.dumps({"result": "REFUSED", "code": refused.code, "detail": refused.detail}, indent=1))
        return 3
    except sa.LedgerError as error:
        print(json.dumps({"result": "REFUSED", "code": REFUSED_LEDGER, "detail": str(error)}, indent=1))
        return 2
    print(json.dumps(result, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
