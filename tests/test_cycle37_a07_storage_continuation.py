"""Cycle #37 — Attempt #7 — MF37A06-02: one attempt-wide storage ledger across segments, freezes and restarts.

The Attempt 6 manager budgeted 1,000,000 bytes, spent 300,000 and froze the ledger (700,000 headroom); a first
continuation spent 600,000 and correctly refused 200,000 more; a second continuation opened from the same unchanged
snapshot took a fresh baseline and admitted the 200,000 -- 1,100,000 projected against 1,000,000. These cases run
``tools/cycle37/storage_admission.py`` and ``storage_snapshot.py`` on byte-sized owned fixtures, each in its own
fresh directory:

* positive -- a continuation and a fresh-process restart keep the attempt's cumulative spent and reserved bytes, its
  root identity, parent linkage and cycle/attempt; the frozen snapshot stays byte-stable while the continuation
  works; the same continuation opened again resumes without a record; a final-output continuation is accounted
  separately and the whole chain proves;
* negative -- the saved replay, concurrent competing continuations (separate processes), a wrong cycle/attempt, a
  root that is not empty or not inherited, growth after the freeze, a truncated or rewritten ledger, a tampered claim
  or snapshot, a snapshot with an open reservation or with work after it, and a stale parent are each refused (or,
  for growth, counted) for their own cause, and none admits duplicate headroom.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools" / "cycle37"
sys.path.insert(0, str(TOOLS))

import storage_admission as sa  # noqa: E402
import storage_snapshot as ss  # noqa: E402


class StorageContinuationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.data = self.base / "data"
        self.data.mkdir()
        self.ops = self.base / "ops"
        self.root_path = self.ops / "STORAGE_RESERVATIONS.jsonl"
        self.root = sa.Ledger(self.root_path)
        self.root.init(budget_bytes=1_000_000, reserve_bytes=0, roots=[self.data], cycle_number=37, attempt_number=7)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ------------------------------------------------------------------ helpers
    def spend(self, ledger: sa.Ledger, name: str, size: int, estimate: int | None = None) -> dict:
        record = ledger.reserve(f"LANE {name}", size if estimate is None else estimate)
        (self.data / name).write_bytes(b"x" * size)
        return ledger.reconcile(record["token"])

    def freeze(self, ledger: sa.Ledger, name: str) -> Path:
        path = self.ops / name
        ss.freeze(ledger.path, path, label="Cycle #37 — Attempt #7 — test", scope="tiny fixture")
        return path

    def continuation(self, snapshot: Path, name: str, **kw) -> tuple[sa.Ledger, dict]:
        path = self.ops / name
        init = ss.open_successor(snapshot, path, [str(self.data)], kind="operational ledger segment",
                                 scope="test continuation", **kw)
        return sa.Ledger(path), init

    def refused(self, code: str, call, *args, **kw) -> str:
        with self.assertRaises(ss.SnapshotRefused) as caught:
            call(*args, **kw)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        return str(caught.exception)

    def frozen_300k(self) -> Path:
        self.spend(self.root, "first", 300_000)
        return self.freeze(self.root, "SNAPSHOT_01.json")

    # ------------------------------------------------------------------ positive
    def test_a_continuation_and_a_fresh_process_restart_keep_the_cumulative_state(self) -> None:
        snapshot = self.frozen_300k()
        before = snapshot.read_bytes()
        child, init = self.continuation(snapshot, "SEGMENT_02.jsonl", cycle_number=37, attempt_number=7)
        root_line = self.root.lines()[0]
        self.assertEqual((init["budget_bytes"], init["segment"], init["opened"]["headroom_bytes"],
                          init["opened"]["added_bytes"]), (1_000_000, 2, 700_000, 300_000))
        self.assertEqual(init["root"], {"ledger": str(self.root_path), "init_record_sha256": sa._digest(root_line)})
        self.assertEqual(init["identity"], {"cycle_number": 37, "attempt_number": 7, "source": "INHERITED_FROM_ROOT"})
        self.assertEqual(init["baseline"], self.root.config(self.root.records())["baseline"])
        self.assertEqual(init["continuation"]["snapshot_content_sha256"], ss.load_snapshot(snapshot)["content_sha256"])
        self.assertEqual(init["continuation"]["claim"]["sha256"], self.root.claim()["_sha256"])
        self.spend(child, "second", 600_000)
        with self.assertRaises(sa.AdmissionRefused):
            child.reserve("LANE past the attempt's budget", 200_000)
        open_one = child.reserve("LANE left open by a restart", 50_000, explicit=True)
        # A fresh process sees the same cumulative state: every byte spent, the open reservation, the identity.
        probe = (f"import sys, json; sys.path.insert(0, {str(TOOLS)!r}); import storage_admission as sa; "
                 f"print(json.dumps(sa.Ledger({str(child.path)!r}).status(), default=str))")
        status = json.loads(subprocess.run([sys.executable, "-B", "-c", probe], capture_output=True, text=True,
                                           check=True).stdout)
        self.assertEqual((status["added_bytes"], status["headroom_bytes"], status["segment"]), (900_000, 50_000, 2))
        self.assertEqual(list(status["open_reservations"]), [open_one["token"]])
        self.assertEqual((status["identity"]["cycle_number"], status["identity"]["attempt_number"]), (37, 7))
        self.assertEqual({(r["cycle_number"], r["attempt_number"]) for r in child.records() + self.root.records()},
                         {(37, 7)})
        child.reconcile(open_one["token"])
        # The frozen snapshot is byte-stable and still proves its ledger with nothing after it.
        self.assertEqual(snapshot.read_bytes(), before)
        verdict = ss.verify(self.root_path, snapshot)
        self.assertEqual((verdict["result"], verdict["post_snapshot_records"]), ("PASS", 0))

    def test_opening_the_same_continuation_again_resumes_it_without_a_record(self) -> None:
        snapshot = self.frozen_300k()
        child, first = self.continuation(snapshot, "SEGMENT_02.jsonl")
        self.spend(child, "second", 100_000)
        records = child.records()
        claim = self.root.claim_path.read_bytes()
        again = ss.open_successor(snapshot, child.path, [str(self.data)], kind="operational ledger segment",
                                  scope="a restart asks again")
        self.assertTrue(again["resumed"])
        self.assertEqual(child.records(), records)
        self.assertEqual(self.root.claim_path.read_bytes(), claim)
        self.assertEqual(child.status()["added_bytes"], 400_000)

    def test_a_final_output_continuation_is_accounted_separately_and_the_chain_proves(self) -> None:
        snapshot = self.frozen_300k()
        child, _ = self.continuation(snapshot, "SEGMENT_02.jsonl")
        self.spend(child, "second", 200_000)
        final_snapshot = self.freeze(child, "STORAGE_EVIDENCE_SNAPSHOT.json")
        sealed = final_snapshot.read_bytes()
        outputs = self.base / "outputs"
        final_path = self.ops / "STORAGE_RESERVATIONS_FINAL_OUTPUT.jsonl"
        init = ss.open_final(final_snapshot, final_path, [str(outputs)], cycle_number=37, attempt_number=7)
        self.assertEqual((init["opened"]["headroom_bytes"], init["segment"]), (500_000, 3))
        final = sa.Ledger(final_path)
        record = final.reserve("FINAL-OUT packet", 4_000)
        outputs.mkdir()
        (outputs / "submission.json").write_bytes(b"{}" * 1_000)
        final.reconcile(record["token"])
        self.assertEqual(final.status()["headroom_bytes"], 498_000)
        proof = ss.chain(final_path)
        self.assertEqual([s["segment"] for s in proof["segments"]], [1, 2, 3])
        self.assertEqual([s["open_reservations"] for s in proof["segments"]], [[], [], []])
        self.assertEqual(proof["root"], str(self.root_path))
        self.assertEqual(final_snapshot.read_bytes(), sealed)
        self.assertEqual(ss.verify(child.path, final_snapshot)["post_snapshot_records"], 0)

    # ------------------------------------------------------------------ negative
    def test_the_managers_replay_of_one_snapshot_is_refused_and_admits_no_duplicate_headroom(self) -> None:
        snapshot = self.frozen_300k()
        first, _ = self.continuation(snapshot, "child.jsonl")
        self.spend(first, "second", 600_000)
        with self.assertRaises(sa.AdmissionRefused):
            first.reserve("EXCEEDS_REMAINING", 200_000)
        message = self.refused(ss.REFUSED_CLAIMED, self.continuation, snapshot, "replayed-child.jsonl")
        self.assertIn("child.jsonl", message)
        self.assertFalse((self.ops / "replayed-child.jsonl").exists())
        # Whatever else is tried, nothing admits past the attempt's 1,000,000 bytes.
        with self.assertRaises(sa.AdmissionRefused):
            first.reserve("still past the budget", 100_001)
        with self.assertRaises(sa.AdmissionRefused):
            self.root.reserve("the frozen, continued root", 1)

    def test_concurrent_competing_continuations_admit_exactly_one(self) -> None:
        snapshot = self.frozen_300k()
        script = textwrap.dedent(f"""
            import json, sys, time
            sys.path.insert(0, {str(TOOLS)!r})
            import storage_snapshot as ss
            while time.time() < float(sys.argv[2]):
                pass
            try:
                ss.open_successor({str(snapshot)!r}, sys.argv[1], [{str(self.data)!r}], kind="race", scope="race")
                print("OPENED")
            except ss.SnapshotRefused as refused:
                print(refused.code)
        """)
        import time
        start = str(time.time() + 3)
        processes = [subprocess.Popen([sys.executable, "-B", "-c", script, str(self.ops / f"racer{i}.jsonl"), start],
                                      stdout=subprocess.PIPE, text=True) for i in range(4)]
        results = [p.communicate(timeout=120)[0].strip() for p in processes]
        self.assertEqual(sorted(results), ["OPENED"] + [ss.REFUSED_CLAIMED] * 3, results)
        winner = [i for i, r in enumerate(results) if r == "OPENED"][0]
        self.assertTrue(sa._same_path(self.root.claim()["child_ledger"], self.ops / f"racer{winner}.jsonl"))
        self.assertEqual(sorted(p.name for p in self.ops.glob("racer?.jsonl")), [f"racer{winner}.jsonl"])

    def test_a_wrong_cycle_or_attempt_is_refused_and_claims_nothing(self) -> None:
        snapshot = self.frozen_300k()
        self.refused(ss.REFUSED_WRONG_ATTEMPT, self.continuation, snapshot, "a6.jsonl", cycle_number=37,
                     attempt_number=6)
        self.refused(ss.REFUSED_WRONG_ATTEMPT, self.continuation, snapshot, "c38.jsonl", cycle_number=38,
                     attempt_number=7)
        self.assertIsNone(self.root.claim())
        child, _ = self.continuation(snapshot, "SEGMENT_02.jsonl", cycle_number=37, attempt_number=7)
        self.assertEqual(child.status()["identity"]["attempt_number"], 7)

    def test_a_root_that_is_not_empty_is_refused_and_every_parent_root_is_inherited(self) -> None:
        snapshot = self.frozen_300k()
        elsewhere = self.base / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "hidden.bin").write_bytes(b"h" * 5_000)
        path = self.ops / "wrong-root.jsonl"
        self.refused(ss.REFUSED_ROOT, ss.open_successor, snapshot, path, [str(elsewhere)], kind="k", scope="s")
        self.assertIsNone(self.root.claim())
        # Naming only a new empty root still inherits the parent's root: nothing escapes measurement.
        fresh = self.base / "fresh"
        init = ss.open_successor(snapshot, path, [str(fresh)], kind="k", scope="s")
        self.assertEqual(sorted(init["baseline"]), sorted([str(self.data), str(fresh)]))
        self.assertEqual(init["opened"]["added_bytes"], 300_000)

    def test_growth_after_the_freeze_is_counted_not_reset(self) -> None:
        snapshot = self.frozen_300k()
        (self.data / "unreserved.bin").write_bytes(b"u" * 250_000)       # written between freeze and continuation
        child, init = self.continuation(snapshot, "SEGMENT_02.jsonl")
        self.assertEqual((init["opened"]["unreserved_growth_bytes"], init["opened"]["headroom_bytes"]),
                         (250_000, 450_000))
        self.assertEqual([r["kind"] for r in child.records()], ["INIT", "OPENED", "UNRESERVED_GROWTH"])
        with self.assertRaises(sa.AdmissionRefused):
            child.reserve("the old headroom", 700_000)
        child.reserve("what is actually left", 450_000)

    def test_a_continuation_that_opens_past_the_budget_is_stopped(self) -> None:
        snapshot = self.frozen_300k()
        (self.data / "overflow.bin").write_bytes(b"o" * 800_000)
        child, init = self.continuation(snapshot, "SEGMENT_02.jsonl")
        self.assertEqual(child.stopped(child.records())["operation"], "OPEN operational ledger segment")
        with self.assertRaises(sa.AdmissionRefused):
            child.reserve("anything", 1)

    def test_a_truncated_or_rewritten_ledger_is_refused(self) -> None:
        snapshot = self.frozen_300k()
        child, _ = self.continuation(snapshot, "SEGMENT_02.jsonl")
        held = child.reserve("LANE open", 10_000)
        lines = child.path.read_text(encoding="utf-8").splitlines()
        child.path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")      # the open reservation cut off
        with self.assertRaises(sa.LedgerError):
            child.records()
        with self.assertRaises(sa.LedgerError):
            child.reserve("would forget the cut reservation", 600_000)
        self.assertTrue(held["token"])
        # The frozen parent's ledger cut short: its snapshot no longer proves it, so no continuation opens from it.
        other = self.base / "other"
        other_ledger = sa.Ledger(other / "L.jsonl")
        other_ledger.init(budget_bytes=1_000, reserve_bytes=0, roots=[other / "d"], cycle_number=37, attempt_number=7)
        record = other_ledger.reserve("LANE x", 10)
        other_ledger.reconcile(record["token"])
        frozen = other / "S.json"
        ss.freeze(other_ledger.path, frozen, label="t", scope="t")
        kept = other_ledger.path.read_text(encoding="utf-8").splitlines()[:-1]
        other_ledger.path.write_text("\n".join(kept) + "\n", encoding="utf-8")
        with self.assertRaises(ss.SnapshotRefused):
            ss.open_successor(frozen, other / "C.jsonl", [str(other / "d")], kind="k", scope="s")

    def test_a_tampered_claim_or_snapshot_is_refused(self) -> None:
        snapshot = self.frozen_300k()
        child, _ = self.continuation(snapshot, "SEGMENT_02.jsonl")
        claim = json.loads(self.root.claim_path.read_text(encoding="utf-8"))
        claim["child_ledger"] = str(self.ops / "someone-else.jsonl")
        self.root.claim_path.write_text(json.dumps(claim), encoding="utf-8")
        with self.assertRaises(sa.AdmissionRefused) as caught:
            child.reserve("LANE after the claim was changed", 1)
        self.assertIn("claim", caught.exception.record["reason"])
        self.refused(ss.REFUSED_CLAIM_INVALID, ss.chain, child.path)
        # A snapshot re-sealed with more headroom gains nothing: the budget is the root's, never the snapshot's.
        fresh = StorageContinuationTests("test_a_tampered_claim_or_snapshot_is_refused")
        fresh.setUp()
        try:
            snap = fresh.frozen_300k()
            document = json.loads(snap.read_text(encoding="utf-8"))
            document["measured"]["headroom_bytes"] = 5_000_000
            tampered = fresh.ops / "TAMPERED.json"
            tampered.write_text(json.dumps(document), encoding="utf-8")
            fresh.refused(ss.REFUSED_TAMPERED, ss.open_successor, tampered, fresh.ops / "t.jsonl", [str(fresh.data)],
                          kind="k", scope="s")
            document["content_sha256"] = ss._content_digest(document)            # re-sealed as a forger would
            tampered.write_text(json.dumps(document), encoding="utf-8")
            init = ss.open_successor(tampered, fresh.ops / "t.jsonl", [str(fresh.data)], kind="k", scope="s")
            self.assertEqual((init["budget_bytes"], init["opened"]["headroom_bytes"]), (1_000_000, 700_000))
            with self.assertRaises(sa.AdmissionRefused):
                sa.Ledger(fresh.ops / "t.jsonl").reserve("the forged headroom", 700_001)
        finally:
            fresh.tearDown()

    def test_a_snapshot_with_an_open_reservation_or_later_work_cannot_be_continued(self) -> None:
        self.spend(self.root, "first", 300_000)
        held = self.root.reserve("LANE open", 1_000)
        with self.assertRaises(ss.SnapshotRefused):
            self.freeze(self.root, "S.json")
        self.root.reconcile(held["token"])
        snapshot = self.freeze(self.root, "S.json")
        self.spend(self.root, "after-the-freeze", 10)                    # the snapshot is now stale
        self.refused(ss.REFUSED_POST_SNAPSHOT, self.continuation, snapshot, "stale.jsonl")
        self.assertIsNone(self.root.claim())

    def test_a_stale_parent_or_a_forked_segment_is_refused(self) -> None:
        s1 = self.frozen_300k()
        child, _ = self.continuation(s1, "SEGMENT_02.jsonl")
        self.spend(child, "second", 100_000)
        s2 = self.freeze(child, "SNAPSHOT_02.json")
        grandchild, init = self.continuation(s2, "SEGMENT_03.jsonl")
        self.assertEqual((init["segment"], init["opened"]["headroom_bytes"]), (3, 600_000))
        # The first snapshot is stale twice over: its ledger was continued, and so was that continuation.
        self.refused(ss.REFUSED_CLAIMED, self.continuation, s1, "from-s1-again.jsonl")
        for stale in (self.root, child):
            with self.assertRaises(sa.AdmissionRefused):
                stale.reserve("LANE on a continued segment", 1)
        # A hand-made copy of the live segment's INIT is not the claimed continuation, so it admits nothing.
        fork = sa.Ledger(self.ops / "fork.jsonl")
        fork.path.write_text(grandchild.lines()[0] + "\n", encoding="utf-8")
        with self.assertRaises(sa.AdmissionRefused) as caught:
            fork.reserve("LANE on a forked segment", 1)
        self.assertIn("names", caught.exception.record["reason"])
        proof = ss.chain(grandchild.path)
        self.assertEqual(([s["segment"] for s in proof["segments"]], proof["identity"]["attempt_number"]), ([1, 2, 3], 7))
        # The refused attempts on the stale segments are recorded after their freezes and reported, admitting nothing.
        self.assertEqual([s["refused_after_its_freeze"] for s in proof["segments"]], [1, 1, None])
        self.refused(ss.REFUSED_POST_SNAPSHOT, ss.verify, self.root_path, s1)
        grandchild.reserve("LANE the live segment", 600_000)

    def test_a_ledger_without_a_named_identity_says_so_and_records_never_use_a_stale_constant(self) -> None:
        other = sa.Ledger(self.base / "unnamed" / "L.jsonl")
        init = other.init(budget_bytes=100, reserve_bytes=0, roots=[self.base / "unnamed-root"])
        self.assertEqual(init["identity"]["source"], "TOOL_DEFAULT")
        self.assertEqual((init["cycle_number"], init["attempt_number"]), (sa.CYCLE_NUMBER, sa.ATTEMPT_NUMBER))
        with self.assertRaises(sa.LedgerError):
            sa.Ledger(self.base / "half" / "L.jsonl").init(budget_bytes=1, reserve_bytes=0, roots=[self.base / "h"],
                                                           cycle_number=37)
        named = sa.Ledger(self.base / "named" / "L.jsonl")
        named.init(budget_bytes=100, reserve_bytes=0, roots=[self.base / "named-root"], cycle_number=37,
                   attempt_number=9)
        named.reconcile(named.reserve("x", 1)["token"])
        self.assertEqual({r["attempt_number"] for r in named.records()}, {9})


if __name__ == "__main__":
    unittest.main()
