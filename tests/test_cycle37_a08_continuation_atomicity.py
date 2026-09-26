"""Cycle #37 — Attempt #8 — MF37A07-02: one continuation is claimed and initialized once, and a stop or a reserve
change is continued only under a recorded revised plan.

The Attempt 7 manager paused two real callers of ``storage_snapshot.open_successor`` for the *same* absent child just
before its first INIT lock: both had already found the child absent (the check ran outside that lock), both appended
an INIT, one returned OPENED and one ``LedgerError``, the chain broke at line 3 and every later restart refused. The
same review showed a continuation of a stopped ledger, and one opened with a lower reserve, simply admitting.

These cases use byte-sized owned fixtures, each in its own fresh directory, and the real locks and appends -- no
record is written by hand. Scheduling is made deterministic by observing the callers, never by timing: the first
caller is held *inside* the initialization (after its checks), and the second is released only once it is seen
waiting on the parent's lock (its lock poll is observed through the module's own ``time.sleep``).

* positive -- two same-path callers produce one INIT and one resumption, the chain proves, a fresh restart resumes
  without a record, and the root budget, spent and reserved bytes, claim, identity and frozen snapshot are unchanged;
  a claim left by an interrupted open is recovered, and a child interrupted between its INIT and its OPENED record is
  completed, each without a second child or any duplicate headroom; a separately reserved final-output continuation
  still proves; a stopped or reserve-changed ledger continues under a feasible plan, bounded by the plan's ceiling;
* negative -- competing different children, a torn INIT, a head log without its ledger, a resume with other
  parameters, a stale snapshot, a wrong attempt, a truncated child and a stopped or reserve-changed continuation with
  no plan (or with an absent, changed, unanswered or infeasible one) are each refused for their own cause, and the
  budget is never a parameter.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools" / "cycle37"
sys.path.insert(0, str(TOOLS))

import storage_admission as sa  # noqa: E402
import storage_snapshot as ss  # noqa: E402


class _ObservedTime:
    """``storage_admission``'s ``time`` with every sleep of a named thread reported: a thread that sleeps inside
    ``Ledger.locked`` is polling a lock another holder has."""

    def __init__(self, watched: str, waiting: threading.Event) -> None:
        self._watched, self._waiting = watched, waiting

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        if threading.current_thread().name == self._watched:
            self._waiting.set()
        time.sleep(seconds)


class ContinuationAtomicityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.data = self.base / "data"
        self.data.mkdir()
        self.ops = self.base / "ops"
        self.root_path = self.ops / "STORAGE_RESERVATIONS.jsonl"
        self.root = sa.Ledger(self.root_path)
        self.root.init(budget_bytes=1_000_000, reserve_bytes=0, roots=[self.data], cycle_number=37, attempt_number=8)
        self.child_path = self.ops / "SEGMENT_02.jsonl"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ------------------------------------------------------------------ helpers
    def spend(self, ledger: sa.Ledger, name: str, size: int, estimate: int | None = None) -> dict:
        record = ledger.reserve(f"LANE {name}", size if estimate is None else estimate)
        (self.data / name).write_bytes(b"x" * size)
        return ledger.reconcile(record["token"])

    def frozen(self, spent: int = 300_000) -> Path:
        self.spend(self.root, "first", spent)
        path = self.ops / "SNAPSHOT_01.json"
        ss.freeze(self.root_path, path, label="Cycle #37 — Attempt #8 — test", scope="tiny fixture")
        return path

    def open(self, snapshot: Path, path: Path | None = None, **kw) -> dict:
        return ss.open_successor(snapshot, path or self.child_path, [str(self.data)], kind="operational ledger segment",
                                 scope="test continuation", **kw)

    def refused(self, code: str, call, *args, **kw) -> str:
        with self.assertRaises(ss.SnapshotRefused) as caught:
            call(*args, **kw)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        return str(caught.exception)

    def inits(self, path: Path) -> int:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if '"kind": "INIT"' in line)

    def authority(self, text: str = "fixture authority: a revised plan under the unchanged ceiling\n") -> dict:
        path = self.base / "AUTHORITY.md"
        path.write_text(text, encoding="utf-8")
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "grant": "fixture"}

    def plan(self, planned: int, *, reserve: int = 0, stop: dict | None = None, **overrides) -> dict:
        document = {"schema": ss.PLAN_SCHEMA, "authority": self.authority(), "decision": "continue within the plan",
                    "planned_bytes": planned, "reserve_bytes": reserve, "reason": "fixture"}
        if stop is not None:
            document["answers_stop"] = {"seq": stop["seq"], "at": stop["at"]}
        document.update(overrides)
        return document

    def stopped_snapshot(self) -> tuple[Path, dict]:
        """300,000 spent under a 100-byte reservation: the readback stops the ledger (an underestimate far past its
        allowance), and the stopped ledger is frozen."""

        record = self.root.reserve("LANE underestimated", 100)
        (self.data / "big").write_bytes(b"x" * 300_000)
        self.root.reconcile(record["token"])
        stop = self.root.stop(record["token"], "LANE underestimated", "used past its allowance", 300_000)
        path = self.ops / "SNAPSHOT_01.json"
        ss.freeze(self.root_path, path, label="Cycle #37 — Attempt #8 — test", scope="stopped fixture")
        return path, stop

    # ------------------------------------------------------------------ MF37A07-02: the saved same-path race
    def test_two_same_path_callers_initialize_once_and_the_second_resumes(self) -> None:
        snapshot = self.frozen()
        snapshot_bytes, claim_before = snapshot.read_bytes(), self.root.claim_path.exists()
        root_records = self.root.records()
        inside, release, waiting = threading.Event(), threading.Event(), threading.Event()
        original = sa.Ledger.init_continuation

        def held(ledger, **kw):  # the first caller is held inside the initialization, after every check it made
            if threading.current_thread().name == "first":
                inside.set()
                release.wait(timeout=30)
            return original(ledger, **kw)

        results: dict[str, dict] = {}

        def call(name: str) -> None:
            try:
                init = self.open(snapshot)
                results[name] = {"result": "OPENED", "resumed": init["resumed"]}
            except Exception as error:  # noqa: BLE001 - recorded, then asserted
                results[name] = {"result": "REFUSED", "error": f"{type(error).__name__}: {error}"}

        with mock.patch.object(sa.Ledger, "init_continuation", held), \
                mock.patch.object(sa, "time", _ObservedTime("second", waiting)):
            first = threading.Thread(target=call, args=("first",), name="first")
            first.start()
            self.assertTrue(inside.wait(timeout=30), "the first caller never reached the initialization")
            second = threading.Thread(target=call, args=("second",), name="second")
            second.start()
            # Deterministic: the second caller cannot pass the parent's lock while the first holds it.
            self.assertTrue(waiting.wait(timeout=30), "the second caller was not waiting on the parent's lock")
            self.assertFalse(self.child_path.exists() and self.inits(self.child_path) > 1)
            release.set()
            first.join(timeout=60)
            second.join(timeout=60)
        self.assertEqual(results["first"], {"result": "OPENED", "resumed": False})
        self.assertEqual(results["second"], {"result": "OPENED", "resumed": True})
        rows = sa.Ledger(self.child_path).records()
        self.assertEqual([r["kind"] for r in rows], ["INIT", "OPENED"])
        self.assertEqual(ss.chain(self.child_path)["result"], "PASS")
        # A fresh restart resumes the one child without writing a record.
        again = self.open(snapshot)
        self.assertTrue(again["resumed"])
        self.assertEqual(sa.Ledger(self.child_path).records(), rows)
        # Budget, spent bytes, claim, identity and the frozen bytes are exactly as they were.
        status = sa.Ledger(self.child_path).status()
        self.assertEqual((status["budget_bytes"], status["added_bytes"], status["headroom_bytes"]),
                         (1_000_000, 300_000, 700_000))
        self.assertEqual((status["identity"]["cycle_number"], status["identity"]["attempt_number"]), (37, 8))
        self.assertFalse(claim_before)
        self.assertEqual(self.root.claim()["child_ledger"], str(self.child_path))
        self.assertEqual(self.root.records(), root_records)
        self.assertEqual(snapshot.read_bytes(), snapshot_bytes)
        with self.assertRaises(sa.AdmissionRefused):
            sa.Ledger(self.child_path).reserve("LANE past the attempt's budget", 700_001)

    def test_many_concurrent_same_path_callers_leave_one_valid_child(self) -> None:
        snapshot = self.frozen()
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            outcomes = list(pool.map(lambda _: self.open(snapshot)["resumed"], range(6)))
        self.assertEqual(sorted(outcomes), [False] + [True] * 5)
        self.assertEqual(self.inits(self.child_path), 1)
        self.assertEqual(ss.chain(self.child_path)["result"], "PASS")

    def test_competing_different_children_admit_exactly_one(self) -> None:
        snapshot = self.frozen()
        other = self.ops / "SEGMENT_02_OTHER.jsonl"

        def attempt(path: Path) -> str:
            try:
                return "OPENED" if not self.open(snapshot, path)["resumed"] else "RESUMED"
            except ss.SnapshotRefused as refusal:
                return refusal.code

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = sorted(pool.map(attempt, [self.child_path, other]))
        self.assertEqual(outcomes, ["OPENED", ss.REFUSED_CLAIMED])
        opened = [p for p in (self.child_path, other) if p.exists()]
        self.assertEqual(len(opened), 1)
        self.assertEqual(self.inits(opened[0]), 1)

    # ------------------------------------------------------------------ interrupted states
    def test_a_claim_left_by_an_interrupted_open_is_recovered_once(self) -> None:
        snapshot = self.frozen()

        def crash(self, **kw):
            raise KeyboardInterrupt("the process ended after its claim")

        with mock.patch.object(sa.Ledger, "init_continuation", crash):
            with self.assertRaises(KeyboardInterrupt):
                self.open(snapshot)
        self.assertTrue(self.root.claim_path.exists())
        self.assertFalse(self.child_path.exists())
        # Another child cannot take the claimed headroom; the same one recovers the interrupted initialization.
        self.refused(ss.REFUSED_CLAIMED, self.open, snapshot, self.ops / "OTHER.jsonl")
        init = self.open(snapshot)
        self.assertFalse(init["resumed"])
        self.assertTrue(init["continuation"]["recovered_interrupted_claim"])
        self.assertEqual(self.inits(self.child_path), 1)
        self.assertEqual(init["opened"]["headroom_bytes"], 700_000)
        self.assertEqual(ss.chain(self.child_path)["result"], "PASS")

    def test_a_child_interrupted_before_its_opened_record_is_completed_on_resume(self) -> None:
        snapshot = self.frozen()
        with mock.patch.object(ss, "_open_record", side_effect=KeyboardInterrupt("ended after the INIT")):
            with self.assertRaises(KeyboardInterrupt):
                self.open(snapshot)
        self.assertEqual([r["kind"] for r in sa.Ledger(self.child_path).records()], ["INIT"])
        again = self.open(snapshot)
        self.assertEqual((again["resumed"], again["recovered"]), (True, "OPENED_RECORD_COMPLETED_AFTER_INTERRUPTION"))
        rows = sa.Ledger(self.child_path).records()
        self.assertEqual([r["kind"] for r in rows], ["INIT", "OPENED"])
        self.assertTrue(rows[1]["completed_after_interruption"])
        self.assertEqual(rows[1]["headroom_bytes"], 700_000)
        self.assertTrue(self.open(snapshot)["resumed"])
        self.assertEqual(len(sa.Ledger(self.child_path).records()), 2)

    def test_a_torn_init_or_a_head_log_without_its_ledger_is_refused_as_interrupted(self) -> None:
        snapshot = self.frozen()
        original = sa.Ledger._append

        def torn(self, rows, record):
            if not rows and self.path.name == "SEGMENT_02.jsonl":
                line = json.dumps({"seq": 1, **record}, sort_keys=True)
                with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(line[: len(line) // 2])        # the process ends in the middle of the INIT line
                raise KeyboardInterrupt("ended while writing the INIT")
            return original(self, rows, record)

        with mock.patch.object(sa.Ledger, "_append", torn):
            with self.assertRaises(KeyboardInterrupt):
                self.open(snapshot)
        torn_bytes = self.child_path.read_bytes()
        self.refused(ss.REFUSED_INIT_INTERRUPTED, self.open, snapshot)
        self.assertEqual(self.child_path.read_bytes(), torn_bytes)          # nothing appended, nothing rewritten
        self.refused(ss.REFUSED_CLAIMED, self.open, snapshot, self.ops / "OTHER.jsonl")   # no second child either
        with self.assertRaises(sa.LedgerError) as caught:
            sa.Ledger(self.child_path).records()
        self.assertIn("incomplete", str(caught.exception))
        # A head log whose ledger is gone is an interrupted or removed initialization, never a fresh start.
        orphan = self.ops / "ORPHAN.jsonl"
        Path(str(orphan) + sa.HEAD_SUFFIX).write_text('{"record_sha256": "x", "seq": 3}\n', encoding="utf-8")
        with self.assertRaises(sa.LedgerError):
            sa.Ledger(orphan).init_continuation(parent=self.root, parent_rows=self.root.records(), new_roots=[],
                                                new_shared=[], reserve_bytes=None, continuation={})
        self.assertFalse(orphan.exists())

    def test_a_resume_with_other_parameters_is_refused(self) -> None:
        snapshot = self.frozen()
        self.open(snapshot)
        records = sa.Ledger(self.child_path).records()
        self.refused(ss.REFUSED_PARAMETERS, self.open, snapshot, reserve_bytes=1)
        self.refused(ss.REFUSED_PARAMETERS, ss.open_successor, snapshot, self.child_path, [str(self.data)],
                     kind="another kind", scope="test continuation")
        self.refused(ss.REFUSED_PARAMETERS, self.open, snapshot, revised_plan=self.plan(1_000))
        self.assertEqual(sa.Ledger(self.child_path).records(), records)

    def test_a_truncated_child_is_refused_on_resume_and_by_the_chain(self) -> None:
        snapshot = self.frozen()
        self.open(snapshot)
        self.spend(sa.Ledger(self.child_path), "second", 1_000)
        lines = self.child_path.read_text(encoding="utf-8").splitlines(keepends=True)
        self.child_path.write_text("".join(lines[:-1]), encoding="utf-8")   # cut the last record
        self.refused(ss.REFUSED_CLAIM_INVALID, self.open, snapshot)
        self.refused(ss.REFUSED_LEDGER, ss.chain, self.child_path)

    def test_a_stale_snapshot_or_a_wrong_attempt_is_refused(self) -> None:
        snapshot = self.frozen()
        self.refused(ss.REFUSED_WRONG_ATTEMPT, self.open, snapshot, attempt_number=7)
        self.assertFalse(self.root.claim_path.exists())
        self.root.reserve("LANE after the freeze", 1)          # the ledger went on: the snapshot is stale
        self.refused(ss.REFUSED_POST_SNAPSHOT, self.open, snapshot)
        self.assertFalse(self.child_path.exists())

    def test_a_final_output_continuation_is_still_accounted_separately(self) -> None:
        snapshot = self.frozen()
        final = self.ops / "FINAL.jsonl"
        init = ss.open_final(snapshot, final, [str(self.data)], cycle_number=37, attempt_number=8)
        self.assertEqual((init["opened"]["headroom_bytes"], init["revised_plan"], init["plan_ceiling_bytes"]),
                         (700_000, None, None))
        ledger = sa.Ledger(final)
        self.spend(ledger, "final-output", 2_000)
        self.assertEqual(ledger.status()["headroom_bytes"], 698_000)
        proof = ss.chain(final)
        self.assertEqual((proof["result"], [s["segment"] for s in proof["segments"]]), ("PASS", [1, 2]))

    # ------------------------------------------------------------------ a stop or a reserve change needs a decision
    def test_a_stopped_ledger_is_continued_only_under_a_feasible_revised_plan(self) -> None:
        snapshot, stop = self.stopped_snapshot()
        # No decision: refused before any claim or child exists.
        self.refused(ss.REFUSED_PLAN_REQUIRED, self.open, snapshot)
        self.assertFalse(self.root.claim_path.exists() or self.child_path.exists())
        # Absent, changed, unanswered, infeasible or mis-reserved plans are refused for their own cause.
        absent = self.plan(10_000, stop=stop)
        absent["authority"] = {"path": str(self.base / "NO_SUCH_AUTHORITY.md"), "sha256": "0" * 64}
        for bad, text in ((absent, "does not exist"),
                          ({**self.plan(10_000, stop=stop), "authority": {**self.authority(), "sha256": "1" * 64}},
                           "no longer hashes"),
                          (self.plan(10_000, stop={"seq": 99, "at": "never"}), "does not answer the stop"),
                          (self.plan(10_000), "does not answer the stop"),
                          (self.plan(700_001, stop=stop), "exceeds the unchanged budget"),
                          (self.plan(10_000, stop=stop, reserve=5), "not the requested"),
                          (self.plan(0, stop=stop), "not a positive byte count"),
                          ({"schema": "something else"}, ss.PLAN_SCHEMA)):
            self.assertIn(text, self.refused(ss.REFUSED_PLAN_INVALID, self.open, snapshot, revised_plan=bad))
        self.assertFalse(self.root.claim_path.exists() or self.child_path.exists())
        # A feasible plan: the budget is the root's, the plan's ceiling bounds the continuation.
        init = self.open(snapshot, revised_plan=self.plan(10_000, stop=stop))
        self.assertEqual((init["budget_bytes"], init["plan_ceiling_bytes"], init["opened"]["headroom_bytes"]),
                         (1_000_000, 310_000, 10_000))
        self.assertEqual(init["inherited_stop"]["seq"], stop["seq"])
        child = sa.Ledger(self.child_path)
        with self.assertRaises(sa.AdmissionRefused) as caught:
            child.reserve("LANE within the budget but past the plan", 10_001)
        self.assertIn("revised plan's ceiling", caught.exception.record["reason"])
        self.spend(child, "within-plan", 4_000, 5_000)
        # A readback past the plan's ceiling stops the continuation (never past the budget).
        record = child.reserve("LANE underestimated again", 1_000)
        (self.data / "past-plan").write_bytes(b"x" * 7_000)
        child.reconcile(record["token"])
        self.assertIn("revised plan's ceiling", child.stopped(child.records())["reason"])
        with self.assertRaises(sa.AdmissionRefused):
            child.reserve("LANE after the second stop", 1)
        proof = ss.chain(self.child_path)
        self.assertEqual((proof["result"], proof["segments"][1]["revised_plan"]["ceiling_bytes"]), ("PASS", 310_000))

    def test_a_continuation_of_an_answered_stop_inherits_the_plan_ceiling(self) -> None:
        snapshot, stop = self.stopped_snapshot()
        self.open(snapshot, revised_plan=self.plan(10_000, stop=stop))
        child = sa.Ledger(self.child_path)
        self.spend(child, "within-plan", 1_000)
        second = self.ops / "SNAPSHOT_02.json"
        ss.freeze(self.child_path, second, label="Cycle #37 — Attempt #8 — test", scope="answered stop")
        final = self.ops / "FINAL.jsonl"
        init = ss.open_final(second, final, [str(self.data)])                 # the plan answered the stop
        self.assertEqual((init["inherited_stop"], init["plan_ceiling_bytes"], init["opened"]["headroom_bytes"]),
                         (None, 310_000, 9_000))
        with self.assertRaises(sa.AdmissionRefused):
            sa.Ledger(final).reserve("LANE past the inherited plan", 9_001)
        self.assertEqual(ss.chain(final)["result"], "PASS")

    def test_a_reserve_change_is_continued_only_under_a_revised_plan(self) -> None:
        snapshot = self.frozen()
        for reserve in (0 + 1, 2**40):                          # lowered or raised: any change is a decision
            self.refused(ss.REFUSED_PLAN_REQUIRED, self.open, snapshot, reserve_bytes=reserve)
        self.assertFalse(self.root.claim_path.exists())
        init = self.open(snapshot, reserve_bytes=1, revised_plan=self.plan(50_000, reserve=1))
        self.assertEqual((init["reserve_bytes"], init["budget_bytes"], init["plan_ceiling_bytes"]),
                         (1, 1_000_000, 350_000))
        self.assertEqual(ss.chain(self.child_path)["result"], "PASS")

    def test_the_managers_stop_and_reserve_cases_no_longer_admit_without_a_decision(self) -> None:
        """The Attempt 7 manager's storage_independent cases, restated: a bounded stop recorded before the freeze, and
        an impossible reserve lowered through the public continuation parameter."""

        self.spend(self.root, "initial", 300_000)
        self.root.stop("", "underrun fixture", "Operation exceeded its individual admitted allowance", 300_000)
        snapshot = self.ops / "S1.json"
        ss.freeze(self.root_path, snapshot, label="Cycle #37 — Attempt #8 — test", scope="stop")
        self.refused(ss.REFUSED_PLAN_REQUIRED, self.open, snapshot)
        other = self.base / "other"
        other_data = other / "data"
        other_data.mkdir(parents=True)
        floor = sa.Ledger(other / "root.jsonl")
        floor.init(budget_bytes=1_000_000, reserve_bytes=2**63, roots=[other_data], cycle_number=37, attempt_number=8)
        floor_snapshot = other / "S.json"
        ss.freeze(floor.path, floor_snapshot, label="Cycle #37 — Attempt #8 — test", scope="floor")
        self.refused(ss.REFUSED_PLAN_REQUIRED, ss.open_successor, floor_snapshot, other / "child.jsonl",
                     [str(other_data)], kind="manager test", scope="isolated", reserve_bytes=0)
        # Inheriting the impossible floor is not a change; it opens and its reservations are refused by the floor.
        ss.open_successor(floor_snapshot, other / "child.jsonl", [str(other_data)], kind="manager test", scope="isolated")
        with self.assertRaises(sa.AdmissionRefused) as caught:
            sa.Ledger(other / "child.jsonl").reserve("challenged allocation", 10_000)
        self.assertIn("below the reserve", caught.exception.record["reason"])

    def test_the_budget_is_never_a_continuation_parameter(self) -> None:
        for call in (ss.open_successor, ss.open_final, sa.Ledger.init_continuation):
            self.assertNotIn("budget_bytes", call.__code__.co_varnames[:call.__code__.co_argcount
                                                                       + call.__code__.co_kwonlyargcount])


if __name__ == "__main__":
    unittest.main()
