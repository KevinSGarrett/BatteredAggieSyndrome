r"""Cycle #37 — Attempt #10 — the lane runner (R37A10-05).

    attempt10_lanes.py --lane <ID> --contract <cycle_contract.json> --out-root <attempt root> [--rehearsal]

The preserved Attempt 9 runner (``attempt09_lanes``, over the Attempt 8, 7, 6, 5, 4 and 3 runners) rebound to the Attempt
10 contract, roots, ledger, suites and tools. Everything the earlier runners bind per run is still bound -- the issued
contract by its sealed digest, the committed subject (branch, head, tree, source digest, descent from the issued base, a
clean tree before and after), the interpreter, module origins, the delivered database by digest, the data root and
``C:\All-22`` measured before and after, the main checkout and both integration worktrees, credential removal, the
guard and storage qualification of the costly lanes, and the shared Git store around every lane. What Attempt 10 adds:

* **START_CONTEXT** binds the Attempt 10 intake, the before-repair reproduction of MF37A09-01 and the Git housekeeping
  preflight receipts.
* **STORAGE_ADMISSION** keeps the accepted Attempt 9 storage behavior by running it fresh: the storage suites (the root
  contract suite among them), the manager's Attempt 8 continuation challenge and the manager's Attempt 9 challenge, each
  replayed with only its fixture root adapted.
* **SOURCE_REGRESSIONS** runs the Attempt 10 interval suite against the exact bytes of the issued base (a ``git
  archive`` of ``1478797b``) and classifies every outcome by what the unfixed verifier did: every new negative case must
  fail there; retained negatives (refused under the earlier rules too) and positives are recorded, never required.
* **CAREER_SUCCESSOR (MF37A09-01)** checks the v6 verifier's interval-grain binding over both genuine successors and runs
  the independent interval oracle (``a10_interval_oracle.py``, no project import) over the genuine files and the saved
  manager interval fixture; the Attempt 9 and Attempt 8 oracles run too.
* **INSTALLED_CONSUMER_C01** replays the manager's saved interval fixture byte for byte through the installed console
  script, the installed module and the source module, and serves this attempt's interval matrix -- the reciprocal
  crossing with NULL, empty, whitespace, parent-copied, enlarged, substring and genuine period text, a one-sided
  crossing, each relation alone, the Attempt 4 format, a list line, missing witnesses, a false restructure claim, a
  content relabel in both formats and stated interval text or dates that are not the identity's -- each restored from
  the genuine file, resealed and refused for its own cause through the console script and the module, with genuine
  blank period text and unstated dates served as the positive controls.
* **LOCAL_INTEGRATION_CANDIDATE** verifies the Attempt 10 append continues ``514d74dc`` with no pack written, replays the
  manager's Attempt 9, 8, 7 and 6 committed-tree reviews, and re-binds the retained CONTROL-07 proposal offline.
* **FULL_FINAL_MOUNTED / STRICT_MOUNTED** compare identities with the Attempt 9 final receipts at the issued base.

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

import attempt09_lanes as a9  # noqa: E402  (the preserved Attempt 9 runner)
import attempt10_candidate as candidate  # noqa: E402
import attempt09_git  # noqa: E402  (unchanged; every Git command carries the housekeeping settings)

a8, a7, a6, a5, a4, base, a6c = a9.a8, a9.a7, a9.a6, a9.a5, a9.a4, a9.base, a9.a6c
storage, snapshot = a9.storage, a9.snapshot
BLOCKED, DATA_ROOT, DELIVERED_DB, FAIL, PASS = a9.BLOCKED, a9.DATA_ROOT, a9.DELIVERED_DB, a9.FAIL, a9.PASS
Tee, credential_scrub, git_out, sha256_bytes, sha256_file, utc_now = (a9.Tee, a9.credential_scrub, a9.git_out,
                                                                      a9.sha256_bytes, a9.sha256_file, a9.utc_now)

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 10
CYCLE_ID = "CYCLE-37"
ATTEMPT_ID = "ATTEMPT-10-20260927"
RUNNER_VERSION = "BAS-C37-ATTEMPT10-LANES-v1"
BASE_SHA = "1478797b68fa4c883dae362a7a3388bf8dc6c560"
BRANCH = "codex/BAT-706-cycle37-rework"
LABEL = "Cycle #37 \u2014 Attempt #10 \u2014"
LANES = a9.LANES
GATED = a9.GATED
MIB = 1024 * 1024
#: Each lane's reservation, from the measured Attempt 9 costs (INSTALLED_CONSUMER_C01 349 MiB, the candidate lane 117
#: MiB, PLATFORM_CARRY 80 MiB, SOURCE_REGRESSIONS and CAREER_SUCCESSOR 22 MiB each) with margin, plus this attempt's
#: additions (the base export and its suite run, the interval oracle's receipts, twenty more interval cases).
LANE_ESTIMATES = {
    "START_CONTEXT": 16 * MIB, "WRITE_PROTECTION": 32 * MIB, "STORAGE_ADMISSION": 64 * MIB,
    "SOURCE_ADMISSION": 32 * MIB, "SOURCE_HARNESS": 32 * MIB, "SOURCE_REGRESSIONS": 192 * MIB,
    "CAREER_SUCCESSOR": 160 * MIB, "INSTALLED_CONSUMER_C01": 640 * MIB, "LOCAL_INTEGRATION_CANDIDATE": 288 * MIB,
    "TRUE_UNMOUNTED": 32 * MIB, "FULL_FINAL_MOUNTED": 64 * MIB, "STRICT_MOUNTED": 32 * MIB,
    "PLATFORM_CARRY": 192 * MIB, "FINAL_PACKET": 32 * MIB,
}

EVIDENCE_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt10"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a10")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37a10")
ATTEMPT9_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt09"
VALIDATION_A09 = Path(r"C:\BatteredAggieSyndrome.validation\c37a09")
PACKAGING_A09 = Path(r"C:\BatteredAggieSyndrome.packaging\c37a09")
MANAGER_A9 = DATA_ROOT / "ops" / "manager_reviews" / "cycle37" / "attempt09" / "review-20260927T224734Z"
MANAGER_A9_FIXTURE_LITERAL = r"C:\BatteredAggieSyndrome.validation\mr37a09-224734"
MANAGER_A9_INTERVAL = Path(MANAGER_A9_FIXTURE_LITERAL) / "interval-adversarial.sqlite"
MANAGER_A9_INTERVAL_SHA256 = "d745f70acb9a6b45fb27c18effa93c8cf929620febf6b25a1dbf286292211357"
A5_SUCCESSOR, A5_SUCCESSOR_SHA256 = a9.A5_SUCCESSOR, a9.A5_SUCCESSOR_SHA256
A4_SUCCESSOR, A4_SUCCESSOR_SHA256 = a9.A4_SUCCESSOR, a9.A4_SUCCESSOR_SHA256
OPERATIONAL_LEDGER = EVIDENCE_ROOT / "STORAGE_RESERVATIONS.jsonl"
FINAL_SNAPSHOT = EVIDENCE_ROOT / "STORAGE_EVIDENCE_SNAPSHOT.json"
FINAL_OUTPUT_LEDGER = EVIDENCE_ROOT / "evidence" / "storage" / "STORAGE_RESERVATIONS_FINAL_OUTPUT.jsonl"
CANDIDATE_RECORDS = EVIDENCE_ROOT / "evidence" / "integration"
BEFORE_REPRODUCTION = EVIDENCE_ROOT / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
INTAKE = EVIDENCE_ROOT / "evidence" / "intake" / "INTAKE.json"
GIT_PREFLIGHTS = (EVIDENCE_ROOT / "evidence" / "intake" / "GIT_HOUSEKEEPING_PREFLIGHT.json",
                  EVIDENCE_ROOT / "evidence" / "intake" / "GIT_HELPER_CONSTRUCTION.json")
FIXTURES = VALIDATION_ROOT / "fixtures"
#: The owned copy of the manager's saved interval fixture (made by the before-repair reproduction; never written) and
#: the owned full copies of the genuine successors, restored before every forgery.
MANAGER_ADVERSARIAL_FIXTURE = FIXTURES / "mr"
SAVED_INTERVAL_COPY = MANAGER_ADVERSARIAL_FIXTURE / "interval-adversarial.sqlite"
LINEAGE_A05 = FIXTURES / "lineage" / "successor_a05.sqlite"
LINEAGE_A04 = FIXTURES / "lineage" / "successor_a04.sqlite"
AFTER_COMMENTS = (("BAT-706", "C37-A10-AFTER-HANDOFF-BAT-706"), ("BAT-708", "C37-A10-AFTER-HANDOFF-BAT-708"))
PLATFORM_TOOL = "tools/cycle37/attempt10_platform.py"
OUTPUTS_TOOL = "tools/cycle37/attempt10_outputs.py"
CONTROL_TOOL = Path(__file__).resolve().parent / "attempt10_control07.py"
INTERVAL_ORACLE_TOOL = Path(__file__).resolve().parent / "a10_interval_oracle.py"
A10_SUITES = ("test_cycle37_a10_interval_lineage",)
STORAGE_SUITES = a9.STORAGE_SUITES
CAREER_SUITES = a9.CAREER_SUITES + A10_SUITES
REGRESSION_SUITES = a9.REGRESSION_SUITES + A10_SUITES
CANDIDATE_SUITES = a9.CANDIDATE_SUITES + A10_SUITES
CAMP, WARREN = "Walter Camp", "Jimmy Warren"

REFUSED_PERIOD = "REFUSED_CAREER_SUCCESSOR_PERIOD_ANCHOR_MISMATCH"
REFUSED_PERIOD_WITNESS = "REFUSED_CAREER_SUCCESSOR_PERIOD_WITNESS_MISMATCH"
REFUSED_RESTRUCTURE = "REFUSED_CAREER_SUCCESSOR_RESTRUCTURE_CLAIM_MISMATCH"
REFUSED_A04_ANCHOR = a9.REFUSED_A04_ANCHOR
SERVED = "SERVED"
GENUINE_ROWS = a9.GENUINE_ROWS
GENUINE_EDGES = a9.GENUINE_EDGES
NAMED_PARENTS = a9.NAMED_PARENTS
#: The genuine interval-grain counts the v6 verifier must reproduce (unrestructured edges inside multi-interval fields,
#: each bound by equal identity ordinals, each child's stated interval read again from its source).
GENUINE_INTERVAL_EDGES = {"A5<-default": 273, "A5<-A4": 279, "A4<-default": 275}
GENUINE_MULTI_INTERVAL = {"A05_entries": 142, "A05_rows": 292, "A04_entries": 137, "A04_rows": 281}
VERIFIER_V6 = "BAS-C37A10-CAREER-SUCCESSOR-VERIFIER-v6"


def rebind() -> None:
    """Point the preserved runners at the Attempt 10 contract, roots, ledger, suites, tools and grants."""

    for name, value in (("ATTEMPT_NUMBER", ATTEMPT_NUMBER), ("ATTEMPT_ID", ATTEMPT_ID),
                        ("RUNNER_VERSION", RUNNER_VERSION), ("BASE_SHA", BASE_SHA), ("LABEL", LABEL),
                        ("LANE_ESTIMATES", LANE_ESTIMATES), ("EVIDENCE_ROOT", EVIDENCE_ROOT),
                        ("VALIDATION_ROOT", VALIDATION_ROOT), ("PACKAGING_ROOT", PACKAGING_ROOT),
                        ("OPERATIONAL_LEDGER", OPERATIONAL_LEDGER), ("FINAL_SNAPSHOT", FINAL_SNAPSHOT),
                        ("FINAL_OUTPUT_LEDGER", FINAL_OUTPUT_LEDGER), ("CANDIDATE_RECORDS", CANDIDATE_RECORDS),
                        ("BEFORE_REPRODUCTION", BEFORE_REPRODUCTION), ("INTAKE", INTAKE),
                        ("GIT_PREFLIGHTS", GIT_PREFLIGHTS), ("FIXTURES", FIXTURES),
                        ("MANAGER_ADVERSARIAL_FIXTURE", MANAGER_ADVERSARIAL_FIXTURE), ("LINEAGE_A05", LINEAGE_A05),
                        ("LINEAGE_A04", LINEAGE_A04), ("AFTER_COMMENTS", AFTER_COMMENTS),
                        ("PLATFORM_TOOL", PLATFORM_TOOL), ("OUTPUTS_TOOL", OUTPUTS_TOOL),
                        ("CONTROL_TOOL", CONTROL_TOOL), ("STORAGE_SUITES", STORAGE_SUITES),
                        ("CAREER_SUITES", CAREER_SUITES), ("REGRESSION_SUITES", REGRESSION_SUITES),
                        ("CANDIDATE_SUITES", CANDIDATE_SUITES), ("candidate", candidate)):
        setattr(a9, name, value)
    a9.rebind()
    base.CYCLE_ID = CYCLE_ID
    # Attempt 9's own roots are now denied writes: guarded like every earlier attempt's. The manager's saved Attempt 9
    # fixture folder is manager-owned and immutable: read (and copied from) only, so it is guarded too.
    base.GUARDED_ROOTS = tuple(dict.fromkeys(base.GUARDED_ROOTS + (VALIDATION_A09, PACKAGING_A09,
                                                                   Path(MANAGER_A9_FIXTURE_LITERAL))))
    attempt09_git.install()


LaneRun = a9.LaneRun
_json_file = a9._json_file
_refusal = a9._refusal


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
        problems.append("contract is not Cycle 37 Attempt 10")
    if contract.get("attempt_id") != ATTEMPT_ID:
        problems.append(f"contract attempt_id {contract.get('attempt_id')!r} is not {ATTEMPT_ID}")
    if (contract.get("repo") or {}).get("base_sha") != BASE_SHA:
        problems.append(f"contract base {(contract.get('repo') or {}).get('base_sha')} is not {BASE_SHA}")
    row = {r["id"]: r for r in contract.get("required_lanes", [])}.get(lane)
    if row is None or row.get("executor") != "worker":
        problems.append(f"{lane} is not a worker lane of this contract")
    elif f"attempt10_lanes.py --lane {lane} " not in row.get("command", ""):
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
    here = runner.parent
    binding.update({
        "base": BASE_SHA,
        "descends_from_base": base.git("merge-base", "--is-ancestor", BASE_SHA, binding["head"]).returncode == 0
        if binding.get("head") else False,
        "commits_after_base": git_out("rev-list", "--count", f"{BASE_SHA}..{binding['head']}") if binding.get("head")
        else None,
        "runner": str(runner), "runner_sha256": sha256_file(runner), "runner_version": RUNNER_VERSION,
        "rebound_attempt9_runner_sha256": sha256_file(Path(a9.__file__).resolve()),
        "a10_interval_oracle_tool_sha256": sha256_file(INTERVAL_ORACLE_TOOL),
        "a09_oracle_tool_sha256": sha256_file(here / "a09_source_unit_oracle.py"),
        "git_wrapper_sha256": sha256_file(Path(attempt09_git.__file__).resolve()),
        "candidate_tool_sha256": sha256_file(Path(candidate.__file__).resolve()),
        "control07_tool_sha256": sha256_file(CONTROL_TOOL),
    })
    return binding


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
                                                                                          "is_issued_base",
                                                                                          "installed_equal_to_base")},
        "started_at": reproduction.get("started_at"), "finished_at": reproduction.get("finished_at"),
        "saved_fixture": {k: (reproduction.get("saved_fixture") or {}).get(k) for k in ("sha256", "copy_matches")},
        "negatives_served_by_unfixed_base": reproduction.get("negatives_served_by_unfixed_base"),
        "positives_observed": reproduction.get("positives_observed"),
        "existing_negative_observed": reproduction.get("existing_negative_observed")}
    served = reproduction.get("negatives_served_by_unfixed_base") or {}
    if not (reproduction.get("reproduced") and (reproduction.get("subject_before") or {}).get("is_issued_base")
            and served and all(served.values())):
        run.problems.append("the before-repair reproduction is missing or did not reproduce MF37A09-01 on the base")
    intake = _json_file(INTAKE) or {}
    run.extra["intake"] = {"file": str(INTAKE), "sha256": sha256_file(INTAKE) if INTAKE.is_file() else None,
                           "contract_matches_issuance": (intake.get("contract") or {}).get("matches_issuance"),
                           "sources_all_match": intake.get("sources_all_match"),
                           "immutable_inputs_all_match": intake.get("immutable_inputs_all_match"),
                           "closures": {k: {kk: v.get(kk) for kk in ("archive_matches", "entries", "archived_mismatches")}
                                        for k, v in (intake.get("closures") or {}).items()},
                           "subjects": {k: (intake.get("subjects") or {}).get(k) for k in
                                        ("repair_is_issued_base", "candidate_is_granted_head", "main_is_recorded")}}
    if not (intake.get("sources_all_match") and (intake.get("contract") or {}).get("matches_issuance")
            and intake.get("immutable_inputs_all_match")):
        run.problems.append("the intake record does not bind every issued source, immutable input and the contract")
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


# ------------------------------------------------------------- storage (preserved, run fresh)


def _manager_a9_storage(run: LaneRun) -> dict[str, Any]:
    """The manager's Attempt 9 continuation challenge, byte-faithful but for its fixture root, importing this
    worktree's (unchanged) storage tools."""

    fixture = run.fresh("mgr_a9_storage_fixture")
    literal = f"F=Path(r'{MANAGER_A9_FIXTURE_LITERAL}')/'storage-independent'"
    copy, replay = a7._replay(run, MANAGER_A9, "storage_independent.py", "mgr_a9_storage_independent",
                              {literal: f"F=Path(r'{fixture}')/'storage-independent'"})
    record = run.run("manager_a9_storage_independent_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None),
                     note="The manager's saved Attempt 9 challenge; it imports this worktree's storage tools.")
    review = _json_file(copy.parent / "STORAGE_INDEPENDENT.json") or {}
    cases = {row["case"]: row for row in review.get("cases") or []}
    concurrent = cases.get("12 concurrent separate processes same child") or {}
    extra = cases.get("same-child restart requests additional empty tracked root") or {}
    others = {name: (row.get("result") or {}).get("code") for name, row in cases.items()
              if name not in ("12 concurrent separate processes same child",
                              "same-child restart requests additional empty tracked root")}
    results = [json.loads(r.get("stdout") or "{}") for r in concurrent.get("results") or []]
    verdict = {**replay, "exit": record.get("exit_code"), "source": review.get("source"),
               "concurrent": {"init_count": concurrent.get("init_count"),
                              "chain": (concurrent.get("chain") or {}).get("result"),
                              "restart": (concurrent.get("restart") or {}).get("result"),
                              "fresh_opens": sum(1 for r in results if r.get("resumed") is False),
                              "resumed_opens": sum(1 for r in results if r.get("resumed") is True)},
               "extra_root_restart": {"result": (extra.get("result") or {}).get("result"),
                                      "code": (extra.get("result") or {}).get("code"),
                                      "root_measured": extra.get("root_measured")},
               "other_cases": others}
    verdict["holds"] = (record.get("exit_code") == 0 and verdict["concurrent"]["init_count"] == 1
                        and verdict["concurrent"]["fresh_opens"] == 1 and verdict["concurrent"]["resumed_opens"] == 11
                        and verdict["concurrent"]["chain"] == "PASS" and verdict["concurrent"]["restart"] == "OPENED"
                        and verdict["extra_root_restart"]["result"] == "REFUSED"
                        and verdict["extra_root_restart"]["code"] == a9.REFUSED_ROOTS
                        and verdict["extra_root_restart"]["root_measured"] is False
                        and others.get("stopped parent without revised plan") == a9.REFUSED_PLAN_REQUIRED
                        and others.get("changed reserve without revised plan") == a9.REFUSED_PLAN_REQUIRED
                        and others.get("second child cannot recycle headroom") == a9.REFUSED_CLAIMED)
    return verdict


def lane_storage_admission(run: LaneRun) -> None:
    a8.lane_storage_admission(run)
    tools = a6c.WORKTREE / "tools" / "cycle37"
    unchanged = {name: {"head": sha256_file(tools / name),
                        "issued_base": sha256_bytes(subprocess.run(
                            attempt09_git.command("show", f"{BASE_SHA}:tools/cycle37/{name}", repo=a6c.WORKTREE),
                            capture_output=True, check=True).stdout)}
                 for name in ("storage_admission.py", "storage_snapshot.py")}
    run.extra["storage_tools_unchanged_since_the_issued_base"] = {
        "files": unchanged, "equal": all(v["head"] == v["issued_base"] for v in unchanged.values()),
        "meaning": ("The Attempt 9 root-contract repair is accepted within its tested scope; Attempt 10 does not change "
                    "the storage tools, and this lane runs their suites and the managers' challenges fresh anyway.")}
    if not run.extra["storage_tools_unchanged_since_the_issued_base"]["equal"]:
        run.problems.append("the storage tools changed since the issued base; the accepted behavior must be requalified")
    run.extra["attempt9_ledgers_retained"] = {
        p.name: sha256_file(p) for p in sorted((ATTEMPT9_ROOT / "evidence" / "storage").glob("*.jsonl"))
        + [ATTEMPT9_ROOT / "STORAGE_RESERVATIONS.jsonl"]}
    for key, probe in (("manager_a8_storage_independent", a9._manager_a8_storage),
                       ("manager_a9_storage_independent", _manager_a9_storage)):
        verdict = probe(run)
        run.extra[key] = verdict
        if not verdict["holds"]:
            run.problems.append(f"the {key.replace('_', ' ')} challenge does not hold against the storage tools: "
                                f"{ {k: v for k, v in verdict.items() if k not in ('literal_adaptations',)} }")


# ------------------------------------------------------------- the new suite on the unfixed base


#: The Attempt 10 suite's new negative cases: every one must fail over the unfixed base's bytes.
NEGATIVE_TESTS = {
    "test_cycle37_a10_interval_lineage": (
        "test_the_managers_crossed_intervals_are_refused_whatever_period_text_they_carry",
        "test_a_one_sided_swap_is_refused", "test_each_relation_alone_is_refused",
        "test_the_attempt4_format_crossing_is_refused", "test_the_list_line_crossing_is_refused",
        "test_missing_witnesses_with_crossed_intervals_are_refused",
        "test_an_identity_relabel_that_moves_the_rows_content_is_refused",
        "test_stated_interval_text_or_dates_that_are_not_the_identitys_are_refused",
        "test_an_attempt4_format_relabel_is_refused", "test_the_ordinal_rule_and_the_count_rule_on_their_own"),
}
#: Retained negatives: refused under the earlier rules too (the Attempt 7 restructure rule); recorded, never required
#: to fail on the base.
RETAINED_NEGATIVE_TESTS = {"test_cycle37_a10_interval_lineage": ("test_a_false_restructure_claim_with_blank_text_is_refused",)}
SAVED_CONSTRUCTION = ("test_cycle37_a10_interval_lineage::"
                      "test_the_managers_crossed_intervals_are_refused_whatever_period_text_they_carry[text='NULL']")


def _suite_on_the_unfixed_base(run: LaneRun) -> dict[str, Any]:
    folder = run.fresh("unfixed_base")
    archive = subprocess.run(attempt09_git.command("archive", "--format=tar", BASE_SHA, "src", "tests", "tools",
                                                   repo=a6c.WORKTREE), capture_output=True, check=False)
    if archive.returncode != 0:
        return {"holds": False, "problem": f"git archive of the issued base failed: {archive.stderr[-400:]!r}"}
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as bundle:
        bundle.extractall(folder, filter="data")
    copied = {}
    for suite in A10_SUITES:
        source = a6c.WORKTREE / "tests" / f"{suite}.py"
        (folder / "tests" / f"{suite}.py").write_bytes(source.read_bytes())
        copied[suite] = sha256_file(source)
    record = run.run("attempt10_suite_on_the_unfixed_base",
                     [run.python, "-B", "-m", "unittest", "-v", *(f"tests.{s}" for s in A10_SUITES)], cwd=folder,
                     env=run.env(pythonpath=None), expect_exit=1, timeout=1800,
                     note="The new suite over a git archive of the issued base 1478797b; every new negative case must "
                          "fail there, and the saved construction must be accepted by the unfixed verifier.")
    text = Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
    outcomes, classes = a9.classify_unfixed_log(text)

    def names(table: dict[str, tuple[str, ...]], key: str) -> bool:
        return key.split("[")[0].split("::")[1] in table.get(key.split("::")[0], ())

    # A test's verbose outcome line carries no subtest parameters; its failure blocks do. Both are selected by name.
    negative_keys = {k for k in set(outcomes) | set(classes) if names(NEGATIVE_TESTS, k)}
    retained_keys = {k for k in set(outcomes) | set(classes) if names(RETAINED_NEGATIVE_TESTS, k)}
    passing_negatives = sorted(k for k in negative_keys if outcomes.get(k) == "ok")
    wanted = {f"{suite}::{name}" for suite, tests in NEGATIVE_TESTS.items() for name in tests}
    seen = {k.split("[")[0] for k in negative_keys}
    negatives = {k: v for k, v in classes.items() if k in negative_keys}
    verdict = {"base": BASE_SHA, "export": str(folder), "suites": copied, "exit": record.get("exit_code"),
               "outcomes": outcomes, "classes": classes,
               "negative_cases": len(negative_keys), "negative_tests_seen": sorted(seen),
               "negative_tests_missing": sorted(wanted - seen), "negative_cases_passing_on_the_base": passing_negatives,
               "accepted_by_the_unfixed_code": sorted(k for k, v in negatives.items() if v == a9.ACCEPTED),
               "refused_under_another_cause": sorted(k for k, v in negatives.items() if v == a9.OTHER_CAUSE),
               "new_api_or_record_absent": sorted(k for k, v in negatives.items() if v == a9.NEW_API),
               "other_behavior": sorted(k for k, v in negatives.items() if v == a9.BEHAVIOR),
               "unclassified": sorted(k for k, v in negatives.items() if v == a9.UNCLASSIFIED),
               "retained_negative_cases_on_the_base": {k: {"outcome": outcomes.get(k), "class": classes.get(k)}
                                                       for k in sorted(retained_keys)},
               "positive_cases_on_the_base": {k: {"outcome": outcomes.get(k), "class": classes.get(k)}
                                              for k in sorted(set(outcomes) | set(classes))
                                              if k not in negative_keys and k not in retained_keys},
               "saved_construction": {"key": SAVED_CONSTRUCTION, "class": classes.get(SAVED_CONSTRUCTION)},
               "meaning": ("Over the unfixed base every new negative case fails: the saved construction (the reciprocal "
                           "crossing with NULL period text) and its blank, whitespace, parent-copied, enlarged and "
                           "substring variants, the one-sided crossing, each relation alone, the Attempt 4 format, the "
                           "list line, missing witnesses, the blank-text content relabels and stated interval text or "
                           "dates that are not the identity's are served there; the genuine-text crossing and the "
                           "relabel that keeps its text are refused there only under the earlier text rule; rows compared "
                           "by their own spans alone (the unit-level ordinal and count case) are accepted there, and the "
                           "new interval reader does not exist there. The retained false-restructure negative is "
                           "refused on both; positive cases (the genuine fixture, blank text and unstated dates, the "
                           "corrected reading, the restructure, the list line, the Attempt 4 format, the new reader's "
                           "unit test) may pass or fail there and are recorded.")}
    verdict["holds"] = (record.get("exit_code") not in (0, None) and not passing_negatives and not verdict["unclassified"]
                        and not verdict["negative_tests_missing"]
                        and verdict["saved_construction"]["class"] == a9.ACCEPTED)
    return verdict


def lane_source_regressions(run: LaneRun) -> None:
    a7.lane_source_regressions(run)
    verdict = _suite_on_the_unfixed_base(run)
    run.extra["attempt10_suite_on_the_unfixed_base"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the Attempt 10 suite does not show the defect on the unfixed base: "
                            f"{ {k: verdict.get(k) for k in ('exit', 'negative_cases_passing_on_the_base', 'unclassified', 'negative_tests_missing', 'saved_construction', 'problem')} }")


# ------------------------------------------------------------- the career successor (MF37A09-01)


def _a10_oracle(run: LaneRun, label: str, successor: Path, a04: Path) -> dict[str, Any]:
    out = run.run_dir / f"ORACLE_A10_{label}.json"
    run.run(f"independent_interval_oracle_{label}", [run.python, "-B", INTERVAL_ORACLE_TOOL, "--successor", successor,
                                                     "--a04", a04, "--database", DELIVERED_DB, "--out", out,
                                                     "--label", label],
            env=run.env(pythonpath=None), timeout=3600,
            note="The independent interval oracle: stdlib and the Attempt 8 raw-structure reader only, no project module.")
    document = _json_file(out) or {}
    document["receipt"] = {"path": str(out), "sha256": sha256_file(out) if out.is_file() else None}
    return document


def _relations(document: dict[str, Any], key: str) -> dict[str, Any]:
    return {r["relation"]: r.get(key) for r in document.get("relations") or []}


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

    def interval_bound(counts: dict[str, Any], edges: int) -> bool:
        return (counts.get("interval_checked") == edges
                and counts.get("interval_edges_bound_by_identity_ordinal") == edges
                and counts.get("interval_rows_read_again_from_source") == edges
                and counts.get("interval_bound_on") == "IDENTITY_ORDINALS_AND_SOURCE_INTERVALS")

    checks = {
        "verifier_is_v6": bindings.get("verifier_version") == VERIFIER_V6,
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
        "a05_default_interval_edges_bound_by_identity_and_source": interval_bound(default,
                                                                                  GENUINE_INTERVAL_EDGES["A5<-default"]),
        "a05_a04_interval_edges_bound_by_identity_and_source": interval_bound(cross, GENUINE_INTERVAL_EDGES["A5<-A4"]),
        "a04_format_interval_edges_bound_by_identity_and_source": interval_bound(older,
                                                                                 GENUINE_INTERVAL_EDGES["A4<-default"]),
    }
    run.extra["source_witness_checks"] = {"checks": checks, "successor": witnessed, "a04_relation": a04_witnessed,
                                          "a04_format": older_witnessed, "default_anchors": default,
                                          "a04_anchors": cross, "a04_format_anchors": older}
    run.extra["interval_grain_checks"] = {
        "checks": {k: v for k, v in checks.items() if "interval" in k or k == "verifier_is_v6"},
        "counts": {relation: {k: counts.get(k) for k in ("edges", "interval_checked",
                                                         "interval_edges_bound_by_identity_ordinal",
                                                         "interval_rows_read_again_from_source",
                                                         "interval_rows_stating_no_interval_text",
                                                         "restructured_entries", "interval_bound_on")}
                   for relation, counts in (("A5<-default", default), ("A5<-A4", cross), ("A4<-default", older))},
        "expected": GENUINE_INTERVAL_EDGES}
    for name, held in checks.items():
        if not held:
            run.problems.append(f"source unit / interval binding: {name} does not hold")
    # The Attempt 8 source-field oracle and the Attempt 9 identity-derived oracle, kept.
    genuine8 = a8._oracle(run, "genuine", A5_SUCCESSOR, A4_SUCCESSOR)
    genuine9 = a9._a09_oracle(run, "genuine", A5_SUCCESSOR, A4_SUCCESSOR)
    kept = {"a08_genuine_crossed": genuine8.get("crossed_edges"), "a08_genuine_unresolved": genuine8.get("unresolved"),
            "a09_genuine_crossed": genuine9.get("crossed_edges"), "a09_genuine_unresolved": genuine9.get("unresolved_edges"),
            "receipts": {"a08": genuine8.get("receipt"), "a09": genuine9.get("receipt")}}
    kept["holds"] = (genuine8.get("crossed_edges") == 0 and all(not v for v in (genuine8.get("unresolved") or {}).values())
                     and genuine9.get("crossed_edges") == 0 and genuine9.get("unresolved_edges") == 0)
    run.extra["earlier_oracles_kept"] = kept
    if not kept["holds"]:
        run.problems.append(f"the Attempt 8 or 9 oracle no longer holds over the genuine files: {kept}")
    # The Attempt 10 independent interval oracle (MF37A09-01): the genuine files and the manager's saved fixture.
    genuine = _a10_oracle(run, "genuine", A5_SUCCESSOR, A4_SUCCESSOR)
    saved_ok = SAVED_INTERVAL_COPY.is_file() and sha256_file(SAVED_INTERVAL_COPY) == MANAGER_A9_INTERVAL_SHA256
    saved = _a10_oracle(run, "manager_a9_interval", SAVED_INTERVAL_COPY, A4_SUCCESSOR) if saved_ok else {}
    groups = (genuine.get("groups") or {}).get("A05") or {}
    verdict = {
        "genuine": {k: genuine.get(k) for k in ("oracle_version", "rows", "captures_read", "groups", "invalid_edges",
                                                 "unresolved_edges", "missing_periods", "limits", "receipt")}
        | {"relations": [{k: r.get(k) for k in ("relation", "interval_grain_edges", "counts", "proven", "unresolved",
                                                "invalid", "examples")} for r in genuine.get("relations") or []]},
        "manager_a9_interval": {"fixture": str(SAVED_INTERVAL_COPY), "sha256_as_issued": saved_ok,
                                "invalid_by_relation": _relations(saved, "invalid"),
                                "examples": {r["relation"]: r.get("examples") for r in saved.get("relations") or []},
                                "a05_row_classes": ((saved.get("groups") or {}).get("A05") or {}).get("row_classes"),
                                "receipt": saved.get("receipt")},
    }
    verdict["holds"] = (
        genuine.get("rows") == GENUINE_ROWS and genuine.get("invalid_edges") == 0
        and groups.get("multi_interval_entries") == GENUINE_MULTI_INTERVAL["A05_entries"]
        and groups.get("rows_in_them") == GENUINE_MULTI_INTERVAL["A05_rows"] and groups.get("invalid") == 0
        and all(((genuine.get("groups") or {}).get(k) or {}).get("invalid") == 0 for k in ("default", "A04", "A05"))
        and saved_ok and _relations(saved, "invalid") == {"A5<-default": 2, "A5<-A4": 2, "A4<-default": 0}
        and all("INVALID_CROSSED_INTERVAL" in (r.get("examples") or {}) for r in saved.get("relations") or []
                if r.get("invalid")))
    run.extra["independent_interval_oracle"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the independent interval oracle does not hold: genuine invalid "
                            f"{genuine.get('invalid_edges')}, A05 groups {groups}, saved {_relations(saved, 'invalid')}")


# ------------------------------------------------------------- the installed consumer (MF37A09-01)


def _rows(c: sqlite3.Connection, table: str, person: str, family: str, row_index: int) -> tuple[dict[str, Any], ...]:
    rows = tuple(dict(r) for r in c.execute(f"SELECT * FROM {table} WHERE person_display=? AND family=? AND row_index=? "
                                            "ORDER BY interval_index", (person, family, row_index)))
    if len(rows) != 2:
        raise RuntimeError(f"{person} {family} {row_index} in {table} is not a two-interval field: {len(rows)} rows")
    return rows


def _camp(c: sqlite3.Connection, table: str = "career_episode_a05") -> tuple[dict[str, Any], ...]:
    return _rows(c, table, CAMP, "COACHING", 2)


def _warren(c: sqlite3.Connection) -> tuple[dict[str, Any], ...]:
    return _rows(c, "career_episode_a05", WARREN, "PLAYING", 1003)


def _set(c: sqlite3.Connection, table: str, row: dict[str, Any], **changes: Any) -> None:
    c.execute(f"UPDATE {table} SET " + ", ".join(f'"{k}"=?' for k in changes) + " WHERE episode_id=?",
              (*changes.values(), row["episode_id"]))


_FIELD_TEXT = "1892, 1894\u20131895"
_INTERVAL_COLUMNS = ("years_as_written", "start", "end", "ongoing", "start_state", "end_state", "start_bounds",
                     "end_bounds", "start_qualifier", "end_qualifier", "definite_first_season", "definite_last_season",
                     "bounds_consistent")


def _crossed(text: str, *, default: bool = True, a04: bool = True) -> Callable[[sqlite3.Connection], dict[str, Any]]:
    """The manager's recipe on Walter Camp's two Stanford intervals, with the rows' period text set to ``text``."""

    def build(c: sqlite3.Connection) -> dict[str, Any]:
        first, second = _camp(c)
        swap = a7._swap_edges(c, first, second, default=default, a04=a04)
        values = {"NULL": (None, None), "empty": ("", ""), "whitespace": ("   ", "   "),
                  "parent-copied": (second["years_as_written"], first["years_as_written"]),
                  "enlarged": (_FIELD_TEXT, _FIELD_TEXT), "substring": ("189", "189"),
                  "genuine": (first["years_as_written"], second["years_as_written"])}[text]
        for row, value in zip((first, second), values):
            _set(c, "career_episode_a05", row, years_as_written=value)
        return {"swap": swap, "period_text": text, "rows": [first["episode_id"], second["episode_id"]]}
    return build


def _one_sided(c: sqlite3.Connection) -> dict[str, Any]:
    """Only the 1892 row is crossed: it names the 1894–1895 row's default and Attempt 4 parents (text NULL); the
    1892 parents are left producing nothing (NOT_PRODUCED), the 1894–1895 parents naming both rows."""

    first, second = _camp(c)
    parent, parent4 = json.loads(second["predecessor_episode_ids"]), json.loads(second["a04_episode_ids"])
    own, own4 = json.loads(first["predecessor_episode_ids"]), json.loads(first["a04_episode_ids"])
    _set(c, "career_episode_a05", first, predecessor_episode_ids=json.dumps(parent), a04_episode_ids=json.dumps(parent4),
         years_as_written=None)
    both = json.dumps(sorted([first["episode_id"], second["episode_id"]]))
    c.execute("UPDATE career_a05_disposition SET successor_episode_ids=? WHERE predecessor_episode_id=?", (both, parent[0]))
    c.execute("UPDATE career_a05_disposition SET successor_episode_ids='[]', disposition=? WHERE predecessor_episode_id=?",
              ("NOT_PRODUCED_BY_THE_SUCCESSOR_PARSER", own[0]))
    c.execute("UPDATE career_a05_from_a04 SET a05_episode_ids=? WHERE a04_episode_id=?", (both, parent4[0]))
    c.execute("UPDATE career_a05_from_a04 SET a05_episode_ids='[]', disposition=? WHERE a04_episode_id=?",
              ("NOT_PRODUCED_BY_THE_SUCCESSOR_PARSER", own4[0]))
    states = {r[0] for r in c.execute("SELECT disposition FROM career_a05_disposition WHERE predecessor_episode_id=?",
                                      (parent[0],))}
    states4 = {r[0] for r in c.execute("SELECT disposition FROM career_a05_from_a04 WHERE a04_episode_id=?",
                                       (parent4[0],))}
    _set(c, "career_episode_a05", first, disposition=",".join(sorted(states)), a04_disposition=",".join(sorted(states4)))
    return {"crossed": first["episode_id"], "names": parent + parent4, "left_not_produced": own + own4}


def _a04_format_crossed(c: sqlite3.Connection) -> dict[str, Any]:
    first, second = _camp(c, "career_episode_a04")
    swap = a7._swap_edges(c, first, second, table="career_episode_a04")
    for row in (first, second):
        _set(c, "career_episode_a04", row, years_as_written=None)
    return {"swap": swap, "period_text": "NULL"}


def _list_line_crossed(c: sqlite3.Connection) -> dict[str, Any]:
    first, second = _warren(c)
    swap = a7._swap_edges(c, first, second)
    for row in (first, second):
        _set(c, "career_episode_a05", row, years_as_written=None)
    return {"swap": swap, "line": first["team_raw"], "period_text": "NULL"}


def _missing_witnesses_crossed(c: sqlite3.Connection) -> dict[str, Any]:
    first, second = _camp(c)
    swap = a7._swap_edges(c, first, second)
    for row in (first, second):
        _set(c, "career_episode_a05", row, years_as_written=None, team_char_span=None, team_byte_span=None,
             years_char_span=None)
    return {"swap": swap, "witnesses": "team, byte and years spans NULL", "period_text": "NULL"}


def _false_restructure(c: sqlite3.Connection) -> dict[str, Any]:
    """Both rows claim both parents as a re-read (restructured) field -- the count is unchanged -- with blank text."""

    first, second = _camp(c)
    parents = sorted(json.loads(first["predecessor_episode_ids"]) + json.loads(second["predecessor_episode_ids"]))
    both = json.dumps(sorted([first["episode_id"], second["episode_id"]]))
    for row in (first, second):
        _set(c, "career_episode_a05", row, predecessor_episode_ids=json.dumps(parents),
             disposition="RESTRUCTURED_INTERVALS", years_as_written=None)
    for parent in parents:
        c.execute("UPDATE career_a05_disposition SET successor_episode_ids=?, disposition='RESTRUCTURED_INTERVALS' "
                  "WHERE predecessor_episode_id=?", (both, parent))
    return {"rows": [first["episode_id"], second["episode_id"]], "claimed_parents": parents}


def _relabel(table: str, blank: bool) -> Callable[[sqlite3.Connection], dict[str, Any]]:
    """Each identity keeps its genuine edges, but the two rows' interval content trades places."""

    def build(c: sqlite3.Connection) -> dict[str, Any]:
        first, second = _camp(c, table)
        for row, other in ((first, second), (second, first)):
            changes = {k: other.get(k) for k in _INTERVAL_COLUMNS}
            if blank:
                changes["years_as_written"] = None
            _set(c, table, row, **changes)
        return {"rows": [first["episode_id"], second["episode_id"]], "content_swapped": list(_INTERVAL_COLUMNS),
                "period_text": "NULL" if blank else "the other row's"}
    return build


def _stated(**change: Any) -> Callable[[sqlite3.Connection], dict[str, Any]]:
    def build(c: sqlite3.Connection) -> dict[str, Any]:
        first, second = _camp(c)
        values = {k: (second["years_as_written"] if v == "OTHER_TEXT" else v) for k, v in change.items()}
        _set(c, "career_episode_a05", first, **values)
        return {"row": first["episode_id"], "stated": values, "edges": "genuine"}
    return build


def _genuine_blank(fields: bool) -> Callable[[sqlite3.Connection], dict[str, Any]]:
    """Positive control: genuine edges, period text NULL (and, with ``fields``, every interval field NULL)."""

    def build(c: sqlite3.Connection) -> dict[str, Any]:
        rows = _camp(c)
        for row in rows:
            changes = {"years_as_written": None}
            if fields:
                changes.update({k: None for k in _INTERVAL_COLUMNS[1:]})
            _set(c, "career_episode_a05", row, **changes)
        return {"rows": [r["episode_id"] for r in rows], "unstated": list(changes)}
    return build


#: (name, format, builder, person, expected refusal code or SERVED, the cause the message must name)
def a10_cases() -> list[tuple[str, str, Callable[[sqlite3.Connection], dict[str, Any]], str, str, str]]:
    cases: list[tuple[str, str, Callable[[sqlite3.Connection], dict[str, Any]], str, str, str]] = [
        (f"a05_crossed_period_text_{text.replace('-', '_')}", "A05", _crossed(text), CAMP, REFUSED_PERIOD, "PERIOD")
        for text in ("NULL", "empty", "whitespace", "parent-copied", "enlarged", "substring", "genuine")]
    cases += [
        ("a05_one_sided_crossing", "A05", _one_sided, CAMP, REFUSED_PERIOD, "PERIOD"),
        ("a05_default_relation_only_crossed", "A05", _crossed("NULL", a04=False), CAMP, REFUSED_PERIOD, "PERIOD"),
        ("a05_attempt4_relation_only_crossed", "A05", _crossed("NULL", default=False), CAMP, REFUSED_A04_ANCHOR,
         "PERIOD"),
        ("a04_format_crossed_null_text", "A04", _a04_format_crossed, CAMP, REFUSED_PERIOD, "PERIOD"),
        ("a05_list_line_crossed_null_text", "A05", _list_line_crossed, WARREN, REFUSED_PERIOD, "PERIOD"),
        ("a05_missing_witnesses_crossed_null_text", "A05", _missing_witnesses_crossed, CAMP, REFUSED_PERIOD, "PERIOD"),
        ("a05_false_restructure_claim_null_text", "A05", _false_restructure, CAMP, REFUSED_RESTRUCTURE, "RESTRUCTURE"),
        ("a05_content_relabel_null_text", "A05", _relabel("career_episode_a05", True), CAMP, REFUSED_PERIOD_WITNESS,
         "PERIOD_WITNESS"),
        ("a05_content_relabel_with_text", "A05", _relabel("career_episode_a05", False), CAMP, REFUSED_PERIOD_WITNESS,
         "PERIOD_WITNESS"),
        ("a04_format_content_relabel_null_text", "A04", _relabel("career_episode_a04", True), CAMP,
         REFUSED_PERIOD_WITNESS, "PERIOD_WITNESS"),
        ("a05_stated_other_interval_text", "A05", _stated(years_as_written="OTHER_TEXT"), CAMP, REFUSED_PERIOD_WITNESS,
         "INTERVAL_TEXT_IS_NOT_ITS_SOURCE_INTERVAL"),
        ("a05_stated_enlarged_text", "A05", _stated(years_as_written=_FIELD_TEXT), CAMP, REFUSED_PERIOD_WITNESS,
         "INTERVAL_TEXT_IS_NOT_ITS_SOURCE_INTERVAL"),
        ("a05_stated_other_start", "A05", _stated(start=1894), CAMP, REFUSED_PERIOD_WITNESS,
         "INTERVAL_FIELD_IS_NOT_ITS_SOURCE_INTERVAL"),
        ("a05_genuine_blank_period_text", "A05", _genuine_blank(False), CAMP, SERVED, ""),
        ("a05_genuine_blank_period_text_and_unstated_dates", "A05", _genuine_blank(True), CAMP, SERVED, ""),
    ]
    return cases


def _manager_a9_interval(run: LaneRun, installed: dict[str, Any]) -> dict[str, Any]:
    """The manager's saved interval fixture, byte for byte (the owned copy, never written), through all three
    entrypoints (the manager's INTERVAL_INDEPENDENT_CHALLENGE commands)."""

    digest = sha256_file(SAVED_INTERVAL_COPY)
    args = ["--career", "--career-successor", SAVED_INTERVAL_COPY, "--career-successor-sha256", digest, "--person", CAMP,
            "--compact"]
    records = {"installed_console_script": base._cli(run, installed, "a10_manager_interval_script", args, expect_exit=1),
               "installed_module": a7._module_entrypoint(run, installed, "a10_manager_interval_module", args,
                                                         expect_exit=1),
               "source_module": a8._source_module_entrypoint(run, installed, "a10_manager_interval_source", args,
                                                             expect_exit=1)}
    texts = {k: Path(r["log_path"]).read_text(encoding="utf-8", errors="replace") for k, r in records.items()}
    refusals = {k: _refusal(t) for k, t in texts.items()}
    exits = {k: r.get("exit_code") for k, r in records.items()}
    verdict = {"fixture": str(SAVED_INTERVAL_COPY), "manager_original": str(MANAGER_A9_INTERVAL),
               "fixture_sha256": digest, "as_issued": digest == MANAGER_A9_INTERVAL_SHA256, "exits": exits,
               "refusals": refusals, "expected": REFUSED_PERIOD,
               "names_the_crossed_intervals": {k: "(interval 0" in t and "(interval 1" in t for k, t in texts.items()},
               "before_repair": "every entrypoint exited 0 serving four rows (evidence/before/BEFORE_REPRODUCTION.json)"}
    verdict["holds"] = verdict["as_issued"] and all(v == 1 for v in exits.values()) and all(
        v == REFUSED_PERIOD for v in refusals.values()) and all(verdict["names_the_crossed_intervals"].values())
    return verdict


def _a10_forgeries(run: LaneRun, installed: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {"fixtures": {"a05": str(LINEAGE_A05), "a04": str(LINEAGE_A04)}, "cases": {},
                               "rule": ("each case restores its fixture from the genuine file, builds its interval "
                                        "construction, reseals every ledger as a careful forger would, pins the digest "
                                        "and serves through the console script and the module entrypoint; a forgery "
                                        "must be refused for its own cause at both, a positive control served at both")}
    for name, fmt, builder, person, expected, cause in a10_cases():
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
        args = ["--career", "--career-successor", fixture, "--career-successor-sha256", digest, "--person", person,
                "--limit", "100", "--compact"]
        exit_expected = 0 if expected == SERVED else 1
        script = base._cli(run, installed, f"a10_{name}", args, expect_exit=exit_expected)
        module = a7._module_entrypoint(run, installed, f"a10_{name}_module", args, expect_exit=exit_expected)
        texts = {kind: Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
                 for kind, record in (("script", script), ("module", module))}
        refusals = {kind: _refusal(text) for kind, text in texts.items()}
        row = {"format": fmt, "person": person, "fixture_sha256": digest, "details": details, "expected": expected,
               "cause": cause, "script_exit": script.get("exit_code"), "module_exit": module.get("exit_code"),
               "refusals": refusals}
        if expected == SERVED:
            served = {kind: (base._stdout_json(record) or {}).get("row_count")
                      for kind, record in (("script", script), ("module", module))}
            row.update(served_rows=served, holds=script.get("exit_code") == 0 and module.get("exit_code") == 0
                       and all(isinstance(v, int) and v > 0 for v in served.values()) and not any(refusals.values()))
        else:
            row.update(cause_named={k: cause in t for k, t in texts.items()},
                       holds=script.get("exit_code") == 1 and module.get("exit_code") == 1
                       and refusals["script"] == expected and refusals["module"] == expected
                       and all(cause in t for t in texts.values()))
        results["cases"][name] = row
        if not row["holds"]:
            run.problems.append(f"A10 interval case {name} did not hold at both entrypoints: {refusals}")
    for fixture, source in ((LINEAGE_A05, A5_SUCCESSOR), (LINEAGE_A04, A4_SUCCESSOR)):
        a6._restore(fixture, source)
    results["genuine_unchanged"] = (sha256_file(A5_SUCCESSOR) == A5_SUCCESSOR_SHA256
                                    and sha256_file(A4_SUCCESSOR) == A4_SUCCESSOR_SHA256)
    results["holds"] = results["genuine_unchanged"] and all(row["holds"] for row in results["cases"].values())
    return results


def lane_installed_consumer_c01(run: LaneRun) -> None:
    a9.lane_installed_consumer_c01(run)
    raw = run.extra.get("installed")
    if not raw:
        return
    installed = {key: Path(value) for key, value in raw.items()}
    verdict = _manager_a9_interval(run, installed)
    run.extra["manager_a9_interval_entrypoints"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's saved interval fixture is not refused for its interval cause at every "
                            f"entrypoint: {verdict}")
    run.extra["a10_interval_cases"] = _a10_forgeries(run, installed)


# ------------------------------------------------------------- the local integration candidate (R37A10-03)


def _append_chain(head: str) -> dict[str, Any]:
    """Every Attempt 10 append continues the one before it, the first from the granted head ``514d74dc``, the last
    ending at ``head``."""

    records = a9._append_records()
    chain = [{"record": str(path), "previous": record.get("previous_candidate_head"),
              "commit": record.get("candidate_commit"), "repair_head": record.get("repair_head"),
              "packs_unchanged": (record.get("git_housekeeping") or {}).get("packs_unchanged")}
             for path, record in records]
    expected = [candidate.ISSUED_CANDIDATE_HEAD] + [row["commit"] for row in chain[:-1]]
    holds = (bool(chain) and [row["previous"] for row in chain] == expected and chain[-1]["commit"] == head
             and all(row["packs_unchanged"] for row in chain))
    return {"appends": chain, "starts_from": candidate.ISSUED_CANDIDATE_HEAD, "holds": holds}


def _manager_a9_committed_tree(run: LaneRun, head: str) -> dict[str, Any]:
    copy, replay = a7._replay(run, MANAGER_A9, "committed_tree_review.py", "mgr_a9_committed_tree")
    record = run.run("manager_a9_committed_tree_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None),
                     note="The manager's saved Attempt 9 committed-byte provenance probe, byte-identical; it reads the "
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
    run.extra["candidate_attempt10"] = {
        "appends_continue_514d74dc_with_no_pack_written": chain["holds"],
        "514d74dc_is_ancestor": description.get("attempt10_start_is_ancestor") is True,
        "c52e7b52_is_ancestor": description.get("attempt9_start_is_ancestor") is True,
        "0c22af20_is_ancestor": description.get("attempt8_start_is_ancestor") is True,
        "bb5253b2_is_ancestor": description.get("attempt7_start_is_ancestor") is True,
        "preserved_first_candidate_is_ancestor": description.get("issued_head_is_ancestor") is True}
    run.extra["candidate_append_chain_attempt10"] = chain
    if not all(run.extra["candidate_attempt10"].values()):
        run.problems.append(f"the candidate does not continue the granted head: {run.extra['candidate_attempt10']}")
    if not run.rehearsal:
        for key, probe in (("manager_a9_committed_tree", _manager_a9_committed_tree),
                           ("manager_a8_committed_tree", a9._manager_a8_committed_tree),
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


# ------------------------------------------------------------- mounted lanes


def _attempt9_final(lane: str) -> dict[str, Any]:
    rows = [json.loads(line) for line in (ATTEMPT9_ROOT / "lanes" / "RUNS.jsonl").read_text(encoding="utf-8")
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
    previous = _attempt9_final("FULL_FINAL_MOUNTED")
    comparison: dict[str, Any] = {"attempt9_receipt": previous.get("receipt"),
                                  "attempt9_receipt_sha256": previous.get("receipt_sha256"),
                                  "attempt9_run": previous.get("run"), "attempt9_result": previous.get("result")}
    if not previous:
        run.problems.append("no Attempt 9 FULL_FINAL_MOUNTED receipt at the issued base to compare with")
    else:
        a9_log = Path(next(c["log_path"] for c in previous["data"]["commands"]
                           if c["lane"].endswith("full_suite_mounted")))
        before = base._log_identities(a9_log)
        persisting = sorted(set(final["failed_or_errored"]) & set(before["failed_or_errored"]))
        new = sorted(set(final["failed_or_errored"]) - set(before["failed_or_errored"]))
        final_causes = base._failure_causes(log, persisting)
        before_causes = base._failure_causes(a9_log, persisting)
        comparison.update({
            "attempt9_log": str(a9_log), "attempt9_log_sha256": sha256_file(a9_log),
            "attempt9_tests_run": before["tests_run"], "final_tests_run": final["tests_run"],
            "attempt9_failed_or_errored": before["failed_or_errored"], "persisting": persisting,
            "new_in_attempt10": new,
            "no_longer_failing": sorted(set(before["failed_or_errored"]) - set(final["failed_or_errored"])),
            "new_failure_causes": base._failure_causes(log, new),
            "persisting_same_cause": sorted(i for i in persisting if final_causes[i] == before_causes[i]),
            "persisting_changed_cause": {i: {"attempt9": before_causes[i], "attempt10": final_causes[i]}
                                         for i in persisting if final_causes[i] != before_causes[i]},
        })
        if new:
            run.problems.append(f"new failing identities relative to Attempt 9: {new}")
    run.extra["attempt9_comparison"] = comparison


def lane_strict_mounted(run: LaneRun) -> None:
    base.lane_strict_mounted(run)
    final = [row["identity"] for row in run.extra.get("strict_findings") or []]
    previous = _attempt9_final("STRICT_MOUNTED")
    comparison: dict[str, Any] = {"attempt9_receipt": previous.get("receipt"), "attempt9_run": previous.get("run"),
                                  "attempt9_result": previous.get("result")}
    if not previous:
        run.problems.append("no Attempt 9 STRICT_MOUNTED receipt at the issued base to compare with")
    else:
        before = [row["identity"] for row in (previous["data"].get("details") or {}).get("strict_findings") or []]
        comparison.update({"attempt9_findings": before, "final_findings": final,
                           "persisting": sorted(set(final) & set(before)),
                           "new_in_attempt10": sorted(set(final) - set(before)),
                           "no_longer_reported": sorted(set(before) - set(final))})
        if comparison["new_in_attempt10"]:
            run.problems.append(f"new strict findings relative to Attempt 9: {comparison['new_in_attempt10']}")
    run.extra["attempt9_comparison"] = comparison


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
