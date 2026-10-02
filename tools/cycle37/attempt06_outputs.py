r"""Cycle #37 — Attempt #6 — worker outputs, submission and accounting check (R37A06-05).

    attempt06_outputs.py classify --contract C --out-root R
    attempt06_outputs.py build --contract C --out-root R [--headline H --writer-released]
    attempt06_outputs.py check --contract C --out-root R [--final-packet]
    attempt06_outputs.py seal --contract C --out-root R

The Attempt 5 accounting (``attempt05_outputs``, over the Attempt 4 and Attempt 3 bases) rebound to the Attempt 6
contract: 16 declared outputs, 774 carryforward identities, 20 clauses and 15 lanes. ``build`` writes the outputs
from what is there -- the issued contract, the lane receipts, the platform receipts and request ledger, the frozen
storage segments and their snapshots, the candidate append record, git, and worker-authored evidence it reads but
never invents (``evidence/INHERITED_FAILURE_CLASSIFICATION.json``, ``evidence/NEW_FINDINGS_ATTEMPT6.json``,
``evidence/CLEANUP_INVENTORY.json``).

MF37A05-03: nothing a later step writes is registered as evidence. The lane index ``lanes/RUNS.jsonl`` (appended by
every lane run, FINAL_PACKET included) and the final-output storage ledger (which accounts for the final packet's
own outputs after the seal) are named by path only; the operational ledger segments are registered only once frozen
by their immutable snapshots, and the last one only once ``STORAGE_EVIDENCE_SNAPSHOT.json`` freezes it.

``classify`` derives the Attempt 6 classification of a red mounted lane from the Attempt 5 one: an identity that
persists with the same cause keeps its Attempt 5 group; anything else is refused for manual classification. The
default headline is IN_PROGRESS_LOCAL_WORK_REMAINS; a terminal headline must be asked for with ``--writer-released``
and is refused while local work remains. This tool never accepts anything.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt03_outputs as base  # noqa: E402  (the preserved Attempt 3 accounting)
import attempt04_outputs as a4o  # noqa: E402  (the preserved Attempt 4 accounting)
import attempt05_outputs as a5o  # noqa: E402  (the preserved Attempt 5 accounting)
import attempt06_candidate as candidate  # noqa: E402
import storage_admission  # noqa: E402
import storage_snapshot as snapshot  # noqa: E402
from attempt03_outputs import (  # noqa: E402
    dumps,
    git_out,
    read_json,
    sha256_file,
    utc_now,
    write_output,
)

CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID, ATTEMPT_ID = 37, 6, "CYCLE-37", "ATTEMPT-06-20260925"
BASE_SHA = "7a0b6a47cfdb441d56cd2570cdb5daed603c4a01"
BRANCH = "codex/BAT-706-cycle37-rework"
DATA = Path(r"C:\BatteredAggieSyndrome.data")
ATTEMPT5_ROOT = DATA / "ops" / "cycle37" / "attempt05"
MANAGER_A5 = DATA / "ops" / "manager_reviews" / "cycle37" / "attempt05" / "review-20260925T134703Z"
A5_POINTER = ATTEMPT5_ROOT / "release" / "CAREER_SUCCESSOR_POINTER.json"
DB_SHA256 = base.DB_SHA256
HEADLINES = base.HEADLINES
WORKER_LANES = a5o.WORKER_LANES
FINDING_IDS = ("MF37A05-01", "MF37A05-02", "MF37A05-03")
REQUIREMENT_LANES = {
    "R37A06-01": ("CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01"),
    "R37A06-02": ("LOCAL_INTEGRATION_CANDIDATE",),
    "R37A06-03": ("STORAGE_ADMISSION", "FINAL_PACKET"),
    "R37A06-04": ("WRITE_PROTECTION", "SOURCE_ADMISSION", "SOURCE_HARNESS", "SOURCE_REGRESSIONS", "CAREER_SUCCESSOR",
                  "INSTALLED_CONSUMER_C01", "TRUE_UNMOUNTED", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED"),
    "R37A06-05": WORKER_LANES,
}
A05_LANES = {lane: (lane,) for lane in WORKER_LANES} | {"MANAGER_REVIEW": ()}
CARRY_COMPOSITION = {"ORIGINAL_CRITERION": 345, "ORIGINAL_OBLIGATION": 148, "ORIGINAL_LANE": 22, "WORKER_FINDING": 73,
                     "MANAGER_FINDING": 18, "ATTEMPT3_CRITERION": 28, "ATTEMPT3_LANE": 13,
                     "ATTEMPT3_WORKER_FINDING": 12, "ATTEMPT4_CRITERION": 28, "ATTEMPT4_LANE": 13,
                     "ATTEMPT4_WORKER_FINDING": 15, "ATTEMPT5_CRITERION": 28, "ATTEMPT5_LANE": 15,
                     "ATTEMPT5_WORKER_FINDING": 16}
LABEL_PREFIX = "Cycle #37 \u2014 Attempt #6 \u2014"
OUTPUT_NAMES = ("LANE_RESULTS.json", "FINDING_CLOSURE_MATRIX.json", "DELIVERED_CONSUMER_MANIFEST.json",
                "PLATFORM_RECONCILIATION.json", "COST_AND_AUTHORITY_LEDGER.json", "CAREER_POPULATION_DISPOSITIONS.json",
                "INHERITED_LANE_EQUIVALENCE.json", "LOCAL_INTEGRATION_CANDIDATE.json", "INTEGRATION_DECISION_PACKET.md",
                "ORIGINAL_OBLIGATION_DISPOSITIONS.json", "WORKER_REPORT.md", "FINAL_PACKET_VALIDATION.json")
#: Storage evidence: the frozen segments with their snapshots, the current operational segment (frozen by the final
#: snapshot), and the final-output ledger that is never evidence.
STORAGE_DIR_NAME = Path("evidence") / "storage"
SEGMENTS = (("STORAGE_RESERVATIONS.jsonl", STORAGE_DIR_NAME / "STORAGE_OPERATIONAL_SEGMENT_01_SNAPSHOT.json"),
            (STORAGE_DIR_NAME / "STORAGE_RESERVATIONS_SEGMENT_02.jsonl",
             STORAGE_DIR_NAME / "STORAGE_OPERATIONAL_SEGMENT_02_SNAPSHOT.json"),
            (STORAGE_DIR_NAME / "STORAGE_RESERVATIONS_SEGMENT_03.jsonl", Path("STORAGE_EVIDENCE_SNAPSHOT.json")))
FINAL_OUTPUT_LEDGER = STORAGE_DIR_NAME / "STORAGE_RESERVATIONS_FINAL_OUTPUT.jsonl"
NEVER_EVIDENCE = ("lanes/RUNS.jsonl", FINAL_OUTPUT_LEDGER.as_posix())
CANDIDATE_GRANT = "APPEND_PRESERVED_LOCAL_INTEGRATION_CANDIDATE"
#: The evidence kinds the Attempt 6 contract's clauses name (R37A06-01..03 and R37A06-04..05). The Attempt 3 base's own
#: kind labels belong to its contract; every Attempt 6 evidence row carries one of these two (or a command log), and
#: ``check`` refuses a packet in which a worker clause's kind is carried by no evidence.
RAW = "bound_raw_execution_and_actual_consumer"
CENSUS = "complete_bound_population_and_receipts"


def rebind() -> None:
    """Point the Attempt 3 accounting at the Attempt 6 identity. The Attempt 4 and 5 helpers reused here keep their
    own constants, which is how they find the Attempt 3, 4 and 5 final lane receipts."""

    base.CYCLE_NUMBER, base.ATTEMPT_NUMBER, base.CYCLE_ID, base.ATTEMPT_ID = (CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID,
                                                                              ATTEMPT_ID)
    base.BASE_SHA = BASE_SHA
    base.BRANCH = BRANCH
    base.WORKER_LANES = WORKER_LANES
    a4o.LABEL_PREFIX = LABEL_PREFIX
    a5o.LABEL_PREFIX = LABEL_PREFIX
    a5o.CYCLE_NUMBER, a5o.ATTEMPT_NUMBER, a5o.CYCLE_ID, a5o.ATTEMPT_ID = (CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID,
                                                                          ATTEMPT_ID)
    a4o.CYCLE_NUMBER, a4o.ATTEMPT_NUMBER = CYCLE_NUMBER, ATTEMPT_NUMBER


def carry_category(key: str) -> str:
    for prefix, name in (("ORIGINAL-AC-", "ORIGINAL_CRITERION"), ("ORIGINAL-OBL-", "ORIGINAL_OBLIGATION"),
                         ("ORIGINAL-LANE-", "ORIGINAL_LANE"), ("A03-AC-", "ATTEMPT3_CRITERION"),
                         ("A03-LANE-", "ATTEMPT3_LANE"), ("A03-WORKER-", "ATTEMPT3_WORKER_FINDING"),
                         ("A04-AC-", "ATTEMPT4_CRITERION"), ("A04-LANE-", "ATTEMPT4_LANE"),
                         ("A04-WORKER-", "ATTEMPT4_WORKER_FINDING"), ("A05-AC-", "ATTEMPT5_CRITERION"),
                         ("A05-LANE-", "ATTEMPT5_LANE"), ("A05-WORKER-", "ATTEMPT5_WORKER_FINDING"),
                         ("WORKER-", "WORKER_FINDING")):
        if key.startswith(prefix):
            return name
    return "MANAGER_FINDING"


class Context(a5o.Context):
    def __init__(self, contract_path: Path, out_root: Path) -> None:
        super().__init__(contract_path, out_root)
        # Attempt 6 serves the Attempt 5 successor by its Attempt 5 pointer; it delivers no new successor.
        self.pointer_path = A5_POINTER
        self.pointer = read_json(A5_POINTER) if A5_POINTER.is_file() else {}
        self.findings_path = out_root / "evidence" / "NEW_FINDINGS_ATTEMPT6.json"
        self.ledger_path = out_root / "STORAGE_RESERVATIONS.jsonl"
        records = sorted((out_root / "evidence" / "integration").glob("CANDIDATE_APPEND_*.json"))
        self.candidate_record_paths = records
        self.candidate_record_path = records[-1] if records else None
        self.attempt5_lanes: list[dict[str, Any]] = []

    def storage(self) -> dict[str, Any]:
        """Every segment against its snapshot (the last only once the final snapshot exists)."""

        rows = []
        for number, (ledger, frozen) in enumerate(SEGMENTS, 1):
            ledger, frozen = self.out_root / ledger, self.out_root / frozen
            row: dict[str, Any] = {"segment": number, "ledger": str(ledger), "snapshot": str(frozen),
                                   "frozen": frozen.is_file()}
            if frozen.is_file():
                try:
                    row["verification"] = snapshot.verify(ledger, frozen)
                    document = snapshot.load_snapshot(frozen)
                    row.update(content_sha256=document["content_sha256"], measured=document["measured"],
                               bounded_stop=document.get("bounded_stop"), budget_bytes=document["configuration"]["budget_bytes"],
                               records=document["ledger"]["records"])
                except snapshot.SnapshotRefused as refusal:
                    row["verification"] = {"result": "REFUSED", "code": refusal.code, "detail": str(refusal)}
            else:
                status = storage_admission.Ledger(ledger).status() if ledger.is_file() else {}
                row["live_status"] = {k: status.get(k) for k in ("records", "budget_bytes", "added_bytes",
                                                                 "headroom_bytes", "open_reservations", "bounded_stop")}
            rows.append(row)
        final = self.out_root / FINAL_OUTPUT_LEDGER
        final_status = storage_admission.Ledger(final).status() if final.is_file() else {}
        return {"segments": rows, "final_output_ledger": {
            "path": str(final), "exists": final.is_file(), "evidence": False,
            "status": {k: final_status.get(k) for k in ("records", "budget_bytes", "added_bytes", "headroom_bytes",
                                                        "open_reservations", "bounded_stop")},
            "rule": ("Accounts for the final packet's own outputs after the operational freeze; it is appended after "
                     "the seal, so it is named here by path and never hashed as evidence.")},
            "all_segments_frozen_and_verified": all(r["frozen"] and (r.get("verification") or {}).get("result") == "PASS"
                                                    for r in rows)}


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
    # lanes/RUNS.jsonl is appended by every lane run: named by path in LANE_RESULTS.json, never evidence here.
    for identity, path, kind, scope in (
            ("E-REQUEST-LEDGER", root / "evidence" / "platform" / "REQUEST_LEDGER.jsonl", CENSUS,
             "Every counted platform request, retries included, appended before its result was used"),
            ("E-FAILURE-CLASSIFICATION", root / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json", CENSUS,
             "Worker classification of every failing identity of a red lane, by cause, kind, owner and next action"),
            ("E-NEW-FINDINGS", ctx.findings_path, CENSUS,
             "Findings discovered in Attempt 6, with severity, disposition, owner and next action"),
            ("E-CLEANUP-INVENTORY", root / "evidence" / "CLEANUP_INVENTORY.json", CENSUS,
             "Every directory this attempt created or wrote, its bytes, and what the owner may remove (nothing removed)"),
            ("E-BEFORE-REPRODUCTION", root / "evidence" / "before_run2" / "BEFORE_REPRODUCTION.json", RAW,
             "Before-repair reproduction of MF37A05-01..03 at the issued base: the manager's probes and two "
             "independent challenges through the Attempt 5 installed consumer")):
        if Path(path).is_file():
            ctx.add(identity, path, kind, scope)
    for folder in ("before", "before_run2"):
        for path in sorted((root / "evidence" / folder).rglob("*")):
            if path.is_file() and path.suffix in (".json", ".log", ".py", ".gz") and path.name != "BEFORE_REPRODUCTION.json":
                relative = path.relative_to(root / "evidence").as_posix()
                ctx.add(f"E-{relative}", path, RAW, f"Before-repair reproduction file {relative}")
    platform = root / "evidence" / "platform"
    for path in sorted(p for p in platform.rglob("*") if p.is_file() and p.suffix in (".json", ".csv", ".txt")
                       and p.parent != platform):
        relative = path.relative_to(platform).as_posix()
        ctx.add(f"E-PLATFORM-{relative}", path, CENSUS, f"Platform lifecycle evidence {relative}")
    for number, (ledger, frozen) in enumerate(SEGMENTS, 1):
        ledger, frozen = root / ledger, root / frozen
        if frozen.is_file():
            ctx.add(f"E-STORAGE-SEGMENT-{number:02d}-SNAPSHOT", frozen, CENSUS,
                    f"The immutable snapshot of operational storage segment {number}: sequence, chain head, prefix and "
                    "file digests, measured totals, configuration and predecessor")
            ctx.add(f"E-STORAGE-SEGMENT-{number:02d}-LEDGER", ledger, CENSUS,
                    f"Operational storage segment {number}, frozen by its snapshot and never written again")
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


# ------------------------------------------------------------------ lanes


def _relabel(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        row = dict(row)
        if row.get("disposition") == "CARRIED_BY_ATTEMPT5_LANE_AT_THE_CANDIDATE_HEAD":
            row["disposition"] = "CARRIED_BY_ATTEMPT6_LANE_AT_THE_CANDIDATE_HEAD"
            row["attempt6_lanes"] = row.pop("attempt5_lanes")
            row["attempt6_results"] = row.pop("attempt5_results")
            if "justification" in row:
                row["justification"] = row["justification"].replace("Attempt 5", "Attempt 6")
        out.append(row)
    return out


def _a05_final(lane: str) -> dict[str, Any]:
    index = ATTEMPT5_ROOT / "lanes" / "RUNS.jsonl"
    rows = [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [row for row in rows if row["lane"] == lane and row["head"] == BASE_SHA]
    return rows[-1] if rows else {}


def attempt5_lane_dispositions(ctx: Context) -> list[dict[str, Any]]:
    rows = []
    for lane, successors in A05_LANES.items():
        final = _a05_final(lane)
        row: dict[str, Any] = {"id": f"A05-LANE-{lane}", "attempt5_lane": lane, "attempt5_run": final.get("run"),
                               "attempt5_result": final.get("result"), "attempt5_head": final.get("head"),
                               "attempt5_receipt": final.get("receipt"),
                               "attempt5_receipt_sha256": final.get("receipt_sha256"),
                               "attempt5_receipt_preserved": bool(final.get("receipt")) and Path(final["receipt"]).is_file()}
        if not successors:
            row.update(disposition="MANAGER_OWNED", justification="The Attempt 5 manager lane is the manager's.")
        else:
            row.update(disposition="CARRIED_BY_ATTEMPT6_LANE_AT_THE_CANDIDATE_HEAD", attempt6_lanes=list(successors),
                       attempt6_results={s: (ctx.receipts[s]["result"] if ctx.at_head(s) else "NOT_AT_HEAD")
                                         for s in successors if s in ctx.receipts},
                       justification=("Re-executed fresh by the same-named Attempt 6 lane at the candidate head; the "
                                      "Attempt 5 receipt stays unchanged as the before-record (its result is never "
                                      "relabelled; a red Attempt 5 result stays red there)."))
        rows.append(row)
    return rows


# ------------------------------------------------------------------ inherited red lanes


def classify(ctx: Context) -> dict[str, Any]:
    """Derive the Attempt 6 classification from Attempt 5's, identity by identity and cause by cause."""

    previous_path = ATTEMPT5_ROOT / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json"
    previous = read_json(previous_path)
    lanes: dict[str, Any] = {}
    problems: list[str] = []
    for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED"):
        receipt = ctx.receipts.get(lane)
        if not receipt or receipt["result"] != "FAIL" or not ctx.at_head(lane):
            continue
        failing = base.failing_identities(receipt) or []
        comparison = (receipt.get("details") or {}).get("attempt5_comparison") or {}
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
                       "attempt5_run": (previous["lanes"].get(lane) or {}).get("run"), "groups": list(groups.values()),
                       "equivalence": {"persisting": len(comparison.get("persisting") or []),
                                       "persisting_same_cause": len(comparison.get("persisting_same_cause") or []),
                                       "new_in_attempt6": comparison.get("new_in_attempt6"),
                                       "no_longer_failing": comparison.get("no_longer_failing") or
                                       comparison.get("no_longer_reported")}}
    if problems:
        raise SystemExit("classification refused:\n" + "\n".join(problems))
    document = {"label": f"{LABEL_PREFIX} IN_PROGRESS_LOCAL_WORK_REMAINS (inherited failure classification)",
                "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
                "attempt_id": ATTEMPT_ID, "authored_at": utc_now(),
                "rule": ("Each failing identity keeps its Attempt 5 group only when it persists with the same traceback "
                         "cause (FULL_FINAL_MOUNTED) or the same finding line (STRICT_MOUNTED); anything else is refused "
                         "for manual classification."),
                "derived_from": {"path": str(previous_path), "sha256": sha256_file(previous_path)}, "lanes": lanes}
    write_output(ctx.out_root / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json", dumps(document))
    return document


def inherited_equivalence(ctx: Context, label: str) -> dict[str, Any]:
    rows = []
    for lane in WORKER_LANES:
        receipt = ctx.receipts.get(lane) or {}
        details = receipt.get("details") or {}
        final = _a05_final(lane)
        rows.append({"lane": lane, "attempt6_run": (ctx.runs.get(lane) or {}).get("run"), "attempt6_result": receipt.get("result"),
                     "at_candidate_head": ctx.at_head(lane), "counts": receipt.get("counts"),
                     "execution": "FRESH_AT_THE_CANDIDATE_HEAD" if ctx.at_head(lane) else "NOT_AT_HEAD",
                     "attempt5_run": final.get("run"), "attempt5_result": final.get("result"),
                     "attempt5_receipt": final.get("receipt"), "attempt5_receipt_sha256": final.get("receipt_sha256"),
                     "attempt5_comparison": details.get("attempt5_comparison"),
                     "failing_identities": base.failing_identities(receipt) if receipt.get("result") == "FAIL" else None})
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "candidate": ctx.candidate, "lanes": rows,
            "equivalence_used": [],
            "equivalence_statement": ("TP37-A06 permits a CHECK lane to carry an old execution by an explicit current "
                                      "dependency comparison. This attempt used none: every one of the 14 worker lanes "
                                      "executed fresh at the candidate head, because the consumer dependency "
                                      "(career_successor.py) changed and a fresh full mounted suite was therefore "
                                      "required once. Each Attempt 5 final receipt is retained unchanged as the "
                                      "before-record and compared by identity; no old execution is relabelled, and the "
                                      "Attempt 5 red lanes (FULL_FINAL_MOUNTED, STRICT_MOUNTED, FINAL_PACKET) stay red "
                                      "there."),
            "classification": ctx.classification, "original_lanes": ctx.original_lanes,
            "attempt3_lanes": ctx.attempt3_lanes, "attempt4_lanes": ctx.attempt4_lanes,
            "attempt5_lanes": ctx.attempt5_lanes,
            "rule": ("Inherited red lanes stay red until genuinely resolved. Equivalence is by exact identity and cause "
                     "against the Attempt 5 final receipts at the issued base; counts alone establish nothing.")}


# ------------------------------------------------------------------ criteria


def _d(ctx: Context, lane: str) -> dict[str, Any]:
    return ctx.details(lane)


def _holds(ctx: Context, lane: str, key: str) -> bool:
    return bool((_d(ctx, lane).get(key) or {}).get("holds"))


def _before(ctx: Context, finding: str) -> bool:
    path = ctx.out_root / "evidence" / "before_run2" / "BEFORE_REPRODUCTION.json"
    return bool(path.is_file() and (read_json(path).get("reproduced") or {}).get(finding))


def _lineage_originals(ctx: Context) -> list[str]:
    cases = (_d(ctx, "INSTALLED_CONSUMER_C01").get("lineage_fixtures") or {}).get("cases") or {}
    return [name for name, row in cases.items() if not row.get("refused_for_the_intended_cause")] if cases else ["none"]


def judge(ctx: Context, key: str, requirement: str) -> tuple[str, str]:
    needed = REQUIREMENT_LANES[requirement]
    installed, career = _d(ctx, "INSTALLED_CONSUMER_C01"), _d(ctx, "CAREER_SUCCESSOR")
    if requirement == "R37A06-01":
        failing = [lane for lane in needed if not ctx.lane_ok(lane)]
        failing += [f"{lane}:{k}" for lane, k in (("INSTALLED_CONSUMER_C01", "a6_forgeries"),
                                                  ("INSTALLED_CONSUMER_C01", "installed_identity_census"),
                                                  ("INSTALLED_CONSUMER_C01", "manager_a5_successor_adversarial"),
                                                  ("INSTALLED_CONSUMER_C01", "manager_a5_successor_population_audit"),
                                                  ("CAREER_SUCCESSOR", "independent_identity_census"))
                    if not _holds(ctx, lane, k)]
        failing += [f"source binding {k}" for k, v in (career.get("source_identity_checks") or {"none": False}).items() if not v]
        failing += [f"original negative {name}" for name in _lineage_originals(ctx)]
        if not (installed.get("successor_pagination") or {}).get("reconciled"):
            failing.append("complete pagination")
        if key.endswith("-C") and not _before(ctx, "MF37A05-01"):
            failing.append("before-repair reproduction")
        if failing:
            return "IN_PROGRESS", "not yet held at the candidate head: " + ", ".join(failing)
        forgeries = installed["a6_forgeries"]["cases"]
        census = career["independent_identity_census"]
        return "VERIFIED_LOCAL", (
            "Every served episode is bound to its own raw capture and to typed predecessor and Attempt 4 identities: "
            f"the repaired verifier binds {census['rows']} rows, {census['predecessor_rows_dispositioned']} predecessor "
            f"dispositions and {census['a04_rows_mapped']} Attempt 4 mappings, and an independent census (no producer "
            f"import) re-read all {census['raw_files']} captures with 0 mismatches while keeping the legitimate classes "
            f"({', '.join(f'{k} {v}' for k, v in census['legitimate_classes'].items())}). Through the fresh installed "
            f"CLI, {sum(1 for n in forgeries if not n.endswith('_genuine'))} independent forgeries (reciprocal cross-"
            "person swaps in both formats, wrong family and revision edges, an unrelated valid capture, display-name "
            "and Wikidata relabels, a contradictory cross-version mapping) are each refused for their own cause, both "
            "manager forgeries are refused, the original missing/dangling/nonreciprocal/duplicate/missing-raw negatives "
            "stay refused, and full pagination serves the genuine population unchanged."
            + (" Before repair, the manager's probes and two independent challenges reproduced the acceptance at the "
               "issued base." if key.endswith("-C") else ""))
    if requirement == "R37A06-02":
        failing = [lane for lane in needed if not ctx.lane_ok(lane)]
        checks = _d(ctx, "LOCAL_INTEGRATION_CANDIDATE").get("candidate_tree_checks") or {}
        failing += [k for k, v in checks.items() if not v] or ([] if checks else ["tree checks"])
        failing += [k for k in ("candidate_negatives", "manager_a5_integration_replay", "candidate_consumer")
                    if not _holds(ctx, "LOCAL_INTEGRATION_CANDIDATE", k)]
        if not ctx.candidate_record_path:
            failing.append("append record")
        if key.endswith("-C") and not _before(ctx, "MF37A05-02"):
            failing.append("before-repair reproduction")
        if failing:
            return "IN_PROGRESS", "not yet held: " + ", ".join(failing)
        proof = _d(ctx, "LOCAL_INTEGRATION_CANDIDATE").get("committed_tree_proof") or {}
        return "VERIFIED_LOCAL", (
            "One normal [material] commit was appended to the preserved candidate (its parent is the preserved head "
            f"{candidate.ISSUED_CANDIDATE_HEAD[:8]}; only the candidate ref moved; main and the repair branch unchanged). "
            "Its provenance was generated by the tree's own canonical generator from a bounded owned byte-for-byte "
            f"materialization and proved against its committed Git blobs: {proof.get('committed_paths')} committed "
            f"paths, {proof.get('manifest_rows')} manifest rows, 0 mismatches; main's exact control blobs kept, the "
            "paid workflow still absent. Changed, absent, stale-view and skip-worktree-masked negatives are refused; "
            "the consumer built from the candidate tree serves and refuses a forgery; its own suites pass; the two "
            "control compatibility errors are characterized as an owner decision and the candidate is not "
            "publication-ready.")
    if requirement == "R37A06-03":
        storage = ctx.storage()
        live = ((_d(ctx, "STORAGE_ADMISSION").get("storage_ledger") or {}).get("live_over_budget_control") or {}).get("refused")
        stable = (_d(ctx, "STORAGE_ADMISSION").get("storage_ledger") or {}).get(
            "hash_stable_while_the_operational_segment_progressed")
        failing = [lane for lane in needed if not ctx.lane_ok(lane)]
        if not live:
            failing.append("live over-budget refusal")
        if not stable:
            failing.append("frozen segments hash-stable while the operational segment progressed")
        if not storage["all_segments_frozen_and_verified"]:
            failing.append("every operational segment frozen and verified")
        validation = sorted((ctx.out_root / "evidence" / "final").glob("FINAL_PACKET_VALIDATION_*.json"))
        if not validation or read_json(validation[-1]).get("result") != "PASS":
            failing.append("FINAL_PACKET validation receipt PASS")
        if key.endswith("-C") and not _before(ctx, "MF37A05-03"):
            failing.append("before-repair reproduction")
        if failing:
            return "IN_PROGRESS", "not yet held: " + ", ".join(failing)
        return "VERIFIED_LOCAL", (
            "The operational ledger is separate from immutable evidence: each of the three operational segments was "
            "frozen, with every reservation closed, into a create-only snapshot (sequence, chain head, prefix and file "
            "digests, measured totals, predecessor) that verifies as a hash-stable prefix while later work proceeds; "
            "each successor segment continues with exactly the frozen headroom, and two genuine budget underestimates "
            "were bounded before any further allocation (W37A06-01, W37A06-02). After the last freeze the runner "
            "refuses every material lane; FINAL_PACKET reserves on the separate final-output ledger, verifies the "
            "snapshots and the packet, and writes a create-only receipt. No ledger a later step writes is sealed; the "
            "Attempt 5 ledger and failed run are retained unchanged.")
    if requirement == "R37A06-04":
        failing = [lane for lane in needed if lane not in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED") and not ctx.lane_ok(lane)]
        failing += [lane for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED") if not ctx.executed(lane)]
        for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED"):
            comparison = _d(ctx, lane).get("attempt5_comparison") or {}
            if comparison.get("new_in_attempt6"):
                failing.append(f"{lane} new identities {comparison['new_in_attempt6']}")
        named = (installed.get("successor_named_cases") or {}).get("holds") or {}
        failing += [f"named {k}" for k, v in named.items() if not v] or ([] if named else ["named cases"])
        failing += [k for k in ("manager_a3_career_challenge", "manager_a4_career_semantic_census",
                                "manager_a4_successor_challenge", "manager_a5_career_semantic_census",
                                "manager_a5_successor_adversarial") if not _holds(ctx, "INSTALLED_CONSUMER_C01", k)]
        if not (installed.get("successor_coverage") or {}).get("predecessor_identity_sets_equal"):
            failing.append("successor coverage")
        if failing:
            return "IN_PROGRESS", "not yet held: " + ", ".join(failing)
        text = {"A": ("All 72,958 genuine rows and 7,950 captures verify; all 72,070 default and 73,082 Attempt 4 "
                      "predecessor rows keep one disposition; the legitimate alias, new, split, removed, missing-team "
                      "and other-sport classes serve with their explicit meanings; the one affected entrypoint (the "
                      "successor verifier) is repaired as a class, no data rebuilt and no fact invented."),
                "B": ("One fresh offline noneditable BAS wheel, composed with the released C01 wheel, paginates the whole "
                      "successor and every filter exactly as the independent SQL oracle and raw identity census derive "
                      "them, and refuses both manager identity forgeries; lost-field and adoption limits are retained."),
                "C": ("The guard, date, defensive-unit, unknown-role, Cory/Danny/Steve, scoring/PIT, harness, "
                      "default/legacy and Cycle 29 behavior pass their suites and the manager replays at the candidate "
                      "head; the full mounted suite ran fresh once and matches Attempt 5 identity for identity with no "
                      "new failure; databases, frozen predictions and defaults are unchanged; the 2,223-row staff "
                      "backlog stays owned.")}[key[-1]]
        return "VERIFIED_LOCAL", text
    # R37A06-05
    if key.endswith("-A"):
        missing = [lane for lane in WORKER_LANES if not ctx.executed(lane)]
        if not missing:
            return "VERIFIED_LOCAL", ("The Attempt 6 lane and output tools were implemented and inspected; tiny storage "
                                      "and seal fixtures qualified first (storage and snapshot suites); every one of the "
                                      "14 worker lanes executed fresh through the issued command at the candidate head "
                                      "with exact binding and raw counts; no equivalence was relabelled and inherited "
                                      "red stays red, compared with Attempt 5 by identity and cause.")
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
            and ctx.lane_ok("FINAL_PACKET") and storage["all_segments_frozen_and_verified"])
    if held:
        return "VERIFIED_LOCAL", ("All 774 carryforward identities keep their meanings and dispositions; 20 clauses, 15 "
                                  "lanes, findings and effects are accounted in a generated report, checklist and "
                                  "submission; the append-only candidate carries committed-blob provenance and "
                                  "consumer proof; the storage evidence is immutable with every reservation reconciled "
                                  "before its freeze; FINAL_PACKET passes. Nothing is claimed about adoption, "
                                  "integration or acceptance.")
    return "IN_PROGRESS", ("; ".join(problems[:3]) or
                           f"PLATFORM_CARRY {ctx.lane_ok('PLATFORM_CARRY')}, candidate "
                           f"{ctx.lane_ok('LOCAL_INTEGRATION_CANDIDATE')}, FINAL_PACKET {ctx.lane_ok('FINAL_PACKET')}, "
                           f"storage frozen {storage['all_segments_frozen_and_verified']}")


def criterion_evidence(ctx: Context, requirement: str) -> list[str]:
    ids: list[str] = []
    for lane in REQUIREMENT_LANES[requirement]:
        if ctx.executed(lane):
            ids += [f"E-LANE-{lane}-RECEIPT", f"E-LANE-{lane}-LOG"]
    extra = {"R37A06-01": ["E-BEFORE-REPRODUCTION"],
             "R37A06-02": ["E-BEFORE-REPRODUCTION", "E-CANDIDATE-APPEND-RECORD",
                           "E-OUTPUT-LOCAL_INTEGRATION_CANDIDATE.json"],
             "R37A06-03": ["E-BEFORE-REPRODUCTION"] + [f"E-STORAGE-SEGMENT-{n:02d}-{k}" for n in (1, 2, 3)
                                                      for k in ("SNAPSHOT", "LEDGER")]
                          + [e for e in ctx.evidence if e.startswith("E-FINAL-")],
             "R37A06-04": ["E-OUTPUT-CAREER_POPULATION_DISPOSITIONS.json", "E-OUTPUT-DELIVERED_CONSUMER_MANIFEST.json",
                           "E-FAILURE-CLASSIFICATION"],
             "R37A06-05": ["E-ORIGINAL-OBLIGATIONS", "E-FAILURE-CLASSIFICATION", "E-REQUEST-LEDGER",
                           "E-OUTPUT-LANE_RESULTS.json", "E-CANDIDATE-APPEND-RECORD",
                           "E-OUTPUT-LOCAL_INTEGRATION_CANDIDATE.json", "E-STORAGE-SEGMENT-03-SNAPSHOT"]}[requirement]
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
        if key.endswith("-B") and criterion["requirement"] == "R37A06-05":
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
        elif row["id"].startswith(("ORIGINAL-LANE-", "A03-LANE-", "A04-LANE-", "A05-LANE-")):
            evidence.append("E-OUTPUT-LANE_RESULTS.json")
        rows.append({"id": row["id"], "disposition": row["disposition"], "attempt6_state": state,
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
        if item["id"] == "U-INDEPENDENT-REVIEW" and "E-LANE-START_CONTEXT-RECEIPT" in ctx.evidence:
            item["evidence_ids"] = ["E-LANE-START_CONTEXT-RECEIPT"]
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
    before = ctx.out_root / "evidence" / "before_run2" / "BEFORE_REPRODUCTION.json"
    reproduction = read_json(before) if before.is_file() else {}
    plan = {
        "MF37A05-01": ([_f(MANAGER_A5 / "SUCCESSOR_ADVERSARIAL_REVIEW.json"), _f(MANAGER_A5 / "successor_adversarial.py"),
                        _f(MANAGER_A5 / "SUCCESSOR_IDENTITY_CENSUS.json"), _f(before)],
                       {"CAREER_SUCCESSOR": "source_identity_checks", "INSTALLED_CONSUMER_C01": "a6_forgeries"}),
        "MF37A05-02": ([_f(MANAGER_A5 / "INTEGRATION_MANIFEST_REVIEW.json"), _f(MANAGER_A5 / "integration_and_storage.py"),
                        _f(before)],
                       {"LOCAL_INTEGRATION_CANDIDATE": "candidate_tree_checks"}),
        "MF37A05-03": ([_f(MANAGER_A5 / "STORAGE_SEAL_REVIEW.json"), _f(MANAGER_A5 / "SEAL_DEPENDENCY_PROOF.json"),
                        _f(ATTEMPT5_ROOT / "STORAGE_RESERVATIONS.jsonl"), _f(before)],
                       {"STORAGE_ADMISSION": "storage_ledger", "FINAL_PACKET": "storage_verification"}),
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
        commits = ctx.finding_commits(key)
        if key == "MF37A05-02":
            for path in ctx.candidate_record_paths:
                record = read_json(path)
                commits = commits + [{"sha": record["candidate_commit"],
                                      "subject": git_out("log", "-1", "--format=%s", record["candidate_commit"]),
                                      "branch": candidate.CANDIDATE_BRANCH}]
        rows.append({
            "finding": key, "requirement": requirement["id"], "original_meaning": carry[key]["original_meaning"],
            "reproduced_before_repair": (reproduction.get("reproduced") or {}).get(key),
            "worker_disposition": "REPAIRED_LOCAL_PENDING_MANAGER_REPLAY", "commits": commits,
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
    manifest = a5o.consumer_manifest(ctx, label)
    installed, career = _d(ctx, "INSTALLED_CONSUMER_C01"), _d(ctx, "CAREER_SUCCESSOR")
    manifest.update({
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "attempt6_identity_verification": {
            "verifier_version": (career.get("source_identity_bindings") or {}).get("verifier_version"),
            "source_bindings": career.get("source_identity_bindings"), "source_checks": career.get("source_identity_checks"),
            "independent_identity_census": career.get("independent_identity_census"),
            "installed_forgeries": installed.get("a6_forgeries"),
            "installed_identity_census": {k: v for k, v in (installed.get("installed_identity_census") or {}).items()
                                          if k != "census"}},
        "manager_a5_replays": {k: installed.get(k) for k in ("manager_a5_successor_adversarial",
                                                             "manager_a5_successor_population_audit",
                                                             "manager_a5_career_semantic_census")},
        "delivered_successor_note": ("Attempt 6 delivers no new successor: it serves the Attempt 5 file by its Attempt 5 "
                                     "pointer, unchanged, and repairs the consumer that verifies it."),
    })
    return manifest


def population_document(ctx: Context, label: str) -> dict[str, Any]:
    document = a5o.population_document(ctx, label)
    career = _d(ctx, "CAREER_SUCCESSOR")
    census = career.get("independent_identity_census") or {}
    document.update({"cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
                     "attempt6_identity_census": census,
                     "attempt6_legitimate_classes": census.get("legitimate_classes"),
                     "attempt6_source_bindings": career.get("source_identity_bindings"),
                     "successor_pointer": {"path": str(A5_POINTER), "sha256": sha256_file(A5_POINTER)},
                     "note": document.get("note", "") + (" Attempt 6 re-verified every row against its own raw capture "
                                                         "and predecessor and Attempt 4 rows; nothing was rebuilt.")})
    return document


def candidate_document(ctx: Context, label: str) -> dict[str, Any]:
    details = _d(ctx, "LOCAL_INTEGRATION_CANDIDATE")
    record = read_json(ctx.candidate_record_path) if ctx.candidate_record_path else {}
    appends = [{k: read_json(path).get(k) for k in ("created_at", "previous_candidate_head", "candidate_commit",
                                                    "repair_head", "refs_changed")} | {"record": str(path)}
               for path in ctx.candidate_record_paths]
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "requirement": "R37A06-02", "finding": "MF37A05-02", "appends": appends,
            "repair_candidate": ctx.candidate,
            "grant": next((g for g in ctx.contract["authority"]["grants"] if g["action"] == CANDIDATE_GRANT), None),
            "integration_candidate": candidate.describe(),
            "append_record": {"path": str(ctx.candidate_record_path) if ctx.candidate_record_path else None,
                              "sha256": sha256_file(ctx.candidate_record_path) if ctx.candidate_record_path else None,
                              **{k: record.get(k) for k in ("created_at", "previous_candidate_head", "candidate_commit",
                                                            "candidate_tree", "repair_head", "refs_changed",
                                                            "only_the_candidate_ref_changed", "previous_head_is_parent",
                                                            "tree_differs_from_repair_in", "provenance_files",
                                                            "validation_view", "worktree")}},
            "lane": {"run": ctx.runs.get("LOCAL_INTEGRATION_CANDIDATE"),
                     "result": (ctx.receipts.get("LOCAL_INTEGRATION_CANDIDATE") or {}).get("result"),
                     "tree_checks": details.get("candidate_tree_checks"),
                     "committed_tree_proof": {k: v for k, v in (details.get("committed_tree_proof") or {}).items()
                                              if k != "protected_entries"},
                     "generated_view": details.get("candidate_generated_view"),
                     "negatives": details.get("candidate_negatives"), "history_policy": details.get("candidate_history_policy"),
                     "manager_a5_integration_replay": details.get("manager_a5_integration_replay"),
                     "consumer": details.get("candidate_consumer"),
                     "review_control_characterization": details.get("candidate_review_control_characterization")},
            "decision_for_the_owner": ("The candidate keeps main's protected scientific-review controls (the paid "
                                       "workflow stays absent); the repair branch's own changes to them are withheld "
                                       "because changing trusted controls on main is an owner decision this contract "
                                       "does not grant. The tests the branch wrote for its own controls fail against "
                                       "main's (the two control compatibility errors); with them the candidate is not "
                                       "publication-ready."),
            "not_done": ("No push, remote PR, merge, retarget, closure, deletion, reset, history rewrite or activation; "
                         "the preserved first candidate stays reachable as the parent and every other ref kept its commit.")}


def final_packet_document(ctx: Context, label: str) -> dict[str, Any]:
    run = ctx.runs.get("FINAL_PACKET") or {}
    receipt = ctx.receipts.get("FINAL_PACKET") or {}
    validation = (receipt.get("final_packet_validation") or {}) if ctx.at_head("FINAL_PACKET") else {}
    path = Path(validation.get("path") or "")
    content = read_json(path) if validation and path.is_file() else None
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "candidate": ctx.candidate,
            "state": (content or {}).get("result") or "PENDING_FINAL_PACKET_LANE",
            "lane_run": run.get("run"), "lane_result": receipt.get("result"),
            "validation_receipt": {"path": str(path) if content else None,
                                   "sha256": sha256_file(path) if content else None,
                                   "recorded_sha256": validation.get("sha256")},
            "validation": content, "storage": ctx.storage(),
            "sealing_order": ["every material lane on operational segment 3", "every reservation reconciled",
                              "segment 3 frozen into STORAGE_EVIDENCE_SNAPSHOT.json", "final-output ledger opened from "
                              "its headroom", "IN_PROGRESS outputs built and sealed under a final-ledger reservation",
                              "FINAL_PACKET lane (frozen snapshots, packet check, v2.4.0 accounting, create-only receipt)",
                              "terminal build, generated checklist, seal", "post-seal accounting receipt",
                              "final reservation reconciled (the final-output ledger is never evidence)"]}


def platform_reconciliation(ctx: Context, label: str) -> dict[str, Any]:
    document = a5o.platform_reconciliation(ctx, label)
    document["cycle_number"], document["attempt_number"] = CYCLE_NUMBER, ATTEMPT_NUMBER
    document["label_note"] = ("Every Attempt 6 platform receipt carries the numeric label. The BEFORE reads bound the "
                              "issued base head with the first repair still uncommitted in the worktree (clean false); "
                              "the DURING reads follow the M1/M2 qualification and the AFTER reads bind the final head.")
    return document


def cost_ledger(ctx: Context, label: str) -> dict[str, Any]:
    document = base.cost_ledger(ctx, label)
    document["cycle_number"], document["attempt_number"] = CYCLE_NUMBER, ATTEMPT_NUMBER
    document["grants_used"] = effects(ctx)
    storage = ctx.storage()
    last = next((row for row in reversed(storage["segments"]) if row.get("measured")), {})
    first = storage["segments"][0]
    document["storage"].update({
        "segments": storage["segments"], "final_output_ledger": storage["final_output_ledger"],
        "attempt_budget_bytes": first.get("budget_bytes"),
        "added_bytes_through_last_frozen_segment": (first.get("budget_bytes") or 0) - (last.get("measured") or {}).get(
            "headroom_bytes", 0) if last else None,
        "rule": ("Each segment's budget is exactly the previous frozen segment's headroom, so the 4 GiB attempt ceiling "
                 "is cumulative across segments; the added bytes of the attempt are the ceiling less the last frozen "
                 "headroom. Reservations measure retained bytes at reconciliation; transient peaks (a SQLite rollback "
                 "journal) count only where a bounded run polls, and the 8 GiB free reserve bounds them."),
        "bounded_stops": [row.get("bounded_stop") for row in storage["segments"] if row.get("bounded_stop")]})
    return document


def effects(ctx: Context) -> list[dict[str, Any]]:
    rows = base.effects(ctx)
    for row in rows:
        if row["id"] == "EFF-LOCAL-COMMITS":
            row["evidence_ids"] = [e for e in ("E-LANE-START_CONTEXT-RECEIPT",) if e in ctx.evidence] or ["E-ORIGINAL-OBLIGATIONS"]
    grant = next((g for g in ctx.contract["authority"]["grants"] if g["action"] == CANDIDATE_GRANT), None)
    for number, path in enumerate(ctx.candidate_record_paths, 1):
        identity = "E-CANDIDATE-APPEND-RECORD" if path == ctx.candidate_record_path else f"E-CANDIDATE-APPEND-RECORD-{number}"
        if not grant or identity not in ctx.evidence:
            continue
        record = read_json(path)
        rows.append({"id": f"EFF-APPEND-LOCAL-INTEGRATION-CANDIDATE-{number}", "actor": grant["actor"],
                     "action": grant["action"], "target": grant["target"], "result": "SUCCEEDED",
                     "detail": (f"One forward commit {record.get('candidate_commit')} on {candidate.CANDIDATE_BRANCH} "
                                f"with parent {record.get('previous_candidate_head')}, from repair head "
                                f"{record.get('repair_head')}; refs changed {record.get('refs_changed')}; shared "
                                "objects, that worktree's index and the named ref only; no new branch or worktree, "
                                "push, merge, deletion or rewrite."),
                     "evidence_ids": [identity]})
    return rows


def integration_packet(ctx: Context, label: str, lanes: list[dict[str, Any]]) -> str:
    text = base.integration_packet(ctx, label, lanes)
    description = candidate.describe()
    record = read_json(ctx.candidate_record_path) if ctx.candidate_record_path else {}
    proof = _d(ctx, "LOCAL_INTEGRATION_CANDIDATE").get("committed_tree_proof") or {}
    github = ctx.latest_github or {}
    extra = ["### The preserved local integration candidate, appended (nothing published)", "",
             f"Branch `{description.get('candidate_branch')}` in `{description.get('candidate_worktree')}`: the preserved "
             f"head `{candidate.ISSUED_CANDIDATE_HEAD}` stays reachable below {len(ctx.candidate_record_paths)} appended "
             f"`[material]` commit(s) ending at `{description.get('candidate_head')}` (tree "
             f"`{description.get('candidate_tree')}`), the last built from repair head `{record.get('repair_head')}`. "
             f"Main `{description.get('main')}` and the repair branch keep their commits; only the candidate ref moved "
             f"({record.get('refs_changed')}).", "",
             f"Committed provenance, proved against the committed blobs: {proof.get('committed_paths')} paths, "
             f"{proof.get('manifest_rows')} manifest rows, {proof.get('current_tree_rows')} CURRENT_TREE rows, "
             f"consistent {proof.get('consistent')}; protected entries equal main {proof.get('protected_entries_equal_main')}.",
             "", "| Path | Main | Repair branch | Candidate |", "| --- | --- | --- | --- |"]
    for row in description.get("protected_paths") or []:
        extra.append(f"| `{row['path']}` | {(row.get('main') or ['', 'absent'])[1][:12]} | "
                     f"{(row.get('repair') or ['', 'absent'])[1][:12]} | {(row.get('candidate') or ['', 'absent'])[1][:12]} |")
    extra += ["", "Owner decisions this candidate needs (none taken): whether the repair branch's review-control changes "
              "(the retired Codex review and the paid-review gate) should reach main -- until then the two control "
              "compatibility errors remain and the candidate is not publication-ready; publication of the candidate "
              f"branch; merge through a reviewed PR with the {github.get('unresolved_thread_total')} unresolved review "
              f"threads of the {github.get('open_pr_count')} open PRs dispositioned. Rollback of any future merge: revert "
              "the candidate commits.", ""]
    return text + "\n".join(extra) + "\n"


# ------------------------------------------------------------------ build


def build(ctx: Context, headline: str, writer_released: bool) -> dict[str, Any]:
    register_evidence(ctx)
    root = ctx.out_root
    lanes = base.lane_rows(ctx)
    ctx.original_lanes = _relabel(a5o.original_lane_dispositions(ctx))
    ctx.attempt3_lanes = _relabel(a5o.attempt3_lane_dispositions(ctx))
    ctx.attempt4_lanes = _relabel(a5o.attempt4_lane_dispositions(ctx))
    ctx.attempt5_lanes = attempt5_lane_dispositions(ctx)
    obligations_path = root / "ORIGINAL_OBLIGATION_DISPOSITIONS.json"
    label = f"{LABEL_PREFIX} {headline}"

    def write_obligations(states: dict[str, dict[str, Any]]) -> None:
        items = []
        for row in ctx.contract["carryforward"]:
            item = {"id": row["id"], "category": carry_category(row["id"]),
                    **{k: row[k] for k in ("original_meaning", "disposition", "source_ids", "requirement_ids",
                                           "acceptance_ids", "owner", "reason", "next_action", "prior_mapping")}}
            if row["id"] in states:
                item["attempt6_state"] = states[row["id"]]["attempt6_state"]
                item["attempt6_evidence_ids"] = [e for e in states[row["id"]]["evidence_ids"] if e != "E-ORIGINAL-OBLIGATIONS"]
            items.append(item)
        ctx.carry_counts = {"composition": dict(collections.Counter(i["category"] for i in items)),
                            "dispositions": dict(collections.Counter(i["disposition"] for i in items))}
        ctx.obligation_items = items
        write_output(obligations_path, dumps({
            "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "contract_sha256": ctx.contract_sha256, "candidate": ctx.candidate,
            **ctx.carry_counts, "items": items, "original_lanes": ctx.original_lanes,
            "attempt3_lanes": ctx.attempt3_lanes, "attempt4_lanes": ctx.attempt4_lanes,
            "attempt5_lanes": ctx.attempt5_lanes,
            "note": ("Original meanings, sources, owners, reasons, next actions, prior mappings and dispositions are "
                     "copied from the issued contract unchanged. OWNED_BACKLOG items stay owned; none is marked "
                     "fulfilled by this accounting.")}))
        ctx.add("E-ORIGINAL-OBLIGATIONS", obligations_path, CENSUS,
                "All 774 carryforward identities with their original meanings and unchanged dispositions")

    write_obligations({})
    write_output(root / "LANE_RESULTS.json", dumps({
        "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "candidate": ctx.candidate,
        "runner": "tools/cycle37/attempt06_lanes.py", "runs_index": str(root / "lanes" / "RUNS.jsonl"),
        "runs_index_rule": "append-only lane index, named by path; never sealed as evidence (every lane run appends)",
        "lanes": lanes, "original_lanes": ctx.original_lanes, "attempt3_lanes": ctx.attempt3_lanes,
        "attempt4_lanes": ctx.attempt4_lanes, "attempt5_lanes": ctx.attempt5_lanes}))
    ctx.add("E-OUTPUT-LANE_RESULTS.json", root / "LANE_RESULTS.json", CENSUS,
            "Every required lane's result at the candidate head; the 22 original and the Attempt 3, 4 and 5 lanes")
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
    census = _d(ctx, "CAREER_SUCCESSOR").get("independent_identity_census") or {}
    if ctx.lane_ok("INSTALLED_CONSUMER_C01") and ctx.lane_ok("CAREER_SUCCESSOR"):
        forgeries = (installed.get("a6_forgeries") or {}).get("cases") or {}
        data_evidence = (f"DELIVERED_RELEASE_{DB_SHA256[:12]}_UNCHANGED; A5_SUCCESSOR_"
                         f"{str(ctx.pointer.get('successor_sha256'))[:12]}_ROWS_{census.get('rows')}_SERVED_UNCHANGED; "
                         f"RAW_CAPTURES_{census.get('raw_files')}_IDENTITY_MISMATCHES_0; PREDECESSOR_"
                         f"{census.get('predecessor_rows_dispositioned')}_A04_{census.get('a04_rows_mapped')}_BOUND; "
                         f"FORGERIES_REFUSED_{sum(1 for k, v in forgeries.items() if not k.endswith('_genuine') and v.get('holds'))}; "
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
    executed = [lane for lane in WORKER_LANES if ctx.executed(lane)]
    ctx.all_runs_clean = bool(executed) and all(
        ctx.receipts[lane]["source_binding"].get("clean") and ctx.receipts[lane]["source_binding_after"].get("clean")
        for lane in executed)
    import attempt06_report  # the narrative report, beside this tool  # noqa: PLC0415

    write_output(root / "WORKER_REPORT.md", attempt06_report.render(ctx, submission))
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
    frozen = ctx.out_root / "STORAGE_EVIDENCE_SNAPSHOT.json"
    if frozen.is_file() and not str(read_json(frozen).get("label", "")).startswith(LABEL_PREFIX):
        problems.append("STORAGE_EVIDENCE_SNAPSHOT.json does not carry the numeric identity label")
    lanes_doc = ctx.out_root / "LANE_RESULTS.json"
    if lanes_doc.is_file():
        document = read_json(lanes_doc)
        if {row["id"] for row in document["lanes"]} != set(ctx.lanes):
            problems.append("LANE_RESULTS lane set differs from the contract's")
        for key, prefix in (("original_lanes", "ORIGINAL-LANE-"), ("attempt3_lanes", "A03-LANE-"),
                            ("attempt4_lanes", "A04-LANE-"), ("attempt5_lanes", "A05-LANE-")):
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
            problems.append("FINDING_CLOSURE_MATRIX does not cover exactly MF37A05-01..03")
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
    submission_path = ctx.out_root / "submission.json"
    if submission_path.is_file():
        submission = read_json(submission_path)
        for row in submission.get("evidence") or []:
            relative = Path(row["path"]).resolve().relative_to(ctx.out_root.resolve()).as_posix()
            if relative in NEVER_EVIDENCE:
                problems.append(f"submission evidence {row['id']} names {relative}, which a later step writes")
            elif final_packet and sha256_file(Path(row["path"])) != row["sha256"]:
                # Before the final packet an interim build may be superseded (the platform lane appends its request
                # ledger); from the final packet on, sealed evidence must be stable.
                problems.append(f"submission evidence {row['id']} changed after the seal")
    if submission_path.is_file():
        kinds = {row["kind"] for row in read_json(submission_path).get("evidence") or []}
        wanted = {c["evidence_kind"] for c in ctx.criteria.values() if c["executor"] == "worker"}
        if not wanted <= kinds:
            problems.append(f"no evidence carries the contract's kind(s) {sorted(wanted - kinds)}")
    if final_packet:
        storage = ctx.storage()
        if not storage["all_segments_frozen_and_verified"]:
            problems.append(f"not every operational segment is frozen and verified: "
                            f"{[(r['segment'], (r.get('verification') or {}).get('result')) for r in storage['segments']]}")
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
                      "lanes": {row["id"]: row["status"] for row in submission["lanes"]},
                      "unfinished": [(u["id"], u["kind"]) for u in submission["unfinished"]],
                      "evidence": len(submission["evidence"])}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
