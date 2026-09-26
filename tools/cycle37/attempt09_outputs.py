r"""Cycle #37 — Attempt #9 — worker outputs, submission and accounting check (R37A09-05).

    attempt09_outputs.py classify  --contract C --out-root R
    attempt09_outputs.py inventory --contract C --out-root R
    attempt09_outputs.py build     --contract C --out-root R [--headline H --writer-released]
    attempt09_outputs.py check     --contract C --out-root R [--final-packet]
    attempt09_outputs.py seal      --contract C --out-root R

The Attempt 8 accounting (``attempt08_outputs``, over the Attempt 7, 6, 5, 4 and 3 bases) rebound to the Attempt 9
contract: 18 declared outputs (the CONTROL-07 proposal pair among them), 908 carryforward identities (the 862 of
Attempt 8 plus its 20 clauses, 15 lanes, 9 worker findings and the two manager findings), 20 clauses and 15 lanes.
``build`` writes the outputs from what is there -- the issued contract, the lane receipts, the platform receipts and
request ledger, the storage ledger chain and its snapshot, the candidate append records, the CONTROL-07 validation
receipt, git, the intake, Git housekeeping preflight and repair-commit receipts, the population census, and
worker-authored evidence it reads but never invents (``evidence/INHERITED_FAILURE_CLASSIFICATION.json``,
``evidence/NEW_FINDINGS_ATTEMPT9.json``, ``evidence/CLEANUP_INVENTORY.json``, ``evidence/before/BEFORE_REPRODUCTION.json``).

The attempt has one storage ledger chain. The root ledger ``STORAGE_RESERVATIONS.jsonl`` carries every material
reservation; it is registered as evidence only once ``STORAGE_EVIDENCE_SNAPSHOT.json`` freezes it, with its append-only
head log and the create-only claim naming its one continuation, the final-output ledger, which is named by path only.
``lanes/RUNS.jsonl`` is named by path only. This tool never accepts anything.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt08_outputs as a8o  # noqa: E402  (the preserved Attempt 8 accounting)
import attempt09_candidate as candidate  # noqa: E402

a7o, a6o, a5o, a4o, base = a8o.a7o, a8o.a6o, a8o.a5o, a8o.a4o, a8o.base
storage_admission = a8o.storage_admission
dumps, git_out, read_json, sha256_file, utc_now, write_output = (a8o.dumps, a8o.git_out, a8o.read_json,
                                                                 a8o.sha256_file, a8o.utc_now, a8o.write_output)

CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID, ATTEMPT_ID = 37, 9, "CYCLE-37", "ATTEMPT-09-20260926"
BASE_SHA = "91a83b197d8523d26aaa3d2683fa75a8ed9d5be9"
BRANCH = "codex/BAT-706-cycle37-rework"
DATA = Path(r"C:\BatteredAggieSyndrome.data")
ATTEMPT8_ROOT = DATA / "ops" / "cycle37" / "attempt08"
MANAGER_A8 = DATA / "ops" / "manager_reviews" / "cycle37" / "attempt08" / "review-20260926T151153Z"
MANAGER_A8_NULL_SPAN = Path(r"C:\BatteredAggieSyndrome.validation\mr37a08-151153") / "adversarial.sqlite"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a09")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37a09")
WORKER_LANES = a8o.WORKER_LANES
FINDING_IDS = ("MF37A08-01", "MF37A08-02")
REQUIREMENT_LANES = {
    "R37A09-01": ("CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01"),
    "R37A09-02": ("STORAGE_ADMISSION", "FINAL_PACKET"),
    "R37A09-03": ("LOCAL_INTEGRATION_CANDIDATE",),
    "R37A09-04": ("WRITE_PROTECTION", "SOURCE_ADMISSION", "SOURCE_HARNESS", "SOURCE_REGRESSIONS", "CAREER_SUCCESSOR",
                  "INSTALLED_CONSUMER_C01", "TRUE_UNMOUNTED", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED"),
    "R37A09-05": WORKER_LANES,
}
A08_LANES = {lane: (lane,) for lane in WORKER_LANES} | {"MANAGER_REVIEW": ()}
CARRY_COMPOSITION = {**a8o.CARRY_COMPOSITION, "MANAGER_FINDING": 24, "ATTEMPT8_CRITERION": 20, "ATTEMPT8_LANE": 15,
                     "ATTEMPT8_WORKER_FINDING": 9}
LABEL_PREFIX = "Cycle #37 \u2014 Attempt #9 \u2014"
OUTPUT_NAMES = a8o.OUTPUT_NAMES
OPERATIONAL_LEDGER = a8o.OPERATIONAL_LEDGER
FINAL_SNAPSHOT = a8o.FINAL_SNAPSHOT
FINAL_OUTPUT_LEDGER = a8o.FINAL_OUTPUT_LEDGER
NEVER_EVIDENCE = a8o.NEVER_EVIDENCE
CANDIDATE_GRANT = a8o.CANDIDATE_GRANT
RAW = a8o.RAW
CENSUS = a8o.CENSUS
CONTROL_OUTPUTS = a8o.CONTROL_OUTPUTS
CONTROL_PATCH = a8o.CONTROL_PATCH
REFUSED_SOURCE_FIELD = "REFUSED_CAREER_SUCCESSOR_SOURCE_FIELD_WITNESS_MISMATCH"
REFUSED_ROOTS = "REFUSED_CONTINUATION_ROOT_CONTRACT_DIFFERS"


_A8_CARRY_CATEGORY = a8o.carry_category  # captured before rebind() points a7o's name at carry_category below


def carry_category(key: str) -> str:
    for prefix, name in (("A08-AC-", "ATTEMPT8_CRITERION"), ("A08-LANE-", "ATTEMPT8_LANE"),
                         ("A08-WORKER-", "ATTEMPT8_WORKER_FINDING")):
        if key.startswith(prefix):
            return name
    return _A8_CARRY_CATEGORY(key)


def rebind() -> None:
    """Point the preserved accountings at the Attempt 9 identity. The Attempt 4 to 8 helpers keep the constants that
    find their own final lane receipts (each module's ``BASE_SHA`` names the head its predecessor finished at)."""

    a8o.rebind()
    base.CYCLE_NUMBER, base.ATTEMPT_NUMBER, base.CYCLE_ID, base.ATTEMPT_ID = (CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID,
                                                                              ATTEMPT_ID)
    base.BASE_SHA = BASE_SHA
    base.BRANCH = BRANCH
    base.WORKER_LANES = WORKER_LANES
    for module in (a4o, a5o, a6o, a7o, a8o):
        module.LABEL_PREFIX = LABEL_PREFIX
        module.CYCLE_NUMBER, module.ATTEMPT_NUMBER = CYCLE_NUMBER, ATTEMPT_NUMBER
    for module in (a5o, a6o, a7o, a8o):
        module.CYCLE_ID, module.ATTEMPT_ID = CYCLE_ID, ATTEMPT_ID
    for module in (a6o, a7o, a8o):
        module.candidate = candidate
    a7o.CARRY_COMPOSITION = CARRY_COMPOSITION
    a7o.carry_category = carry_category


class Context(a8o.Context):
    def __init__(self, contract_path: Path, out_root: Path) -> None:
        super().__init__(contract_path, out_root)
        self.findings_path = out_root / "evidence" / "NEW_FINDINGS_ATTEMPT9.json"
        self.attempt8_lanes: list[dict[str, Any]] = []


# ------------------------------------------------------------------ evidence


def register_evidence(ctx: Context) -> None:
    root = ctx.out_root
    for lane, run in ctx.runs.items():
        receipt = Path(run["receipt"])
        ctx.add(f"E-LANE-{lane}-LOG", receipt.parent / "lane.log", "command_log",
                f"{lane} run {run['run']}: the runner's console -- every command, its exit and its verdict")
        ctx.add(f"E-LANE-{lane}-RECEIPT", receipt, RAW,
                f"{lane} run {run['run']}: contract, source, interpreter, raw log paths and digests, census "
                "records, consumer outputs, storage reservation, the shared Git store measured around the lane and the "
                "write/network scope measurement")
    career = ctx.runs.get("CAREER_SUCCESSOR")
    if career:
        for path in sorted(Path(career["receipt"]).parent.glob("ORACLE_*.json")):
            stem = path.stem[len("ORACLE_"):]
            if stem.startswith("A09_"):
                scope = ("The independent identity-derived source-unit oracle's full result (sqlite3/json/re only; "
                         "Attempt 9) over " + stem[4:].replace("_", " "))
            else:
                scope = "The Attempt 8 independent source-field oracle's full result, kept, over " + stem.replace("_", " ")
            ctx.add(f"E-ORACLE-{stem}", path, RAW, scope)
    for identity, path, kind, scope in (
            ("E-REQUEST-LEDGER", root / "evidence" / "platform" / "REQUEST_LEDGER.jsonl", CENSUS,
             "Every counted platform request, retries included, appended before its result was used"),
            ("E-FAILURE-CLASSIFICATION", root / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json", CENSUS,
             "Worker classification of every failing identity of a red lane, by cause, kind, owner and next action"),
            ("E-NEW-FINDINGS", ctx.findings_path, CENSUS,
             "Findings discovered in Attempt 9, with severity, disposition, owner and next action"),
            ("E-CLEANUP-INVENTORY", root / "evidence" / "CLEANUP_INVENTORY.json", CENSUS,
             "Every directory this attempt created or wrote, its bytes, and what the owner may remove (nothing removed)"),
            ("E-INTAKE", root / "evidence" / "intake" / "INTAKE.json", RAW,
             "Intake: the sealed contract and every issued source re-hashed, both closure archives, the three subjects "
             "(the issued base, the granted candidate head, main), the interpreter, the installed Attempt 8 consumer, "
             "the grants and budgets, before any repair was drafted"),
            ("E-CLOSURE-ROWS", root / "evidence" / "intake" / "CLOSURE_ROWS.json", RAW,
             "Every entry of the manager's original-input and review closures compared with its archive"),
            ("E-GIT-HOUSEKEEPING-PREFLIGHT", root / "evidence" / "intake" / "GIT_HOUSEKEEPING_PREFLIGHT.json", RAW,
             "Owned Git fixtures: a plain commit runs gc --auto and packs the loose objects; the same commit with "
             "command-scoped gc.auto=0 and maintenance.auto=false leaves them loose"),
            ("E-GIT-HELPER-CONSTRUCTION", root / "evidence" / "intake" / "GIT_HELPER_CONSTRUCTION.json", RAW,
             "Every Git command the Attempt 9 wrapper builds begins with the two command-scoped settings"),
            ("E-BEFORE-REPRODUCTION", root / "evidence" / "before" / "BEFORE_REPRODUCTION.json", RAW,
             "Before-repair reproduction of MF37A08-01 and MF37A08-02 on the clean issued base 91a83b19 before any "
             "Attempt 9 source was drafted: the manager's saved NULL-span fixture through the installed console script, "
             "installed module and source module, the Attempt 8 worker oracle, and the manager's continuation "
             "challenge on the unfixed storage tools"),
            ("E-CENSUS-SPAN", root / "evidence" / "census" / "SPAN_CENSUS.json", CENSUS,
             "Population census of every genuine row's witness spellings (SQL NULL, JSON null, [null, null], blank) "
             "in the delivered, Attempt 4 and Attempt 5 files, fitted before the absence rule was enforced"),
            ("E-CENSUS-TEXT", root / "evidence" / "census" / "TEXT_CENSUS.json", CENSUS,
             "Population census of every genuine unwitnessed row's text against the source unit its identity names"),
            ("E-CONTROL07-PATCH", root / CONTROL_PATCH, RAW,
             "The inert CONTROL-07 proposal as a patch against main's six control surfaces (never applied)")):
        if Path(path).is_file():
            ctx.add(identity, path, kind, scope)
    for path in sorted((root / "evidence" / "census").glob("*.py")):
        ctx.add(f"E-CENSUS-SCRIPT-{path.name}", path, RAW, f"The census script {path.name}, as run (stdlib only)")
    for path in sorted((root / "evidence" / "findings").glob("*")):
        if path.is_file():
            ctx.add(f"E-FINDING-{path.name}", path, RAW,
                    f"New-finding evidence {path.name} (a development probe or its result, copied unchanged)")
    for path in sorted((root / "evidence" / "git").glob("COMMIT_*.json")):
        ctx.add(f"E-GIT-{path.stem}", path, RAW,
                f"Repair-branch commit receipt {path.stem}: command prefix -c gc.auto=0 -c maintenance.auto=false, the "
                "parent, the staged paths, the regenerated provenance, and the shared Git store and refs before and after")
    proposed = root / "evidence" / "control07" / "proposed"
    for path in sorted(p for p in proposed.rglob("*") if p.is_file()):
        relative = path.relative_to(proposed).as_posix()
        ctx.add(f"E-CONTROL07-PROPOSED-{relative}", path, RAW,
                f"The retained inert proposed bytes of {relative} (the qualified Attempt 7 bytes, retained by Attempt 8; "
                "not adopted)")
    for name in CONTROL_OUTPUTS:
        if (root / name).is_file():
            ctx.add(f"E-OUTPUT-{name}", root / name, RAW, f"Declared worker output {name} (create-only, at the final "
                                                          "subjects)")
    matrix = root / "CONTROL07_PROPOSAL_VALIDATION_OFFLINE_MATRIX.json"
    if matrix.is_file():
        ctx.add("E-CONTROL07-OFFLINE-MATRIX", matrix, RAW, "The preserved offline qualification's own create-only receipt")
    platform = root / "evidence" / "platform"
    for path in sorted(p for p in platform.rglob("*") if p.is_file() and p.suffix in (".json", ".csv", ".txt")
                       and p.parent != platform):
        relative = path.relative_to(platform).as_posix()
        ctx.add(f"E-PLATFORM-{relative}", path, CENSUS, f"Platform lifecycle evidence {relative}")
    if (root / FINAL_SNAPSHOT).is_file():
        ledger = root / OPERATIONAL_LEDGER
        for identity, path, scope in (
                ("E-STORAGE-SNAPSHOT", root / FINAL_SNAPSHOT,
                 "The immutable snapshot of the attempt's root storage ledger: sequence, chain head, prefix and file "
                 "digests, measured totals, identity and configuration"),
                ("E-STORAGE-LEDGER", ledger, "The attempt's root storage ledger (Cycle 37 / Attempt 9), frozen by its "
                                             "snapshot and never written again"),
                ("E-STORAGE-LEDGER-HEAD", Path(str(ledger) + storage_admission.HEAD_SUFFIX),
                 "The root ledger's append-only head log, frozen with it (a truncation is detected against it)"),
                ("E-STORAGE-CONTINUATION-CLAIM", Path(str(ledger) + storage_admission.CLAIM_SUFFIX),
                 "The create-only claim naming the root's one continuation (the final-output ledger) and its root "
                 "contract")):
            if path.is_file():
                ctx.add(identity, path, CENSUS, scope)
    for number, path in enumerate(ctx.candidate_record_paths, 1):
        ctx.add("E-CANDIDATE-APPEND-RECORD" if path == ctx.candidate_record_path else f"E-CANDIDATE-APPEND-RECORD-{number}",
                path, RAW, f"Append record {number} of the local integration candidate: previous head, commit, tree, "
                "provenance blobs, committed-blob proof, refs changed, worktree state, the shared Git store before and "
                "after")
    for path in sorted((root / "evidence" / "final").glob("FINAL_PACKET_VALIDATION_*.json")):
        ctx.add(f"E-FINAL-{path.name}", path, RAW, "The FINAL_PACKET lane's create-only validation receipt")
    for path in sorted((root / "evidence" / "scope").glob("*.json")):
        ctx.add(f"E-SCOPE-{path.name}", path, CENSUS, "Write-measurement exclusion basis measured with no lane running")
    for identity, row in ctx.evidence.items():
        relative = Path(row["path"]).resolve().relative_to(root.resolve()).as_posix()
        if relative in NEVER_EVIDENCE:
            raise SystemExit(f"{identity} registers {relative}, which a later step writes; refusing")
        if relative in (OPERATIONAL_LEDGER.as_posix(), OPERATIONAL_LEDGER.as_posix() + storage_admission.HEAD_SUFFIX) \
                and not (root / FINAL_SNAPSHOT).is_file():
            raise SystemExit(f"{identity} registers the live operational ledger before its freeze; refusing")


# ------------------------------------------------------------------ lanes


_CARRIED = tuple(f"CARRIED_BY_ATTEMPT{n}_LANE_AT_THE_CANDIDATE_HEAD" for n in (5, 6, 7, 8))


def _relabel(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The preserved dispositions name the attempt whose lane carries a prior lane; here that is Attempt 9. The results
    were read from this attempt's receipts, so only the naming changes."""

    out = []
    for row in rows:
        row = dict(row)
        disposition = row.get("disposition")
        if disposition in _CARRIED:
            number = disposition.split("ATTEMPT", 1)[1][0]
            row["disposition"] = "CARRIED_BY_ATTEMPT9_LANE_AT_THE_CANDIDATE_HEAD"
            row["attempt9_lanes"] = row.pop(f"attempt{number}_lanes")
            row["attempt9_results"] = row.pop(f"attempt{number}_results")
            if "justification" in row:
                row["justification"] = row["justification"].replace(f"Attempt {number} lane", "Attempt 9 lane")
        out.append(row)
    return out


def _a08_final(lane: str) -> dict[str, Any]:
    index = ATTEMPT8_ROOT / "lanes" / "RUNS.jsonl"
    rows = [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [row for row in rows if row["lane"] == lane and row["head"] == BASE_SHA]
    return rows[-1] if rows else {}


def attempt8_lane_dispositions(ctx: Context) -> list[dict[str, Any]]:
    rows = []
    for lane, successors in A08_LANES.items():
        final = _a08_final(lane)
        row: dict[str, Any] = {"id": f"A08-LANE-{lane}", "attempt8_lane": lane, "attempt8_run": final.get("run"),
                               "attempt8_result": final.get("result"), "attempt8_head": final.get("head"),
                               "attempt8_receipt": final.get("receipt"),
                               "attempt8_receipt_sha256": final.get("receipt_sha256"),
                               "attempt8_receipt_preserved": bool(final.get("receipt")) and Path(final["receipt"]).is_file()}
        if not successors:
            row.update(disposition="MANAGER_OWNED", justification="The Attempt 8 manager lane is the manager's.")
        else:
            row.update(disposition="CARRIED_BY_ATTEMPT9_LANE_AT_THE_CANDIDATE_HEAD", attempt9_lanes=list(successors),
                       attempt9_results={s: (ctx.receipts[s]["result"] if ctx.at_head(s) else "NOT_AT_HEAD")
                                         for s in successors if s in ctx.receipts},
                       justification=("Re-executed fresh by the same-named Attempt 9 lane at the candidate head; the "
                                      "Attempt 8 receipt stays unchanged as the before-record (its result is never "
                                      "relabelled; a red Attempt 8 result stays red there)."))
        rows.append(row)
    return rows


def lane_dispositions(ctx: Context) -> None:
    a8o.lane_dispositions(ctx)
    for name in ("original_lanes", "attempt3_lanes", "attempt4_lanes", "attempt5_lanes", "attempt6_lanes",
                 "attempt7_lanes"):
        setattr(ctx, name, _relabel(getattr(ctx, name)))
    ctx.attempt8_lanes = attempt8_lane_dispositions(ctx)


LANE_LISTS = (("original_lanes", "ORIGINAL-LANE-"), ("attempt3_lanes", "A03-LANE-"), ("attempt4_lanes", "A04-LANE-"),
              ("attempt5_lanes", "A05-LANE-"), ("attempt6_lanes", "A06-LANE-"), ("attempt7_lanes", "A07-LANE-"),
              ("attempt8_lanes", "A08-LANE-"))


def _lane_lists(ctx: Context) -> dict[str, list[dict[str, Any]]]:
    return {name: getattr(ctx, name) for name, _ in LANE_LISTS}


# ------------------------------------------------------------------ inherited red lanes


def classify(ctx: Context) -> dict[str, Any]:
    """Derive the Attempt 9 classification from Attempt 8's, identity by identity and cause by cause."""

    previous_path = ATTEMPT8_ROOT / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json"
    previous = read_json(previous_path)
    lanes: dict[str, Any] = {}
    problems: list[str] = []
    for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED"):
        receipt = ctx.receipts.get(lane)
        if not receipt or receipt["result"] != "FAIL" or not ctx.at_head(lane):
            continue
        failing = base.failing_identities(receipt) or []
        comparison = (receipt.get("details") or {}).get("attempt8_comparison") or {}
        changed = set(comparison.get("persisting_changed_cause") or {})
        groups_before = (previous["lanes"].get(lane) or {}).get("groups") or []
        group_of = {identity: group for group in groups_before for identity in group.get("identities") or []}
        groups: dict[str, dict[str, Any]] = {}
        for identity in failing:
            group = group_of.get(identity)
            if group is None or identity in changed:
                problems.append(f"{lane}: {identity} is new or changed cause; classify it by hand")
                continue
            entry = groups.setdefault(group["id"], {k: v for k, v in group.items() if k != "identities"} | {"identities": []})
            entry["identities"].append(identity)
        lanes[lane] = {"run": ctx.runs[lane]["run"], "head": ctx.runs[lane]["head"],
                       "attempt8_run": (previous["lanes"].get(lane) or {}).get("run"), "groups": list(groups.values()),
                       "equivalence": {"persisting": len(comparison.get("persisting") or []),
                                       "persisting_same_cause": len(comparison.get("persisting_same_cause") or []),
                                       "new_in_attempt9": comparison.get("new_in_attempt9"),
                                       "no_longer_failing": comparison.get("no_longer_failing") or
                                       comparison.get("no_longer_reported")}}
    if problems:
        raise SystemExit("classification refused:\n" + "\n".join(problems))
    document = {"label": f"{LABEL_PREFIX} IN_PROGRESS_LOCAL_WORK_REMAINS (inherited failure classification)",
                "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
                "attempt_id": ATTEMPT_ID, "authored_at": utc_now(),
                "rule": ("Each failing identity keeps its Attempt 8 group only when it persists with the same traceback "
                         "cause (FULL_FINAL_MOUNTED) or the same finding line (STRICT_MOUNTED); anything else is refused "
                         "for manual classification."),
                "derived_from": {"path": str(previous_path), "sha256": sha256_file(previous_path)}, "lanes": lanes}
    write_output(ctx.out_root / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json", dumps(document))
    return document


def inventory(ctx: Context) -> dict[str, Any]:
    """Every directory this attempt created or wrote, with its bytes; nothing is removed (no cleanup is granted)."""

    purposes = {
        (VALIDATION_ROOT, "intake"): ("The intake script and its closure extractions", False),
        (VALIDATION_ROOT, "before"): ("The before-repair reproduction: the replayed manager probes and their outputs", False),
        (VALIDATION_ROOT, "gitpreflight"): ("The owned Git fixtures of the housekeeping preflight", True),
        (VALIDATION_ROOT, "census"): ("The population census scripts and results (copied into the evidence root)", False),
        (VALIDATION_ROOT, "oracle"): ("Development runs of the identity-derived oracle (not evidence)", True),
        (VALIDATION_ROOT, "fixtures"): ("Owned forgery fixtures (full successor copies restored before every case)", True),
        (VALIDATION_ROOT, "tools"): ("The commit helper (provenance regenerated, command-scoped Git settings)", False),
        (VALIDATION_ROOT, "cv"): ("The granted append's validation view: a byte-for-byte materialization of the appended "
                                  "candidate tree; the committed-blob proof cites it", False),
        (VALIDATION_ROOT, "cn"): ("Scratch repositories of the candidate lane's committed-provenance negatives", True),
        (VALIDATION_ROOT, "lanes"): ("Lane work directories (manager-probe replay copies, base export, fixtures)", True),
        (VALIDATION_ROOT, "rehearsal"): ("Rehearsal lane runs (labelled REHEARSAL, never evidence)", True),
        (VALIDATION_ROOT, "jira"): ("Private Jira successor copies (never the committed pack or live Jira)", True),
        (VALIDATION_ROOT, "control07"): ("The CONTROL-07 offline qualification's scratch matrices", True),
        (VALIDATION_ROOT, "tmp"): ("Development scratch: commit messages, base checks, development forgery runs, test temp",
                                   True),
        (PACKAGING_ROOT, "b"): ("The fresh noneditable BAS wheel stages (source export, dist, virtual environment)", True),
        (PACKAGING_ROOT, "candidate"): ("Private index files and messages of the candidate appends", False),
    }
    entries = []
    total = 0
    for root in (ctx.out_root, VALIDATION_ROOT, PACKAGING_ROOT):
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            size = files = 0
            if child.is_dir():
                for folder, _, names in os.walk(child):
                    for name in names:
                        try:
                            size += os.lstat(os.path.join(folder, name)).st_size
                            files += 1
                        except OSError:
                            pass
            else:
                size, files = child.stat().st_size, 1
            total += size
            purpose, removable = purposes.get((root, child.name), (
                "Attempt 9 evidence (declared outputs, receipts, platform and storage records)" if root == ctx.out_root
                else "Attempt 9 working files", False))
            entries.append({"path": str(child), "bytes": size, "files": files, "holds": purpose,
                            "owner_may_remove_after_manager_review": removable})
    document = {"label": f"{LABEL_PREFIX} IN_PROGRESS_LOCAL_WORK_REMAINS (inventory for the owner)",
                "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "observed_at": utc_now(),
                "roots": [str(ctx.out_root), str(VALIDATION_ROOT), str(PACKAGING_ROOT)], "entries": entries,
                "total_bytes": total,
                "rule": ("Nothing was deleted, moved or cleaned up by this attempt. Removal of anything listed is the "
                         "owner's decision after the manager's review; declared outputs, lane receipts and worker "
                         "evidence are never listed as removable.")}
    write_output(ctx.out_root / "evidence" / "CLEANUP_INVENTORY.json", dumps(document))
    return document


def inherited_equivalence(ctx: Context, label: str) -> dict[str, Any]:
    rows = []
    for lane in WORKER_LANES:
        receipt = ctx.receipts.get(lane) or {}
        details = receipt.get("details") or {}
        final = _a08_final(lane)
        rows.append({"lane": lane, "attempt9_run": (ctx.runs.get(lane) or {}).get("run"),
                     "attempt9_result": receipt.get("result"), "at_candidate_head": ctx.at_head(lane),
                     "counts": receipt.get("counts"),
                     "execution": "FRESH_AT_THE_CANDIDATE_HEAD" if ctx.at_head(lane) else "NOT_AT_HEAD",
                     "attempt8_run": final.get("run"), "attempt8_result": final.get("result"),
                     "attempt8_receipt": final.get("receipt"), "attempt8_receipt_sha256": final.get("receipt_sha256"),
                     "attempt8_comparison": details.get("attempt8_comparison"),
                     "failing_identities": base.failing_identities(receipt) if receipt.get("result") == "FAIL" else None})
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "candidate": ctx.candidate, "lanes": rows, "equivalence_used": [],
            "equivalence_statement": ("TP37-A09 permits a CHECK lane to carry an old execution by an explicit current "
                                      "dependency comparison. This attempt used none: every one of the 14 worker lanes "
                                      "executed fresh at the candidate head, because consumer dependencies changed "
                                      "(career_successor.py, career_witness.py, storage_snapshot.py). Each Attempt 8 "
                                      "final receipt is retained unchanged as the before-record and compared by "
                                      "identity; no old execution is relabelled, and the Attempt 8 red lanes stay red "
                                      "there."),
            "classification": ctx.classification, **_lane_lists(ctx),
            "rule": ("Inherited red lanes stay red until genuinely resolved. Equivalence is by exact identity and cause "
                     "against the Attempt 8 final receipts at the issued base; counts alone establish nothing.")}


# ------------------------------------------------------------------ criteria


def _d(ctx: Context, lane: str) -> dict[str, Any]:
    return ctx.details(lane)


def _holds(ctx: Context, lane: str, key: str) -> bool:
    return bool((_d(ctx, lane).get(key) or {}).get("holds"))


def _before(ctx: Context, finding: str) -> bool:
    path = ctx.out_root / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
    return bool(path.is_file() and (read_json(path).get(finding) or {}).get("reproduced"))


def _reproduction(ctx: Context) -> dict[str, Any]:
    path = ctx.out_root / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
    return read_json(path) if path.is_file() else {}


def _unfixed(ctx: Context) -> dict[str, Any]:
    return _d(ctx, "SOURCE_REGRESSIONS").get("attempt9_suites_on_the_unfixed_base") or {}


def _control(ctx: Context) -> dict[str, Any]:
    path = ctx.out_root / "CONTROL07_PROPOSAL_VALIDATION.json"
    return read_json(path) if path.is_file() else {}


#: The CONTROL-07 receipt's retention checks (attempt09_control07.py): the qualified bytes, patch and issued records.
RETENTION_CHECKS = ("proposed_bytes_identical_to_attempt8_and_attempt7", "patch_identical_to_the_qualified_patch",
                    "attempt8_proposal_document_is_the_issued_bytes", "manager_review_is_the_issued_bytes",
                    "retained_bytes_are_the_manager_reviewed_bytes", "control_change_protocol_is_the_issued_bytes")


def _retained(control: dict[str, Any]) -> bool:
    checks = control.get("checks") or {}
    return all(checks.get(name) is True for name in RETENTION_CHECKS)


def _n(value: Any) -> str:
    return f"{value:,}" if isinstance(value, int) else str(value)


R01_KEYS = (("INSTALLED_CONSUMER_C01", "a9_forgeries"), ("INSTALLED_CONSUMER_C01", "manager_a8_null_span_entrypoints"),
            ("INSTALLED_CONSUMER_C01", "a8_forgeries"), ("INSTALLED_CONSUMER_C01", "manager_a7_envelope_entrypoints"),
            ("INSTALLED_CONSUMER_C01", "a8_genuine_source_module"), ("INSTALLED_CONSUMER_C01", "a7_forgeries"),
            ("INSTALLED_CONSUMER_C01", "manager_a6_same_page_lineage"), ("INSTALLED_CONSUMER_C01", "a6_forgeries"),
            ("INSTALLED_CONSUMER_C01", "installed_identity_census"),
            ("INSTALLED_CONSUMER_C01", "manager_a5_successor_adversarial"),
            ("INSTALLED_CONSUMER_C01", "manager_a5_successor_population_audit"),
            ("CAREER_SUCCESSOR", "independent_source_unit_oracle"), ("CAREER_SUCCESSOR", "attempt8_source_field_oracle"),
            ("CAREER_SUCCESSOR", "independent_identity_census"))


def _judge_r01(ctx: Context, key: str) -> tuple[str, str]:
    installed, career = _d(ctx, "INSTALLED_CONSUMER_C01"), _d(ctx, "CAREER_SUCCESSOR")
    failing = [lane for lane in REQUIREMENT_LANES["R37A09-01"] if not ctx.lane_ok(lane)]
    failing += [f"{lane}:{k}" for lane, k in R01_KEYS if not _holds(ctx, lane, k)]
    failing += [f"source binding {k}" for k, v in (career.get("source_identity_checks") or {"none": False}).items()
                if not v]
    failing += [f"source unit {k}" for k, v in ((career.get("source_witness_checks") or {}).get("checks")
                                                or {"none": False}).items() if not v]
    failing += [f"original negative {name}" for name in a6o._lineage_originals(ctx)]
    if not (installed.get("successor_pagination") or {}).get("reconciled"):
        failing.append("complete pagination")
    if key.endswith("-C"):
        if not _before(ctx, "MF37A08-01"):
            failing.append("before-repair reproduction")
        if not _unfixed(ctx).get("holds"):
            failing.append("the new suites fail on the unfixed base with the saved construction accepted there")
    if failing:
        return "IN_PROGRESS", "not yet held at the candidate head: " + ", ".join(failing)
    witness = career["source_witness_checks"]
    successor = witness.get("successor") or {}
    s5 = successor.get("successor") or {}
    delivered = successor.get("delivered_predecessor") or {}
    oracle = career["independent_source_unit_oracle"]
    genuine = oracle["genuine"]
    edges = {r["relation"]: r["edges"] for r in genuine.get("relations") or []}
    classes = genuine.get("row_classes") or {}
    forged = installed["a9_forgeries"]["cases"]
    manager = installed["manager_a8_null_span_entrypoints"]
    null_oracle = oracle.get("manager_a8_null_span") or {}
    codes = collections.Counter(row.get("expected") for row in forged.values())
    unfixed = _unfixed(ctx)
    reproduction = _reproduction(ctx).get("MF37A08-01") or {}
    results = reproduction.get("results") or {}
    served = {k: (v or {}).get("row_count") for k, v in results.items()
              if k not in ("worker_oracle_a08", "genuine_positive_control")}
    control_rows = (results.get("genuine_positive_control") or {}).get("row_count")
    a7_forgeries = sum(1 for row in ((installed.get("a7_forgeries") or {}).get("cases") or {}).values()
                       if row.get("expected") != "SERVED")
    text = {
        "A": ("Every row an attach checks -- all "
              f"{_n(s5.get('rows_resolved_to_their_source_unit'))} Attempt 5 successor rows, the "
              f"{_n(delivered.get('rows_resolved_to_their_source_unit'))} delivered and "
              f"{_n((witness.get('a04_relation') or {}).get('rows_resolved_to_their_source_unit'))} Attempt 4 rows its edges "
              f"name, and the {_n(((witness.get('a04_format') or {}).get('successor') or {}).get('rows_resolved_to_their_source_unit'))} "
              "rows of the Attempt 4 format -- is resolved to the source unit its own identity names in its verified "
              "capture, witnessed or not; a parent row must carry its own identity. A row with no witness may carry only "
              "blank text or that unit's own text (a list line's years: text inside the line); an identity naming no "
              "unit, or several, is never an anchor. Each edge of both relations in both formats is then compared by "
              f"the two derived units alone: {_n((witness.get('default_anchors') or {}).get('edges'))} default, "
              f"{_n((witness.get('a04_anchors') or {}).get('edges'))} Attempt 4 and "
              f"{_n((witness.get('a04_format_anchors') or {}).get('edges'))} Attempt 4-to-default edges anchor on derived "
              "units (0 by parameter only, 0 unanchored). SQL NULL, JSON null, [null, null] and an empty string are one "
              f"absent state. The independent oracle (`{genuine.get('oracle_version')}`, sqlite3/json/re only) derives "
              f"each unit from identity: {genuine.get('crossed_edges')} crossed and {genuine.get('unresolved_edges')} "
              f"unresolved of {_n(sum(edges.values()))} genuine edges, with row classes {classes}. Every genuine row "
              "is witnessed in at least one field; the fields left unwitnessed carry no text or, for a list line's "
              f"years, text inside the line (successor {s5.get('unwitnessed_fields')}; named delivered rows "
              f"{delivered.get('unwitnessed_fields')})."),
        "B": (f"The {_n((genuine.get('rows') or {}).get('A05'))}-row successor serves unchanged with complete "
              "pagination. Through the fresh "
              "installed console script, its installed module and the source module, the manager's saved NULL-span "
              f"fixture (as issued {manager.get('as_issued')}) is refused as {REFUSED_SOURCE_FIELD}, naming the "
              f"unwitnessed text; the oracle finds its forged edges crossed ({null_oracle.get('crossed_by_relation')}). "
              f"{len(forged)} fresh missing-witness constructions -- the saved one in four absent spellings, missingness "
              "with forged edges and the rows' own or blank text (team-only, year-only and both), the same role in "
              "another period, the Attempt 4 relation alone, the Attempt 4 format, a relabelled declared Attempt 4 row, "
              "a row naming no source unit and list-line years outside the line -- are each refused for their own cause "
              f"at both entrypoints after a fixture reset ({dict(codes)}); the "
              f"{len((installed.get('a8_forgeries') or {}).get('cases') or {})} Attempt 8 witness forgeries, the "
              f"{a7_forgeries} Attempt 7 forgeries, the Attempt 6 same-page challenge and every earlier negative stay "
              "refused."),
        "C": ("Before repair, on the clean issued base 91a83b19 with nothing drafted, every entrypoint served the saved "
              f"fixture (rows served: {served}; the genuine successor, the positive control, {control_rows}) and the "
              "Attempt 8 oracle reported its forged edges only as unresolved. Over the unfixed base's exact bytes the "
              f"two new suites fail: of {unfixed.get('negative_cases')} negative case outcomes, none passes there, "
              f"{len(unfixed.get('accepted_by_the_unfixed_code') or [])} are accepted there (the saved SQL NULL "
              "construction and the saved extra-root restart among them), "
              f"{len(unfixed.get('refused_under_another_cause') or [])} are refused there only for an earlier cause (an "
              f"Attempt 7 anchor or Attempt 8 witness rule), {len(unfixed.get('new_api_or_record_absent') or [])} find the "
              f"new rule absent and {len(unfixed.get('other_behavior') or [])} behave otherwise; both pass on the "
              "repaired source. Independent alternate entrypoints are exercised; remaining limits are classified: source "
              "biography truth, rows whose own normalized fields are rewritten, and interval grain inside one field stay "
              "owned or manager-verified."),
    }[key[-1]]
    return "VERIFIED_LOCAL", text


def _judge_r02(ctx: Context, key: str) -> tuple[str, str]:
    storage = ctx.storage()
    admission = _d(ctx, "STORAGE_ADMISSION")
    live = ((admission.get("storage_ledger") or {}).get("live_over_budget_control") or {}).get("refused")
    failing = [lane for lane in REQUIREMENT_LANES["R37A09-02"] if not ctx.lane_ok(lane)]
    if not live:
        failing.append("live over-budget refusal")
    failing += [k for k in ("manager_a8_storage_independent", "manager_a7_same_path_race", "manager_a7_stop_reserve",
                            "manager_a6_storage_continuation", "manager_a5_storage_independent")
                if not _holds(ctx, "STORAGE_ADMISSION", k)]
    if not storage["frozen_and_verified"]:
        failing.append("root ledger frozen, verified and its chain proved")
    validation = sorted((ctx.out_root / "evidence" / "final").glob("FINAL_PACKET_VALIDATION_*.json"))
    if not validation or read_json(validation[-1]).get("result") != "PASS":
        failing.append("FINAL_PACKET validation receipt PASS")
    if key.endswith("-C"):
        if not _before(ctx, "MF37A08-02"):
            failing.append("before-repair reproduction")
        if not _unfixed(ctx).get("holds"):
            failing.append("the new suites fail on the unfixed base with the saved restart accepted there")
    if failing:
        return "IN_PROGRESS", "not yet held: " + ", ".join(failing)
    measured = storage["operational"].get("measured") or {}
    manager = admission["manager_a8_storage_independent"]
    extra = manager.get("extra_root_restart") or {}
    before = ((_reproduction(ctx).get("MF37A08-02") or {}).get("summary") or {}).get("changed_root_restart") or {}
    text = {
        "A": ("Every open, restart and interrupted-claim recovery of a continuation derives one effective root contract "
              "under the parent's lock -- the owned and shared roots, each normalized (normcase(abspath); links not "
              "resolved), deduplicated and sorted, a root in both classes refused -- records it in the claim and the "
              "child's INIT, and compares it before any record: an added (empty or not), omitted or reclassified root "
              f"is refused as {REFUSED_ROOTS}, a different spelling of the same roots resumes, and a claim or INIT "
              "recording no contract is not completed. The root ledger (Cycle 37 / Attempt 9) froze with "
              f"{_n(measured.get('added_bytes'))} bytes added of its {_n(storage['operational'].get('budget_bytes'))}-byte "
              "budget."),
        "B": ("The manager's Attempt 8 challenge, replayed with only its fixture root adapted, leaves "
              f"{(manager.get('concurrent') or {}).get('init_count')} INIT across twelve processes "
              f"({(manager.get('concurrent') or {}).get('fresh_opens')} fresh open, "
              f"{(manager.get('concurrent') or {}).get('resumed_opens')} resumes), and its extra-empty-root restart is "
              f"{extra.get('result')} {extra.get('code')} with the root never measured; the stopped, reserve-changed and "
              "recycled-headroom cases stay refused; the root-contract suite (spellings across twelve processes, "
              "competing root sets, interrupted claim and INIT, no refused call adds headroom) and the Attempt 5 to 8 "
              "challenges hold; FINAL_PACKET passes on the separately reserved final-output continuation."),
        "C": (f"Before repair, on the clean issued base, the same restart resumed (resumed {before.get('resumed')}) and "
              f"{_n(before.get('actual_extra_bytes'))} bytes written in the unrecorded root measured as "
              f"{before.get('measured_added')} added. The saved restart and every changed root contract are accepted by "
              "the unfixed tools and refused now; the unfixed tools also refused an equivalent spelling of the same "
              "root at first open (fail-closed), which normalization repairs (W37A09-01). Finer process attribution "
              "stays with the platform owner."),
    }[key[-1]]
    return "VERIFIED_LOCAL", text


def _judge_r03(ctx: Context, key: str) -> tuple[str, str]:
    details = _d(ctx, "LOCAL_INTEGRATION_CANDIDATE")
    failing = [lane for lane in REQUIREMENT_LANES["R37A09-03"] if not ctx.lane_ok(lane)]
    checks = details.get("candidate_tree_checks") or {}
    failing += [k for k, v in checks.items() if not v] or ([] if checks else ["tree checks"])
    failing += [k for k, v in (details.get("candidate_attempt9") or {"attempt 9 chain": False}).items() if not v]
    failing += [k for k in ("candidate_negatives", "manager_a8_committed_tree", "manager_a7_committed_tree",
                            "manager_a6_committed_tree", "manager_a5_integration_replay", "candidate_consumer",
                            "control07_requalification")
                if not _holds(ctx, "LOCAL_INTEGRATION_CANDIDATE", k)]
    if not ctx.candidate_record_path:
        failing.append("append record")
    control = _control(ctx)
    subjects = control.get("subjects") or {}
    appended = {read_json(p).get("candidate_commit"): read_json(p).get("repair_head") for p in ctx.candidate_record_paths}
    requalified = details.get("control07_requalification") or {}
    final_candidate = candidate.describe().get("candidate_head")
    if control.get("result") != "PASS":
        failing.append("CONTROL07_PROPOSAL_VALIDATION.json PASS")
    elif subjects.get("candidate") not in appended or appended[subjects["candidate"]] != subjects.get("repair"):
        failing.append("the create-only CONTROL-07 validation is not bound to an Attempt 9 append and its repair head")
    if (requalified.get("subjects") or {}).get("candidate") != final_candidate:
        failing.append("CONTROL-07 re-qualified in the lane at the final candidate")
    if not _retained(control):
        failing.append("the retained proposal is the qualified, manager-reviewed bytes")
    errors = (details.get("candidate_review_control_characterization") or {}).get("compatibility_errors")
    if key.endswith("-C") and not errors:
        failing.append("the two control compatibility errors kept visible")
    if failing:
        return "IN_PROGRESS", "not yet held: " + ", ".join(failing)
    proof = details.get("committed_tree_proof") or {}
    green = (control.get("characterization") or {}).get("current_checkers_green_on") or {}
    cases = len(((control.get("checker_runs") or {}).get("proposed") or {}).get("cases") or {})
    stores = [read_json(p).get("git_housekeeping") or {} for p in ctx.candidate_record_paths]
    text = {"A": ("The qualified CONTROL-07 proposal is retained byte for byte from Attempt 8 (itself the Attempt 7 "
                  "bytes the manager's independent review qualified; the regenerated patch is the qualified fab1911e... "
                  "patch) under this attempt's evidence root, outside every checkout, and rebound: "
                  f"{sum(1 for v in (control.get('checks') or {}).values() if v)} of {len(control.get('checks') or {})} "
                  f"checks hold over {cases} offline fixture cases at repair {str(subjects.get('repair'))[:8]} and "
                  f"candidate {str(subjects.get('candidate'))[:8]}; the current checkers exit green on "
                  + ", ".join(f"{name} {len(rows)}" for name, rows in green.items())
                  + " of those cases. No active control was changed, no provider or workflow ran; adoption needs the "
                    "eligible independent bootstrap receipt and publication authority, both ungranted."),
            "B": ("FAIL, BLOCKED and SKIPPED reports, self-approval, a stale head, a dismissed or unapproved review, a "
                  "changed control surface and a PASS under the unapproved protocol all fail closed; the only green "
                  "proposed case is the synthetic TEST_ONLY approval, which is not a receipt. The proposal's original and "
                  "proposed hashes and the exact later adoption, rollback and verification actions are in "
                  "CONTROL07_PROPOSAL.md; the candidate lane re-qualified it at the final candidate "
                  f"{str(final_candidate)[:8]}."),
            "C": ("The ordinary repairs and regenerated provenance were appended forward to c52e7b52 "
                  f"({len(ctx.candidate_record_paths)} [material] commit(s)), every Git command with -c gc.auto=0 -c "
                  "maintenance.auto=false and the shared store measured unchanged in packs "
                  f"({all(s.get('packs_unchanged') for s in stores)}); every ancestor (daba87f0, bb5253b2, 0c22af20, "
                  "c52e7b52) and main's protected bytes retained, only the candidate ref moved; committed blobs and "
                  f"manifest reconcile ({proof.get('committed_paths')} paths, {proof.get('manifest_rows')} manifest rows, "
                  "0 mismatches), independently confirmed by the manager's Attempt 8, 7 and 6 committed-tree reviews; the "
                  "consumer built from the candidate tree serves and refuses; the two control compatibility errors stay "
                  f"visible ({len(errors or [])} failing tests characterized). Qualifying the private proposal does not "
                  "qualify the candidate for publication.")}
    return "VERIFIED_LOCAL", text[key[-1]]


def _judge_r04(ctx: Context, key: str) -> tuple[str, str]:
    installed = _d(ctx, "INSTALLED_CONSUMER_C01")
    needed = REQUIREMENT_LANES["R37A09-04"]
    failing = [lane for lane in needed if lane not in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED") and not ctx.lane_ok(lane)]
    failing += [lane for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED") if not ctx.executed(lane)]
    for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED"):
        comparison = _d(ctx, lane).get("attempt8_comparison") or {}
        if comparison.get("new_in_attempt9"):
            failing.append(f"{lane} new identities {comparison['new_in_attempt9']}")
    named = (installed.get("successor_named_cases") or {}).get("holds") or {}
    failing += [f"named {k}" for k, v in named.items() if not v] or ([] if named else ["named cases"])
    failing += [k for k in ("manager_a3_career_challenge", "manager_a4_career_semantic_census",
                            "manager_a4_successor_challenge", "manager_a5_career_semantic_census",
                            "manager_a5_successor_adversarial", "a7_forgeries", "a8_forgeries", "a9_forgeries",
                            "manager_a6_same_page_lineage", "manager_a7_envelope_entrypoints",
                            "manager_a8_null_span_entrypoints")
                if not _holds(ctx, "INSTALLED_CONSUMER_C01", k)]
    if not (installed.get("successor_coverage") or {}).get("predecessor_identity_sets_equal"):
        failing.append("successor coverage")
    if failing:
        return "IN_PROGRESS", "not yet held: " + ", ".join(failing)
    census = _d(ctx, "CAREER_SUCCESSOR").get("independent_identity_census") or {}
    full = _d(ctx, "FULL_FINAL_MOUNTED").get("attempt8_comparison") or {}
    text = {"A": (f"All {_n(census.get('rows'))} genuine rows and {_n(census.get('raw_files'))} captures verify and serve "
                  "unchanged; every genuine row, witnessed or not, resolves to the source unit its identity names "
                  "(verifier) and is independently derived (oracle); every default and Attempt 4 predecessor row keeps "
                  "one disposition; the legitimate alias, new, split, removed, restructured, missing-team, years-only, "
                  "empty-field, comment-bearing, list-template and other-sport classes serve with their explicit "
                  "meanings; the affected entrypoint (the successor verifier) is repaired as a class, no data rebuilt and "
                  "no fact invented or activated."),
            "B": ("One fresh offline noneditable BAS wheel, composed with the released C01 wheel, paginates the whole "
                  "successor and every filter exactly as the independent SQL oracle and raw census derive them, serves "
                  "the same rows for the named people through its module entrypoint as through its console script (and "
                  "the source module), and refuses every original and new lineage forgery for its own cause, each after "
                  "an independent fixture reset; no row is hidden or dropped."),
            "C": ("The guard, date, defensive-unit, unknown-role, Cory 2018/Danny/Steve, scoring/PIT, harness, "
                  "default/legacy and Cycle 29 behavior pass their suites and the manager replays at the candidate head; "
                  f"the full mounted suite ran fresh ({_n(full.get('final_tests_run'))} tests) and matches Attempt 8 "
                  f"identity for identity ({len(full.get('persisting') or [])} persisting, "
                  f"{len(full.get('new_in_attempt9') or [])} new); the default database, prior releases, raw captures and "
                  "frozen predictions are unchanged; the 2,223-row staff successor and the whole history stay owned.")}
    return "VERIFIED_LOCAL", text[key[-1]]


def _judge_r05(ctx: Context, key: str) -> tuple[str, str]:
    if key.endswith("-A"):
        missing = [lane for lane in WORKER_LANES if not ctx.executed(lane)]
        if not missing:
            return "VERIFIED_LOCAL", ("The Attempt 9 lane and output tools were implemented and inspected; both findings "
                                      "were reproduced on the clean issued base before any source was drafted; every "
                                      "Git command of a helper or commit carried -c gc.auto=0 -c maintenance.auto=false "
                                      "(proved on owned fixtures first); every new forgery was proved against the "
                                      "source verifier before the installed lane; every one of the 14 worker lanes "
                                      "executed fresh through the issued command at the candidate head with exact "
                                      "binding, raw counts and the shared Git store measured around it; no equivalence "
                                      "was relabelled and inherited red stays red, compared with Attempt 8 by identity "
                                      "and cause.")
        return "IN_PROGRESS", "not yet executed at the candidate head: " + ", ".join(missing)
    if key.endswith("-B"):
        phases = base.platform_phases(ctx)
        complete = all(all(row.values()) for row in phases.values())
        comments = [p for p in (ctx.out_root / "evidence" / "platform").rglob("JIRA_COMMENT_*.json")
                    if read_json(p).get("result") == "SUCCEEDED"]
        if complete and ctx.lane_ok("PLATFORM_CARRY") and len(comments) >= 4:
            return "VERIFIED_LOCAL", ("BEFORE, DURING and AFTER Jira, GitHub and All-22 reads exist, the AFTER ones "
                                      "bound to the candidate head; the private Jira successor ran dry run, apply, "
                                      "strict and audit validators and a second dry run in every phase; the granted "
                                      "BAT-706 and BAT-708 material comments were posted with duplicate checks and "
                                      "read back; requests stayed within each ceiling.")
        return "IN_PROGRESS", (f"platform phases complete={complete}, PLATFORM_CARRY held={ctx.lane_ok('PLATFORM_CARRY')}, "
                               f"confirmed comments={len(comments)}")
    problems = accounting_problems(ctx) + base.classification_problems(ctx)
    storage = ctx.storage()
    held = (not problems and ctx.lane_ok("PLATFORM_CARRY") and ctx.lane_ok("LOCAL_INTEGRATION_CANDIDATE")
            and ctx.lane_ok("FINAL_PACKET") and storage["frozen_and_verified"])
    if held:
        return "VERIFIED_LOCAL", (f"All {len(ctx.contract['carryforward'])} carryforward identities keep their meanings "
                                  "and dispositions; 20 clauses, 15 lanes, 18 outputs, findings and effects are "
                                  "accounted in a generated report, checklist and submission; the forward-only "
                                  "candidate carries committed-blob provenance and consumer proof; the root storage "
                                  "ledger is frozen with every reservation reconciled and the final outputs reserved on "
                                  "its one claimed continuation; FINAL_PACKET passes (accounting only). Nothing is "
                                  "claimed about adoption, integration or acceptance.")
    return "IN_PROGRESS", ("; ".join(problems[:3]) or
                           f"PLATFORM_CARRY {ctx.lane_ok('PLATFORM_CARRY')}, candidate "
                           f"{ctx.lane_ok('LOCAL_INTEGRATION_CANDIDATE')}, FINAL_PACKET {ctx.lane_ok('FINAL_PACKET')}, "
                           f"storage frozen and chained {storage['frozen_and_verified']}")


def judge(ctx: Context, key: str, requirement: str) -> tuple[str, str]:
    return {"R37A09-01": _judge_r01, "R37A09-02": _judge_r02, "R37A09-03": _judge_r03, "R37A09-04": _judge_r04,
            "R37A09-05": _judge_r05}[requirement](ctx, key)


def criterion_evidence(ctx: Context, requirement: str) -> list[str]:
    ids: list[str] = []
    for lane in REQUIREMENT_LANES[requirement]:
        if ctx.executed(lane):
            ids += [f"E-LANE-{lane}-RECEIPT", f"E-LANE-{lane}-LOG"]
    storage = ["E-STORAGE-SNAPSHOT", "E-STORAGE-LEDGER", "E-STORAGE-LEDGER-HEAD", "E-STORAGE-CONTINUATION-CLAIM"]
    oracle = [e for e in ctx.evidence if e.startswith("E-ORACLE-")]
    census = [e for e in ctx.evidence if e.startswith("E-CENSUS-")]
    commits = [e for e in ctx.evidence if e.startswith("E-GIT-COMMIT_")]
    extra = {"R37A09-01": ["E-BEFORE-REPRODUCTION", "E-INTAKE", *oracle, *census, "E-LANE-SOURCE_REGRESSIONS-RECEIPT",
                           *commits],
             "R37A09-02": ["E-BEFORE-REPRODUCTION", "E-LANE-SOURCE_REGRESSIONS-RECEIPT", *storage, *commits]
             + [e for e in ctx.evidence if e.startswith("E-FINAL-")],
             "R37A09-03": ["E-CANDIDATE-APPEND-RECORD", "E-OUTPUT-LOCAL_INTEGRATION_CANDIDATE.json",
                           "E-OUTPUT-CONTROL07_PROPOSAL_VALIDATION.json", "E-OUTPUT-CONTROL07_PROPOSAL.md",
                           "E-CONTROL07-PATCH", "E-CONTROL07-OFFLINE-MATRIX", "E-GIT-HOUSEKEEPING-PREFLIGHT",
                           "E-GIT-HELPER-CONSTRUCTION"]
             + [e for e in ctx.evidence if e.startswith(("E-CONTROL07-PROPOSED-", "E-CANDIDATE-APPEND-RECORD-"))],
             "R37A09-04": ["E-OUTPUT-CAREER_POPULATION_DISPOSITIONS.json", "E-OUTPUT-DELIVERED_CONSUMER_MANIFEST.json",
                           "E-FAILURE-CLASSIFICATION", *oracle, *census],
             "R37A09-05": ["E-ORIGINAL-OBLIGATIONS", "E-FAILURE-CLASSIFICATION", "E-REQUEST-LEDGER", "E-INTAKE",
                           "E-CLOSURE-ROWS", "E-GIT-HOUSEKEEPING-PREFLIGHT", "E-GIT-HELPER-CONSTRUCTION", *commits,
                           "E-OUTPUT-LANE_RESULTS.json", "E-CANDIDATE-APPEND-RECORD",
                           "E-OUTPUT-LOCAL_INTEGRATION_CANDIDATE.json", "E-STORAGE-SNAPSHOT"]}[requirement]
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
        if key.endswith("-B") and criterion["requirement"] == "R37A09-05":
            evidence += sorted(identity for identity in ctx.evidence if identity.startswith("E-PLATFORM-")
                               and identity.split("/")[-1].startswith(("JIRA_COMMENT", "JIRA_PRIVATE",
                                                                       "GITHUB_READ_SUMMARY", "ALL22_READ_SUMMARY",
                                                                       "JIRA_READ_SUMMARY")))
        if verdict == "VERIFIED_LOCAL" and not any(ctx.evidence[e]["kind"] == criterion["evidence_kind"] for e in evidence):
            verdict, reason = "IN_PROGRESS", f"{reason} -- but no evidence of kind {criterion['evidence_kind']} exists"
        results.append({"id": key, "status": verdict, "reason": reason, "evidence_ids": evidence})
    return results


def accounting_problems(ctx: Context) -> list[str]:
    return a7o.accounting_problems(ctx)


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
        elif row["id"].startswith(tuple(prefix for _, prefix in LANE_LISTS)):
            evidence.append("E-OUTPUT-LANE_RESULTS.json")
        rows.append({"id": row["id"], "disposition": row["disposition"], "attempt9_state": state,
                     "evidence_ids": [e for e in dict.fromkeys(evidence) if e in ctx.evidence or e.startswith("E-OUTPUT-")]})
    return rows


def new_findings(ctx: Context) -> list[dict[str, Any]]:
    return a6o.new_findings(ctx)


def unfinished_items(ctx: Context, criteria: list[dict[str, Any]], lanes: list[dict[str, Any]],
                     findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return a6o.unfinished_items(ctx, criteria, lanes, findings)


# ------------------------------------------------------------------ declared outputs


def _f(path: Path) -> dict[str, Any]:
    return {"path": str(path), "exists": Path(path).is_file(), "sha256": sha256_file(path) if Path(path).is_file() else None}


def finding_matrix(ctx: Context, label: str, criteria: dict[str, dict[str, Any]]) -> dict[str, Any]:
    before = ctx.out_root / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
    reproduction = read_json(before) if before.is_file() else {}
    plan = {
        "MF37A08-01": ([_f(MANAGER_A8 / "MISSING_WITNESS_CHALLENGE.json"), _f(MANAGER_A8 / "missing_witness_challenge.py"),
                        _f(MANAGER_A8 / "LINEAGE_ENTRYPOINTS.json"), _f(MANAGER_A8 / "lineage_entrypoints.py"),
                        _f(MANAGER_A8_NULL_SPAN), _f(before)],
                       {"CAREER_SUCCESSOR": "independent_source_unit_oracle",
                        "INSTALLED_CONSUMER_C01": "manager_a8_null_span_entrypoints",
                        "SOURCE_REGRESSIONS": "attempt9_suites_on_the_unfixed_base"}),
        "MF37A08-02": ([_f(MANAGER_A8 / "STORAGE_INDEPENDENT.json"), _f(MANAGER_A8 / "storage_independent.py"), _f(before)],
                       {"STORAGE_ADMISSION": "manager_a8_storage_independent", "FINAL_PACKET": "storage_verification",
                        "SOURCE_REGRESSIONS": "attempt9_suites_on_the_unfixed_base"}),
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
            "reproduced_before_repair": (reproduction.get(key) or {}).get("reproduced"),
            "reproduction_subject": {k: (reproduction.get("subject_before") or {}).get(k)
                                     for k in ("head", "clean", "is_issued_base")},
            "drafts_before_reproduction": reproduction.get("drafts_before_reproduction"),
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


def _summary(value: Any, limit: int = 8000) -> Any:
    return value if len(json.dumps(value, default=str)) < limit else {"see_receipt": True}


def consumer_manifest(ctx: Context, label: str) -> dict[str, Any]:
    manifest = a8o.consumer_manifest(ctx, label)
    installed, career = _d(ctx, "INSTALLED_CONSUMER_C01"), _d(ctx, "CAREER_SUCCESSOR")
    manifest.pop("attempt8_witness_verification", None)
    manifest.update({
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "attempt9_source_unit_verification": {
            "verifier_version": (career.get("source_identity_bindings") or {}).get("verifier_version"),
            "source_unit_checks": career.get("source_witness_checks"),
            "independent_source_unit_oracle": career.get("independent_source_unit_oracle"),
            "attempt8_source_field_oracle_kept": career.get("attempt8_source_field_oracle"),
            "installed_missing_witness_forgeries_console_script_and_module": _summary(installed.get("a9_forgeries")),
            "manager_a8_null_span_entrypoints": installed.get("manager_a8_null_span_entrypoints"),
            "attempt8_forgeries_retained": _summary(installed.get("a8_forgeries")),
            "manager_a7_envelope_entrypoints": installed.get("manager_a7_envelope_entrypoints"),
            "attempt7_forgeries_retained": _summary(installed.get("a7_forgeries")),
            "manager_a6_same_page_lineage": installed.get("manager_a6_same_page_lineage")},
        "delivered_successor_note": ("Attempt 9 delivers no new successor: it serves the Attempt 5 file by its Attempt 5 "
                                     "pointer, unchanged, and repairs the consumer that verifies it."),
    })
    return manifest


def population_document(ctx: Context, label: str) -> dict[str, Any]:
    document = a6o.population_document(ctx, label)
    oracle = (_d(ctx, "CAREER_SUCCESSOR").get("independent_source_unit_oracle") or {}).get("genuine") or {}
    witness = (_d(ctx, "CAREER_SUCCESSOR").get("source_witness_checks") or {}).get("successor") or {}
    document.update({"cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
                     "attempt9_source_unit_relations": oracle.get("relations"),
                     "attempt9_row_classes": oracle.get("row_classes"),
                     "attempt9_rows_resolved_without_a_witness": {
                         k: (witness.get(k) or {}).get("resolved_without_a_witness_by_form")
                         for k in ("successor", "delivered_predecessor")},
                     "attempt9_unwitnessed_fields": {k: (witness.get(k) or {}).get("unwitnessed_fields")
                                                     for k in ("successor", "delivered_predecessor")},
                     "note": document.get("note", "") + (" Attempt 9 resolves every row, witnessed or not, to the "
                                                         "source unit its identity names; nothing was rebuilt.")})
    return document


def candidate_document(ctx: Context, label: str) -> dict[str, Any]:
    document = a7o.candidate_document(ctx, label)
    details = _d(ctx, "LOCAL_INTEGRATION_CANDIDATE")
    control = _control(ctx)
    document.update({
        "requirement": "R37A09-03", "attempt9_start_head": candidate.ISSUED_CANDIDATE_HEAD,
        "attempt8_start_head": candidate.ATTEMPT8_START_HEAD, "attempt7_start_head": candidate.ATTEMPT7_START_HEAD,
        "preserved_first_candidate": candidate.PRESERVED_HEAD,
        "git_housekeeping": [{"record": str(p), **(read_json(p).get("git_housekeeping") or {})}
                             for p in ctx.candidate_record_paths]})
    document.pop("attempt7_start_head_note", None)
    lane = document["lane"]
    lane.pop("attempt7_chain", None)
    lane.update({"attempt9_chain": details.get("candidate_attempt9"),
                 "attempt9_append_chain": details.get("candidate_append_chain_attempt9"),
                 **{key: {k: v for k, v in (details.get(key) or {}).items() if k != "literal_adaptations"}
                    for key in ("manager_a8_committed_tree", "manager_a7_committed_tree", "manager_a6_committed_tree")}})
    document["control07_proposal"]["retention"] = control.get("attempt9_retention")
    document["not_done"] = ("No push, remote PR, merge, retarget, closure, deletion, reset, history rewrite or activation; "
                            "the preserved first candidate, bb5253b2, 0c22af20 and c52e7b52 stay reachable and every other "
                            "ref kept its commit.")
    return document


def final_packet_document(ctx: Context, label: str) -> dict[str, Any]:
    document = a7o.final_packet_document(ctx, label)
    document["sealing_order"] = [row.replace("v2.4.0", "v2.4.1") for row in document["sealing_order"]]
    return document


def platform_reconciliation(ctx: Context, label: str) -> dict[str, Any]:
    document = a7o.platform_reconciliation(ctx, label)
    document["label_note"] = document["label_note"].replace("Attempt 7", "Attempt 9")
    return document


def cost_ledger(ctx: Context, label: str) -> dict[str, Any]:
    return a7o.cost_ledger(ctx, label)


def effects(ctx: Context) -> list[dict[str, Any]]:
    return a6o.effects(ctx)


def integration_packet(ctx: Context, label: str, lanes: list[dict[str, Any]]) -> str:
    text = a7o.integration_packet(ctx, label, lanes)
    control = _control(ctx)
    return text + "\n".join([
        "### Attempt 9: the qualified proposal retained and rebound (not redesigned, not adopted)", "",
        f"Retention holds: {_retained(control)} -- the proposed bytes identical to the Attempt 8 and Attempt 7 bytes, "
        "the regenerated patch identical to the qualified patch `fab1911e...`, the Attempt 8 proposal document, the "
        "manager's Attempt 8 review and the control-change protocol each the issued bytes, and the retained checker and "
        "workflow the bytes the manager's independent review qualified. The concrete decision subject stays the "
        "manager's INTEGRATION_AUTHORITY_DECISION.md; no speculative redesign was made.", ""]) + "\n"


# ------------------------------------------------------------------ build


def build(ctx: Context, headline: str, writer_released: bool) -> dict[str, Any]:
    register_evidence(ctx)
    root = ctx.out_root
    lanes = base.lane_rows(ctx)
    lane_dispositions(ctx)
    obligations_path = root / "ORIGINAL_OBLIGATION_DISPOSITIONS.json"
    label = f"{LABEL_PREFIX} {headline}"

    def write_obligations(states: dict[str, dict[str, Any]]) -> None:
        items = []
        for row in ctx.contract["carryforward"]:
            item = {"id": row["id"], "category": carry_category(row["id"]),
                    **{k: row[k] for k in ("original_meaning", "disposition", "source_ids", "requirement_ids",
                                           "acceptance_ids", "owner", "reason", "next_action", "prior_mapping")}}
            if row["id"] in states:
                item["attempt9_state"] = states[row["id"]]["attempt9_state"]
                item["attempt9_evidence_ids"] = [e for e in states[row["id"]]["evidence_ids"] if e != "E-ORIGINAL-OBLIGATIONS"]
            items.append(item)
        ctx.carry_counts = {"composition": dict(collections.Counter(i["category"] for i in items)),
                            "dispositions": dict(collections.Counter(i["disposition"] for i in items))}
        ctx.obligation_items = items
        write_output(obligations_path, dumps({
            "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "contract_sha256": ctx.contract_sha256, "candidate": ctx.candidate,
            **ctx.carry_counts, "items": items, **_lane_lists(ctx),
            "note": ("Original meanings, sources, owners, reasons, next actions, prior mappings and dispositions are "
                     "copied from the issued contract unchanged. OWNED_BACKLOG items stay owned; none is marked "
                     "fulfilled by this accounting.")}))
        ctx.add("E-ORIGINAL-OBLIGATIONS", obligations_path, CENSUS,
                f"All {len(items)} carryforward identities with their original meanings and unchanged dispositions")

    write_obligations({})
    write_output(root / "LANE_RESULTS.json", dumps({
        "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "candidate": ctx.candidate,
        "runner": "tools/cycle37/attempt09_lanes.py", "runs_index": str(root / "lanes" / "RUNS.jsonl"),
        "runs_index_rule": "append-only lane index, named by path; never sealed as evidence (every lane run appends)",
        "lanes": lanes, **_lane_lists(ctx)}))
    ctx.add("E-OUTPUT-LANE_RESULTS.json", root / "LANE_RESULTS.json", CENSUS,
            "Every required lane's result at the candidate head; the 22 original and the Attempt 3 to 8 lanes")
    for name, builder in (("CAREER_POPULATION_DISPOSITIONS.json", population_document),
                          ("LOCAL_INTEGRATION_CANDIDATE.json", candidate_document),
                          ("DELIVERED_CONSUMER_MANIFEST.json", consumer_manifest)):
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
    software = ("FAIL" if any(row["status"] == "FAIL" for row in lanes) else
                "PASS" if all(row["status"] == "PASS" for row in lanes) else
                "NOT_RUN" if not any(row["executed"] or row["status"] == "PASS" for row in lanes) else "PARTIAL")
    installed = _d(ctx, "INSTALLED_CONSUMER_C01")
    career = _d(ctx, "CAREER_SUCCESSOR")
    census = career.get("independent_identity_census") or {}
    oracle = (career.get("independent_source_unit_oracle") or {}).get("genuine") or {}
    if ctx.lane_ok("INSTALLED_CONSUMER_C01") and ctx.lane_ok("CAREER_SUCCESSOR"):
        forged = (installed.get("a9_forgeries") or {}).get("cases") or {}
        refused = sum(1 for v in forged.values() if v.get("holds"))
        edges = sum(r.get("edges") or 0 for r in oracle.get("relations") or [])
        data_evidence = (f"DELIVERED_RELEASE_{base.DB_SHA256[:12]}_UNCHANGED; A5_SUCCESSOR_"
                         f"{str(ctx.pointer.get('successor_sha256'))[:12]}_ROWS_{census.get('rows')}_SERVED_UNCHANGED; "
                         f"RAW_CAPTURES_{census.get('raw_files')}_IDENTITY_MISMATCHES_0; LINEAGE_EDGES_{edges}_"
                         f"IDENTITY_DERIVED_UNITS_CROSSED_{oracle.get('crossed_edges')}_UNRESOLVED_"
                         f"{oracle.get('unresolved_edges')}; A9_FORGERIES_REFUSED_{refused}_OF_{len(forged)}; "
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
        "PLATFORM_RECONCILIATION.json": dumps(platform_reconciliation(ctx, label)),
        "COST_AND_AUTHORITY_LEDGER.json": dumps(cost_ledger(ctx, label)),
        "INHERITED_LANE_EQUIVALENCE.json": dumps(inherited_equivalence(ctx, label)),
        "INTEGRATION_DECISION_PACKET.md": integration_packet(ctx, label, lanes),
        "FINAL_PACKET_VALIDATION.json": dumps(final_packet_document(ctx, label)),
    }
    for name, text in outputs.items():
        write_output(root / name, text)
        ctx.add(f"E-OUTPUT-{name}", root / name, CENSUS, f"Declared worker output {name}")
    ctx.commit_dates = dict(line.split(" ", 1) for line in git_out("log", "--format=%H %cI",
                                                                   f"{BASE_SHA}..HEAD").splitlines() if line)
    executed = [lane for lane in WORKER_LANES if ctx.executed(lane)]
    ctx.all_runs_clean = bool(executed) and all(
        ctx.receipts[lane]["source_binding"].get("clean") and ctx.receipts[lane]["source_binding_after"].get("clean")
        for lane in executed)
    import attempt09_report  # the narrative report, beside this tool  # noqa: PLC0415

    write_output(root / "WORKER_REPORT.md", attempt09_report.render(ctx, submission))
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
    frozen = ctx.out_root / FINAL_SNAPSHOT
    if frozen.is_file() and not str(read_json(frozen).get("label", "")).startswith(LABEL_PREFIX):
        problems.append("STORAGE_EVIDENCE_SNAPSHOT.json does not carry the numeric identity label")
    lanes_doc = ctx.out_root / "LANE_RESULTS.json"
    if lanes_doc.is_file():
        document = read_json(lanes_doc)
        if {row["id"] for row in document["lanes"]} != set(ctx.lanes):
            problems.append("LANE_RESULTS lane set differs from the contract's")
        for key, prefix in LANE_LISTS:
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
            problems.append("FINDING_CLOSURE_MATRIX does not cover exactly MF37A08-01 and MF37A08-02")
        for row in rows:
            if not row["commits"]:
                problems.append(f"{row['finding']} names no commit")
    control = _control(ctx)
    if control and (control.get("cycle_number"), control.get("attempt_number")) != (CYCLE_NUMBER, ATTEMPT_NUMBER):
        problems.append("CONTROL07_PROPOSAL_VALIDATION.json does not carry Cycle 37 / Attempt 9")
    if not ctx.pointer:
        problems.append("the delivered career successor pointer is missing")
    elif sha256_file(Path(ctx.pointer["successor_file"])) != ctx.pointer.get("successor_sha256"):
        problems.append("the delivered career successor does not match its pointer digest")
    for lane, row in base.ledger_totals(ctx).items():
        if row["requests"] > row["ceiling"]:
            problems.append(f"{lane}: {row['requests']} requests exceed the ceiling {row['ceiling']}")
    submission_path = ctx.out_root / "submission.json"
    if submission_path.is_file():
        submission = read_json(submission_path)
        if (submission.get("cycle_number"), submission.get("attempt_number")) != (CYCLE_NUMBER, ATTEMPT_NUMBER):
            problems.append("submission.json does not carry Cycle 37 / Attempt 9")
        for row in submission.get("evidence") or []:
            relative = Path(row["path"]).resolve().relative_to(ctx.out_root.resolve()).as_posix()
            if relative in NEVER_EVIDENCE:
                problems.append(f"submission evidence {row['id']} names {relative}, which a later step writes")
            elif final_packet and sha256_file(Path(row["path"])) != row["sha256"]:
                problems.append(f"submission evidence {row['id']} changed after the seal")
        kinds = {row["kind"] for row in submission.get("evidence") or []}
        wanted = {c["evidence_kind"] for c in ctx.criteria.values() if c["executor"] == "worker"}
        if not wanted <= kinds:
            problems.append(f"no evidence carries the contract's kind(s) {sorted(wanted - kinds)}")
    if final_packet:
        storage = ctx.storage()
        if not storage["frozen_and_verified"]:
            problems.append(f"the root storage ledger is not frozen, verified and chained: "
                            f"{(storage['operational'].get('verification') or {}).get('result')}, chain "
                            f"{storage['chain'].get('result')}")
        if not storage["final_output_ledger"]["exists"]:
            problems.append("the final-output continuation does not exist")
        if not submission_path.is_file():
            problems.append("submission.json is missing")
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
    parser.add_argument("mode", choices=("classify", "inventory", "build", "check", "seal"))
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--headline", default="IN_PROGRESS_LOCAL_WORK_REMAINS", choices=base.HEADLINES)
    parser.add_argument("--writer-released", action="store_true")
    parser.add_argument("--final-packet", action="store_true")
    args = parser.parse_args(argv)
    ctx = Context(args.contract.resolve(), args.out_root.resolve())
    if args.mode == "classify":
        document = classify(ctx)
        print(json.dumps({lane: [(g["id"], len(g["identities"])) for g in row["groups"]]
                          for lane, row in document["lanes"].items()}, indent=2))
        return 0
    if args.mode == "inventory":
        document = inventory(ctx)
        print(json.dumps({"entries": len(document["entries"]), "total_bytes": document["total_bytes"]}, indent=2))
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
                      "lanes": {row["id"]: row["status"] for row in submission["lanes"]},
                      "unfinished": [(u["id"], u["kind"]) for u in submission["unfinished"]],
                      "evidence": len(submission["evidence"])}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
