r"""Cycle #37 — Attempt #4 — worker outputs, submission and accounting check (R37A04-07).

    attempt04_outputs.py classify --contract C --out-root R
    attempt04_outputs.py build --contract C --out-root R [--headline H --writer-released]
    attempt04_outputs.py check --contract C --out-root R [--final-packet]
    attempt04_outputs.py seal --contract C --out-root R

``build`` writes the declared worker outputs under the attempt root from what is there: the issued contract,
the lane receipts named in ``lanes/RUNS.jsonl``, the platform receipts and request ledger, the delivered career
successor (by its pointer and digest), git, and worker-authored evidence it reads but never invents:
``evidence/INHERITED_FAILURE_CLASSIFICATION.json`` and ``evidence/NEW_FINDINGS_ATTEMPT4.json``.

``classify`` derives the Attempt 4 failure classification of a red mounted lane from the Attempt 3 one: an
identity that persists with the same traceback cause keeps its Attempt 3 group; any identity that is new, or
whose cause changed, is refused and must be classified by hand. Nothing is classified by count.

``check`` fails on any gap: a carryforward identity missing, renamed or with a changed original field; a request
ceiling exceeded; a red lane whose failures are not classified by exact identity; an output without the numeric
label; ``--final-packet`` also requires every worker lane except FINAL_PACKET to have a receipt at the head.

The default headline is IN_PROGRESS_LOCAL_WORK_REMAINS. A terminal headline must be asked for explicitly, with
``--writer-released``, and is refused while any unfinished item is local work. This tool never accepts anything.
"""

from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt03_outputs as base  # noqa: E402  (the preserved Attempt 3 accounting this module rebinds)
from attempt03_outputs import (  # noqa: E402
    CENSUS,
    RAW,
    WORKTREE,
    dumps,
    git_out,
    read_json,
    sha256_file,
    utc_now,
    write_output,
)

CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID, ATTEMPT_ID = 37, 4, "CYCLE-37", "ATTEMPT-04-20260924"
BASE_SHA = "ade8f25a814ed68c19c2b451a93e2651787bf592"
#: The Attempt 2 head (the Attempt 3 base): what "changed since Attempt 2" is measured from.
ATTEMPT2_HEAD = "8fcb5fb66867ef08a61de12bf2eff569b54ac253"
BRANCH = "codex/BAT-706-cycle37-rework"
DATA = Path(r"C:\BatteredAggieSyndrome.data")
ATTEMPT2_ROOT = DATA / "ops" / "cycle37" / "attempts" / "REWORK-20260922T171601Z"
ATTEMPT3_ROOT = DATA / "ops" / "cycle37" / "attempt03"
MANAGER_A3 = DATA / "ops" / "manager_reviews" / "cycle37" / "attempt03" / "review-20260924T212311Z"
C29_SUCCESSOR = base.SUCCESSOR
DB_SHA256 = base.DB_SHA256
C01_SHA256 = base.C01_SHA256
HEADLINES = base.HEADLINES
BLOCKERS = base.BLOCKERS
WORKER_LANES = ("START_CONTEXT", "WRITE_PROTECTION", "SOURCE_ADMISSION", "SOURCE_HARNESS", "SOURCE_REGRESSIONS",
                "INSTALLED_CONSUMER_C01", "CAREER_SUCCESSOR", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED", "TRUE_UNMOUNTED",
                "PLATFORM_CARRY", "FINAL_PACKET")
FINDING_IDS = ("MF37A03-01", "MF37A03-02", "MF37A03-03", "MF37A03-04", "MF37A03-05")
REQUIREMENT_LANES = {
    "R37A04-01": ("WRITE_PROTECTION", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED", "TRUE_UNMOUNTED"),
    "R37A04-02": ("SOURCE_ADMISSION", "INSTALLED_CONSUMER_C01"),
    "R37A04-03": ("SOURCE_ADMISSION", "INSTALLED_CONSUMER_C01"),
    "R37A04-04": ("CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01"),
    "R37A04-05": ("CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01"),
    "R37A04-06": ("CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01", "SOURCE_REGRESSIONS"),
    "R37A04-07": WORKER_LANES,
}
#: Attempt 3's thirteen lanes and the Attempt 4 lanes that carry each obligation now.
A03_LANES = {
    "START_CONTEXT": ("START_CONTEXT",), "WRITE_PROTECTION": ("WRITE_PROTECTION",),
    "SOURCE_ADMISSION": ("SOURCE_ADMISSION",), "SOURCE_HARNESS": ("SOURCE_HARNESS",),
    "SOURCE_REGRESSIONS": ("SOURCE_REGRESSIONS",), "INSTALLED_CONSUMER_C01": ("INSTALLED_CONSUMER_C01",),
    "CLAIM_SUCCESSOR": ("CAREER_SUCCESSOR",), "FULL_FINAL_MOUNTED": ("FULL_FINAL_MOUNTED",),
    "STRICT_MOUNTED": ("STRICT_MOUNTED",), "TRUE_UNMOUNTED": ("TRUE_UNMOUNTED",),
    "PLATFORM_CARRY": ("PLATFORM_CARRY",), "FINAL_PACKET": ("FINAL_PACKET",), "MANAGER_REVIEW": (),
}
CARRY_COMPOSITION = {"ORIGINAL_CRITERION": 345, "ORIGINAL_OBLIGATION": 148, "ORIGINAL_LANE": 22,
                     "WORKER_FINDING": 73, "ATTEMPT3_CRITERION": 28, "ATTEMPT3_LANE": 13,
                     "ATTEMPT3_WORKER_FINDING": 12, "MANAGER_FINDING": 10}
LABEL_PREFIX = "Cycle #37 \u2014 Attempt #4 \u2014"


def rebind() -> None:
    base.CYCLE_NUMBER, base.ATTEMPT_NUMBER, base.CYCLE_ID, base.ATTEMPT_ID = (CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID,
                                                                              ATTEMPT_ID)
    base.BASE_SHA = BASE_SHA
    base.BRANCH = BRANCH
    base.WORKER_LANES = WORKER_LANES


def carry_category(key: str) -> str:
    for prefix, name in (("ORIGINAL-AC-", "ORIGINAL_CRITERION"), ("ORIGINAL-OBL-", "ORIGINAL_OBLIGATION"),
                         ("ORIGINAL-LANE-", "ORIGINAL_LANE"), ("A03-AC-", "ATTEMPT3_CRITERION"),
                         ("A03-LANE-", "ATTEMPT3_LANE"), ("A03-WORKER-", "ATTEMPT3_WORKER_FINDING"),
                         ("WORKER-", "WORKER_FINDING")):
        if key.startswith(prefix):
            return name
    return "MANAGER_FINDING"


# ------------------------------------------------------------------ context


class Context(base.Context):
    def __init__(self, contract_path: Path, out_root: Path) -> None:
        super().__init__(contract_path, out_root)
        pointer = out_root / "release" / "CAREER_SUCCESSOR_POINTER.json"
        self.pointer_path = pointer
        self.pointer = read_json(pointer) if pointer.is_file() else {}
        self.findings_path = out_root / "evidence" / "NEW_FINDINGS_ATTEMPT4.json"

    def build_summary(self) -> dict[str, Any]:
        path = Path(self.pointer.get("build_summary", "")) if self.pointer else None
        return read_json(path) if path and path.is_file() else {}

    def finding_commits(self, finding: str) -> list[dict[str, str]]:
        return [{"sha": sha, "subject": subject} for sha, subject in reversed(self.commits)
                if re.search(rf"\b{re.escape(finding)}\b", subject)]


# ------------------------------------------------------------------ evidence


def register_evidence(ctx: Context) -> None:
    base.register_evidence(ctx)
    root = ctx.out_root
    for identity, path, kind, scope in (
            ("E-NEW-FINDINGS", ctx.findings_path, CENSUS,
             "Findings discovered in Attempt 4, with severity, disposition, owner and next action"),
            ("E-BEFORE-MANIFEST", root / "evidence" / "before" / "BEFORE_REPRODUCTION_MANIFEST.json", RAW,
             "Before-repair reproduction of MF37A03-01..05 against the Attempt 3 head and installed wheel"),
            ("E-SUCCESSOR-POINTER", ctx.pointer_path, CENSUS,
             "The delivered explicit career successor: file, digest, predecessor digest and build summary")):
        if Path(path).is_file():
            ctx.add(identity, path, kind, scope)
    for path in sorted((root / "evidence" / "before").glob("*")):
        if path.is_file() and path.name != "BEFORE_REPRODUCTION_MANIFEST.json":
            ctx.add(f"E-BEFORE-{path.name}", path, RAW, f"Before-repair reproduction file {path.name}")
    release = root / "release"
    for path in sorted(release.rglob("*")):
        if path.is_file() and path.suffix in (".json", ".gz") and path != ctx.pointer_path:
            ctx.add(f"E-RELEASE-{path.relative_to(release).as_posix()}", path, CENSUS,
                    f"Delivered career successor build file {path.name}")


# ------------------------------------------------------------------ lanes


def lane_rows(ctx: Context) -> list[dict[str, Any]]:
    return base.lane_rows(ctx)


def original_lane_dispositions(ctx: Context) -> list[dict[str, Any]]:
    """The 22 original lanes: Attempt 2 receipts preserved, carried by the Attempt 4 lanes that re-execute them."""

    rows = []
    for original, (slug, successors) in base.ORIGINAL_LANES.items():
        path = ATTEMPT2_ROOT / "evidence" / "lanes" / f"{slug}.json"
        receipt = read_json(path) if path.is_file() else {}
        row: dict[str, Any] = {
            "id": f"ORIGINAL-LANE-{original}", "original_lane": original, "attempt2_receipt": str(path),
            "attempt2_receipt_sha256": sha256_file(path) if path.is_file() else None,
            "attempt2_result": receipt.get("result"), "attempt2_head": (receipt.get("source_binding") or {}).get("head"),
            "attempt2_receipt_preserved": path.is_file()}
        if successors:
            row.update(disposition="CARRIED_BY_ATTEMPT4_LANE_AT_THE_CANDIDATE_HEAD", attempt4_lanes=list(successors),
                       attempt4_results={lane: (ctx.receipts[lane]["result"] if ctx.at_head(lane) else "NOT_AT_HEAD")
                                         for lane in successors if lane in ctx.receipts},
                       justification="Re-executed by the named Attempt 4 lane(s) at the candidate head; the Attempt 2 "
                                     "receipt stays unchanged as the before-record.")
        else:
            paths = base.lane_dependencies(receipt) if original != "FULL_BASELINE_MOUNTED" else ["src", "tests", "tools"]
            changed = [line for line in git_out("diff", "--name-only", f"{ATTEMPT2_HEAD}..{ctx.candidate['head']}",
                                                "--", *paths).splitlines() if line.strip()]
            if original == "FULL_BASELINE_MOUNTED":
                row.update(disposition="RETAINED_AS_THE_IMMUTABLE_HISTORICAL_BASELINE", dependency_paths=list(paths),
                           changed_since_attempt2_count=len(changed),
                           justification="A baseline is a before-record; FULL_FINAL_MOUNTED compares by identity with "
                                         "the Attempt 3 and Attempt 2 final logs.")
            elif changed:
                row.update(disposition="NOT_REUSED_DEPENDENCIES_CHANGED_OWNED_BACKLOG", dependency_paths=list(paths),
                           changed_since_attempt2=changed[:60], changed_since_attempt2_count=len(changed),
                           justification="Not a required Attempt 4 lane, and files under its dependency paths changed "
                                         "after its run, so its Attempt 2 result is history, not current-head "
                                         "evidence; the obligation stays owned backlog.")
            else:
                row.update(disposition="REUSED_BY_UNCHANGED_DEPENDENCY_EQUIVALENCE", dependency_paths=list(paths),
                           changed_since_attempt2=[], changed_since_attempt2_count=0,
                           justification="No file under its dependency paths changed since the Attempt 2 head, so its "
                                         "result is carried with that equivalence, not relabelled.")
        rows.append(row)
    rows.append({"id": "ORIGINAL-LANE-MANAGER_INDEPENDENT", "original_lane": "MANAGER_INDEPENDENT",
                 "disposition": "MANAGER_OWNED",
                 "justification": "Manager-owned; the Attempt 4 MANAGER_REVIEW lane is pending the manager."})
    return rows


def _a03_final(lane: str) -> dict[str, Any]:
    index = ATTEMPT3_ROOT / "lanes" / "RUNS.jsonl"
    rows = [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [row for row in rows if row["lane"] == lane and row["head"] == BASE_SHA]
    return rows[-1] if rows else {}


def attempt3_lane_dispositions(ctx: Context) -> list[dict[str, Any]]:
    rows = []
    for lane, successors in A03_LANES.items():
        final = _a03_final(lane)
        row: dict[str, Any] = {"id": f"A03-LANE-{lane}", "attempt3_lane": lane,
                               "attempt3_run": final.get("run"), "attempt3_result": final.get("result"),
                               "attempt3_head": final.get("head"), "attempt3_receipt": final.get("receipt"),
                               "attempt3_receipt_sha256": final.get("receipt_sha256"),
                               "attempt3_receipt_preserved": bool(final.get("receipt")) and Path(final["receipt"]).is_file()}
        if not successors:
            row.update(disposition="MANAGER_OWNED", justification="The Attempt 3 manager lane is the manager's.")
        else:
            row.update(disposition="CARRIED_BY_ATTEMPT4_LANE_AT_THE_CANDIDATE_HEAD", attempt4_lanes=list(successors),
                       attempt4_results={s: (ctx.receipts[s]["result"] if ctx.at_head(s) else "NOT_AT_HEAD")
                                         for s in successors if s in ctx.receipts},
                       justification=("The Cycle 29 claim-successor checks of CLAIM_SUCCESSOR run inside "
                                      "CAREER_SUCCESSOR, unchanged." if lane == "CLAIM_SUCCESSOR" else
                                      "Re-executed by the same-named Attempt 4 lane at the candidate head."))
        rows.append(row)
    return rows


# ------------------------------------------------------------------ inherited red lanes


def classify(ctx: Context) -> dict[str, Any]:
    """Derive the Attempt 4 classification from Attempt 3's, identity by identity and cause by cause."""

    previous = read_json(ATTEMPT3_ROOT / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json")
    lanes: dict[str, Any] = {}
    problems: list[str] = []
    for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED"):
        receipt = ctx.receipts.get(lane)
        if not receipt or receipt["result"] != "FAIL" or not ctx.at_head(lane):
            continue
        failing = base.failing_identities(receipt) or []
        details = receipt.get("details") or {}
        comparison = details.get("attempt3_comparison") or {}
        changed = set((comparison.get("persisting_changed_cause") or {}))
        a3_groups = (previous["lanes"].get(lane) or {}).get("groups") or []
        group_of = {identity: group for group in a3_groups for identity in group.get("identities") or []}
        groups: dict[str, dict[str, Any]] = {}
        for identity in failing:
            group = group_of.get(identity)
            if group is None or identity in changed:
                problems.append(f"{lane}: {identity} is new or changed cause; classify it by hand")
                continue
            entry = groups.setdefault(group["id"], {k: v for k, v in group.items() if k != "identities"} | {"identities": []})
            entry["identities"].append(identity)
        lanes[lane] = {"run": ctx.runs[lane]["run"], "head": ctx.runs[lane]["head"],
                       "attempt3_run": (previous["lanes"].get(lane) or {}).get("run"),
                       "groups": list(groups.values()),
                       "equivalence": {"persisting": len(comparison.get("persisting") or []),
                                       "persisting_same_cause": len(comparison.get("persisting_same_cause") or []),
                                       "new_in_attempt4": comparison.get("new_in_attempt4"),
                                       "no_longer_failing": comparison.get("no_longer_failing") or
                                       comparison.get("no_longer_reported")}}
    if problems:
        raise SystemExit("classification refused:\n" + "\n".join(problems))
    document = {"label": f"{LABEL_PREFIX} IN_PROGRESS_LOCAL_WORK_REMAINS (inherited failure classification)",
                "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
                "attempt_id": ATTEMPT_ID, "authored_at": utc_now(),
                "rule": ("Each failing identity keeps its Attempt 3 group only when it persists with the same "
                         "traceback cause (FULL_FINAL_MOUNTED) or the same finding line (STRICT_MOUNTED); anything "
                         "else is refused for manual classification."),
                "derived_from": {"path": str(ATTEMPT3_ROOT / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json"),
                                 "sha256": sha256_file(ATTEMPT3_ROOT / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json")},
                "lanes": lanes}
    path = ctx.out_root / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json"
    write_output(path, dumps(document))
    return document


def inherited_equivalence(ctx: Context, label: str) -> dict[str, Any]:
    rows = []
    for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED", "TRUE_UNMOUNTED"):
        receipt = ctx.receipts.get(lane) or {}
        details = receipt.get("details") or {}
        rows.append({"lane": lane, "run": (ctx.runs.get(lane) or {}).get("run"), "result": receipt.get("result"),
                     "at_candidate_head": ctx.at_head(lane), "counts": receipt.get("counts"),
                     "attempt3_comparison": details.get("attempt3_comparison"),
                     "attempt2_comparison": {k: v for k, v in (details.get("baseline_comparison") or {}).items()
                                             if k not in ("final_failed_or_errored",)},
                     "failing_identities": base.failing_identities(receipt) if receipt else None})
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "candidate": ctx.candidate, "inherited_red": rows,
            "classification": ctx.classification, "original_lanes": ctx.original_lanes,
            "attempt3_lanes": ctx.attempt3_lanes,
            "rule": ("Inherited red lanes stay red until genuinely resolved. Equivalence is by exact identity and cause "
                     "against the Attempt 3 final receipts at the issued base; counts alone establish nothing.")}


# ------------------------------------------------------------------ criteria


def judge(ctx: Context, key: str, requirement: str) -> tuple[str, str]:
    if requirement == "R37A04-01":
        lanes = [lane for lane in WORKER_LANES if ctx.executed(lane)]
        writes = sum(ctx.receipts[lane]["write_and_network_scope"]["measurement"]["writes_outside_owned_roots"]
                     for lane in lanes)
        mounted = ctx.executed("FULL_FINAL_MOUNTED") and ctx.executed("STRICT_MOUNTED") and ctx.executed("TRUE_UNMOUNTED")
        probe = ((ctx.receipts.get("WRITE_PROTECTION") or {}).get("details") or {}).get("manager_a3_git_alias_probe") or {}
        if ctx.lane_ok("WRITE_PROTECTION") and mounted and writes == 0 and probe.get("alias_refused_before_effect"):
            return "VERIFIED_LOCAL", ("The guard suites (write/route/network matrix and the Git child matrix with live "
                                      "controls) and both manager probes hold at the candidate head: the Attempt 3 "
                                      "alias is refused before any effect and the protected sentinel keeps its bytes. "
                                      "The mounted lanes ran after that qualification, under the v37.4 guard, and "
                                      f"across {len(lanes)} executed lane runs the data root and All-22 measured zero "
                                      "writes outside the owned roots. This is a Python-process guard, not OS isolation.")
        return "IN_PROGRESS", (f"WRITE_PROTECTION held={ctx.lane_ok('WRITE_PROTECTION')}, alias refused="
                               f"{probe.get('alias_refused_before_effect')}, mounted lanes executed={mounted}, "
                               f"writes outside owned roots={writes}")
    if requirement in ("R37A04-02", "R37A04-03"):
        if ctx.lane_ok("SOURCE_ADMISSION") and ctx.lane_ok("INSTALLED_CONSUMER_C01"):
            return "VERIFIED_LOCAL", ("Source and the fresh installed wheel refuse the Attempt 3 manager's forged "
                                      "contest, forged probability/Brier/authority, pre-freeze correction, missing and "
                                      "mixed target cutoffs, and the Attempt 2 probes; this attempt's own challenges "
                                      "refuse too; the positives hold only under TEST_ONLY authority, with real "
                                      "eligible forecasts and proven PIT rows zero.")
        return "IN_PROGRESS", "SOURCE_ADMISSION or INSTALLED_CONSUMER_C01 has not held at the candidate head"
    if requirement in ("R37A04-04", "R37A04-05", "R37A04-06"):
        needed = REQUIREMENT_LANES[requirement]
        if all(ctx.lane_ok(lane) for lane in needed):
            text = {"R37A04-04": ("Unknown role parentheticals (DFO, STQC, SA, novel codes, unpaired text) are "
                                  "explicitly unresolved and never head coach; the 343 priority rows keep no head-coach "
                                  "row; every one of the 3896 broad-screen rows has a disposition with a grounded "
                                  "basis; TX/OC/multiple-role/no-title controls hold; the installed CLI serves it."),
                    "R37A04-05": ("Unknown, partial, approximate and decade endpoints keep explicit states distinct "
                                  "from present; season membership uses definite bounds; the 312 screened rows are "
                                  "dispositioned; the installed CLI's season filters match the independent oracle."),
                    "R37A04-06": ("All 72,070 predecessor rows carry exactly one disposition; the rebuild from the "
                                  "committed subject reproduces the delivered successor; the installed CLI paginates "
                                  "it completely and refuses tampered, duplicate, missing and wrong-predecessor "
                                  "successors; routing, harness and the Cycle 29 successor are preserved.")}[requirement]
            return "VERIFIED_LOCAL", text
        return "IN_PROGRESS", "not all of " + ", ".join(needed) + " held at the candidate head"
    if key.endswith("-A"):
        missing = [lane for lane in WORKER_LANES if not ctx.executed(lane)]
        if not missing:
            return "VERIFIED_LOCAL", ("Every required worker lane executed through the attempt04 runner at the "
                                      "candidate head with the issued command, the guard qualified first; the 22 "
                                      "original and 13 Attempt 3 lanes each carry a disposition; inherited red "
                                      "identities are compared by identity and cause.")
        return "IN_PROGRESS", "not yet executed at the candidate head: " + ", ".join(missing)
    if key.endswith("-B"):
        phases = base.platform_phases(ctx)
        complete = all(all(row.values()) for row in phases.values())
        if complete and ctx.lane_ok("PLATFORM_CARRY"):
            return "VERIFIED_LOCAL", ("BEFORE, DURING and AFTER Jira, GitHub and All-22 receipts exist, the AFTER ones "
                                      "bound to the candidate head; every granted comment was read back; the private "
                                      "Jira successor ran every step; requests stayed within each ceiling.")
        return "IN_PROGRESS", f"platform phases complete={complete}, PLATFORM_CARRY held={ctx.lane_ok('PLATFORM_CARRY')}"
    problems = accounting_problems(ctx) + base.classification_problems(ctx)
    if not problems and ctx.lane_ok("PLATFORM_CARRY"):
        return "VERIFIED_LOCAL", ("All 651 carryforward identities keep their meanings and dispositions; red lanes stay "
                                  "red with every failing identity classified; one conditional integration packet "
                                  "is prepared with no history rewrite, PR or merge.")
    return "IN_PROGRESS", "; ".join(problems[:3]) or "PLATFORM_CARRY has not held at the candidate head"


def criterion_evidence(ctx: Context, requirement: str) -> list[str]:
    ids: list[str] = []
    for lane in REQUIREMENT_LANES[requirement]:
        if ctx.executed(lane):
            ids += [f"E-LANE-{lane}-RECEIPT", f"E-LANE-{lane}-LOG"]
    extra = {"R37A04-01": ["E-BEFORE-MANIFEST", "E-BEFORE-INDEPENDENT_WRITE_GUARD.json"],
             "R37A04-02": ["E-BEFORE-MANIFEST", "E-BEFORE-INDEPENDENT_ADMISSION_SOURCE.json",
                           "E-BEFORE-INDEPENDENT_ADMISSION_INSTALLED.json"],
             "R37A04-03": ["E-BEFORE-MANIFEST", "E-BEFORE-INDEPENDENT_PIT_SOURCE.json",
                           "E-BEFORE-INDEPENDENT_PIT_INSTALLED.json"],
             "R37A04-04": ["E-BEFORE-MANIFEST", "E-BEFORE-CAREER_SEMANTIC_REPRODUCTION.json", "E-SUCCESSOR-POINTER"],
             "R37A04-05": ["E-BEFORE-MANIFEST", "E-BEFORE-CAREER_SEMANTIC_REPRODUCTION.json", "E-SUCCESSOR-POINTER"],
             "R37A04-06": ["E-SUCCESSOR-POINTER", "E-OUTPUT-CAREER_POPULATION_DISPOSITIONS.json",
                           "E-OUTPUT-CAREER_CORRECTION_SUCCESSOR.json"],
             "R37A04-07": ["E-RUNS-INDEX", "E-ORIGINAL-OBLIGATIONS", "E-FAILURE-CLASSIFICATION", "E-REQUEST-LEDGER",
                           "E-OUTPUT-LANE_RESULTS.json"]}.get(requirement, [])
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
        if key.endswith("-B") and criterion["requirement"] == "R37A04-07":
            evidence += sorted(identity for identity in ctx.evidence if identity.startswith("E-PLATFORM-")
                               and identity.split("/")[-1].startswith(("JIRA_COMMENT", "JIRA_PRIVATE",
                                                                       "GITHUB_READ_SUMMARY", "ALL22_READ_SUMMARY",
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
                         "acceptance_ids", "source_ids", "prior_mapping")):
            problems.append(f"{key}: an original field changed")
    composition = dict(collections.Counter(carry_category(key) for key in expected))
    if composition != CARRY_COMPOSITION:
        problems.append(f"carryforward composition {composition} is not {CARRY_COMPOSITION}")
    return problems


# ------------------------------------------------------------------ carryforward, findings, unfinished


def carryforward_rows(ctx: Context, criteria: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in ctx.contract["carryforward"]:
        evidence = ["E-ORIGINAL-OBLIGATIONS"]
        state = "OWNED_BACKLOG_RETAINED_NOT_FULFILLED_BY_ACCOUNTING"
        if row["disposition"] == "IN_CYCLE":
            linked = [criteria[a] for a in row["acceptance_ids"] if a in criteria]
            if not linked:
                linked = [criteria[c] for req in row["requirement_ids"] for c in criteria
                          if c.startswith(req + "-") and not c.endswith("-M")]
            evidence += [e for c in linked for e in c["evidence_ids"]]
            state = ("ACTIVE_LINKS_VERIFIED_LOCAL_PENDING_MANAGER" if linked and all(
                c["status"] == "VERIFIED_LOCAL" for c in linked) else "ACTIVE_LINKS_NOT_ALL_VERIFIED")
        elif row["id"].startswith(("ORIGINAL-LANE-", "A03-LANE-")):
            evidence.append("E-OUTPUT-LANE_RESULTS.json")
        rows.append({"id": row["id"], "disposition": row["disposition"], "attempt4_state": state,
                     "evidence_ids": [e for e in dict.fromkeys(evidence) if e in ctx.evidence or e.startswith("E-OUTPUT-")]})
    return rows


def new_findings(ctx: Context) -> list[dict[str, Any]]:
    if not ctx.findings_path.is_file():
        return []
    rows = []
    for row in read_json(ctx.findings_path)["findings"]:
        row = dict(row)
        # Declared outputs are registered as evidence later in the same build, before the submission is sealed.
        row["evidence_ids"] = [e for e in dict.fromkeys(["E-NEW-FINDINGS", *row.get("evidence_ids", [])])
                               if e in ctx.evidence or e.startswith("E-OUTPUT-")]
        row.setdefault("criterion_ids", [])
        row.setdefault("lane_ids", [])
        rows.append(row)
    return rows


def unfinished_items(ctx: Context, criteria: list[dict[str, Any]], lanes: list[dict[str, Any]],
                     findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = base.unfinished_items(ctx, criteria, lanes, findings)
    for item in items:
        if item["id"] == "U-OPEN-ASSIGNED-FINDINGS":
            item["evidence_ids"] = ["E-NEW-FINDINGS"] if "E-NEW-FINDINGS" in ctx.evidence else item["evidence_ids"]
    owner_findings = [f for f in findings if f["disposition"] == "OPEN_OUT_OF_SCOPE"]
    if owner_findings:
        items.append({"id": "U-NEW-FINDINGS-OWNED", "kind": "OWNER_DECISION", "criterion_ids": [], "lane_ids": [],
                      "finding_ids": [f["id"] for f in owner_findings], "owner": "BAS owner / next cycle planning",
                      "next_action": "; ".join(f"{f['id']}: {f['next_action']}" for f in owner_findings)[:1500],
                      "alternatives_and_reason": "Discovered and disclosed in this attempt; outside its issued repair "
                                                 "scope or awaiting an owner decision.",
                      "evidence_ids": ["E-NEW-FINDINGS"]})
    return items


# ------------------------------------------------------------------ declared outputs


def _f(path: Path) -> dict[str, Any]:
    return {"path": str(path), "exists": path.is_file(), "sha256": sha256_file(path) if path.is_file() else None}


def finding_matrix(ctx: Context, label: str, criteria: dict[str, dict[str, Any]]) -> dict[str, Any]:
    before = ctx.out_root / "evidence" / "before"
    plan = {
        "MF37A03-01": ([_f(MANAGER_A3 / "INDEPENDENT_WRITE_GUARD.json"), _f(MANAGER_A3 / "independent_probes.py"),
                        _f(before / "INDEPENDENT_WRITE_GUARD.json")],
                       {"WRITE_PROTECTION": "manager_a3_git_alias_probe", "FULL_FINAL_MOUNTED": "attempt3_comparison",
                        "STRICT_MOUNTED": "attempt3_comparison", "TRUE_UNMOUNTED": None}),
        "MF37A03-02": ([_f(MANAGER_A3 / "INDEPENDENT_ADMISSION_SOURCE.json"),
                        _f(MANAGER_A3 / "INDEPENDENT_ADMISSION_INSTALLED.json"),
                        _f(before / "INDEPENDENT_ADMISSION_SOURCE.json"), _f(before / "INDEPENDENT_ADMISSION_INSTALLED.json")],
                       {"SOURCE_ADMISSION": "manager_a3_source", "INSTALLED_CONSUMER_C01": "manager_a3_installed"}),
        "MF37A03-03": ([_f(MANAGER_A3 / "INDEPENDENT_PIT_SOURCE.json"), _f(MANAGER_A3 / "INDEPENDENT_PIT_INSTALLED.json"),
                        _f(before / "INDEPENDENT_PIT_SOURCE.json"), _f(before / "INDEPENDENT_PIT_INSTALLED.json")],
                       {"SOURCE_ADMISSION": "manager_a3_source", "INSTALLED_CONSUMER_C01": "manager_a3_installed"}),
        "MF37A03-04": ([_f(MANAGER_A3 / "CAREER_SEMANTIC_COUNTEREXAMPLE.json"),
                        _f(MANAGER_A3 / "CAREER_SEMANTIC_REPRODUCTION.json"), _f(MANAGER_A3 / "career_challenge.py"),
                        _f(before / "CAREER_SEMANTIC_REPRODUCTION.json")],
                       {"CAREER_SUCCESSOR": "screens", "INSTALLED_CONSUMER_C01": "successor_named_cases"}),
        "MF37A03-05": ([_f(MANAGER_A3 / "CAREER_SEMANTIC_REPRODUCTION.json"),
                        _f(before / "CAREER_PARSER_INSTALLED.stdout.json")],
                       {"CAREER_SUCCESSOR": "successor_accounting", "INSTALLED_CONSUMER_C01": "successor_filtered_oracle"}),
    }
    carry = {row["id"]: row for row in ctx.contract["carryforward"]}
    findings = {f["id"]: f for f in new_findings(ctx)}
    rows = []
    for key, (before_files, lanes) in plan.items():
        requirement = next(r for r in ctx.contract["requirements"] if key in r["inherited_ids"])
        after = []
        for lane, detail_key in lanes.items():
            receipt = ctx.receipts.get(lane) or {}
            detail = (receipt.get("details") or {}).get(detail_key) if detail_key else None
            after.append({"lane": lane, "run": (ctx.runs.get(lane) or {}).get("run"), "result": receipt.get("result"),
                          "at_candidate_head": ctx.at_head(lane), "receipt_evidence_id": f"E-LANE-{lane}-RECEIPT",
                          "receipt_sha256": (ctx.runs.get(lane) or {}).get("receipt_sha256"),
                          "consumer_output": detail if detail is not None and len(json.dumps(detail, default=str)) < 8000
                          else ({"see_receipt_details_key": detail_key} if detail is not None else None)})
        rows.append({
            "finding": key, "requirement": requirement["id"], "original_meaning": carry[key]["original_meaning"],
            "worker_disposition": "REPAIRED_LOCAL_PENDING_MANAGER_REPLAY", "commits": ctx.finding_commits(key),
            "before_raw_proof": before_files, "after_raw_proof": after,
            "consumer": requirement["acceptance"][0]["consumer"],
            "criteria": {ac["id"]: criteria[ac["id"]]["status"] for ac in requirement["acceptance"]},
            "related_new_findings": sorted(fid for fid, f in findings.items() if key in (f.get("related_to") or [])),
        })
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "contract_sha256": ctx.contract_sha256, "candidate": ctx.candidate,
            "findings": rows,
            "not_claimed": "Each repair is local and pending the manager's independent replay; the worker closes no finding."}


def consumer_manifest(ctx: Context, label: str) -> dict[str, Any]:
    details = (ctx.receipts.get("INSTALLED_CONSUMER_C01") or {}).get("details") or {}
    manifest = base.consumer_manifest(ctx, label)
    manifest.pop("claim_successor", None)
    manifest.update({
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "explicit_career_successor": {
            "pointer": str(ctx.pointer_path), "pointer_sha256": sha256_file(ctx.pointer_path) if ctx.pointer_path.is_file() else None,
            "successor_file": ctx.pointer.get("successor_file"), "successor_sha256": ctx.pointer.get("successor_sha256"),
            "selection": "bas-staff-query --career-successor <file> --career-successor-sha256 <digest>; never a default",
            "cli_results": details.get("successor_cli_results"), "named_cases": details.get("successor_named_cases"),
            "pagination": details.get("successor_pagination"), "filtered_oracle": details.get("successor_filtered_oracle"),
            "coverage": details.get("successor_coverage"), "locators": details.get("successor_locators")},
        "manager_a3_installed": details.get("manager_a3_installed"),
        "manager_a3_career_challenge": details.get("manager_a3_career_challenge"),
        "claim_successor": {"path": str(C29_SUCCESSOR), "sha256": sha256_file(C29_SUCCESSOR),
                            "consumer": "tools/validate_cycle29_gates.py --claim-inventory-successor",
                            "lane": ctx.runs.get("CAREER_SUCCESSOR"),
                            "checks": ((ctx.receipts.get("CAREER_SUCCESSOR") or {}).get("details") or {}).get("claim_successor")},
        "default_routing": ("Without --career-successor the installed CLI answers from the delivered release's own "
                            "corrected table exactly as Attempt 3 delivered it; that default is not changed."),
        "not_claimed": ("No release, successor or restoration candidate is activated or published; the career "
                        "successor is private worker evidence, not accepted and not the default."),
    })
    return manifest


def platform_reconciliation(ctx: Context, label: str) -> dict[str, Any]:
    document = base.platform_reconciliation(ctx, label)
    document["cycle_number"], document["attempt_number"] = CYCLE_NUMBER, ATTEMPT_NUMBER
    document["label_note"] = ("Every Attempt 4 platform receipt carries the numeric label; the BEFORE reads were taken "
                              "after the first local repairs had begun, and their subject binds that exact head.")
    document["baseline"] = {"issued": ctx.contract["delivery_plan"]["outcome"]["baseline"]}
    owners = {o["id"]: o["remote_revision"] for o in ctx.contract["platform_plan"]["all22"]["owners"]}
    latest = ctx.latest_all22 or {}
    document["all22_owner_revisions"] = [
        {"repository": r["name"], "issued_remote_revision": owners.get(r["name"]), "observed_remote_head": r["remote_head"],
         "changed_since_issuance": owners.get(r["name"]) not in (None, r["remote_head"]),
         "local_head": r.get("local_head"), "local_dirty_entries": r.get("local_dirty_entries")}
        for r in latest.get("repositories") or []]
    return document


def successor_document(ctx: Context, label: str) -> dict[str, Any]:
    summary = ctx.build_summary()
    lane = (ctx.receipts.get("CAREER_SUCCESSOR") or {}).get("details") or {}
    installed = (ctx.receipts.get("INSTALLED_CONSUMER_C01") or {}).get("details") or {}
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "requirements": ["R37A04-04", "R37A04-05", "R37A04-06"],
            "findings": ["MF37A03-04", "MF37A03-05"], "candidate": ctx.candidate,
            "pointer": {"path": str(ctx.pointer_path), **ctx.pointer},
            "identity": (summary.get("successor") or {}).get("identity"),
            "episodes": (summary.get("successor") or {}).get("episodes"),
            "accounting": summary.get("accounting"), "parse": summary.get("parse"), "inputs": summary.get("inputs"),
            "predecessor": summary.get("predecessor"), "uncertainty_classes": summary.get("uncertainty_classes"),
            "role_bases": summary.get("role_bases"),
            "reproduction_at_candidate_head": lane.get("successor_reproduction"),
            "installed_serving": {k: installed.get(k) for k in ("successor_pagination", "successor_coverage",
                                                                "successor_named_cases")},
            "selection_rule": ("Selected only by naming the file (and its digest) on the installed CLI. The delivered "
                               "database keeps its bytes, default path and default answer; old identities are never "
                               "reused (C37A04:<pageid>:<revision>:<family>:<row>:<interval>)."),
            "not_claimed": summary.get("not_claimed")}


def population_document(ctx: Context, label: str) -> dict[str, Any]:
    summary = ctx.build_summary()
    screens = summary.get("screens") or {}
    rows_by_screen = summary.get("screen_rows") or {}
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "candidate": ctx.candidate,
            "population": {"predecessor_rows": (summary.get("accounting") or {}).get("predecessor_rows"),
                           "successor_episodes": (summary.get("accounting") or {}).get("successor_episodes"),
                           "pages": (summary.get("parse") or {}).get("pages")},
            "by_disposition": (summary.get("dispositions") or {}).get("by_disposition"),
            "by_screen": (summary.get("dispositions") or {}).get("by_screen"),
            "changed_field_counts": (summary.get("dispositions") or {}).get("changed_field_counts"),
            "complete_row_dispositions": {"file": (summary.get("dispositions") or {}).get("file"),
                                          "sha256": (summary.get("dispositions") or {}).get("file_sha256"),
                                          "also_in": "career_a04_disposition table of the successor file"},
            "screens": screens, "screen_rows": rows_by_screen,
            "census_reconciliation": summary.get("census_reconciliation"),
            "independently_discovered_classes": [f for f in new_findings(ctx) if f.get("class_of") == "CAREER_POPULATION"],
            "note": ("Every one of the predecessor rows has exactly one disposition in the named file; the three manager "
                     "screens are listed row by row here, each unchanged screened row with the source-grounded basis "
                     "for keeping its meaning.")}


def integration_packet(ctx: Context, label: str, lanes: list[dict[str, Any]]) -> str:
    text = base.integration_packet(ctx, label, lanes)
    github = ctx.latest_github or {}
    main_head = github.get("main_head")
    ahead = git_out("rev-list", "--count", f"{main_head}..{ctx.candidate['head']}") if main_head else None
    behind = git_out("rev-list", "--count", f"{ctx.candidate['head']}..{main_head}") if main_head else None
    files = git_out("diff", "--name-only", f"{main_head}...{ctx.candidate['head']}").splitlines() if main_head else []
    tags = collections.Counter(re.match(r"^\[(\w+)\]", s).group(1) if re.match(r"^\[(\w+)\]", s) else "untagged"
                               for _, s in ctx.commits)
    extra = [
        "### Candidate against main", "",
        f"Main `{main_head}`: the candidate is {ahead} commits ahead and {behind} behind (merge base "
        f"`{git_out('merge-base', str(main_head), ctx.candidate['head']) if main_head else None}`), {len(files)} files "
        "differ. This attempt adds only the commits listed above to the preserved Attempt 3 candidate.", "",
        "### Sequential squash versus one consolidated review (comparison, nothing executed)", "",
        "- *Sequential stack*: the 13 open PRs would each need rebase onto its squashed parent, fresh checks, eligible "
        "approvals and dispositions of their review threads, in dependency order; every squash changes the next base, "
        "so re-review repeats per step. No merge is currently eligible (review decisions and rollups above).",
        "- *One consolidated candidate*: this branch carries the stack plus the Cycle 37 repairs as one coherent, "
        "locally qualified subject. It needs one publication grant and one review, but a large diff; the thread "
        "dispositions above still have to be answered.",
        "- Recommendation: keep the single candidate, qualified locally, and decide publication after independent "
        "manager review. Neither path is executed here.", "",
        "### Commit-classification correction mechanism", "",
        f"Commits after the issued base by subject tag: {dict(tags)}. A subject that was mis-tagged is never "
        "rewritten (no history rewrite is granted). The supported correction is an appended record: a "
        "`[process]` commit whose message names the earlier commit's SHA and its corrected class, or, at "
        "integration, the squash message's classification. Integration tooling reads the latest such record for a "
        "SHA; the original commit stays byte-identical.", "",
        "### Trusted controls and dependency policy (owner decisions, none taken)", "",
        "- The protected review workflows and rules (`.github/workflows/*scientific-review.yml`, "
        "`.github/CODE_REVIEW_RULES.md`, the review prompt, schema and validator) are denied write roots here and were "
        "not changed; whether paid or external reviewers gate integration is an owner decision (none invoked).",
        "- Runtime dependencies are unchanged by this attempt; the numpy 1.26 to 2.x and CPython 3.12 float drifts behind "
        "inherited red identities need an owner re-bind decision (see the unfinished items).",
        "- The released C01 0.1.2 wheel is composed as released; adopting a newer owner revision is an owner decision.",
        ""]
    return text + "\n".join(extra) + "\n"


def cost_ledger(ctx: Context, label: str) -> dict[str, Any]:
    document = base.cost_ledger(ctx, label)
    document["cycle_number"], document["attempt_number"] = CYCLE_NUMBER, ATTEMPT_NUMBER
    return document


# ------------------------------------------------------------------ build


def build(ctx: Context, headline: str, writer_released: bool) -> dict[str, Any]:
    register_evidence(ctx)
    root = ctx.out_root
    lanes = lane_rows(ctx)
    ctx.original_lanes = original_lane_dispositions(ctx)
    ctx.attempt3_lanes = attempt3_lane_dispositions(ctx)
    obligations_path = root / "ORIGINAL_OBLIGATION_DISPOSITIONS.json"
    label = f"{LABEL_PREFIX} {headline}"

    def write_obligations(states: dict[str, dict[str, Any]]) -> None:
        items = []
        for row in ctx.contract["carryforward"]:
            item = {"id": row["id"], "category": carry_category(row["id"]),
                    **{k: row[k] for k in ("original_meaning", "disposition", "source_ids", "requirement_ids",
                                           "acceptance_ids", "owner", "reason", "next_action", "prior_mapping")}}
            if row["id"] in states:
                item["attempt4_state"] = states[row["id"]]["attempt4_state"]
                item["attempt4_evidence_ids"] = [e for e in states[row["id"]]["evidence_ids"] if e != "E-ORIGINAL-OBLIGATIONS"]
            items.append(item)
        ctx.carry_counts = {"composition": dict(collections.Counter(i["category"] for i in items)),
                            "dispositions": dict(collections.Counter(i["disposition"] for i in items))}
        ctx.obligation_items = items
        write_output(obligations_path, dumps({
            "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "contract_sha256": ctx.contract_sha256, "candidate": ctx.candidate,
            **ctx.carry_counts, "items": items, "original_lanes": ctx.original_lanes,
            "attempt3_lanes": ctx.attempt3_lanes,
            "note": ("Original meanings, sources, owners, reasons, next actions, prior mappings and dispositions are "
                     "copied from the issued contract unchanged. OWNED_BACKLOG items stay owned; none is marked "
                     "fulfilled by this accounting.")}))
        ctx.add("E-ORIGINAL-OBLIGATIONS", obligations_path, CENSUS,
                "All 651 carryforward identities with their original meanings and unchanged dispositions")

    write_obligations({})
    write_output(root / "LANE_RESULTS.json", dumps({
        "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "candidate": ctx.candidate,
        "runner": "tools/cycle37/attempt04_lanes.py", "runs_index": str(root / "lanes" / "RUNS.jsonl"),
        "lanes": lanes, "original_lanes": ctx.original_lanes, "attempt3_lanes": ctx.attempt3_lanes}))
    ctx.add("E-OUTPUT-LANE_RESULTS.json", root / "LANE_RESULTS.json", CENSUS,
            "Every required lane's result at the candidate head, the 22 original and 13 Attempt 3 lane dispositions")
    for name, builder in (("CAREER_CORRECTION_SUCCESSOR.json", successor_document),
                          ("CAREER_POPULATION_DISPOSITIONS.json", population_document)):
        write_output(root / name, dumps(builder(ctx, label)))
        ctx.add(f"E-OUTPUT-{name}", root / name, CENSUS, f"Declared worker output {name}")
    criteria = criterion_results(ctx)
    by_id = {row["id"]: row for row in criteria}
    carry = carryforward_rows(ctx, by_id)
    write_obligations({row["id"]: row for row in carry})
    carry = carryforward_rows(ctx, by_id)
    findings = new_findings(ctx)
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
    # The v2.4.0 aggregate exactly: the manager lane is a lane, so software validation cannot read PASS before it.
    software = ("FAIL" if any(l["status"] == "FAIL" for l in lanes) else
                "PASS" if all(l["status"] == "PASS" for l in lanes) else
                "NOT_RUN" if not any(l["executed"] or l["status"] == "PASS" for l in lanes) else "PARTIAL")
    summary = ctx.build_summary()
    installed = (ctx.receipts.get("INSTALLED_CONSUMER_C01") or {}).get("details") or {}
    pagination = installed.get("successor_pagination") or {}
    if ctx.lane_ok("INSTALLED_CONSUMER_C01") and ctx.lane_ok("CAREER_SUCCESSOR"):
        by = (summary.get("dispositions") or {}).get("by_disposition") or {}
        data_evidence = (f"DELIVERED_RELEASE_{DB_SHA256[:12]}_UNCHANGED; EXPLICIT_CAREER_SUCCESSOR_"
                         f"{str(ctx.pointer.get('successor_sha256'))[:12]}_ROWS_{pagination.get('distinct')}; "
                         f"PREDECESSOR_ROWS_DISPOSITIONED_{(summary.get('accounting') or {}).get('dispositions')}"
                         f"({', '.join(f'{k} {v}' for k, v in sorted(by.items()))}); REAL_ELIGIBLE_FORECASTS_0; "
                         "REAL_PROVEN_PIT_0; NOT_ACTIVATED")
    else:
        data_evidence = "INCOMPLETE"
    submission = {
        "schema_version": "BAS-SUBMISSION-2.4", "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "cycle_id": CYCLE_ID, "attempt_id": ATTEMPT_ID, "display_label": label,
        "contract_sha256": ctx.contract_sha256, "headline": headline, "candidate": ctx.candidate,
        "writer_released": writer_released, "safe_local_work_remaining": headline == "IN_PROGRESS_LOCAL_WORK_REMAINS",
        "dimensions": {"implementation": "COMPLETE_LOCAL" if complete else "IN_PROGRESS",
                       "data_evidence": data_evidence, "software_validation": software,
                       "independent_acceptance": "PENDING_MANAGER_REVIEW", "integration_release": "NOT_AUTHORIZED",
                       "overall_cycle": headline},
        "predictive_skill": "NOT_ESTABLISHED", "criteria": criteria,
        "carryforward": [{"id": r["id"], "disposition": r["disposition"], "evidence_ids": r["evidence_ids"]} for r in carry],
        "lanes": lanes, "evidence": [], "unfinished": unfinished, "new_findings": findings,
        "effects": base.effects(ctx), "costs": base.costs(ctx), "platform_receipts": base.platform_receipts(ctx, by_id),
        "handoff_artifacts": [], "observed_at": utc_now(),
    }
    outputs = {
        "FINDING_CLOSURE_MATRIX.json": dumps(finding_matrix(ctx, label, by_id)),
        "DELIVERED_CONSUMER_MANIFEST.json": dumps(consumer_manifest(ctx, label)),
        "PLATFORM_RECONCILIATION.json": dumps(platform_reconciliation(ctx, label)),
        "COST_AND_AUTHORITY_LEDGER.json": dumps(cost_ledger(ctx, label)),
        "INHERITED_LANE_EQUIVALENCE.json": dumps(inherited_equivalence(ctx, label)),
        "INTEGRATION_DECISION_PACKET.md": integration_packet(ctx, label, lanes),
    }
    for name, text in outputs.items():
        write_output(root / name, text)
        ctx.add(f"E-OUTPUT-{name}", root / name, CENSUS, f"Declared worker output {name}")
    executed = [lane for lane in WORKER_LANES if ctx.executed(lane)]
    ctx.all_runs_clean = bool(executed) and all(
        ctx.receipts[lane]["source_binding"].get("clean") and ctx.receipts[lane]["source_binding_after"].get("clean")
        for lane in executed)
    import attempt04_report  # the narrative report, beside this tool

    write_output(root / "WORKER_REPORT.md", attempt04_report.render(ctx, submission))
    return submission


def seal(ctx: Context, submission: dict[str, Any]) -> None:
    base.seal(ctx, submission)


# ------------------------------------------------------------------ check


OUTPUT_NAMES = ("LANE_RESULTS.json", "FINDING_CLOSURE_MATRIX.json", "DELIVERED_CONSUMER_MANIFEST.json",
                "PLATFORM_RECONCILIATION.json", "COST_AND_AUTHORITY_LEDGER.json", "CAREER_CORRECTION_SUCCESSOR.json",
                "CAREER_POPULATION_DISPOSITIONS.json", "INHERITED_LANE_EQUIVALENCE.json",
                "INTEGRATION_DECISION_PACKET.md", "ORIGINAL_OBLIGATION_DISPOSITIONS.json", "WORKER_REPORT.md")


def check(ctx: Context, final_packet: bool) -> list[str]:
    problems = accounting_problems(ctx) + base.classification_problems(ctx)
    for name in OUTPUT_NAMES:
        path = ctx.out_root / name
        if not path.is_file():
            problems.append(f"{name} is missing")
            continue
        first = path.read_text(encoding="utf-8").splitlines()[:2]
        if not any(LABEL_PREFIX in line for line in first):
            problems.append(f"{name} does not begin with the numeric identity label")
    lanes_doc = ctx.out_root / "LANE_RESULTS.json"
    if lanes_doc.is_file():
        document = read_json(lanes_doc)
        if {row["id"] for row in document["lanes"]} != set(ctx.lanes):
            problems.append("LANE_RESULTS lane set differs from the contract's")
        for key, prefix in (("original_lanes", "ORIGINAL-LANE-"), ("attempt3_lanes", "A03-LANE-")):
            have = {row["id"] for row in document.get(key) or []}
            wanted = {row["id"] for row in ctx.contract["carryforward"] if row["id"].startswith(prefix)}
            if have != wanted:
                problems.append(f"LANE_RESULTS {key} differ: {sorted(have ^ wanted)}")
        if document["candidate"] != ctx.candidate:
            problems.append("LANE_RESULTS was built for another subject")
    matrix = ctx.out_root / "FINDING_CLOSURE_MATRIX.json"
    if matrix.is_file():
        rows = read_json(matrix)["findings"]
        if {row["finding"] for row in rows} != set(FINDING_IDS):
            problems.append("FINDING_CLOSURE_MATRIX does not cover exactly MF37A03-01..05")
        for row in rows:
            if not row["commits"]:
                problems.append(f"{row['finding']} names no commit")
    if not ctx.pointer:
        problems.append("the delivered career successor pointer is missing")
    elif sha256_file(Path(ctx.pointer["successor_file"])) != ctx.pointer.get("successor_sha256"):
        problems.append("the delivered career successor does not match its pointer digest")
    for lane, row in base.ledger_totals(ctx).items():
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
    rebind()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=("classify", "build", "check", "seal"))
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--headline", default="IN_PROGRESS_LOCAL_WORK_REMAINS", choices=HEADLINES)
    parser.add_argument("--writer-released", action="store_true")
    parser.add_argument("--final-packet", action="store_true")
    args = parser.parse_args(argv)
    ctx = Context(args.contract.resolve(), args.out_root.resolve())
    if args.mode == "classify":
        document = classify(ctx)
        print(json.dumps({lane: [(g["id"], len(g["identities"])) for g in row["groups"]]
                          for lane, row in document["lanes"].items()}, indent=2))
        return 0
    if args.mode == "check":
        problems = check(ctx, args.final_packet)
        print(json.dumps({"label": f"{LABEL_PREFIX} accounting check", "result": "PASS" if not problems else "FAIL",
                          "problems": problems, "candidate": ctx.candidate}, indent=2, ensure_ascii=False))
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
    raise SystemExit(main())
