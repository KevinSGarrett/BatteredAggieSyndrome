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

TOOL_VERSION = "BAS-C37A05-STORAGE-ADMISSION-v1"
CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 5
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

    # ------------------------------------------------------------ file access
    def records(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            raise LedgerError(f"no storage ledger at {self.path}; run init first")
        rows = []
        previous = None
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("previous_record_sha256") != previous:
                raise LedgerError(f"ledger chain broken at line {number}")
            previous = _digest(line)
            rows.append(row)
        if not rows or rows[0].get("kind") != "INIT":
            raise LedgerError("the ledger does not start with INIT")
        return rows

    def _append(self, rows: list[dict[str, Any]], record: dict[str, Any]) -> dict[str, Any]:
        previous = None
        if rows:
            lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
            previous = _digest(lines[-1])
        record = {"seq": len(rows) + 1, "previous_record_sha256": previous, "at": utc_now(),
                  "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "tool_version": TOOL_VERSION,
                  "tool_sha256": tool_sha256(), "pid": os.getpid(), **record}
        line = json.dumps(record, sort_keys=True, ensure_ascii=False)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        rows.append(record)
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
            try:
                self.lock_path.unlink()
            except OSError:
                pass

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
             shared: Iterable[Path | str] = (), note: str = "") -> dict[str, Any]:
        if self.path.exists():
            raise LedgerError(f"{self.path} exists; a ledger is initialized once and never re-baselined")
        declared = [str(Path(root)) for root in roots] + [str(Path(root)) for root in shared]
        if not declared:
            raise LedgerError("at least one root is required")
        # Measure before this ledger (inside one of the roots) exists, so its own bytes are counted as added.
        baseline = {root: measure(root) for root in declared}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        disk = os.path.splitdrive(str(self.path.resolve()))[0] + os.sep
        with self.locked():
            return self._append([], {
                "kind": "INIT", "budget_bytes": int(budget_bytes), "reserve_bytes": int(reserve_bytes),
                "owned_roots": [str(Path(root)) for root in roots], "shared_roots": [str(Path(r)) for r in shared],
                "baseline": baseline, "disk": disk, "free_bytes_at_init": shutil.disk_usage(disk).free,
                "note": note,
                "rule": ("admit iff added_now + open_estimates + estimate <= budget and free - open_estimates - "
                         "estimate >= reserve; no re-baseline, no retroactive increase, no deletion")})

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
            stop = self.stopped(rows)
            reasons = []
            if stop:
                reasons.append(f"a bounded stop is recorded (seq {stop['seq']}); no further allocation is admitted")
            if projected > init["budget_bytes"]:
                reasons.append(f"added {state['added_bytes']} + open reservations {pending_bytes} + estimate "
                               f"{estimate_bytes} = {projected} exceeds the budget {init['budget_bytes']}")
            if free_after < init["reserve_bytes"]:
                reasons.append(f"free {state['free_bytes']} - open {pending_bytes} - estimate {estimate_bytes} = "
                               f"{free_after} is below the reserve {init['reserve_bytes']}")
            record = self._append(rows, {
                "kind": "RESERVE", "token": uuid.uuid4().hex, "operation": operation,
                "estimate_bytes": int(estimate_bytes), "added_bytes_before": state["added_bytes"],
                "open_reservations_before": sorted(pending), "open_estimate_bytes_before": pending_bytes,
                "projected_added_bytes": projected, "free_bytes": state["free_bytes"],
                "free_bytes_after_reservations": free_after, "budget_bytes": init["budget_bytes"],
                "reserve_bytes": init["reserve_bytes"], "decision": "REFUSED" if reasons else "ADMITTED",
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
            if state["added_bytes"] > init["budget_bytes"] and not self.stopped(rows):
                self._append(rows, {"kind": "BOUNDED_STOP", "token": token, "operation": opened["operation"],
                                    "added_bytes": state["added_bytes"], "budget_bytes": init["budget_bytes"],
                                    "reason": "the measured total passed the budget; every later reservation is refused"})
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
        return {"ledger": str(self.path), "records": len(rows), "budget_bytes": init["budget_bytes"],
                "reserve_bytes": init["reserve_bytes"], "added_bytes": state["added_bytes"],
                "headroom_bytes": init["budget_bytes"] - state["added_bytes"]
                - sum(int(r["estimate_bytes"]) for r in pending.values()),
                "free_bytes": state["free_bytes"], "open_reservations": {k: {"operation": v["operation"],
                                                                                "estimate_bytes": v["estimate_bytes"],
                                                                                "pid": v["pid"]}
                                                                            for k, v in pending.items()},
                "bounded_stop": self.stopped(rows), "roots": state["roots"],
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
                                 shared=args.shared, note=args.note)
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
