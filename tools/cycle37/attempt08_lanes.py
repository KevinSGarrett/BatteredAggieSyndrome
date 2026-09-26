r"""Cycle #37 — Attempt #8 — the lane runner (R37A08-05).

    attempt08_lanes.py --lane <ID> --contract <cycle_contract.json> --out-root <attempt root> [--rehearsal]

The preserved Attempt 7 runner (``attempt07_lanes``, over the Attempt 6, 5, 4 and 3 runners) rebound to the Attempt 8
contract, roots, ledger, suites and tools. Everything the earlier runners bind per run is still bound -- the issued
contract by its sealed digest, the committed subject (branch, head, tree, source digest, descent from the issued base,
a clean tree before and after), the interpreter, module origins, the delivered database by digest, the data root and
``C:\All-22`` measured before and after, the main checkout and both integration worktrees, credential removal, and the
guard and storage qualification of the costly lanes. What Attempt 8 changes:

* **STORAGE_ADMISSION (MF37A07-02)** adds the atomicity suite and replays the manager's Attempt 7 same-path race
  byte-faithfully (only its fixture root adapted): the repaired tools must leave one INIT, an intact chain and a usable
  restart; and the manager's stop/reserve challenge, whose stopped continuation must now be refused where it opens.
* **SOURCE_REGRESSIONS** also runs the two Attempt 8 suites against the exact bytes of the issued base (a ``git
  archive`` of ``996ada4d``): they must not pass there.
* **CAREER_SUCCESSOR (MF37A07-01)** checks the v4 verifier's witness proof over both genuine successors and runs the
  independent source-field oracle (``a08_source_field_oracle.py``, sqlite3/json/re only) over the genuine files and
  both saved manager fixtures (the Attempt 7 enlarged envelope and the Attempt 6 same-page swap).
* **INSTALLED_CONSUMER_C01** replays the manager's saved envelope fixture (its exact bytes) through the installed
  console script, the installed module and the source module, and serves ten fresh substitutions -- year-only,
  team-only and both-field envelopes, a full-page span, a boundary shifted into the next field, a partial span, a
  witness moved onto another job's genuine field, a list line enlarged over its neighbour, the envelope through the
  Attempt 4 format and an envelope in the declared Attempt 4 file -- each restored from the genuine file, resealed and
  refused for its source-field cause through the console script and the module. The Attempt 7 forgeries are kept;
  the year-only and team-only substitutions are now refused for the stricter source-field cause.
* **LOCAL_INTEGRATION_CANDIDATE** verifies the Attempt 8 appends continue ``0c22af20``, replays the manager's Attempt 7
  committed-tree review, and re-qualifies the retained CONTROL-07 proposal offline at this head.
* **FULL_FINAL_MOUNTED / STRICT_MOUNTED** compare identities with the Attempt 7 final receipts at the issued base.

A lane decides what its commands did. It does not decide scientific acceptance, and it cannot turn an inherited red
lane green.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt03_lanes as base  # noqa: E402  (the preserved Attempt 3 runner)
import attempt04_lanes as a4  # noqa: E402
import attempt05_lanes as a5  # noqa: E402
import attempt06_lanes as a6  # noqa: E402
import attempt06_candidate as a6c  # noqa: E402
import attempt07_lanes as a7  # noqa: E402  (the preserved Attempt 7 runner)
import attempt08_candidate as candidate  # noqa: E402
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
ATTEMPT_NUMBER = 8
CYCLE_ID = "CYCLE-37"
ATTEMPT_ID = "ATTEMPT-08-20260926"
RUNNER_VERSION = "BAS-C37-ATTEMPT08-LANES-v1"
BASE_SHA = "996ada4d3054b2fda103688b5078ef255110019c"
BRANCH = "codex/BAT-706-cycle37-rework"
LABEL = "Cycle #37 \u2014 Attempt #8 \u2014"
LANES = a7.LANES
GATED = a7.GATED
MIB = 1024 * 1024
#: Each lane's reservation, from the measured Attempt 7 costs (INSTALLED_CONSUMER_C01 366 MB, the candidate lane 119 MB,
#: PLATFORM_CARRY 85 MB, CAREER_SUCCESSOR 23 MB) with margin, plus this attempt's additions (the base export and its
#: suite run, the oracle's three receipts, ten more forgeries, the saved fixture's replays).
LANE_ESTIMATES = {
    "START_CONTEXT": 16 * MIB, "WRITE_PROTECTION": 32 * MIB, "STORAGE_ADMISSION": 48 * MIB,
    "SOURCE_ADMISSION": 32 * MIB, "SOURCE_HARNESS": 32 * MIB, "SOURCE_REGRESSIONS": 160 * MIB,
    "CAREER_SUCCESSOR": 96 * MIB, "INSTALLED_CONSUMER_C01": 576 * MIB, "LOCAL_INTEGRATION_CANDIDATE": 256 * MIB,
    "TRUE_UNMOUNTED": 32 * MIB, "FULL_FINAL_MOUNTED": 64 * MIB, "STRICT_MOUNTED": 32 * MIB,
    "PLATFORM_CARRY": 160 * MIB, "FINAL_PACKET": 32 * MIB,
}

EVIDENCE_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt08"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a08")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37a08")
ATTEMPT7_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt07"
VALIDATION_A07 = Path(r"C:\BatteredAggieSyndrome.validation\c37a07")
PACKAGING_A07 = Path(r"C:\BatteredAggieSyndrome.packaging\c37a07")
MANAGER_A7 = DATA_ROOT / "ops" / "manager_reviews" / "cycle37" / "attempt07" / "review-20260926T023810Z"
MANAGER_A7_FIXTURE_LITERAL = r"C:\BatteredAggieSyndrome.validation\mr37a07-023810"
MANAGER_A7_ENVELOPE = Path(MANAGER_A7_FIXTURE_LITERAL) / "adversarial.sqlite"
MANAGER_A7_ENVELOPE_SHA256 = "183f8accc377af6d0c855daf4c524dbf747ad9d669adf325c00a3c1f9f6d3bee"
A5_SUCCESSOR = a7.A5_SUCCESSOR
A5_SUCCESSOR_SHA256 = a7.A5_SUCCESSOR_SHA256
A4_SUCCESSOR = a7.A4_SUCCESSOR
A4_SUCCESSOR_SHA256 = a7.A4_SUCCESSOR_SHA256
OPERATIONAL_LEDGER = EVIDENCE_ROOT / "STORAGE_RESERVATIONS.jsonl"
FINAL_SNAPSHOT = EVIDENCE_ROOT / "STORAGE_EVIDENCE_SNAPSHOT.json"
FINAL_OUTPUT_LEDGER = EVIDENCE_ROOT / "evidence" / "storage" / "STORAGE_RESERVATIONS_FINAL_OUTPUT.jsonl"
CANDIDATE_RECORDS = EVIDENCE_ROOT / "evidence" / "integration"
BEFORE_REPRODUCTION = EVIDENCE_ROOT / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
#: The Attempt 6 manager's same-page fixture, saved by Attempt 7 at intake (read only here).
SAVED_SAME_PAGE_FIXTURE = a7.SAVED_SAME_PAGE_FIXTURE
SAVED_SAME_PAGE_SHA256 = a7.SAVED_SAME_PAGE_SHA256
FIXTURES = VALIDATION_ROOT / "fixtures"
#: One owned full copy of each genuine successor, restored before every use. The Attempt 5 copy is the one the
#: before-repair reproduction made from the manager's envelope fixture; every lane restores it before it forges.
MANAGER_ADVERSARIAL_FIXTURE = FIXTURES / "mr"
LINEAGE_A05 = MANAGER_ADVERSARIAL_FIXTURE / "adversarial.sqlite"
LINEAGE_A04 = FIXTURES / "lineage" / "successor_a04.sqlite"
CANDIDATE_WORKTREE = a6c.CANDIDATE_WORKTREE
GUARD = a7.GUARD
AFTER_COMMENTS = (("BAT-706", "C37-A08-AFTER-HANDOFF-BAT-706"), ("BAT-708", "C37-A08-AFTER-HANDOFF-BAT-708"))
PLATFORM_TOOL = "tools/cycle37/attempt08_platform.py"
OUTPUTS_TOOL = "tools/cycle37/attempt08_outputs.py"
CONTROL_TOOL = Path(__file__).resolve().parent / "attempt08_control07.py"
ORACLE_TOOL = Path(__file__).resolve().parent / "a08_source_field_oracle.py"
GOVERNANCE_V241 = DATA_ROOT / "ops" / "manager_review" / "releases" / "v2.4.1"
FRED = a7.FRED
A8_SUITES = ("test_cycle37_a08_continuation_atomicity", "test_cycle37_a08_source_witness")
STORAGE_SUITES = a7.STORAGE_SUITES + ("test_cycle37_a08_continuation_atomicity",)
CAREER_SUITES = a7.CAREER_SUITES + ("test_cycle37_a08_source_witness",)
REGRESSION_SUITES = a7.REGRESSION_SUITES + A8_SUITES
CANDIDATE_SUITES = a7.CANDIDATE_SUITES + A8_SUITES

REFUSED_SOURCE_FIELD = "REFUSED_CAREER_SUCCESSOR_SOURCE_FIELD_WITNESS_MISMATCH"
REFUSED_PLAN_REQUIRED = "REFUSED_CONTINUATION_REVISED_PLAN_REQUIRED"
#: The genuine counts the verifier and the oracle must reproduce (all 218,110 rows; 216,893 edges).
GENUINE_ROWS = {"A05": 72958, "A04": 73082, "default": 72070}
GENUINE_EDGES = {"A5<-default": 71915, "A5<-A4": 72904, "A4<-default": 72074}
#: The distinct delivered and Attempt 4 rows the successor's edges name (NOT_PRODUCED rows are named by none).
NAMED_PARENTS = {"delivered": 71775, "attempt4": 72764}


def rebind() -> None:
    """Point the preserved runners at the Attempt 8 contract, roots, ledger, suites, tools and grants."""

    for name, value in (("ATTEMPT_NUMBER", ATTEMPT_NUMBER), ("ATTEMPT_ID", ATTEMPT_ID),
                        ("RUNNER_VERSION", RUNNER_VERSION), ("BASE_SHA", BASE_SHA), ("LABEL", LABEL),
                        ("LANE_ESTIMATES", LANE_ESTIMATES), ("EVIDENCE_ROOT", EVIDENCE_ROOT),
                        ("VALIDATION_ROOT", VALIDATION_ROOT), ("PACKAGING_ROOT", PACKAGING_ROOT),
                        ("OPERATIONAL_LEDGER", OPERATIONAL_LEDGER), ("FINAL_SNAPSHOT", FINAL_SNAPSHOT),
                        ("FINAL_OUTPUT_LEDGER", FINAL_OUTPUT_LEDGER), ("CANDIDATE_RECORDS", CANDIDATE_RECORDS),
                        ("BEFORE_REPRODUCTION", BEFORE_REPRODUCTION), ("FIXTURES", FIXTURES),
                        ("MANAGER_ADVERSARIAL_FIXTURE", MANAGER_ADVERSARIAL_FIXTURE), ("LINEAGE_A05", LINEAGE_A05),
                        ("LINEAGE_A04", LINEAGE_A04), ("AFTER_COMMENTS", AFTER_COMMENTS),
                        ("PLATFORM_TOOL", PLATFORM_TOOL), ("OUTPUTS_TOOL", OUTPUTS_TOOL),
                        ("CONTROL_TOOL", CONTROL_TOOL), ("STORAGE_SUITES", STORAGE_SUITES),
                        ("CAREER_SUITES", CAREER_SUITES), ("REGRESSION_SUITES", REGRESSION_SUITES),
                        ("CANDIDATE_SUITES", CANDIDATE_SUITES), ("candidate", candidate)):
        setattr(a7, name, value)
    # The Attempt 7 forgeries are kept; two of them are now refused for the stricter source-field cause.
    a7._a7_cases = retained_attempt7_cases
    a7.rebind()
    base.CYCLE_ID = CYCLE_ID
    # The v2.4.1 release is this contract's accounting (the Attempt 7 contract used v2.4.0).
    base.GOVERNANCE = GOVERNANCE_V241
    # Attempt 7's own roots are now denied writes: guarded like every earlier attempt's.
    base.GUARDED_ROOTS = tuple(dict.fromkeys(base.GUARDED_ROOTS + (VALIDATION_A07, PACKAGING_A07)))


LaneRun = a7.LaneRun
_ATTEMPT7_CASES = a7._a7_cases


def retained_attempt7_cases() -> list[tuple[str, str, Callable[[sqlite3.Connection], dict[str, Any]], str, str]]:
    """The Attempt 7 anchor forgeries, unchanged in construction. A year-only or team-only substitution moves a genuine
    span onto another job's field -- no longer the victim row's own source field -- so it is now refused as a source
    field witness before any anchor is compared; every other case keeps its cause."""

    stricter = {"a05_year_only_anchor_substitution", "a05_team_only_anchor_substitution"}
    return [(name, fmt, builder, REFUSED_SOURCE_FIELD if name in stricter else code, person)
            for name, fmt, builder, code, person in _ATTEMPT7_CASES()]


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
        problems.append("contract is not Cycle 37 Attempt 8")
    if contract.get("attempt_id") != ATTEMPT_ID:
        problems.append(f"contract attempt_id {contract.get('attempt_id')!r} is not {ATTEMPT_ID}")
    if (contract.get("repo") or {}).get("base_sha") != BASE_SHA:
        problems.append(f"contract base {(contract.get('repo') or {}).get('base_sha')} is not {BASE_SHA}")
    row = {r["id"]: r for r in contract.get("required_lanes", [])}.get(lane)
    if row is None or row.get("executor") != "worker":
        problems.append(f"{lane} is not a worker lane of this contract")
    elif f"attempt08_lanes.py --lane {lane} " not in row.get("command", ""):
        problems.append(f"the contract's command for {lane} does not invoke this runner for this lane")
    if os.path.normcase(str(out_root)) != os.path.normcase(str(Path(contract["paths"]["evidence_root"]))):
        problems.append(f"out-root {out_root} is not the contract evidence root {contract['paths']['evidence_root']}")
    contract["_sha256"] = digest
    contract["_issuance_contract_sha256"] = recorded
    contract["_lane"] = row
    return contract, problems


def bind_source() -> dict[str, Any]:
    binding = a7.bind_source()
    runner = Path(__file__).resolve()
    binding.update({
        "base": BASE_SHA,
        "descends_from_base": base.git("merge-base", "--is-ancestor", BASE_SHA, binding["head"]).returncode == 0
        if binding.get("head") else False,
        "commits_after_base": git_out("rev-list", "--count", f"{BASE_SHA}..{binding['head']}") if binding.get("head")
        else None,
        "runner": str(runner), "runner_sha256": sha256_file(runner), "runner_version": RUNNER_VERSION,
        "rebound_attempt7_runner_sha256": sha256_file(Path(a7.__file__).resolve()),
        "oracle_tool_sha256": sha256_file(ORACLE_TOOL),
    })
    return binding


def _json_file(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).is_file() else None


def _refusal(text: str) -> str | None:
    """The last full refusal code the text names (a traceback's source lines also print constant names)."""

    codes = re.findall(r"REFUSED_[A-Z0-9_]+", text)
    return codes[-1] if codes else None


# ------------------------------------------------------------- lanes: context and storage (MF37A07-02)


def lane_start_context(run: LaneRun) -> None:
    a4.lane_start_context(run)
    state = a7.storage_state()
    run.extra["storage"] = state
    run.problems.extend(a7._storage_problems(state))
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
        else None, "reproduced": reproduction.get("reproduced"),
        "subject_before": {k: (reproduction.get("subject_before") or {}).get(k) for k in ("head", "clean",
                                                                                          "is_issued_base")},
        "started_at": reproduction.get("started_at"), "finished_at": reproduction.get("finished_at"),
        "MF37A07-01": (reproduction.get("MF37A07-01") or {}).get("reproduced"),
        "MF37A07-02": (reproduction.get("MF37A07-02") or {}).get("reproduced")}
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


def _manager_a7_race(run: LaneRun) -> dict[str, Any]:
    """The manager's Attempt 7 same-path race, byte-faithful but for its fixture root, importing this worktree's
    repaired tools. Its scheduler holds the first caller at the child's first INIT lock until a second caller arrives
    -- which the repaired open can no longer do while the first holds the parent's lock -- so the harness's own barrier
    breaks both callers; what must hold is the child: at most one INIT, an intact chain, a usable restart."""

    fixture = run.fresh("mgr_a7_race_fixture")
    literal = f"F=Path(r'{MANAGER_A7_FIXTURE_LITERAL}')/'same-path-continuation-race'"
    copy, replay = a7._replay(run, MANAGER_A7, "storage_same_path_race.py", "mgr_a7_storage_same_path_race",
                              {literal: f"F=Path(r'{fixture}')/'same-path-continuation-race'"})
    record = run.run("manager_a7_same_path_race_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None),
                     note="The manager's saved race; it imports this worktree's storage tools and writes its fixture.")
    review = _json_file(copy.parent / "STORAGE_SAME_PATH_CONCURRENCY.json") or {}
    child = fixture / "same-path-continuation-race" / "child.jsonl"
    try:
        after = snapshot.chain(child)["result"]
    except snapshot.SnapshotRefused as refusal:
        after = refusal.code
    verdict = {**replay, "exit": record.get("exit_code"), "results": review.get("results"),
               "init_count": review.get("init_count"), "chain_in_script": (review.get("chain") or {}).get("result"),
               "restart": review.get("restart"), "chain_after_restart": after,
               "events": len(review.get("events") or []),
               "meaning": ("Before repair both callers wrote an INIT (two INITs, chain broken at line 3, restart refused). "
                           "Repaired, the first caller holds the parent's lock through its INIT, so the harness's barrier "
                           "times out and both of its callers are refused by the harness itself; the child is never "
                           "corrupted and the fresh restart opens it once.")}
    verdict["holds"] = (verdict["init_count"] is not None and verdict["init_count"] <= 1
                        and (verdict["restart"] or {}).get("result") == "OPENED" and after == "PASS")
    return verdict


def _manager_a7_stop_reserve(run: LaneRun) -> dict[str, Any]:
    """The manager's Attempt 7 stop/reserve challenge, byte-faithful but for its fixture root: its saved replay must
    stay refused, and its continuation of a stopped ledger must now be refused where it opens, for want of a plan."""

    fixture = run.fresh("mgr_a7_stop_reserve_fixture")
    literal = f"F=Path(r'{MANAGER_A7_FIXTURE_LITERAL}')/'storage-independent-v2'"
    copy, replay = a7._replay(run, MANAGER_A7, "storage_independent.py", "mgr_a7_storage_independent",
                              {literal: f"F=Path(r'{fixture}')/'storage-independent-v2'"})
    record = run.run("manager_a7_stop_reserve_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None), expect_exit=1,
                     note="The manager's saved challenge; its stopped continuation must now be refused at open.")
    text = Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
    stopped_child = fixture / "storage-independent-v2" / "bounded-stop" / "child.jsonl"
    verdict = {**replay, "exit": record.get("exit_code"), "refusal": _refusal(text),
               "stopped_continuation_created": stopped_child.exists(),
               "replay_folder_first_case_child": (fixture / "storage-independent-v2" / "replay" / "child.jsonl").exists(),
               "meaning": ("Before repair the stopped ledger's continuation admitted with no decision. Repaired, the "
                           "script's own saved-replay and restart cases run first; its stopped-ledger case is refused "
                           "where it opens (a revised plan is required), so the script ends there.")}
    verdict["holds"] = (verdict["exit"] != 0 and verdict["refusal"] == REFUSED_PLAN_REQUIRED
                        and not verdict["stopped_continuation_created"])
    return verdict


def lane_storage_admission(run: LaneRun) -> None:
    a7.lane_storage_admission(run)
    run.extra["attempt7_ledgers_retained"] = {
        p.name: sha256_file(p) for p in sorted((ATTEMPT7_ROOT / "evidence" / "storage").glob("*.jsonl"))
        + [ATTEMPT7_ROOT / "STORAGE_RESERVATIONS.jsonl"]}
    for key, probe in (("manager_a7_same_path_race", _manager_a7_race),
                       ("manager_a7_stop_reserve", _manager_a7_stop_reserve)):
        verdict = probe(run)
        run.extra[key] = verdict
        if not verdict["holds"]:
            run.problems.append(f"the manager's Attempt 7 {key.split('_', 3)[-1]} challenge does not hold against the "
                                f"repaired tools: {verdict}")


def lane_source_regressions(run: LaneRun) -> None:
    a7.lane_source_regressions(run)
    # The Attempt 8 suites against the issued base's exact bytes: they must not pass there.
    folder = run.fresh("unfixed_base")
    archive = subprocess.run(["git", "--no-optional-locks", "-C", str(a6c.WORKTREE), "archive", "--format=tar", BASE_SHA,
                              "src", "tests", "tools"], capture_output=True, check=False)
    if archive.returncode != 0:
        run.problems.append(f"git archive of the issued base failed: {archive.stderr[-400:]}")
        return
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as bundle:
        bundle.extractall(folder, filter="data")
    copied = {}
    for suite in A8_SUITES:
        source = a6c.WORKTREE / "tests" / f"{suite}.py"
        (folder / "tests" / f"{suite}.py").write_bytes(source.read_bytes())
        copied[suite] = sha256_file(source)
    record = run.run("attempt8_suites_on_the_unfixed_base",
                     [run.python, "-B", "-m", "unittest", "-v", *(f"tests.{s}" for s in A8_SUITES)], cwd=folder,
                     env=run.env(pythonpath=None), expect_exit=1, timeout=1800,
                     note="The new suites over a git archive of the issued base 996ada4d; they must not pass there.")
    text = Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
    failed = [m.group(1) for m in re.finditer(r"^(?:FAIL|ERROR): (\S+ \([^)]*\))$", text, re.M)]
    summary = re.findall(r"^(Ran \d+ tests? in [\d.]+s|OK.*|FAILED \(.*\))$", text, re.M)
    verdict = {"base": BASE_SHA, "export": str(folder), "suites": copied, "exit": record.get("exit_code"),
               "summary": summary, "failed_or_errored": failed,
               "modules_failing_to_import": [f for f in failed if "_FailedTest" in f],
               "meaning": ("On the unfixed base the storage suite's deterministic race finds the second caller never "
                           "serialized, and the cases that name the repair's refusals or plan fail; the witness suite "
                           "cannot import the repair's witness module. Neither suite passes there.")}
    verdict["holds"] = record.get("exit_code") not in (0, None) and bool(failed) and not any(
        line.startswith("OK") for line in summary)
    run.extra["attempt8_suites_on_the_unfixed_base"] = verdict
    if not verdict["holds"]:
        run.problems.append("the Attempt 8 suites passed on the unfixed base; they do not test the findings")
    run.extra["attempt8_witness_suite_on_the_unfixed_verifier"] = _witness_suite_on_the_unfixed_verifier(run, folder)


#: The witness suite's cases that forge a witness (each may run several labelled subcases).
WITNESS_FORGERY_TESTS = (
    "test_the_managers_enlarged_envelope_with_the_reciprocal_swap_is_refused",
    "test_year_only_team_only_and_both_field_envelopes_are_refused",
    "test_a_full_page_a_shifted_boundary_and_a_partial_span_are_refused",
    "test_a_witness_moved_onto_another_jobs_genuine_field_is_refused",
    "test_a_list_line_enlarged_over_its_neighbour_is_refused",
    "test_the_envelope_through_the_attempt4_format_entrypoint_is_refused",
    "test_an_attempt4_file_row_carrying_an_envelope_is_refused",
)
#: The suite's genuine-form cases: on the unfixed verifier they attach and fail only reading the repair's new record.
WITNESS_GENUINE_TESTS = ("test_every_genuine_form_attaches_and_serves",
                         "test_a_row_that_records_no_span_is_an_absent_field_not_a_witness")
SERVED, OTHER_CAUSE, ATTACHED, UNCLASSIFIED = ("SERVED_BY_THE_UNFIXED_VERIFIER",
                                               "REFUSED_BY_THE_UNFIXED_VERIFIER_UNDER_ANOTHER_CAUSE",
                                               "ATTACHED_BY_THE_UNFIXED_VERIFIER", "UNCLASSIFIED")
_CASE = r"(test_\w+) \([^)]*\)(?: \(label='([^']*)'\))?"


def _classify_unfixed_verifier_log(text: str) -> tuple[dict[str, str], dict[str, str]]:
    """Every verbose outcome line, and every failure block classified by what the unfixed verifier did: a forgery it
    served fails as ``CareerSuccessorError not raised``; one it refused under its own (Attempt 7) rule errors inside
    ``refused()`` only when the suite compares the refusal to the repair's new code; a genuine form it attached errors
    only when the suite reads the repair's new ``source_witnesses_proved`` record."""

    outcomes = {f"{m.group(1)}[{m.group(2) or ''}]": m.group(3)
                for m in re.finditer(rf"^\s*{_CASE} \.\.\. (ok|FAIL|ERROR)\s*$", text, re.M)}
    classes: dict[str, str] = {}
    for block in re.split(r"^={20,}\s*$", text, flags=re.M):
        head = re.match(rf"\s*(FAIL|ERROR): {_CASE}", block)
        if not head:
            continue
        key = f"{head.group(2)}[{head.group(3) or ''}]"
        if head.group(1) == "FAIL" and "AssertionError: CareerSuccessorError not raised" in block:
            classes[key] = SERVED
        elif (head.group(1) == "ERROR" and "in refused" in block
              and "has no attribute 'REFUSED_SOURCE_FIELD'" in block):
            classes[key] = OTHER_CAUSE
        elif head.group(1) == "ERROR" and "KeyError: 'source_witnesses_proved'" in block:
            classes[key] = ATTACHED
        else:
            classes[key] = UNCLASSIFIED
    return outcomes, classes


def _witness_suite_on_the_unfixed_verifier(run: LaneRun, folder: Path) -> dict[str, Any]:
    """The witness suite against the issued base's verifier, with only the repair's standalone unit reader
    (career_witness.py, which the suite uses to compute its genuine spans) added beside it, so the import no longer
    stands in for a result. Each forgery subcase is then either served by the unfixed verifier (the defect) or refused
    by it under its own earlier rule; none may pass there, and the manager's envelope must be served."""

    helper = a6c.WORKTREE / "src" / "aggie_analytics" / "cycle37" / "career_witness.py"
    target = folder / "src" / "aggie_analytics" / "cycle37" / "career_witness.py"
    if target.exists():
        return {"holds": False, "problem": f"{target} already exists in the base export"}
    target.write_bytes(helper.read_bytes())
    suite = "test_cycle37_a08_source_witness"
    record = run.run("attempt8_witness_suite_on_the_unfixed_verifier",
                     [run.python, "-B", "-m", "unittest", "-v", f"tests.{suite}"], cwd=folder,
                     env=run.env(pythonpath=None), expect_exit=1, timeout=1800,
                     note="The witness suite over the issued base's verifier with only the repair's unit reader added; "
                          "each forgery subcase is classified as served or refused under another cause.")
    outcomes, classes = _classify_unfixed_verifier_log(
        Path(record["log_path"]).read_text(encoding="utf-8", errors="replace"))
    forged = {k: v for k, v in outcomes.items() if k.split("[")[0] in WITNESS_FORGERY_TESTS}
    genuine = {k: v for k, v in outcomes.items() if k.split("[")[0] in WITNESS_GENUINE_TESTS}
    verdict = {"base": BASE_SHA, "export": str(folder), "helper_added": {"path": str(target), "sha256": sha256_file(target)},
               "suite_sha256": sha256_file(a6c.WORKTREE / "tests" / f"{suite}.py"), "exit": record.get("exit_code"),
               "outcomes": outcomes, "classes": classes,
               "forgery_cases": sorted(forged),
               "served_by_the_unfixed_verifier": sorted(k for k in forged if classes.get(k) == SERVED),
               "refused_by_the_unfixed_verifier_under_another_cause":
                   sorted(k for k in forged if classes.get(k) == OTHER_CAUSE),
               "forgery_cases_passing_on_the_unfixed_verifier": sorted(k for k, v in forged.items() if v == "ok"),
               "forgery_cases_unclassified": sorted(k for k, v in forged.items()
                                                    if v != "ok" and classes.get(k) not in (SERVED, OTHER_CAUSE)),
               "genuine_cases_attached_by_the_unfixed_verifier":
                   sorted(k for k, v in genuine.items() if v == "ok" or classes.get(k) == ATTACHED),
               "genuine_cases": sorted(genuine),
               "meaning": ("With the import satisfied, the unfixed verifier serves the forged witnesses its overlap rule "
                           "cannot see (the manager's envelope among them) and refuses the rest only under its earlier "
                           "anchor rule, never as a source-field mismatch; the genuine forms attach there as well.")}
    verdict["holds"] = (record.get("exit_code") not in (0, None)
                        and set(WITNESS_FORGERY_TESTS) <= {k.split("[")[0] for k in forged}
                        and "test_the_managers_enlarged_envelope_with_the_reciprocal_swap_is_refused[]"
                        in verdict["served_by_the_unfixed_verifier"]
                        and not verdict["forgery_cases_passing_on_the_unfixed_verifier"]
                        and not verdict["forgery_cases_unclassified"]
                        and sorted(genuine) == verdict["genuine_cases_attached_by_the_unfixed_verifier"]
                        and set(WITNESS_GENUINE_TESTS) <= {k.split("[")[0] for k in genuine})
    if not verdict["holds"]:
        run.problems.append(f"the witness suite on the unfixed verifier does not show the defect: {classes}")
    return verdict


# ------------------------------------------------------------- the career successor (MF37A07-01)


def _oracle(run: LaneRun, label: str, successor: Path, a04: Path) -> dict[str, Any]:
    out = run.run_dir / f"ORACLE_{label}.json"
    run.run(f"independent_source_field_oracle_{label}", [run.python, "-B", ORACLE_TOOL, "--successor", successor,
                                                         "--a04", a04, "--database", DELIVERED_DB, "--out", out,
                                                         "--label", label],
            env=run.env(pythonpath=None), timeout=3600,
            note="The independent source-field oracle: sqlite3/json/re only, no project module on its path.")
    document = _json_file(out) or {}
    document["receipt"] = {"path": str(out), "sha256": sha256_file(out) if out.is_file() else None}
    return document


def lane_career_successor(run: LaneRun) -> None:
    a6.lane_career_successor(run)
    bindings = run.extra.get("source_identity_bindings") or {}
    a05 = ((bindings.get("A05") or {}).get("lineage_proved_independently_of_the_ledgers") or {})
    a04 = ((bindings.get("A04") or {}).get("lineage_proved_independently_of_the_ledgers") or {})
    default, cross = a05.get("parent_edges_bound_to_source_field") or {}, a05.get("a04_edges_bound_to_source_field") or {}
    older = a04.get("parent_edges_bound_to_source_field") or {}
    witnessed, a04_witnessed = a05.get("source_witnesses_proved") or {}, a05.get("a04_source_witnesses_proved") or {}
    older_witnessed = a04.get("source_witnesses_proved") or {}

    def anchored(counts: dict[str, Any], edges: int) -> bool:
        return counts.get("edges") == edges and (int(counts.get("anchored_by_source_field") or 0)
                                                 + int(counts.get("anchored_by_parameter_only") or 0)) == edges

    checks = {
        "verifier_is_v4": bindings.get("verifier_version") == "BAS-C37A08-CAREER-SUCCESSOR-VERIFIER-v4",
        "a05_every_successor_witness_is_its_source_unit":
            (witnessed.get("successor") or {}).get("rows_proved") == GENUINE_ROWS["A05"],
        "a05_every_named_delivered_witness_is_its_source_unit":
            (witnessed.get("delivered_predecessor") or {}).get("rows_proved") == NAMED_PARENTS["delivered"],
        "a05_every_named_attempt4_witness_is_its_source_unit":
            a04_witnessed.get("rows_proved") == NAMED_PARENTS["attempt4"],
        "a04_format_every_witness_is_its_source_unit":
            (older_witnessed.get("successor") or {}).get("rows_proved") == GENUINE_ROWS["A04"],
        "a05_default_edges_anchored": anchored(default, GENUINE_EDGES["A5<-default"]),
        "a05_a04_edges_anchored": anchored(cross, GENUINE_EDGES["A5<-A4"]),
        "a05_versions_agree_on_every_row": a05.get("rows_whose_versions_agree_on_predecessor_rows") == GENUINE_ROWS["A05"],
        "a04_default_edges_anchored": anchored(older, GENUINE_EDGES["A4<-default"]),
        "captures_read_at_attach": a05.get("source_captures_read_at_attach") == 7950,
    }
    run.extra["source_witness_checks"] = {"checks": checks, "successor": witnessed, "a04_relation": a04_witnessed,
                                          "a04_format": older_witnessed, "default_anchors": default,
                                          "a04_anchors": cross, "a04_format_anchors": older}
    for name, held in checks.items():
        if not held:
            run.problems.append(f"source witness binding: {name} does not hold")
    genuine = _oracle(run, "genuine", A5_SUCCESSOR, A4_SUCCESSOR)
    envelope_ok = sha256_file(MANAGER_A7_ENVELOPE) == MANAGER_A7_ENVELOPE_SHA256
    envelope = _oracle(run, "manager_a7_envelope", MANAGER_A7_ENVELOPE, A4_SUCCESSOR) if envelope_ok else {}
    same_page_ok = SAVED_SAME_PAGE_FIXTURE.is_file() and sha256_file(SAVED_SAME_PAGE_FIXTURE) == SAVED_SAME_PAGE_SHA256
    same_page = _oracle(run, "manager_a6_same_page", SAVED_SAME_PAGE_FIXTURE, A4_SUCCESSOR) if same_page_ok else {}

    def relation_counts(document: dict[str, Any]) -> dict[str, int]:
        return {r["relation"]: r["crossed_edges"] for r in document.get("relations") or []}

    classes = genuine.get("witness_classes") or {}
    exact = ("EXACT_UNIT", "EXACT_UNIT_UNDER_THE_LITERAL_READING")
    verdict = {
        "genuine": {k: genuine.get(k) for k in ("oracle_version", "rows", "captures_read", "captures_unreadable_or_changed",
                                                 "witness_classes", "unit_forms", "crossed_edges", "triangle_mismatches",
                                                 "unresolved", "receipt")}
        | {"relations": [{k: r.get(k) for k in ("relation", "edges", "counts", "crossed_edges",
                                                "edges_into_multi_interval_fields_not_interval_adjudicated")}
                         for r in genuine.get("relations") or []]},
        "manager_a7_envelope": {"fixture": str(MANAGER_A7_ENVELOPE), "sha256_as_issued": envelope_ok,
                                "a05_witness_classes": (envelope.get("witness_classes") or {}).get("A05"),
                                "invalid_witnesses": (envelope.get("invalid_witness_examples") or {}).get("A05"),
                                "crossed_by_relation": relation_counts(envelope), "receipt": envelope.get("receipt")},
        "manager_a6_same_page": {"fixture": str(SAVED_SAME_PAGE_FIXTURE), "sha256_as_saved": same_page_ok,
                                 "crossed_by_relation": relation_counts(same_page), "receipt": same_page.get("receipt")},
    }
    verdict["holds"] = (
        genuine.get("rows") == GENUINE_ROWS and genuine.get("crossed_edges") == 0
        and genuine.get("triangle_mismatches") == 0 and genuine.get("captures_unreadable_or_changed") == 0
        and all(set(counts) <= set(exact) for counts in classes.values())
        and all(not v for v in (genuine.get("unresolved") or {}).values())
        and {r["relation"]: r["edges"] for r in genuine.get("relations") or []} == GENUINE_EDGES
        and envelope_ok and relation_counts(envelope) == {"A5<-default": 2, "A5<-A4": 2, "A4<-default": 0}
        and len((envelope.get("invalid_witness_examples") or {}).get("A05") or []) == 2
        and same_page_ok and relation_counts(same_page) == {"A5<-default": 2, "A5<-A4": 2, "A4<-default": 0})
    run.extra["independent_source_field_oracle"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the independent source-field oracle does not hold: genuine crossed "
                            f"{genuine.get('crossed_edges')}, envelope {relation_counts(envelope)}, same page "
                            f"{relation_counts(same_page)}")


# ------------------------------------------------------------- the installed consumer (MF37A07-01)


def _text_of(row: dict[str, Any]) -> str:
    page = next(iter(json.loads(Path(row["raw_file"]).read_bytes())["query"]["pages"].values()))
    return page["revisions"][0]["slots"]["main"]["*"]


def _span(row: dict[str, Any], field: str) -> list[int]:
    return json.loads(row[f"{field}_char_span"])


def _witness(c: sqlite3.Connection, table: str, row: dict[str, Any], field: str, span: list[int]) -> dict[str, Any]:
    """Give a row a witness that is a genuine substring of its revision at ``span`` (its raw text reproduces it)."""

    text = _text_of(row)
    changes = {f"{field}_char_span": json.dumps(span), f"{field}_raw": text[span[0]:span[1]]}
    if field == "team":
        changes["team_byte_span"] = json.dumps([len(text[:span[0]].encode("utf-8")), len(text[:span[1]].encode("utf-8"))])
    c.execute(f"UPDATE {table} SET " + ", ".join(f"{k}=?" for k in changes) + " WHERE episode_id=?",
              (*changes.values(), row["episode_id"]))
    return {"episode": row["episode_id"], "field": field, "from": row[f"{field}_char_span"], "to": span}


def _fred(c: sqlite3.Connection, table: str = "career_episode_a05") -> tuple[dict[str, Any], dict[str, Any]]:
    return a7._fred_rows(c, table)


def _one_to_one(c: sqlite3.Connection, row: dict[str, Any]) -> bool:
    """One parent in each relation, whose disposition names exactly this row: a swap then changes nothing else, so
    no earlier structural refusal can stand in for the witness's."""

    for key, table, owner, children in (("predecessor_episode_ids", "career_a05_disposition", "predecessor_episode_id",
                                         "successor_episode_ids"),
                                        ("a04_episode_ids", "career_a05_from_a04", "a04_episode_id", "a05_episode_ids")):
        parents = json.loads(row[key] or "[]")
        if len(parents) != 1:
            return False
        named = c.execute(f"SELECT {children} FROM {table} WHERE {owner}=?", (parents[0],)).fetchone()
        if named is None or json.loads(named[0]) != [row["episode_id"]]:
            return False
    return True


def _envelope(fields: tuple[str, ...], swap: bool = True) -> Callable[[sqlite3.Connection], dict[str, Any]]:
    def build(c: sqlite3.Connection) -> dict[str, Any]:
        one, six = _fred(c)
        details: dict[str, Any] = {"swap": a7._swap_edges(c, one, six) if swap else None, "witnesses": []}
        for field in fields:
            lo, hi = min(_span(one, field)[0], _span(six, field)[0]), max(_span(one, field)[1], _span(six, field)[1])
            for row in (one, six):
                details["witnesses"].append(_witness(c, "career_episode_a05", row, field, [lo, hi]))
        return details
    return build


def _full_page(c: sqlite3.Connection) -> dict[str, Any]:
    one, six = _fred(c)
    swap = a7._swap_edges(c, one, six)
    return {"swap": swap, "witnesses": [_witness(c, "career_episode_a05", one, "team", [0, len(_text_of(one))])]}


def _boundary_shift(c: sqlite3.Connection) -> dict[str, Any]:
    one, _ = _fred(c)
    start, end = _span(one, "years")
    return {"swap": None, "witnesses": [_witness(c, "career_episode_a05", one, "years", [start, end + 6])]}


def _partial(c: sqlite3.Connection) -> dict[str, Any]:
    one, _ = _fred(c)
    start, end = _span(one, "team")
    return {"swap": None, "witnesses": [_witness(c, "career_episode_a05", one, "team", [start, min(end, start + 20)])]}


def _same_role_other_period(c: sqlite3.Connection) -> dict[str, Any]:
    """Two numbered jobs of one person with the same employer text (the same role, another period): the first row's
    witnesses move onto the second's genuine fields and its edges onto the second's parents, both relations."""

    for a in c.execute("SELECT * FROM career_episode_a05 WHERE row_index < 1000 AND interval_index = 0 "
                       "AND years_char_span IS NOT NULL AND team_char_span NOT LIKE '[null%' "
                       "AND predecessor_episode_ids != '[]' ORDER BY pageid, row_index").fetchall():
        a = dict(a)
        b = c.execute("SELECT * FROM career_episode_a05 WHERE pageid=? AND revision=? AND family=? AND team_raw=? "
                      "AND row_index > ? AND row_index < 1000 AND interval_index = 0 AND years_char_span IS NOT NULL "
                      "AND years_raw != ? AND predecessor_episode_ids != '[]'",
                      (a["pageid"], a["revision"], a["family"], a["team_raw"], a["row_index"], a["years_raw"])).fetchone()
        if b is None:
            continue
        b = dict(b)
        if not (_one_to_one(c, a) and _one_to_one(c, b)):
            continue
        swap = a7._swap_edges(c, a, b)
        moved = [_witness(c, "career_episode_a05", a, field, _span(b, field)) for field in ("team", "years")]
        return {"victim": a["episode_id"], "other_period": b["episode_id"], "person": a["person_display"],
                "team_raw": a["team_raw"], "swap": swap, "witnesses": moved}
    raise RuntimeError("no two numbered jobs of one person share an employer text for the challenge")


def _list_line_envelope(c: sqlite3.Connection) -> dict[str, Any]:
    for a in c.execute("SELECT * FROM career_episode_a05 WHERE row_index = 1001 AND interval_index = 0 "
                       "AND predecessor_episode_ids != '[]' ORDER BY pageid").fetchall():
        a = dict(a)
        b = c.execute("SELECT * FROM career_episode_a05 WHERE pageid=? AND revision=? AND family=? AND row_index=1002 "
                      "AND interval_index=0", (a["pageid"], a["revision"], a["family"])).fetchone()
        if b is None:
            continue
        b = dict(b)
        return {"victim": a["episode_id"], "neighbour": b["episode_id"], "person": a["person_display"],
                "witnesses": [_witness(c, "career_episode_a05", a, "team", [_span(a, "team")[0], _span(b, "team")[1]])]}
    raise RuntimeError("no list field with two lines for the challenge")


def _a04_format_envelope(c: sqlite3.Connection) -> dict[str, Any]:
    one, six = _fred(c, "career_episode_a04")
    swap = a7._swap_edges(c, one, six, table="career_episode_a04")
    lo, hi = _span(one, "team")[0], _span(six, "team")[1]
    return {"swap": swap, "witnesses": [_witness(c, "career_episode_a04", row, "team", [lo, hi]) for row in (one, six)]}


def _declared_a04_file_envelope(c: sqlite3.Connection) -> dict[str, Any]:
    """Every Attempt 5 row genuine; the declared Attempt 4 file (the successor's own declaration) holds an enlarged
    witness for Fred's first row, resealed, with the Attempt 5 mapping digest recomputed as a careful forger would."""

    a4 = a6._open_fixture(LINEAGE_A04)
    one, six = _fred(a4, "career_episode_a04")
    columns = [r[1] for r in a4.execute("PRAGMA table_info(career_episode_a04)")]

    def digest(identity: str) -> str:
        row = a4.execute(f"SELECT {','.join(chr(34) + x + chr(34) for x in columns)} FROM career_episode_a04 "
                         "WHERE episode_id=?", (identity,)).fetchone()
        return a7._canonical_digest(list(row))

    recorded = c.execute("SELECT a04_row_sha256 FROM career_a05_from_a04 WHERE a04_episode_id=?",
                         (one["episode_id"],)).fetchone()[0]
    if digest(one["episode_id"]) != recorded:
        raise RuntimeError("the table-order row digest does not reproduce the genuine mapping digest")
    witness = _witness(a4, "career_episode_a04", one, "team", [_span(one, "team")[0], _span(six, "team")[1]])
    new_digest = digest(one["episode_id"])
    a6._reseal(a4, a6.A04_TABLES)
    a4.commit()
    a4.close()
    c.execute("UPDATE career_a05_from_a04 SET a04_row_sha256=? WHERE a04_episode_id=?", (new_digest, one["episode_id"]))
    c.execute("UPDATE successor_identity SET value=? WHERE key='a04_successor_path'", (str(LINEAGE_A04),))
    c.execute("UPDATE successor_identity SET value=? WHERE key='a04_successor_sha256'", (sha256_file(LINEAGE_A04),))
    return {"a04_file": str(LINEAGE_A04), "witness": witness, "mapping_digest_recomputed": True}


#: (name, format, builder, person or "" for the builder's own) -- every case must be refused as a source-field witness.
def a8_cases() -> list[tuple[str, str, Callable[[sqlite3.Connection], dict[str, Any]], str]]:
    return [
        ("a05_year_only_envelope", "A05", _envelope(("years",)), FRED),
        ("a05_team_only_envelope", "A05", _envelope(("team",)), FRED),
        ("a05_both_fields_envelope", "A05", _envelope(("team", "years")), FRED),
        ("a05_full_page_witness", "A05", _full_page, FRED),
        ("a05_boundary_shifted_into_the_next_field", "A05", _boundary_shift, FRED),
        ("a05_partial_witness", "A05", _partial, FRED),
        ("a05_witness_moved_onto_another_jobs_field", "A05", _same_role_other_period, ""),
        ("a05_list_line_enlarged_over_its_neighbour", "A05", _list_line_envelope, ""),
        ("a04_format_envelope", "A04", _a04_format_envelope, FRED),
        ("a05_declared_a04_file_envelope", "A05", _declared_a04_file_envelope, FRED),
    ]


def _source_module_entrypoint(run: LaneRun, installed: dict[str, Any], name: str, args: list[Any], *,
                              expect_exit: int = 0) -> dict[str, Any]:
    """The source entrypoint: the same interpreter with the committed subject's ``src`` first on its path."""

    return run.run(name, [installed["python"], "-B", "-P", "-m", "aggie_analytics.cycle33.query", "--database",
                          DELIVERED_DB, *args], cwd=installed["stage"], env=run.env(pythonpath="source"),
                   expect_exit=expect_exit, timeout=3600, note="The source module entrypoint (committed src first).")


def _manager_a7_envelope(run: LaneRun, installed: dict[str, Any]) -> dict[str, Any]:
    """The manager's saved envelope fixture, byte for byte, through all three entrypoints (LINEAGE_ENTRYPOINTS)."""

    with MANAGER_A7_ENVELOPE.open("rb") as reader, LINEAGE_A05.open("r+b") as writer:
        writer.truncate(0)
        shutil.copyfileobj(reader, writer)
    digest = sha256_file(LINEAGE_A05)
    args = ["--career", "--career-successor", LINEAGE_A05, "--career-successor-sha256", digest, "--person", FRED,
            "--compact"]
    records = {"installed_console_script": base._cli(run, installed, "a8_manager_envelope_script", args, expect_exit=1),
               "installed_module": a7._module_entrypoint(run, installed, "a8_manager_envelope_module", args,
                                                         expect_exit=1),
               "source_module": _source_module_entrypoint(run, installed, "a8_manager_envelope_source", args,
                                                          expect_exit=1)}
    refusals = {k: _refusal(Path(r["log_path"]).read_text(encoding="utf-8", errors="replace")) for k, r in records.items()}
    exits = {k: r.get("exit_code") for k, r in records.items()}
    a6._restore(LINEAGE_A05, A5_SUCCESSOR)
    verdict = {"fixture_sha256": digest, "as_issued": digest == MANAGER_A7_ENVELOPE_SHA256, "exits": exits,
               "refusals": refusals, "expected": REFUSED_SOURCE_FIELD,
               "before_repair": "every entrypoint exited 0 serving seven rows (evidence/before/BEFORE_REPRODUCTION.json)"}
    verdict["holds"] = verdict["as_issued"] and all(v == 1 for v in exits.values()) and all(
        v == REFUSED_SOURCE_FIELD for v in refusals.values())
    return verdict


def _a8_forgeries(run: LaneRun, installed: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {"fixtures": {"a05": str(LINEAGE_A05), "a04": str(LINEAGE_A04)}, "cases": {},
                               "expected": REFUSED_SOURCE_FIELD,
                               "rule": ("each case restores its fixture(s) from the genuine files, gives a row a witness "
                                        "that is a genuine substring of its revision but not the source field its "
                                        "identity names (with or without swapping its edges), reseals every ledger as "
                                        "a careful forger would, pins the digest and serves through the console script "
                                        "and the module entrypoint")}
    for name, fmt, builder, person in a8_cases():
        a6._restore(LINEAGE_A05, A5_SUCCESSOR)
        a6._restore(LINEAGE_A04, A4_SUCCESSOR)
        fixture, tables = (LINEAGE_A05, a6.A05_TABLES) if fmt == "A05" else (LINEAGE_A04, a6.A04_TABLES)
        target = a6._open_fixture(fixture)
        details = builder(target)
        a6._reseal(target, tables)
        target.commit()
        target.close()
        digest = sha256_file(fixture)
        who = person or details.get("person") or FRED
        args = ["--career", "--career-successor", fixture, "--career-successor-sha256", digest, "--person", who,
                "--limit", "100", "--compact"]
        script = base._cli(run, installed, f"a8_{name}", args, expect_exit=1)
        module = a7._module_entrypoint(run, installed, f"a8_{name}_module", args, expect_exit=1)
        refusals = {kind: _refusal(Path(record["log_path"]).read_text(encoding="utf-8", errors="replace"))
                    for kind, record in (("script", script), ("module", module))}
        results["cases"][name] = {"format": fmt, "person": who, "fixture_sha256": digest, "details": details,
                                  "script_exit": script.get("exit_code"), "module_exit": module.get("exit_code"),
                                  "refusals": refusals,
                                  "holds": script.get("exit_code") == 1 and module.get("exit_code") == 1
                                  and refusals["script"] == REFUSED_SOURCE_FIELD
                                  and refusals["module"] == REFUSED_SOURCE_FIELD}
        if not results["cases"][name]["holds"]:
            run.problems.append(f"A8 forgery {name} was not refused for its source-field cause at both entrypoints: "
                                f"{refusals}")
    for fixture, source in ((LINEAGE_A05, A5_SUCCESSOR), (LINEAGE_A04, A4_SUCCESSOR)):
        a6._restore(fixture, source)
    results["genuine_unchanged"] = (sha256_file(A5_SUCCESSOR) == A5_SUCCESSOR_SHA256
                                    and sha256_file(A4_SUCCESSOR) == A4_SUCCESSOR_SHA256)
    results["holds"] = results["genuine_unchanged"] and all(row["holds"] for row in results["cases"].values())
    return results


def lane_installed_consumer_c01(run: LaneRun) -> None:
    a7.lane_installed_consumer_c01(run)
    raw = run.extra.get("installed")
    if not raw:
        return
    installed = {key: Path(value) for key, value in raw.items()}
    genuine = {}
    for label, entry in (("source_module", _source_module_entrypoint),):
        args = ["--career", "--career-successor", A5_SUCCESSOR, "--career-successor-sha256", A5_SUCCESSOR_SHA256,
                "--person", FRED, "--compact"]
        record = entry(run, installed, f"a8_genuine_{label}", args)
        genuine[label] = {"exit": record.get("exit_code"),
                          "row_count": (base._stdout_json(record) or {}).get("row_count")}
    run.extra["a8_genuine_source_module"] = {**genuine, "holds": all(v["exit"] == 0 and v["row_count"] == 7
                                                                     for v in genuine.values())}
    if not run.extra["a8_genuine_source_module"]["holds"]:
        run.problems.append(f"the genuine successor does not serve Fred Mariani's seven rows through the source module: "
                            f"{genuine}")
    envelope = _manager_a7_envelope(run, installed)
    run.extra["manager_a7_envelope_entrypoints"] = envelope
    if not envelope["holds"]:
        run.problems.append(f"the manager's saved envelope is not refused for its source-field cause at every "
                            f"entrypoint: {envelope}")
    run.extra["a8_forgeries"] = _a8_forgeries(run, installed)


# ------------------------------------------------------------- the local integration candidate (R37A08-03)


def _manager_a7_committed_tree(run: LaneRun, head: str) -> dict[str, Any]:
    copy, replay = a7._replay(run, MANAGER_A7, "committed_tree_review.py", "mgr_a7_committed_tree")
    record = run.run("manager_a7_committed_tree_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None),
                     note="The manager's saved Attempt 7 committed-byte provenance probe, byte-identical; it reads the "
                          "named candidate branch through this worktree's shared Git store.")
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


def lane_local_integration_candidate(run: LaneRun) -> None:
    a7.lane_local_integration_candidate(run)
    head = (run.extra.get("candidate") or {}).get("candidate_head")
    if not head:
        return
    description = candidate.describe()
    chain = a7._append_chain(head)
    run.extra["candidate_attempt8"] = {
        "appends_continue_0c22af20": chain["holds"],
        "0c22af20_is_ancestor": description.get("attempt8_start_is_ancestor") is True,
        "bb5253b2_is_ancestor": description.get("attempt7_start_is_ancestor") is True,
        "preserved_first_candidate_is_ancestor": description.get("issued_head_is_ancestor") is True}
    run.extra["candidate_append_chain_attempt8"] = chain
    if not all(run.extra["candidate_attempt8"].values()):
        run.problems.append(f"the candidate does not continue the granted head: {run.extra['candidate_attempt8']}")
    if not run.rehearsal:
        verdict = _manager_a7_committed_tree(run, head)
        run.extra["manager_a7_committed_tree"] = verdict
        if not verdict["holds"]:
            run.problems.append(f"the manager's Attempt 7 committed-tree review finds mismatches: {verdict}")


# ------------------------------------------------------------- mounted, unmounted, platform and packet lanes


def _attempt7_final(lane: str) -> dict[str, Any]:
    rows = [json.loads(line) for line in (ATTEMPT7_ROOT / "lanes" / "RUNS.jsonl").read_text(encoding="utf-8")
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
    previous = _attempt7_final("FULL_FINAL_MOUNTED")
    comparison: dict[str, Any] = {"attempt7_receipt": previous.get("receipt"),
                                  "attempt7_receipt_sha256": previous.get("receipt_sha256"),
                                  "attempt7_run": previous.get("run"), "attempt7_result": previous.get("result")}
    if previous:
        a7_log = Path(next(c["log_path"] for c in previous["data"]["commands"]
                           if c["lane"].endswith("full_suite_mounted")))
        before = base._log_identities(a7_log)
        persisting = sorted(set(final["failed_or_errored"]) & set(before["failed_or_errored"]))
        new = sorted(set(final["failed_or_errored"]) - set(before["failed_or_errored"]))
        final_causes = base._failure_causes(log, persisting)
        before_causes = base._failure_causes(a7_log, persisting)
        comparison.update({
            "attempt7_log": str(a7_log), "attempt7_log_sha256": sha256_file(a7_log),
            "attempt7_tests_run": before["tests_run"], "final_tests_run": final["tests_run"],
            "attempt7_failed_or_errored": before["failed_or_errored"], "persisting": persisting,
            "new_in_attempt8": new,
            "no_longer_failing": sorted(set(before["failed_or_errored"]) - set(final["failed_or_errored"])),
            "new_failure_causes": base._failure_causes(log, new),
            "persisting_same_cause": sorted(i for i in persisting if final_causes[i] == before_causes[i]),
            "persisting_changed_cause": {i: {"attempt7": before_causes[i], "attempt8": final_causes[i]}
                                         for i in persisting if final_causes[i] != before_causes[i]},
        })
        if new:
            run.problems.append(f"new failing identities relative to Attempt 7: {new}")
    run.extra["attempt7_comparison"] = comparison


def lane_strict_mounted(run: LaneRun) -> None:
    base.lane_strict_mounted(run)
    final = [row["identity"] for row in run.extra.get("strict_findings") or []]
    previous = _attempt7_final("STRICT_MOUNTED")
    comparison: dict[str, Any] = {"attempt7_receipt": previous.get("receipt"), "attempt7_run": previous.get("run"),
                                  "attempt7_result": previous.get("result")}
    if previous:
        before = [row["identity"] for row in (previous["data"].get("details") or {}).get("strict_findings") or []]
        comparison.update({"attempt7_findings": before, "final_findings": final,
                           "persisting": sorted(set(final) & set(before)),
                           "new_in_attempt8": sorted(set(final) - set(before)),
                           "no_longer_reported": sorted(set(before) - set(final))})
        if comparison["new_in_attempt8"]:
            run.problems.append(f"new strict findings relative to Attempt 7: {comparison['new_in_attempt8']}")
    run.extra["attempt7_comparison"] = comparison


LANE_FUNCTIONS: dict[str, Callable[[LaneRun], None]] = {
    "START_CONTEXT": lane_start_context,
    "WRITE_PROTECTION": a7.lane_write_protection,
    "STORAGE_ADMISSION": lane_storage_admission,
    "SOURCE_ADMISSION": a7.lane_source_admission,
    "SOURCE_HARNESS": a7.lane_source_harness,
    "SOURCE_REGRESSIONS": lane_source_regressions,
    "CAREER_SUCCESSOR": lane_career_successor,
    "INSTALLED_CONSUMER_C01": lane_installed_consumer_c01,
    "LOCAL_INTEGRATION_CANDIDATE": lane_local_integration_candidate,
    "TRUE_UNMOUNTED": a7.lane_true_unmounted,
    "FULL_FINAL_MOUNTED": lane_full_final_mounted,
    "STRICT_MOUNTED": lane_strict_mounted,
    "PLATFORM_CARRY": a7.lane_platform_carry,
    "FINAL_PACKET": a7.lane_final_packet,
}


# ------------------------------------------------------------- the runner


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
    paths = a7.storage_paths(out_root, args.rehearsal and final_lane) if not blocked else {}
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
