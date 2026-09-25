"""Cycle #37 — Attempt #6 — MF37A05-03: an immutable snapshot of a mutable storage ledger, proved on tiny fixtures.

Attempt 5 sealed the live ledger's hash as evidence while the final-packet lane still appended its own reservation
to that ledger, so the lane could not pass and one reservation was left open to hold the sealed hash still.
``tools/cycle37/storage_snapshot.py`` separates the two. These cases run the whole sealing order on byte-sized
owned fixtures before any expensive work:

* a snapshot cannot be frozen while a reservation is open; once every reservation is closed it can, and it then
  verifies as a hash-stable prefix of the ledger;
* the sealing order -- close reservations, freeze, seal the snapshot (not the ledger), open the separate
  final-output ledger from the snapshot's headroom, reserve and reconcile final outputs there -- leaves the
  sealed snapshot valid throughout, while the final-output ledger keeps the cumulative ceiling;
* a tampered field, a truncated file, a wrong sequence or head, a rewritten ledger prefix, a snapshot naming another
  ledger and an operational record appended after the freeze are each refused for their own cause;
* the final-output ledger refuses an allocation past the carried headroom, keeps counting across a restart, and
  nothing here deletes or rewrites a ledger or a snapshot.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "cycle37"))

import storage_admission as sa  # noqa: E402
import storage_snapshot as ss  # noqa: E402


class StorageSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.owned = self.base / "owned"
        self.owned.mkdir()
        self.ledger_path = self.base / "ops" / "STORAGE_RESERVATIONS.jsonl"
        self.ledger = sa.Ledger(self.ledger_path)
        self.ledger.init(budget_bytes=10_000, reserve_bytes=0, roots=[self.owned],
                         note=json.dumps({"predecessor": {"ledger": "A5", "open_reservation": "cc7643de",
                                                          "state": "historical condition"}}))
        self.snapshot = self.base / "ops" / "STORAGE_EVIDENCE_SNAPSHOT.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, name: str, size: int) -> None:
        (self.owned / name).write_bytes(b"x" * size)

    def work(self, name: str, size: int, estimate: int) -> dict:
        record = self.ledger.reserve(f"LANE {name}", estimate)
        self.write(name, size)
        return self.ledger.reconcile(record["token"])

    def freeze(self, **kw) -> dict:
        return ss.freeze(self.ledger_path, self.snapshot, label="Cycle #37 — Attempt #6 — test",
                         scope=kw.get("scope", "tiny fixture"))

    def refused(self, code: str, call, *args, **kw) -> str:
        with self.assertRaises(ss.SnapshotRefused) as caught:
            call(*args, **kw)
        self.assertEqual(caught.exception.code, code, str(caught.exception))
        return str(caught.exception)

    # -- freeze

    def test_a_snapshot_refuses_an_open_reservation_and_freezes_once_every_reservation_is_closed(self) -> None:
        self.work("a.bin", 1_000, 2_000)
        held = self.ledger.reserve("DEV-01 open", 500)
        self.refused(ss.REFUSED_OPEN_RESERVATIONS, self.freeze)
        self.assertFalse(self.snapshot.exists())
        self.ledger.reconcile(held["token"])
        document = self.freeze()
        self.assertEqual(document["ledger"]["records"], 5)          # INIT, RESERVE, RECONCILE, RESERVE, RECONCILE
        self.assertEqual(document["open_reservations"], {})
        self.assertEqual(document["measured"]["added_bytes"], 1_000)
        self.assertEqual(document["measured"]["headroom_bytes"], 9_000)
        self.assertEqual(document["configuration"]["predecessor"]["open_reservation"], "cc7643de")
        self.assertEqual(ss.verify(self.ledger_path, self.snapshot)["result"], "PASS")
        self.refused(ss.REFUSED_EXISTS, self.freeze)               # written once, never rewritten

    # -- the sealing order, end to end

    def test_the_sealing_order_keeps_the_sealed_snapshot_valid_while_final_outputs_are_accounted_separately(self) -> None:
        self.work("lane1.bin", 3_000, 4_000)
        self.work("lane2.bin", 2_000, 2_500)
        document = self.freeze(scope="all lanes")
        sealed = {"STORAGE_EVIDENCE_SNAPSHOT.json": document["content_sha256"]}   # the packet seals the snapshot
        final_root = self.base / "final"
        final_root.mkdir()
        final_ledger_path = self.base / "ops" / "final" / "STORAGE_FINAL_OUTPUT_LEDGER.jsonl"
        init = ss.open_final(self.snapshot, final_ledger_path, [str(final_root)])
        self.assertEqual(init["budget_bytes"], 5_000)              # exactly the operational headroom
        self.assertEqual(json.loads(init["note"])["continues_snapshot"]["content_sha256"],
                         sealed["STORAGE_EVIDENCE_SNAPSHOT.json"])
        final = sa.Ledger(final_ledger_path)
        record = final.reserve("FINAL-OUT-01 packet build and seal", 1_500)
        (final_root / "submission.json").write_bytes(b"{}" * 400)
        closing = final.reconcile(record["token"])
        self.assertEqual(closing["operation_added_bytes"], 800)
        record = final.reserve("FINAL-OUT-02 FINAL_PACKET lane", 1_000)
        (final_root / "receipt.json").write_bytes(b"r" * 300)
        final.reconcile(record["token"])
        # The operational ledger was not written again, so the sealed snapshot still verifies unchanged.
        verdict = ss.verify(self.ledger_path, self.snapshot)
        self.assertEqual((verdict["result"], verdict["post_snapshot_records"]), ("PASS", 0))
        self.assertEqual(ss.load_snapshot(self.snapshot)["content_sha256"], sealed["STORAGE_EVIDENCE_SNAPSHOT.json"])
        # The final-output ledger continues the cumulative ceiling: 5,000 - 800 - 300 remain.
        self.assertEqual(final.status()["headroom_bytes"], 3_900)
        with self.assertRaises(sa.AdmissionRefused):
            final.reserve("FINAL-OUT-03 too large", 3_901)
        self.assertEqual(sa.Ledger(final_ledger_path).status()["headroom_bytes"], 3_900)   # a restart keeps counting

    # -- negatives, each independently

    def test_a_tampered_snapshot_is_refused(self) -> None:
        self.work("a.bin", 100, 200)
        self.freeze()
        document = json.loads(self.snapshot.read_text(encoding="utf-8"))
        document["measured"]["added_bytes"] = 0
        self.snapshot.write_text(json.dumps(document), encoding="utf-8")
        self.refused(ss.REFUSED_TAMPERED, ss.verify, self.ledger_path, self.snapshot)

    def test_a_truncated_snapshot_is_refused(self) -> None:
        self.work("a.bin", 100, 200)
        self.freeze()
        data = self.snapshot.read_bytes()
        self.snapshot.write_bytes(data[: len(data) // 2])
        self.refused(ss.REFUSED_MALFORMED, ss.verify, self.ledger_path, self.snapshot)
        self.snapshot.write_text(json.dumps({"schema": "OTHER"}), encoding="utf-8")
        self.refused(ss.REFUSED_MALFORMED, ss.verify, self.ledger_path, self.snapshot)

    def test_a_wrong_sequence_or_head_is_refused(self) -> None:
        self.work("a.bin", 100, 200)
        document = self.freeze()
        for field, value in (("records", document["ledger"]["records"] + 1), ("records", 0),
                             ("head_record_sha256", "0" * 64), ("last_seq", 99)):
            forged = json.loads(self.snapshot.read_text(encoding="utf-8"))
            forged["ledger"][field] = value
            forged["content_sha256"] = ss._content_digest(forged)      # re-sealed as a forger would
            other = self.base / f"forged-{field}-{value}.json"
            other.write_text(json.dumps(forged), encoding="utf-8")
            with self.subTest(field=field, value=value):
                self.refused(ss.REFUSED_SEQUENCE, ss.verify, self.ledger_path, other)

    def test_a_rewritten_ledger_prefix_is_refused(self) -> None:
        self.work("a.bin", 100, 200)
        self.freeze()
        lines = self.ledger_path.read_text(encoding="utf-8").splitlines()
        second = json.loads(lines[1])
        second["estimate_bytes"] = 999
        lines[1] = json.dumps(second, sort_keys=True, ensure_ascii=False)
        self.ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # The admission tool's own chain check refuses the rewritten ledger before the prefix is even compared.
        self.refused(ss.REFUSED_LEDGER, ss.verify, self.ledger_path, self.snapshot)

    def test_a_snapshot_naming_another_ledger_is_refused(self) -> None:
        self.work("a.bin", 100, 200)
        self.freeze()
        other = sa.Ledger(self.base / "other" / "STORAGE_RESERVATIONS.jsonl")
        other.init(budget_bytes=10_000, reserve_bytes=0, roots=[self.owned])
        self.refused(ss.REFUSED_WRONG_LEDGER, ss.verify, other.path, self.snapshot)

    def test_an_operational_record_appended_after_the_freeze_is_refused_unless_declared(self) -> None:
        self.work("a.bin", 100, 200)
        self.freeze()
        self.work("late.bin", 50, 100)            # measured work the snapshot does not cover
        self.refused(ss.REFUSED_POST_SNAPSHOT, ss.verify, self.ledger_path, self.snapshot)
        verdict = ss.verify(self.ledger_path, self.snapshot, allow_post_snapshot=("LANE late.bin",))
        self.assertEqual((verdict["result"], verdict["post_snapshot_records"]), ("PASS", 2))
        # A declared exception names an operation prefix; an undeclared one still refuses.
        self.refused(ss.REFUSED_POST_SNAPSHOT, ss.verify, self.ledger_path, self.snapshot,
                     allow_post_snapshot=("LANE other",))

    def test_the_final_ledger_cannot_open_without_headroom_and_nothing_is_deleted(self) -> None:
        self.work("a.bin", 10_000, 10_000)
        self.freeze()
        final_ledger_path = self.base / "ops" / "final.jsonl"
        self.refused(ss.REFUSED_SEQUENCE, ss.open_final, self.snapshot, final_ledger_path, [str(self.base / "f")])
        self.assertFalse(final_ledger_path.exists())
        self.assertTrue(self.ledger_path.is_file() and self.snapshot.is_file() and (self.owned / "a.bin").is_file())
        self.assertFalse(any(name for name in dir(ss) if "delete" in name.lower() or "remove" in name.lower()))

    def test_a_bounded_stop_stays_in_force_and_a_successor_ledger_continues_the_same_ceiling(self) -> None:
        # An underestimated operation is bounded: its ledger records a stop and refuses every later reservation.
        self.work("fine.bin", 1_000, 2_000)
        with mock.patch.object(sa, "TOLERANCE_BYTES", 0):      # byte-sized fixture: no slack over the estimate
            result = sa.run_bounded(self.ledger, "LANE underestimated", 100,
                                    [sys.executable, "-c", "import pathlib,time; pathlib.Path(r'%s').write_bytes(b'x' * 3000);"
                                     " time.sleep(8)" % (self.owned / "big.bin")], poll_seconds=0.2)
        self.assertTrue(result["bounded_stop"])
        with self.assertRaises(sa.AdmissionRefused):
            self.ledger.reserve("anything after the stop", 1)
        document = self.freeze(scope="stopped operational ledger")
        self.assertIsNotNone(document["bounded_stop"])
        self.assertEqual(document["measured"]["added_bytes"], 4_000)
        # The successor ledger's budget is exactly the remaining headroom; its INIT names the snapshot and the stop.
        successor_path = self.base / "ops" / "STORAGE_RESERVATIONS_SEGMENT_02.jsonl"
        init = ss.open_successor(self.snapshot, successor_path, [str(self.owned)], kind="operational ledger segment 2",
                                 scope="continuation after the bounded stop")
        self.assertEqual(init["budget_bytes"], 6_000)
        reference = json.loads(init["note"])["continues_snapshot"]
        self.assertEqual((reference["content_sha256"], reference["bounded_stop"]["operation"]),
                         (document["content_sha256"], "LANE underestimated"))
        successor = sa.Ledger(successor_path)
        with self.assertRaises(sa.AdmissionRefused):
            successor.reserve("past the carried ceiling", 6_001)
        record = successor.reserve("LANE next", 500)
        self.write("next.bin", 400)
        successor.reconcile(record["token"])
        self.assertEqual(successor.status()["headroom_bytes"], 5_600)
        # The stopped ledger is not written again, so its snapshot still verifies with nothing after the freeze.
        verdict = ss.verify(self.ledger_path, self.snapshot)
        self.assertEqual((verdict["result"], verdict["post_snapshot_records"]), ("PASS", 0))
        self.assertEqual(sa.Ledger(self.ledger_path).status()["bounded_stop"]["operation"], "LANE underestimated")
        # A refused attempt is itself a record: touching the stopped ledger after the freeze is caught.
        with self.assertRaises(sa.AdmissionRefused):
            self.ledger.reserve("still stopped", 1)
        self.refused(ss.REFUSED_POST_SNAPSHOT, ss.verify, self.ledger_path, self.snapshot)

    def test_the_command_line_freezes_verifies_and_opens_a_final_ledger(self) -> None:
        self.work("a.bin", 100, 200)
        self.assertEqual(ss.main(["freeze", "--ledger", str(self.ledger_path), "--out", str(self.snapshot),
                                  "--label", "Cycle #37 — Attempt #6 — cli", "--scope", "cli"]), 0)
        self.assertEqual(ss.main(["verify", "--ledger", str(self.ledger_path), "--snapshot", str(self.snapshot)]), 0)
        self.assertEqual(ss.main(["open-final", "--snapshot", str(self.snapshot), "--ledger",
                                  str(self.base / "ops" / "final.jsonl"), "--root", str(self.base / "f")]), 0)
        self.work("late.bin", 10, 20)
        self.assertEqual(ss.main(["verify", "--ledger", str(self.ledger_path), "--snapshot", str(self.snapshot)]), 3)


if __name__ == "__main__":
    unittest.main()
