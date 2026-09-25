r"""Cycle #37 — Attempt #5 — worker outputs, submission and accounting check (R37A05-07).

    attempt05_outputs.py classify --contract C --out-root R
    attempt05_outputs.py build --contract C --out-root R [--headline H --writer-released]
    attempt05_outputs.py check --contract C --out-root R [--final-packet]
    attempt05_outputs.py seal --contract C --out-root R

The Attempt 4 accounting (``attempt04_outputs``, over the Attempt 3 base) rebound to the Attempt 5 contract.
``build`` writes the declared worker outputs from what is there: the issued contract, the lane receipts named in
``lanes/RUNS.jsonl``, the platform receipts and request ledger, the storage ledger, the delivered career successor
(by its pointer and digest), the integration candidate (by Git and its creation record), git, and worker-authored
evidence it reads but never invents: ``evidence/INHERITED_FAILURE_CLASSIFICATION.json`` and
``evidence/NEW_FINDINGS_ATTEMPT5.json``.

``classify`` derives the Attempt 5 classification of a red mounted lane from the Attempt 4 one: an identity that
persists with the same cause keeps its Attempt 4 group; a new identity, or one whose cause changed, is refused and
must be classified by hand. ``check`` fails on any gap. The default headline is IN_PROGRESS_LOCAL_WORK_REMAINS; a
terminal headline must be asked for with ``--writer-released`` and is refused while local work remains. This tool
never accepts anything.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt03_outputs as base  # noqa: E402  (the preserved Attempt 3 accounting)
import attempt04_outputs as a4o  # noqa: E402  (the preserved Attempt 4 accounting)
import attempt05_candidate as candidate  # noqa: E402
from attempt03_outputs import (  # noqa: E402
    CENSUS,
    RAW,
    dumps,
    git_out,
    read_json,
    sha256_file,
    utc_now,
    write_output,
)

CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID, ATTEMPT_ID = 37, 5, "CYCLE-37", "ATTEMPT-05-20260925"
BASE_SHA = "cfdc588c0d580e80615374e3e05edd1b6b4c3bc7"
BRANCH = "codex/BAT-706-cycle37-rework"
DATA = Path(r"C:\BatteredAggieSyndrome.data")
ATTEMPT4_ROOT = DATA / "ops" / "cycle37" / "attempt04"
MANAGER_A4 = DATA / "ops" / "manager_reviews" / "cycle37" / "attempt04" / "review-20260925T025537Z"
DB_SHA256 = base.DB_SHA256
C01_SHA256 = base.C01_SHA256
HEADLINES = base.HEADLINES
WORKER_LANES = ("START_CONTEXT", "WRITE_PROTECTION", "STORAGE_ADMISSION", "SOURCE_ADMISSION", "SOURCE_HARNESS",
                "SOURCE_REGRESSIONS", "CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01", "LOCAL_INTEGRATION_CANDIDATE",
                "TRUE_UNMOUNTED", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED", "PLATFORM_CARRY", "FINAL_PACKET")
FINDING_IDS = ("MF37A04-01", "MF37A04-02", "MF37A04-03", "MF37A04-04", "MF37A04-05")
REQUIREMENT_LANES = {
    "R37A05-01": ("WRITE_PROTECTION", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED", "TRUE_UNMOUNTED"),
    "R37A05-02": ("CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01"),
    "R37A05-03": ("CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01"),
    "R37A05-04": ("CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01"),
    "R37A05-05": ("STORAGE_ADMISSION",),
    "R37A05-06": ("CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01", "SOURCE_ADMISSION", "SOURCE_REGRESSIONS"),
    "R37A05-07": WORKER_LANES,
}
#: The Attempt 4 lanes and the Attempt 5 lanes that carry each obligation now.
A04_LANES = {lane: (lane,) for lane in ("START_CONTEXT", "WRITE_PROTECTION", "SOURCE_ADMISSION", "SOURCE_HARNESS",
                                        "SOURCE_REGRESSIONS", "INSTALLED_CONSUMER_C01", "CAREER_SUCCESSOR",
                                        "FULL_FINAL_MOUNTED", "STRICT_MOUNTED", "TRUE_UNMOUNTED", "PLATFORM_CARRY",
                                        "FINAL_PACKET")} | {"MANAGER_REVIEW": ()}
CARRY_COMPOSITION = {"ORIGINAL_CRITERION": 345, "ORIGINAL_OBLIGATION": 148, "ORIGINAL_LANE": 22, "WORKER_FINDING": 73,
                     "MANAGER_FINDING": 15, "ATTEMPT3_CRITERION": 28, "ATTEMPT3_LANE": 13,
                     "ATTEMPT3_WORKER_FINDING": 12, "ATTEMPT4_CRITERION": 28, "ATTEMPT4_LANE": 13,
                     "ATTEMPT4_WORKER_FINDING": 15}
LABEL_PREFIX = "Cycle #37 \u2014 Attempt #5 \u2014"
OUTPUT_NAMES = ("LANE_RESULTS.json", "FINDING_CLOSURE_MATRIX.json", "DELIVERED_CONSUMER_MANIFEST.json",
                "PLATFORM_RECONCILIATION.json", "COST_AND_AUTHORITY_LEDGER.json", "CAREER_CORRECTION_SUCCESSOR.json",
                "CAREER_POPULATION_DISPOSITIONS.json", "INHERITED_LANE_EQUIVALENCE.json",
                "LOCAL_INTEGRATION_CANDIDATE.json", "INTEGRATION_DECISION_PACKET.md",
                "ORIGINAL_OBLIGATION_DISPOSITIONS.json", "WORKER_REPORT.md")


def rebind() -> None:
    """Point the Attempt 3 accounting at the Attempt 5 identity. The Attempt 4 helpers reused here keep their own
    base, which is how they find the Attempt 3 final lane receipts."""

    base.CYCLE_NUMBER, base.ATTEMPT_NUMBER, base.CYCLE_ID, base.ATTEMPT_ID = (CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID,
                                                                              ATTEMPT_ID)
    base.BASE_SHA = BASE_SHA
    base.BRANCH = BRANCH
    base.WORKER_LANES = WORKER_LANES
    a4o.LABEL_PREFIX = LABEL_PREFIX


def carry_category(key: str) -> str:
    for prefix, name in (("ORIGINAL-AC-", "ORIGINAL_CRITERION"), ("ORIGINAL-OBL-", "ORIGINAL_OBLIGATION"),
                         ("ORIGINAL-LANE-", "ORIGINAL_LANE"), ("A03-AC-", "ATTEMPT3_CRITERION"),
                         ("A03-LANE-", "ATTEMPT3_LANE"), ("A03-WORKER-", "ATTEMPT3_WORKER_FINDING"),
                         ("A04-AC-", "ATTEMPT4_CRITERION"), ("A04-LANE-", "ATTEMPT4_LANE"),
                         ("A04-WORKER-", "ATTEMPT4_WORKER_FINDING"), ("WORKER-", "WORKER_FINDING")):
        if key.startswith(prefix):
            return name
    return "MANAGER_FINDING"


class Context(base.Context):
    def __init__(self, contract_path: Path, out_root: Path) -> None:
        super().__init__(contract_path, out_root)
        self.pointer_path = out_root / "release" / "CAREER_SUCCESSOR_POINTER.json"
        self.pointer = read_json(self.pointer_path) if self.pointer_path.is_file() else {}
        self.findings_path = out_root / "evidence" / "NEW_FINDINGS_ATTEMPT5.json"
        self.ledger_path = out_root / "STORAGE_RESERVATIONS.jsonl"
        records = sorted((out_root / "evidence" / "integration").glob("CANDIDATE_RECORD_*.json"))
        self.candidate_record_path = records[-1] if records else None
        self.attempt3_lanes: list[dict[str, Any]] = []
        self.attempt4_lanes: list[dict[str, Any]] = []

    def build_summary(self) -> dict[str, Any]:
        path = Path(self.pointer.get("build_summary", "")) if self.pointer else None
        return read_json(path) if path and path.is_file() else {}

    def finding_commits(self, finding: str) -> list[dict[str, str]]:
        return [{"sha": sha, "subject": subject} for sha, subject in reversed(self.commits)
                if re.search(rf"\b{re.escape(finding)}\b", subject)]

    def details(self, lane: str) -> dict[str, Any]:
        return (self.receipts.get(lane) or {}).get("details") or {}


# ------------------------------------------------------------------ evidence


def register_evidence(ctx: Context) -> None:
    base.register_evidence(ctx)
    root = ctx.out_root
    for identity, path, kind, scope in (
            ("E-NEW-FINDINGS", ctx.findings_path, CENSUS,
             "Findings discovered in Attempt 5, with severity, disposition, owner and next action"),
            ("E-BEFORE-REPRODUCTION", root / "evidence" / "before" / "BEFORE_REPRODUCTION.json", RAW,
             "Before-repair reproduction of MF37A04-01..05 at the issued base with the manager's own probes"),
            ("E-BEFORE-MF05-V2", root / "evidence" / "before_mf05_v2" / "BEFORE_MF05_RERUN.json", RAW,
             "MF37A04-05 before-repair reading with the corrected detector (the first result retained)"),
            ("E-SUCCESSOR-POINTER", ctx.pointer_path, CENSUS,
             "The delivered explicit career successor: file, digests, predecessor and Attempt 4 digests, build summary"),
            ("E-STORAGE-LEDGER", ctx.ledger_path, CENSUS,
             "The attempt's cumulative, hash-chained storage ledger: every reservation, reconciliation and refusal")):
        if Path(path).is_file():
            ctx.add(identity, path, kind, scope)
    if ctx.candidate_record_path:
        ctx.add("E-CANDIDATE-RECORD", ctx.candidate_record_path, RAW,
                "The creation record of the local integration candidate: commit, tree, refs changed, skip-worktree")
    for path in sorted((root / "evidence" / "storage").glob("*.json")):
        ctx.add(f"E-STORAGE-{path.name}", path, CENSUS,
                "Exact inventory of the directories this attempt created, their bytes and cleanup candidates")
    for folder in ("before", "before_mf05_v2"):
        for path in sorted((root / "evidence" / folder).rglob("*")):
            if path.is_file() and path.suffix in (".json", ".log", ".py", ".gz") and path.name not in (
                    "BEFORE_REPRODUCTION.json", "BEFORE_MF05_RERUN.json"):
                relative = path.relative_to(root / "evidence").as_posix()
                ctx.add(f"E-{relative}", path, RAW, f"Before-repair reproduction file {relative}")
    release = root / "release"
    for path in sorted(release.rglob("*")):
        if path.is_file() and path.suffix in (".json", ".gz") and path != ctx.pointer_path:
            ctx.add(f"E-RELEASE-{path.relative_to(release).as_posix()}", path, CENSUS,
                    f"Delivered career successor or census file {path.name}")


# ------------------------------------------------------------------ lanes


def original_lane_dispositions(ctx: Context) -> list[dict[str, Any]]:
    rows = []
    for row in a4o.original_lane_dispositions(ctx):
        row = dict(row)
        if row.get("disposition") == "CARRIED_BY_ATTEMPT4_LANE_AT_THE_CANDIDATE_HEAD":
            row["disposition"] = "CARRIED_BY_ATTEMPT5_LANE_AT_THE_CANDIDATE_HEAD"
            row["attempt5_lanes"] = row.pop("attempt4_lanes")
            row["attempt5_results"] = row.pop("attempt4_results")
            row["justification"] = ("Re-executed by the named Attempt 5 lane(s) at the candidate head; the Attempt 2 "
                                    "receipt stays unchanged as the before-record.")
        rows.append(row)
    return rows


def attempt3_lane_dispositions(ctx: Context) -> list[dict[str, Any]]:
    rows = []
    for row in a4o.attempt3_lane_dispositions(ctx):
        row = dict(row)
        if row.get("disposition") == "CARRIED_BY_ATTEMPT4_LANE_AT_THE_CANDIDATE_HEAD":
            row["disposition"] = "CARRIED_BY_ATTEMPT5_LANE_AT_THE_CANDIDATE_HEAD"
            row["attempt5_lanes"] = row.pop("attempt4_lanes")
            row["attempt5_results"] = row.pop("attempt4_results")
        rows.append(row)
    return rows


def _a04_final(lane: str) -> dict[str, Any]:
    index = ATTEMPT4_ROOT / "lanes" / "RUNS.jsonl"
    rows = [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [row for row in rows if row["lane"] == lane and row["head"] == BASE_SHA]
    return rows[-1] if rows else {}


def attempt4_lane_dispositions(ctx: Context) -> list[dict[str, Any]]:
    rows = []
    for lane, successors in A04_LANES.items():
        final = _a04_final(lane)
        row: dict[str, Any] = {"id": f"A04-LANE-{lane}", "attempt4_lane": lane, "attempt4_run": final.get("run"),
                               "attempt4_result": final.get("result"), "attempt4_head": final.get("head"),
                               "attempt4_receipt": final.get("receipt"),
                               "attempt4_receipt_sha256": final.get("receipt_sha256"),
                               "attempt4_receipt_preserved": bool(final.get("receipt")) and Path(final["receipt"]).is_file()}
        if not successors:
            row.update(disposition="MANAGER_OWNED", justification="The Attempt 4 manager lane is the manager's.")
        else:
            row.update(disposition="CARRIED_BY_ATTEMPT5_LANE_AT_THE_CANDIDATE_HEAD", attempt5_lanes=list(successors),
                       attempt5_results={s: (ctx.receipts[s]["result"] if ctx.at_head(s) else "NOT_AT_HEAD")
                                         for s in successors if s in ctx.receipts},
                       justification="Re-executed by the same-named Attempt 5 lane at the candidate head.")
        rows.append(row)
    return rows


# ------------------------------------------------------------------ inherited red lanes


def classify(ctx: Context) -> dict[str, Any]:
    """Derive the Attempt 5 classification from Attempt 4's, identity by identity and cause by cause."""

    previous_path = ATTEMPT4_ROOT / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json"
    previous = read_json(previous_path)
    lanes: dict[str, Any] = {}
    problems: list[str] = []
    for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED"):
        receipt = ctx.receipts.get(lane)
        if not receipt or receipt["result"] != "FAIL" or not ctx.at_head(lane):
            continue
        failing = base.failing_identities(receipt) or []
        comparison = (receipt.get("details") or {}).get("attempt4_comparison") or {}
        changed = set(comparison.get("persisting_changed_cause") or {})
        a4_groups = (previous["lanes"].get(lane) or {}).get("groups") or []
        group_of = {identity: group for group in a4_groups for identity in group.get("identities") or []}
        groups: dict[str, dict[str, Any]] = {}
        for identity in failing:
            group = group_of.get(identity)
            if group is None or identity in changed:
                problems.append(f"{lane}: {identity} is new or changed cause; classify it by hand")
                continue
            entry = groups.setdefault(group["id"], {k: v for k, v in group.items() if k != "identities"} | {"identities": []})
            entry["identities"].append(identity)
        lanes[lane] = {"run": ctx.runs[lane]["run"], "head": ctx.runs[lane]["head"],
                       "attempt4_run": (previous["lanes"].get(lane) or {}).get("run"), "groups": list(groups.values()),
                       "equivalence": {"persisting": len(comparison.get("persisting") or []),
                                       "persisting_same_cause": len(comparison.get("persisting_same_cause") or []),
                                       "new_in_attempt5": comparison.get("new_in_attempt5"),
                                       "no_longer_failing": comparison.get("no_longer_failing") or
                                       comparison.get("no_longer_reported")}}
    if problems:
        raise SystemExit("classification refused:\n" + "\n".join(problems))
    document = {"label": f"{LABEL_PREFIX} IN_PROGRESS_LOCAL_WORK_REMAINS (inherited failure classification)",
                "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
                "attempt_id": ATTEMPT_ID, "authored_at": utc_now(),
                "rule": ("Each failing identity keeps its Attempt 4 group only when it persists with the same traceback "
                         "cause (FULL_FINAL_MOUNTED) or the same finding line (STRICT_MOUNTED); anything else is refused "
                         "for manual classification."),
                "derived_from": {"path": str(previous_path), "sha256": sha256_file(previous_path)}, "lanes": lanes}
    write_output(ctx.out_root / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json", dumps(document))
    return document


def inherited_equivalence(ctx: Context, label: str) -> dict[str, Any]:
    rows = []
    for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED", "TRUE_UNMOUNTED"):
        receipt = ctx.receipts.get(lane) or {}
        details = receipt.get("details") or {}
        rows.append({"lane": lane, "run": (ctx.runs.get(lane) or {}).get("run"), "result": receipt.get("result"),
                     "at_candidate_head": ctx.at_head(lane), "counts": receipt.get("counts"),
                     "attempt4_comparison": details.get("attempt4_comparison"),
                     "attempt2_comparison": {k: v for k, v in (details.get("baseline_comparison") or {}).items()
                                             if k not in ("final_failed_or_errored",)},
                     "failing_identities": base.failing_identities(receipt) if receipt else None})
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "candidate": ctx.candidate, "inherited_red": rows,
            "classification": ctx.classification, "original_lanes": ctx.original_lanes,
            "attempt3_lanes": ctx.attempt3_lanes, "attempt4_lanes": ctx.attempt4_lanes,
            "rule": ("Inherited red lanes stay red until genuinely resolved. Equivalence is by exact identity and cause "
                     "against the Attempt 4 final receipts at the issued base; counts alone establish nothing.")}


# ------------------------------------------------------------------ criteria


def _holds(ctx: Context, lane: str, key: str) -> bool:
    return bool((ctx.details(lane).get(key) or {}).get("holds"))


def judge(ctx: Context, key: str, requirement: str) -> tuple[str, str]:
    needed = REQUIREMENT_LANES[requirement]
    if requirement == "R37A05-01":
        lanes = [lane for lane in WORKER_LANES if ctx.executed(lane)]
        writes = sum(ctx.receipts[lane]["write_and_network_scope"]["measurement"]["writes_outside_owned_roots"]
                     for lane in lanes)
        mounted = all(ctx.executed(lane) for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED", "TRUE_UNMOUNTED"))
        challenge = _holds(ctx, "WRITE_PROTECTION", "manager_a4_git_option_challenge_v2")
        scratch = _holds(ctx, "WRITE_PROTECTION", "live_scratch_control")
        if ctx.lane_ok("WRITE_PROTECTION") and challenge and scratch and mounted and writes == 0:
            return "VERIFIED_LOCAL", ("The typed Git grammar suite, the Attempt 2 and 3 manager probes and the manager's "
                                      "Attempt 4 GIT_OPTION_CHALLENGE_V2 hold at the candidate head: the attached and "
                                      "abbreviated -f writes are refused before any effect and the protected fixture "
                                      "keeps its bytes; a guarded Git write with no declared scratch root is refused "
                                      "live. The mounted lanes ran only after that qualification, and across "
                                      f"{len(lanes)} executed lane runs the data root and All-22 measured zero writes "
                                      "outside the owned roots. This is a Python-process guard, not OS isolation.")
        return "IN_PROGRESS", (f"WRITE_PROTECTION held={ctx.lane_ok('WRITE_PROTECTION')}, manager challenge={challenge}, "
                               f"scratch control={scratch}, mounted executed={mounted}, writes outside={writes}")
    if requirement == "R37A05-05":
        storage = ctx.details("STORAGE_ADMISSION").get("storage_ledger") or {}
        live = (storage.get("live_over_budget_control") or {}).get("refused")
        if ctx.lane_ok("STORAGE_ADMISSION") and live:
            return "VERIFIED_LOCAL", ("The storage suite (admitted, too large, cumulative, concurrent, free reserve, "
                                      "underestimate, bounded stop, restart, orphan/explicit holders, broken chain, no "
                                      "deletion) passes; the attempt's own hash-chained ledger refused a live over-budget "
                                      "reservation before any effect; every lane run reserved before it ran and "
                                      "reconciled after it. W37A04-15 remains an observed Attempt 4 breach.")
        return "IN_PROGRESS", f"STORAGE_ADMISSION held={ctx.lane_ok('STORAGE_ADMISSION')}, live refusal={live}"
    if requirement in ("R37A05-02", "R37A05-03", "R37A05-04", "R37A05-06"):
        if not all(ctx.lane_ok(lane) for lane in needed):
            return "IN_PROGRESS", "not all of " + ", ".join(needed) + " held at the candidate head"
        installed = ctx.details("INSTALLED_CONSUMER_C01")
        named = (installed.get("successor_named_cases") or {}).get("holds") or {}
        extra = {"R37A05-02": ("manager_a4_successor_challenge",),
                 "R37A05-03": ("manager_a4_career_semantic_census",),
                 "R37A05-04": ("manager_a4_career_semantic_census",), "R37A05-06": ()}[requirement]
        failing = [name for name in extra if not _holds(ctx, "INSTALLED_CONSUMER_C01", name)]
        if requirement == "R37A05-02":
            cases = (installed.get("lineage_fixtures") or {}).get("cases") or {}
            failing += [f"fixture {k}" for k, v in cases.items() if not v.get("refused_for_the_intended_cause")]
            if not cases:
                failing.append("no lineage fixtures")
        if requirement == "R37A05-03":
            failing += [k for k in ("cory_2018_eagles_2015_2019", "cory_nested_keeps_its_own_dates",
                                    "danny_nested_keeps_1998", "steve_wilks_inheritance_names_its_parent",
                                    "brookshier_range_read") if not named.get(k)]
        if requirement == "R37A05-04":
            failing += [k for k in ("defensive_pgc_is_defense",) if not named.get(k)]
        if failing:
            return "IN_PROGRESS", "the lanes passed but these checks do not hold: " + ", ".join(failing)
        text = {"R37A05-02": ("The consumer proves lineage from the rows: resealed missing, extra, dangling, "
                              "nonreciprocal, duplicate, unmapped and invalid-identity successors, and absent, removed "
                              "or tampered raw evidence, are each refused for their own cause through the installed "
                              "CLI; the manager's Attempt 4 resealed challenge is refused; the genuine Attempt 5 "
                              "successor (72,070 predecessor and 73,082 Attempt 4 rows dispositioned) and the Attempt 4 "
                              "format still serve; no absent evidence is labelled verified."),
                "R37A05-03": ("Season templates keep both endpoints, to present or an open end, and unsupported forms "
                              "stay explicitly unresolved; nested and dated role lines keep their own dates and an "
                              "inherited date names its parent; every one of the 2,257 template-screen rows is "
                              "dispositioned and read as its template states; installed season queries (Cory Undlin "
                              "2018 Eagles 2015-2019) match the independent oracle."),
                "R37A05-04": ("A side-dependent role takes its unit only from its own words: all 33 defensive "
                              "passing-game rows are DEFENSE through source and the installed package; the manager's "
                              "semantic census finds no mislabel; unit changes across the population and 2,223 "
                              "affected delivered staff rows are recorded; no play-calling authority is inferred."),
                "R37A05-06": ("All 72,070 predecessor and 73,082 Attempt 4 rows carry exactly one disposition; the "
                              "rebuild from the committed subject is byte-identical; the independent template census "
                              "and the Attempt 4 raw census reconcile with every gap grounded; the fresh installed CLI "
                              "paginates the successor completely against an independent SQL oracle; admission, "
                              "routing, harness and the Cycle 29 successor are preserved.")}[requirement]
        return "VERIFIED_LOCAL", text
    # R37A05-07
    if key.endswith("-A"):
        missing = [lane for lane in WORKER_LANES if not ctx.executed(lane)]
        if not missing:
            return "VERIFIED_LOCAL", ("Every required worker lane executed through the attempt05 runner at the candidate "
                                      "head with the issued command, guard and storage qualified first; W37A04-12 is "
                                      "repaired; the 22 original, 13 Attempt 3 and 13 Attempt 4 lanes each carry a "
                                      "disposition; inherited red identities are compared by identity and cause.")
        return "IN_PROGRESS", "not yet executed at the candidate head: " + ", ".join(missing)
    if key.endswith("-B"):
        phases = base.platform_phases(ctx)
        complete = all(all(row.values()) for row in phases.values())
        if complete and ctx.lane_ok("PLATFORM_CARRY"):
            return "VERIFIED_LOCAL", ("BEFORE, DURING and AFTER Jira, GitHub and All-22 receipts exist, the AFTER ones "
                                      "bound to the candidate head; every granted comment was read back; the private Jira "
                                      "successor ran every step; requests stayed within each ceiling.")
        return "IN_PROGRESS", f"platform phases complete={complete}, PLATFORM_CARRY held={ctx.lane_ok('PLATFORM_CARRY')}"
    problems = accounting_problems(ctx) + base.classification_problems(ctx)
    if not problems and ctx.lane_ok("PLATFORM_CARRY") and ctx.lane_ok("LOCAL_INTEGRATION_CANDIDATE"):
        return "VERIFIED_LOCAL", ("One separate local candidate on main carries the repair branch's tree with the "
                                  "protected review controls kept at main's bytes; its tree, history policy, refs and "
                                  "consumer are verified; all 712 carryforward identities keep their meanings and "
                                  "dispositions; red lanes stay red with every failing identity classified; no remote "
                                  "action, activation or history rewrite.")
    return "IN_PROGRESS", ("; ".join(problems[:3]) or
                           f"PLATFORM_CARRY held={ctx.lane_ok('PLATFORM_CARRY')}, "
                           f"LOCAL_INTEGRATION_CANDIDATE held={ctx.lane_ok('LOCAL_INTEGRATION_CANDIDATE')}")


def criterion_evidence(ctx: Context, requirement: str) -> list[str]:
    ids: list[str] = []
    for lane in REQUIREMENT_LANES[requirement]:
        if ctx.executed(lane):
            ids += [f"E-LANE-{lane}-RECEIPT", f"E-LANE-{lane}-LOG"]
    extra = {"R37A05-01": ["E-BEFORE-REPRODUCTION"],
             "R37A05-02": ["E-BEFORE-REPRODUCTION", "E-SUCCESSOR-POINTER"],
             "R37A05-03": ["E-BEFORE-REPRODUCTION", "E-SUCCESSOR-POINTER", "E-OUTPUT-CAREER_POPULATION_DISPOSITIONS.json"],
             "R37A05-04": ["E-BEFORE-REPRODUCTION", "E-SUCCESSOR-POINTER", "E-OUTPUT-CAREER_POPULATION_DISPOSITIONS.json"],
             "R37A05-05": ["E-BEFORE-MF05-V2", "E-STORAGE-LEDGER"],
             "R37A05-06": ["E-SUCCESSOR-POINTER", "E-OUTPUT-CAREER_POPULATION_DISPOSITIONS.json",
                           "E-OUTPUT-CAREER_CORRECTION_SUCCESSOR.json"],
             "R37A05-07": ["E-RUNS-INDEX", "E-ORIGINAL-OBLIGATIONS", "E-FAILURE-CLASSIFICATION", "E-REQUEST-LEDGER",
                           "E-OUTPUT-LANE_RESULTS.json", "E-CANDIDATE-RECORD",
                           "E-OUTPUT-LOCAL_INTEGRATION_CANDIDATE.json"]}.get(requirement, [])
    return [identity for identity in dict.fromkeys(ids + extra) if identity in ctx.evidence]


def criterion_results(ctx: Context) -> list[dict[str, Any]]:
    results = []
    for key, criterion in ctx.criteria.items():
        if criterion["executor"] != "worker":
            results.append({"id": key, "status": "PENDING_MANAGER", "evidence_ids": [],
                            "reason": "Manager-owned independent review; the worker cannot self-accept."})
            continue
        verdict, reason = judge(ctx, key, criterion["requirement"])
        evidence = criterion_evidence(ctx, criterion["requirement"])
        if key.endswith("-B") and criterion["requirement"] == "R37A05-07":
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
        elif row["id"].startswith(("ORIGINAL-LANE-", "A03-LANE-", "A04-LANE-")):
            evidence.append("E-OUTPUT-LANE_RESULTS.json")
        rows.append({"id": row["id"], "disposition": row["disposition"], "attempt5_state": state,
                     "evidence_ids": [e for e in dict.fromkeys(evidence) if e in ctx.evidence or e.startswith("E-OUTPUT-")]})
    return rows


def new_findings(ctx: Context) -> list[dict[str, Any]]:
    if not ctx.findings_path.is_file():
        return []
    rows = []
    for row in read_json(ctx.findings_path)["findings"]:
        row = dict(row)
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
                      "next_action": "; ".join(f"{f['id']}: {f['next_action']}" for f in owner_findings)[:1800],
                      "alternatives_and_reason": "Discovered and disclosed in this attempt; outside its issued repair "
                                                 "scope or awaiting an owner decision.",
                      "evidence_ids": ["E-NEW-FINDINGS"]})
    return items


# ------------------------------------------------------------------ declared outputs


def _f(path: Path) -> dict[str, Any]:
    return {"path": str(path), "exists": Path(path).is_file(), "sha256": sha256_file(path) if Path(path).is_file() else None}


def finding_matrix(ctx: Context, label: str, criteria: dict[str, dict[str, Any]]) -> dict[str, Any]:
    before = ctx.out_root / "evidence" / "before"
    reproduction = read_json(before / "BEFORE_REPRODUCTION.json") if (before / "BEFORE_REPRODUCTION.json").is_file() else {}
    plan = {
        "MF37A04-01": ([_f(MANAGER_A4 / "GIT_OPTION_CHALLENGE_V2.json"), _f(MANAGER_A4 / "git_option_challenge_v2.py"),
                        _f(before / "BEFORE_REPRODUCTION.json")],
                       {"WRITE_PROTECTION": "manager_a4_git_option_challenge_v2", "FULL_FINAL_MOUNTED": "attempt4_comparison",
                        "STRICT_MOUNTED": "attempt4_comparison", "TRUE_UNMOUNTED": None}),
        "MF37A04-02": ([_f(MANAGER_A4 / "SUCCESSOR_CHALLENGE.json"), _f(MANAGER_A4 / "successor_challenge.py"),
                        _f(before / "BEFORE_REPRODUCTION.json")],
                       {"CAREER_SUCCESSOR": "successor_checks", "INSTALLED_CONSUMER_C01": "lineage_fixtures"}),
        "MF37A04-03": ([_f(MANAGER_A4 / "CAREER_SEMANTIC_CENSUS.json"), _f(MANAGER_A4 / "career_semantic_census.py"),
                        _f(before / "BEFORE_REPRODUCTION.json")],
                       {"CAREER_SUCCESSOR": "screens", "INSTALLED_CONSUMER_C01": "successor_named_cases"}),
        "MF37A04-04": ([_f(MANAGER_A4 / "CAREER_SEMANTIC_CENSUS.json"), _f(before / "BEFORE_REPRODUCTION.json")],
                       {"CAREER_SUCCESSOR": "unit_changes", "INSTALLED_CONSUMER_C01": "manager_a4_career_semantic_census"}),
        "MF37A04-05": ([_f(ctx.out_root / "evidence" / "before_mf05_v2" / "BEFORE_MF05_RERUN.json"),
                        _f(ATTEMPT4_ROOT / "evidence" / "STORAGE_MEASUREMENT_20260925T021819Z.json")],
                       {"STORAGE_ADMISSION": "storage_ledger"}),
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
            "reproduced_before_repair": (reproduction.get("reproduced") or {}).get(
                key if key != "MF37A04-03" and key != "MF37A04-04" else "MF37A04-03/04"),
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
    details = ctx.details("INSTALLED_CONSUMER_C01")
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
            "coverage": details.get("successor_coverage"), "locators": details.get("successor_locators"),
            "lineage_fixtures": details.get("lineage_fixtures")},
        "manager_replays": {"a3_admission_pit_installed": details.get("manager_a3_installed"),
                            "a3_career_challenge": details.get("manager_a3_career_challenge"),
                            "a4_career_semantic_census": details.get("manager_a4_career_semantic_census"),
                            "a4_successor_challenge": details.get("manager_a4_successor_challenge")},
        "claim_successor": {"path": str(base.SUCCESSOR), "sha256": sha256_file(base.SUCCESSOR),
                            "consumer": "tools/validate_cycle29_gates.py --claim-inventory-successor",
                            "lane": ctx.runs.get("CAREER_SUCCESSOR"),
                            "checks": ctx.details("CAREER_SUCCESSOR").get("claim_successor")},
        "default_routing": ("Without --career-successor the installed CLI answers from the delivered release's own "
                            "corrected table exactly as before; that default is not changed."),
        "not_claimed": ("No release, successor or candidate is activated or published; the career successor is private "
                        "worker evidence, not accepted and not the default."),
    })
    return manifest


def platform_reconciliation(ctx: Context, label: str) -> dict[str, Any]:
    document = a4o.platform_reconciliation(ctx, label)
    document["cycle_number"], document["attempt_number"] = CYCLE_NUMBER, ATTEMPT_NUMBER
    document["label_note"] = ("Every Attempt 5 platform receipt carries the numeric label. The BEFORE reads were taken "
                              "after the local repairs had begun; each receipt binds the exact head it read at.")
    return document


def successor_document(ctx: Context, label: str) -> dict[str, Any]:
    summary = ctx.build_summary()
    lane = ctx.details("CAREER_SUCCESSOR")
    installed = ctx.details("INSTALLED_CONSUMER_C01")
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "requirements": ["R37A05-02", "R37A05-03", "R37A05-04", "R37A05-06"],
            "findings": ["MF37A04-02", "MF37A04-03", "MF37A04-04"], "candidate": ctx.candidate,
            "pointer": {"path": str(ctx.pointer_path), **ctx.pointer},
            "identity": (summary.get("successor") or {}).get("identity"),
            "episodes": (summary.get("successor") or {}).get("episodes"),
            "accounting": summary.get("accounting"), "a04_mapping": summary.get("a04_mapping"),
            "parse": summary.get("parse"), "inputs": summary.get("inputs"), "predecessor": summary.get("predecessor"),
            "a04_successor": summary.get("a04_successor"), "uncertainty_classes": summary.get("uncertainty_classes"),
            "date_basis": summary.get("date_basis"), "comparison_rule": summary.get("comparison_rule"),
            "not_produced_by_cause": summary.get("not_produced_by_cause"),
            "reproduction_at_candidate_head": lane.get("successor_reproduction"),
            "rebuild_checks_at_candidate_head": lane.get("successor_checks"),
            "installed_serving": {k: installed.get(k) for k in ("successor_pagination", "successor_coverage",
                                                                "successor_named_cases")},
            "selection_rule": ("Selected only by naming the file (and its digest) on the installed CLI. The delivered "
                               "database and the Attempt 4 successor keep their bytes, default path and default answer; "
                               "old identities are never reused (C37A05:<pageid>:<revision>:<family>:<row>:<interval>)."),
            "not_claimed": summary.get("not_claimed")}


def population_document(ctx: Context, label: str) -> dict[str, Any]:
    summary = ctx.build_summary()
    detail_path = Path(((summary.get("files") or {}).get("detail_rows") or {}).get("path", ""))
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "candidate": ctx.candidate,
            "population": {"predecessor_rows": (summary.get("accounting") or {}).get("predecessor_rows"),
                           "a04_rows": (summary.get("a04_mapping") or {}).get("total"),
                           "successor_episodes": (summary.get("accounting") or {}).get("successor_episodes"),
                           "pages": (summary.get("parse") or {}).get("pages")},
            "predecessor_dispositions": summary.get("dispositions"), "a04_dispositions": summary.get("a04_mapping"),
            "complete_row_dispositions": {"predecessor": (summary.get("files") or {}).get("dispositions"),
                                          "a04": (summary.get("files") or {}).get("a04_mapping"),
                                          "also_in": "career_a05_disposition and career_a05_from_a04 tables of the successor"},
            "a3_screens": summary.get("a3_screens"), "a4_screens": summary.get("a4_screens"),
            "screen_rows_file": {"path": str(detail_path), "sha256": sha256_file(detail_path) if detail_path.is_file() else None,
                                 "content": "every member of the 2,257-row and 33-row screens, the unit changes and the "
                                            "affected delivered staff rows"},
            "a4_raw_census_reconciliation": summary.get("a4_raw_census_reconciliation"),
            "a4_raw_census_uncovered_by_cause": summary.get("a4_raw_census_uncovered_by_cause"),
            "template_census_reconciliation": summary.get("template_census_reconciliation"),
            "not_produced_by_cause": summary.get("not_produced_by_cause"),
            "unit_changes": summary.get("unit_changes"), "staff_descendants": summary.get("staff_descendants"),
            "independently_discovered_classes": [f for f in new_findings(ctx) if f.get("class_of") == "CAREER_POPULATION"],
            "note": ("Every predecessor row and every Attempt 4 row has exactly one disposition in the named files; the "
                     "two manager screens are listed member by member in the rows file, each with a check that does "
                     "not use the parser or the taxonomy.")}


def candidate_document(ctx: Context, label: str) -> dict[str, Any]:
    details = ctx.details("LOCAL_INTEGRATION_CANDIDATE")
    record = read_json(ctx.candidate_record_path) if ctx.candidate_record_path else {}
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "requirement": "R37A05-07-C", "repair_candidate": ctx.candidate,
            "grant": next((g for g in ctx.contract["authority"]["grants"]
                           if g["action"] == "PREPARE_SEPARATE_PRESERVED_LOCAL_INTEGRATION_CANDIDATE"), None),
            "integration_candidate": candidate.describe(),
            "creation_record": {"path": str(ctx.candidate_record_path) if ctx.candidate_record_path else None,
                                "sha256": sha256_file(ctx.candidate_record_path) if ctx.candidate_record_path else None,
                                **{k: record.get(k) for k in ("created_at", "candidate_commit", "candidate_tree",
                                                              "refs_changed", "only_the_new_branch_ref_changed",
                                                              "protected_paths_marked_skip_worktree",
                                                              "protected_paths_written_to_disk",
                                                              "withheld_protected_paths")}},
            "lane": {"run": ctx.runs.get("LOCAL_INTEGRATION_CANDIDATE"),
                     "result": (ctx.receipts.get("LOCAL_INTEGRATION_CANDIDATE") or {}).get("result"),
                     "tree_checks": details.get("candidate_tree_checks"), "history_policy": details.get("candidate_history_policy"),
                     "consumer": details.get("candidate_consumer"),
                     "review_control_characterization": details.get("candidate_review_control_characterization")},
            "decision_for_the_owner": ("The candidate keeps main's protected scientific-review controls; the repair "
                                       "branch's own changes to them (listed) are withheld because changing trusted "
                                       "controls on main is an owner decision the contract does not grant."),
            "not_done": ("No push, remote PR, merge, retarget, closure, deletion, history rewrite or default activation; "
                         "the repair branch keeps every original commit and every other ref its commit.")}


def integration_packet(ctx: Context, label: str, lanes: list[dict[str, Any]]) -> str:
    text = base.integration_packet(ctx, label, lanes)
    github = ctx.latest_github or {}
    main_head = github.get("main_head")
    tags = collections.Counter(re.match(r"^\[(\w+)\]", s).group(1) if re.match(r"^\[(\w+)\]", s) else "untagged"
                               for _, s in ctx.commits)
    head = ctx.candidate["head"]
    ahead = git_out("rev-list", "--count", f"{main_head}..{head}") if main_head else None
    description = candidate.describe()
    text += "\n".join([
        "### Repair branch against main", "",
        f"Main at the latest read: `{main_head}`. The repair branch is {ahead} "
        "commits ahead of it. Commits after the issued base by subject tag: " + str(dict(tags)) + ". A mis-tagged "
        "subject is never rewritten; the supported correction is an appended record naming the earlier commit.", "",
        "### Sequential squash versus one consolidated candidate (comparison)", "",
        f"- Sequential stack: the {github.get('open_pr_count')} open PRs would each need rebase onto its squashed parent, fresh checks, eligible "
        "approvals and thread dispositions in dependency order; every squash changes the next base.",
        "- One consolidated candidate (prepared below, locally only): the repair branch as one commit on main, with "
        "the protected review controls kept at main's bytes; one publication grant and one review, a large diff.",
        "- Recommendation: keep the single candidate and decide publication after independent manager review.", ""])
    protected = description.get("protected_paths") or []
    extra = ["### The separate local integration candidate (prepared; nothing published)", "",
             f"Branch `{description.get('candidate_branch')}` at `{description.get('candidate_head')}` in "
             f"`{description.get('candidate_worktree')}`: one `[material]` commit on main `{description.get('main')}` "
             f"(parents {description.get('candidate_parents')}), tree `{description.get('candidate_tree')}`, "
             f"{description.get('files_changed_against_main')} files changed against main, consolidating "
             f"{description.get('repair_commits_consolidated')} repair-branch commits whose originals stay on "
             f"`{description.get('repair_branch')}` at `{description.get('repair_head')}`.", "",
             "The candidate tree equals the repair branch's final tree except the protected scientific-review controls, "
             "which keep main's exact bytes (the checkout never wrote them; they are skip-worktree entries):", "",
             "| Path | Main | Repair branch | Candidate |", "| --- | --- | --- | --- |"]
    for row in protected:
        extra.append(f"| `{row['path']}` | {(row.get('main') or ['', 'absent'])[1][:12]} | "
                     f"{(row.get('repair') or ['', 'absent'])[1][:12]} | {(row.get('candidate') or ['', 'absent'])[1][:12]} |")
    extra += ["", "Owner decisions this candidate needs (none taken): whether the repair branch's review-control changes "
              "(the retired Codex review and the paid-review gate) should reach main; publication of the candidate branch; "
              f"merge through a reviewed PR with the {github.get('unresolved_thread_total')} unresolved review threads of "
              f"the {github.get('open_pr_count')} open PRs dispositioned. Rollback of any future merge: revert the single "
              "candidate commit.", ""]
    return text + "\n".join(extra) + "\n"


def effects(ctx: Context) -> list[dict[str, Any]]:
    """The Attempt 3 effects, plus the one granted local integration action this attempt took."""

    rows = base.effects(ctx)
    grant = next((g for g in ctx.contract["authority"]["grants"]
                  if g["action"] == "PREPARE_SEPARATE_PRESERVED_LOCAL_INTEGRATION_CANDIDATE"), None)
    if grant and ctx.candidate_record_path and "E-CANDIDATE-RECORD" in ctx.evidence:
        record = read_json(ctx.candidate_record_path)
        rows.append({"id": "EFF-LOCAL-INTEGRATION-CANDIDATE", "actor": grant["actor"], "action": grant["action"],
                     "target": grant["target"], "result": "SUCCEEDED",
                     "detail": (f"New local branch {candidate.CANDIDATE_BRANCH} at {record.get('candidate_commit')} and "
                                f"worktree {candidate.CANDIDATE_WORKTREE}; refs changed {record.get('refs_changed')}; "
                                "shared objects, the new ref and the worktree registration only; no push, merge or "
                                "rewrite."),
                     "evidence_ids": ["E-CANDIDATE-RECORD"]})
    return rows


def cost_ledger(ctx: Context, label: str) -> dict[str, Any]:
    document = base.cost_ledger(ctx, label)
    document["cycle_number"], document["attempt_number"] = CYCLE_NUMBER, ATTEMPT_NUMBER
    document["grants_used"] = effects(ctx)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import storage_admission  # noqa: PLC0415

    status = storage_admission.Ledger(ctx.ledger_path).status() if ctx.ledger_path.is_file() else {}
    document["storage"].update({"ledger": str(ctx.ledger_path), "ledger_sha256": sha256_file(ctx.ledger_path)
                                if ctx.ledger_path.is_file() else None,
                                **{k: status.get(k) for k in ("records", "added_bytes", "headroom_bytes",
                                                              "open_reservations", "bounded_stop", "refused",
                                                              "underestimated", "roots")}})
    return document


# ------------------------------------------------------------------ build


def build(ctx: Context, headline: str, writer_released: bool) -> dict[str, Any]:
    register_evidence(ctx)
    root = ctx.out_root
    lanes = base.lane_rows(ctx)
    ctx.original_lanes = original_lane_dispositions(ctx)
    ctx.attempt3_lanes = attempt3_lane_dispositions(ctx)
    ctx.attempt4_lanes = attempt4_lane_dispositions(ctx)
    obligations_path = root / "ORIGINAL_OBLIGATION_DISPOSITIONS.json"
    label = f"{LABEL_PREFIX} {headline}"

    def write_obligations(states: dict[str, dict[str, Any]]) -> None:
        items = []
        for row in ctx.contract["carryforward"]:
            item = {"id": row["id"], "category": carry_category(row["id"]),
                    **{k: row[k] for k in ("original_meaning", "disposition", "source_ids", "requirement_ids",
                                           "acceptance_ids", "owner", "reason", "next_action", "prior_mapping")}}
            if row["id"] in states:
                item["attempt5_state"] = states[row["id"]]["attempt5_state"]
                item["attempt5_evidence_ids"] = [e for e in states[row["id"]]["evidence_ids"] if e != "E-ORIGINAL-OBLIGATIONS"]
            items.append(item)
        ctx.carry_counts = {"composition": dict(collections.Counter(i["category"] for i in items)),
                            "dispositions": dict(collections.Counter(i["disposition"] for i in items))}
        ctx.obligation_items = items
        write_output(obligations_path, dumps({
            "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "contract_sha256": ctx.contract_sha256, "candidate": ctx.candidate,
            **ctx.carry_counts, "items": items, "original_lanes": ctx.original_lanes,
            "attempt3_lanes": ctx.attempt3_lanes, "attempt4_lanes": ctx.attempt4_lanes,
            "note": ("Original meanings, sources, owners, reasons, next actions, prior mappings and dispositions are "
                     "copied from the issued contract unchanged. OWNED_BACKLOG items stay owned; none is marked "
                     "fulfilled by this accounting.")}))
        ctx.add("E-ORIGINAL-OBLIGATIONS", obligations_path, CENSUS,
                "All 712 carryforward identities with their original meanings and unchanged dispositions")

    write_obligations({})
    write_output(root / "LANE_RESULTS.json", dumps({
        "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "candidate": ctx.candidate,
        "runner": "tools/cycle37/attempt05_lanes.py", "runs_index": str(root / "lanes" / "RUNS.jsonl"),
        "lanes": lanes, "original_lanes": ctx.original_lanes, "attempt3_lanes": ctx.attempt3_lanes,
        "attempt4_lanes": ctx.attempt4_lanes}))
    ctx.add("E-OUTPUT-LANE_RESULTS.json", root / "LANE_RESULTS.json", CENSUS,
            "Every required lane's result at the candidate head; the 22 original, 13 Attempt 3 and 13 Attempt 4 lanes")
    for name, builder in (("CAREER_CORRECTION_SUCCESSOR.json", successor_document),
                          ("CAREER_POPULATION_DISPOSITIONS.json", population_document),
                          ("LOCAL_INTEGRATION_CANDIDATE.json", candidate_document)):
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
    software = ("FAIL" if any(l["status"] == "FAIL" for l in lanes) else
                "PASS" if all(l["status"] == "PASS" for l in lanes) else
                "NOT_RUN" if not any(l["executed"] or l["status"] == "PASS" for l in lanes) else "PARTIAL")
    summary = ctx.build_summary()
    pagination = ctx.details("INSTALLED_CONSUMER_C01").get("successor_pagination") or {}
    if ctx.lane_ok("INSTALLED_CONSUMER_C01") and ctx.lane_ok("CAREER_SUCCESSOR"):
        by = (summary.get("dispositions") or {}).get("by_disposition") or {}
        by4 = (summary.get("a04_mapping") or {}).get("by_disposition") or {}
        data_evidence = (f"DELIVERED_RELEASE_{DB_SHA256[:12]}_UNCHANGED; EXPLICIT_CAREER_SUCCESSOR_"
                         f"{str(ctx.pointer.get('successor_sha256'))[:12]}_ROWS_{pagination.get('distinct')}; "
                         f"PREDECESSOR_ROWS_DISPOSITIONED_{(summary.get('accounting') or {}).get('dispositions')}"
                         f"({', '.join(f'{k} {v}' for k, v in sorted(by.items()))}); A04_ROWS_MAPPED_"
                         f"{(summary.get('a04_mapping') or {}).get('total')}({', '.join(f'{k} {v}' for k, v in sorted(by4.items()))}); "
                         "REAL_ELIGIBLE_FORECASTS_0; REAL_PROVEN_PIT_0; NOT_ACTIVATED")
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
        "effects": effects(ctx), "costs": base.costs(ctx), "platform_receipts": base.platform_receipts(ctx, by_id),
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
    import attempt05_report  # the narrative report, beside this tool  # noqa: PLC0415

    write_output(root / "WORKER_REPORT.md", attempt05_report.render(ctx, submission))
    return submission


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
        for key, prefix in (("original_lanes", "ORIGINAL-LANE-"), ("attempt3_lanes", "A03-LANE-"),
                            ("attempt4_lanes", "A04-LANE-")):
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
            problems.append("FINDING_CLOSURE_MATRIX does not cover exactly MF37A04-01..05")
        for row in rows:
            if not row["commits"]:
                problems.append(f"{row['finding']} names no commit")
    if not ctx.pointer:
        problems.append("the delivered career successor pointer is missing")
    elif sha256_file(Path(ctx.pointer["successor_file"])) != ctx.pointer.get("successor_sha256"):
        problems.append("the delivered career successor does not match its pointer digest")
    if not ctx.ledger_path.is_file():
        problems.append("the storage ledger is missing")
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
        base.seal(ctx, submission)
        print(json.dumps({"sealed": [row["id"] for row in submission["handoff_artifacts"]]}, indent=2))
        return 0
    submission = build(ctx, args.headline, args.writer_released)
    base.seal(ctx, submission)
    print(json.dumps({"headline": submission["headline"],
                      "criteria": dict(collections.Counter(c["status"] for c in submission["criteria"])),
                      "lanes": {l["id"]: l["status"] for l in submission["lanes"]},
                      "unfinished": [(u["id"], u["kind"]) for u in submission["unfinished"]],
                      "evidence": len(submission["evidence"])}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
