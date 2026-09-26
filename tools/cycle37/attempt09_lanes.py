r"""Cycle #37 — Attempt #9 — the lane runner (R37A09-05).

    attempt09_lanes.py --lane <ID> --contract <cycle_contract.json> --out-root <attempt root> [--rehearsal]

The preserved Attempt 8 runner (``attempt08_lanes``, over the Attempt 7, 6, 5, 4 and 3 runners) rebound to the Attempt 9
contract, roots, ledger, suites and tools. Everything the earlier runners bind per run is still bound -- the issued
contract by its sealed digest, the committed subject (branch, head, tree, source digest, descent from the issued base, a
clean tree before and after), the interpreter, module origins, the delivered database by digest, the data root and
``C:\All-22`` measured before and after, the main checkout and both integration worktrees, credential removal, and the
guard and storage qualification of the costly lanes. What Attempt 9 changes:

* **START_CONTEXT** binds the intake record, the before-repair reproduction of MF37A08-01/-02 and the Git
  housekeeping preflight receipts.
* **STORAGE_ADMISSION (MF37A08-02)** adds the root-contract suite and replays the manager's Attempt 8 continuation
  challenge (only its fixture root adapted): one INIT across twelve processes, and the same-child restart naming an
  extra empty root refused as ``REFUSED_CONTINUATION_ROOT_CONTRACT_DIFFERS`` before any record.
* **SOURCE_REGRESSIONS** runs the two Attempt 9 suites against the exact bytes of the issued base (a ``git archive`` of
  ``91a83b19``) and classifies every failure by what the unfixed verifier or tool did: every negative case must fail
  there, and the saved constructions must be served (accepted) by it.
* **CAREER_SUCCESSOR (MF37A08-01)** checks the v5 verifier's identity-derived units over both genuine successors and
  runs the independent identity-derived oracle (``a09_source_unit_oracle.py``) over the genuine files and the saved
  manager fixtures (the Attempt 8 NULL-span construction, the Attempt 7 envelope, the Attempt 6 same-page swap); the
  Attempt 8 oracle runs too.
* **INSTALLED_CONSUMER_C01** replays the manager's saved NULL-span fixture byte for byte through the installed console
  script, the installed module and the source module, and serves this attempt's missing-witness matrix -- the saved
  construction in four absent spellings, missingness with forged edges and the rows' own or blank text, team-only and
  year-only absence, the same role in another period, the Attempt 4 relation alone, the Attempt 4 format, a relabelled
  declared Attempt 4 row, a row naming no source unit, and list-line years text outside the line -- each restored from
  the genuine file, resealed and refused for its own cause through the console script and the module.
* **LOCAL_INTEGRATION_CANDIDATE** verifies the Attempt 9 appends continue ``c52e7b52`` with no pack written, replays
  the manager's Attempt 8, 7 and 6 committed-tree reviews, and re-binds the retained CONTROL-07 proposal offline at
  this head.

Every lane also measures the shared Git store (packs, loose objects, refs) before and after it runs; a pack written or
removed, a loose object gone or a ref moved during a lane fails it.
* **FULL_FINAL_MOUNTED / STRICT_MOUNTED** compare identities with the Attempt 8 final receipts at the issued base.

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

import attempt08_lanes as a8  # noqa: E402  (the preserved Attempt 8 runner)
import attempt09_candidate as candidate  # noqa: E402
import attempt09_git  # noqa: E402

a7, a6, a5, a4, base, a6c = a8.a7, a8.a6, a8.a5, a8.a4, a8.base, a8.a6c
storage, snapshot = a8.storage, a8.snapshot
BLOCKED, DATA_ROOT, DELIVERED_DB, FAIL, PASS = a8.BLOCKED, a8.DATA_ROOT, a8.DELIVERED_DB, a8.FAIL, a8.PASS
Tee, credential_scrub, git_out, sha256_bytes, sha256_file, utc_now = (a8.Tee, a8.credential_scrub, a8.git_out,
                                                                      a8.sha256_bytes, a8.sha256_file, a8.utc_now)

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 9
CYCLE_ID = "CYCLE-37"
ATTEMPT_ID = "ATTEMPT-09-20260926"
RUNNER_VERSION = "BAS-C37-ATTEMPT09-LANES-v1"
BASE_SHA = "91a83b197d8523d26aaa3d2683fa75a8ed9d5be9"
BRANCH = "codex/BAT-706-cycle37-rework"
LABEL = "Cycle #37 \u2014 Attempt #9 \u2014"
LANES = a8.LANES
GATED = a8.GATED
MIB = 1024 * 1024
#: Each lane's reservation, from the measured Attempt 8 costs with margin, plus this attempt's additions (the base
#: export and its two suites, the second oracle's four receipts, fourteen more forgeries and the saved fixture replay).
LANE_ESTIMATES = {
    "START_CONTEXT": 16 * MIB, "WRITE_PROTECTION": 32 * MIB, "STORAGE_ADMISSION": 64 * MIB,
    "SOURCE_ADMISSION": 32 * MIB, "SOURCE_HARNESS": 32 * MIB, "SOURCE_REGRESSIONS": 192 * MIB,
    "CAREER_SUCCESSOR": 128 * MIB, "INSTALLED_CONSUMER_C01": 640 * MIB, "LOCAL_INTEGRATION_CANDIDATE": 288 * MIB,
    "TRUE_UNMOUNTED": 32 * MIB, "FULL_FINAL_MOUNTED": 64 * MIB, "STRICT_MOUNTED": 32 * MIB,
    "PLATFORM_CARRY": 160 * MIB, "FINAL_PACKET": 32 * MIB,
}

EVIDENCE_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt09"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a09")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37a09")
ATTEMPT8_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt08"
VALIDATION_A08 = Path(r"C:\BatteredAggieSyndrome.validation\c37a08")
PACKAGING_A08 = Path(r"C:\BatteredAggieSyndrome.packaging\c37a08")
MANAGER_A8 = DATA_ROOT / "ops" / "manager_reviews" / "cycle37" / "attempt08" / "review-20260926T151153Z"
MANAGER_A8_FIXTURE_LITERAL = r"C:\BatteredAggieSyndrome.validation\mr37a08-151153"
MANAGER_A8_NULL_SPAN = Path(MANAGER_A8_FIXTURE_LITERAL) / "adversarial.sqlite"
MANAGER_A8_NULL_SPAN_SHA256 = "b40bb1970d9a6119ff5bb88821c579bcac414ead0c8f3b3b8792273756d437a8"
A5_SUCCESSOR, A5_SUCCESSOR_SHA256 = a8.A5_SUCCESSOR, a8.A5_SUCCESSOR_SHA256
A4_SUCCESSOR, A4_SUCCESSOR_SHA256 = a8.A4_SUCCESSOR, a8.A4_SUCCESSOR_SHA256
OPERATIONAL_LEDGER = EVIDENCE_ROOT / "STORAGE_RESERVATIONS.jsonl"
FINAL_SNAPSHOT = EVIDENCE_ROOT / "STORAGE_EVIDENCE_SNAPSHOT.json"
FINAL_OUTPUT_LEDGER = EVIDENCE_ROOT / "evidence" / "storage" / "STORAGE_RESERVATIONS_FINAL_OUTPUT.jsonl"
CANDIDATE_RECORDS = EVIDENCE_ROOT / "evidence" / "integration"
BEFORE_REPRODUCTION = EVIDENCE_ROOT / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
INTAKE = EVIDENCE_ROOT / "evidence" / "intake" / "INTAKE.json"
GIT_PREFLIGHTS = (EVIDENCE_ROOT / "evidence" / "intake" / "GIT_HOUSEKEEPING_PREFLIGHT.json",
                  EVIDENCE_ROOT / "evidence" / "intake" / "GIT_HELPER_CONSTRUCTION.json")
FIXTURES = VALIDATION_ROOT / "fixtures"
#: One owned full copy of each genuine successor, restored before every use. The Attempt 5 copy is the one the
#: before-repair reproduction made from the manager's NULL-span fixture; every lane restores it before it forges.
MANAGER_ADVERSARIAL_FIXTURE = FIXTURES / "mr"
LINEAGE_A05 = MANAGER_ADVERSARIAL_FIXTURE / "adversarial.sqlite"
LINEAGE_A04 = FIXTURES / "lineage" / "successor_a04.sqlite"
AFTER_COMMENTS = (("BAT-706", "C37-A09-AFTER-HANDOFF-BAT-706"), ("BAT-708", "C37-A09-AFTER-HANDOFF-BAT-708"))
PLATFORM_TOOL = "tools/cycle37/attempt09_platform.py"
OUTPUTS_TOOL = "tools/cycle37/attempt09_outputs.py"
CONTROL_TOOL = Path(__file__).resolve().parent / "attempt09_control07.py"
ORACLE_TOOL = Path(__file__).resolve().parent / "a09_source_unit_oracle.py"
FRED = a8.FRED
A9_SUITES = ("test_cycle37_a09_continuation_roots", "test_cycle37_a09_missing_witness")
STORAGE_SUITES = a8.STORAGE_SUITES + ("test_cycle37_a09_continuation_roots",)
CAREER_SUITES = a8.CAREER_SUITES + ("test_cycle37_a09_missing_witness",)
REGRESSION_SUITES = a8.REGRESSION_SUITES + A9_SUITES
CANDIDATE_SUITES = a8.CANDIDATE_SUITES + A9_SUITES

REFUSED_SOURCE_FIELD = "REFUSED_CAREER_SUCCESSOR_SOURCE_FIELD_WITNESS_MISMATCH"
REFUSED_EPISODE = "REFUSED_CAREER_SUCCESSOR_EPISODE_ANCHOR_MISMATCH"
REFUSED_UNANCHORED = "REFUSED_CAREER_SUCCESSOR_UNANCHORED_LINEAGE"
REFUSED_A04_ANCHOR = "REFUSED_CAREER_SUCCESSOR_A04_ANCHOR_MISMATCH"
REFUSED_A04_IDENTITY = "REFUSED_CAREER_SUCCESSOR_A04_IDENTITY_MISMATCH"
REFUSED_ROOTS = "REFUSED_CONTINUATION_ROOT_CONTRACT_DIFFERS"
REFUSED_PLAN_REQUIRED = "REFUSED_CONTINUATION_REVISED_PLAN_REQUIRED"
REFUSED_CLAIMED = "REFUSED_CONTINUATION_ALREADY_CLAIMED"
GENUINE_ROWS = a8.GENUINE_ROWS
GENUINE_EDGES = a8.GENUINE_EDGES
NAMED_PARENTS = a8.NAMED_PARENTS


def rebind() -> None:
    """Point the preserved runners at the Attempt 9 contract, roots, ledger, suites, tools and grants."""

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
        setattr(a8, name, value)
    a8.rebind()
    base.CYCLE_ID = CYCLE_ID
    # Attempt 8's own roots are now denied writes: guarded like every earlier attempt's. The manager's saved Attempt 8
    # fixture folder is manager-owned and immutable: read (and copied from) only, so it is guarded too.
    base.GUARDED_ROOTS = tuple(dict.fromkeys(base.GUARDED_ROOTS + (VALIDATION_A08, PACKAGING_A08,
                                                                   Path(MANAGER_A8_FIXTURE_LITERAL))))
    # Every Git command the candidate-append chain builds carries -c gc.auto=0 -c maintenance.auto=false.
    attempt09_git.install()


LaneRun = a8.LaneRun


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
        problems.append("contract is not Cycle 37 Attempt 9")
    if contract.get("attempt_id") != ATTEMPT_ID:
        problems.append(f"contract attempt_id {contract.get('attempt_id')!r} is not {ATTEMPT_ID}")
    if (contract.get("repo") or {}).get("base_sha") != BASE_SHA:
        problems.append(f"contract base {(contract.get('repo') or {}).get('base_sha')} is not {BASE_SHA}")
    row = {r["id"]: r for r in contract.get("required_lanes", [])}.get(lane)
    if row is None or row.get("executor") != "worker":
        problems.append(f"{lane} is not a worker lane of this contract")
    elif f"attempt09_lanes.py --lane {lane} " not in row.get("command", ""):
        problems.append(f"the contract's command for {lane} does not invoke this runner for this lane")
    if os.path.normcase(str(out_root)) != os.path.normcase(str(Path(contract["paths"]["evidence_root"]))):
        problems.append(f"out-root {out_root} is not the contract evidence root {contract['paths']['evidence_root']}")
    contract["_sha256"] = digest
    contract["_issuance_contract_sha256"] = recorded
    contract["_lane"] = row
    return contract, problems


def bind_source() -> dict[str, Any]:
    binding = a8.bind_source()
    runner = Path(__file__).resolve()
    binding.update({
        "base": BASE_SHA,
        "descends_from_base": base.git("merge-base", "--is-ancestor", BASE_SHA, binding["head"]).returncode == 0
        if binding.get("head") else False,
        "commits_after_base": git_out("rev-list", "--count", f"{BASE_SHA}..{binding['head']}") if binding.get("head")
        else None,
        "runner": str(runner), "runner_sha256": sha256_file(runner), "runner_version": RUNNER_VERSION,
        "rebound_attempt8_runner_sha256": sha256_file(Path(a8.__file__).resolve()),
        "a09_oracle_tool_sha256": sha256_file(ORACLE_TOOL),
        "git_wrapper_sha256": sha256_file(Path(attempt09_git.__file__).resolve()),
        "candidate_tool_sha256": sha256_file(Path(candidate.__file__).resolve()),
        "control07_tool_sha256": sha256_file(CONTROL_TOOL),
    })
    return binding


def _json_file(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).is_file() else None


def _refusal(text: str) -> str | None:
    """The last full refusal code the text names (a traceback's source lines also print constant names)."""

    codes = re.findall(r"REFUSED_[A-Z0-9_]+", text)
    return codes[-1] if codes else None


# ------------------------------------------------------------- context


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
        "MF37A08-01": (reproduction.get("MF37A08-01") or {}).get("reproduced"),
        "MF37A08-02": (reproduction.get("MF37A08-02") or {}).get("reproduced")}
    if not (reproduction.get("reproduced") and (reproduction.get("subject_before") or {}).get("is_issued_base")):
        run.problems.append("the before-repair reproduction is missing or did not reproduce both findings on the base")
    intake = _json_file(INTAKE) or {}
    run.extra["intake"] = {"file": str(INTAKE), "sha256": sha256_file(INTAKE) if INTAKE.is_file() else None,
                           "contract_matches_issuance": (intake.get("contract") or {}).get("matches_issuance"),
                           "sources_all_match": intake.get("sources_all_match"),
                           "closures": {k: {kk: v.get(kk) for kk in ("archive_matches", "entries", "archived_mismatches")}
                                        for k, v in (intake.get("closures") or {}).items()},
                           "subjects": {k: (intake.get("subjects") or {}).get(k) for k in
                                        ("repair_is_issued_base", "candidate_is_granted_head", "main_is_recorded")}}
    if not (intake.get("sources_all_match") and (intake.get("contract") or {}).get("matches_issuance")):
        run.problems.append("the intake record does not bind every issued source and the sealed contract")
    preflights = {}
    for path in GIT_PREFLIGHTS:
        document = _json_file(path) or {}
        preflights[path.name] = {"sha256": sha256_file(path) if path.is_file() else None, "holds": document.get("holds")}
    run.extra["git_housekeeping_preflight"] = preflights
    if not all(row["holds"] for row in preflights.values()):
        run.problems.append(f"the Git housekeeping preflight does not hold: {preflights}")
    run.extra["guard"] = {"path": str(a8.GUARD), "sha256": sha256_file(a8.GUARD)}
    run.extra["integration_candidate"] = {"state": a5.candidate_state(), "description": candidate.describe()}
    proposed = EVIDENCE_ROOT / "evidence" / "control07" / "proposed"
    run.extra["control07_proposal_inputs"] = {
        "root": str(proposed), "files": {p.relative_to(proposed).as_posix(): sha256_file(p)
                                         for p in sorted(proposed.rglob("*")) if p.is_file()},
        "outside_every_checkout": all(checkout not in proposed.parents
                                      for checkout in (a6c.WORKTREE, candidate.CANDIDATE_WORKTREE, base.MAIN_CHECKOUT))}
    run.extra["platform_receipts"] = sorted(str(p.relative_to(EVIDENCE_ROOT)) for p in
                                            (EVIDENCE_ROOT / "evidence" / "platform").rglob("*.json"))


# ------------------------------------------------------------- storage (MF37A08-02)


def _manager_a8_storage(run: LaneRun) -> dict[str, Any]:
    """The manager's Attempt 8 continuation challenge, byte-faithful but for its fixture root, importing this
    worktree's repaired tools: one INIT across twelve processes still, and the restart naming an extra empty root now
    refused for its root contract before any record (bytes written there afterwards are not tracked, and no headroom
    changed)."""

    fixture = run.fresh("mgr_a8_storage_fixture")
    literal = f"F=Path(r'{MANAGER_A8_FIXTURE_LITERAL}')/'storage-independent'"
    copy, replay = a7._replay(run, MANAGER_A8, "storage_independent.py", "mgr_a8_storage_independent",
                              {literal: f"F=Path(r'{fixture}')/'storage-independent'"})
    record = run.run("manager_a8_storage_independent_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None),
                     note="The manager's saved Attempt 8 challenge; it imports this worktree's storage tools.")
    review = _json_file(copy.parent / "STORAGE_INDEPENDENT.json") or {}
    cases = {row["case"]: row for row in review.get("cases") or []}
    concurrent = cases.get("12 concurrent separate processes same child") or {}
    extra = cases.get("same-child restart requests additional empty tracked root") or {}
    others = {name: (row.get("result") or {}).get("code") for name, row in cases.items()
              if name not in ("12 concurrent separate processes same child",
                              "same-child restart requests additional empty tracked root")}
    child = fixture / "storage-independent" / "concurrent" / "child.jsonl"
    rows = storage.Ledger(child).records() if child.is_file() else []
    verdict = {**replay, "exit": record.get("exit_code"), "source": review.get("source"),
               "concurrent": {"results": [json.loads(r.get("stdout") or "{}") for r in concurrent.get("results") or []],
                              "init_count": concurrent.get("init_count"),
                              "chain": (concurrent.get("chain") or {}).get("result"),
                              "restart": (concurrent.get("restart") or {}).get("result")},
               "extra_root_restart": {"result": (extra.get("result") or {}).get("result"),
                                      "code": (extra.get("result") or {}).get("code"),
                                      "root_measured": extra.get("root_measured"),
                                      "measured_added": extra.get("measured_added")},
               "child_records_after": [r["kind"] for r in rows], "other_cases": others,
               "before_repair": ("resumed=True, the extra root unrecorded and 10,000 bytes there measured as 0 added "
                                 "(evidence/before/BEFORE_REPRODUCTION.json)")}
    verdict["concurrent"]["fresh_opens"] = sum(1 for r in verdict["concurrent"]["results"] if r.get("resumed") is False)
    verdict["concurrent"]["resumed_opens"] = sum(1 for r in verdict["concurrent"]["results"] if r.get("resumed") is True)
    verdict["holds"] = (record.get("exit_code") == 0 and verdict["concurrent"]["init_count"] == 1
                        and verdict["concurrent"]["fresh_opens"] == 1 and verdict["concurrent"]["resumed_opens"] == 11
                        and verdict["concurrent"]["chain"] == "PASS" and verdict["concurrent"]["restart"] == "OPENED"
                        and verdict["extra_root_restart"]["result"] == "REFUSED"
                        and verdict["extra_root_restart"]["code"] == REFUSED_ROOTS
                        and verdict["extra_root_restart"]["root_measured"] is False
                        and verdict["child_records_after"] == ["INIT", "OPENED"]
                        and others.get("stopped parent without revised plan") == REFUSED_PLAN_REQUIRED
                        and others.get("changed reserve without revised plan") == REFUSED_PLAN_REQUIRED
                        and others.get("second child cannot recycle headroom") == REFUSED_CLAIMED)
    return verdict


def lane_storage_admission(run: LaneRun) -> None:
    a8.lane_storage_admission(run)
    run.extra["attempt8_ledgers_retained"] = {
        p.name: sha256_file(p) for p in sorted((ATTEMPT8_ROOT / "evidence" / "storage").glob("*.jsonl"))
        + [ATTEMPT8_ROOT / "STORAGE_RESERVATIONS.jsonl"]}
    verdict = _manager_a8_storage(run)
    run.extra["manager_a8_storage_independent"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's Attempt 8 continuation challenge does not hold against the repaired tools: "
                            f"{ {k: v for k, v in verdict.items() if k not in ('literal_adaptations',)} }")


# ------------------------------------------------------------- the new suites on the unfixed base


#: The Attempt 9 suites' negative cases: every one must fail over the unfixed base's bytes.
NEGATIVE_TESTS = {
    "test_cycle37_a09_missing_witness": (
        "test_the_managers_null_span_enlarged_text_swap_is_refused_in_every_absent_spelling",
        "test_missing_witnesses_with_forged_edges_are_refused_whatever_text_they_carry",
        "test_the_same_role_in_another_period_is_refused_without_witnesses",
        "test_the_attempt4_relation_alone_is_refused", "test_the_attempt4_format_entrypoint_is_refused",
        "test_a_declared_attempt4_file_row_without_witnesses_is_refused",
        "test_a_declared_attempt4_file_row_relabelled_under_another_identity_is_refused",
        "test_a_row_naming_no_source_unit_anchors_no_edge", "test_no_comparable_field_and_another_parameter_is_unanchored",
        "test_a_lines_years_text_outside_its_line_is_refused", "test_the_absent_spellings_and_malformed_spans",
        "test_resolve_unit_refuses_ambiguity_and_text_without_a_unit",
        "test_genuinely_absent_witnesses_keep_their_meaning_in_every_spelling"),
    "test_cycle37_a09_continuation_roots": (
        "test_the_saved_additional_empty_root_restart_is_refused_before_any_effect",
        "test_a_nonempty_added_root_on_restart_is_refused", "test_omitting_a_root_the_child_was_opened_with_is_refused",
        "test_a_changed_shared_set_is_refused", "test_a_root_moved_between_classes_is_refused_at_open_and_on_restart",
        "test_processes_racing_with_competing_root_sets_open_one_contract",
        "test_an_interrupted_claim_is_completed_only_under_the_roots_it_claimed",
        "test_a_claim_recording_no_root_contract_cannot_be_completed",
        "test_an_interrupted_init_is_completed_only_under_its_own_roots",
        "test_no_refused_call_resets_the_baseline_or_adds_headroom",
        "test_twelve_processes_with_one_contract_in_different_spellings_leave_one_child"),
}
ACCEPTED, OTHER_CAUSE, NEW_API, BEHAVIOR, UNCLASSIFIED = (
    "ACCEPTED_BY_THE_UNFIXED_CODE", "REFUSED_BY_THE_UNFIXED_CODE_UNDER_ANOTHER_CAUSE",
    "NEW_API_OR_RECORD_ABSENT_IN_THE_UNFIXED_CODE", "OTHER_BEHAVIOR_OF_THE_UNFIXED_CODE", "UNCLASSIFIED")
_CASE = r"(test_\w+) \((tests\.\w+)\.\w+\.\w+\)(?: \((.*?)\))?"


def classify_unfixed_log(text: str) -> tuple[dict[str, str], dict[str, str]]:
    """Every verbose outcome line, and every failure block classified by what the unfixed code did."""

    outcomes = {f"{m.group(2).split('.')[-1]}::{m.group(1)}[{m.group(3) or ''}]": m.group(4)
                for m in re.finditer(rf"^\s*{_CASE} \.\.\. (ok|FAIL|ERROR)\s*$", text, re.M)}
    classes: dict[str, str] = {}
    for block in re.split(r"^={20,}\s*$", text, flags=re.M):
        head = re.match(rf"\s*(FAIL|ERROR): {_CASE}\s*$", block, re.M)
        if not head:
            continue
        key = f"{head.group(3).split('.')[-1]}::{head.group(2)}[{head.group(4) or ''}]"
        errors = [line for line in block.splitlines() if re.match(r"^[A-Za-z]+Error:", line)]
        last = errors[-1] if errors else ""
        if re.search(r"AssertionError: (CareerSuccessorError|SnapshotRefused) not raised", last):
            classes[key] = ACCEPTED
        elif last.startswith("AssertionError: ") and "REFUSED_" in last:
            classes[key] = OTHER_CAUSE
        elif last.startswith(("AttributeError: ", "KeyError: ")):
            classes[key] = NEW_API
        elif last.startswith("AssertionError: "):
            classes[key] = BEHAVIOR
        else:
            classes[key] = UNCLASSIFIED
    return outcomes, classes


def _suites_on_the_unfixed_base(run: LaneRun) -> dict[str, Any]:
    folder = run.fresh("unfixed_base")
    archive = subprocess.run(attempt09_git.command("archive", "--format=tar", BASE_SHA, "src", "tests", "tools",
                                                   repo=a6c.WORKTREE), capture_output=True, check=False)
    if archive.returncode != 0:
        return {"holds": False, "problem": f"git archive of the issued base failed: {archive.stderr[-400:]!r}"}
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as bundle:
        bundle.extractall(folder, filter="data")
    copied = {}
    for suite in A9_SUITES:
        source = a6c.WORKTREE / "tests" / f"{suite}.py"
        (folder / "tests" / f"{suite}.py").write_bytes(source.read_bytes())
        copied[suite] = sha256_file(source)
    record = run.run("attempt9_suites_on_the_unfixed_base",
                     [run.python, "-B", "-m", "unittest", "-v", *(f"tests.{s}" for s in A9_SUITES)], cwd=folder,
                     env=run.env(pythonpath=None), expect_exit=1, timeout=1800,
                     note="The two new suites over a git archive of the issued base 91a83b19; every negative case must "
                          "fail there, and the saved constructions must be accepted by the unfixed code.")
    text = Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
    outcomes, classes = classify_unfixed_log(text)
    negative_keys = {k for k in outcomes if k.split("[")[0].split("::")[1] in NEGATIVE_TESTS[k.split("::")[0]]}
    passing_negatives = sorted(k for k in negative_keys if outcomes[k] == "ok")
    wanted = {f"{suite}::{name}" for suite, names in NEGATIVE_TESTS.items() for name in names}
    seen = {k.split("[")[0] for k in negative_keys}
    manager = "test_cycle37_a09_missing_witness::test_the_managers_null_span_enlarged_text_swap_is_refused_in_every_absent_spelling[absent='SQL NULL']"
    saved_root = "test_cycle37_a09_continuation_roots::test_the_saved_additional_empty_root_restart_is_refused_before_any_effect[]"
    verdict = {"base": BASE_SHA, "export": str(folder), "suites": copied, "exit": record.get("exit_code"),
               "outcomes": outcomes, "classes": classes,
               "negative_cases": len(negative_keys), "negative_tests_seen": sorted(seen),
               "negative_tests_missing": sorted(wanted - seen), "negative_cases_passing_on_the_base": passing_negatives,
               "accepted_by_the_unfixed_code": sorted(k for k, v in classes.items() if v == ACCEPTED),
               "refused_under_another_cause": sorted(k for k, v in classes.items() if v == OTHER_CAUSE),
               "new_api_or_record_absent": sorted(k for k, v in classes.items() if v == NEW_API),
               "other_behavior": sorted(k for k, v in classes.items() if v == BEHAVIOR),
               "unclassified": sorted(k for k, v in classes.items() if v == UNCLASSIFIED),
               "positive_cases_on_the_base": {k: v for k, v in outcomes.items() if k not in negative_keys},
               "saved_constructions": {"manager_null_span_sql_null": classes.get(manager),
                                       "saved_extra_empty_root_restart": classes.get(saved_root)},
               "meaning": ("Over the unfixed base every negative case fails: the saved NULL-span construction (SQL NULL, "
                           "JSON null, [null, null]) and missingness with enlarged text are served, the saved extra-root "
                           "restart and every changed root contract are accepted; other forgeries are refused there only "
                           "under the earlier text or parameter anchors; the unit-level cases find the new API absent. "
                           "Positive cases (the genuine fixture, own-text absence, same roots in any spelling) may pass.")}
    verdict["holds"] = (record.get("exit_code") not in (0, None) and not passing_negatives and not verdict["unclassified"]
                        and not verdict["negative_tests_missing"]
                        and verdict["saved_constructions"]["manager_null_span_sql_null"] == ACCEPTED
                        and verdict["saved_constructions"]["saved_extra_empty_root_restart"] == ACCEPTED)
    return verdict


def lane_source_regressions(run: LaneRun) -> None:
    a7.lane_source_regressions(run)
    verdict = _suites_on_the_unfixed_base(run)
    run.extra["attempt9_suites_on_the_unfixed_base"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the Attempt 9 suites do not show the defects on the unfixed base: "
                            f"{ {k: verdict.get(k) for k in ('exit', 'negative_cases_passing_on_the_base', 'unclassified', 'negative_tests_missing', 'saved_constructions', 'problem')} }")


# ------------------------------------------------------------- the career successor (MF37A08-01)


def _a09_oracle(run: LaneRun, label: str, successor: Path, a04: Path) -> dict[str, Any]:
    out = run.run_dir / f"ORACLE_A09_{label}.json"
    run.run(f"independent_source_unit_oracle_{label}", [run.python, "-B", ORACLE_TOOL, "--successor", successor,
                                                        "--a04", a04, "--database", DELIVERED_DB, "--out", out,
                                                        "--label", label],
            env=run.env(pythonpath=None), timeout=3600,
            note="The independent identity-derived oracle: sqlite3/json/re only, no project module on its path.")
    document = _json_file(out) or {}
    document["receipt"] = {"path": str(out), "sha256": sha256_file(out) if out.is_file() else None}
    return document


def _crossed(document: dict[str, Any]) -> dict[str, int]:
    return {r["relation"]: r["crossed_edges"] for r in document.get("relations") or []}


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
        return (counts.get("edges") == edges and int(counts.get("anchored_by_source_field") or 0) == edges
                and int(counts.get("anchored_by_parameter_only") or 0) == 0
                and counts.get("anchored_on") == "DERIVED_SOURCE_UNITS")

    def resolved(record: dict[str, Any], rows: int) -> bool:
        return (record.get("rows_resolved_to_their_source_unit") == rows and record.get("rows_proved") == rows
                and record.get("rows_naming_no_source_unit") == 0)

    checks = {
        "verifier_is_v5": bindings.get("verifier_version") == "BAS-C37A09-CAREER-SUCCESSOR-VERIFIER-v5",
        "a05_every_successor_row_resolves_to_its_witnessed_unit": resolved(witnessed.get("successor") or {},
                                                                            GENUINE_ROWS["A05"]),
        "a05_every_named_delivered_row_resolves": resolved(witnessed.get("delivered_predecessor") or {},
                                                           NAMED_PARENTS["delivered"]),
        "a05_every_named_attempt4_row_resolves": resolved(a04_witnessed, NAMED_PARENTS["attempt4"]),
        "a04_format_every_row_resolves": resolved(older_witnessed.get("successor") or {}, GENUINE_ROWS["A04"]),
        "a05_default_edges_anchored_on_derived_units": anchored(default, GENUINE_EDGES["A5<-default"]),
        "a05_a04_edges_anchored_on_derived_units": anchored(cross, GENUINE_EDGES["A5<-A4"]),
        "a05_versions_agree_on_every_row": a05.get("rows_whose_versions_agree_on_predecessor_rows") == GENUINE_ROWS["A05"],
        "a04_default_edges_anchored_on_derived_units": anchored(older, GENUINE_EDGES["A4<-default"]),
        "captures_read_at_attach": a05.get("source_captures_read_at_attach") == 7950,
    }
    run.extra["source_witness_checks"] = {"checks": checks, "successor": witnessed, "a04_relation": a04_witnessed,
                                          "a04_format": older_witnessed, "default_anchors": default,
                                          "a04_anchors": cross, "a04_format_anchors": older}
    for name, held in checks.items():
        if not held:
            run.problems.append(f"source unit binding: {name} does not hold")
    # The Attempt 8 source-field oracle, kept (genuine, the Attempt 7 envelope, the Attempt 6 same-page swap).
    genuine8 = a8._oracle(run, "genuine", A5_SUCCESSOR, A4_SUCCESSOR)
    envelope_ok = sha256_file(a8.MANAGER_A7_ENVELOPE) == a8.MANAGER_A7_ENVELOPE_SHA256
    same_page_ok = a8.SAVED_SAME_PAGE_FIXTURE.is_file() and sha256_file(a8.SAVED_SAME_PAGE_FIXTURE) == a8.SAVED_SAME_PAGE_SHA256
    envelope8 = a8._oracle(run, "manager_a7_envelope", a8.MANAGER_A7_ENVELOPE, A4_SUCCESSOR) if envelope_ok else {}
    same_page8 = a8._oracle(run, "manager_a6_same_page", a8.SAVED_SAME_PAGE_FIXTURE, A4_SUCCESSOR) if same_page_ok else {}
    kept = {"genuine_crossed": genuine8.get("crossed_edges"), "genuine_unresolved": genuine8.get("unresolved"),
            "manager_a7_envelope": _crossed(envelope8), "manager_a6_same_page": _crossed(same_page8),
            "receipts": {k: v.get("receipt") for k, v in (("genuine", genuine8), ("envelope", envelope8),
                                                          ("same_page", same_page8))}}
    kept["holds"] = (genuine8.get("crossed_edges") == 0 and all(not v for v in (genuine8.get("unresolved") or {}).values())
                     and kept["manager_a7_envelope"] == {"A5<-default": 2, "A5<-A4": 2, "A4<-default": 0}
                     and kept["manager_a6_same_page"] == {"A5<-default": 2, "A5<-A4": 2, "A4<-default": 0})
    run.extra["attempt8_source_field_oracle"] = kept
    if not kept["holds"]:
        run.problems.append(f"the Attempt 8 source-field oracle no longer holds: {kept}")
    # The Attempt 9 identity-derived oracle (MF37A08-01).
    genuine = _a09_oracle(run, "genuine", A5_SUCCESSOR, A4_SUCCESSOR)
    null_ok = sha256_file(MANAGER_A8_NULL_SPAN) == MANAGER_A8_NULL_SPAN_SHA256
    null_span = _a09_oracle(run, "manager_a8_null_span", MANAGER_A8_NULL_SPAN, A4_SUCCESSOR) if null_ok else {}
    envelope = _a09_oracle(run, "manager_a7_envelope", a8.MANAGER_A7_ENVELOPE, A4_SUCCESSOR) if envelope_ok else {}
    same_page = _a09_oracle(run, "manager_a6_same_page", a8.SAVED_SAME_PAGE_FIXTURE, A4_SUCCESSOR) if same_page_ok else {}
    valid = ("UNIT_WITNESSED_EXACT", "UNIT_BY_IDENTITY_NO_WITNESS")
    verdict = {
        "genuine": {k: genuine.get(k) for k in ("oracle_version", "rows", "captures_read", "captures_unreadable_or_changed",
                                                 "row_classes", "crossed_edges", "unresolved_edges", "limits", "receipt")}
        | {"relations": [{k: r.get(k) for k in ("relation", "edges", "counts", "crossed_edges", "unresolved_edges")}
                         for r in genuine.get("relations") or []]},
        "manager_a8_null_span": {"fixture": str(MANAGER_A8_NULL_SPAN), "sha256_as_issued": null_ok,
                                 "a05_row_classes": (null_span.get("row_classes") or {}).get("A05"),
                                 "invalid_rows": (null_span.get("invalid_row_examples") or {}).get("A05"),
                                 "crossed_by_relation": _crossed(null_span),
                                 "examples": {r["relation"]: r.get("examples") for r in null_span.get("relations") or []},
                                 "receipt": null_span.get("receipt")},
        "manager_a7_envelope": {"crossed_by_relation": _crossed(envelope), "receipt": envelope.get("receipt")},
        "manager_a6_same_page": {"crossed_by_relation": _crossed(same_page), "receipt": same_page.get("receipt")},
    }
    verdict["holds"] = (
        genuine.get("rows") == GENUINE_ROWS and genuine.get("crossed_edges") == 0 and genuine.get("unresolved_edges") == 0
        and genuine.get("captures_unreadable_or_changed") == 0
        and all(set(counts) <= set(valid) for counts in (genuine.get("row_classes") or {}).values())
        and {r["relation"]: r["edges"] for r in genuine.get("relations") or []} == GENUINE_EDGES
        and null_ok and _crossed(null_span) == {"A5<-default": 2, "A5<-A4": 2, "A4<-default": 0}
        and len((null_span.get("invalid_row_examples") or {}).get("A05") or []) == 2
        and _crossed(envelope) == {"A5<-default": 2, "A5<-A4": 2, "A4<-default": 0}
        and _crossed(same_page) == {"A5<-default": 2, "A5<-A4": 2, "A4<-default": 0})
    run.extra["independent_source_unit_oracle"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the independent identity-derived oracle does not hold: genuine crossed "
                            f"{genuine.get('crossed_edges')} unresolved {genuine.get('unresolved_edges')}, NULL-span "
                            f"{_crossed(null_span)}, envelope {_crossed(envelope)}, same page {_crossed(same_page)}")


# ------------------------------------------------------------- the installed consumer (MF37A08-01)


def _text_of(row: dict[str, Any]) -> str:
    return a8._text_of(row)


def _span(row: dict[str, Any], field: str) -> list[int]:
    return a8._span(row, field)


def _fred(c: sqlite3.Connection, table: str = "career_episode_a05") -> tuple[dict[str, Any], dict[str, Any]]:
    return a7._fred_rows(c, table)


def _unwitness(c: sqlite3.Connection, table: str, row: dict[str, Any], fields: tuple[str, ...], absent: Any,
               text: Any = "keep") -> dict[str, Any]:
    """Remove a row's witnesses for ``fields`` (``absent`` spelling) and set their text ("keep" leaves it, "own" writes
    the unit's own genuine text, anything else replaces it)."""

    changes: dict[str, Any] = {}
    for field in fields:
        changes[f"{field}_char_span"] = absent
        if field == "team":
            changes["team_byte_span"] = absent
        if text == "own":
            changes[f"{field}_raw"] = (_text_of(row)[_span(row, field)[0]:_span(row, field)[1]]
                                       if row.get(f"{field}_char_span") else None)
        elif text != "keep":
            changes[f"{field}_raw"] = text
    c.execute(f"UPDATE {table} SET " + ", ".join(f"{k}=?" for k in changes) + " WHERE episode_id=?",
              (*changes.values(), row["episode_id"]))
    return {"episode": row["episode_id"], "fields": list(fields), "absent_as": absent,
            "text": text if text in ("keep", "own") else (None if text is None else f"{len(str(text))} chars")}


def _managers_construction(absent: Any) -> Callable[[sqlite3.Connection], dict[str, Any]]:
    """The Attempt 8 manager's recipe: Fred's jobs 1 and 6 swapped in both relations, their team, byte and years spans
    set to ``absent``, their team and years text enlarged from job 1's field to job 6's."""

    def build(c: sqlite3.Connection) -> dict[str, Any]:
        one, six = _fred(c)
        swap = a7._swap_edges(c, one, six)
        page = _text_of(one)
        texts = {field: page[min(_span(one, field)[0], _span(six, field)[0]):max(_span(one, field)[1],
                                                                                   _span(six, field)[1])]
                 for field in ("team", "years")}
        changed = []
        for row in (one, six):
            c.execute("UPDATE career_episode_a05 SET team_raw=?, years_raw=? WHERE episode_id=?",
                      (texts["team"], texts["years"], row["episode_id"]))
            changed.append(_unwitness(c, "career_episode_a05", row, ("team", "years"), absent))
        return {"swap": swap, "rows": changed, "absent_spelling": absent}
    return build


def _missing_with_swap(fields: tuple[str, ...], text: Any) -> Callable[[sqlite3.Connection], dict[str, Any]]:
    def build(c: sqlite3.Connection) -> dict[str, Any]:
        one, six = _fred(c)
        swap = a7._swap_edges(c, one, six)
        return {"swap": swap, "rows": [_unwitness(c, "career_episode_a05", row, fields, None, text) for row in (one, six)]}
    return build


def _same_role_other_period(c: sqlite3.Connection) -> dict[str, Any]:
    """Two numbered jobs of one person with the same employer text: their edges swapped in both relations and both
    rows' witnesses removed (their own text kept) -- the text fallback of v4 agreed on the shared employer text."""

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
        if not (a8._one_to_one(c, a) and a8._one_to_one(c, b)):
            continue
        swap = a7._swap_edges(c, a, b)
        rows = [_unwitness(c, "career_episode_a05", row, ("team", "years"), None, "keep") for row in (a, b)]
        return {"victim": a["episode_id"], "other_period": b["episode_id"], "person": a["person_display"],
                "team_raw": a["team_raw"], "swap": swap, "rows": rows}
    raise RuntimeError("no two numbered jobs of one person share an employer text for the challenge")


def _a04_relation_only(c: sqlite3.Connection) -> dict[str, Any]:
    one, six = _fred(c)
    swap = a7._swap_edges(c, one, six, default=False)
    return {"swap": swap, "rows": [_unwitness(c, "career_episode_a05", row, ("team", "years"), None, None)
                                   for row in (one, six)]}


def _a04_format(c: sqlite3.Connection) -> dict[str, Any]:
    one, six = _fred(c, "career_episode_a04")
    swap = a7._swap_edges(c, one, six, table="career_episode_a04")
    return {"swap": swap, "rows": [_unwitness(c, "career_episode_a04", row, ("team", "years"), None, None)
                                   for row in (one, six)]}


def _declared_a04_file_relabelled(c: sqlite3.Connection) -> dict[str, Any]:
    """Every Attempt 5 edge genuine but job 1's Attempt 4 edge, which now names the declared Attempt 4 file's job-6 row;
    that row carries job 1's row index, witnesses and text (its episode identity still names job 6), the Attempt 5
    mapping digests recomputed as a careful forger would."""

    a4 = a6._open_fixture(LINEAGE_A04)
    one4, six4 = _fred(a4, "career_episode_a04")
    columns = [r[1] for r in a4.execute("PRAGMA table_info(career_episode_a04)")]

    def digest(identity: str) -> str:
        row = a4.execute(f"SELECT {','.join(chr(34) + x + chr(34) for x in columns)} FROM career_episode_a04 "
                         "WHERE episode_id=?", (identity,)).fetchone()
        return a7._canonical_digest(list(row))

    fields = ("row_index", "team_char_span", "team_byte_span", "team_raw", "years_char_span", "years_raw",
              "years_as_written", "predecessor_episode_ids")
    a4.execute("UPDATE career_episode_a04 SET " + ", ".join(f"{f}=?" for f in fields) + " WHERE episode_id=?",
               (*(one4.get(f) for f in fields), six4["episode_id"]))
    new_digest = digest(six4["episode_id"])
    a6._reseal(a4, a6.A04_TABLES)
    a4.commit()
    a4.close()
    one, six = _fred(c)
    swap = a7._swap_edges(c, one, six, default=False)
    c.execute("UPDATE career_a05_from_a04 SET a04_row_sha256=? WHERE a04_episode_id=?", (new_digest, six4["episode_id"]))
    c.execute("UPDATE successor_identity SET value=? WHERE key='a04_successor_path'", (str(LINEAGE_A04),))
    c.execute("UPDATE successor_identity SET value=? WHERE key='a04_successor_sha256'", (sha256_file(LINEAGE_A04),))
    return {"a04_file": str(LINEAGE_A04), "relabelled": six4["episode_id"], "carries_row_of": one4["episode_id"],
            "swap": swap, "mapping_digest_recomputed": True}


def _row_naming_no_unit(c: sqlite3.Connection) -> dict[str, Any]:
    """A genuine one-to-one numbered row renamed to an identity naming nothing in its revision (row 777), its witnesses
    and text removed, every reference to it rewritten: its edges can be anchored to no unit."""

    one, _six = _fred(c)
    if not a8._one_to_one(c, one):
        raise RuntimeError("Fred Mariani's first job is not one-to-one")
    old = one["episode_id"]
    new = old.rsplit(":", 2)[0] + ":777:" + old.rsplit(":", 1)[1]
    c.execute("UPDATE career_episode_a05 SET episode_id=?, row_index=777, team_char_span=NULL, team_byte_span=NULL, "
              "years_char_span=NULL, team_raw=NULL, years_raw=NULL WHERE episode_id=?", (new, old))
    for table, column in (("career_a05_disposition", "successor_episode_ids"), ("career_a05_from_a04", "a05_episode_ids")):
        for key, value in c.execute(f"SELECT rowid, {column} FROM {table}").fetchall():
            ids = json.loads(value or "[]")
            if old in ids:
                c.execute(f"UPDATE {table} SET {column}=? WHERE rowid=?",
                          (json.dumps([new if x == old else x for x in ids]), key))
    return {"renamed": old, "to": new}


def _line_years_outside(c: sqlite3.Connection) -> dict[str, Any]:
    for a in c.execute("SELECT * FROM career_episode_a05 WHERE row_index BETWEEN 1001 AND 1999 AND interval_index = 0 "
                       "AND years_char_span IS NOT NULL ORDER BY pageid").fetchall():
        a = dict(a)
        b = c.execute("SELECT years_raw FROM career_episode_a05 WHERE pageid=? AND row_index BETWEEN 1001 AND 1999 "
                      "AND row_index != ? AND years_raw IS NOT NULL", (a["pageid"], a["row_index"])).fetchone()
        line = _text_of(a)[_span(a, "team")[0]:_span(a, "team")[1]]
        if b is None or not b[0] or b[0] in line:
            continue
        c.execute("UPDATE career_episode_a05 SET years_char_span=NULL, years_raw=? WHERE episode_id=?",
                  (b[0], a["episode_id"]))
        return {"victim": a["episode_id"], "person": a["person_display"], "years_text": b[0], "line": line[:120]}
    raise RuntimeError("no list line with another line's dates for the challenge")


#: (name, format, builder, person or "" for the builder's own, expected refusal code, a cause the message must name)
def a9_cases() -> list[tuple[str, str, Callable[[sqlite3.Connection], dict[str, Any]], str, str, str]]:
    field = REFUSED_SOURCE_FIELD
    return [
        ("a05_manager_construction_sql_null", "A05", _managers_construction(None), FRED, field,
         "TEAM_TEXT_WITHOUT_A_WITNESS_IS_NOT_ITS_SOURCE_UNIT"),
        ("a05_manager_construction_json_null", "A05", _managers_construction("null"), FRED, field,
         "TEAM_TEXT_WITHOUT_A_WITNESS_IS_NOT_ITS_SOURCE_UNIT"),
        ("a05_manager_construction_null_pair", "A05", _managers_construction("[null, null]"), FRED, field,
         "TEAM_TEXT_WITHOUT_A_WITNESS_IS_NOT_ITS_SOURCE_UNIT"),
        ("a05_manager_construction_empty_string", "A05", _managers_construction(""), FRED, field,
         "TEAM_TEXT_WITHOUT_A_WITNESS_IS_NOT_ITS_SOURCE_UNIT"),
        ("a05_both_missing_own_text_swapped", "A05", _missing_with_swap(("team", "years"), "own"), FRED,
         REFUSED_EPISODE, "EPISODE"),
        ("a05_both_missing_blank_text_swapped", "A05", _missing_with_swap(("team", "years"), None), FRED,
         REFUSED_EPISODE, "EPISODE"),
        ("a05_team_missing_own_text_swapped", "A05", _missing_with_swap(("team",), "own"), FRED, REFUSED_EPISODE,
         "EPISODE"),
        ("a05_years_missing_own_text_swapped", "A05", _missing_with_swap(("years",), "own"), FRED, REFUSED_EPISODE,
         "EPISODE"),
        ("a05_same_role_other_period_without_witnesses", "A05", _same_role_other_period, "", REFUSED_EPISODE,
         "EPISODE"),
        ("a05_a04_relation_only_without_witnesses", "A05", _a04_relation_only, FRED, REFUSED_A04_ANCHOR, "EPISODE"),
        ("a04_format_without_witnesses_swapped", "A04", _a04_format, FRED, REFUSED_EPISODE, "EPISODE"),
        ("a05_declared_a04_file_row_relabelled", "A05", _declared_a04_file_relabelled, FRED, REFUSED_A04_IDENTITY,
         "identity"),
        ("a05_row_naming_no_source_unit", "A05", _row_naming_no_unit, FRED, REFUSED_UNANCHORED,
         "no source unit was derived"),
        ("a05_list_line_years_text_outside_its_line", "A05", _line_years_outside, "", field,
         "YEARS_TEXT_WITHOUT_A_WITNESS_IS_NOT_IN_ITS_LINE"),
    ]


def _manager_a8_null_span(run: LaneRun, installed: dict[str, Any]) -> dict[str, Any]:
    """The manager's saved NULL-span fixture, byte for byte, through all three entrypoints (LINEAGE_ENTRYPOINTS)."""

    with MANAGER_A8_NULL_SPAN.open("rb") as reader, LINEAGE_A05.open("r+b") as writer:
        writer.truncate(0)
        shutil.copyfileobj(reader, writer)
    digest = sha256_file(LINEAGE_A05)
    args = ["--career", "--career-successor", LINEAGE_A05, "--career-successor-sha256", digest, "--person", FRED,
            "--compact"]
    records = {"installed_console_script": base._cli(run, installed, "a9_manager_null_span_script", args, expect_exit=1),
               "installed_module": a7._module_entrypoint(run, installed, "a9_manager_null_span_module", args,
                                                         expect_exit=1),
               "source_module": a8._source_module_entrypoint(run, installed, "a9_manager_null_span_source", args,
                                                             expect_exit=1)}
    texts = {k: Path(r["log_path"]).read_text(encoding="utf-8", errors="replace") for k, r in records.items()}
    refusals = {k: _refusal(t) for k, t in texts.items()}
    exits = {k: r.get("exit_code") for k, r in records.items()}
    a6._restore(LINEAGE_A05, A5_SUCCESSOR)
    verdict = {"fixture_sha256": digest, "as_issued": digest == MANAGER_A8_NULL_SPAN_SHA256, "exits": exits,
               "refusals": refusals, "expected": REFUSED_SOURCE_FIELD,
               "names_the_unwitnessed_text": {k: "WITHOUT_A_WITNESS" in t for k, t in texts.items()},
               "before_repair": "every entrypoint exited 0 serving seven rows (evidence/before/BEFORE_REPRODUCTION.json)"}
    verdict["holds"] = verdict["as_issued"] and all(v == 1 for v in exits.values()) and all(
        v == REFUSED_SOURCE_FIELD for v in refusals.values()) and all(verdict["names_the_unwitnessed_text"].values())
    return verdict


def _a9_forgeries(run: LaneRun, installed: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {"fixtures": {"a05": str(LINEAGE_A05), "a04": str(LINEAGE_A04)}, "cases": {},
                               "rule": ("each case restores its fixture(s) from the genuine files, removes witnesses "
                                        "(in the spelling named) with or without forged edges and with enlarged, own or "
                                        "blank text, reseals every ledger as a careful forger would, pins the digest and "
                                        "serves through the console script and the module entrypoint; each must be "
                                        "refused for its own cause")}
    for name, fmt, builder, person, expected, cause in a9_cases():
        a6._restore(LINEAGE_A05, A5_SUCCESSOR)
        a6._restore(LINEAGE_A04, A4_SUCCESSOR)
        fixture, tables = (LINEAGE_A05, a6.A05_TABLES) if fmt == "A05" else (LINEAGE_A04, a6.A04_TABLES)
        target = a6._open_fixture(fixture)
        try:
            details = builder(target)
            a6._reseal(target, tables)
            target.commit()
        finally:
            target.close()
        digest = sha256_file(fixture)
        who = person or details.get("person") or FRED
        args = ["--career", "--career-successor", fixture, "--career-successor-sha256", digest, "--person", who,
                "--limit", "100", "--compact"]
        script = base._cli(run, installed, f"a9_{name}", args, expect_exit=1)
        module = a7._module_entrypoint(run, installed, f"a9_{name}_module", args, expect_exit=1)
        texts = {kind: Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
                 for kind, record in (("script", script), ("module", module))}
        refusals = {kind: _refusal(text) for kind, text in texts.items()}
        results["cases"][name] = {"format": fmt, "person": who, "fixture_sha256": digest, "details": details,
                                  "expected": expected, "cause": cause,
                                  "script_exit": script.get("exit_code"), "module_exit": module.get("exit_code"),
                                  "refusals": refusals, "cause_named": {k: cause in t for k, t in texts.items()},
                                  "holds": script.get("exit_code") == 1 and module.get("exit_code") == 1
                                  and refusals["script"] == expected and refusals["module"] == expected
                                  and all(cause in t for t in texts.values())}
        if not results["cases"][name]["holds"]:
            run.problems.append(f"A9 forgery {name} was not refused for its cause at both entrypoints: {refusals}")
    for fixture, source in ((LINEAGE_A05, A5_SUCCESSOR), (LINEAGE_A04, A4_SUCCESSOR)):
        a6._restore(fixture, source)
    results["genuine_unchanged"] = (sha256_file(A5_SUCCESSOR) == A5_SUCCESSOR_SHA256
                                    and sha256_file(A4_SUCCESSOR) == A4_SUCCESSOR_SHA256)
    results["holds"] = results["genuine_unchanged"] and all(row["holds"] for row in results["cases"].values())
    return results


def lane_installed_consumer_c01(run: LaneRun) -> None:
    a8.lane_installed_consumer_c01(run)
    raw = run.extra.get("installed")
    if not raw:
        return
    installed = {key: Path(value) for key, value in raw.items()}
    verdict = _manager_a8_null_span(run, installed)
    run.extra["manager_a8_null_span_entrypoints"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's saved NULL-span fixture is not refused for its source-field cause at every "
                            f"entrypoint: {verdict}")
    run.extra["a9_forgeries"] = _a9_forgeries(run, installed)


# ------------------------------------------------------------- the local integration candidate (R37A09-03)


def _append_records() -> list[tuple[Path, dict[str, Any]]]:
    return [(path, _json_file(path)) for path in sorted(CANDIDATE_RECORDS.glob("CANDIDATE_APPEND_*.json"))]


def _append_chain(head: str) -> dict[str, Any]:
    """Every Attempt 9 append continues the one before it, the first from the granted head ``c52e7b52`` (a rehearsal
    scratch candidate starts there too), the last ending at ``head``."""

    records = _append_records()
    chain = [{"record": str(path), "previous": record.get("previous_candidate_head"),
              "commit": record.get("candidate_commit"), "repair_head": record.get("repair_head"),
              "packs_unchanged": (record.get("git_housekeeping") or {}).get("packs_unchanged")}
             for path, record in records]
    expected = [candidate.ISSUED_CANDIDATE_HEAD] + [row["commit"] for row in chain[:-1]]
    holds = (bool(chain) and [row["previous"] for row in chain] == expected and chain[-1]["commit"] == head
             and all(row["packs_unchanged"] for row in chain))
    return {"appends": chain, "starts_from": candidate.ISSUED_CANDIDATE_HEAD, "holds": holds}


def _manager_a8_committed_tree(run: LaneRun, head: str) -> dict[str, Any]:
    copy, replay = a7._replay(run, MANAGER_A8, "committed_tree_review.py", "mgr_a8_committed_tree")
    record = run.run("manager_a8_committed_tree_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None),
                     note="The manager's saved Attempt 8 committed-byte provenance probe, byte-identical; it reads the "
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
    a6.lane_local_integration_candidate(run)
    head = (run.extra.get("candidate") or {}).get("candidate_head")
    if not head:
        return
    description = candidate.describe()
    chain = _append_chain(head)
    run.extra["candidate_attempt9"] = {
        "appends_continue_c52e7b52_with_no_pack_written": chain["holds"],
        "c52e7b52_is_ancestor": description.get("attempt9_start_is_ancestor") is True,
        "0c22af20_is_ancestor": description.get("attempt8_start_is_ancestor") is True,
        "bb5253b2_is_ancestor": description.get("attempt7_start_is_ancestor") is True,
        "preserved_first_candidate_is_ancestor": description.get("issued_head_is_ancestor") is True}
    run.extra["candidate_append_chain_attempt9"] = chain
    if not all(run.extra["candidate_attempt9"].values()):
        run.problems.append(f"the candidate does not continue the granted head: {run.extra['candidate_attempt9']}")
    if not run.rehearsal:
        # The manager's Attempt 8 committed-byte probe, and the Attempt 7 and 6 ones the earlier runners replayed: each
        # is read-only, byte-identical, and reads the named candidate branch through the shared Git store.
        for key, probe in (("manager_a8_committed_tree", _manager_a8_committed_tree),
                           ("manager_a7_committed_tree", a8._manager_a7_committed_tree),
                           ("manager_a6_committed_tree", a7._manager_a6_committed_tree)):
            verdict = probe(run, head)
            run.extra[key] = verdict
            if not verdict["holds"]:
                run.problems.append(f"the {key.replace('_', ' ')} review finds mismatches: {verdict}")
    control = a7._control07_requalification(run)
    run.extra["control07_requalification"] = control
    if not control["holds"]:
        run.problems.append(f"the retained CONTROL-07 proposal does not re-bind offline: {control.get('checks')}")


# ------------------------------------------------------------- mounted, unmounted, platform and packet lanes


def _attempt8_final(lane: str) -> dict[str, Any]:
    rows = [json.loads(line) for line in (ATTEMPT8_ROOT / "lanes" / "RUNS.jsonl").read_text(encoding="utf-8")
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
    previous = _attempt8_final("FULL_FINAL_MOUNTED")
    comparison: dict[str, Any] = {"attempt8_receipt": previous.get("receipt"),
                                  "attempt8_receipt_sha256": previous.get("receipt_sha256"),
                                  "attempt8_run": previous.get("run"), "attempt8_result": previous.get("result")}
    if not previous:
        run.problems.append("no Attempt 8 FULL_FINAL_MOUNTED receipt at the issued base to compare with")
    else:
        a8_log = Path(next(c["log_path"] for c in previous["data"]["commands"]
                           if c["lane"].endswith("full_suite_mounted")))
        before = base._log_identities(a8_log)
        persisting = sorted(set(final["failed_or_errored"]) & set(before["failed_or_errored"]))
        new = sorted(set(final["failed_or_errored"]) - set(before["failed_or_errored"]))
        final_causes = base._failure_causes(log, persisting)
        before_causes = base._failure_causes(a8_log, persisting)
        comparison.update({
            "attempt8_log": str(a8_log), "attempt8_log_sha256": sha256_file(a8_log),
            "attempt8_tests_run": before["tests_run"], "final_tests_run": final["tests_run"],
            "attempt8_failed_or_errored": before["failed_or_errored"], "persisting": persisting,
            "new_in_attempt9": new,
            "no_longer_failing": sorted(set(before["failed_or_errored"]) - set(final["failed_or_errored"])),
            "new_failure_causes": base._failure_causes(log, new),
            "persisting_same_cause": sorted(i for i in persisting if final_causes[i] == before_causes[i]),
            "persisting_changed_cause": {i: {"attempt8": before_causes[i], "attempt9": final_causes[i]}
                                         for i in persisting if final_causes[i] != before_causes[i]},
        })
        if new:
            run.problems.append(f"new failing identities relative to Attempt 8: {new}")
    run.extra["attempt8_comparison"] = comparison


def lane_strict_mounted(run: LaneRun) -> None:
    base.lane_strict_mounted(run)
    final = [row["identity"] for row in run.extra.get("strict_findings") or []]
    previous = _attempt8_final("STRICT_MOUNTED")
    comparison: dict[str, Any] = {"attempt8_receipt": previous.get("receipt"), "attempt8_run": previous.get("run"),
                                  "attempt8_result": previous.get("result")}
    if not previous:
        run.problems.append("no Attempt 8 STRICT_MOUNTED receipt at the issued base to compare with")
    else:
        before = [row["identity"] for row in (previous["data"].get("details") or {}).get("strict_findings") or []]
        comparison.update({"attempt8_findings": before, "final_findings": final,
                           "persisting": sorted(set(final) & set(before)),
                           "new_in_attempt9": sorted(set(final) - set(before)),
                           "no_longer_reported": sorted(set(before) - set(final))})
        if comparison["new_in_attempt9"]:
            run.problems.append(f"new strict findings relative to Attempt 8: {comparison['new_in_attempt9']}")
    run.extra["attempt8_comparison"] = comparison


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
    store_before = candidate.git_store_state()
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
    store_after = candidate.git_store_state()
    git_store = {"store_before": {k: v for k, v in store_before.items() if k != "refs"},
                 "store_after": {k: v for k, v in store_after.items() if k != "refs"},
                 "packs_unchanged": store_before["packs_sha256"] == store_after["packs_sha256"],
                 "loose_objects_not_decreased": store_after["loose_objects"] >= store_before["loose_objects"],
                 "refs_unchanged": store_before["refs"] == store_after["refs"],
                 "meaning": ("The shared Git store measured around the lane: no pack written or removed, no loose object "
                             "gone and no ref moved means no Git housekeeping and no ref change happened in it.")}
    if not (git_store["packs_unchanged"] and git_store["loose_objects_not_decreased"] and git_store["refs_unchanged"]):
        result = FAIL
        reason = f"{reason}; the shared Git store's packs, loose objects or refs changed during the lane"
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
            "shared_git_store": git_store,
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
