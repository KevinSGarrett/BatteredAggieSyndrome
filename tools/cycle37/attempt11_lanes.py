r"""Cycle #37 — Attempt #11 — the lane runner (MF37A10-01, R37A11-01..05).

    attempt11_lanes.py --lane <ID> --contract <cycle_contract.json> --out-root <attempt root> [--rehearsal]

The preserved Attempt 10 runner (``attempt10_lanes``, over the Attempt 9, 8, 7, 6, 5, 4 and 3 runners) rebound to the
Attempt 11 contract, roots, ledger, suites and tools. Everything the earlier runners bind per run is still bound -- the
issued contract by its sealed digest, the committed subject (branch, head, tree, source digest, descent from the issued
base, a clean tree before and after), the interpreter, module origins, the delivered database by digest, the data root
and ``C:\All-22`` measured before and after, the main checkout and both integration worktrees, credential removal, the
guard and storage qualification of the costly lanes, and the shared Git store around every lane. What Attempt 11 adds:

* **START_CONTEXT** binds the Attempt 11 intake, the before-repair reproduction of MF37A10-01 (the manager's saved
  count-changing false restructure served by the unfixed base at all three entrypoints) and the Git housekeeping
  preflight receipts.
* **STORAGE_ADMISSION** keeps the accepted storage behavior by running it fresh (the storage suites and the managers'
  Attempt 8 and 9 challenges) and proves the storage tools and suites are the exact bytes the Attempt 10 final
  STORAGE_ADMISSION receipt qualified (R37A11-02-A).
* **SOURCE_REGRESSIONS** runs the Attempt 11 restructure suite against the exact bytes of the issued base (a ``git
  archive`` of ``c2f82759``) and classifies every outcome by what the unfixed verifier did: every new negative case must
  fail there; retained negatives (refused under the earlier rules too) and positives are recorded, never required.
* **CAREER_SUCCESSOR (MF37A10-01)** checks the v7 verifier's every-row source-interval census, its restructure
  qualification, its NOT_PRODUCED and completeness proofs over both genuine successors, and runs the independent
  source-cardinality oracle (``a11_interval_oracle.py``, no project import, no restructure exemption) over the genuine
  files, the manager's saved false-restructure fixture and the manager's saved Attempt 9 interval fixture; the Attempt
  8, 9 and 10 oracles run too.
* **INSTALLED_CONSUMER_C01** replays the manager's saved false-restructure fixture byte for byte through the installed
  console script, the installed module and the source module, and serves this attempt's matrix -- count-changing
  collapse with genuine, forged, blank, enlarged and parent-copied period text, expansion with and without a
  fabricated interval, a restructured merge expanded past its source, a restructured split collapsed and relabelled
  ordinary, forged periods on every formerly exempt branch (ordinary single, added, role line, restructured merge and
  split), the Attempt 4 format, and the retained collapse variants -- each restored from the genuine file, resealed and
  refused for its own cause through the console script and the module, with the genuine source-supported splits,
  merges, role lines, added and corrected rows and genuine blank period text served as the positive controls.
* **LOCAL_INTEGRATION_CANDIDATE** verifies the Attempt 11 append continues ``cf992e4b`` with no pack written, replays
  the manager's Attempt 10, 9, 8, 7 and 6 committed-tree reviews, and re-binds the retained CONTROL-07 proposal offline.
* **FULL_FINAL_MOUNTED / STRICT_MOUNTED** compare identities with the Attempt 10 final receipts at the issued base.
* Every lane's receipt and its index line are written inside a reservation of their own, opened after the lane's
  reservation is reconciled (R37A11-02-B: receipt overhead is admitted before it is written).

A lane decides what its commands did. It does not decide scientific acceptance, and it cannot turn an inherited red
lane green.

Same-assignment continuation of Attempt 11 (no Attempt 12; MF37A11-01 / W37A11-07):

* The lane reservation is opened before the run folder, so it cannot carry the run's stamp. The runner keeps the
  reservation it was admitted under (``run.storage_reservation``) and FINAL_PACKET's ledger check is bound to that token
  and operation (``attempt07_lanes._owned_final_reservation``), not to a second clock reading. A rehearsal is charged to the
  live ledger and mirrors its reservation into the tiny final-output ledger its packet check reads.
* ``--continuation`` admits a lane after the operational ledger is frozen, on the attempt's one claimed final-output
  continuation (same budget, roots and reserve; no segment or root is added). Without it a frozen attempt refuses
  material lanes exactly as before.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt10_lanes as a10  # noqa: E402  (the preserved Attempt 10 runner)
import attempt11_candidate as candidate  # noqa: E402
import attempt09_git  # noqa: E402  (unchanged; every Git command carries the housekeeping settings)

a9, a8, a7, a6, a5, a4, base, a6c = a10.a9, a10.a8, a10.a7, a10.a6, a10.a5, a10.a4, a10.base, a10.a6c
storage, snapshot = a10.storage, a10.snapshot
BLOCKED, DATA_ROOT, DELIVERED_DB, FAIL, PASS = a10.BLOCKED, a10.DATA_ROOT, a10.DELIVERED_DB, a10.FAIL, a10.PASS
Tee, credential_scrub, git_out, sha256_bytes, sha256_file, utc_now = (a10.Tee, a10.credential_scrub, a10.git_out,
                                                                      a10.sha256_bytes, a10.sha256_file, a10.utc_now)

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 11
CYCLE_ID = "CYCLE-37"
ATTEMPT_ID = "ATTEMPT-11-20260928"
RUNNER_VERSION = "BAS-C37-ATTEMPT11-LANES-v1"
BASE_SHA = "c2f82759f85b8a6c919fd43234bacbea29b7ae28"
BRANCH = "codex/BAT-706-cycle37-rework"
LABEL = "Cycle #37 \u2014 Attempt #11 \u2014"
LANES = a10.LANES
GATED = a10.GATED
MIB = 1024 * 1024
#: Each lane's reservation, from the measured Attempt 10 costs (INSTALLED_CONSUMER_C01 350 to 545 MiB, the candidate
#: lane 119 MiB, PLATFORM_CARRY 81 MiB, SOURCE_REGRESSIONS and CAREER_SUCCESSOR 22 MiB each) with margin, plus this
#: attempt's additions (the oracle's receipts over four files, thirty-odd more installed cases).
LANE_ESTIMATES = {
    "START_CONTEXT": 16 * MIB, "WRITE_PROTECTION": 32 * MIB, "STORAGE_ADMISSION": 64 * MIB,
    "SOURCE_ADMISSION": 32 * MIB, "SOURCE_HARNESS": 32 * MIB, "SOURCE_REGRESSIONS": 96 * MIB,
    "CAREER_SUCCESSOR": 192 * MIB, "INSTALLED_CONSUMER_C01": 768 * MIB, "LOCAL_INTEGRATION_CANDIDATE": 256 * MIB,
    "TRUE_UNMOUNTED": 32 * MIB, "FULL_FINAL_MOUNTED": 64 * MIB, "STRICT_MOUNTED": 32 * MIB,
    "PLATFORM_CARRY": 192 * MIB, "FINAL_PACKET": 32 * MIB,
}
#: The receipt window each lane opens after its own reservation is reconciled: the receipt (the largest, the
#: installed lane's, was 3 MiB in Attempt 10), the index line, the lane log's last lines and the ledger's own records.
RECEIPT_ESTIMATE = 16 * MIB

EVIDENCE_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt11"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a11")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37a11")
ATTEMPT10_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt10"
VALIDATION_A10 = Path(r"C:\BatteredAggieSyndrome.validation\c37a10")
PACKAGING_A10 = Path(r"C:\BatteredAggieSyndrome.packaging\c37a10")
MANAGER_A10 = DATA_ROOT / "ops" / "manager_reviews" / "cycle37" / "attempt10" / "review-20260928T174921Z"
MANAGER_A10_FIXTURE_LITERAL = r"C:\BatteredAggieSyndrome.validation\mr37a10-174921"
MANAGER_A10_FALSE_RESTRUCTURE = Path(MANAGER_A10_FIXTURE_LITERAL) / "false-restructure-adversarial.sqlite"
MANAGER_A10_FALSE_RESTRUCTURE_SHA256 = "868d22d73c985aeb0cbf49016c2e796b7f617fc0a63be544e2268df741696135"
KNOWN_ANOMALIES = MANAGER_A10 / "INTERVAL_POPULATION_INDEPENDENT.json"
A5_SUCCESSOR, A5_SUCCESSOR_SHA256 = a10.A5_SUCCESSOR, a10.A5_SUCCESSOR_SHA256
A4_SUCCESSOR, A4_SUCCESSOR_SHA256 = a10.A4_SUCCESSOR, a10.A4_SUCCESSOR_SHA256
OPERATIONAL_LEDGER = EVIDENCE_ROOT / "STORAGE_RESERVATIONS.jsonl"
FINAL_SNAPSHOT = EVIDENCE_ROOT / "STORAGE_EVIDENCE_SNAPSHOT.json"
FINAL_OUTPUT_LEDGER = EVIDENCE_ROOT / "evidence" / "storage" / "STORAGE_RESERVATIONS_FINAL_OUTPUT.jsonl"
CANDIDATE_RECORDS = EVIDENCE_ROOT / "evidence" / "integration"
BEFORE_REPRODUCTION = EVIDENCE_ROOT / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
INTAKE = EVIDENCE_ROOT / "evidence" / "intake" / "INTAKE.json"
GIT_PREFLIGHTS = (EVIDENCE_ROOT / "evidence" / "intake" / "GIT_HOUSEKEEPING_PREFLIGHT.json",
                  EVIDENCE_ROOT / "evidence" / "intake" / "GIT_HELPER_CONSTRUCTION.json")
FIXTURES = VALIDATION_ROOT / "fixtures"
#: The owned copy of the manager's saved false-restructure fixture (made by the before-repair reproduction; never
#: written) and the owned full copies of the genuine successors, restored before every forgery.
MANAGER_ADVERSARIAL_FIXTURE = FIXTURES / "mr"
SAVED_FALSE_RESTRUCTURE_COPY = MANAGER_ADVERSARIAL_FIXTURE / "false-restructure-adversarial.sqlite"
LINEAGE_A05 = FIXTURES / "lineage" / "successor_a05.sqlite"
LINEAGE_A04 = FIXTURES / "lineage" / "successor_a04.sqlite"
AFTER_COMMENTS = (("BAT-706", "C37-A11-AFTER-HANDOFF-BAT-706"), ("BAT-708", "C37-A11-AFTER-HANDOFF-BAT-708"))
PLATFORM_TOOL = "tools/cycle37/attempt11_platform.py"
OUTPUTS_TOOL = "tools/cycle37/attempt11_outputs.py"
CONTROL_TOOL = Path(__file__).resolve().parent / "attempt11_control07.py"
INTERVAL_ORACLE_TOOL = Path(__file__).resolve().parent / "a11_interval_oracle.py"
A11_SUITES = ("test_cycle37_a11_restructure_lineage",)
STORAGE_SUITES = a10.STORAGE_SUITES
CAREER_SUITES = a10.CAREER_SUITES + A11_SUITES
REGRESSION_SUITES = a10.REGRESSION_SUITES + A11_SUITES
CANDIDATE_SUITES = a10.CANDIDATE_SUITES + A11_SUITES
CAMP = a10.CAMP

REFUSED_CARDINALITY = "REFUSED_CAREER_SUCCESSOR_INTERVAL_CARDINALITY_MISMATCH"
REFUSED_PERIOD_WITNESS = a10.REFUSED_PERIOD_WITNESS
REFUSED_RESTRUCTURE = a10.REFUSED_RESTRUCTURE
REFUSED_DANGLING = "REFUSED_CAREER_SUCCESSOR_DANGLING_REFERENCE"
REFUSED_A04_ANCHOR = a10.REFUSED_A04_ANCHOR
SERVED = a10.SERVED
GENUINE_ROWS = a10.GENUINE_ROWS
VERIFIER_V7 = "BAS-C37A11-CAREER-SUCCESSOR-VERIFIER-v7"
#: What the v7 verifier must reproduce over the genuine files (measured at development, before any lane): every row of
#: every relation read again from its source unit; rows with no interval text only where the source states none; every
#: restructure claim qualified by its source; every NOT_PRODUCED claim proved; every field unit held.
GENUINE_SOURCE_INTERVALS = {
    "A05": {"relation": "successor", "rows_read_again_from_source": 72958, "rows_stating_no_interval_text": 348,
            "rows_whose_source_row_states_no_interval": 348, "fields": 72808, "multi_interval_fields": 142,
            "rows_in_multi_interval_fields": 292},
    "A05<-A4": {"relation": "Attempt 4 file", "rows_read_again_from_source": 72764, "rows_stating_no_interval_text": 367,
                "rows_whose_source_row_states_no_interval": 367, "fields": 72621, "multi_interval_fields": 136,
                "rows_in_multi_interval_fields": 279},
    "A04": {"relation": "successor", "rows_read_again_from_source": 73082, "rows_stating_no_interval_text": 370,
            "rows_whose_source_row_states_no_interval": 370, "fields": 72938, "multi_interval_fields": 137,
            "rows_in_multi_interval_fields": 281},
}
GENUINE_NOT_PRODUCED = {"A05": {"relation": "delivered predecessor", "not_produced_claims": 295, "claims_proved": 295},
                        "A05<-A4": {"relation": "Attempt 4 file", "not_produced_claims": 318, "claims_proved": 318},
                        "A04": {"relation": "delivered predecessor", "not_produced_claims": 0, "claims_proved": 0}}
GENUINE_COMPLETENESS = {"relation": "successor", "captures": 7950, "source_fields": 72808, "source_fields_held": 72808}
GENUINE_RESTRUCTURES = {"A5<-default": 233, "A5<-A4": 5, "A4<-default": 228}


def rebind() -> None:
    """Point the preserved runners at the Attempt 11 contract, roots, ledger, suites, tools and grants."""

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
                        ("CANDIDATE_SUITES", CANDIDATE_SUITES), ("candidate", candidate),
                        # The manager's saved Attempt 9 interval fixture is read in place (the consumer attaches a
                        # successor read-only and immutable); its folder is guarded, so nothing can be written there.
                        ("SAVED_INTERVAL_COPY", a10.MANAGER_A9_INTERVAL)):
        setattr(a10, name, value)
    a10.rebind()
    base.CYCLE_ID = CYCLE_ID
    # Attempt 10's own roots are now denied writes: guarded like every earlier attempt's. The manager's saved Attempt 10
    # fixture folder is manager-owned and immutable: read (and copied from) only, so it is guarded too.
    base.GUARDED_ROOTS = tuple(dict.fromkeys(base.GUARDED_ROOTS + (VALIDATION_A10, PACKAGING_A10,
                                                                   Path(MANAGER_A10_FIXTURE_LITERAL))))
    attempt09_git.install()


LaneRun = a10.LaneRun
_json_file = a10._json_file
_refusal = a10._refusal


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
        problems.append("contract is not Cycle 37 Attempt 11")
    if contract.get("attempt_id") != ATTEMPT_ID:
        problems.append(f"contract attempt_id {contract.get('attempt_id')!r} is not {ATTEMPT_ID}")
    if (contract.get("repo") or {}).get("base_sha") != BASE_SHA:
        problems.append(f"contract base {(contract.get('repo') or {}).get('base_sha')} is not {BASE_SHA}")
    row = {r["id"]: r for r in contract.get("required_lanes", [])}.get(lane)
    if row is None or row.get("executor") != "worker":
        problems.append(f"{lane} is not a worker lane of this contract")
    elif f"attempt11_lanes.py --lane {lane} " not in row.get("command", ""):
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
        "rebound_attempt10_runner_sha256": sha256_file(Path(a10.__file__).resolve()),
        "a11_interval_oracle_tool_sha256": sha256_file(INTERVAL_ORACLE_TOOL),
        "a10_interval_oracle_tool_sha256": sha256_file(here / "a10_interval_oracle.py"),
        "a09_oracle_tool_sha256": sha256_file(here / "a09_source_unit_oracle.py"),
        "git_wrapper_sha256": sha256_file(Path(attempt09_git.__file__).resolve()),
        "candidate_tool_sha256": sha256_file(Path(candidate.__file__).resolve()),
        "control07_tool_sha256": sha256_file(CONTROL_TOOL),
    })
    return binding


# ------------------------------------------------------------- context


def lane_start_context(run: LaneRun) -> None:
    a10.lane_start_context(run)
    reproduction = _json_file(BEFORE_REPRODUCTION) or {}
    saved = reproduction.get("saved_fixture") or {}
    run.extra["before_reproduction_attempt11"] = {
        "manager_original": saved.get("manager_original"), "working_copy": saved.get("working_copy"),
        "saved_fixture_is_the_managers": saved.get("sha256") == MANAGER_A10_FALSE_RESTRUCTURE_SHA256,
        "served_by_the_unfixed_base_at": {r.get("entrypoint"): {"exit": r.get("exit"), "rows": r.get("row_count"),
                                                                "refusal": r.get("refusal")}
                                          for r in saved.get("results") or []},
        "independent_source_cardinality": saved.get("independent_source_cardinality"),
        "retained_negatives_observed": reproduction.get("retained_negatives_observed"),
        "unchanged_inputs_match": reproduction.get("unchanged_inputs_match"),
        "drafts_before_reproduction": reproduction.get("drafts_before_reproduction")}
    entrypoints = run.extra["before_reproduction_attempt11"]["served_by_the_unfixed_base_at"]
    if not (run.extra["before_reproduction_attempt11"]["saved_fixture_is_the_managers"]
            and set(entrypoints) == {"installed_console_script", "installed_module", "source_module"}
            and all(v["exit"] == 0 and not v["refusal"] for v in entrypoints.values())
            and reproduction.get("unchanged_inputs_match")):
        run.problems.append("the before-repair reproduction does not show the saved false restructure served by the "
                            f"unfixed base at all three entrypoints: {entrypoints}")


# ------------------------------------------------------------- storage (preserved, run fresh, bound to Attempt 10)


STORAGE_DEPENDENCIES = ("tools/cycle37/storage_admission.py", "tools/cycle37/storage_snapshot.py")


def _attempt10_final(lane: str) -> dict[str, Any]:
    rows = [json.loads(line) for line in (ATTEMPT10_ROOT / "lanes" / "RUNS.jsonl").read_text(encoding="utf-8")
            .splitlines() if line.strip()]
    rows = [row for row in rows if row["lane"] == lane and row["head"] == BASE_SHA]
    if not rows:
        return {}
    path = Path(rows[-1]["receipt"])
    return {"receipt": str(path), "receipt_sha256": sha256_file(path), "run": rows[-1]["run"],
            "result": rows[-1]["result"], "data": json.loads(path.read_text(encoding="utf-8"))}


def lane_storage_admission(run: LaneRun) -> None:
    a10.lane_storage_admission(run)
    accepted = _attempt10_final("STORAGE_ADMISSION")
    files = {f"tests/{suite}.py" for suite in STORAGE_SUITES} | set(STORAGE_DEPENDENCIES)

    def blob(revision: str, path: str) -> str | None:
        shown = subprocess.run(attempt09_git.command("rev-parse", "--verify", "--quiet", f"{revision}:{path}",
                                                     repo=a6c.WORKTREE), capture_output=True, text=True, check=False)
        return shown.stdout.strip() or None

    head = run.binding["head"]
    dependencies = {path: {"attempt10_final": blob(BASE_SHA, path), "head": blob(head, path)} for path in sorted(files)}
    verdict = {"attempt10_final_receipt": accepted.get("receipt"), "attempt10_final_receipt_sha256":
               accepted.get("receipt_sha256"), "attempt10_final_run": accepted.get("run"),
               "attempt10_final_result": accepted.get("result"), "attempt10_final_head": BASE_SHA,
               "dependencies": dependencies,
               "unchanged": all(v["head"] and v["head"] == v["attempt10_final"] for v in dependencies.values()),
               "attempt10_ledgers_retained": {
                   p.name: sha256_file(p) for p in sorted((ATTEMPT10_ROOT / "evidence" / "storage").glob("*.jsonl"))
                   + [ATTEMPT10_ROOT / "STORAGE_RESERVATIONS.jsonl", ATTEMPT10_ROOT / "STORAGE_EVIDENCE_SNAPSHOT.json"]
                   if p.is_file()},
               "meaning": ("The storage tools and the storage suites at this head are the exact blobs the Attempt 10 "
                           "final STORAGE_ADMISSION receipt qualified at c2f82759 (and its manager accepted); Attempt 11 "
                           "changes none of them. The suites and both saved manager challenges run fresh here anyway. "
                           "The Attempt 10 ledgers are closed history, hashed here only as retained.")}
    verdict["holds"] = accepted.get("result") == PASS and verdict["unchanged"]
    run.extra["storage_dependencies_equal_to_attempt10_accepted"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the storage dependencies are not the Attempt 10 qualified bytes: "
                            f"{ {k: v for k, v in verdict.items() if k != 'meaning'} }")


# ------------------------------------------------------------- the new suite on the unfixed base


#: The Attempt 11 suite's new negative cases: every one must fail over the unfixed base's bytes.
NEGATIVE_TESTS = {
    "test_cycle37_a11_restructure_lineage": (
        "test_the_managers_count_changing_collapse_is_refused_whatever_period_the_remaining_row_states",
        "test_an_expansion_past_the_source_count_is_refused",
        "test_a_fabricated_ordinal_in_a_genuinely_restructured_field_is_refused",
        "test_a_restructured_merge_expanded_past_its_source_is_refused",
        "test_a_restructured_split_collapsed_and_relabelled_an_ordinary_field_is_refused",
        "test_a_forged_period_on_every_formerly_exempt_branch_is_refused",
        "test_a_forged_period_in_the_declared_attempt4_file_is_refused",
        "test_a_partial_restructure_that_leaves_a_reread_row_unclaimed_is_refused",
        "test_the_attempt4_format_collapse_expansion_and_forgery_are_refused",
        "test_the_source_interval_check_on_its_own", "test_the_restructure_qualification_on_its_own"),
}
#: Retained negatives: refused under the earlier rules too; recorded, never required to fail on the base.
RETAINED_NEGATIVE_TESTS = {"test_cycle37_a11_restructure_lineage": (
    "test_a_count_preserving_false_restructure_stays_refused", "test_a_collapse_claimed_in_one_relation_only_stays_refused",
    "test_a_forged_period_on_a_row_its_unrestructured_attempt4_edge_reaches_stays_refused")}
SAVED_CONSTRUCTION = ("test_cycle37_a11_restructure_lineage::"
                      "test_the_managers_count_changing_collapse_is_refused_whatever_period_the_remaining_row_states"
                      "[period='genuine']")


def _suite_on_the_unfixed_base(run: LaneRun) -> dict[str, Any]:
    folder = run.fresh("unfixed_base")
    archive = subprocess.run(attempt09_git.command("archive", "--format=tar", BASE_SHA, "src", "tests", "tools",
                                                   repo=a6c.WORKTREE), capture_output=True, check=False)
    if archive.returncode != 0:
        return {"holds": False, "problem": f"git archive of the issued base failed: {archive.stderr[-400:]!r}"}
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as bundle:
        bundle.extractall(folder, filter="data")
    copied = {}
    for suite in A11_SUITES:
        source = a6c.WORKTREE / "tests" / f"{suite}.py"
        (folder / "tests" / f"{suite}.py").write_bytes(source.read_bytes())
        copied[suite] = sha256_file(source)
    record = run.run("attempt11_suite_on_the_unfixed_base",
                     [run.python, "-B", "-m", "unittest", "-v", *(f"tests.{s}" for s in A11_SUITES)], cwd=folder,
                     env=run.env(pythonpath=None), expect_exit=1, timeout=1800,
                     note="The new suite over a git archive of the issued base c2f82759; every new negative case must "
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
               "meaning": ("Over the unfixed base every new negative case fails: the saved construction (the manager's "
                           "count-changing collapse with the remaining row's genuine period) and its forged, blank, "
                           "enlarged and parent-copied variants, the expansion with and without a fabricated interval, "
                           "the fabricated ordinal, the restructured merge expanded past its source, the restructured "
                           "split collapsed and relabelled ordinary, forged periods on every formerly exempt branch, "
                           "the forged period in the declared Attempt 4 file, the partial restructure and the Attempt 4 "
                           "format are all served there; the new source-interval check does not exist there, and the "
                           "restructure qualification accepts a claim there that the source does not support. Retained "
                           "negatives (the count-preserving false restructure, the one-relation collapse, the forged "
                           "period an unrestructured Attempt 4 edge reaches) are refused on both; positive cases (the "
                           "genuine fixture, the Attempt 4 format, blank text and unstated dates, the fixture left "
                           "attachable) may pass or fail there and are recorded.")}
    verdict["holds"] = (record.get("exit_code") not in (0, None) and not passing_negatives and not verdict["unclassified"]
                        and not verdict["negative_tests_missing"]
                        and verdict["saved_construction"]["class"] == a9.ACCEPTED)
    return verdict


def lane_source_regressions(run: LaneRun) -> None:
    a7.lane_source_regressions(run)
    verdict = _suite_on_the_unfixed_base(run)
    run.extra["attempt11_suite_on_the_unfixed_base"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the Attempt 11 suite does not show the defect on the unfixed base: "
                            f"{ {k: verdict.get(k) for k in ('exit', 'negative_cases_passing_on_the_base', 'unclassified', 'negative_tests_missing', 'saved_construction', 'problem')} }")


# ------------------------------------------------------------- the career successor (MF37A10-01)


def _a11_oracle(run: LaneRun, label: str, successor: Path, a04: Path) -> dict[str, Any]:
    out = run.run_dir / f"ORACLE_A11_{label}.json"
    run.run(f"independent_cardinality_oracle_{label}",
            [run.python, "-B", INTERVAL_ORACLE_TOOL, "--successor", successor, "--a04", a04, "--database",
             DELIVERED_DB, "--out", out, "--label", label, "--known-anomalies", KNOWN_ANOMALIES],
            env=run.env(pythonpath=None), timeout=3600,
            note="The independent source-cardinality oracle: stdlib and the Attempt 8 raw-structure reader only, no "
                 "project module and no restructure exemption.")
    document = _json_file(out) or {}
    document["receipt"] = {"path": str(out), "sha256": sha256_file(out) if out.is_file() else None}
    return document


def _oracle_summary(document: dict[str, Any]) -> dict[str, Any]:
    return {k: document.get(k) for k in ("oracle_version", "format", "parser_splitting", "successor_sha256", "rows",
                                         "fields", "captures_read", "field_classes", "invalid_fields",
                                         "unresolved_fields", "invalid_field_examples", "named_anomalies",
                                         "multi_interval_fields", "rows_in_multi_interval_fields",
                                         "invalid_relation_verdicts", "completeness", "missing_periods",
                                         "invalid_total", "limits", "receipt")} | {
        "known_anomaly_comparison_equal": (document.get("known_anomaly_comparison") or {}).get("equal"),
        "relations": [{k: r.get(k) for k in ("relation", "counts", "invalid", "examples")}
                      for r in document.get("relations") or []]}


def _camp_field_invalid(document: dict[str, Any]) -> bool:
    return any(row.get("entry", [None])[0] == "176858" and str(row.get("class", "")).startswith("INVALID")
               for row in document.get("invalid_field_examples") or [])


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

    def qualified(counts: dict[str, Any], claims: int) -> bool:
        return counts.get("restructured_entries") == claims and counts.get("restructure_claims_qualified") == claims

    checks = {
        "verifier_is_v7": bindings.get("verifier_version") == VERIFIER_V7,
        "a05_every_successor_row_resolves_to_its_witnessed_unit": resolved(witnessed.get("successor") or {},
                                                                            GENUINE_ROWS["A05"]),
        "a05_every_named_delivered_row_resolves": resolved(witnessed.get("delivered_predecessor") or {},
                                                           a10.NAMED_PARENTS["delivered"]),
        "a05_every_named_attempt4_row_resolves": resolved(a04_witnessed, a10.NAMED_PARENTS["attempt4"]),
        "a04_format_every_row_resolves": resolved(older_witnessed.get("successor") or {}, GENUINE_ROWS["A04"]),
        "a05_default_edges_anchored_on_derived_units": anchored(default, a10.GENUINE_EDGES["A5<-default"]),
        "a05_a04_edges_anchored_on_derived_units": anchored(cross, a10.GENUINE_EDGES["A5<-A4"]),
        "a04_default_edges_anchored_on_derived_units": anchored(older, a10.GENUINE_EDGES["A4<-default"]),
        "a05_default_interval_edges_bound_by_identity_and_source": interval_bound(
            default, a10.GENUINE_INTERVAL_EDGES["A5<-default"]),
        "a05_a04_interval_edges_bound_by_identity_and_source": interval_bound(cross, a10.GENUINE_INTERVAL_EDGES["A5<-A4"]),
        "a04_format_interval_edges_bound_by_identity_and_source": interval_bound(
            older, a10.GENUINE_INTERVAL_EDGES["A4<-default"]),
        # MF37A10-01: every row of every relation read again from its source, whatever its disposition.
        "a05_every_successor_row_read_again_from_its_source": a05.get("source_intervals_proved")
        == GENUINE_SOURCE_INTERVALS["A05"],
        "a05_every_named_attempt4_row_read_again_from_its_source": a05.get("a04_source_intervals_proved")
        == GENUINE_SOURCE_INTERVALS["A05<-A4"],
        "a04_format_every_row_read_again_from_its_source": a04.get("source_intervals_proved")
        == GENUINE_SOURCE_INTERVALS["A04"],
        "a05_every_restructure_claim_qualified_by_its_source": qualified(default, GENUINE_RESTRUCTURES["A5<-default"]),
        "a05_every_attempt4_restructure_claim_qualified_by_its_source": qualified(cross, GENUINE_RESTRUCTURES["A5<-A4"]),
        "a04_format_every_restructure_claim_qualified_by_its_source": qualified(older,
                                                                                GENUINE_RESTRUCTURES["A4<-default"]),
        "a05_every_not_produced_claim_proved": a05.get("not_produced_claims_proved") == GENUINE_NOT_PRODUCED["A05"],
        "a05_every_attempt4_not_produced_claim_proved": a05.get("a04_not_produced_claims_proved")
        == GENUINE_NOT_PRODUCED["A05<-A4"],
        "a04_format_not_produced_claims": a04.get("not_produced_claims_proved") == GENUINE_NOT_PRODUCED["A04"],
        "a05_every_source_field_held": a05.get("source_completeness_proved") == GENUINE_COMPLETENESS,
        "captures_read_at_attach": a05.get("source_captures_read_at_attach") == 7950,
    }
    run.extra["source_interval_checks"] = {
        "checks": checks, "expected": {"source_intervals": GENUINE_SOURCE_INTERVALS, "not_produced": GENUINE_NOT_PRODUCED,
                                       "completeness": GENUINE_COMPLETENESS, "restructures": GENUINE_RESTRUCTURES},
        "observed": {"A05": {k: a05.get(k) for k in ("source_intervals_proved", "a04_source_intervals_proved",
                                                     "not_produced_claims_proved", "a04_not_produced_claims_proved",
                                                     "source_completeness_proved")},
                     "A04": {k: a04.get(k) for k in ("source_intervals_proved", "not_produced_claims_proved")},
                     "anchors": {"A5<-default": default, "A5<-A4": cross, "A4<-default": older}}}
    for name, held in checks.items():
        if not held:
            run.problems.append(f"source interval binding: {name} does not hold")
    # The Attempt 8 source-field, Attempt 9 identity-derived and Attempt 10 interval oracles, kept.
    genuine8 = a8._oracle(run, "genuine", A5_SUCCESSOR, A4_SUCCESSOR)
    genuine9 = a9._a09_oracle(run, "genuine", A5_SUCCESSOR, A4_SUCCESSOR)
    genuine10 = a10._a10_oracle(run, "genuine", A5_SUCCESSOR, A4_SUCCESSOR)
    kept = {"a08_genuine_crossed": genuine8.get("crossed_edges"), "a08_genuine_unresolved": genuine8.get("unresolved"),
            "a09_genuine_crossed": genuine9.get("crossed_edges"), "a09_genuine_unresolved": genuine9.get("unresolved_edges"),
            "a10_genuine_invalid": genuine10.get("invalid_edges"),
            "receipts": {"a08": genuine8.get("receipt"), "a09": genuine9.get("receipt"), "a10": genuine10.get("receipt")}}
    kept["holds"] = (genuine8.get("crossed_edges") == 0 and all(not v for v in (genuine8.get("unresolved") or {}).values())
                     and genuine9.get("crossed_edges") == 0 and genuine9.get("unresolved_edges") == 0
                     and genuine10.get("invalid_edges") == 0)
    run.extra["earlier_oracles_kept"] = kept
    if not kept["holds"]:
        run.problems.append(f"the Attempt 8, 9 or 10 oracle no longer holds over the genuine files: {kept}")
    # The Attempt 11 independent source-cardinality oracle: the genuine files and both saved manager fixtures.
    genuine5 = _a11_oracle(run, "genuine_a05", A5_SUCCESSOR, A4_SUCCESSOR)
    genuine4 = _a11_oracle(run, "genuine_a04", A4_SUCCESSOR, A4_SUCCESSOR)
    saved_ok = (SAVED_FALSE_RESTRUCTURE_COPY.is_file()
                and sha256_file(SAVED_FALSE_RESTRUCTURE_COPY) == MANAGER_A10_FALSE_RESTRUCTURE_SHA256)
    saved = _a11_oracle(run, "manager_a10_false_restructure", SAVED_FALSE_RESTRUCTURE_COPY, A4_SUCCESSOR) if saved_ok \
        else {}
    interval_ok = a10.MANAGER_A9_INTERVAL.is_file() and sha256_file(a10.MANAGER_A9_INTERVAL) == \
        a10.MANAGER_A9_INTERVAL_SHA256
    crossed = _a11_oracle(run, "manager_a9_interval", a10.MANAGER_A9_INTERVAL, A4_SUCCESSOR) if interval_ok else {}
    verdict = {"genuine_a05": _oracle_summary(genuine5), "genuine_a04": _oracle_summary(genuine4),
               "manager_a10_false_restructure": {"fixture": str(SAVED_FALSE_RESTRUCTURE_COPY),
                                                 "manager_original": str(MANAGER_A10_FALSE_RESTRUCTURE),
                                                 "sha256_as_issued": saved_ok, **_oracle_summary(saved)},
               "manager_a9_interval": {"fixture": str(a10.MANAGER_A9_INTERVAL), "sha256_as_issued": interval_ok,
                                       **_oracle_summary(crossed)}}
    genuine5_checks = {
        "rows": genuine5.get("rows") == {"successor": GENUINE_ROWS["A05"], "default": GENUINE_ROWS["default"]},
        "captures": genuine5.get("captures_read") == 7950, "no_invalid": genuine5.get("invalid_total") == 0,
        "multi_interval_groups": (genuine5.get("multi_interval_fields"), genuine5.get("rows_in_multi_interval_fields"))
        == (142, 292),
        "named_anomalies_are_the_managers_seven": len(genuine5.get("named_anomalies") or []) == 7
        and (genuine5.get("known_anomaly_comparison") or {}).get("equal") is True,
        "every_field_unit_held": (genuine5.get("completeness") or {}).get("units_stating_a_period_not_held") == 0}
    verdict["checks"] = {
        "genuine_a05": genuine5_checks,
        "genuine_a04_no_invalid": genuine4.get("invalid_total") == 0 and genuine4.get("rows", {}).get("successor")
        == GENUINE_ROWS["A04"],
        "manager_a10_false_restructure_invalid": saved_ok and int(saved.get("invalid_total") or 0) > 0
        and _camp_field_invalid(saved),
        "manager_a9_interval_invalid": interval_ok and int(crossed.get("invalid_total") or 0) > 0}
    verdict["holds"] = all(genuine5_checks.values()) and all(v for k, v in verdict["checks"].items() if k != "genuine_a05")
    run.extra["independent_cardinality_oracle"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the independent source-cardinality oracle does not hold: {verdict['checks']}")


# ------------------------------------------------------------- the installed consumer (MF37A10-01)


RESTRUCTURED = "RESTRUCTURED_INTERVALS"
NOT_PRODUCED = "NOT_PRODUCED_BY_THE_SUCCESSOR_PARSER"
FORGED = {"years_as_written": "1800\u20132099", "start": 1800, "end": 2099, "definite_first_season": 1800,
          "definite_last_season": 2099}


def _table(fmt: str) -> str:
    return "career_episode_a05" if fmt == "A05" else "career_episode_a04"


def _field(c: sqlite3.Connection, fmt: str, person: str, family: str, index: int) -> list[dict[str, Any]]:
    return [dict(r) for r in c.execute(f"SELECT * FROM {_table(fmt)} WHERE person_display=? AND family=? AND "
                                       "row_index=? ORDER BY interval_index", (person, family, index))]


def _update(c: sqlite3.Connection, table: str, episode: str, **changes: Any) -> None:
    c.execute(f"UPDATE {table} SET " + ", ".join(f'"{k}"=?' for k in changes) + " WHERE episode_id=?",
              (*changes.values(), episode))


def _insert_copy(c: sqlite3.Connection, table: str, row: dict[str, Any], **changes: Any) -> str:
    new = {**row, **changes}
    columns = list(new)
    c.execute(f"INSERT INTO {table} (" + ",".join(f'"{k}"' for k in columns) + ") VALUES ("
              + ",".join("?" for _ in columns) + ")", [new[k] for k in columns])
    return new["episode_id"]


def _parents(rows: list[dict[str, Any]], key: str = "predecessor_episode_ids") -> list[str]:
    return sorted({p for r in rows for p in json.loads(r.get(key) or "[]")})


def _claim(c: sqlite3.Connection, fmt: str, targets: list[str], parents: list[str], a4_parents: list[str] | None,
           state: str) -> None:
    """Every target claims every parent, and every parent names every target -- reciprocal in both relations."""

    dispositions = "career_a05_disposition" if fmt == "A05" else "career_a04_disposition"
    for target in targets:
        changes: dict[str, Any] = {"predecessor_episode_ids": json.dumps(parents), "disposition": state}
        if a4_parents is not None:
            changes.update(a04_episode_ids=json.dumps(a4_parents), a04_disposition=state)
        _update(c, _table(fmt), target, **changes)
    for parent in parents:
        c.execute(f"UPDATE {dispositions} SET successor_episode_ids=?, disposition=? WHERE predecessor_episode_id=?",
                  (json.dumps(sorted(targets)), state, parent))
    for parent in a4_parents or ():
        c.execute("UPDATE career_a05_from_a04 SET a05_episode_ids=?, disposition=? WHERE a04_episode_id=?",
                  (json.dumps(sorted(targets)), state, parent))


def _collapse(fmt: str, period: str = "genuine") -> Callable[[sqlite3.Connection], dict[str, Any]]:
    """The manager's recipe: Walter Camp's second Stanford interval removed, both parents claimed by the remaining row
    as a re-read (RESTRUCTURED_INTERVALS) field, reciprocal in both relations; the remaining row's period as given."""

    def build(c: sqlite3.Connection) -> dict[str, Any]:
        rows = _field(c, fmt, CAMP, "COACHING", 2)
        keep, drop = rows[0], rows[1:]
        parents = _parents(rows)
        a4 = _parents(rows, "a04_episode_ids") if fmt == "A05" else None
        for row in drop:
            c.execute(f"DELETE FROM {_table(fmt)} WHERE episode_id=?", (row["episode_id"],))
        _claim(c, fmt, [keep["episode_id"]], parents, a4, RESTRUCTURED)
        other = rows[1]
        stated = {"genuine": {}, "forged": FORGED, "blank": {"years_as_written": None},
                  "enlarged": {"years_as_written": "1892, 1894\u20131895"},
                  "parent-copied": {k: other[k] for k in ("years_as_written", "start", "end", "definite_first_season",
                                                          "definite_last_season")}}[period]
        if stated:
            _update(c, _table(fmt), keep["episode_id"], **stated)
        return {"kept": keep["episode_id"], "removed": [r["episode_id"] for r in drop], "claimed_parents": parents,
                "claimed_a04_parents": a4, "period": period, "stated": stated}
    return build


def _expand(fmt: str, *, fabricated: bool = False, person: str = CAMP, family: str = "COACHING", index: int = 2,
            extra: int = 1) -> Callable[[sqlite3.Connection], dict[str, Any]]:
    """Rows added to the field under fabricated interval ordinals; every row claims every parent as a re-read field,
    reciprocal in both relations."""

    def build(c: sqlite3.Connection) -> dict[str, Any]:
        rows = _field(c, fmt, person, family, index)
        parents = _parents(rows)
        a4 = _parents(rows, "a04_episode_ids") if fmt == "A05" else None
        added = []
        for k in range(extra):
            ordinal = len(rows) + k
            changes: dict[str, Any] = {"episode_id": f"{rows[-1]['episode_id'].rsplit(':', 1)[0]}:{ordinal}",
                                       "interval_index": ordinal}
            if fabricated:
                changes.update(years_as_written=str(1896 + k), start=1896 + k, end=1896 + k,
                               definite_first_season=1896 + k, definite_last_season=1896 + k)
            added.append(_insert_copy(c, _table(fmt), rows[-1], **changes))
        _claim(c, fmt, [r["episode_id"] for r in rows] + added, parents, a4, RESTRUCTURED)
        return {"added": added, "claimed_parents": parents, "claimed_a04_parents": a4, "fabricated_period": fabricated}
    return build


def _forge(fmt: str, person: str, family: str, index: int, ordinal: int = 0
           ) -> Callable[[sqlite3.Connection], dict[str, Any]]:
    """The row's stated period forged; its edges and its field left genuine."""

    def build(c: sqlite3.Connection) -> dict[str, Any]:
        rows = _field(c, fmt, person, family, index)
        row = rows[ordinal]
        _update(c, _table(fmt), row["episode_id"], **FORGED)
        return {"row": row["episode_id"], "genuine": {k: row[k] for k in FORGED}, "stated": FORGED,
                "disposition": row["disposition"], "entry_rows": len(rows)}
    return build


def _blank(fmt: str, person: str, family: str, index: int) -> Callable[[sqlite3.Connection], dict[str, Any]]:
    def build(c: sqlite3.Connection) -> dict[str, Any]:
        rows = _field(c, fmt, person, family, index)
        for row in rows:
            _update(c, _table(fmt), row["episode_id"], years_as_written=None)
        return {"rows": [r["episode_id"] for r in rows], "unstated": ["years_as_written"]}
    return build


def _collapse_unclaimed(c: sqlite3.Connection) -> dict[str, Any]:
    """Walter Camp's second interval removed with its parents left NOT_PRODUCED: a count change with no claim."""

    keep, drop = _field(c, "A05", CAMP, "COACHING", 2)
    c.execute("DELETE FROM career_episode_a05 WHERE episode_id=?", (drop["episode_id"],))
    for key, table, column, target in (("predecessor_episode_ids", "career_a05_disposition", "predecessor_episode_id",
                                        "successor_episode_ids"),
                                       ("a04_episode_ids", "career_a05_from_a04", "a04_episode_id", "a05_episode_ids")):
        for parent in json.loads(drop[key]):
            c.execute(f"UPDATE {table} SET {target}='[]', disposition=? WHERE {column}=?", (NOT_PRODUCED, parent))
    return {"kept": keep["episode_id"], "removed": drop["episode_id"], "claim": "none (parents left NOT_PRODUCED)"}


def _split_collapsed(state: str) -> Callable[[sqlite3.Connection], dict[str, Any]]:
    """Cedric Scott's genuinely restructured split (one delivered row, two v37.5 intervals) collapsed to its first
    interval and claimed under ``state`` in both relations."""

    def build(c: sqlite3.Connection) -> dict[str, Any]:
        rows = _field(c, "A05", "Cedric Scott", "PLAYING", 1002)
        keep, drop = rows
        c.execute("DELETE FROM career_episode_a05 WHERE episode_id=?", (drop["episode_id"],))
        _claim(c, "A05", [keep["episode_id"]], _parents(rows), _parents(rows, "a04_episode_ids"), state)
        return {"kept": keep["episode_id"], "removed": drop["episode_id"], "claimed_as": state}
    return build


def _count_preserving_false_restructure(c: sqlite3.Connection) -> dict[str, Any]:
    rows = _field(c, "A05", CAMP, "COACHING", 2)
    _claim(c, "A05", [r["episode_id"] for r in rows], _parents(rows), _parents(rows, "a04_episode_ids"), RESTRUCTURED)
    for row in rows:
        _update(c, "career_episode_a05", row["episode_id"], years_as_written=None)
    return {"rows": [r["episode_id"] for r in rows], "claim": "all-to-all with the count unchanged, blank text"}


def _one_sided_collapse(c: sqlite3.Connection) -> dict[str, Any]:
    """The collapse stated by the remaining row only: its parents' dispositions still name the removed row."""

    rows = _field(c, "A05", CAMP, "COACHING", 2)
    keep, drop = rows
    c.execute("DELETE FROM career_episode_a05 WHERE episode_id=?", (drop["episode_id"],))
    _update(c, "career_episode_a05", keep["episode_id"], predecessor_episode_ids=json.dumps(_parents(rows)),
            a04_episode_ids=json.dumps(_parents(rows, "a04_episode_ids")), disposition=RESTRUCTURED,
            a04_disposition=RESTRUCTURED)
    return {"kept": keep["episode_id"], "removed": drop["episode_id"], "dispositions": "left naming the removed row"}


#: What each refusal must say, not only its code: the cardinality census names rows that are not one of the intervals
#: their source states; the period census names rows stating an interval that is not theirs; the restructure rule
#: names its anchor.
CARDINALITY_CAUSE = "not one of the intervals their verified source field states"
PERIOD_WITNESS_CAUSE = "state an interval that is not the one"
RESTRUCTURE_CAUSE = "fail the RESTRUCTURE anchor"


Builder = Callable[[sqlite3.Connection], dict[str, Any]]
#: (name, kind, format, builder or None for the genuine file, person, expected refusal code or SERVED, the cause the
#: output must name). POSITIVE cases are genuine source-supported branches served; NEGATIVE cases are the new
#: MF37A10-01 constructions; RETAINED cases were refused under the earlier rules and must stay refused.
A11_CASES: list[tuple[str, str, str, Builder | None, str, str, str]] = [
    ("a05_genuine_multi_interval_walter_camp", "POSITIVE", "A05", None, CAMP, SERVED, ""),
    ("a05_genuine_restructured_split_cedric_scott", "POSITIVE", "A05", None, "Cedric Scott", SERVED, ""),
    ("a05_genuine_restructured_merge_douglas_hunt", "POSITIVE", "A05", None, "Douglas I. Hunt", SERVED, ""),
    ("a05_genuine_restructured_merge_wally_cruice", "POSITIVE", "A05", None, "Wally Cruice", SERVED, ""),
    ("a05_genuine_role_line_split_harold_smith", "POSITIVE", "A05", None, "Harold Smith", SERVED, ""),
    ("a05_genuine_added_row_les_dye", "POSITIVE", "A05", None, "Les Dye", SERVED, ""),
    ("a05_genuine_corrected_jim_mcdonald", "POSITIVE", "A05", None, "Jim McDonald", SERVED, ""),
    ("a05_genuine_blank_period_charles_buell", "POSITIVE", "A05", None, "Charles Buell", SERVED, ""),
    ("a04_genuine_multi_interval_walter_camp", "POSITIVE", "A04", None, CAMP, SERVED, ""),
    ("a05_genuine_edges_blank_period_multi", "POSITIVE", "A05", _blank("A05", CAMP, "COACHING", 2), CAMP, SERVED, ""),
    ("a05_genuine_edges_blank_period_restructured", "POSITIVE", "A05", _blank("A05", "Cedric Scott", "PLAYING", 1002),
     "Cedric Scott", SERVED, ""),
    ("a05_collapse_two_to_one", "NEGATIVE", "A05", _collapse("A05"), CAMP, REFUSED_CARDINALITY, CARDINALITY_CAUSE),
    ("a05_collapse_forged_period", "NEGATIVE", "A05", _collapse("A05", "forged"), CAMP, REFUSED_CARDINALITY,
     CARDINALITY_CAUSE),
    ("a05_collapse_blank_period", "NEGATIVE", "A05", _collapse("A05", "blank"), CAMP, REFUSED_CARDINALITY,
     CARDINALITY_CAUSE),
    ("a05_collapse_enlarged_period", "NEGATIVE", "A05", _collapse("A05", "enlarged"), CAMP, REFUSED_CARDINALITY,
     CARDINALITY_CAUSE),
    ("a05_collapse_parent_copied_period", "NEGATIVE", "A05", _collapse("A05", "parent-copied"), CAMP,
     REFUSED_CARDINALITY, CARDINALITY_CAUSE),
    ("a05_expand_two_to_three", "NEGATIVE", "A05", _expand("A05"), CAMP, REFUSED_CARDINALITY, CARDINALITY_CAUSE),
    ("a05_expand_fabricated_interval", "NEGATIVE", "A05", _expand("A05", fabricated=True), CAMP, REFUSED_CARDINALITY,
     CARDINALITY_CAUSE),
    ("a05_restructured_merge_expanded_past_source", "NEGATIVE", "A05",
     _expand("A05", person="Douglas I. Hunt", family="COACHING", index=1, extra=2), "Douglas I. Hunt",
     REFUSED_CARDINALITY, CARDINALITY_CAUSE),
    ("a05_split_collapsed_relabelled_unchanged", "NEGATIVE", "A05", _split_collapsed("UNCHANGED"), "Cedric Scott",
     REFUSED_CARDINALITY, CARDINALITY_CAUSE),
    ("a05_ordinary_single_forged_period", "NEGATIVE", "A05", _forge("A05", CAMP, "COACHING", 1), CAMP,
     REFUSED_PERIOD_WITNESS, PERIOD_WITNESS_CAUSE),
    ("a05_added_row_forged_period", "NEGATIVE", "A05", _forge("A05", "Les Dye", "PLAYING", 2001), "Les Dye",
     REFUSED_PERIOD_WITNESS, PERIOD_WITNESS_CAUSE),
    ("a05_role_line_forged_period", "NEGATIVE", "A05", _forge("A05", "Harold Smith", "COACHING", 100101),
     "Harold Smith", REFUSED_PERIOD_WITNESS, PERIOD_WITNESS_CAUSE),
    ("a05_restructured_merge_forged_period", "NEGATIVE", "A05", _forge("A05", "Douglas I. Hunt", "COACHING", 1),
     "Douglas I. Hunt", REFUSED_PERIOD_WITNESS, PERIOD_WITNESS_CAUSE),
    ("a05_restructured_split_forged_period", "NEGATIVE", "A05", _forge("A05", "Cedric Scott", "PLAYING", 1002, 1),
     "Cedric Scott", REFUSED_PERIOD_WITNESS, PERIOD_WITNESS_CAUSE),
    ("a04_collapse_two_to_one", "NEGATIVE", "A04", _collapse("A04"), CAMP, REFUSED_CARDINALITY, CARDINALITY_CAUSE),
    ("a04_expand_two_to_three", "NEGATIVE", "A04", _expand("A04"), CAMP, REFUSED_CARDINALITY, CARDINALITY_CAUSE),
    ("a04_ordinary_single_forged_period", "NEGATIVE", "A04", _forge("A04", CAMP, "COACHING", 1), CAMP,
     REFUSED_PERIOD_WITNESS, PERIOD_WITNESS_CAUSE),
    ("a05_count_preserving_false_restructure", "RETAINED", "A05", _count_preserving_false_restructure, CAMP,
     REFUSED_RESTRUCTURE, RESTRUCTURE_CAUSE),
    ("a05_collapse_count_change_unclaimed", "RETAINED", "A05", _collapse_unclaimed, CAMP, REFUSED_RESTRUCTURE,
     RESTRUCTURE_CAUSE),
    ("a05_one_sided_collapse", "RETAINED", "A05", _one_sided_collapse, CAMP, REFUSED_DANGLING, ""),
    ("a05_restructured_split_collapsed_to_parent_count", "RETAINED", "A05", _split_collapsed(RESTRUCTURED),
     "Cedric Scott", REFUSED_RESTRUCTURE, RESTRUCTURE_CAUSE),
]


def _manager_a10_false_restructure(run: LaneRun, installed: dict[str, Any]) -> dict[str, Any]:
    """The manager's saved false-restructure fixture, byte for byte (the owned copy, never written), through all three
    entrypoints (the manager's FALSE_RESTRUCTURE_CHALLENGE commands)."""

    digest = sha256_file(SAVED_FALSE_RESTRUCTURE_COPY)
    args = ["--career", "--career-successor", SAVED_FALSE_RESTRUCTURE_COPY, "--career-successor-sha256", digest,
            "--person", CAMP, "--compact"]
    records = {"installed_console_script": base._cli(run, installed, "a11_manager_false_restructure_script", args,
                                                     expect_exit=1),
               "installed_module": a7._module_entrypoint(run, installed, "a11_manager_false_restructure_module", args,
                                                         expect_exit=1),
               "source_module": a8._source_module_entrypoint(run, installed, "a11_manager_false_restructure_source",
                                                             args, expect_exit=1)}
    texts = {k: Path(r["log_path"]).read_text(encoding="utf-8", errors="replace") for k, r in records.items()}
    refusals = {k: _refusal(t) for k, t in texts.items()}
    exits = {k: r.get("exit_code") for k, r in records.items()}
    verdict = {"fixture": str(SAVED_FALSE_RESTRUCTURE_COPY), "manager_original": str(MANAGER_A10_FALSE_RESTRUCTURE),
               "fixture_sha256": digest, "as_issued": digest == MANAGER_A10_FALSE_RESTRUCTURE_SHA256, "exits": exits,
               "refusals": refusals, "expected": REFUSED_CARDINALITY,
               "names_the_source_count": {k: "its source states 2 interval(s)" in t for k, t in texts.items()},
               "before_repair": "every entrypoint exited 0 serving three rows (evidence/before/BEFORE_REPRODUCTION.json)"}
    verdict["holds"] = verdict["as_issued"] and all(v == 1 for v in exits.values()) and all(
        v == REFUSED_CARDINALITY for v in refusals.values()) and all(verdict["names_the_source_count"].values())
    return verdict


def _a11_forgeries(run: LaneRun, installed: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {"fixtures": {"a05": str(LINEAGE_A05), "a04": str(LINEAGE_A04)}, "cases": {},
                               "rule": ("each case restores its fixture from the genuine file, builds its construction, "
                                        "reseals every ledger as a careful forger would, pins the digest and serves "
                                        "through the console script and the module entrypoint; a forgery must be refused "
                                        "for its own cause at both, a positive control served at both with every row "
                                        "of its field")}
    for name, kind, fmt, builder, person, expected, cause in A11_CASES:
        genuine = A5_SUCCESSOR if fmt == "A05" else A4_SUCCESSOR
        fixture = genuine
        details: dict[str, Any] = {"file": "the genuine successor, unchanged"}
        if builder is not None:
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
                "--limit", "200", "--compact"]
        exit_expected = 0 if expected == SERVED else 1
        script = base._cli(run, installed, f"a11_{name}", args, expect_exit=exit_expected)
        module = a7._module_entrypoint(run, installed, f"a11_{name}_module", args, expect_exit=exit_expected)
        texts = {entry: Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
                 for entry, record in (("script", script), ("module", module))}
        refusals = {entry: _refusal(text) for entry, text in texts.items()}
        row = {"kind": kind, "format": fmt, "person": person, "fixture": str(fixture), "fixture_sha256": digest,
               "details": details, "expected": expected, "cause": cause, "script_exit": script.get("exit_code"),
               "module_exit": module.get("exit_code"), "refusals": refusals}
        if expected == SERVED:
            served = {entry: (base._stdout_json(record) or {}).get("row_count")
                      for entry, record in (("script", script), ("module", module))}
            row.update(served_rows=served, holds=script.get("exit_code") == 0 and module.get("exit_code") == 0
                       and all(isinstance(v, int) and v > 0 for v in served.values()) and not any(refusals.values()))
        else:
            row.update(cause_named={k: cause in t for k, t in texts.items()},
                       holds=script.get("exit_code") == 1 and module.get("exit_code") == 1
                       and refusals["script"] == expected and refusals["module"] == expected
                       and all(cause in t for t in texts.values()))
        results["cases"][name] = row
        if not row["holds"]:
            run.problems.append(f"A11 case {name} did not hold at both entrypoints: {refusals}")
    for fixture, source in ((LINEAGE_A05, A5_SUCCESSOR), (LINEAGE_A04, A4_SUCCESSOR)):
        a6._restore(fixture, source)
    results["genuine_unchanged"] = (sha256_file(A5_SUCCESSOR) == A5_SUCCESSOR_SHA256
                                    and sha256_file(A4_SUCCESSOR) == A4_SUCCESSOR_SHA256)
    results["counts"] = {kind: sum(1 for row in results["cases"].values() if row["kind"] == kind)
                         for kind in ("POSITIVE", "NEGATIVE", "RETAINED")}
    results["holds"] = results["genuine_unchanged"] and all(row["holds"] for row in results["cases"].values())
    return results


def lane_installed_consumer_c01(run: LaneRun) -> None:
    a10.lane_installed_consumer_c01(run)
    raw = run.extra.get("installed")
    if not raw:
        return
    installed = {key: Path(value) for key, value in raw.items()}
    verdict = _manager_a10_false_restructure(run, installed)
    run.extra["manager_a10_false_restructure_entrypoints"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's saved false-restructure fixture is not refused for its cardinality cause at "
                            f"every entrypoint: {verdict}")
    run.extra["a11_cases"] = _a11_forgeries(run, installed)


# ------------------------------------------------------------- the local integration candidate (R37A11-03)


def _append_chain(head: str) -> dict[str, Any]:
    """Every Attempt 11 append continues the one before it, the first from the granted head ``cf992e4b``, the last
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


def _manager_committed_tree(folder: Path, label: str) -> Callable[[LaneRun, str], dict[str, Any]]:
    def probe(run: LaneRun, head: str) -> dict[str, Any]:
        copy, replay = a7._replay(run, folder, "committed_tree_review.py", f"mgr_{label}_committed_tree")
        record = run.run(f"manager_{label}_committed_tree_replay", [run.python, "-B", copy], cwd=copy.parent,
                         env=run.env(guarded=False, pythonpath=None),
                         note=f"The manager's saved {label} committed-byte provenance probe, byte-identical; it reads the "
                              "named candidate branch through this worktree's shared Git store.")
        review = _json_file(copy.parent / "COMMITTED_TREE_PROVENANCE.json") or {}
        verdict = {**replay, "exit": record.get("exit_code"), "head": review.get("head"), "paths": review.get("paths"),
                   "manifest_rows": review.get("manifest_rows"), "mismatches": review.get("mismatches"),
                   "hash_view_equal": review.get("hash_view_equal"), "tree_view_equal": review.get("tree_view_equal"),
                   "protected_same_as_main": [r.get("same_as_main") for r in review.get("protected") or []],
                   "original_candidate_ancestor": review.get("original_candidate_ancestor")}
        verdict["holds"] = (verdict["head"] == head and verdict["mismatches"] == []
                            and verdict["hash_view_equal"] is True and verdict["tree_view_equal"] is True
                            and all(verdict["protected_same_as_main"])
                            and verdict["original_candidate_ancestor"] is True)
        return verdict
    return probe


def lane_local_integration_candidate(run: LaneRun) -> None:
    a6.lane_local_integration_candidate(run)
    head = (run.extra.get("candidate") or {}).get("candidate_head")
    if not head:
        return
    description = candidate.describe()
    chain = _append_chain(head)
    run.extra["candidate_attempt11"] = {
        "appends_continue_cf992e4b_with_no_pack_written": chain["holds"],
        "cf992e4b_is_ancestor": description.get("attempt11_start_is_ancestor") is True,
        "514d74dc_is_ancestor": description.get("attempt10_start_is_ancestor") is True,
        "c52e7b52_is_ancestor": description.get("attempt9_start_is_ancestor") is True,
        "0c22af20_is_ancestor": description.get("attempt8_start_is_ancestor") is True,
        "bb5253b2_is_ancestor": description.get("attempt7_start_is_ancestor") is True,
        "preserved_first_candidate_is_ancestor": description.get("issued_head_is_ancestor") is True}
    run.extra["candidate_append_chain_attempt11"] = chain
    if not all(run.extra["candidate_attempt11"].values()):
        run.problems.append(f"the candidate does not continue the granted head: {run.extra['candidate_attempt11']}")
    if not run.rehearsal:
        for key, probe in (("manager_a10_committed_tree", _manager_committed_tree(MANAGER_A10, "a10")),
                           ("manager_a9_committed_tree", a10._manager_a9_committed_tree),
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


def lane_full_final_mounted(run: LaneRun) -> None:
    base.lane_full_final_mounted(run)
    record = next(r for r in reversed(run.commands) if r.get("lane", "").endswith("full_suite_mounted"))
    log = Path(record["log_path"])
    final = base._log_identities(log)
    previous = _attempt10_final("FULL_FINAL_MOUNTED")
    comparison: dict[str, Any] = {"attempt10_receipt": previous.get("receipt"),
                                  "attempt10_receipt_sha256": previous.get("receipt_sha256"),
                                  "attempt10_run": previous.get("run"), "attempt10_result": previous.get("result")}
    if not previous:
        run.problems.append("no Attempt 10 FULL_FINAL_MOUNTED receipt at the issued base to compare with")
    else:
        a10_log = Path(next(c["log_path"] for c in previous["data"]["commands"]
                            if c["lane"].endswith("full_suite_mounted")))
        before = base._log_identities(a10_log)
        persisting = sorted(set(final["failed_or_errored"]) & set(before["failed_or_errored"]))
        new = sorted(set(final["failed_or_errored"]) - set(before["failed_or_errored"]))
        final_causes = base._failure_causes(log, persisting)
        before_causes = base._failure_causes(a10_log, persisting)
        comparison.update({
            "attempt10_log": str(a10_log), "attempt10_log_sha256": sha256_file(a10_log),
            "attempt10_tests_run": before["tests_run"], "final_tests_run": final["tests_run"],
            "attempt10_failed_or_errored": before["failed_or_errored"], "persisting": persisting,
            "new_in_attempt11": new,
            "no_longer_failing": sorted(set(before["failed_or_errored"]) - set(final["failed_or_errored"])),
            "new_failure_causes": base._failure_causes(log, new),
            "persisting_same_cause": sorted(i for i in persisting if final_causes[i] == before_causes[i]),
            "persisting_changed_cause": {i: {"attempt10": before_causes[i], "attempt11": final_causes[i]}
                                         for i in persisting if final_causes[i] != before_causes[i]},
        })
        if new:
            run.problems.append(f"new failing identities relative to Attempt 10: {new}")
    run.extra["attempt10_comparison"] = comparison


def lane_strict_mounted(run: LaneRun) -> None:
    base.lane_strict_mounted(run)
    final = [row["identity"] for row in run.extra.get("strict_findings") or []]
    previous = _attempt10_final("STRICT_MOUNTED")
    comparison: dict[str, Any] = {"attempt10_receipt": previous.get("receipt"), "attempt10_run": previous.get("run"),
                                  "attempt10_result": previous.get("result")}
    if not previous:
        run.problems.append("no Attempt 10 STRICT_MOUNTED receipt at the issued base to compare with")
    else:
        before = [row["identity"] for row in (previous["data"].get("details") or {}).get("strict_findings") or []]
        comparison.update({"attempt10_findings": before, "final_findings": final,
                           "persisting": sorted(set(final) & set(before)),
                           "new_in_attempt11": sorted(set(final) - set(before)),
                           "no_longer_reported": sorted(set(before) - set(final))})
        if comparison["new_in_attempt11"]:
            run.problems.append(f"new strict findings relative to Attempt 10: {comparison['new_in_attempt11']}")
    run.extra["attempt10_comparison"] = comparison


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


_guard_events = a10._guard_events


def _reservation_for_check(args: argparse.Namespace, final_lane: bool, reservation: dict[str, Any] | None,
                           paths: dict[str, Path]) -> dict[str, Any] | None:
    """The reservation the FINAL_PACKET lane's ledger check must find open (MF37A11-01, W37A11-07).

    An issued run is admitted on the attempt's live ledger and that is the ledger the check reads, so the lane's own
    admitted reservation is the one. A rehearsal is charged to the live ledger as well (its window covers the tiny ledgers
    it makes) but its packet check reads those tiny ledgers (``a7.storage_paths``), so the tiny final-output ledger takes a
    mirror of the lane's reservation -- the same operation, a tiny estimate -- and the rehearsal exercises the same
    predicate on a real singleton reservation. The mirror lives only in the scratch ledger the rehearsal itself made."""

    if not (args.rehearsal and final_lane and reservation and paths):
        return reservation
    return storage.Ledger(paths["final_output_ledger"]).reserve(
        reservation["operation"], 1024, note="rehearsal mirror of the lane's reservation on the live ledger")


def main(argv: list[str] | None = None) -> int:
    rebind()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lane", required=True, choices=LANES)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--rehearsal", action="store_true",
                        help="Development only: write under the validation root, allow a dirty tree, spend no "
                             "request budget. A rehearsal receipt is labelled as such and is never evidence.")
    parser.add_argument("--continuation", action="store_true",
                        help="After the operational ledger is frozen, admit this lane on the attempt's one claimed "
                             "final-output continuation (same budget, roots and reserve; no new segment). Without it a "
                             "material lane is refused once the ledger is frozen.")
    args = parser.parse_args(argv)
    out_root = args.out_root.resolve()
    issued_root = out_root
    if args.rehearsal:
        out_root = VALIDATION_ROOT / "rehearsal"
    final_lane = args.lane == "FINAL_PACKET"
    # The ledger and the reservation come first: nothing of the lane (its run folder, its log) is written before the
    # lane's own window opens.
    contract, contract_problems = load_contract(args.contract.resolve(), args.lane, issued_root)
    binding = bind_source()
    blocked = list(contract_problems)
    if binding["branch"] != BRANCH:
        blocked.append(f"branch is {binding['branch']}, not {BRANCH}")
    if not binding["descends_from_base"]:
        blocked.append(f"head {binding['head']} does not descend from the issued base {BASE_SHA}")
    if not binding["clean"] and not args.rehearsal:
        blocked.append("the worktree is dirty; lanes run only at a committed subject")
    if FINAL_SNAPSHOT.is_file() and not final_lane and not args.continuation:
        blocked.append(f"the operational ledger is frozen by {FINAL_SNAPSHOT.name}; material lanes are refused "
                       "(--continuation admits one on the final-output continuation)")
    if args.continuation and not FINAL_SNAPSHOT.is_file():
        blocked.append("--continuation applies only after the operational ledger is frozen")
    if final_lane and not args.rehearsal and not (FINAL_SNAPSHOT.is_file() and FINAL_OUTPUT_LEDGER.is_file()):
        blocked.append("FINAL_PACKET runs only after the operational snapshot and the final-output ledger exist")
    gate = None
    if args.lane in GATED:
        gate = a5.qualification(out_root, binding["head"], binding["guard_sha256"])
        if not gate["holds"]:
            blocked.append("WRITE_PROTECTION and STORAGE_ADMISSION have not both passed at this head with these guard "
                           f"bytes: {gate}")
    # Every lane, a blocked one and a rehearsal included, is charged to the attempt's live ledger: the operational
    # ledger until it is frozen, the final-output continuation after. A FINAL_PACKET rehearsal's own tiny ledgers
    # (a7.storage_paths) are made inside this window.
    frozen = FINAL_SNAPSHOT.is_file()
    ledger_path = (FINAL_OUTPUT_LEDGER if FINAL_OUTPUT_LEDGER.is_file() else None) if frozen else OPERATIONAL_LEDGER
    ledger = storage.Ledger(ledger_path) if ledger_path else None
    reservation = None
    stamp_hint = utc_now()
    if ledger is None:
        blocked.append("no open ledger admits this lane's writes: the operational ledger is frozen and no final-output "
                       "continuation exists; the receipt below is written unadmitted")
    else:
        estimate = RECEIPT_ESTIMATE if blocked else LANE_ESTIMATES[args.lane]
        if args.lane == "INSTALLED_CONSUMER_C01" and not blocked:
            estimate += a6.missing_fixture_bytes()
        try:
            reservation = ledger.reserve(f"LANE {args.lane} {stamp_hint}" + (" (blocked before any effect)" if blocked
                                                                              else "")
                                         + (" (rehearsal)" if args.rehearsal else ""),
                                         estimate, note=f"head {binding['head']}")
        except storage.AdmissionRefused as refusal:
            blocked.append(f"storage admission refused the lane before any effect: {refusal.record.get('reason')}; "
                           "the receipt below is written unadmitted")
    paths = a7.storage_paths(out_root, args.rehearsal and final_lane) if not blocked else {}
    run = LaneRun(args.lane, args.contract.resolve(), out_root)
    run.rehearsal = args.rehearsal
    run.storage_reservation = _reservation_for_check(args, final_lane, reservation, paths)
    run.contract = contract
    run.binding = binding
    console = Tee(run.run_dir / "lane.log", sys.stdout)
    sys.stdout = console
    print(f"{LABEL} lane {args.lane} run {run.stamp}" + (" (REHEARSAL, NOT EVIDENCE)" if args.rehearsal else ""))
    interpreter = base.bind_interpreter(run.python)
    if args.rehearsal and args.lane == "LOCAL_INTEGRATION_CANDIDATE" and not blocked:
        run.extra["rehearsal_scratch_candidate"] = a6.rehearse_candidate()
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
    guard_events, guard_fragments = _guard_events(run.guard_log)
    if guard_fragments:
        reason = (f"{reason}; {len(guard_fragments)} guard-log line(s) left torn by concurrent appenders are kept as "
                  "fragments, not events")
    print(f"[{args.lane}] {result}: {reason}")
    console.flush()
    reconciled = ledger.reconcile(reservation["token"], note=f"lane {result}") if reservation else None
    if reconciled and reconciled.get("underestimated"):
        reason = f"{reason}; the lane used {reconciled['operation_added_bytes']} bytes, past its reservation"
    # The receipt, its index line and the log's close are written inside a reservation of their own (R37A11-02-B).
    receipt_window = None
    if ledger is not None:
        try:
            receipt_window = ledger.reserve(f"RECEIPT {args.lane} {run.stamp}" + (" (rehearsal)" if args.rehearsal
                                                                                   else ""),
                                            RECEIPT_ESTIMATE, note=f"lane {result}: receipt, index line, log close")
        except storage.AdmissionRefused as refusal:
            result = FAIL
            reason = (f"{reason}; the receipt window was refused ({refusal.record.get('reason')}); the receipt is "
                      "written unadmitted")
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
                    "reconcile": reconciled, "receipt_window": receipt_window,
                    "paths": {k: str(v) for k, v in paths.items()},
                    "final_snapshot_existed": FINAL_SNAPSHOT.is_file(),
                    "order": ("lane reservation before the run folder; reconcile after the lane's last print; the "
                              "receipt window reserved before the receipt, the index line and the log close, and "
                              "reconciled after them")},
        "final_packet_validation": {"path": str(validation), "sha256": sha256_file(validation)} if validation else None,
        "write_and_network_scope": {
            "guarded_roots": [str(root) for root in base.GUARDED_ROOTS],
            "writable_roots": [str(out_root), str(VALIDATION_ROOT), str(PACKAGING_ROOT)],
            "git_scratch_root": run.tmp_spelling,
            "network": "DENY_NON_LOOPBACK for guarded children", "credential_variables_removed": sorted(credential_scrub()),
            "temp_root": str(run.tmp), "temp_spelling_given_to_children": run.tmp_spelling,
            "exceptions": run.exceptions, "guard_events": len(guard_events),
            "guard_blocked_events": [row for row in guard_events if row.get("event") == "BLOCKED"][:100],
            "guard_log_fragments": guard_fragments,
            "guard_log_limitation": ("the guard log is a diagnostic record appended by concurrent children; a torn line "
                                     "is kept as a fragment, and the event count is not an exhaustive count of "
                                     "attempted writes (the before/after measurement is the independent check)"),
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
    if receipt_window:
        ledger.reconcile(receipt_window["token"], note=f"receipt {digest}")
    return 0 if result == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
