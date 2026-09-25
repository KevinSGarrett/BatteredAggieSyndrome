r"""Cycle #37 — Attempt #6 — the lane runner (R37A06-05).

    attempt06_lanes.py --lane <ID> --contract <cycle_contract.json> --out-root <attempt root>

This is the preserved Attempt 5 runner (``attempt05_lanes``, over the Attempt 4 and Attempt 3 runners) rebound to
the Attempt 6 contract, roots and evidence. Everything the earlier runners bind per run is still bound: the issued
contract by its sealed digest, the committed subject (branch, head, tree, source digest, descent from the issued
base, a clean tree before and after), the interpreter, module origins, the delivered database by digest, a
before/after measurement of the data root and ``C:\All-22``, the heads of the main checkout and both integration
worktrees, credential removal, and the guard and storage qualification of the costly lanes.

What Attempt 6 changes:

* **Storage (MF37A05-03).** Material lanes reserve on the operational ledger's current segment 3
  (``evidence/storage/STORAGE_RESERVATIONS_SEGMENT_03.jsonl``). Segment 1 (``STORAGE_RESERVATIONS.jsonl``) and
  segment 2 are frozen by their snapshots after their bounded stops (BEFORE-01, FORGERY-SMOKE-02); each later
  segment continues the frozen one with exactly its headroom. Once ``STORAGE_EVIDENCE_SNAPSHOT.json`` freezes
  segment 3, every material lane is refused before any effect and only FINAL_PACKET runs, reserving on the
  separate final-output ledger opened from that snapshot's headroom. No lane hashes a ledger a later step writes.
* **WRITE_PROTECTION** adds the manager's Attempt 5 ``GUARD_FRESH_VARIANTS`` replay.
* **STORAGE_ADMISSION** adds the snapshot suite, verifies the frozen segment against its ledger while segment 2
  progresses, and replays the manager's Attempt 5 independent storage challenge.
* **CAREER_SUCCESSOR (MF37A05-01)** adds the typed identity suite, the repaired verifier's bindings over the genuine
  Attempt 5 and Attempt 4 successors, and an independent identity census (no ``aggie_analytics`` import) of every
  row against its raw capture, its predecessor rows and its Attempt 4 rows.
* **INSTALLED_CONSUMER_C01 (MF37A05-01)** adds this attempt's own forgeries -- reciprocal cross-person swaps in both
  formats, wrong family and revision edges, an unrelated valid capture, display-name and Wikidata relabels and a
  contradictory cross-version mapping -- each restored independently from the genuine file, resealed as a careful
  forger would and refused for its own cause through the fresh installed CLI; the served population's identity
  against the census; and the manager's Attempt 5 adversarial, population and semantic replays.
* **LOCAL_INTEGRATION_CANDIDATE (MF37A05-02)** verifies the appended candidate from Git alone: the preserved head is
  its parent, only its ref moved, every provenance row agrees with the committed blobs, protected entries keep
  main's blobs, changed/absent/stale/masked negatives are refused, the consumer built from its tree serves and
  refuses, its own suites pass, and the two control compatibility errors are characterized for the owner.
* **FULL_FINAL_MOUNTED / STRICT_MOUNTED** run fresh once (a consumer dependency changed) and compare identities with
  the Attempt 5 final receipts at the issued base.
* **FINAL_PACKET** verifies both frozen snapshots and the final-output ledger, checks the packet, runs the v2.4.0
  submission accounting and writes a create-only validation receipt.

A lane decides what its commands did. It does not decide scientific acceptance, and it cannot turn an inherited
red lane green.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt03_lanes as base  # noqa: E402  (the preserved Attempt 3 runner)
import attempt04_lanes as a4  # noqa: E402  (the preserved Attempt 4 runner)
import attempt05_lanes as a5  # noqa: E402  (the preserved Attempt 5 runner)
import attempt06_candidate as candidate  # noqa: E402
import storage_admission as storage  # noqa: E402
import storage_snapshot as snapshot  # noqa: E402
from attempt03_lanes import (  # noqa: E402
    BLOCKED,
    DATA_ROOT,
    DELIVERED_DB,
    FAIL,
    PASS,
    Tee,
    credential_scrub,
    git_out,
    sha256_bytes,
    sha256_file,
    utc_now,
    write_json,
)

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 6
CYCLE_ID = "CYCLE-37"
ATTEMPT_ID = "ATTEMPT-06-20260925"
RUNNER_VERSION = "BAS-C37-ATTEMPT06-LANES-v1"
BASE_SHA = "7a0b6a47cfdb441d56cd2570cdb5daed603c4a01"
BRANCH = "codex/BAT-706-cycle37-rework"
LABEL = "Cycle #37 \u2014 Attempt #6 \u2014"
LANES = a5.LANES
GATED = a5.GATED
MIB = 1024 * 1024
#: Each lane's reservation (reserved before the lane, reconciled after it); the Attempt 5 final lanes used at most
#: 323 MB (INSTALLED_CONSUMER_C01, reusing its lineage fixture) and 114 MB (the candidate lane).
LANE_ESTIMATES = {
    "START_CONTEXT": 16 * MIB, "WRITE_PROTECTION": 64 * MIB, "STORAGE_ADMISSION": 64 * MIB,
    "SOURCE_ADMISSION": 96 * MIB, "SOURCE_HARNESS": 64 * MIB, "SOURCE_REGRESSIONS": 128 * MIB,
    "CAREER_SUCCESSOR": 160 * MIB, "INSTALLED_CONSUMER_C01": 512 * MIB, "LOCAL_INTEGRATION_CANDIDATE": 256 * MIB,
    "TRUE_UNMOUNTED": 128 * MIB, "FULL_FINAL_MOUNTED": 256 * MIB, "STRICT_MOUNTED": 96 * MIB,
    "PLATFORM_CARRY": 160 * MIB, "FINAL_PACKET": 32 * MIB,
}
#: The two owned lineage fixtures (full copies of the Attempt 5 and Attempt 4 successors) are made once and restored
#: from the genuine file before every case, without a rollback journal; a missing one is reserved on top of the
#: lane's estimate at its genuine file's size plus this margin.
LINEAGE_FIXTURE_MARGIN = 32 * MIB

EVIDENCE_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt06"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a06")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37a06")
ATTEMPT5_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt05"
VALIDATION_A05 = Path(r"C:\BatteredAggieSyndrome.validation\c37a05")
PACKAGING_A05 = Path(r"C:\BatteredAggieSyndrome.packaging\c37a05")
MANAGER_A5 = DATA_ROOT / "ops" / "manager_reviews" / "cycle37" / "attempt05" / "review-20260925T134703Z"
MANAGER_A5_FIXTURE_LITERAL = r"C:\BatteredAggieSyndrome.validation\mr37a05-134703"
A5_VENV_LITERAL = r"C:\BatteredAggieSyndrome.packaging\c37a05\b\5f400707\venv"
A5_SUCCESSOR = ATTEMPT5_ROOT / "release" / "successor" / "CAREER_SUCCESSOR_A05.sqlite"
A5_SUCCESSOR_SHA256 = "10c9a198a4c15595ce11f18f0153c0203b36d16adc2c871187279312d13822ec"
A4_SUCCESSOR = a5.A4_SUCCESSOR
A4_SUCCESSOR_SHA256 = a5.A4_SUCCESSOR_SHA256
#: Attempt 6 delivers no new successor: it serves the Attempt 5 file, by its Attempt 5 pointer.
SUCCESSOR_POINTER = ATTEMPT5_ROOT / "release" / "CAREER_SUCCESSOR_POINTER.json"
DELIVERED_CENSUS = ATTEMPT5_ROOT / "release" / "census" / "CAREER_TEMPLATE_CENSUS.json"
STORAGE_DIR = EVIDENCE_ROOT / "evidence" / "storage"
SEGMENT1_LEDGER = EVIDENCE_ROOT / "STORAGE_RESERVATIONS.jsonl"
SEGMENT1_SNAPSHOT = STORAGE_DIR / "STORAGE_OPERATIONAL_SEGMENT_01_SNAPSHOT.json"
SEGMENT2_LEDGER = STORAGE_DIR / "STORAGE_RESERVATIONS_SEGMENT_02.jsonl"
SEGMENT2_SNAPSHOT = STORAGE_DIR / "STORAGE_OPERATIONAL_SEGMENT_02_SNAPSHOT.json"
#: The frozen operational segments, in order, each with its immutable snapshot.
FROZEN_SEGMENTS = ((SEGMENT1_LEDGER, SEGMENT1_SNAPSHOT), (SEGMENT2_LEDGER, SEGMENT2_SNAPSHOT))
OPERATIONAL_LEDGER = STORAGE_DIR / "STORAGE_RESERVATIONS_SEGMENT_03.jsonl"
FINAL_SNAPSHOT = EVIDENCE_ROOT / "STORAGE_EVIDENCE_SNAPSHOT.json"
FINAL_OUTPUT_LEDGER = STORAGE_DIR / "STORAGE_RESERVATIONS_FINAL_OUTPUT.jsonl"
CANDIDATE_RECORDS = EVIDENCE_ROOT / "evidence" / "integration"
BEFORE_REPRODUCTION = EVIDENCE_ROOT / "evidence" / "before_run2" / "BEFORE_REPRODUCTION.json"
BEFORE_INTERRUPTED = EVIDENCE_ROOT / "evidence" / "before"
FIXTURES = VALIDATION_ROOT / "fixtures"
#: ``lineage/successor_a05.sqlite`` and its hot rollback journal are the retained state of the stopped
#: FORGERY-SMOKE-02 run; nothing opens them again (opening would make SQLite roll the journal back and remove it).
LINEAGE_A05 = FIXTURES / "lineage-b" / "successor_a05.sqlite"
LINEAGE_A04 = FIXTURES / "lineage" / "successor_a04.sqlite"
MANAGER_ADVERSARIAL_FIXTURE = FIXTURES / "mr37a05-adversarial"
CANDIDATE_WORKTREE = candidate.CANDIDATE_WORKTREE
CANDIDATE_BRANCH = candidate.CANDIDATE_BRANCH
MAIN_SHA = candidate.MAIN_SHA
GUARD = a5.GUARD
AFTER_COMMENTS = (("BAT-706", "C37-A06-AFTER-HANDOFF-BAT-706"), ("BAT-708", "C37-A06-AFTER-HANDOFF-BAT-708"))
PLATFORM_TOOL = "tools/cycle37/attempt06_platform.py"
OUTPUTS_TOOL = "tools/cycle37/attempt06_outputs.py"
FRED = a5.FRED

BOUND_MODULES = a5.BOUND_MODULES
GUARD_SUITES = a5.GUARD_SUITES
STORAGE_SUITES = a5.STORAGE_SUITES + ("test_cycle37_a06_storage_snapshot",)
CAREER_SUITES = a5.CAREER_SUITES + ("test_cycle37_a06_successor_identity",)
A6_SUITES = ("test_cycle37_a06_successor_identity", "test_cycle37_a06_storage_snapshot",
             "test_cycle37_a06_candidate_provenance")
REGRESSION_SUITES = a5.REGRESSION_SUITES + A6_SUITES
CANDIDATE_SUITES = a5.CANDIDATE_SUITES + A6_SUITES

#: The refusal each of this attempt's forgeries must produce through the installed CLI.
REFUSED_PREDECESSOR_IDENTITY = "REFUSED_CAREER_SUCCESSOR_PREDECESSOR_IDENTITY_MISMATCH"
REFUSED_SOURCE_LOCATOR = "REFUSED_CAREER_SUCCESSOR_SOURCE_LOCATOR_MISMATCH"
REFUSED_A04_IDENTITY = "REFUSED_CAREER_SUCCESSOR_A04_IDENTITY_MISMATCH"
REFUSED_PAGE_IDENTITY = "REFUSED_CAREER_SUCCESSOR_PAGE_IDENTITY_MISMATCH"
REFUSED_DANGLING = "REFUSED_CAREER_SUCCESSOR_DANGLING_REFERENCE"
REFUSED_RAW_EVIDENCE_ABSENT = "REFUSED_CAREER_SUCCESSOR_RAW_EVIDENCE_ABSENT"


def rebind() -> None:
    """Point the preserved runners at the Attempt 6 contract, roots, suites and grants."""

    a5.rebind()
    base.ATTEMPT_NUMBER = ATTEMPT_NUMBER
    base.ATTEMPT_ID = ATTEMPT_ID
    base.RUNNER_VERSION = RUNNER_VERSION
    base.BASE_SHA = BASE_SHA
    base.LANES = LANES
    base.EVIDENCE_ROOT = EVIDENCE_ROOT
    base.VALIDATION_ROOT = VALIDATION_ROOT
    base.PACKAGING_ROOT = PACKAGING_ROOT
    base.WATCH_EXCLUDED = (
        DATA_ROOT / "ops" / "manager_review",
        DATA_ROOT / "ops" / "manager_reviews",
        DATA_ROOT / "ops" / "cycle26" / "session_watchdog",
        EVIDENCE_ROOT,
    )
    base.GUARDED_ROOTS = (DATA_ROOT, base.MAIN_CHECKOUT, base.INTEGRATION_WORKTREE, base.ALL22, a4.VALIDATION_A03,
                          a4.PACKAGING_A03, a5.VALIDATION_A04, a5.PACKAGING_A04, VALIDATION_A05, PACKAGING_A05,
                          CANDIDATE_WORKTREE)
    base.AFTER_COMMENTS = AFTER_COMMENTS
    base.BOUND_MODULES = BOUND_MODULES
    base.REGRESSION_SUITES = REGRESSION_SUITES
    for name, value in (("ATTEMPT_NUMBER", ATTEMPT_NUMBER), ("ATTEMPT_ID", ATTEMPT_ID),
                        ("RUNNER_VERSION", RUNNER_VERSION), ("BASE_SHA", BASE_SHA), ("LANES", LANES),
                        ("EVIDENCE_ROOT", EVIDENCE_ROOT), ("VALIDATION_ROOT", VALIDATION_ROOT),
                        ("PACKAGING_ROOT", PACKAGING_ROOT), ("SUCCESSOR_POINTER", SUCCESSOR_POINTER),
                        ("AFTER_COMMENTS", AFTER_COMMENTS), ("PLATFORM_TOOL", PLATFORM_TOOL),
                        ("OUTPUTS_TOOL", OUTPUTS_TOOL), ("BOUND_MODULES", BOUND_MODULES),
                        ("GUARD_SUITES", GUARD_SUITES), ("REGRESSION_SUITES", REGRESSION_SUITES)):
        setattr(a4, name, value)
    for name, value in (("ATTEMPT_NUMBER", ATTEMPT_NUMBER), ("ATTEMPT_ID", ATTEMPT_ID),
                        ("RUNNER_VERSION", RUNNER_VERSION), ("BASE_SHA", BASE_SHA),
                        ("EVIDENCE_ROOT", EVIDENCE_ROOT), ("VALIDATION_ROOT", VALIDATION_ROOT),
                        ("PACKAGING_ROOT", PACKAGING_ROOT), ("SUCCESSOR_POINTER", SUCCESSOR_POINTER),
                        ("DELIVERED_CENSUS", DELIVERED_CENSUS), ("STORAGE_LEDGER", OPERATIONAL_LEDGER),
                        ("CANDIDATE_RECORDS", CANDIDATE_RECORDS), ("LINEAGE_FIXTURE_REUSE", LINEAGE_A05),
                        ("STORAGE_SUITES", STORAGE_SUITES), ("CAREER_SUITES", CAREER_SUITES),
                        ("REGRESSION_SUITES", REGRESSION_SUITES), ("CANDIDATE_SUITES", CANDIDATE_SUITES),
                        ("AFTER_COMMENTS", AFTER_COMMENTS), ("PLATFORM_TOOL", PLATFORM_TOOL),
                        ("OUTPUTS_TOOL", OUTPUTS_TOOL)):
        setattr(a5, name, value)


LaneRun = a5.LaneRun


# ------------------------------------------------------------- bindings


def load_contract(path: Path, lane: str, out_root: Path) -> tuple[dict[str, Any], list[str]]:
    problems: list[str] = []
    data = path.read_bytes()
    contract = json.loads(data.decode("utf-8"))
    digest = sha256_bytes(data)
    issuance = path.parent / "issuance" / "issuance.json"
    recorded = json.loads(issuance.read_text(encoding="utf-8")).get("contract_sha256") if issuance.is_file() else None
    if recorded != digest:
        problems.append(f"contract SHA-256 {digest} differs from the sealed issuance record {recorded}")
    if (contract.get("cycle_number"), contract.get("attempt_number")) != (CYCLE_NUMBER, ATTEMPT_NUMBER):
        problems.append("contract is not Cycle 37 Attempt 6")
    if contract.get("attempt_id") != ATTEMPT_ID:
        problems.append(f"contract attempt_id {contract.get('attempt_id')!r} is not {ATTEMPT_ID}")
    if (contract.get("repo") or {}).get("base_sha") != BASE_SHA:
        problems.append(f"contract base {(contract.get('repo') or {}).get('base_sha')} is not {BASE_SHA}")
    row = {r["id"]: r for r in contract.get("required_lanes", [])}.get(lane)
    if row is None or row.get("executor") != "worker":
        problems.append(f"{lane} is not a worker lane of this contract")
    elif f"attempt06_lanes.py --lane {lane} " not in row.get("command", ""):
        problems.append(f"the contract's command for {lane} does not invoke this runner for this lane")
    if os.path.normcase(str(out_root)) != os.path.normcase(str(Path(contract["paths"]["evidence_root"]))):
        problems.append(f"out-root {out_root} is not the contract evidence root {contract['paths']['evidence_root']}")
    contract["_sha256"] = digest
    contract["_issuance_contract_sha256"] = recorded
    contract["_lane"] = row
    return contract, problems


def bind_source() -> dict[str, Any]:
    binding = a4.bind_source()
    runner = Path(__file__).resolve()
    binding.update({
        "base": BASE_SHA,
        "descends_from_base": base.git("merge-base", "--is-ancestor", BASE_SHA, binding["head"]).returncode == 0
        if binding.get("head") else False,
        "commits_after_base": git_out("rev-list", "--count", f"{BASE_SHA}..{binding['head']}") if binding.get("head")
        else None,
        "runner": str(runner), "runner_sha256": sha256_file(runner), "runner_version": RUNNER_VERSION,
        "rebound_attempt5_runner": str(Path(a5.__file__).resolve()),
        "rebound_attempt5_runner_sha256": sha256_file(Path(a5.__file__).resolve()),
        "rebound_attempt4_runner_sha256": sha256_file(Path(a4.__file__).resolve()),
        "guard": str(GUARD), "guard_sha256": sha256_file(GUARD),
        "storage_tool_sha256": sha256_file(Path(storage.__file__).resolve()),
        "snapshot_tool_sha256": sha256_file(Path(snapshot.__file__).resolve()),
        "candidate_tool_sha256": sha256_file(Path(candidate.__file__).resolve()),
    })
    return binding


def _json_file(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).is_file() else None


def _ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _refusal(text: str) -> str | None:
    """The refusal code the consumer raised: the last full code in its output. A traceback also prints the source
    line that raises it, whose constant *name* (``REFUSED_PREDECESSOR_IDENTITY``) is not the code."""

    codes = re.findall(r"REFUSED_CAREER_SUCCESSOR_[A-Z0-9_]+", text or "") or re.findall(r"REFUSED_[A-Z0-9_]+", text or "")
    return codes[-1] if codes else None


# ------------------------------------------------------------- storage


def storage_state() -> dict[str, Any]:
    """The frozen segment proved against its ledger, the operational segment's chain and continuity, and whether
    the final snapshot exists. Nothing here writes a ledger."""

    state: dict[str, Any] = {"frozen": {}}
    for number, (ledger_path, snapshot_path) in enumerate(FROZEN_SEGMENTS, 1):
        try:
            state["frozen"][f"segment_{number}"] = snapshot.verify(ledger_path, snapshot_path)
        except snapshot.SnapshotRefused as refusal:
            state["frozen"][f"segment_{number}"] = {"result": "REFUSED", "code": refusal.code, "detail": str(refusal)}
    chain = []
    for number, ledger_path in enumerate([path for path, _ in FROZEN_SEGMENTS[1:]] + [OPERATIONAL_LEDGER], 2):
        previous = FROZEN_SEGMENTS[number - 2][1]
        try:
            rows = storage.Ledger(ledger_path).records()
            init = storage.Ledger.config(rows)
            continues = json.loads(init.get("note") or "{}").get("continues_snapshot") or {}
            frozen = snapshot.load_snapshot(previous)
            chain.append({"segment": number, "continues": str(previous),
                          "names_the_frozen_snapshot": continues.get("content_sha256") == frozen["content_sha256"],
                          "budget_equals_its_headroom": init["budget_bytes"] == frozen["measured"]["headroom_bytes"]})
        except (storage.LedgerError, snapshot.SnapshotRefused, ValueError, KeyError) as error:
            chain.append({"segment": number, "continues": str(previous), "error": str(error)})
    state["continuity"] = chain
    ledger = storage.Ledger(OPERATIONAL_LEDGER)
    try:
        rows = ledger.records()
        status = ledger.status()
        state["operational"] = {
            "segment": len(FROZEN_SEGMENTS) + 1, "ledger": str(OPERATIONAL_LEDGER), "chain_intact": True,
            "records": len(rows),
            **{k: status.get(k) for k in ("budget_bytes", "reserve_bytes", "added_bytes", "headroom_bytes", "free_bytes",
                                          "open_reservations", "bounded_stop", "refused", "underestimated")}}
    except storage.LedgerError as error:
        state["operational"] = {"ledger": str(OPERATIONAL_LEDGER), "chain_intact": False, "error": str(error)}
    state["final_snapshot_exists"] = FINAL_SNAPSHOT.is_file()
    return state


def _storage_problems(state: dict[str, Any]) -> list[str]:
    problems = [f"frozen {name} does not verify against its ledger: {row}"
                for name, row in state["frozen"].items() if row.get("result") != "PASS"]
    problems += [f"segment {row['segment']} does not continue {row['continues']} with exactly its headroom: {row}"
                 for row in state["continuity"] if not (row.get("names_the_frozen_snapshot")
                                                        and row.get("budget_equals_its_headroom"))]
    segment = state["operational"]
    if not segment.get("chain_intact"):
        problems.append(f"the operational ledger is not usable: {segment.get('error')}")
    else:
        if segment.get("bounded_stop"):
            problems.append(f"the operational segment records a bounded stop: {segment['bounded_stop']}")
        if int(segment.get("added_bytes") or 0) > int(segment.get("budget_bytes") or 0):
            problems.append("the operational segment's measured added bytes exceed its budget")
    return problems


# ------------------------------------------------------------- lanes: context, guard, storage, source


def lane_start_context(run: LaneRun) -> None:
    a4.lane_start_context(run)
    state = storage_state()
    run.extra["storage"] = state
    run.problems.extend(_storage_problems(state))
    pointer = a5.successor_pointer()
    built = (pointer.get("built_from") or {}).get("head")
    run.extra["career_successor_built_from"] = {
        "head": built, "ancestor_of_this_head": bool(built) and base.git("merge-base", "--is-ancestor", str(built),
                                                                          run.binding["head"]).returncode == 0}
    if not run.extra["career_successor_built_from"]["ancestor_of_this_head"]:
        run.problems.append("the delivered successor was built from a head this subject does not descend from")
    reproduction = _json_file(BEFORE_REPRODUCTION) or {}
    run.extra["before_reproduction"] = {
        "file": str(BEFORE_REPRODUCTION), "sha256": sha256_file(BEFORE_REPRODUCTION) if BEFORE_REPRODUCTION.is_file()
        else None, "reproduced": reproduction.get("reproduced"), "subject": reproduction.get("subject"),
        "interrupted_first_run_retained": sorted(str(p) for p in BEFORE_INTERRUPTED.rglob("*") if p.is_file())[:40]}
    if not reproduction.get("reproduced"):
        run.problems.append("the before-repair reproduction is missing or did not reproduce the findings")
    run.extra["guard"] = {"path": str(GUARD), "sha256": sha256_file(GUARD)}
    run.extra["integration_candidate"] = {"state": a5.candidate_state(), "description": candidate.describe()}
    run.extra["platform_receipts"] = sorted(str(p.relative_to(EVIDENCE_ROOT)) for p in
                                            (EVIDENCE_ROOT / "evidence" / "platform").rglob("*.json"))


def lane_write_protection(run: LaneRun) -> None:
    a5.lane_write_protection(run)
    # The manager's Attempt 5 fresh native Git variants, against this subject's guard (the script names this
    # worktree), in an owned fixture root.
    fixture = run.fresh("mgr_a5_guard_variants_fixture")
    copy, replay = a4._replay_from(run, MANAGER_A5, "guard_fresh_variants.py",
                                   adapt={f"F=Path(r'{MANAGER_A5_FIXTURE_LITERAL}')": f"F=Path(r'{fixture}')"})
    record = run.run("manager_a5_guard_fresh_variants_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None),
                     note="The manager's saved probe, fixture root adapted; it installs the guard in its own child.")
    result = _json_file(copy.parent / "GUARD_FRESH_VARIANTS.json") or {}
    cases = json.loads(result.get("stdout") or "[]") if str(result.get("stdout") or "").startswith("[") else []
    by_name = {row.get("name"): row for row in cases if isinstance(row, dict)}
    writes = ("separated-file", "long-file", "diff-output", "helper", "env-config")
    verdict = {**replay, "exit": record.get("exit_code"), "child_exit": result.get("exit"),
               "protected_unchanged": bool(result.get("protected_before"))
               and result.get("protected_before") == result.get("protected_after"),
               "reads_admitted": {name: (by_name.get(name) or {}).get("exit") == 0 for name in ("read-status", "read-diff")},
               "writes_refused": {name: bool((by_name.get(name) or {}).get("refused"))
                                  or (by_name.get(name) or {}).get("exit") not in (0, None) for name in writes},
               "cases": cases}
    verdict["holds"] = (verdict["protected_unchanged"] and all(verdict["reads_admitted"].values())
                        and all(verdict["writes_refused"].values()))
    run.extra["manager_a5_guard_fresh_variants"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's Attempt 5 guard variants do not hold against this guard: {verdict}")


def lane_storage_admission(run: LaneRun) -> None:
    run.census("storage_suites", STORAGE_SUITES,
               note="Admission (admitted, too large, cumulative, concurrent, free reserve, underestimate, bounded stop, "
                    "restart, orphan/explicit holders, broken chain, no deletion) and the snapshot separation "
                    "(freeze, verify, tamper/truncate/sequence/prefix/other-ledger/post-freeze refusals, final-output "
                    "ledger), each on owned fixtures.")
    before = storage_state()
    ledger = storage.Ledger(OPERATIONAL_LEDGER)
    status = ledger.status()
    # A live control on the attempt's own operational ledger: one byte past the remaining budget is refused before
    # any effect (the refusal is itself recorded, as every refusal is).
    try:
        ledger.reserve("STORAGE_ADMISSION live control: one byte past the remaining budget",
                       int(status["headroom_bytes"]) + 1, note="must be refused; nothing is allocated")
        live = {"refused": False}
    except storage.AdmissionRefused as refusal:
        live = {"refused": True, "record_seq": refusal.record.get("seq"), "reason": refusal.record.get("reason")}
    after = storage_state()
    rows = ledger.records()
    lanes = [row for row in rows if row["kind"] == "RESERVE" and str(row.get("operation", "")).startswith("LANE ")]
    reconciled = {row["token"] for row in rows if row["kind"] == "RECONCILE"}
    pairs = {"lane_reservations": len(lanes),
             "admitted": sum(1 for row in lanes if row["decision"] == "ADMITTED"),
             "admitted_and_reconciled": sum(1 for row in lanes if row["decision"] == "ADMITTED"
                                            and row["token"] in reconciled),
             "open_now": sorted(row["token"] for row in lanes if row["decision"] == "ADMITTED"
                                and row["token"] not in reconciled)}
    # The frozen segments stay hash-stable while the operational segment progresses (it gained a record above).
    stable = (all(row.get("result") == "PASS" for row in (*before["frozen"].values(), *after["frozen"].values()))
              and {k: v.get("content_sha256") for k, v in before["frozen"].items()}
              == {k: v.get("content_sha256") for k, v in after["frozen"].items()}
              and after["operational"].get("records", 0) > before["operational"].get("records", 0))
    run.extra["storage_ledger"] = {
        "operational_ledger": str(OPERATIONAL_LEDGER), "records": len(rows), "chain_intact": True,
        **{k: status.get(k) for k in ("budget_bytes", "reserve_bytes", "added_bytes", "headroom_bytes", "free_bytes",
                                      "bounded_stop")},
        "live_over_budget_control": live, "lane_reservation_pairs": pairs,
        "frozen_segments": [{"snapshot": str(path), "snapshot_sha256": sha256_file(path),
                             "content_sha256": snapshot.load_snapshot(path)["content_sha256"],
                             "bounded_stop": snapshot.load_snapshot(path).get("bounded_stop")}
                            for _, path in FROZEN_SEGMENTS],
        "frozen_verified_before": before["frozen"], "frozen_verified_after": after["frozen"],
        "hash_stable_while_the_operational_segment_progressed": stable,
        "continuity": after["continuity"], "operational_segment": after["operational"],
        "attempt5_ledger_retained": {"path": str(ATTEMPT5_ROOT / "STORAGE_RESERVATIONS.jsonl"),
                                     "sha256": sha256_file(ATTEMPT5_ROOT / "STORAGE_RESERVATIONS.jsonl"),
                                     "state": "sealed with reservation cc7643de open; read only, never reconciled here"}}
    if not live["refused"]:
        run.problems.append("an over-budget reservation was admitted on the operational ledger")
    if not stable:
        run.problems.append("a frozen segment is not hash-stable while the operational segment progresses")
    run.problems.extend(_storage_problems(after))
    # The manager's Attempt 5 independent storage challenge against this admission tool, in an owned fixture.
    fixture = run.fresh("mgr_a5_storage_fixture")
    copy, replay = a4._replay_from(run, MANAGER_A5, "storage_independent.py", adapt={
        f"F=Path(r'{MANAGER_A5_FIXTURE_LITERAL}')/'storage-proof'": f"F=Path(r'{fixture}')/'storage-proof'"})
    record = run.run("manager_a5_storage_independent_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(pythonpath=None), note="The manager's saved storage challenge, fixture root adapted.")
    review = _json_file(copy.parent / "STORAGE_INDEPENDENT_REVIEW.json") or {}
    results = review.get("results") or []
    verdict = {**replay, "exit": record.get("exit_code"),
               "positive_readback": (results[0] if results else {}).get("operation_added_bytes"),
               "concurrent": (results[1] if len(results) > 1 else {}).get("decision"),
               "restart_added": (review.get("restart") or {}).get("added_bytes"),
               "underestimated": (results[2] if len(results) > 2 else {}).get("underestimated"),
               "after_bounded_stop": (results[3] if len(results) > 3 else {}).get("decision")}
    verdict["holds"] = (verdict["positive_readback"] == 2000 and verdict["concurrent"] == "REFUSED"
                        and verdict["restart_added"] == 2000 and verdict["underestimated"] is True
                        and verdict["after_bounded_stop"] == "REFUSED")
    run.extra["manager_a5_storage_independent"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's Attempt 5 storage challenge does not hold: {verdict}")


def lane_source_admission(run: LaneRun) -> None:
    a5.lane_source_admission(run)


def lane_source_harness(run: LaneRun) -> None:
    a5.lane_source_harness(run)


def lane_source_regressions(run: LaneRun) -> None:
    a5.lane_source_regressions(run)


# ------------------------------------------------------------- the career successor (MF37A05-01)


def _display_of(title: Any) -> str:
    """The display name a Wikipedia page is served under: its title without a trailing disambiguation."""

    return re.sub(r"\s*\(.*\)$", "", str(title or ""))


def _capture(path: Path) -> dict[str, Any]:
    """Page, revision, title, Wikidata item and revision-text digest of one raw capture, read from its bytes."""

    data = path.read_bytes()
    payload = json.loads(data.decode("utf-8-sig"))
    pages = (payload.get("query") or {}).get("pages") or {}
    pages = list(pages.values()) if isinstance(pages, dict) else list(pages)
    found = []
    for page in pages:
        for revision in page.get("revisions") or []:
            slot = ((revision.get("slots") or {}).get("main") or {})
            text = slot.get("*", slot.get("content"))
            found.append({"pageid": str(page.get("pageid")), "revision": str(revision.get("revid")),
                          "title": page.get("title"), "wikibase_item": (page.get("pageprops") or {}).get("wikibase_item"),
                          "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if isinstance(text, str)
                          else None})
    return {"sha256": hashlib.sha256(data).hexdigest(), "revisions": found}


def independent_identity_census(successor: Path, a04: Path, database: Path) -> dict[str, Any]:
    """Every served row against its own raw capture, its predecessor rows and its Attempt 4 rows -- sqlite3, json and
    hashlib only, no ``aggie_analytics`` import -- with the legitimate classes the repair must keep."""

    conn, previous, older = _ro(successor), _ro(database), _ro(a04)
    try:
        rows = [dict(row) for row in conn.execute("SELECT * FROM career_episode_a05 ORDER BY episode_id")]
        dispositions = {row["predecessor_episode_id"]: dict(row)
                        for row in conn.execute("SELECT * FROM career_a05_disposition")}
        from_a04 = {row["a04_episode_id"]: dict(row) for row in conn.execute("SELECT * FROM career_a05_from_a04")}
        parents = {row["episode_id"]: dict(row) for row in previous.execute("SELECT * FROM career_episode_successor")}
        a04_rows = {row["episode_id"]: dict(row) for row in older.execute("SELECT * FROM career_episode_a04")}
    finally:
        conn.close()
        previous.close()
        older.close()
    identity = ("pageid", "revision", "family")
    page = ("page_title", "person_display", "wikidata_qid", "raw_file_sha256", "wikitext_sha256")
    mismatches: dict[str, list[Any]] = collections.defaultdict(list)
    captures: dict[str, dict[str, Any]] = {}
    qid_not_stated = 0
    for row in rows:
        path = str(row["raw_file"] or "")
        if path not in captures:
            captures[path] = _capture(Path(path)) if path and Path(path).is_file() else {"sha256": None, "revisions": []}
        capture = captures[path]
        if capture["sha256"] != row["raw_file_sha256"]:
            mismatches["raw_file_digest"].append(row["episode_id"])
        match = [r for r in capture["revisions"] if (r["pageid"], r["revision"]) == (str(row["pageid"]), str(row["revision"]))]
        if len(match) != 1:
            mismatches["raw_page_or_revision"].append(row["episode_id"])
            continue
        found = match[0]
        if found["title"] != row["page_title"]:
            mismatches["raw_title"].append(row["episode_id"])
        if _display_of(found["title"]) != row["person_display"]:
            mismatches["display_not_derived_from_capture_title"].append(row["episode_id"])
        if found["wikibase_item"] is None:
            qid_not_stated += 1
        elif found["wikibase_item"] != row["wikidata_qid"]:
            mismatches["wikidata_item"].append(row["episode_id"])
        if found["text_sha256"] != row["wikitext_sha256"]:
            mismatches["revision_text_digest"].append(row["episode_id"])
        for parent_id in json.loads(row["predecessor_episode_ids"] or "[]"):
            parent = parents.get(parent_id)
            if parent is None:
                mismatches["parent_absent"].append([row["episode_id"], parent_id])
            elif any(str(parent[k]) != str(row[k]) for k in identity):
                mismatches["parent_page_revision_family"].append([row["episode_id"], parent_id])
            elif any(str(parent[k]) != str(row[k]) for k in page):
                mismatches["parent_page_identity_or_capture"].append([row["episode_id"], parent_id])
            elif row["episode_id"] not in json.loads((dispositions.get(parent_id) or {}).get("successor_episode_ids") or "[]"):
                mismatches["parent_disposition_not_reciprocal"].append([row["episode_id"], parent_id])
        for a04_id in json.loads(row["a04_episode_ids"] or "[]"):
            older_row = a04_rows.get(a04_id)
            if older_row is None:
                mismatches["a04_absent"].append([row["episode_id"], a04_id])
            elif any(str(older_row[k]) != str(row[k]) for k in identity):
                mismatches["a04_page_revision_family"].append([row["episode_id"], a04_id])
            elif any(str(older_row[k]) != str(row[k]) for k in page):
                mismatches["a04_page_identity_or_capture"].append([row["episode_id"], a04_id])
            elif row["episode_id"] not in json.loads((from_a04.get(a04_id) or {}).get("a05_episode_ids") or "[]"):
                mismatches["a04_mapping_not_reciprocal"].append([row["episode_id"], a04_id])
    pages = collections.defaultdict(set)
    for row in rows:
        pages[(row["pageid"], row["revision"])].add(tuple(str(row[k]) for k in page))
    predecessor_pages = {(p["pageid"], p["revision"]) for p in parents.values()}
    classes = {
        "rows_added_without_predecessor": sum(1 for r in rows if r["predecessor_episode_ids"] in (None, "", "[]")),
        "pages_without_predecessor_rows": sum(1 for key in pages if key not in predecessor_pages),
        "predecessor_rows_not_produced": sum(1 for d in dispositions.values()
                                             if json.loads(d["successor_episode_ids"] or "[]") == []),
        "predecessor_rows_split": sum(1 for d in dispositions.values()
                                      if len(json.loads(d["successor_episode_ids"] or "[]")) > 1),
        "rows_served_under_a_disambiguated_title": sum(1 for r in rows if r["person_display"] != r["page_title"]),
        "rows_with_homonym_display_name": sum(1 for r in rows if r.get("homonym_display_name")),
        "rows_without_team_text": sum(1 for r in rows if r["team_raw"] in (None, "")
                                      or r["team_char_span"] in (None, "", "[]", "[null, null]")),
        "rows_of_a_named_other_sport_person": sum(1 for r in rows if r["person_display"] == "Larry Panciera"),
        "rows_whose_capture_states_no_wikidata_item": qid_not_stated,
    }
    result = {"method": ("sqlite3/json/hashlib only: each raw capture re-read and hashed, its page, revision, title, "
                         "Wikidata item and revision text compared with every row that names it; every predecessor "
                         "and Attempt 4 edge compared on page, revision, family, page identity and capture digests"),
              "successor": str(successor), "successor_sha256": sha256_file(successor), "rows": len(rows),
              "raw_files": len(captures), "pages": len(pages),
              "pages_uniform": sum(1 for values in pages.values() if len(values) == 1),
              "predecessor_rows": len(parents), "predecessor_rows_dispositioned": len(dispositions),
              "predecessor_identity_sets_equal": set(dispositions) == set(parents),
              "a04_rows": len(a04_rows), "a04_rows_mapped": len(from_a04),
              "a04_identity_sets_equal": set(from_a04) == set(a04_rows),
              "mismatch_counts": {k: len(v) for k, v in mismatches.items()},
              "mismatch_examples": {k: v[:5] for k, v in mismatches.items()}, "legitimate_classes": classes}
    result["holds"] = (not mismatches and result["rows"] == 72958 and result["raw_files"] == 7950
                       and result["pages_uniform"] == result["pages"]
                       and result["predecessor_identity_sets_equal"] and len(parents) == 72070
                       and result["a04_identity_sets_equal"] and len(a04_rows) == 73082)
    result["_identity_by_episode"] = {row["episode_id"]: [str(row[k]) for k in (*identity, *page)] for row in rows}
    return result


def lane_career_successor(run: LaneRun) -> None:
    a5.lane_career_successor(run)
    # The repaired verifier (this subject's source) over both genuine successors: what it binds.
    script = ("import json, sqlite3, sys\n"
              "from pathlib import Path\n"
              "from aggie_analytics.cycle37 import career_successor as cs\n"
              "db = Path(sys.argv[1])\n"
              "out = {'verifier_version': cs.VERIFIER_VERSION}\n"
              "for name, path, digest in (('A05', sys.argv[2], sys.argv[3]), ('A04', sys.argv[4], sys.argv[5])):\n"
              "    conn = sqlite3.connect(db.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)\n"
              "    binding = cs.attach_successor(conn, Path(path), database=db, expected_sha256=digest)\n"
              "    out[name] = {k: binding.get(k) for k in ('format_version', 'episode_table', 'successor_sha256', "
              "'lineage_proved_independently_of_the_ledgers')}\n"
              "    conn.close()\n"
              "print(json.dumps(out, default=str))\n")
    record = run.run("source_attach_genuine_successors", [run.python, "-B", "-c", script, DELIVERED_DB, A5_SUCCESSOR,
                                                          A5_SUCCESSOR_SHA256, A4_SUCCESSOR, A4_SUCCESSOR_SHA256],
                     note="The repaired verifier from the committed source over the genuine Attempt 5 and 4 files.")
    bindings = base._stdout_json(record) or {}
    a05 = ((bindings.get("A05") or {}).get("lineage_proved_independently_of_the_ledgers") or {})
    a04 = ((bindings.get("A04") or {}).get("lineage_proved_independently_of_the_ledgers") or {})
    run.extra["source_identity_bindings"] = bindings
    checks = {
        "a05_all_rows_bound": a05.get("episodes") == 72958 and a05.get("rows_with_raw_provenance") == 72958,
        "a05_dispositions_bound": a05.get("dispositions_bound_to_predecessor_row_digest") == 72070,
        "a05_parent_edges_bound": bool(a05.get("parent_edges_bound_to_page_revision_family"))
        and a05.get("parent_edges_bound_to_page_revision_family") == a05.get("edges"),
        "a05_pages_uniform": a05.get("pages_uniform") == 7950,
        "a05_a04_edges_bound": bool(a05.get("a04_edges_bound_to_page_revision_family")),
        "a04_attaches": (bindings.get("A04") or {}).get("format_version") is not None and bool(a04),
    }
    run.extra["source_identity_checks"] = checks
    for name, held in checks.items():
        if not held:
            run.problems.append(f"source identity binding: {name} does not hold ({a05 if 'a05' in name else a04})")
    census = independent_identity_census(A5_SUCCESSOR, A4_SUCCESSOR, DELIVERED_DB)
    census.pop("_identity_by_episode")
    run.extra["independent_identity_census"] = census
    if not census["holds"]:
        run.problems.append(f"the independent identity census finds mismatches: {census['mismatch_counts']}")


# ------------------------------------------------------------- the installed consumer (MF37A05-01)


def _reseal(conn: sqlite3.Connection, tables: tuple[tuple[str, str], ...]) -> None:
    """Re-hash the ledgers exactly as the manager's probe does: a careful forger's reseal."""

    for table, key in tables:
        digest = hashlib.sha256()
        count = 0
        for row in conn.execute(f"SELECT * FROM {table} ORDER BY {key}"):
            digest.update((json.dumps(list(row), ensure_ascii=False, separators=(",", ":"), default=str) + "\n").encode())
            count += 1
        for field, value in ((f"ledger::{table}::sha256", digest.hexdigest()), (f"ledger::{table}::rows", str(count))):
            conn.execute("UPDATE successor_identity SET value=? WHERE key=?", (value, field))


A05_TABLES = (("career_episode_a05", "episode_id"), ("career_a05_disposition", "predecessor_episode_id"),
              ("career_a05_from_a04", "a04_episode_id"))
A04_TABLES = (("career_episode_a04", "episode_id"), ("career_a04_disposition", "predecessor_episode_id"))


def _one_to_one(c: sqlite3.Connection, episodes: str, dispositions: str, where: str, args: tuple[Any, ...],
                order: str = "episode_id") -> dict[str, Any] | None:
    """A row with exactly one parent whose disposition names exactly that row."""

    for row in c.execute(f"SELECT * FROM {episodes} WHERE predecessor_episode_ids != '[]' AND {where} ORDER BY {order}",
                         args):
        row = dict(row)
        parents = json.loads(row["predecessor_episode_ids"])
        if len(parents) != 1:
            continue
        disposition = c.execute(f"SELECT * FROM {dispositions} WHERE predecessor_episode_id=?", (parents[0],)).fetchone()
        if disposition and json.loads(disposition["successor_episode_ids"]) == [row["episode_id"]]:
            return row
    return None


def _swap_parents(c: sqlite3.Connection, episodes: str, dispositions: str, *, copy_disposition: bool) -> dict[str, Any]:
    victim = _one_to_one(c, episodes, dispositions, "person_display = ?", (FRED,))
    other = _one_to_one(c, episodes, dispositions, "person_display != ? AND pageid != ?",
                        (FRED, victim["pageid"]), order="episode_id DESC")
    pa, pb = json.loads(victim["predecessor_episode_ids"])[0], json.loads(other["predecessor_episode_ids"])[0]
    for child, parent in ((victim, pb), (other, pa)):
        text = c.execute(f"SELECT disposition FROM {dispositions} WHERE predecessor_episode_id=?", (parent,)).fetchone()[0]
        if copy_disposition:
            c.execute(f"UPDATE {episodes} SET predecessor_episode_ids=?, disposition=? WHERE episode_id=?",
                      (json.dumps([parent]), text, child["episode_id"]))
        else:
            c.execute(f"UPDATE {episodes} SET predecessor_episode_ids=? WHERE episode_id=?",
                      (json.dumps([parent]), child["episode_id"]))
    c.execute(f"UPDATE {dispositions} SET successor_episode_ids=? WHERE predecessor_episode_id=?",
              (json.dumps([other["episode_id"]]), pa))
    c.execute(f"UPDATE {dispositions} SET successor_episode_ids=? WHERE predecessor_episode_id=?",
              (json.dumps([victim["episode_id"]]), pb))
    return {"victim_episode": victim["episode_id"], "other_episode": other["episode_id"],
            "other_person": other["person_display"], "original_parent": pa, "forged_parent": pb}


def _rename(c: sqlite3.Connection, field: str, value: str) -> dict[str, Any]:
    """Move one of Fred Mariani's rows to another revision or family, with its identity and every reference renamed,
    so the identity grammar, reciprocity and the ledgers all still hold."""

    for candidate_row in c.execute("SELECT * FROM career_episode_a05 WHERE person_display=? AND "
                                   "predecessor_episode_ids != '[]' ORDER BY episode_id", (FRED,)).fetchall():
        row = dict(candidate_row)
        prefix, pageid, revision, family, index, interval = row["episode_id"].split(":")
        parts = {"revision": revision, "family": family}
        parts[field] = value
        new_id = ":".join((prefix, pageid, parts["revision"], parts["family"], index, interval))
        if new_id != row["episode_id"] and not c.execute("SELECT 1 FROM career_episode_a05 WHERE episode_id=?",
                                                         (new_id,)).fetchone():
            break
    else:
        raise RuntimeError(f"no row of {FRED} can move to {field}={value} without colliding")
    c.execute(f"UPDATE career_episode_a05 SET episode_id=?, {field}=? WHERE episode_id=?", (new_id, value, row["episode_id"]))
    for table, column in (("career_a05_disposition", "successor_episode_ids"), ("career_a05_from_a04", "a05_episode_ids")):
        for key, ids in c.execute(f"SELECT rowid, {column} FROM {table} WHERE {column} LIKE ?",
                                  (f'%"{row["episode_id"]}"%',)).fetchall():
            listed = [new_id if item == row["episode_id"] else item for item in json.loads(ids)]
            c.execute(f"UPDATE {table} SET {column}=? WHERE rowid=?", (json.dumps(listed), key))
    return {"episode": row["episode_id"], "renamed_to": new_id, "field": field, "value": value}


def _unrelated_capture(c: sqlite3.Connection) -> dict[str, Any]:
    fred = dict(c.execute("SELECT * FROM career_episode_a05 WHERE person_display=? AND team_raw LIKE '%DFO%' LIMIT 1",
                          (FRED,)).fetchone())
    donor = dict(c.execute("SELECT * FROM career_episode_a05 WHERE person_display != ? AND team_char_span IS NOT NULL "
                           "AND pageid != ? ORDER BY episode_id DESC LIMIT 1", (FRED, fred["pageid"])).fetchone())
    columns = ("raw_file", "raw_file_sha256", "wikitext_sha256", "team_char_span", "team_byte_span", "team_raw",
               "years_char_span", "years_raw")
    c.execute("UPDATE career_episode_a05 SET " + ",".join(f"{k}=?" for k in columns) + " WHERE episode_id=?",
              tuple(donor[k] for k in columns) + (fred["episode_id"],))
    return {"victim_episode": fred["episode_id"], "donor_episode": donor["episode_id"],
            "donor_person": donor["person_display"], "donor_pageid": donor["pageid"]}


def _relabel_display(c: sqlite3.Connection) -> dict[str, Any]:
    """Every row of one page that has no predecessor rows is relabelled as Fred Mariani: the page stays uniform and
    no predecessor contradicts it, so only the served row's own capture title can refuse it."""

    predecessor_pages = {row[0] for row in c.execute(
        "SELECT DISTINCT pageid FROM career_episode_a05 WHERE predecessor_episode_ids != '[]'")}
    page = next(row[0] for row in c.execute("SELECT DISTINCT pageid FROM career_episode_a05 ORDER BY pageid")
                if row[0] not in predecessor_pages)
    before = c.execute("SELECT DISTINCT person_display FROM career_episode_a05 WHERE pageid=?", (page,)).fetchall()
    count = c.execute("UPDATE career_episode_a05 SET person_display=? WHERE pageid=?", (FRED, page)).rowcount
    return {"pageid": page, "original_display": [row[0] for row in before], "relabelled_rows": count,
            "page_has_predecessor_rows": False}


def _relabel_qid(c: sqlite3.Connection) -> dict[str, Any]:
    page = c.execute("SELECT pageid, wikidata_qid FROM career_episode_a05 WHERE person_display=? LIMIT 1",
                     (FRED,)).fetchone()
    count = c.execute("UPDATE career_episode_a05 SET wikidata_qid=? WHERE pageid=?", ("Q1", page[0])).rowcount
    return {"pageid": page[0], "original_qid": page[1], "forged_qid": "Q1", "relabelled_rows": count}


def _swap_a04(c: sqlite3.Connection) -> dict[str, Any]:
    def pick(where: str, args: tuple[Any, ...], order: str) -> dict[str, Any]:
        for row in c.execute(f"SELECT * FROM career_episode_a05 WHERE a04_episode_ids != '[]' AND {where} ORDER BY {order}",
                             args):
            row = dict(row)
            ids = json.loads(row["a04_episode_ids"])
            mapped = c.execute("SELECT a05_episode_ids FROM career_a05_from_a04 WHERE a04_episode_id=?",
                               (ids[0],)).fetchone() if len(ids) == 1 else None
            if mapped and json.loads(mapped[0]) == [row["episode_id"]]:
                return row
        raise RuntimeError("no one-to-one Attempt 4 mapping for the challenge")

    victim = pick("person_display = ?", (FRED,), "episode_id")
    other = pick("person_display != ? AND pageid != ?", (FRED, victim["pageid"]), "episode_id DESC")
    ax, ay = json.loads(victim["a04_episode_ids"])[0], json.loads(other["a04_episode_ids"])[0]
    for child, mapped in ((victim, ay), (other, ax)):
        text = c.execute("SELECT disposition FROM career_a05_from_a04 WHERE a04_episode_id=?", (mapped,)).fetchone()[0]
        c.execute("UPDATE career_episode_a05 SET a04_episode_ids=?, a04_disposition=? WHERE episode_id=?",
                  (json.dumps([mapped]), text, child["episode_id"]))
    c.execute("UPDATE career_a05_from_a04 SET a05_episode_ids=? WHERE a04_episode_id=?",
              (json.dumps([other["episode_id"]]), ax))
    c.execute("UPDATE career_a05_from_a04 SET a05_episode_ids=? WHERE a04_episode_id=?",
              (json.dumps([victim["episode_id"]]), ay))
    return {"victim_episode": victim["episode_id"], "other_episode": other["episode_id"],
            "other_person": other["person_display"], "original_a04": ax, "forged_a04": ay}


#: This attempt's forgeries: (name, format, builder, expected refusal). Each is built on a copy restored from the
#: genuine file, resealed, pinned by its digest and served through the installed CLI for Fred Mariani.
A6_FORGERIES: tuple[tuple[str, str, Callable[[sqlite3.Connection], dict[str, Any]], str], ...] = (
    ("a05_cross_person_reciprocal_lineage", "A05",
     lambda c: _swap_parents(c, "career_episode_a05", "career_a05_disposition", copy_disposition=True),
     REFUSED_PREDECESSOR_IDENTITY),
    ("a05_wrong_family_edge", "A05", lambda c: _rename(c, "family", "PLAYING"), REFUSED_PREDECESSOR_IDENTITY),
    ("a05_wrong_revision_edge", "A05", lambda c: _rename(c, "revision", "1"), REFUSED_PREDECESSOR_IDENTITY),
    ("a05_unrelated_valid_raw_capture", "A05", _unrelated_capture, REFUSED_SOURCE_LOCATOR),
    ("a05_display_relabel_without_predecessor", "A05", _relabel_display, REFUSED_PAGE_IDENTITY),
    ("a05_wikidata_relabel", "A05", _relabel_qid, REFUSED_PAGE_IDENTITY),
    ("a05_cross_version_contradictory_mapping", "A05", _swap_a04, REFUSED_A04_IDENTITY),
    ("a04_cross_person_reciprocal_lineage", "A04",
     lambda c: _swap_parents(c, "career_episode_a04", "career_a04_disposition", copy_disposition=False),
     REFUSED_PREDECESSOR_IDENTITY),
)


def _restore(fixture: Path, source: Path) -> None:
    """Make ``fixture`` an exact copy of ``source`` by SQLite backup, writing no rollback journal: a journal of an
    in-place restore is about the size of the file (the FORGERY-SMOKE-02 bounded stop), and a scratch copy that is
    restored before every use needs none."""

    fixture.parent.mkdir(parents=True, exist_ok=True)
    genuine, target = _ro(source), sqlite3.connect(fixture)
    target.execute("PRAGMA journal_mode=OFF")
    genuine.backup(target)
    genuine.close()
    target.close()


def _open_fixture(fixture: Path) -> sqlite3.Connection:
    target = sqlite3.connect(fixture)
    target.execute("PRAGMA journal_mode=OFF")
    target.row_factory = sqlite3.Row
    return target


def missing_fixture_bytes() -> int:
    return sum(source.stat().st_size + LINEAGE_FIXTURE_MARGIN
               for fixture, source in ((LINEAGE_A05, A5_SUCCESSOR), (LINEAGE_A04, A4_SUCCESSOR))
               if not fixture.is_file())


def ensure_lineage_fixtures() -> dict[str, Any]:
    """The owned full copies the forgeries restore into; made once (SQLite backup of the genuine files)."""

    made = {}
    for path, source in ((LINEAGE_A05, A5_SUCCESSOR), (LINEAGE_A04, A4_SUCCESSOR)):
        made[str(path)] = "REUSED"
        if not path.is_file():
            _restore(path, source)
            made[str(path)] = "CREATED"
    return made


def _forgeries(run: LaneRun, installed: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {"fixtures": {"a05": str(LINEAGE_A05), "a04": str(LINEAGE_A04)},
                               "rule": ("each case restores its fixture from the genuine file by SQLite backup, "
                                        "changes it one way, reseals every ledger as a careful forger would, pins "
                                        "it by its digest and serves Fred Mariani through the installed CLI"),
                               "cases": {}}
    outdir = run.run_dir / "a6_forgeries"
    outdir.mkdir()
    for label, fmt, path, digest in (("a05_genuine", "A05", A5_SUCCESSOR, A5_SUCCESSOR_SHA256),
                                     ("a04_genuine", "A04", A4_SUCCESSOR, A4_SUCCESSOR_SHA256)):
        record = base._cli(run, installed, f"a6_{label}", ["--career", "--career-successor", path,
                                                          "--career-successor-sha256", digest, "--person", FRED,
                                                          "--compact"], save=outdir / f"{label}.json.gz")
        payload = base._gz_json(outdir / f"{label}.json.gz") or {}
        results["cases"][label] = {"format": fmt, "exit": record.get("exit_code"), "row_count": payload.get("row_count"),
                                   "expected": "SERVED", "holds": record.get("exit_code") == 0
                                   and bool(payload.get("row_count"))}
    for name, fmt, builder, code in A6_FORGERIES:
        fixture, source, tables = ((LINEAGE_A05, A5_SUCCESSOR, A05_TABLES) if fmt == "A05"
                                   else (LINEAGE_A04, A4_SUCCESSOR, A04_TABLES))
        _restore(fixture, source)
        target = _open_fixture(fixture)
        details = builder(target)
        _reseal(target, tables)
        target.commit()
        target.close()
        digest = sha256_file(fixture)
        record = base._cli(run, installed, f"a6_{name}", ["--career", "--career-successor", fixture,
                                                         "--career-successor-sha256", digest, "--person", FRED,
                                                         "--limit", "100", "--compact"], expect_exit=1)
        text = Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
        refusal = _refusal(text)
        results["cases"][name] = {"format": fmt, "exit": record.get("exit_code"), "expected": code,
                                  "refusal": refusal, "fixture_sha256": digest, "details": details,
                                  "holds": record.get("exit_code") == 1 and refusal == code}
        if refusal != code:
            run.problems.append(f"forgery {name} was not refused for its own cause: {refusal} (expected {code})")
    # Leave both fixtures as exact copies of the genuine files, as the next reuse expects.
    for fixture, source in ((LINEAGE_A05, A5_SUCCESSOR), (LINEAGE_A04, A4_SUCCESSOR)):
        _restore(fixture, source)
    results["holds"] = all(row["holds"] for row in results["cases"].values())
    results["genuine_unchanged"] = (sha256_file(A5_SUCCESSOR) == A5_SUCCESSOR_SHA256
                                    and sha256_file(A4_SUCCESSOR) == A4_SUCCESSOR_SHA256)
    if not results["genuine_unchanged"]:
        run.problems.append("a genuine successor changed during the forgeries")
    return results


def _served_identity(run: LaneRun) -> dict[str, Any]:
    """Every row the installed CLI served in full pagination, against the stored row's identity fields and the
    independent census (which re-read every raw capture)."""

    census = independent_identity_census(A5_SUCCESSOR, A4_SUCCESSOR, DELIVERED_DB)
    expected = census.pop("_identity_by_episode")
    served: dict[str, list[str]] = {}
    fields = ("pageid", "revision", "family", "page_title", "person_display", "wikidata_qid", "raw_file_sha256",
              "wikitext_sha256")
    for page in sorted((run.run_dir / "successor_pages").glob("career_successor_*.json.gz")):
        for row in (base._gz_json(page) or {}).get("rows") or []:
            served[str(row.get("episode_id"))] = [str(row.get(k)) for k in fields]
    differing = sorted(key for key in served if served[key] != expected.get(key))
    result = {"served_rows": len(served), "stored_rows": len(expected), "same_identities": set(served) == set(expected),
              "rows_whose_served_identity_differs": len(differing), "examples": differing[:5],
              "fields": list(fields), "census": census}
    result["holds"] = result["same_identities"] and not differing and census["holds"]
    return result


def _manager_a5_replays(run: LaneRun, installed: dict[str, Any]) -> None:
    """The manager's Attempt 5 probes against this wheel: its adversarial lineage and raw challenge (which must now
    refuse its two forgeries for their causes), its population audit and its semantic census."""

    run.exceptions.append("The manager's Attempt 5 probes start the installed bas-staff-query launcher (a native "
                          "executable) with their own minimal environment; the guard refuses a native child, so they "
                          "run without the lane guard. They open the delivered files read-only and write only in "
                          "their owned fixture directory and replay folder; the snapshots measure them.")
    venv = {f"V=Path(r'{A5_VENV_LITERAL}')": f"V=Path(r'{installed['venv']}')"}
    # 1. The adversarial challenge, in the owned fixture it was reproduced in (its copy is restored per case).
    MANAGER_ADVERSARIAL_FIXTURE.mkdir(parents=True, exist_ok=True)
    (MANAGER_ADVERSARIAL_FIXTURE / "temp").mkdir(exist_ok=True)
    copy, replay = a4._replay_from(run, MANAGER_A5, "successor_adversarial.py", adapt={
        f"F=Path(r'{MANAGER_A5_FIXTURE_LITERAL}')": f"F=Path(r'{MANAGER_ADVERSARIAL_FIXTURE}')",
        f"V=Path(r'{A5_VENV_LITERAL}');T=F/'adversarial.sqlite'":
            f"V=Path(r'{installed['venv']}');T=F/'adversarial.sqlite'"})
    record = run.run("manager_a5_successor_adversarial_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None), timeout=3600)
    review = _json_file(copy.parent / "SUCCESSOR_ADVERSARIAL_REVIEW.json") or {}
    cases = {row["case"]: {"exit": row.get("exit"), "row_count": row.get("row_count"),
                           "refusal": _refusal(row.get("stderr") or "")} for row in review.get("cases") or []}
    expected = {"A5-genuine": None, "A5-missing-row": REFUSED_DANGLING,
                "A5-missing-raw-independent": REFUSED_RAW_EVIDENCE_ABSENT, "A5-missing-spans": None,
                "A5-cross-person-reciprocal-lineage": REFUSED_PREDECESSOR_IDENTITY,
                "A5-other-person-raw-binding": REFUSED_SOURCE_LOCATOR}
    held = {label: ((cases.get(label) or {}).get("exit") == 0 and bool((cases.get(label) or {}).get("row_count")))
            if code is None else ((cases.get(label) or {}).get("exit") not in (0, None)
                                  and (cases.get(label) or {}).get("refusal") == code)
            for label, code in expected.items()}
    verdict = {**replay, "exit": record.get("exit_code"), "cases": cases, "expected": expected, "held": held,
               "subject_unchanged": review.get("subject_sha256_before") == review.get("subject_sha256_after")
               == A5_SUCCESSOR_SHA256,
               "meaning": ("The genuine successor and the copy with absent spans serve (absent fields are legitimate); "
                           "the missing row and missing raw evidence stay refused; the two forgeries that the Attempt 5 "
                           "consumer served are refused for their own causes.")}
    verdict["holds"] = verdict["subject_unchanged"] and all(held.values())
    run.extra["manager_a5_successor_adversarial"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's Attempt 5 adversarial challenge does not hold: {held}")
    # 2. The population audit: raw locators, lineage and full installed pagination against its own SQL.
    fixture = run.fresh("mgr_a5_population_fixture")
    (fixture / "temp").mkdir()
    temp_literal = (f"TEMP=r'{MANAGER_A5_FIXTURE_LITERAL}\\temp',TMP=r'{MANAGER_A5_FIXTURE_LITERAL}\\temp'")
    copy, replay = a4._replay_from(run, MANAGER_A5, "successor_population_audit.py", adapt={
        f"F=Path(r'{MANAGER_A5_FIXTURE_LITERAL}')": f"F=Path(r'{fixture}')", **venv,
        temp_literal: f"TEMP=r'{fixture}\\temp',TMP=r'{fixture}\\temp'"})
    record = run.run("manager_a5_successor_population_audit_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None), timeout=3 * 3600)
    lineage = _json_file(copy.parent / "SUCCESSOR_RAW_AND_LINEAGE.json") or {}
    pagination = _json_file(copy.parent / "SUCCESSOR_INSTALLED_PAGINATION.json") or {}
    verdict = {**replay, "exit": record.get("exit_code"), "rows": lineage.get("rows"),
               "raw_files": lineage.get("raw_files"), "raw_errors": len(lineage.get("raw_errors") or []),
               "lineage_errors": len(lineage.get("lineage_errors") or []),
               "complete_predecessor_set": lineage.get("complete_predecessor_set"),
               "all_columns_multiset_match": pagination.get("all_columns_multiset_match"),
               "served": pagination.get("served"), "missing": pagination.get("missing"), "extra": pagination.get("extra"),
               "filters": [{k: f.get(k) for k in ("case", "expected", "returned", "matches")}
                           for f in pagination.get("filters") or []]}
    # The raw-byte screen flags rows whose team text is legitimately absent (the manager adjudicated those); only
    # lineage, completeness and the served population are gates here.
    verdict["holds"] = (verdict["exit"] == 0 and verdict["rows"] == 72958 and verdict["lineage_errors"] == 0
                        and verdict["complete_predecessor_set"] is True
                        and verdict["all_columns_multiset_match"] is True
                        and all(f.get("matches") for f in verdict["filters"]))
    run.extra["manager_a5_successor_population_audit"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's Attempt 5 population audit does not hold: "
                            f"{ {k: v for k, v in verdict.items() if k != 'filters'} }")
    # 3. The semantic census (season templates, defensive passing-game units, named people).
    fixture = run.fresh("mgr_a5_census_fixture")
    (fixture / "temp").mkdir()
    copy, replay = a4._replay_from(run, MANAGER_A5, "career_semantic_census.py", adapt={
        f"V=Path(r'{A5_VENV_LITERAL}');F=Path(r'{MANAGER_A5_FIXTURE_LITERAL}')":
            f"V=Path(r'{installed['venv']}');F=Path(r'{fixture}')",
        temp_literal: f"TEMP=r'{fixture}\\temp',TMP=r'{fixture}\\temp'"})
    record = run.run("manager_a5_career_semantic_census_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None), timeout=3600)
    census = _json_file(copy.parent / "CAREER_SEMANTIC_CENSUS.json") or {}
    defensive = census.get("defensive_pass_game_rows") or []
    calls = [{"exit": row.get("exit"), "row_count": row.get("row_count")} for row in census.get("consumer_calls") or []]
    verdict = {**replay, "exit": record.get("exit_code"), "successor_sha256": census.get("successor_sha256"),
               "year_template_population": census.get("year_template_population"),
               "collapsed_to_first_year": census.get("collapsed_to_first_year"), "defensive_rows": len(defensive),
               "offense_mislabels": sum(1 for r in defensive if (r.get("assignment") or {}).get("unit") == "OFFENSE"),
               "consumer_calls": calls}
    collapsed = [r for r in census.get("range_rows") or [] if r.get("collapsed_to_first")]
    verdict["holds"] = (verdict["successor_sha256"] == A5_SUCCESSOR_SHA256 and bool(defensive)
                        and verdict["offense_mislabels"] == 0
                        and all(str(r.get("template_endpoint")) == str(r.get("start")) for r in collapsed)
                        and bool(calls) and all(c["exit"] == 0 and (c["row_count"] or 0) >= 1 for c in calls))
    run.extra["manager_a5_career_semantic_census"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's Attempt 5 semantic census does not hold: {verdict}")


def lane_installed_consumer_c01(run: LaneRun) -> None:
    run.extra["lineage_fixtures_prepared"] = ensure_lineage_fixtures()
    a5.lane_installed_consumer_c01(run)
    raw = run.extra.get("installed")
    if not raw:
        return
    installed = {key: Path(value) for key, value in raw.items()}
    run.extra["a6_forgeries"] = _forgeries(run, installed)
    served = _served_identity(run)
    run.extra["installed_identity_census"] = served
    if not served["holds"]:
        run.problems.append(f"the installed consumer's served identities do not agree with the independent census: "
                            f"{ {k: v for k, v in served.items() if k != 'census'} }")
    _manager_a5_replays(run, installed)


# ------------------------------------------------------------- the local integration candidate (MF37A05-02)


def _append_record() -> tuple[Path | None, dict[str, Any]]:
    records = sorted(CANDIDATE_RECORDS.glob("CANDIDATE_APPEND_*.json"))
    return (records[-1], _json_file(records[-1])) if records else (None, {})


def _negatives(run: LaneRun, head: str, repair: str) -> dict[str, Any]:
    """Changed, absent, stale and masked committed provenance, each built as a tree in a scratch repository that
    borrows the shared objects read-only, and each refused by the committed-blob proof for its own cause."""

    scratch = VALIDATION_ROOT / "cn" / sha256_bytes(run.stamp.encode("utf-8"))[:8]
    repo = scratch / "repo.git"
    common = Path(git_out("rev-parse", "--path-format=absolute", "--git-common-dir"))
    # The candidate's own object store as well (the same store for the granted candidate; a rehearsal's scratch
    # repository otherwise).
    own = Path(candidate.git("rev-parse", "--path-format=absolute", "--git-common-dir"))
    borrowed = list(dict.fromkeys((common / "objects").as_posix() for common in (common, own)))
    subprocess.run(["git", "init", "--bare", "--quiet", str(repo)], check=True, capture_output=True)
    (repo / "objects" / "info" / "alternates").write_text("".join(line + "\n" for line in borrowed), encoding="utf-8",
                                                         newline="\n")
    saved = candidate.REPO
    candidate.REPO = repo
    try:
        index = scratch / "negative.index"
        env = {**os.environ, "GIT_INDEX_FILE": str(index)}
        ordinary = "README.md"

        def tree_with(records: list[str]) -> str:
            """The candidate tree with index records applied through ``--index-info`` (which, unlike the other
            index edits, needs no work tree): ``<mode> <blob>\t<path>``, mode 0 removing the path."""

            candidate.git("read-tree", f"{head}^{{tree}}", env=env)
            candidate.git("update-index", "-z", "--index-info", env=env,
                          stdin="".join(record + "\0" for record in records))
            return candidate.git("write-tree", env=env)

        changed_blob = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), "hash-object", "-w", "--stdin"],
                                      input=b"a changed README the manifest does not know\n", capture_output=True,
                                      check=True).stdout.decode().strip()
        stale = {path: candidate.entry(repair, path) for path in candidate.PROVENANCE_FILES}
        trees = {
            "changed_committed_path": tree_with([f"100644 {changed_blob}\t{ordinary}"]),
            "absent_committed_path": tree_with([f"0 {'0' * 40}\t{ordinary}"]),
            "stale_generated_view": tree_with([f"{mode} {blob}\t{path}" for path, (mode, blob) in stale.items()]),
        }
        proofs = {name: candidate.verify_tree(tree) for name, tree in trees.items()}
        # Skip-worktree masking: the preserved first candidate, whose worktree held the stale control rows behind
        # skip-worktree entries absent on disk.
        proofs["skip_worktree_masked_first_candidate"] = candidate.verify_tree(candidate.ISSUED_CANDIDATE_HEAD)
    finally:
        candidate.REPO = saved
    expected = {
        "changed_committed_path": lambda p: p["manifest_rows_differing_from_blobs"] == [ordinary],
        "absent_committed_path": lambda p: p["manifest_absent_from_tree"] == [ordinary],
        "stale_generated_view": lambda p: not p["consistent"] and bool(p["manifest_rows_differing_from_blobs"]),
        "skip_worktree_masked_first_candidate": lambda p: not p["consistent"]
        and bool(p["manifest_rows_differing_from_blobs"]) and bool(p["manifest_absent_from_tree"]),
    }
    summary = {name: {"tree": proof["tree"], "consistent": proof["consistent"], "problems": proof["problems"],
                      "refused_for_its_cause": (not proof["consistent"]) and expected[name](proof)}
               for name, proof in proofs.items()}
    return {"scratch_repository": str(repo), "borrowed_objects": borrowed, "cases": summary,
            "holds": all(row["refused_for_its_cause"] for row in summary.values())}


def lane_local_integration_candidate(run: LaneRun) -> None:
    description = candidate.describe()
    run.extra["candidate"] = description
    head = description.get("candidate_head")
    record_path, record = _append_record()
    run.extra["candidate_append_record"] = {
        "file": str(record_path) if record_path else None, "sha256": sha256_file(record_path) if record_path else None,
        **{k: record.get(k) for k in ("candidate_commit", "candidate_tree", "previous_candidate_head", "repair_head",
                                      "refs_changed", "only_the_candidate_ref_changed", "previous_head_is_parent",
                                      "tree_differs_from_repair_in", "provenance_files", "validation_view")}}
    if not head or not record:
        run.problems.append("the appended local integration candidate or its record does not exist")
        return
    repair_head = run.binding["head"]
    proof = candidate.verify_tree(head)
    run.extra["committed_tree_proof"] = proof
    view = Path((record.get("validation_view") or {}).get("view") or "")
    generated = {path: {"view_sha256": sha256_file(view / path) if (view / path).is_file() else None,
                        "recorded_sha256": row.get("sha256"),
                        "committed_blob_sha256": sha256_bytes(subprocess.run(
                            ["git", "--no-optional-locks", "-C", str(candidate.REPO), "show", f"{head}:{path}"],
                            capture_output=True, check=False).stdout)}
                 for path, row in (record.get("provenance_files") or {}).items()}
    status = base.porcelain(CANDIDATE_WORKTREE)
    skip = git_out("ls-files", "-v", "--", *candidate.PROTECTED_PATHS, repo=CANDIDATE_WORKTREE).splitlines()
    checks = {
        "parent_is_the_preserved_candidate": description.get("candidate_parents") == [candidate.ISSUED_CANDIDATE_HEAD],
        "preserved_head_reachable": description.get("issued_head_is_ancestor") is True,
        "main_ref_unchanged": description.get("main_ref") == MAIN_SHA,
        "repair_branch_at_this_head": description.get("repair_head") == repair_head,
        "appended_from_this_repair_head": record.get("repair_head") == repair_head,
        "record_names_this_commit": record.get("candidate_commit") == head,
        "append_changed_only_the_candidate_ref": record.get("only_the_candidate_ref_changed") is True,
        "tree_differs_from_repair_only_in_protected_and_provenance":
            description.get("only_protected_and_provenance_paths_differ") is True,
        "protected_entries_equal_main": description.get("protected_paths_equal_main") is True
        and proof["protected_entries_equal_main"],
        "paid_workflow_absent": all(row["candidate"] is None for row in description.get("protected_paths") or []
                                    if row["path"].endswith("paid-scientific-review.yml")),
        "committed_provenance_agrees_with_committed_blobs": proof["consistent"],
        "provenance_is_the_canonical_generators_view": len(generated) == 3 and all(
            row["view_sha256"] == row["recorded_sha256"] == row["committed_blob_sha256"] for row in generated.values()),
        "protected_paths_never_written": not any((CANDIDATE_WORKTREE / p).exists() for p in candidate.PROTECTED_PATHS),
        "protected_entries_skip_worktree": bool(skip) and all(line[:1] == "S" for line in skip),
        "worktree_clean": not status,
        "worktree_head_is_candidate": git_out("rev-parse", "HEAD", repo=CANDIDATE_WORKTREE) == head,
    }
    run.extra["candidate_generated_view"] = generated
    run.extra["candidate_history_policy"] = policy = a5._history_policy(head)
    checks["history_policy"] = policy["holds"]
    run.extra["candidate_negatives"] = negatives = _negatives(run, head, repair_head)
    checks["negatives_refused"] = negatives["holds"]
    run.extra["candidate_tree_checks"] = checks
    for name, held in checks.items():
        if not held:
            run.problems.append(f"integration candidate: {name} does not hold")
    # The manager's Attempt 5 committed-tree probe, replayed against the appended candidate. It compares committed
    # manifest rows only for paths that differ from the repair tree, and needs a row for each: the paid workflow
    # (absent from both tree and manifest) and the two self-referential provenance files (excluded from the manifest
    # by configs/repository_policy.json) can have none. Those three are explained; every other path must agree.
    fixture = run.fresh("mgr_a5_integration_fixture")
    copy, replay = a4._replay_from(run, MANAGER_A5, "integration_and_storage.py", adapt={
        r"W=Path(r'C:\BatteredAggieSyndrome.data\ops\cycle37\attempt05');F=Path(r'C:\BatteredAggieSyndrome.validation\mr37a05-134703')":
            f"W=Path(r'{EVIDENCE_ROOT}');F=Path(r'{fixture}')"})
    record_run = run.run("manager_a5_integration_and_storage_replay", [run.python, "-B", copy], cwd=copy.parent,
                         env=run.env(guarded=False, pythonpath=None))
    review = _json_file(copy.parent / "INTEGRATION_MANIFEST_REVIEW.json") or {}
    explained = {"provenance/PROJECT_FILE_MANIFEST.csv": "excluded from the manifest by repository policy",
                 "provenance/PROJECT_FILE_HASHES.sha256": "excluded from the manifest by repository policy",
                 ".github/workflows/paid-scientific-review.yml": "absent from the committed tree and from the manifest"}
    rows = review.get("committed_tree_checks") or []
    unexplained = [row["path"] for row in rows if not row.get("consistent") and not (
        row["path"] in explained and (row["path"] != ".github/workflows/paid-scientific-review.yml"
                                      or (not row.get("committed_blob_exists") and not row.get("manifest"))))]
    verdict = {**replay, "exit": record_run.get("exit_code"), "candidate_head": review.get("candidate_head"),
               "changed_paths_from_repair": review.get("changed_paths_from_repair"),
               "probe_counted_inconsistent": [row["path"] for row in rows if not row.get("consistent")],
               "explained": explained, "unexplained": unexplained,
               "worktree_validator_findings": len(review.get("worktree_validator_findings") or [])}
    verdict["holds"] = review.get("candidate_head") == head and not unexplained
    run.extra["manager_a5_integration_replay"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's committed-tree probe finds unexplained mismatches: {unexplained}")
    _candidate_consumer(run, head, description)


def _candidate_consumer(run: LaneRun, head: str, description: dict[str, Any]) -> None:
    """The consumer built from the candidate's own committed tree, its suites from its worktree, and the withheld
    review controls characterized from an export of the candidate commit."""

    stage = PACKAGING_ROOT / "c" / sha256_bytes(run.stamp.encode("utf-8"))[:8]
    archive, export, dist, venv = stage / "source.tar", stage / "source", stage / "dist", stage / "venv"
    stage.mkdir(parents=True)
    run.run("git_archive_candidate", ["git", "--no-optional-locks", "-C", CANDIDATE_WORKTREE, "archive", "--format=tar",
                                      "-o", archive, head, "--", *base.BUILD_INPUTS], env=run.env())
    with tarfile.open(archive) as bundle:
        bundle.extractall(export, filter="data")
    run.run("build_candidate_wheel", [run.python, "-B", "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
                                      "--no-index", "--no-cache-dir", "--disable-pip-version-check", "-w", dist, export],
            cwd=stage, env=run.env(pythonpath=None), timeout=3600)
    wheels = sorted(dist.glob("aggie_analytics*.whl"))
    if not wheels:
        run.problems.append("no wheel was built from the candidate tree")
        return
    run.run("create_candidate_venv", [run.python, "-B", "-m", "venv", venv], cwd=stage, env=run.env(pythonpath=None))
    python = venv / "Scripts" / "python.exe"
    run.run("install_candidate_noneditable", [python, "-m", "pip", "install", "--no-deps", "--no-index", "--no-cache-dir",
                                              "--disable-pip-version-check", wheels[0], base.C01_WHEEL],
            cwd=stage, env=base._installed_env(run), timeout=1800)
    installed = {"stage": stage, "venv": venv, "python": python, "script": venv / "Scripts" / "bas-staff-query.exe",
                 "wheel": wheels[0]}
    pin = ["--career-successor", A5_SUCCESSOR, "--career-successor-sha256", A5_SUCCESSOR_SHA256]
    outdir = run.run_dir / "candidate_cli"
    outdir.mkdir()
    for name, args, expected in (("schema", ["--schema"], 0), ("bill_anderson_default", ["--person", a4.BILL], 0),
                                 ("cory_undlin_2018_successor", ["--career", "--person", "Cory Undlin", "--season",
                                                                 "2018", *pin], 0),
                                 ("refuse_wrong_pin", ["--career", "--career-successor", A5_SUCCESSOR,
                                                       "--career-successor-sha256", "0" * 64], 1)):
        base._cli(run, installed, f"candidate_{name}", args, expect_exit=expected, save=outdir / f"{name}.json.gz")
    # One of this attempt's forgeries through the candidate's consumer: the reciprocal cross-person swap, in the
    # owned lineage fixture the installed lane made (never a new copy here).
    if not LINEAGE_A05.is_file():
        run.problems.append("the owned lineage fixture is absent; run INSTALLED_CONSUMER_C01 first")
        return
    _restore(LINEAGE_A05, A5_SUCCESSOR)
    target = _open_fixture(LINEAGE_A05)
    details = _swap_parents(target, "career_episode_a05", "career_a05_disposition", copy_disposition=True)
    _reseal(target, A05_TABLES)
    target.commit()
    target.close()
    forged = base._cli(run, installed, "candidate_refuse_cross_person_swap",
                       ["--career", "--career-successor", LINEAGE_A05, "--career-successor-sha256",
                        sha256_file(LINEAGE_A05), "--person", FRED, "--compact"], expect_exit=1)
    refusal = _refusal(Path(forged["log_path"]).read_text(encoding="utf-8", errors="replace"))
    _restore(LINEAGE_A05, A5_SUCCESSOR)
    cory = (base._gz_json(outdir / "cory_undlin_2018_successor.json.gz") or {}).get("rows") or []
    site = venv / "Lib" / "site-packages"
    records = sorted(site.glob("aggie_analytics_engine-*.dist-info/RECORD"))
    listed = [line.split(",", 1)[0] for line in records[0].read_text(encoding="utf-8").splitlines()
              if line.startswith("aggie_analytics/") and not line.split(",", 1)[0].endswith(".pyc")] if records else []
    different = [name for name in listed
                 if sha256_bytes(subprocess.run(["git", "--no-optional-locks", "-C", str(CANDIDATE_WORKTREE), "show",
                                                 f"{head}:src/{name}"], capture_output=True, check=False).stdout)
                 != sha256_file(site / name)]
    consumer = {"wheel": str(wheels[0]), "wheel_sha256": sha256_file(wheels[0]), "installed_files": len(listed),
                "installed_differs_from_candidate_tree": different,
                "cory_2018_eagles": [(r.get("start"), r.get("end")) for r in cory
                                     if r.get("employer_display") == "Philadelphia Eagles"],
                "cross_person_swap": {"refusal": refusal, "expected": REFUSED_PREDECESSOR_IDENTITY, "details": details}}
    consumer["holds"] = (bool(listed) and not different and (2015, 2019) in [tuple(x) for x in consumer["cory_2018_eagles"]]
                         and refusal == REFUSED_PREDECESSOR_IDENTITY)
    run.extra["candidate_consumer"] = consumer
    if not consumer["holds"]:
        run.problems.append(f"the consumer built from the candidate tree does not hold: {consumer}")
    env = run.env(pythonpath=os.pathsep.join((str(CANDIDATE_WORKTREE), str(CANDIDATE_WORKTREE / "src"))))
    records_path = run.census_dir / "candidate_suites.records.jsonl"
    summary_path = run.census_dir / "candidate_suites.summary.json"
    run.run("candidate_suites", [run.python, "-B", "-m", "aggie_analytics.validation.unittest_census", *CANDIDATE_SUITES,
                                 "--records", records_path, "--summary", summary_path, "--selected-root",
                                 CANDIDATE_WORKTREE, "-v"], cwd=CANDIDATE_WORKTREE / "tests", kind="TEST", env=env,
            census=(records_path, summary_path), timeout=3600)
    # The two control compatibility errors: the candidate keeps main's review controls; the repair branch's tests
    # written for its own controls are characterized from an export of the candidate commit, never gated here.
    control_tar, control_root = stage / "control.tar", stage / "control"
    run.run("git_archive_candidate_controls", ["git", "--no-optional-locks", "-C", CANDIDATE_WORKTREE, "archive",
                                               "--format=tar", "-o", control_tar, head, "--", *a5.CONTROL_EXPORT],
            env=run.env())
    with tarfile.open(control_tar) as bundle:
        bundle.extractall(control_root, filter="data")
    control_env = run.env(pythonpath=os.pathsep.join((str(control_root), str(control_root / "src"))))
    script = ("import json, sys, unittest\n"
              "suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:])\n"
              "result = unittest.TextTestRunner(verbosity=0).run(suite)\n"
              "def cause(text):\n"
              "    lines = [line for line in text.strip().splitlines() if line.strip()]\n"
              "    return lines[-1][:300] if lines else ''\n"
              "print(json.dumps({'tests_run': result.testsRun, "
              "'failures': sorted(t.id() for t, _ in result.failures), "
              "'errors': sorted(t.id() for t, _ in result.errors), "
              "'causes': {t.id(): cause(text) for t, text in result.failures + result.errors}, "
              "'skipped': len(result.skipped)}))\n")
    control = run.run("candidate_review_control_characterization", [run.python, "-B", "-c", script, *a5.CONTROL_SUITES],
                      cwd=control_root / "tests", env=control_env,
                      note="Characterization only: the script reports outcomes and exits 0; the candidate keeps main's "
                           "review controls, and tests written for the repair branch's controls may fail against them.")
    outcome = base._stdout_json(control) or {}
    run.extra["candidate_review_control_characterization"] = {
        "suites": a5.CONTROL_SUITES, "exit": control.get("exit_code"), "outcome": outcome,
        "compatibility_errors": sorted((outcome.get("failures") or []) + (outcome.get("errors") or [])),
        "export": {"root": str(control_root), "paths": list(a5.CONTROL_EXPORT),
                   "protected_files_sha256": {path: (sha256_file(control_root / path) if (control_root / path).is_file()
                                                     else None) for path in candidate.PROTECTED_PATHS}},
        "withheld_paths": [row["path"] for row in description.get("protected_paths") or [] if row["repair"] != row["main"]],
        "disposition": "OWNER_DECISION",
        "meaning": ("The repair branch changed these review controls; the candidate keeps main's exact blobs because "
                    "changing trusted controls on main is an owner decision this contract does not grant. The tests "
                    "the branch wrote for its own controls fail against main's: that is the recorded effect of "
                    "withholding them. A candidate with these errors is not publication-ready.")}
    if base.porcelain(CANDIDATE_WORKTREE):
        run.problems.append("the candidate worktree changed during the lane")


# ------------------------------------------------------------- mounted, unmounted, platform and packet lanes


def _attempt5_final(lane: str) -> dict[str, Any]:
    rows = [json.loads(line) for line in (ATTEMPT5_ROOT / "lanes" / "RUNS.jsonl").read_text(encoding="utf-8")
            .splitlines() if line.strip()]
    rows = [row for row in rows if row["lane"] == lane and row["head"] == BASE_SHA]
    if not rows:
        return {}
    path = Path(rows[-1]["receipt"])
    return {"receipt": str(path), "receipt_sha256": sha256_file(path), "run": rows[-1]["run"],
            "result": rows[-1]["result"], "data": json.loads(path.read_text(encoding="utf-8"))}


def lane_full_final_mounted(run: LaneRun) -> None:
    base.lane_full_final_mounted(run)
    record = next(r for r in reversed(run.commands) if r.get("lane", "").endswith("full_suite_mounted"))
    log = Path(record["log_path"])
    final = base._log_identities(log)
    previous = _attempt5_final("FULL_FINAL_MOUNTED")
    comparison: dict[str, Any] = {"attempt5_receipt": previous.get("receipt"),
                                  "attempt5_receipt_sha256": previous.get("receipt_sha256"),
                                  "attempt5_run": previous.get("run"), "attempt5_result": previous.get("result")}
    if previous:
        a5_log = Path(next(c["log_path"] for c in previous["data"]["commands"]
                           if c["lane"].endswith("full_suite_mounted")))
        before = base._log_identities(a5_log)
        persisting = sorted(set(final["failed_or_errored"]) & set(before["failed_or_errored"]))
        new = sorted(set(final["failed_or_errored"]) - set(before["failed_or_errored"]))
        final_causes = base._failure_causes(log, persisting)
        before_causes = base._failure_causes(a5_log, persisting)
        comparison.update({
            "attempt5_log": str(a5_log), "attempt5_log_sha256": sha256_file(a5_log),
            "attempt5_tests_run": before["tests_run"], "final_tests_run": final["tests_run"],
            "attempt5_failed_or_errored": before["failed_or_errored"],
            "persisting": persisting, "new_in_attempt6": new,
            "no_longer_failing": sorted(set(before["failed_or_errored"]) - set(final["failed_or_errored"])),
            "new_failure_causes": base._failure_causes(log, new),
            "persisting_same_cause": sorted(i for i in persisting if final_causes[i] == before_causes[i]),
            "persisting_changed_cause": {i: {"attempt5": before_causes[i], "attempt6": final_causes[i]}
                                         for i in persisting if final_causes[i] != before_causes[i]},
        })
        if new:
            run.problems.append(f"new failing identities relative to Attempt 5: {new}")
    run.extra["attempt5_comparison"] = comparison


def lane_strict_mounted(run: LaneRun) -> None:
    base.lane_strict_mounted(run)
    final = [row["identity"] for row in run.extra.get("strict_findings") or []]
    previous = _attempt5_final("STRICT_MOUNTED")
    comparison: dict[str, Any] = {"attempt5_receipt": previous.get("receipt"), "attempt5_run": previous.get("run"),
                                  "attempt5_result": previous.get("result")}
    if previous:
        before = [row["identity"] for row in (previous["data"].get("details") or {}).get("strict_findings") or []]
        comparison.update({"attempt5_findings": before, "final_findings": final,
                           "persisting": sorted(set(final) & set(before)),
                           "new_in_attempt6": sorted(set(final) - set(before)),
                           "no_longer_reported": sorted(set(before) - set(final))})
        if comparison["new_in_attempt6"]:
            run.problems.append(f"new strict findings relative to Attempt 5: {comparison['new_in_attempt6']}")
    run.extra["attempt5_comparison"] = comparison


def lane_true_unmounted(run: LaneRun) -> None:
    base.lane_true_unmounted(run)


def lane_platform_carry(run: LaneRun) -> None:
    a4.lane_platform_carry(run)


def lane_final_packet(run: LaneRun) -> None:
    """Verify the frozen storage evidence and the packet; the operational ledger is not written here."""

    paths = run.extra["storage_paths"]
    verification: dict[str, Any] = {}
    checks = [(f"frozen_segment_{number}", ledger_path, snapshot_path)
              for number, (ledger_path, snapshot_path) in enumerate(FROZEN_SEGMENTS, 1)]
    checks.append(("operational_final", paths["operational_ledger"], paths["final_snapshot"]))
    for name, ledger_path, snapshot_path in checks:
        try:
            verification[name] = snapshot.verify(ledger_path, snapshot_path)
        except snapshot.SnapshotRefused as refusal:
            verification[name] = {"result": "REFUSED", "code": refusal.code, "detail": str(refusal)}
            run.problems.append(f"{name} snapshot does not verify: {refusal.code}")
    final_ledger = storage.Ledger(paths["final_output_ledger"])
    try:
        rows = final_ledger.records()
        init = final_ledger.config(rows)
        continues = json.loads(init.get("note") or "{}").get("continues_snapshot") or {}
        frozen = snapshot.load_snapshot(paths["final_snapshot"])
        open_now = final_ledger.open_reservations(rows)
        verification["final_output_ledger"] = {
            "ledger": str(final_ledger.path), "records": len(rows), "chain_intact": True,
            "continues_the_final_snapshot": continues.get("content_sha256") == frozen["content_sha256"],
            "budget_equals_snapshot_headroom": init["budget_bytes"] == frozen["measured"]["headroom_bytes"],
            "open_reservations": {k: v.get("operation") for k, v in open_now.items()},
            "only_this_lane_open": [v.get("operation") for v in open_now.values()] == [f"LANE FINAL_PACKET {run.stamp}"
                                                                                     + (" (rehearsal)" if run.rehearsal
                                                                                        else "")],
            "never_hashed_as_evidence": True}
        if not (verification["final_output_ledger"]["continues_the_final_snapshot"]
                and verification["final_output_ledger"]["budget_equals_snapshot_headroom"]
                and verification["final_output_ledger"]["only_this_lane_open"]):
            run.problems.append(f"the final-output ledger does not continue the final snapshot cleanly: "
                                f"{verification['final_output_ledger']}")
    except (storage.LedgerError, snapshot.SnapshotRefused, ValueError, KeyError) as error:
        verification["final_output_ledger"] = {"chain_intact": False, "error": str(error)}
        run.problems.append(f"the final-output ledger is not usable: {error}")
    run.extra["storage_verification"] = verification
    run.run("packet_consistency", [run.python, "-B", OUTPUTS_TOOL, "check", "--contract", run.contract_path,
                                   "--out-root", run.out_root, "--final-packet"],
            env=run.env(), note="Outputs, lane receipts at the final head, frozen storage evidence and the packet agree.")
    submission = run.out_root / "submission.json"
    if submission.is_file():
        run.run("cycle_protocol_submission_accounting",
                [run.python, "-B", base.GOVERNANCE / "cycle_protocol.py", "submission", run.contract_path, submission,
                 "--issuance", run.contract_path.parent / "issuance" / "issuance.json"],
                env=run.env(pythonpath=None), note="The v2.4.0 accounting check; it grants no acceptance.")
    else:
        run.problems.append("submission.json does not exist yet")


LANE_FUNCTIONS: dict[str, Callable[[LaneRun], None]] = {
    "START_CONTEXT": lane_start_context,
    "WRITE_PROTECTION": lane_write_protection,
    "STORAGE_ADMISSION": lane_storage_admission,
    "SOURCE_ADMISSION": lane_source_admission,
    "SOURCE_HARNESS": lane_source_harness,
    "SOURCE_REGRESSIONS": lane_source_regressions,
    "CAREER_SUCCESSOR": lane_career_successor,
    "INSTALLED_CONSUMER_C01": lane_installed_consumer_c01,
    "LOCAL_INTEGRATION_CANDIDATE": lane_local_integration_candidate,
    "TRUE_UNMOUNTED": lane_true_unmounted,
    "FULL_FINAL_MOUNTED": lane_full_final_mounted,
    "STRICT_MOUNTED": lane_strict_mounted,
    "PLATFORM_CARRY": lane_platform_carry,
    "FINAL_PACKET": lane_final_packet,
}


# ------------------------------------------------------------- the runner


def rehearse_candidate() -> dict[str, Any]:
    """Rehearsal only: bind the candidate lane to the scratch repository the append rehearsal
    (``attempt06_candidate.py rehearse``) prepared -- its own refs and objects, borrowing the shared ones read-only
    -- so the lane reads a scratch candidate appended exactly as the granted one is. The granted candidate is
    appended once, from the final head, and is never touched by a rehearsal."""

    global CANDIDATE_WORKTREE, CANDIDATE_RECORDS
    scratch = sorted(p for p in (VALIDATION_ROOT / "rc").iterdir()
                     if (p / "records" / "CANDIDATE_APPEND_REHEARSAL.json").is_file())[-1]
    candidate.REPO = scratch / "repo.git"
    candidate.CANDIDATE_WORKTREE = a5.CANDIDATE_WORKTREE = CANDIDATE_WORKTREE = scratch / "w"
    CANDIDATE_RECORDS = scratch / "records"
    base.GUARDED_ROOTS = base.GUARDED_ROOTS + (CANDIDATE_WORKTREE,)
    return {"scratch": str(scratch), "repository": str(candidate.REPO), "candidate_worktree": str(CANDIDATE_WORKTREE),
            "records": str(CANDIDATE_RECORDS),
            "meaning": "A rehearsal copy of the appended candidate; the granted append is made separately."}


def storage_paths(out_root: Path, rehearsal: bool) -> dict[str, Path]:
    """The ledgers and snapshots a lane uses. A FINAL_PACKET rehearsal gets its own tiny frozen operational ledger
    and final-output ledger under the rehearsal root, so the real operational ledger is never frozen by a rehearsal."""

    if not rehearsal:
        return {"operational_ledger": OPERATIONAL_LEDGER, "final_snapshot": FINAL_SNAPSHOT,
                "final_output_ledger": FINAL_OUTPUT_LEDGER}
    root = out_root / "storage-rehearsal" / utc_now().replace(":", "").replace("-", "").replace("+", "")[:22]
    root.mkdir(parents=True)
    (root / "data").mkdir()
    operational, frozen, final = root / "operational.jsonl", root / "OPERATIONAL_SNAPSHOT.json", root / "final.jsonl"
    ledger = storage.Ledger(operational)
    ledger.init(budget_bytes=64 * MIB, reserve_bytes=0, roots=[root / "data"], note="rehearsal operational ledger")
    token = ledger.reserve("rehearsal material work", 1024)["token"]
    (root / "data" / "work.bin").write_bytes(b"x" * 512)
    ledger.reconcile(token)
    snapshot.freeze(operational, frozen, label=f"{LABEL} REHEARSAL (not evidence)", scope="rehearsal only")
    snapshot.open_final(frozen, final, [str(root / "data")], reserve_bytes=0)
    return {"operational_ledger": operational, "final_snapshot": frozen, "final_output_ledger": final}


def main(argv: list[str] | None = None) -> int:
    rebind()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lane", required=True, choices=LANES)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--rehearsal", action="store_true",
                        help="Development only: write under the validation root, allow a dirty tree, spend no "
                             "request budget. A rehearsal receipt is labelled as such and is never evidence.")
    args = parser.parse_args(argv)
    out_root = args.out_root.resolve()
    issued_root = out_root
    if args.rehearsal:
        out_root = VALIDATION_ROOT / "rehearsal"
    run = LaneRun(args.lane, args.contract.resolve(), out_root)
    run.rehearsal = args.rehearsal
    console = Tee(run.run_dir / "lane.log", sys.stdout)
    sys.stdout = console
    print(f"{LABEL} lane {args.lane} run {run.stamp}" + (" (REHEARSAL, NOT EVIDENCE)" if args.rehearsal else ""))
    contract, contract_problems = load_contract(run.contract_path, args.lane, issued_root)
    run.contract = contract
    run.binding = bind_source()
    interpreter = base.bind_interpreter(run.python)
    blocked = list(contract_problems)
    if run.binding["branch"] != BRANCH:
        blocked.append(f"branch is {run.binding['branch']}, not {BRANCH}")
    if not run.binding["descends_from_base"]:
        blocked.append(f"head {run.binding['head']} does not descend from the issued base {BASE_SHA}")
    if not run.binding["clean"] and not args.rehearsal:
        blocked.append("the worktree is dirty; lanes run only at a committed subject")
    final_lane = args.lane == "FINAL_PACKET"
    # MF37A05-03: once the operational ledger is frozen, no material lane may allocate against it, and the final
    # packet runs only after that freeze, on its own final-output ledger.
    if FINAL_SNAPSHOT.is_file() and not final_lane:
        blocked.append(f"the operational ledger is frozen by {FINAL_SNAPSHOT.name}; material lanes are refused")
    if final_lane and not args.rehearsal and not (FINAL_SNAPSHOT.is_file() and FINAL_OUTPUT_LEDGER.is_file()):
        blocked.append("FINAL_PACKET runs only after the operational snapshot and the final-output ledger exist")
    if args.rehearsal and args.lane == "LOCAL_INTEGRATION_CANDIDATE":
        run.extra["rehearsal_scratch_candidate"] = rehearse_candidate()
    gate = None
    if args.lane in GATED:
        gate = a5.qualification(out_root, run.binding["head"], run.binding["guard_sha256"])
        if not gate["holds"]:
            blocked.append("WRITE_PROTECTION and STORAGE_ADMISSION have not both passed at this head with these guard "
                           f"bytes: {gate}")
    paths = storage_paths(out_root, args.rehearsal and final_lane) if not blocked else {}
    run.extra["storage_paths"] = {k: str(v) for k, v in paths.items()}
    ledger_path = paths.get("final_output_ledger") if final_lane else OPERATIONAL_LEDGER
    ledger = storage.Ledger(ledger_path) if ledger_path else None
    reservation = None
    if not blocked:
        estimate = LANE_ESTIMATES[args.lane]
        if args.lane == "INSTALLED_CONSUMER_C01":
            estimate += missing_fixture_bytes()
        try:
            reservation = ledger.reserve(f"LANE {args.lane} {run.stamp}" + (" (rehearsal)" if args.rehearsal else ""),
                                         estimate, note=f"head {run.binding['head']}")
        except storage.AdmissionRefused as refusal:
            blocked.append(f"storage admission refused the lane before any effect: {refusal.record.get('reason')}")
    before = base.scope_before()
    candidate_before = a5.candidate_state()
    if blocked:
        result, reason = BLOCKED, "; ".join(blocked)
        print(f"[{args.lane}] BLOCKED: {reason}")
    else:
        run.extra["storage_paths"] = {k: Path(v) for k, v in paths.items()}
        try:
            LANE_FUNCTIONS[args.lane](run)
        except (Exception, SystemExit) as error:  # noqa: BLE001 - a crashed lane is a recorded failure, never a pass
            import traceback

            traceback.print_exc(file=sys.stdout)
            run.problems.append(f"the lane raised {type(error).__name__}: {error}")
        run.extra["storage_paths"] = {k: str(v) for k, v in paths.items()}
        result, reason = base.decide(run, (contract.get("_lane") or {}).get("kind", "CHECK"))
    scope = base.scope_after(before)
    candidate_after = a5.candidate_state()
    after_binding = bind_source()
    if scope["writes_outside_owned_roots"]:
        result = FAIL
        reason = f"{reason}; {scope['writes_outside_owned_roots']} write(s) outside the owned roots"
    if not (scope["main_checkout"]["unchanged"] and scope["integration_worktree"]["unchanged"]):
        result = FAIL
        reason = f"{reason}; the main checkout or the old integration worktree changed during the lane"
    if candidate_before != candidate_after:
        result = FAIL
        reason = f"{reason}; the local integration candidate worktree changed during the lane"
    if after_binding["head"] != run.binding["head"] or after_binding["clean"] != run.binding["clean"] or (
            after_binding.get("dirty_entries") != run.binding.get("dirty_entries")):
        result = FAIL
        reason = f"{reason}; the worktree head or its working-tree state changed during the lane"
    validation = None
    if final_lane and not blocked:
        # The create-only validation receipt the terminal packet copies; written before this lane's reservation
        # closes, so the final-output ledger accounts for it. It is scoped to this run and never rewritten.
        validation = run.out_root / "evidence" / "final" / f"FINAL_PACKET_VALIDATION_{run.stamp}.json"
        validation.parent.mkdir(parents=True, exist_ok=True)
        with validation.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({
                "label": f"{LABEL} FINAL_PACKET {result}" + (" (REHEARSAL, NOT EVIDENCE)" if args.rehearsal else ""),
                "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
                "attempt_id": ATTEMPT_ID, "run": run.stamp, "result": result, "state_reason": reason,
                "subject": {k: run.binding.get(k) for k in ("branch", "head", "tree", "source_digest", "clean")},
                "contract_sha256": contract.get("_sha256"),
                "storage_verification": run.extra.get("storage_verification"),
                "commands": [{"name": c.get("lane"), "exit": c.get("exit_code"),
                              "result": c.get("result_against_expectation"), "log": c.get("log_path"),
                              "log_sha256": c.get("log_sha256")} for c in run.commands],
                "problems": run.problems, "written_at": utc_now(),
                "rule": ("Read only immutable inputs: the frozen snapshots (never a live ledger), the sealed outputs and "
                         "the lane receipts. This receipt is scoped to this run and written once; the final-output "
                         "ledger that accounts for it is never hashed as evidence."),
            }, indent=2, ensure_ascii=False, default=str) + "\n")
    reconciled = ledger.reconcile(reservation["token"], note=f"lane {result}") if reservation else None
    if reconciled and reconciled.get("underestimated"):
        reason = f"{reason}; the lane used {reconciled['operation_added_bytes']} bytes, past its reservation"
    guard_events = []
    if run.guard_log.is_file():
        guard_events = [json.loads(line) for line in run.guard_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    receipt = {
        "label": f"{LABEL} lane {args.lane} {result}" + (" (REHEARSAL, NOT EVIDENCE)" if args.rehearsal else ""),
        "rehearsal": args.rehearsal,
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID, "attempt_id": ATTEMPT_ID,
        "lane": args.lane, "kind": (contract.get("_lane") or {}).get("kind"), "run": run.stamp,
        "started_at": run.started, "finished_at": utc_now(), "result": result, "state_reason": reason,
        "contract": {"path": str(run.contract_path), "sha256": contract.get("_sha256"),
                     "issuance_contract_sha256": contract.get("_issuance_contract_sha256"),
                     "issued_command": (contract.get("_lane") or {}).get("command"),
                     "issued_cwd": (contract.get("_lane") or {}).get("cwd"),
                     "issued_environment": (contract.get("_lane") or {}).get("environment"),
                     "issued_data_binding": (contract.get("_lane") or {}).get("data_binding")},
        "invocation": {"argv": sys.argv, "cwd": os.getcwd()},
        "source_binding": run.binding, "source_binding_after": after_binding, "interpreter": interpreter,
        "qualification_gate": gate,
        "storage": {"ledger": str(ledger_path) if ledger_path else None, "reservation": reservation,
                    "reconcile": reconciled, "paths": {k: str(v) for k, v in paths.items()},
                    "final_snapshot_existed": FINAL_SNAPSHOT.is_file()},
        "final_packet_validation": {"path": str(validation), "sha256": sha256_file(validation)} if validation else None,
        "write_and_network_scope": {
            "guarded_roots": [str(root) for root in base.GUARDED_ROOTS],
            "writable_roots": [str(out_root), str(VALIDATION_ROOT), str(PACKAGING_ROOT)],
            "git_scratch_root": run.tmp_spelling,
            "network": "DENY_NON_LOOPBACK for guarded children", "credential_variables_removed": sorted(credential_scrub()),
            "temp_root": str(run.tmp), "temp_spelling_given_to_children": run.tmp_spelling,
            "exceptions": run.exceptions, "guard_events": len(guard_events),
            "guard_blocked_events": [row for row in guard_events if row.get("event") == "BLOCKED"][:100],
            "measurement": scope,
            "integration_candidate": {"before": candidate_before, "after": candidate_after,
                                      "unchanged": candidate_before == candidate_after},
            "confinement_statement": ("The guard refuses the write, child and network routes it audits; zero "
                                      "reported writes is not OS confinement, and the snapshots are the independent "
                                      "measurement."),
        },
        "counts": base.counts(run.commands),
        "commands": run.commands, "problems": run.problems, "details": run.extra,
        "lane_log": str(run.run_dir / "lane.log"),
    }
    print(f"[{args.lane}] {result}: {reason}")
    console.flush()
    receipt["lane_log_sha256_at_receipt"] = sha256_file(run.run_dir / "lane.log")
    digest = write_json(run.run_dir / "receipt.json", receipt)
    index = out_root / "lanes" / "RUNS.jsonl"
    with index.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({"lane": args.lane, "run": run.stamp, "result": result,
                                 "head": run.binding.get("head"), "source_digest": run.binding.get("source_digest"),
                                 "receipt": str(run.run_dir / "receipt.json"), "receipt_sha256": digest,
                                 "at": utc_now()}, sort_keys=True) + "\n")
    sys.stdout = console.stream
    console.handle.close()
    return 0 if result == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
