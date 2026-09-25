r"""Cycle #37 — Attempt #5 — the lane runner (R37A05-07-A).

    attempt05_lanes.py --lane <ID> --contract <cycle_contract.json> --out-root <attempt root>

This is the preserved Attempt 4 runner (``attempt04_lanes``, itself the Attempt 3 runner rebound) rebound to the
Attempt 5 contract, roots and evidence, with the lanes Attempt 5 adds or changes. Everything the earlier runners
bind per run is still bound: the issued contract by its sealed digest, the committed subject (branch, head, tree,
source digest, descent from the issued base, a clean tree before and after), the interpreter and its
distributions, module origins, the delivered database by digest, a before/after measurement of the data root and
``C:\All-22``, the heads of the main checkout and both integration worktrees, and credential removal.

What Attempt 5 changes:

* **Storage is admitted before every lane.** The runner reserves each lane's estimate in the attempt's one
  cumulative ledger (``storage_admission``, MF37A04-05) before the lane starts and reconciles the measured cost
  after it; a refused reservation blocks the lane before any effect. STORAGE_ADMISSION qualifies the ledger
  itself (suite, chain, a live over-budget refusal, per-lane reservation pairs).
* **Guard and storage qualification gate the costly lanes.** CAREER_SUCCESSOR, INSTALLED_CONSUMER_C01,
  LOCAL_INTEGRATION_CANDIDATE and the mounted/unmounted lanes run only after WRITE_PROTECTION and
  STORAGE_ADMISSION have passed at the same head, with the same guard bytes.
* **WRITE_PROTECTION** adds the v37.5 typed-grammar suite, the manager's Attempt 4 ``GIT_OPTION_CHALLENGE_V2``
  replay (MF37A04-01) and a live check that a guarded Git write with no declared scratch root is refused.
* **CAREER_SUCCESSOR** rebuilds the independent template census and the Attempt 5 successor from the committed
  subject and requires the rebuild to be byte-identical to the delivered file, every predecessor and Attempt 4 row
  dispositioned once, every screen member grounded and every census form reconciled.
* **INSTALLED_CONSUMER_C01** serves the Attempt 5 successor through the fresh installed ``bas-staff-query``: named
  corrections and controls, full pagination and filters against an independent SQL/Python oracle, refusals by
  cause for resealed missing, extra, dangling, nonreciprocal, duplicate and unmapped rows and for absent, removed or
  tampered raw evidence, and the manager's Attempt 4 challenges replayed against it.
* **LOCAL_INTEGRATION_CANDIDATE** verifies the one separate candidate: its tree, its history policy, that every
  other ref kept its commit, that the protected review controls keep main's bytes and were never written, and the
  consumer built from the candidate's own tree.

A lane decides what its commands did. It does not decide scientific acceptance, and it cannot turn an inherited
red lane green.
"""

from __future__ import annotations

import argparse
import collections
import gzip
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
import attempt04_lanes as a4  # noqa: E402  (the preserved Attempt 4 runner)
import attempt05_candidate as candidate  # noqa: E402
import storage_admission as storage  # noqa: E402
from attempt03_lanes import (  # noqa: E402
    BLOCKED,
    FAIL,
    PASS,
    ALL22,
    C01_WHEEL,
    DATA_ROOT,
    DELIVERED_DB,
    INTEGRATION_WORKTREE,
    MAIN_CHECKOUT,
    WORKTREE,
    Tee,
    credential_scrub,
    git_out,
    sha256_bytes,
    sha256_file,
    utc_now,
    write_json,
)

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 5
CYCLE_ID = "CYCLE-37"
ATTEMPT_ID = "ATTEMPT-05-20260925"
RUNNER_VERSION = "BAS-C37-ATTEMPT05-LANES-v1"
BASE_SHA = "cfdc588c0d580e80615374e3e05edd1b6b4c3bc7"
BRANCH = "codex/BAT-706-cycle37-rework"
LANES = (
    "START_CONTEXT", "WRITE_PROTECTION", "STORAGE_ADMISSION", "SOURCE_ADMISSION", "SOURCE_HARNESS",
    "SOURCE_REGRESSIONS", "CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01", "LOCAL_INTEGRATION_CANDIDATE",
    "TRUE_UNMOUNTED", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED", "PLATFORM_CARRY", "FINAL_PACKET",
)
#: Lanes that run only after WRITE_PROTECTION and STORAGE_ADMISSION passed at the same head and guard bytes.
GATED = frozenset({"CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01", "LOCAL_INTEGRATION_CANDIDATE", "TRUE_UNMOUNTED",
                   "FULL_FINAL_MOUNTED", "STRICT_MOUNTED"})
MIB = 1024 * 1024
#: Each lane's reservation in the cumulative storage ledger (reserved before the lane, reconciled after it).
LANE_ESTIMATES = {
    "START_CONTEXT": 16 * MIB, "WRITE_PROTECTION": 64 * MIB, "STORAGE_ADMISSION": 64 * MIB,
    "SOURCE_ADMISSION": 96 * MIB, "SOURCE_HARNESS": 64 * MIB, "SOURCE_REGRESSIONS": 128 * MIB,
    "CAREER_SUCCESSOR": 160 * MIB, "INSTALLED_CONSUMER_C01": 640 * MIB, "LOCAL_INTEGRATION_CANDIDATE": 192 * MIB,
    "TRUE_UNMOUNTED": 128 * MIB, "FULL_FINAL_MOUNTED": 256 * MIB, "STRICT_MOUNTED": 96 * MIB,
    "PLATFORM_CARRY": 128 * MIB, "FINAL_PACKET": 32 * MIB,
}
#: A rehearsal of the candidate lane also checks out its own scratch candidate (about 155 MB).
REHEARSAL_CANDIDATE_BYTES = 224 * MIB

EVIDENCE_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt05"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a05")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37a05")
ATTEMPT4_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt04"
VALIDATION_A04 = Path(r"C:\BatteredAggieSyndrome.validation\c37a04")
PACKAGING_A04 = Path(r"C:\BatteredAggieSyndrome.packaging\c37a04")
MANAGER_A4 = DATA_ROOT / "ops" / "manager_reviews" / "cycle37" / "attempt04" / "review-20260925T025537Z"
MANAGER_FIXTURE_LITERAL = r"C:\BatteredAggieSyndrome.validation\mr37a04-025537"
A4_VENV_LITERAL = r"C:\BatteredAggieSyndrome.packaging\c37a04\b\b9a46658\venv"
A4_SUCCESSOR = ATTEMPT4_ROOT / "release" / "successor" / "CAREER_SUCCESSOR_A04.sqlite"
A4_SUCCESSOR_SHA256 = "f7103f781259ecf13a06dfc59318ab7c735a9ff7c1080b9fd4608f04ae0373c7"
A4_RAW_CENSUS = ATTEMPT4_ROOT / "release" / "census" / "CAREER_RAW_CENSUS.json"
DELIVERED_CENSUS = EVIDENCE_ROOT / "release" / "census" / "CAREER_TEMPLATE_CENSUS.json"
SUCCESSOR_POINTER = EVIDENCE_ROOT / "release" / "CAREER_SUCCESSOR_POINTER.json"
STORAGE_LEDGER = EVIDENCE_ROOT / "STORAGE_RESERVATIONS.jsonl"
CANDIDATE_RECORDS = EVIDENCE_ROOT / "evidence" / "integration"
CANDIDATE_WORKTREE = candidate.CANDIDATE_WORKTREE
CANDIDATE_BRANCH = candidate.CANDIDATE_BRANCH
MAIN_SHA = candidate.MAIN_SHA
GUARD = WORKTREE / "tools" / "cycle37" / "canonical_write_guard" / "bas_canonical_write_guard.py"
#: Every installed CLI command runs under this standard-library helper, started with -S so it installs nothing of
#: its own; the CLI child inherits the guarded environment unchanged and installs the write guard itself, as before.
STREAM_HELPER = WORKTREE / "tools" / "cycle37" / "attempt05_stream_stdout.py"
#: Standard output up to this size stays in the command log exactly as before. A larger answer (a population page)
#: is kept whole in a gzip file beside it, with its raw bytes' SHA-256 and size, and is not repeated uncompressed in
#: the log: the rehearsal of this lane wrote 1.0 GB of such logs against a 4 GiB attempt budget (MF37A04-05).
ECHO_LIMIT = 4 * MIB
STREAM_EXCEPTION = ("Installed CLI commands run under tools/cycle37/attempt05_stream_stdout.py, a standard-library "
                    "helper started with -S (no guard of its own; it writes only the log directory). The CLI child "
                    "inherits the guarded environment unchanged and installs the write guard itself. Standard output "
                    "over 4 MiB is kept whole in a gzip file with its raw SHA-256 instead of an uncompressed log copy.")
AFTER_COMMENTS = (("BAT-706", "C37-A05-AFTER-HANDOFF-BAT-706"), ("BAT-708", "C37-A05-AFTER-HANDOFF-BAT-708"))
PLATFORM_TOOL = "tools/cycle37/attempt05_platform.py"
OUTPUTS_TOOL = "tools/cycle37/attempt05_outputs.py"
FRED = a4.FRED

BOUND_MODULES = a4.BOUND_MODULES + ("aggie_analytics.cycle37.staff_record",)
GUARD_SUITES = a4.GUARD_SUITES + ("test_cycle37_a05_git_grammar_guard",)
STORAGE_SUITES = ("test_cycle37_a05_storage_admission",)
CAREER_SUITES = ("test_cycle37_a04_career_successor", "test_cycle37_a05_career_successor",
                 "test_cycle37_career_reparse", "test_cycle37_staff_reparse")
REGRESSION_SUITES = a4.REGRESSION_SUITES + ("test_cycle37_a05_career_successor", "test_jira_authority_progress_comments")
#: Suites run from the candidate's own tree: the consumer and repair suites it must pass.
CANDIDATE_SUITES = ("test_cycle37_a05_career_successor", "test_cycle37_a04_career_successor",
                    "test_cycle37_release_query", "test_cycle37_a05_storage_admission",
                    "test_jira_authority_progress_comments", "test_cycle37_career_reparse")
#: Suites that exercise the protected review controls, whose repair-branch changes the candidate withholds; run
#: from the candidate as a characterization of that withholding, not as a pass/fail gate of this lane.
CONTROL_SUITES = ("test_cycle26_adversarial_regressions", "test_cycle27_trusted_control_protocol",
                  "test_pr_review_defense_infrastructure")
#: The part of the candidate commit those suites import and read, exported under the packaging stage: the candidate
#: worktree never holds the protected files on disk (skip-worktree), so the controls can only run from an export.
CONTROL_EXPORT = ("tests", "tools", "src", ".github", "schemas", "instructions", "artifacts/scientific_integrity",
                  "jira/tools", "pyproject.toml", "README.md")


def rebind() -> None:
    """Point the preserved runners at the Attempt 5 contract, roots, suites and grants."""

    a4.rebind()
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
    base.GUARDED_ROOTS = tuple(root for root in (DATA_ROOT, MAIN_CHECKOUT, INTEGRATION_WORKTREE, ALL22,
                                                 a4.VALIDATION_A03, a4.PACKAGING_A03, VALIDATION_A04, PACKAGING_A04,
                                                 CANDIDATE_WORKTREE))
    base.AFTER_COMMENTS = AFTER_COMMENTS
    base._cli = _cli
    base._stdout_json = _stdout_json
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


class LaneRun(a4.LaneRun):
    """The Attempt 4 lane context: guarded children get the declared Git scratch root (the packaging root)."""


def _cli(run: LaneRun, installed: dict[str, Any], name: str, args: list[Any], *, database: Path | None = None,
         expect_exit: int = 0, save: Path | None = None, note: str = "") -> dict[str, Any]:
    """The installed CLI, as the preserved runners call it, with its standard output kept by the stream helper."""

    if STREAM_EXCEPTION not in run.exceptions:
        run.exceptions.append(STREAM_EXCEPTION)
    target = save if save is not None else run.log_dir / f"{run.lane}__{name}.stdout.json.gz"
    summary = run.log_dir / f"{run.lane}__{name}.stdout.json"
    record = run.run(name, [run.python, "-S", "-B", STREAM_HELPER, target, ECHO_LIMIT, summary, "--",
                            installed["script"], "--database", database or base.DELIVERED_DB, *args],
                     cwd=installed["stage"], env=base._installed_env(run), expect_exit=expect_exit, timeout=3600,
                     note=note)
    captured = _json_file(summary) or {}
    record["stdout_capture"] = {"helper": str(STREAM_HELPER), "helper_sha256": sha256_file(STREAM_HELPER),
                                "summary": str(summary), **captured}
    if captured.get("streamed_to"):
        record["stdout_gzip"] = captured["streamed_to"]
        record["stdout_gzip_sha256"] = sha256_file(Path(captured["streamed_to"]))
        if save is not None:
            record["saved_output_gzip"] = str(save)
            record["saved_output_sha256"] = record["stdout_gzip_sha256"]
    elif save is not None:
        text = Path(record["log_path"]).read_bytes()
        with gzip.open(save, "wb") as handle:
            handle.write(text)
        record["saved_output_gzip"] = str(save)
        record["saved_output_sha256"] = sha256_file(save)
    return record


def _stdout_json(record: dict[str, Any]) -> Any:
    """The first JSON value of a command's standard output: from its gzip file when it was streamed there."""

    if record.get("stdout_gzip"):
        return base._gz_json(Path(record["stdout_gzip"]))
    return base.first_json(Path(record["log_path"]).read_text(encoding="utf-8", errors="replace"))


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
        problems.append("contract is not Cycle 37 Attempt 5")
    if contract.get("attempt_id") != ATTEMPT_ID:
        problems.append(f"contract attempt_id {contract.get('attempt_id')!r} is not {ATTEMPT_ID}")
    if (contract.get("repo") or {}).get("base_sha") != BASE_SHA:
        problems.append(f"contract base {(contract.get('repo') or {}).get('base_sha')} is not {BASE_SHA}")
    row = {r["id"]: r for r in contract.get("required_lanes", [])}.get(lane)
    if row is None or row.get("executor") != "worker":
        problems.append(f"{lane} is not a worker lane of this contract")
    elif f"attempt05_lanes.py --lane {lane} " not in row.get("command", ""):
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
        "rebound_attempt4_runner": str(Path(a4.__file__).resolve()),
        "rebound_attempt4_runner_sha256": sha256_file(Path(a4.__file__).resolve()),
        "guard": str(GUARD), "guard_sha256": sha256_file(GUARD),
        "storage_tool_sha256": sha256_file(Path(storage.__file__).resolve()),
    })
    return binding


def successor_pointer() -> dict[str, Any]:
    return json.loads(SUCCESSOR_POINTER.read_text(encoding="utf-8")) if SUCCESSOR_POINTER.is_file() else {}


def _json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _runs(out_root: Path) -> list[dict[str, Any]]:
    index = out_root / "lanes" / "RUNS.jsonl"
    if not index.is_file():
        return []
    return [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line.strip()]


def qualification(out_root: Path, head: str, guard_sha256: str | None) -> dict[str, Any]:
    """The latest WRITE_PROTECTION and STORAGE_ADMISSION receipts at this head, and whether both hold."""

    result: dict[str, Any] = {}
    for lane in ("WRITE_PROTECTION", "STORAGE_ADMISSION"):
        rows = [row for row in _runs(out_root) if row["lane"] == lane and row["head"] == head]
        latest = rows[-1] if rows else None
        receipt = _json_file(Path(latest["receipt"])) if latest else None
        guard = ((receipt or {}).get("source_binding") or {}).get("guard_sha256")
        result[lane] = {"run": (latest or {}).get("run"), "result": (latest or {}).get("result"),
                        "receipt": (latest or {}).get("receipt"), "guard_sha256": guard,
                        "holds": bool(latest) and latest["result"] == PASS and guard == guard_sha256}
    result["holds"] = all(row["holds"] for row in result.values() if isinstance(row, dict))
    return result


def candidate_state() -> dict[str, Any]:
    state = base.checkout_state(CANDIDATE_WORKTREE)
    if state.get("exists"):
        state["branch_ref"] = git_out("rev-parse", "--verify", "--quiet", f"refs/heads/{CANDIDATE_BRANCH}",
                                      repo=CANDIDATE_WORKTREE)
    return state


def rehearse_candidate(run: LaneRun) -> dict[str, Any]:
    """Rehearsal only: prepare a scratch candidate exactly as the granted one is prepared, but in a scratch bare
    repository under the validation root that borrows the shared objects read-only (objects/info/alternates) and holds
    its own copies of the main and repair refs. The granted candidate is created once, so its lane must already
    have run end to end; this never writes to the shared repository."""

    global CANDIDATE_WORKTREE, CANDIDATE_RECORDS
    # A short folder: the checkout must fit the same path limit as the granted candidate's (no core.longpaths).
    scratch = VALIDATION_ROOT / "rc" / sha256_bytes(run.stamp.encode("utf-8"))[:8]
    repo = scratch / "repo.git"
    common = Path(git_out("rev-parse", "--path-format=absolute", "--git-common-dir"))
    subprocess.run(["git", "init", "--bare", "--quiet", str(repo)], check=True, capture_output=True)
    # LF only: git reads a CRLF line as an object directory whose name ends in a carriage return.
    (repo / "objects" / "info" / "alternates").write_text((common / "objects").as_posix() + "\n", encoding="utf-8",
                                                         newline="\n")
    for ref, sha in (("refs/heads/main", MAIN_SHA), (f"refs/heads/{candidate.REPAIR_BRANCH}", run.binding["head"])):
        subprocess.run(["git", "--no-optional-locks", "-C", str(repo), "update-ref", ref, sha], check=True,
                       capture_output=True)
    candidate.REPO = repo
    candidate.SCRATCH = scratch / "index"
    candidate.CANDIDATE_WORKTREE = CANDIDATE_WORKTREE = scratch / "w"
    CANDIDATE_RECORDS = scratch / "records"
    base.GUARDED_ROOTS = base.GUARDED_ROOTS + (CANDIDATE_WORKTREE,)
    record = candidate.create(CANDIDATE_RECORDS / f"CANDIDATE_RECORD_{run.stamp}.json")
    return {"scratch_repository": str(repo), "borrowed_objects": str(common / "objects"),
            "candidate_worktree": str(CANDIDATE_WORKTREE), "candidate_commit": record.get("candidate_commit"),
            "refs_changed": record.get("refs_changed"),
            "meaning": "A rehearsal copy of the candidate; the granted candidate is prepared separately."}


# ------------------------------------------------------------------ lanes


def lane_start_context(run: LaneRun) -> None:
    a4.lane_start_context(run)
    ledger = storage.Ledger(STORAGE_LEDGER)
    try:
        rows = ledger.records()
        status = ledger.status()
        chain = {"intact": True, "records": len(rows)}
    except storage.LedgerError as error:
        status, chain = {}, {"intact": False, "error": str(error)}
    run.extra["storage_ledger"] = {"path": str(STORAGE_LEDGER), "chain": chain,
                                   **{k: status.get(k) for k in ("budget_bytes", "reserve_bytes", "added_bytes",
                                                                 "headroom_bytes", "free_bytes", "bounded_stop",
                                                                 "refused", "underestimated")}}
    if not chain["intact"] or status.get("bounded_stop"):
        run.problems.append(f"the storage ledger is not usable: {chain}, stop={status.get('bounded_stop')}")
    pointer = successor_pointer()
    if pointer:
        built = (pointer.get("built_from") or {}).get("head")
        run.extra["career_successor_built_from"] = {
            "head": built, "clean": (pointer.get("built_from") or {}).get("clean"),
            "ancestor_of_this_head": base.git("merge-base", "--is-ancestor", str(built),
                                              run.binding["head"]).returncode == 0}
        if not run.extra["career_successor_built_from"]["ancestor_of_this_head"]:
            run.problems.append("the delivered successor was built from a head this subject does not descend from")
    before = EVIDENCE_ROOT / "evidence" / "before"
    rerun = EVIDENCE_ROOT / "evidence" / "before_mf05_v2" / "BEFORE_MF05_RERUN.json"
    reproduction = _json_file(before / "BEFORE_REPRODUCTION.json") or {}
    run.extra["before_reproduction"] = {
        "file": str(before / "BEFORE_REPRODUCTION.json"), "sha256": sha256_file(before / "BEFORE_REPRODUCTION.json"),
        "reproduced": reproduction.get("reproduced"), "subject": reproduction.get("subject"),
        "mf05_detector_v2": {"file": str(rerun), "sha256": sha256_file(rerun),
                             "reproduced": ((_json_file(rerun) or {}).get("result") or {}).get("reproduced")}}
    run.extra["guard"] = {"path": str(GUARD), "sha256": sha256_file(GUARD)}
    run.extra["integration_candidate"] = {"state": candidate_state(), "description": candidate.describe()}
    run.extra["platform_receipts"] = sorted(str(p.relative_to(EVIDENCE_ROOT)) for p in
                                            (EVIDENCE_ROOT / "evidence" / "platform").rglob("*.json"))


def lane_write_protection(run: LaneRun) -> None:
    a4.lane_write_protection(run)
    # MF37A04-01: the manager's Attempt 4 challenge, against this subject's guard (the script names this worktree).
    fixture = run.fresh("mgr_a4_git_option_fixture")
    (fixture / "temp").mkdir()
    copy, replay = a4._replay_from(run, MANAGER_A4, "git_option_challenge_v2.py",
                                   adapt={f'F=pathlib.Path(r"{MANAGER_FIXTURE_LITERAL}")': f'F=pathlib.Path(r"{fixture}")'})
    record = run.run("manager_a4_git_option_challenge_v2_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None),
                     note="The manager's saved challenge, fixture root adapted; it installs the guard in its own child.")
    result = _json_file(copy.parent / "GIT_OPTION_CHALLENGE_V2.json") or {}
    child = json.loads(result.get("stdout") or "[]") if result.get("stdout") else []
    by_label = {row.get("label"): row for row in child if isinstance(row, dict) and row.get("label")}
    refused = {label: bool(by_label.get(label, {}).get("refused")) or (by_label.get(label, {}).get("exit") not in (0, None))
               for label in ("protected_attached_file", "protected_attached_file_abbreviated_unset")}
    verdict = {**replay, "exit": record.get("exit_code"),
               "protected_bytes_unchanged": result.get("protected_bytes_unchanged"),
               "final_fixture_bytes": result.get("final_fixture_bytes"),
               "ordinary_write_refused": (child[0] if child else {}).get("ordinary_write_refused"),
               "owned_positive_exit": by_label.get("owned_positive", {}).get("exit"),
               "refused": refused, "child": child}
    verdict["holds"] = (result.get("protected_bytes_unchanged") is True and all(refused.values())
                        and verdict["ordinary_write_refused"] is True and verdict["owned_positive_exit"] == 0)
    run.extra["manager_a4_git_option_challenge_v2"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"MF37A04-01 is not closed by the manager's challenge: {verdict}")
    # A fresh live control: a guarded Git write with no declared scratch root is refused before any effect, and
    # the same write inside the declared scratch root is admitted.
    probe = run.fresh("no_scratch_control")
    script = ("import json, subprocess, sys\n"
              "target = sys.argv[1]\n"
              "try:\n"
              "    done = subprocess.run(['git', 'init', '-q', target], capture_output=True, text=True)\n"
              "    print(json.dumps({'refused': False, 'exit': done.returncode}))\n"
              "except OSError as error:\n"
              "    print(json.dumps({'refused': True, 'error': str(error)}))\n")
    no_scratch = run.env()
    no_scratch["BAS_CANONICAL_WRITE_GIT_SCRATCH"] = None
    denied = run.run("live_git_write_without_declared_scratch", [run.python, "-B", "-c", script, probe / "repo"],
                     env=no_scratch, note="Guarded child; no scratch root declared; the write must be refused.")
    admitted_target = PACKAGING_ROOT / "lane_git_positive" / run.stamp
    admitted = run.run("live_git_write_inside_declared_scratch", [run.python, "-B", "-c", script, admitted_target],
                       note="Guarded child; the same write inside the declared scratch root is admitted.")
    denied_out, admitted_out = base._stdout_json(denied) or {}, base._stdout_json(admitted) or {}
    control = {"denied": denied_out, "denied_target_exists": (probe / "repo").exists(),
               "admitted": admitted_out, "admitted_target_is_repository": (admitted_target / ".git").is_dir()}
    control["holds"] = (denied_out.get("refused") is True and "scratch" in str(denied_out.get("error"))
                        and not control["denied_target_exists"] and admitted_out.get("exit") == 0
                        and control["admitted_target_is_repository"])
    run.extra["live_scratch_control"] = control
    if not control["holds"]:
        run.problems.append(f"the live scratch-root control does not hold: {control}")
    run.extra["guard"] = {"path": str(GUARD), "sha256": sha256_file(GUARD)}


def lane_storage_admission(run: LaneRun) -> None:
    run.census("storage_suites", STORAGE_SUITES,
               note="Admitted, too large, cumulative, concurrent, free reserve, underestimate, bounded stop, restart, "
                    "orphan and explicit holders, broken chain and no deletion, each on an owned ledger.")
    ledger = storage.Ledger(STORAGE_LEDGER)
    rows = ledger.records()  # raises on a broken chain
    status = ledger.status()
    # A live control on the attempt's own ledger: an allocation past the budget is refused before any effect.
    try:
        ledger.reserve("STORAGE_ADMISSION live control: one byte past the remaining budget",
                       int(status["budget_bytes"]) + 1, note="must be refused; nothing is allocated")
        live = {"refused": False}
    except storage.AdmissionRefused as refusal:
        live = {"refused": True, "record_seq": refusal.record.get("seq"), "reason": refusal.record.get("reason")}
    rows = ledger.records()
    lanes = [row for row in rows if row["kind"] == "RESERVE" and str(row.get("operation", "")).startswith("LANE ")]
    reconciled = {row["token"] for row in rows if row["kind"] == "RECONCILE"}
    pairs = {"lane_reservations": len(lanes),
             "admitted": sum(1 for row in lanes if row["decision"] == "ADMITTED"),
             "refused": sum(1 for row in lanes if row["decision"] == "REFUSED"),
             "admitted_and_reconciled": sum(1 for row in lanes if row["decision"] == "ADMITTED"
                                            and row["token"] in reconciled),
             "open_now": sorted(row["token"] for row in lanes if row["decision"] == "ADMITTED"
                                and row["token"] not in reconciled)}
    # MF37A04-05, replayed against this runner: the Attempt 4 detector (v2) over its source now finds the
    # admission calls that the Attempt 4 runners lacked.
    source = Path(__file__).resolve().read_text(encoding="utf-8").splitlines()
    calls = [f"{n}: {line.strip()}" for n, line in enumerate(source, 1)
             if re.search(r"\breserve\(|storage_admission|\bLedger\(|run_bounded\(|reservation\(", line)]
    breach = sorted((ATTEMPT4_ROOT / "evidence").glob("STORAGE_MEASUREMENT_*.json"))
    run.extra["storage_ledger"] = {
        "path": str(STORAGE_LEDGER), "records": len(rows), "chain_intact": True,
        **{k: status.get(k) for k in ("budget_bytes", "reserve_bytes", "added_bytes", "headroom_bytes", "free_bytes",
                                      "bounded_stop")},
        "live_over_budget_control": live, "lane_reservation_pairs": pairs,
        "runner_admission_calls": calls[:40],
        "attempt4_breach_retained": {"file": str(breach[-1]) if breach else None,
                                     "sha256": sha256_file(breach[-1]) if breach else None,
                                     "state": "W37A04-15 remains an observed Attempt 4 breach; nothing was deleted"}}
    if not live["refused"]:
        run.problems.append("an over-budget reservation was admitted on the attempt's ledger")
    if status.get("bounded_stop"):
        run.problems.append(f"a bounded stop is recorded: {status['bounded_stop']}")
    if int(status["added_bytes"]) > int(status["budget_bytes"]):
        run.problems.append("the attempt's measured added bytes exceed the budget")
    if not calls:
        run.problems.append("the runner source makes no storage admission call")


def lane_source_admission(run: LaneRun) -> None:
    a4.lane_source_admission(run)


def lane_source_harness(run: LaneRun) -> None:
    base.lane_source_harness(run)


def lane_source_regressions(run: LaneRun) -> None:
    base.lane_source_regressions(run)


# ---- the explicit career successor --------------------------------------------------------------------------


def _check_build(run: LaneRun, summary: dict[str, Any]) -> dict[str, Any]:
    """Every accounting, screen and census condition the rebuilt summary must meet, each recorded."""

    accounting = summary.get("accounting") or {}
    a3 = summary.get("a3_screens") or {}
    a4s = summary.get("a4_screens") or {}
    template = a4s.get("MANAGER_A04_TWO_ARGUMENT_SEASON_TEMPLATE_2257") or {}
    defensive = a4s.get("MANAGER_A04_DEFENSIVE_PASS_GAME_TITLE_33") or {}
    raw_census = summary.get("a4_raw_census_reconciliation") or {}
    raw_counts = raw_census.get("counts") or {}
    uncovered = (summary.get("a4_raw_census_uncovered_by_cause") or {}).get("by_cause") or {}
    tcensus = summary.get("template_census_reconciliation") or {}
    tcounts = tcensus.get("counts") or {}
    nested_consistent = sum(v for k, v in tcounts.items() if k.startswith("nested::") and k.endswith("::CONSISTENT"))
    not_produced = summary.get("not_produced_by_cause") or {}
    checks = {
        "byte_identical_rebuild": (summary.get("rebuild_comparison") or {}).get("byte_identical") is True,
        "predecessor_unchanged": (summary.get("predecessor") or {}).get("unchanged") is True,
        "a04_successor_unchanged": (summary.get("a04_successor") or {}).get("unchanged") is True,
        "every_predecessor_row_dispositioned_once": accounting.get("every_predecessor_row_dispositioned_once") is True
        and accounting.get("predecessor_rows") == 72070,
        "successor_identities_distinct": accounting.get("successor_identities_distinct") is True,
        "every_a04_row_mapped_once": (summary.get("a04_mapping") or {}).get("every_a04_row_mapped_once") is True
        and (summary.get("a04_mapping") or {}).get("total") == 73082,
        "a3_screens_grounded": len(a3) == 3 and all(
            row.get("members") == row.get("expected") and not row.get("without_disposition")
            and row.get("builder_label_equals_manager_set") and not row.get("unchanged_without_grounded_basis")
            for row in a3.values()),
        "a3_priority_rows_not_head_coach": (a3.get("MANAGER_ROLE_CODE_343") or {}).get("successor_rows_still_head_coach") == 0,
        "template_screen_complete_and_read": template.get("members") == 2257 and not template.get("without_disposition")
        and not template.get("template_not_read_as_its_form_states") and not template.get("manager_endpoint_not_read"),
        "defensive_screen_all_defense": defensive.get("members") == 33 and not defensive.get("without_disposition")
        and not defensive.get("independent_side_differs_or_absent"),
        "raw_census_reconciled": raw_census.get("rows_sha256_matches_census") is True and not any(
            v for k, v in raw_counts.items() if "_without_" in k or "not_read_verbatim" in k),
        "raw_census_uncovered_only_hidden_text": not uncovered.get("no_row_for_another_reason"),
        "template_census_reconciled": tcensus.get("template_rows_sha256_matches") is True
        and tcensus.get("list_items_sha256_matches") is True and not any(
            v for k, v in tcounts.items() if "not_read_as_stated" in k or "not_inside_any_row_years_span" in k),
        "nested_items_consistent": nested_consistent + tcounts.get("nested::NONE::NO_PARENT_ITEM_ABOVE_IT", 0)
        == tcounts.get("nested_items"),
        "not_produced_rows_grounded": not any("NO_ROW_AT_THIS_LOCATOR" in cause for side in not_produced.values()
                                              for cause in side),
    }
    for name, held in checks.items():
        if not held:
            run.problems.append(f"career successor rebuild: {name} does not hold")
    return checks


def lane_career_successor(run: LaneRun) -> None:
    run.census("career_suites", CAREER_SUITES)
    pointer = successor_pointer()
    if not pointer:
        run.problems.append("no delivered career successor pointer")
        return
    delivered = Path(pointer["successor_file"])
    work = run.fresh("successor_rebuild")
    census_dir, rebuild_dir = work / "census", work / "rebuild"
    run.run("career_template_census", [run.python, "-B", "tools/cycle37/a05_career_template_census.py", "--out",
                                       census_dir], timeout=3 * 3600,
            note="The independent template census, rebuilt from the committed subject (no parser import).")
    rebuilt_census = _json_file(census_dir / "CAREER_TEMPLATE_CENSUS.json") or {}
    delivered_census = _json_file(DELIVERED_CENSUS) or {}
    census_equal = {key: rebuilt_census.get(key) == delivered_census.get(key) and bool(rebuilt_census.get(key))
                    for key in ("template_rows_sha256", "list_items_sha256", "template_occurrences")}
    run.extra["template_census_reproduction"] = {"rebuilt": str(census_dir), "delivered": str(DELIVERED_CENSUS),
                                                 "delivered_sha256": sha256_file(DELIVERED_CENSUS), **census_equal}
    if not all(census_equal.values()):
        run.problems.append(f"the rebuilt template census differs from the delivered one: {census_equal}")
    run.run("career_successor_rebuild_compare",
            [run.python, "-B", "tools/cycle37/a05_career_successor.py", "--out", rebuild_dir, "--census", A4_RAW_CENSUS,
             "--template-census", census_dir / "CAREER_TEMPLATE_CENSUS.json", "--compare-to", delivered],
            timeout=6 * 3600, note="Rebuilt in memory from the committed parser, taxonomy and builder; compared byte "
                                   "for byte with the delivered file; no second successor file is written.")
    summary = _json_file(rebuild_dir / "CAREER_A05_SUCCESSOR_REBUILD.json") or {}
    run.extra["successor_reproduction"] = {"delivered": str(delivered), "delivered_sha256": sha256_file(delivered),
                                           "pointer_sha256": pointer.get("successor_sha256"),
                                           "comparison": summary.get("rebuild_comparison")}
    if sha256_file(delivered) != pointer.get("successor_sha256"):
        run.problems.append("the delivered successor does not match its pointer")
    run.extra["successor_checks"] = _check_build(run, summary)
    run.extra["successor_accounting"] = summary.get("accounting")
    run.extra["successor_dispositions"] = summary.get("dispositions")
    run.extra["a04_mapping"] = summary.get("a04_mapping")
    run.extra["screens"] = {"a3": summary.get("a3_screens"), "a4": summary.get("a4_screens")}
    run.extra["census_reconciliation"] = {"a4_raw": {k: v for k, v in (summary.get("a4_raw_census_reconciliation") or {})
                                                     .items() if k != "examples"},
                                          "a4_raw_uncovered_by_cause": summary.get("a4_raw_census_uncovered_by_cause"),
                                          "template": {k: v for k, v in (summary.get("template_census_reconciliation") or {})
                                                       .items() if k != "examples"}}
    run.extra["not_produced_by_cause"] = summary.get("not_produced_by_cause")
    run.extra["unit_changes"] = summary.get("unit_changes")
    run.extra["staff_descendants"] = summary.get("staff_descendants")
    # The Attempt 4 format still attaches and serves: a legacy selection keeps working, named superseded.
    legacy = ("import json, sqlite3, sys\n"
              "from pathlib import Path\n"
              "from aggie_analytics.cycle37 import career_successor as cs\n"
              "db, successor = Path(sys.argv[1]), Path(sys.argv[2])\n"
              "conn = sqlite3.connect(db.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)\n"
              "binding = cs.attach_successor(conn, successor, database=db, expected_sha256=sys.argv[3])\n"
              "print(json.dumps({k: binding[k] for k in ('format_version', 'episode_table', 'a04_table', "
              "'superseded_semantics', 'lineage_proved_independently_of_the_ledgers')}))\n")
    record = run.run("a04_successor_still_attaches", [run.python, "-B", "-c", legacy, DELIVERED_DB, A4_SUCCESSOR,
                                                      A4_SUCCESSOR_SHA256])
    run.extra["a04_successor_legacy"] = base._stdout_json(record)
    base.lane_claim_successor(run)


# ---- the installed consumer -----------------------------------------------------------------------------


def _successor_oracle(database: Path, successor: Path) -> dict[str, Any]:
    """Direct sqlite3 over the Attempt 5 successor, the Attempt 4 file and the predecessor; no aggie_analytics."""

    conn = sqlite3.connect(f"file:{successor.as_posix()}?mode=ro&immutable=1", uri=True)
    try:
        cursor = conn.execute('SELECT episode_id, pageid, page_title, person_display, family, start, "end", ongoing, '
                              "assignments, classification, resolution, definite_first_season, definite_last_season, "
                              "uncertainty_classes, row_index, interval_index, date_basis, date_parent, years_raw, "
                              "employer_display, team_raw FROM career_episode_a05")
        columns = [c[0] for c in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor]
        order = [str(row[0]) for row in conn.execute(
            "SELECT episode_id FROM career_episode_a05 ORDER BY pageid, family, row_index, interval_index, episode_id")]
        dispositions = {str(row[0]): row[1] for row in conn.execute(
            "SELECT predecessor_episode_id, disposition FROM career_a05_disposition")}
        a04_map = {str(row[0]): row[1] for row in conn.execute("SELECT a04_episode_id, disposition FROM career_a05_from_a04")}
        identity = {str(row[0]): str(row[1]) for row in conn.execute("SELECT key, value FROM successor_identity")}
    finally:
        conn.close()
    other = sqlite3.connect(f"file:{A4_SUCCESSOR.as_posix()}?mode=ro&immutable=1", uri=True)
    try:
        a04_ids = {str(row[0]) for row in other.execute("SELECT episode_id FROM career_episode_a04")}
    finally:
        other.close()
    predecessor = sqlite3.connect(f"file:{database.as_posix()}?mode=ro&immutable=1", uri=True)
    try:
        programs = {str(row[0]): json.loads(row[1] or "[]") for row in
                    predecessor.execute("SELECT program_id, display_names FROM canonical_program")}
        predecessor_ids = {str(row[0]) for row in predecessor.execute("SELECT episode_id FROM career_episode_successor")}
    finally:
        predecessor.close()
    return {"rows": rows, "order": order, "dispositions": dispositions, "a04_map": a04_map, "a04_ids": a04_ids,
            "identity": identity, "programs": programs, "predecessor_ids": predecessor_ids}


#: Each deliberately broken successor, the change that breaks it, whether its ledgers are resealed, the refusal
#: code the installed CLI must give, and the query that exercises it.
LINEAGE_CASES: tuple[tuple[str, tuple[str, ...], bool, str], ...] = (
    ("unsealed_missing_row", ("DELETE FROM career_episode_a05 WHERE episode_id = :fred",), False,
     "REFUSED_CAREER_SUCCESSOR_LEDGER_MISMATCH"),
    ("resealed_missing_row", ("DELETE FROM career_episode_a05 WHERE episode_id = :fred",), True,
     "REFUSED_CAREER_SUCCESSOR_DANGLING_REFERENCE"),
    ("resealed_missing_raw", ("UPDATE career_episode_a05 SET raw_file = NULL, raw_file_sha256 = NULL "
                              "WHERE episode_id = :fred",), True, "REFUSED_CAREER_SUCCESSOR_RAW_EVIDENCE_ABSENT"),
    ("resealed_dangling_disposition", ("UPDATE career_a05_disposition SET successor_episode_ids = "
                                       "'[\"C37A05:1:1:COACHING:1:0\"]' WHERE predecessor_episode_id = :fred_parent",),
     True, "REFUSED_CAREER_SUCCESSOR_DANGLING_REFERENCE"),
    ("resealed_nonreciprocal", ("UPDATE career_episode_a05 SET predecessor_episode_ids = :two_parents "
                                "WHERE episode_id = :fred",), True, "REFUSED_CAREER_SUCCESSOR_NONRECIPROCAL_LINEAGE"),
    ("resealed_extra_row", ("CREATE TEMP TABLE extra_row AS SELECT * FROM career_episode_a05 WHERE episode_id = :fred",
                            "UPDATE temp.extra_row SET episode_id = :fred_extra, interval_index = 9",
                            "INSERT INTO career_episode_a05 SELECT * FROM temp.extra_row",
                            "DROP TABLE temp.extra_row"), True, "REFUSED_CAREER_SUCCESSOR_NONRECIPROCAL_LINEAGE"),
    ("resealed_duplicate_identity", ("DROP INDEX a05_episode_id",
                                     "INSERT INTO career_episode_a05 SELECT * FROM career_episode_a05 "
                                     "WHERE episode_id = :fred"), True, "REFUSED_CAREER_SUCCESSOR_IDENTITY_COVERAGE"),
    ("resealed_extra_disposition", ("INSERT INTO career_a05_disposition SELECT 'R37-05:1:1:COACHING:1:0', disposition, "
                                    "successor_episode_ids, changed_fields, predecessor_row_sha256, screens, reason "
                                    "FROM career_a05_disposition WHERE predecessor_episode_id = :fred_parent",), True,
     "REFUSED_CAREER_SUCCESSOR_IDENTITY_COVERAGE"),
    ("resealed_incompatible_disposition", ("UPDATE career_a05_disposition SET disposition = "
                                           "'NOT_PRODUCED_BY_THE_SUCCESSOR_PARSER' WHERE predecessor_episode_id = "
                                           ":fred_parent",), True, "REFUSED_CAREER_SUCCESSOR_DISPOSITION_INCOMPATIBLE"),
    ("resealed_invalid_identity", ("UPDATE career_episode_a05 SET row_index = row_index + 7 WHERE episode_id = :fred",),
     True, "REFUSED_CAREER_SUCCESSOR_INVALID_IDENTITY"),
    ("resealed_unmapped_a04_row", ("DELETE FROM career_a05_from_a04 WHERE a04_episode_id = :fred_a04",), True,
     "REFUSED_CAREER_SUCCESSOR_A04_MAPPING_BROKEN"),
    ("resealed_raw_file_removed", ("UPDATE career_episode_a05 SET raw_file = :absent_raw WHERE episode_id = :fred",),
     True, "REFUSED_CAREER_SUCCESSOR_RAW_FILE_ABSENT"),
    ("resealed_raw_file_tampered", ("UPDATE career_episode_a05 SET raw_file = :tampered_raw WHERE episode_id = :fred",),
     True, "REFUSED_CAREER_SUCCESSOR_RAW_BYTES_CHANGED"),
    ("resealed_wrong_predecessor", ("UPDATE successor_identity SET value = '" + "0" * 64 + "' "
                                    "WHERE key = 'predecessor_database_sha256'",), True,
     "REFUSED_CAREER_SUCCESSOR_PREDECESSOR_DIGEST_MISMATCH"),
    ("resealed_claims_activation", ("UPDATE successor_identity SET value = 'ACTIVATED_DEFAULT' "
                                    "WHERE key = 'default_activation'",), True,
     "REFUSED_CAREER_SUCCESSOR_CLAIMS_ACTIVATION"),
)


#: The lineage fixtures restore into the full copy the first (failed) installed-lane rehearsal left behind. Every
#: case rewrites it from the delivered successor by SQLite backup before breaking it, so reusing it changes nothing a
#: case sees and allocates no new 205 MB copy against the attempt's 4 GiB storage budget (W37A05-11). A fresh copy is
#: made when that file is absent or not the delivered successor's size.
LINEAGE_FIXTURE_REUSE = (VALIDATION_ROOT / "lanes" / "INSTALLED_CONSUMER_C01" / "20260925T062153132164Z"
                         / "lineage_fixtures" / "successor_fixture.sqlite")


def _reseal(conn: sqlite3.Connection) -> None:
    from aggie_analytics.cycle37 import career_successor as cs  # noqa: PLC0415

    for table, columns, key in ((cs.A05_EPISODE_TABLE, cs.A05_EPISODE_COLUMNS, "episode_id"),
                                (cs.A05_DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, "predecessor_episode_id"),
                                (cs.A05_FROM_A04_TABLE, cs.A04_MAP_COLUMNS, "a04_episode_id")):
        digest, count = cs.table_ledger(conn, table, columns, key)
        conn.execute("UPDATE successor_identity SET value = ? WHERE key = ?", (digest, f"ledger::{table}::sha256"))
        conn.execute("UPDATE successor_identity SET value = ? WHERE key = ?", (str(count), f"ledger::{table}::rows"))


def _lineage_fixtures(run: LaneRun, installed: dict[str, Any], delivered: Path) -> dict[str, Any]:
    """One owned full copy of the delivered successor, restored from it before each case, broken one way, resealed
    as a careful forger would, and served through the installed CLI. The delivered file is only read."""

    work = run.fresh("lineage_fixtures")
    reused = LINEAGE_FIXTURE_REUSE.is_file() and LINEAGE_FIXTURE_REUSE.stat().st_size == delivered.stat().st_size
    copy = LINEAGE_FIXTURE_REUSE if reused else work / "successor_fixture.sqlite"
    source = sqlite3.connect(f"file:{delivered.as_posix()}?mode=ro&immutable=1", uri=True)
    fred = source.execute("SELECT episode_id, predecessor_episode_ids, a04_episode_ids, raw_file FROM career_episode_a05 "
                          "WHERE person_display = ? AND team_raw LIKE '%DFO%' LIMIT 1", (FRED,)).fetchone()
    other_parent = source.execute("SELECT predecessor_episode_id FROM career_a05_disposition WHERE "
                                  "predecessor_episode_id != ? ORDER BY predecessor_episode_id LIMIT 1",
                                  (json.loads(fred[1])[0],)).fetchone()[0]
    raw = Path(fred[3])
    tampered = work / "raw" / f"tampered_{raw.name}"
    tampered.parent.mkdir()
    data = bytearray(raw.read_bytes())
    data[-2] = (data[-2] + 1) % 256
    tampered.write_bytes(bytes(data))
    parameters = {"fred": fred[0], "fred_parent": json.loads(fred[1])[0], "fred_a04": json.loads(fred[2])[0],
                  "two_parents": json.dumps([json.loads(fred[1])[0], other_parent]),
                  "fred_extra": re.sub(r":\d+$", ":9", fred[0]), "absent_raw": str(work / "raw" / "never_written.json"),
                  "tampered_raw": str(tampered)}
    results: dict[str, Any] = {"fixture": str(copy), "fixture_reused": reused,
                               "fixture_rule": "restored from the delivered successor by SQLite backup before each case",
                               "parameters": parameters, "cases": {}}
    for name, statements, reseal, code in LINEAGE_CASES:
        target = sqlite3.connect(copy)
        source.backup(target)
        for statement in statements:
            target.execute(statement, {k: v for k, v in parameters.items() if f":{k}" in statement})
        if reseal:
            _reseal(target)
        target.commit()
        target.close()
        # Every one of Fred Mariani's rows is served (the broken row is his DFO row), so a refusal that happens
        # only when a row is served is reached.
        record = base._cli(run, installed, f"lineage_fixture_{name}",
                           ["--career", "--career-successor", copy, "--person", FRED, "--limit", "100"], expect_exit=1)
        text = Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
        results["cases"][name] = {"exit": record.get("exit_code"), "expected_code": code, "resealed": reseal,
                                  "refused_for_the_intended_cause": code in text}
        if code not in text:
            run.problems.append(f"lineage fixture {name} was not refused with {code}")
    source.close()
    missing = base._cli(run, installed, "lineage_fixture_missing_file",
                        ["--career", "--career-successor", work / "absent_successor.sqlite", "--limit", "5"],
                        expect_exit=1)
    text = Path(missing["log_path"]).read_text(encoding="utf-8", errors="replace")
    results["cases"]["missing_file"] = {"exit": missing.get("exit_code"),
                                        "expected_code": "REFUSED_CAREER_SUCCESSOR_ABSENT",
                                        "refused_for_the_intended_cause": "REFUSED_CAREER_SUCCESSOR_ABSENT" in text}
    if "REFUSED_CAREER_SUCCESSOR_ABSENT" not in text:
        run.problems.append("an absent successor file was not refused with REFUSED_CAREER_SUCCESSOR_ABSENT")
    results["delivered_unchanged"] = sha256_file(delivered) == successor_pointer().get("successor_sha256")
    return results


def _roles_units(row: dict[str, Any]) -> list[tuple[Any, Any]]:
    value = row.get("assignments")
    value = json.loads(value) if isinstance(value, str) else (value or [])
    return [(a.get("role"), a.get("unit")) for a in value if isinstance(a, dict)]


def _defensive_pass_game_units(row: dict[str, Any]) -> list[Any]:
    """The units of the row's passing-game coordinator assignments whose own title says defensive."""

    value = row.get("assignments")
    value = json.loads(value) if isinstance(value, str) else (value or [])
    return [a.get("unit") for a in value if isinstance(a, dict) and a.get("role") == "pass_game_coordinator"
            and re.search(r"defensive\s+pass(?:ing)?\s+game", str(a.get("source_title") or ""), re.I)]


def _installed_successor(run: LaneRun, installed: dict[str, Any]) -> None:
    pointer = successor_pointer()
    successor = Path(pointer.get("successor_file", ""))
    digest = sha256_file(successor)
    if not pointer or digest != pointer.get("successor_sha256"):
        run.problems.append("the delivered career successor is absent or does not match its pointer")
        return
    pin = ["--career-successor", successor, "--career-successor-sha256", digest]
    outdir = run.run_dir / "successor_cli"
    outdir.mkdir()
    people = {"cory_undlin": "Cory Undlin", "danny_barrett": "Danny Barrett", "steve_wilks": "Steve Wilks",
              "curome_cox": "Curome Cox", "sam_shade": "Sam Shade", "tom_brookshier": "Tom Brookshier",
              "fred_mariani": FRED, "don_carthel": a4.CARTHEL, "skyler_cassity": a4.CASSITY, "archie_hahn": a4.HAHN,
              "bill_anderson": a4.BILL}
    plan: list[tuple[str, list[Any], int]] = [(f"{key}_successor", ["--person", name, *pin], 0)
                                              for key, name in people.items()]
    plan += [
        ("cory_undlin_2018", ["--career", "--person", "Cory Undlin", "--season", "2018", *pin], 0),
        ("fred_mariani_default", ["--person", FRED], 0),
        ("fred_mariani_a04_legacy", ["--person", FRED, "--career-successor", A4_SUCCESSOR,
                                     "--career-successor-sha256", A4_SUCCESSOR_SHA256], 0),
        ("career_unresolved_role", ["--career", "--uncertainty", "UNRESOLVED_ROLE", "--all", *pin], 0),
        ("career_unresolved_date_template", ["--career", "--uncertainty", "UNRESOLVED_DATE_TEMPLATE", "--all", *pin], 0),
        ("career_unknown_end", ["--career", "--uncertainty", "UNKNOWN_END", "--all", *pin], 0),
        ("career_uncertain_start", ["--career", "--uncertainty", "UNCERTAIN_START", "--all", *pin], 0),
        ("career_tamu_2026", ["--career", "--team", "Texas A&M", "--season", "2026", "--all", *pin], 0),
        ("career_fcs_1985", ["--career", "--season", "1985", "--division", "FCS", "--all", *pin], 0),
        ("career_fbs_2010_oc", ["--career", "--season", "2010", "--division", "FBS", "--role",
                                "offensive_coordinator", "--all", *pin], 0),
        ("career_fbs_2023_pgc", ["--career", "--season", "2023", "--division", "FBS", "--role",
                                 "pass_game_coordinator", "--all", *pin], 0),
        ("career_hc_coaching", ["--career", "--role", "head_coach", "--family", "COACHING", "--all", *pin], 0),
        ("career_season_2018", ["--career", "--season", "2018", "--all", *pin], 0),
    ]
    plan += [(name, args, 1) for name, args in (
        ("refuse_successor_with_legacy_audit", ["--career", "--legacy-audit", *pin]),
        ("refuse_unknown_uncertainty", ["--career", "--uncertainty", "NOT_A_CLASS", *pin]),
        ("refuse_uncertainty_without_successor", ["--career", "--uncertainty", "UNKNOWN_END"]),
        ("refuse_pin_without_successor", ["--career", "--career-successor-sha256", digest]),
        ("refuse_wrong_pin", ["--career", "--career-successor", successor, "--career-successor-sha256", "0" * 64]),
        ("refuse_successor_on_team_staff", ["--team", "Texas A&M", "--season", "2026", *pin]))]
    results: dict[str, Any] = {}
    for name, args, expected in plan:
        record = base._cli(run, installed, name, args, expect_exit=expected, save=outdir / f"{name}.json.gz")
        results[name] = {"exit": record.get("exit_code"), "expected_exit": expected,
                         "result": record["result_against_expectation"], "args": [str(a) for a in args]}
        if name in a4.SUCCESSOR_REFUSALS:
            text = Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
            results[name]["refused_for_the_intended_cause"] = a4.SUCCESSOR_REFUSALS[name] in text
            if a4.SUCCESSOR_REFUSALS[name] not in text:
                run.problems.append(f"{name} was not refused for its intended cause ({a4.SUCCESSOR_REFUSALS[name]})")
    run.extra["successor_cli_results"] = results
    failed = [name for name, row in results.items() if row.get("result") == FAIL]
    if failed:
        run.problems.append(f"installed successor cases not as expected: {failed}")

    def load(name: str) -> list[dict[str, Any]]:
        payload = base._gz_json(outdir / f"{name}.json.gz") or {}
        return payload.get("rows") or payload.get("career_episodes") or []

    def pick(rows: list[dict[str, Any]], **match: Any) -> list[dict[str, Any]]:
        return [r for r in rows if all(str(v) in str(r.get(k)) for k, v in match.items())]

    cory = load("cory_undlin_successor")
    cory_2018 = load("cory_undlin_2018")
    danny = load("danny_barrett_successor")
    steve = load("steve_wilks_successor")
    named: dict[str, Any] = {
        "cory_undlin_2018_eagles": [{k: r.get(k) for k in ("episode_id", "employer_display", "start", "end",
                                                            "years_raw", "date_basis")}
                                    for r in pick(cory_2018, employer_display="Philadelphia Eagles")],
        "cory_undlin_nested_1007": [{k: r.get(k) for k in ("episode_id", "start", "end", "years_raw", "date_basis")}
                                    for r in cory if str(r.get("episode_id", "")).endswith(":COACHING:1007:0")],
        "danny_barrett_1003": [{k: r.get(k) for k in ("episode_id", "start", "end", "years_raw", "date_basis")}
                               for r in danny if str(r.get("episode_id", "")).endswith(":COACHING:1003:0")],
        "steve_wilks_inherited": [{k: r.get(k) for k in ("episode_id", "start", "end", "date_basis", "date_parent")}
                                  for r in steve if r.get("date_basis") == "INHERITED_FROM_PARENT_ITEM"],
        "defensive_pass_game_units": {key: [(r.get("employer_display"), _defensive_pass_game_units(r))
                                            for r in load(f"{key}_successor") if _defensive_pass_game_units(r)]
                                      for key in ("curome_cox", "sam_shade", "steve_wilks")},
        "tom_brookshier": [(r.get("start"), r.get("end"), r.get("years_raw")) for r in load("tom_brookshier_successor")
                           if "NFL Year|1956" in str(r.get("years_raw"))],
    }
    fred = load("fred_mariani_successor")
    named["fred_mariani_dfo_not_head_coach"] = bool(pick(fred, team_raw="DFO")) and all(
        "head_coach" not in [role for role, _ in _roles_units(r)] for r in pick(fred, team_raw="DFO"))
    stamford = [r for r in load("bill_anderson_successor") if r.get("employer_display") == "Stamford HS (TX)"]
    named["stamford_controls"] = [(r.get("role_basis"), [role for role, _ in _roles_units(r)]) for r in stamford]
    holds = {
        "cory_2018_eagles_2015_2019": any(r["start"] == 2015 and r["end"] == 2019
                                          for r in named["cory_undlin_2018_eagles"]),
        "cory_nested_keeps_its_own_dates": any(r["start"] == 2005 and r["end"] == 2006
                                               and r["date_basis"] == "CHILD_DATE_WITHOUT_BALANCED_PARENTHESES"
                                               for r in named["cory_undlin_nested_1007"]),
        "danny_nested_keeps_1998": any(r["start"] == 1998 and r["end"] == 1998 for r in named["danny_barrett_1003"]),
        "steve_wilks_inheritance_names_its_parent": bool(named["steve_wilks_inherited"]) and all(
            (r.get("date_parent") or {}).get("row_index") for r in named["steve_wilks_inherited"]
            if isinstance(r.get("date_parent"), dict)) and all(
            r.get("date_parent") for r in named["steve_wilks_inherited"]),
        "defensive_pgc_is_defense": all(unit == "DEFENSE" for rows in named["defensive_pass_game_units"].values()
                                        for _, units in rows for unit in units)
        and all(named["defensive_pass_game_units"][key] for key in ("curome_cox", "sam_shade", "steve_wilks")),
        "brookshier_range_read": any(r[0] == 1956 and r[1] == 1961 for r in named["tom_brookshier"]),
        "fred_dfo_not_head_coach": named["fred_mariani_dfo_not_head_coach"],
        "stamford_head_coach_kept": len(stamford) == 3 and any(
            b == "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL" and "head_coach" in roles for b, roles in named["stamford_controls"]),
    }
    named["holds"] = holds
    run.extra["successor_named_cases"] = named
    for key, value in holds.items():
        if not value:
            run.problems.append(f"installed successor named case {key} does not hold")
    # Full pagination and the filtered answers against the independent oracle.
    oracle = _successor_oracle(DELIVERED_DB, successor)
    pages = run.run_dir / "successor_pages"
    pages.mkdir()
    run.extra["successor_pagination"] = base._paginate(run, installed, "career_successor", ["--career", *pin],
                                                       "episode_id", 10000, oracle["order"], pages)
    filtered = {}
    for name, flt in (("career_tamu_2026", {"team": "Texas A&M", "season": 2026}),
                      ("career_fcs_1985", {"season": 1985, "division": "fcs"}),
                      ("career_fbs_2010_oc", {"season": 2010, "division": "fbs", "role": "offensive_coordinator"}),
                      ("career_fbs_2023_pgc", {"season": 2023, "division": "fbs", "role": "pass_game_coordinator"}),
                      ("career_hc_coaching", {"role": "head_coach", "family": "COACHING"}),
                      ("career_season_2018", {"season": 2018}),
                      ("career_unresolved_role", {"uncertainty": "UNRESOLVED_ROLE"}),
                      ("career_unresolved_date_template", {"uncertainty": "UNRESOLVED_DATE_TEMPLATE"}),
                      ("career_unknown_end", {"uncertainty": "UNKNOWN_END"}),
                      ("career_uncertain_start", {"uncertainty": "UNCERTAIN_START"}),
                      ("cory_undlin_2018", {"person": "Cory Undlin", "season": 2018}),
                      *((f"{key}_successor", {"person": name}) for key, name in people.items())):
        rows = load(name)
        cli_ids = {str(row["episode_id"]) for row in rows}
        expected = a4._successor_filter(oracle["rows"], oracle["programs"], **flt)
        filtered[name] = {"cli": len(cli_ids), "oracle": len(expected), "equal": cli_ids == expected}
        if cli_ids != expected:
            run.problems.append(f"successor filter {name} differs from the independent filter")
    run.extra["successor_filtered_oracle"] = filtered
    coverage = {"predecessor_rows": len(oracle["predecessor_ids"]), "dispositions": len(oracle["dispositions"]),
                "predecessor_identity_sets_equal": set(oracle["dispositions"]) == oracle["predecessor_ids"],
                "a04_rows": len(oracle["a04_ids"]), "a04_mapped": len(oracle["a04_map"]),
                "a04_identity_sets_equal": set(oracle["a04_map"]) == oracle["a04_ids"],
                "successor_rows": len(oracle["order"]),
                "all_versioned": all(i.startswith("C37A05:") for i in oracle["order"]),
                "identity": {k: v for k, v in oracle["identity"].items() if not k.startswith("ledger::")}}
    run.extra["successor_coverage"] = coverage
    if not (coverage["predecessor_identity_sets_equal"] and coverage["a04_identity_sets_equal"]
            and coverage["all_versioned"] and coverage["predecessor_rows"] == 72070 and coverage["a04_rows"] == 73082):
        run.problems.append(f"successor coverage does not hold: {coverage}")
    run.extra["successor_locators"] = locators = base._verify_career_locators(pages, "career_successor")
    if locators["rows"] != len(oracle["order"]) or locators["raw_file_digest_mismatch"] or \
            locators["span_mismatch"] or locators["wikitext_not_found"] or locators["raw_file_absent"]:
        run.problems.append(f"successor locators do not all resolve to their raw bytes: {locators}")
    run.extra["lineage_fixtures"] = _lineage_fixtures(run, installed, successor)


def _manager_a4_replays(run: LaneRun, installed: dict[str, Any]) -> None:
    """The manager's Attempt 4 challenges against this wheel: its semantic census over the Attempt 5 successor, and
    its resealed challenge over its own Attempt 4 subject, which this consumer must now refuse."""

    run.exceptions.append("The manager's Attempt 4 challenges start the installed bas-staff-query launcher (a native "
                          "executable) with their own minimal environment; the guard refuses a native child, so they "
                          "run without the lane guard. They open the delivered files read-only and write only in their "
                          "owned fixture directories; the snapshots measure them.")
    successor = Path(successor_pointer()["successor_file"])
    fixture = run.fresh("mgr_a4_census_fixture")
    copy, replay = a4._replay_from(run, MANAGER_A4, "career_semantic_census.py", adapt={
        r"S=Path(r'C:\BatteredAggieSyndrome.data\ops\cycle37\attempt04\release\successor\CAREER_SUCCESSOR_A04.sqlite')":
            f"S=Path(r'{successor}')",
        f"V=Path(r'{A4_VENV_LITERAL}')": f"V=Path(r'{installed['venv']}')",
        f"F=Path(r'{MANAGER_FIXTURE_LITERAL}')": f"F=Path(r'{fixture}')",
        "select * from career_episode_a04": "select * from career_episode_a05"})
    record = run.run("manager_a4_career_semantic_census_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None))
    census = _json_file(copy.parent / "CAREER_SEMANTIC_CENSUS.json") or {}
    defensive = census.get("defensive_pass_game_rows") or []
    calls = {Path(str(row.get("stdout"))).name.split(".")[0]: {"exit": row.get("exit"), "row_count": row.get("row_count")}
             for row in census.get("consumer_calls") or []}
    verdict = {**replay, "exit": record.get("exit_code"), "successor_sha256": census.get("successor_sha256"),
               "year_template_population": census.get("year_template_population"),
               "collapsed_to_first_year": census.get("collapsed_to_first_year"),
               "defensive_rows": len(defensive),
               "defensive_units": dict(collections.Counter((r.get("assignment") or {}).get("unit") for r in defensive)),
               "consumer_calls": calls}
    # A row the census marks collapsed must be a template that itself states one season ({{nfly|2010|2010}}).
    collapsed = [r for r in census.get("range_rows") or [] if r.get("collapsed_to_first")]
    verdict["collapsed_rows_whose_template_states_one_season"] = sum(
        1 for r in collapsed if str(r.get("template_endpoint")) == str(r.get("start")))
    verdict["holds"] = (all(str(r.get("template_endpoint")) == str(r.get("start")) for r in collapsed)
                        and bool(defensive)
                        and all((r.get("assignment") or {}).get("unit") == "DEFENSE" for r in defensive)
                        and (calls.get("cory-2018") or {}).get("row_count", 0) >= 1
                        and all(row.get("exit") == 0 for row in calls.values()))
    run.extra["manager_a4_career_semantic_census"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's Attempt 4 semantic census does not hold against this consumer: {verdict}")
    fixture = run.fresh("mgr_a4_successor_fixture")
    copy, replay = a4._replay_from(run, MANAGER_A4, "successor_challenge.py", adapt={
        f"F=Path(r'{MANAGER_FIXTURE_LITERAL}')": f"F=Path(r'{fixture}')",
        f"V=Path(r'{A4_VENV_LITERAL}')": f"V=Path(r'{installed['venv']}')"})
    record = run.run("manager_a4_successor_challenge_replay", [run.python, "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None))
    challenge = _json_file(copy.parent / "SUCCESSOR_CHALLENGE.json") or {}
    cases = {row["label"]: row for row in challenge.get("cases") or []}
    summary = {label: {"exit": row.get("exit"), "row_count": row.get("row_count"),
                       "refusal": next((code for code in re.findall(r"REFUSED_[A-Z_]+", row.get("stderr") or "")), None)}
               for label, row in cases.items()}
    verdict = {**replay, "exit": record.get("exit_code"), "cases": summary,
               "subject_unchanged": challenge.get("subject_sha_before") == challenge.get("subject_sha_after")
               == A4_SUCCESSOR_SHA256}
    verdict["holds"] = (verdict["subject_unchanged"]
                        and (cases.get("successor-genuine-positive") or {}).get("exit") == 0
                        and all((cases.get(label) or {}).get("exit") not in (0, None)
                                for label in ("successor-unsealed-missing-row", "successor-resealed-missing-row",
                                              "successor-resealed-missing-raw")))
    run.extra["manager_a4_successor_challenge"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the manager's resealed successor challenge is not refused by this consumer: {verdict}")


def _manager_a3_career_challenge(run: LaneRun, installed: dict[str, Any]) -> None:
    """The Attempt 3 manager's career challenge against this wheel (as Attempt 4 replayed it)."""

    copy, replay = a4._replay_from(run, a4.MANAGER_A3, "career_challenge.py", adapt={
        r"V=Path(r'C:\BatteredAggieSyndrome.packaging\c37a03\b\34986ede\venv')": f"V=Path(r'{installed['venv']}')"})
    shutil.copy2(a4.MANAGER_A3 / "DELIVERED_DATABASE_INVENTORY.json", copy.parent / "DELIVERED_DATABASE_INVENTORY.json")
    record = run.run("manager_a3_career_challenge_installed", [installed["python"], "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None))
    challenge = _json_file(copy.parent / "CAREER_SEMANTIC_REPRODUCTION.json") or {}
    parser = challenge.get("parser") or {}
    teams = parser.get("teams") or {}
    site = str(installed["venv"] / "Lib" / "site-packages").lower()
    unresolved = {raw: (teams.get(raw) or {}).get("role_basis") for raw in teams
                  if any(code in raw for code in ("DFO", "STQC", "(SA)", "UNRECOGNIZED_JOB"))}
    verdict = {**replay, "exit": record.get("exit_code"), "parser_import": parser.get("import"),
               "parser_from_site_packages": str(parser.get("import", "")).lower().startswith(site),
               "unknown_suffixes_unresolved": unresolved,
               "default_answer_row_count": len(challenge.get("installed_rows") or [])}
    verdict["holds"] = verdict["parser_from_site_packages"] and len(unresolved) == 4 and all(
        basis == "UNRESOLVED_PARENTHETICAL" for basis in unresolved.values())
    run.extra["manager_a3_career_challenge"] = verdict
    if not verdict["holds"]:
        run.problems.append(f"the Attempt 3 manager's career challenge does not hold: {verdict}")


def lane_installed_consumer_c01(run: LaneRun) -> None:
    base.lane_installed_consumer_c01(run)
    raw = run.extra.get("installed")
    if not raw:
        return
    installed = {key: Path(value) for key, value in raw.items()}
    _installed_successor(run, installed)
    run.extra["manager_a3_installed"] = a4._manager_a3_admission_pit(
        run, "installed", installed["python"], installed["python"], base._installed_env(run))
    site = str(installed["venv"] / "Lib" / "site-packages").lower()
    for kind in ("admission", "pit"):
        modules = (run.extra["manager_a3_installed"].get(kind) or {}).get("modules") or {}
        outside = [name for name, row in modules.items() if not str(row.get("path", "")).lower().startswith(site)]
        if outside or not modules:
            run.problems.append(f"the installed manager {kind} probe did not import from the fresh wheel: {outside}")
    _manager_a3_career_challenge(run, installed)
    _manager_a4_replays(run, installed)


# ---- the local integration candidate --------------------------------------------------------------------


def _history_policy(head: str) -> dict[str, Any]:
    """The commit-class policy over the candidate's first-parent history: every subject classified, and no two
    consecutive process-only commits among the commits the candidate adds."""

    subjects = git_out("log", "--first-parent", "--format=%H %s", "-n", "30", head,
                       repo=CANDIDATE_WORKTREE).splitlines()
    rows = [{"sha": line[:40], "subject": line[41:],
             "class": (re.match(r"^\[(\w+)\]", line[41:]) or [None, "untagged"])[1]} for line in subjects]
    streaks = [rows[i]["sha"] for i in range(len(rows) - 1)
               if rows[i]["class"] == rows[i + 1]["class"] == "process"]
    # The candidate adds exactly one commit; being [material], it cannot start or extend a process-only streak.
    # Main's own earlier streaks, if any, are reported as context, not as the candidate's.
    return {"first_parent_recent": rows[:10], "candidate_commit_class": rows[0]["class"] if rows else None,
            "consecutive_process_pairs_in_main_history": [sha for sha in streaks if rows and sha != rows[0]["sha"]],
            "holds": bool(rows) and rows[0]["class"] == "material"}


def lane_local_integration_candidate(run: LaneRun) -> None:
    description = candidate.describe()
    run.extra["candidate"] = description
    head = description.get("candidate_head")
    if not head:
        run.problems.append("the local integration candidate does not exist")
        return
    record_files = sorted(CANDIDATE_RECORDS.glob("CANDIDATE_RECORD_*.json"))
    creation = _json_file(record_files[-1]) if record_files else {}
    run.extra["candidate_creation_record"] = {"file": str(record_files[-1]) if record_files else None,
                                              "sha256": sha256_file(record_files[-1]) if record_files else None,
                                              "refs_changed": (creation or {}).get("refs_changed"),
                                              "protected_paths_written_to_disk":
                                                  (creation or {}).get("protected_paths_written_to_disk")}
    repair_head = run.binding["head"]
    status = base.porcelain(CANDIDATE_WORKTREE)
    skip = git_out("ls-files", "-v", "--", *candidate.PROTECTED_PATHS, repo=CANDIDATE_WORKTREE).splitlines()
    tree_checks = {
        "parent_is_main": description.get("candidate_parents") == [MAIN_SHA],
        "main_ref_unchanged": description.get("main_ref") == MAIN_SHA,
        "built_from_this_repair_head": description.get("repair_head") == repair_head,
        "tree_equals_repair_tree_except_protected_paths": description.get("only_protected_paths_differ") is True,
        "protected_paths_keep_main_bytes": description.get("protected_paths_equal_main") is True,
        "protected_paths_never_written": not any((CANDIDATE_WORKTREE / p).exists() for p in candidate.PROTECTED_PATHS),
        "protected_entries_skip_worktree": all(line[:1] == "S" for line in skip) and bool(skip),
        "worktree_clean": not status,
        "worktree_head_is_candidate": git_out("rev-parse", "HEAD", repo=CANDIDATE_WORKTREE) == head,
        "creation_changed_only_the_new_ref": (creation or {}).get("only_the_new_branch_ref_changed") is True,
    }
    run.extra["candidate_tree_checks"] = tree_checks
    run.extra["candidate_history_policy"] = policy = _history_policy(head)
    tree_checks["history_policy"] = policy["holds"]
    for name, held in tree_checks.items():
        if not held:
            run.problems.append(f"integration candidate: {name} does not hold")
    # The consumer built from the candidate's own tree, installed fresh and queried.
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
                                              "--disable-pip-version-check", wheels[0], C01_WHEEL],
            cwd=stage, env=base._installed_env(run), timeout=1800)
    installed = {"stage": stage, "venv": venv, "python": python, "script": venv / "Scripts" / "bas-staff-query.exe",
                 "wheel": wheels[0]}
    pointer = successor_pointer()
    pin = ["--career-successor", pointer["successor_file"], "--career-successor-sha256", pointer["successor_sha256"]]
    outdir = run.run_dir / "candidate_cli"
    outdir.mkdir()
    for name, args, expected in (("schema", ["--schema"], 0), ("bill_anderson_default", ["--person", a4.BILL], 0),
                                 ("cory_undlin_2018_successor", ["--career", "--person", "Cory Undlin", "--season",
                                                                 "2018", *pin], 0),
                                 ("refuse_wrong_pin", ["--career", "--career-successor", pointer["successor_file"],
                                                       "--career-successor-sha256", "0" * 64], 1)):
        base._cli(run, installed, f"candidate_{name}", args, expect_exit=expected, save=outdir / f"{name}.json.gz")
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
                                     if r.get("employer_display") == "Philadelphia Eagles"]}
    consumer["holds"] = bool(listed) and not different and (2015, 2019) in [tuple(x) for x in consumer["cory_2018_eagles"]]
    run.extra["candidate_consumer"] = consumer
    if not consumer["holds"]:
        run.problems.append(f"the consumer built from the candidate tree does not hold: {consumer}")
    # The candidate's own suites, from its worktree, under the guard (the candidate worktree is guarded).
    env = run.env(pythonpath=os.pathsep.join((str(CANDIDATE_WORKTREE), str(CANDIDATE_WORKTREE / "src"))))
    records_path, summary_path = run.census_dir / "candidate_suites.records.jsonl", run.census_dir / "candidate_suites.summary.json"
    run.run("candidate_suites", [run.python, "-B", "-m", "aggie_analytics.validation.unittest_census", *CANDIDATE_SUITES,
                                 "--records", records_path, "--summary", summary_path, "--selected-root",
                                 CANDIDATE_WORKTREE, "-v"], cwd=CANDIDATE_WORKTREE / "tests", kind="TEST", env=env,
            census=(records_path, summary_path), timeout=3600)
    # A characterization of the withheld review controls: their suites run from an export of the candidate commit
    # (its tests with main's protected controls), and the outcome -- not a pass/fail gate of this lane -- is
    # recorded for the owner's integration decision. The export is under the packaging stage, never a worktree.
    control_tar, control_root = stage / "control.tar", stage / "control"
    run.run("git_archive_candidate_controls", ["git", "--no-optional-locks", "-C", CANDIDATE_WORKTREE, "archive",
                                               "--format=tar", "-o", control_tar, head, "--", *CONTROL_EXPORT],
            env=run.env())
    with tarfile.open(control_tar) as bundle:
        bundle.extractall(control_root, filter="data")
    control_env = run.env(pythonpath=os.pathsep.join((str(control_root), str(control_root / "src"))))
    exported = {path: (sha256_file(control_root / path) if (control_root / path).is_file() else None)
                for path in candidate.PROTECTED_PATHS}
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
    control = run.run("candidate_review_control_characterization", [run.python, "-B", "-c", script, *CONTROL_SUITES],
                      cwd=control_root / "tests", env=control_env,
                      note="Characterization only, from an export of the candidate commit: the candidate keeps main's "
                           "review controls; the repair branch's changes to them are withheld pending an owner "
                           "decision.")
    run.extra["candidate_review_control_characterization"] = {
        "suites": CONTROL_SUITES, "exit": control.get("exit_code"), "outcome": base._stdout_json(control),
        "export": {"root": str(control_root), "paths": list(CONTROL_EXPORT), "protected_files_sha256": exported},
        "withheld_paths": [row["path"] for row in description.get("protected_paths") or [] if row["repair"] != row["main"]],
        "meaning": ("The repair branch changed these review controls; the candidate keeps main's. Tests written for the "
                    "branch's controls may fail against main's; that is the recorded effect of withholding them, "
                    "not a defect of the candidate's consumer.")}
    after = candidate_state()
    run.extra["candidate_worktree_after"] = after
    if base.porcelain(CANDIDATE_WORKTREE):
        run.problems.append("the candidate worktree changed during the lane")


# ---- mounted, unmounted, platform and packet lanes ------------------------------------------------------


def _attempt4_final(lane: str) -> dict[str, Any]:
    rows = [json.loads(line) for line in (ATTEMPT4_ROOT / "lanes" / "RUNS.jsonl").read_text(encoding="utf-8")
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
    a4final = _attempt4_final("FULL_FINAL_MOUNTED")
    comparison: dict[str, Any] = {"attempt4_receipt": a4final.get("receipt"),
                                  "attempt4_receipt_sha256": a4final.get("receipt_sha256"),
                                  "attempt4_run": a4final.get("run"), "attempt4_result": a4final.get("result")}
    if a4final:
        a4_log = Path(next(c["log_path"] for c in a4final["data"]["commands"]
                           if c["lane"].endswith("full_suite_mounted")))
        before = base._log_identities(a4_log)
        persisting = sorted(set(final["failed_or_errored"]) & set(before["failed_or_errored"]))
        new = sorted(set(final["failed_or_errored"]) - set(before["failed_or_errored"]))
        final_causes = base._failure_causes(log, persisting)
        before_causes = base._failure_causes(a4_log, persisting)
        comparison.update({
            "attempt4_log": str(a4_log), "attempt4_log_sha256": sha256_file(a4_log),
            "attempt4_tests_run": before["tests_run"], "final_tests_run": final["tests_run"],
            "attempt4_failed_or_errored": before["failed_or_errored"],
            "persisting": persisting, "new_in_attempt5": new,
            "no_longer_failing": sorted(set(before["failed_or_errored"]) - set(final["failed_or_errored"])),
            "new_failure_causes": base._failure_causes(log, new),
            "persisting_same_cause": sorted(i for i in persisting if final_causes[i] == before_causes[i]),
            "persisting_changed_cause": {i: {"attempt4": before_causes[i], "attempt5": final_causes[i]}
                                         for i in persisting if final_causes[i] != before_causes[i]},
        })
        if new:
            run.problems.append(f"new failing identities relative to Attempt 4: {new}")
    run.extra["attempt4_comparison"] = comparison


def lane_strict_mounted(run: LaneRun) -> None:
    base.lane_strict_mounted(run)
    final = [row["identity"] for row in run.extra.get("strict_findings") or []]
    a4final = _attempt4_final("STRICT_MOUNTED")
    comparison: dict[str, Any] = {"attempt4_receipt": a4final.get("receipt"), "attempt4_run": a4final.get("run")}
    if a4final:
        before = [row["identity"] for row in (a4final["data"].get("details") or {}).get("strict_findings") or []]
        comparison.update({"attempt4_findings": before, "final_findings": final,
                           "persisting": sorted(set(final) & set(before)),
                           "new_in_attempt5": sorted(set(final) - set(before)),
                           "no_longer_reported": sorted(set(before) - set(final))})
        if comparison["new_in_attempt5"]:
            run.problems.append(f"new strict findings relative to Attempt 4: {comparison['new_in_attempt5']}")
    run.extra["attempt4_comparison"] = comparison


def lane_true_unmounted(run: LaneRun) -> None:
    base.lane_true_unmounted(run)


def lane_platform_carry(run: LaneRun) -> None:
    a4.lane_platform_carry(run)


def lane_final_packet(run: LaneRun) -> None:
    a4.lane_final_packet(run)


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
    print(f"Cycle #37 \u2014 Attempt #5 \u2014 lane {args.lane} run {run.stamp}"
          + (" (REHEARSAL, NOT EVIDENCE)" if args.rehearsal else ""))
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
    gate = None
    if args.lane in GATED:
        gate = qualification(out_root, run.binding["head"], run.binding["guard_sha256"])
        if not gate["holds"]:
            blocked.append("WRITE_PROTECTION and STORAGE_ADMISSION have not both passed at this head with these guard "
                           f"bytes: {gate}")
    ledger = storage.Ledger(STORAGE_LEDGER)
    reservation = None
    if not blocked:
        try:
            estimate = LANE_ESTIMATES[args.lane] + (REHEARSAL_CANDIDATE_BYTES if args.rehearsal and
                                                    args.lane == "LOCAL_INTEGRATION_CANDIDATE" else 0)
            reservation = ledger.reserve(f"LANE {args.lane} {run.stamp}" + (" (rehearsal)" if args.rehearsal else ""),
                                         estimate, note=f"head {run.binding['head']}")
        except storage.AdmissionRefused as refusal:
            blocked.append(f"storage admission refused the lane before any effect: {refusal.record.get('reason')}")
    if not blocked and args.rehearsal and args.lane == "LOCAL_INTEGRATION_CANDIDATE":
        try:
            run.extra["rehearsal_scratch_candidate"] = rehearse_candidate(run)
        except (SystemExit, Exception) as error:  # noqa: BLE001 - a refused scratch candidate blocks the rehearsal
            blocked.append(f"the rehearsal's scratch candidate could not be prepared: {error}")
    before = base.scope_before()
    candidate_before = candidate_state()
    if blocked:
        result, reason = BLOCKED, "; ".join(blocked)
        print(f"[{args.lane}] BLOCKED: {reason}")
    else:
        try:
            LANE_FUNCTIONS[args.lane](run)
        except Exception as error:  # noqa: BLE001 - a crashed lane is a recorded failure, never a pass
            import traceback

            traceback.print_exc(file=sys.stdout)
            run.problems.append(f"the lane raised {type(error).__name__}: {error}")
        result, reason = base.decide(run, (contract.get("_lane") or {}).get("kind", "CHECK"))
    scope = base.scope_after(before)
    candidate_after = candidate_state()
    reconciled = ledger.reconcile(reservation["token"], note=f"lane {result}") if reservation else None
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
    if reconciled and reconciled.get("underestimated"):
        reason = f"{reason}; the lane used {reconciled['operation_added_bytes']} bytes, past its reservation"
    guard_events = []
    if run.guard_log.is_file():
        guard_events = [json.loads(line) for line in run.guard_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    receipt = {
        "label": f"Cycle #37 \u2014 Attempt #5 \u2014 lane {args.lane} {result}"
                 + (" (REHEARSAL, NOT EVIDENCE)" if args.rehearsal else ""),
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
        "storage": {"ledger": str(STORAGE_LEDGER), "reservation": reservation, "reconcile": reconciled},
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
