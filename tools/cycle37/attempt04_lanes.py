r"""Cycle #37 — Attempt #4 — the lane runner (R37A04-07-A).

    attempt04_lanes.py --lane <ID> --contract <cycle_contract.json> --out-root <attempt root>

This is the preserved Attempt 3 runner (``attempt03_lanes``) rebound to the Attempt 4 contract, roots and
evidence, with the lanes Attempt 4 changes. Everything the Attempt 3 runner binds per run is still bound here:
the issued contract by its sealed digest, the committed source subject (branch, head, tree, source digest,
descent from the issued base, a clean tree before and after), the interpreter and its distributions, the
import origins of every module this attempt changed, the delivered database by digest, a before/after
measurement of the data root and ``C:\All-22`` plus the heads of the main checkout and the integration
worktree, and credential removal from every child.

What Attempt 4 changes:

* **Git children are confined.** Guarded children run under the v37.4 canonical write guard, which admits a
  ``git`` child only in an exact read form under a controlled configuration and environment, and a
  repository-building ``init/add/commit/config`` only inside the declared Git scratch root
  (``BAS_CANONICAL_WRITE_GIT_SCRATCH``, this attempt's own packaging root). The Attempt 3 validation and
  packaging roots are guarded too: they are denied write roots of this contract.
* **WRITE_PROTECTION qualifies the guard first** with the guard suites, the Attempt 2 manager probe and the
  Attempt 3 manager's Git alias probe, replayed in an owned directory. Mounted lanes follow it.
* **Admission and PIT** replay the Attempt 3 manager's independent probes from source and from the fresh
  installed wheel, beside the Attempt 2 probes and this attempt's own suites.
* **CAREER_SUCCESSOR** rebuilds the raw census and the explicit career successor from the committed subject,
  requires the rebuild to reproduce the delivered successor's ledgers, accounts every predecessor row and every
  screened candidate, and keeps the Cycle 29 claim successor checks.
* **INSTALLED_CONSUMER_C01** serves the delivered successor through the installed ``bas-staff-query`` with full
  pagination and filters against an independent SQL/Python oracle, the named corrections and controls, and
  refusals for tampered, missing, duplicated and wrong-predecessor successors -- while the default answer stays
  the delivered release's own.
* **FULL_FINAL_MOUNTED / STRICT_MOUNTED** compare by identity with the Attempt 3 final lanes (20 failing test
  identities, 5 strict findings) as well as with the Attempt 2 baseline.

A lane decides what its commands did. It does not decide scientific acceptance, and it cannot turn an inherited
red lane green.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt03_lanes as base  # noqa: E402  (the preserved Attempt 3 runner this module rebinds)
from attempt03_lanes import (  # noqa: E402
    BLOCKED,
    FAIL,
    PASS,
    DATA_ROOT,
    DELIVERED_DB,
    DELIVERED_DB_SHA256,
    MAIN_CHECKOUT,
    INTEGRATION_WORKTREE,
    ALL22,
    ATTEMPT2_ROOT,
    C01_WHEEL,
    C01_WHEEL_SHA256,
    GOVERNANCE,
    WORKTREE,
    Tee,
    credential_scrub,
    git,
    git_out,
    porcelain,
    sha256_bytes,
    sha256_file,
    source_digest,
    utc_now,
    write_json,
)

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 4
CYCLE_ID = "CYCLE-37"
ATTEMPT_ID = "ATTEMPT-04-20260924"
RUNNER_VERSION = "BAS-C37-ATTEMPT04-LANES-v1"
BASE_SHA = "ade8f25a814ed68c19c2b451a93e2651787bf592"
BRANCH = "codex/BAT-706-cycle37-rework"
LANES = (
    "START_CONTEXT", "WRITE_PROTECTION", "SOURCE_ADMISSION", "SOURCE_HARNESS", "SOURCE_REGRESSIONS",
    "INSTALLED_CONSUMER_C01", "CAREER_SUCCESSOR", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED", "TRUE_UNMOUNTED",
    "PLATFORM_CARRY", "FINAL_PACKET",
)

EVIDENCE_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt04"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a04")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37a04")
ATTEMPT3_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt03"
VALIDATION_A03 = Path(r"C:\BatteredAggieSyndrome.validation\c37a03")
PACKAGING_A03 = Path(r"C:\BatteredAggieSyndrome.packaging\c37a03")
MANAGER_A3 = DATA_ROOT / "ops" / "manager_reviews" / "cycle37" / "attempt03" / "review-20260924T212311Z"
#: The pointer to the delivered explicit career successor; written once when the successor is delivered.
SUCCESSOR_POINTER = EVIDENCE_ROOT / "release" / "CAREER_SUCCESSOR_POINTER.json"
AFTER_COMMENTS = (("BAT-706", "C37-A04-AFTER-HANDOFF-BAT-706"), ("BAT-708", "C37-A04-AFTER-HANDOFF-BAT-708"))
PLATFORM_TOOL = "tools/cycle37/attempt04_platform.py"
OUTPUTS_TOOL = "tools/cycle37/attempt04_outputs.py"
FRED = "Fred Mariani"
CARTHEL = "Don Carthel"
#: A student-assistant code and a novel non-vocabulary role, as the cached revisions write them.
CASSITY = "Skyler Cassity"
HAHN = "Archie Hahn (sprinter)"
BILL = base.BILL

BOUND_MODULES = base.BOUND_MODULES + (
    "aggie_analytics.cycle37.career_infobox",
    "aggie_analytics.cycle37.career_successor",
)
ADMISSION_SUITES = base.ADMISSION_SUITES + ("test_cycle37_a04_scoring_pit_admission",)
GUARD_SUITES = ("test_cycle37_canonical_write_guard", "test_cycle37_a04_git_child_guard")
CAREER_SUITES = ("test_cycle37_a04_career_successor", "test_cycle37_career_reparse")
CLAIM_SUITES = base.CLAIM_SUITES
#: Attempt 3's regression set, unchanged, plus this attempt's own suites. The guard suites stay in
#: WRITE_PROTECTION: they install and strip guards themselves and cannot run inside one.
REGRESSION_SUITES = base.REGRESSION_SUITES + (
    "test_cycle37_a04_scoring_pit_admission",
    "test_cycle37_a04_career_successor",
    "test_repo_integrity_tools",
)


def rebind() -> None:
    """Point the preserved Attempt 3 runner at the Attempt 4 contract, roots, suites and grants."""

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
                                                 VALIDATION_A03, PACKAGING_A03))
    # The All-22 lane system works concurrently in its own areas: its Instructions workspace (Attempt 3 excluded its
    # cycles/ scratch; Attempt 4 measured it writing state/), its worktrees, and the .git metadata of the owner
    # repositories it commits to (evidence/scope/EXTERNAL_WRITER_*.json: each created inside a lane run, with no lane
    # command naming All-22 and no guard write event there). These are excluded from the write measurement only;
    # the owner repositories' checked-out files and every other All-22 path stay measured, and the guard still
    # refuses every guarded lane child any write under All-22 and confines its git children to read-only builtins.
    repositories = sorted((ALL22 / "repos").iterdir()) if (ALL22 / "repos").is_dir() else []
    base.ALL22_EXCLUDED = (ALL22 / "Instructions" / "LANE_SYSTEM_DEVELOPMENT_PM_WORKER_V2", ALL22 / "worktrees",
                           *(repo / ".git" for repo in repositories if (repo / ".git").exists()))
    base.AFTER_COMMENTS = AFTER_COMMENTS
    base.BOUND_MODULES = BOUND_MODULES
    base.ADMISSION_SUITES = ADMISSION_SUITES
    base.REGRESSION_SUITES = REGRESSION_SUITES


class LaneRun(base.LaneRun):
    """The Attempt 3 lane context with the v37.4 guard's Git scratch root declared for guarded children."""

    def env(self, *, guarded: bool = True, network: bool = False, pythonpath: str | None = "source",
            extra: dict[str, str | None] | None = None) -> dict[str, str | None]:
        env = super().env(guarded=guarded, network=network, pythonpath=pythonpath, extra=None)
        env["BAS_CANONICAL_WRITE_GIT_SCRATCH"] = self.tmp_spelling if guarded else None
        if extra:
            env.update(extra)
        return env


# ------------------------------------------------------------- bindings


def load_contract(path: Path, lane: str, out_root: Path) -> tuple[dict[str, Any], list[str]]:
    problems: list[str] = []
    data = path.read_bytes()
    contract = json.loads(data.decode("utf-8"))
    digest = sha256_bytes(data)
    issuance = path.parent / "issuance" / "issuance.json"
    recorded = None
    if issuance.is_file():
        recorded = json.loads(issuance.read_text(encoding="utf-8")).get("contract_sha256")
    if recorded != digest:
        problems.append(f"contract SHA-256 {digest} differs from the sealed issuance record {recorded}")
    if (contract.get("cycle_number"), contract.get("attempt_number")) != (CYCLE_NUMBER, ATTEMPT_NUMBER):
        problems.append("contract is not Cycle 37 Attempt 4")
    if contract.get("attempt_id") != ATTEMPT_ID:
        problems.append(f"contract attempt_id {contract.get('attempt_id')!r} is not {ATTEMPT_ID}")
    if (contract.get("repo") or {}).get("base_sha") != BASE_SHA:
        problems.append(f"contract base {(contract.get('repo') or {}).get('base_sha')} is not {BASE_SHA}")
    lanes = {row["id"]: row for row in contract.get("required_lanes", [])}
    row = lanes.get(lane)
    if row is None or row.get("executor") != "worker":
        problems.append(f"{lane} is not a worker lane of this contract")
    elif f"attempt04_lanes.py --lane {lane} " not in row.get("command", ""):
        problems.append(f"the contract's command for {lane} does not invoke this runner for this lane")
    if os.path.normcase(str(out_root)) != os.path.normcase(str(Path(contract["paths"]["evidence_root"]))):
        problems.append(f"out-root {out_root} is not the contract evidence root {contract['paths']['evidence_root']}")
    contract["_sha256"] = digest
    contract["_issuance_contract_sha256"] = recorded
    contract["_lane"] = row
    return contract, problems


def bind_source() -> dict[str, Any]:
    head = git_out("rev-parse", "HEAD")
    dirty = porcelain()
    runner = Path(__file__).resolve()
    return {
        "worktree": str(WORKTREE),
        "branch": git_out("rev-parse", "--abbrev-ref", "HEAD"),
        "head": head,
        "tree": git_out("rev-parse", "HEAD^{tree}"),
        "source_digest": source_digest(head) if head else None,
        "source_digest_method": "sha256(git ls-tree -r --full-tree HEAD)",
        "base": BASE_SHA,
        "descends_from_base": git("merge-base", "--is-ancestor", BASE_SHA, head).returncode == 0 if head else False,
        "commits_after_base": git_out("rev-list", "--count", f"{BASE_SHA}..{head}") if head else None,
        "clean": not dirty,
        "dirty_entries": dirty[:50],
        "runner": str(runner),
        "runner_sha256": sha256_file(runner),
        "runner_version": RUNNER_VERSION,
        "rebound_attempt3_runner": str(Path(base.__file__).resolve()),
        "rebound_attempt3_runner_sha256": sha256_file(Path(base.__file__).resolve()),
    }


def successor_pointer() -> dict[str, Any]:
    """The delivered explicit career successor, by its pointer; every field is re-verified by the caller."""

    if not SUCCESSOR_POINTER.is_file():
        return {}
    return json.loads(SUCCESSOR_POINTER.read_text(encoding="utf-8"))


def _replay_from(run: LaneRun, directory: Path, script: str, *,
                 adapt: dict[str, str] | None = None) -> tuple[Path, dict[str, Any]]:
    """Copy a saved manager probe into an owned directory, byte-for-byte unless ``adapt`` rewrites literals."""

    source = directory / script
    original = source.read_bytes()
    target_dir = run.fresh(f"replay_{directory.name}_{Path(script).stem}")
    text = original.decode("utf-8")
    changes = []
    for old, new in (adapt or {}).items():
        if text.count(old) != 1:
            raise RuntimeError(f"{script}: the literal to adapt occurs {text.count(old)} times, not once")
        text = text.replace(old, new)
        changes.append({"from": old, "to": new})
    target = target_dir / script
    target.write_bytes(text.encode("utf-8"))
    return target, {"manager_original": str(source), "manager_original_sha256": sha256_bytes(original),
                    "replay_copy": str(target), "replay_copy_sha256": sha256_file(target),
                    "byte_identical": not changes, "literal_adaptations": changes}


def _json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


# ------------------------------------------------------------------ lanes


def lane_start_context(run: LaneRun) -> None:
    base.lane_start_context(run)
    contract = run.contract
    references = []
    for ref in contract.get("source_refs", []):
        path = Path(str(ref.get("path") or ""))
        expected = ref.get("sha256")
        actual = sha256_file(path) if path.is_file() else None
        references.append({"id": ref.get("id"), "path": str(path), "expected_sha256": expected,
                           "actual_sha256": actual, "matches": bool(expected) and actual == expected})
    run.extra["source_refs"] = references
    # The worktree's own JIRA-SYNC / JIRA-MODEL references are pinned at issuance; everything else is immutable
    # manager or attempt evidence. A mismatch is reported, never silently accepted.
    mismatched = [row["id"] for row in references if row["expected_sha256"] and not row["matches"]]
    if mismatched:
        run.problems.append(f"source references whose bytes differ from the issued digest: {mismatched}")
    pointer = successor_pointer()
    if pointer:
        path = Path(pointer.get("successor_file", ""))
        run.extra["career_successor"] = {"pointer": str(SUCCESSOR_POINTER), "pointer_sha256": sha256_file(SUCCESSOR_POINTER),
                                         "successor_file": str(path), "declared_sha256": pointer.get("successor_sha256"),
                                         "actual_sha256": sha256_file(path)}
        if sha256_file(path) != pointer.get("successor_sha256"):
            run.problems.append("the delivered career successor does not match its pointer digest")
    else:
        run.extra["career_successor"] = {"pointer": str(SUCCESSOR_POINTER), "state": "NOT_YET_DELIVERED"}
        run.problems.append("no delivered career successor pointer exists yet")


def _prepare_manager_fixture(root: Path) -> None:
    """The fixture layout the Attempt 3 manager's orchestrator creates before its guard child runs."""

    root.mkdir()
    for name in ("temp", "git-owned", "protected-fixture"):
        (root / name).mkdir()
    (root / "protected-fixture" / "sentinel.txt").write_text("ORIGINAL-MANAGER-FIXTURE")


def _manager_a3_adapt(fixture: Path, installed_python: Path | None = None) -> dict[str, str]:
    adapt = {r"F=P(r'C:\BatteredAggieSyndrome.packaging\manager-c37a03-212311')": f"F=P(r'{fixture}')"}
    if installed_python is not None:
        adapt[r"INST=P(r'C:\BatteredAggieSyndrome.packaging\c37a03\b\34986ede\venv\Scripts\python.exe')"] = \
            f"INST=P(r'{installed_python}')"
    return adapt


def lane_write_protection(run: LaneRun) -> None:
    run.exceptions.append("The guard suites and the manager guard probes run without the lane guard: they install, "
                          "strip and propagate guards themselves, so an outer guard would change what they test. "
                          "The before/after snapshots measure this lane instead.")
    run.census("guard_suites", GUARD_SUITES, env=run.env(guarded=False),
               note="Write/route/network matrix, the Git child matrix, live-vector controls and the manager alias.")
    # The Attempt 2 manager probe, exactly as Attempt 3 replayed it.
    probe, replay = base._replay(run, "probe_write_guard.py")
    record = run.run("manager_a2_probe_write_guard_replay", [run.python, "-B", probe], cwd=probe.parent,
                     env=run.env(guarded=False, pythonpath=None))
    result_path = probe.parent / "WRITE_GUARD_INDEPENDENT_PROBE.json"
    result = _json_file(result_path) or {}
    outcome = json.loads(result.get("stdout") or "{}") if result.get("stdout") else {}
    refused = all(outcome.get(key) == "CanonicalWriteRefused" for key in ("ordinary_write", "sqlite_update",
                                                                          "keyword_unlink"))
    preserved = (result.get("ordinary_write_preserved") is True and result.get("sqlite_value") == "ORIGINAL"
                 and result.get("keyword_target_exists") is True)
    run.extra["manager_a2_write_guard_probe"] = {**replay, "child_outcomes": outcome, "all_three_refused": refused,
                                                 "bytes_preserved": preserved, "exit": record.get("exit_code")}
    if not (refused and preserved):
        run.problems.append(f"the Attempt 2 manager guard probe is not fully refused: {outcome}, preserved={preserved}")
    # MF37A03-01: the Attempt 3 manager's Git alias probe. Its orchestrator's fixture layout is prepared in an
    # owned directory and its own ``guard-retry`` mode runs the guarded child against it.
    fixture = run.work / "mgr_a3_fixture"
    copy, replay = _replay_from(run, MANAGER_A3, "independent_probes.py", adapt=_manager_a3_adapt(fixture))
    _prepare_manager_fixture(fixture)
    init = run.run("manager_a3_fixture_git_init", ["git", "init", fixture / "git-owned"], cwd=fixture,
                   env=run.env(guarded=False, pythonpath=None),
                   note="The unguarded fixture repository the manager's orchestrator creates.")
    record = run.run("manager_a3_git_alias_probe_replay", [run.python, "-B", copy, "guard-retry"], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None),
                     note="Manager probe, owned fixture root; the child re-installs the guard over the sentinel.")
    receipt = _json_file(copy.parent / "INDEPENDENT_WRITE_GUARD.json") or {}
    child = json.loads(receipt.get("stdout") or "{}") if receipt.get("stdout") else {}
    verdict = {
        **replay, "init_exit": init.get("exit_code"), "exit": record.get("exit_code"),
        "protected_bytes_unchanged": receipt.get("protected_bytes_unchanged"),
        "ordinary_write_refused": child.get("ordinary_write_refused"),
        "positive_git_version_exit": (child.get("positive_git") or {}).get("exit"),
        "git_alias": child.get("git_alias"),
        "guard_source_sha256": receipt.get("guard_source_sha256"),
    }
    verdict["alias_refused_before_effect"] = bool((child.get("git_alias") or {}).get("refused")) and \
        receipt.get("protected_bytes_unchanged") is True
    run.extra["manager_a3_git_alias_probe"] = verdict
    if not (verdict["alias_refused_before_effect"] and verdict["ordinary_write_refused"] is True
            and verdict["positive_git_version_exit"] == 0):
        run.problems.append(f"MF37A03-01 is not closed by the manager's probe: {verdict}")


def _judge_a3_admission(output: dict[str, Any]) -> dict[str, Any]:
    cases = output.get("cases") or {}

    def admitted(case: Any) -> bool:
        return isinstance(case, dict) and (case.get("admitted") is True or case.get("state") == "ADMITTED_FOR_SCORING")

    positive = {name: admitted(cases.get(name)) for name in ("positive_original", "positive_corrected")}
    supersession = cases.get("positive_supersession") or {}
    positive["positive_supersession"] = isinstance(supersession, dict) and bool(supersession.get("supersedes"))
    negatives = {name: not admitted(cases.get(name)) for name in ("invented_digests_refused", "altered_model_refused")}
    for name in ("forged_contest", "forged_probability_and_brier", "correction_before_freeze"):
        negatives[name] = (cases.get(name) or {}).get("refused") is True
    return {"positives": positive, "negatives_refused": negatives,
            "all_hold": all(positive.values()) and all(negatives.values()) and len(cases) == 8,
            "case_count": len(cases), "modules": (output.get("binding") or {}).get("modules")}


def _judge_a3_pit(output: dict[str, Any]) -> dict[str, Any]:
    cases = output.get("cases") or {}
    verdicts = {}
    for name, case in cases.items():
        classification = (case or {}).get("classification") or {}
        verdicts[name] = {"state": classification.get("successor_state") or classification.get("state"),
                          "cutoff_utc": classification.get("cutoff_utc"),
                          "consumer_admitted": bool((case or {}).get("consumer_admitted"))}
    positive = verdicts.get("positive") or {}
    refused = {name: not row["consumer_admitted"] for name, row in verdicts.items() if name != "positive"}
    return {"cases": verdicts, "positive_admitted_with_its_cutoff": positive.get("consumer_admitted") is True
            and bool(positive.get("cutoff_utc")), "negatives_refused": refused,
            "all_hold": positive.get("consumer_admitted") is True and bool(positive.get("cutoff_utc"))
            and all(refused.values()) and len(verdicts) == 6,
            "modules": (output.get("binding") or {}).get("modules")}


def _manager_a3_admission_pit(run: LaneRun, mode: str, python: Path, installed_python: Path | None,
                              env: dict[str, str | None]) -> dict[str, Any]:
    fixture = run.work / f"mgr_a3_{mode}_fixture"
    copy, replay = _replay_from(run, MANAGER_A3, "independent_probes.py",
                                adapt=_manager_a3_adapt(fixture, installed_python))
    _prepare_manager_fixture(fixture)
    result: dict[str, Any] = {**replay}
    for kind in ("admission", "pit"):
        record = run.run(f"manager_a3_{kind}_{mode}", [python, "-B", copy, kind, mode], cwd=copy.parent, env=env,
                         note=f"Attempt 3 manager probe, {mode} consumer, owned fixture root.")
        name = f"INDEPENDENT_{'ADMISSION' if kind == 'admission' else 'PIT'}_{mode.upper()}.json"
        output = _json_file(copy.parent / name) or {}
        judged = _judge_a3_admission(output) if kind == "admission" else _judge_a3_pit(output)
        result[kind] = {"exit": record.get("exit_code"), "receipt": str(copy.parent / name),
                        "receipt_sha256": sha256_file(copy.parent / name), **judged}
        if not judged["all_hold"]:
            run.problems.append(f"the Attempt 3 manager {kind} probe does not hold in {mode}: {judged}")
    return result


def lane_source_admission(run: LaneRun) -> None:
    base.lane_source_admission(run)
    run.extra["manager_a3_source"] = _manager_a3_admission_pit(
        run, "source", run.python, None, run.env(pythonpath=None))


def lane_source_harness(run: LaneRun) -> None:
    base.lane_source_harness(run)


def lane_source_regressions(run: LaneRun) -> None:
    base.lane_source_regressions(run)


# ---- the explicit career successor --------------------------------------------------------------------------


def _successor_oracle(database: Path, successor: Path) -> dict[str, Any]:
    """Direct sqlite3 over the successor and predecessor, with no aggie_analytics import."""

    conn = sqlite3.connect(f"file:{successor.as_posix()}?mode=ro&immutable=1", uri=True)
    try:
        rows = [dict(zip((c[0] for c in cursor.description), row)) for cursor in
                [conn.execute('SELECT episode_id, pageid, page_title, person_display, family, start, "end", ongoing, '
                              "assignments, classification, resolution, definite_first_season, definite_last_season, "
                              "uncertainty_classes, row_index, interval_index FROM career_episode_a04")]
                for row in cursor]
        order = [str(row[0]) for row in conn.execute(
            "SELECT episode_id FROM career_episode_a04 ORDER BY pageid, family, row_index, interval_index, episode_id")]
        dispositions = {str(row[0]): row[1] for row in conn.execute(
            "SELECT predecessor_episode_id, disposition FROM career_a04_disposition")}
        identity = {str(row[0]): str(row[1]) for row in conn.execute("SELECT key, value FROM successor_identity")}
    finally:
        conn.close()
    predecessor = sqlite3.connect(f"file:{database.as_posix()}?mode=ro&immutable=1", uri=True)
    try:
        programs = {str(row[0]): json.loads(row[1] or "[]") for row in
                    predecessor.execute("SELECT program_id, display_names FROM canonical_program")}
        predecessor_ids = {str(row[0]) for row in predecessor.execute("SELECT episode_id FROM career_episode_successor")}
    finally:
        predecessor.close()
    return {"rows": rows, "order": order, "dispositions": dispositions, "identity": identity,
            "programs": programs, "predecessor_ids": predecessor_ids}


def _successor_filter(rows: list[dict[str, Any]], programs: dict[str, list[str]], **flt: Any) -> set[str]:
    """Independent Python filters over the successor rows: season membership on definite bounds only."""

    def norm(value: Any) -> str:
        return " ".join(str(value).split()).casefold()

    team = None
    if flt.get("team"):
        matches = [pid for pid, names in programs.items() if any(norm(n) == norm(flt["team"]) for n in names)]
        team = matches[0] if len(matches) == 1 else "__AMBIGUOUS__"
    result = set()
    for row in rows:
        resolution = json.loads(row["resolution"] or "{}")
        classification = json.loads(row["classification"] or "{}")
        roles = [a.get("role") for a in json.loads(row["assignments"] or "[]") if isinstance(a, dict)]
        season = flt.get("season")
        if team is not None and resolution.get("program_id") != team:
            continue
        if season is not None:
            first, last, ongoing = row["definite_first_season"], row["definite_last_season"], row["ongoing"]
            if first is None or first > season or not ((last is not None and last >= season)
                                                       or (last is None and ongoing == 1)):
                continue
        if flt.get("division"):
            if season is not None:
                if str((classification.get("by_season") or {}).get(str(season), "")).lower() != flt["division"].lower():
                    continue
            elif flt["division"].lower() not in [str(d).lower() for d in classification.get("divisions") or []]:
                continue
        if flt.get("role") and flt["role"].lower() not in [str(r).lower() for r in roles]:
            continue
        if flt.get("family") and str(row["family"]).upper() != flt["family"].upper():
            continue
        if flt.get("person") and norm(flt["person"]) not in (norm(row["page_title"]), norm(row["person_display"])):
            continue
        if flt.get("uncertainty") and flt["uncertainty"] not in json.loads(row["uncertainty_classes"] or "[]"):
            continue
        result.add(str(row["episode_id"]))
    return result


def _tampered_successors(work: Path, delivered: Path) -> dict[str, Path]:
    """Owned fixtures derived from the delivered successor, each broken one way. The delivered file is only read.

    ``tampered_row`` is a full copy with one row changed and its ledger left as delivered, so its refusal comes
    from the re-hashed ledger. The others keep every disposition row and identity but only the first 50 episode
    rows, with the ledgers re-sealed as a careful forger would; each must then be refused by the later check it
    targets (predecessor digest, activation claim, identity coverage), not by the ledger. Small derived files keep
    the lane inside the attempt's storage budget.
    """

    from aggie_analytics.cycle37 import career_successor as cs  # noqa: PLC0415

    fixtures: dict[str, Path] = {}

    def reseal(conn: sqlite3.Connection) -> None:
        for table, columns, key in ((cs.EPISODE_TABLE, cs.EPISODE_COLUMNS, "episode_id"),
                                    (cs.DISPOSITION_TABLE, cs.DISPOSITION_COLUMNS, "predecessor_episode_id")):
            digest, count = cs.table_ledger(conn, table, columns, key)
            conn.execute("UPDATE successor_identity SET value = ? WHERE key = ?", (digest, f"ledger::{table}::sha256"))
            conn.execute("UPDATE successor_identity SET value = ? WHERE key = ?", (str(count), f"ledger::{table}::rows"))

    path = work / "tampered_row.sqlite"
    shutil.copyfile(delivered, path)
    conn = sqlite3.connect(path)
    conn.execute("UPDATE career_episode_a04 SET role_text = 'head coach' WHERE rowid = (SELECT MIN(rowid) FROM "
                 "career_episode_a04)")
    conn.commit()
    conn.close()
    fixtures["tampered_row"] = path

    def derive(name: str, *statements: str) -> None:
        target = work / f"{name}.sqlite"
        conn = sqlite3.connect(f"file:{target.as_posix()}", uri=True)  # a URI connection, so ATTACH reads a URI
        conn.execute("ATTACH DATABASE ? AS delivered", (f"file:{delivered.as_posix()}?mode=ro&immutable=1",))
        conn.execute(f"CREATE TABLE {cs.IDENTITY_TABLE} AS SELECT * FROM delivered.{cs.IDENTITY_TABLE}")
        conn.execute(f"CREATE TABLE {cs.DISPOSITION_TABLE} AS SELECT * FROM delivered.{cs.DISPOSITION_TABLE}")
        conn.execute(f"CREATE TABLE {cs.EPISODE_TABLE} AS SELECT * FROM delivered.{cs.EPISODE_TABLE} "
                     "ORDER BY episode_id LIMIT 50")
        conn.commit()
        conn.execute("DETACH DATABASE delivered")
        for statement in statements:
            conn.execute(statement)
        reseal(conn)
        conn.commit()
        conn.close()
        fixtures[name] = target

    derive("duplicate_identity_resealed",
           f"INSERT INTO {cs.DISPOSITION_TABLE} SELECT * FROM {cs.DISPOSITION_TABLE} ORDER BY predecessor_episode_id LIMIT 1")
    derive("missing_disposition_resealed",
           f"DELETE FROM {cs.DISPOSITION_TABLE} WHERE rowid = (SELECT MIN(rowid) FROM {cs.DISPOSITION_TABLE})")
    derive("wrong_predecessor_resealed", "UPDATE successor_identity SET value = '" + "0" * 64 + "' "
                                         "WHERE key = 'predecessor_database_sha256'")
    derive("claims_activation_resealed",
           "UPDATE successor_identity SET value = 'ACTIVATED_DEFAULT' WHERE key = 'default_activation'")
    fixtures["missing_file"] = work / "absent_successor.sqlite"
    return fixtures


#: The refusal each deliberately wrong successor invocation must give, by its stable code or message.
SUCCESSOR_REFUSALS = {
    "refuse_successor_with_legacy_audit": "REFUSED_EXPLICIT_SUCCESSOR_AND_LEGACY_AUDIT_ARE_EXCLUSIVE",
    "refuse_unknown_uncertainty": "REFUSED_UNKNOWN_UNCERTAINTY_CLASS",
    "refuse_uncertainty_without_successor": "--uncertainty is carried only by a named --career-successor",
    "refuse_pin_without_successor": "pins a successor that was not named",
    "refuse_wrong_pin": "REFUSED_CAREER_SUCCESSOR_FILE_DIGEST_MISMATCH",
    "refuse_successor_on_team_staff": "do not apply to a team-season staff query",
}


def _installed_successor(run: LaneRun, installed: dict[str, Any]) -> None:
    pointer = successor_pointer()
    if not pointer:
        run.problems.append("no delivered career successor to serve")
        return
    successor = Path(pointer["successor_file"])
    digest = sha256_file(successor)
    if digest != pointer.get("successor_sha256"):
        run.problems.append("the delivered career successor does not match its pointer")
        return
    pin = ["--career-successor", successor, "--career-successor-sha256", digest]
    outdir = run.run_dir / "successor_cli"
    outdir.mkdir()
    plan: list[tuple[str, list[Any], int]] = [
        ("fred_mariani_successor", ["--person", FRED, *pin], 0),
        ("fred_mariani_default", ["--person", FRED], 0),
        ("don_carthel_successor", ["--person", CARTHEL, *pin], 0),
        ("skyler_cassity_successor", ["--person", CASSITY, *pin], 0),
        ("archie_hahn_successor", ["--person", HAHN, *pin], 0),
        ("bill_anderson_successor", ["--person", BILL, *pin], 0),
        ("career_unresolved_role", ["--career", "--uncertainty", "UNRESOLVED_ROLE", "--all", *pin], 0),
        ("career_unknown_end", ["--career", "--uncertainty", "UNKNOWN_END", "--all", *pin], 0),
        ("career_unknown_start", ["--career", "--uncertainty", "UNKNOWN_START", "--all", *pin], 0),
        ("career_uncertain_start", ["--career", "--uncertainty", "UNCERTAIN_START", "--all", *pin], 0),
        ("career_no_definite_season", ["--career", "--uncertainty", "NO_DEFINITE_SEASON", "--all", *pin], 0),
        ("career_tamu_2026", ["--career", "--team", "Texas A&M", "--season", "2026", "--all", *pin], 0),
        ("career_fcs_1985", ["--career", "--season", "1985", "--division", "FCS", "--all", *pin], 0),
        ("career_fbs_2010_oc", ["--career", "--season", "2010", "--division", "FBS", "--role",
                                "offensive_coordinator", "--all", *pin], 0),
        ("career_hc_coaching", ["--career", "--role", "head_coach", "--family", "COACHING", "--all", *pin], 0),
        ("career_season_2009", ["--career", "--season", "2009", "--all", *pin], 0),
        ("refuse_successor_with_legacy_audit", ["--career", "--legacy-audit", *pin], 1),
        ("refuse_unknown_uncertainty", ["--career", "--uncertainty", "NOT_A_CLASS", *pin], 1),
        ("refuse_uncertainty_without_successor", ["--career", "--uncertainty", "UNKNOWN_END"], 1),
        ("refuse_pin_without_successor", ["--career", "--career-successor-sha256", digest], 1),
        ("refuse_wrong_pin", ["--career", "--career-successor", successor, "--career-successor-sha256", "0" * 64], 1),
        ("refuse_successor_on_team_staff", ["--team", "Texas A&M", "--season", "2026", *pin], 1),
    ]
    results: dict[str, Any] = {}
    for name, args, expected in plan:
        record = base._cli(run, installed, name, args, expect_exit=expected, save=outdir / f"{name}.json.gz")
        results[name] = {"exit": record.get("exit_code"), "expected_exit": expected,
                         "result": record["result_against_expectation"], "args": [str(a) for a in args]}
        if name in SUCCESSOR_REFUSALS:
            text = Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
            results[name]["refused_for_the_intended_cause"] = SUCCESSOR_REFUSALS[name] in text
            if SUCCESSOR_REFUSALS[name] not in text:
                run.problems.append(f"{name} was not refused for its intended cause ({SUCCESSOR_REFUSALS[name]})")
    fixtures = _tampered_successors(run.fresh("tampered_successors"), successor)
    for name, code in (("tampered_row", "REFUSED_CAREER_SUCCESSOR_LEDGER_MISMATCH"),
                       ("duplicate_identity_resealed", "REFUSED_CAREER_SUCCESSOR_IDENTITY_COVERAGE"),
                       ("wrong_predecessor_resealed", "REFUSED_CAREER_SUCCESSOR_PREDECESSOR_DIGEST_MISMATCH"),
                       ("claims_activation_resealed", "REFUSED_CAREER_SUCCESSOR_CLAIMS_ACTIVATION"),
                       ("missing_disposition_resealed", "REFUSED_CAREER_SUCCESSOR_IDENTITY_COVERAGE"),
                       ("missing_file", "REFUSED_CAREER_SUCCESSOR_ABSENT")):
        record = base._cli(run, installed, f"successor_fixture_{name}",
                           ["--career", "--career-successor", fixtures[name], "--limit", "5"], expect_exit=1)
        text = Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
        results[f"successor_fixture_{name}"] = {"exit": record.get("exit_code"), "expected_code": code,
                                                "refused_for_the_intended_cause": code in text}
        if code not in text:
            run.problems.append(f"successor fixture {name} was not refused with {code}")
    run.extra["successor_cli_results"] = results
    failed = [name for name, row in results.items() if row.get("result") == FAIL]
    if failed:
        run.problems.append(f"installed successor cases not as expected: {failed}")

    def load(name: str) -> dict[str, Any]:
        return base._gz_json(outdir / f"{name}.json.gz") or {}

    # The named manager counterexamples and controls, read from the installed consumer's own output.
    fred = load("fred_mariani_successor")
    fred_default = load("fred_mariani_default")
    rutgers = [row for row in fred.get("career_episodes", []) if "Rutgers" in str(row.get("employer_display"))]
    default_rutgers = [row for row in fred_default.get("career_episodes", [])
                       if "Rutgers" in str(row.get("employer_display"))]
    carthel = load("don_carthel_successor")
    stqc = [row for row in carthel.get("career_episodes", []) if "STQC" in str(row.get("team_raw"))]
    cassity = [row for row in load("skyler_cassity_successor").get("career_episodes", [])
               if "(SA)" in str(row.get("team_raw"))]
    hahn = [row for row in load("archie_hahn_successor").get("career_episodes", [])
            if "(trainer)" in str(row.get("team_raw"))]
    bill = load("bill_anderson_successor")
    stamford = [row for row in bill.get("career_episodes", []) if row.get("employer_display") == "Stamford HS (TX)"]

    def roles(row: dict[str, Any]) -> list[str]:
        """The row's served assignments, read from the stored column exactly as the CLI returned it."""

        value = row.get("assignments")
        value = json.loads(value) if isinstance(value, str) else (value or [])
        return [a.get("role") for a in value if isinstance(a, dict)]

    named = {
        "fred_mariani": {"mode": (fred.get("release_dispatch") or {}).get("mode"),
                         "rutgers_rows": [{"episode_id": r.get("episode_id"), "team_raw": r.get("team_raw"),
                                           "roles": roles(r), "role_basis": r.get("role_basis"),
                                           "uncertainty": (r.get("corrected") or {}).get("uncertainty_classes")}
                                          for r in rutgers],
                         "default_mode": (fred_default.get("release_dispatch") or {}).get("mode"),
                         "default_rutgers_roles": [roles(r) for r in default_rutgers]},
        "don_carthel": {"stqc_rows": [{"episode_id": r.get("episode_id"), "team_raw": r.get("team_raw"),
                                       "roles": roles(r), "role_basis": r.get("role_basis")} for r in stqc]},
        "bill_anderson": {"stamford_rows": [{"episode_id": r.get("episode_id"), "team_raw": r.get("team_raw"),
                                             "roles": roles(r), "role_basis": r.get("role_basis")} for r in stamford]},
        "skyler_cassity": {"sa_rows": [{"episode_id": r.get("episode_id"), "team_raw": r.get("team_raw"),
                                        "roles": roles(r), "role_basis": r.get("role_basis")} for r in cassity]},
        "archie_hahn": {"trainer_rows": [{"episode_id": r.get("episode_id"), "team_raw": r.get("team_raw"),
                                          "roles": roles(r), "role_basis": r.get("role_basis")} for r in hahn]},
    }
    named["fred_mariani"]["dfo_not_head_coach"] = bool(rutgers) and all(
        "head_coach" not in roles(r) for r in rutgers if "DFO" in str(r.get("team_raw")))
    named["don_carthel"]["stqc_not_head_coach"] = bool(stqc) and all("head_coach" not in roles(r) for r in stqc)
    # The Stamford HS (TX) control: (TX) is a place, never a title; a Stamford row that states no role keeps the
    # head-coach convention, and the one that states "(assistant)" keeps that role.
    named["bill_anderson"]["stamford_head_coach_kept"] = len(stamford) == 3 and any(
        r.get("role_basis") == "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL" for r in stamford) and all(
        ("head_coach" in roles(r)) == (r.get("role_basis") == "INFOBOX_CONVENTION_NO_ROLE_PARENTHETICAL")
        and "TX" not in str(r.get("role_text") or "") for r in stamford)
    named["skyler_cassity"]["sa_not_head_coach"] = bool(cassity) and all("head_coach" not in roles(r) for r in cassity)
    named["archie_hahn"]["trainer_not_head_coach"] = bool(hahn) and all("head_coach" not in roles(r) for r in hahn)
    run.extra["successor_named_cases"] = named
    for key, flag in (("fred_mariani", "dfo_not_head_coach"), ("don_carthel", "stqc_not_head_coach"),
                      ("bill_anderson", "stamford_head_coach_kept"), ("skyler_cassity", "sa_not_head_coach"),
                      ("archie_hahn", "trainer_not_head_coach")):
        if not named[key][flag]:
            run.problems.append(f"installed successor: {key} {flag} does not hold: {named[key]}")

    # Full pagination and filters against the independent oracle.
    oracle = _successor_oracle(DELIVERED_DB, successor)
    pages = run.run_dir / "successor_pages"
    pages.mkdir()
    run.extra["successor_pagination"] = base._paginate(run, installed, "career_successor", ["--career", *pin],
                                                       "episode_id", 10000, oracle["order"], pages)
    filtered = {}
    for name, flt in (("career_tamu_2026", {"team": "Texas A&M", "season": 2026}),
                      ("career_fcs_1985", {"season": 1985, "division": "fcs"}),
                      ("career_fbs_2010_oc", {"season": 2010, "division": "fbs", "role": "offensive_coordinator"}),
                      ("career_hc_coaching", {"role": "head_coach", "family": "COACHING"}),
                      ("career_season_2009", {"season": 2009}),
                      ("career_unresolved_role", {"uncertainty": "UNRESOLVED_ROLE"}),
                      ("career_unknown_end", {"uncertainty": "UNKNOWN_END"}),
                      ("career_unknown_start", {"uncertainty": "UNKNOWN_START"}),
                      ("career_uncertain_start", {"uncertainty": "UNCERTAIN_START"}),
                      ("career_no_definite_season", {"uncertainty": "NO_DEFINITE_SEASON"}),
                      ("fred_mariani_successor", {"person": FRED}),
                      ("don_carthel_successor", {"person": CARTHEL}),
                      ("skyler_cassity_successor", {"person": CASSITY}),
                      ("archie_hahn_successor", {"person": HAHN}),
                      ("bill_anderson_successor", {"person": BILL})):
        payload = load(name)
        rows = payload.get("rows") or payload.get("career_episodes") or []
        cli_ids = {str(row["episode_id"]) for row in rows}
        expected = _successor_filter(oracle["rows"], oracle["programs"], **flt)
        filtered[name] = {"cli": len(cli_ids), "oracle": len(expected), "equal": cli_ids == expected,
                          "reported_total": (payload.get("pagination") or {}).get("total_count")}
        if cli_ids != expected:
            run.problems.append(f"successor filter {name} differs from the independent filter")
    run.extra["successor_filtered_oracle"] = filtered
    # Every predecessor row has exactly one disposition, and nothing outside the versioned namespace is served.
    coverage = {"predecessor_rows": len(oracle["predecessor_ids"]), "dispositions": len(oracle["dispositions"]),
                "same_identity_set": set(oracle["dispositions"]) == oracle["predecessor_ids"],
                "successor_rows": len(oracle["order"]),
                "all_versioned": all(i.startswith("C37A04:") for i in oracle["order"]),
                "identity": {k: v for k, v in oracle["identity"].items() if not k.startswith("ledger::")}}
    run.extra["successor_coverage"] = coverage
    if not (coverage["same_identity_set"] and coverage["all_versioned"]):
        run.problems.append(f"successor coverage does not hold: {coverage}")
    run.extra["successor_locators"] = base._verify_career_locators(pages, "career_successor")
    locators = run.extra["successor_locators"]
    if locators["rows"] != len(oracle["order"]) or locators["raw_file_digest_mismatch"] or \
            locators["span_mismatch"] or locators["wikitext_not_found"] or locators["raw_file_absent"]:
        run.problems.append(f"successor locators do not all resolve to their raw bytes: {locators}")


def lane_installed_consumer_c01(run: LaneRun) -> None:
    base.lane_installed_consumer_c01(run)
    raw = run.extra.get("installed")
    if not raw:
        return
    installed = {key: Path(value) for key, value in raw.items()}
    _installed_successor(run, installed)
    # The Attempt 3 manager's admission/PIT probes against the fresh installed wheel.
    run.extra["manager_a3_installed"] = _manager_a3_admission_pit(
        run, "installed", installed["python"], installed["python"], base._installed_env(run))
    site = str(installed["venv"] / "Lib" / "site-packages").lower()
    for kind in ("admission", "pit"):
        modules = (run.extra["manager_a3_installed"].get(kind) or {}).get("modules") or {}
        outside = [name for name, row in modules.items() if not str(row.get("path", "")).lower().startswith(site)]
        if outside or not modules:
            run.problems.append(f"the installed manager {kind} probe did not import from the fresh wheel: {outside}")
    # The Attempt 3 manager's career challenge, against this wheel: its default answer is still the delivered
    # predecessor's (no default activation); its parser probe reads the installed v37.4 parser.
    copy, replay = _replay_from(run, MANAGER_A3, "career_challenge.py", adapt={
        r"V=Path(r'C:\BatteredAggieSyndrome.packaging\c37a03\b\34986ede\venv')": f"V=Path(r'{installed['venv']}')"})
    shutil.copy2(MANAGER_A3 / "DELIVERED_DATABASE_INVENTORY.json", copy.parent / "DELIVERED_DATABASE_INVENTORY.json")
    run.exceptions.append("The Attempt 3 manager's career challenge starts the installed bas-staff-query launcher (a "
                          "native executable) with its own minimal environment; the guard rightly refuses a native "
                          "child, so this replay runs without the lane guard. It opens the delivered database "
                          "read-only and immutable and writes only beside its owned copy; the snapshots measure it.")
    record = run.run("manager_a3_career_challenge_installed", [installed["python"], "-B", copy], cwd=copy.parent,
                     env=run.env(guarded=False, pythonpath=None))
    challenge = _json_file(copy.parent / "CAREER_SEMANTIC_REPRODUCTION.json") or {}
    parser = challenge.get("parser") or {}
    teams = parser.get("teams") or {}
    years = parser.get("years") or {}

    def team(raw: str) -> dict[str, Any]:
        return teams.get(raw) or {}

    judged = {
        **replay, "exit": record.get("exit_code"), "parser_import": parser.get("import"),
        "parser_from_site_packages": str(parser.get("import", "")).lower().startswith(site),
        "unknown_suffixes_unresolved": {raw: team(raw).get("role_basis") for raw in teams
                                        if any(code in raw for code in ("DFO", "STQC", "(SA)", "UNRECOGNIZED_JOB"))},
        "location_and_oc_controls": {raw: {"role_basis": team(raw).get("role_basis"),
                                           "qualifier_kinds": team(raw).get("employer_qualifier_kinds")}
                                     for raw in teams if raw.endswith("(TX)") or raw.endswith("(OC)")},
        "years": {raw: {k: (value or [{}])[0].get(k) for k in ("start", "end", "ongoing", "start_state",
                                                              "end_state")}
                  for raw, value in years.items()},
        "default_answer_row_count": len(challenge.get("installed_rows") or []),
        "default_answer_note": "The default answer is the delivered release's own row (no activation).",
    }
    judged["holds"] = judged["parser_from_site_packages"] and all(
        basis == "UNRESOLVED_PARENTHETICAL" for basis in judged["unknown_suffixes_unresolved"].values()) and \
        len(judged["unknown_suffixes_unresolved"]) == 4
    run.extra["manager_a3_career_challenge"] = judged
    if not judged["holds"]:
        run.problems.append(f"the manager's career challenge does not hold against the installed parser: {judged}")


def _rebuild_successor(run: LaneRun) -> dict[str, Any]:
    work = run.fresh("successor_rebuild")
    census_dir = work / "census"
    successor_dir = work / "successor"
    run.run("career_raw_census", [run.python, "-B", "tools/cycle37/a04_career_raw_census.py", "--out", census_dir],
            timeout=4 * 3600, note="The independent raw census of every cached career infobox, from the committed "
                                   "subject.")
    run.run("career_successor_build", [run.python, "-B", "tools/cycle37/a04_career_successor.py", "--out",
                                       successor_dir, "--census", census_dir / "CAREER_RAW_CENSUS.json"],
            timeout=6 * 3600, note="The explicit successor, rebuilt from the committed parser and builder.")
    return {"census_dir": census_dir, "successor_dir": successor_dir}


def lane_career_successor(run: LaneRun) -> None:
    run.census("career_suites", CAREER_SUITES)
    pointer = successor_pointer()
    rebuilt = _rebuild_successor(run)
    build = _json_file(rebuilt["successor_dir"] / "CAREER_A04_SUCCESSOR_BUILD.json") or {}
    rebuilt_file = rebuilt["successor_dir"] / "CAREER_SUCCESSOR_A04.sqlite"
    comparison: dict[str, Any] = {"rebuilt_file": str(rebuilt_file), "rebuilt_sha256": sha256_file(rebuilt_file),
                                  "pointer": str(SUCCESSOR_POINTER), "delivered": pointer}
    if pointer and rebuilt_file.is_file():
        delivered = Path(pointer["successor_file"])

        def ident(path: Path) -> dict[str, str]:
            conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro&immutable=1", uri=True)
            try:
                return {str(r[0]): str(r[1]) for r in conn.execute("SELECT key, value FROM successor_identity")}
            finally:
                conn.close()

        a, b = ident(delivered), ident(rebuilt_file)
        ledgers = sorted(k for k in set(a) | set(b) if k.startswith("ledger::"))
        comparison.update({
            "delivered_sha256": sha256_file(delivered),
            "delivered_matches_pointer": sha256_file(delivered) == pointer.get("successor_sha256"),
            "byte_identical_rebuild": sha256_file(delivered) == sha256_file(rebuilt_file),
            "ledgers_reproduced": {k: a.get(k) == b.get(k) for k in ledgers},
            "identity_differences": {k: {"delivered": a.get(k), "rebuilt": b.get(k)} for k in sorted(set(a) | set(b))
                                     if a.get(k) != b.get(k)},
        })
        if not (comparison["delivered_matches_pointer"] and ledgers and all(comparison["ledgers_reproduced"].values())):
            run.problems.append("the rebuild from the committed subject does not reproduce the delivered successor's "
                                f"ledgers: {comparison['identity_differences']}")
    else:
        run.problems.append("no delivered successor pointer, or the rebuild produced no successor file")
    run.extra["successor_reproduction"] = comparison
    accounting = build.get("accounting") or {}
    run.extra["successor_accounting"] = accounting
    screens = build.get("screens") or {}
    run.extra["screens"] = screens
    for name, row in screens.items():
        if row.get("expected") is not None and row.get("members") != row.get("expected"):
            run.problems.append(f"screen {name} has {row.get('members')} members, not {row.get('expected')}")
        if row.get("without_disposition"):
            run.problems.append(f"screen {name} has members without a disposition: {row.get('without_disposition')}")
        if row.get("unchanged_without_grounded_basis"):
            run.problems.append(f"screen {name} keeps rows unchanged without a grounded basis: "
                                f"{row['unchanged_without_grounded_basis'][:10]}")
        if not row.get("builder_label_equals_manager_set"):
            run.problems.append(f"screen {name}: the builder's label set differs from the manager's")
    if (screens.get("MANAGER_ROLE_CODE_343") or {}).get("successor_rows_still_head_coach"):
        run.problems.append("a priority role-code row is still served as a head coach")
    if len(screens) != 3:
        run.problems.append(f"the build accounts {len(screens)} manager screens, not 3")
    if not accounting or not accounting.get("every_predecessor_row_dispositioned_once") or \
            not accounting.get("successor_identities_distinct"):
        run.problems.append(f"the predecessor/successor identity accounting does not hold: {accounting}")
    # The independent raw census, reconciled row by row against the rebuilt successor.
    census = build.get("census_reconciliation") or {}
    counts = census.get("counts") or {}
    run.extra["census_reconciliation"] = {k: v for k, v in census.items() if k != "examples"} | {
        "example_keys": sorted((census.get("examples") or {}))}
    gaps = {k: v for k, v in counts.items() if v and (k.startswith("uncovered::") or "_without_" in k
                                                      or "not_read_verbatim" in k)}
    if not census or not census.get("rows_sha256_matches_census") or counts.get("covered") != counts.get("census_rows") \
            or gaps:
        run.problems.append(f"the raw census does not reconcile with the rebuilt successor: {gaps or counts}")
    # The Cycle 29 claim successor stays exactly as Attempt 3 delivered it (R37A04-06-C).
    base.lane_claim_successor(run)


# ---- mounted, unmounted, platform and packet lanes ------------------------------------------------------


def _attempt3_final(lane: str) -> dict[str, Any]:
    """The Attempt 3 final receipt of a lane, from its RUNS index (the last run at the Attempt 3 final head)."""

    rows = [json.loads(line) for line in (ATTEMPT3_ROOT / "lanes" / "RUNS.jsonl").read_text(encoding="utf-8")
            .splitlines() if line.strip()]
    rows = [row for row in rows if row["lane"] == lane and row["head"] == BASE_SHA]
    if not rows:
        return {}
    receipt_path = Path(rows[-1]["receipt"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return {"receipt": str(receipt_path), "receipt_sha256": sha256_file(receipt_path), "data": receipt}


def lane_full_final_mounted(run: LaneRun) -> None:
    base.lane_full_final_mounted(run)
    record = next(r for r in reversed(run.commands) if r.get("lane", "").endswith("full_suite_mounted"))
    log = Path(record["log_path"])
    final = base._log_identities(log)
    a3 = _attempt3_final("FULL_FINAL_MOUNTED")
    comparison: dict[str, Any] = {"attempt3_receipt": a3.get("receipt"), "attempt3_receipt_sha256": a3.get("receipt_sha256")}
    if a3:
        a3_log = Path(next(c["log_path"] for c in a3["data"]["commands"] if c["lane"].endswith("full_suite_mounted")))
        before = base._log_identities(a3_log)
        persisting = sorted(set(final["failed_or_errored"]) & set(before["failed_or_errored"]))
        new = sorted(set(final["failed_or_errored"]) - set(before["failed_or_errored"]))
        final_causes = base._failure_causes(log, persisting)
        before_causes = base._failure_causes(a3_log, persisting)
        comparison.update({
            "attempt3_log": str(a3_log), "attempt3_log_sha256": sha256_file(a3_log),
            "attempt3_tests_run": before["tests_run"], "final_tests_run": final["tests_run"],
            "attempt3_failed_or_errored": before["failed_or_errored"],
            "persisting": persisting, "new_in_attempt4": new,
            "no_longer_failing": sorted(set(before["failed_or_errored"]) - set(final["failed_or_errored"])),
            "new_failure_causes": base._failure_causes(log, new),
            "persisting_same_cause": sorted(i for i in persisting if final_causes[i] == before_causes[i]),
            "persisting_changed_cause": {i: {"attempt3": before_causes[i], "attempt4": final_causes[i]}
                                         for i in persisting if final_causes[i] != before_causes[i]},
        })
        if new:
            run.problems.append(f"new failing identities relative to Attempt 3: {new}")
    run.extra["attempt3_comparison"] = comparison


def lane_strict_mounted(run: LaneRun) -> None:
    base.lane_strict_mounted(run)
    final = [row["identity"] for row in run.extra.get("strict_findings") or []]
    a3 = _attempt3_final("STRICT_MOUNTED")
    comparison: dict[str, Any] = {"attempt3_receipt": a3.get("receipt")}
    if a3:
        before = [row["identity"] for row in (a3["data"].get("details") or {}).get("strict_findings") or []]
        comparison.update({"attempt3_findings": before, "final_findings": final,
                           "persisting": sorted(set(final) & set(before)),
                           "new_in_attempt4": sorted(set(final) - set(before)),
                           "no_longer_reported": sorted(set(before) - set(final))})
        if comparison["new_in_attempt4"]:
            run.problems.append(f"new strict findings relative to Attempt 3: {comparison['new_in_attempt4']}")
    run.extra["attempt3_comparison"] = comparison


def lane_true_unmounted(run: LaneRun) -> None:
    base.lane_true_unmounted(run)


def lane_platform_carry(run: LaneRun) -> None:
    run.exceptions.append("The platform reader and the two granted comments call gh and Jira and need the network, "
                          "so those commands run without the lane guard; they write only create-only files under "
                          "the attempt root, and the snapshots measure the rest. The private Jira successor is "
                          "offline and runs under the guard.")
    platform_env = run.env(guarded=False, network=True, pythonpath=None)
    after = run.out_root / "evidence" / "platform" / "AFTER"
    head = run.binding["head"]
    reads: dict[str, Any] = {}
    for mode, pattern, extra in (("github-read", "github/GITHUB_READ_SUMMARY_*.json", []),
                                 ("all22-read", "all22/ALL22_READ_SUMMARY_*.json",
                                  ["--remote-manifest", base.ALL22_REMOTE_MANIFEST]),
                                 ("jira-read", "jira/JIRA_READ_SUMMARY_*.json", ["--full-export"])):
        existing = base._after_receipt_at_head(after, pattern, head)
        if existing:
            reads[mode] = {"state": "REUSED_RECEIPT_AT_THIS_HEAD", "summary": str(existing),
                           "sha256": sha256_file(existing)}
        elif run.rehearsal:
            reads[mode] = {"state": "NOT_RUN_IN_REHEARSAL", "reason": "no request budget is spent on a rehearsal"}
        else:
            run.run(f"platform_{mode}_after", [run.python, "-B", PLATFORM_TOOL, mode, "--out-root", run.out_root,
                                               "--phase", "AFTER", *extra], env=platform_env, timeout=1800)
            made = base._after_receipt_at_head(after, pattern, head)
            reads[mode] = {"state": "READ_AT_THIS_HEAD" if made else "NO_RECEIPT_AT_THIS_HEAD",
                           "summary": str(made) if made else None, "sha256": sha256_file(made) if made else None}
            if not made:
                run.problems.append(f"{mode} left no AFTER receipt bound to head {head}")
    run.extra["platform_reads"] = reads
    exports = sorted((after / "jira").glob("BAT_CANONICAL_EXPORT_2*.csv"))
    if run.rehearsal and not exports:
        exports = sorted((EVIDENCE_ROOT / "evidence" / "platform" / "BEFORE" / "jira").glob("BAT_CANONICAL_EXPORT_2*.csv"))
    if not exports:
        run.problems.append("no AFTER canonical export exists for the private Jira successor")
    else:
        export = exports[-1]
        digest = sha256_file(export)
        folder = export.parent

        def done_for_export() -> list[Path]:
            return [path for path in sorted(folder.glob("JIRA_PRIVATE_SUCCESSOR_*.json"))
                    if (json.loads(path.read_text(encoding="utf-8")).get("source_export") or {}).get("sha256") == digest]

        done = done_for_export()
        if done:
            run.extra["jira_private_successor"] = {"state": "REUSED_RECEIPT_FOR_THIS_EXPORT", "receipt": str(done[-1])}
        else:
            phase = "AFTER" if folder == after / "jira" else "BEFORE"
            run.run("jira_private_successor", [run.python, "-B", PLATFORM_TOOL, "jira-successor", "--out-root",
                                               run.out_root, "--phase", phase, "--export", export, "--apply"],
                    env=run.env(pythonpath=None), timeout=1800,
                    note="Dry run, apply, strict and audit validators and a second dry run, in a private copy.")
            done = done_for_export()
        if done:
            receipt = json.loads(done[-1].read_text(encoding="utf-8"))
            steps = {row["name"]: row for row in receipt.get("commands") or []}
            summary = {"receipt": str(done[-1]), "export": str(export), "export_sha256": digest,
                       "steps": {name: {"exit": row["exit"], "conflicts": row["conflict_count"]}
                                 for name, row in steps.items()},
                       "private_changes": len(receipt.get("record_changes_in_private_copy") or []),
                       "guard_blocked": len((receipt.get("write_guard") or {}).get("blocked") or []),
                       "committed_canonical_mutations": receipt.get("committed_canonical_mutations"),
                       "adopted": receipt.get("adopted")}
            run.extra["jira_private_successor"] = {**run.extra.get("jira_private_successor", {}), **summary}
            if set(steps) != {"dry-run", "apply", "strict", "audit", "second-dry-run"} or any(
                    row["exit"] != 0 for row in steps.values()):
                run.problems.append(f"the private Jira successor did not complete every step: {summary['steps']}")
            if summary["guard_blocked"] or summary["committed_canonical_mutations"]:
                run.problems.append("the private Jira successor touched, or tried to touch, a protected root")
    comments: dict[str, Any] = {}
    for issue, marker in AFTER_COMMENTS:
        body = after / "comment_bodies" / f"{marker}.txt"

        def confirmed() -> list[Path]:
            return [path for path in sorted((after / "jira").glob(f"JIRA_COMMENT_{issue}_*.json"))
                    if json.loads(path.read_text(encoding="utf-8")).get("marker") == marker
                    and json.loads(path.read_text(encoding="utf-8")).get("result") == "SUCCEEDED"]

        posted = confirmed()
        if posted:
            comments[issue] = {"state": "POSTED_AND_READ_BACK", "receipt": str(posted[-1]), "marker": marker}
            continue
        if not body.is_file() or marker not in body.read_text(encoding="utf-8"):
            run.problems.append(f"the AFTER comment body for {issue} is missing or lacks its marker {marker}")
            continue
        if run.rehearsal:
            comments[issue] = {"state": "NOT_POSTED_IN_REHEARSAL", "body": str(body), "marker": marker}
            continue
        run.run(f"jira_comment_after_{issue}", [run.python, "-B", PLATFORM_TOOL, "jira-comment", "--out-root",
                                                run.out_root, "--phase", "AFTER", "--issue", issue, "--marker", marker,
                                                "--body-file", body], env=platform_env, timeout=600)
        posted = confirmed()
        comments[issue] = {"state": "POSTED_AND_READ_BACK" if posted else "NOT_CONFIRMED",
                           "receipt": str(posted[-1]) if posted else None, "marker": marker}
        if not posted:
            run.problems.append(f"the AFTER comment on {issue} was not confirmed by readback")
    run.extra["after_comments"] = comments
    ledger = run.run("platform_ledger_totals", [run.python, "-B", PLATFORM_TOOL, "ledger", "--out-root", run.out_root,
                                                "--phase", "AFTER"], env=run.env(pythonpath=None))
    totals = base._stdout_json(ledger) or {}
    run.extra["request_totals"] = totals
    for lane, row in totals.items():
        if isinstance(row, dict) and row.get("requests", 0) > row.get("ceiling", 0):
            run.problems.append(f"{lane} exceeded its ceiling: {row}")
    run.run("carryforward_accounting", [run.python, "-B", OUTPUTS_TOOL, "check", "--contract", run.contract_path,
                                        "--out-root", run.out_root],
            env=run.env(), note="Every original criterion, obligation, lane and finding accounted, by identity.")


def lane_final_packet(run: LaneRun) -> None:
    run.run("packet_consistency", [run.python, "-B", OUTPUTS_TOOL, "check", "--contract", run.contract_path,
                                   "--out-root", run.out_root, "--final-packet"],
            env=run.env(), note="Outputs, lane receipts at the final head and the integration packet agree.")
    submission = run.out_root / "submission.json"
    if submission.is_file():
        run.run("cycle_protocol_submission_accounting",
                [run.python, "-B", GOVERNANCE / "cycle_protocol.py", "submission", run.contract_path, submission,
                 "--issuance", run.contract_path.parent / "issuance" / "issuance.json"],
                env=run.env(pythonpath=None), note="The v2.4.0 accounting check; it grants no acceptance.")
    else:
        run.problems.append("submission.json does not exist yet")


LANE_FUNCTIONS: dict[str, Callable[[LaneRun], None]] = {
    "START_CONTEXT": lane_start_context,
    "WRITE_PROTECTION": lane_write_protection,
    "SOURCE_ADMISSION": lane_source_admission,
    "SOURCE_HARNESS": lane_source_harness,
    "SOURCE_REGRESSIONS": lane_source_regressions,
    "INSTALLED_CONSUMER_C01": lane_installed_consumer_c01,
    "CAREER_SUCCESSOR": lane_career_successor,
    "FULL_FINAL_MOUNTED": lane_full_final_mounted,
    "STRICT_MOUNTED": lane_strict_mounted,
    "TRUE_UNMOUNTED": lane_true_unmounted,
    "PLATFORM_CARRY": lane_platform_carry,
    "FINAL_PACKET": lane_final_packet,
}


def idle_window(seconds: int) -> Path:
    """Measure All-22 and the data root with no lane running, so exclusions rest on this attempt's evidence."""

    before_all22 = base.snapshot(ALL22, base.ALL22_EXCLUDED)
    before_data = base.snapshot(DATA_ROOT, base.WATCH_EXCLUDED)
    started = utc_now()
    time.sleep(seconds)
    after_all22 = base.snapshot(ALL22, base.ALL22_EXCLUDED)
    after_data = base.snapshot(DATA_ROOT, base.WATCH_EXCLUDED)
    path = EVIDENCE_ROOT / "evidence" / "scope" / f"IDLE_WINDOW_{base.utc_stamp()}.json"
    write_json(path, {"label": "Cycle #37 \u2014 Attempt #4 \u2014 IN_PROGRESS_LOCAL_WORK_REMAINS (idle-window measurement)",
                      "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "started_at": started,
                      "finished_at": utc_now(), "seconds": seconds,
                      "excluded": [str(p) for p in (*base.WATCH_EXCLUDED, *base.ALL22_EXCLUDED)],
                      "all22": base.diff_snapshots(before_all22, after_all22),
                      "data_root": base.diff_snapshots(before_data, after_data)})
    return path


def main(argv: list[str] | None = None) -> int:
    rebind()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lane", choices=LANES)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--out-root", type=Path)
    parser.add_argument("--rehearsal", action="store_true",
                        help="Development only: write under the validation root, allow a dirty tree, spend no "
                             "request budget. A rehearsal receipt is labelled as such and is never evidence.")
    parser.add_argument("--idle-window", type=int, default=None,
                        help="Measure the watched roots for this many seconds with no lane running, then exit.")
    args = parser.parse_args(argv)
    if args.idle_window is not None:
        print(idle_window(args.idle_window))
        return 0
    if not (args.lane and args.contract and args.out_root):
        parser.error("--lane, --contract and --out-root are required")
    out_root = args.out_root.resolve()
    issued_root = out_root
    if args.rehearsal:
        out_root = VALIDATION_ROOT / "rehearsal"
    run = LaneRun(args.lane, args.contract.resolve(), out_root)
    run.rehearsal = args.rehearsal
    console = Tee(run.run_dir / "lane.log", sys.stdout)
    sys.stdout = console
    print(f"Cycle #37 \u2014 Attempt #4 \u2014 lane {args.lane} run {run.stamp}"
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
    before = base.scope_before()
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
    after_binding = bind_source()
    if scope["writes_outside_owned_roots"]:
        result = FAIL
        reason = f"{reason}; {scope['writes_outside_owned_roots']} write(s) outside the owned roots"
    if not (scope["main_checkout"]["unchanged"] and scope["integration_worktree"]["unchanged"]):
        result = FAIL
        reason = f"{reason}; the main checkout or the integration worktree changed during the lane"
    if after_binding["head"] != run.binding["head"] or after_binding["clean"] != run.binding["clean"] or (
            after_binding.get("dirty_entries") != run.binding.get("dirty_entries")):
        result = FAIL
        reason = f"{reason}; the worktree head or its working-tree state changed during the lane"
    guard_events = []
    if run.guard_log.is_file():
        guard_events = [json.loads(line) for line in run.guard_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    receipt = {
        "label": f"Cycle #37 \u2014 Attempt #4 \u2014 lane {args.lane} {result}"
                 + (" (REHEARSAL, NOT EVIDENCE)" if args.rehearsal else ""),
        "rehearsal": args.rehearsal,
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID, "attempt_id": ATTEMPT_ID,
        "lane": args.lane, "kind": (contract.get("_lane") or {}).get("kind"), "run": run.stamp,
        "started_at": run.started, "finished_at": utc_now(),
        "result": result, "state_reason": reason,
        "contract": {"path": str(run.contract_path), "sha256": contract.get("_sha256"),
                     "issuance_contract_sha256": contract.get("_issuance_contract_sha256"),
                     "issued_command": (contract.get("_lane") or {}).get("command"),
                     "issued_cwd": (contract.get("_lane") or {}).get("cwd"),
                     "issued_environment": (contract.get("_lane") or {}).get("environment"),
                     "issued_data_binding": (contract.get("_lane") or {}).get("data_binding")},
        "invocation": {"argv": sys.argv, "cwd": os.getcwd()},
        "source_binding": run.binding, "source_binding_after": after_binding, "interpreter": interpreter,
        "write_and_network_scope": {
            "guarded_roots": [str(root) for root in base.GUARDED_ROOTS],
            "writable_roots": [str(out_root), str(VALIDATION_ROOT), str(PACKAGING_ROOT)],
            "git_scratch_root": run.tmp_spelling,
            "network": "DENY_NON_LOOPBACK for guarded children", "credential_variables_removed": sorted(credential_scrub()),
            "temp_root": str(run.tmp), "temp_spelling_given_to_children": run.tmp_spelling,
            "exceptions": run.exceptions, "guard_events": len(guard_events),
            "guard_blocked_events": [row for row in guard_events if row.get("event") == "BLOCKED"][:100],
            "measurement": scope,
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
