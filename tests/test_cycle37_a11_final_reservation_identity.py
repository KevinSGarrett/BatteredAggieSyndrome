"""Cycle #37 — Attempt #11 — MF37A11-01 / W37A11-07: FINAL_PACKET is bound to the reservation it was admitted under.

The Attempt 11 runner opens each lane's reservation before it makes the run folder, so it cannot name the reservation with
the run's stamp; it named it with a second clock reading (``LANE FINAL_PACKET <utc_now>``). The inherited FINAL_PACKET
ledger check rebuilt the name from the run stamp (``LANE FINAL_PACKET 20260929T051755163011Z``) and refused the run's own
valid, singleton reservation ("only_this_lane_open" false). The run keeps the reservation it was admitted under
(``run.storage_reservation``) and the check is bound to its token and operation.

These cases run the real ledger, snapshot and continuation tools on byte-sized owned fixtures, and the real
``lane_final_packet`` function against them:

* positive -- the valid singleton reservation (named with a clock reading, not the stamp), a closed frozen predecessor
  and the cumulative continuation pass, for an issued run and for a rehearsal; a historical caller that keeps no
  reservation keeps the original contract;
* negative -- a missing reservation, an extra open reservation, a wrong token, a changed operation, another lane's
  reservation, a reservation made for a run blocked before any effect, a rehearsal/issued mismatch, a refused decision
  and a record appended to the frozen predecessor each refuse for their own cause;
* structure -- the runner keeps the reservation it was admitted under, and the check reads it.
"""

from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools" / "cycle37"
sys.path.insert(0, str(TOOLS))

import attempt07_lanes as a7  # noqa: E402
import attempt07_outputs as a7o  # noqa: E402
import attempt11_lanes as a11  # noqa: E402
import storage_admission as sa  # noqa: E402
import storage_snapshot as snapshot  # noqa: E402

CLOCK = "2026-09-29T05:17:54.451886+00:00"  # a second clock reading, not the run stamp
STAMP = "20260929T051755163011Z"


class FakeRun:
    """The parts of a lane run ``lane_final_packet`` uses, with the packet and accounting commands recorded, not run."""

    def __init__(self, paths: dict[str, Path], out_root: Path, *, stamp: str = STAMP, rehearsal: bool = False,
                 **attributes: Any) -> None:
        self.extra = {"storage_paths": paths}
        self.problems: list[str] = []
        self.commands: list[tuple[str, list[str]]] = []
        self.out_root = out_root
        self.contract_path = out_root / "contract.json"
        self.python = Path(sys.executable)
        self.stamp = stamp
        self.rehearsal = rehearsal
        for name, value in attributes.items():
            setattr(self, name, value)

    def env(self, **_: Any) -> dict[str, str | None]:
        return {}

    def run(self, name: str, argv: Any, **_: Any) -> dict[str, Any]:
        self.commands.append((name, [str(a) for a in argv]))
        return {}

    def held(self) -> dict[str, Any]:
        return self.extra["storage_verification"]["final_output_ledger"]


class FinalReservationIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fresh()

    def fresh(self) -> None:
        """A new tiny operational ledger, its immutable snapshot and the one claimed final-output continuation, exactly
        as a FINAL_PACKET rehearsal makes them (attempt07_lanes.storage_paths), in a directory of its own."""

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out_root = Path(tmp.name)
        self.paths = a7.storage_paths(self.out_root, True)
        self.final = sa.Ledger(self.paths["final_output_ledger"])

    # ------------------------------------------------------------------ helpers
    def open_reservation(self, operation: str) -> dict[str, Any]:
        return self.final.reserve(operation, 1024, note="test")

    def run_for(self, admitted: Any, *, rehearsal: bool = False, stamp: str = STAMP) -> FakeRun:
        return FakeRun(self.paths, self.out_root, rehearsal=rehearsal, stamp=stamp, storage_reservation=admitted)

    def check(self, run: FakeRun) -> bool:
        a7.lane_final_packet(run)
        return run.held()["only_this_lane_open"]

    def ledger_problems(self, run: FakeRun) -> list[str]:
        return [p for p in run.problems if "final-output ledger" in p]

    def operation(self, rehearsal: bool = False, lane: str = "FINAL_PACKET", extra: str = "") -> str:
        return f"LANE {lane} {CLOCK}{extra}" + (" (rehearsal)" if rehearsal else "")

    # ------------------------------------------------------------------ positive
    def test_the_valid_singleton_reservation_named_with_a_clock_passes_for_an_issued_run(self) -> None:
        admitted = self.open_reservation(self.operation())
        self.assertNotIn(STAMP, admitted["operation"])
        run = self.run_for(admitted)
        self.assertTrue(self.check(run))
        held = run.held()
        self.assertTrue(held["continues_the_final_snapshot"])
        self.assertTrue(held["carries_the_root_budget"])
        self.assertEqual(run.extra["storage_verification"]["operational_snapshot"]["result"], "PASS")
        self.assertEqual(run.extra["storage_verification"]["chain"]["result"], "PASS")
        self.assertEqual(self.ledger_problems(run), [])

    def test_the_valid_singleton_reservation_passes_for_a_rehearsal(self) -> None:
        run = self.run_for(self.open_reservation(self.operation(rehearsal=True)), rehearsal=True)
        self.assertTrue(self.check(run))
        self.assertEqual(self.ledger_problems(run), [])

    def test_the_admitted_reservation_is_the_one_the_ledger_records(self) -> None:
        admitted = self.open_reservation(self.operation())
        rows = self.final.records()
        open_now = self.final.open_reservations(rows)
        self.assertEqual(set(open_now), {admitted["token"]})
        self.assertEqual(open_now[admitted["token"]]["operation"], admitted["operation"])
        self.assertTrue(a7._owned_final_reservation(self.run_for(admitted), open_now))

    def test_a_historical_caller_that_keeps_no_reservation_keeps_the_original_contract(self) -> None:
        self.open_reservation(f"LANE FINAL_PACKET {STAMP}")
        run = FakeRun(self.paths, self.out_root)  # no storage_reservation attribute
        self.assertFalse(hasattr(run, "storage_reservation"))
        self.assertTrue(self.check(run))

    def test_a_historical_caller_named_with_the_stamp_still_refuses_a_clock_named_reservation(self) -> None:
        self.open_reservation(self.operation())
        run = FakeRun(self.paths, self.out_root)
        self.assertFalse(self.check(run))
        self.assertTrue(self.ledger_problems(run))

    def test_a_historical_rehearsal_caller_expects_the_rehearsal_suffix(self) -> None:
        self.open_reservation(f"LANE FINAL_PACKET {STAMP} (rehearsal)")
        self.assertTrue(self.check(FakeRun(self.paths, self.out_root, rehearsal=True)))

    def test_a_historical_extra_reservation_refuses(self) -> None:
        self.open_reservation(f"LANE FINAL_PACKET {STAMP}")
        self.open_reservation("LANE FINAL_PACKET another")
        self.assertFalse(self.check(FakeRun(self.paths, self.out_root)))

    # ------------------------------------------------------------------ negative
    def test_a_missing_reservation_refuses(self) -> None:
        admitted = self.open_reservation(self.operation())
        self.final.reconcile(admitted["token"])  # it is no longer open: nothing is open
        run = self.run_for(admitted)
        self.assertFalse(self.check(run))
        self.assertEqual(run.held()["open_reservations"], {})
        self.assertTrue(self.ledger_problems(run))

    def test_a_run_that_kept_no_reservation_refuses_even_with_a_valid_one_open(self) -> None:
        self.open_reservation(self.operation())
        for kept in (None, "token", 7, {}):
            with self.subTest(kept=kept):
                self.assertFalse(self.check(self.run_for(kept)))

    def test_an_extra_open_reservation_refuses(self) -> None:
        admitted = self.open_reservation(self.operation())
        self.open_reservation("LANE STORAGE_ADMISSION extra")
        run = self.run_for(admitted)
        self.assertFalse(self.check(run))
        self.assertEqual(len(run.held()["open_reservations"]), 2)
        self.assertTrue(self.ledger_problems(run))

    def test_a_wrong_token_refuses(self) -> None:
        admitted = self.open_reservation(self.operation())
        self.assertFalse(self.check(self.run_for({**admitted, "token": "0" * 32})))
        self.assertTrue(self.check(self.run_for(admitted)))  # the same reservation with its own token passes

    def test_a_reservation_admitted_but_since_closed_is_not_the_open_one(self) -> None:
        first = self.open_reservation(self.operation())
        self.final.reconcile(first["token"])
        second = self.open_reservation(self.operation(extra=" second"))
        self.assertFalse(self.check(self.run_for(first)))
        self.assertTrue(self.check(self.run_for(second)))

    def test_a_changed_operation_refuses(self) -> None:
        admitted = self.open_reservation(self.operation())
        for changed in (admitted["operation"] + " altered", admitted["operation"].replace("FINAL_PACKET", "FINAL_PACKE")):
            with self.subTest(changed=changed):
                self.assertFalse(self.check(self.run_for({**admitted, "operation": changed})))

    def test_another_lanes_reservation_refuses(self) -> None:
        for lane in ("STORAGE_ADMISSION", "PLATFORM_CARRY", "RECEIPT", "FINAL_OUTPUTS"):
            with self.subTest(lane=lane):
                self.fresh()
                admitted = self.open_reservation(self.operation(lane=lane))
                self.assertFalse(self.check(self.run_for(admitted)))

    def test_a_reservation_made_for_a_blocked_run_refuses(self) -> None:
        admitted = self.open_reservation(self.operation(extra=" (blocked before any effect)"))
        self.assertFalse(self.check(self.run_for(admitted)))

    def test_an_issued_run_refuses_a_rehearsal_reservation_and_the_reverse(self) -> None:
        rehearsal_named = self.open_reservation(self.operation(rehearsal=True))
        self.assertFalse(self.check(self.run_for(rehearsal_named, rehearsal=False)))
        self.fresh()
        issued_named = self.open_reservation(self.operation())
        self.assertFalse(self.check(self.run_for(issued_named, rehearsal=True)))

    def test_a_refused_decision_is_not_an_admitted_reservation(self) -> None:
        admitted = self.open_reservation(self.operation())
        self.assertFalse(self.check(self.run_for({**admitted, "decision": "REFUSED"})))

    def test_a_record_appended_to_the_frozen_predecessor_still_refuses(self) -> None:
        admitted = self.open_reservation(self.operation())
        self.assertEqual(self.run_for(admitted).problems, [])
        sa.Ledger(self.paths["operational_ledger"]).stop("x", "post-freeze stop", "a record after the freeze", 1)
        run = self.run_for(admitted)
        a7.lane_final_packet(run)
        self.assertNotEqual(run.extra["storage_verification"]["operational_snapshot"].get("result"), "PASS")
        self.assertTrue([p for p in run.problems if "operational snapshot" in p])

    # ------------------------------------------------------------------ the rehearsal mirror
    def test_a_rehearsal_mirrors_the_lane_reservation_into_the_tiny_final_ledger(self) -> None:
        live = {"token": "a" * 32, "operation": self.operation(rehearsal=True), "decision": "ADMITTED"}
        args = SimpleNamespace(rehearsal=True)
        mirror = a11._reservation_for_check(args, True, live, self.paths)
        self.assertIsNot(mirror, live)
        self.assertEqual(mirror["operation"], live["operation"])
        self.assertNotEqual(mirror["token"], live["token"])
        self.assertEqual(set(self.final.open_reservations(self.final.records())), {mirror["token"]})
        self.assertTrue(self.check(self.run_for(mirror, rehearsal=True)))

    def test_an_issued_run_and_a_blocked_run_keep_their_own_reservation(self) -> None:
        live = {"token": "b" * 32, "operation": self.operation(), "decision": "ADMITTED"}
        self.assertIs(a11._reservation_for_check(SimpleNamespace(rehearsal=False), True, live, self.paths), live)
        self.assertIs(a11._reservation_for_check(SimpleNamespace(rehearsal=True), False, live, self.paths), live)
        self.assertIsNone(a11._reservation_for_check(SimpleNamespace(rehearsal=True), True, None, self.paths))
        self.assertIs(a11._reservation_for_check(SimpleNamespace(rehearsal=True), True, live, {}), live)
        self.assertEqual(self.final.open_reservations(self.final.records()), {})


class RunnerKeepsTheAdmittedReservationTests(unittest.TestCase):
    """The runner and the check are two files; a change to either must not drop the binding unnoticed."""

    @staticmethod
    def function(path: Path, name: str) -> ast.FunctionDef:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)

    def test_main_keeps_the_reservation_it_was_admitted_under(self) -> None:
        main = self.function(TOOLS / "attempt11_lanes.py", "main")
        stored = [n for n in ast.walk(main) if isinstance(n, ast.Assign)
                  and any(ast.unparse(t) == "run.storage_reservation" for t in n.targets)]
        self.assertEqual(len(stored), 1)
        self.assertIn("_reservation_for_check", ast.unparse(stored[0].value))
        self.assertIn("reservation", ast.unparse(stored[0].value))

    def test_the_final_packet_check_reads_the_kept_reservation(self) -> None:
        packet = self.function(TOOLS / "attempt07_lanes.py", "lane_final_packet")
        self.assertIn("_owned_final_reservation(run, open_now)", ast.unparse(packet))
        rebuilt = "LANE FINAL_PACKET {run.stamp}"
        self.assertNotIn(rebuilt, ast.unparse(packet))

    def test_the_continuation_flag_is_explicit_and_only_lifts_the_frozen_refusal(self) -> None:
        text = (TOOLS / "attempt11_lanes.py").read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--continuation", action="store_true"', text)
        self.assertIn("if FINAL_SNAPSHOT.is_file() and not final_lane and not args.continuation:", text)
        self.assertIn("if args.continuation and not FINAL_SNAPSHOT.is_file():", text)


def exercise_refused_snapshot_sequence(folder: Path) -> dict[str, Any]:
    """Frozen root, refused live-control reserves, one continuation, singleton reservation, both real checkers.

    The genuine root with zero, one and two refused trailing records passes. An altered prefix, a post-freeze stop,
    an admitted post-freeze write, a wrong reservation token and an extra live reservation each refuse. Refused
    records stay historical evidence and are not treated as admitted allocation.
    """

    folder.mkdir(parents=True, exist_ok=True)
    budget = 8 * 1024 * 1024
    details: dict[str, Any] = {}

    def scene(name: str, refusals: int, mutate: str | None = None) -> tuple[FakeRun, dict[str, Any]]:
        root = folder / name
        data = root / "data"
        data.mkdir(parents=True)
        operational = root / "STORAGE_RESERVATIONS.jsonl"
        frozen = root / "STORAGE_EVIDENCE_SNAPSHOT.json"
        final = root / "evidence" / "storage" / "STORAGE_RESERVATIONS_FINAL_OUTPUT.jsonl"
        ledger = sa.Ledger(operational)
        ledger.init(budget_bytes=budget, reserve_bytes=0, roots=[data], note=name,
                    cycle_number=37, attempt_number=11)
        token = ledger.reserve("material work before the freeze", 4096)["token"]
        (data / "work.bin").write_bytes(b"x")
        ledger.reconcile(token)
        snapshot.freeze(operational, frozen, label="Cycle #37 — Attempt #11 — fixture", scope="fixture only")
        if mutate == "admitted":
            ledger.reserve("post-freeze admitted write", 4096)
            (data / "after.bin").write_bytes(b"y")
        elif mutate == "stop":
            ledger.stop("probe", "stop after freeze", "must remain visible", 1)
        else:
            for _ in range(refusals):
                try:
                    ledger.reserve("post-freeze live negative control", budget + 1)
                except sa.AdmissionRefused:
                    continue
                raise RuntimeError("the post-freeze live control was admitted")
        if mutate in ("admitted", "stop"):
            try:
                snapshot.open_final(frozen, final, [str(data)], reserve_bytes=0,
                                    cycle_number=37, attempt_number=11)
            except snapshot.SnapshotRefused:
                pass
        else:
            snapshot.open_final(frozen, final, [str(data)], reserve_bytes=0,
                                cycle_number=37, attempt_number=11)
        if mutate == "prefix":
            # Change the frozen prefix hash and reseal the snapshot document. The ledger chain stays readable, so
            # both checkers reach the prefix rule and refuse it. Rewriting ledger bytes instead breaks the chain
            # inside the parent walk before that rule runs.
            document = json.loads(frozen.read_text(encoding="utf-8"))
            document["ledger"]["prefix_sha256"] = "ab" * 32
            document["content_sha256"] = snapshot._content_digest(document)
            frozen.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        admitted = None
        if final.is_file():
            final_ledger = sa.Ledger(final)
            admitted = final_ledger.reserve(f"LANE FINAL_PACKET {CLOCK}", 1024)
            if mutate == "wrong_token":
                admitted = {**admitted, "token": "0" * 32}
            elif mutate == "extra":
                final_ledger.reserve("EXTRA live reservation", 1024)
        (root / "submission.json").write_text("{}\n", encoding="utf-8", newline="\n")
        paths = {"operational_ledger": operational, "final_snapshot": frozen, "final_output_ledger": final}
        run = FakeRun(paths, root, storage_reservation=admitted)
        a7.lane_final_packet(run)
        storage_row = a7o.Context.storage(SimpleNamespace(out_root=root))
        return run, storage_row

    def refused_count(run: FakeRun) -> Any:
        return ((run.extra.get("storage_verification") or {}).get("operational_snapshot") or {}).get(
            "post_snapshot_refused_reservations")

    checks: dict[str, bool] = {}
    for count, name in ((0, "zero_refused"), (1, "one_refused"), (2, "two_refused")):
        run, storage_row = scene(name, count)
        checks[f"{name}_passes"] = (not run.problems and refused_count(run) == count
                                    and storage_row.get("frozen_and_verified") is True
                                    and storage_row["operational"]["verification"]["post_snapshot_refused_reservations"] == count)
        details[name] = {"problems": run.problems, "refused": refused_count(run),
                         "frozen_and_verified": storage_row.get("frozen_and_verified")}
    for name, mutate in (("altered_prefix", "prefix"), ("post_freeze_stop", "stop"),
                         ("post_freeze_admitted_write", "admitted")):
        run, storage_row = scene(name, 0, mutate)
        checks[f"{name}_refuses"] = bool(run.problems) and storage_row.get("frozen_and_verified") is not True
        details[name] = {"problems": run.problems, "frozen_and_verified": storage_row.get("frozen_and_verified")}
    for name, mutate in (("wrong_token", "wrong_token"), ("extra_live_reservation", "extra")):
        run, storage_row = scene(name, 0, mutate)
        checks[f"{name}_refuses"] = bool(run.problems) and storage_row.get("frozen_and_verified") is True
        details[name] = {"problems": run.problems, "frozen_and_verified": storage_row.get("frozen_and_verified")}
    return {"checks": checks, "holds": all(checks.values()), "details": details}


class RefusedTrailingSnapshotTests(unittest.TestCase):
    """MF37A11-02 / W37A11-15: both snapshot callers admit only valid refused trailing records."""

    def test_the_actual_finalization_sequence_admits_only_refused_trailing_records(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        result = exercise_refused_snapshot_sequence(Path(tmp.name))
        self.assertTrue(result["holds"], result["details"])


if __name__ == "__main__":
    unittest.main()
