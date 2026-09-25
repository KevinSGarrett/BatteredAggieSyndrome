"""Cycle #37 — Attempt #5 — MF37A04-05: cumulative storage is reserved before every allocation.

Attempt 4 recorded a 4 GiB peak budget, checked only the free-space reserve, and measured 6,069,669,694 added
bytes (W37A04-15). ``tools/cycle37/storage_admission.py`` is the prevention. These cases run it on small owned
ledgers with byte-sized budgets:

* an adequately budgeted operation is admitted, and its actual cost is read back;
* a too-large, a cumulative (earlier allocations already measured) and a concurrent (another open reservation)
  allocation are refused *before* the operation runs, as is one that would breach the free-space reserve;
* an underestimated operation is recorded as such; one that takes the total past the budget records a bounded
  stop, after which every reservation is refused -- no retroactive increase;
* a running command that passes its reservation is stopped (bounded stop) and cannot finish its writes;
* a restart (a new ledger object, a new process) keeps every earlier allocation, because the added total is
  measured, and a reservation left open by a dead process is closed as an orphan while an explicit one is not;
* the ledger refuses a second initialization and a broken hash chain, and the tool deletes nothing.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "cycle37" / "storage_admission.py"
sys.path.insert(0, str(TOOL.parent))

import storage_admission as sa  # noqa: E402

MIB = 1024 * 1024


class StorageAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.owned = self.base / "owned"
        self.ledger_path = self.base / "ledger" / "STORAGE_RESERVATIONS.jsonl"
        self.ledger = sa.Ledger(self.ledger_path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def init(self, budget: int, reserve: int = 0) -> None:
        self.ledger.init(budget_bytes=budget, reserve_bytes=reserve, roots=[self.owned])

    def write(self, name: str, size: int) -> None:
        self.owned.mkdir(parents=True, exist_ok=True)
        (self.owned / name).write_bytes(b"x" * size)

    def test_an_adequately_budgeted_operation_is_admitted_and_read_back(self) -> None:
        self.init(4 * MIB)
        with sa.reservation(self.ledger, "write one MiB", 2 * MIB) as record:
            self.assertEqual(record["decision"], "ADMITTED")
            self.write("a.bin", MIB)
        rows = self.ledger.records()
        closing = next(row for row in rows if row["kind"] == "RECONCILE")
        self.assertEqual(closing["operation_added_bytes"], MIB)
        self.assertFalse(closing["underestimated"])
        self.assertTrue(closing["within_budget"])

    def test_a_too_large_allocation_is_refused_before_it_runs(self) -> None:
        self.init(4 * MIB)
        ran = []
        with self.assertRaises(sa.AdmissionRefused) as refused:
            with sa.reservation(self.ledger, "too large", 5 * MIB):
                ran.append(True)
        self.assertEqual(ran, [])
        self.assertEqual(refused.exception.record["decision"], "REFUSED")
        self.assertIn("exceeds the budget", refused.exception.record["reason"])

    def test_a_cumulative_allocation_counts_every_earlier_one(self) -> None:
        self.init(4 * MIB)
        for number in range(3):
            with sa.reservation(self.ledger, f"step {number}", MIB + 1024):
                self.write(f"s{number}.bin", MIB)
        # 3 MiB are already measured; 1.5 MiB more would pass 4 MiB even though it is small by itself.
        with self.assertRaises(sa.AdmissionRefused) as refused:
            self.ledger.reserve("one more", MIB + MIB // 2)
        self.assertEqual(refused.exception.record["added_bytes_before"], 3 * MIB)

    def test_a_concurrent_open_reservation_is_counted(self) -> None:
        self.init(4 * MIB)
        first = self.ledger.reserve("long running", 3 * MIB)
        with self.assertRaises(sa.AdmissionRefused) as refused:
            self.ledger.reserve("concurrent", 2 * MIB)
        self.assertEqual(refused.exception.record["open_estimate_bytes_before"], 3 * MIB)
        self.assertIn(first["token"], refused.exception.record["open_reservations_before"])
        self.ledger.reconcile(first["token"])
        self.assertEqual(self.ledger.reserve("after it closed", 2 * MIB)["decision"], "ADMITTED")

    def test_the_free_space_reserve_is_enforced(self) -> None:
        free = __import__("shutil").disk_usage(self.base).free
        self.init(10**15, reserve=free)  # any positive estimate would leave less than the reserve free
        with self.assertRaises(sa.AdmissionRefused) as refused:
            self.ledger.reserve("needs free space", MIB)
        self.assertIn("below the reserve", refused.exception.record["reason"])

    def test_an_underestimate_is_recorded_and_a_budget_breach_stops_every_later_allocation(self) -> None:
        self.init(2 * MIB)
        held = self.ledger.reserve("underestimated", MIB // 2)["token"]
        self.write("big.bin", 3 * MIB)
        closing = self.ledger.reconcile(held)
        self.assertTrue(closing["underestimated"])
        self.assertFalse(closing["within_budget"])
        stops = [row for row in self.ledger.records() if row["kind"] == "BOUNDED_STOP"]
        self.assertEqual(len(stops), 1)
        with self.assertRaises(sa.AdmissionRefused) as refused:
            self.ledger.reserve("anything later", 1)
        self.assertIn("bounded stop", refused.exception.record["reason"])
        # The budget is never raised after the fact: there is no command that changes it.
        self.assertFalse(any(name for name in dir(sa.Ledger) if "increase" in name or "raise" in name))

    def test_a_running_command_past_its_reservation_is_stopped(self) -> None:
        self.init(64 * MIB)
        writer = textwrap.dedent('''
            import sys, time
            from pathlib import Path
            target = Path(sys.argv[1])
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                for _ in range(400):
                    handle.write(b"y" * (256 * 1024))
                    handle.flush()
                    time.sleep(0.05)
        ''')
        result = sa.run_bounded(self.ledger, "writes 100 MiB against a 2 MiB reservation", 2 * MIB,
                                [sys.executable, "-B", "-c", writer, str(self.owned / "stream.bin")],
                                poll_seconds=0.2)
        self.assertIsNotNone(result["bounded_stop"])
        self.assertNotEqual(result["exit_code"], 0)
        size = (self.owned / "stream.bin").stat().st_size
        self.assertLess(size, 64 * MIB)
        self.assertLess(size, 2 * MIB + sa.TOLERANCE_BYTES + 16 * MIB)
        kinds = [row["kind"] for row in self.ledger.records()]
        self.assertIn("BOUNDED_STOP", kinds)
        self.assertEqual(kinds[-1], "RECONCILE")

    def test_a_restart_keeps_every_earlier_allocation(self) -> None:
        self.init(4 * MIB)
        with sa.reservation(self.ledger, "before restart", 2 * MIB):
            self.write("kept.bin", 2 * MIB)
        # A new process and a new ledger object: the earlier 2 MiB are measured again, not forgotten.
        probe = (f"import sys; sys.path.insert(0, {str(TOOL.parent)!r}); import storage_admission as sa, json\n"
                 f"print(json.dumps(sa.Ledger({str(self.ledger_path)!r}).status()))")
        completed = subprocess.run([sys.executable, "-B", "-c", probe], capture_output=True, text=True, timeout=120)
        status = json.loads(completed.stdout)
        self.assertEqual(status["added_bytes"], 2 * MIB)
        with self.assertRaises(sa.AdmissionRefused):
            sa.Ledger(self.ledger_path).reserve("would pass the budget", 3 * MIB)
        with self.assertRaises(sa.LedgerError):
            sa.Ledger(self.ledger_path).init(budget_bytes=10**12, reserve_bytes=0, roots=[self.owned])

    def test_orphans_close_by_measurement_and_explicit_holders_stay_open(self) -> None:
        self.init(8 * MIB)
        dead = subprocess.run([sys.executable, "-B", "-c", (
            f"import sys; sys.path.insert(0, {str(TOOL.parent)!r}); import storage_admission as sa\n"
            f"sa.Ledger({str(self.ledger_path)!r}).reserve('left open by a process that ends', {MIB})")],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(dead.returncode, 0, dead.stderr)
        explicit = self.ledger.reserve("held for an explicit readback", MIB, explicit=True)
        self.ledger.reserve("a later reservation triggers the orphan check", MIB)
        rows = self.ledger.records()
        orphaned = [row for row in rows if row["kind"] == "ORPHAN_CLOSED"]
        self.assertEqual([row["operation"] for row in orphaned], ["left open by a process that ends"])
        self.assertIn(explicit["token"], sa.Ledger.open_reservations(rows))

    def test_a_broken_chain_is_refused(self) -> None:
        self.init(4 * MIB)
        self.ledger.reserve("one", MIB)
        lines = self.ledger_path.read_text(encoding="utf-8").splitlines()
        lines[0] = lines[0].replace('"budget_bytes": 4194304', '"budget_bytes": 999999999999')
        self.ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaises(sa.LedgerError):
            self.ledger.records()

    def test_the_tool_deletes_nothing_but_its_own_lock(self) -> None:
        tree = ast.parse(TOOL.read_text(encoding="utf-8"))
        deleting = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in (
                    "unlink", "remove", "rmtree", "rmdir", "removedirs", "rename", "replace", "move"):
                deleting.append(ast.unparse(node))
        self.assertTrue(deleting)
        self.assertTrue(all("lock_path" in call for call in deleting), deleting)


if __name__ == "__main__":
    unittest.main()
