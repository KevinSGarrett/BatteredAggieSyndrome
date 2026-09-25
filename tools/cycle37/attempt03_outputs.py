r"""Cycle #37 — Attempt #3 — worker outputs, submission and accounting check (R37A03-07).

    attempt03_outputs.py build --contract C --out-root R [--headline H --writer-released]
    attempt03_outputs.py check --contract C --out-root R [--final-packet]

``build`` writes the declared worker outputs under the attempt root from what is actually there: the issued
contract, the lane receipts named in ``lanes/RUNS.jsonl``, the platform receipts and request ledger, the Cycle 29
census and successor, git, and two worker-authored evidence files it reads but never invents:
``evidence/INHERITED_FAILURE_CLASSIFICATION.json`` (every failing identity of a red lane, grouped by cause, with
the blocker kind, owner and next action) and ``evidence/NEW_FINDINGS_ATTEMPT3.json``. A classification is
refused unless it names exactly the failing identities of the lane's latest run.

``check`` re-reads those outputs and fails on any gap: an original obligation, criterion, lane, finding or
platform duty missing or renamed; a carryforward disposition or meaning changed; a request ceiling exceeded; a
red lane whose failures are not classified by exact identity. ``--final-packet`` also requires every worker lane
except FINAL_PACKET itself to have a receipt at the candidate head.

The default headline is IN_PROGRESS_LOCAL_WORK_REMAINS. A terminal headline must be asked for explicitly, with
``--writer-released``, and is refused while any unfinished item is local work. This tool never accepts anything:
manager and owner criteria stay pending, integration stays unauthorised.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

WORKTREE = Path(__file__).resolve().parents[2]
CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID, ATTEMPT_ID = 37, 3, "CYCLE-37", "ATTEMPT-03-20260924"
BASE_SHA = "8fcb5fb66867ef08a61de12bf2eff569b54ac253"
BRANCH = "codex/BAT-706-cycle37-rework"
ATTEMPT2_ROOT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempts\REWORK-20260922T171601Z")
MANAGER_A2 = Path(r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle37\attempt02\final-review-20260924143701Z")
SUCCESSOR = WORKTREE / "artifacts" / "scientific_integrity" / "cycle29_successor" / "CYCLE29_CLAIM_INVENTORY_SUCCESSOR.v1.json"
ORIGINAL_INVENTORY = WORKTREE / "artifacts" / "scientific_integrity" / "cycle29" / "CYCLE29_CLAIM_INVENTORY.json"
DB_SHA256 = "757d4b5f0649d60943c4594d6e0c22b7c930f5ef3acf9f675b4f93f328a7d331"
C01_SHA256 = "a57d4a58cb268e14f88ea7a66bf49131e89b7f930ea1acabc05c2dfeca689af3"
WORKER_LANES = ("START_CONTEXT", "WRITE_PROTECTION", "SOURCE_ADMISSION", "SOURCE_HARNESS", "SOURCE_REGRESSIONS",
                "INSTALLED_CONSUMER_C01", "CLAIM_SUCCESSOR", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED", "TRUE_UNMOUNTED",
                "PLATFORM_CARRY", "FINAL_PACKET")
RAW = "bound_raw_execution_and_consumer_output"
CENSUS = "complete_bound_census_and_raw_receipts"
BLOCKERS = {"LOCAL_CODE", "LOCAL_DATA_PROCESSING", "LOCAL_VALIDATION", "MISSING_SOURCE_FACT", "ACCESS", "RIGHTS",
            "BUDGET", "OWNER_DECISION", "INDEPENDENT_REVIEW", "RELEASE_AUTHORITY", "FUTURE_EVENT"}
HEADLINES = ("IN_PROGRESS_LOCAL_WORK_REMAINS", "BLOCKED_INCOMPLETE", "IMPLEMENTATION_SUBMITTED_NOT_ACCEPTED",
             "IMPLEMENTATION_COMPLETE_REVIEW_PENDING")

#: The lanes whose receipts carry each requirement's evidence.
REQUIREMENT_LANES = {
    "R37A03-01": ("WRITE_PROTECTION", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED", "TRUE_UNMOUNTED"),
    "R37A03-02": ("SOURCE_ADMISSION", "INSTALLED_CONSUMER_C01"),
    "R37A03-03": ("SOURCE_ADMISSION", "INSTALLED_CONSUMER_C01"),
    "R37A03-04": ("INSTALLED_CONSUMER_C01", "SOURCE_REGRESSIONS"),
    "R37A03-05": ("SOURCE_HARNESS", "FULL_FINAL_MOUNTED"),
    "R37A03-06": ("CLAIM_SUCCESSOR",),
    "R37A03-07": WORKER_LANES,
}
#: Attempt 2's 21 worker lanes: its receipt name and the Attempt 3 lanes that now carry the obligation.
ORIGINAL_LANES = {
    "START_BINDING": ("binding", ("START_CONTEXT",)),
    "PATH_NEGATIVES": ("paths", ("SOURCE_REGRESSIONS",)),
    "HARNESS_CONTROLS": ("harness", ("SOURCE_HARNESS",)),
    "SOURCE_FOCUSED": ("focused", ("SOURCE_REGRESSIONS",)),
    "STRICT_MOUNTED": ("strict-mounted", ("STRICT_MOUNTED",)),
    "FULL_BASELINE_MOUNTED": ("full-baseline-mounted", ()),
    "FULL_FINAL_MOUNTED": ("full-final-mounted", ("FULL_FINAL_MOUNTED",)),
    "TRUE_UNMOUNTED": ("true-unmounted", ("TRUE_UNMOUNTED",)),
    "HASHSEED0": ("hashseed-0", ()),
    "HASHSEED1": ("hashseed-1", ()),
    "WARNINGS_ERROR": ("warnings-error", ()),
    "FAMILY_B_COMPOSED": ("family-b", ()),
    "DELIVERED_DB_INDEPENDENT": ("delivered-db", ("INSTALLED_CONSUMER_C01",)),
    "BAS_WHEEL_CLI": ("wheel-cli", ("INSTALLED_CONSUMER_C01",)),
    "C01_RELEASE_COMPOSED": ("c01-release", ("INSTALLED_CONSUMER_C01",)),
    "C36_15_END_TO_END": ("c36-15", ()),
    "FLOAT_SUCCESSOR": ("float-successor", ()),
    "JIRA_PRIVATE_SYNC": ("jira-private", ("PLATFORM_CARRY",)),
    "PUBLIC_PACKAGE_PRIVACY": ("privacy", ()),
    "RETIRED_INACTIVE": ("retired", ("START_CONTEXT",)),
    "FINAL_PACKET": ("packet", ("FINAL_PACKET",)),
}
def lane_dependencies(receipt: dict[str, Any]) -> list[str]:
    """What an Attempt 2 lane's commands read from the checkout: every script its argv names inside the
    worktree, the whole ``src`` package they import, ``tests`` for a unittest run and the build inputs for a
    packaging run. Deliberately wide: a result is reused only when nothing it could have read has changed."""

    paths = {"src"}
    for command in receipt.get("commands") or []:
        argv = [str(item) for item in (command.get("argv") or command.get("command") or [])]
        for item in argv:
            candidate = Path(item)
            try:
                relative = candidate.resolve().relative_to(WORKTREE)
            except (OSError, ValueError):
                continue
            if relative.suffix == ".py":
                paths.add(relative.as_posix())
        if "unittest" in argv or any("unittest" in item for item in argv):
            paths.add("tests")
        if any(item.endswith(("pip", "build", "wheel")) or "wheel" in item for item in argv):
            paths.update({"pyproject.toml", "README.md"})
    return sorted(paths)
FINDING_IDS = ("MF37A02-01", "MF37A02-02", "MF37A02-03", "MF37A02-04", "MF37A02-05", "WORKER-W37R-71")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_out(*args: str) -> str:
    return subprocess.run(["git", "--no-optional-locks", "-C", str(WORKTREE), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", check=False).stdout.strip()


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_output(path: Path, text: str) -> str:
    """Declared outputs are rewritten until the writer is released; evidence files are never rewritten."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(temporary, path)
    return sha256_file(path)


def dumps(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n"


def carry_category(key: str) -> str:
    for prefix, name in (("ORIGINAL-AC-", "ORIGINAL_CRITERION"), ("ORIGINAL-OBL-", "ORIGINAL_OBLIGATION"),
                         ("ORIGINAL-LANE-", "ORIGINAL_LANE"), ("WORKER-", "WORKER_FINDING")):
        if key.startswith(prefix):
            return name
    return "MANAGER_FINDING"


# ------------------------------------------------------------------ context


class Context:
    def __init__(self, contract_path: Path, out_root: Path) -> None:
        self.contract_path = contract_path
        self.contract = read_json(contract_path)
        self.contract_sha256 = sha256_file(contract_path)
        self.out_root = out_root
        self.evidence: dict[str, dict[str, Any]] = {}
        self.runs = self._runs()
        self.receipts = {lane: read_json(Path(run["receipt"])) for lane, run in self.runs.items()}
        head = git_out("rev-parse", "HEAD")
        listing = subprocess.run(["git", "--no-optional-locks", "-C", str(WORKTREE), "ls-tree", "-r", "--full-tree",
                                  head], capture_output=True, check=True).stdout
        self.candidate = {"head": head, "tree": git_out("rev-parse", "HEAD^{tree}"),
                          "source_digest": hashlib.sha256(listing).hexdigest()}
        self.commits = [line.split(" ", 1) for line in git_out("log", "--format=%H %s", f"{BASE_SHA}..HEAD").splitlines()]
        self.candidate_commit_count = len(self.commits)
        self.criteria = {ac["id"]: {**ac, "requirement": req["id"]} for req in self.contract["requirements"]
                         for ac in req["acceptance"]}
        self.lanes = {lane["id"]: lane for lane in self.contract["required_lanes"]}
        path = out_root / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json"
        self.classification = read_json(path) if path.is_file() else {"lanes": {}}
        self.original_lanes: list[dict[str, Any]] = []
        self.obligation_items: list[dict[str, Any]] = []
        self.carry_counts: dict[str, Any] = {}
        self.latest_github = self._latest_summary("github/GITHUB_READ_SUMMARY_*.json")
        self.latest_all22 = self._latest_summary("all22/ALL22_READ_SUMMARY_*.json")

    def _runs(self) -> dict[str, dict[str, Any]]:
        index = self.out_root / "lanes" / "RUNS.jsonl"
        latest: dict[str, dict[str, Any]] = {}
        if index.is_file():
            for line in index.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    latest[row["lane"]] = row
        return latest

    def _latest_summary(self, pattern: str) -> dict[str, Any] | None:
        rows = []
        for phase in ("BEFORE", "DURING", "AFTER"):
            rows += sorted((self.out_root / "evidence" / "platform" / phase).glob(pattern))
        return read_json(rows[-1]) if rows else None

    def add(self, identity: str, path: Path, kind: str, scope: str) -> str:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"evidence {identity} is missing: {path}")
        self.evidence[identity] = {"id": identity, "path": str(path), "kind": kind, "scope": scope,
                                   "observed_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                                   "sha256": sha256_file(path)}
        return identity

    def at_head(self, lane: str) -> bool:
        run = self.runs.get(lane)
        return (bool(run) and run["head"] == self.candidate["head"]
                and run["source_digest"] == self.candidate["source_digest"])

    def lane_ok(self, lane: str) -> bool:
        return lane in self.receipts and self.receipts[lane]["result"] == "PASS" and self.at_head(lane)

    def executed(self, lane: str) -> bool:
        return lane in self.receipts and self.receipts[lane]["result"] in ("PASS", "FAIL") and self.at_head(lane)

    def finding_commits(self, finding: str) -> list[dict[str, str]]:
        token = finding.replace("WORKER-", "")
        return [{"sha": sha, "subject": subject} for sha, subject in reversed(self.commits)
                if re.search(rf"\b{re.escape(token)}\b", subject)]


# ------------------------------------------------------------------ evidence


def register_evidence(ctx: Context) -> None:
    root = ctx.out_root
    for lane, run in ctx.runs.items():
        receipt = Path(run["receipt"])
        ctx.add(f"E-LANE-{lane}-LOG", receipt.parent / "lane.log", "command_log",
                f"{lane} run {run['run']}: the runner's console -- every command, its exit and its verdict")
        ctx.add(f"E-LANE-{lane}-RECEIPT", receipt, RAW,
                f"{lane} run {run['run']}: contract, source, interpreter, raw log paths and digests, census "
                "records, consumer outputs and the write/network scope measurement")
    index = root / "lanes" / "RUNS.jsonl"
    if index.is_file():
        ctx.add("E-RUNS-INDEX", index, CENSUS, "Append-only index of every lane run: lane, head, source digest, receipt digest")
    for identity, path, scope in (
            ("E-INTAKE", root / "evidence" / "intake" / "INTAKE_BEFORE_IMPLEMENTATION.json",
             "Issuance, contract, database, wheels and storage verified before any change"),
            ("E-C29-CENSUS", root / "evidence" / "c29" / "CYCLE29_NUMERIC_CENSUS.json",
             "Independent raw numeric census of every Cycle 29 artifact, by JSON pointer"),
            ("E-REQUEST-LEDGER", root / "evidence" / "platform" / "REQUEST_LEDGER.jsonl",
             "Every counted platform request, retries included, appended before its result was used"),
            ("E-FAILURE-CLASSIFICATION", root / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json",
             "Worker classification of every failing identity of a red lane, by cause, kind, owner and next action"),
            ("E-NEW-FINDINGS", root / "evidence" / "NEW_FINDINGS_ATTEMPT3.json",
             "Findings discovered in Attempt 3, with severity, disposition, owner and next action")):
        if path.is_file():
            ctx.add(identity, path, CENSUS, scope)
    platform = root / "evidence" / "platform"
    for path in sorted(p for p in platform.rglob("*") if p.is_file() and p.suffix in (".json", ".csv", ".txt")
                       and p.parent != platform):
        relative = path.relative_to(platform).as_posix()
        ctx.add(f"E-PLATFORM-{relative}", path, CENSUS, f"Platform lifecycle evidence {relative}")
    for path in sorted((root / "evidence" / "scope").glob("*.json")):
        ctx.add(f"E-SCOPE-{path.name}", path, CENSUS, "Write-measurement exclusion basis measured with no lane running")


# ------------------------------------------------------------------ lanes


def lane_rows(ctx: Context) -> list[dict[str, Any]]:
    rows = []
    zero = {k: 0 for k in ("tests", "failures", "errors", "import_errors", "failed_subtests", "skipped")}
    for lane_id, lane in ctx.lanes.items():
        base = {"id": lane_id, "cwd": lane["cwd"], "command": lane["command"], "environment": lane["environment"],
                "data_binding": lane["data_binding"]}
        if lane["executor"] != "worker":
            rows.append({**base, "status": "PENDING_MANAGER", "executed": False, "exit_code": None, **zero,
                         "reason": "Manager-owned review lane; the worker neither executes nor signs it."})
            continue
        receipt = ctx.receipts.get(lane_id)
        if not receipt or not ctx.at_head(lane_id) or receipt["result"] not in ("PASS", "FAIL"):
            reason = ("Not yet run" if not receipt else
                      f"Latest run {ctx.runs[lane_id]['run']} is not at the candidate head" if not ctx.at_head(lane_id)
                      else f"Latest run {ctx.runs[lane_id]['run']} did not execute: {receipt['state_reason']}")
            rows.append({**base, "status": "NOT_RUN", "executed": False, "exit_code": None, **zero, "reason": reason})
            continue
        counts = receipt.get("counts") or {}
        status = receipt["result"]
        rows.append({**base, "status": status, "executed": True, "exit_code": 0 if status == "PASS" else 1,
                     **{k: int(counts.get(k) or 0) for k in zero},
                     "head": ctx.runs[lane_id]["head"], "source_digest": ctx.runs[lane_id]["source_digest"],
                     "log_id": f"E-LANE-{lane_id}-LOG", "receipt_id": f"E-LANE-{lane_id}-RECEIPT",
                     "run": ctx.runs[lane_id]["run"], "started_at": receipt.get("started_at"),
                     "finished_at": receipt.get("finished_at"), "reason": receipt["state_reason"]})
    return rows


def original_lane_dispositions(ctx: Context) -> list[dict[str, Any]]:
    rows = []
    for original, (slug, successors) in ORIGINAL_LANES.items():
        path = ATTEMPT2_ROOT / "evidence" / "lanes" / f"{slug}.json"
        receipt = read_json(path) if path.is_file() else {}
        row: dict[str, Any] = {
            "id": f"ORIGINAL-LANE-{original}", "original_lane": original, "attempt2_receipt": str(path),
            "attempt2_receipt_sha256": sha256_file(path) if path.is_file() else None,
            "attempt2_result": receipt.get("result"),
            "attempt2_head": (receipt.get("source_binding") or {}).get("head"),
            "attempt2_receipt_preserved": path.is_file(),
        }
        if successors:
            row.update(disposition="CARRIED_BY_ATTEMPT3_LANE_AT_THE_CANDIDATE_HEAD", attempt3_lanes=list(successors),
                       attempt3_results={lane: (ctx.receipts[lane]["result"] if ctx.at_head(lane) else "NOT_AT_HEAD")
                                         for lane in successors if lane in ctx.receipts},
                       justification="The obligation is re-executed by the named Attempt 3 lane(s) at the candidate "
                                     "head; the Attempt 2 receipt stays unchanged as the before-record and is not "
                                     "relabelled to the new head.")
        else:
            paths = lane_dependencies(receipt) if original != "FULL_BASELINE_MOUNTED" else ["src", "tests", "tools"]
            changed = [line for line in git_out("diff", "--name-only", f"{BASE_SHA}..{ctx.candidate['head']}", "--",
                                                *paths).splitlines() if line.strip()]
            if original == "FULL_BASELINE_MOUNTED":
                row.update(disposition="RETAINED_AS_THE_IMMUTABLE_HISTORICAL_BASELINE", dependency_paths=list(paths),
                           changed_since_attempt2_count=len(changed),
                           justification="A baseline is a before-record by definition; the Attempt 3 mounted lane "
                                         "compares its identities with the Attempt 2 final log, which itself "
                                         "recorded its comparison with this baseline.")
            elif changed:
                row.update(disposition="NOT_REUSED_DEPENDENCIES_CHANGED_OWNED_BACKLOG", dependency_paths=list(paths),
                           changed_since_attempt2=changed[:60], changed_since_attempt2_count=len(changed),
                           justification="Not a required Attempt 3 lane, and files under its dependency paths "
                                         "changed after its run, so its Attempt 2 result is history only, not "
                                         "current-head evidence; the obligation stays owned backlog.")
            else:
                row.update(disposition="REUSED_BY_UNCHANGED_DEPENDENCY_EQUIVALENCE", dependency_paths=list(paths),
                           changed_since_attempt2=[], changed_since_attempt2_count=0,
                           justification="No file under its dependency paths changed between the issued base (the "
                                         "Attempt 2 head) and the candidate head, so its Attempt 2 result is "
                                         "carried with that equivalence, not relabelled.")
        rows.append(row)
    rows.append({"id": "ORIGINAL-LANE-MANAGER_INDEPENDENT", "original_lane": "MANAGER_INDEPENDENT",
                 "disposition": "MANAGER_OWNED",
                 "justification": "Manager-owned; the Attempt 3 MANAGER_REVIEW lane is pending the manager."})
    return rows


# ------------------------------------------------------------------ criteria


def platform_phases(ctx: Context) -> dict[str, dict[str, bool]]:
    root = ctx.out_root / "evidence" / "platform"
    return {phase: {"jira": any((root / phase / "jira").glob("JIRA_READ_2*.json")),
                    "github": any((root / phase / "github").glob("GITHUB_READ_2*.json")),
                    "all22": any((root / phase / "all22").glob("ALL22_READ_2*.json"))}
            for phase in ("BEFORE", "DURING", "AFTER")}


def classification_problems(ctx: Context) -> list[str]:
    """A red lane's classification must name exactly its latest run's failing identities, and nothing local."""

    problems = []
    classified = ctx.classification.get("lanes") or {}
    for lane, receipt in ctx.receipts.items():
        if receipt["result"] != "FAIL" or not ctx.at_head(lane):
            continue
        entry = classified.get(lane)
        if not entry:
            problems.append(f"{lane} is red and its failures are not classified")
            continue
        if entry.get("run") != ctx.runs[lane]["run"]:
            problems.append(f"{lane}: the classification names run {entry.get('run')}, not the latest {ctx.runs[lane]['run']}")
        named = [identity for group in entry["groups"] for identity in group.get("identities") or []]
        failing = failing_identities(receipt)
        if failing is not None and sorted(named) != sorted(failing):
            problems.append(f"{lane}: classified identities differ from the run's failing identities "
                            f"(missing {sorted(set(failing) - set(named))[:5]}, extra {sorted(set(named) - set(failing))[:5]})")
        for group in entry["groups"]:
            if group.get("kind") not in BLOCKERS:
                problems.append(f"{lane}/{group.get('id')}: unknown blocker kind {group.get('kind')}")
    return problems


def failing_identities(receipt: dict[str, Any]) -> list[str] | None:
    details = receipt.get("details") or {}
    if "baseline_comparison" in details and "final_failed_or_errored" in details["baseline_comparison"]:
        return list(details["baseline_comparison"]["final_failed_or_errored"])
    if "strict_findings" in details:
        return [row["identity"] for row in details["strict_findings"]]
    return None


def judge(ctx: Context, key: str, requirement: str) -> tuple[str, str]:
    """A worker criterion is VERIFIED_LOCAL only when its carrying lanes ran at the candidate head and held."""

    if requirement == "R37A03-01":
        lanes = [lane for lane in WORKER_LANES if ctx.executed(lane)]
        writes = sum(ctx.receipts[lane]["write_and_network_scope"]["measurement"]["writes_outside_owned_roots"]
                     for lane in lanes)
        mounted = ctx.executed("FULL_FINAL_MOUNTED") and ctx.executed("STRICT_MOUNTED")
        if ctx.lane_ok("WRITE_PROTECTION") and mounted and writes == 0:
            return "VERIFIED_LOCAL", ("The guard suite and the manager's saved probe replay pass at the candidate "
                                      "head; the canonical-mounted lanes ran under the guard; across all "
                                      f"{len(lanes)} executed lane runs the data root and All-22 measured zero "
                                      "writes outside the owned roots.")
        return "IN_PROGRESS", (f"WRITE_PROTECTION held={ctx.lane_ok('WRITE_PROTECTION')}, mounted lanes executed="
                               f"{mounted}, writes outside owned roots={writes}")
    if requirement in ("R37A03-02", "R37A03-03"):
        if ctx.lane_ok("SOURCE_ADMISSION") and ctx.lane_ok("INSTALLED_CONSUMER_C01"):
            return "VERIFIED_LOCAL", ("Source and installed-wheel consumers refuse every manager counterexample and "
                                      "declared negative, the fixture positives pass only under test-only "
                                      "authority, and real eligible forecasts and proven PIT rows remain zero.")
        return "IN_PROGRESS", "SOURCE_ADMISSION or INSTALLED_CONSUMER_C01 has not held at the candidate head"
    if requirement == "R37A03-04":
        if ctx.lane_ok("INSTALLED_CONSUMER_C01") and ctx.lane_ok("SOURCE_REGRESSIONS"):
            return "VERIFIED_LOCAL", ("The installed noneditable wheel answers from the corrected tables with a raw "
                                      "locator and predecessor disposition per row; every table paginates to the "
                                      "SQL oracle; older releases stay readable; malformed releases refuse by name.")
        return "IN_PROGRESS", "INSTALLED_CONSUMER_C01 or SOURCE_REGRESSIONS has not held at the candidate head"
    if requirement == "R37A03-05":
        accounted = False
        if ctx.executed("FULL_FINAL_MOUNTED"):
            census = [row.get("census_reconciliation") or {} for row in ctx.receipts["FULL_FINAL_MOUNTED"]["commands"]
                      if row.get("census_reconciliation")]
            accounted = bool(census) and all(row.get("consistent") and row.get("origin_audit_holds") for row in census)
        classified = not [p for p in classification_problems(ctx) if p.startswith("FULL_FINAL_MOUNTED")]
        if ctx.lane_ok("SOURCE_HARNESS") and accounted and classified:
            return "VERIFIED_LOCAL", ("The harness binds the selected root; the full mounted suite's identities "
                                      "reconcile across unittest's counts, the verbose text and per-outcome records "
                                      "with no foreign import; its failures stay failures and every one is "
                                      "classified by identity against the Attempt 2 log.")
        return "IN_PROGRESS", (f"SOURCE_HARNESS held={ctx.lane_ok('SOURCE_HARNESS')}, full-suite accounting "
                               f"consistent={accounted}, failures classified={classified}")
    if requirement == "R37A03-06":
        if ctx.lane_ok("CLAIM_SUCCESSOR"):
            return "VERIFIED_LOCAL", ("The versioned successor reproduces from bytes, the independent census "
                                      "reproduces, the explicit-selection validator passes, and the default path "
                                      "still fails on the unchanged original inventory.")
        return "IN_PROGRESS", "CLAIM_SUCCESSOR has not held at the candidate head"
    if key.endswith("-A"):
        missing = [lane for lane in WORKER_LANES if not ctx.executed(lane)]
        if not missing:
            return "VERIFIED_LOCAL", ("Every required worker lane executed through the attempt03 runner at the "
                                      "candidate head with the issued command; the 22 original lane receipts are "
                                      "preserved with a reuse or invalidation disposition each.")
        return "IN_PROGRESS", "not yet executed at the candidate head: " + ", ".join(missing)
    if key.endswith("-B"):
        phases = platform_phases(ctx)
        complete = all(all(row.values()) for row in phases.values())
        if complete and ctx.lane_ok("PLATFORM_CARRY"):
            return "VERIFIED_LOCAL", ("BEFORE, DURING and AFTER Jira, GitHub and All-22 receipts exist, the AFTER "
                                      "ones bound to the candidate head; every granted comment was read back; the "
                                      "private Jira successor ran every step; requests stayed within each ceiling.")
        return "IN_PROGRESS", f"platform phases complete={complete}, PLATFORM_CARRY held={ctx.lane_ok('PLATFORM_CARRY')}"
    problems = accounting_problems(ctx) + classification_problems(ctx)
    if not problems and ctx.lane_ok("PLATFORM_CARRY"):
        return "VERIFIED_LOCAL", ("All 593 carryforward identities (345 criteria, 148 obligations, 22 lanes, 73 "
                                  "worker findings, 5 manager findings) keep their meanings and dispositions; red "
                                  "lanes stay red with every failing identity classified, local work separated "
                                  "from owner decisions.")
    return "IN_PROGRESS", "; ".join(problems[:3]) or "PLATFORM_CARRY has not held at the candidate head"


def criterion_evidence(ctx: Context, requirement: str) -> list[str]:
    ids: list[str] = []
    for lane in REQUIREMENT_LANES[requirement]:
        if ctx.executed(lane):
            ids += [f"E-LANE-{lane}-RECEIPT", f"E-LANE-{lane}-LOG"]
    extra = {"R37A03-05": ["E-FAILURE-CLASSIFICATION"],
             "R37A03-06": ["E-C29-CENSUS"],
             "R37A03-07": ["E-RUNS-INDEX", "E-ORIGINAL-OBLIGATIONS", "E-FAILURE-CLASSIFICATION", "E-REQUEST-LEDGER",
                           "E-INTAKE"]}.get(requirement, [])
    ids += extra
    return [identity for identity in dict.fromkeys(ids) if identity in ctx.evidence]


def criterion_results(ctx: Context) -> list[dict[str, Any]]:
    results = []
    for key, criterion in ctx.criteria.items():
        if criterion["executor"] != "worker":
            results.append({"id": key, "status": "PENDING_MANAGER", "evidence_ids": [],
                            "reason": "Manager-owned independent review; the worker cannot self-accept."})
            continue
        verdict, reason = judge(ctx, key, criterion["requirement"])
        evidence = criterion_evidence(ctx, criterion["requirement"])
        if key.endswith("-B") and criterion["requirement"] == "R37A03-07":
            evidence += sorted(identity for identity in ctx.evidence if identity.startswith("E-PLATFORM-")
                               and "/" in identity and identity.split("/")[-1].startswith(("JIRA_COMMENT", "JIRA_PRIVATE",
                                                                                          "GITHUB_READ_SUMMARY",
                                                                                          "ALL22_READ_SUMMARY",
                                                                                          "JIRA_READ_SUMMARY")))
        if verdict == "VERIFIED_LOCAL" and not any(ctx.evidence[e]["kind"] == criterion["evidence_kind"] for e in evidence):
            verdict, reason = "IN_PROGRESS", f"{reason} -- but no evidence of kind {criterion['evidence_kind']} exists"
        results.append({"id": key, "status": verdict, "reason": reason, "evidence_ids": evidence})
    return results


def accounting_problems(ctx: Context) -> list[str]:
    problems = []
    path = ctx.out_root / "ORIGINAL_OBLIGATION_DISPOSITIONS.json"
    if not path.is_file():
        return ["ORIGINAL_OBLIGATION_DISPOSITIONS.json is missing"]
    rows = {row["id"]: row for row in read_json(path).get("items", [])}
    expected = {row["id"]: row for row in ctx.contract["carryforward"]}
    if set(rows) != set(expected):
        problems.append(f"carryforward identities differ: missing {sorted(set(expected) - set(rows))[:5]}, "
                        f"extra {sorted(set(rows) - set(expected))[:5]}")
    for key, row in expected.items():
        mine = rows.get(key)
        if mine and any(mine.get(field) != row.get(field) for field in
                        ("original_meaning", "disposition", "owner", "reason", "next_action", "requirement_ids",
                         "acceptance_ids", "source_ids")):
            problems.append(f"{key}: an original field changed")
    composition = dict(collections.Counter(carry_category(key) for key in expected))
    wanted = {"ORIGINAL_CRITERION": 345, "ORIGINAL_OBLIGATION": 148, "ORIGINAL_LANE": 22, "WORKER_FINDING": 73,
              "MANAGER_FINDING": 5}
    if composition != wanted:
        problems.append(f"carryforward composition {composition} is not {wanted}")
    return problems


# ------------------------------------------------------------------ carryforward, findings, unfinished


def carryforward_rows(ctx: Context, criteria: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in ctx.contract["carryforward"]:
        evidence = ["E-ORIGINAL-OBLIGATIONS"]
        state = "OWNED_BACKLOG_RETAINED_NOT_FULFILLED_BY_ACCOUNTING"
        if row["disposition"] == "IN_CYCLE":
            linked = [criteria[a] for a in row["acceptance_ids"] if a in criteria]
            evidence += [e for c in linked for e in c["evidence_ids"]]
            state = ("ACTIVE_LINKS_VERIFIED_LOCAL_PENDING_MANAGER" if linked and all(
                c["status"] == "VERIFIED_LOCAL" for c in linked) else "ACTIVE_LINKS_NOT_ALL_VERIFIED")
        elif row["id"].startswith("ORIGINAL-LANE-"):
            evidence.append("E-OUTPUT-LANE_RESULTS.json")
        rows.append({"id": row["id"], "disposition": row["disposition"], "attempt3_state": state,
                     "evidence_ids": [e for e in dict.fromkeys(evidence) if e in ctx.evidence or e.startswith("E-OUTPUT-")]})
    return rows


def new_findings(ctx: Context, criteria: dict[str, Any]) -> list[dict[str, Any]]:
    path = ctx.out_root / "evidence" / "NEW_FINDINGS_ATTEMPT3.json"
    if not path.is_file():
        return []
    rows = []
    for row in read_json(path)["findings"]:
        row = dict(row)
        row["evidence_ids"] = list(dict.fromkeys(["E-NEW-FINDINGS", *row.get("evidence_ids", [])]))
        row["evidence_ids"] = [e for e in row["evidence_ids"] if e in ctx.evidence]
        row.setdefault("criterion_ids", [])
        row.setdefault("lane_ids", [])
        rows.append(row)
    return rows


def unfinished_items(ctx: Context, criteria: list[dict[str, Any]], lanes: list[dict[str, Any]],
                     findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = [{"id": "U-INDEPENDENT-REVIEW", "kind": "INDEPENDENT_REVIEW",
              "criterion_ids": [c["id"] for c in criteria if c["status"] == "PENDING_MANAGER"],
              "lane_ids": [lane["id"] for lane in lanes if lane["status"] == "PENDING_MANAGER"], "finding_ids": [],
              "owner": "Independent BAS manager",
              "next_action": "Replay the saved probes against the final source and the installed wheel in a fresh "
                             "owned namespace, review the lane receipts, platform readbacks and delivered files, and "
                             "accept or reject only supported scope.",
              "alternatives_and_reason": "The worker cannot award manager acceptance or sign the manager lane.",
              "evidence_ids": ["E-RUNS-INDEX" if "E-RUNS-INDEX" in ctx.evidence else "E-ORIGINAL-OBLIGATIONS"]}]
    local = [c for c in criteria if c["status"] not in ("VERIFIED_LOCAL", "PENDING_MANAGER")]
    if local:
        items.append({"id": "U-LOCAL-CRITERIA", "kind": "LOCAL_VALIDATION", "criterion_ids": [c["id"] for c in local],
                      "lane_ids": [], "finding_ids": [], "owner": "BAS worker",
                      "next_action": "Complete: " + "; ".join(f"{c['id']} ({c['reason']})" for c in local)[:1500],
                      "alternatives_and_reason": "Local work remains in this attempt.",
                      "evidence_ids": ["E-ORIGINAL-OBLIGATIONS"]})
    classified = ctx.classification.get("lanes") or {}
    for lane in lanes:
        if lane["status"] in ("PASS", "PENDING_MANAGER"):
            continue
        entry = classified.get(lane["id"])
        if lane["status"] == "FAIL" and entry and entry.get("run") == lane.get("run"):
            for group in entry["groups"]:
                identities = group.get("identities") or []
                items.append({"id": f"U-{lane['id']}-{group['id']}", "kind": group["kind"], "criterion_ids": [],
                              "lane_ids": [lane["id"]], "finding_ids": [], "owner": group["owner"],
                              "next_action": group["next_action"],
                              "alternatives_and_reason": f"{group['cause']} ({len(identities)} identities) "
                                                         f"{group['alternatives_and_reason']}",
                              "evidence_ids": [f"E-LANE-{lane['id']}-RECEIPT", "E-FAILURE-CLASSIFICATION"]})
        else:
            items.append({"id": f"U-{lane['id']}", "kind": "LOCAL_VALIDATION", "criterion_ids": [],
                          "lane_ids": [lane["id"]], "finding_ids": [], "owner": "BAS worker",
                          "next_action": (f"Run {lane['id']} at the candidate head with the issued command"
                                          if lane["status"] == "NOT_RUN" else
                                          f"Classify every failing identity of {lane['id']}'s latest run by cause"),
                          "alternatives_and_reason": lane.get("reason") or "not yet executed",
                          "evidence_ids": ["E-ORIGINAL-OBLIGATIONS"]})
    open_assigned = [f["id"] for f in findings if f["disposition"] == "OPEN_ASSIGNED"]
    if open_assigned:
        items.append({"id": "U-OPEN-ASSIGNED-FINDINGS", "kind": "LOCAL_CODE", "criterion_ids": [], "lane_ids": [],
                      "finding_ids": open_assigned, "owner": "BAS worker", "next_action": "Repair the named findings.",
                      "alternatives_and_reason": "Assigned in this attempt.", "evidence_ids": ["E-NEW-FINDINGS"]})
    return items


# ------------------------------------------------------------------ declared outputs


def before_after(ctx: Context) -> dict[str, dict[str, Any]]:
    def f(path: Path) -> dict[str, Any]:
        return {"path": str(path), "exists": path.is_file(), "sha256": sha256_file(path) if path.is_file() else None}

    a2_log = ATTEMPT2_ROOT / "logs" / "full-final-mounted" / "full-final-mounted__full_suite_final.log"
    return {
        "MF37A02-01": ([f(MANAGER_A2 / "WRITE_GUARD_INDEPENDENT_PROBE.json"), f(MANAGER_A2 / "probe_write_guard.py")],
                       ["WRITE_PROTECTION", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED"], "manager_write_guard_probe"),
        "MF37A02-02": ([f(MANAGER_A2 / "ADMISSION_SOURCE_PROBE.json"), f(MANAGER_A2 / "ADMISSION_INSTALLED_PROBE.json"),
                        f(MANAGER_A2 / "probe_admission.py")], ["SOURCE_ADMISSION", "INSTALLED_CONSUMER_C01"],
                       "manager_probe_admission"),
        "MF37A02-03": ([f(MANAGER_A2 / "PIT_INSTALLED_PROBE.json"), f(MANAGER_A2 / "probe_pit.py")],
                       ["SOURCE_ADMISSION", "INSTALLED_CONSUMER_C01"], "manager_probe_pit"),
        "MF37A02-04": ([f(MANAGER_A2 / "SUCCESSOR_CONSUMER_GAP.json"), f(MANAGER_A2 / "career-current-cli.json"),
                        f(MANAGER_A2 / "responsibility-current-cli.json")],
                       ["INSTALLED_CONSUMER_C01", "SOURCE_REGRESSIONS"], "bill_anderson"),
        "MF37A02-05": ([f(MANAGER_A2 / "HARNESS_IMPORT_INDEPENDENT_PROBE.json"), f(MANAGER_A2 / "probe_harness_import.py"),
                        f(ATTEMPT2_ROOT / "evidence" / "lanes" / "full-final-mounted.json"), f(a2_log)],
                       ["SOURCE_HARNESS", "FULL_FINAL_MOUNTED"], "manager_harness_import_probe"),
        "WORKER-W37R-71": ([f(ORIGINAL_INVENTORY)], ["CLAIM_SUCCESSOR"], "claim_successor"),
    }


def finding_matrix(ctx: Context, label: str, criteria: dict[str, dict[str, Any]]) -> dict[str, Any]:
    carry = {row["id"]: row for row in ctx.contract["carryforward"]}
    rows = []
    for key, (before, lanes, detail_key) in before_after(ctx).items():
        requirement = next(r for r in ctx.contract["requirements"] if key in r["inherited_ids"])
        after = []
        for lane in lanes:
            receipt = ctx.receipts.get(lane) or {}
            detail = (receipt.get("details") or {}).get(detail_key)
            after.append({"lane": lane, "run": (ctx.runs.get(lane) or {}).get("run"), "result": receipt.get("result"),
                          "at_candidate_head": ctx.at_head(lane), "receipt_evidence_id": f"E-LANE-{lane}-RECEIPT",
                          "receipt_sha256": (ctx.runs.get(lane) or {}).get("receipt_sha256"),
                          "consumer_output": detail if detail is not None and len(json.dumps(detail, default=str)) < 6000
                          else ({"see_receipt_details_key": detail_key} if detail is not None else None)})
        rows.append({
            "finding": key, "requirement": requirement["id"], "original_meaning": carry[key]["original_meaning"],
            "worker_disposition": "REPAIRED_LOCAL_PENDING_MANAGER_REPLAY",
            "commits": ctx.finding_commits(key),
            "before_raw_proof": before, "after_raw_proof": after,
            "consumer": requirement["acceptance"][0]["consumer"],
            "criteria": {ac["id"]: criteria[ac["id"]]["status"] for ac in requirement["acceptance"]},
        })
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "contract_sha256": ctx.contract_sha256, "candidate": ctx.candidate,
            "findings": rows,
            "not_claimed": "Each repair is local and pending the manager's independent replay; the worker closes no finding."}


def consumer_manifest(ctx: Context, label: str) -> dict[str, Any]:
    details = (ctx.receipts.get("INSTALLED_CONSUMER_C01") or {}).get("details") or {}
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "candidate": ctx.candidate,
            "installed_lane_run": ctx.runs.get("INSTALLED_CONSUMER_C01"),
            "wheel": {"built_from": "git archive of the candidate head's pyproject.toml, README.md and src, built "
                                    "offline with cached tooling, installed noneditable into a new environment",
                      "sha256": details.get("wheel_sha256"), "environment": details.get("installed")},
            "module_origins": details.get("installed_origins"),
            "installed_source_equivalence": details.get("installed_source_equivalence"),
            "c01": {"wheel_sha256": C01_SHA256, "composition": details.get("c01_composition"),
                    "manager_probe_replay": details.get("manager_c01_independent")},
            "delivered_database": {"sha256": DB_SHA256, "unchanged": details.get("delivered_database_unchanged")},
            "cli_results": details.get("cli_results"), "pagination": details.get("pagination"),
            "filtered_oracle": details.get("filtered_oracle"), "bill_anderson": details.get("bill_anderson"),
            "career_locators": details.get("career_locators"),
            "responsibility_locators": details.get("responsibility_locators"),
            "admission_installed": details.get("attempt03_admission_probe_installed"),
            "manager_admission_installed": details.get("manager_probe_admission_installed"),
            "manager_pit_installed": details.get("manager_probe_pit_installed"),
            "claim_successor": {"path": str(SUCCESSOR), "sha256": sha256_file(SUCCESSOR),
                                "consumer": "tools/validate_cycle29_gates.py --claim-inventory-successor",
                                "lane": ctx.runs.get("CLAIM_SUCCESSOR")},
            "consumers": {"bas-staff-query": "aggie_analytics.cycle33.query:main (installed console script)",
                          "scoring": "aggie_analytics.cycle36.scoring_guards",
                          "pit": "aggie_analytics.cycle36.kernel_reference",
                          "receipt_authority": "aggie_analytics.cycle37.receipt_authority",
                          "write_guard": "tools/cycle37/canonical_write_guard (sitecustomize audit hook)",
                          "test_census": "aggie_analytics.validation.unittest_census --selected-root"},
            "real_eligible_forecasts": 0, "real_proven_pit_rows": 0,
            "not_claimed": "No release, successor inventory or restoration candidate is activated or published."}


def platform_reconciliation(ctx: Context, label: str) -> dict[str, Any]:
    root = ctx.out_root / "evidence" / "platform"
    receipts: dict[str, Any] = {}
    for phase in ("BEFORE", "DURING", "AFTER"):
        receipts[phase] = {system: [{"path": str(p), "sha256": sha256_file(p), "label": (read_json(p).get("label")
                                                                                       if p.suffix == ".json" else None)}
                                    for p in sorted((root / phase / system).glob("*")) if p.is_file()]
                           for system in ("jira", "github", "all22")}
    comments = []
    for path in sorted(root.rglob("JIRA_COMMENT_*.json")):
        data = read_json(path)
        comments.append({k: data.get(k) for k in ("phase", "issue", "marker", "result", "created_id",
                                                  "readback_comment_ids", "comments_before", "comments_after",
                                                  "body_sha256", "action", "actor", "target")}
                        | {"receipt": str(path), "receipt_sha256": sha256_file(path)})
    successors = []
    for path in sorted(root.rglob("JIRA_PRIVATE_SUCCESSOR_*.json")):
        data = read_json(path)
        successors.append({"receipt": str(path), "receipt_sha256": sha256_file(path), "phase": data.get("phase"),
                           "source_export": data.get("source_export"),
                           "steps": [{"name": c["name"], "exit": c["exit"], "conflicts": c["conflict_count"],
                                      "summary": c["summary"]} for c in data.get("commands", [])],
                           "private_changes": len(data.get("record_changes_in_private_copy") or []),
                           "committed_canonical_mutations": data.get("committed_canonical_mutations"),
                           "write_guard_blocked": len((data.get("write_guard") or {}).get("blocked") or []),
                           "outside_scope_count": data.get("outside_scope_count"),
                           "canonical_ids_missing_from_live": data.get("canonical_ids_missing_from_live"),
                           "adopted": data.get("adopted")})
    corrections = [{"path": str(p), "sha256": sha256_file(p), "defect": read_json(p).get("defect")}
                   for p in sorted(root.rglob("*.provenance.json"))]
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
            "candidate": ctx.candidate, "receipts": receipts, "granted_comments": comments,
            "private_jira_successors": successors, "export_corrections": corrections,
            "label_note": ("BEFORE and DURING receipts carry the ASCII label 'Cycle #37 - Attempt #3 - <phase>'; they "
                           "are unchanged and bound here by digest under the numeric label."),
            "mutations": {"jira_status_label_owner_board_done": 0, "github": 0, "all22_owner_repositories": 0,
                          "granted_jira_comments_succeeded": sum(1 for c in comments if c["result"] == "SUCCEEDED")},
            "not_claimed": ("A converging private successor is not canonical adoption, a comment is not canonical "
                            "convergence, and no proposal is adoption; none of those authorities is granted here.")}


def ledger_totals(ctx: Context) -> dict[str, dict[str, int]]:
    ledger = ctx.out_root / "evidence" / "platform" / "REQUEST_LEDGER.jsonl"
    totals = {lane["id"]: {"requests": 0, "retries": 0, "ceiling": lane["ceiling"]}
              for lane in ctx.contract["budgets"]["network_lanes"]}
    if ledger.is_file():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                totals[row["lane"]]["requests"] += 1
                totals[row["lane"]]["retries"] += int(bool(row.get("retry")))
    return totals


def costs(ctx: Context) -> dict[str, Any]:
    return {"paid_ai_calls": 0, "paid_ai_cost": 0,
            "request_ledger_ref": str(ctx.out_root / "evidence" / "platform" / "REQUEST_LEDGER.jsonl"),
            "network_usage": [{"id": lane, "requests": row["requests"], "retries": row["retries"], "cache_hits": 0,
                               "evidence_ids": ["E-REQUEST-LEDGER"] if row["requests"] else [],
                               "overrun_finding_ids": []} for lane, row in ledger_totals(ctx).items()]}


def effects(ctx: Context) -> list[dict[str, Any]]:
    grants = ctx.contract["authority"]["grants"]
    local = next(g for g in grants if g["action"] == "LOCAL_IMPLEMENTATION_AND_PRIVATE_SUCCESSOR_EVIDENCE")
    reads = next(g for g in grants if g["action"] == "READ_ONLY_FREE_METADATA")
    rows = [{"id": "EFF-LOCAL-COMMITS", "actor": local["actor"], "action": local["action"], "target": local["target"],
             "result": "SUCCEEDED",
             "detail": f"{len(ctx.commits)} local commits on {BRANCH} after the issued base, ending at "
                       f"{ctx.candidate['head']}; nothing pushed, merged, retargeted or rewritten; private Jira "
                       "successors only under the validation root.",
             "evidence_ids": [e for e in ("E-LANE-START_CONTEXT-RECEIPT", "E-RUNS-INDEX") if e in ctx.evidence]}]
    totals = ledger_totals(ctx)
    if "E-REQUEST-LEDGER" in ctx.evidence:
        rows.append({"id": "EFF-READ-ONLY-METADATA", "actor": reads["actor"], "action": reads["action"],
                     "target": reads["target"], "result": "SUCCEEDED",
                     "detail": "; ".join(f"{k} {v['requests']}/{v['ceiling']} requests ({v['retries']} retries)"
                                         for k, v in totals.items()),
                     "evidence_ids": ["E-REQUEST-LEDGER"]})
    for path in sorted((ctx.out_root / "evidence" / "platform").rglob("JIRA_COMMENT_*.json")):
        data = read_json(path)
        key = f"E-PLATFORM-{path.relative_to(ctx.out_root / 'evidence' / 'platform').as_posix()}"
        rows.append({"id": f"EFF-{data['phase']}-{data['marker']}", "actor": data["actor"], "action": data["action"],
                     "target": data["target"], "result": data["result"],
                     "detail": f"Marker {data['marker']} checked against {data.get('comments_before')} existing "
                               f"comments; created {data.get('created_id')}; read back {data.get('readback_comment_ids')}.",
                     "evidence_ids": [key]})
    return rows


def platform_receipts(ctx: Context, criteria: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    phases = platform_phases(ctx)
    rows = []
    for duty in ctx.contract["platform_plan"]["lifecycle"]:
        if duty["executor"] != "worker":
            rows.append({"id": duty["id"], "state": "PENDING_MANAGER", "result": "Independent review remains",
                         "next_action": "The manager re-reads the platform state and the receipts independently",
                         "evidence_ids": []})
            continue
        system, phase = duty["platform"].lower(), duty["phase"]
        files = sorted(e for e in ctx.evidence if e.startswith(f"E-PLATFORM-{phase}/{system}/"))
        verified = phases[phase][system] and all(criteria[a]["status"] == "VERIFIED_LOCAL" for a in duty["acceptance_ids"])
        summary = [e for e in files if "SUMMARY" in e]
        rows.append({"id": duty["id"], "state": "VERIFIED" if verified else "IN_PROGRESS",
                     "result": (f"{len(files)} {system} {phase} evidence file(s)"
                                + (f", read summary {summary[-1].split('/')[-1]}" if summary else "")),
                     "next_action": "Independent review remains" if verified else "Complete the phase and PLATFORM_CARRY",
                     "evidence_ids": files or ["E-ORIGINAL-OBLIGATIONS"]})
    return rows


def claim_successor(ctx: Context, label: str) -> dict[str, Any]:
    document = read_json(SUCCESSOR)
    lane = ctx.receipts.get("CLAIM_SUCCESSOR") or {}
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "finding": "W37R-71",
            "requirement": "R37A03-06", "candidate": ctx.candidate,
            "successor": {"path": str(SUCCESSOR), "sha256": sha256_file(SUCCESSOR),
                          "version": document.get("successor_version"), "body_sha256": document.get("body_sha256"),
                          "claims": document.get("claim_count"), "pointers": document.get("pointer_count"),
                          "classification_counts": document.get("classification_counts"),
                          "accounting": document.get("numeric_value_accounting")},
            "original_inventory": {"path": str(ORIGINAL_INVENTORY), "sha256": sha256_file(ORIGINAL_INVENTORY),
                                   "unchanged_since_base": not git_out("diff", "--name-only", BASE_SHA, "--",
                                                                       str(ORIGINAL_INVENTORY.relative_to(WORKTREE)))},
            "predecessor_inventory": document.get("predecessor_inventory"), "census": document.get("census"),
            "lane": {"run": ctx.runs.get("CLAIM_SUCCESSOR"), "result": lane.get("result"),
                     "at_candidate_head": ctx.at_head("CLAIM_SUCCESSOR"),
                     "details": (lane.get("details") or {}).get("claim_successor")},
            "claims_by_class": {cls: [c["claim_id"] for c in document.get("claims", []) if c["classification"] == cls]
                                for cls in ("EVIDENCE_BACKED", "RECONSTRUCTED", "UNSUPPORTED", "CONTRADICTED")},
            "carried_forward_original_claims": document.get("carried_forward_original_claims"),
            "not_claimed": document.get("not_claimed"), "limitations": document.get("limitations")}


A2_THREADS = ATTEMPT2_ROOT / "evidence" / "repairs" / "R37_I_THREAD_DISPOSITIONS.json"


def thread_map(ctx: Context) -> dict[str, Any] | None:
    """Every unresolved review thread at the latest GitHub read, joined by thread ID to its Attempt 2 disposition,
    with whether this attempt changed the file the thread is about. Nothing here resolves a thread."""

    raws = []
    for phase in ("BEFORE", "DURING", "AFTER"):
        raws += sorted((ctx.out_root / "evidence" / "platform" / phase / "github").glob("GITHUB_READ_2*.json"))
    if not raws:
        return None
    raw = read_json(raws[-1])
    previous = read_json(A2_THREADS)["threads"] if A2_THREADS.is_file() else []
    prior = {row["thread_id"]: row for row in previous}
    located = collections.defaultdict(list)
    for row in previous:
        located[(row.get("pr"), row.get("path"), row.get("line"))].append(row)
    changed_paths = set(git_out("diff", "--name-only", f"{BASE_SHA}..{ctx.candidate['head']}").splitlines())
    rows = []
    for pr in raw.get("open_pull_requests") or []:
        for thread in (pr.get("reviewThreads") or {}).get("nodes") or []:
            if thread.get("isResolved"):
                continue
            before, joined = (prior.get(thread["id"]), "thread_id") if thread.get("id") else (None, None)
            if before is None:
                # A read without thread IDs is joined only where PR, path and line name exactly one prior thread.
                candidates = located.get((pr.get("number"), thread.get("path"), thread.get("line"))) or []
                if len(candidates) == 1:
                    before, joined = candidates[0], "pr_path_line_unique"
            rows.append({"pr": pr.get("number"), "thread_id": thread.get("id"), "joined_by": joined,
                         "path": thread.get("path"),
                         "line": thread.get("line"), "outdated": thread.get("isOutdated"),
                         "attempt2_disposition": (before or {}).get("disposition") or "NOT_IN_ATTEMPT2_SET",
                         "attempt2_title": (before or {}).get("title"),
                         "attempt2_remaining": (before or {}).get("remaining"),
                         "attempt2_owner": (before or {}).get("owner"),
                         "path_changed_by_attempt3": thread.get("path") in changed_paths})
    return {"read": str(raws[-1]), "read_sha256": sha256_file(raws[-1]), "thread_ids_read": all(r["thread_id"] for r in rows),
            "attempt2_dispositions": str(A2_THREADS), "attempt2_dispositions_sha256": sha256_file(A2_THREADS) if A2_THREADS.is_file() else None,
            "unresolved": len(rows),
            "by_attempt2_disposition": dict(collections.Counter(r["attempt2_disposition"] for r in rows)),
            "paths_changed_by_attempt3": sorted({r["path"] for r in rows if r["path_changed_by_attempt3"]}),
            "threads": rows}


def integration_packet(ctx: Context, label: str, lanes: list[dict[str, Any]]) -> str:
    github = ctx.latest_github or {}
    lines = [f"# {label}", "", "## Integration decision packet (no action executed)", "",
             f"Internal identity `{CYCLE_ID}` / `{ATTEMPT_ID}`; contract SHA-256 `{ctx.contract_sha256}`. Candidate "
             f"branch `{BRANCH}`: head `{ctx.candidate['head']}`, tree `{ctx.candidate['tree']}`, source digest "
             f"`{ctx.candidate['source_digest']}`, {len(ctx.commits)} commits after the issued base `{BASE_SHA}`.", "",
             "Decision state: **NOT_AUTHORIZED**. The cycle hold is active. This attempt holds no grant to push, open, "
             "close or retarget a pull request, merge, publish, activate a release or successor, delete a branch or "
             "change an owner repository, so none of those was done.", "", "### Candidate commits", ""]
    lines += [f"- `{sha[:12]}` {subject}" for sha, subject in reversed(ctx.commits)]
    lines += ["", "### Lane state at the candidate head", "",
              "| Lane | Status | Tests | Failures | Errors | Skipped |", "| --- | --- | --- | --- | --- | --- |"]
    lines += [f"| {l['id']} | {l['status']} | {l['tests']} | {l['failures']} | {l['errors']} | {l['skipped']} |"
              for l in lanes]
    lines += ["", "### GitHub state at the latest read", "",
              f"Read {github.get('phase')} at {github.get('observed_at')}: main `{github.get('main_head')}`, "
              f"{github.get('open_pr_count')} open pull requests, {github.get('unresolved_thread_total')} unresolved "
              "review threads, subject bound in the read receipt.", "",
              "| PR | Base | Head | Draft | Review decision | Unresolved threads | Rollup |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for pr in github.get("open_prs") or []:
        lines.append(f"| #{pr.get('number')} | {pr.get('base')} | `{(pr.get('head') or '')[:12]}` | {pr.get('draft')} | "
                     f"{pr.get('review_decision')} | {pr.get('unresolved_threads')} | {pr.get('rollup')} |")
    threads = thread_map(ctx)
    if threads:
        lines += ["", "### Unresolved review threads mapped to their dispositions", "",
                  f"{threads['unresolved']} unresolved threads at `{Path(threads['read']).name}` (SHA-256 "
                  f"`{threads['read_sha256']}`), joined by thread ID to the Attempt 2 dispositions "
                  f"(`{threads['attempt2_dispositions']}`). Thread IDs present in the read: {threads['thread_ids_read']}. "
                  "Counts by that disposition: "
                  + ", ".join(f"{k} {v}" for k, v in sorted(threads["by_attempt2_disposition"].items())) + ". "
                  "The Attempt 2 thread repairs are regression-tested by `test_cycle37_thread_repairs`, which runs in "
                  "SOURCE_REGRESSIONS at the candidate head. No thread is resolved or replied to: there is no grant.", ""]
        if threads["paths_changed_by_attempt3"]:
            lines += ["Files these threads concern that this attempt changed (each re-verified by the lane suites "
                      "named in LANE_RESULTS.json): " + ", ".join(f"`{p}`" for p in threads["paths_changed_by_attempt3"]), ""]
        lines += ["| PR | Thread | Path:line | Attempt 2 disposition | Remaining | Owner |", "| --- | --- | --- | --- | --- | --- |"]
        for row in threads["threads"]:
            lines.append(f"| #{row['pr']} | `{row['thread_id']}` | `{row['path']}`:{row['line']} | {row['attempt2_disposition']} | "
                         f"{(row['attempt2_remaining'] or '').replace('|', '/')[:160]} | {(row['attempt2_owner'] or '').replace('|', '/')[:80]} |")
    lines += ["", "### Separable decisions for the owner and manager (none executed)", "",
              "1. **Review** -- keep the candidate on its branch for the independent manager review of this attempt "
              "(recommended next step; needs no grant).",
              "2. **Publish** -- push the branch to the remote for hosted checks. Needs an explicit actor/action/target "
              "grant naming this branch and head; reversible by deleting the remote ref.",
              "3. **Integrate** -- after manager acceptance and a merge grant naming base, head and method, integrate "
              "through a reviewed pull request; the open review threads and the inherited red canonical-mounted "
              "lanes must be dispositioned first. Rollback: revert the merge commit.",
              "4. **Activate** -- the corrected national release, the Cycle 29 claim-inventory successor and the "
              "prepared canonical-inventory restoration candidate each need a separate owner decision; all remain "
              "NOT_ACTIVATED.",
              "5. **Owner re-binds** -- the inherited mounted failures clear only through the owner decisions named "
              "in UNFINISHED items of submission.json (Family B activation, canonical inventory restoration, core-"
              "module re-binds).", ""]
    return "\n".join(lines) + "\n"


def cost_ledger(ctx: Context, label: str) -> dict[str, Any]:
    free = shutil.disk_usage("C:/").free
    reserve = ctx.contract["budgets"]["storage_reserve_bytes"]
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
            "paid_ai": {"calls": 0, "cost_usd": 0, "ceiling_usd": ctx.contract["budgets"]["paid_ai_usd"]},
            "request_lanes": ledger_totals(ctx), "request_ledger": str(ctx.out_root / "evidence" / "platform" / "REQUEST_LEDGER.jsonl"),
            "storage": {"free_bytes_now": free, "reserve_bytes": reserve, "reserve_satisfied": free >= reserve,
                        "peak_extra_bytes_allowed": ctx.contract["budgets"]["storage_peak_extra_bytes"]},
            "grants_used": effects(ctx),
            "authority_not_used": ["publication", "merge", "PR creation, closure or retarget", "branch deletion or rewrite",
                                   "filesystem cleanup or moves", "canonical activation", "protected evaluation",
                                   "owner-repository or schema mutation", "paid providers", "source acquisition",
                                   "retired assistive execution", "Jira status, label, owner, Done or board changes",
                                   "CFIP comments (prior denial not bypassed)"]}


# ------------------------------------------------------------------ build


def build(ctx: Context, headline: str, writer_released: bool) -> dict[str, Any]:
    register_evidence(ctx)
    root = ctx.out_root
    lanes = lane_rows(ctx)
    ctx.original_lanes = original_lane_dispositions(ctx)
    obligations_path = root / "ORIGINAL_OBLIGATION_DISPOSITIONS.json"

    def write_obligations(label: str, states: dict[str, dict[str, Any]]) -> None:
        items = []
        for row in ctx.contract["carryforward"]:
            item = {"id": row["id"], "category": carry_category(row["id"]),
                    **{k: row[k] for k in ("original_meaning", "disposition", "source_ids", "requirement_ids",
                                           "acceptance_ids", "owner", "reason", "next_action")}}
            if row["id"] in states:
                item["attempt3_state"] = states[row["id"]]["attempt3_state"]
                item["attempt3_evidence_ids"] = [e for e in states[row["id"]]["evidence_ids"]
                                                 if e != "E-ORIGINAL-OBLIGATIONS"]
            items.append(item)
        ctx.carry_counts = {"composition": dict(collections.Counter(i["category"] for i in items)),
                            "dispositions": dict(collections.Counter(i["disposition"] for i in items))}
        ctx.obligation_items = items
        write_output(obligations_path, dumps({
            "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "contract_sha256": ctx.contract_sha256, "candidate": ctx.candidate,
            **ctx.carry_counts, "items": items, "original_lanes": ctx.original_lanes,
            "note": ("Original meanings, sources, owners, reasons, next actions and dispositions are copied from the "
                     "issued contract unchanged. OWNED_BACKLOG items stay owned; none is marked fulfilled by this "
                     "accounting.")}))
        ctx.add("E-ORIGINAL-OBLIGATIONS", obligations_path, CENSUS,
                "All 593 carryforward identities with their original meanings and unchanged dispositions")

    label = f"Cycle #{CYCLE_NUMBER} \u2014 Attempt #{ATTEMPT_NUMBER} \u2014 {headline}"
    write_obligations(label, {})
    # The lane accounting must exist before the criteria that judge it are computed.
    write_output(root / "LANE_RESULTS.json", dumps({
        "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "candidate": ctx.candidate,
        "runner": "tools/cycle37/attempt03_lanes.py", "runs_index": str(root / "lanes" / "RUNS.jsonl"),
        "lanes": lanes, "original_lanes": ctx.original_lanes}))
    ctx.add("E-OUTPUT-LANE_RESULTS.json", root / "LANE_RESULTS.json", CENSUS,
            "Every required lane's result at the candidate head and all 22 original lane dispositions")
    criteria = criterion_results(ctx)
    by_id = {row["id"]: row for row in criteria}
    carry = carryforward_rows(ctx, by_id)
    write_obligations(label, {row["id"]: row for row in carry})
    carry = carryforward_rows(ctx, by_id)
    findings = new_findings(ctx, by_id)
    unfinished = unfinished_items(ctx, criteria, lanes, findings)
    local = [item["id"] for item in unfinished if item["kind"].startswith("LOCAL_")]
    if headline != "IN_PROGRESS_LOCAL_WORK_REMAINS":
        if local:
            raise SystemExit(f"refusing terminal headline {headline}: local work remains in {local}")
        if not writer_released:
            raise SystemExit("a terminal headline requires --writer-released")
    worker = [c for c in criteria if ctx.criteria[c["id"]]["executor"] == "worker"]
    complete = all(c["status"] == "VERIFIED_LOCAL" for c in worker) and not any(
        f["disposition"] == "OPEN_ASSIGNED" for f in findings)
    software = ("FAIL" if any(l["status"] == "FAIL" for l in lanes) else
                "PASS" if all(l["status"] == "PASS" for l in lanes) else
                "NOT_RUN" if not any(l["executed"] or l["status"] == "PASS" for l in lanes) else "PARTIAL")
    installed = (ctx.receipts.get("INSTALLED_CONSUMER_C01") or {}).get("details") or {}
    pagination = installed.get("pagination") or {}
    successor = read_json(SUCCESSOR)
    if ctx.lane_ok("INSTALLED_CONSUMER_C01") and ctx.lane_ok("CLAIM_SUCCESSOR"):
        data_evidence = (f"DELIVERED_RELEASE_{DB_SHA256[:12]}_UNCHANGED; CORRECTED_CAREER_ROWS_SERVED_"
                         f"{(pagination.get('career_corrected') or {}).get('distinct')}; CORRECTED_RESPONSIBILITY_ROWS_SERVED_"
                         f"{(pagination.get('responsibility_corrected') or {}).get('distinct')}; C29_SUCCESSOR_"
                         f"{successor.get('claim_count')}_CLAIMS; REAL_ELIGIBLE_FORECASTS_0; REAL_PROVEN_PIT_0")
    else:
        data_evidence = "INCOMPLETE"
    submission = {
        "schema_version": "BAS-SUBMISSION-2.4", "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "cycle_id": CYCLE_ID, "attempt_id": ATTEMPT_ID, "display_label": label,
        "contract_sha256": ctx.contract_sha256, "headline": headline, "candidate": ctx.candidate,
        "writer_released": writer_released,
        "safe_local_work_remaining": headline == "IN_PROGRESS_LOCAL_WORK_REMAINS",
        "dimensions": {"implementation": "COMPLETE_LOCAL" if complete else "IN_PROGRESS",
                       "data_evidence": data_evidence, "software_validation": software,
                       "independent_acceptance": "PENDING_MANAGER_REVIEW", "integration_release": "NOT_AUTHORIZED",
                       "overall_cycle": headline},
        "predictive_skill": "NOT_ESTABLISHED",
        "criteria": criteria,
        "carryforward": [{"id": r["id"], "disposition": r["disposition"], "evidence_ids": r["evidence_ids"]} for r in carry],
        "lanes": lanes, "evidence": [], "unfinished": unfinished, "new_findings": findings,
        "effects": effects(ctx), "costs": costs(ctx), "platform_receipts": platform_receipts(ctx, by_id),
        "handoff_artifacts": [], "observed_at": utc_now(),
    }
    outputs = {
        "FINDING_CLOSURE_MATRIX.json": dumps(finding_matrix(ctx, label, by_id)),
        "DELIVERED_CONSUMER_MANIFEST.json": dumps(consumer_manifest(ctx, label)),
        "PLATFORM_RECONCILIATION.json": dumps(platform_reconciliation(ctx, label)),
        "COST_AND_AUTHORITY_LEDGER.json": dumps(cost_ledger(ctx, label)),
        "HISTORICAL_CLAIM_SUCCESSOR.json": dumps(claim_successor(ctx, label)),
        "INTEGRATION_DECISION_PACKET.md": integration_packet(ctx, label, lanes),
    }
    for name, text in outputs.items():
        write_output(root / name, text)
        ctx.add(f"E-OUTPUT-{name}", root / name, CENSUS, f"Declared worker output {name}")
    ctx.successor_summary = (f"{successor.get('claim_count')} claims at {successor.get('pointer_count')} JSON "
                             f"pointers, classified {successor.get('classification_counts')}")
    executed = [lane for lane in WORKER_LANES if ctx.executed(lane)]
    ctx.all_runs_clean = bool(executed) and all(
        ctx.receipts[lane]["source_binding"].get("clean") and ctx.receipts[lane]["source_binding_after"].get("clean")
        for lane in executed)
    import attempt03_report  # the narrative report, beside this tool

    report = attempt03_report.render(ctx, submission)
    write_output(root / "WORKER_REPORT.md", report)
    return submission


def seal(ctx: Context, submission: dict[str, Any]) -> None:
    """Record every declared output except submission.json by digest, then the evidence index, then write."""

    artifacts = []
    for name in ctx.contract["paths"]["worker_outputs"]:
        path = ctx.out_root / name
        if name != "submission.json" and path.is_file():
            artifacts.append({"id": name, "sha256": sha256_file(path)})
    submission["handoff_artifacts"] = artifacts
    submission["evidence"] = [ctx.evidence[k] for k in sorted(ctx.evidence)]
    write_output(ctx.out_root / "submission.json", dumps(submission))


# ------------------------------------------------------------------ check


def check(ctx: Context, final_packet: bool) -> list[str]:
    problems = accounting_problems(ctx) + classification_problems(ctx)
    for name in ("LANE_RESULTS.json", "FINDING_CLOSURE_MATRIX.json", "DELIVERED_CONSUMER_MANIFEST.json",
                 "PLATFORM_RECONCILIATION.json", "COST_AND_AUTHORITY_LEDGER.json", "HISTORICAL_CLAIM_SUCCESSOR.json",
                 "INTEGRATION_DECISION_PACKET.md", "ORIGINAL_OBLIGATION_DISPOSITIONS.json", "WORKER_REPORT.md"):
        path = ctx.out_root / name
        if not path.is_file():
            problems.append(f"{name} is missing")
            continue
        # A report's first line, or a JSON document's first key, carries the numeric identity label.
        first = path.read_text(encoding="utf-8").splitlines()[:2]
        if not any("Cycle #37 \u2014 Attempt #3 \u2014" in line for line in first):
            problems.append(f"{name} does not begin with the numeric identity label")
    lanes_doc = ctx.out_root / "LANE_RESULTS.json"
    if lanes_doc.is_file():
        document = read_json(lanes_doc)
        if {row["id"] for row in document["lanes"]} != set(ctx.lanes):
            problems.append("LANE_RESULTS lane set differs from the contract's")
        originals = {row["id"] for row in document["original_lanes"]}
        wanted = {row["id"] for row in ctx.contract["carryforward"] if row["id"].startswith("ORIGINAL-LANE-")}
        if originals != wanted:
            problems.append(f"LANE_RESULTS original lanes differ: {sorted(originals ^ wanted)}")
        if document["candidate"] != ctx.candidate:
            problems.append("LANE_RESULTS was built for another subject")
    matrix = ctx.out_root / "FINDING_CLOSURE_MATRIX.json"
    if matrix.is_file():
        rows = read_json(matrix)["findings"]
        if {row["finding"] for row in rows} != set(FINDING_IDS):
            problems.append("FINDING_CLOSURE_MATRIX does not cover exactly MF37A02-01..05 and W37R-71")
        for row in rows:
            if not row["commits"]:
                problems.append(f"{row['finding']} names no commit")
    for lane, row in ledger_totals(ctx).items():
        if row["requests"] > row["ceiling"]:
            problems.append(f"{lane}: {row['requests']} requests exceed the ceiling {row['ceiling']}")
    if final_packet:
        for lane in WORKER_LANES:
            if lane == "FINAL_PACKET":
                continue
            if lane not in ctx.receipts:
                problems.append(f"{lane} has no receipt")
            elif not ctx.at_head(lane):
                problems.append(f"{lane}'s latest receipt is not at the candidate head")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=("build", "check", "seal"),
                        help="seal: after cycle_protocol.py checklist has written WORKER_CHECKLIST.csv, record every "
                             "declared output's digest in the existing submission without rebuilding anything")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--headline", default="IN_PROGRESS_LOCAL_WORK_REMAINS", choices=HEADLINES)
    parser.add_argument("--writer-released", action="store_true")
    parser.add_argument("--final-packet", action="store_true")
    args = parser.parse_args(argv)
    ctx = Context(args.contract.resolve(), args.out_root.resolve())
    if args.mode == "check":
        problems = check(ctx, args.final_packet)
        print(json.dumps({"label": "Cycle #37 \u2014 Attempt #3 \u2014 accounting check",
                          "result": "PASS" if not problems else "FAIL", "problems": problems,
                          "candidate": ctx.candidate}, indent=2, ensure_ascii=False))
        return 0 if not problems else 1
    if args.mode == "seal":
        submission = read_json(ctx.out_root / "submission.json")
        stale = [row["id"] for row in submission["evidence"] if sha256_file(Path(row["path"])) != row["sha256"]]
        if stale:
            raise SystemExit(f"evidence changed after the build; rebuild instead of sealing: {stale}")
        ctx.evidence = {row["id"]: row for row in submission["evidence"]}
        seal(ctx, submission)
        print(json.dumps({"sealed": [row["id"] for row in submission["handoff_artifacts"]]}, indent=2))
        return 0
    submission = build(ctx, args.headline, args.writer_released)
    seal(ctx, submission)
    print(json.dumps({"headline": submission["headline"],
                      "criteria": dict(collections.Counter(c["status"] for c in submission["criteria"])),
                      "lanes": {l["id"]: l["status"] for l in submission["lanes"]},
                      "unfinished": [(u["id"], u["kind"]) for u in submission["unfinished"]],
                      "evidence": len(submission["evidence"])}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
