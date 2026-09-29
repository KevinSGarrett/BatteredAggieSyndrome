r"""Cycle #37 — Attempt #11 — worker outputs, submission and accounting check (R37A11-05).

    attempt11_outputs.py classify  --contract C --out-root R
    attempt11_outputs.py inventory --contract C --out-root R
    attempt11_outputs.py build     --contract C --out-root R [--headline H --writer-released]
    attempt11_outputs.py check     --contract C --out-root R [--final-packet]
    attempt11_outputs.py seal      --contract C --out-root R
    attempt11_outputs.py audit     --ledger L

The Attempt 10 accounting (``attempt10_outputs``, over the Attempt 9 to 3 bases) rebound to the Attempt 11 contract:
18 declared outputs (the CONTROL-07 proposal pair among them), 991 carryforward identities (the 949 of Attempt 10 plus
its 20 clauses, 15 lanes, 6 worker findings and the one manager finding MF37A10-01), 20 clauses and 15 lanes.
``build`` writes the outputs from what is there -- the issued contract, the lane receipts, the platform receipts and
request ledger, the storage ledger chain and its snapshot, the candidate append records, the CONTROL-07 validation
receipt, git, the intake, Git housekeeping preflight, output preflight and repair-commit receipts, and worker-authored
evidence it reads but never invents (``evidence/INHERITED_FAILURE_CLASSIFICATION.json``,
``evidence/NEW_FINDINGS_ATTEMPT11.json``, ``evidence/CLEANUP_INVENTORY.json``,
``evidence/before/BEFORE_REPRODUCTION.json``).

What changes from Attempt 10 (R37A11-05-C): a criterion's process predicates are computed from the evidence itself --
the storage ledgers' windows (every byte measured between two windows must be the ledger's own records; windows are
serialized; no reservation is exceeded; every lane receipt is written inside a window of its own), the Git commands'
recorded prefixes, the request ledger against its ceilings and the granted comments' readback -- and a violated
predicate makes its criteria FAIL whatever any finding's disposition says. A finding's disposition never turns a
criterion green or red: a FIXED_LOCAL finding whose criteria are unmet is listed as unfinished, an OPEN_OUT_OF_SCOPE
one goes to the owner. The guard log is a diagnostic record whose torn lines are kept as fragments; nothing here claims
an exhaustive zero-write count from it. This tool never accepts anything.
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

import attempt10_outputs as a10o  # noqa: E402  (the preserved Attempt 10 accounting)
import attempt11_candidate as candidate  # noqa: E402

a9o, a8o, a7o, a6o, a5o, a4o, base = a10o.a9o, a10o.a8o, a10o.a7o, a10o.a6o, a10o.a5o, a10o.a4o, a10o.base
storage_admission = a10o.storage_admission
dumps, git_out, read_json, sha256_file, utc_now, write_output = (a10o.dumps, a10o.git_out, a10o.read_json,
                                                                 a10o.sha256_file, a10o.utc_now, a10o.write_output)

CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID, ATTEMPT_ID = 37, 11, "CYCLE-37", "ATTEMPT-11-20260928"
BASE_SHA = "c2f82759f85b8a6c919fd43234bacbea29b7ae28"
BRANCH = "codex/BAT-706-cycle37-rework"
DATA = Path(r"C:\BatteredAggieSyndrome.data")
ATTEMPT10_ROOT = DATA / "ops" / "cycle37" / "attempt10"
MANAGER_A10 = DATA / "ops" / "manager_reviews" / "cycle37" / "attempt10" / "review-20260928T174921Z"
MANAGER_A10_FALSE_RESTRUCTURE = Path(r"C:\BatteredAggieSyndrome.validation\mr37a10-174921") / \
    "false-restructure-adversarial.sqlite"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a11")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37a11")
WORKER_LANES = a10o.WORKER_LANES
FINDING_IDS = ("MF37A10-01",)
REQUIREMENT_LANES = {
    "R37A11-01": ("SOURCE_REGRESSIONS", "CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01"),
    "R37A11-02": ("STORAGE_ADMISSION", "FINAL_PACKET"),
    "R37A11-03": ("LOCAL_INTEGRATION_CANDIDATE",),
    "R37A11-04": ("WRITE_PROTECTION", "SOURCE_ADMISSION", "SOURCE_HARNESS", "SOURCE_REGRESSIONS", "CAREER_SUCCESSOR",
                  "INSTALLED_CONSUMER_C01", "TRUE_UNMOUNTED", "FULL_FINAL_MOUNTED", "STRICT_MOUNTED"),
    "R37A11-05": WORKER_LANES,
}
A10_LANES = {lane: (lane,) for lane in WORKER_LANES} | {"MANAGER_REVIEW": ()}
CARRY_COMPOSITION = {**a10o.CARRY_COMPOSITION, "MANAGER_FINDING": 26, "ATTEMPT10_CRITERION": 20, "ATTEMPT10_LANE": 15,
                     "ATTEMPT10_WORKER_FINDING": 6}
LABEL_PREFIX = "Cycle #37 \u2014 Attempt #11 \u2014"
OUTPUT_NAMES = a10o.OUTPUT_NAMES
OPERATIONAL_LEDGER = a10o.OPERATIONAL_LEDGER
FINAL_SNAPSHOT = a10o.FINAL_SNAPSHOT
FINAL_OUTPUT_LEDGER = a10o.FINAL_OUTPUT_LEDGER
NEVER_EVIDENCE = a10o.NEVER_EVIDENCE
RAW = a10o.RAW
CENSUS = a10o.CENSUS
CONTROL_OUTPUTS = a10o.CONTROL_OUTPUTS
CONTROL_PATCH = a10o.CONTROL_PATCH
PREFLIGHT = Path("evidence") / "preflight" / "OUTPUTS_PREFLIGHT.json"
REFUSED_CARDINALITY = "REFUSED_CAREER_SUCCESSOR_INTERVAL_CARDINALITY_MISMATCH"
GIT_SETTINGS = ("gc.auto=0", "maintenance.auto=false")

_A10_CARRY_CATEGORY = a10o.carry_category  # captured before rebind() points a7o's name at carry_category below


def carry_category(key: str) -> str:
    for prefix, name in (("A10-AC-", "ATTEMPT10_CRITERION"), ("A10-LANE-", "ATTEMPT10_LANE"),
                         ("A10-WORKER-", "ATTEMPT10_WORKER_FINDING")):
        if key.startswith(prefix):
            return name
    return _A10_CARRY_CATEGORY(key)


def rebind() -> None:
    """Point the preserved accountings at the Attempt 11 identity. The Attempt 4 to 10 helpers keep the constants that
    find their own final lane receipts (each module's ``BASE_SHA`` names the head its predecessor finished at)."""

    a10o.rebind()
    base.CYCLE_NUMBER, base.ATTEMPT_NUMBER, base.CYCLE_ID, base.ATTEMPT_ID = (CYCLE_NUMBER, ATTEMPT_NUMBER, CYCLE_ID,
                                                                              ATTEMPT_ID)
    base.BASE_SHA = BASE_SHA
    base.BRANCH = BRANCH
    base.WORKER_LANES = WORKER_LANES
    for module in (a4o, a5o, a6o, a7o, a8o, a9o, a10o):
        module.LABEL_PREFIX = LABEL_PREFIX
        module.CYCLE_NUMBER, module.ATTEMPT_NUMBER = CYCLE_NUMBER, ATTEMPT_NUMBER
    for module in (a5o, a6o, a7o, a8o, a9o, a10o):
        module.CYCLE_ID, module.ATTEMPT_ID = CYCLE_ID, ATTEMPT_ID
    for module in (a6o, a7o, a8o, a9o, a10o):
        module.candidate = candidate
    a7o.CARRY_COMPOSITION = CARRY_COMPOSITION
    a7o.carry_category = carry_category


class Context(a10o.Context):
    def __init__(self, contract_path: Path, out_root: Path) -> None:
        super().__init__(contract_path, out_root)
        self.findings_path = out_root / "evidence" / "NEW_FINDINGS_ATTEMPT11.json"
        self.attempt10_lanes: list[dict[str, Any]] = []
        self._predicates: dict[str, Any] | None = None
        self.criterion_meta: dict[str, dict[str, list[str]]] = {}


# ------------------------------------------------------------------ process predicates (R37A11-05-C)


def window_audit(ledger: Path) -> dict[str, Any]:
    """Every measured window of one storage ledger, read from its own records: what was added between one record's
    measurement and the next reservation's, against the bytes the ledger itself appended in between (its record lines
    and their head-log lines); overlapping reservations; exceeded reservations; reservations never reconciled."""

    ledger = Path(ledger)
    if not ledger.is_file():
        return {"ledger": str(ledger), "exists": False, "holds": False}
    head_path = Path(str(ledger) + storage_admission.HEAD_SUFFIX)
    head_bytes: dict[int, int] = {}
    if head_path.is_file():
        for raw in head_path.read_bytes().split(b"\n"):
            if raw.strip():
                head_bytes[int(json.loads(raw)["seq"])] = len(raw) + 1
    gaps, overlaps, exceeded = [], [], []
    open_tokens: dict[str, int] = {}
    measured_at: int | None = None
    lock_at_measure = 0
    since = 0

    def lock_bytes(row: dict[str, Any]) -> int:
        # Every measurement is taken while the ledger's lock file exists; it holds the writer's pid and a timestamp in
        # the ledger's own format, so its size varies with the pid's digits (storage_admission.Ledger.locked).
        return len(json.dumps({"pid": row.get("pid"), "at": row.get("at")}).encode("utf-8")) if row.get("pid") else 0

    for raw in ledger.read_bytes().split(b"\n"):
        if not raw.strip():
            continue
        row = json.loads(raw)
        seq, kind = int(row.get("seq") or 0), row.get("kind")
        if kind == "RESERVE":
            admitted = row.get("decision") == "ADMITTED"
            if admitted and open_tokens:
                overlaps.append({"seq": seq, "operation": row.get("operation"), "open_before": sorted(open_tokens)})
            before = row.get("added_bytes_before")
            # Bytes measured while a window is open belong to that window; only a reservation opened with no window
            # open closes a gap between windows.
            if measured_at is not None and before is not None and not open_tokens:
                gap = int(before) - measured_at
                own = since + lock_bytes(row) - lock_at_measure
                gaps.append({"seq": seq, "operation": row.get("operation"), "added_between_windows": gap,
                             "ledger_own_bytes": own, "unattributed": gap - own})
            if admitted and row.get("token"):
                open_tokens[row["token"]] = seq
        elif kind == "RECONCILE":
            open_tokens.pop(row.get("token"), None)
            if row.get("underestimated"):
                exceeded.append({"seq": seq, "operation": row.get("operation"),
                                 "estimate_bytes": row.get("estimate_bytes"),
                                 "operation_added_bytes": row.get("operation_added_bytes")})
        # A continuation's OPENED record carries its measurement as ``added_bytes`` (its UNRESERVED_GROWTH record
        # repeats that figure; it is not a new measurement).
        after = next((row[k] for k in ("added_bytes_after", "added_bytes_before") if row.get(k) is not None),
                     row.get("added_bytes") if kind == "OPENED" else None)
        if after is not None:
            # The OPENED measurement is taken while the parent's lock and the continuation's own are both held by
            # the opening process (storage_snapshot.open_final), so two lock files are in it.
            measured_at, since = int(after), 0
            lock_at_measure = lock_bytes(row) * (2 if kind == "OPENED" else 1)
        since += len(raw) + 1 + head_bytes.get(seq, 0)
    unattributed = [g for g in gaps if g["unattributed"] != 0]
    return {"ledger": str(ledger), "exists": True, "records": sum(1 for r in ledger.read_bytes().split(b"\n")
                                                                  if r.strip()),
            "windows": len(gaps) + 1, "gaps": len(gaps),
            "unattributed_gaps": unattributed, "unattributed_bytes": sum(g["unattributed"] for g in unattributed),
            "overlapping_reservations": overlaps, "exceeded_reservations": exceeded,
            "unreconciled_reservations": sorted(open_tokens.values()),
            "holds": not unattributed and not overlaps and not exceeded,
            "rule": ("Between two windows only the ledger's own bytes may be added: its record and head-log lines and the "
                     "size difference of its lock file (present at every measurement, holding the writer's pid). Bytes "
                     "measured while a window is open belong to it; a reservation refused inside an open window opens "
                     "nothing. An admitted reservation opened while another is open, an exceeded reservation or an "
                     "unattributed byte is a process deviation; an open reservation is unfinished (and a deviation once "
                     "the ledger is frozen).")}


def _receipt_windows(ctx: Context) -> dict[str, Any]:
    missing = []
    for lane in WORKER_LANES:
        receipt = ctx.receipts.get(lane)
        if not receipt or not ctx.at_head(lane):
            continue
        window = (receipt.get("storage") or {}).get("receipt_window")
        if not (window and window.get("decision") == "ADMITTED"):
            missing.append(lane)
    return {"lanes_without_a_receipt_window": missing, "holds": not missing}


def _git_prefixes(ctx: Context) -> dict[str, Any]:
    rows = []
    for path in sorted((ctx.out_root / "evidence" / "git").glob("COMMIT_*.json")):
        prefix = read_json(path).get("command_prefix") or []
        rows.append({"record": path.name, "prefix": prefix, "holds": all(any(s in p for p in prefix) for s in GIT_SETTINGS),
                     "packs_unchanged": read_json(path).get("packs_unchanged")})
    for path in ctx.candidate_record_paths:
        housekeeping = read_json(path).get("git_housekeeping") or {}
        prefix = housekeeping.get("command_prefix") or []
        rows.append({"record": Path(path).name, "prefix": prefix,
                     "holds": all(any(s in p for p in prefix) for s in GIT_SETTINGS),
                     "packs_unchanged": housekeeping.get("packs_unchanged")})
    return {"records": rows, "holds": bool(rows) and all(r["holds"] and r["packs_unchanged"] is not False for r in rows)}


def _requests(ctx: Context) -> dict[str, Any]:
    totals = base.ledger_totals(ctx)
    over = {lane: row for lane, row in totals.items() if row["requests"] > row["ceiling"]}
    return {"totals": totals, "over_ceiling": over, "holds": not over}


def _comments(ctx: Context) -> dict[str, Any]:
    rows = []
    for path in sorted((ctx.out_root / "evidence" / "platform").rglob("JIRA_COMMENT_*.json")):
        record = read_json(path)
        rows.append({"file": path.relative_to(ctx.out_root).as_posix(), "issue": record.get("issue"),
                     "marker": record.get("marker"), "result": record.get("result"),
                     "readback": bool(record.get("readback_comment_ids") or record.get("readback"))})
    wrong = [r for r in rows if r["issue"] not in ("BAT-706", "BAT-708")]
    failed = [r for r in rows if r["result"] == "SUCCEEDED" and not r["readback"]]
    return {"comments": rows, "outside_the_grant": wrong, "succeeded_without_readback": failed,
            "holds": not wrong and not failed}


def process_predicates(ctx: Context) -> dict[str, Any]:
    if ctx._predicates is not None:
        return ctx._predicates
    root = ctx.out_root
    operational = window_audit(root / OPERATIONAL_LEDGER)
    final = window_audit(root / FINAL_OUTPUT_LEDGER) if (root / FINAL_OUTPUT_LEDGER).is_file() else None
    frozen = (root / FINAL_SNAPSHOT).is_file()
    windows = {"operational": operational, "final_output": final,
               "unreconciled_at_freeze": operational.get("unreconciled_reservations") if frozen else [],
               # No ledger is missing evidence (judged by the storage checks), not a violation read from evidence.
               "holds": None if not operational.get("exists") else (
                   operational["holds"] and (final is None or bool(final.get("holds")))
                   and not (frozen and operational.get("unreconciled_reservations")))}
    receipts = sorted((root / PREFLIGHT).parent.glob("OUTPUTS_PREFLIGHT*.json"))
    preflight = read_json(receipts[-1]) if receipts else {}
    here = Path(__file__).resolve().parent
    current = {"outputs_tool_sha256": sha256_file(here / "attempt11_outputs.py"),
               "lanes_tool_sha256": sha256_file(here / "attempt11_lanes.py"),
               "report_tool_sha256": sha256_file(here / "attempt11_report.py")}
    bound = {k: preflight.get(k) == v for k, v in current.items()}
    predicates = {
        "storage_windows": windows,
        "receipt_windows": _receipt_windows(ctx),
        "git_command_scope": _git_prefixes(ctx),
        "request_ceilings": _requests(ctx),
        "granted_comments": _comments(ctx),
        "tiny_preflight": {"receipts": [str(p) for p in receipts], "latest": str(receipts[-1]) if receipts else None,
                           "result": preflight.get("result"), "binds_the_current_tools": bound,
                           "holds": preflight.get("result") == "PASS" and all(bound.values()),
                           "rule": ("the latest preflight receipt must PASS and bind the current lane, output and "
                                    "report tool bytes; an earlier receipt stays as the record of its own tools")},
    }
    ctx._predicates = predicates
    return predicates


#: Which violated predicate makes which criterion FAIL. ``tiny_preflight`` missing is unfinished work, not a violation.
PREDICATE_CRITERIA = {
    "storage_windows": ("R37A11-02-B", "R37A11-05-A", "R37A11-05-C"),
    "receipt_windows": ("R37A11-02-B",),
    "git_command_scope": ("R37A11-03-C", "R37A11-05-A"),
    "request_ceilings": ("R37A11-05-B",),
    "granted_comments": ("R37A11-05-B",),
}


def _violations(ctx: Context, key: str) -> list[str]:
    """Predicates violated by the evidence and bound to this criterion. A predicate with no evidence yet (no commit,
    no comment) is not a violation; it is judged by the criterion's own completeness checks."""

    predicates = process_predicates(ctx)
    out = []
    for name, keys in PREDICATE_CRITERIA.items():
        if key not in keys:
            continue
        row = predicates[name]
        if name == "git_command_scope" and not row["records"]:
            continue
        if row["holds"] is False:
            out.append(name)
    return out


# ------------------------------------------------------------------ evidence


def register_evidence(ctx: Context) -> None:
    root = ctx.out_root
    for lane, run in ctx.runs.items():
        receipt = Path(run["receipt"])
        ctx.add(f"E-LANE-{lane}-LOG", receipt.parent / "lane.log", "command_log",
                f"{lane} run {run['run']}: the runner's console -- every command, its exit and its verdict")
        ctx.add(f"E-LANE-{lane}-RECEIPT", receipt, RAW,
                f"{lane} run {run['run']}: contract, source, interpreter, raw log paths and digests, census "
                "records, consumer outputs, the lane's and its receipt's storage windows, the shared Git store measured "
                "around the lane and the write/network scope measurement")
    career = ctx.runs.get("CAREER_SUCCESSOR")
    if career:
        for path in sorted(Path(career["receipt"]).parent.glob("ORACLE_*.json")):
            stem = path.stem[len("ORACLE_"):]
            if stem.startswith("A11_"):
                scope = ("The independent source-cardinality oracle's full result (stdlib and the Attempt 8 "
                         "raw-structure reader only, no restructure exemption; Attempt 11) over "
                         + stem[4:].replace("_", " ") + ": every field's source periods against the rows that name it, "
                         "every lineage claim, completeness and missing periods")
            elif stem.startswith("A10_"):
                scope = "The Attempt 10 interval oracle's full result, kept, over " + stem[4:].replace("_", " ")
            elif stem.startswith("A09_"):
                scope = "The Attempt 9 identity-derived source-unit oracle's full result, kept, over " + \
                        stem[4:].replace("_", " ")
            else:
                scope = "The Attempt 8 independent source-field oracle's full result, kept, over " + stem.replace("_", " ")
            ctx.add(f"E-ORACLE-{stem}", path, RAW, scope)
    for identity, path, kind, scope in (
            ("E-REQUEST-LEDGER", root / "evidence" / "platform" / "REQUEST_LEDGER.jsonl", CENSUS,
             "Every counted platform request, retries included, appended before its result was used"),
            ("E-FAILURE-CLASSIFICATION", root / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json", CENSUS,
             "Worker classification of every failing identity of a red lane, by cause, kind, owner and next action"),
            ("E-NEW-FINDINGS", ctx.findings_path, CENSUS,
             "Findings discovered in Attempt 11, with severity, disposition, owner and next action"),
            ("E-CLEANUP-INVENTORY", root / "evidence" / "CLEANUP_INVENTORY.json", CENSUS,
             "Every directory this attempt created or wrote, its bytes, and what the owner may remove (nothing removed)"),
            ("E-INTAKE", root / "evidence" / "intake" / "INTAKE.json", RAW,
             "Intake: the sealed contract and every issued source re-hashed, both closure archives member by member, "
             "the three subjects (the issued base, the granted candidate head, main), the interpreter, the installed "
             "Attempt 10 consumer, the manager's saved fixture and the delivered data files, before any repair was "
             "drafted"),
            ("E-CLOSURE-ROWS", root / "evidence" / "intake" / "CLOSURE_ROWS.json", RAW,
             "Every entry of the manager's original-input and review closures compared with its archive"),
            ("E-GIT-HOUSEKEEPING-PREFLIGHT", root / "evidence" / "intake" / "GIT_HOUSEKEEPING_PREFLIGHT.json", RAW,
             "Owned Git fixtures: a plain commit runs gc --auto and packs the loose objects; the same commit with "
             "command-scoped gc.auto=0 and maintenance.auto=false leaves them loose"),
            ("E-GIT-HELPER-CONSTRUCTION", root / "evidence" / "intake" / "GIT_HELPER_CONSTRUCTION.json", RAW,
             "Every Git command the unchanged Attempt 9 wrapper builds begins with the two command-scoped settings"),
            ("E-BEFORE-REPRODUCTION", root / "evidence" / "before" / "BEFORE_REPRODUCTION.json", RAW,
             "Before-repair reproduction of MF37A10-01 on the clean issued base c2f82759 before any Attempt 11 source "
             "was drafted: the manager's saved false-restructure fixture through the installed console script, "
             "installed module and source module, the exception-branch matrix (collapse, expansion, forged periods, "
             "retained negatives and genuine positives) and the unchanged Attempt 10 oracle over the fixture"),
            ("E-CONTROL07-PATCH", root / CONTROL_PATCH, RAW,
             "The inert CONTROL-07 proposal as a patch against main's six control surfaces (never applied)")):
        if Path(path).is_file():
            ctx.add(identity, path, kind, scope)
    preflights = sorted((root / PREFLIGHT).parent.glob("OUTPUTS_PREFLIGHT*.json"))
    for path in preflights:
        latest = path == preflights[-1]
        ctx.add("E-OUTPUTS-PREFLIGHT" if latest else f"E-OUTPUTS-PREFLIGHT-{path.stem}", path, RAW,
                ("The latest tiny-fixture preflight" if latest else "An earlier tiny-fixture preflight, kept as the "
                 "record of its own tool bytes") + " of the lane and output tools: exact identities and evidence kinds, "
                "the reserve-to-final-output storage lifecycle, the window audit on clean, gapped, overlapping, exceeded "
                "and refused-inside-a-window ledgers, the generated report, checklist and submission, and the expected "
                "states for OPEN_OUT_OF_SCOPE and partially FIXED_LOCAL findings")
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
                f"The retained inert proposed bytes of {relative} (the qualified Attempt 7 bytes, retained by Attempts 8 "
                "to 10; not adopted)")
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
                ("E-STORAGE-LEDGER", ledger, "The attempt's root storage ledger (Cycle 37 / Attempt 11), frozen by its "
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
    for identity, row in ctx.evidence.items():
        relative = Path(row["path"]).resolve().relative_to(root.resolve()).as_posix()
        if relative in NEVER_EVIDENCE:
            raise SystemExit(f"{identity} registers {relative}, which a later step writes; refusing")
        if relative in (OPERATIONAL_LEDGER.as_posix(), OPERATIONAL_LEDGER.as_posix() + storage_admission.HEAD_SUFFIX) \
                and not (root / FINAL_SNAPSHOT).is_file():
            raise SystemExit(f"{identity} registers the live operational ledger before its freeze; refusing")


# ------------------------------------------------------------------ lanes


_CARRIED = "CARRIED_BY_ATTEMPT10_LANE_AT_THE_CANDIDATE_HEAD"


def _relabel(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The preserved dispositions name the attempt whose lane carries a prior lane; here that is Attempt 11. The
    results were read from this attempt's receipts, so only the naming changes."""

    out = []
    for row in rows:
        row = dict(row)
        if row.get("disposition") == _CARRIED:
            row["disposition"] = "CARRIED_BY_ATTEMPT11_LANE_AT_THE_CANDIDATE_HEAD"
            row["attempt11_lanes"] = row.pop("attempt10_lanes")
            row["attempt11_results"] = row.pop("attempt10_results")
            if "justification" in row:
                row["justification"] = row["justification"].replace("Attempt 10 lane", "Attempt 11 lane")
        out.append(row)
    return out


def _a10_final(lane: str) -> dict[str, Any]:
    index = ATTEMPT10_ROOT / "lanes" / "RUNS.jsonl"
    rows = [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [row for row in rows if row["lane"] == lane and row["head"] == BASE_SHA]
    return rows[-1] if rows else {}


def attempt10_lane_dispositions(ctx: Context) -> list[dict[str, Any]]:
    rows = []
    for lane, successors in A10_LANES.items():
        final = _a10_final(lane)
        row: dict[str, Any] = {"id": f"A10-LANE-{lane}", "attempt10_lane": lane, "attempt10_run": final.get("run"),
                               "attempt10_result": final.get("result"), "attempt10_head": final.get("head"),
                               "attempt10_receipt": final.get("receipt"),
                               "attempt10_receipt_sha256": final.get("receipt_sha256"),
                               "attempt10_receipt_preserved": bool(final.get("receipt"))
                               and Path(final["receipt"]).is_file()}
        if not successors:
            row.update(disposition="MANAGER_OWNED",
                       justification="The Attempt 10 manager lane is the manager's; its review is retained in the "
                                     "issued closure.")
        else:
            row.update(disposition="CARRIED_BY_ATTEMPT11_LANE_AT_THE_CANDIDATE_HEAD", attempt11_lanes=list(successors),
                       attempt11_results={s: (ctx.receipts[s]["result"] if ctx.at_head(s) else "NOT_AT_HEAD")
                                          for s in successors if s in ctx.receipts},
                       justification=("Re-executed fresh by the same-named Attempt 11 lane at the candidate head; the "
                                      "Attempt 10 receipt stays unchanged as the before-record (its result is never "
                                      "relabelled; a red Attempt 10 result stays red there)."))
        rows.append(row)
    return rows


LANE_LISTS = a10o.LANE_LISTS + (("attempt10_lanes", "A10-LANE-"),)


def lane_dispositions(ctx: Context) -> None:
    a10o.lane_dispositions(ctx)
    for name, _ in a10o.LANE_LISTS:
        setattr(ctx, name, _relabel(getattr(ctx, name)))
    ctx.attempt10_lanes = attempt10_lane_dispositions(ctx)


def _lane_lists(ctx: Context) -> dict[str, list[dict[str, Any]]]:
    return {name: getattr(ctx, name) for name, _ in LANE_LISTS}


# ------------------------------------------------------------------ inherited red lanes


def classify(ctx: Context) -> dict[str, Any]:
    """Derive the Attempt 11 classification from Attempt 10's, identity by identity and cause by cause."""

    previous_path = ATTEMPT10_ROOT / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json"
    previous = read_json(previous_path)
    lanes: dict[str, Any] = {}
    problems: list[str] = []
    for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED"):
        receipt = ctx.receipts.get(lane)
        if not receipt or receipt["result"] != "FAIL" or not ctx.at_head(lane):
            continue
        failing = base.failing_identities(receipt) or []
        comparison = (receipt.get("details") or {}).get("attempt10_comparison") or {}
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
                       "attempt10_run": (previous["lanes"].get(lane) or {}).get("run"), "groups": list(groups.values()),
                       "equivalence": {"persisting": len(comparison.get("persisting") or []),
                                       "persisting_same_cause": len(comparison.get("persisting_same_cause") or []),
                                       "new_in_attempt11": comparison.get("new_in_attempt11"),
                                       "no_longer_failing": comparison.get("no_longer_failing") or
                                       comparison.get("no_longer_reported")}}
    if problems:
        raise SystemExit("classification refused:\n" + "\n".join(problems))
    document = {"label": f"{LABEL_PREFIX} IN_PROGRESS_LOCAL_WORK_REMAINS (inherited failure classification)",
                "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
                "attempt_id": ATTEMPT_ID, "authored_at": utc_now(),
                "rule": ("Each failing identity keeps its Attempt 10 group only when it persists with the same traceback "
                         "cause (FULL_FINAL_MOUNTED) or the same finding line (STRICT_MOUNTED); anything else is refused "
                         "for manual classification."),
                "derived_from": {"path": str(previous_path), "sha256": sha256_file(previous_path)}, "lanes": lanes}
    write_output(ctx.out_root / "evidence" / "INHERITED_FAILURE_CLASSIFICATION.json", dumps(document))
    return document


def inventory(ctx: Context) -> dict[str, Any]:
    """Every directory this attempt created or wrote, with its bytes; nothing is removed (no cleanup is granted)."""

    purposes = {
        (VALIDATION_ROOT, "intake"): ("The intake script", False),
        (VALIDATION_ROOT, "before"): ("The before-repair reproduction script, its consumer outputs and the oracle run",
                                      False),
        (VALIDATION_ROOT, "gitpreflight"): ("The owned Git fixtures of the housekeeping preflight", True),
        (VALIDATION_ROOT, "preflight"): ("The tiny-fixture preflight roots of the lane and output tools (not evidence; "
                                         "its receipt is)", True),
        (VALIDATION_ROOT, "dev"): ("Development scratch: the unfixed-base export, oracle and case-matrix development "
                                   "runs, the v7 genuine counts (not evidence)", True),
        (VALIDATION_ROOT, "fixtures"): ("Owned forgery fixtures: the copy of the manager's saved false-restructure "
                                        "fixture (never written) and full successor copies restored before every case",
                                        True),
        (VALIDATION_ROOT, "tools"): ("The commit helper (provenance regenerated, command-scoped Git settings)", False),
        (VALIDATION_ROOT, "cv"): ("The granted append's validation view: a byte-for-byte materialization of the appended "
                                  "candidate tree; the committed-blob proof cites it", False),
        (VALIDATION_ROOT, "cn"): ("Scratch repositories of the candidate lane's committed-provenance negatives", True),
        (VALIDATION_ROOT, "lanes"): ("Lane work directories (manager-probe replay copies, base export, fixtures)", True),
        (VALIDATION_ROOT, "rehearsal"): ("Rehearsal lane runs (labelled REHEARSAL, never evidence)", True),
        (VALIDATION_ROOT, "jira"): ("Private Jira successor copies (never the committed pack or live Jira)", True),
        (VALIDATION_ROOT, "control07"): ("The CONTROL-07 offline qualification's scratch matrices", True),
        (VALIDATION_ROOT, "platform"): ("Console output of the platform reads (not evidence)", True),
        (VALIDATION_ROOT, "tmp"): ("Development scratch: commit messages, test temp, console output", True),
        (PACKAGING_ROOT, "b"): ("The fresh noneditable BAS wheel stages (source export, dist, virtual environment)", True),
        (PACKAGING_ROOT, "candidate"): ("Private index files and messages of the candidate append", False),
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
                "Attempt 11 evidence (declared outputs, receipts, platform and storage records)" if root == ctx.out_root
                else "Attempt 11 working files", False))
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
        final = _a10_final(lane)
        rows.append({"lane": lane, "attempt11_run": (ctx.runs.get(lane) or {}).get("run"),
                     "attempt11_result": receipt.get("result"), "at_candidate_head": ctx.at_head(lane),
                     "counts": receipt.get("counts"),
                     "execution": "FRESH_AT_THE_CANDIDATE_HEAD" if ctx.at_head(lane) else "NOT_AT_HEAD",
                     "attempt10_run": final.get("run"), "attempt10_result": final.get("result"),
                     "attempt10_receipt": final.get("receipt"), "attempt10_receipt_sha256": final.get("receipt_sha256"),
                     "attempt10_comparison": details.get("attempt10_comparison"),
                     "failing_identities": base.failing_identities(receipt) if receipt.get("result") == "FAIL" else None})
    return {"label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "cycle_id": CYCLE_ID,
            "attempt_id": ATTEMPT_ID, "candidate": ctx.candidate, "lanes": rows, "equivalence_used": [],
            "equivalence_statement": ("TP37-A11 permits a lane to carry an old execution by a complete current "
                                      "dependency comparison. This attempt used none for a lane: the consumer's "
                                      "dependencies changed (career_successor.py, career_interval.py), so every one of "
                                      "the 14 worker lanes executed fresh at the candidate head. The storage tools and "
                                      "suites are proved to be the exact bytes the Attempt 10 final STORAGE_ADMISSION "
                                      "qualified, and that lane re-ran them anyway. Each Attempt 10 final receipt is "
                                      "retained unchanged as the before-record and compared by identity; no old "
                                      "execution is relabelled, and the Attempt 10 red lanes stay red there."),
            "classification": ctx.classification, **_lane_lists(ctx),
            "rule": ("Inherited red lanes stay red until genuinely resolved. Equivalence is by exact identity and cause "
                     "against the Attempt 10 final receipts at the issued base; counts alone establish nothing.")}


# ------------------------------------------------------------------ criteria


_d, _holds, _n, _f, _summary = a10o._d, a10o._holds, a10o._n, a10o._f, a10o._summary


def _reproduction(ctx: Context) -> dict[str, Any]:
    path = ctx.out_root / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
    return read_json(path) if path.is_file() else {}


def _before(ctx: Context) -> bool:
    record = _reproduction(ctx)
    served = record.get("negatives_served_by_unfixed_base") or {}
    saved = (record.get("saved_fixture") or {}).get("results") or []
    return bool(record.get("reproduced") and (record.get("subject_before") or {}).get("is_issued_base")
                and served and all(served.values()) and len(saved) == 3
                and all(r.get("exit") == 0 and not r.get("refusal") for r in saved))


def _unfixed(ctx: Context) -> dict[str, Any]:
    return _d(ctx, "SOURCE_REGRESSIONS").get("attempt11_suite_on_the_unfixed_base") or {}


def _control(ctx: Context) -> dict[str, Any]:
    path = ctx.out_root / "CONTROL07_PROPOSAL_VALIDATION.json"
    return read_json(path) if path.is_file() else {}


#: The CONTROL-07 receipt's retention checks (attempt11_control07.py): the qualified bytes, patch and issued records.
RETENTION_CHECKS = ("proposed_bytes_identical_to_attempt10_9_8_and_7", "patch_identical_to_the_qualified_patch",
                    "attempt10_proposal_document_is_the_issued_bytes", "attempt10_validation_is_the_issued_bytes",
                    "manager_review_is_the_issued_bytes", "retained_bytes_are_the_manager_reviewed_bytes",
                    "integration_decision_is_the_issued_bytes", "control_change_protocol_is_the_issued_bytes")


def _retained(control: dict[str, Any]) -> bool:
    checks = control.get("checks") or {}
    return all(checks.get(name) is True for name in RETENTION_CHECKS)


def _state(failing: list[str], violated: list[str]) -> str:
    return "FAIL" if violated else "IN_PROGRESS"


#: The criterion ``judge`` is deciding, so ``_refuse`` can record what failed it: violated predicates (a recorded
#: deviation no further local work undoes) and unmet local checks (work that remains).
_JUDGING: dict[str, Any] = {}


def _refuse(failing: list[str], violated: list[str], prefix: str = "not held at the candidate head") -> tuple[str, str]:
    if _JUDGING:
        _JUDGING["ctx"].criterion_meta[_JUDGING["key"]] = {"violated": list(violated), "local": list(failing)}
    parts = [f"process predicate violated by the evidence: {name}" for name in violated] + failing
    return _state(failing, violated), f"{prefix}: " + ", ".join(parts)


R01_KEYS = (("INSTALLED_CONSUMER_C01", "a11_cases"),
            ("INSTALLED_CONSUMER_C01", "manager_a10_false_restructure_entrypoints"),
            ("INSTALLED_CONSUMER_C01", "a10_interval_cases"), ("INSTALLED_CONSUMER_C01", "manager_a9_interval_entrypoints"),
            ("INSTALLED_CONSUMER_C01", "a9_forgeries"), ("INSTALLED_CONSUMER_C01", "manager_a8_null_span_entrypoints"),
            ("INSTALLED_CONSUMER_C01", "a8_forgeries"), ("INSTALLED_CONSUMER_C01", "manager_a7_envelope_entrypoints"),
            ("INSTALLED_CONSUMER_C01", "a8_genuine_source_module"), ("INSTALLED_CONSUMER_C01", "a7_forgeries"),
            ("INSTALLED_CONSUMER_C01", "manager_a6_same_page_lineage"), ("INSTALLED_CONSUMER_C01", "a6_forgeries"),
            ("INSTALLED_CONSUMER_C01", "installed_identity_census"),
            ("INSTALLED_CONSUMER_C01", "manager_a5_successor_adversarial"),
            ("INSTALLED_CONSUMER_C01", "manager_a5_successor_population_audit"),
            ("CAREER_SUCCESSOR", "independent_cardinality_oracle"), ("CAREER_SUCCESSOR", "earlier_oracles_kept"),
            ("CAREER_SUCCESSOR", "independent_identity_census"))


def _judge_r01(ctx: Context, key: str) -> tuple[str, str]:
    installed, career = _d(ctx, "INSTALLED_CONSUMER_C01"), _d(ctx, "CAREER_SUCCESSOR")
    violated = _violations(ctx, key)
    failing = [lane for lane in REQUIREMENT_LANES["R37A11-01"] if not ctx.lane_ok(lane)]
    failing += [f"{lane}:{k}" for lane, k in R01_KEYS if not _holds(ctx, lane, k)]
    failing += [f"source binding {k}" for k, v in (career.get("source_identity_checks") or {"none": False}).items()
                if not v]
    failing += [f"source interval {k}" for k, v in ((career.get("source_interval_checks") or {}).get("checks")
                                                    or {"none": False}).items() if not v]
    failing += [f"original negative {name}" for name in a6o._lineage_originals(ctx)]
    if not (installed.get("successor_pagination") or {}).get("reconciled"):
        failing.append("complete pagination")
    if key.endswith("-C"):
        if not _before(ctx):
            failing.append("before-repair reproduction at all three entrypoints")
        if not _unfixed(ctx).get("holds"):
            failing.append("the new suite fails on the unfixed base with the saved construction accepted there")
    if failing or violated:
        return _refuse(failing, violated)
    checks = career["source_interval_checks"]
    observed = checks.get("observed") or {}
    a05 = observed.get("A05") or {}
    anchors = observed.get("anchors") or {}
    oracle = career["independent_cardinality_oracle"]
    genuine = oracle.get("genuine_a05") or {}
    saved = oracle.get("manager_a10_false_restructure") or {}
    cases = installed["a11_cases"]["cases"]
    manager = installed["manager_a10_false_restructure_entrypoints"]
    codes = collections.Counter(row.get("expected") for row in cases.values())
    kinds = collections.Counter(row.get("kind") for row in cases.values())
    unfixed = _unfixed(ctx)
    reproduction = _reproduction(ctx)
    served = {r.get("entrypoint"): r.get("row_count") for r in (reproduction.get("saved_fixture") or {}).get("results") or []}
    intervals = a05.get("source_intervals_proved") or {}
    relations = {r["relation"]: r.get("counts") for r in genuine.get("relations") or []}
    text = {
        "A": ("Every successor row of both relations and both formats is now read again from its verified source unit "
              "whatever its disposition, restructured included: the rows naming one source field must be exactly the "
              "intervals that field states -- membership, ordinal and multiplicity -- and each row's stated interval must "
              "be the one its source states; a restructure claim is admitted only when the child's whole field in the "
              "parent's unit is claimed and its count genuinely changed; a NOT_PRODUCED claim must name a unit its "
              "source does not produce; every period-stating field unit of a cited capture must be held. Over the "
              f"genuine Attempt 5 file {_n(intervals.get('rows_read_again_from_source'))} rows were read again "
              f"({_n(intervals.get('multi_interval_fields'))} multi-interval fields, "
              f"{_n(intervals.get('rows_in_multi_interval_fields'))} rows; "
              f"{_n(intervals.get('rows_stating_no_interval_text'))} rows with no period text, each where its source "
              f"states none), {_n((anchors.get('A5<-default') or {}).get('restructure_claims_qualified'))} of "
              f"{_n((anchors.get('A5<-default') or {}).get('restructured_entries'))} restructure claims qualified by "
              f"their source, NOT_PRODUCED claims {_j(a05.get('not_produced_claims_proved'))}, completeness "
              f"{_j(a05.get('source_completeness_proved'))}. The independent oracle "
              f"(`{genuine.get('oracle_version')}`) has no restructure exemption: it judges every field and claim from "
              "the raw capture. Legitimate splits, merges, corrections and unknown dates keep their lineage; no "
              "normalized date is compared across versions and nothing is rebuilt or activated."),
        "B": (f"The {_n((genuine.get('rows') or {}).get('successor'))}-row successor and the default and Attempt 4 "
              "dispositions serve unchanged with complete pagination. The oracle reads "
              f"{_n(genuine.get('captures_read'))} captures and finds {genuine.get('invalid_total')} invalid; all "
              f"{genuine.get('multi_interval_fields')} multi-interval groups ({genuine.get('rows_in_multi_interval_fields')} "
              f"Attempt 5 rows) are classified with their parents; its named anomalies are the manager's seven parser "
              f"fields (equal {genuine.get('known_anomaly_comparison_equal')}); lineage verdicts {_j(relations, 600)}. "
              f"The manager's saved false-restructure fixture (as issued {manager.get('as_issued')}) is refused as "
              f"{REFUSED_CARDINALITY} through the installed console script, the installed module and the source "
              f"module, and the oracle finds it invalid ({saved.get('invalid_total')}); {len(cases)} fresh cases "
              f"({dict(kinds)}), each after a fixture reset, hold at both entrypoints ({dict(codes)})."),
        "C": ("Before repair, on the clean issued base c2f82759 with nothing drafted, the saved fixture was served at "
              f"every entrypoint ({served}) and every new negative of the exception-branch matrix was served too "
              f"({sum(1 for v in (reproduction.get('negatives_served_by_unfixed_base') or {}).values() if v)} of "
              f"{len(reproduction.get('negatives_served_by_unfixed_base') or {})}); the retained negatives were already "
              f"refused ({_j(reproduction.get('retained_negatives_observed'), 400)}) and the genuine positives served. "
              f"Over the unfixed base's exact bytes the new suite fails: of {unfixed.get('negative_cases')} negative "
              f"case outcomes none passes there, {len(unfixed.get('accepted_by_the_unfixed_code') or [])} are accepted "
              f"there (the saved construction among them), {len(unfixed.get('new_api_or_record_absent') or [])} use the "
              "new check absent there; the source cardinality was derived without the production predicate."),
    }[key[-1]]
    return "VERIFIED_LOCAL", text


def _j(value: Any, limit: int = 300) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + " ..."


def _judge_r02(ctx: Context, key: str) -> tuple[str, str]:
    storage = ctx.storage()
    admission = _d(ctx, "STORAGE_ADMISSION")
    predicates = process_predicates(ctx)
    violated = _violations(ctx, key)
    live = ((admission.get("storage_ledger") or {}).get("live_over_budget_control") or {}).get("refused")
    failing = [lane for lane in REQUIREMENT_LANES["R37A11-02"] if not ctx.lane_ok(lane)]
    if not live:
        failing.append("live over-budget refusal")
    failing += [k for k in ("manager_a9_storage_independent", "manager_a8_storage_independent",
                            "manager_a7_same_path_race", "manager_a7_stop_reserve",
                            "manager_a6_storage_continuation", "manager_a5_storage_independent",
                            "storage_dependencies_equal_to_attempt10_accepted")
                if not _holds(ctx, "STORAGE_ADMISSION", k)]
    if not storage["frozen_and_verified"]:
        failing.append("root ledger frozen, verified and its chain proved")
    validation = sorted((ctx.out_root / "evidence" / "final").glob("FINAL_PACKET_VALIDATION_*.json"))
    if not validation or read_json(validation[-1]).get("result") != "PASS":
        failing.append("FINAL_PACKET validation receipt PASS")
    if key.endswith("-C") and not predicates["tiny_preflight"]["holds"]:
        failing.append("tiny-fixture preflight PASS")
    if failing or violated:
        return _refuse(failing, violated, "not held")
    measured = storage["operational"].get("measured") or {}
    windows = predicates["storage_windows"]
    operational = windows["operational"]
    final = windows.get("final_output") or {}
    manager = admission["manager_a9_storage_independent"]
    extra = manager.get("extra_root_restart") or {}
    dependencies = admission["storage_dependencies_equal_to_attempt10_accepted"]
    text = {
        "A": ("The accepted storage behavior is preserved: the storage tools and suites at this head are the exact "
              f"blobs the Attempt 10 final STORAGE_ADMISSION receipt qualified ({dependencies.get('attempt10_final_run')}, "
              f"{dependencies.get('attempt10_final_result')}) and they ran fresh anyway: the storage suites pass, the "
              "managers' Attempt 9 and Attempt 8 challenges, replayed with only their fixture roots adapted, leave "
              f"{(manager.get('concurrent') or {}).get('init_count')} INIT across twelve processes "
              f"({(manager.get('concurrent') or {}).get('fresh_opens')} fresh open, "
              f"{(manager.get('concurrent') or {}).get('resumed_opens')} resumes) and refuse the extra-empty-root restart "
              f"as {extra.get('code')} with the root never measured; the stopped, reserve-changed and recycled-headroom "
              "cases stay refused; no ceiling, baseline or headroom changed."),
        "B": ("The Attempt 11 root ledger was initialized before any Attempt 11 write; every operation, every lane and "
              "every lane's receipt was reserved before it wrote and reconciled after; the windows are serialized "
              f"({len(operational.get('overlapping_reservations') or [])} overlaps), none exceeded its reservation "
              f"({len(operational.get('exceeded_reservations') or [])}), and between the "
              f"{_n(operational.get('windows'))} root windows only the ledger's own record and head lines were added "
              f"(unattributed bytes {_n(operational.get('unattributed_bytes'))}; final-output continuation "
              f"{_n(final.get('unattributed_bytes'))}). The ledger froze with {_n(measured.get('added_bytes'))} bytes "
              f"added of its {_n(storage['operational'].get('budget_bytes'))}-byte budget; the final outputs are "
              "reserved on its one claimed continuation and FINAL_PACKET passes on it. Earlier attempts' ledgers are "
              "retained unchanged; their historical deviations stay theirs."),
        "C": ("The lifecycle was exercised on tiny owned fixtures before any costly lane (identity, grant, reserve, "
              "execute, measure, close, freeze, final-output continuation; the window audit on a clean and a gapped "
              "ledger; E-OUTPUTS-PREFLIGHT); the retained storage attacks and twelve-process root tests ran fresh; a "
              "snapshot is not new spending authority, and the one cumulative budget carried across both segments."),
    }[key[-1]]
    return "VERIFIED_LOCAL", text


def _judge_r03(ctx: Context, key: str) -> tuple[str, str]:
    details = _d(ctx, "LOCAL_INTEGRATION_CANDIDATE")
    violated = _violations(ctx, key)
    failing = [lane for lane in REQUIREMENT_LANES["R37A11-03"] if not ctx.lane_ok(lane)]
    checks = details.get("candidate_tree_checks") or {}
    failing += [k for k, v in checks.items() if not v] or ([] if checks else ["tree checks"])
    failing += [k for k, v in (details.get("candidate_attempt11") or {"attempt 11 chain": False}).items() if not v]
    failing += [k for k in ("candidate_negatives", "manager_a10_committed_tree", "manager_a9_committed_tree",
                            "manager_a8_committed_tree", "manager_a7_committed_tree", "manager_a6_committed_tree",
                            "manager_a5_integration_replay", "candidate_consumer", "control07_requalification")
                if not _holds(ctx, "LOCAL_INTEGRATION_CANDIDATE", k)]
    if not ctx.candidate_record_path:
        failing.append("append record")
    control = _control(ctx)
    subjects = control.get("subjects") or {}
    final_candidate = candidate.describe().get("candidate_head")
    requalified = details.get("control07_requalification") or {}
    last = read_json(ctx.candidate_record_path) if ctx.candidate_record_path else {}
    if control.get("result") != "PASS":
        failing.append("CONTROL07_PROPOSAL_VALIDATION.json PASS")
    elif subjects.get("candidate") != final_candidate or last.get("candidate_commit") != final_candidate \
            or subjects.get("repair") != last.get("repair_head"):
        failing.append("the create-only CONTROL-07 validation is bound to the final candidate and its repair head")
    if (requalified.get("subjects") or {}).get("candidate") != final_candidate:
        failing.append("CONTROL-07 re-qualified in the lane at the final candidate")
    if not _retained(control):
        failing.append("the retained proposal is the qualified, manager-reviewed bytes")
    errors = (details.get("candidate_review_control_characterization") or {}).get("compatibility_errors")
    if key.endswith("-C") and not errors:
        failing.append("the two control compatibility errors kept visible")
    if failing or violated:
        return _refuse(failing, violated, "not held")
    proof = details.get("committed_tree_proof") or {}
    green = (control.get("characterization") or {}).get("current_checkers_green_on") or {}
    cases = len(((control.get("checker_runs") or {}).get("proposed") or {}).get("cases") or {})
    stores = [read_json(p).get("git_housekeeping") or {} for p in ctx.candidate_record_paths]
    text = {"A": ("The qualified CONTROL-07 proposal is retained byte for byte from Attempt 10 (identical to the Attempt 9, "
                  "8 and 7 bytes, the checker and workflow the managers' independent case review qualified; the "
                  "regenerated patch is the qualified fab1911e... patch) under this attempt's evidence root, outside "
                  "every checkout, and rebound: "
                  f"{sum(1 for v in (control.get('checks') or {}).values() if v)} of {len(control.get('checks') or {})} "
                  f"checks hold over {cases} offline fixture cases at repair {str(subjects.get('repair'))[:8]} and the "
                  f"final candidate {str(subjects.get('candidate'))[:8]}; the current checkers exit green on "
                  + ", ".join(f"{name} {len(rows)}" for name, rows in green.items())
                  + " of those cases. No active control was changed, no provider or workflow ran; adoption needs the "
                    "eligible independent bootstrap receipt and publication authority, both ungranted."),
            "B": ("The prior independent offline proof is retained by exact unchanged dependencies (proposal bytes, "
                  "patch, the committed protocol and main's control surfaces unchanged; this attempt touches none of "
                  "them) and the worker's matrix re-ran only to bind the new heads: FAIL, BLOCKED and SKIPPED reports, "
                  "self-approval, a stale head, a dismissed or unapproved review, a changed control surface and a PASS "
                  "under the unapproved protocol all fail closed; the only green proposed case is the synthetic "
                  "TEST_ONLY approval, which is not a receipt. The original and proposed hashes and the exact later "
                  "adoption, rollback and verification actions are in CONTROL07_PROPOSAL.md, written at the final "
                  f"candidate {str(final_candidate)[:8]}."),
            "C": ("The restructure-lineage repair and regenerated provenance were appended forward to cf992e4b "
                  f"({len(ctx.candidate_record_paths)} [material] commit(s)), every Git command with -c gc.auto=0 -c "
                  "maintenance.auto=false and the shared store measured unchanged in packs "
                  f"({all(s.get('packs_unchanged') for s in stores)}); every ancestor (daba87f0, bb5253b2, 0c22af20, "
                  "c52e7b52, 514d74dc, cf992e4b) and main's protected bytes retained, only the candidate ref moved; "
                  f"committed blobs and manifest reconcile ({proof.get('committed_paths')} paths, "
                  f"{proof.get('manifest_rows')} manifest rows, 0 mismatches), independently confirmed by the "
                  "manager's Attempt 10, 9, 8, 7 and 6 committed-tree reviews; the consumer built from the candidate "
                  "tree serves and refuses; the two control compatibility errors stay visible "
                  f"({len(errors or [])} failing tests characterized). Qualifying the private proposal does not qualify "
                  "the candidate for publication.")}
    return "VERIFIED_LOCAL", text[key[-1]]


def _judge_r04(ctx: Context, key: str) -> tuple[str, str]:
    installed = _d(ctx, "INSTALLED_CONSUMER_C01")
    violated = _violations(ctx, key)
    needed = REQUIREMENT_LANES["R37A11-04"]
    failing = [lane for lane in needed if lane not in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED") and not ctx.lane_ok(lane)]
    failing += [lane for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED") if not ctx.executed(lane)]
    for lane in ("FULL_FINAL_MOUNTED", "STRICT_MOUNTED"):
        comparison = _d(ctx, lane).get("attempt10_comparison") or {}
        if comparison.get("new_in_attempt11"):
            failing.append(f"{lane} new identities {comparison['new_in_attempt11']}")
    named = (installed.get("successor_named_cases") or {}).get("holds") or {}
    failing += [f"named {k}" for k, v in named.items() if not v] or ([] if named else ["named cases"])
    failing += [k for k in ("manager_a3_career_challenge", "manager_a4_career_semantic_census",
                            "manager_a4_successor_challenge", "manager_a5_career_semantic_census",
                            "manager_a5_successor_adversarial", "a7_forgeries", "a8_forgeries", "a9_forgeries",
                            "a10_interval_cases", "a11_cases", "manager_a6_same_page_lineage",
                            "manager_a7_envelope_entrypoints", "manager_a8_null_span_entrypoints",
                            "manager_a9_interval_entrypoints", "manager_a10_false_restructure_entrypoints")
                if not _holds(ctx, "INSTALLED_CONSUMER_C01", k)]
    if not (installed.get("successor_coverage") or {}).get("predecessor_identity_sets_equal"):
        failing.append("successor coverage")
    if failing or violated:
        return _refuse(failing, violated, "not held")
    census = _d(ctx, "CAREER_SUCCESSOR").get("independent_identity_census") or {}
    full = _d(ctx, "FULL_FINAL_MOUNTED").get("attempt10_comparison") or {}
    oracle = (_d(ctx, "CAREER_SUCCESSOR").get("independent_cardinality_oracle") or {}).get("genuine_a05") or {}
    text = {"A": (f"All {_n(census.get('rows'))} genuine rows and {_n(census.get('raw_files'))} captures verify and serve "
                  "unchanged; every default and Attempt 4 predecessor row keeps one disposition; all "
                  f"{oracle.get('multi_interval_fields')} multi-interval groups ({oracle.get('rows_in_multi_interval_fields')} "
                  "Attempt 5 rows) and their parents were reviewed at interval grain by the verifier and independently "
                  "by the oracle; legitimate missingness, unknown dates, corrections, splits and restructures keep their "
                  "meanings (the seven known parser-anomaly fields stay owned future scope, Cedric Scott's two separately "
                  "stated periods a supported correction); no database was rebuilt and no fact invented or activated."),
            "B": ("One fresh offline noneditable BAS wheel, built from the candidate head outside every checkout and "
                  "composed with the released C01 wheel, paginates the whole successor and every filter exactly as the "
                  "independent SQL oracle and raw census derive them, serves the same rows through its module entrypoint "
                  "as through its console script (and the source module), and refuses every original and new lineage "
                  "forgery for its own cause, each negative after an independent fixture reset; no row is hidden or "
                  "dropped; the C01 composition keeps its lost-field and adoption limits."),
            "C": ("The guard, date, defensive-unit, unknown-role, Cory 2018/Danny/Steve, scoring/PIT, harness, "
                  "default/legacy and Cycle 29 behavior pass their suites and the manager replays at the candidate head; "
                  f"the full mounted suite ran fresh ({_n(full.get('final_tests_run'))} tests) and matches Attempt 10 "
                  f"identity for identity ({len(full.get('persisting') or [])} persisting, "
                  f"{len(full.get('new_in_attempt11') or [])} new); the default database, prior releases, raw captures and "
                  "frozen predictions are unchanged; the 2,223-row staff successor and the whole history stay owned.")}
    return "VERIFIED_LOCAL", text[key[-1]]


def _judge_r05(ctx: Context, key: str) -> tuple[str, str]:
    predicates = process_predicates(ctx)
    violated = _violations(ctx, key)
    if key.endswith("-A"):
        missing = [lane for lane in WORKER_LANES if not ctx.executed(lane)]
        failing = [f"not yet executed at the candidate head: {', '.join(missing)}"] if missing else []
        if not predicates["tiny_preflight"]["holds"]:
            failing.append("tiny-fixture preflight PASS")
        if not predicates["git_command_scope"]["records"]:
            failing.append("repair commit receipts")
        if failing or violated:
            return _refuse(failing, violated, "not held")
        return "VERIFIED_LOCAL", ("The Attempt 11 lane and output tools were preflighted on tiny owned fixtures (exact "
                                  "IDs, evidence kinds, generated report/checklist/submission agreement, the "
                                  "reserve-to-final-output lifecycle, the window audit, and the expected states of "
                                  "OPEN_OUT_OF_SCOPE and partially FIXED_LOCAL findings) before any costly lane; the "
                                  "finding was reproduced on the clean issued base before any source was drafted; every "
                                  "recorded Git mutator carried -c gc.auto=0 -c maintenance.auto=false "
                                  f"({len(predicates['git_command_scope']['records'])} records); every one of the 14 "
                                  "worker lanes executed fresh through the issued command at the candidate head with "
                                  "exact binding, raw counts and the shared Git store measured around it; MANAGER_REVIEW "
                                  "stays pending; inherited red stays red, compared with Attempt 10 by identity and cause.")
    if key.endswith("-B"):
        phases = base.platform_phases(ctx)
        complete = all(all(row.values()) for row in phases.values())
        comments = [c for c in predicates["granted_comments"]["comments"] if c["result"] == "SUCCEEDED"]
        failing = []
        if not complete:
            failing.append(f"platform phases {phases}")
        if not ctx.lane_ok("PLATFORM_CARRY"):
            failing.append("PLATFORM_CARRY")
        if len(comments) < 4:
            failing.append(f"confirmed granted comments {len(comments)}")
        if failing or violated:
            return _refuse(failing, violated, "not held")
        totals = predicates["request_ceilings"]["totals"]
        return "VERIFIED_LOCAL", ("BEFORE, DURING and AFTER Jira, GitHub and All-22 reads exist, the AFTER ones bound to "
                                  "the candidate head; the private Jira successor ran dry run, apply, strict and audit "
                                  "validators and a second dry run in every phase; "
                                  f"{len(comments)} granted BAT-706/BAT-708 material comments were posted with "
                                  "deterministic markers, duplicate checks and readback; requests stayed within each "
                                  "ceiling ("
                                  + ", ".join(f"{lane} {row['requests']}/{row['ceiling']}" for lane, row in totals.items())
                                  + ").")
    problems = accounting_problems(ctx) + base.classification_problems(ctx)
    storage = ctx.storage()
    failing = problems[:3]
    for lane in ("PLATFORM_CARRY", "LOCAL_INTEGRATION_CANDIDATE", "FINAL_PACKET"):
        if not ctx.lane_ok(lane):
            failing.append(lane)
    if not storage["frozen_and_verified"]:
        failing.append("storage frozen and chained")
    if failing or violated:
        return _refuse(failing, violated, "not held")
    fragments = sum(len(((ctx.receipts[lane].get("write_and_network_scope") or {}).get("guard_log_fragments") or []))
                    for lane in WORKER_LANES if lane in ctx.receipts and ctx.at_head(lane))
    return "VERIFIED_LOCAL", (f"All {len(ctx.contract['carryforward'])} carryforward identities keep their meanings and "
                              "dispositions; 20 clauses, 15 lanes, 18 outputs, findings and effects are accounted in a "
                              "generated report, checklist and submission read from the same records; the process "
                              "predicates are computed from the evidence and none is violated; the forward-only "
                              "candidate carries committed-blob provenance and consumer proof; the root storage ledger "
                              "is frozen with every reservation reconciled and the final outputs reserved on its one "
                              f"claimed continuation; FINAL_PACKET passes (accounting only). Guard-log limitation kept: "
                              f"{fragments} torn guard-log line(s) across the final lanes are fragments, and no "
                              "exhaustive zero-write claim is made from the log. Nothing is claimed about adoption, "
                              "integration or acceptance.")


def judge(ctx: Context, key: str, requirement: str) -> tuple[str, str]:
    _JUDGING.update(ctx=ctx, key=key)
    try:
        return {"R37A11-01": _judge_r01, "R37A11-02": _judge_r02, "R37A11-03": _judge_r03, "R37A11-04": _judge_r04,
                "R37A11-05": _judge_r05}[requirement](ctx, key)
    finally:
        _JUDGING.clear()


def deviation_only(ctx: Context, key: str) -> bool:
    """FAIL only because the evidence violates a process predicate, with every local check of the clause met: the
    deviation already happened and no further local run undoes it (it is the manager's to weigh, not local work)."""

    meta = ctx.criterion_meta.get(key) or {}
    return bool(meta.get("violated")) and not meta.get("local")


def criterion_evidence(ctx: Context, requirement: str) -> list[str]:
    ids: list[str] = []
    for lane in REQUIREMENT_LANES[requirement]:
        if ctx.executed(lane):
            ids += [f"E-LANE-{lane}-RECEIPT", f"E-LANE-{lane}-LOG"]
    storage = ["E-STORAGE-SNAPSHOT", "E-STORAGE-LEDGER", "E-STORAGE-LEDGER-HEAD", "E-STORAGE-CONTINUATION-CLAIM"]
    oracle = [e for e in ctx.evidence if e.startswith("E-ORACLE-")]
    commits = [e for e in ctx.evidence if e.startswith("E-GIT-COMMIT_")]
    findings = [e for e in ctx.evidence if e.startswith("E-FINDING-")]
    extra = {"R37A11-01": ["E-BEFORE-REPRODUCTION", "E-INTAKE", *oracle, "E-LANE-SOURCE_REGRESSIONS-RECEIPT", *commits],
             "R37A11-02": ["E-INTAKE", "E-OUTPUTS-PREFLIGHT", *storage, *commits]
             + [e for e in ctx.evidence if e.startswith("E-FINAL-")],
             "R37A11-03": ["E-CANDIDATE-APPEND-RECORD", "E-OUTPUT-LOCAL_INTEGRATION_CANDIDATE.json",
                           "E-OUTPUT-CONTROL07_PROPOSAL_VALIDATION.json", "E-OUTPUT-CONTROL07_PROPOSAL.md",
                           "E-CONTROL07-PATCH", "E-CONTROL07-OFFLINE-MATRIX", "E-GIT-HOUSEKEEPING-PREFLIGHT",
                           "E-GIT-HELPER-CONSTRUCTION"]
             + [e for e in ctx.evidence if e.startswith(("E-CONTROL07-PROPOSED-", "E-CANDIDATE-APPEND-RECORD-"))],
             "R37A11-04": ["E-OUTPUT-CAREER_POPULATION_DISPOSITIONS.json", "E-OUTPUT-DELIVERED_CONSUMER_MANIFEST.json",
                           "E-FAILURE-CLASSIFICATION", *oracle],
             "R37A11-05": ["E-ORIGINAL-OBLIGATIONS", "E-FAILURE-CLASSIFICATION", "E-REQUEST-LEDGER", "E-INTAKE",
                           "E-CLOSURE-ROWS", "E-GIT-HOUSEKEEPING-PREFLIGHT", "E-GIT-HELPER-CONSTRUCTION",
                           "E-OUTPUTS-PREFLIGHT", *commits, "E-OUTPUT-LANE_RESULTS.json", "E-CANDIDATE-APPEND-RECORD",
                           "E-OUTPUT-LOCAL_INTEGRATION_CANDIDATE.json", "E-STORAGE-SNAPSHOT", "E-NEW-FINDINGS",
                           *findings]}[requirement]
    return [identity for identity in dict.fromkeys(ids + extra) if identity in ctx.evidence]


def criterion_results(ctx: Context) -> list[dict[str, Any]]:
    results = []
    findings = new_findings(ctx)
    for key, criterion in ctx.criteria.items():
        if criterion["executor"] != "worker":
            results.append({"id": key, "status": "PENDING_MANAGER", "evidence_ids": [],
                            "reason": "Manager-owned independent review; the worker cannot self-accept."})
            continue
        verdict, reason = judge(ctx, key, criterion["requirement"])
        evidence = criterion_evidence(ctx, criterion["requirement"])
        if key.endswith("-B") and criterion["requirement"] == "R37A11-05":
            evidence += sorted(identity for identity in ctx.evidence if identity.startswith("E-PLATFORM-")
                               and identity.split("/")[-1].startswith(("JIRA_COMMENT", "JIRA_PRIVATE",
                                                                       "GITHUB_READ_SUMMARY", "ALL22_READ_SUMMARY",
                                                                       "JIRA_READ_SUMMARY")))
        if verdict == "VERIFIED_LOCAL" and not any(ctx.evidence[e]["kind"] == criterion["evidence_kind"] for e in evidence):
            verdict, reason = "IN_PROGRESS", f"{reason} -- but no evidence of kind {criterion['evidence_kind']} exists"
        linked = [f["id"] for f in findings if key in (f.get("criterion_ids") or [])]
        if linked:
            reason = f"{reason} (findings recorded against this criterion, which do not decide it: {', '.join(linked)})"
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
        rows.append({"id": row["id"], "disposition": row["disposition"], "attempt11_state": state,
                     "evidence_ids": [e for e in dict.fromkeys(evidence) if e in ctx.evidence or e.startswith("E-OUTPUT-")]})
    return rows


def new_findings(ctx: Context) -> list[dict[str, Any]]:
    return a6o.new_findings(ctx)


def unfinished_items(ctx: Context, criteria: list[dict[str, Any]], lanes: list[dict[str, Any]],
                     findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = a6o.unfinished_items(ctx, criteria, lanes, findings)
    for item in list(items):
        if item["id"] == "U-LOCAL-CRITERIA":
            item["criterion_ids"] = [k for k in item["criterion_ids"] if not deviation_only(ctx, k)]
            if not item["criterion_ids"]:
                items.remove(item)
    status = {c["id"]: c["status"] for c in criteria}
    unmet = [f for f in findings if f.get("disposition") == "FIXED_LOCAL"
             and any(status.get(k) not in ("VERIFIED_LOCAL", "PENDING_MANAGER") for k in f.get("criterion_ids") or [])]
    if unmet:
        items.append({"id": "U-FIXED-LOCAL-WITH-UNMET-CLAUSES", "kind": "LOCAL_VALIDATION",
                      "criterion_ids": sorted({k for f in unmet for k in f.get("criterion_ids") or []
                                               if status.get(k) not in ("VERIFIED_LOCAL", "PENDING_MANAGER")}),
                      "lane_ids": sorted({lane for f in unmet for lane in f.get("lane_ids") or []}),
                      "finding_ids": [f["id"] for f in unmet], "owner": "BAS worker",
                      "next_action": "; ".join(f"{f['id']}: {f['next_action']}" for f in unmet)[:1800],
                      "alternatives_and_reason": ("A finding marked FIXED_LOCAL does not meet the original clauses it "
                                                  "names; those clauses stay unmet until their own evidence holds."),
                      "evidence_ids": ["E-NEW-FINDINGS"] if "E-NEW-FINDINGS" in ctx.evidence
                      else ["E-ORIGINAL-OBLIGATIONS"]})
    failed = [c for c in criteria if c["status"] == "FAIL"]
    if failed:
        # A clause failed only by a recorded deviation is listed here alone; one with unmet local checks stays in
        # U-LOCAL-CRITERIA too.
        items.append({"id": "U-PROCESS-DEVIATIONS", "kind": "INDEPENDENT_REVIEW",
                      "criterion_ids": [c["id"] for c in failed], "lane_ids": [], "finding_ids": [],
                      "owner": "Independent BAS manager",
                      "next_action": "; ".join(f"{c['id']}: {c['reason']}" for c in failed)[:1800],
                      "alternatives_and_reason": ("A process deviation read from the evidence cannot be undone by "
                                                  "another run; it is recorded, its criterion stays FAIL, and the "
                                                  "manager decides its weight."),
                      "evidence_ids": ["E-ORIGINAL-OBLIGATIONS"]})
    return items


# ------------------------------------------------------------------ declared outputs


def finding_matrix(ctx: Context, label: str, criteria: dict[str, dict[str, Any]]) -> dict[str, Any]:
    before = ctx.out_root / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
    reproduction = read_json(before) if before.is_file() else {}
    plan = {
        "MF37A10-01": ([_f(MANAGER_A10 / "FINDINGS.json"), _f(MANAGER_A10 / "FALSE_RESTRUCTURE_CHALLENGE.json"),
                        _f(MANAGER_A10 / "restructure_challenge.py"), _f(MANAGER_A10 / "lineage_independent.py"),
                        _f(MANAGER_A10 / "INTERVAL_POPULATION_INDEPENDENT.json"), _f(MANAGER_A10_FALSE_RESTRUCTURE),
                        _f(before)],
                       {"CAREER_SUCCESSOR": "independent_cardinality_oracle",
                        "INSTALLED_CONSUMER_C01": "manager_a10_false_restructure_entrypoints",
                        "SOURCE_REGRESSIONS": "attempt11_suite_on_the_unfixed_base"}),
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
            "reproduced_before_repair": reproduction.get("reproduced"),
            "reproduction_subject": {k: (reproduction.get("subject_before") or {}).get(k)
                                     for k in ("head", "clean", "is_issued_base", "installed_equal_to_base")},
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
            "not_claimed": "The repair is local and pending the manager's independent replay; the worker closes no finding."}


def consumer_manifest(ctx: Context, label: str) -> dict[str, Any]:
    manifest = a9o.consumer_manifest(ctx, label)
    installed, career = _d(ctx, "INSTALLED_CONSUMER_C01"), _d(ctx, "CAREER_SUCCESSOR")
    manifest.pop("attempt9_source_unit_verification", None)
    manifest.update({
        "retained_verification": {
            "attempt10_interval_cases_console_script_and_module": _summary(installed.get("a10_interval_cases")),
            "manager_a9_interval_entrypoints": installed.get("manager_a9_interval_entrypoints"),
            "attempt9_missing_witness_forgeries_console_script_and_module": _summary(installed.get("a9_forgeries")),
            "manager_a8_null_span_entrypoints": installed.get("manager_a8_null_span_entrypoints"),
            "attempt8_forgeries_retained": _summary(installed.get("a8_forgeries")),
            "manager_a7_envelope_entrypoints": installed.get("manager_a7_envelope_entrypoints"),
            "attempt7_forgeries_retained": _summary(installed.get("a7_forgeries")),
            "manager_a6_same_page_lineage": installed.get("manager_a6_same_page_lineage")},
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "attempt11_source_interval_verification": {
            "verifier_version": (career.get("source_identity_bindings") or {}).get("verifier_version"),
            "source_interval_checks": career.get("source_interval_checks"),
            "independent_cardinality_oracle": _summary(career.get("independent_cardinality_oracle"), 30000),
            "earlier_oracles_kept": career.get("earlier_oracles_kept"),
            "installed_cases_console_script_and_module": _summary(installed.get("a11_cases"), 30000),
            "manager_a10_false_restructure_entrypoints": installed.get("manager_a10_false_restructure_entrypoints")},
        "delivered_successor_note": ("Attempt 11 delivers no new successor: it serves the Attempt 5 file by its Attempt 5 "
                                     "pointer, unchanged, and repairs the consumer that verifies it."),
    })
    return manifest


def population_document(ctx: Context, label: str) -> dict[str, Any]:
    document = a9o.population_document(ctx, label)
    for stale in ("attempt9_source_unit_relations", "attempt9_row_classes"):
        document.pop(stale, None)
    oracle = _d(ctx, "CAREER_SUCCESSOR").get("independent_cardinality_oracle") or {}
    genuine = oracle.get("genuine_a05") or {}
    receipt = (genuine.get("receipt") or {}).get("path")
    full = read_json(Path(receipt)) if receipt and Path(receipt).is_file() else {}
    document.update({"cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
                     "attempt11_field_classes": genuine.get("field_classes"),
                     "attempt11_relations": genuine.get("relations"),
                     "attempt11_missing_periods": genuine.get("missing_periods"),
                     "attempt11_completeness": genuine.get("completeness"),
                     "attempt11_named_parser_anomalies": genuine.get("named_anomalies"),
                     "attempt11_every_multi_interval_group": full.get("multi_interval_groups") or [],
                     "attempt11_attempt4_format": {k: (oracle.get("genuine_a04") or {}).get(k)
                                                   for k in ("field_classes", "invalid_total", "unresolved_fields",
                                                             "relations", "multi_interval_fields",
                                                             "rows_in_multi_interval_fields")},
                     "attempt11_source_interval_checks": _d(ctx, "CAREER_SUCCESSOR").get("source_interval_checks"),
                     "note": document.get("note", "") + (" Attempt 11 reads every successor row of both relations "
                                                         "again from its source unit, restructured rows included, and "
                                                         "classifies every multi-interval group independently; nothing "
                                                         "was rebuilt.")})
    return document


def candidate_document(ctx: Context, label: str) -> dict[str, Any]:
    document = a9o.candidate_document(ctx, label)
    details = _d(ctx, "LOCAL_INTEGRATION_CANDIDATE")
    control = _control(ctx)
    document.update({
        "requirement": "R37A11-03", "attempt11_start_head": candidate.ISSUED_CANDIDATE_HEAD,
        "attempt10_start_head": candidate.ATTEMPT10_START_HEAD, "attempt9_start_head": candidate.ATTEMPT9_START_HEAD})
    lane = document["lane"]
    for stale in ("attempt9_chain", "attempt9_append_chain"):
        lane.pop(stale, None)
    lane.update({"attempt11_chain": details.get("candidate_attempt11"),
                 "attempt11_append_chain": details.get("candidate_append_chain_attempt11"),
                 **{key: {k: v for k, v in (details.get(key) or {}).items() if k != "literal_adaptations"}
                    for key in ("manager_a10_committed_tree", "manager_a9_committed_tree")}})
    document["control07_proposal"]["retention"] = control.get("attempt11_retention")
    document["not_done"] = ("No push, remote PR, merge, retarget, closure, deletion, reset, history rewrite or activation; "
                            "the preserved first candidate, bb5253b2, 0c22af20, c52e7b52, 514d74dc and cf992e4b stay "
                            "reachable and every other ref kept its commit.")
    return document


def final_packet_document(ctx: Context, label: str) -> dict[str, Any]:
    document = a9o.final_packet_document(ctx, label)
    document["process_predicates"] = process_predicates(ctx)
    return document


def platform_reconciliation(ctx: Context, label: str) -> dict[str, Any]:
    document = a7o.platform_reconciliation(ctx, label)
    document["label_note"] = document["label_note"].replace("Attempt 7", "Attempt 11")
    return document


def cost_ledger(ctx: Context, label: str) -> dict[str, Any]:
    document = a7o.cost_ledger(ctx, label)
    predicates = process_predicates(ctx)
    document["storage_windows"] = predicates["storage_windows"]
    document["receipt_windows"] = predicates["receipt_windows"]
    return document


def effects(ctx: Context) -> list[dict[str, Any]]:
    return a6o.effects(ctx)


def integration_packet(ctx: Context, label: str, lanes: list[dict[str, Any]]) -> str:
    text = a7o.integration_packet(ctx, label, lanes)
    control = _control(ctx)
    return text + "\n".join([
        "### Attempt 11: the qualified proposal retained and rebound (not redesigned, not adopted)", "",
        f"Retention holds: {_retained(control)} -- the proposed bytes identical to the Attempt 10, 9, 8 and 7 bytes, "
        "the regenerated patch identical to the qualified patch `fab1911e...`, the Attempt 10 proposal document and "
        "validation receipt, the Attempt 10 manager's review and integration decision and the control-change protocol "
        "each the issued bytes, and the retained checker and workflow the bytes the managers' independent case review "
        "qualified. The receipt names the final candidate it was run at. The concrete decision subject stays the "
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
                item["attempt11_state"] = states[row["id"]]["attempt11_state"]
                item["attempt11_evidence_ids"] = [e for e in states[row["id"]]["evidence_ids"]
                                                  if e != "E-ORIGINAL-OBLIGATIONS"]
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
        "runner": "tools/cycle37/attempt11_lanes.py", "runs_index": str(root / "lanes" / "RUNS.jsonl"),
        "runs_index_rule": "append-only lane index, named by path; never sealed as evidence (every lane run appends)",
        "lanes": lanes, **_lane_lists(ctx)}))
    ctx.add("E-OUTPUT-LANE_RESULTS.json", root / "LANE_RESULTS.json", CENSUS,
            "Every required lane's result at the candidate head; the 22 original and the Attempt 3 to 10 lanes")
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
    open_assigned = any(f["disposition"] == "OPEN_ASSIGNED" for f in findings)
    complete = all(c["status"] == "VERIFIED_LOCAL" for c in worker) and not open_assigned
    complete_with_deviations = (not complete and not open_assigned and all(
        c["status"] == "VERIFIED_LOCAL" or (c["status"] == "FAIL" and deviation_only(ctx, c["id"])) for c in worker))
    software = ("FAIL" if any(row["status"] == "FAIL" for row in lanes) else
                "PASS" if all(row["status"] == "PASS" for row in lanes) else
                "NOT_RUN" if not any(row["executed"] or row["status"] == "PASS" for row in lanes) else "PARTIAL")
    installed = _d(ctx, "INSTALLED_CONSUMER_C01")
    career = _d(ctx, "CAREER_SUCCESSOR")
    census = career.get("independent_identity_census") or {}
    oracle = (career.get("independent_cardinality_oracle") or {}).get("genuine_a05") or {}
    if ctx.lane_ok("INSTALLED_CONSUMER_C01") and ctx.lane_ok("CAREER_SUCCESSOR"):
        cases = (installed.get("a11_cases") or {}).get("cases") or {}
        held = sum(1 for v in cases.values() if v.get("holds"))
        data_evidence = (f"DELIVERED_RELEASE_{base.DB_SHA256[:12]}_UNCHANGED; A5_SUCCESSOR_"
                         f"{str(ctx.pointer.get('successor_sha256'))[:12]}_ROWS_{census.get('rows')}_SERVED_UNCHANGED; "
                         f"RAW_CAPTURES_{census.get('raw_files')}_IDENTITY_MISMATCHES_0; MULTI_INTERVAL_GROUPS_"
                         f"{oracle.get('multi_interval_fields')}_ROWS_{oracle.get('rows_in_multi_interval_fields')}; "
                         f"ORACLE_INVALID_{oracle.get('invalid_total')}_NAMED_PARSER_ANOMALIES_"
                         f"{len(oracle.get('named_anomalies') or [])}; A11_CASES_HELD_{held}_OF_{len(cases)}; "
                         "REAL_ELIGIBLE_FORECASTS_0; REAL_PROVEN_PIT_0; NOT_ACTIVATED")
    else:
        data_evidence = "INCOMPLETE"
    submission = {
        "schema_version": "BAS-SUBMISSION-2.4", "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "cycle_id": CYCLE_ID, "attempt_id": ATTEMPT_ID, "display_label": label,
        "contract_sha256": ctx.contract_sha256, "headline": headline, "candidate": ctx.candidate,
        "writer_released": writer_released, "safe_local_work_remaining": headline == "IN_PROGRESS_LOCAL_WORK_REMAINS",
        "dimensions": {"implementation": ("COMPLETE_LOCAL" if complete else
                                          "COMPLETE_LOCAL_WITH_RECORDED_PROCESS_DEVIATIONS" if complete_with_deviations
                                          else "IN_PROGRESS"),
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
    ctx.process_predicates = process_predicates(ctx)
    import attempt11_report  # the narrative report, beside this tool  # noqa: PLC0415

    write_output(root / "WORKER_REPORT.md", attempt11_report.render(ctx, submission))
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
            problems.append("FINDING_CLOSURE_MATRIX does not cover exactly MF37A10-01")
        for row in rows:
            if not row["commits"]:
                problems.append(f"{row['finding']} names no commit")
    control = _control(ctx)
    if control and (control.get("cycle_number"), control.get("attempt_number")) != (CYCLE_NUMBER, ATTEMPT_NUMBER):
        problems.append("CONTROL07_PROPOSAL_VALIDATION.json does not carry Cycle 37 / Attempt 11")
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
            problems.append("submission.json does not carry Cycle 37 / Attempt 11")
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
        statuses = {row["id"]: row["status"] for row in submission.get("criteria") or []}
        for name, keys in PREDICATE_CRITERIA.items():
            if name in _violated_names(ctx):
                for key in keys:
                    if statuses.get(key) == "VERIFIED_LOCAL":
                        problems.append(f"{key} is VERIFIED_LOCAL although the evidence violates {name}")
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


def _violated_names(ctx: Context) -> list[str]:
    predicates = process_predicates(ctx)
    return [name for name in PREDICATE_CRITERIA if predicates[name]["holds"] is False
            and not (name == "git_command_scope" and not predicates[name]["records"])]


def main(argv: list[str] | None = None) -> int:
    rebind()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=("classify", "inventory", "build", "check", "seal", "audit"))
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--out-root", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--headline", default="IN_PROGRESS_LOCAL_WORK_REMAINS", choices=base.HEADLINES)
    parser.add_argument("--writer-released", action="store_true")
    parser.add_argument("--final-packet", action="store_true")
    args = parser.parse_args(argv)
    if args.mode == "audit":
        print(json.dumps(window_audit(args.ledger), indent=2, ensure_ascii=False))
        return 0
    if not (args.contract and args.out_root):
        parser.error("--contract and --out-root are required")
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
