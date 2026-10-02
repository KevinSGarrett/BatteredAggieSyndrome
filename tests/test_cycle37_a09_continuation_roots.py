"""Cycle #37 — Attempt #9 — MF37A08-02: a continuation is opened, resumed and recovered only under its effective roots.

The Attempt 8 manager opened one child from twelve separate processes (one INIT, a valid chain: the race was repaired),
then called the same child again naming an additional empty root through the public ``roots`` argument. It returned
``resumed=True`` without recording or refusing the root, and 10,000 bytes written there measured as zero added bytes:
``_resume`` compared the reserve, plan and kind, never the roots.

These cases use byte-sized owned fixtures, each in its own fresh directory, the real locks and appends (no record is
written by hand) and, for concurrency, separate processes whose outcomes are observed, never timed:

* positive -- the same effective roots in any spelling (case, separators, ``.``/``..``, a trailing separator, order,
  duplicates), owned and shared, resume without a record; twelve processes naming one contract in different spellings
  leave one INIT and a proved chain; growth in every tracked root stays charged; nothing is re-baselined;
* negative -- the saved additional-empty-root restart, a nonempty added root, an omitted added root, a root moved
  between the owned and shared classes (at first open and on restart), a root named in both, a changed shared set,
  processes racing with competing root sets, and the completion of an interrupted claim or INIT under other roots are
  each refused with ``REFUSED_CONTINUATION_ROOT_CONTRACT_DIFFERS`` before any record, claim or baseline changes; no
  refused call adds headroom or raises the ceiling.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools" / "cycle37"
sys.path.insert(0, str(TOOLS))

import storage_admission as sa  # noqa: E402
import storage_snapshot as ss  # noqa: E402

#: The v4 refusal and root spelling, spelled out (not read from the module) so this suite also runs, and fails for
#: what the tool does, over the unfixed base's bytes.
REFUSED_ROOTS = "REFUSED_CONTINUATION_ROOT_CONTRACT_DIFFERS"


def norm(path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def recorded_owned(path: Path) -> list[str]:
    ledger = sa.Ledger(path)
    return sorted({norm(r) for r in ledger.config(ledger.records()).get("owned_roots") or []})

#: One caller in its own process: opens (or resumes) the child with the roots it is given, prints its outcome.
CALLER = r"""
import json, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import storage_snapshot as ss
snapshot, child, roots = sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
try:
    result = ss.open_successor(snapshot, child, roots, kind="operational ledger segment", scope="process caller")
    print(json.dumps({"result": "OPENED", "resumed": result["resumed"]}))
except ss.SnapshotRefused as refusal:
    print(json.dumps({"result": "REFUSED", "code": refusal.code}))
"""


class ContinuationRootContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.data = self.base / "data"
        self.data.mkdir()
        self.shared = self.base / "shared"
        self.shared.mkdir()
        self.ops = self.base / "ops"
        self.root_path = self.ops / "STORAGE_RESERVATIONS.jsonl"
        self.root = sa.Ledger(self.root_path)
        self.root.init(budget_bytes=1_000_000, reserve_bytes=0, roots=[self.data], shared=[self.shared],
                       cycle_number=37, attempt_number=9)
        self.child_path = self.ops / "SEGMENT_02.jsonl"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ------------------------------------------------------------------ helpers
    def frozen(self, spent: int = 300_000) -> Path:
        record = self.root.reserve("LANE first", spent)
        (self.data / "first").write_bytes(b"x" * spent)
        self.root.reconcile(record["token"])
        path = self.ops / "SNAPSHOT_01.json"
        ss.freeze(self.root_path, path, label="Cycle #37 — Attempt #9 — test", scope="tiny fixture")
        return path

    def open(self, snapshot: Path, roots=None, shared=(), path: Path | None = None) -> dict:
        return ss.open_successor(snapshot, path or self.child_path, [str(self.data)] if roots is None else roots,
                                 kind="operational ledger segment", scope="test continuation", shared=list(shared))

    def refused(self, code: str, call, *args, **kw) -> str:
        with self.assertRaises(ss.SnapshotRefused) as caught:
            call(*args, **kw)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        return str(caught.exception)

    def state(self) -> dict:
        """What a refused call must leave unchanged: the child's and the root's bytes, the claim, and the child's
        budget, baseline, roots and headroom."""

        child = sa.Ledger(self.child_path)
        status = child.status() if self.child_path.exists() else None
        return {"child": self.child_path.read_bytes() if self.child_path.exists() else None,
                "root": self.root_path.read_bytes(),
                "claim": self.root.claim_path.read_bytes() if self.root.claim_path.exists() else None,
                "budget": status and status["budget_bytes"], "headroom": status and status["headroom_bytes"],
                "roots": status and sorted(status["roots"])}

    def spellings(self, path: Path) -> list[str]:
        text = str(path)
        return [text, text.upper() if os.name == "nt" else text, text + os.sep, str(path.parent / "." / path.name),
                str(path.parent / "sub" / ".." / path.name), text.replace("\\", "/")]

    def processes(self, snapshot: Path, root_sets: list[list[str]]) -> list[dict]:
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        def call(roots: list[str]) -> dict:
            completed = subprocess.run([sys.executable, "-B", "-c", CALLER, str(TOOLS), str(snapshot),
                                        str(self.child_path), json.dumps(roots)], capture_output=True, text=True,
                                       env=env, timeout=120)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return {**json.loads(completed.stdout.strip().splitlines()[-1]), "roots": roots}

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(root_sets)) as pool:
            return list(pool.map(call, root_sets))

    # ------------------------------------------------------------------ same effective roots resume
    def test_the_same_roots_in_any_spelling_order_or_repetition_resume_without_a_record(self) -> None:
        snapshot = self.frozen()
        self.assertFalse(self.open(snapshot)["resumed"])
        records = len(sa.Ledger(self.child_path).records())
        for spelling in self.spellings(self.data):
            with self.subTest(spelling=spelling):
                self.assertTrue(self.open(snapshot, [spelling, spelling, str(self.data)])["resumed"])
        self.assertTrue(self.open(snapshot, [], [str(self.shared).upper() if os.name == "nt" else str(self.shared)])
                        ["resumed"])
        self.assertEqual(len(sa.Ledger(self.child_path).records()), records)

    def test_an_added_root_resumes_in_any_spelling_and_its_growth_is_charged(self) -> None:
        snapshot = self.frozen()
        extra = self.base / "extra"
        extra.mkdir()
        opened = self.open(snapshot, [str(self.data), str(extra)])
        self.assertIn(str(extra), opened["owned_roots"])
        self.assertTrue(self.open(snapshot, [str(extra) + os.sep, str(self.data).lower() if os.name == "nt"
                                             else str(self.data)])["resumed"])
        child = sa.Ledger(self.child_path)
        before = child.status()["added_bytes"]
        (extra / "growth").write_bytes(b"y" * 10_000)
        (self.data / "growth").write_bytes(b"z" * 5_000)
        self.assertEqual(child.status()["added_bytes"] - before, 15_000)

    def test_twelve_processes_with_one_contract_in_different_spellings_leave_one_child(self) -> None:
        snapshot = self.frozen()
        spellings = self.spellings(self.data)
        outcomes = self.processes(snapshot, [[spellings[i % len(spellings)]] for i in range(12)])
        self.assertEqual(sorted(o["result"] for o in outcomes), ["OPENED"] * 12)
        self.assertEqual(sum(1 for o in outcomes if o["resumed"] is False), 1)
        rows = sa.Ledger(self.child_path).records()
        self.assertEqual([r["kind"] for r in rows], ["INIT", "OPENED"])
        self.assertEqual(ss.chain(self.child_path)["result"], "PASS")

    # ------------------------------------------------------------------ changed roots are refused before effects
    def test_the_saved_additional_empty_root_restart_is_refused_before_any_effect(self) -> None:
        snapshot = self.frozen()
        self.open(snapshot)
        extra = self.base / "extra"
        extra.mkdir()
        before = self.state()
        message = self.refused(REFUSED_ROOTS, self.open, snapshot, [str(self.data), str(extra)])
        self.assertIn("owned_added", message)
        self.assertEqual(self.state(), before)
        # The manager's observation afterwards: bytes written there are not claimed as tracked -- the root was refused,
        # not silently ignored -- and the tracked roots' totals are unchanged.
        (extra / "untracked-growth").write_bytes(b"x" * 10_000)
        status = sa.Ledger(self.child_path).status()
        self.assertNotIn(str(extra), status["roots"])
        self.assertEqual(status["headroom_bytes"], before["headroom"])

    def test_a_nonempty_added_root_on_restart_is_refused(self) -> None:
        snapshot = self.frozen()
        self.open(snapshot)
        full = self.base / "full"
        full.mkdir()
        (full / "old").write_bytes(b"x" * 1234)
        before = self.state()
        self.refused(REFUSED_ROOTS, self.open, snapshot, [str(self.data), str(full)])
        self.assertEqual(self.state(), before)

    def test_omitting_a_root_the_child_was_opened_with_is_refused(self) -> None:
        snapshot = self.frozen()
        extra = self.base / "extra"
        extra.mkdir()
        self.open(snapshot, [str(self.data), str(extra)])
        before = self.state()
        message = self.refused(REFUSED_ROOTS, self.open, snapshot, [str(self.data)])
        self.assertIn("owned_omitted", message)
        self.assertEqual(self.state(), before)

    def test_a_changed_shared_set_is_refused(self) -> None:
        snapshot = self.frozen()
        other = self.base / "other-shared"
        other.mkdir()
        self.open(snapshot)
        before = self.state()
        self.refused(REFUSED_ROOTS, self.open, snapshot, [str(self.data)], [str(other)])
        self.assertEqual(self.state(), before)
        # ...and a child opened with an added shared root refuses a restart that omits it.
        self._tmp.cleanup()
        self.setUp()
        snapshot = self.frozen()
        other = self.base / "other-shared"
        other.mkdir()
        self.open(snapshot, [str(self.data)], [str(other)])
        self.refused(REFUSED_ROOTS, self.open, snapshot, [str(self.data)])

    def test_a_root_moved_between_classes_is_refused_at_open_and_on_restart(self) -> None:
        snapshot = self.frozen()
        # At the first open: the parent's owned root named shared, the shared one named owned, one named in both --
        # refused before any claim or child exists.
        for roots, shared in (([], [str(self.data)]), ([str(self.data), str(self.shared)], []),
                              ([str(self.data)], [str(self.data).upper() if os.name == "nt" else str(self.data)])):
            with self.subTest(roots=roots, shared=shared):
                self.refused(REFUSED_ROOTS, self.open, snapshot, roots, shared)
                self.assertFalse(self.root.claim_path.exists())
                self.assertFalse(self.child_path.exists())
        # On restart: an added owned root named shared.
        extra = self.base / "extra"
        extra.mkdir()
        self.open(snapshot, [str(self.data), str(extra)])
        before = self.state()
        self.refused(REFUSED_ROOTS, self.open, snapshot, [str(self.data)], [str(extra)])
        self.assertEqual(self.state(), before)

    def test_processes_racing_with_competing_root_sets_open_one_contract(self) -> None:
        snapshot = self.frozen()
        extra = self.base / "extra"
        extra.mkdir()
        plain, wider = [str(self.data)], [str(self.data), str(extra)]
        outcomes = self.processes(snapshot, [plain if i % 2 else wider for i in range(12)])
        winner = [o for o in outcomes if o["result"] == "OPENED" and o["resumed"] is False]
        self.assertEqual(len(winner), 1)
        recorded = recorded_owned(self.child_path)
        for outcome in outcomes:
            same = sorted({norm(r) for r in outcome["roots"]}) == recorded
            with self.subTest(outcome=outcome):
                self.assertEqual(outcome["result"] == "OPENED", same)
                if not same:
                    self.assertEqual(outcome["code"], REFUSED_ROOTS)
        self.assertEqual([r["kind"] for r in sa.Ledger(self.child_path).records()], ["INIT", "OPENED"])
        self.assertEqual(ss.chain(self.child_path)["result"], "PASS")

    def test_an_interrupted_claim_is_completed_only_under_the_roots_it_claimed(self) -> None:
        snapshot = self.frozen()
        extra = self.base / "extra"
        extra.mkdir()

        def crash(self, **kw):
            raise KeyboardInterrupt("the process ended after its claim")

        with mock.patch.object(sa.Ledger, "init_continuation", crash):
            with self.assertRaises(KeyboardInterrupt):
                self.open(snapshot)
        before = self.state()
        self.refused(REFUSED_ROOTS, self.open, snapshot, [str(self.data), str(extra)])
        self.assertEqual(self.state(), before)
        self.assertFalse(self.child_path.exists())
        claim = json.loads(self.root.claim_path.read_text(encoding="utf-8"))
        self.assertEqual(claim["root_contract"]["owned"], [norm(self.data)])
        recovered = self.open(snapshot, [str(self.data) + os.sep])
        self.assertTrue(recovered["continuation"]["recovered_interrupted_claim"])
        self.assertEqual(ss.chain(self.child_path)["result"], "PASS")

    def test_a_claim_recording_no_root_contract_cannot_be_completed(self) -> None:
        snapshot = self.frozen()

        def crash(self, **kw):
            raise KeyboardInterrupt("the process ended after its claim")

        with mock.patch.object(sa.Ledger, "init_continuation", crash):
            with self.assertRaises(KeyboardInterrupt):
                self.open(snapshot)
        # An earlier tool's claim: the same document without the root contract.
        document = json.loads(self.root.claim_path.read_text(encoding="utf-8"))
        document.pop("root_contract", None)
        self.root.claim_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        message = self.refused(REFUSED_ROOTS, self.open, snapshot)
        self.assertIn("unrecorded", message)
        self.assertFalse(self.child_path.exists())

    def test_an_interrupted_init_is_completed_only_under_its_own_roots(self) -> None:
        snapshot = self.frozen()
        extra = self.base / "extra"
        extra.mkdir()
        with mock.patch.object(ss, "_open_record", side_effect=KeyboardInterrupt("ended after the INIT")):
            with self.assertRaises(KeyboardInterrupt):
                self.open(snapshot)
        self.assertEqual([r["kind"] for r in sa.Ledger(self.child_path).records()], ["INIT"])
        before = self.state()
        self.refused(REFUSED_ROOTS, self.open, snapshot, [str(self.data), str(extra)])
        self.assertEqual(self.state(), before)
        self.assertEqual([r["kind"] for r in sa.Ledger(self.child_path).records()], ["INIT"])
        again = self.open(snapshot)
        self.assertEqual((again["resumed"], again["recovered"]), (True, "OPENED_RECORD_COMPLETED_AFTER_INTERRUPTION"))

    def test_no_refused_call_resets_the_baseline_or_adds_headroom(self) -> None:
        snapshot = self.frozen()
        opened = self.open(snapshot)
        extra = self.base / "extra"
        extra.mkdir()
        for roots, shared in (([str(self.data), str(extra)], []), ([], [str(self.data)]), ([str(self.data)], [str(extra)])):
            with self.assertRaises(ss.SnapshotRefused):
                self.open(snapshot, roots, shared)
        status = sa.Ledger(self.child_path).status()
        self.assertEqual((status["budget_bytes"], status["headroom_bytes"]),
                         (1_000_000, opened["opened"]["headroom_bytes"]))
        self.assertEqual(sa.Ledger(self.child_path).config(sa.Ledger(self.child_path).records())["baseline"],
                         opened["baseline"])
        self.assertEqual(ss.chain(self.child_path)["segments"][-1]["root_contract"],
                         {"owned": [norm(self.data)], "shared": [norm(self.shared)]})


if __name__ == "__main__":
    unittest.main()
