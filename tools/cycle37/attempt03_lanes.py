r"""Cycle #37 — Attempt #3 — the attempt-parameterized lane runner (R37A03-05, R37A03-07).

    attempt03_lanes.py --lane <ID> --contract <cycle_contract.json> --out-root <attempt root>

Every worker lane the issued contract names runs through this one entry point. What it binds, per run:

* **the contract** -- its SHA-256 must equal the digest the sealed issuance recorded, the lane must be a
  worker lane of that contract, the out-root must be the contract's evidence root, and the contract's command
  for the lane must invoke this runner for that lane;
* **the source** -- branch, head, tree, the SHA-256 of the full recursive tree listing (the 64-hex source
  digest a submission names), descent from the issued base, and a clean worktree before *and* after the lane;
* **the interpreter and dependencies** -- executable, version, digest and ``pip freeze --all``;
* **imports** -- children get ``PYTHONPATH=<worktree>;<worktree>\src`` and test runs go through
  :mod:`aggie_analytics.validation.unittest_census` with ``--selected-root``, which refuses an import from any
  other checkout (MF37A02-05);
* **data** -- the delivered database by digest where a lane reads it, and a before/after measurement of the
  data root and ``C:\All-22`` plus the heads and status of the main checkout and the integration worktree;
* **write and network scope** -- children run under the BAS canonical write guard over the data root, the
  main checkout, the integration worktree and All-22, with only this attempt's evidence, validation and
  packaging roots writable, and under ``BAS_NETWORK_GUARD=DENY_NON_LOOPBACK``. The exceptions are named in the
  receipt: the guard's own suite (it installs and strips guards itself) and the platform reader (it calls
  ``gh``); both are measured by the snapshots instead;
* **credentials** -- credential-bearing environment variables are removed from every child.

Raw output of every command is written under the run directory before any classification, and every lane
receipt is a new file in a new run directory: no earlier run, Attempt 2 receipt or log is overwritten. A lane
decides what its commands did. It does not decide scientific acceptance, and it cannot turn an inherited red
lane green.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

sys.dont_write_bytecode = True

WORKTREE = Path(__file__).resolve().parents[2]
if str(WORKTREE / "src") not in sys.path:
    sys.path.insert(0, str(WORKTREE / "src"))

from aggie_analytics.validation.lane_harness import (  # noqa: E402
    BLOCKED,
    FAIL,
    NOT_RUN,
    PASS,
    UNSATISFIED,
    run_lane,
)

CYCLE_NUMBER = 37
ATTEMPT_NUMBER = 3
CYCLE_ID = "CYCLE-37"
ATTEMPT_ID = "ATTEMPT-03-20260924"
RUNNER_VERSION = "BAS-C37-ATTEMPT03-LANES-v1"
BASE_SHA = "8fcb5fb66867ef08a61de12bf2eff569b54ac253"
BRANCH = "codex/BAT-706-cycle37-rework"
LANES = (
    "START_CONTEXT", "WRITE_PROTECTION", "SOURCE_ADMISSION", "SOURCE_HARNESS", "SOURCE_REGRESSIONS",
    "INSTALLED_CONSUMER_C01", "CLAIM_SUCCESSOR", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED", "TRUE_UNMOUNTED",
    "PLATFORM_CARRY", "FINAL_PACKET",
)

DATA_ROOT = Path(r"C:\BatteredAggieSyndrome.data")
EVIDENCE_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempt03"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a03")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37a03")
MAIN_CHECKOUT = Path(r"C:\BatteredAggieSyndrome")
INTEGRATION_WORKTREE = Path(r"C:\BatteredAggieSyndrome.worktrees\cycle37-integration")
ALL22 = Path(r"C:\All-22")
ATTEMPT2_ROOT = DATA_ROOT / "ops" / "cycle37" / "attempts" / "REWORK-20260922T171601Z"
DELIVERED_DB = (ATTEMPT2_ROOT / "release" / "sha256"
                / "67d2ce357dc36d5a13a8edc94d0ffa9fc27115768817b1ee1ac9dff567757671"
                / "CYCLE37_CORRECTED_NATIONAL_RELEASE.sqlite")
DELIVERED_DB_SHA256 = "757d4b5f0649d60943c4594d6e0c22b7c930f5ef3acf9f675b4f93f328a7d331"
V361_DB = (DATA_ROOT / "ops" / "cycle36" / "runs" / "20260921T200027Z" / "implementation_output"
           / "release_c36_r1" / "CYCLE36_NATIONAL_RELEASE.sqlite")
V371_DB = (ATTEMPT2_ROOT / "release" / "sha256"
           / "fbeccd3add307e78129ba04630bc00aff343dae8ef3431e910a253237d69e52a"
           / "CYCLE37_CORRECTED_NATIONAL_RELEASE.sqlite")
C01_WHEEL = (DATA_ROOT / "ops" / "manager_reviews" / "cycle35" / "20260921T131038Z" / "c01_release"
             / "cfbintelligencecontracts-0.1.2-py3-none-any.whl")
C01_WHEEL_SHA256 = "a57d4a58cb268e14f88ea7a66bf49131e89b7f930ea1acabc05c2dfeca689af3"
MANAGER_PROBES = DATA_ROOT / "ops" / "manager_reviews" / "cycle37" / "attempt02" / "final-review-20260924143701Z"
ALL22_REMOTE_MANIFEST = (DATA_ROOT / "ops" / "manager_reviews" / "cycle37" / "attempt03" / "issued-20260924"
                         / "REMOTE_OWNER_AUTHORITY_MANIFEST.json")
#: The two granted AFTER handoff comments: (issue, deterministic marker). Their bodies are authored under
#: evidence/platform/AFTER/comment_bodies/<marker>.txt before the lane runs.
AFTER_COMMENTS = (("BAT-706", "C37-A03-AFTER-HANDOFF-BAT-706"), ("BAT-708", "C37-A03-AFTER-HANDOFF-BAT-708"))
GOVERNANCE = DATA_ROOT / "ops" / "manager_review" / "releases" / "v2.4.0"
GUARD_DIR = WORKTREE / "tools" / "cycle37" / "canonical_write_guard"
GUARDED_ROOTS = (DATA_ROOT, MAIN_CHECKOUT, INTEGRATION_WORKTREE, ALL22)
#: Live areas of other writers, and this attempt's own root, are not measured for writes: the manager's review
#: trees and a Cycle 26 session watchdog that rewrites its status every minute. The guard still protects them.
WATCH_EXCLUDED = (
    DATA_ROOT / "ops" / "manager_review",
    DATA_ROOT / "ops" / "manager_reviews",
    DATA_ROOT / "ops" / "cycle26" / "session_watchdog",
    EVIDENCE_ROOT,
)
#: Measured with no lane running (evidence/scope/IDLE_WINDOW_*.json): another system's worker rewrites its own
#: check scratch here every few seconds. It is excluded from the write measurement only; the guard still
#: refuses every guarded lane child a write anywhere under All-22.
ALL22_EXCLUDED = (ALL22 / "Instructions" / "LANE_SYSTEM_DEVELOPMENT_PM_WORKER_V2" / "cycles",)
CREDENTIAL_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "APIKEY", "JIRA", "ATLASSIAN", "OPENAI",
                      "OPENROUTER", "ANTHROPIC", "AWS_", "SCRAPFLY", "GH_", "GITHUB_", "CREDENTIAL")
BILL = "Bill Anderson (American football, born 1925)"

#: Modules this attempt changed or depends on. Each must resolve inside the selected worktree at START_CONTEXT
#: and inside site-packages, never a checkout, in the installed lane.
BOUND_MODULES = (
    "aggie_analytics.validation.lane_harness",
    "aggie_analytics.validation.unittest_census",
    "aggie_analytics.cycle33.query",
    "aggie_analytics.cycle35.query",
    "aggie_analytics.cycle36.release_query",
    "aggie_analytics.cycle36.kernel_reference",
    "aggie_analytics.cycle36.scoring_guards",
    "aggie_analytics.cycle37.admission_domains",
    "aggie_analytics.cycle37.receipt_authority",
    "aggie_analytics.cycle37.receipt_fixtures",
    "aggie_analytics.cycle36.c01_boundary",
)

#: SOURCE_ADMISSION: the admission suites and the manager's admission/PIT negatives (MF37A02-02/03).
ADMISSION_SUITES = (
    "test_cycle36_scoring_guards",
    "test_cycle36_kernel_reference",
    "test_cycle37_admission_domains",
    "test_cycle37_a03_admission_authority",
)
#: SOURCE_HARNESS: harness accounting, lane classification and the six governance tests that need the root.
HARNESS_SUITES = (
    "test_cycle37_a03_harness_accounting",
    "test_cycle37_lane_harness",
    "test_acceptance_governance",
)
#: SOURCE_REGRESSIONS: every suite bound to a module this attempt changed, the predecessor-positive suites of
#: those modules, and the Attempt 2 focused set. The guard's own suite runs in WRITE_PROTECTION instead,
#: because it installs and strips guards itself and cannot run inside one.
REGRESSION_SUITES = (
    "test_cycle37_a03_admission_authority",
    "test_cycle37_a03_harness_accounting",
    "test_cycle37_a03_release_dispatch",
    "test_cycle37_a03_c29_claim_successor",
    "test_cycle36_scoring_guards",
    "test_cycle36_kernel_reference",
    "test_cycle37_admission_domains",
    "test_cycle37_release_query",
    "test_cycle37_corrected_release",
    "test_cycle35_r35_06_query_adapter",
    "test_cycle36_release_builder",
    "test_cycle33_national_staff",
    "test_acceptance_governance",
    "test_cycle37_workspace_paths",
    "test_cycle37_lane_harness",
    "test_cycle37_source_identity",
    "test_cycle37_membership_authenticity",
    "test_cycle37_national_eras",
    "test_cycle37_deterministic_stats",
    "test_cycle37_restoration_search",
    "test_cycle37_c01_boundary_repair",
    "test_cycle37_plan_domain_trace",
    "test_cycle37_cfip_proposals",
    "test_cycle37_obligation_reverification",
    "test_cycle37_contest_site",
    "test_cycle37_responsibility",
    "test_cycle37_kernel_reconciliation",
    "test_cycle37_staff_reparse",
    "test_cycle37_career_reparse",
    "test_cycle37_user_corpus_lineage",
    "test_cycle37_fetch",
    "test_cycle37_alias_team_season",
    "test_cycle37_career_link_identity",
    "test_cycle37_independent_tools",
    "test_cycle37_thread_repairs",
    "test_cycle37_packet_headline",
    "test_cycle36_c01_boundary",
    "test_cycle36_membership_lineage",
    "test_cycle33_availability_pit_corpus",
    "test_cycle36_availability_identity",
    "test_tracked_file_purity",
)
CLAIM_SUITES = ("test_cycle37_a03_c29_claim_successor", "test_cycle37_thread_repairs")


# ------------------------------------------------------------------ helpers


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def sha256_file(path: Path) -> str | None:
    path = Path(path)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str, repo: Path = WORKTREE) -> subprocess.CompletedProcess[str]:
    """Git with optional locks disabled, so reading any checkout never rewrites its index."""

    return subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", check=False)


def git_out(*args: str, repo: Path = WORKTREE) -> str:
    return (git(*args, repo=repo).stdout or "").strip()


def porcelain(repo: Path = WORKTREE) -> list[str]:
    completed = git("status", "--porcelain=v1", "-uall", "-z", repo=repo)
    return [record for record in (completed.stdout or "").split("\0") if len(record) >= 4]


def source_digest(head: str = "HEAD") -> str:
    """SHA-256 of ``git ls-tree -r --full-tree <head>``: every path, mode and blob of the committed subject."""

    completed = subprocess.run(["git", "--no-optional-locks", "-C", str(WORKTREE), "ls-tree", "-r", "--full-tree",
                                head], capture_output=True, check=True)
    return sha256_bytes(completed.stdout)


def write_json(path: Path, value: Any) -> str:
    """Create a new JSON file (never replace one) and return its SHA-256."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, default=str, ensure_ascii=False) + "\n")
    return sha256_file(path) or ""


def snapshot(root: Path, excluded: Iterable[Path] = ()) -> dict[str, list[int]]:
    """[size, mtime_ns, birth_ns] per file and [0, 0, birth_ns] per directory; reparse points never followed."""

    skip = {os.path.normcase(str(path)) for path in excluded}
    result: dict[str, list[int]] = {}
    stack = [str(root)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if os.path.normcase(entry.path) in skip:
                        continue
                    try:
                        stat = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    birth = getattr(stat, "st_birthtime_ns", None) or stat.st_ctime_ns
                    is_dir = entry.is_dir(follow_symlinks=False)
                    result[os.path.relpath(entry.path, root).replace("\\", "/")] = (
                        [0, 0, birth] if is_dir else [stat.st_size, stat.st_mtime_ns, birth])
                    if is_dir and not getattr(stat, "st_file_attributes", 0) & 0x400:
                        stack.append(entry.path)
        except OSError:
            continue
    return result


def diff_snapshots(before: dict[str, list[int]], after: dict[str, list[int]]) -> dict[str, Any]:
    created = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(path for path in set(before) & set(after) if before[path] != after[path])
    return {"created": created[:200], "removed": removed[:200],
            "changed": [{"path": p, "before": before[p], "after": after[p]} for p in changed[:200]],
            "count": len(created) + len(removed) + len(changed)}


def credential_scrub() -> dict[str, None]:
    return {key: None for key in os.environ if any(marker in key.upper() for marker in CREDENTIAL_MARKERS)}


class Tee:
    """Mirror the runner's own console into the lane log (the submission's command_log evidence)."""

    def __init__(self, path: Path, stream) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = path.open("x", encoding="utf-8", newline="\n")
        self.stream = stream

    def write(self, text: str) -> int:
        self.handle.write(text)
        self.handle.flush()
        return self.stream.write(text)

    def flush(self) -> None:
        self.handle.flush()
        self.stream.flush()


# --------------------------------------------------------------- the context


class LaneRun:
    """Everything one lane invocation binds, runs and records."""

    def __init__(self, lane: str, contract_path: Path, out_root: Path) -> None:
        self.lane = lane
        self.contract_path = contract_path
        self.out_root = out_root
        self.stamp = utc_stamp()
        self.run_dir = out_root / "lanes" / lane / self.stamp
        self.log_dir = self.run_dir / "logs"
        self.census_dir = self.run_dir / "census"
        self.work = VALIDATION_ROOT / "lanes" / lane / self.stamp
        # Children's TEMP is the packaging root itself, in its long spelling. Two measured constraints fix that
        # choice: the workspace-path suites allocate run roots under TEMP within an 86-character budget (met
        # by a TEMP of at most 41 characters), and suites that resolve() their temporary paths break under an
        # 8.3 spelling (the resolved and unresolved spellings then name different identities) or overflow
        # MAX_PATH under a longer one. The packaging root is the only attempt-owned directory that satisfies
        # all three; tempfile gives every use its own unique subdirectory inside it.
        self.tmp = PACKAGING_ROOT
        for path in (self.log_dir, self.census_dir, self.tmp, self.work):
            path.mkdir(parents=True, exist_ok=True)
        self.tmp_spelling = str(self.tmp)
        self.guard_log = self.log_dir / "guard_events.jsonl"
        self.python = Path(sys.executable)
        self.commands: list[dict[str, Any]] = []
        self.problems: list[str] = []
        self.exceptions: list[str] = []
        self.extra: dict[str, Any] = {}
        self.started = utc_now()
        self.contract: dict[str, Any] = {}
        self.binding: dict[str, Any] = {}
        self.rehearsal = False

    # ---------------------------------------------------------------- env
    def env(self, *, guarded: bool = True, network: bool = False, pythonpath: str | None = "source",
            extra: dict[str, str | None] | None = None) -> dict[str, str | None]:
        env: dict[str, str | None] = dict(credential_scrub())
        paths = {"source": os.pathsep.join((str(WORKTREE), str(WORKTREE / "src"))), None: None}
        base = paths.get(pythonpath, pythonpath)
        env.update({
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONHASHSEED": None,
            "TEMP": self.tmp_spelling,
            "TMP": self.tmp_spelling,
            "BAS_VALIDATION_ROOT": str(VALIDATION_ROOT),
            "BAS_PACKAGING_ROOT": str(PACKAGING_ROOT),
            "PIP_NO_INDEX": "1",
            "PIP_NO_CACHE_DIR": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "BAS_CANONICAL_WRITE_GUARD": None,
            "BAS_CANONICAL_WRITE_ALLOW": None,
            "BAS_CANONICAL_WRITE_GUARD_LOG": None,
            "BAS_NETWORK_GUARD": None,
        })
        parts = [part for part in (base or "").split(os.pathsep) if part]
        if guarded:
            parts.insert(0, str(GUARD_DIR))
            env["BAS_CANONICAL_WRITE_GUARD"] = os.pathsep.join(str(root) for root in GUARDED_ROOTS if root.exists())
            env["BAS_CANONICAL_WRITE_ALLOW"] = os.pathsep.join((str(self.out_root), str(VALIDATION_ROOT),
                                                                 str(PACKAGING_ROOT)))
            env["BAS_CANONICAL_WRITE_GUARD_LOG"] = str(self.guard_log)
            if not network:
                env["BAS_NETWORK_GUARD"] = "DENY_NON_LOOPBACK"
        env["PYTHONPATH"] = os.pathsep.join(parts) if parts else None
        if extra:
            env.update(extra)
        return env

    # ---------------------------------------------------------------- run
    def run(self, name: str, argv: Iterable[Any], *, cwd: Path = WORKTREE, kind: str = "CHECK",
            env: dict[str, str | None] | None = None, timeout: int = 3600, note: str = "",
            census: tuple[Path, Path] | None = None, expect_exit: int = 0) -> dict[str, Any]:
        record = run_lane(f"{self.lane}__{name}", [str(item) for item in argv], cwd=cwd,
                          env=env if env is not None else self.env(), timeout=timeout, log_dir=self.log_dir,
                          parse=kind.upper() == "TEST", kind=kind, note=note, census=census)
        record["expected_exit"] = expect_exit
        if expect_exit != 0:
            # A deliberate negative control: the command must fail, with exactly the declared exit code.
            record["result_against_expectation"] = PASS if record.get("exit_code") == expect_exit else FAIL
        else:
            record["result_against_expectation"] = record["result"]
        record["log_sha256"] = sha256_file(Path(record["log_path"]))
        self.commands.append(record)
        print(f"[{self.lane}] {name}: {record['result_against_expectation']} (exit {record.get('exit_code')}, "
              f"{record.get('elapsed_seconds')}s) {record.get('state_reason') or ''}")
        return record

    def census(self, name: str, names: Iterable[str] = (), *, start_dir: str | None = None,
               env: dict[str, str | None] | None = None, timeout: int = 3600, note: str = "") -> dict[str, Any]:
        records = self.census_dir / f"{name}.records.jsonl"
        summary = self.census_dir / f"{name}.summary.json"
        argv: list[Any] = [self.python, "-B", "-m", "aggie_analytics.validation.unittest_census", *names,
                           "--records", records, "--summary", summary, "--selected-root", WORKTREE, "-v"]
        if start_dir:
            argv += ["--start-dir", start_dir]
        record = self.run(name, argv, cwd=WORKTREE / "tests", kind="TEST", env=env, timeout=timeout, note=note,
                          census=(records, summary))
        record["census_records"] = str(records)
        record["census_summary"] = str(summary)
        if summary.is_file():
            data = json.loads(summary.read_text(encoding="utf-8"))
            audit = data.get("origin_audit") or {}
            record["runner_inside_selected_root"] = audit.get("runner_inside_selected_root")
            if audit.get("runner_inside_selected_root") is False:
                self.problems.append(f"{name}: the census runner itself was imported from outside the worktree")
        return record

    def fresh(self, name: str) -> Path:
        path = self.work / name
        if path.exists():
            raise RuntimeError(f"{path} exists; lane work directories are never reused")
        path.mkdir(parents=True)
        return path


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
        problems.append("contract is not Cycle 37 Attempt 3")
    if contract.get("attempt_id") != ATTEMPT_ID:
        problems.append(f"contract attempt_id {contract.get('attempt_id')!r} is not {ATTEMPT_ID}")
    lanes = {row["id"]: row for row in contract.get("required_lanes", [])}
    row = lanes.get(lane)
    if row is None or row.get("executor") != "worker":
        problems.append(f"{lane} is not a worker lane of this contract")
    elif f"attempt03_lanes.py --lane {lane} " not in row.get("command", ""):
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
        "runner": str(Path(__file__).resolve()),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "runner_version": RUNNER_VERSION,
    }


def bind_interpreter(python: Path) -> dict[str, Any]:
    freeze = subprocess.run([str(python), "-m", "pip", "freeze", "--all"], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=False,
                            env={**{k: v for k, v in os.environ.items() if k not in credential_scrub()},
                                 "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"})
    lines = sorted(line for line in (freeze.stdout or "").splitlines() if line.strip())
    return {"executable": str(python), "sha256": sha256_file(python), "version": sys.version,
            "implementation": platform.python_implementation(), "base_prefix": sys.base_prefix,
            "role": "lane interpreter: an input, never a write target",
            "pip_freeze_exit": freeze.returncode, "distributions": lines,
            "distributions_sha256": sha256_bytes("\n".join(lines).encode("utf-8")),
            "editable_installs": [line for line in lines if line.startswith("-e ")]}


def checkout_state(path: Path) -> dict[str, Any]:
    if not path.is_dir():
        return {"path": str(path), "exists": False}
    return {"path": str(path), "exists": True, "head": git_out("rev-parse", "HEAD", repo=path),
            "status_entries": len(porcelain(path))}


def scope_before() -> dict[str, Any]:
    return {"data_root": snapshot(DATA_ROOT, WATCH_EXCLUDED),
            "all22": snapshot(ALL22, ALL22_EXCLUDED) if ALL22.is_dir() else {},
            "main_checkout": checkout_state(MAIN_CHECKOUT),
            "integration_worktree": checkout_state(INTEGRATION_WORKTREE)}


def scope_after(before: dict[str, Any]) -> dict[str, Any]:
    after_data = snapshot(DATA_ROOT, WATCH_EXCLUDED)
    after_all22 = snapshot(ALL22, ALL22_EXCLUDED) if ALL22.is_dir() else {}
    main_after = checkout_state(MAIN_CHECKOUT)
    integration_after = checkout_state(INTEGRATION_WORKTREE)
    data = diff_snapshots(before["data_root"], after_data)
    all22 = diff_snapshots(before["all22"], after_all22)
    return {
        "measured_roots": [str(DATA_ROOT), str(ALL22)],
        "excluded_from_measurement": [str(path) for path in (*WATCH_EXCLUDED, *ALL22_EXCLUDED)],
        "exclusion_basis": ("Other writers' live areas and this attempt's own root; the All-22 lane-system "
                            "scratch was measured changing with no lane running "
                            f"({sorted(str(p) for p in (EVIDENCE_ROOT / 'evidence' / 'scope').glob('IDLE_WINDOW_*.json'))})."),
        "data_root": data,
        "all22": all22,
        "main_checkout": {"before": before["main_checkout"], "after": main_after,
                          "unchanged": before["main_checkout"] == main_after},
        "integration_worktree": {"before": before["integration_worktree"], "after": integration_after,
                                 "unchanged": before["integration_worktree"] == integration_after},
        "writes_outside_owned_roots": data["count"] + all22["count"],
    }


# ------------------------------------------------------------------ lanes


def lane_start_context(run: LaneRun) -> None:
    contract = run.contract
    run.run("git_subject", ["git", "--no-optional-locks", "-C", WORKTREE, "rev-parse", "HEAD", "HEAD^{tree}"],
            env=run.env(guarded=False))
    run.run("git_status", ["git", "--no-optional-locks", "-C", WORKTREE, "status", "--porcelain=v1", "-uall",
                           "--branch"], env=run.env(guarded=False))
    probe = ("import importlib, pathlib, sys\n"
             "root = pathlib.Path(sys.argv[1]).resolve()\n"
             "outside = []\n"
             "for name in sys.argv[2:]:\n"
             "    origin = pathlib.Path(importlib.import_module(name).__file__).resolve()\n"
             "    print(name, origin)\n"
             "    if root not in origin.parents:\n"
             "        outside.append(name)\n"
             "print('outside the selected worktree:', outside or 'none')\n"
             "sys.exit(1 if outside else 0)\n")
    run.run("module_origins", [run.python, "-B", "-c", probe, WORKTREE, *BOUND_MODULES])
    run.run("retired_assistive_decommission",
            [run.python, "-B", "tools/validate_retired_assistive_pipeline_decommission.py", "--repo-root", "."],
            note="The branch AGENTS.md retires the Fort Knox interlock; this proves the decommission, read-only.")
    database = sha256_file(DELIVERED_DB)
    wheel = sha256_file(C01_WHEEL)
    total, used, free = shutil.disk_usage("C:/")
    budgets = contract.get("budgets", {})
    reserve = int(budgets.get("storage_reserve_bytes") or 0)
    run.extra.update({
        "delivered_database": {"path": str(DELIVERED_DB), "sha256": database, "expected": DELIVERED_DB_SHA256,
                               "bytes": DELIVERED_DB.stat().st_size if DELIVERED_DB.is_file() else None},
        "c01_wheel": {"path": str(C01_WHEEL), "sha256": wheel, "expected": C01_WHEEL_SHA256},
        "storage": {"free_bytes": free, "reserve_bytes": reserve, "reserve_satisfied": free >= reserve,
                    "peak_extra_bytes": budgets.get("storage_peak_extra_bytes")},
        "hold_active": contract.get("authority", {}).get("hold_active"),
        "grants": [{k: g.get(k) for k in ("actor", "action", "target")} for g in contract.get("authority", {}).get("grants", [])],
        "main_checkout": checkout_state(MAIN_CHECKOUT),
        "integration_worktree": checkout_state(INTEGRATION_WORKTREE),
        "registered_worktrees": [line.split(" ", 1)[1] for line in git_out("worktree", "list", "--porcelain").splitlines()
                                 if line.startswith("worktree ")],
        "retired_assistive_interlock": ("The main checkout's AGENTS.md still carries the P0 Fort Knox text; this "
                                        "branch's AGENTS.md retires it and forbids running "
                                        "validate_codex_usage_interlock.py as a gate. The contract forbids reviving "
                                        "retired assistive execution. The decommission validator is run instead."),
    })
    if database != DELIVERED_DB_SHA256:
        run.problems.append("the delivered database does not match its issued digest")
    if wheel != C01_WHEEL_SHA256:
        run.problems.append("the released C01 wheel does not match its digest")
    if reserve and free < reserve:
        run.problems.append(f"free space {free} is below the contract reserve {reserve}")
    if not contract.get("authority", {}).get("hold_active"):
        run.problems.append("the contract no longer records an active hold")


def _replay(run: LaneRun, script: str, *, adapt: dict[str, str] | None = None) -> tuple[Path, dict[str, Any]]:
    """Copy a saved manager probe into an owned directory, byte-for-byte unless ``adapt`` rewrites path literals."""

    source = MANAGER_PROBES / script
    original = source.read_bytes()
    target_dir = run.fresh(f"replay_{Path(script).stem}")
    text = original.decode("utf-8")
    changes = []
    for old, new in (adapt or {}).items():
        if text.count(old) != 1:
            raise RuntimeError(f"{script}: the path literal to adapt occurs {text.count(old)} times, not once")
        text = text.replace(old, new)
        changes.append({"from": old, "to": new})
    target = target_dir / script
    target.write_bytes(text.encode("utf-8"))
    return target, {"manager_original": str(source), "manager_original_sha256": sha256_bytes(original),
                    "replay_copy": str(target), "replay_copy_sha256": sha256_file(target),
                    "byte_identical": not changes, "path_adaptations": changes}


def first_json(text: str) -> Any:
    """The first complete JSON object in a log (stdout comes first; stderr follows and is ignored)."""

    start = text.find("{")
    if start < 0:
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:])
    except ValueError:
        return None
    return value


def _stdout_json(record: dict[str, Any]) -> Any:
    return first_json(Path(record["log_path"]).read_text(encoding="utf-8", errors="replace"))


def _gz_json(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return first_json(handle.read())


def lane_write_protection(run: LaneRun) -> None:
    run.exceptions.append("The guard's own suite and the manager's guard probe run without the lane guard: they "
                          "install, strip and propagate guards themselves, so an outer guard would change what "
                          "they test. The before/after snapshots measure this lane instead.")
    run.census("guard_suite", ["test_cycle37_canonical_write_guard"], env=run.env(guarded=False),
               note="Manager counterexample verbatim, the general route matrix and the network cases.")
    probe, replay = _replay(run, "probe_write_guard.py")
    record = run.run("manager_probe_write_guard_replay", [run.python, "-B", probe], cwd=probe.parent,
                     env=run.env(guarded=False, pythonpath=None),
                     note="Manager's saved probe, byte-identical copy in an owned directory; it only writes its "
                          "own guard-probe scratch beside the copy.")
    result_path = probe.parent / "WRITE_GUARD_INDEPENDENT_PROBE.json"
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
    outcome = json.loads(result.get("stdout") or "{}") if result.get("stdout") else {}
    refused = all(outcome.get(key) == "CanonicalWriteRefused" for key in ("ordinary_write", "sqlite_update",
                                                                          "keyword_unlink"))
    preserved = (result.get("ordinary_write_preserved") is True and result.get("sqlite_value") == "ORIGINAL"
                 and result.get("keyword_target_exists") is True)
    run.extra["manager_write_guard_probe"] = {**replay, "result_file": str(result_path),
                                              "result_sha256": sha256_file(result_path), "child_outcomes": outcome,
                                              "all_three_refused": refused, "bytes_preserved": preserved,
                                              "exit": record.get("exit_code")}
    if not (refused and preserved):
        run.problems.append(f"the manager's guard probe is not fully refused: {outcome}, preserved={preserved}")
    if result_path.is_file():
        shutil.copy2(result_path, run.run_dir / "WRITE_GUARD_INDEPENDENT_PROBE.replay.json")


def lane_source_admission(run: LaneRun) -> None:
    run.census("admission_suites", ADMISSION_SUITES)
    receipt = run.run_dir / "ADMISSION_SOURCE_PROBE.json"
    run.run("attempt03_admission_probe_source",
            [run.python, "-B", "tools/cycle37/attempt03_admission_probe.py", "--mode", "source", "--import-root",
             WORKTREE / "src", "--scratch", run.fresh("admission_probe"), "--out", receipt])
    for script in ("probe_admission.py", "probe_pit.py"):
        probe, replay = _replay(run, script)
        record = run.run(f"manager_{Path(script).stem}_replay_source",
                         [run.python, "-B", probe, WORKTREE / "src"], cwd=probe.parent,
                         note="Manager's saved probe, byte-identical, importing the selected worktree's src.")
        run.extra[f"manager_{Path(script).stem}"] = {**replay, **_judge_manager_probe(script, record)}
        if not run.extra[f"manager_{Path(script).stem}"]["all_refused"]:
            run.problems.append(f"{script}: a manager counterexample is still admitted from source")
    run.extra["attempt03_admission_probe"] = _admission_receipt(run, receipt)


def _admission_receipt(run: LaneRun, receipt: Path) -> dict[str, Any]:
    data = json.loads(receipt.read_text(encoding="utf-8")) if receipt.is_file() else {}
    summary = {"receipt": str(receipt), "sha256": sha256_file(receipt), "result": data.get("result"),
               "case_count": data.get("case_count"), "mismatches": data.get("mismatches"),
               "modules": data.get("modules"), "resolved_inside_a_git_checkout": data.get("resolved_inside_a_git_checkout")}
    if data.get("result") != PASS or not data.get("case_count"):
        run.problems.append(f"the admission probe did not pass every case: {summary['mismatches']}")
    return summary


def _judge_manager_probe(script: str, record: dict[str, Any]) -> dict[str, Any]:
    output = _stdout_json(record) or {}
    verdicts: dict[str, Any] = {}
    if script == "probe_admission.py":
        for name, result in (output.get("results") or {}).items():
            state = (result or {}).get("state") if isinstance(result, dict) else None
            admitted = isinstance(result, dict) and (result.get("admitted") is True
                                                     or state == "ADMITTED_FOR_SCORING")
            verdicts[name] = {"state": state or (result or {}).get("exception"), "admitted": admitted}
        expected = 6
    else:
        for name, case in (output.get("cases") or {}).items():
            classification = (case or {}).get("classification") or {}
            admitted = bool(case.get("standalone_gate")) or bool(case.get("row_bound_gate")) or \
                classification.get("successor_state") == "PIT_PROVEN"
            verdicts[name] = {"successor_state": classification.get("successor_state"),
                              "standalone_gate": case.get("standalone_gate"),
                              "row_bound_gate": case.get("row_bound_gate"), "admitted": admitted}
        expected = 3
    return {"exit": record.get("exit_code"), "module": output.get("module"),
            "module_sha256": output.get("module_sha256"), "interpreter": output.get("interpreter"),
            "cases": verdicts, "case_count": len(verdicts), "expected_case_count": expected,
            "all_refused": len(verdicts) == expected and not any(v["admitted"] for v in verdicts.values())
            and record.get("exit_code") == 0}


def lane_source_harness(run: LaneRun) -> None:
    run.census("harness_suites", HARNESS_SUITES,
               note="The six governance tests import tools.validate_acceptance from the selected root.")
    # The original MF37A02-05 failure, reproduced deliberately: the Attempt 2 invocation put only src on the
    # path, so the governance tests could not import tools.* from the selected root.
    control = run.run("attempt2_invocation_negative_control",
                      [run.python, "-B", "-m", "unittest", "-v", "test_acceptance_governance"],
                      cwd=WORKTREE / "tests", kind="CHECK", expect_exit=1,
                      env=run.env(pythonpath=str(WORKTREE / "src")),
                      note="PYTHONPATH=src only, as Attempt 2 ran it: must fail to import tools.* here.")
    text = Path(control["log_path"]).read_text(encoding="utf-8", errors="replace")
    run.extra["attempt2_invocation_negative_control"] = {
        "exit": control.get("exit_code"), "import_error_seen": "ModuleNotFoundError" in text or "ImportError" in text,
        "log": control["log_path"]}
    probe, replay = _replay(run, "probe_harness_import.py")
    record = run.run("manager_probe_harness_import_replay", [run.python, "-B", probe], cwd=probe.parent,
                     env=run.env(pythonpath=None),
                     note="Manager's saved probe, byte-identical; it refuses writes, children and network itself.")
    output = _stdout_json(record) or {}
    run.extra["manager_harness_import_probe"] = {
        **replay, "exit": record.get("exit_code"), "without_repo_root": output.get("without_repo_root"),
        "positive_tests": output.get("positive_tests"), "positive_failures": output.get("positive_failures"),
        "positive_errors": output.get("positive_errors"),
        "positive_imported_tool": output.get("positive_imported_tool")}
    tool = str(output.get("positive_imported_tool") or "")
    if not (output.get("positive_tests") == 6 and not output.get("positive_failures")
            and not output.get("positive_errors") and tool.lower().startswith(str(WORKTREE).lower())):
        run.problems.append("the manager harness-import probe did not run six passing tests from this worktree")
    # The Attempt 2 full-suite log, re-read with the repaired parser: the four skips the old parser missed.
    log = ATTEMPT2_ROOT / "logs" / "full-final-mounted" / "full-final-mounted__full_suite_final.log"
    if log.is_file():
        from aggie_analytics.validation import lane_harness

        parsed = lane_harness.parse_unittest(log.read_text(encoding="utf-8", errors="replace"))
        raw_skip_lines = len(re.findall(r" \.\.\. skipped", log.read_text(encoding="utf-8", errors="replace")))
        run.extra["attempt2_log_reparse"] = {
            "log": str(log), "sha256": sha256_file(log), "tests_run": parsed.get("tests_run"),
            "raw_skip_lines": raw_skip_lines, "parsed_skips": len(parsed.get("skipped") or []),
            "skipped_count": parsed.get("skipped_count"), "executed_test_count": parsed.get("executed_test_count"),
            "reconciliation": lane_harness.reconcile(parsed)}


def lane_source_regressions(run: LaneRun) -> None:
    run.census("regression_suites", REGRESSION_SUITES,
               note="Changed-module suites, their predecessor-positive suites and the Attempt 2 focused set.")


def lane_claim_successor(run: LaneRun) -> None:
    run.census("claim_suites", CLAIM_SUITES)
    successor = WORKTREE / "artifacts" / "scientific_integrity" / "cycle29_successor" / \
        "CYCLE29_CLAIM_INVENTORY_SUCCESSOR.v1.json"
    default = run.run("validator_default_still_fails", [run.python, "-B", "tools/validate_cycle29_gates.py"],
                      expect_exit=1, note="The committed inventory alone: its 35 omissions are still reported.")
    selected = run.run("validator_with_the_selected_successor",
                       [run.python, "-B", "tools/validate_cycle29_gates.py", "--claim-inventory-successor", successor])
    census_out = run.run_dir / "CYCLE29_NUMERIC_CENSUS.rerun.json"
    run.run("census_rerun", [run.python, "-B", "tools/cycle37/c29_numeric_census.py", "--out", census_out])
    rebuilt = run.run_dir / "CYCLE29_CLAIM_INVENTORY_SUCCESSOR.rerun.json"
    run.run("successor_rebuild", [run.python, "-B", "tools/cycle37/c29_claim_successor.py", "--census", census_out,
                                  "--out", rebuilt])
    committed = json.loads(successor.read_text(encoding="utf-8"))
    comparison: dict[str, Any] = {}
    if census_out.is_file() and rebuilt.is_file():
        census = json.loads(census_out.read_text(encoding="utf-8"))
        again = json.loads(rebuilt.read_text(encoding="utf-8"))
        comparison = {
            "census_body_sha256_rerun": census.get("census_body_sha256"),
            "census_body_sha256_committed": committed["census"]["census_body_sha256"],
            "census_reproduced": census.get("census_body_sha256") == committed["census"]["census_body_sha256"],
            "claims_reproduced": again["claims"] == committed["claims"],
            "dispositions_reproduced": again["census_pair_dispositions"] == committed["census_pair_dispositions"],
            "accounting_reproduced": again["numeric_value_accounting"] == committed["numeric_value_accounting"],
            "carried_forward_reproduced": again["carried_forward_original_claims"]
            == committed["carried_forward_original_claims"],
        }
    inventory = WORKTREE / "artifacts" / "scientific_integrity" / "cycle29" / "CYCLE29_CLAIM_INVENTORY.json"
    committed_inventory = subprocess.run(["git", "--no-optional-locks", "-C", str(WORKTREE), "show",
                                          f"{BASE_SHA}:artifacts/scientific_integrity/cycle29/CYCLE29_CLAIM_INVENTORY.json"],
                                         capture_output=True, check=False).stdout
    comparison.update({
        "original_inventory_sha256": sha256_file(inventory),
        "original_inventory_sha256_at_issued_base": sha256_bytes(committed_inventory),
        "original_inventory_unchanged_since_base": sha256_file(inventory) == sha256_bytes(committed_inventory),
        "successor_names_the_same_original": committed["predecessor_inventory"]["sha256"] == sha256_file(inventory),
        "default_reports_35": "35 numeric claims absent" in Path(default["log_path"]).read_text(encoding="utf-8"),
        "selected_passes": selected.get("exit_code") == 0,
    })
    run.extra["claim_successor"] = comparison
    for key, value in comparison.items():
        if isinstance(value, bool) and not value:
            run.problems.append(f"claim successor check failed: {key}")


# ---- installed consumer and C01 -------------------------------------------------------------------------


def _installed_env(run: LaneRun) -> dict[str, str | None]:
    """Installed runs: no source on the path at all, only the guard directory for its sitecustomize."""

    return run.env(pythonpath=None)


#: Everything the setuptools build reads: the project file, its readme, and the ``src`` tree it packages.
BUILD_INPUTS = ("pyproject.toml", "README.md", "src")


def _build_and_install(run: LaneRun) -> dict[str, Any] | None:
    # A short stage keeps every installed file inside MAX_PATH.
    stage = PACKAGING_ROOT / "b" / sha256_bytes(run.stamp.encode("utf-8"))[:8]
    export = stage / "source"
    dist = stage / "dist"
    venv = stage / "venv"
    archive = stage / "source.tar"
    stage.mkdir(parents=True)
    head = run.binding["head"]
    run.run("git_archive_committed_subject", ["git", "--no-optional-locks", "-C", WORKTREE, "archive",
                                              "--format=tar", "-o", archive, head, "--", *BUILD_INPUTS],
            env=run.env(), note="The wheel is built from the committed subject's build inputs, not the working "
                                "directory.")
    with tarfile.open(archive) as bundle:
        bundle.extractall(export, filter="data")
    build = run.run("build_wheel", [run.python, "-B", "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
                                    "--no-index", "--no-cache-dir", "--disable-pip-version-check", "-w", dist, export],
                    cwd=stage, env=run.env(pythonpath=None), timeout=3600,
                    note="Offline, with the lane interpreter's cached setuptools; no index, cache or isolation.")
    wheels = sorted(dist.glob("aggie_analytics*.whl")) or sorted(dist.glob("*.whl"))
    if build["result"] != PASS or not wheels:
        run.problems.append("the BAS wheel was not built")
        return None
    run.run("create_fresh_venv", [run.python, "-B", "-m", "venv", venv], cwd=stage, env=run.env(pythonpath=None))
    python = venv / "Scripts" / "python.exe"
    run.run("install_bas_and_c01_noneditable", [python, "-m", "pip", "install", "--no-deps", "--no-index",
                                                 "--no-cache-dir", "--disable-pip-version-check", wheels[0],
                                                 C01_WHEEL], cwd=stage, env=_installed_env(run), timeout=1800)
    run.run("pip_check", [python, "-m", "pip", "check"], cwd=stage, env=_installed_env(run))
    run.run("pip_freeze_installed", [python, "-m", "pip", "freeze", "--all"], cwd=stage, env=_installed_env(run))
    script = venv / "Scripts" / "bas-staff-query.exe"
    if not script.is_file():
        run.problems.append("the non-editable install produced no bas-staff-query entry point")
        return None
    return {"stage": stage, "export": export, "wheel": wheels[0], "venv": venv, "python": python, "script": script}


def _equivalence(installed: dict[str, Any]) -> dict[str, Any]:
    """Every file the wheel installed under aggie_analytics, byte-compared with the committed source.

    The installed set is read from the distribution's own RECORD. Committed source files the declared
    package configuration does not ship are listed separately: they are not installed, so they cannot differ.
    """

    site = installed["venv"] / "Lib" / "site-packages"
    records = sorted(site.glob("aggie_analytics_engine-*.dist-info/RECORD"))
    listed = []
    if records:
        for line in records[0].read_text(encoding="utf-8").splitlines():
            name = line.split(",", 1)[0]
            if name.startswith("aggie_analytics/") and not name.endswith(".pyc"):
                listed.append(name)
    different = []
    for name in listed:
        source = WORKTREE / "src" / name
        target = site / name
        if not source.is_file() or not target.is_file() or sha256_file(source) != sha256_file(target):
            different.append(name)
    committed = [path[len("src/"):] for path in git_out("ls-files", "src/aggie_analytics").splitlines()]
    not_packaged = sorted(set(committed) - set(listed))
    python_not_packaged = [name for name in not_packaged if name.endswith(".py")]
    return {"record": str(records[0]) if records else None, "installed_files": len(listed),
            "installed_equal_to_committed_source": len(listed) - len(different), "different": different,
            "committed_source_files": len(committed),
            "committed_files_not_packaged": not_packaged, "python_modules_not_packaged": python_not_packaged,
            "not_packaged_basis": "pyproject declares package data only for aggie_analytics.cycle30 schemas/*.json",
            "pth_files": [p.name for p in site.glob("*.pth")],
            "worktree_on_any_pth": any(str(WORKTREE).lower() in p.read_text(errors="replace").lower()
                                       for p in site.glob("*.pth"))}


def _cli(run: LaneRun, installed: dict[str, Any], name: str, args: list[Any], *, database: Path = DELIVERED_DB,
         expect_exit: int = 0, save: Path | None = None, note: str = "") -> dict[str, Any]:
    record = run.run(name, [installed["script"], "--database", database, *args], cwd=installed["stage"],
                     env=_installed_env(run), expect_exit=expect_exit, timeout=3600, note=note)
    if save is not None:
        text = Path(record["log_path"]).read_bytes()
        with gzip.open(save, "wb") as handle:
            handle.write(text)
        record["saved_output_gzip"] = str(save)
        record["saved_output_sha256"] = sha256_file(save)
    return record


def _payload(record: dict[str, Any]) -> dict[str, Any]:
    value = _stdout_json(record)
    return value if isinstance(value, dict) else {}


def _oracle(database: Path) -> dict[str, Any]:
    """The independent SQL oracle: direct sqlite3 with no aggie_analytics import."""

    conn = sqlite3.connect(f"file:{database.as_posix()}?mode=ro&immutable=1", uri=True)
    try:
        def ids(sql: str) -> list[str]:
            return [str(row[0]) for row in conn.execute(sql)]

        oracle = {
            "career_successor": ids("SELECT episode_id FROM career_episode_successor "
                                    "ORDER BY pageid, family, row_index, interval_index, episode_id"),
            "career_predecessor": ids("SELECT career_episode_id FROM career_episode ORDER BY career_episode_id, span_id"),
            "responsibility_successor": ids("SELECT successor_key FROM responsibility_successor ORDER BY "
                                            "(release_responsibility_id IS NULL), release_responsibility_id, successor_key"),
            "responsibility_predecessor": ids("SELECT responsibility_id FROM responsibility_assertion ORDER BY responsibility_id"),
            "scheme": ids("SELECT scheme_assertion_id FROM scheme_assertion ORDER BY scheme_assertion_id"),
        }
        rows = [dict(zip(("episode_id", "pageid", "page_title", "person_display", "family", "start", "end",
                          "ongoing", "assignments", "classification", "resolution"), row))
                for row in conn.execute('SELECT episode_id, pageid, page_title, person_display, family, start, "end", '
                                        "ongoing, assignments, classification, resolution FROM career_episode_successor")]
        programs = {str(row[0]): json.loads(row[1] or "[]") for row in
                    conn.execute("SELECT program_id, display_names FROM canonical_program")}
    finally:
        conn.close()
    return {"ids": oracle, "career_rows": rows, "programs": programs}


def _python_filter(rows: list[dict[str, Any]], programs: dict[str, list[str]], **flt: Any) -> set[str]:
    """An independent Python implementation of the career filters, sharing no code with the consumer."""

    def norm(value: Any) -> str:
        return " ".join(str(value).split()).casefold()

    result = set()
    team = None
    if flt.get("team"):
        matches = [pid for pid, names in programs.items() if any(norm(n) == norm(flt["team"]) for n in names)]
        team = matches[0] if len(matches) == 1 else "__AMBIGUOUS__"
    for row in rows:
        resolution = json.loads(row["resolution"] or "{}")
        classification = json.loads(row["classification"] or "{}")
        roles = [a.get("role") for a in json.loads(row["assignments"] or "[]") if isinstance(a, dict)]
        season = flt.get("season")
        if team is not None and resolution.get("program_id") != team:
            continue
        if season is not None:
            start, end, ongoing = row["start"], row["end"], row["ongoing"]
            if start is None or start > season or not ((end is not None and end >= season) or (end is None and ongoing == 1)):
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
        result.add(str(row["episode_id"]))
    return result


def _paginate(run: LaneRun, installed: dict[str, Any], label: str, args: list[str], key: str, limit: int,
              expected: list[str], outdir: Path) -> dict[str, Any]:
    seen: list[str] = []
    offset, pages, totals, problems = 0, 0, set(), []
    while True:
        record = _cli(run, installed, f"page_{label}_{pages:02d}", [*args, "--limit", str(limit), "--offset",
                                                                       str(offset), "--compact"],
                      save=outdir / f"{label}_{pages:02d}.json.gz")
        payload = _payload(record)
        pages += 1
        pagination = payload.get("pagination") or {}
        totals.add(pagination.get("total_count"))
        rows = payload.get("rows") or []
        seen.extend(str(row[key]) for row in rows)
        if pagination.get("next_offset") is None or pages > 200:
            break
        if pagination["next_offset"] != offset + len(rows):
            problems.append(f"next_offset {pagination['next_offset']} after {offset}+{len(rows)}")
            break
        offset = pagination["next_offset"]
    result = {"pages": pages, "rows_returned": len(seen), "distinct": len(set(seen)), "expected": len(expected),
              "total_counts_reported": sorted(t for t in totals if t is not None),
              "no_duplicates": len(seen) == len(set(seen)), "same_set_as_oracle": set(seen) == set(expected),
              "same_order_as_oracle": seen == expected, "problems": problems,
              "identity_digest": sha256_bytes("\n".join(seen).encode("utf-8"))}
    result["reconciled"] = (result["no_duplicates"] and result["same_set_as_oracle"] and result["same_order_as_oracle"]
                            and result["total_counts_reported"] == [len(expected)] and not problems)
    if not result["reconciled"]:
        run.problems.append(f"pagination {label} does not reconcile to its table: {result}")
    return result


def _verify_career_locators(outdir: Path, label: str) -> dict[str, Any]:
    """Re-read every corrected row's raw revision and check its recorded spans against the bytes."""

    # Rows arrive ordered by page, so one raw file is held at a time; every file read is still counted.
    read_files: set[str] = set()
    current: tuple[Any, Any] = (object(), None)
    counts = {"rows": 0, "verified": 0, "raw_file_digest_mismatch": 0, "wikitext_not_found": 0,
              "span_mismatch": 0, "team_absent_in_source": 0, "raw_file_absent": 0}
    mismatches: list[dict[str, Any]] = []

    def load(path: Any) -> Any:
        file = Path(path) if path else None
        if file is None or not file.is_file():
            return None
        data = file.read_bytes()
        texts: dict[str, str] = {}

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)
            elif isinstance(node, str) and len(node) > 20:
                texts[sha256_bytes(node.encode("utf-8"))] = node

        walk(json.loads(data.decode("utf-8")))
        return {"sha256": sha256_bytes(data), "texts": texts}

    for page in sorted(outdir.glob(f"{label}_*.json.gz")):
        payload = _gz_json(page) or {}
        for row in payload.get("rows") or []:
            counts["rows"] += 1
            path = row.get("raw_file")
            if current[0] != path:
                current = (path, load(path))
                read_files.add(str(path))
            entry = current[1]
            if entry is None:
                counts["raw_file_absent"] += 1
                continue
            if entry["sha256"] != row.get("raw_file_sha256"):
                counts["raw_file_digest_mismatch"] += 1
                continue
            wikitext = entry["texts"].get(row.get("wikitext_sha256"))
            if wikitext is None:
                counts["wikitext_not_found"] += 1
                continue
            def span(field: str) -> list[int] | None:
                value = json.loads(row[field]) if row.get(field) else None
                # "[null, null]" is how the release records a row whose source states no such text.
                return value if isinstance(value, list) and len(value) == 2 and all(
                    isinstance(v, int) for v in value) else None

            team, team_bytes, years = span("team_char_span"), span("team_byte_span"), span("years_char_span")
            ok = True
            if team is None:
                # The infobox row states years but no team: missingness recorded by the release, not a locator.
                counts["team_absent_in_source"] += 1
                ok = row.get("team_raw") is None
            else:
                ok = wikitext[team[0]:team[1]] == row.get("team_raw")
                if team_bytes:
                    ok = ok and wikitext.encode("utf-8")[team_bytes[0]:team_bytes[1]].decode(
                        "utf-8", "replace") == row.get("team_raw")
            if years is not None and row.get("years_raw") is not None:
                ok = ok and wikitext[years[0]:years[1]] == row.get("years_raw")
            if ok:
                counts["verified"] += 1
            else:
                counts["span_mismatch"] += 1
                if len(mismatches) < 25:
                    mismatches.append({"episode_id": row.get("episode_id"), "team_raw": row.get("team_raw"),
                                       "at_team_span": wikitext[team[0]:team[1]][:200] if team else None,
                                       "years_raw": row.get("years_raw"),
                                       "at_years_span": wikitext[years[0]:years[1]][:200] if years else None})
    return {**counts, "raw_files_read": len(read_files), "mismatch_examples": mismatches}


def _verify_responsibility_locators(outdir: Path, label: str) -> dict[str, Any]:
    counts = {"rows": 0, "observation_linked": 0, "capture_digest_verified": 0, "capture_digest_mismatch": 0,
              "capture_absent": 0, "encyclopedia_rows": 0, "wiki_file_found_with_revision": 0,
              "wiki_file_not_found": 0, "capture_text_rows": 0, "capture_text_file_present": 0}
    wiki_dir = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\wikimedia")
    digests: dict[str, str | None] = {}
    for page in sorted(outdir.glob(f"{label}_*.json.gz")):
        payload = _gz_json(page) or {}
        for row in payload.get("rows") or []:
            counts["rows"] += 1
            locator = row.get("locator") or {}
            if locator.get("observation_payload_sha256"):
                counts["observation_linked"] += 1
                path = locator.get("observation_capture_path") or locator.get("capture_path")
                if path not in digests:
                    digests[path] = sha256_file(Path(path)) if path else None
                if digests[path] is None:
                    counts["capture_absent"] += 1
                elif digests[path] == locator["observation_payload_sha256"]:
                    counts["capture_digest_verified"] += 1
                else:
                    counts["capture_digest_mismatch"] += 1
            if row.get("source_kind") == "ENCYCLOPEDIA_REVISION":
                counts["encyclopedia_rows"] += 1
                file = wiki_dir / str(row.get("wiki_file"))
                if file.is_file() and str(row.get("revision_id")) in file.read_text(encoding="utf-8", errors="replace"):
                    counts["wiki_file_found_with_revision"] += 1
                else:
                    counts["wiki_file_not_found"] += 1
            if row.get("source_kind") == "OFFICIAL_CAPTURE_TEXT":
                counts["capture_text_rows"] += 1
                if row.get("capture_path") and Path(row["capture_path"]).is_file():
                    counts["capture_text_file_present"] += 1
    return {**counts, "wiki_file_directory_basis": (
        "wiki_file is stored as a bare file name; it was looked up in the Wikimedia raw directory the career rows' "
        "raw_file paths name. Offsets into rendered or plain text were not re-derived; only file presence, the "
        "revision id and capture digests were checked.")}


def _malformed_fixtures(work: Path) -> dict[str, Path]:
    """Owned synthetic releases for the refusal cases; no delivered byte is copied or changed."""

    markers = ("CREATE TABLE canonical_program (program_id TEXT, display_names TEXT, in_football_population INTEGER);"
               "CREATE TABLE program_season_membership (program_id TEXT, season INTEGER);"
               "CREATE TABLE core_role_cell (program_id TEXT);"
               "CREATE TABLE staff_observation (observation_id TEXT, person TEXT);"
               "CREATE TABLE release_identity (key TEXT, value TEXT);")
    career = ("CREATE TABLE career_episode (career_episode_id INTEGER, span_id TEXT, pageid TEXT, page_title TEXT, "
              "wikidata_qid TEXT, wikimedia_revision TEXT, episode_index INTEGER, person_display_name TEXT, "
              "employer_raw TEXT, employer_resolution_state TEXT, employer_program_id TEXT, source_title TEXT, "
              "role_codes TEXT, start_year INTEGER, end_year INTEGER, ongoing INTEGER, source_year_text TEXT, "
              "evidence_class TEXT, state TEXT, flags TEXT, joined INTEGER, pit_admitted INTEGER);"
              "CREATE TABLE responsibility_assertion (responsibility_id INTEGER, person TEXT, program_id TEXT, "
              "season INTEGER, source_title TEXT, evidence_code TEXT, disposition TEXT, "
              "inferred_from_role_title INTEGER, pit_admitted INTEGER);")
    fixtures = {
        "unregistered_version": markers + career
        + "INSERT INTO release_identity VALUES ('release_version', 'BAS-FUTURE-NATIONAL-RELEASE-v99');",
        "undeclared_version": markers + career + "INSERT INTO release_identity VALUES ('release_id', 'X');",
        "declared_successor_absent": markers + career
        + "INSERT INTO release_identity VALUES ('release_version', "
          "'BAS-CYCLE37-CORRECTED-NATIONAL-RELEASE-v37.2-STAFF-REPARSE');"
          "CREATE TABLE release_lineage (key TEXT, value TEXT);"
          "INSERT INTO release_lineage VALUES ('successor_release_version', "
          "'BAS-CYCLE37-CORRECTED-NATIONAL-RELEASE-v37.2-STAFF-REPARSE');"
          "INSERT INTO release_lineage VALUES ('successor_table::career_episode_successor::ledger_sha256', 'a');"
          "INSERT INTO release_lineage VALUES ('successor_table::career_predecessor_disposition::ledger_sha256', 'b');",
        "unknown_schema": "CREATE TABLE something_else (x TEXT);",
    }
    paths = {}
    for name, script in fixtures.items():
        path = work / f"{name}.sqlite"
        conn = sqlite3.connect(path)
        conn.executescript(script)
        conn.commit()
        conn.close()
        paths[name] = path
    return paths


def lane_installed_consumer_c01(run: LaneRun) -> None:
    db_before = sha256_file(DELIVERED_DB)
    installed = _build_and_install(run)
    if installed is None:
        return
    run.extra["installed"] = {key: str(value) for key, value in installed.items()}
    run.extra["wheel_sha256"] = sha256_file(installed["wheel"])
    shutil.copy2(installed["wheel"], run.run_dir / installed["wheel"].name)
    origin_probe = ("import importlib, json, sys\n"
                    "rows = {}\n"
                    "for name in sys.argv[1:]:\n"
                    "    rows[name] = importlib.import_module(name).__file__\n"
                    "rows['cfb_intelligence_contracts'] = importlib.import_module('cfb_intelligence_contracts').__file__\n"
                    "print(json.dumps({'origins': rows, 'sys_path': sys.path}))\n")
    record = run.run("installed_module_origins", [installed["python"], "-B", "-c", origin_probe, *BOUND_MODULES],
                     cwd=installed["stage"], env=_installed_env(run))
    origins = (_payload(record).get("origins") or {})
    site = str(installed["venv"] / "Lib" / "site-packages").lower()
    outside = {name: path for name, path in origins.items() if not str(path).lower().startswith(site)}
    run.extra["installed_origins"] = {"origins": origins, "outside_site_packages": outside}
    if outside or len(origins) != len(BOUND_MODULES) + 1:
        run.problems.append(f"installed modules resolved outside site-packages: {outside}")
    equivalence = run.extra["installed_source_equivalence"] = _equivalence(installed)
    if equivalence["different"] or equivalence["worktree_on_any_pth"] or equivalence["python_modules_not_packaged"] \
            or not equivalence["installed_files"]:
        run.problems.append("the installed package differs from the committed source, omits a module or points "
                            "at the worktree")

    outdir = run.run_dir / "cli"
    outdir.mkdir()
    plan: list[tuple[str, list[Any], int]] = [
        ("schema", ["--schema"], 0),
        # The manager's sixteen Attempt 2 consumer cases, exact.
        ("mgr_01_season_1963", ["--season", "1963"], 0),
        ("mgr_02_season_1978_fcs", ["--season", "1978", "--division", "FCS"], 0),
        ("mgr_03_season_1998_fbs", ["--season", "1998", "--division", "FBS"], 0),
        ("mgr_04_season_2026_fcs", ["--season", "2026", "--division", "FCS"], 0),
        ("mgr_05_season_2026_fbs", ["--season", "2026", "--division", "FBS"], 0),
        ("mgr_06_ohio_2026", ["--team", "Ohio", "--season", "2026"], 0),
        ("mgr_07_ohio_state_2026", ["--team", "Ohio State", "--season", "2026"], 0),
        ("mgr_08_montana_2026", ["--team", "Montana", "--season", "2026"], 0),
        ("mgr_09_tamu_2026", ["--team", "Texas A&M", "--season", "2026"], 0),
        ("mgr_10_nonexistent_team", ["--team", "MANAGER-NONEXISTENT", "--season", "2026"], 0),
        ("mgr_11_season_1800", ["--season", "1800"], 0),
        ("mgr_12_idaho_seasons", ["--team", "Idaho", "--seasons-for-team"], 0),
        ("mgr_13_person_paul_brown", ["--person", "Paul Brown"], 0),
        ("mgr_14_person_mike_elko", ["--person", "Mike Elko"], 0),
        ("mgr_15_scheme_montana_2026", ["--scheme", "--team", "Montana", "--season", "2026"], 0),
        ("mgr_16_responsibility_ohio_state_2026", ["--responsibility", "--team", "Ohio State", "--season", "2026"], 0),
        # MF37A02-04: the corrected career, role, employer, interval and responsibility rows.
        ("bill_anderson_corrected", ["--person", BILL], 0),
        ("bill_anderson_legacy_audit", ["--person", BILL, "--legacy-audit"], 0),
        ("bill_anderson_display_name", ["--person", "Bill Anderson"], 0),
        ("career_current_tamu_2026", ["--career", "--team", "Texas A&M", "--season", "2026", "--all"], 0),
        ("career_historical_fcs_1985", ["--career", "--season", "1985", "--division", "FCS", "--all"], 0),
        ("career_fbs_2010_offensive_coordinators", ["--career", "--season", "2010", "--division", "FBS", "--role",
                                                    "offensive_coordinator", "--all"], 0),
        ("career_head_coaches_coaching_family", ["--career", "--role", "head_coach", "--family", "COACHING", "--all"], 0),
        ("career_one_identity", ["--career", "--pageid", "17440905", "--all"], 0),
        ("responsibility_encyclopedia", ["--responsibility", "--source-kind", "ENCYCLOPEDIA_REVISION", "--all"], 0),
        ("responsibility_person", ["--responsibility", "--person", "Maurice Crum Jr."], 0),
        ("scheme_tamu", ["--scheme", "--team", "Texas A&M"], 0),
        ("coverage", ["--coverage"], 0),
        ("provenance", ["--provenance"], 0),
        ("unresolved", ["--unresolved"], 0),
        # Refusals for their intended causes.
        ("refuse_invalid_limit", ["--career", "--limit", "0"], 1),
        ("refuse_legacy_on_team_staff", ["--team", "Texas A&M", "--season", "2026", "--legacy-audit"], 1),
        ("refuse_non_integer_season", ["--career", "--season", "CURRENT"], 1),
    ]
    results: dict[str, Any] = {}
    for name, args, expected in plan:
        record = _cli(run, installed, name, args, expect_exit=expected, save=outdir / f"{name}.json.gz")
        results[name] = {"exit": record.get("exit_code"), "expected_exit": expected,
                         "result": record["result_against_expectation"], "args": [str(a) for a in args]}
    # Older releases stay readable, from their own tables.
    for name, database, args, expected in (
        ("v361_person", V361_DB, ["--person", BILL], 0),
        ("v361_responsibility", V361_DB, ["--responsibility", "--limit", "5"], 0),
        ("v371_person", V371_DB, ["--person", BILL], 0),
        ("v361_division_refused", V361_DB, ["--career", "--division", "FBS"], 1),
    ):
        record = _cli(run, installed, name, args, database=database, expect_exit=expected,
                      save=outdir / f"{name}.json.gz")
        results[name] = {"exit": record.get("exit_code"), "expected_exit": expected,
                         "result": record["result_against_expectation"], "database": str(database),
                         "database_sha256": sha256_file(database)}
    fixtures = _malformed_fixtures(run.fresh("malformed_fixtures"))
    for name, code in (("unregistered_version", "REFUSED_RELEASE_VERSION_NOT_SUPPORTED"),
                       ("undeclared_version", "REFUSED_RELEASE_VERSION_NOT_DECLARED"),
                       ("declared_successor_absent", "REFUSED_REQUIRED_TABLES_ABSENT"),
                       ("unknown_schema", "matches no schema")):
        record = _cli(run, installed, f"fixture_{name}", ["--person", BILL], database=fixtures[name], expect_exit=1)
        text = Path(record["log_path"]).read_text(encoding="utf-8", errors="replace")
        results[f"fixture_{name}"] = {"exit": record.get("exit_code"), "expected_code": code,
                                      "refused_for_the_intended_cause": code in text}
        if code not in text:
            run.problems.append(f"fixture {name} was not refused with {code}")
    run.extra["cli_results"] = results
    failed = [name for name, row in results.items() if row.get("result") == FAIL]
    if failed:
        run.problems.append(f"installed CLI cases not as expected: {failed}")

    # The manager's counterexample, read from the installed CLI's own output.
    bill = _gz_json(outdir / "bill_anderson_corrected.json.gz") or {}
    legacy = _gz_json(outdir / "bill_anderson_legacy_audit.json.gz") or {}
    stamford = [row for row in bill.get("career_episodes", []) if row.get("employer_display") == "Stamford HS (TX)"]
    run.extra["bill_anderson"] = {
        "mode": (bill.get("release_dispatch") or {}).get("mode"),
        "selected_table": (bill.get("release_dispatch") or {}).get("selected_table"),
        "corrected_rows": len(bill.get("career_episodes", [])),
        "stamford_rows": [{k: row.get(k) for k in ("episode_id", "employer_display", "start", "end")}
                          | {"roles": row["corrected"]["roles"],
                             "dispositions": [d["state"] for d in row["predecessor_dispositions"]]}
                          for row in stamford],
        "any_row_with_title_TX": any(row.get("source_title") == "TX" for row in bill.get("career_episodes", [])),
        "legacy_mode": (legacy.get("release_dispatch") or {}).get("mode"),
        "legacy_rows_with_title_TX": [row.get("span_id") for row in legacy.get("career_episodes", [])
                                      if row.get("source_title") == "TX"],
    }
    if run.extra["bill_anderson"]["any_row_with_title_TX"] or len(stamford) != 3:
        run.problems.append("the installed CLI does not return Bill Anderson's corrected Stamford HS (TX) rows")

    # Full pagination of every selected table against the independent SQL oracle.
    oracle = _oracle(DELIVERED_DB)
    pages = run.run_dir / "pages"
    pages.mkdir()
    ids = oracle["ids"]
    run.extra["pagination"] = {
        "career_corrected": _paginate(run, installed, "career_corrected", ["--career"], "episode_id", 10000,
                                      ids["career_successor"], pages),
        "career_legacy": _paginate(run, installed, "career_legacy", ["--career", "--legacy-audit"],
                                   "career_episode_id", 10000, ids["career_predecessor"], pages),
        "responsibility_corrected": _paginate(run, installed, "responsibility_corrected", ["--responsibility"],
                                              "successor_key", 1000, ids["responsibility_successor"], pages),
        "responsibility_legacy": _paginate(run, installed, "responsibility_legacy",
                                           ["--responsibility", "--legacy-audit"], "responsibility_id", 1000,
                                           ids["responsibility_predecessor"], pages),
        "scheme": _paginate(run, installed, "scheme", ["--scheme"], "scheme_assertion_id", 5000, ids["scheme"], pages),
    }
    # Filtered answers against an independent Python filter over the same rows.
    filtered = {}
    for name, flt in (("career_current_tamu_2026", {"team": "Texas A&M", "season": 2026}),
                      ("career_historical_fcs_1985", {"season": 1985, "division": "fcs"}),
                      ("career_fbs_2010_offensive_coordinators", {"season": 2010, "division": "fbs",
                                                                  "role": "offensive_coordinator"}),
                      ("career_head_coaches_coaching_family", {"role": "head_coach", "family": "COACHING"}),
                      ("bill_anderson_corrected", {"person": BILL})):
        payload = _gz_json(outdir / f"{name}.json.gz") or {}
        rows = payload.get("rows") or payload.get("career_episodes") or []
        cli_ids = {str(row["episode_id"]) for row in rows}
        expected = _python_filter(oracle["career_rows"], oracle["programs"], **flt)
        filtered[name] = {"cli": len(cli_ids), "oracle": len(expected), "equal": cli_ids == expected}
        if cli_ids != expected:
            run.problems.append(f"filtered career answer {name} differs from the independent filter")
    run.extra["filtered_oracle"] = filtered
    run.extra["career_locators"] = _verify_career_locators(pages, "career_corrected")
    run.extra["responsibility_locators"] = _verify_responsibility_locators(pages, "responsibility_corrected")
    locators = run.extra["career_locators"]
    if locators["rows"] != len(ids["career_successor"]) or locators["raw_file_digest_mismatch"] or \
            locators["span_mismatch"] or locators["wikitext_not_found"] or locators["raw_file_absent"]:
        run.problems.append(f"career locators do not all resolve to their raw bytes: {locators}")

    # Installed admission and PIT refusals, and the composition with the released C01 wheel.
    work = run.fresh("installed_probes")
    probe_copy = work / "attempt03_admission_probe.py"
    shutil.copy2(WORKTREE / "tools" / "cycle37" / "attempt03_admission_probe.py", probe_copy)
    admission = run.run_dir / "ADMISSION_INSTALLED_PROBE.json"
    run.run("attempt03_admission_probe_installed", [installed["python"], "-B", probe_copy, "--mode", "installed",
                                                    "--scratch", work / "scratch", "--out", admission],
            cwd=work, env=_installed_env(run))
    run.extra["attempt03_admission_probe_installed"] = _admission_receipt(run, admission)
    if run.extra["attempt03_admission_probe_installed"]["resolved_inside_a_git_checkout"] is not False:
        run.problems.append("the installed admission probe did not resolve outside every checkout")
    for script in ("probe_admission.py", "probe_pit.py"):
        copy, replay = _replay(run, script)
        record = run.run(f"manager_{Path(script).stem}_replay_installed", [installed["python"], "-B", copy],
                         cwd=copy.parent, env=_installed_env(run),
                         note="Manager's saved probe, byte-identical, with no import root: site-packages only.")
        verdict = {**replay, **_judge_manager_probe(script, record)}
        module = str(verdict.get("module") or "").lower()
        verdict["module_from_site_packages"] = module.startswith(site)
        run.extra[f"manager_{Path(script).stem}_installed"] = verdict
        if not verdict["all_refused"] or not verdict["module_from_site_packages"]:
            run.problems.append(f"{script}: a counterexample is admitted, or not from the installed wheel")
    composition_copy = work / "r37_13_c01_composition.py"
    shutil.copy2(WORKTREE / "tools" / "cycle37" / "r37_13_c01_composition.py", composition_copy)
    composition = run.run_dir / "C01_COMPOSITION_INSTALLED.json"
    run.run("compose_installed_bas_with_released_c01", [installed["python"], "-B", composition_copy, "--wheel",
                                                         C01_WHEEL, "--wheel-sha256", C01_WHEEL_SHA256,
                                                         "--wheel-interpreter", installed["python"], "--out",
                                                         composition],
            cwd=work, env=_installed_env(run),
            note="The composition tool copied outside every checkout, so its BAS imports resolve to the wheel.")
    receipt = json.loads(composition.read_text(encoding="utf-8")) if composition.is_file() else {}
    run.extra["c01_composition"] = {"receipt": str(composition), "sha256": sha256_file(composition),
                                    "all_fixtures_honoured": receipt.get("all_fixtures_honoured"),
                                    "all_consumer_checks_hold": receipt.get("all_consumer_checks_hold"),
                                    "f10_separation_holds": receipt.get("f10_separation_holds"),
                                    "positives": receipt.get("positives"),
                                    "positives_accepted_by_both": receipt.get("positives_accepted_by_both"),
                                    "negatives": receipt.get("negatives"),
                                    "negatives_refused": receipt.get("negatives_refused"),
                                    "wheel_version": (receipt.get("vector") or {}).get("wheel_version")}
    if not (receipt.get("all_fixtures_honoured") and receipt.get("all_consumer_checks_hold")
            and receipt.get("f10_separation_holds")):
        run.problems.append("the installed BAS adapter does not compose with the released C01 wheel")
    c01_copy, c01_replay = _replay(run, "c01_independent.py", adapt={
        r"C:\BatteredAggieSyndrome.validation\c37r-171601\lane_wheel_cli\wheel_venv\Lib\site-packages":
            str(installed["venv"] / "Lib" / "site-packages"),
        r"C:\BatteredAggieSyndrome.packaging\c37r-171601\c01_release\cfbintelligencecontracts-0.1.2-py3-none-any.whl":
            str(C01_WHEEL),
    })
    record = run.run("manager_c01_independent_replay_installed", [installed["python"], "-B", c01_copy],
                     cwd=c01_copy.parent, env=_installed_env(run),
                     note="Manager's saved C01 probe; only its two absolute path literals are adapted.")
    output = _stdout_json(record) or {}
    run.extra["manager_c01_independent"] = {**c01_replay, "exit": record.get("exit_code"),
                                            "installed_files": output.get("installed_files"),
                                            "mismatches": output.get("mismatches"),
                                            "results": {k: ("refused" if v.get("refused") else "projected")
                                                        for k, v in (output.get("results") or {}).items()}}
    run.extra["delivered_database_unchanged"] = {"before": db_before, "after": sha256_file(DELIVERED_DB),
                                                 "expected": DELIVERED_DB_SHA256}
    if not (db_before == sha256_file(DELIVERED_DB) == DELIVERED_DB_SHA256):
        run.problems.append("the delivered database digest changed or is not the issued one")


# ---- mounted, unmounted, platform and packet lanes ------------------------------------------------------


def _log_identities(path: Path) -> dict[str, Any]:
    from aggie_analytics.validation import lane_harness

    parsed = lane_harness.parse_unittest(path.read_text(encoding="utf-8", errors="replace"))
    return {"tests_run": parsed.get("tests_run"),
            "failed_or_errored": sorted(parsed.get("failed_or_errored_identities") or []),
            "import_errors": sorted(parsed.get("import_error_identities") or []),
            "skipped": sorted(row["identity"] for row in parsed.get("skipped") or [])}


def _failure_causes(log: Path, identities: Iterable[str]) -> dict[str, str]:
    """The final exception line of each identity's traceback block, and whether the guard caused it.

    unittest heads a block ``ERROR: test_method (module.Class.test_method)`` for a method and
    ``ERROR: setUpClass (module.Class)`` for a class fixture; the census names them ``module.Class.test_method``
    and ``setUpClass (module.Class)``.
    """

    text = log.read_text(encoding="utf-8", errors="replace")
    blocks: dict[str, str] = {}
    for block in re.split(r"\n={50,}\n", text):
        head = block.strip().splitlines()[0] if block.strip() else ""
        match = re.match(r"^(?:FAIL|ERROR): (\S+) \(([^)]+)\)", head)
        if match:
            name, qualified = match.groups()
            key = qualified if qualified.endswith(f".{name}") else f"{name} ({qualified})"
            blocks.setdefault(key, block.split("\n" + "-" * 70, 1)[-1])
    causes = {}
    for identity in identities:
        block = blocks.get(identity)
        if block is None:
            causes[identity] = "NO_TRACEBACK_BLOCK_FOUND"
        elif "CanonicalWriteRefused" in block:
            causes[identity] = "GUARD_REFUSED: " + next((line for line in block.splitlines()
                                                         if "CanonicalWriteRefused:" in line), "")[:240]
        elif "NetworkRefused" in block:
            causes[identity] = "GUARD_REFUSED_NETWORK: " + next((line for line in block.splitlines()
                                                                 if "NetworkRefused:" in line), "")[:240]
        else:
            last = [line for line in block.splitlines()
                    if re.match(r"^[A-Za-z_][\w.]*(Error|Exception|Refused|Violation|Failure|Exit)\b", line)]
            causes[identity] = last[-1][:240] if last else block.strip().splitlines()[-1][:240]
    return causes


def lane_full_final_mounted(run: LaneRun) -> None:
    record = run.census("full_suite_mounted", start_dir=".", timeout=4 * 3600,
                        env=run.env(extra={"AGGIE_ANALYTICS_DATA_ROOT": str(DATA_ROOT)}),
                        note="Whole suite, canonical data root mounted read-only under the guard.")
    log = Path(record["log_path"])
    baseline_log = ATTEMPT2_ROOT / "logs" / "full-final-mounted" / "full-final-mounted__full_suite_final.log"
    final = _log_identities(log)
    comparison: dict[str, Any] = {"baseline_log": str(baseline_log), "baseline_sha256": sha256_file(baseline_log)}
    if baseline_log.is_file():
        base = _log_identities(baseline_log)
        persisting = sorted(set(final["failed_or_errored"]) & set(base["failed_or_errored"]))
        new = sorted(set(final["failed_or_errored"]) - set(base["failed_or_errored"]))
        fixed = sorted(set(base["failed_or_errored"]) - set(final["failed_or_errored"]))
        final_causes = _failure_causes(log, persisting)
        base_causes = _failure_causes(baseline_log, persisting)
        comparison.update({"baseline_tests_run": base["tests_run"], "final_tests_run": final["tests_run"],
                           "baseline_skipped": base["skipped"], "final_skipped": final["skipped"],
                           "persisting": persisting, "new_in_attempt3": new, "no_longer_failing": fixed,
                           "new_failure_causes": _failure_causes(log, new),
                           "persisting_failure_causes": final_causes,
                           "persisting_same_cause": sorted(i for i in persisting if final_causes[i] == base_causes[i]),
                           "persisting_changed_cause": {i: {"attempt2": base_causes[i], "attempt3": final_causes[i]}
                                                        for i in persisting if final_causes[i] != base_causes[i]}})
    comparison["final_failed_or_errored"] = final["failed_or_errored"]
    run.extra["baseline_comparison"] = comparison


def lane_strict_mounted(run: LaneRun) -> None:
    record = run.run("validate_repository_strict", [run.python, "-B", "tools/validate_repository.py", "--repo-root",
                                                    ".", "--strict"],
                     env=run.env(extra={"AGGIE_ANALYTICS_DATA_ROOT": str(DATA_ROOT)}), timeout=4 * 3600,
                     note="The repository validator against the canonical data root, under the guard.")
    baseline = ATTEMPT2_ROOT / "logs" / "strict-mounted" / "strict-mounted__validate_repository_strict.log"
    final = _strict_findings(Path(record["log_path"]))
    base = _strict_findings(baseline) if baseline.is_file() else []
    # Each finding line is its own identity: gate, artifact and the exact disagreement.
    run.extra["strict_findings"] = [{"identity": line, "gate": line.split(":", 1)[0]} for line in final]
    run.extra["baseline_comparison"] = {
        "baseline_log": str(baseline), "baseline_sha256": sha256_file(baseline),
        "baseline_findings": len(base), "final_findings": len(final),
        "persisting": sorted(set(final) & set(base)), "new_in_attempt3": sorted(set(final) - set(base)),
        "no_longer_reported": sorted(set(base) - set(final))}
    declared = re.search(r"^FAIL: (\d+) finding", Path(record["log_path"]).read_text(encoding="utf-8", errors="replace"),
                         re.M)
    if declared and int(declared.group(1)) != len(final):
        run.problems.append(f"the validator declared {declared.group(1)} findings but {len(final)} were parsed")


def _strict_findings(log: Path) -> list[str]:
    """The ``- <gate>: <artifact>: <disagreement>`` lines of the first ``FAIL: N finding(s)`` block."""

    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if re.match(r"^FAIL: \d+ finding", line):
            block = []
            for row in lines[index + 1:]:
                if not row.startswith("- "):
                    break
                block.append(row[2:])
            return block
    return []


def lane_true_unmounted(run: LaneRun) -> None:
    empty = run.fresh("empty_data_root")
    literal = str(DATA_ROOT)
    carriers = []
    for path in sorted((WORKTREE / "src").rglob("*.py")):
        count = path.read_text(encoding="utf-8", errors="replace").count(literal)
        if count:
            carriers.append({"path": str(path.relative_to(WORKTREE)), "occurrences": count})
    run.extra["private_root_literal_census"] = {"literal": literal, "files": len(carriers),
                                                "occurrences": sum(row["occurrences"] for row in carriers),
                                                "carriers": carriers}
    run.census("regression_suites_unmounted", REGRESSION_SUITES,
               env=run.env(extra={"AGGIE_ANALYTICS_DATA_ROOT": str(empty)}),
               note="Data root pointed at an empty owned directory; the canonical root stays write-guarded.")


def _after_receipt_at_head(folder: Path, pattern: str, head: str) -> Path | None:
    """An AFTER receipt already taken against this exact head, so a lane rerun never spends requests twice."""

    for path in sorted(folder.glob(pattern), reverse=True):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if (document.get("subject") or {}).get("head") == head:
            return path
    return None


def lane_platform_carry(run: LaneRun) -> None:
    run.exceptions.append("The platform reader and the two granted comments call gh and Jira and need the network, "
                          "so those commands run without the lane guard; they write only create-only files under "
                          "the attempt root, and the snapshots measure the rest. The private Jira successor is "
                          "offline and runs under the guard.")
    platform_env = run.env(guarded=False, network=True, pythonpath=None)
    tool = "tools/cycle37/attempt03_platform.py"
    after = run.out_root / "evidence" / "platform" / "AFTER"
    head = run.binding["head"]
    reads: dict[str, Any] = {}
    # The reader loads its own Jira credential from the project .env; it is not passed through this environment.
    for mode, pattern, extra in (("github-read", "github/GITHUB_READ_SUMMARY_*.json", []),
                                 ("all22-read", "all22/ALL22_READ_SUMMARY_*.json",
                                  ["--remote-manifest", ALL22_REMOTE_MANIFEST]),
                                 ("jira-read", "jira/JIRA_READ_SUMMARY_*.json", ["--full-export"])):
        existing = _after_receipt_at_head(after, pattern, head)
        if existing:
            reads[mode] = {"state": "REUSED_RECEIPT_AT_THIS_HEAD", "summary": str(existing),
                           "sha256": sha256_file(existing)}
        elif run.rehearsal:
            reads[mode] = {"state": "NOT_RUN_IN_REHEARSAL", "reason": "no request budget is spent on a rehearsal"}
        else:
            run.run(f"platform_{mode}_after", [run.python, "-B", tool, mode, "--out-root", run.out_root, "--phase",
                                               "AFTER", *extra], env=platform_env, timeout=1800)
            made = _after_receipt_at_head(after, pattern, head)
            reads[mode] = {"state": "READ_AT_THIS_HEAD" if made else "NO_RECEIPT_AT_THIS_HEAD",
                           "summary": str(made) if made else None, "sha256": sha256_file(made) if made else None}
            if not made:
                run.problems.append(f"{mode} left no AFTER receipt bound to head {head}")
    run.extra["platform_reads"] = reads
    # The selected sync contract, rerun against the AFTER export in a private copy (never the committed pack).
    exports = sorted((after / "jira").glob("BAT_CANONICAL_EXPORT_2*.csv"))
    if run.rehearsal and not exports:
        exports = sorted((EVIDENCE_ROOT / "evidence" / "platform" / "DURING" / "jira")
                         .glob("BAT_CANONICAL_EXPORT_CORRECTED_*.csv"))
    if not exports:
        run.problems.append("no AFTER canonical export exists for the private Jira successor")
    else:
        export = exports[-1]
        digest = sha256_file(export)
        done = [path for path in sorted((after / "jira").glob("JIRA_PRIVATE_SUCCESSOR_*.json"))
                if (json.loads(path.read_text(encoding="utf-8")).get("source_export") or {}).get("sha256") == digest]
        if done:
            run.extra["jira_private_successor"] = {"state": "REUSED_RECEIPT_FOR_THIS_EXPORT", "receipt": str(done[-1])}
        else:
            run.run("jira_private_successor_after", [run.python, "-B", tool, "jira-successor", "--out-root",
                                                     run.out_root, "--phase", "AFTER", "--export", export, "--apply"],
                    env=run.env(pythonpath=None), timeout=1800,
                    note="Dry run, apply, strict and audit validators and a second dry run, in a private copy.")
            done = [path for path in sorted((after / "jira").glob("JIRA_PRIVATE_SUCCESSOR_*.json"))
                    if (json.loads(path.read_text(encoding="utf-8")).get("source_export") or {}).get("sha256") == digest]
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
    # The two granted handoff comments, each with a deterministic marker, a duplicate check and a readback.
    comments: dict[str, Any] = {}
    for issue, marker in AFTER_COMMENTS:
        body = after / "comment_bodies" / f"{marker}.txt"
        posted = [path for path in sorted((after / "jira").glob(f"JIRA_COMMENT_{issue}_*.json"))
                  if json.loads(path.read_text(encoding="utf-8")).get("marker") == marker
                  and json.loads(path.read_text(encoding="utf-8")).get("result") == "SUCCEEDED"]
        if posted:
            comments[issue] = {"state": "POSTED_AND_READ_BACK", "receipt": str(posted[-1]), "marker": marker}
            continue
        if not body.is_file() or marker not in body.read_text(encoding="utf-8"):
            run.problems.append(f"the AFTER comment body for {issue} is missing or lacks its marker {marker}")
            continue
        if run.rehearsal:
            comments[issue] = {"state": "NOT_POSTED_IN_REHEARSAL", "body": str(body), "marker": marker}
            continue
        run.run(f"jira_comment_after_{issue}", [run.python, "-B", tool, "jira-comment", "--out-root", run.out_root,
                                                "--phase", "AFTER", "--issue", issue, "--marker", marker,
                                                "--body-file", body], env=platform_env, timeout=600)
        posted = [path for path in sorted((after / "jira").glob(f"JIRA_COMMENT_{issue}_*.json"))
                  if json.loads(path.read_text(encoding="utf-8")).get("marker") == marker
                  and json.loads(path.read_text(encoding="utf-8")).get("result") == "SUCCEEDED"]
        comments[issue] = {"state": "POSTED_AND_READ_BACK" if posted else "NOT_CONFIRMED",
                           "receipt": str(posted[-1]) if posted else None, "marker": marker}
        if not posted:
            run.problems.append(f"the AFTER comment on {issue} was not confirmed by readback")
    run.extra["after_comments"] = comments
    ledger = run.run("platform_ledger_totals", [run.python, "-B", tool, "ledger",
                                                "--out-root", run.out_root, "--phase", "AFTER"],
                     env=run.env(pythonpath=None))
    totals = _stdout_json(ledger) or {}
    run.extra["request_totals"] = totals
    for lane, row in totals.items():
        if isinstance(row, dict) and row.get("requests", 0) > row.get("ceiling", 0):
            run.problems.append(f"{lane} exceeded its ceiling: {row}")
    run.run("carryforward_accounting", [run.python, "-B", "tools/cycle37/attempt03_outputs.py", "check",
                                        "--contract", run.contract_path, "--out-root", run.out_root],
            env=run.env(), note="Every original criterion, obligation, lane and finding accounted, by identity.")


def lane_final_packet(run: LaneRun) -> None:
    run.run("packet_consistency", [run.python, "-B", "tools/cycle37/attempt03_outputs.py", "check",
                                   "--contract", run.contract_path, "--out-root", run.out_root, "--final-packet"],
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
    "CLAIM_SUCCESSOR": lane_claim_successor,
    "FULL_FINAL_MOUNTED": lane_full_final_mounted,
    "STRICT_MOUNTED": lane_strict_mounted,
    "TRUE_UNMOUNTED": lane_true_unmounted,
    "PLATFORM_CARRY": lane_platform_carry,
    "FINAL_PACKET": lane_final_packet,
}


# ------------------------------------------------------------------ result


def counts(commands: list[dict[str, Any]]) -> dict[str, int]:
    """The lane's test counts, from the census records of its TEST commands."""

    totals = {"tests": 0, "failures": 0, "errors": 0, "import_errors": 0, "failed_subtests": 0, "skipped": 0}
    for record in commands:
        summary_path = record.get("census_summary")
        if not summary_path or not Path(summary_path).is_file():
            continue
        summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
        framework = summary.get("framework_counts") or {}
        records = [json.loads(line) for line in Path(record["census_records"]).read_text(encoding="utf-8").splitlines()
                   if line.strip()]
        totals["tests"] += int(summary.get("tests_run") or 0)
        totals["failures"] += int(framework.get("failures") or 0)
        totals["errors"] += int(framework.get("errors") or 0)
        totals["import_errors"] += sum(1 for row in records if row.get("is_import_error"))
        totals["failed_subtests"] += sum(1 for row in records if row.get("kind") in ("SUBTEST_FAIL", "SUBTEST_ERROR"))
        totals["skipped"] += sum(1 for row in records if row.get("kind") == "SKIP" and not row.get("fixture"))
    return totals


def decide(run: LaneRun, kind: str) -> tuple[str, str]:
    reasons = list(run.problems)
    for record in run.commands:
        outcome = record.get("result_against_expectation")
        if outcome != PASS:
            reasons.append(f"{record['lane']}: {outcome} ({record.get('state_reason')})")
    if not run.commands:
        reasons.append("the lane ran no command")
    if kind == "TEST" and not any(record.get("kind") == "TEST" for record in run.commands):
        reasons.append("a TEST lane ran no test command")
    if any(record.get("result") == BLOCKED for record in run.commands) and not reasons:
        reasons.append("a command did not complete")
    return (PASS, "every command and check held") if not reasons else (FAIL, "; ".join(reasons)[:4000])


def main(argv: list[str] | None = None) -> int:
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
    print(f"Cycle #37 \u2014 Attempt #3 \u2014 lane {args.lane} run {run.stamp}"
          + (" (REHEARSAL, NOT EVIDENCE)" if args.rehearsal else ""))
    contract, contract_problems = load_contract(run.contract_path, args.lane, issued_root)
    run.contract = contract
    run.binding = bind_source()
    interpreter = bind_interpreter(run.python)
    blocked = list(contract_problems)
    if run.binding["branch"] != BRANCH:
        blocked.append(f"branch is {run.binding['branch']}, not {BRANCH}")
    if not run.binding["descends_from_base"]:
        blocked.append(f"head {run.binding['head']} does not descend from the issued base {BASE_SHA}")
    if not run.binding["clean"] and not args.rehearsal:
        blocked.append("the worktree is dirty; lanes run only at a committed subject")
    before = scope_before()
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
        result, reason = decide(run, (contract.get("_lane") or {}).get("kind", "CHECK"))
    scope = scope_after(before)
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
        "label": f"Cycle #37 \u2014 Attempt #3 \u2014 lane {args.lane} {result}"
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
            "guarded_roots": [str(root) for root in GUARDED_ROOTS], "writable_roots": [str(out_root),
                                                                                        str(VALIDATION_ROOT),
                                                                                        str(PACKAGING_ROOT)],
            "network": "DENY_NON_LOOPBACK for guarded children", "credential_variables_removed": sorted(credential_scrub()),
            "temp_root": str(run.tmp), "temp_spelling_given_to_children": run.tmp_spelling,
            "exceptions": run.exceptions, "guard_events": len(guard_events),
            "guard_blocked_events": [row for row in guard_events if row.get("event") == "BLOCKED"][:100],
            "measurement": scope},
        "counts": counts(run.commands),
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
