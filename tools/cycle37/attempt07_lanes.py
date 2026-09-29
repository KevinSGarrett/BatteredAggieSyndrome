r"""Cycle #37 — Attempt #7 — the lane runner (R37A07-05).

    attempt07_lanes.py --lane <ID> --contract <cycle_contract.json> --out-root <attempt root> [--rehearsal]

The preserved Attempt 6 runner (``attempt06_lanes``, over the Attempt 5, 4 and 3 runners) rebound to the Attempt 7
contract, roots and evidence. Everything the earlier runners bind per run is still bound -- the issued contract by
its sealed digest, the committed subject (branch, head, tree, source digest, descent from the issued base, a clean
tree before and after), the interpreter, module origins, the delivered database by digest, the data root and
``C:\All-22`` measured before and after, the main checkout and both integration worktrees, credential removal, and
the guard and storage qualification of the costly lanes. What Attempt 7 changes:

* **Storage (MF37A06-02).** Every material lane reserves on the Attempt 7 root ledger
  (``STORAGE_RESERVATIONS.jsonl``, identity Cycle 37 / Attempt 7). Once ``STORAGE_EVIDENCE_SNAPSHOT.json`` freezes it,
  every material lane is refused before any effect and FINAL_PACKET reserves on the root's claimed final-output
  continuation. ``storage_snapshot.chain`` proves the ledger chain in every lane that reads storage.
* **STORAGE_ADMISSION** adds the continuation suite, proves the chain, and replays the manager's Attempt 6 storage
  challenge twice: byte-faithful (its replayed continuation must now be refused where it opens) and instrumented
  (the refusal recorded as a result instead of a traceback).
* **WRITE_PROTECTION** adds the manager's Attempt 6 Git option challenge.
* **CAREER_SUCCESSOR (MF37A06-01)** adds the repaired verifier's source-field anchor bindings over the genuine
  successors and an independent raw-text anchor oracle (sqlite3/json/re only, no ``aggie_analytics``): each span is
  placed in the infobox parameter and list line of its own raw capture, every default, Attempt 4 and Attempt 4-to-
  default edge must share that source job, and intervals of an unrestructured field must fall in the same written
  segment. The oracle also reads the manager's saved same-page fixture and must find its crossed edges.
* **INSTALLED_CONSUMER_C01** adds this attempt's anchor forgeries -- the same-page cross-episode swap (both formats),
  a year-only and a team-only anchor substitution, two intervals of one field swapped (same role, different period),
  a cross-version anchor, an Attempt 4 file whose own lineage crosses, and a false restructure claim -- each restored
  from the genuine file, resealed and refused for its own cause through the console script *and* the module
  entrypoint; and the manager's Attempt 6 same-page challenge, which must now refuse.
* **LOCAL_INTEGRATION_CANDIDATE** verifies the Attempt 7 appends continue ``bb5253b2``, replays the manager's Attempt 6
  committed-tree review, and re-qualifies the private CONTROL-07 proposal offline at this head.
* **FULL_FINAL_MOUNTED / STRICT_MOUNTED** compare identities with the Attempt 6 final receipts at the issued base.

A lane decides what its commands did. It does not decide scientific acceptance, and it cannot turn an inherited red
lane green.
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt03_lanes as base  # noqa: E402  (the preserved Attempt 3 runner)
import attempt04_lanes as a4  # noqa: E402
import attempt05_lanes as a5  # noqa: E402
import attempt06_lanes as a6  # noqa: E402  (the preserved Attempt 6 runner)
import attempt06_candidate as a6c  # noqa: E402
import attempt07_candidate as candidate  # noqa: E402
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
)

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 7
CYCLE_ID = "CYCLE-37"
ATTEMPT_ID = "ATTEMPT-07-20260925"
RUNNER_VERSION = "BAS-C37-ATTEMPT07-LANES-v1"
BASE_SHA = "a2ce6b0827416772341af5575715b1735ffa29fd"
BRANCH = "codex/BAT-706-cycle37-rework"
LABEL = "Cycle #37 \u2014 Attempt #7 \u2014"
LANES = a6.LANES
GATED = a6.GATED
MIB = 1024 * 1024
#: Each lane's reservation, from the measured Attempt 6 costs with margin (INSTALLED_CONSUMER_C01 365 MB reusing its
#: fixtures, the candidate lane 116 MB, PLATFORM_CARRY 85 MB, CAREER_SUCCESSOR 23 MB) and this attempt's additions
#: (the anchor oracle's output, the CONTROL-07 matrices, one more fixture use).
LANE_ESTIMATES = {
    "START_CONTEXT": 16 * MIB, "WRITE_PROTECTION": 32 * MIB, "STORAGE_ADMISSION": 32 * MIB,
    "SOURCE_ADMISSION": 32 * MIB, "SOURCE_HARNESS": 32 * MIB, "SOURCE_REGRESSIONS": 32 * MIB,
    "CAREER_SUCCESSOR": 96 * MIB, "INSTALLED_CONSUMER_C01": 512 * MIB, "LOCAL_INTEGRATION_CANDIDATE": 256 * MIB,
    "TRUE_UNMOUNTED": 32 * MIB, "FULL_FINAL_MOUNTED": 64 * MIB, "STRICT_MOUNTED": 32 * MIB,
    "PLATFORM_CARRY": 160 * MIB, "FINAL_PACKET": 32 * MIB,
}

EVIDENCE_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt07"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a07")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37a07")
ATTEMPT6_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt06"
VALIDATION_A06 = Path(r"C:\BatteredAggieSyndrome.validation\c37a06")
PACKAGING_A06 = Path(r"C:\BatteredAggieSyndrome.packaging\c37a06")
MANAGER_A6 = DATA_ROOT / "ops" / "manager_reviews" / "cycle37" / "attempt06" / "review-20260925T205004Z"
MANAGER_A6_FIXTURE_LITERAL = r"C:\BatteredAggieSyndrome.validation\mr37a06-205004"
A6_VENV_LITERAL = r"C:\BatteredAggieSyndrome.packaging\c37a06\b\edadaddf\venv"
A5_SUCCESSOR = a6.A5_SUCCESSOR
A5_SUCCESSOR_SHA256 = a6.A5_SUCCESSOR_SHA256
A4_SUCCESSOR = a6.A4_SUCCESSOR
A4_SUCCESSOR_SHA256 = a6.A4_SUCCESSOR_SHA256
OPERATIONAL_LEDGER = EVIDENCE_ROOT / "STORAGE_RESERVATIONS.jsonl"
FINAL_SNAPSHOT = EVIDENCE_ROOT / "STORAGE_EVIDENCE_SNAPSHOT.json"
FINAL_OUTPUT_LEDGER = EVIDENCE_ROOT / "evidence" / "storage" / "STORAGE_RESERVATIONS_FINAL_OUTPUT.jsonl"
CANDIDATE_RECORDS = EVIDENCE_ROOT / "evidence" / "integration"
BEFORE_REPRODUCTION = EVIDENCE_ROOT / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
SAVED_SAME_PAGE_FIXTURE = VALIDATION_ROOT / "before" / "lineage" / "fixture" / "same-page-lineage.sqlite"
SAVED_SAME_PAGE_SHA256 = "e902f3909f8a88a93af6ed003dd0b3947521092dbc06dddec836c14c96243324"
FIXTURES = VALIDATION_ROOT / "fixtures"
#: One owned full copy of each genuine successor, restored before every use (no rollback journal). The Attempt 5
#: copy is also the manager replays' working copy, so the lane holds one 205 MB file, not three.
MANAGER_ADVERSARIAL_FIXTURE = FIXTURES / "mr"
LINEAGE_A05 = MANAGER_ADVERSARIAL_FIXTURE / "adversarial.sqlite"
LINEAGE_A04 = FIXTURES / "lineage" / "successor_a04.sqlite"
CANDIDATE_WORKTREE = a6c.CANDIDATE_WORKTREE
CANDIDATE_BRANCH = a6c.CANDIDATE_BRANCH
MAIN_SHA = a6c.MAIN_SHA
GUARD = a6.GUARD
AFTER_COMMENTS = (("BAT-706", "C37-A07-AFTER-HANDOFF-BAT-706"), ("BAT-708", "C37-A07-AFTER-HANDOFF-BAT-708"))
PLATFORM_TOOL = "tools/cycle37/attempt07_platform.py"
OUTPUTS_TOOL = "tools/cycle37/attempt07_outputs.py"
CONTROL_TOOL = Path(__file__).resolve().parent / "attempt07_control07.py"
FRED = a6.FRED
A7_SUITES = ("test_cycle37_a07_storage_continuation", "test_cycle37_a07_source_anchor")
STORAGE_SUITES = a6.STORAGE_SUITES + ("test_cycle37_a07_storage_continuation",)
CAREER_SUITES = a6.CAREER_SUITES + ("test_cycle37_a07_source_anchor",)
REGRESSION_SUITES = a6.REGRESSION_SUITES + A7_SUITES
CANDIDATE_SUITES = a6.CANDIDATE_SUITES + A7_SUITES

REFUSED_EPISODE = "REFUSED_CAREER_SUCCESSOR_EPISODE_ANCHOR_MISMATCH"
REFUSED_TEAM = "REFUSED_CAREER_SUCCESSOR_TEAM_ANCHOR_MISMATCH"
REFUSED_YEARS = "REFUSED_CAREER_SUCCESSOR_YEARS_ANCHOR_MISMATCH"
REFUSED_PERIOD = "REFUSED_CAREER_SUCCESSOR_PERIOD_ANCHOR_MISMATCH"
REFUSED_RESTRUCTURE = "REFUSED_CAREER_SUCCESSOR_RESTRUCTURE_CLAIM_MISMATCH"
REFUSED_A04_ANCHOR = "REFUSED_CAREER_SUCCESSOR_A04_ANCHOR_MISMATCH"
REFUSED_CROSS_VERSION = "REFUSED_CAREER_SUCCESSOR_CROSS_VERSION_LINEAGE_MISMATCH"
REFUSED_CLAIMED = "REFUSED_CONTINUATION_ALREADY_CLAIMED"


def rebind() -> None:
    """Point the preserved runners at the Attempt 7 contract, roots, ledger, suites and grants."""

    for name, value in (("ATTEMPT_NUMBER", ATTEMPT_NUMBER), ("ATTEMPT_ID", ATTEMPT_ID),
                        ("RUNNER_VERSION", RUNNER_VERSION), ("BASE_SHA", BASE_SHA), ("LABEL", LABEL),
                        ("EVIDENCE_ROOT", EVIDENCE_ROOT), ("VALIDATION_ROOT", VALIDATION_ROOT),
                        ("PACKAGING_ROOT", PACKAGING_ROOT), ("AFTER_COMMENTS", AFTER_COMMENTS),
                        ("PLATFORM_TOOL", PLATFORM_TOOL), ("OUTPUTS_TOOL", OUTPUTS_TOOL),
                        ("STORAGE_SUITES", STORAGE_SUITES), ("CAREER_SUITES", CAREER_SUITES),
                        ("REGRESSION_SUITES", REGRESSION_SUITES), ("CANDIDATE_SUITES", CANDIDATE_SUITES),
                        ("OPERATIONAL_LEDGER", OPERATIONAL_LEDGER), ("FINAL_SNAPSHOT", FINAL_SNAPSHOT),
                        ("FINAL_OUTPUT_LEDGER", FINAL_OUTPUT_LEDGER), ("FROZEN_SEGMENTS", ()),
                        ("CANDIDATE_RECORDS", CANDIDATE_RECORDS), ("BEFORE_REPRODUCTION", BEFORE_REPRODUCTION),
                        ("BEFORE_INTERRUPTED", EVIDENCE_ROOT / "evidence" / "before"), ("FIXTURES", FIXTURES),
                        ("LINEAGE_A05", LINEAGE_A05), ("LINEAGE_A04", LINEAGE_A04),
                        ("MANAGER_ADVERSARIAL_FIXTURE", MANAGER_ADVERSARIAL_FIXTURE),
                        ("LANE_ESTIMATES", LANE_ESTIMATES)):
        setattr(a6, name, value)
    a6.rebind()
    a6._append_chain = _append_chain
    a6c.SCRATCH = candidate.SCRATCH
    base.CYCLE_ID = CYCLE_ID
    # Attempt 6's own roots are now denied writes: guarded like every earlier attempt's.
    base.GUARDED_ROOTS = tuple(dict.fromkeys(base.GUARDED_ROOTS + (VALIDATION_A06, PACKAGING_A06)))


LaneRun = a6.LaneRun


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
        problems.append("contract is not Cycle 37 Attempt 7")
    if contract.get("attempt_id") != ATTEMPT_ID:
        problems.append(f"contract attempt_id {contract.get('attempt_id')!r} is not {ATTEMPT_ID}")
    if (contract.get("repo") or {}).get("base_sha") != BASE_SHA:
        problems.append(f"contract base {(contract.get('repo') or {}).get('base_sha')} is not {BASE_SHA}")
    row = {r["id"]: r for r in contract.get("required_lanes", [])}.get(lane)
    if row is None or row.get("executor") != "worker":
        problems.append(f"{lane} is not a worker lane of this contract")
    elif f"attempt07_lanes.py --lane {lane} " not in row.get("command", ""):
        problems.append(f"the contract's command for {lane} does not invoke this runner for this lane")
    if os.path.normcase(str(out_root)) != os.path.normcase(str(Path(contract["paths"]["evidence_root"]))):
        problems.append(f"out-root {out_root} is not the contract evidence root {contract['paths']['evidence_root']}")
    contract["_sha256"] = digest
    contract["_issuance_contract_sha256"] = recorded
    contract["_lane"] = row
    return contract, problems


def bind_source() -> dict[str, Any]:
    binding = a6.bind_source()
    runner = Path(__file__).resolve()
    binding.update({
        "base": BASE_SHA,
        "descends_from_base": base.git("merge-base", "--is-ancestor", BASE_SHA, binding["head"]).returncode == 0
        if binding.get("head") else False,
        "commits_after_base": git_out("rev-list", "--count", f"{BASE_SHA}..{binding['head']}") if binding.get("head")
        else None,
        "runner": str(runner), "runner_sha256": sha256_file(runner), "runner_version": RUNNER_VERSION,
        "rebound_attempt6_runner_sha256": sha256_file(Path(a6.__file__).resolve()),
        "candidate_tool_sha256": sha256_file(Path(candidate.__file__).resolve()),
        "control07_tool_sha256": sha256_file(CONTROL_TOOL),
        "storage_tool_sha256": sha256_file(Path(storage.__file__).resolve()),
        "snapshot_tool_sha256": sha256_file(Path(snapshot.__file__).resolve()),
    })
    return binding


def _json_file(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).is_file() else None


def _refusal(text: str) -> str | None:
    return a6._refusal(text)


def _replay(run: LaneRun, directory: Path, script: str, name: str,
            adapt: dict[str, str] | None = None) -> tuple[Path, dict[str, Any]]:
    """``attempt04_lanes._replay_from`` under a folder name of the caller's choosing, so one saved probe can be
    replayed more than once in a lane (each literal still replaced exactly once)."""

    source = directory / script
    original = source.read_bytes()
    text = original.decode("utf-8")
    changes = []
    for old, new in (adapt or {}).items():
        if text.count(old) != 1:
            raise RuntimeError(f"{script}: the literal to adapt occurs {text.count(old)} times, not once")
        text = text.replace(old, new)
        changes.append({"from": old, "to": new})
    target = run.fresh(f"replay_{name}") / script
    target.write_bytes(text.encode("utf-8"))
    return target, {"manager_original": str(source), "manager_original_sha256": sha256_bytes(original),
                    "replay_copy": str(target), "replay_copy_sha256": sha256_file(target),
                    "byte_identical": not changes, "literal_adaptations": changes}


# ------------------------------------------------------------- storage (MF37A06-02)


def storage_state() -> dict[str, Any]:
    """The attempt's ledger chain proved back to its root, the operational ledger's status, and every record's
    identity. Nothing here writes a ledger."""

    live = FINAL_OUTPUT_LEDGER if FINAL_OUTPUT_LEDGER.is_file() else OPERATIONAL_LEDGER
    state: dict[str, Any] = {"live_ledger": str(live)}
    try:
        state["chain"] = snapshot.chain(live)
    except snapshot.SnapshotRefused as refusal:
        state["chain"] = {"result": "REFUSED", "code": refusal.code, "detail": str(refusal)}
    ledger = storage.Ledger(OPERATIONAL_LEDGER)
    try:
        rows = ledger.records()
        status = ledger.status()
        state["operational"] = {"ledger": str(OPERATIONAL_LEDGER), "chain_intact": True, "records": len(rows),
                                "identities": sorted({(r.get("cycle_number"), r.get("attempt_number")) for r in rows}),
                                **{k: status.get(k) for k in ("identity", "segment", "budget_bytes", "reserve_bytes",
                                                              "added_bytes", "headroom_bytes", "free_bytes",
                                                              "open_reservations", "bounded_stop", "refused",
                                                              "underestimated", "continued_by")}}
    except storage.LedgerError as error:
        state["operational"] = {"ledger": str(OPERATIONAL_LEDGER), "chain_intact": False, "error": str(error)}
    state["final_snapshot_exists"] = FINAL_SNAPSHOT.is_file()
    if FINAL_SNAPSHOT.is_file():
        try:
            state["final_snapshot"] = snapshot.verify(OPERATIONAL_LEDGER, FINAL_SNAPSHOT, allow_refused=True)
        except snapshot.SnapshotRefused as refusal:
            state["final_snapshot"] = {"result": "REFUSED", "code": refusal.code, "detail": str(refusal)}
    return state


def _storage_problems(state: dict[str, Any]) -> list[str]:
    problems = []
    if (state.get("chain") or {}).get("result") != "PASS":
        problems.append(f"the storage chain does not prove: {state.get('chain')}")
    segment = state["operational"]
    if not segment.get("chain_intact"):
        problems.append(f"the operational ledger is not usable: {segment.get('error')}")
    else:
        if segment.get("identities") != [(CYCLE_NUMBER, ATTEMPT_NUMBER)]:
            problems.append(f"operational records carry identities {segment.get('identities')}, not Cycle 37 Attempt 7")
        if segment.get("bounded_stop"):
            problems.append(f"the operational ledger records a bounded stop: {segment['bounded_stop']}")
        if int(segment.get("added_bytes") or 0) > int(segment.get("budget_bytes") or 0):
            problems.append("the attempt's measured added bytes exceed its budget")
    if state.get("final_snapshot") and state["final_snapshot"].get("result") != "PASS":
        problems.append(f"the final snapshot does not verify: {state['final_snapshot']}")
    return problems


# ------------------------------------------------------------- lanes: context, guard, storage


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
        "MF37A06-01": (reproduction.get("MF37A06-01") or {}).get("reproduced"),
        "MF37A06-02": (reproduction.get("MF37A06-02") or {}).get("reproduced")}
    if not reproduction.get("reproduced"):
        run.problems.append("the before-repair reproduction is missing or did not reproduce the findings")
    run.extra["guard"] = {"path": str(GUARD), "sha256": sha256_file(GUARD)}
    run.extra["integration_candidate"] = {"state": a5.candidate_state(), "description": candidate.describe()}
    proposed = EVIDENCE_ROOT / "evidence" / "control07" / "proposed"
    run.extra["control07_proposal_inputs"] = {
        "root": str(proposed), "files": {p.relative_to(proposed).as_posix(): sha256_file(p)
                                         for p in sorted(proposed.rglob("*")) if p.is_file()},
        "outside_every_checkout": all(checkout not in proposed.parents
                                      for checkout in (a6c.WORKTREE, CANDIDATE_WORKTREE, base.MAIN_CHECKOUT))}
    run.extra["platform_receipts"] = sorted(str(p.relative_to(EVIDENCE_ROOT)) for p in
                                            (EVIDENCE_ROOT / "evidence" / "platform").rglob("*.json"))


def lane_write_protection(run: LaneRun) -> None:
    a6.lane_write_protection(run)
    # The manager's Attempt 6 guarded Git option challenge, in an owned fixture root.
    fixture = run.fresh("mgr_a6_git_option_fixture")
    (fixture / "temp").mkdir()
    copy, replay = a4._replay_from(run, MANAGER_A6, "git_option_challenge_v2.py", adapt={
        f'F=pathlib.Path(r"{MANAGER_A6_FIXTURE_LITERAL}")': f'F=pathlib.Path(r"{fixture}")'})
    record = run.run("manager_a6_git_option_challenge_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None),
                     note="The manager's saved probe, fixture root adapted; it installs the guard in its own child.")
    result = _json_file(copy.parent / "GIT_OPTION_CHALLENGE_V2.json") or {}
    cases = json.loads(result.get("stdout") or "[]") if str(result.get("stdout") or "").startswith("[") else []
    by_label = {row.get("label"): row for row in cases if isinstance(row, dict) and row.get("label")}
    ordinary = next((row for row in cases if isinstance(row, dict) and "ordinary_write_refused" in row), {})
    refused = {label: bool((by_label.get(label) or {}).get("refused")) or (by_label.get(label) or {}).get("exit") not in (0, None)
               for label in ("protected_attached_file", "protected_attached_file_abbreviated_unset")}
    verdict = {**replay, "exit": record.get("exit_code"), "child_exit": result.get("exit"),
               "protected_bytes_unchanged": result.get("protected_bytes_unchanged"),
               "ordinary_write_refused": ordinary.get("ordinary_write_refused"),
               "owned_positive_exit": (by_label.get("owned_positive") or {}).get("exit"),
               "protected_writes_refused": refused, "cases": cases}
    verdict["holds"] = (verdict["protected_bytes_unchanged"] is True and verdict["ordinary_write_refused"] is True
                        and verdict["owned_positive_exit"] == 0 and all(refused.values()))
    run.extra["manager_a6_git_option_challenge"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's Attempt 6 Git option challenge does not hold: "
                            f"{ {k: v for k, v in verdict.items() if k != 'cases'} }")


def _manager_a6_storage(run: LaneRun) -> dict[str, Any]:
    """The manager's Attempt 6 storage challenge against the repaired tools: once byte-faithful (only its fixture root
    adapted; its replayed continuation must now be refused where it opens), once instrumented to record that
    refusal as a result."""

    opened = ("replay=F/'replayed-child.jsonl';init=ss.open_successor(snapshot,replay,[str(root)],"
              "kind='restart continuation',scope='retry after restart')\nRC=sa.Ledger(replay)")
    out: dict[str, Any] = {}
    for mode in ("faithful", "instrumented"):
        fixture = run.fresh(f"mgr_a6_storage_{mode}")
        adapt = {f"F=Path(r'{MANAGER_A6_FIXTURE_LITERAL}\\storage-challenge')": f"F=Path(r'{fixture}\\storage-challenge')"}
        if mode == "instrumented":
            # The refusal at open recorded as the replay's result, where the original script expects a decision.
            adapt[opened] = (
                "replay=F/'replayed-child.jsonl'\n"
                "try:init=ss.open_successor(snapshot,replay,[str(root)],kind='restart continuation',"
                "scope='retry after restart')\n"
                "except ss.SnapshotRefused as e:init={'refused_at_open':e.code}\n"
                "RC=None if init.get('refused_at_open') else sa.Ledger(replay)")
            adapt["try:\n admitted=RC.reserve('REPLAYED_200KB',200000)"] = (
                "try:\n if RC is None:raise sa.AdmissionRefused({'reason':init['refused_at_open']})\n"
                " admitted=RC.reserve('REPLAYED_200KB',200000)")
        copy, replay = _replay(run, MANAGER_A6, "storage_challenge.py", f"mgr_a6_storage_challenge_{mode}", adapt)
        record = run.run(f"manager_a6_storage_challenge_{mode}", [run.python, "-B", copy], cwd=copy.parent,
                         env=run.env(guarded=False, pythonpath=None), expect_exit=1 if mode == "faithful" else 0,
                         note="The manager's saved challenge; it imports this worktree's storage tools.")
        text = Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
        raised = [line for line in text.splitlines() if "SnapshotRefused:" in line]
        codes = re.findall(r"REFUSED_[A-Z_]+", raised[-1]) if raised else []
        review = _json_file(copy.parent / "STORAGE_CONTINUATION_CHALLENGE.json") or {}
        row = {**replay, "exit": record.get("exit_code"), "refusal": codes[0] if codes else None,
               "challenge_json": review or None, "replay_child_created": (fixture / "storage-challenge" /
                                                                          "replayed-child.jsonl").exists()}
        if mode == "faithful":
            row["holds"] = row["exit"] != 0 and row["refusal"] == REFUSED_CLAIMED and not row["replay_child_created"]
        else:
            result = review.get("replayed_snapshot_new_child") or {}
            row["holds"] = (review.get("single_child_correctly_refused_over_budget") is True
                            and result.get("decision") == "REFUSED" and REFUSED_CLAIMED in str(result.get("reason"))
                            and review.get("snapshot_sha256_unchanged") is True
                            and review.get("tampered_snapshot") == snapshot.REFUSED_TAMPERED)
        out[mode] = row
    out["holds"] = all(row["holds"] for row in out.values() if isinstance(row, dict))
    return out


def lane_storage_admission(run: LaneRun) -> None:
    run.census("storage_suites", STORAGE_SUITES,
               note="Admission (admitted, too large, cumulative, concurrent, free reserve, underestimate, bounded stop, "
                    "restart, orphan/explicit holders, broken chain, no deletion), the snapshot separation, and the "
                    "Attempt 7 continuation authority (replay, a four-process race, restart, wrong attempt/root, "
                    "post-freeze growth, truncation, tamper, open reservation, stale parent), each on owned fixtures.")
    before = storage_state()
    ledger = storage.Ledger(OPERATIONAL_LEDGER)
    status = ledger.status()
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
    run.extra["storage_ledger"] = {
        "operational_ledger": str(OPERATIONAL_LEDGER), "records": len(rows),
        **{k: status.get(k) for k in ("identity", "segment", "budget_bytes", "reserve_bytes", "added_bytes",
                                      "headroom_bytes", "free_bytes", "bounded_stop")},
        "live_over_budget_control": live,
        "lane_reservation_pairs": {"lane_reservations": len(lanes),
                                   "admitted": sum(1 for r in lanes if r["decision"] == "ADMITTED"),
                                   "admitted_and_reconciled": sum(1 for r in lanes if r["decision"] == "ADMITTED"
                                                                  and r["token"] in reconciled)},
        "chain_before": before["chain"], "chain_after": after["chain"],
        "records_carry_cycle37_attempt7": after["operational"].get("identities") == [(CYCLE_NUMBER, ATTEMPT_NUMBER)],
        "attempt6_ledgers_retained": {p.name: sha256_file(p) for p in sorted((ATTEMPT6_ROOT / "evidence" / "storage")
                                                                            .glob("*.jsonl")) + [ATTEMPT6_ROOT / "STORAGE_RESERVATIONS.jsonl"]},
    }
    if not live["refused"]:
        run.problems.append("an over-budget reservation was admitted on the operational ledger")
    run.problems.extend(_storage_problems(after))
    # The manager's Attempt 5 independent challenge (kept) and Attempt 6 continuation challenge (MF37A06-02).
    fixture = run.fresh("mgr_a5_storage_fixture")
    copy, replay = a4._replay_from(run, a6.MANAGER_A5, "storage_independent.py", adapt={
        f"F=Path(r'{a6.MANAGER_A5_FIXTURE_LITERAL}')/'storage-proof'": f"F=Path(r'{fixture}')/'storage-proof'"})
    record = run.run("manager_a5_storage_independent_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(pythonpath=None), note="The manager's saved Attempt 5 storage challenge.")
    review = _json_file(copy.parent / "STORAGE_INDEPENDENT_REVIEW.json") or {}
    results = review.get("results") or []
    a5_verdict = {**replay, "exit": record.get("exit_code"),
                  "positive_readback": (results[0] if results else {}).get("operation_added_bytes"),
                  "concurrent": (results[1] if len(results) > 1 else {}).get("decision"),
                  "restart_added": (review.get("restart") or {}).get("added_bytes"),
                  "underestimated": (results[2] if len(results) > 2 else {}).get("underestimated"),
                  "after_bounded_stop": (results[3] if len(results) > 3 else {}).get("decision")}
    a5_verdict["holds"] = (a5_verdict["positive_readback"] == 2000 and a5_verdict["concurrent"] == "REFUSED"
                           and a5_verdict["restart_added"] == 2000 and a5_verdict["underestimated"] is True
                           and a5_verdict["after_bounded_stop"] == "REFUSED")
    run.extra["manager_a5_storage_independent"] = a5_verdict
    if not a5_verdict["holds"]:
        run.problems.append(f"the manager's Attempt 5 storage challenge does not hold: {a5_verdict}")
    a6_verdict = _manager_a6_storage(run)
    run.extra["manager_a6_storage_continuation"] = a6_verdict
    if not a6_verdict["holds"]:
        run.problems.append(f"the manager's Attempt 6 storage challenge does not hold against the repaired tools: "
                            f"{a6_verdict}")


def lane_source_admission(run: LaneRun) -> None:
    a5.lane_source_admission(run)


def lane_source_harness(run: LaneRun) -> None:
    a5.lane_source_harness(run)


def lane_source_regressions(run: LaneRun) -> None:
    a5.lane_source_regressions(run)


# ------------------------------------------------------------- the independent anchor oracle (MF37A06-01)
#
# sqlite3, json and re only -- no ``aggie_analytics`` import. Every span of the three generations is first grounded
# in its own raw capture (the capture's revision text, sliced at the span, must reproduce the stored field text);
# then every edge of the three relations is judged from those grounded anchors, and every restructure claim and the
# cross-version triangle are rebuilt from the rows themselves.

_ORACLE_COLUMNS = ("episode_id", "pageid", "revision", "family", "row_index", "interval_index", "raw_file",
                   "team_char_span", "years_char_span", "team_raw", "years_raw", "years_as_written")
_ORACLE_CROSSED = ("PARENT_ABSENT", "EPISODE", "TEAM", "YEARS", "UNANCHORED", "PERIOD")


def _span(value: Any) -> tuple[int, int] | None:
    try:
        decoded = json.loads(value) if isinstance(value, str) else value
    except ValueError:
        return None
    if isinstance(decoded, list) and len(decoded) == 2 and all(isinstance(v, int) and not isinstance(v, bool)
                                                                for v in decoded) and 0 <= decoded[0] <= decoded[1]:
        return decoded[0], decoded[1]
    return None


def _agree(a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Equal, overlapping, or an empty parameter position inside the other span."""

    return (a == b or (a[0] < b[1] and b[0] < a[1]) or (a[0] == a[1] and b[0] <= a[0] <= b[1])
            or (b[0] == b[1] and a[0] <= b[0] <= a[1]))


def _plain(text: Any) -> str | None:
    return re.sub(r"\s+", "", str(text)).casefold() if text not in (None, "") else None


def _field_verdict(child: dict[str, Any], parent: dict[str, Any], field: str) -> str:
    mine, theirs = _span(child[f"{field}_char_span"]), _span(parent[f"{field}_char_span"])
    if mine and theirs:
        return "SPAN_AGREES" if _agree(mine, theirs) else "SPAN_DISJOINT"
    if mine and not theirs:
        region = [s for s in (_span(parent["team_char_span"]), _span(parent["years_char_span"])) if s]
        if any(_agree(mine, s) for s in region):
            return "REGION_AGREES"
    x, y = _plain(child[f"{field}_raw"]), _plain(parent[f"{field}_raw"])
    if x and y:
        return "TEXT_CONTAINED" if (x in y or y in x) else "TEXT_DISJOINT"
    return "ABSENT"


def _entry(row: dict[str, Any]) -> tuple[Any, ...]:
    return row["pageid"], row["revision"], row["family"], row["row_index"]


def _ground(rows: dict[str, dict[str, Any]], texts: dict[tuple[str, str, str], str | None]) -> dict[str, Any]:
    counts, examples = collections.Counter(), []
    for row in rows.values():
        key = (str(row["raw_file"] or ""), str(row["pageid"]), str(row["revision"]))
        if key not in texts:
            texts[key] = None
            try:
                payload = json.loads(Path(key[0]).read_bytes().decode("utf-8-sig"))
                pages = (payload.get("query") or {}).get("pages") or {}
                for page in (pages.values() if isinstance(pages, dict) else pages):
                    for revision in page.get("revisions") or []:
                        if (str(page.get("pageid")), str(revision.get("revid"))) == key[1:]:
                            slot = (revision.get("slots") or {}).get("main") or {}
                            texts[key] = slot.get("*", slot.get("content"))
            except (OSError, ValueError, AttributeError, TypeError):
                pass
        text = texts[key]
        for field in ("team", "years"):
            span = _span(row[f"{field}_char_span"])
            if span is None:
                counts[f"{field}_without_span"] += 1
            elif text is None:
                counts[f"{field}_capture_unreadable"] += 1
            elif text[span[0]:span[1]] == row[f"{field}_raw"]:
                counts[f"{field}_reproduced"] += 1
            else:
                counts[f"{field}_not_reproduced"] += 1
                if len(examples) < 5:
                    examples.append([row["episode_id"], field, list(span), text[span[0]:span[1]][:80],
                                     str(row[f"{field}_raw"])[:80]])
    return {"counts": dict(counts), "examples": examples,
            "holds": not any(k.endswith(("_not_reproduced", "_capture_unreadable")) for k in counts)}


def _relation(children: dict[str, dict[str, Any]], parents: dict[str, dict[str, Any]], key: str,
              dispositions: dict[str, tuple[str, list[str]]], name: str) -> dict[str, Any]:
    parent_entries = collections.Counter(_entry(r) for r in parents.values())
    child_entries = collections.Counter(_entry(r) for r in children.values())
    counts, examples = collections.Counter(), collections.defaultdict(list)
    for cid, child in children.items():
        for pid in json.loads(child[key] or "[]"):
            parent = parents.get(pid)
            if parent is None:
                verdict = "PARENT_ABSENT"
            else:
                team, years = _field_verdict(child, parent, "team"), _field_verdict(child, parent, "years")
                if "DISJOINT" in team and "DISJOINT" in years:
                    verdict = "EPISODE"
                elif "DISJOINT" in team:
                    verdict = "TEAM"
                elif "DISJOINT" in years:
                    verdict = "YEARS"
                elif team == years == "ABSENT":
                    verdict = "SAME_PARAMETER" if child["row_index"] == parent["row_index"] else "UNANCHORED"
                else:
                    verdict = "SOURCE_FIELD"
                    same = _span(child["team_char_span"]) == _span(parent["team_char_span"]) and (
                        _span(child["team_char_span"]) is not None
                        or _span(child["years_char_span"]) == _span(parent["years_char_span"]))
                    several = parent_entries[_entry(parent)] > 1 or child_entries[_entry(child)] > 1
                    if same and several and dispositions.get(pid, ("",))[0] != "RESTRUCTURED_INTERVALS":
                        x, y = _plain(child["years_as_written"]), _plain(parent["years_as_written"])
                        verdict = "SOURCE_FIELD_SAME_PERIOD" if (not x or not y or x in y or y in x) else "PERIOD"
            counts[verdict] += 1
            if verdict in _ORACLE_CROSSED and len(examples[verdict]) < 5:
                examples[verdict].append([cid, pid])
    entries = collections.defaultdict(list)
    for pid, parent in parents.items():
        entries[_entry(parent)].append(pid)
    restructured, violations = 0, []
    for entry, pids in entries.items():
        states = [dispositions.get(pid, ("", [])) for pid in pids]
        if not any(state == "RESTRUCTURED_INTERVALS" for state, _ in states):
            continue
        restructured += 1
        successors = {tuple(sorted(ids)) for _, ids in states}
        if not all(state == "RESTRUCTURED_INTERVALS" for state, _ in states) or len(successors) != 1:
            violations.append([list(entry), "not all-to-all"])
            continue
        same_entry = [s for s in next(iter(successors)) if s in children
                      and _span(children[s]["team_char_span"]) == _span(parents[pids[0]]["team_char_span"])]
        if len(same_entry) == len(pids):
            violations.append([list(entry), "interval count unchanged"])
    return {"relation": name, "edges": sum(counts.values()), "counts": dict(counts),
            "crossed_edges": sum(counts[v] for v in _ORACLE_CROSSED), "examples": dict(examples),
            "restructured_entries": restructured, "restructure_violations": violations[:10],
            "restructure_violation_count": len(violations)}


def independent_anchor_oracle(successor: Path, a04: Path, database: Path, *,
                              texts: dict[tuple[str, str, str], str | None] | None = None) -> dict[str, Any]:
    def load(path: Path, table: str, extra: tuple[str, ...] = ()) -> dict[str, dict[str, Any]]:
        conn = a6._ro(path)
        try:
            return {r["episode_id"]: dict(r) for r in conn.execute(
                f"SELECT {','.join(_ORACLE_COLUMNS + extra)} FROM {table}")}
        finally:
            conn.close()

    def ledger(path: Path, sql: str) -> dict[str, tuple[str, list[str]]]:
        conn = a6._ro(path)
        try:
            return {str(r[0]): (str(r[1]), json.loads(r[2] or "[]")) for r in conn.execute(sql)}
        finally:
            conn.close()

    texts = {} if texts is None else texts
    parents = load(database, "career_episode_successor")
    children = load(successor, "career_episode_a05", ("predecessor_episode_ids", "a04_episode_ids"))
    older = load(a04, "career_episode_a04", ("predecessor_episode_ids",))
    grounding = {"default": _ground(parents, texts), "A05": _ground(children, texts), "A04": _ground(older, texts)}
    relations = [
        _relation(children, parents, "predecessor_episode_ids", ledger(successor, (
            "SELECT predecessor_episode_id, disposition, successor_episode_ids FROM career_a05_disposition")),
            "A5<-default"),
        _relation(children, older, "a04_episode_ids", ledger(successor, (
            "SELECT a04_episode_id, disposition, a05_episode_ids FROM career_a05_from_a04")), "A5<-A4"),
        _relation(older, parents, "predecessor_episode_ids", ledger(a04, (
            "SELECT predecessor_episode_id, disposition, successor_episode_ids FROM career_a04_disposition")),
            "A4<-default"),
    ]
    triangle = []
    for cid, child in children.items():
        through: set[str] = set()
        for aid in json.loads(child["a04_episode_ids"] or "[]"):
            through.update(json.loads((older.get(aid) or {}).get("predecessor_episode_ids") or "[]"))
        if through != set(json.loads(child["predecessor_episode_ids"] or "[]")):
            triangle.append(cid)
    return {"method": ("sqlite3/json/re only (no project module): every span of the default, Attempt 4 and Attempt 5 "
                       "rows sliced from its own raw capture must reproduce the stored field text; every edge of the "
                       "three relations is judged from those anchors (spans equal, overlapping or an empty parameter "
                       "inside; a spanless parent by its region or contained text; an edge with no comparable field "
                       "only within its own parameter), intervals of an unrestructured field by their written periods, "
                       "restructure claims all-to-all over a changed interval count, and each row's predecessor rows "
                       "against those its Attempt 4 rows derive from."),
            "successor": str(successor), "successor_sha256": sha256_file(successor), "rows": len(children),
            "a04_rows": len(older), "default_rows": len(parents), "captures_read": len(texts),
            "grounding": grounding, "relations": relations,
            "crossed_edges": sum(r["crossed_edges"] for r in relations),
            "restructure_violations": sum(r["restructure_violation_count"] for r in relations),
            "triangle_mismatches": len(triangle), "triangle_examples": triangle[:5]}


def lane_career_successor(run: LaneRun) -> None:
    a6.lane_career_successor(run)
    bindings = run.extra.get("source_identity_bindings") or {}
    a05 = ((bindings.get("A05") or {}).get("lineage_proved_independently_of_the_ledgers") or {})
    a04 = ((bindings.get("A04") or {}).get("lineage_proved_independently_of_the_ledgers") or {})
    default, cross = a05.get("parent_edges_bound_to_source_field") or {}, a05.get("a04_edges_bound_to_source_field") or {}
    older = a04.get("parent_edges_bound_to_source_field") or {}

    def anchored(counts: dict[str, Any], edges: int) -> bool:
        return counts.get("edges") == edges and (int(counts.get("anchored_by_source_field") or 0)
                                                 + int(counts.get("anchored_by_parameter_only") or 0)) == edges

    checks = {
        "verifier_is_v3": bindings.get("verifier_version") == "BAS-C37A07-CAREER-SUCCESSOR-VERIFIER-v3",
        "a05_default_edges_anchored": anchored(default, 71915),
        "a05_a04_edges_anchored": anchored(cross, 72904),
        "a05_versions_agree_on_every_row": a05.get("rows_whose_versions_agree_on_predecessor_rows") == 72958,
        "a04_default_edges_anchored": anchored(older, 72074),
    }
    run.extra["source_anchor_checks"] = {"checks": checks, "default": default, "a04_relation": cross, "a04_file": older}
    for name, held in checks.items():
        if not held:
            run.problems.append(f"source anchor binding: {name} does not hold")
    texts: dict[tuple[str, str, str], str | None] = {}
    oracle = independent_anchor_oracle(A5_SUCCESSOR, A4_SUCCESSOR, DELIVERED_DB, texts=texts)
    saved: dict[str, Any] = {"fixture": str(SAVED_SAME_PAGE_FIXTURE), "exists": SAVED_SAME_PAGE_FIXTURE.is_file(),
                             "meaning": "the manager's Attempt 6 same-page swap, saved at intake; it must be found"}
    if saved["exists"]:
        saved["sha256"] = sha256_file(SAVED_SAME_PAGE_FIXTURE)
        forged = independent_anchor_oracle(SAVED_SAME_PAGE_FIXTURE, A4_SUCCESSOR, DELIVERED_DB, texts=texts)
        saved["relations"] = [{k: r[k] for k in ("relation", "crossed_edges", "counts", "examples")}
                              for r in forged["relations"]]
        saved["holds"] = (saved["sha256"] == SAVED_SAME_PAGE_SHA256
                          and [r["crossed_edges"] for r in forged["relations"]] == [2, 2, 0]
                          and all(set(r["examples"]) == {"EPISODE"} for r in forged["relations"][:2]))
    oracle["saved_manager_fixture"] = saved
    oracle["holds"] = (oracle["crossed_edges"] == 0 and oracle["restructure_violations"] == 0
                       and oracle["triangle_mismatches"] == 0 and oracle["rows"] == 72958
                       and all(g["holds"] for g in oracle["grounding"].values())
                       and [r["edges"] for r in oracle["relations"]] == [71915, 72904, 72074] and bool(saved.get("holds")))
    run.extra["independent_anchor_oracle"] = oracle
    if not oracle["holds"]:
        run.problems.append(f"the independent anchor oracle does not hold: crossed {oracle['crossed_edges']}, "
                            f"restructure {oracle['restructure_violations']}, triangle {oracle['triangle_mismatches']}, "
                            f"saved fixture {saved.get('holds')}")


# ------------------------------------------------------------- the installed consumer (MF37A06-01)


def _canonical_digest(values: list[Any]) -> str:
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(",", ":"), default=str)
                          .encode("utf-8")).hexdigest()


def _fred_rows(c: sqlite3.Connection, table: str) -> tuple[dict[str, Any], dict[str, Any]]:
    one = dict(c.execute(f"SELECT * FROM {table} WHERE person_display=? AND family='COACHING' AND row_index=1 "
                         "AND interval_index=0", (FRED,)).fetchone())
    six = dict(c.execute(f"SELECT * FROM {table} WHERE person_display=? AND family='COACHING' AND team_raw LIKE "
                         "'%DFO%'", (FRED,)).fetchone())
    return one, six


def _swap_edges(c: sqlite3.Connection, a: dict[str, Any], b: dict[str, Any], *, default: bool = True,
                a04: bool = True, table: str = "career_episode_a05") -> dict[str, Any]:
    """Swap two rows' reciprocal edges, with their disposition texts, in the chosen relations (the manager's recipe)."""

    relations = []
    if default:
        relations.append(("predecessor_episode_ids", "disposition",
                          "career_a05_disposition" if table == "career_episode_a05" else "career_a04_disposition",
                          "predecessor_episode_id", "successor_episode_ids"))
    if a04 and table == "career_episode_a05":
        relations.append(("a04_episode_ids", "a04_disposition", "career_a05_from_a04", "a04_episode_id",
                          "a05_episode_ids"))
    for field, state, owner_table, owner_key, children in relations:
        pa, pb = json.loads(a[field]), json.loads(b[field])
        da = dict(c.execute(f"SELECT * FROM {owner_table} WHERE {owner_key}=?", (pa[0],)).fetchone())
        db = dict(c.execute(f"SELECT * FROM {owner_table} WHERE {owner_key}=?", (pb[0],)).fetchone())
        c.execute(f"UPDATE {table} SET {field}=?, {state}=? WHERE episode_id=?", (json.dumps(pb), db["disposition"],
                                                                                   a["episode_id"]))
        c.execute(f"UPDATE {table} SET {field}=?, {state}=? WHERE episode_id=?", (json.dumps(pa), da["disposition"],
                                                                                   b["episode_id"]))
        c.execute(f"UPDATE {owner_table} SET {children}=? WHERE {owner_key}=?", (json.dumps([b["episode_id"]]), pa[0]))
        c.execute(f"UPDATE {owner_table} SET {children}=? WHERE {owner_key}=?", (json.dumps([a["episode_id"]]), pb[0]))
    return {"a": a["episode_id"], "b": b["episode_id"], "relations": [r[0] for r in relations]}


def _interval_pair(c: sqlite3.Connection) -> tuple[dict[str, Any], dict[str, Any]]:
    """Two intervals of one unrestructured field, each derived one-to-one from its own interval, whose written
    periods do not contain each other: the same role, a different period."""

    for row in c.execute("SELECT * FROM career_episode_a05 WHERE interval_index=1 AND years_as_written IS NOT NULL "
                         "ORDER BY pageid"):
        second = dict(row)
        first = c.execute("SELECT * FROM career_episode_a05 WHERE pageid=? AND revision=? AND family=? AND row_index=? "
                          "AND interval_index=0", (second["pageid"], second["revision"], second["family"],
                                                   second["row_index"])).fetchone()
        if first is None:
            continue
        first = dict(first)
        pa, pb = json.loads(first["predecessor_episode_ids"]), json.loads(second["predecessor_episode_ids"])
        qa, qb = json.loads(first["a04_episode_ids"]), json.loads(second["a04_episode_ids"])
        wa, wb = str(first["years_as_written"] or ""), str(second["years_as_written"] or "")
        if (len(pa) == len(pb) == len(qa) == len(qb) == 1 and pa != pb and first["disposition"] != "RESTRUCTURED_INTERVALS"
                and second["disposition"] != "RESTRUCTURED_INTERVALS" and wa and wb and wa not in wb and wb not in wa
                and first["team_char_span"] == second["team_char_span"]):
            siblings = c.execute("SELECT COUNT(*) FROM career_episode_a05 WHERE pageid=? AND revision=? AND family=? "
                                 "AND row_index=?", (first["pageid"], first["revision"], first["family"],
                                                     first["row_index"])).fetchone()[0]
            if siblings == 2:
                return first, second
    raise RuntimeError("no unrestructured two-interval field for the same-role/different-period challenge")


def _set_anchor(c: sqlite3.Connection, victim: dict[str, Any], donor: dict[str, Any], field: str) -> dict[str, Any]:
    c.execute(f"UPDATE career_episode_a05 SET {field}_raw=?, {field}_char_span=? WHERE episode_id=?",
              (donor[f"{field}_raw"], donor[f"{field}_char_span"], victim["episode_id"]))
    return {"victim": victim["episode_id"], "field": field, "donor": donor["episode_id"],
            "donor_span": donor[f"{field}_char_span"]}


def _false_restructure(c: sqlite3.Connection, first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    parents = json.loads(first["predecessor_episode_ids"]) + json.loads(second["predecessor_episode_ids"])
    children = [first["episode_id"], second["episode_id"]]
    for child in children:
        c.execute("UPDATE career_episode_a05 SET predecessor_episode_ids=?, disposition=? WHERE episode_id=?",
                  (json.dumps(parents), "RESTRUCTURED_INTERVALS", child))
    for parent in parents:
        c.execute("UPDATE career_a05_disposition SET successor_episode_ids=?, disposition=? WHERE predecessor_episode_id=?",
                  (json.dumps(children), "RESTRUCTURED_INTERVALS", parent))
    return {"children": children, "parents": parents, "claim": "RESTRUCTURED_INTERVALS over an unchanged interval count"}


def _cross_a04_file(c: sqlite3.Connection) -> dict[str, Any]:
    """Cross the Attempt 4 file's own default lineage for Fred's rows 1 and 6 (resealed), then declare that file and
    its new digest in the Attempt 5 copy with the two mapping digests recomputed, as a careful forger would. The
    digest order is the one that reproduces the genuine mapping digest, or the forgery is not attempted."""

    a4 = a6._open_fixture(LINEAGE_A04)
    one, six = _fred_rows(a4, "career_episode_a04")
    columns = [r[1] for r in a4.execute("PRAGMA table_info(career_episode_a04)")]

    def digest(identity: str) -> str:
        row = a4.execute(f"SELECT {','.join(chr(34) + x + chr(34) for x in columns)} FROM career_episode_a04 "
                         "WHERE episode_id=?", (identity,)).fetchone()
        return _canonical_digest(list(row))

    recorded = c.execute("SELECT a04_row_sha256 FROM career_a05_from_a04 WHERE a04_episode_id=?",
                         (one["episode_id"],)).fetchone()[0]
    if digest(one["episode_id"]) != recorded:
        raise RuntimeError("the table-order row digest does not reproduce the genuine mapping digest")
    a4.execute("UPDATE career_episode_a04 SET predecessor_episode_ids=? WHERE episode_id=?",
               (six["predecessor_episode_ids"], one["episode_id"]))
    a4.execute("UPDATE career_episode_a04 SET predecessor_episode_ids=? WHERE episode_id=?",
               (one["predecessor_episode_ids"], six["episode_id"]))
    digests = {identity: digest(identity) for identity in (one["episode_id"], six["episode_id"])}
    a6._reseal(a4, a6.A04_TABLES)
    a4.commit()
    a4.close()
    for identity, value in digests.items():
        c.execute("UPDATE career_a05_from_a04 SET a04_row_sha256=? WHERE a04_episode_id=?", (value, identity))
    c.execute("UPDATE successor_identity SET value=? WHERE key='a04_successor_path'", (str(LINEAGE_A04),))
    c.execute("UPDATE successor_identity SET value=? WHERE key='a04_successor_sha256'", (sha256_file(LINEAGE_A04),))
    return {"a04_file": str(LINEAGE_A04), "crossed_a04_rows": list(digests), "mapping_digests_recomputed": True,
            "a04_file_resealed": True}


#: (name, format, builder, expected refusal, person); a builder receives the fixture connection and the genuine rows.
def _a7_cases() -> list[tuple[str, str, Callable[[sqlite3.Connection], dict[str, Any]], str, str]]:
    def swap(default: bool, a04: bool) -> Callable[[sqlite3.Connection], dict[str, Any]]:
        return lambda c: _swap_edges(c, *_fred_rows(c, "career_episode_a05"), default=default, a04=a04)

    def anchor(field: str) -> Callable[[sqlite3.Connection], dict[str, Any]]:
        return lambda c: _set_anchor(c, *_fred_rows(c, "career_episode_a05"), field)

    def a04_swap(c: sqlite3.Connection) -> dict[str, Any]:
        return _swap_edges(c, *_fred_rows(c, "career_episode_a04"), table="career_episode_a04")

    return [
        ("a05_same_page_cross_episode_swap", "A05", swap(True, True), REFUSED_EPISODE, FRED),
        ("a05_year_only_anchor_substitution", "A05", anchor("years"), REFUSED_YEARS, FRED),
        ("a05_team_only_anchor_substitution", "A05", anchor("team"), REFUSED_TEAM, FRED),
        ("a05_same_role_different_period", "A05", lambda c: _swap_edges(c, *_interval_pair(c)), REFUSED_PERIOD, ""),
        ("a05_cross_version_anchor_substitution", "A05", swap(False, True), REFUSED_A04_ANCHOR, FRED),
        ("a05_cross_version_lineage", "A05", _cross_a04_file, REFUSED_CROSS_VERSION, FRED),
        ("a05_false_restructure_claim", "A05", lambda c: _false_restructure(c, *_interval_pair(c)), REFUSED_RESTRUCTURE,
         ""),
        ("a04_same_page_cross_episode_swap", "A04", a04_swap, REFUSED_EPISODE, FRED),
    ]


def _module_entrypoint(run: LaneRun, installed: dict[str, Any], name: str, args: list[Any], *, expect_exit: int = 0,
                       save: Path | None = None) -> dict[str, Any]:
    """The installed package's other entrypoint, ``python -P -m aggie_analytics.cycle33.query`` from the same venv
    (``-P``: the working directory is not put on the import path), under the same stream helper and environment as
    the console script."""

    target = save if save is not None else run.log_dir / f"{run.lane}__{name}.stdout.json.gz"
    summary = run.log_dir / f"{run.lane}__{name}.stdout.json"
    record = run.run(name, [run.python, "-S", "-B", a5.STREAM_HELPER, target, a5.ECHO_LIMIT, summary, "--",
                            installed["python"], "-B", "-P", "-m", "aggie_analytics.cycle33.query", "--database",
                            DELIVERED_DB, *args], cwd=installed["stage"], env=base._installed_env(run),
                     expect_exit=expect_exit, timeout=3600,
                     note="The alternate installed entrypoint (module), same venv, environment and stream helper.")
    captured = _json_file(summary) or {}
    record["stdout_capture"] = {"helper": str(a5.STREAM_HELPER), "summary": str(summary), **captured}
    # As attempt05_lanes._cli: the helper streams a large output to the gzip file; a small one stays in the log.
    if captured.get("streamed_to"):
        record["stdout_gzip"] = captured["streamed_to"]
        record["stdout_gzip_sha256"] = sha256_file(Path(captured["streamed_to"]))
    elif save is not None:
        with gzip.open(save, "wb") as handle:
            handle.write(Path(record["log_path"]).read_bytes())
    if save is not None:
        record["saved_output_gzip"] = str(save)
        record["saved_output_sha256"] = sha256_file(save)
    return record


def _a7_forgeries(run: LaneRun, installed: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {"fixtures": {"a05": str(LINEAGE_A05), "a04": str(LINEAGE_A04)}, "cases": {},
                               "rule": ("each case restores its fixture(s) from the genuine files, changes one anchor or "
                                        "relation, reseals every ledger as a careful forger would, pins the digest and "
                                        "serves through the console script and the module entrypoint")}
    outdir = run.run_dir / "a7_forgeries"
    outdir.mkdir()
    genuine = sqlite3.connect(A5_SUCCESSOR.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    genuine.row_factory = sqlite3.Row
    pair = _interval_pair(genuine)
    genuine.close()
    period_person = pair[0]["person_display"]
    for label, fmt, path, digest, person in (("a05_genuine", "A05", A5_SUCCESSOR, A5_SUCCESSOR_SHA256, FRED),
                                             ("a05_genuine_interval_person", "A05", A5_SUCCESSOR, A5_SUCCESSOR_SHA256,
                                              period_person),
                                             ("a04_genuine", "A04", A4_SUCCESSOR, A4_SUCCESSOR_SHA256, FRED)):
        args = ["--career", "--career-successor", path, "--career-successor-sha256", digest, "--person", person,
                "--compact"]
        script = base._cli(run, installed, f"a7_{label}", args, save=outdir / f"{label}.json.gz")
        module = _module_entrypoint(run, installed, f"a7_{label}_module", args, save=outdir / f"{label}.module.json.gz")
        rows = (base._gz_json(outdir / f"{label}.json.gz") or {}).get("row_count")
        module_rows = (base._gz_json(outdir / f"{label}.module.json.gz") or {}).get("rows")
        same = bool(module_rows) and (base._gz_json(outdir / f"{label}.json.gz") or {}).get("rows") == module_rows
        results["cases"][label] = {"format": fmt, "person": person, "script_exit": script.get("exit_code"),
                                   "module_exit": module.get("exit_code"), "row_count": rows,
                                   "entrypoints_serve_the_same_rows": same, "expected": "SERVED",
                                   "holds": script.get("exit_code") == 0 and module.get("exit_code") == 0 and bool(rows)
                                   and same}
    for name, fmt, builder, code, person in _a7_cases():
        a6._restore(LINEAGE_A05, A5_SUCCESSOR)
        a6._restore(LINEAGE_A04, A4_SUCCESSOR)
        fixture, tables = (LINEAGE_A05, a6.A05_TABLES) if fmt == "A05" else (LINEAGE_A04, a6.A04_TABLES)
        target = a6._open_fixture(fixture)
        details = builder(target)
        a6._reseal(target, tables)
        target.commit()
        target.close()
        digest = sha256_file(fixture)
        who = person or period_person
        args = ["--career", "--career-successor", fixture, "--career-successor-sha256", digest, "--person", who,
                "--limit", "100", "--compact"]
        script = base._cli(run, installed, f"a7_{name}", args, expect_exit=1)
        module = _module_entrypoint(run, installed, f"a7_{name}_module", args, expect_exit=1)
        refusals = {kind: _refusal(Path(record["log_path"]).read_text(encoding="utf-8", errors="replace"))
                    for kind, record in (("script", script), ("module", module))}
        results["cases"][name] = {"format": fmt, "person": who, "expected": code, "fixture_sha256": digest,
                                  "script_exit": script.get("exit_code"), "module_exit": module.get("exit_code"),
                                  "refusals": refusals, "details": details,
                                  "holds": script.get("exit_code") == 1 and module.get("exit_code") == 1
                                  and refusals["script"] == code and refusals["module"] == code}
        if not results["cases"][name]["holds"]:
            run.problems.append(f"A7 forgery {name} was not refused for its own cause at both entrypoints: {refusals} "
                                f"(expected {code})")
    for fixture, source in ((LINEAGE_A05, A5_SUCCESSOR), (LINEAGE_A04, A4_SUCCESSOR)):
        a6._restore(fixture, source)
    results["genuine_unchanged"] = (sha256_file(A5_SUCCESSOR) == A5_SUCCESSOR_SHA256
                                    and sha256_file(A4_SUCCESSOR) == A4_SUCCESSOR_SHA256)
    results["holds"] = results["genuine_unchanged"] and all(row["holds"] for row in results["cases"].values())
    return results


def _manager_a6_lineage(run: LaneRun, installed: dict[str, Any]) -> dict[str, Any]:
    """The manager's Attempt 6 same-page lineage challenge (over its adversarial plumbing) against this wheel: its
    exact reciprocal swap must now be refused as an episode anchor."""

    directory = run.fresh("replay_mgr_a6_same_page")
    adversarial = (MANAGER_A6 / "successor_adversarial.py").read_bytes().decode("utf-8-sig")
    fresh = (MANAGER_A6 / "fresh_lineage_challenge.py").read_bytes().decode("utf-8")
    adaptations = {
        "successor_adversarial.py": {f"F=Path(r'{MANAGER_A6_FIXTURE_LITERAL}')": f"F=Path(r'{MANAGER_ADVERSARIAL_FIXTURE}')",
                                     f"V=Path(r'{A6_VENV_LITERAL}')": f"V=Path(r'{installed['venv']}')"},
        "fresh_lineage_challenge.py": {"T=F/'same-page-lineage.sqlite'": "T=F/'adversarial.sqlite'"},
    }
    texts = {"successor_adversarial.py": adversarial, "fresh_lineage_challenge.py": fresh}
    for name, changes in adaptations.items():
        for old, new in changes.items():
            if texts[name].count(old) != 1:
                raise RuntimeError(f"{name}: the literal to adapt occurs {texts[name].count(old)} times")
            texts[name] = texts[name].replace(old, new)
        (directory / name).write_text(texts[name], encoding="utf-8")
    MANAGER_ADVERSARIAL_FIXTURE.mkdir(parents=True, exist_ok=True)
    (MANAGER_ADVERSARIAL_FIXTURE / "temp").mkdir(exist_ok=True)
    run.exceptions.append("The manager's Attempt 6 same-page challenge starts the installed launcher with its own "
                          "minimal environment; it runs without the lane guard, writing only its owned fixture and "
                          "its replay folder, which the snapshots measure.")
    record = run.run("manager_a6_same_page_lineage_replay", [run.python, "-B", directory / "fresh_lineage_challenge.py"],
                     cwd=directory, env=run.env(guarded=False, pythonpath=None), timeout=3600)
    review = _json_file(directory / "FRESH_LINEAGE_CHALLENGE.json") or {}
    cases = review.get("cases") or []
    case = cases[0] if cases else {}
    verdict = {"manager_originals": {name: sha256_bytes((MANAGER_A6 / name).read_bytes()) for name in texts},
               "replay_copies": {name: sha256_file(directory / name) for name in texts}, "adaptations": adaptations,
               "exit": record.get("exit_code"), "case_exit": case.get("exit"), "row_count": case.get("row_count"),
               "refusal": _refusal(case.get("stderr") or ""), "expected": REFUSED_EPISODE,
               "successor_sha256": review.get("successor_sha256")}
    verdict["holds"] = (verdict["case_exit"] == 1 and verdict["refusal"] == REFUSED_EPISODE
                        and verdict["successor_sha256"] == A5_SUCCESSOR_SHA256)
    a6._restore(LINEAGE_A05, A5_SUCCESSOR)
    return verdict


def lane_installed_consumer_c01(run: LaneRun) -> None:
    a6.lane_installed_consumer_c01(run)
    raw = run.extra.get("installed")
    if not raw:
        return
    installed = {key: Path(value) for key, value in raw.items()}
    run.extra["a7_forgeries"] = _a7_forgeries(run, installed)
    verdict = _manager_a6_lineage(run, installed)
    run.extra["manager_a6_same_page_lineage"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's Attempt 6 same-page challenge is not refused as an episode anchor: {verdict}")


# ------------------------------------------------------------- the local integration candidate (R37A07-03)


def _append_records() -> list[tuple[Path, dict[str, Any]]]:
    return [(path, _json_file(path)) for path in sorted(a6.CANDIDATE_RECORDS.glob("CANDIDATE_APPEND_*.json"))]


def _append_chain(head: str) -> dict[str, Any]:
    """Every Attempt 7 append continues the one before it, the first from the granted head ``bb5253b2`` (a rehearsal
    scratch candidate starts there too), the last ending at ``head``."""

    records = _append_records()
    chain = [{"record": str(path), "previous": record.get("previous_candidate_head"),
              "commit": record.get("candidate_commit"), "repair_head": record.get("repair_head")}
             for path, record in records]
    expected = [candidate.ISSUED_CANDIDATE_HEAD] + [row["commit"] for row in chain[:-1]]
    holds = bool(chain) and [row["previous"] for row in chain] == expected and chain[-1]["commit"] == head
    return {"appends": chain, "starts_from": candidate.ISSUED_CANDIDATE_HEAD, "holds": holds}


def _manager_a6_committed_tree(run: LaneRun, head: str) -> dict[str, Any]:
    copy, replay = a4._replay_from(run, MANAGER_A6, "committed_tree_review.py")
    record = run.run("manager_a6_committed_tree_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None),
                     note="The manager's saved committed-byte provenance probe, byte-identical; it reads the named "
                          "candidate branch through this worktree's shared Git store.")
    review = _json_file(copy.parent / "COMMITTED_TREE_PROVENANCE.json") or {}
    verdict = {**replay, "exit": record.get("exit_code"), "head": review.get("head"), "paths": review.get("paths"),
               "manifest_rows": review.get("manifest_rows"), "mismatches": review.get("mismatches"),
               "hash_view_equal": review.get("hash_view_equal"), "tree_view_equal": review.get("tree_view_equal"),
               "protected_same_as_main": [r.get("same_as_main") for r in review.get("protected") or []],
               "original_candidate_ancestor": review.get("original_candidate_ancestor")}
    verdict["holds"] = (verdict["head"] == head and verdict["mismatches"] == [] and verdict["hash_view_equal"] is True
                        and verdict["tree_view_equal"] is True and all(verdict["protected_same_as_main"])
                        and verdict["original_candidate_ancestor"] is True)
    return verdict


def _control07_requalification(run: LaneRun) -> dict[str, Any]:
    folder = run.fresh("control07")
    record = run.run("control07_offline_requalification",
                     [run.python, "-B", CONTROL_TOOL, "validate", "--out-root", EVIDENCE_ROOT,
                      "--receipt", folder / "CONTROL07_PROPOSAL_VALIDATION.json",
                      "--markdown", folder / "CONTROL07_PROPOSAL.md", "--patch", folder / "CONTROL07_PROPOSAL.patch",
                      "--candidate", candidate.describe().get("candidate_head")],
                     env=run.env(guarded=False, pythonpath="source"),
                     note="The inert proposal re-qualified offline at this head; each checker run inside is guarded "
                          "with non-loopback network denied. Nothing active is written.")
    document = _json_file(folder / "CONTROL07_PROPOSAL_VALIDATION.json") or {}
    return {"exit": record.get("exit_code"), "receipt": str(folder / "CONTROL07_PROPOSAL_VALIDATION.json"),
            "result": document.get("result"), "checks": document.get("checks"),
            "current_green": (document.get("characterization") or {}).get("current_checkers_green_on"),
            "subjects": document.get("subjects"), "holds": document.get("result") == "PASS"}


def lane_local_integration_candidate(run: LaneRun) -> None:
    a6.lane_local_integration_candidate(run)
    head = (run.extra.get("candidate") or {}).get("candidate_head")
    if not head:
        return
    description = candidate.describe()
    run.extra["candidate_attempt7"] = {
        "appends_continue_bb5253b2": _append_chain(head)["holds"],
        "bb5253b2_is_ancestor": description.get("attempt7_start_is_ancestor") is True,
        "preserved_first_candidate_is_ancestor": description.get("issued_head_is_ancestor") is True}
    if not all(run.extra["candidate_attempt7"].values()):
        run.problems.append(f"the candidate does not continue the granted head: {run.extra['candidate_attempt7']}")
    if not run.rehearsal:
        verdict = _manager_a6_committed_tree(run, head)
        run.extra["manager_a6_committed_tree"] = verdict
        if not verdict["holds"]:
            run.problems.append(f"the manager's Attempt 6 committed-tree review finds mismatches: {verdict}")
    control = _control07_requalification(run)
    run.extra["control07_requalification"] = control
    if not control["holds"]:
        run.problems.append(f"the private CONTROL-07 proposal does not re-qualify offline: {control.get('checks')}")


# ------------------------------------------------------------- mounted, unmounted, platform and packet lanes


def _attempt6_final(lane: str) -> dict[str, Any]:
    rows = [json.loads(line) for line in (ATTEMPT6_ROOT / "lanes" / "RUNS.jsonl").read_text(encoding="utf-8")
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
    previous = _attempt6_final("FULL_FINAL_MOUNTED")
    comparison: dict[str, Any] = {"attempt6_receipt": previous.get("receipt"),
                                  "attempt6_receipt_sha256": previous.get("receipt_sha256"),
                                  "attempt6_run": previous.get("run"), "attempt6_result": previous.get("result")}
    if previous:
        a6_log = Path(next(c["log_path"] for c in previous["data"]["commands"]
                           if c["lane"].endswith("full_suite_mounted")))
        before = base._log_identities(a6_log)
        persisting = sorted(set(final["failed_or_errored"]) & set(before["failed_or_errored"]))
        new = sorted(set(final["failed_or_errored"]) - set(before["failed_or_errored"]))
        final_causes = base._failure_causes(log, persisting)
        before_causes = base._failure_causes(a6_log, persisting)
        comparison.update({
            "attempt6_log": str(a6_log), "attempt6_log_sha256": sha256_file(a6_log),
            "attempt6_tests_run": before["tests_run"], "final_tests_run": final["tests_run"],
            "attempt6_failed_or_errored": before["failed_or_errored"], "persisting": persisting,
            "new_in_attempt7": new,
            "no_longer_failing": sorted(set(before["failed_or_errored"]) - set(final["failed_or_errored"])),
            "new_failure_causes": base._failure_causes(log, new),
            "persisting_same_cause": sorted(i for i in persisting if final_causes[i] == before_causes[i]),
            "persisting_changed_cause": {i: {"attempt6": before_causes[i], "attempt7": final_causes[i]}
                                         for i in persisting if final_causes[i] != before_causes[i]},
        })
        if new:
            run.problems.append(f"new failing identities relative to Attempt 6: {new}")
    run.extra["attempt6_comparison"] = comparison


def lane_strict_mounted(run: LaneRun) -> None:
    base.lane_strict_mounted(run)
    final = [row["identity"] for row in run.extra.get("strict_findings") or []]
    previous = _attempt6_final("STRICT_MOUNTED")
    comparison: dict[str, Any] = {"attempt6_receipt": previous.get("receipt"), "attempt6_run": previous.get("run"),
                                  "attempt6_result": previous.get("result")}
    if previous:
        before = [row["identity"] for row in (previous["data"].get("details") or {}).get("strict_findings") or []]
        comparison.update({"attempt6_findings": before, "final_findings": final,
                           "persisting": sorted(set(final) & set(before)),
                           "new_in_attempt7": sorted(set(final) - set(before)),
                           "no_longer_reported": sorted(set(before) - set(final))})
        if comparison["new_in_attempt7"]:
            run.problems.append(f"new strict findings relative to Attempt 6: {comparison['new_in_attempt7']}")
    run.extra["attempt6_comparison"] = comparison


def lane_true_unmounted(run: LaneRun) -> None:
    base.lane_true_unmounted(run)


def lane_platform_carry(run: LaneRun) -> None:
    a4.lane_platform_carry(run)


def _owned_final_reservation(run: LaneRun, open_now: dict[str, dict[str, Any]]) -> bool:
    """Is the one reservation open in the final-output ledger the one this FINAL_PACKET run was admitted under?

    Cycle #37 -- Attempt #11 (MF37A11-01, W37A11-07). The Attempt 11 runner reserves before it makes its run folder, so
    it cannot name the reservation with the run's stamp; it named it with a second clock reading and the check below
    compared the two names, refusing the run's own valid reservation. A runner that keeps the reservation it was admitted
    under (``run.storage_reservation``) is judged by that reservation's token and operation, never by a name rebuilt from
    a clock: exactly one reservation is open, it is the admitted token, the ledger's own record of it carries the
    operation the runner was admitted under, and that operation is this lane's (not another lane's, not one made for a
    run blocked before any effect, and a rehearsal's only for a rehearsal). A missing, extra, wrong-token, changed-operation
    or wrong-lane reservation each refuse. A caller that keeps no reservation keeps the original contract (the run stamp
    names the reservation)."""

    if not hasattr(run, "storage_reservation"):
        return [v.get("operation") for v in open_now.values()] == [
            f"LANE FINAL_PACKET {run.stamp}" + (" (rehearsal)" if run.rehearsal else "")]
    admitted = run.storage_reservation
    if not isinstance(admitted, dict):
        return False
    token, operation = admitted.get("token"), admitted.get("operation")
    if not (isinstance(token, str) and token and isinstance(operation, str)) or admitted.get("decision") != "ADMITTED":
        return False
    if set(open_now) != {token}:
        return False
    return (open_now[token].get("operation") == operation and operation.startswith("LANE FINAL_PACKET ")
            and "(blocked before any effect)" not in operation
            and operation.endswith("(rehearsal)") == bool(run.rehearsal))


def lane_final_packet(run: LaneRun) -> None:
    """Verify the frozen operational ledger, the chain through the final-output continuation, and the packet."""

    paths = run.extra["storage_paths"]
    verification: dict[str, Any] = {}
    try:
        verification["operational_snapshot"] = snapshot.verify(paths["operational_ledger"], paths["final_snapshot"])
    except snapshot.SnapshotRefused as refusal:
        verification["operational_snapshot"] = {"result": "REFUSED", "code": refusal.code, "detail": str(refusal)}
        run.problems.append(f"the operational snapshot does not verify: {refusal.code}")
    try:
        proof = snapshot.chain(paths["final_output_ledger"])
        final_ledger = storage.Ledger(paths["final_output_ledger"])
        rows = final_ledger.records()
        init = final_ledger.config(rows)
        open_now = final_ledger.open_reservations(rows)
        continuation = init.get("continuation") or {}
        verification["chain"] = proof
        verification["final_output_ledger"] = {
            "ledger": str(final_ledger.path), "records": len(rows), "segment": init.get("segment"),
            "identity": final_ledger.identity(rows),
            "continues_the_final_snapshot": continuation.get("snapshot_content_sha256")
            == snapshot.load_snapshot(paths["final_snapshot"])["content_sha256"],
            "carries_the_root_budget": init["budget_bytes"] == storage.Ledger(paths["operational_ledger"]).config(
                storage.Ledger(paths["operational_ledger"]).records())["budget_bytes"],
            "open_reservations": {k: v.get("operation") for k, v in open_now.items()},
            "only_this_lane_open": _owned_final_reservation(run, open_now),
            "never_hashed_as_evidence": True}
        held = verification["final_output_ledger"]
        if not (proof.get("result") == "PASS" and held["continues_the_final_snapshot"] and held["carries_the_root_budget"]
                and held["only_this_lane_open"]):
            run.problems.append(f"the final-output ledger does not continue the frozen root cleanly: {held}")
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


def storage_paths(out_root: Path, rehearsal: bool) -> dict[str, Path]:
    """The ledgers a lane uses. A FINAL_PACKET rehearsal gets its own tiny root, snapshot and claimed final-output
    continuation under the rehearsal root, so the attempt's ledger is never frozen or continued by a rehearsal."""

    if not rehearsal:
        return {"operational_ledger": OPERATIONAL_LEDGER, "final_snapshot": FINAL_SNAPSHOT,
                "final_output_ledger": FINAL_OUTPUT_LEDGER}
    root = out_root / "storage-rehearsal" / utc_now().replace(":", "").replace("-", "").replace("+", "")[:22]
    root.mkdir(parents=True)
    (root / "data").mkdir()
    operational, frozen, final = root / "operational.jsonl", root / "OPERATIONAL_SNAPSHOT.json", root / "final.jsonl"
    ledger = storage.Ledger(operational)
    ledger.init(budget_bytes=64 * MIB, reserve_bytes=0, roots=[root / "data"], note="rehearsal operational ledger",
                cycle_number=CYCLE_NUMBER, attempt_number=ATTEMPT_NUMBER)
    token = ledger.reserve("rehearsal material work", 1024)["token"]
    (root / "data" / "work.bin").write_bytes(b"x" * 512)
    ledger.reconcile(token)
    snapshot.freeze(operational, frozen, label=f"{LABEL} REHEARSAL (not evidence)", scope="rehearsal only")
    snapshot.open_final(frozen, final, [str(root / "data")], reserve_bytes=0, cycle_number=CYCLE_NUMBER,
                        attempt_number=ATTEMPT_NUMBER)
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
    if FINAL_SNAPSHOT.is_file() and not final_lane:
        blocked.append(f"the operational ledger is frozen by {FINAL_SNAPSHOT.name}; material lanes are refused")
    if final_lane and not args.rehearsal and not (FINAL_SNAPSHOT.is_file() and FINAL_OUTPUT_LEDGER.is_file()):
        blocked.append("FINAL_PACKET runs only after the operational snapshot and the final-output ledger exist")
    if args.rehearsal and args.lane == "LOCAL_INTEGRATION_CANDIDATE":
        run.extra["rehearsal_scratch_candidate"] = a6.rehearse_candidate()
    gate = None
    if args.lane in GATED:
        gate = a5.qualification(out_root, run.binding["head"], run.binding["guard_sha256"])
        if not gate["holds"]:
            blocked.append("WRITE_PROTECTION and STORAGE_ADMISSION have not both passed at this head with these guard "
                           f"bytes: {gate}")
    paths = storage_paths(out_root, args.rehearsal and final_lane) if not blocked else {}
    ledger_path = paths.get("final_output_ledger") if final_lane else OPERATIONAL_LEDGER
    ledger = storage.Ledger(ledger_path) if ledger_path else None
    reservation = None
    if not blocked:
        estimate = LANE_ESTIMATES[args.lane]
        if args.lane == "INSTALLED_CONSUMER_C01":
            estimate += a6.missing_fixture_bytes()
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
                "rule": ("Read only immutable inputs: the frozen snapshot (never a live ledger), the sealed outputs and "
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
    digest = base.write_json(run.run_dir / "receipt.json", receipt)
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
