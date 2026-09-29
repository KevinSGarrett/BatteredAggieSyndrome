r"""Cycle #37 — Attempt #11 — tiny-fixture preflight of the lane and output tools (R37A11-05-A/C, R37A11-02-C).

    attempt11_preflight.py --contract <cycle_contract.json> --scratch <new directory> --receipt <new file>

Run before any costly lane, on owned tiny fixtures only; it writes nothing outside ``--scratch`` and ``--receipt``:

* **Identity**: the issued contract (its digest against the sealed issuance record), its 5 requirements, 20 clauses
  (15 worker, 5 manager), 15 lanes (14 worker, each issued as ``attempt11_lanes.py --lane <ID>`` and implemented by the
  runner), 991 carryforward identities in the composition the accounting expects, and 18 declared outputs equal to the
  accounting's output names; every worker clause's evidence kind is one the accounting registers.
* **Storage lifecycle**: a tiny ledger initialized, reserved, written, measured, reconciled, frozen by a snapshot and
  continued by its one final-output ledger, the chain proved; the window audit holds on it and detects, on three more
  tiny ledgers, a byte written between windows, an overlapping reservation and an exceeded reservation, and treats a
  reservation refused inside an open window (the storage lane's live over-budget control) as neither.
* **Repair (MF37A11-01, R37A11-05-A)**: the real ``lane_final_packet`` function against tiny frozen ledgers and their one
  continuation -- the valid singleton reservation (named with a clock reading, not the run stamp) passes; a missing, extra,
  wrong-token, changed-operation, wrong-lane, blocked-run and rehearsal-mismatched reservation each refuse; historical
  callers keep the original contract -- the repair's own regression modules run in this process, and a lane retained under
  a current dependency check builds into the declared outputs, passes the release's submission validation and is reported
  as retained (never fresh), while a refused check leaves the lane not at the head.
* **Outputs**: the accounting builds the declared outputs, the report, the submission and the checklist on a tiny out
  root holding the gapped ledger and two findings -- one OPEN_OUT_OF_SCOPE, one FIXED_LOCAL whose clause is unmet --
  and must: keep every worker clause short of VERIFIED_LOCAL (no lane ran), make the clauses bound to the violated
  storage predicate FAIL from the evidence alone, list the out-of-scope finding for the owner and the partially fixed
  one as unfinished, refuse a terminal headline, pass the release's own submission validation and checklist
  generation (rebound to the tiny root) and agree clause by clause between report, checklist and submission. The same
  build on a clean ledger must not FAIL any clause. A clause failed only by a violated predicate, with every local check
  met, is listed as a process deviation for the manager and not as local work.

The receipt states each expectation and what was observed; PASS only when all hold. Nothing here is lane evidence or
acceptance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt11_lanes as lanes  # noqa: E402
import attempt11_outputs as outputs  # noqa: E402
import attempt11_reuse as reuse  # noqa: E402
import storage_admission  # noqa: E402
import storage_snapshot  # noqa: E402

#: The declared outputs the accounting does not write itself: the release writes the checklist and the seal the
#: submission; the storage ledger and its snapshot are the ledger's own.
OTHER_OUTPUTS = ("WORKER_CHECKLIST.csv", "submission.json", "STORAGE_RESERVATIONS.jsonl", "STORAGE_EVIDENCE_SNAPSHOT.json")
RELEASE = Path(r"C:\BatteredAggieSyndrome.data\ops\manager_review\releases\v2.4.1")
MIB = 1024 * 1024


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _release_module(name: str):
    sys.path.insert(0, str(RELEASE))
    spec = importlib.util.spec_from_file_location(f"release_{name}", RELEASE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def identity(contract_path: Path) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    issuance = json.loads((contract_path.parent / "issuance" / "issuance.json").read_text(encoding="utf-8"))
    criteria = [(req["id"], ac) for req in contract["requirements"] for ac in req["acceptance"]]
    worker = [ac for _, ac in criteria if ac["executor"] == "worker"]
    lane_rows = contract["required_lanes"]
    composition = dict(sorted(__import__("collections").Counter(outputs.carry_category(r["id"])
                                                               for r in contract["carryforward"]).items()))
    checks = {
        "contract_is_the_issued_bytes": _sha(contract_path) == issuance.get("contract_sha256"),
        "cycle_and_attempt": (contract.get("cycle_number"), contract.get("attempt_number"),
                              contract.get("attempt_id")) == (37, 11, lanes.ATTEMPT_ID),
        "requirements_5": [r["id"] for r in contract["requirements"]] == [f"R37A11-0{n}" for n in range(1, 6)],
        "clauses_20_worker_15": len(criteria) == 20 and len(worker) == 15,
        "lanes_15_worker_14": len(lane_rows) == 15 and sum(1 for r in lane_rows if r["executor"] == "worker") == 14,
        "every_worker_lane_issued_to_this_runner": all(f"attempt11_lanes.py --lane {r['id']} " in r["command"]
                                                       for r in lane_rows if r["executor"] == "worker"),
        "every_worker_lane_implemented": {r["id"] for r in lane_rows if r["executor"] == "worker"}
        == set(lanes.LANE_FUNCTIONS),
        "carryforward_991": len(contract["carryforward"]) == 991,
        "carry_composition": composition == dict(sorted(outputs.CARRY_COMPOSITION.items())),
        "outputs_18": set(contract["paths"]["worker_outputs"]) == set(outputs.OUTPUT_NAMES) | set(OTHER_OUTPUTS)
        and len(contract["paths"]["worker_outputs"]) == 18,
        "worker_evidence_kinds_registered": {ac["evidence_kind"] for ac in worker} <= {outputs.RAW, outputs.CENSUS},
        "worker_lanes_list": set(outputs.WORKER_LANES) == {r["id"] for r in lane_rows if r["executor"] == "worker"},
    }
    return {"checks": checks, "composition": composition, "holds": all(checks.values())}


def _ledger(folder: Path, name: str, budget: int = 8 * MIB) -> tuple[storage_admission.Ledger, Path]:
    data = folder / f"{name}-data"
    data.mkdir(parents=True)
    ledger = storage_admission.Ledger(folder / f"{name}.jsonl")
    ledger.init(budget_bytes=budget, reserve_bytes=0, roots=[folder], note=f"preflight {name}",
                cycle_number=37, attempt_number=11)
    return ledger, data


def _work(ledger: storage_admission.Ledger, data: Path, name: str, size: int, estimate: int = 64 * 1024) -> None:
    token = ledger.reserve(f"preflight {name}", estimate)["token"]
    (data / f"{name}.bin").write_bytes(b"x" * size)
    ledger.reconcile(token)


def storage_lifecycle(folder: Path) -> dict[str, Any]:
    folder.mkdir(parents=True)
    clean_dir = folder / "clean"
    clean_dir.mkdir()
    clean, data = _ledger(clean_dir, "operational")
    _work(clean, data, "one", 4096)
    _work(clean, data, "two", 8192)
    frozen = clean_dir / "SNAPSHOT.json"
    storage_snapshot.freeze(clean.path, frozen, label=f"{lanes.LABEL} PREFLIGHT (not evidence)", scope="preflight only")
    final_path = clean_dir / "final.jsonl"
    storage_snapshot.open_final(frozen, final_path, [str(clean_dir)], reserve_bytes=0, cycle_number=37,
                                attempt_number=11)
    final = storage_admission.Ledger(final_path)
    _work(final, data, "final-output", 2048)
    verification = storage_snapshot.verify(clean.path, frozen)
    chain = storage_snapshot.chain(final_path)
    audit_clean = outputs.window_audit(clean.path)
    audit_final = outputs.window_audit(final_path)

    gapped_dir = folder / "gapped"
    gapped_dir.mkdir()
    gapped, gdata = _ledger(gapped_dir, "operational")
    _work(gapped, gdata, "one", 4096)
    (gdata / "between-windows.bin").write_bytes(b"y" * 4096)
    _work(gapped, gdata, "two", 1024)
    audit_gapped = outputs.window_audit(gapped.path)

    overlap_dir = folder / "overlap"
    overlap_dir.mkdir()
    overlap, odata = _ledger(overlap_dir, "operational")
    first = overlap.reserve("preflight first", 64 * 1024)["token"]
    second = overlap.reserve("preflight second (overlapping)", 64 * 1024)["token"]
    (odata / "a.bin").write_bytes(b"z" * 1024)
    overlap.reconcile(first)
    overlap.reconcile(second)
    audit_overlap = outputs.window_audit(overlap.path)

    refused_dir = folder / "refused-inside-window"
    refused_dir.mkdir()
    inside, rdata = _ledger(refused_dir, "operational")
    token = inside.reserve("preflight open window", 64 * 1024)["token"]
    try:
        inside.reserve("preflight live control past the budget", 64 * MIB)
        refused = False
    except storage_admission.AdmissionRefused:
        refused = True
    (rdata / "inside.bin").write_bytes(b"w" * 2048)
    inside.reconcile(token)
    _work(inside, rdata, "after", 1024)
    audit_refused = outputs.window_audit(inside.path)

    exceeded_dir = folder / "exceeded"
    exceeded_dir.mkdir()
    exceeded, edata = _ledger(exceeded_dir, "operational")
    _work(exceeded, edata, "too-big", 256 * 1024, estimate=4096)
    audit_exceeded = outputs.window_audit(exceeded.path)

    checks = {
        "snapshot_verifies": verification.get("result") == "PASS",
        "chain_proves_through_the_continuation": chain.get("result") == "PASS",
        "clean_ledger_windows_hold": audit_clean["holds"] and audit_clean["unattributed_bytes"] == 0,
        "continuation_windows_hold": audit_final["holds"],
        "gap_detected_to_the_byte": (not audit_gapped["holds"]) and audit_gapped["unattributed_bytes"] == 4096,
        "overlap_detected": (not audit_overlap["holds"]) and len(audit_overlap["overlapping_reservations"]) == 1,
        "exceeded_detected": (not audit_exceeded["holds"]) and len(audit_exceeded["exceeded_reservations"]) == 1,
        "refused_reservation_inside_a_window_is_neither_gap_nor_overlap": refused and audit_refused["holds"],
    }
    return {"checks": checks, "holds": all(checks.values()),
            "audits": {"clean": audit_clean, "continuation": audit_final, "gapped": audit_gapped,
                       "overlap": audit_overlap, "exceeded": audit_exceeded, "refused_inside_window": audit_refused},
            "verification": verification, "chain": {k: chain.get(k) for k in ("result", "segments")},
            "gapped_ledger": str(gapped.path), "clean_ledger": str(clean.path)}


FINDINGS = [
    {"id": "PF-01", "severity": "P3", "disposition": "OPEN_OUT_OF_SCOPE",
     "title": "Preflight fixture: an out-of-scope finding against an original clause",
     "detail": "Tiny fixture only.", "owner": "BAS owner", "next_action": "Owner decision (fixture).",
     "evidence_ids": ["E-NEW-FINDINGS"], "criterion_ids": ["R37A11-01-A"], "lane_ids": [], "related_to": []},
    {"id": "PF-02", "severity": "P3", "disposition": "FIXED_LOCAL",
     "title": "Preflight fixture: a partially fixed finding whose original clause is unmet",
     "detail": "Tiny fixture only.", "owner": "BAS worker", "next_action": "Meet the clause's own evidence (fixture).",
     "evidence_ids": ["E-NEW-FINDINGS"], "criterion_ids": ["R37A11-04-B"], "lane_ids": ["INSTALLED_CONSUMER_C01"],
     "related_to": []},
]


def _tiny_root(folder: Path, ledger: Path) -> Path:
    root = folder
    (root / "evidence").mkdir(parents=True)
    for suffix in ("", storage_admission.HEAD_SUFFIX):
        source = Path(str(ledger) + suffix)
        if source.is_file():
            shutil.copyfile(source, root / (outputs.OPERATIONAL_LEDGER.name + suffix))
    (root / "evidence" / "NEW_FINDINGS_ATTEMPT11.json").write_text(json.dumps({
        "label": f"{lanes.LABEL} PREFLIGHT FIXTURE (not evidence)", "cycle_number": 37, "attempt_number": 11,
        "findings": FINDINGS}, indent=2), encoding="utf-8")
    return root


def build_outputs(contract_path: Path, root: Path) -> dict[str, Any]:
    protocol = _release_module("cycle_protocol")
    handoff = _release_module("handoff_integrity")
    ctx = outputs.Context(contract_path, root)
    submission = outputs.build(ctx, "IN_PROGRESS_LOCAL_WORK_REMAINS", False)
    outputs.base.seal(ctx, submission)
    sealed = json.loads((root / "submission.json").read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    rebound = {**contract, "paths": {**contract["paths"], "evidence_root": str(root)}}
    try:
        validation = protocol.validate_submission(rebound, sealed, _sha(contract_path))
        validation = {"result": "VALID", "detail": validation}
    except (KeyError, TypeError, ValueError, OSError) as error:
        validation = {"result": "INVALID_OR_INCOMPLETE", "error": str(error)}
    checklist = list(csv.DictReader(io.StringIO(handoff.checklist_text(rebound, sealed, protocol))))
    report = (root / "WORKER_REPORT.md").read_text(encoding="utf-8")
    statuses = {row["id"]: row["status"] for row in sealed["criteria"]}
    fieldnames = list(checklist[0]) if checklist else []
    id_field, state_field = "acceptance_id", "status"
    checklist_status = {row[id_field]: row.get(state_field) for row in checklist if row.get(id_field) in statuses}
    terminal = None
    try:
        outputs.build(outputs.Context(contract_path, root), "IMPLEMENTATION_SUBMITTED_NOT_ACCEPTED", True)
        terminal = "BUILT"
    except SystemExit as refusal:
        terminal = f"REFUSED: {refusal}"
    return {"submission": sealed, "validation": validation, "checklist_fields": fieldnames,
            "checklist_status": checklist_status, "report_head": report.splitlines()[:1], "report": report,
            "statuses": statuses, "terminal_headline": terminal,
            "check_problems": outputs.check(outputs.Context(contract_path, root), False)}


def deviation_only_case(contract_path: Path, root: Path) -> dict[str, Any]:
    """A clause failed only by a violated predicate (its local checks all met) is the manager's to weigh, not local
    work: it leaves U-LOCAL-CRITERIA, stays in U-PROCESS-DEVIATIONS, and leaves the implementation dimension complete
    with recorded deviations; a clause with unmet local checks stays local."""

    ctx = outputs.Context(contract_path, root)
    ctx.criterion_meta = {"R37A11-02-B": {"violated": ["storage_windows"], "local": []},
                          "R37A11-05-A": {"violated": ["storage_windows"], "local": ["FINAL_PACKET"]}}
    criteria = [{"id": key, "status": "PENDING_MANAGER" if key.endswith("-M") else
                 "FAIL" if key in ctx.criterion_meta else "VERIFIED_LOCAL", "reason": "fixture", "evidence_ids": []}
                for key in ctx.criteria]
    items = {row["id"]: row for row in outputs.unfinished_items(ctx, criteria, [], [])}
    local = set((items.get("U-LOCAL-CRITERIA") or {}).get("criterion_ids") or [])
    deviations = set((items.get("U-PROCESS-DEVIATIONS") or {}).get("criterion_ids") or [])
    checks = {"deviation_only_clause_is_not_local": "R37A11-02-B" not in local,
              "clause_with_local_checks_stays_local": "R37A11-05-A" in local,
              "both_listed_as_process_deviations": deviations == {"R37A11-02-B", "R37A11-05-A"},
              "deviation_only_predicate": outputs.deviation_only(ctx, "R37A11-02-B")
              and not outputs.deviation_only(ctx, "R37A11-05-A")}
    return {"checks": checks, "holds": all(checks.values())}


def outputs_expectations(gapped: dict[str, Any], clean: dict[str, Any]) -> dict[str, Any]:
    s = gapped["submission"]
    statuses = gapped["statuses"]
    unfinished = {row["id"]: row for row in s["unfinished"]}
    fail_expected = {"R37A11-02-B", "R37A11-05-A", "R37A11-05-C"}
    lanes_by = {row["id"]: row["status"] for row in s["lanes"]}
    report = gapped["report"]
    checks = {
        "report_starts_with_the_numeric_label": bool(gapped["report_head"])
        and gapped["report_head"][0].startswith(f"# {lanes.LABEL}"),
        "twenty_clauses": len(statuses) == 20,
        "manager_clauses_pending": sorted(k for k, v in statuses.items() if v == "PENDING_MANAGER")
        == [f"R37A11-0{n}-M" for n in range(1, 6)],
        "no_worker_clause_verified": not any(v == "VERIFIED_LOCAL" for v in statuses.values()),
        "violated_storage_predicate_fails_its_clauses": {k for k, v in statuses.items() if v == "FAIL"} == fail_expected,
        "other_worker_clauses_in_progress": all(v == "IN_PROGRESS" for k, v in statuses.items()
                                                if not k.endswith("-M") and k not in fail_expected),
        "clean_ledger_fails_no_clause": not any(v == "FAIL" for v in clean["statuses"].values()),
        "fifteen_lanes_14_not_run_1_manager": len(lanes_by) == 15 and sum(v == "NOT_RUN" for v in lanes_by.values()) == 14
        and lanes_by.get("MANAGER_REVIEW") == "PENDING_MANAGER",
        "carryforward_991": len(s["carryforward"]) == 991,
        "out_of_scope_finding_goes_to_the_owner": "PF-01" in (unfinished.get("U-NEW-FINDINGS-OWNED") or {}).get(
            "finding_ids", []),
        "partially_fixed_finding_is_unfinished": "PF-02" in (unfinished.get("U-FIXED-LOCAL-WITH-UNMET-CLAUSES") or {}).get(
            "finding_ids", []),
        "process_deviations_listed": set((unfinished.get("U-PROCESS-DEVIATIONS") or {}).get("criterion_ids", []))
        == fail_expected,
        "terminal_headline_refused": str(gapped["terminal_headline"]).startswith("REFUSED"),
        "release_submission_validation_passes": gapped["validation"]["result"] == "VALID",
        "clean_release_submission_validation_passes": clean["validation"]["result"] == "VALID",
        "checklist_agrees_with_submission": bool(gapped["checklist_status"])
        and all(gapped["checklist_status"].get(k) in (None, v) for k, v in statuses.items()),
        "report_agrees_with_submission": all(f"| {k} | " in report and f"| {v} |" in report.split(f"| {k} | ", 1)[1]
                                             .split("\n", 1)[0] for k, v in statuses.items()),
        "declared_outputs_written": all((Path(gapped["root"]) / name).is_file()
                                        for name in outputs.OUTPUT_NAMES if not name.startswith("CONTROL07")
                                        and name not in ("WORKER_CHECKLIST.csv", "STORAGE_RESERVATIONS.jsonl",
                                                         "STORAGE_EVIDENCE_SNAPSHOT.json")),
        "check_names_the_missing_control_outputs": any("CONTROL07_PROPOSAL.md" in p for p in gapped["check_problems"]),
    }
    return {"checks": checks, "holds": all(checks.values())}


# ------------------------------------------------------------------ the repair, on tiny fixtures

CLOCK = "2026-09-29T05:17:54.451886+00:00"
STAMP = "20260929T051755163011Z"


class _FakeRun:
    """The parts of a lane run ``lane_final_packet`` uses; the packet and accounting commands are recorded, not run."""

    def __init__(self, paths: dict[str, Path], out_root: Path, *, rehearsal: bool = False, **attributes: Any) -> None:
        self.extra = {"storage_paths": paths}
        self.problems: list[str] = []
        self.out_root = out_root
        self.contract_path = out_root / "contract.json"
        self.python = Path(sys.executable)
        self.stamp, self.rehearsal = STAMP, rehearsal
        for name, value in attributes.items():
            setattr(self, name, value)

    def env(self, **_: Any) -> dict[str, str | None]:
        return {}

    def run(self, *_a: Any, **_k: Any) -> dict[str, Any]:
        return {}


def final_packet_identity(folder: Path) -> dict[str, Any]:
    """The real ``lane_final_packet`` on tiny ledgers: one case per reservation the check must accept or refuse."""

    a7 = lanes.a7
    folder.mkdir(parents=True)
    counter = [0]

    def scene() -> tuple[dict[str, Path], Path, storage_admission.Ledger]:
        counter[0] += 1
        root = folder / f"case-{counter[0]:02d}"
        root.mkdir()
        paths = a7.storage_paths(root, True)
        return paths, root, storage_admission.Ledger(paths["final_output_ledger"])

    def held(paths: dict[str, Path], root: Path, admitted: Any, *, rehearsal: bool = False, keep: bool = True) -> bool:
        run = _FakeRun(paths, root, rehearsal=rehearsal, **({"storage_reservation": admitted} if keep else {}))
        a7.lane_final_packet(run)
        return bool(run.extra["storage_verification"]["final_output_ledger"]["only_this_lane_open"])

    results: dict[str, bool] = {}
    paths, root, ledger = scene()
    admitted = ledger.reserve(f"LANE FINAL_PACKET {CLOCK}", 1024)
    results["valid_singleton_named_with_a_clock"] = held(paths, root, admitted)
    results["wrong_token_refuses"] = not held(paths, root, {**admitted, "token": "0" * 32})
    results["changed_operation_refuses"] = not held(paths, root, {**admitted, "operation": admitted["operation"] + " x"})
    results["refused_decision_refuses"] = not held(paths, root, {**admitted, "decision": "REFUSED"})
    results["no_kept_reservation_refuses"] = not held(paths, root, None)
    paths, root, ledger = scene()
    admitted = ledger.reserve(f"LANE FINAL_PACKET {CLOCK} (rehearsal)", 1024)
    results["valid_singleton_rehearsal"] = held(paths, root, admitted, rehearsal=True)
    results["rehearsal_name_for_an_issued_run_refuses"] = not held(paths, root, admitted, rehearsal=False)
    paths, root, ledger = scene()
    admitted = ledger.reserve(f"LANE FINAL_PACKET {CLOCK}", 1024)
    ledger.reserve("LANE STORAGE_ADMISSION extra", 1024)
    results["extra_open_reservation_refuses"] = not held(paths, root, admitted)
    paths, root, ledger = scene()
    admitted = ledger.reserve(f"LANE FINAL_PACKET {CLOCK}", 1024)
    ledger.reconcile(admitted["token"])
    results["missing_reservation_refuses"] = not held(paths, root, admitted)
    paths, root, ledger = scene()
    results["wrong_lane_refuses"] = not held(paths, root, ledger.reserve(f"LANE STORAGE_ADMISSION {CLOCK}", 1024))
    paths, root, ledger = scene()
    results["blocked_run_reservation_refuses"] = not held(
        paths, root, ledger.reserve(f"LANE FINAL_PACKET {CLOCK} (blocked before any effect)", 1024))
    paths, root, ledger = scene()
    ledger.reserve(f"LANE FINAL_PACKET {STAMP}", 1024)
    results["historical_caller_named_with_the_stamp_passes"] = held(paths, root, None, keep=False)
    paths, root, ledger = scene()
    ledger.reserve(f"LANE FINAL_PACKET {CLOCK}", 1024)
    results["historical_caller_refuses_a_clock_name"] = not held(paths, root, None, keep=False)
    return {"checks": results, "holds": all(results.values()), "cases": len(results)}


def repair_tests() -> dict[str, Any]:
    """The repair's own regression modules, run in this process before any costly work."""

    root = Path(lanes.base.WORKTREE)
    sys.path.insert(0, str(root))
    names = ["tests.test_cycle37_a11_final_reservation_identity", "tests.test_cycle37_a11_lane_reuse"]
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=0).run(unittest.defaultTestLoader.loadTestsFromNames(names))
    return {"modules": names, "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
            "skipped": len(result.skipped), "holds": result.wasSuccessful() and result.testsRun > 0 and not result.skipped,
            "output_tail": stream.getvalue()[-1200:]}


def _fixture_lane(root: Path, lane: str, head: str) -> dict[str, Any]:
    """An original execution of one lane at another head: a receipt, its log and its index row."""

    run = "20260929T000000000000Z"
    folder = root / "lanes" / lane / run
    folder.mkdir(parents=True)
    log = folder / "lane.log"
    log.write_text(f"{lanes.LABEL} fixture lane {lane}\n", encoding="utf-8")
    zero = {k: 0 for k in ("tests", "failures", "errors", "import_errors", "failed_subtests", "skipped")}
    receipt = {"lane": lane, "run": run, "result": "PASS", "state_reason": "fixture original execution", "counts": zero,
               "started_at": "2026-09-29T00:00:00+00:00", "finished_at": "2026-09-29T00:01:00+00:00",
               "source_binding": {"clean": True, "head": head, "source_digest": "aa" * 32},
               "source_binding_after": {"clean": True, "head": head},
               "storage": {"receipt_window": {"decision": "ADMITTED"}}, "write_and_network_scope": {}, "details": {},
               "commands": [], "lane_log": str(log)}
    path = folder / "receipt.json"
    path.write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    row = {"lane": lane, "run": run, "result": "PASS", "head": head, "source_digest": "aa" * 32, "receipt": str(path),
           "receipt_sha256": _sha(path), "at": "2026-09-29T00:01:00+00:00"}
    with (root / "lanes" / "RUNS.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return {"run": run, "head": head, "source_digest": "aa" * 32, "result": "PASS", "receipt": str(path),
            "receipt_sha256": row["receipt_sha256"], "counts": zero}


def retained_lane_case(contract_path: Path, folder: Path, ledger: Path) -> dict[str, Any]:
    """A lane kept at its original execution: the accounting must adopt it only when the check holds, build every declared
    output, pass the release's own submission validation, and say in the row, the report and the equivalence document that
    the lane was retained and not executed again. A refused check must leave the lane not at the head."""

    lane = "START_CONTEXT"
    fake_head = "b" * 40
    results: dict[str, Any] = {}
    for variant in ("accepted", "refused"):
        root = _tiny_root(folder / variant, ledger)
        original = _fixture_lane(root, lane, fake_head)
        proof = root / "evidence" / "reuse" / f"REUSE_{lane}_{fake_head[:12]}_FIXTURE.json"
        proof.parent.mkdir(parents=True)
        proof.write_text(json.dumps({"fixture": True}), encoding="utf-8")
        candidate_head = outputs.git_out("rev-parse", "HEAD")
        proof = proof.rename(proof.with_name(f"REUSE_{lane}_{candidate_head[:12]}_FIXTURE.json"))
        accepted = {lane: {"proof": str(proof), "proof_sha256": _sha(proof), "original": original, "checks": 12,
                           "reexecuted": [], "delta": {"changed": []}, "commands": [], "original_handoff": {}}}
        answer = (accepted, {}) if variant == "accepted" else ({}, {lane: {"proof": str(proof), "refused_by": ["fixture"]}})
        with mock.patch.object(reuse, "verified_lanes", lambda env, names, _a=answer: _a):
            built = build_outputs(contract_path, root)
            equivalence = json.loads((root / "INHERITED_LANE_EQUIVALENCE.json").read_text(encoding="utf-8"))
        row = next(r for r in built["submission"]["lanes"] if r["id"] == lane)
        report = built["report"]
        if variant == "accepted":
            results[variant] = {
                "lane_row_is_pass_and_executed": row["status"] == "PASS" and row["executed"] is True,
                "row_is_bound_to_the_candidate_head_the_release_requires": row["head"] == built["submission"]["candidate"]["head"],
                "row_says_retained_and_names_the_original": row.get("execution") == "RETAINED_ORIGINAL_EXECUTION"
                and row.get("original_head") == fake_head and row.get("executed_again_at_this_head") is False
                and row["reason"].startswith("RETAINED, not executed again"),
                "release_submission_validation_passes": built["validation"]["result"] == "VALID",
                "evidence_registers_the_check": any(e["id"] == f"E-REUSE-{lane}" for e in built["submission"]["evidence"]),
                "report_says_retained": "keep their original execution" in report
                and f"| {lane} | CHECK | PASS | RETAINED_ORIGINAL_EXECUTION |" in report,
                "report_never_claims_every_lane_ran_fresh": "Every lane executed fresh" not in report
                and "the head every lane ran at" not in report,
                "equivalence_document_lists_it_unrelabelled": [u["lane"] for u in equivalence["equivalence_used"]] == [lane]
                and equivalence["equivalence_used"][0]["relabelled_fresh"] is False
                and next(x for x in equivalence["lanes"] if x["lane"] == lane)["execution"] == "RETAINED_ORIGINAL_EXECUTION",
                "check_reports_no_refusal": not [p for p in built["check_problems"] if "retained-lane" in p]}
        else:
            results[variant] = {
                "refused_lane_is_not_at_the_head": row["status"] == "NOT_RUN" and row["executed"] is False,
                "check_names_the_refusal": bool([p for p in built["check_problems"] if "retained-lane dependency check" in p]),
                "equivalence_document_uses_none": equivalence["equivalence_used"] == []
                and lane in equivalence["equivalence_refused"]}
    flat = {f"{variant}.{name}": value for variant, group in results.items() for name, value in group.items()}
    return {"checks": flat, "holds": all(flat.values())}


def main(argv: list[str] | None = None) -> int:
    lanes.rebind()
    outputs.rebind()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--scratch", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.scratch.exists() or args.receipt.exists():
        raise SystemExit("the scratch folder and the receipt are written once")
    started = outputs.utc_now()
    ident = identity(args.contract.resolve())
    store = storage_lifecycle(args.scratch / "storage")
    gapped_root = _tiny_root(args.scratch / "root-gapped", Path(store["gapped_ledger"]))
    clean_root = _tiny_root(args.scratch / "root-clean", Path(store["clean_ledger"]))
    gapped = build_outputs(args.contract.resolve(), gapped_root)
    gapped["root"] = str(gapped_root)
    clean = build_outputs(args.contract.resolve(), clean_root)
    expectations = outputs_expectations(gapped, clean)
    deviation = deviation_only_case(args.contract.resolve(), gapped_root)
    expectations["checks"].update(deviation["checks"])
    expectations["holds"] = expectations["holds"] and deviation["holds"]
    packet_identity = final_packet_identity(args.scratch / "final-packet-identity")
    regression = repair_tests()
    retained = retained_lane_case(args.contract.resolve(), args.scratch / "retained", Path(store["clean_ledger"]))
    result = "PASS" if (ident["holds"] and store["holds"] and expectations["holds"] and packet_identity["holds"]
                        and regression["holds"] and retained["holds"]) else "FAIL"
    receipt = {
        "label": f"{lanes.LABEL} IN_PROGRESS_LOCAL_WORK_REMAINS (tiny-fixture preflight {result})",
        "cycle_number": 37, "attempt_number": 11, "cycle_id": lanes.CYCLE_ID, "attempt_id": lanes.ATTEMPT_ID,
        "tool": str(Path(__file__).resolve()), "tool_sha256": _sha(Path(__file__)),
        "outputs_tool_sha256": _sha(Path(outputs.__file__)), "lanes_tool_sha256": _sha(Path(lanes.__file__)),
        "report_tool_sha256": _sha(Path(outputs.__file__).with_name("attempt11_report.py")),
        "reuse_tool_sha256": _sha(Path(reuse.__file__)),
        "contract": str(args.contract), "contract_sha256": _sha(args.contract), "scratch": str(args.scratch),
        "started_at": started, "finished_at": outputs.utc_now(), "result": result,
        "identity": ident, "final_packet_reservation_identity": packet_identity,
        "repair_regression_tests": regression, "retained_lane_outputs": retained, "storage_lifecycle": {k: v for k, v in store.items() if k != "audits"}
        | {"audits": {k: {kk: vv for kk, vv in v.items() if kk != "rule"} for k, v in store["audits"].items()}},
        "outputs": {"expectations": expectations,
                    "gapped": {"statuses": gapped["statuses"], "validation": gapped["validation"],
                               "terminal_headline": gapped["terminal_headline"],
                               "unfinished": [(u["id"], u["kind"], u["criterion_ids"], u["finding_ids"])
                                              for u in gapped["submission"]["unfinished"]],
                               "checklist_fields": gapped["checklist_fields"],
                               "check_problems": gapped["check_problems"][:12]},
                    "clean": {"statuses": clean["statuses"], "validation": clean["validation"]}},
        "rule": ("Tiny owned fixtures only; nothing here is lane evidence, a qualification of the real ledger or "
                 "acceptance. The real outputs are built later from the real receipts by the same code."),
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(receipt, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({"result": result, "identity": ident["checks"], "storage": store["checks"],
                      "outputs": expectations["checks"], "final_packet_reservation_identity": packet_identity["checks"],
                      "repair_regression_tests": {k: regression[k] for k in ("tests_run", "failures", "errors", "skipped")},
                      "retained_lane_outputs": retained["checks"]}, indent=2))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
