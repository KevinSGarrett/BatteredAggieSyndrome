r"""Cycle #37 — Attempt #7 — worker outputs, submission and accounting check (R37A07-05).

    attempt07_outputs.py classify --contract C --out-root R
    attempt07_outputs.py build --contract C --out-root R [--headline H --writer-released]
    attempt07_outputs.py check --contract C --out-root R [--final-packet]
    attempt07_outputs.py seal --contract C --out-root R

The Attempt 6 accounting (``attempt06_outputs``, over the Attempt 5, 4 and 3 bases) rebound to the Attempt 7
contract: 18 declared outputs (the CONTROL-07 proposal pair among them), 819 carryforward identities, 20 clauses and
15 lanes. ``build`` writes the outputs from what is there -- the issued contract, the lane receipts, the platform
receipts and request ledger, the storage ledger chain and its snapshot, the candidate append records, the CONTROL-07
validation receipt, git, and worker-authored evidence it reads but never invents
(``evidence/INHERITED_FAILURE_CLASSIFICATION.json``, ``evidence/NEW_FINDINGS_ATTEMPT7.json``,
``evidence/CLEANUP_INVENTORY.json``).

MF37A06-02: the attempt has one storage ledger chain. The root ledger ``STORAGE_RESERVATIONS.jsonl`` carries every
material reservation; it is registered as evidence only once ``STORAGE_EVIDENCE_SNAPSHOT.json`` freezes it, together
with its append-only head log and the create-only claim naming its one continuation. That continuation, the
final-output ledger, inherits the root's budget and baselines, accounts for the final packet's own outputs after the
seal, and is named by path only. ``lanes/RUNS.jsonl`` is named by path only. This tool never accepts anything.
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
import attempt04_outputs as a4o  # noqa: E402
import attempt05_outputs as a5o  # noqa: E402
import attempt06_outputs as a6o  # noqa: E402  (the preserved Attempt 6 accounting)
import attempt07_candidate as candidate  # noqa: E402
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

CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID, ATTEMPT_ID = 37, 7, "CYCLE-37", "ATTEMPT-07-20260925"
BASE_SHA = "a2ce6b0827416772341af5575715b1735ffa29fd"
BRANCH = "codex/BAT-706-cycle37-rework"
DATA = Path(r"C:\BatteredAggieSyndrome.data")
ATTEMPT6_ROOT = DATA / "ops" / "cycle37" / "attempt06"
MANAGER_A6 = DATA / "ops" / "manager_reviews" / "cycle37" / "attempt06" / "review-20260925T205004Z"
A5_POINTER = a6o.A5_POINTER
DB_SHA256 = base.DB_SHA256
HEADLINES = base.HEADLINES
WORKER_LANES = a6o.WORKER_LANES
FINDING_IDS = ("MF37A06-01", "MF37A06-02")
REQUIREMENT_LANES = {
    "R37A07-01": ("CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01"),
    "R37A07-02": ("STORAGE_ADMISSION", "FINAL_PACKET"),
    "R37A07-03": ("LOCAL_INTEGRATION_CANDIDATE",),
    "R37A07-04": ("WRITE_PROTECTION", "SOURCE_ADMISSION", "SOURCE_HARNESS", "SOURCE_REGRESSIONS", "CAREER_SUCCESSOR",
                  "INSTALLED_CONSUMER_C01", "TRUE_UNMOUNTED", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED"),
    "R37A07-05": WORKER_LANES,
}
A06_LANES = {lane: (lane,) for lane in WORKER_LANES} | {"MANAGER_REVIEW": ()}
CARRY_COMPOSITION = {**a6o.CARRY_COMPOSITION, "MANAGER_FINDING": 20, "ATTEMPT6_CRITERION": 20, "ATTEMPT6_LANE": 15,
                     "ATTEMPT6_WORKER_FINDING": 8}
LABEL_PREFIX = "Cycle #37 \u2014 Attempt #7 \u2014"
OUTPUT_NAMES = a6o.OUTPUT_NAMES + ("CONTROL07_PROPOSAL.md", "CONTROL07_PROPOSAL_VALIDATION.json")
OPERATIONAL_LEDGER = Path("STORAGE_RESERVATIONS.jsonl")
FINAL_SNAPSHOT = Path("STORAGE_EVIDENCE_SNAPSHOT.json")
FINAL_OUTPUT_LEDGER = Path("evidence") / "storage" / "STORAGE_RESERVATIONS_FINAL_OUTPUT.jsonl"
#: Written by a later step than any build: the lane index, and the final-output ledger with its head log.
NEVER_EVIDENCE = ("lanes/RUNS.jsonl", FINAL_OUTPUT_LEDGER.as_posix(),
                  FINAL_OUTPUT_LEDGER.as_posix() + storage_admission.HEAD_SUFFIX)
CANDIDATE_GRANT = a6o.CANDIDATE_GRANT
RAW = a6o.RAW
CENSUS = a6o.CENSUS
CONTROL_OUTPUTS = ("CONTROL07_PROPOSAL.md", "CONTROL07_PROPOSAL_VALIDATION.json")
CONTROL_PATCH = Path("evidence") / "control07" / "CONTROL07_PROPOSAL.patch"


def rebind() -> None:
    """Point the preserved accountings at the Attempt 7 identity. The Attempt 4, 5 and 6 helpers keep the constants
    that find their own final lane receipts (each module's ``BASE_SHA`` names the head its predecessor finished at)."""

    a6o.rebind()
    base.CYCLE_NUMBER, base.ATTEMPT_NUMBER, base.CYCLE_ID, base.ATTEMPT_ID = (CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID,
                                                                              ATTEMPT_ID)
    base.BASE_SHA = BASE_SHA
    base.BRANCH = BRANCH
    base.WORKER_LANES = WORKER_LANES
    for module in (a4o, a5o, a6o):
        module.LABEL_PREFIX = LABEL_PREFIX
        module.CYCLE_NUMBER, module.ATTEMPT_NUMBER = CYCLE_NUMBER, ATTEMPT_NUMBER
    for module in (a5o, a6o):
        module.CYCLE_ID, module.ATTEMPT_ID = CYCLE_ID, ATTEMPT_ID


def carry_category(key: str) -> str:
    for prefix, name in (("A06-AC-", "ATTEMPT6_CRITERION"), ("A06-LANE-", "ATTEMPT6_LANE"),
                         ("A06-WORKER-", "ATTEMPT6_WORKER_FINDING")):
        if key.startswith(prefix):
            return name
    return a6o.carry_category(key)


class Context(a6o.Context):
    def __init__(self, contract_path: Path, out_root: Path) -> None:
        super().__init__(contract_path, out_root)
        self.findings_path = out_root / "evidence" / "NEW_FINDINGS_ATTEMPT7.json"
        self.ledger_path = out_root / OPERATIONAL_LEDGER
        self.attempt6_lanes: list[dict[str, Any]] = []

    def storage(self) -> dict[str, Any]:
        """The attempt's ledger chain proved back to its root; the root verified against its snapshot once frozen."""

        root = self.out_root
        operational, frozen, final = root / OPERATIONAL_LEDGER, root / FINAL_SNAPSHOT, root / FINAL_OUTPUT_LEDGER
        live = final if final.is_file() else operational
        try:
            proof = snapshot.chain(live)
        except snapshot.SnapshotRefused as refusal:
            proof = {"result": "REFUSED", "code": refusal.code, "detail": str(refusal)}
        row: dict[str, Any] = {"ledger": str(operational), "snapshot": str(frozen), "frozen": frozen.is_file()}
        if frozen.is_file():
            try:
                row["verification"] = snapshot.verify(operational, frozen)
                document = snapshot.load_snapshot(frozen)
                row.update(content_sha256=document["content_sha256"], measured=document["measured"],
                           bounded_stop=document.get("bounded_stop"),
                           budget_bytes=document["configuration"]["budget_bytes"],
                           reserve_bytes=document["configuration"].get("reserve_bytes"),
                           records=document["ledger"]["records"], identity=document.get("identity"))
            except (snapshot.SnapshotRefused, KeyError) as error:
                row["verification"] = {"result": "REFUSED", "code": getattr(error, "code", "KEY"), "detail": str(error)}
        elif operational.is_file():
            status = storage_admission.Ledger(operational).status()
            row["live_status"] = {k: status.get(k) for k in ("records", "identity", "budget_bytes", "added_bytes",
                                                             "headroom_bytes", "open_reservations", "bounded_stop")}
        claim = Path(str(operational) + storage_admission.CLAIM_SUFFIX)
        final_status = storage_admission.Ledger(final).status() if final.is_file() else {}
        return {"chain": proof, "operational": row,
                "continuation_claim": {"path": str(claim), "exists": claim.is_file(),
                                       "sha256": sha256_file(claim) if claim.is_file() else None},
                "final_output_ledger": {
                    "path": str(final), "exists": final.is_file(), "evidence": False,
                    "status": {k: final_status.get(k) for k in ("records", "identity", "segment", "budget_bytes",
                                                                "added_bytes", "headroom_bytes", "open_reservations",
                                                                "bounded_stop")},
                    "rule": ("The root's one claimed continuation: it inherits the root budget and baselines and "
                             "accounts for the final packet's own outputs after the seal, so it is named by path and "
                             "never hashed as evidence.")},
                "frozen_and_verified": (row["frozen"] and (row.get("verification") or {}).get("result") == "PASS"
                                        and proof.get("result") == "PASS")}


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
    for identity, path, kind, scope in (
            ("E-INTAKE", root / "evidence" / "intake" / "INTAKE_START.json", CENSUS,
             "The untouched starting state: contract and issuance digests, every source reference re-hashed"),
            ("E-REQUEST-LEDGER", root / "evidence" / "platform" / "REQUEST_LEDGER.jsonl", CENSUS,
             "Every counted platform request, retries included, appended before its result was used"),
            ("E-FAILURE-CLASSIFICATION", root / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json", CENSUS,
             "Worker classification of every failing identity of a red lane, by cause, kind, owner and next action"),
            ("E-NEW-FINDINGS", ctx.findings_path, CENSUS,
             "Findings discovered in Attempt 7, with severity, disposition, owner and next action"),
            ("E-CLEANUP-INVENTORY", root / "evidence" / "CLEANUP_INVENTORY.json", CENSUS,
             "Every directory this attempt created or wrote, its bytes, and what the owner may remove (nothing removed)"),
            ("E-BEFORE-REPRODUCTION", root / "evidence" / "before" / "BEFORE_REPRODUCTION.json", RAW,
             "Before-repair reproduction of MF37A06-01 and MF37A06-02 at the issued base: the manager's saved "
             "same-page fixture through the Attempt 6 installed consumer and the saved storage replay, with digests "
             "of every probe input and output"),
            ("E-CONTROL07-PATCH", root / CONTROL_PATCH, RAW,
             "The inert CONTROL-07 proposal as a patch against main's six control surfaces (never applied)")):
        if Path(path).is_file():
            ctx.add(identity, path, kind, scope)
    proposed = root / "evidence" / "control07" / "proposed"
    for path in sorted(p for p in proposed.rglob("*") if p.is_file()):
        relative = path.relative_to(proposed).as_posix()
        ctx.add(f"E-CONTROL07-PROPOSED-{relative}", path, RAW,
                f"The inert proposed bytes of {relative}, outside every checkout (not adopted)")
    for name in CONTROL_OUTPUTS:
        if (root / name).is_file():
            ctx.add(f"E-OUTPUT-{name}", root / name, RAW, f"Declared worker output {name} (create-only, at the final "
                                                          "subjects)")
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
                ("E-STORAGE-LEDGER", ledger, "The attempt's root storage ledger (Cycle 37 / Attempt 7), frozen by its "
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


_CARRIED = ("CARRIED_BY_ATTEMPT5_LANE_AT_THE_CANDIDATE_HEAD", "CARRIED_BY_ATTEMPT6_LANE_AT_THE_CANDIDATE_HEAD")


def _relabel(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The preserved dispositions name the attempt whose lane carries a prior lane; here that is Attempt 7. The
    results were read from this attempt's receipts, so only the naming changes."""

    out = []
    for row in rows:
        row = dict(row)
        disposition = row.get("disposition")
        if disposition in _CARRIED:
            number = "5" if disposition == _CARRIED[0] else "6"
            row["disposition"] = "CARRIED_BY_ATTEMPT7_LANE_AT_THE_CANDIDATE_HEAD"
            row["attempt7_lanes"] = row.pop(f"attempt{number}_lanes")
            row["attempt7_results"] = row.pop(f"attempt{number}_results")
            if "justification" in row:
                row["justification"] = row["justification"].replace(f"Attempt {number} lane", "Attempt 7 lane")
        out.append(row)
    return out


def _a06_final(lane: str) -> dict[str, Any]:
    index = ATTEMPT6_ROOT / "lanes" / "RUNS.jsonl"
    rows = [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [row for row in rows if row["lane"] == lane and row["head"] == BASE_SHA]
    return rows[-1] if rows else {}


def attempt6_lane_dispositions(ctx: Context) -> list[dict[str, Any]]:
    rows = []
    for lane, successors in A06_LANES.items():
        final = _a06_final(lane)
        row: dict[str, Any] = {"id": f"A06-LANE-{lane}", "attempt6_lane": lane, "attempt6_run": final.get("run"),
                               "attempt6_result": final.get("result"), "attempt6_head": final.get("head"),
                               "attempt6_receipt": final.get("receipt"),
                               "attempt6_receipt_sha256": final.get("receipt_sha256"),
                               "attempt6_receipt_preserved": bool(final.get("receipt")) and Path(final["receipt"]).is_file()}
        if not successors:
            row.update(disposition="MANAGER_OWNED", justification="The Attempt 6 manager lane is the manager's.")
        else:
            row.update(disposition="CARRIED_BY_ATTEMPT7_LANE_AT_THE_CANDIDATE_HEAD", attempt7_lanes=list(successors),
                       attempt7_results={s: (ctx.receipts[s]["result"] if ctx.at_head(s) else "NOT_AT_HEAD")
                                         for s in successors if s in ctx.receipts},
                       justification=("Re-executed fresh by the same-named Attempt 7 lane at the candidate head; the "
                                      "Attempt 6 receipt stays unchanged as the before-record (its result is never "
                                      "relabelled; a red Attempt 6 result stays red there)."))
        rows.append(row)
    return rows


def lane_dispositions(ctx: Context) -> None:
    ctx.original_lanes = _relabel(a5o.original_lane_dispositions(ctx))
    ctx.attempt3_lanes = _relabel(a5o.attempt3_lane_dispositions(ctx))
    ctx.attempt4_lanes = _relabel(a5o.attempt4_lane_dispositions(ctx))
    ctx.attempt5_lanes = _relabel(a6o.attempt5_lane_dispositions(ctx))
    ctx.attempt6_lanes = attempt6_lane_dispositions(ctx)


# ------------------------------------------------------------------ inherited red lanes


def classify(ctx: Context) -> dict[str, Any]:
    """Derive the Attempt 7 classification from Attempt 6's, identity by identity and cause by cause."""

    previous_path = ATTEMPT6_ROOT / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json"
    previous = read_json(previous_path)
    lanes: dict[str, Any] = {}
    problems: list[str] = []
    for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED"):
        receipt = ctx.receipts.get(lane)
        if not receipt or receipt["result"] != "FAIL" or not ctx.at_head(lane):
            continue
        failing = base.failing_identities(receipt) or []
        comparison = (receipt.get("details") or {}).get("attempt6_comparison") or {}
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
                       "attempt6_run": (previous["lanes"].get(lane) or {}).get("run"), "groups": list(groups.values()),
                       "equivalence": {"persisting": len(comparison.get("persisting") or []),
                                       "persisting_same_cause": len(comparison.get("persisting_same_cause") or []),
                                       "new_in_attempt7": comparison.get("new_in_attempt7"),
                                       "no_longer_failing": comparison.get("no_longer_failing") or
                                       comparison.get("no_longer_reported")}}
    if problems:
        raise SystemExit("classification refused:\n" + "\n".join(problems))
    document = {"label": f"{LABEL_PREFIX} IN_PROGRESS_LOCAL_WORK_REMAINS (inherited failure classification)",
                "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
                "attempt_id": ATTEMPT_ID, "authored_at": utc_now(),
                "rule": ("Each failing identity keeps its Attempt 6 group only when it persists with the same traceback "
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
        final = _a06_final(lane)
        rows.append({"lane": lane, "attempt7_run": (ctx.runs.get(lane) or {}).get("run"),
                     "attempt7_result": receipt.get("result"), "at_candidate_head": ctx.at_head(lane),
                     "counts": receipt.get("counts"),
                     "execution": "FRESH_AT_THE_CANDIDATE_HEAD" if ctx.at_head(lane) else "NOT_AT_HEAD",
                     "attempt6_run": final.get("run"), "attempt6_result": final.get("result"),
                     "attempt6_receipt": final.get("receipt"), "attempt6_receipt_sha256": final.get("receipt_sha256"),
                     "attempt6_comparison": details.get("attempt6_comparison"),
                     "failing_identities": base.failing_identities(receipt) if receipt.get("result") == "FAIL" else None})
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "candidate": ctx.candidate, "lanes": rows, "equivalence_used": [],
            "equivalence_statement": ("TP37-A07 permits a CHECK lane to carry an old execution by an explicit current "
                                      "dependency comparison. This attempt used none: every one of the 14 worker lanes "
                                      "executed fresh at the candidate head, because consumer dependencies changed "
                                      "(career_successor.py, the storage tools). Each Attempt 6 final receipt is "
                                      "retained unchanged as the before-record and compared by identity; no old "
                                      "execution is relabelled, and the Attempt 6 red lanes stay red there."),
            "classification": ctx.classification, "original_lanes": ctx.original_lanes,
            "attempt3_lanes": ctx.attempt3_lanes, "attempt4_lanes": ctx.attempt4_lanes,
            "attempt5_lanes": ctx.attempt5_lanes, "attempt6_lanes": ctx.attempt6_lanes,
            "rule": ("Inherited red lanes stay red until genuinely resolved. Equivalence is by exact identity and cause "
                     "against the Attempt 6 final receipts at the issued base; counts alone establish nothing.")}


# ------------------------------------------------------------------ criteria


def _d(ctx: Context, lane: str) -> dict[str, Any]:
    return ctx.details(lane)


def _holds(ctx: Context, lane: str, key: str) -> bool:
    return bool((_d(ctx, lane).get(key) or {}).get("holds"))


def _before(ctx: Context, finding: str) -> bool:
    path = ctx.out_root / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
    return bool(path.is_file() and (read_json(path).get(finding) or {}).get("reproduced"))


def _control(ctx: Context) -> dict[str, Any]:
    path = ctx.out_root / "CONTROL07_PROPOSAL_VALIDATION.json"
    return read_json(path) if path.is_file() else {}


def judge(ctx: Context, key: str, requirement: str) -> tuple[str, str]:
    needed = REQUIREMENT_LANES[requirement]
    installed, career = _d(ctx, "INSTALLED_CONSUMER_C01"), _d(ctx, "CAREER_SUCCESSOR")
    if requirement == "R37A07-01":
        failing = [lane for lane in needed if not ctx.lane_ok(lane)]
        failing += [f"{lane}:{k}" for lane, k in (("INSTALLED_CONSUMER_C01", "a7_forgeries"),
                                                  ("INSTALLED_CONSUMER_C01", "manager_a6_same_page_lineage"),
                                                  ("INSTALLED_CONSUMER_C01", "a6_forgeries"),
                                                  ("INSTALLED_CONSUMER_C01", "installed_identity_census"),
                                                  ("INSTALLED_CONSUMER_C01", "manager_a5_successor_adversarial"),
                                                  ("INSTALLED_CONSUMER_C01", "manager_a5_successor_population_audit"),
                                                  ("CAREER_SUCCESSOR", "independent_anchor_oracle"),
                                                  ("CAREER_SUCCESSOR", "independent_identity_census"))
                    if not _holds(ctx, lane, k)]
        failing += [f"source binding {k}" for k, v in (career.get("source_identity_checks") or {"none": False}).items()
                    if not v]
        failing += [f"source anchor {k}" for k, v in ((career.get("source_anchor_checks") or {}).get("checks")
                                                      or {"none": False}).items() if not v]
        failing += [f"original negative {name}" for name in a6o._lineage_originals(ctx)]
        if not (installed.get("successor_pagination") or {}).get("reconciled"):
            failing.append("complete pagination")
        if key.endswith("-C") and not _before(ctx, "MF37A06-01"):
            failing.append("before-repair reproduction")
        if failing:
            return "IN_PROGRESS", "not yet held at the candidate head: " + ", ".join(failing)
        oracle = career["independent_anchor_oracle"]
        forgeries = installed["a7_forgeries"]["cases"]
        refused = [n for n in forgeries if not n.endswith(("_genuine", "_genuine_interval_person"))]
        edges = {r["relation"]: r["edges"] for r in oracle["relations"]}
        return "VERIFIED_LOCAL", (
            "Every lineage edge is bound to the source field and interval it was read from, in both relations: the "
            f"repaired verifier anchors {edges.get('A5<-default')} default, {edges.get('A5<-A4')} Attempt 4 and "
            f"{edges.get('A4<-default')} Attempt 4-to-default edges and agrees on every row's predecessors across "
            "versions; an independent oracle (sqlite3/json/re only) grounds every span in its own raw capture and "
            f"finds {oracle['crossed_edges']} crossed edges, {oracle['restructure_violations']} false restructure claims "
            f"and {oracle['triangle_mismatches']} cross-version mismatches, and finds exactly the manager's saved "
            f"same-page swap. Through the fresh installed console script and its module entrypoint, {len(refused)} "
            "forgeries (the same-page cross-episode swap in both formats, year-only and team-only anchor "
            "substitutions, same role in a different period, a cross-version anchor, an Attempt 4 file whose own "
            "lineage crosses, a false restructure claim) are each refused for their own cause after a fixture reset; "
            "the manager's Attempt 6 challenge is refused as an episode anchor; every Attempt 6 and original negative "
            "stays refused; the genuine 72,958-row successor serves unchanged with complete pagination."
            + (" Before repair, the saved fixture was served seven rows by the Attempt 6 installed consumer at the "
               "issued base." if key.endswith("-C") else ""))
    if requirement == "R37A07-02":
        storage = ctx.storage()
        admission = _d(ctx, "STORAGE_ADMISSION")
        live = ((admission.get("storage_ledger") or {}).get("live_over_budget_control") or {}).get("refused")
        failing = [lane for lane in needed if not ctx.lane_ok(lane)]
        if not live:
            failing.append("live over-budget refusal")
        failing += [k for k in ("manager_a6_storage_continuation", "manager_a5_storage_independent")
                    if not _holds(ctx, "STORAGE_ADMISSION", k)]
        if not storage["frozen_and_verified"]:
            failing.append("root ledger frozen, verified and its chain proved")
        validation = sorted((ctx.out_root / "evidence" / "final").glob("FINAL_PACKET_VALIDATION_*.json"))
        if not validation or read_json(validation[-1]).get("result") != "PASS":
            failing.append("FINAL_PACKET validation receipt PASS")
        if key.endswith("-C") and not _before(ctx, "MF37A06-02"):
            failing.append("before-repair reproduction")
        if failing:
            return "IN_PROGRESS", "not yet held: " + ", ".join(failing)
        measured = storage["operational"].get("measured") or {}
        return "VERIFIED_LOCAL", (
            "The attempt keeps one storage ledger chain with one baseline: the root ledger (identity Cycle 37 / "
            f"Attempt 7) carried every material reservation and was frozen with {measured.get('added_bytes')} bytes "
            f"added of its {storage['operational'].get('budget_bytes')}-byte budget; its one continuation (the "
            "final-output ledger) was claimed once under the root's lock and inherits the root's budget and "
            "baselines, so a replay of the frozen snapshot is refused where it opens "
            "(REFUSED_CONTINUATION_ALREADY_CLAIMED), a same-path restart resumes, and growth between freeze and "
            "continuation is recorded against the same budget. The continuation suite refuses the four-process race, "
            "wrong attempt or root, truncation, tamper, an open reservation and a stale or forked parent on tiny "
            "fixtures; the manager's Attempt 6 challenge replayed byte-faithfully fails at its replay and, "
            "instrumented, records the refusal; the chain proves back to the root; FINAL_PACKET passes with every "
            "reservation reconciled." + (" Before repair, the saved replay admitted duplicate headroom at the issued "
                                         "base." if key.endswith("-C") else ""))
    if requirement == "R37A07-03":
        details = _d(ctx, "LOCAL_INTEGRATION_CANDIDATE")
        failing = [lane for lane in needed if not ctx.lane_ok(lane)]
        checks = details.get("candidate_tree_checks") or {}
        failing += [k for k, v in checks.items() if not v] or ([] if checks else ["tree checks"])
        failing += [k for k, v in (details.get("candidate_attempt7") or {"attempt 7 chain": False}).items() if not v]
        failing += [k for k in ("candidate_negatives", "manager_a6_committed_tree", "manager_a5_integration_replay",
                                "candidate_consumer", "control07_requalification")
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
            failing.append("the create-only CONTROL-07 validation is not bound to an Attempt 7 append and its repair head")
        # The create-only receipt names the append it was produced at; the lane re-qualifies the same proposal at the
        # final candidate, so a later forward append never leaves the proposal unqualified at the delivered head.
        if (requalified.get("subjects") or {}).get("candidate") != final_candidate:
            failing.append("CONTROL-07 re-qualified in the lane at the final candidate")
        errors = ((details.get("candidate_review_control_characterization") or {}).get("compatibility_errors"))
        if key.endswith("-C") and not errors:
            failing.append("the two control compatibility errors kept visible")
        if failing:
            return "IN_PROGRESS", "not yet held: " + ", ".join(failing)
        proof = details.get("committed_tree_proof") or {}
        green = (control.get("characterization") or {}).get("current_checkers_green_on") or {}
        cases = len(((control.get("checker_runs") or {}).get("proposed") or {}).get("cases") or {})
        text = {"A": ("A private, inert CONTROL-07 proposal (a checker that requires a PASS report carried by an "
                      "eligible independent reviewer's APPROVED review of the exact head, and a workflow with no paid "
                      "provider, secret or dispatch path that takes the checker from the protected base) is bound "
                      "byte-for-byte against main, the repair branch and the candidate and qualified offline: "
                      f"{sum(1 for v in (control.get('checks') or {}).values() if v)} of {len(control.get('checks') or {})} "
                      f"checks hold over {cases} fixture cases; FAIL, BLOCKED and SKIPPED reports, self-approval, a "
                      "stale head, a dismissed or unapproved review, a changed control surface and a PASS under the "
                      "unapproved protocol all fail closed, where the current checkers exit green on "
                      + ", ".join(f"{name} {len(rows)}" for name, rows in green.items())
                      + f" of the {cases} cases. The create-only receipt was produced at repair "
                      f"{str(subjects.get('repair'))[:8]} and candidate {str(subjects.get('candidate'))[:8]}; the "
                      f"candidate lane re-qualified the same proposal offline at the final candidate "
                      f"{str(final_candidate)[:8]}. It was not adopted, applied or published."),
                "B": ("The candidate advanced forward only from bb5253b2: "
                      f"{len(ctx.candidate_record_paths)} [material] commit(s), each continuing the one before, the "
                      "preserved first candidate and bb5253b2 still ancestors, only the candidate ref moved; its "
                      f"committed provenance agrees with its committed blobs ({proof.get('committed_paths')} paths, "
                      f"{proof.get('manifest_rows')} manifest rows, 0 mismatches), the manager's Attempt 6 full-set "
                      "committed-tree review finds 0 mismatches, main's entries for the six protected control paths "
                      "are kept (the paid workflow absent), and the consumer built from the candidate tree serves and "
                      "refuses."),
                "C": ("The ordinary repairs and regenerated provenance were appended to bb5253b2 with every ancestor and "
                      "main's protected bytes retained; committed blobs and manifest reconcile independently; the two "
                      f"control compatibility errors stay visible ({len(errors or [])} failing tests characterized for "
                      "the owner). Qualifying the private proposal does not qualify the candidate for publication.")}
        return "VERIFIED_LOCAL", text[key[-1]]
    if requirement == "R37A07-04":
        failing = [lane for lane in needed if lane not in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED") and not ctx.lane_ok(lane)]
        failing += [lane for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED") if not ctx.executed(lane)]
        for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED"):
            comparison = _d(ctx, lane).get("attempt6_comparison") or {}
            if comparison.get("new_in_attempt7"):
                failing.append(f"{lane} new identities {comparison['new_in_attempt7']}")
        named = (installed.get("successor_named_cases") or {}).get("holds") or {}
        failing += [f"named {k}" for k, v in named.items() if not v] or ([] if named else ["named cases"])
        failing += [k for k in ("manager_a3_career_challenge", "manager_a4_career_semantic_census",
                                "manager_a4_successor_challenge", "manager_a5_career_semantic_census",
                                "manager_a5_successor_adversarial", "a7_forgeries", "manager_a6_same_page_lineage")
                    if not _holds(ctx, "INSTALLED_CONSUMER_C01", k)]
        if not (installed.get("successor_coverage") or {}).get("predecessor_identity_sets_equal"):
            failing.append("successor coverage")
        if failing:
            return "IN_PROGRESS", "not yet held: " + ", ".join(failing)
        text = {"A": ("All 72,958 genuine rows and 7,950 captures verify and serve unchanged; all 72,070 default and "
                      "73,082 Attempt 4 predecessor rows keep one disposition; the legitimate alias, new, split, "
                      "removed, restructured, missing-team and other-sport classes serve with their explicit meanings; "
                      "the affected entrypoint (the successor verifier) is repaired as a class, no data rebuilt and no "
                      "fact invented or activated."),
                "B": ("One fresh offline noneditable BAS wheel, composed with the released C01 wheel, paginates the whole "
                      "successor and every filter exactly as the independent SQL oracle and raw census derive them, "
                      "serves the same rows for the named people through its module entrypoint as through its console "
                      "script, and refuses every original and new within-page lineage forgery for its own cause; no "
                      "row is hidden or dropped."),
                "C": ("The guard, date, defensive-unit, unknown-role, Cory 2018/Danny/Steve, scoring/PIT, harness, "
                      "default/legacy and Cycle 29 behavior pass their suites and the manager replays at the candidate "
                      "head; the full mounted suite ran fresh and matches Attempt 6 identity for identity with no new "
                      "failure; the default database, prior releases, raw captures and frozen predictions are "
                      "unchanged; the 2,223-row staff successor and the whole history stay owned.")}[key[-1]]
        return "VERIFIED_LOCAL", text
    # R37A07-05
    if key.endswith("-A"):
        missing = [lane for lane in WORKER_LANES if not ctx.executed(lane)]
        if not missing:
            return "VERIFIED_LOCAL", ("The Attempt 7 lane and output tools were implemented and inspected; the storage "
                                      "continuation and seal qualified first on tiny fixtures and every new forgery was "
                                      "proved against the source verifier before the installed lane; every one of the "
                                      "14 worker lanes executed fresh through the issued command at the candidate head "
                                      "with exact binding and raw counts; no equivalence was relabelled and inherited "
                                      "red stays red, compared with Attempt 6 by identity and cause.")
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
        return "VERIFIED_LOCAL", ("All 819 carryforward identities keep their meanings and dispositions; 20 clauses, 15 "
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
    extra = {"R37A07-01": ["E-BEFORE-REPRODUCTION"],
             "R37A07-02": ["E-BEFORE-REPRODUCTION", *storage] + [e for e in ctx.evidence if e.startswith("E-FINAL-")],
             "R37A07-03": ["E-CANDIDATE-APPEND-RECORD", "E-OUTPUT-LOCAL_INTEGRATION_CANDIDATE.json",
                           "E-OUTPUT-CONTROL07_PROPOSAL_VALIDATION.json", "E-OUTPUT-CONTROL07_PROPOSAL.md",
                           "E-CONTROL07-PATCH"] + [e for e in ctx.evidence if e.startswith("E-CONTROL07-PROPOSED-")],
             "R37A07-04": ["E-OUTPUT-CAREER_POPULATION_DISPOSITIONS.json", "E-OUTPUT-DELIVERED_CONSUMER_MANIFEST.json",
                           "E-FAILURE-CLASSIFICATION"],
             "R37A07-05": ["E-ORIGINAL-OBLIGATIONS", "E-FAILURE-CLASSIFICATION", "E-REQUEST-LEDGER",
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
        if key.endswith("-B") and criterion["requirement"] == "R37A07-05":
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
        elif row["id"].startswith(("ORIGINAL-LANE-", "A03-LANE-", "A04-LANE-", "A05-LANE-", "A06-LANE-")):
            evidence.append("E-OUTPUT-LANE_RESULTS.json")
        rows.append({"id": row["id"], "disposition": row["disposition"], "attempt7_state": state,
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
        "MF37A06-01": ([_f(MANAGER_A6 / "FRESH_LINEAGE_CHALLENGE.json"), _f(MANAGER_A6 / "fresh_lineage_challenge.py"),
                        _f(MANAGER_A6 / "successor_adversarial.py"), _f(before)],
                       {"CAREER_SUCCESSOR": "source_anchor_checks", "INSTALLED_CONSUMER_C01": "a7_forgeries"}),
        "MF37A06-02": ([_f(MANAGER_A6 / "STORAGE_CONTINUATION_CHALLENGE.json"), _f(MANAGER_A6 / "storage_challenge.py"),
                        _f(ATTEMPT6_ROOT / "STORAGE_EVIDENCE_SNAPSHOT.json"), _f(before)],
                       {"STORAGE_ADMISSION": "manager_a6_storage_continuation", "FINAL_PACKET": "storage_verification"}),
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
    oracle = career.get("independent_anchor_oracle") or {}
    manifest.update({
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "attempt7_anchor_verification": {
            "verifier_version": (career.get("source_identity_bindings") or {}).get("verifier_version"),
            "source_anchor_checks": career.get("source_anchor_checks"),
            "independent_anchor_oracle": {k: oracle.get(k) for k in ("method", "rows", "a04_rows", "default_rows",
                                                                     "captures_read", "grounding", "crossed_edges",
                                                                     "restructure_violations", "triangle_mismatches",
                                                                     "holds")}
            | {"relations": [{k: r.get(k) for k in ("relation", "edges", "counts", "crossed_edges",
                                                    "restructured_entries", "restructure_violation_count")}
                             for r in oracle.get("relations") or []],
               "saved_manager_fixture": oracle.get("saved_manager_fixture")},
            "installed_forgeries_console_script_and_module": _summary(installed.get("a7_forgeries")),
            "manager_a6_same_page_lineage": installed.get("manager_a6_same_page_lineage")},
        "delivered_successor_note": ("Attempt 7 delivers no new successor: it serves the Attempt 5 file by its Attempt 5 "
                                     "pointer, unchanged, and repairs the consumer that verifies it."),
    })
    return manifest


def population_document(ctx: Context, label: str) -> dict[str, Any]:
    document = a6o.population_document(ctx, label)
    oracle = _d(ctx, "CAREER_SUCCESSOR").get("independent_anchor_oracle") or {}
    document.update({"cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
                     "attempt7_source_anchor_relations": [{k: r.get(k) for k in ("relation", "edges", "counts",
                                                                                 "restructured_entries")}
                                                          for r in oracle.get("relations") or []],
                     "attempt7_raw_grounding": oracle.get("grounding"),
                     "note": document.get("note", "") + (" Attempt 7 bound every lineage edge to the source field and "
                                                         "interval it was read from; nothing was rebuilt.")})
    return document


def candidate_document(ctx: Context, label: str) -> dict[str, Any]:
    details = _d(ctx, "LOCAL_INTEGRATION_CANDIDATE")
    record = read_json(ctx.candidate_record_path) if ctx.candidate_record_path else {}
    appends = [{k: read_json(path).get(k) for k in ("created_at", "previous_candidate_head", "candidate_commit",
                                                    "repair_head", "refs_changed")} | {"record": str(path)}
               for path in ctx.candidate_record_paths]
    control = _control(ctx)
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "requirement": "R37A07-03", "appends": appends,
            "attempt7_start_head": candidate.ISSUED_CANDIDATE_HEAD, "preserved_first_candidate": candidate.PRESERVED_HEAD,
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
                     "attempt7_chain": details.get("candidate_attempt7"),
                     "tree_checks": details.get("candidate_tree_checks"),
                     "committed_tree_proof": {k: v for k, v in (details.get("committed_tree_proof") or {}).items()
                                              if k != "protected_entries"},
                     "generated_view": details.get("candidate_generated_view"),
                     "negatives": details.get("candidate_negatives"), "history_policy": details.get("candidate_history_policy"),
                     "manager_a6_committed_tree": {k: v for k, v in (details.get("manager_a6_committed_tree") or {}).items()
                                                   if k != "literal_adaptations"},
                     "manager_a5_integration_replay": details.get("manager_a5_integration_replay"),
                     "consumer": details.get("candidate_consumer"),
                     "control07_requalification_in_lane": details.get("control07_requalification"),
                     "review_control_characterization": details.get("candidate_review_control_characterization")},
            "control07_proposal": {"validation": _f(ctx.out_root / "CONTROL07_PROPOSAL_VALIDATION.json"),
                                   "document": _f(ctx.out_root / "CONTROL07_PROPOSAL.md"),
                                   "patch": _f(ctx.out_root / CONTROL_PATCH), "result": control.get("result"),
                                   "subjects": control.get("subjects"), "part_of_the_candidate": False},
            "decision_for_the_owner": ("The candidate keeps main's protected scientific-review controls (the paid "
                                       "workflow stays absent); the repair branch's own changes to them are withheld "
                                       "because changing trusted controls on main is an owner decision this contract "
                                       "does not grant, so the two control compatibility errors remain and the "
                                       "candidate is not publication-ready. The private CONTROL-07 proposal is the "
                                       "concrete no-paid, fail-closed alternative for that decision; it is not part of "
                                       "the candidate and adopting it needs the eligible independent reviewer's receipt "
                                       "and separate publication authority."),
            "not_done": ("No push, remote PR, merge, retarget, closure, deletion, reset, history rewrite or activation; "
                         "the preserved first candidate and bb5253b2 stay reachable and every other ref kept its commit.")}


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
            "sealing_order": ["every material lane on the root ledger", "every reservation reconciled",
                              "root ledger frozen into STORAGE_EVIDENCE_SNAPSHOT.json",
                              "its one continuation (the final-output ledger) claimed, inheriting the root budget",
                              "IN_PROGRESS outputs built and sealed under a final-ledger reservation",
                              "FINAL_PACKET lane (snapshot, chain proof, packet check, v2.4.0 accounting, create-only "
                              "receipt)", "terminal build, generated checklist, seal", "post-seal accounting receipt",
                              "final reservation reconciled (the final-output ledger is never evidence)"],
            "meaning": "Passing FINAL_PACKET is accounting only; it grants no acceptance."}


def platform_reconciliation(ctx: Context, label: str) -> dict[str, Any]:
    document = a5o.platform_reconciliation(ctx, label)
    document["cycle_number"], document["attempt_number"] = CYCLE_NUMBER, ATTEMPT_NUMBER
    subjects = phase_subjects(ctx)
    bound = {phase: sorted({f"{row['head'][:8]} (clean {row['clean']})" for row in rows})
             for phase, rows in subjects.items() if rows}
    document["phase_subjects"] = subjects
    document["label_note"] = ("Every Attempt 7 platform receipt carries the numeric label and binds the exact head it "
                              "read at: " + "; ".join(f"{phase} at {', '.join(heads)}" for phase, heads in bound.items())
                              + ".")
    return document


_BOUND_RECEIPTS = ("GITHUB_READ_SUMMARY", "ALL22_READ_SUMMARY", "JIRA_READ_SUMMARY", "JIRA_PRIVATE_SUCCESSOR",
                   "JIRA_COMMENT")


def phase_subjects(ctx: Context) -> dict[str, list[dict[str, Any]]]:
    """The head and tree state each platform receipt bound, phase by phase, as the receipts record them."""

    root = ctx.out_root / "evidence" / "platform"
    out: dict[str, list[dict[str, Any]]] = {}
    for phase in ("BEFORE", "DURING", "AFTER"):
        rows = []
        for path in sorted((root / phase).rglob("*.json")):
            if not path.name.startswith(_BOUND_RECEIPTS):
                continue
            subject = (read_json(path) or {}).get("subject")
            if isinstance(subject, dict) and subject.get("head"):
                rows.append({"receipt": path.name, "head": subject["head"], "clean": subject.get("clean")})
        out[phase] = rows
    return out


def cost_ledger(ctx: Context, label: str) -> dict[str, Any]:
    document = base.cost_ledger(ctx, label)
    document["cycle_number"], document["attempt_number"] = CYCLE_NUMBER, ATTEMPT_NUMBER
    document["grants_used"] = effects(ctx)
    storage = ctx.storage()
    operational = storage["operational"]
    document["storage"].update({
        "chain": storage["chain"], "operational": operational, "continuation_claim": storage["continuation_claim"],
        "final_output_ledger": storage["final_output_ledger"],
        "attempt_budget_bytes": operational.get("budget_bytes"),
        "added_bytes_at_freeze": (operational.get("measured") or {}).get("added_bytes"),
        "rule": ("One budget and one baseline per attempt: the root ledger's. A continuation inherits them and cannot "
                 "open twice, so no replay restores headroom. Reservations measure retained bytes at reconciliation; "
                 "transient peaks (a SQLite rollback journal) count only where a bounded run polls, and the 8 GiB free "
                 "reserve bounds them."),
        "bounded_stops": [operational.get("bounded_stop")] if operational.get("bounded_stop") else []})
    return document


def effects(ctx: Context) -> list[dict[str, Any]]:
    return a6o.effects(ctx)


def integration_packet(ctx: Context, label: str, lanes: list[dict[str, Any]]) -> str:
    text = base.integration_packet(ctx, label, lanes)
    description = candidate.describe()
    record = read_json(ctx.candidate_record_path) if ctx.candidate_record_path else {}
    proof = _d(ctx, "LOCAL_INTEGRATION_CANDIDATE").get("committed_tree_proof") or {}
    control = _control(ctx)
    github = ctx.latest_github or {}
    extra = ["### The local integration candidate, advanced forward (nothing published)", "",
             f"Branch `{description.get('candidate_branch')}` in `{description.get('candidate_worktree')}`: from the "
             f"granted head `{candidate.ISSUED_CANDIDATE_HEAD}` (the preserved first candidate "
             f"`{candidate.PRESERVED_HEAD}` below it) {len(ctx.candidate_record_paths)} appended `[material]` commit(s) "
             f"end at `{description.get('candidate_head')}` (tree `{description.get('candidate_tree')}`), the last built "
             f"from repair head `{record.get('repair_head')}`. Main `{description.get('main')}` and the repair branch "
             f"keep their commits; only the candidate ref moved ({record.get('refs_changed')}).", "",
             f"Committed provenance, proved against the committed blobs: {proof.get('committed_paths')} paths, "
             f"{proof.get('manifest_rows')} manifest rows, {proof.get('current_tree_rows')} CURRENT_TREE rows, "
             f"consistent {proof.get('consistent')}; protected entries equal main {proof.get('protected_entries_equal_main')}.",
             "", "| Path | Main | Repair branch | Candidate |", "| --- | --- | --- | --- |"]
    for row in description.get("protected_paths") or []:
        extra.append(f"| `{row['path']}` | {(row.get('main') or ['', 'absent'])[1][:12]} | "
                     f"{(row.get('repair') or ['', 'absent'])[1][:12]} | {(row.get('candidate') or ['', 'absent'])[1][:12]} |")
    extra += ["", "### CONTROL-07: the private no-paid, fail-closed proposal (inert; not adopted)", "",
              f"Validation `{ctx.out_root / 'CONTROL07_PROPOSAL_VALIDATION.json'}`: result {control.get('result')}, "
              f"subjects {json.dumps(control.get('subjects'))}; the proposal's bytes live only under "
              f"`{ctx.out_root / 'evidence' / 'control07' / 'proposed'}` and as the patch `{ctx.out_root / CONTROL_PATCH}`. "
              "Adoption needs the eligible independent reviewer's bootstrap receipt under the trusted control-change "
              "protocol and separate publication authority; neither is granted, and the only green proposed case is a "
              "synthetic TEST_ONLY approval, which is not a review receipt. See CONTROL07_PROPOSAL.md.", "",
              "Owner decisions this candidate needs (none taken): whether to adopt a no-paid review control such as "
              "CONTROL-07 on main -- until a trusted control reaches main the two control compatibility errors remain "
              "and the candidate is not publication-ready; publication of the candidate branch; merge through a "
              f"reviewed PR with the {github.get('unresolved_thread_total')} unresolved review threads of the "
              f"{github.get('open_pr_count')} open PRs dispositioned. Rollback of any future merge: revert the candidate "
              "commits.", ""]
    return text + "\n".join(extra) + "\n"


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
                item["attempt7_state"] = states[row["id"]]["attempt7_state"]
                item["attempt7_evidence_ids"] = [e for e in states[row["id"]]["evidence_ids"] if e != "E-ORIGINAL-OBLIGATIONS"]
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
            "note": ("Original meanings, sources, owners, reasons, next actions, prior mappings and dispositions are "
                     "copied from the issued contract unchanged. OWNED_BACKLOG items stay owned; none is marked "
                     "fulfilled by this accounting.")}))
        ctx.add("E-ORIGINAL-OBLIGATIONS", obligations_path, CENSUS,
                "All 819 carryforward identities with their original meanings and unchanged dispositions")

    write_obligations({})
    write_output(root / "LANE_RESULTS.json", dumps({
        "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "candidate": ctx.candidate,
        "runner": "tools/cycle37/attempt07_lanes.py", "runs_index": str(root / "lanes" / "RUNS.jsonl"),
        "runs_index_rule": "append-only lane index, named by path; never sealed as evidence (every lane run appends)",
        "lanes": lanes, "original_lanes": ctx.original_lanes, "attempt3_lanes": ctx.attempt3_lanes,
        "attempt4_lanes": ctx.attempt4_lanes, "attempt5_lanes": ctx.attempt5_lanes,
        "attempt6_lanes": ctx.attempt6_lanes}))
    ctx.add("E-OUTPUT-LANE_RESULTS.json", root / "LANE_RESULTS.json", CENSUS,
            "Every required lane's result at the candidate head; the 22 original and the Attempt 3, 4, 5 and 6 lanes")
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
    oracle = career.get("independent_anchor_oracle") or {}
    if ctx.lane_ok("INSTALLED_CONSUMER_C01") and ctx.lane_ok("CAREER_SUCCESSOR"):
        forgeries = (installed.get("a7_forgeries") or {}).get("cases") or {}
        refused = sum(1 for k, v in forgeries.items() if not k.endswith(("_genuine", "_genuine_interval_person"))
                      and v.get("holds"))
        edges = sum(r.get("edges") or 0 for r in oracle.get("relations") or [])
        data_evidence = (f"DELIVERED_RELEASE_{DB_SHA256[:12]}_UNCHANGED; A5_SUCCESSOR_"
                         f"{str(ctx.pointer.get('successor_sha256'))[:12]}_ROWS_{census.get('rows')}_SERVED_UNCHANGED; "
                         f"RAW_CAPTURES_{census.get('raw_files')}_IDENTITY_MISMATCHES_0; LINEAGE_EDGES_{edges}_"
                         f"SOURCE_ANCHORED_CROSSED_{oracle.get('crossed_edges')}; A7_FORGERIES_REFUSED_{refused}; "
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
    import attempt07_report  # the narrative report, beside this tool  # noqa: PLC0415

    write_output(root / "WORKER_REPORT.md", attempt07_report.render(ctx, submission))
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
                            ("attempt6_lanes", "A06-LANE-")):
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
            problems.append("FINDING_CLOSURE_MATRIX does not cover exactly MF37A06-01 and MF37A06-02")
        for row in rows:
            if not row["commits"]:
                problems.append(f"{row['finding']} names no commit")
    control = _control(ctx)
    if control and (control.get("cycle_number"), control.get("attempt_number")) != (CYCLE_NUMBER, ATTEMPT_NUMBER):
        problems.append("CONTROL07_PROPOSAL_VALIDATION.json does not carry Cycle 37 / Attempt 7")
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
