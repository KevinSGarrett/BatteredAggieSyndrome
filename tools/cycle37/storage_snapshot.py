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

Cycle #37 -- Attempt #7 (MF37A06-02). Replaying one unchanged snapshot opened a second continuation with a fresh
baseline and the same headroom as the first: 1,000,000 budgeted, 300,000 spent and frozen, 600,000 spent by the
first continuation, and the second still admitted 200,000. ``open_successor`` (``open_final`` is one kind of it) now
opens *the* continuation of a ledger:

* it proves the snapshot is a hash-stable prefix of its ledger with nothing after it (a stale snapshot of a ledger
  that went on, or a truncated or rewritten ledger, is refused), that the parent is itself its parent's claimed
  continuation, and that a caller naming a cycle or attempt names the chain's own;
* under the parent ledger's lock it creates the create-only claim ``<parent>.continuation.json`` naming the new
  ledger. A second or concurrent continuation -- from this snapshot or any other -- is refused
  (``REFUSED_CONTINUATION_ALREADY_CLAIMED``); opening the same continuation again resumes it without a new record;
* the new ledger's INIT inherits the root's budget and per-root baselines and every root of its parent (a root it
  adds must be empty), so its measured added total is the attempt's cumulative total: the bytes spent before the
  freeze, by the first continuation and between the freeze and the continuation all count, and the headroom it
  opens with is exactly what the attempt has left. Growth the parent never measured is recorded as
  ``UNRESERVED_GROWTH``; a continuation that opens past its budget records a bounded stop;
* the snapshot's own ``measured`` fields are never a budget: a forger who re-seals a snapshot with more headroom
  gains nothing.

:func:`chain` walks a ledger back to its root and proves every segment's claim, identity, budget and baselines.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import storage_admission as sa  # noqa: E402

TOOL_VERSION = "BAS-C37A07-STORAGE-SNAPSHOT-v2"
SNAPSHOT_SCHEMA = "BAS-STORAGE-EVIDENCE-SNAPSHOT-1"
CLAIM_SCHEMA = "BAS-STORAGE-CONTINUATION-CLAIM-1"

REFUSED_OPEN_RESERVATIONS = "REFUSED_SNAPSHOT_OPEN_RESERVATIONS"
REFUSED_MALFORMED = "REFUSED_SNAPSHOT_TRUNCATED_OR_MALFORMED"
REFUSED_TAMPERED = "REFUSED_SNAPSHOT_CONTENT_TAMPERED"
REFUSED_LEDGER = "REFUSED_SNAPSHOT_LEDGER_UNREADABLE_OR_CHAIN_BROKEN"
REFUSED_SEQUENCE = "REFUSED_SNAPSHOT_WRONG_LEDGER_SEQUENCE_OR_HEAD"
REFUSED_PREFIX = "REFUSED_SNAPSHOT_LEDGER_PREFIX_REWRITTEN"
REFUSED_POST_SNAPSHOT = "REFUSED_SNAPSHOT_OPERATIONAL_RECORDS_AFTER_FREEZE"
REFUSED_WRONG_LEDGER = "REFUSED_SNAPSHOT_NAMES_ANOTHER_LEDGER"
REFUSED_EXISTS = "REFUSED_SNAPSHOT_TARGET_EXISTS"
# v2 (MF37A06-02): one continuation per ledger, of the same attempt, over the same roots.
REFUSED_CLAIMED = "REFUSED_CONTINUATION_ALREADY_CLAIMED"
REFUSED_WRONG_ATTEMPT = "REFUSED_CONTINUATION_WRONG_CYCLE_OR_ATTEMPT"
REFUSED_ROOT = "REFUSED_CONTINUATION_ROOT_NOT_EMPTY_OR_NOT_INHERITED"
REFUSED_CLAIM_INVALID = "REFUSED_CONTINUATION_CLAIM_OR_CHAIN_INVALID"


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
    identity = ledger.identity(rows)
    document: dict[str, Any] = {
        "schema": SNAPSHOT_SCHEMA, "label": label, "cycle_number": identity["cycle_number"],
        "attempt_number": identity["attempt_number"], "identity_source": identity["source"],
        "segment": init.get("segment") or 1, "root": init.get("root"),
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
           allow_post_snapshot: tuple[str, ...] = (), allow_refused: bool = False) -> dict[str, Any]:
    """Prove the snapshot is a hash-stable prefix of the ledger as it is now. Raises :class:`SnapshotRefused`.

    ``allow_refused`` (A7): a reservation *refused* after the freeze admitted and holds nothing, so a caller that
    only needs the frozen state (a continuation, the chain proof) may accept such records; they are reported."""

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
    refused_after = [row for row in after if row.get("kind") == "RESERVE" and row.get("decision") == "REFUSED"]
    undeclared = [row for row in after if not any(str(row.get("operation", "")).startswith(prefix)
                                                  for prefix in allow_post_snapshot)
                  and not (allow_refused and row in refused_after)]
    if undeclared:
        raise SnapshotRefused(REFUSED_POST_SNAPSHOT, (
            f"{len(undeclared)} record(s) were appended to the operational ledger after the freeze and are not "
            f"declared final-output work: {[(r['seq'], r['kind'], r.get('operation')) for r in undeclared[:5]]}"))
    return {"result": "PASS", "snapshot": str(snapshot_path), "content_sha256": document["content_sha256"],
            "ledger": str(ledger.path), "records_at_freeze": count, "records_now": len(rows),
            "head_record_sha256": recorded["head_record_sha256"], "post_snapshot_records": len(after),
            "post_snapshot_declared": [(r["seq"], r["kind"], r.get("operation")) for r in after],
            "post_snapshot_refused_reservations": len(refused_after),
            "open_reservations_at_freeze": 0, "bounded_stop_at_freeze": document.get("bounded_stop"),
            "measured_at_freeze": document.get("measured")}


# ----------------------------------------------------------------------------------------------- final ledger


#: The records that state a measured added total, and the field that holds it.
_MEASURED = {"RESERVE": "added_bytes_before", "RECONCILE": "added_bytes_after", "ORPHAN_CLOSED": "added_bytes_now",
             "BOUNDED_STOP": "added_bytes", "OPENED": "added_bytes", "UNRESERVED_GROWTH": "added_bytes"}


def _last_measured_added(rows: list[dict[str, Any]]) -> int:
    """The last added total a ledger measured (0 for a root with no measurement yet)."""

    value = 0
    for row in rows[1:]:
        field = _MEASURED.get(row.get("kind"))
        if field and row.get(field) is not None:
            value = int(row[field])
    return value


def open_successor(snapshot_path: Path | str, ledger_path: Path | str, roots: list[str], *, kind: str, scope: str,
                   shared: list[str] = (), reserve_bytes: int | None = None, note: str = "",
                   cycle_number: int | None = None, attempt_number: int | None = None) -> dict[str, Any]:
    """Open (or resume) *the* continuation of the ledger a snapshot froze: claimed once, under the parent's lock,
    and inheriting the root's budget, baselines, roots and identity. Returns the continuation's INIT (with
    ``resumed`` true when it already existed). The frozen ledger is never written; nothing is re-baselined."""

    document = load_snapshot(snapshot_path)
    headroom = int(document["measured"]["headroom_bytes"])
    if headroom <= 0:
        raise SnapshotRefused(REFUSED_SEQUENCE, f"the snapshot records no headroom ({headroom} bytes); nothing can be "
                                                "reserved after it")
    parent = sa.Ledger(document["ledger"]["path"])
    child = sa.Ledger(ledger_path)
    if sa._same_path(parent.path, child.path):
        raise SnapshotRefused(REFUSED_CLAIM_INVALID, f"{child.path} is the ledger the snapshot froze")
    with parent.locked():
        # A stale snapshot (its ledger went on), a truncated or rewritten ledger, a tampered snapshot: refused here.
        proof = verify(parent.path, snapshot_path, allow_refused=True)
        rows = parent.records()
        identity = parent.identity(rows)
        if (cycle_number is not None and cycle_number != identity["cycle_number"]) or (
                attempt_number is not None and attempt_number != identity["attempt_number"]):
            raise SnapshotRefused(REFUSED_WRONG_ATTEMPT, (
                f"the snapshot's ledger serves Cycle {identity['cycle_number']} Attempt {identity['attempt_number']}; "
                f"the caller asked for Cycle {cycle_number} Attempt {attempt_number}"))
        problems = parent.claim_problems(rows)
        if problems:
            raise SnapshotRefused(REFUSED_CLAIM_INVALID, f"the parent is not its attempt's claimed segment: {problems}")
        # Every root of the parent is inherited with its root baseline; a root added now must be empty.
        inherited = set(parent.config(rows)["baseline"])
        new = [str(Path(r)) for r in [*roots, *shared] if str(Path(r)) not in inherited]
        nonempty = {r: sa.measure(r)["bytes"] for r in new if sa.measure(r)["bytes"]}
        if nonempty:
            raise SnapshotRefused(REFUSED_ROOT, (
                f"a root a continuation adds must be empty (its bytes were never measured by this attempt): {nonempty}"))
        claim_document = {"schema": CLAIM_SCHEMA, "parent_ledger": str(parent.path),
                          "parent_init_record_sha256": sa._digest(parent.lines()[0]),
                          "parent_records": document["ledger"]["records"],
                          "parent_head_record_sha256": document["ledger"]["head_record_sha256"],
                          "snapshot": str(Path(snapshot_path)), "snapshot_content_sha256": document["content_sha256"],
                          "child_ledger": str(child.path), "kind": kind, "cycle_number": identity["cycle_number"],
                          "attempt_number": identity["attempt_number"], "claimed_at": utc_now(), "pid": os.getpid()}
        try:
            with parent.claim_path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(claim_document, indent=2, ensure_ascii=False) + "\n")
        except FileExistsError:
            existing = parent.claim()
            if not (sa._same_path(existing.get("child_ledger"), child.path)
                    and existing.get("snapshot_content_sha256") == document["content_sha256"]):
                raise SnapshotRefused(REFUSED_CLAIMED, (
                    f"{parent.path} was already continued by {existing.get('child_ledger')} from snapshot "
                    f"{existing.get('snapshot_content_sha256')} (claim {parent.claim_path}); a second continuation "
                    "would take the same headroom again")) from None
        claim = parent.claim()
    # Resume: the same continuation, opened again (a restart), is returned as it is -- no new record.
    if child.path.exists():
        try:
            child_rows = child.records()
        except sa.LedgerError as error:
            raise SnapshotRefused(REFUSED_CLAIM_INVALID, f"the claimed continuation is unreadable: {error}") from error
        recorded = (child.config(child_rows).get("continuation") or {}).get("claim") or {}
        if recorded.get("sha256") != claim["_sha256"]:
            raise SnapshotRefused(REFUSED_CLAIM_INVALID, (
                f"{child.path} exists but does not record the claim {parent.claim_path} ({claim['_sha256']})"))
        return {**child.config(child_rows), "resumed": True}
    continuation = {
        "kind": kind, "scope": scope, "parent_ledger": str(parent.path),
        "parent_init_record_sha256": claim_document["parent_init_record_sha256"],
        "snapshot": str(Path(snapshot_path)), "snapshot_content_sha256": document["content_sha256"],
        "parent_records": document["ledger"]["records"],
        "parent_head_record_sha256": document["ledger"]["head_record_sha256"],
        "claim": {"path": str(parent.claim_path), "sha256": claim["_sha256"]},
        "parent_bounded_stop": document.get("bounded_stop"), "snapshot_verified": proof["result"],
    }
    reference = json.dumps({
        "label": f"Cycle #{identity['cycle_number']} — Attempt #{identity['attempt_number']} — {kind}", "scope": scope,
        "continues_snapshot": {"path": str(Path(snapshot_path)), "content_sha256": document["content_sha256"],
                               "ledger": document["ledger"]["path"], "records": document["ledger"]["records"],
                               "head_record_sha256": document["ledger"]["head_record_sha256"],
                               "bounded_stop": document.get("bounded_stop"),
                               "predecessor": document["configuration"].get("predecessor")},
        "budget_rule": ("the root's budget and baselines: the added total is the attempt's cumulative total, so the "
                        "headroom opened with is exactly what the attempt has left"),
        "note": note}, ensure_ascii=False)
    child.init_continuation(parent=parent, parent_rows=rows, new_roots=[str(Path(r)) for r in roots],
                            new_shared=[str(Path(r)) for r in shared], reserve_bytes=reserve_bytes,
                            continuation=continuation, note=reference)
    # What the continuation opened with, measured against the root's baselines, and the growth no ledger measured.
    with child.locked():
        child_rows = child.records()
        state = child.measured(child_rows)
        budget = child.config(child_rows)["budget_bytes"]
        growth = state["added_bytes"] - _last_measured_added(rows)
        opened = {"added_bytes": state["added_bytes"], "headroom_bytes": budget - state["added_bytes"],
                  "parent_last_measured_added_bytes": _last_measured_added(rows),
                  "unreserved_growth_bytes": growth, "roots": state["roots"]}
        child._append(child_rows, {"kind": "OPENED", **opened,
                                   "note": "measured once the continuation exists; its own files are counted"})
        if growth > 0:
            child._append(child_rows, {"kind": "UNRESERVED_GROWTH", "added_bytes": state["added_bytes"],
                                       "growth_bytes": growth,
                                       "note": ("bytes written after the parent's last measurement and before this "
                                                "continuation (the snapshot, the claim, unreserved writes); counted, "
                                                "never reset")})
        if state["added_bytes"] > budget:
            child._append(child_rows, {"kind": "BOUNDED_STOP", "token": None, "operation": f"OPEN {kind}",
                                       "added_bytes": state["added_bytes"], "budget_bytes": budget,
                                       "reason": "the continuation opened past the attempt's budget"})
    return {**child.config(child.records()), "resumed": False, "opened": opened}


def open_final(snapshot_path: Path | str, ledger_path: Path | str, roots: list[str], *,
               reserve_bytes: int | None = None, note: str = "", cycle_number: int | None = None,
               attempt_number: int | None = None) -> dict[str, Any]:
    """Open the final-output ledger: the claimed continuation of the operational ledger the snapshot froze, so the
    final outputs are accounted against what the attempt has left, never a fresh baseline."""

    return open_successor(snapshot_path, ledger_path, roots, kind="final-output ledger",
                          scope=("final packet builds, seal and the FINAL_PACKET lane's own outputs, after the "
                                 "operational snapshot"), reserve_bytes=reserve_bytes, note=note,
                          cycle_number=cycle_number, attempt_number=attempt_number)


def chain(ledger_path: Path | str) -> dict[str, Any]:
    """Walk a ledger back to its root and prove each link: every continuation is the one its parent's claim names,
    its INIT carries the root's identity, budget and baselines, every root of its parent, and its parent's snapshot
    still verifies with nothing after it. Raises :class:`SnapshotRefused`; returns the segments root first."""

    segments: list[dict[str, Any]] = []
    pending_refused = 0
    ledger = sa.Ledger(ledger_path)
    seen: set[str] = set()
    while True:
        key = os.path.normcase(os.path.abspath(str(ledger.path)))
        if key in seen:
            raise SnapshotRefused(REFUSED_CLAIM_INVALID, f"the chain loops at {ledger.path}")
        seen.add(key)
        try:
            rows = ledger.records()
        except sa.LedgerError as error:
            raise SnapshotRefused(REFUSED_LEDGER, f"{ledger.path}: {error}") from error
        init = ledger.config(rows)
        claim = ledger.claim()
        segment = {"ledger": str(ledger.path), "segment": init.get("segment") or 1, "records": len(rows),
                   "identity": ledger.identity(rows), "budget_bytes": init["budget_bytes"],
                   "roots": sorted(init["baseline"]), "continued_by": claim.get("child_ledger") if claim else None,
                   "claim_sha256": claim["_sha256"] if claim else None,
                   "open_reservations": sorted(ledger.open_reservations(rows)),
                   "bounded_stop": (ledger.stopped(rows) or {}).get("seq"),
                   "refused_after_its_freeze": None}
        if segments:
            segment["refused_after_its_freeze"] = pending_refused
        segments.append(segment)
        continuation = init.get("continuation")
        if not continuation:
            break
        problems = ledger.claim_problems(rows)
        if problems:
            raise SnapshotRefused(REFUSED_CLAIM_INVALID, f"{ledger.path}: {problems}")
        parent = sa.Ledger(continuation["parent_ledger"])
        parent_rows = parent.records()
        parent_init = parent.config(parent_rows)
        refused_after = verify(parent.path, continuation["snapshot"], allow_refused=True)[
            "post_snapshot_refused_reservations"]
        if load_snapshot(continuation["snapshot"])["content_sha256"] != continuation["snapshot_content_sha256"]:
            raise SnapshotRefused(REFUSED_CLAIM_INVALID, f"{ledger.path} continues a snapshot whose content changed")
        mismatch = [field for field, same in (
            ("identity", {k: v for k, v in ledger.identity(rows).items() if k != "source"}
             == {k: v for k, v in parent.identity(parent_rows).items() if k != "source"}),
            ("budget", init["budget_bytes"] == parent_init["budget_bytes"]),
            ("baselines", all(init["baseline"].get(root) == value for root, value in parent_init["baseline"].items())),
            ("root", init.get("root") == (parent_init.get("root") or {
                "ledger": str(parent.path), "init_record_sha256": sa._digest(parent.lines()[0])})),
            ("parent_init", continuation.get("parent_init_record_sha256") == sa._digest(parent.lines()[0])))
            if not same]
        if mismatch:
            raise SnapshotRefused(REFUSED_CLAIM_INVALID, f"{ledger.path} does not inherit its parent's {mismatch}")
        pending_refused = refused_after
        ledger = parent
    segments.reverse()
    return {"result": "PASS", "segments": segments, "root": segments[0]["ledger"],
            "live": segments[-1]["ledger"], "identity": segments[0]["identity"]}


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
    for command in (final, successor):
        command.add_argument("--cycle-number", type=int, default=None)
        command.add_argument("--attempt-number", type=int, default=None)
    chained = sub.add_parser("chain")
    chained.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.mode == "freeze":
            result = freeze(args.ledger, args.out, label=args.label, scope=args.scope)
        elif args.mode == "verify":
            result = verify(args.ledger, args.snapshot, allow_post_snapshot=tuple(args.allow_post_snapshot))
        elif args.mode == "chain":
            result = chain(args.ledger)
        elif args.mode == "open-successor":
            result = open_successor(args.snapshot, args.ledger, args.root, kind=args.kind, scope=args.scope,
                                    shared=args.shared, note=args.note, cycle_number=args.cycle_number,
                                    attempt_number=args.attempt_number)
        else:
            result = open_final(args.snapshot, args.ledger, args.root, reserve_bytes=args.reserve_bytes, note=args.note,
                                cycle_number=args.cycle_number, attempt_number=args.attempt_number)
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
