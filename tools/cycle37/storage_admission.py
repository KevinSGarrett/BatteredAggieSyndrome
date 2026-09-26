r"""Cycle #37 — Attempt #5 — cumulative storage admission before every allocation (TP37-A05-05, MF37A04-05).

    storage_admission.py init      --ledger <jsonl> --budget-bytes N --reserve-bytes N --root <dir> ... [--shared <dir> ...]
    storage_admission.py reserve   --ledger <jsonl> --operation <id> --estimate-bytes N
    storage_admission.py reconcile --ledger <jsonl> --token <id>
    storage_admission.py run       --ledger <jsonl> --operation <id> --estimate-bytes N -- <command ...>
    storage_admission.py status    --ledger <jsonl>

Attempt 4 recorded its storage ceiling and checked only the free-space reserve, so repeated builds, full-size
tamper fixtures and saved pages reached 6,069,669,694 bytes against a 4,294,967,296-byte budget (W37A04-15). This
module is the prevention. It is not a filesystem quota and does not claim to be one.

* **One append-only ledger per attempt.** ``init`` measures the declared roots once (an attempt's own roots are
  normally absent, so their baseline is zero; a shared Git store has a nonzero baseline) and writes the budget,
  the free-space reserve and that baseline. It refuses to run on an existing ledger, so a restart can never take
  a new baseline and forget earlier allocations. Every record carries the SHA-256 of the one before it.
* **Added bytes are measured, not remembered.** The added total is the logical size of every file under the
  declared roots now, minus the baseline -- a restart, a crashed process or a forgotten record cannot lower it.
  Reparse points are counted as entries and never followed.
* **Reservation before effect.** ``reserve`` admits an operation only if the measured added bytes, plus the
  estimates of every reservation still open (including another process's concurrent one), plus this estimate
  stay within the budget, and the free bytes left after all of them stay above the reserve. Otherwise it records
  ``REFUSED`` and the operation must not start. The check and the append happen under one lock.
* **Readback after effect.** ``reconcile`` measures again and records the actual added bytes. An operation that
  used more than it reserved is recorded as ``UNDERESTIMATED``; one that took the cumulative total past the
  budget records ``BOUNDED_STOP``, and every later reservation is refused -- there is no retroactive increase.
* **Bounded stop while running.** ``run`` reserves, starts the command, measures every few seconds and ends the
  command's process tree the moment the added total passes the budget or the operation passes its own
  reservation (with a small tolerance for measurement lag), recording ``BOUNDED_STOP``.
* **Restart.** A reservation left open by a process that no longer exists is closed by the next command with the
  measured total at that moment (``ORPHAN_CLOSED``); until then it still counts as pending. A reservation made from
  the command line outlives the command that made it, so it is held for an explicit ``reconcile`` instead.

Nothing here deletes, moves or prunes a file. Cleanup is a separate owner decision.

Cycle #37 -- Attempt #7 (MF37A06-02). A continuation opened from an unchanged, valid snapshot measured a *fresh*
baseline and took the snapshot's headroom as its budget, so a second continuation of the same snapshot saw every
byte the first had spent as baseline and admitted the same headroom again (1,100,000 projected against a
1,000,000-byte budget). A ledger segment is now a file of one attempt-wide ledger, never a new baseline:

* **Identity comes from the ledger.** A root ``init`` records the cycle and attempt it serves (``--cycle-number``,
  ``--attempt-number``); every later record, in every segment, carries that identity from its root's INIT -- never
  a module constant, which labelled Attempt 6's new segments "Attempt 5".
* **A continuation inherits the root's state.** Its INIT (written by ``storage_snapshot.open_successor``) carries the
  root ledger's budget and per-root baselines, every root of its parent, and its root and parent identities, so the
  added total it measures is the attempt's cumulative total. A root it adds must be empty when it is added.
* **One continuation per ledger.** Continuing a ledger claims it: a create-only claim file beside it
  (``<ledger>.continuation.json``), created under the ledger's lock. A second or concurrent continuation, from the
  same or any snapshot, is refused; the same continuation opened again resumes. A continued ledger refuses every
  later reservation (the refusal is recorded), and a continuation whose parent's claim does not name it refuses too.
* **A truncated ledger is refused.** After each append the ledger's head (record count and last record digest) is
  appended to ``<ledger>.head.jsonl``; a ledger shorter than its last head, or whose head record changed, is
  refused. (A procedural record, not an OS-level tamper seal: the head log could be cut consistently too.)

Cycle #37 -- Attempt #8 (MF37A07-02). Two callers opening the *same* continuation were each told the child did not
exist -- the check ran outside the lock that wrote the INIT -- and both appended one; the child's chain broke at line
3 and every later restart refused. And a continuation of a stopped ledger, or one opened with a lower reserve, simply
admitted: the stop and the reserve were not carried into the state a continuation inherits.

* **Initialization is atomic.** A continuation's INIT is written only while its parent's lock is held (by
  ``storage_snapshot.open_successor``) *and* its own: the child's absence, and the absence of a head log that would
  mean an interrupted earlier initialization, are checked under that lock, never before it.
* **A torn record is an interrupted append, not a crash.** A line that is not a complete JSON record raises
  :class:`LedgerError` naming it (``ledger line N is incomplete``), so a caller refuses it for that cause.
* **A stop and a reserve are inherited.** A continuation's INIT records its parent's *effective* stop (its own
  ``BOUNDED_STOP``, or one it inherited and never answered) and the reserve it runs under. A continuation opened from a
  stopped parent, or with a reserve other than its parent's, must carry a **revised plan**: a named existing authority
  document (path and SHA-256), the decision, the bytes it needs and the stop it answers, feasible under the unchanged
  ceiling when it is opened. Without one, ``open_successor`` refuses. With one, the plan's ceiling -- the cumulative
  total measured at the open plus the planned bytes, never more than the budget -- bounds every later reservation of
  that continuation and of the continuations it inherits to; exceeding it at readback records a bounded stop. The tool
  proves the plan names an existing, unchanged document and is feasible; whether that document *is* authority is the
  owner's and the manager's decision, never this tool's. The budget itself is never a parameter of a continuation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

TOOL_VERSION = "BAS-C37A08-STORAGE-ADMISSION-v3"
#: The identity a root ledger records only when its caller names none (``identity.source`` says so); every record
#: after a ledger's INIT carries the INIT's identity, not these.
CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 8
#: Beside a ledger: the create-only claim of its one continuation, and the head written after every append.
CLAIM_SUFFIX = ".continuation.json"
HEAD_SUFFIX = ".head.jsonl"
#: Measurement lag allowance for ``run``: an operation may exceed its reservation by this much before it is stopped.
TOLERANCE_BYTES = 8 * 1024 * 1024
LOCK_TIMEOUT_SECONDS = 120.0
#: The holder of a reservation made from the command line: it is closed only by an explicit ``reconcile``.
EXPLICIT_HOLDER = "EXPLICIT_RECONCILE"
_REPARSE = 0x400


class AdmissionRefused(RuntimeError):
    """A reservation the ledger refused; the operation must not start."""

    def __init__(self, record: dict[str, Any]) -> None:
        super().__init__(record.get("reason") or "storage admission refused")
        self.record = record


class LedgerError(RuntimeError):
    """The ledger is missing, unreadable or its chain is broken."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _same_path(a: Any, b: Any) -> bool:
    return bool(a) and bool(b) and os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))


def tool_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def measure(root: Path | str) -> dict[str, int]:
    """Logical bytes, files and directories under ``root``; reparse points counted, never followed."""

    total = files = directories = reparse = errors = 0
    base = str(root)
    if not os.path.lexists(base):
        return {"bytes": 0, "files": 0, "directories": 0, "reparse_points": 0, "errors": 0, "exists": 0}
    stack = [base]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        stat = entry.stat(follow_symlinks=False)
                    except OSError:
                        errors += 1
                        continue
                    attributes = getattr(stat, "st_file_attributes", 0)
                    if entry.is_dir(follow_symlinks=False):
                        directories += 1
                        if attributes & _REPARSE:
                            reparse += 1
                        else:
                            stack.append(entry.path)
                    else:
                        files += 1
                        # A directory listing on Windows reports the size a file had when its entry was last
                        # updated, which lags a file another process still has open for writing; lstat opens the
                        # file itself and reads its current size, so a running writer is seen as it grows.
                        try:
                            size = os.lstat(entry.path).st_size
                        except OSError:
                            size = stat.st_size
                        total += size
                        if attributes & _REPARSE:
                            reparse += 1
        except OSError:
            errors += 1
    return {"bytes": total, "files": files, "directories": directories, "reparse_points": reparse,
            "errors": errors, "exists": 1}


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes  # noqa: PLC0415

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class Ledger:
    """One attempt's storage ledger: an append-only, hash-chained JSON-lines file and its lock."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.claim_path = Path(str(self.path) + CLAIM_SUFFIX)
        self.head_path = Path(str(self.path) + HEAD_SUFFIX)

    # ------------------------------------------------------------ file access
    def lines(self) -> list[str]:
        return [line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def records(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            raise LedgerError(f"no storage ledger at {self.path}; run init first")
        rows = []
        previous = None
        lines = self.lines()
        for number, line in enumerate(lines, start=1):
            try:
                row = json.loads(line)
            except ValueError as error:
                # MF37A07-02: a torn line is an interrupted append; it is named, never a crash of the caller.
                raise LedgerError(f"ledger line {number} is incomplete (an interrupted append): {error}") from error
            if not isinstance(row, dict):
                raise LedgerError(f"ledger line {number} is not a ledger record")
            if row.get("previous_record_sha256") != previous:
                raise LedgerError(f"ledger chain broken at line {number}")
            previous = _digest(line)
            rows.append(row)
        if not rows or rows[0].get("kind") != "INIT":
            raise LedgerError("the ledger does not start with INIT")
        # MF37A06-02: a chain cannot show that its own tail was cut off; the head written after every append can.
        # A head that lags (a crash between an append and its head write) is tolerated; a ledger shorter than its
        # head, or whose head record is no longer the one recorded, is not.
        head = self.head()
        if head is not None:
            seq, digest = head
            if seq > len(lines) or _digest(lines[seq - 1]) != digest:
                raise LedgerError(f"the ledger is truncated or rewritten: its head records {seq} record(s) ending in "
                                  f"{digest}, but the ledger now has {len(lines)}")
        return rows

    def head(self) -> tuple[int, str] | None:
        """(record count, last record digest) of the last complete line of the append-only head log; a torn final
        line (a crash while it was written) is ignored, since the ledger line it follows was already written."""

        if not self.head_path.is_file():
            return None
        last = None
        for line in self.head_path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
                last = (int(entry["seq"]), str(entry["record_sha256"]))
            except (ValueError, KeyError, TypeError):
                continue
        return last

    @staticmethod
    def identity(rows: list[dict[str, Any]]) -> dict[str, Any]:
        """The cycle and attempt a ledger serves: its INIT's, which a continuation inherits from its root."""

        init = rows[0]
        stated = init.get("identity") or {}
        return {"cycle_number": stated.get("cycle_number", init.get("cycle_number")),
                "attempt_number": stated.get("attempt_number", init.get("attempt_number")),
                "source": stated.get("source", "INIT_STAMP_BEFORE_ATTEMPT_7")}

    def _append(self, rows: list[dict[str, Any]], record: dict[str, Any]) -> dict[str, Any]:
        previous = None
        if rows:
            previous = _digest(self.lines()[-1])
            identity = self.identity(rows)
        else:  # the INIT states the identity itself
            identity = record.get("identity") or {"cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER}
        record = {"seq": len(rows) + 1, "previous_record_sha256": previous, "at": utc_now(),
                  "cycle_number": identity["cycle_number"], "attempt_number": identity["attempt_number"],
                  "tool_version": TOOL_VERSION, "tool_sha256": tool_sha256(), "pid": os.getpid(), **record}
        line = json.dumps(record, sort_keys=True, ensure_ascii=False)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        rows.append(record)
        with self.head_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"seq": record["seq"], "record_sha256": _digest(line)}, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return record

    @contextmanager
    def locked(self) -> Iterator[None]:
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        while True:
            try:
                descriptor = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(descriptor, json.dumps({"pid": os.getpid(), "at": utc_now()}).encode("utf-8"))
                os.close(descriptor)
                break
            except FileExistsError:
                try:
                    holder = json.loads(self.lock_path.read_text(encoding="utf-8") or "{}")
                except (OSError, ValueError):
                    holder = {}
                if holder.get("pid") and not _pid_alive(int(holder["pid"])):
                    # A lock whose holder ended is released here; the ledger itself is never rewritten.
                    try:
                        self.lock_path.unlink()
                    except OSError:
                        pass
                    continue
                if time.monotonic() > deadline:
                    raise LedgerError(f"the ledger lock {self.lock_path} is held by {holder}")
                time.sleep(0.2)
        try:
            yield
        finally:
            # MF37A07-02 (found by the Attempt 8 many-caller test): on Windows a waiter reading the lock file at the
            # moment of release makes the unlink fail, and a lock left behind by a live process was then never
            # released -- every later caller in that process timed out. The release is retried until it succeeds.
            for _ in range(250):
                try:
                    self.lock_path.unlink()
                    break
                except FileNotFoundError:
                    break
                except OSError:
                    time.sleep(0.02)

    # ------------------------------------------------------------ state
    @staticmethod
    def config(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return rows[0]

    def measured(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        init = self.config(rows)
        roots = {}
        added = 0
        for root, baseline in init["baseline"].items():
            now = measure(root)
            delta = now["bytes"] - baseline["bytes"]
            roots[root] = {"bytes_now": now["bytes"], "baseline_bytes": baseline["bytes"], "added_bytes": delta,
                           "files": now["files"], "reparse_points": now["reparse_points"], "errors": now["errors"]}
            added += delta
        free = shutil.disk_usage(init["disk"]).free
        return {"added_bytes": added, "free_bytes": free, "roots": roots}

    @staticmethod
    def open_reservations(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        open_rows: dict[str, dict[str, Any]] = {}
        for row in rows:
            if row["kind"] == "RESERVE" and row.get("decision") == "ADMITTED":
                open_rows[row["token"]] = row
            elif row["kind"] in ("RECONCILE", "ORPHAN_CLOSED") and row.get("token") in open_rows:
                open_rows.pop(row["token"])
        return open_rows

    @staticmethod
    def stopped(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        return next((row for row in rows if row["kind"] == "BOUNDED_STOP"), None)

    def effective_stop(self, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        """MF37A07-02: the stop this ledger is under -- its own ``BOUNDED_STOP``, or the stop its INIT inherited and
        no revised plan answered. A continuation written before Attempt 8 recorded only its parent's own stop."""

        own = self.stopped(rows)
        if own:
            return {**own, "ledger": str(self.path), "inherited": False}
        init = self.config(rows)
        inherited = (init["inherited_stop"] if "inherited_stop" in init
                     else (init.get("continuation") or {}).get("parent_bounded_stop"))
        if inherited and not init.get("revised_plan"):
            return {**inherited, "inherited": True}
        return None

    @staticmethod
    def plan_ceiling(rows: list[dict[str, Any]]) -> int | None:
        """The cumulative added total a revised plan (this ledger's, or one inherited) allows, or None."""

        value = rows[0].get("plan_ceiling_bytes")
        return None if value is None else int(value)

    def admission_limit(self, rows: list[dict[str, Any]]) -> int:
        """What the measured cumulative total may reach: the root's budget, or less under a revised plan."""

        budget = int(self.config(rows)["budget_bytes"])
        ceiling = self.plan_ceiling(rows)
        return budget if ceiling is None else min(budget, ceiling)

    def _close_orphans(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        closed = []
        for token, row in self.open_reservations(rows).items():
            if row.get("holder") == EXPLICIT_HOLDER:
                continue  # closed only by an explicit readback, never by process liveness
            if row.get("pid") != os.getpid() and not _pid_alive(int(row.get("pid") or 0)):
                state = self.measured(rows)
                closed.append(self._append(rows, {
                    "kind": "ORPHAN_CLOSED", "token": token, "operation": row.get("operation"),
                    "added_bytes_now": state["added_bytes"], "free_bytes": state["free_bytes"],
                    "note": ("the reserving process ended without a readback; the reservation is closed with the "
                             "measured total, which already contains whatever it wrote")}))
        return closed

    # ------------------------------------------------------------ commands
    def init(self, *, budget_bytes: int, reserve_bytes: int, roots: Iterable[Path | str],
             shared: Iterable[Path | str] = (), note: str = "", cycle_number: int | None = None,
             attempt_number: int | None = None) -> dict[str, Any]:
        """Start an attempt's root ledger: the one baseline every later segment of the attempt inherits."""

        if self.path.exists():
            raise LedgerError(f"{self.path} exists; a ledger is initialized once and never re-baselined")
        declared = [str(Path(root)) for root in roots] + [str(Path(root)) for root in shared]
        if not declared:
            raise LedgerError("at least one root is required")
        if (cycle_number is None) != (attempt_number is None):
            raise LedgerError("name both the cycle and the attempt a ledger serves, or neither")
        identity = ({"cycle_number": int(cycle_number), "attempt_number": int(attempt_number), "source": "CALLER"}
                    if cycle_number is not None else
                    {"cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "source": "TOOL_DEFAULT"})
        # Measure before this ledger (inside one of the roots) exists, so its own bytes are counted as added.
        baseline = {root: measure(root) for root in declared}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        disk = os.path.splitdrive(str(self.path.resolve()))[0] + os.sep
        with self.locked():
            return self._append([], {
                "kind": "INIT", "budget_bytes": int(budget_bytes), "reserve_bytes": int(reserve_bytes),
                "owned_roots": [str(Path(root)) for root in roots], "shared_roots": [str(Path(r)) for r in shared],
                "baseline": baseline, "disk": disk, "free_bytes_at_init": shutil.disk_usage(disk).free,
                "note": note, "identity": identity, "segment": 1, "root": None,
                "rule": ("admit iff added_now + open_estimates + estimate <= budget and free - open_estimates - "
                         "estimate >= reserve; no re-baseline, no retroactive increase, no deletion")})

    def init_continuation(self, *, parent: "Ledger", parent_rows: list[dict[str, Any]], new_roots: Iterable[str],
                          new_shared: Iterable[str], reserve_bytes: int | None, continuation: dict[str, Any],
                          note: str = "", inherited_stop: dict[str, Any] | None = None,
                          revised_plan: dict[str, Any] | None = None,
                          plan_ceiling_bytes: int | None = None) -> dict[str, Any]:
        """Write the INIT of the claimed continuation of ``parent`` (called by ``storage_snapshot.open_successor``
        while it holds the parent's lock, after it has verified the parent's snapshot and created the claim): the
        root's budget, every root with the baseline its root measured, the root's identity, the new, empty roots it
        adds, the stop it inherits and the revised plan (if any) it continues under.

        MF37A07-02: the child's absence is checked under the child's own lock, in the same critical section as the
        append -- never before it -- so two callers can never both write an INIT."""

        init = self.config(parent_rows)
        owned, shared = list(init.get("owned_roots") or []), list(init.get("shared_roots") or [])
        baseline = {root: dict(value) for root, value in init["baseline"].items()}
        added_roots = {}
        for root, bucket in [(str(Path(r)), owned) for r in new_roots] + [(str(Path(r)), shared) for r in new_shared]:
            if root in baseline:
                continue
            now = measure(root)
            if now["bytes"]:
                raise LedgerError(f"a root a continuation adds must be empty when it is added; {root} holds "
                                  f"{now['bytes']} bytes that no ledger of this attempt measured")
            baseline[root] = now
            bucket.append(root)
            added_roots[root] = now
        parent_line = parent.lines()[0]
        root = init.get("root") or {"ledger": str(parent.path), "init_record_sha256": _digest(parent_line)}
        identity = {**self.identity(parent_rows), "source": "INHERITED_FROM_ROOT"}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        disk = os.path.splitdrive(str(self.path.resolve()))[0] + os.sep
        with self.locked():
            if self.path.exists():
                raise LedgerError(f"{self.path} exists; a ledger is initialized once and never re-baselined")
            if self.head_path.exists():
                raise LedgerError(f"{self.head_path} exists without its ledger: an earlier initialization was "
                                  "interrupted or the ledger was removed; it is not initialized again")
            return self._append([], {
                "kind": "INIT", "budget_bytes": int(init["budget_bytes"]),
                "reserve_bytes": int(init["reserve_bytes"] if reserve_bytes is None else reserve_bytes),
                "owned_roots": owned, "shared_roots": shared, "baseline": baseline, "roots_added": added_roots,
                "disk": disk, "free_bytes_at_init": shutil.disk_usage(disk).free, "note": note,
                "identity": identity, "segment": int(init.get("segment") or 1) + 1, "root": root,
                "continuation": continuation, "inherited_stop": inherited_stop, "revised_plan": revised_plan,
                "plan_ceiling_bytes": plan_ceiling_bytes,
                "rule": ("one attempt-wide ledger: the root's budget and baselines, every root of the parent; admit iff "
                         "added_now + open_estimates + estimate <= min(budget, revised plan ceiling) and free - "
                         "open_estimates - estimate >= reserve, and no unanswered stop; no re-baseline, no "
                         "retroactive increase, no deletion")})

    # ------------------------------------------------------------ continuation claims
    def claim(self) -> dict[str, Any] | None:
        """The claim of this ledger's one continuation, or None when it has not been continued."""

        if not self.claim_path.is_file():
            return None
        data = self.claim_path.read_bytes()
        try:
            document = json.loads(data.decode("utf-8"))
        except ValueError as error:
            raise LedgerError(f"the continuation claim {self.claim_path} is unreadable: {error}") from error
        return {**document, "_sha256": hashlib.sha256(data).hexdigest()}

    def continuation_problems(self, rows: list[dict[str, Any]]) -> list[str]:
        """Why this ledger may not admit a reservation: it was continued, or it is a continuation its parent's
        claim does not name (a forked, replayed or stale segment). Empty when it is the attempt's live segment."""

        problems = []
        claim = self.claim()
        if claim is not None:
            problems.append(f"this ledger was continued by {claim.get('child_ledger')} (claim {self.claim_path}); "
                            "reservations belong on its continuation")
        return problems + self.claim_problems(rows)

    def claim_problems(self, rows: list[dict[str, Any]]) -> list[str]:
        """For a continuation: why its parent's claim does not name it (empty for a root or a claimed segment)."""

        problems: list[str] = []
        continuation = self.config(rows).get("continuation")
        if continuation:
            recorded = continuation.get("claim") or {}
            parent = Ledger(continuation.get("parent_ledger") or "")
            try:
                parent_claim = parent.claim()
            except LedgerError as error:
                parent_claim, problems = None, problems + [str(error)]
            if parent_claim is None:
                problems.append(f"its parent {parent.path} holds no continuation claim")
            elif parent_claim["_sha256"] != recorded.get("sha256") or not _same_path(
                    parent_claim.get("child_ledger"), self.path):
                problems.append(f"its parent's claim {parent.claim_path} names {parent_claim.get('child_ledger')} "
                                f"(SHA-256 {parent_claim['_sha256']}), not this ledger's recorded claim "
                                f"{recorded.get('sha256')}")
        return problems

    def reserve(self, operation: str, estimate_bytes: int, *, note: str = "",
                explicit: bool = False) -> dict[str, Any]:
        """Admit or refuse ``operation``. ``explicit`` reservations (the command-line form, which outlives its own
        process) stay open until an explicit ``reconcile``; the others close as orphans when their process ends."""

        if int(estimate_bytes) < 0:
            raise ValueError("an estimate is a nonnegative byte count")
        with self.locked():
            rows = self.records()
            self._close_orphans(rows)
            init = self.config(rows)
            state = self.measured(rows)
            pending = self.open_reservations(rows)
            pending_bytes = sum(int(row["estimate_bytes"]) for row in pending.values())
            projected = state["added_bytes"] + pending_bytes + int(estimate_bytes)
            free_after = state["free_bytes"] - pending_bytes - int(estimate_bytes)
            # MF37A07-02: a stop this segment inherited and no revised plan answered refuses exactly as its own does.
            stop = self.effective_stop(rows)
            ceiling = self.plan_ceiling(rows)
            reasons = []
            if stop:
                reasons.append(f"a bounded stop is recorded (seq {stop.get('seq')}"
                               + (", inherited from the ledger this one continues" if stop.get("inherited") else "")
                               + "); no further allocation is admitted without a revised plan")
            # MF37A06-02: only the attempt's one live segment admits; a continued or unclaimed segment refuses.
            reasons.extend(self.continuation_problems(rows))
            if projected > init["budget_bytes"]:
                reasons.append(f"added {state['added_bytes']} + open reservations {pending_bytes} + estimate "
                               f"{estimate_bytes} = {projected} exceeds the budget {init['budget_bytes']}")
            if ceiling is not None and projected > ceiling:
                reasons.append(f"added {state['added_bytes']} + open reservations {pending_bytes} + estimate "
                               f"{estimate_bytes} = {projected} exceeds the revised plan's ceiling {ceiling}")
            if free_after < init["reserve_bytes"]:
                reasons.append(f"free {state['free_bytes']} - open {pending_bytes} - estimate {estimate_bytes} = "
                               f"{free_after} is below the reserve {init['reserve_bytes']}")
            record = self._append(rows, {
                "kind": "RESERVE", "token": uuid.uuid4().hex, "operation": operation,
                "estimate_bytes": int(estimate_bytes), "added_bytes_before": state["added_bytes"],
                "open_reservations_before": sorted(pending), "open_estimate_bytes_before": pending_bytes,
                "projected_added_bytes": projected, "free_bytes": state["free_bytes"],
                "free_bytes_after_reservations": free_after, "budget_bytes": init["budget_bytes"],
                "reserve_bytes": init["reserve_bytes"], "plan_ceiling_bytes": ceiling,
                "decision": "REFUSED" if reasons else "ADMITTED",
                "holder": EXPLICIT_HOLDER if explicit else f"pid:{os.getpid()}",
                "reason": "; ".join(reasons) or None, "note": note})
        if reasons:
            raise AdmissionRefused(record)
        return record

    def reconcile(self, token: str, *, note: str = "") -> dict[str, Any]:
        with self.locked():
            rows = self.records()
            opened = next((row for row in rows if row["kind"] == "RESERVE" and row.get("token") == token), None)
            if opened is None or opened.get("decision") != "ADMITTED":
                raise LedgerError(f"no admitted reservation {token}")
            if token not in self.open_reservations(rows):
                raise LedgerError(f"reservation {token} is already closed")
            init = self.config(rows)
            state = self.measured(rows)
            used = state["added_bytes"] - opened["added_bytes_before"]
            under = used > opened["estimate_bytes"]
            record = self._append(rows, {
                "kind": "RECONCILE", "token": token, "operation": opened["operation"],
                "estimate_bytes": opened["estimate_bytes"], "added_bytes_before": opened["added_bytes_before"],
                "added_bytes_after": state["added_bytes"], "operation_added_bytes": used,
                "underestimated": under, "free_bytes": state["free_bytes"], "roots": state["roots"],
                "within_budget": state["added_bytes"] <= init["budget_bytes"], "note": note,
                "attribution": ("the change in the measured total over the operation; a concurrent operation's "
                                "writes in the same window are included, which is conservative")})
            limit = self.admission_limit(rows)
            if state["added_bytes"] > limit and not self.stopped(rows):
                self._append(rows, {"kind": "BOUNDED_STOP", "token": token, "operation": opened["operation"],
                                    "added_bytes": state["added_bytes"], "budget_bytes": init["budget_bytes"],
                                    "plan_ceiling_bytes": self.plan_ceiling(rows),
                                    "reason": ("the measured total passed the budget" if limit == init["budget_bytes"]
                                               else "the measured total passed the revised plan's ceiling")
                                    + "; every later reservation is refused"})
        return record

    def stop(self, token: str, operation: str, reason: str, added: int) -> dict[str, Any]:
        with self.locked():
            rows = self.records()
            return self._append(rows, {"kind": "BOUNDED_STOP", "token": token, "operation": operation,
                                       "added_bytes": added, "budget_bytes": self.config(rows)["budget_bytes"],
                                       "reason": reason})

    def status(self) -> dict[str, Any]:
        rows = self.records()
        init = self.config(rows)
        state = self.measured(rows)
        pending = self.open_reservations(rows)
        claim = self.claim()
        return {"ledger": str(self.path), "records": len(rows), "identity": self.identity(rows),
                "segment": init.get("segment") or 1, "root": init.get("root"),
                "continuation": init.get("continuation"),
                "continued_by": claim.get("child_ledger") if claim else None,
                "continuation_problems": self.continuation_problems(rows), "budget_bytes": init["budget_bytes"],
                "reserve_bytes": init["reserve_bytes"], "added_bytes": state["added_bytes"],
                "headroom_bytes": self.admission_limit(rows) - state["added_bytes"]
                - sum(int(r["estimate_bytes"]) for r in pending.values()),
                "free_bytes": state["free_bytes"], "open_reservations": {k: {"operation": v["operation"],
                                                                                "estimate_bytes": v["estimate_bytes"],
                                                                                "pid": v["pid"]}
                                                                            for k, v in pending.items()},
                "bounded_stop": self.stopped(rows), "effective_stop": self.effective_stop(rows),
                "plan_ceiling_bytes": self.plan_ceiling(rows), "revised_plan": init.get("revised_plan"),
                "roots": state["roots"],
                "refused": sum(1 for r in rows if r["kind"] == "RESERVE" and r["decision"] == "REFUSED"),
                "underestimated": sum(1 for r in rows if r["kind"] == "RECONCILE" and r.get("underestimated"))}


@contextmanager
def reservation(ledger: Ledger, operation: str, estimate_bytes: int, *, note: str = "") -> Iterator[dict[str, Any]]:
    """Reserve before the block runs (raising :class:`AdmissionRefused` before any effect), reconcile after."""

    record = ledger.reserve(operation, estimate_bytes, note=note)
    try:
        yield record
    finally:
        ledger.reconcile(record["token"], note="context exit")


def _terminate_tree(process: subprocess.Popen) -> None:
    """End the command and its descendants; inside a canonical write guard (which refuses ``taskkill`` as a native
    child) only the direct child can be ended, which is what a guarded caller started."""

    ended_tree = False
    if os.name == "nt":
        try:
            ended_tree = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                                        check=False).returncode == 0
        except OSError:
            ended_tree = False
    if not ended_tree and process.poll() is None:
        process.kill()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()


def run_bounded(ledger: Ledger, operation: str, estimate_bytes: int, argv: list[str], *, cwd: str | None = None,
                env: dict[str, str] | None = None, poll_seconds: float = 3.0, stdout: Any = None,
                stderr: Any = None, timeout: float | None = None) -> dict[str, Any]:
    """Reserve, run ``argv`` while measuring, stop it at the budget or past its reservation, then reconcile."""

    record = ledger.reserve(operation, estimate_bytes)
    token = record["token"]
    rows = ledger.records()
    budget = ledger.config(rows)["budget_bytes"]
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr)
    stopped = None
    peak = record["added_bytes_before"]
    started = time.monotonic()
    while True:
        try:
            exit_code = process.wait(timeout=poll_seconds)
            break
        except subprocess.TimeoutExpired:
            pass
        added = ledger.measured(rows)["added_bytes"]
        peak = max(peak, added)
        used = added - record["added_bytes_before"]
        if added > budget:
            stopped = f"the measured total {added} passed the budget {budget} while {operation} ran"
        elif used > estimate_bytes + TOLERANCE_BYTES:
            stopped = (f"{operation} used {used} bytes, past its reservation {estimate_bytes} + tolerance "
                       f"{TOLERANCE_BYTES}")
        elif timeout is not None and time.monotonic() - started > timeout:
            stopped = f"{operation} passed its time limit of {timeout}s"
        if stopped:
            _terminate_tree(process)
            exit_code = process.returncode
            ledger.stop(token, operation, stopped, added)
            break
    closing = ledger.reconcile(token, note="bounded run" + (f"; stopped: {stopped}" if stopped else ""))
    return {"reservation": record, "reconcile": closing, "exit_code": exit_code, "bounded_stop": stopped,
            "peak_added_bytes_observed": max(peak, closing["added_bytes_after"])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    for name in ("init", "reserve", "reconcile", "run", "status"):
        command = sub.add_parser(name)
        command.add_argument("--ledger", type=Path, required=True)
        if name == "init":
            command.add_argument("--budget-bytes", type=int, required=True)
            command.add_argument("--reserve-bytes", type=int, required=True)
            command.add_argument("--root", action="append", required=True)
            command.add_argument("--shared", action="append", default=[])
            command.add_argument("--note", default="")
            command.add_argument("--cycle-number", type=int, default=None)
            command.add_argument("--attempt-number", type=int, default=None)
        if name in ("reserve", "run"):
            command.add_argument("--operation", required=True)
            command.add_argument("--estimate-bytes", type=int, required=True)
            command.add_argument("--note", default="")
        if name == "reconcile":
            command.add_argument("--token", required=True)
            command.add_argument("--note", default="")
        if name == "run":
            command.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    ledger = Ledger(args.ledger)
    try:
        if args.mode == "init":
            result = ledger.init(budget_bytes=args.budget_bytes, reserve_bytes=args.reserve_bytes, roots=args.root,
                                 shared=args.shared, note=args.note, cycle_number=args.cycle_number,
                                 attempt_number=args.attempt_number)
        elif args.mode == "reserve":
            result = ledger.reserve(args.operation, args.estimate_bytes, note=args.note, explicit=True)
        elif args.mode == "reconcile":
            result = ledger.reconcile(args.token, note=args.note)
        elif args.mode == "run":
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            if not command:
                parser.error("run needs a command after --")
            result = run_bounded(ledger, args.operation, args.estimate_bytes, command)
            print(json.dumps(result, indent=1, default=str))
            return 0 if result["exit_code"] == 0 and not result["bounded_stop"] else 1
        else:
            result = ledger.status()
    except AdmissionRefused as refused:
        print(json.dumps(refused.record, indent=1, default=str))
        return 3
    except LedgerError as error:
        print(json.dumps({"error": str(error)}))
        return 2
    print(json.dumps(result, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
