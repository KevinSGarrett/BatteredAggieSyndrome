r"""Cycle #37 — Attempt #8 — worker outputs, submission and accounting check (R37A08-05).

    attempt08_outputs.py classify  --contract C --out-root R
    attempt08_outputs.py inventory --contract C --out-root R
    attempt08_outputs.py build     --contract C --out-root R [--headline H --writer-released]
    attempt08_outputs.py check     --contract C --out-root R [--final-packet]
    attempt08_outputs.py seal      --contract C --out-root R

The Attempt 7 accounting (``attempt07_outputs``, over the Attempt 6, 5, 4 and 3 bases) rebound to the Attempt 8
contract: 18 declared outputs (the CONTROL-07 proposal pair among them), 862 carryforward identities (the 819 of
Attempt 7 plus its 20 clauses, 15 lanes, 6 worker findings and the two manager findings), 20 clauses and 15 lanes.
``build`` writes the outputs from what is there -- the issued contract, the lane receipts, the platform receipts and
request ledger, the storage ledger chain and its snapshot, the candidate append records, the CONTROL-07 validation
receipt, git, and worker-authored evidence it reads but never invents (``evidence/INHERITED_FAILURE_CLASSIFICATION.json``,
``evidence/NEW_FINDINGS_ATTEMPT8.json``, ``evidence/CLEANUP_INVENTORY.json``, ``evidence/intake/DRAFT_PARKING.json``,
``evidence/before/BEFORE_REPRODUCTION.json``).

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

import attempt03_outputs as base  # noqa: E402  (the preserved Attempt 3 accounting)
import attempt04_outputs as a4o  # noqa: E402
import attempt05_outputs as a5o  # noqa: E402
import attempt06_outputs as a6o  # noqa: E402
import attempt07_outputs as a7o  # noqa: E402  (the preserved Attempt 7 accounting)
import attempt08_candidate as candidate  # noqa: E402
import storage_admission  # noqa: E402
from attempt03_outputs import (  # noqa: E402
    dumps,
    git_out,
    read_json,
    sha256_file,
    utc_now,
    write_output,
)

CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID, ATTEMPT_ID = 37, 8, "CYCLE-37", "ATTEMPT-08-20260926"
BASE_SHA = "996ada4d3054b2fda103688b5078ef255110019c"
BRANCH = "codex/BAT-706-cycle37-rework"
DATA = Path(r"C:\BatteredAggieSyndrome.data")
ATTEMPT7_ROOT = DATA / "ops" / "cycle37" / "attempt07"
MANAGER_A7 = DATA / "ops" / "manager_reviews" / "cycle37" / "attempt07" / "review-20260926T023810Z"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a08")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37a08")
WORKER_LANES = a7o.WORKER_LANES
FINDING_IDS = ("MF37A07-01", "MF37A07-02")
REQUIREMENT_LANES = {
    "R37A08-01": ("CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01"),
    "R37A08-02": ("STORAGE_ADMISSION", "FINAL_PACKET"),
    "R37A08-03": ("LOCAL_INTEGRATION_CANDIDATE",),
    "R37A08-04": ("WRITE_PROTECTION", "SOURCE_ADMISSION", "SOURCE_HARNESS", "SOURCE_REGRESSIONS", "CAREER_SUCCESSOR",
                  "INSTALLED_CONSUMER_C01", "TRUE_UNMOUNTED", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED"),
    "R37A08-05": WORKER_LANES,
}
A07_LANES = {lane: (lane,) for lane in WORKER_LANES} | {"MANAGER_REVIEW": ()}
CARRY_COMPOSITION = {**a7o.CARRY_COMPOSITION, "MANAGER_FINDING": 22, "ATTEMPT7_CRITERION": 20, "ATTEMPT7_LANE": 15,
                     "ATTEMPT7_WORKER_FINDING": 6}
LABEL_PREFIX = "Cycle #37 \u2014 Attempt #8 \u2014"
OUTPUT_NAMES = a7o.OUTPUT_NAMES
OPERATIONAL_LEDGER = a7o.OPERATIONAL_LEDGER
FINAL_SNAPSHOT = a7o.FINAL_SNAPSHOT
FINAL_OUTPUT_LEDGER = a7o.FINAL_OUTPUT_LEDGER
NEVER_EVIDENCE = a7o.NEVER_EVIDENCE
CANDIDATE_GRANT = a7o.CANDIDATE_GRANT
RAW = a7o.RAW
CENSUS = a7o.CENSUS
CONTROL_OUTPUTS = a7o.CONTROL_OUTPUTS
CONTROL_PATCH = a7o.CONTROL_PATCH
REFUSED_SOURCE_FIELD = "REFUSED_CAREER_SUCCESSOR_SOURCE_FIELD_WITNESS_MISMATCH"


_A7_CARRY_CATEGORY = a7o.carry_category  # captured before rebind() points a7o's name at carry_category below


def carry_category(key: str) -> str:
    for prefix, name in (("A07-AC-", "ATTEMPT7_CRITERION"), ("A07-LANE-", "ATTEMPT7_LANE"),
                         ("A07-WORKER-", "ATTEMPT7_WORKER_FINDING")):
        if key.startswith(prefix):
            return name
    return _A7_CARRY_CATEGORY(key)


def rebind() -> None:
    """Point the preserved accountings at the Attempt 8 identity. The Attempt 4 to 7 helpers keep the constants that
    find their own final lane receipts (each module's ``BASE_SHA`` names the head its predecessor finished at)."""

    a7o.rebind()
    base.CYCLE_NUMBER, base.ATTEMPT_NUMBER, base.CYCLE_ID, base.ATTEMPT_ID = (CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID,
                                                                              ATTEMPT_ID)
    base.BASE_SHA = BASE_SHA
    base.BRANCH = BRANCH
    base.WORKER_LANES = WORKER_LANES
    for module in (a4o, a5o, a6o, a7o):
        module.LABEL_PREFIX = LABEL_PREFIX
        module.CYCLE_NUMBER, module.ATTEMPT_NUMBER = CYCLE_NUMBER, ATTEMPT_NUMBER
    for module in (a5o, a6o, a7o):
        module.CYCLE_ID, module.ATTEMPT_ID = CYCLE_ID, ATTEMPT_ID
    a7o.CARRY_COMPOSITION = CARRY_COMPOSITION
    a7o.carry_category = carry_category
    a7o.candidate = candidate


class Context(a7o.Context):
    def __init__(self, contract_path: Path, out_root: Path) -> None:
        super().__init__(contract_path, out_root)
        self.findings_path = out_root / "evidence" / "NEW_FINDINGS_ATTEMPT8.json"
        self.attempt7_lanes: list[dict[str, Any]] = []


# ------------------------------------------------------------------ evidence


def register_evidence(ctx: Context) -> None:
    root = ctx.out_root
    for lane, run in ctx.runs.items():
        receipt = Path(run["receipt"])
        ctx.add(f"E-LANE-{lane}-LOG", receipt.parent / "lane.log", "command_log",
                f"{lane} run {run['run']}: the runner's console -- every command, its exit and its verdict")
        ctx.add(f"E-LANE-{lane}-RECEIPT", receipt, RAW,
                f"{lane} run {run['run']}: contract, source, interpreter, raw log paths and digests, census "
                "records, consumer outputs, storage reservation and the write/network scope measurement")
    career = ctx.runs.get("CAREER_SUCCESSOR")
    if career:
        for path in sorted(Path(career["receipt"]).parent.glob("ORACLE_*.json")):
            ctx.add(f"E-ORACLE-{path.stem[len('ORACLE_'):]}", path, RAW,
                    "The independent source-field oracle's full result (sqlite3/json/re only) over "
                    + path.stem[len("ORACLE_"):].replace("_", " "))
    for identity, path, kind, scope in (
            ("E-REQUEST-LEDGER", root / "evidence" / "platform" / "REQUEST_LEDGER.jsonl", CENSUS,
             "Every counted platform request, retries included, appended before its result was used"),
            ("E-FAILURE-CLASSIFICATION", root / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json", CENSUS,
             "Worker classification of every failing identity of a red lane, by cause, kind, owner and next action"),
            ("E-NEW-FINDINGS", ctx.findings_path, CENSUS,
             "Findings discovered in Attempt 8, with severity, disposition, owner and next action"),
            ("E-CLEANUP-INVENTORY", root / "evidence" / "CLEANUP_INVENTORY.json", CENSUS,
             "Every directory this attempt created or wrote, its bytes, and what the owner may remove (nothing removed)"),
            ("E-DRAFT-PARKING", root / "evidence" / "intake" / "DRAFT_PARKING.json", RAW,
             "The uncommitted MF37A07-01 draft parked outside the repair worktree before the unfixed reproduction, with "
             "the worktree's clean issued-base state bound"),
            ("E-BEFORE-REPRODUCTION", root / "evidence" / "before" / "BEFORE_REPRODUCTION.json", RAW,
             "Before-repair reproduction of MF37A07-01 and MF37A07-02 on the clean issued base 996ada4d: the manager's "
             "saved envelope fixture through the installed console script, installed module and source module, the "
             "Attempt 7 worker oracle, and the manager's same-path race and stop/reserve challenges on the unfixed "
             "storage tools"),
            ("E-CONTROL07-PATCH", root / CONTROL_PATCH, RAW,
             "The inert CONTROL-07 proposal as a patch against main's six control surfaces (never applied)")):
        if Path(path).is_file():
            ctx.add(identity, path, kind, scope)
    proposed = root / "evidence" / "control07" / "proposed"
    for path in sorted(p for p in proposed.rglob("*") if p.is_file()):
        relative = path.relative_to(proposed).as_posix()
        ctx.add(f"E-CONTROL07-PROPOSED-{relative}", path, RAW,
                f"The retained inert proposed bytes of {relative} (the qualified Attempt 7 bytes; not adopted)")
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
                ("E-STORAGE-LEDGER", ledger, "The attempt's root storage ledger (Cycle 37 / Attempt 8), frozen by its "
                                             "snapshot and never written again"),
                ("E-STORAGE-LEDGER-HEAD", Path(str(ledger) + storage_admission.HEAD_SUFFIX),
                 "The root ledger's append-only head log, frozen with it (a truncation is detected against it)"),
                ("E-STORAGE-CONTINUATION-CLAIM", Path(str(ledger) + storage_admission.CLAIM_SUFFIX),
                 "The create-only claim naming the root's one continuation (the final-output ledger)")):
            if path.is_file():
                ctx.add(identity, path, CENSUS, scope)
    for number, path in enumerate(ctx.candidate_record_paths, 1):
        ctx.add("E-CANDIDATE-APPEND-RECORD" if path == ctx.candidate_record_path else f"E-CANDIDATE-APPEND-RECORD-{number}",
                path, RAW, f"Append record {number} of the local integration candidate: previous head, commit, tree, "
                "provenance blobs, committed-blob proof, refs changed, worktree state")
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


_CARRIED = ("CARRIED_BY_ATTEMPT5_LANE_AT_THE_CANDIDATE_HEAD", "CARRIED_BY_ATTEMPT6_LANE_AT_THE_CANDIDATE_HEAD",
            "CARRIED_BY_ATTEMPT7_LANE_AT_THE_CANDIDATE_HEAD")


def _relabel(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The preserved dispositions name the attempt whose lane carries a prior lane; here that is Attempt 8. The results
    were read from this attempt's receipts, so only the naming changes."""

    out = []
    for row in rows:
        row = dict(row)
        disposition = row.get("disposition")
        if disposition in _CARRIED:
            number = disposition.split("ATTEMPT", 1)[1][0]
            row["disposition"] = "CARRIED_BY_ATTEMPT8_LANE_AT_THE_CANDIDATE_HEAD"
            row["attempt8_lanes"] = row.pop(f"attempt{number}_lanes")
            row["attempt8_results"] = row.pop(f"attempt{number}_results")
            if "justification" in row:
                row["justification"] = row["justification"].replace(f"Attempt {number} lane", "Attempt 8 lane")
        out.append(row)
    return out


def _a07_final(lane: str) -> dict[str, Any]:
    index = ATTEMPT7_ROOT / "lanes" / "RUNS.jsonl"
    rows = [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [row for row in rows if row["lane"] == lane and row["head"] == BASE_SHA]
    return rows[-1] if rows else {}


def attempt7_lane_dispositions(ctx: Context) -> list[dict[str, Any]]:
    rows = []
    for lane, successors in A07_LANES.items():
        final = _a07_final(lane)
        row: dict[str, Any] = {"id": f"A07-LANE-{lane}", "attempt7_lane": lane, "attempt7_run": final.get("run"),
                               "attempt7_result": final.get("result"), "attempt7_head": final.get("head"),
                               "attempt7_receipt": final.get("receipt"),
                               "attempt7_receipt_sha256": final.get("receipt_sha256"),
                               "attempt7_receipt_preserved": bool(final.get("receipt")) and Path(final["receipt"]).is_file()}
        if not successors:
            row.update(disposition="MANAGER_OWNED", justification="The Attempt 7 manager lane is the manager's.")
        else:
            row.update(disposition="CARRIED_BY_ATTEMPT8_LANE_AT_THE_CANDIDATE_HEAD", attempt8_lanes=list(successors),
                       attempt8_results={s: (ctx.receipts[s]["result"] if ctx.at_head(s) else "NOT_AT_HEAD")
                                         for s in successors if s in ctx.receipts},
                       justification=("Re-executed fresh by the same-named Attempt 8 lane at the candidate head; the "
                                      "Attempt 7 receipt stays unchanged as the before-record (its result is never "
                                      "relabelled; a red Attempt 7 result stays red there)."))
        rows.append(row)
    return rows


def lane_dispositions(ctx: Context) -> None:
    a7o.lane_dispositions(ctx)
    ctx.original_lanes = _relabel(ctx.original_lanes)
    ctx.attempt3_lanes = _relabel(ctx.attempt3_lanes)
    ctx.attempt4_lanes = _relabel(ctx.attempt4_lanes)
    ctx.attempt5_lanes = _relabel(ctx.attempt5_lanes)
    ctx.attempt6_lanes = _relabel(ctx.attempt6_lanes)
    ctx.attempt7_lanes = attempt7_lane_dispositions(ctx)


# ------------------------------------------------------------------ inherited red lanes


def classify(ctx: Context) -> dict[str, Any]:
    """Derive the Attempt 8 classification from Attempt 7's, identity by identity and cause by cause."""

    previous_path = ATTEMPT7_ROOT / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json"
    previous = read_json(previous_path)
    lanes: dict[str, Any] = {}
    problems: list[str] = []
    for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED"):
        receipt = ctx.receipts.get(lane)
        if not receipt or receipt["result"] != "FAIL" or not ctx.at_head(lane):
            continue
        failing = base.failing_identities(receipt) or []
        comparison = (receipt.get("details") or {}).get("attempt7_comparison") or {}
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
                       "attempt7_run": (previous["lanes"].get(lane) or {}).get("run"), "groups": list(groups.values()),
                       "equivalence": {"persisting": len(comparison.get("persisting") or []),
                                       "persisting_same_cause": len(comparison.get("persisting_same_cause") or []),
                                       "new_in_attempt8": comparison.get("new_in_attempt8"),
                                       "no_longer_failing": comparison.get("no_longer_failing") or
                                       comparison.get("no_longer_reported")}}
    if problems:
        raise SystemExit("classification refused:\n" + "\n".join(problems))
    document = {"label": f"{LABEL_PREFIX} IN_PROGRESS_LOCAL_WORK_REMAINS (inherited failure classification)",
                "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
                "attempt_id": ATTEMPT_ID, "authored_at": utc_now(),
                "rule": ("Each failing identity keeps its Attempt 7 group only when it persists with the same traceback "
                         "cause (FULL_FINAL_MOUNTED) or the same finding line (STRICT_MOUNTED); anything else is refused "
                         "for manual classification."),
                "derived_from": {"path": str(previous_path), "sha256": sha256_file(previous_path)}, "lanes": lanes}
    write_output(ctx.out_root / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json", dumps(document))
    return document


def inventory(ctx: Context) -> dict[str, Any]:
    """Every directory this attempt created or wrote, with its bytes; nothing is removed (no cleanup is granted)."""

    purposes = {
        (VALIDATION_ROOT, "before"): ("The before-repair reproduction: the replayed manager probes and their outputs", False),
        (VALIDATION_ROOT, "drafts"): ("The uncommitted MF37A07-01 draft parked during the unfixed reproduction", False),
        (VALIDATION_ROOT, "fixtures"): ("Owned forgery fixtures (full successor copies restored before every case)", True),
        (VALIDATION_ROOT, "rc"): ("Scratch repositories of the candidate-append rehearsal (shared objects borrowed read "
                                  "only)", True),
        (VALIDATION_ROOT, "cv"): ("The granted append's validation view: a byte-for-byte materialization of the appended "
                                  "candidate tree; the committed-blob proof cites it", False),
        (VALIDATION_ROOT, "cn"): ("Scratch repositories of the candidate lane's committed-provenance negatives", True),
        (VALIDATION_ROOT, "lanes"): ("Lane work directories (manager-probe replay copies, base export, fixtures)", True),
        (VALIDATION_ROOT, "rehearsal"): ("Rehearsal lane runs (labelled REHEARSAL, never evidence)", True),
        (VALIDATION_ROOT, "jira"): ("Private Jira successor copies (never the committed pack or live Jira)", True),
        (VALIDATION_ROOT, "control07"): ("The CONTROL-07 offline qualification's scratch matrices", True),
        (VALIDATION_ROOT, "oracle-dev"): ("Development runs of the independent oracle (not evidence)", True),
        (VALIDATION_ROOT, "tmp"): ("Development scratch: commit messages, the reservation token, test temp", True),
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
                "Attempt 8 evidence (declared outputs, receipts, platform and storage records)" if root == ctx.out_root
                else "Attempt 8 working files", False))
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
        final = _a07_final(lane)
        rows.append({"lane": lane, "attempt8_run": (ctx.runs.get(lane) or {}).get("run"),
                     "attempt8_result": receipt.get("result"), "at_candidate_head": ctx.at_head(lane),
                     "counts": receipt.get("counts"),
                     "execution": "FRESH_AT_THE_CANDIDATE_HEAD" if ctx.at_head(lane) else "NOT_AT_HEAD",
                     "attempt7_run": final.get("run"), "attempt7_result": final.get("result"),
                     "attempt7_receipt": final.get("receipt"), "attempt7_receipt_sha256": final.get("receipt_sha256"),
                     "attempt7_comparison": details.get("attempt7_comparison"),
                     "failing_identities": base.failing_identities(receipt) if receipt.get("result") == "FAIL" else None})
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "candidate": ctx.candidate, "lanes": rows, "equivalence_used": [],
            "equivalence_statement": ("TP37-A08 permits a CHECK lane to carry an old execution by an explicit current "
                                      "dependency comparison. This attempt used none: every one of the 14 worker lanes "
                                      "executed fresh at the candidate head, because consumer dependencies changed "
                                      "(career_successor.py, career_witness.py, the storage tools). Each Attempt 7 "
                                      "final receipt is retained unchanged as the before-record and compared by "
                                      "identity; no old execution is relabelled, and the Attempt 7 red lanes stay red "
                                      "there."),
            "classification": ctx.classification, "original_lanes": ctx.original_lanes,
            "attempt3_lanes": ctx.attempt3_lanes, "attempt4_lanes": ctx.attempt4_lanes,
            "attempt5_lanes": ctx.attempt5_lanes, "attempt6_lanes": ctx.attempt6_lanes,
            "attempt7_lanes": ctx.attempt7_lanes,
            "rule": ("Inherited red lanes stay red until genuinely resolved. Equivalence is by exact identity and cause "
                     "against the Attempt 7 final receipts at the issued base; counts alone establish nothing.")}


# ------------------------------------------------------------------ criteria


def _d(ctx: Context, lane: str) -> dict[str, Any]:
    return ctx.details(lane)


def _holds(ctx: Context, lane: str, key: str) -> bool:
    return bool((_d(ctx, lane).get(key) or {}).get("holds"))


def _before(ctx: Context, finding: str) -> bool:
    path = ctx.out_root / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
    return bool(path.is_file() and (read_json(path).get(finding) or {}).get("reproduced"))


def _unfixed(ctx: Context) -> dict[str, Any]:
    return _d(ctx, "SOURCE_REGRESSIONS").get("attempt8_witness_suite_on_the_unfixed_verifier") or {
        "served_by_the_unfixed_verifier": [], "refused_by_the_unfixed_verifier_under_another_cause": [],
        "forgery_cases": []}


def _control(ctx: Context) -> dict[str, Any]:
    path = ctx.out_root / "CONTROL07_PROPOSAL_VALIDATION.json"
    return read_json(path) if path.is_file() else {}



def judge(ctx: Context, key: str, requirement: str) -> tuple[str, str]:
    needed = REQUIREMENT_LANES[requirement]
    installed, career = _d(ctx, "INSTALLED_CONSUMER_C01"), _d(ctx, "CAREER_SUCCESSOR")
    if requirement == "R37A08-01":
        failing = [lane for lane in needed if not ctx.lane_ok(lane)]
        failing += [f"{lane}:{k}" for lane, k in (("INSTALLED_CONSUMER_C01", "a8_forgeries"),
                                                  ("INSTALLED_CONSUMER_C01", "manager_a7_envelope_entrypoints"),
                                                  ("INSTALLED_CONSUMER_C01", "a8_genuine_source_module"),
                                                  ("INSTALLED_CONSUMER_C01", "a7_forgeries"),
                                                  ("INSTALLED_CONSUMER_C01", "manager_a6_same_page_lineage"),
                                                  ("INSTALLED_CONSUMER_C01", "a6_forgeries"),
                                                  ("INSTALLED_CONSUMER_C01", "installed_identity_census"),
                                                  ("INSTALLED_CONSUMER_C01", "manager_a5_successor_adversarial"),
                                                  ("INSTALLED_CONSUMER_C01", "manager_a5_successor_population_audit"),
                                                  ("CAREER_SUCCESSOR", "independent_source_field_oracle"),
                                                  ("CAREER_SUCCESSOR", "independent_identity_census"))
                    if not _holds(ctx, lane, k)]
        failing += [f"source binding {k}" for k, v in (career.get("source_identity_checks") or {"none": False}).items()
                    if not v]
        failing += [f"source witness {k}" for k, v in ((career.get("source_witness_checks") or {}).get("checks")
                                                       or {"none": False}).items() if not v]
        failing += [f"original negative {name}" for name in a6o._lineage_originals(ctx)]
        if not (installed.get("successor_pagination") or {}).get("reconciled"):
            failing.append("complete pagination")
        if key.endswith("-C"):
            if not _before(ctx, "MF37A07-01"):
                failing.append("before-repair reproduction")
            if not _holds(ctx, "SOURCE_REGRESSIONS", "attempt8_suites_on_the_unfixed_base"):
                failing.append("the new suites fail on the unfixed base")
            if not _holds(ctx, "SOURCE_REGRESSIONS", "attempt8_witness_suite_on_the_unfixed_verifier"):
                failing.append("the witness forgeries are served by the unfixed verifier")
        if failing:
            return "IN_PROGRESS", "not yet held at the candidate head: " + ", ".join(failing)
        oracle = career["independent_source_field_oracle"]
        genuine = oracle["genuine"]
        edges = {r["relation"]: r["edges"] for r in genuine.get("relations") or []}
        forged = installed["a8_forgeries"]["cases"]
        a7 = installed["a7_forgeries"]["cases"]
        witness = career.get("source_witness_checks") or {}
        proved = {name: ((witness.get(key) or {}).get("successor") or {}).get("rows_proved")
                  for name, key in (("A05", "successor"), ("A04", "a04_format"))}
        text = {
            "A": ("Every recorded span a lineage anchor uses is first proved to be the source unit its row's identity "
                  "names in the cited revision -- the numbered field's value, or the list line, nested line or role "
                  "line -- under the reading of the parser version that wrote the row, in the successor and in every "
                  "delivered and Attempt 4 row an edge names, through both supported formats and every entrypoint; "
                  f"two proven units agree only by containment. The repaired verifier proves all "
                  f"{proved['A05']} Attempt 5 and {proved['A04']} Attempt 4 witnesses and anchors {edges.get('A5<-default')} default, "
                  f"{edges.get('A5<-A4')} Attempt 4 and {edges.get('A4<-default')} Attempt 4-to-default edges. The "
                  "independent oracle derives fields, list lines and role lines from the raw text itself (its own "
                  f"bracket stack, no shared code): {genuine.get('crossed_edges')} crossed and 0 unresolved edges over "
                  f"the genuine files, and it finds the manager's saved envelope "
                  f"({oracle['manager_a7_envelope'].get('crossed_by_relation')}) and the Attempt 6 same-page fixture "
                  f"({oracle['manager_a6_same_page'].get('crossed_by_relation')}); interval agreement inside one "
                  "multi-interval field is reported as not independently adjudicated. Legitimate comment-bearing, "
                  "nested, role-line, list-template, empty and absent-field forms serve."),
            "B": (f"The 72,958-row successor serves unchanged with complete pagination; all 72,070 default and 73,082 "
                  f"Attempt 4 dispositions reconcile; the independent oracle adjudicates every genuine witness (no "
                  "unresolved class). Through the fresh installed console script, its installed module and the source "
                  f"module, the manager's saved envelope is refused as {REFUSED_SOURCE_FIELD}; {len(forged)} fresh "
                  "substitutions (year-only, team-only and both-field envelopes, a full-page span, a boundary shifted "
                  "into the next field, a partial span, a witness moved onto another job's genuine field, a list line "
                  "enlarged over its neighbour, the envelope through the Attempt 4 format and in the declared Attempt 4 "
                  "file) are each refused for their source-field cause after a fixture reset; the "
                  f"{len(a7)} Attempt 7 forgeries, the Attempt 6 same-page challenge and every earlier cross-person, "
                  "revision, family and raw-binding negative stay refused."),
            "C": ("Before repair, on the clean issued base (the draft parked outside the worktree), every entrypoint "
                  "served the saved fixture's seven rows and the Attempt 7 worker oracle reported 0 crossed edges. The "
                  "repair's suites fail on the unfixed base's exact bytes and pass on the repaired source; with only the "
                  "repair's unit reader added beside the unfixed verifier, "
                  f"{len(_unfixed(ctx)['served_by_the_unfixed_verifier'])} of {len(_unfixed(ctx)['forgery_cases'])} "
                  "witness forgery cases, the manager's envelope among them, are served there (no refusal raised) and "
                  f"the other {len(_unfixed(ctx)['refused_by_the_unfixed_verifier_under_another_cause'])} are refused "
                  "only under the earlier anchor rule, never as a source-field mismatch. "
                  "Independent "
                  "alternate entrypoints (installed module, source module) are exercised; remaining limits are "
                  "classified: source biography truth, rows whose own normalized fields are rewritten, and interval "
                  "grain inside one field stay owned or manager-verified."),
        }[key[-1]]
        return "VERIFIED_LOCAL", text
    if requirement == "R37A08-02":
        storage = ctx.storage()
        admission = _d(ctx, "STORAGE_ADMISSION")
        live = ((admission.get("storage_ledger") or {}).get("live_over_budget_control") or {}).get("refused")
        failing = [lane for lane in needed if not ctx.lane_ok(lane)]
        if not live:
            failing.append("live over-budget refusal")
        failing += [k for k in ("manager_a7_same_path_race", "manager_a7_stop_reserve",
                                "manager_a6_storage_continuation", "manager_a5_storage_independent")
                    if not _holds(ctx, "STORAGE_ADMISSION", k)]
        if not storage["frozen_and_verified"]:
            failing.append("root ledger frozen, verified and its chain proved")
        validation = sorted((ctx.out_root / "evidence" / "final").glob("FINAL_PACKET_VALIDATION_*.json"))
        if not validation or read_json(validation[-1]).get("result") != "PASS":
            failing.append("FINAL_PACKET validation receipt PASS")
        if key.endswith("-C") and not _before(ctx, "MF37A07-02"):
            failing.append("before-repair reproduction")
        if failing:
            return "IN_PROGRESS", "not yet held: " + ", ".join(failing)
        measured = storage["operational"].get("measured") or {}
        race = admission["manager_a7_same_path_race"]
        text = {
            "A": ("Claim, the child's existence and identity, its INIT and its OPENED record now happen in one critical "
                  "section under the parent's lock (the child's absence checked under its own lock): a second caller "
                  "of the same continuation resumes the one child or is refused for the parameter that differs; an "
                  "interrupted claim or INIT is recovered without a second child or duplicate headroom, a torn INIT "
                  "is refused; a stopped or reserve-changed continuation needs a recorded revised plan naming an "
                  "existing authority, feasible under the unchanged ceiling, whose ceiling then bounds it. The root "
                  f"ledger (Cycle 37 / Attempt 8) froze with {measured.get('added_bytes')} bytes added of its "
                  f"{storage['operational'].get('budget_bytes')}-byte budget."),
            "B": ("The deterministic race suite (real locks: the second caller observed waiting on the parent's lock) "
                  "leaves one INIT and a restart that resumes; interrupted, torn, conflicting, stale, wrong-attempt, "
                  "truncated and plan cases each hold; the manager's Attempt 7 race replayed byte-faithfully leaves "
                  f"{race.get('init_count')} INIT, restart {(race.get('restart') or {}).get('result')}, chain "
                  f"{race.get('chain_after_restart')}; its stop/reserve challenge is refused where the stopped ledger "
                  "would continue; the Attempt 5 and 6 challenges and the live over-budget control hold; FINAL_PACKET "
                  "passes on the separately reserved final-output continuation."),
            "C": ("Before repair, on the clean issued base, the manager's race wrote two INITs (chain broken at line 3, "
                  "restart refused) and a stopped or lowered-reserve continuation admitted; both families refuse or "
                  "recover now, and a lock-release defect the new many-caller test found is repaired (W37A08-01). "
                  "Finer process attribution stays with the platform owner."),
        }[key[-1]]
        return "VERIFIED_LOCAL", text
    if requirement == "R37A08-03":
        details = _d(ctx, "LOCAL_INTEGRATION_CANDIDATE")
        failing = [lane for lane in needed if not ctx.lane_ok(lane)]
        checks = details.get("candidate_tree_checks") or {}
        failing += [k for k, v in checks.items() if not v] or ([] if checks else ["tree checks"])
        failing += [k for k, v in (details.get("candidate_attempt8") or {"attempt 8 chain": False}).items() if not v]
        failing += [k for k in ("candidate_negatives", "manager_a7_committed_tree", "manager_a6_committed_tree",
                                "manager_a5_integration_replay", "candidate_consumer", "control07_requalification")
                    if not _holds(ctx, "LOCAL_INTEGRATION_CANDIDATE", k)]
        if not ctx.candidate_record_path:
            failing.append("append record")
        control = _control(ctx)
        subjects = control.get("subjects") or {}
        appended = {read_json(p).get("candidate_commit"): read_json(p).get("repair_head")
                    for p in ctx.candidate_record_paths}
        requalified = details.get("control07_requalification") or {}
        final_candidate = candidate.describe().get("candidate_head")
        if control.get("result") != "PASS":
            failing.append("CONTROL07_PROPOSAL_VALIDATION.json PASS")
        elif subjects.get("candidate") not in appended or appended[subjects["candidate"]] != subjects.get("repair"):
            failing.append("the create-only CONTROL-07 validation is not bound to an Attempt 8 append and its repair head")
        if (requalified.get("subjects") or {}).get("candidate") != final_candidate:
            failing.append("CONTROL-07 re-qualified in the lane at the final candidate")
        retention = control.get("attempt8_retention") or {}
        if not (retention.get("proposed_bytes_identical_to_attempt7")
                and retention.get("patch_identical_to_the_qualified_attempt7_patch")
                and (retention.get("manager_independent_review") or {}).get("retained_bytes_are_the_reviewed_bytes")):
            failing.append("the retained proposal is the qualified Attempt 7 bytes")
        errors = ((details.get("candidate_review_control_characterization") or {}).get("compatibility_errors"))
        if key.endswith("-C") and not errors:
            failing.append("the two control compatibility errors kept visible")
        if failing:
            return "IN_PROGRESS", "not yet held: " + ", ".join(failing)
        proof = details.get("committed_tree_proof") or {}
        green = (control.get("characterization") or {}).get("current_checkers_green_on") or {}
        cases = len(((control.get("checker_runs") or {}).get("proposed") or {}).get("cases") or {})
        text = {"A": ("The qualified Attempt 7 CONTROL-07 proposal is retained byte for byte (its checker and workflow "
                      "are exactly the bytes the manager's 21 independent offline cases reviewed; the regenerated patch "
                      "is the qualified fab1911e... patch) under this attempt's evidence root, outside every checkout, "
                      f"and rebound: {sum(1 for v in (control.get('checks') or {}).values() if v)} of "
                      f"{len(control.get('checks') or {})} checks hold over {cases} offline fixture cases at repair "
                      f"{str(subjects.get('repair'))[:8]} and candidate {str(subjects.get('candidate'))[:8]}; the current "
                      "checkers exit green on "
                      + ", ".join(f"{name} {len(rows)}" for name, rows in green.items())
                      + " of those cases. No active control was changed, no provider or workflow ran; adoption needs the "
                        "eligible independent bootstrap receipt and publication authority, both ungranted."),
                "B": ("FAIL, BLOCKED and SKIPPED reports, self-approval, a stale head, a dismissed or unapproved review, "
                      "a changed control surface and a PASS under the unapproved protocol all fail closed; the only green "
                      "proposed case is the synthetic TEST_ONLY approval, which is not a receipt. The proposal's "
                      "original and proposed hashes and the exact later adoption, rollback and verification actions are "
                      "in CONTROL07_PROPOSAL.md; the candidate lane re-qualified it at the final candidate "
                      f"{str(final_candidate)[:8]}."),
                "C": ("The ordinary repairs and regenerated provenance were appended forward to 0c22af20 "
                      f"({len(ctx.candidate_record_paths)} [material] commit(s)), every ancestor (daba87f0, bb5253b2, "
                      "0c22af20) and main's protected bytes retained, only the candidate ref moved; committed blobs and "
                      f"manifest reconcile ({proof.get('committed_paths')} paths, {proof.get('manifest_rows')} manifest "
                      "rows, 0 mismatches), independently confirmed by the manager's Attempt 7 and 6 committed-tree "
                      "reviews; the consumer built from the candidate tree serves and refuses; the two control "
                      f"compatibility errors stay visible ({len(errors or [])} failing tests characterized). Qualifying "
                      "the private proposal does not qualify the candidate for publication.")}
        return "VERIFIED_LOCAL", text[key[-1]]
    if requirement == "R37A08-04":
        failing = [lane for lane in needed if lane not in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED") and not ctx.lane_ok(lane)]
        failing += [lane for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED") if not ctx.executed(lane)]
        for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED"):
            comparison = _d(ctx, lane).get("attempt7_comparison") or {}
            if comparison.get("new_in_attempt8"):
                failing.append(f"{lane} new identities {comparison['new_in_attempt8']}")
        named = (installed.get("successor_named_cases") or {}).get("holds") or {}
        failing += [f"named {k}" for k, v in named.items() if not v] or ([] if named else ["named cases"])
        failing += [k for k in ("manager_a3_career_challenge", "manager_a4_career_semantic_census",
                                "manager_a4_successor_challenge", "manager_a5_career_semantic_census",
                                "manager_a5_successor_adversarial", "a7_forgeries", "a8_forgeries",
                                "manager_a6_same_page_lineage", "manager_a7_envelope_entrypoints")
                    if not _holds(ctx, "INSTALLED_CONSUMER_C01", k)]
        if not (installed.get("successor_coverage") or {}).get("predecessor_identity_sets_equal"):
            failing.append("successor coverage")
        if failing:
            return "IN_PROGRESS", "not yet held: " + ", ".join(failing)
        text = {"A": ("All 72,958 genuine rows and 7,950 captures verify and serve unchanged, and every genuine witness "
                      "is proved to be its source field (verifier) and independently adjudicated (oracle); all 72,070 "
                      "default and 73,082 Attempt 4 predecessor rows keep one disposition; the legitimate alias, new, "
                      "split, removed, restructured, missing-team, comment-bearing, list-template and other-sport classes "
                      "serve with their explicit meanings; the affected entrypoint (the successor verifier) is repaired "
                      "as a class, no data rebuilt and no fact invented or activated."),
                "B": ("One fresh offline noneditable BAS wheel, composed with the released C01 wheel, paginates the whole "
                      "successor and every filter exactly as the independent SQL oracle and raw census derive them, "
                      "serves the same rows for the named people through its module entrypoint as through its console "
                      "script (and the source module), and refuses every original and new within-page lineage forgery "
                      "for its own cause, each after an independent fixture reset; no row is hidden or dropped."),
                "C": ("The guard, date, defensive-unit, unknown-role, Cory 2018/Danny/Steve, scoring/PIT, harness, "
                      "default/legacy and Cycle 29 behavior pass their suites and the manager replays at the candidate "
                      "head; the full mounted suite ran fresh and matches Attempt 7 identity for identity with no new "
                      "failure; the default database, prior releases, raw captures and frozen predictions are "
                      "unchanged; the 2,223-row staff successor and the whole history stay owned.")}[key[-1]]
        return "VERIFIED_LOCAL", text
    # R37A08-05
    if key.endswith("-A"):
        missing = [lane for lane in WORKER_LANES if not ctx.executed(lane)]
        if not missing:
            return "VERIFIED_LOCAL", ("The Attempt 8 lane and output tools were implemented and inspected; the storage "
                                      "continuation and seal qualified first on tiny fixtures (the deterministic race, "
                                      "interrupted states, plans, and a stress of 24 threads and 6 processes) and every "
                                      "new forgery was proved against the source verifier before the installed lane; "
                                      "every one of the 14 worker lanes executed fresh through the issued command at the "
                                      "candidate head with exact binding and raw counts; no equivalence was relabelled "
                                      "and inherited red stays red, compared with Attempt 7 by identity and cause.")
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
        return "VERIFIED_LOCAL", ("All 862 carryforward identities keep their meanings and dispositions; 20 clauses, 15 "
                                  "lanes, 18 outputs, findings and effects are accounted in a generated report, "
                                  "checklist and submission; the forward-only candidate carries committed-blob "
                                  "provenance and consumer proof; the root storage ledger is frozen with every "
                                  "reservation reconciled and the final outputs reserved on its one claimed "
                                  "continuation; FINAL_PACKET passes (accounting only). Nothing is claimed about "
                                  "adoption, integration or acceptance.")
    return "IN_PROGRESS", ("; ".join(problems[:3]) or
                           f"PLATFORM_CARRY {ctx.lane_ok('PLATFORM_CARRY')}, candidate "
                           f"{ctx.lane_ok('LOCAL_INTEGRATION_CANDIDATE')}, FINAL_PACKET {ctx.lane_ok('FINAL_PACKET')}, "
                           f"storage frozen and chained {storage['frozen_and_verified']}")


def criterion_evidence(ctx: Context, requirement: str) -> list[str]:
    ids: list[str] = []
    for lane in REQUIREMENT_LANES[requirement]:
        if ctx.executed(lane):
            ids += [f"E-LANE-{lane}-RECEIPT", f"E-LANE-{lane}-LOG"]
    storage = ["E-STORAGE-SNAPSHOT", "E-STORAGE-LEDGER", "E-STORAGE-LEDGER-HEAD", "E-STORAGE-CONTINUATION-CLAIM"]
    oracle = [e for e in ctx.evidence if e.startswith("E-ORACLE-")]
    extra = {"R37A08-01": ["E-BEFORE-REPRODUCTION", "E-DRAFT-PARKING", *oracle, "E-LANE-SOURCE_REGRESSIONS-RECEIPT"],
             "R37A08-02": ["E-BEFORE-REPRODUCTION", *storage] + [e for e in ctx.evidence if e.startswith("E-FINAL-")],
             "R37A08-03": ["E-CANDIDATE-APPEND-RECORD", "E-OUTPUT-LOCAL_INTEGRATION_CANDIDATE.json",
                           "E-OUTPUT-CONTROL07_PROPOSAL_VALIDATION.json", "E-OUTPUT-CONTROL07_PROPOSAL.md",
                           "E-CONTROL07-PATCH", "E-CONTROL07-OFFLINE-MATRIX"]
             + [e for e in ctx.evidence if e.startswith("E-CONTROL07-PROPOSED-")],
             "R37A08-04": ["E-OUTPUT-CAREER_POPULATION_DISPOSITIONS.json", "E-OUTPUT-DELIVERED_CONSUMER_MANIFEST.json",
                           "E-FAILURE-CLASSIFICATION", *oracle],
             "R37A08-05": ["E-ORIGINAL-OBLIGATIONS", "E-FAILURE-CLASSIFICATION", "E-REQUEST-LEDGER",
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
        if key.endswith("-B") and criterion["requirement"] == "R37A08-05":
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
        elif row["id"].startswith(("ORIGINAL-LANE-", "A03-LANE-", "A04-LANE-", "A05-LANE-", "A06-LANE-", "A07-LANE-")):
            evidence.append("E-OUTPUT-LANE_RESULTS.json")
        rows.append({"id": row["id"], "disposition": row["disposition"], "attempt8_state": state,
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
        "MF37A07-01": ([_f(MANAGER_A7 / "FRESH_LINEAGE_ENVELOPE_CHALLENGE.json"),
                        _f(MANAGER_A7 / "lineage_envelope_challenge.py"), _f(MANAGER_A7 / "LINEAGE_ENTRYPOINTS.json"),
                        _f(MANAGER_A7 / "WORKER_ORACLE_ENVELOPE_CHALLENGE.json"), _f(before)],
                       {"CAREER_SUCCESSOR": "independent_source_field_oracle",
                        "INSTALLED_CONSUMER_C01": "manager_a7_envelope_entrypoints",
                        "SOURCE_REGRESSIONS": "attempt8_witness_suite_on_the_unfixed_verifier"}),
        "MF37A07-02": ([_f(MANAGER_A7 / "STORAGE_SAME_PATH_CONCURRENCY.json"), _f(MANAGER_A7 / "storage_same_path_race.py"),
                        _f(MANAGER_A7 / "STORAGE_INDEPENDENT.json"), _f(MANAGER_A7 / "storage_independent.py"), _f(before)],
                       {"STORAGE_ADMISSION": "manager_a7_same_path_race", "FINAL_PACKET": "storage_verification",
                        "SOURCE_REGRESSIONS": "attempt8_suites_on_the_unfixed_base"}),
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
    manifest = a6o.consumer_manifest(ctx, label)
    installed, career = _d(ctx, "INSTALLED_CONSUMER_C01"), _d(ctx, "CAREER_SUCCESSOR")
    oracle = career.get("independent_source_field_oracle") or {}
    manifest.update({
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "attempt8_witness_verification": {
            "verifier_version": (career.get("source_identity_bindings") or {}).get("verifier_version"),
            "source_witness_checks": career.get("source_witness_checks"),
            "independent_source_field_oracle": oracle,
            "installed_forgeries_console_script_and_module": _summary(installed.get("a8_forgeries")),
            "manager_a7_envelope_entrypoints": installed.get("manager_a7_envelope_entrypoints"),
            "attempt7_forgeries_retained": _summary(installed.get("a7_forgeries")),
            "manager_a6_same_page_lineage": installed.get("manager_a6_same_page_lineage")},
        "delivered_successor_note": ("Attempt 8 delivers no new successor: it serves the Attempt 5 file by its Attempt 5 "
                                     "pointer, unchanged, and repairs the consumer that verifies it."),
    })
    return manifest


def population_document(ctx: Context, label: str) -> dict[str, Any]:
    document = a6o.population_document(ctx, label)
    oracle = (_d(ctx, "CAREER_SUCCESSOR").get("independent_source_field_oracle") or {}).get("genuine") or {}
    document.update({"cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
                     "attempt8_source_field_relations": oracle.get("relations"),
                     "attempt8_witness_classes": oracle.get("witness_classes"),
                     "attempt8_unit_forms": oracle.get("unit_forms"),
                     "note": document.get("note", "") + (" Attempt 8 proves every lineage witness is the source field "
                                                         "its identity names; nothing was rebuilt.")})
    return document


def candidate_document(ctx: Context, label: str) -> dict[str, Any]:
    document = a7o.candidate_document(ctx, label)
    details = _d(ctx, "LOCAL_INTEGRATION_CANDIDATE")
    control = _control(ctx)
    document.update({
        "requirement": "R37A08-03", "attempt8_start_head": candidate.ISSUED_CANDIDATE_HEAD,
        "attempt7_start_head": candidate.ATTEMPT7_START_HEAD, "preserved_first_candidate": candidate.PRESERVED_HEAD})
    document.pop("attempt7_start_head_note", None)
    document["lane"].update({"attempt8_chain": details.get("candidate_attempt8"),
                             "manager_a7_committed_tree": {k: v for k, v in (details.get("manager_a7_committed_tree") or {})
                                                           .items() if k != "literal_adaptations"}})
    document["control07_proposal"]["retention"] = control.get("attempt8_retention")
    document["not_done"] = ("No push, remote PR, merge, retarget, closure, deletion, reset, history rewrite or activation; "
                            "the preserved first candidate, bb5253b2 and 0c22af20 stay reachable and every other ref kept "
                            "its commit.")
    return document


def final_packet_document(ctx: Context, label: str) -> dict[str, Any]:
    return a7o.final_packet_document(ctx, label)


def platform_reconciliation(ctx: Context, label: str) -> dict[str, Any]:
    document = a7o.platform_reconciliation(ctx, label)
    document["label_note"] = document["label_note"].replace("Attempt 7", "Attempt 8")
    return document


def cost_ledger(ctx: Context, label: str) -> dict[str, Any]:
    return a7o.cost_ledger(ctx, label)


def effects(ctx: Context) -> list[dict[str, Any]]:
    return a6o.effects(ctx)


def integration_packet(ctx: Context, label: str, lanes: list[dict[str, Any]]) -> str:
    text = a7o.integration_packet(ctx, label, lanes)
    control = _control(ctx)
    retention = control.get("attempt8_retention") or {}
    return text + "\n".join([
        "### Attempt 8: the qualified proposal retained and rebound (not redesigned, not adopted)", "",
        f"Proposed bytes identical to the Attempt 7 qualified bytes: {retention.get('proposed_bytes_identical_to_attempt7')}; "
        f"patch identical to the qualified patch `fab1911e...`: {retention.get('patch_identical_to_the_qualified_attempt7_patch')}; "
        "the retained checker and workflow are the bytes the manager's independent review qualified: "
        f"{(retention.get('manager_independent_review') or {}).get('retained_bytes_are_the_reviewed_bytes')}. The "
        "concrete decision subject stays the manager's INTEGRATION_AUTHORITY_DECISION.md; no speculative redesign was "
        "made.", ""]) + "\n"


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
                item["attempt8_state"] = states[row["id"]]["attempt8_state"]
                item["attempt8_evidence_ids"] = [e for e in states[row["id"]]["evidence_ids"] if e != "E-ORIGINAL-OBLIGATIONS"]
            items.append(item)
        ctx.carry_counts = {"composition": dict(collections.Counter(i["category"] for i in items)),
                            "dispositions": dict(collections.Counter(i["disposition"] for i in items))}
        ctx.obligation_items = items
        write_output(obligations_path, dumps({
            "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "contract_sha256": ctx.contract_sha256, "candidate": ctx.candidate,
            **ctx.carry_counts, "items": items, "original_lanes": ctx.original_lanes,
            "attempt3_lanes": ctx.attempt3_lanes, "attempt4_lanes": ctx.attempt4_lanes,
            "attempt5_lanes": ctx.attempt5_lanes, "attempt6_lanes": ctx.attempt6_lanes,
            "attempt7_lanes": ctx.attempt7_lanes,
            "note": ("Original meanings, sources, owners, reasons, next actions, prior mappings and dispositions are "
                     "copied from the issued contract unchanged. OWNED_BACKLOG items stay owned; none is marked "
                     "fulfilled by this accounting.")}))
        ctx.add("E-ORIGINAL-OBLIGATIONS", obligations_path, CENSUS,
                "All 862 carryforward identities with their original meanings and unchanged dispositions")

    write_obligations({})
    write_output(root / "LANE_RESULTS.json", dumps({
        "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "candidate": ctx.candidate,
        "runner": "tools/cycle37/attempt08_lanes.py", "runs_index": str(root / "lanes" / "RUNS.jsonl"),
        "runs_index_rule": "append-only lane index, named by path; never sealed as evidence (every lane run appends)",
        "lanes": lanes, "original_lanes": ctx.original_lanes, "attempt3_lanes": ctx.attempt3_lanes,
        "attempt4_lanes": ctx.attempt4_lanes, "attempt5_lanes": ctx.attempt5_lanes,
        "attempt6_lanes": ctx.attempt6_lanes, "attempt7_lanes": ctx.attempt7_lanes}))
    ctx.add("E-OUTPUT-LANE_RESULTS.json", root / "LANE_RESULTS.json", CENSUS,
            "Every required lane's result at the candidate head; the 22 original and the Attempt 3 to 7 lanes")
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
    oracle = (career.get("independent_source_field_oracle") or {}).get("genuine") or {}
    if ctx.lane_ok("INSTALLED_CONSUMER_C01") and ctx.lane_ok("CAREER_SUCCESSOR"):
        forged = (installed.get("a8_forgeries") or {}).get("cases") or {}
        refused = sum(1 for v in forged.values() if v.get("holds"))
        edges = sum(r.get("edges") or 0 for r in oracle.get("relations") or [])
        data_evidence = (f"DELIVERED_RELEASE_{base.DB_SHA256[:12]}_UNCHANGED; A5_SUCCESSOR_"
                         f"{str(ctx.pointer.get('successor_sha256'))[:12]}_ROWS_{census.get('rows')}_SERVED_UNCHANGED; "
                         f"RAW_CAPTURES_{census.get('raw_files')}_IDENTITY_MISMATCHES_0; LINEAGE_EDGES_{edges}_"
                         f"SOURCE_FIELD_WITNESSED_CROSSED_{oracle.get('crossed_edges')}; A8_FORGERIES_REFUSED_{refused}; "
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
    import attempt08_report  # the narrative report, beside this tool  # noqa: PLC0415

    write_output(root / "WORKER_REPORT.md", attempt08_report.render(ctx, submission))
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
        for key, prefix in (("original_lanes", "ORIGINAL-LANE-"), ("attempt3_lanes", "A03-LANE-"),
                            ("attempt4_lanes", "A04-LANE-"), ("attempt5_lanes", "A05-LANE-"),
                            ("attempt6_lanes", "A06-LANE-"), ("attempt7_lanes", "A07-LANE-")):
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
            problems.append("FINDING_CLOSURE_MATRIX does not cover exactly MF37A07-01 and MF37A07-02")
        for row in rows:
            if not row["commits"]:
                problems.append(f"{row['finding']} names no commit")
    control = _control(ctx)
    if control and (control.get("cycle_number"), control.get("attempt_number")) != (CYCLE_NUMBER, ATTEMPT_NUMBER):
        problems.append("CONTROL07_PROPOSAL_VALIDATION.json does not carry Cycle 37 / Attempt 8")
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
            problems.append("submission.json does not carry Cycle 37 / Attempt 8")
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
