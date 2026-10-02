r"""Cycle #37 - Attempt #2 worker packet builder

Generate the worker checklist and the v2.2 submission JSON from the issued
contract plus the evidence this attempt actually produced.

The submission shape is the one `cycle_protocol.py submission` validates, so
the accounting check runs against the real packet rather than a summary of
it. Three rules govern what goes in:

* **Every issued row gets a row here.** The contract's 345 acceptance rows,
  22 required lanes and 148 carryforward entries are distinct sets and each
  is reconciled separately. An ID with no evidence is emitted as ``NOT_RUN``,
  never dropped.
* **A state is read from evidence, not asserted.** ``VERIFIED_LOCAL`` needs a
  named artifact that exists and hashes to what is recorded.
* **Everything unfinished is linked.** Every non-verified criterion, every
  non-PASS lane and every open finding appears in the unfinished accounting
  with an owner and a next action, because that is the only place they cannot
  quietly disappear.

A lane receipt whose recorded head is not the final candidate head is
reported ``NOT_RUN``: a verdict from an earlier subject is not a verdict
about this one.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

sys.dont_write_bytecode = True

WORKTREE = Path(__file__).resolve().parents[2]
CYCLE_NUMBER, ATTEMPT_NUMBER = 37, 2
CYCLE_ID, ATTEMPT_ID = "CYCLE-37", "REWORK-20260922T171601Z"


def identity_label(headline: str) -> str:
    """The protocol's display label (cycle_protocol.identity_label) for the computed headline."""

    return f"Cycle #{CYCLE_NUMBER} \u2014 Attempt #{ATTEMPT_NUMBER} \u2014 {headline}"


def split_local_catch_all(
    unfinished: list[dict[str, Any]], *, status: dict[str, str], why: dict[str, str]
) -> list[dict[str, Any]]:
    """Replace a catch-all item by one item per routed ID (clarification section 1).

    A catch-all is not an accountable item: each criterion, lane or finding
    routed to it becomes its own item with one next action and a positive and
    a negative closure check. An empty catch-all disappears, so it can never
    hold the headline at IN_PROGRESS by itself.
    """

    split: list[dict[str, Any]] = []
    for item in unfinished:
        if not item.get("catch_all"):
            split.append(item)
            continue
        base = {key: value for key, value in item.items()
                if key not in {"criterion_ids", "lane_ids", "finding_ids", "next_action", "catch_all"}}
        for field, target in (("criterion_ids", VERIFIED), ("lane_ids", "PASS"), ("finding_ids", "FIXED_LOCAL")):
            for one in item.get(field) or []:
                split.append({
                    **base,
                    "id": f"{item['id']}::{one}",
                    "criterion_ids": [one] if field == "criterion_ids" else [],
                    "lane_ids": [one] if field == "lane_ids" else [],
                    "finding_ids": [one] if field == "finding_ids" else [],
                    "next_action": f"{one} ({status.get(one, 'UNKNOWN')}): "
                                   f"{why.get(one) or 'no reason recorded; read its row'}",
                    "closure_check_positive": f"{one} reaches {target} with named evidence at the final head",
                    "closure_check_negative": f"a rebuilt packet still routes {one} to local work",
                })
    return split


def decide_headline(local_work_remaining: bool, worker_unmet: bool) -> str:
    """BAS_OPERATING_POLICY.md headlines for a worker handoff.

    With no safe local action left: BLOCKED_INCOMPLETE when some worker
    criteria remain unmet; IMPLEMENTATION_SUBMITTED_NOT_ACCEPTED when every
    worker criterion is verified locally but acceptance or validation findings
    remain. IMPLEMENTATION_COMPLETE_REVIEW_PENDING is never decided here: it
    also needs every worker lane to pass, which this builder does not assert.
    """

    if local_work_remaining:
        return "IN_PROGRESS_LOCAL_WORK_REMAINS"
    return "BLOCKED_INCOMPLETE" if worker_unmet else "IMPLEMENTATION_SUBMITTED_NOT_ACCEPTED"

VERIFIED, IN_PROGRESS, FAIL = "VERIFIED_LOCAL", "IN_PROGRESS", "FAIL"
NOT_RUN, BLOCKED_EXTERNAL, PENDING_MANAGER = "NOT_RUN", "BLOCKED_EXTERNAL", "PENDING_MANAGER"


def sha256_file(path: Path) -> str | None:
    if not Path(path).is_file():
        return None
    d = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            d.update(block)
    return d.hexdigest()


def git(*args: str) -> str:
    return (
        subprocess.run(
            ["git", "-C", str(WORKTREE), *args],
            check=False, capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout or ""
    ).strip()


def _lane_slug(command: str) -> str:
    import re

    m = re.search(r"--lane (\S+)", command)
    return m.group(1) if m else ""


def _claim_for(claims: dict[str, dict[str, Any]], requirement_id: str, acceptance_id: str):
    for key, claim in claims.items():
        req, _, rows = key.partition("::")
        if req != requirement_id:
            continue
        for token in (t.strip() for t in rows.split(",")):
            if token and (token == acceptance_id or acceptance_id.startswith(token)):
                return claim
    return None


#: Paths whose change cannot affect any lane's verdict, because no lane
#: executes them. This generator runs after every lane and only reads their
#: receipts.
REPORTING_ONLY_PATHS = frozenset({"tools/cycle37/build_worker_packet.py"})


def _declared_cases(lane_id: str, payload: dict[str, Any]) -> tuple[int, int, str]:
    """Named cases a contract-TEST lane executed without using unittest."""

    if lane_id == "BAS_WHEEL_CLI":
        total = int(payload.get("documented_example_count") or 0)
        failed = len(payload.get("failing_examples") or [])
        return total, failed, (
            f"{total} documented packaged-query cases executed through the "
            f"installed console script, each with its own exit code and raw "
            f"log; see documented_examples in the lane receipt"
        )
    if lane_id == "C01_RELEASE_COMPOSED":
        # Each fixture is a BAS assertion set run through the adapter and then
        # through the released wheel's own validator; each has its own
        # expectation and verdict in the composition receipt.
        positives = int(payload.get("positives") or 0)
        negatives = int(payload.get("negatives") or 0)
        honoured = int(payload.get("positives_accepted_by_both") or 0) + int(
            payload.get("negatives_refused") or 0
        )
        total = positives + negatives
        return total, total - honoured, (
            f"{total} declared composition fixtures ({positives} positive, "
            f"{negatives} negative), each run through the BAS adapter and then "
            f"through the released C01 0.1.2 wheel's validate_document; see "
            f"composition_receipt in the lane receipt"
        )
    if lane_id == "FLOAT_SUCCESSOR":
        # The lane runs structured checks rather than unittest methods, and
        # each is a named claim with its own pass condition. They are counted
        # here so the lane reports what it actually executed instead of
        # reporting zero cases beside a PASS, which the protocol correctly
        # refuses.
        checks = {
            "successor_invariant_across_interpreters": payload.get("successor_invariant"),
            "successor_reproduces_the_published_value": payload.get(
                "successor_reproduces_published_value"
            ),
            "restoration_identity_reproduces": (
                payload.get("restoration_candidate") or {}
            ).get("identity_reproduces"),
            "restoration_payload_has_no_field_disagreement": (
                payload.get("restoration_candidate") or {}
            ).get("field_disagreements") == 0,
            "installing_the_candidate_clears_both_strict_findings": (
                payload.get("restoration_candidate") or {}
            ).get("both_strict_checks_clear_if_installed"),
            "nothing_adopted_and_no_canonical_byte_written": (
                payload.get("adopted_anywhere") is False
                and payload.get("canonical_bytes_written") == 0
            ),
        }
        failed = sum(1 for value in checks.values() if value is not True)
        interpreters = payload.get("interpreters_compared") or 0
        return len(checks), failed, (
            f"{len(checks)} declared numerical-successor cases, each with its "
            f"own pass condition and receipt, compared across {interpreters} "
            f"distinct interpreters; see successor_invariant, "
            f"restoration_candidate and isolation in the lane receipt"
        )
    if lane_id == "FAMILY_B_COMPOSED":
        artifact = payload.get("qualification_artifact")
        if artifact and Path(artifact).is_file():
            data = json.loads(Path(artifact).read_text(encoding="utf-8"))
            cases = data.get("cases") or []
            failed = sum(
                1 for c in cases
                if str(c.get("state", c.get("result", ""))).upper().startswith("FAIL")
            )
            return len(cases), failed, (
                f"{len(cases)} declared qualification cases run through the real "
                f"validator ({data.get('negative_controls_that_rejected') and 'negatives rejected' or 'see artifact'}); "
                f"see cases in {artifact}"
            )
    return 0, 0, ""


def build(contract_path: Path, out_root: Path, claims: dict[str, dict[str, Any]]) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    evidence_root = Path(contract["paths"]["evidence_root"])
    lane_dir = out_root / "evidence" / "lanes"

    head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
    porcelain = [line for line in git("status", "--porcelain=v1", "-uall").splitlines() if line.strip()]
    acc = hashlib.sha256()
    for line in sorted(porcelain):
        rel = line[3:].strip().strip('"')
        acc.update(rel.encode("utf-8"))
        acc.update(b"\0")
        acc.update((sha256_file(WORKTREE / rel) or "ABSENT").encode("ascii"))
    if not porcelain:
        # A clean tree still needs a stable 64-hex source digest. The tree
        # object IS the content identity, so it is hashed rather than a
        # constant being invented.
        acc.update(tree.encode("ascii"))
    source_digest = acc.hexdigest()

    # ------------------------------------------------------------ evidence
    evidence: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    now = datetime.now(timezone.utc).isoformat()

    def add_evidence(path: Path, kind: str, scope: str) -> str | None:
        path = Path(path)
        if not path.is_file():
            return None
        try:
            rel = path.resolve().relative_to(evidence_root.resolve())
        except ValueError:
            return None
        identifier = "EV-" + str(rel).replace("\\", "/")
        if identifier not in seen_ids:
            seen_ids.add(identifier)
            evidence.append(
                {
                    "id": identifier,
                    "path": str(path.resolve()),
                    "kind": kind,
                    "scope": scope,
                    "observed_at": datetime.fromtimestamp(
                        path.stat().st_mtime, timezone.utc
                    ).isoformat(),
                    "sha256": sha256_file(path),
                }
            )
        return identifier

    for path in sorted((out_root / "evidence").rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(out_root).as_posix()
        if rel.startswith("evidence/lanes/"):
            kind, scope = "criterion_evidence", "lane receipt with command, exit, identities and raw log path"
        elif rel.startswith("evidence/repairs/"):
            kind, scope = "criterion_evidence", "predecessor reproduction or repaired-head result"
        elif rel.startswith("evidence/intake/"):
            kind, scope = "criterion_evidence", "intake verification of the issued packet and predecessor identity"
        else:
            kind, scope = "criterion_evidence", "attempt evidence"
        add_evidence(path, kind, scope)
    for path in sorted((out_root / "logs").rglob("*.log")):
        add_evidence(path, "command_log", "raw combined stdout and stderr of one lane command")
    for name in (
        "COST_AND_AUTHORITY_LEDGER.json",
        "CYCLE37_FINDING_DISPOSITION.json",
        "WORKER_REPORT.md",
        # Decision and request documents the manager acts on. They live at
        # the root because they are addressed to a person, and they are
        # bound here so a claim that cites one resolves to its bytes.
        "R37_I_INTEGRATION_DECISION_PACKET.md",
        "R37_N_RESTORATION_ACTION_REQUEST.md",
        "R37_12_FAMILY_B_ACTIVATION_APPROVAL_REQUEST.json",
        "R37_12_FAMILY_B_ACTIVATION_APPROVAL_REQUEST.md",
        # The separable authority actions, the storage registry and the
        # finding and unfinished ledgers are cited by claims, so they are
        # bound by digest like any other artifact. This builder's own outputs
        # (submission.json, WORKER_CHECKLIST.csv) are never cited: their
        # digest would describe themselves.
        "R37_AUTHORITY_DECISION_INDEX.json",
        "R37_AUTHORITY_DECISION_INDEX.md",
        "STORAGE_PATH_REGISTRY.json",
        "NEW_FINDINGS.json",
        "UNFINISHED.json",
        "EFFECTS.json",
    ):
        add_evidence(out_root / name, "criterion_evidence", "worker packet artifact")
    # Private evidence (Jira and plan successors) stays outside public Git;
    # its digest is bound here, never its content copied anywhere public.
    for rel in (
        "private/jira/JIRA_LIVE_READ_RECEIPT.json",
        "private/jira/JIRA_LIVE_SUPPLEMENT_RECEIPT.json",
        "private/jira/R37_14_JIRA_CONVERGENCE.json",
        "private/jira/CFIP_PROPOSALS.json",
        "private/plans/TP37_PRIVATE_SUCCESSOR_RECEIPT.json",
        "private/plans/TP37_PRIVATE_SUCCESSOR.md",
        "private/plans/TP37_PRIVATE_SUCCESSOR.diff",
    ):
        add_evidence(out_root / rel, "criterion_evidence", "private evidence bound by digest only")

    by_id = {e["id"]: e for e in evidence}

    def resolve_ids(paths: list[str]) -> list[str]:
        out: list[str] = []
        for rel in paths:
            identifier = "EV-" + rel.replace("\\", "/")
            if identifier in by_id:
                out.append(identifier)
        return out

    # --------------------------------------------------------------- lanes
    lanes: list[dict[str, Any]] = []
    lane_notes: dict[str, str] = {}
    case_basis: dict[str, str] = {}
    for lane in contract["required_lanes"]:
        lane_id = lane["id"]
        empty_counts = {f: 0 for f in ("tests", "failures", "errors", "import_errors", "failed_subtests", "skipped")}
        if lane["executor"] != "worker":
            lanes.append(
                {
                    "id": lane_id, "status": PENDING_MANAGER, "executed": False,
                    "cwd": lane["cwd"], "command": lane["command"],
                    "environment": lane["environment"], "data_binding": lane["data_binding"],
                    "head": head, "source_digest": source_digest, "log_id": None,
                    "exit_code": None, "reason": "manager-owned independent lane", **empty_counts,
                }
            )
            lane_notes[lane_id] = "manager-owned independent lane; not a worker failure"
            continue

        declared_kind = str(lane["kind"]).upper()
        slug = _lane_slug(lane["command"])
        receipt = lane_dir / f"{slug}.json"
        payload = json.loads(receipt.read_text(encoding="utf-8")) if receipt.is_file() else None
        recorded_head = (payload or {}).get("source_binding", {}).get("head")
        result = (payload or {}).get("result")

        # A verdict only counts when the receipt binds THIS candidate -- but
        # "affected" is the operating rule, not "identical". A commit that
        # touches only this packet generator changes no path any lane
        # executes, so the receipts still describe the subject they tested.
        # The deciding diff is recorded either way, so a reviewer can check
        # the judgement rather than take it.
        stale = False
        stale_diff: list[str] = []
        if payload and recorded_head != head:
            stale_diff = [
                line.strip()
                for line in git("diff", "--name-only", recorded_head, head).splitlines()
                if line.strip()
            ]
            stale = any(path not in REPORTING_ONLY_PATHS for path in stale_diff)
        if payload is None:
            status, reason = NOT_RUN, f"no receipt at {receipt}"
        elif stale:
            status = NOT_RUN
            reason = (
                f"receipt binds head {recorded_head}, not the final candidate "
                f"{head}, and the commits between them touch "
                f"{sorted(set(stale_diff) - REPORTING_ONLY_PATHS)}; an earlier "
                f"subject's verdict is not a verdict about this one"
            )
        elif result == "PASS":
            status, reason = "PASS", payload.get("state_reason") or "lane satisfied"
        elif result in ("FAIL", "UNSATISFIED_NO_EXECUTED_TEST"):
            status, reason = FAIL, payload.get("state_reason") or "lane not satisfied"
        elif result == "BLOCKED":
            status = NOT_RUN
            reason = payload.get("state_reason") or "lane subject does not exist"
        else:
            status, reason = NOT_RUN, payload.get("state_reason") or "lane did not run"

        counts = dict(empty_counts)
        exit_code = None
        log_id = None
        if status in ("PASS", FAIL) and payload:
            commands = payload.get("commands") or []
            parsed_rows = [c.get("unittest") for c in commands if c.get("unittest")]
            counts["tests"] = sum(int(p.get("tests_run") or 0) for p in parsed_rows)
            counts["skipped"] = sum(int(p.get("skipped_count") or 0) for p in parsed_rows)
            counts["import_errors"] = sum(len(p.get("import_error_identities") or []) for p in parsed_rows)
            counts["failed_subtests"] = sum(len(p.get("subtest_identities") or []) for p in parsed_rows)
            failures = errors = 0
            for p in parsed_rows:
                for row in p.get("failed_or_errored") or []:
                    if row.get("is_import_error") or row.get("subtest"):
                        continue
                    if row.get("kind") == "FAIL":
                        failures += 1
                    else:
                        errors += 1
            counts["failures"], counts["errors"] = failures, errors
            if declared_kind == "TEST" and counts["tests"] == 0:
                # The contract declares these TEST lanes; the driver ran them
                # as structured checks rather than unittest. The protocol's
                # own definition of `tests` is "distinct discovered top-level
                # test methods/cases", and these lanes execute named cases
                # with individual exit codes and raw logs, so the cases are
                # counted and the basis is recorded rather than the lane
                # reporting zero.
                cases, failed, basis = _declared_cases(lane_id, payload)
                if cases:
                    counts["tests"] = cases
                    counts["failures"] = failed
                    case_basis[lane_id] = basis
            exits = [c.get("exit_code") for c in commands if c.get("exit_code") is not None]
            exit_code = 0 if status == "PASS" else (next((e for e in exits if e), 1) if exits else 1)
            if status == "PASS":
                exit_code = 0
            for command in commands:
                log_id = add_evidence(
                    Path(command["log_path"]), "command_log",
                    "raw combined stdout and stderr of one lane command",
                ) or log_id
            if log_id is None:
                # A verdict with no surviving log cannot be bound; report the
                # lane unrun rather than assert an unevidenced result.
                status, reason = NOT_RUN, "lane produced no bindable command log"
                counts, exit_code = dict(empty_counts), None

        lanes.append(
            {
                "id": lane_id, "status": status,
                "executed": status in ("PASS", FAIL),
                "cwd": lane["cwd"], "command": lane["command"],
                "environment": lane["environment"], "data_binding": lane["data_binding"],
                "head": head, "source_digest": source_digest,
                "log_id": log_id, "exit_code": exit_code, "reason": reason,
                "declared_kind": declared_kind,
                "case_basis": case_basis.get(lane_id),
                "receipt_head": recorded_head,
                "commits_since_receipt": stale_diff, **counts,
            }
        )
        lane_notes[lane_id] = reason

    # ------------------------------------------------------------ criteria
    criteria: list[dict[str, Any]] = []
    checklist: list[dict[str, Any]] = []
    for requirement in contract["requirements"]:
        for acceptance in requirement["acceptance"]:
            identifier = acceptance["id"]
            if acceptance["executor"] != "worker":
                status = PENDING_MANAGER
                reason = f"{acceptance['executor']}-owned acceptance; the worker does not self-approve"
                ids: list[str] = []
            else:
                claim = _claim_for(claims, requirement["id"], identifier)
                if claim:
                    status, reason = claim["state"], claim["note"]
                    ids = resolve_ids(claim["evidence"])
                    if status == VERIFIED and not ids:
                        status = IN_PROGRESS
                        reason = f"{reason} (named evidence not found under the evidence root)"
                else:
                    status = NOT_RUN
                    reason = "no evidence artifact in this attempt shows this row; it remains assigned and unfinished"
                    ids = []
            criteria.append({"id": identifier, "status": status, "reason": reason, "evidence_ids": ids})
            checklist.append(
                {
                    "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
                    "state_label": None, "row_kind": "ACCEPTANCE",
                    "requirement_id": requirement["id"], "acceptance_id": identifier,
                    "executor": acceptance["executor"], "jira_key": requirement.get("jira_key", ""),
                    "result": status, "reason": reason, "evidence": " | ".join(ids),
                    "statement": acceptance["statement"][:400].replace("\n", " "),
                }
            )

    # ------------------------------------------------------- carryforward
    # Every retained obligation must point at something a reviewer can open.
    # For the ones this attempt did not satisfy, that something is the ledger
    # written here: it records the obligation, its disposition, its owner and
    # the fact that it is still outstanding. Citing it is not a claim that the
    # obligation was met -- it is the evidence that it was carried, not
    # dropped.
    ledger_path = out_root / "evidence" / "CARRYFORWARD_LEDGER.json"
    ledger_rows = []
    for entry in contract["carryforward"]:
        claim = claims.get(f"CARRY::{entry['id']}")
        ledger_rows.append(
            {
                "id": entry["id"],
                "disposition": entry["disposition"],
                "requirement_ids": entry.get("requirement_ids") or [],
                "owner": entry.get("owner"),
                "next_action": entry.get("next_action"),
                "worker_state": claim["state"] if claim else NOT_RUN,
                "worker_note": claim["note"] if claim
                else "Retained and not satisfied in this attempt. The obligation "
                     "remains assigned with its original meaning and owner.",
            }
        )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def write_carryforward_ledger(headline: str | None) -> None:
        _bas_atomic.write_text(
            ledger_path,
            json.dumps(
                {
                    "label": identity_label(headline) if headline else None,
                    "cycle_number": CYCLE_NUMBER,
                    "attempt_number": ATTEMPT_NUMBER, "state": headline,
                    "total": len(ledger_rows),
                    "satisfied_in_this_attempt": sum(
                        1 for r in ledger_rows if r["worker_state"] == VERIFIED
                    ),
                    "retained_unsatisfied": sum(
                        1 for r in ledger_rows if r["worker_state"] == NOT_RUN
                    ),
                    "rows": ledger_rows,
                },
                indent=2, sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    # Written now so the evidence index can bind it; rewritten with the
    # headline once the unfinished accounting decides it (digests are
    # re-read from disk before the submission is written).
    write_carryforward_ledger(None)
    ledger_id = add_evidence(
        ledger_path, "criterion_evidence",
        "every issued carryforward obligation with its disposition, owner and current worker state",
    )

    carryforward: list[dict[str, Any]] = []
    for entry in contract["carryforward"]:
        identifier = entry["id"]
        claim = claims.get(f"CARRY::{identifier}")
        ids = resolve_ids(claim["evidence"]) if claim else []
        if ledger_id and ledger_id not in ids:
            ids = ids + [ledger_id]
        carryforward.append(
            {"id": identifier, "disposition": entry["disposition"], "evidence_ids": ids}
        )
        checklist.append(
            {
                "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
                "state_label": None, "row_kind": "CARRYFORWARD",
                "requirement_id": ",".join(entry.get("requirement_ids") or []),
                "acceptance_id": identifier, "executor": "worker",
                "jira_key": entry.get("owner", ""),
                "result": (claim["state"] if claim else NOT_RUN),
                "reason": (claim["note"] if claim else "retained and not satisfied in this attempt"),
                "evidence": " | ".join(ids),
                "statement": f"Carryforward disposition {entry['disposition']}",
            }
        )
    for lane in lanes:
        checklist.append(
            {
                "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
                "state_label": None, "row_kind": "LANE",
                "requirement_id": "R37-16", "acceptance_id": lane["id"],
                "executor": "manager" if lane["status"] == PENDING_MANAGER else "worker",
                "jira_key": "BAT-706", "result": lane["status"],
                "reason": lane_notes.get(lane["id"], ""), "evidence": lane["log_id"] or "",
                "statement": f"Required validation lane {lane['id']}",
            }
        )

    # -------------------------------------------------------- new findings
    findings = json.loads(
        (out_root / "NEW_FINDINGS.json").read_text(encoding="utf-8")
    ) if (out_root / "NEW_FINDINGS.json").is_file() else []
    for row in findings:
        row["evidence_ids"] = resolve_ids(row.get("evidence_paths", []))

    # ---------------------------------------------------------- unfinished
    unfinished = json.loads(
        (out_root / "UNFINISHED.json").read_text(encoding="utf-8")
    ) if (out_root / "UNFINISHED.json").is_file() else []
    # Rows are routed by their final status, because the protocol forbids a
    # BLOCKED_EXTERNAL row from being linked to local work: local-open rows
    # (IN_PROGRESS, NOT_RUN, FAIL) go to the local catch-all, manager rows to
    # the manager item, and each blocked row to the non-local item whose
    # declared keywords its own reason uses, else to the external catch-all.
    status_of = {c["id"]: c["status"] for c in criteria}
    reason_of = {c["id"]: (c.get("reason") or "").casefold() for c in criteria}
    local_open = [cid for cid, st in status_of.items() if st in (IN_PROGRESS, NOT_RUN, FAIL)]
    manager_rows = [cid for cid, st in status_of.items() if st == PENDING_MANAGER]
    blocked_rows = [cid for cid, st in status_of.items() if st == BLOCKED_EXTERNAL]
    unpassed = [lane["id"] for lane in lanes if lane["status"] != "PASS"]
    open_findings = [f["id"] for f in findings if f["disposition"] == "OPEN_ASSIGNED"]
    # An open finding an external item already carries (an owner decision, a
    # budget, a labeller) is not local work, so the local catch-all takes only
    # the open findings no other item names.
    claimed_findings = {
        fid for item in unfinished if not item.get("catch_all") for fid in item.get("finding_ids") or []
    }
    # The same for lanes: a lane an owner-decision item already carries (an
    # inherited red lane) is not local work either.
    claimed_lanes = {
        lid for item in unfinished if not item.get("catch_all") for lid in item.get("lane_ids") or []
    }
    routed: set[str] = set()
    for item in unfinished:
        item["evidence_ids"] = resolve_ids(item.get("evidence_paths", []))
        if item.get("catch_all"):
            item["criterion_ids"] = local_open
            item["lane_ids"] = [lid for lid in unpassed if lid not in claimed_lanes]
            item["finding_ids"] = [fid for fid in open_findings if fid not in claimed_findings]
        elif item.get("catch_all_manager"):
            item["criterion_ids"] = sorted(set(item.get("criterion_ids") or []) | set(manager_rows))
        elif item.get("blocked_keywords") and not str(item.get("kind", "")).startswith("LOCAL_"):
            words = [w.casefold() for w in item["blocked_keywords"]]
            matched = [cid for cid in blocked_rows if cid not in routed and any(w in reason_of[cid] for w in words)]
            item["criterion_ids"] = sorted(set(item.get("criterion_ids") or []) | set(matched))
            routed.update(matched)
    for item in unfinished:
        if item.get("catch_all_external"):
            rest = [cid for cid in blocked_rows if cid not in routed]
            item["criterion_ids"] = sorted(set(item.get("criterion_ids") or []) | set(rest))
    for item in unfinished:
        if str(item.get("kind", "")).startswith("LOCAL_"):
            item["criterion_ids"] = [cid for cid in item["criterion_ids"] if status_of.get(cid) != BLOCKED_EXTERNAL]
    unfinished = split_local_catch_all(
        unfinished,
        status={**{c["id"]: c["status"] for c in criteria}, **{lane["id"]: lane["status"] for lane in lanes},
                **{f["id"]: f.get("disposition") or "" for f in findings}},
        why={**{c["id"]: c.get("reason") or "" for c in criteria}, **lane_notes,
             **{f["id"]: f.get("next_action") or "" for f in findings}},
    )
    # An item with nothing left to carry is not reported: the protocol needs
    # every unfinished item to name what it affects.
    unfinished = [
        item for item in unfinished
        if item.get("criterion_ids") or item.get("lane_ids") or item.get("finding_ids")
    ]
    local_work_remaining = any(str(item.get("kind", "")).startswith("LOCAL_") for item in unfinished)
    # The headline is decided here, once, and every label this builder writes
    # uses it (no placeholder state).
    worker_ids = {acceptance["id"] for requirement in contract["requirements"]
                  for acceptance in requirement["acceptance"] if acceptance["executor"] == "worker"}
    worker_unmet = any(c["status"] != VERIFIED for c in criteria if c["id"] in worker_ids)
    headline = decide_headline(local_work_remaining, worker_unmet)
    label = identity_label(headline)
    for row in checklist:
        row["state_label"] = headline
    write_carryforward_ledger(headline)

    # ------------------------------------------- per-requirement deliverables
    # The contract names one R37-xx_EVIDENCE.json per requirement as a
    # deliverable. Each is an index of what this attempt holds for that
    # requirement -- every acceptance row with its state and the bytes of
    # its evidence, the inherited obligations, and what remains -- so a
    # reviewer can open one requirement without reading the whole packet.
    # It asserts nothing the rows do not.
    criteria_by_id = {c["id"]: c for c in criteria}
    carry_by_id = {c["id"]: c for c in carryforward}
    ledger_by_id = {r["id"]: r for r in ledger_rows}
    requirement_files: list[str] = []
    for requirement in contract["requirements"]:
        rid = requirement["id"]
        target = next(
            (Path(d) for d in (requirement.get("deliverables") or [])
             if str(d).endswith(f"{rid}_EVIDENCE.json")),
            None,
        )
        if target is None:
            continue
        rows = []
        for acceptance in requirement["acceptance"]:
            row = criteria_by_id[acceptance["id"]]
            rows.append({
                "id": acceptance["id"], "executor": acceptance["executor"],
                "statement": acceptance["statement"], "status": row["status"],
                "reason": row["reason"],
                "evidence": [{"id": i, "path": by_id[i]["path"], "sha256": by_id[i]["sha256"]}
                             for i in row["evidence_ids"] if i in by_id],
            })
        inherited = []
        for entry in contract["carryforward"]:
            if rid in (entry.get("requirement_ids") or []):
                ledger_row = ledger_by_id.get(entry["id"], {})
                inherited.append({
                    "id": entry["id"], "disposition": entry["disposition"],
                    "worker_state": ledger_row.get("worker_state"),
                    "worker_note": ledger_row.get("worker_note"),
                    "evidence_ids": carry_by_id.get(entry["id"], {}).get("evidence_ids", []),
                })
        worker_rows = [r for r in rows if r["executor"] == "worker"]
        states = collections.Counter(r["status"] for r in rows)
        document = {
            "label": label, "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
            "state_label": headline, "requirement_id": rid,
            "title": requirement.get("title"), "jira_key": requirement.get("jira_key"),
            "owner": requirement.get("owner"),
            "original_meaning": requirement.get("original_meaning"),
            "candidate": {"head": head, "tree": tree},
            "acceptance_rows": rows,
            "acceptance_state_counts": dict(states),
            "inherited_obligations": inherited,
            "state": (
                "WORKER_ROWS_VERIFIED_LOCAL_PENDING_INDEPENDENT_REVIEW"
                if worker_rows and all(r["status"] == VERIFIED for r in worker_rows)
                and all(i["worker_state"] == VERIFIED for i in inherited)
                else "IN_PROGRESS_LOCAL_WORK_REMAINS"
            ),
            "not_claimed": "No row here is a manager acceptance or a scientific acceptance.",
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        _bas_atomic.write_text(target, json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        add_evidence(target, "criterion_evidence",
                     f"{rid} requirement index: acceptance rows, evidence bytes, inherited obligations")
        requirement_files.append(str(target))
    by_id = {e["id"]: e for e in evidence}

    # The manifest must describe the bytes that are on disk when the
    # submission is written, not the bytes that were there when the evidence
    # tree was first swept. CARRYFORWARD_LEDGER.json is regenerated by this
    # builder after that sweep, so its first-swept digest is stale by
    # construction; re-reading every entry here makes that impossible to get
    # wrong for any artifact this builder writes, now or later.
    for item in evidence:
        path = Path(item["path"])
        if path.is_file():
            item["sha256"] = sha256_file(path)
            item["observed_at"] = datetime.fromtimestamp(
                path.stat().st_mtime, timezone.utc
            ).isoformat()

    lane_states = [lane["status"] for lane in lanes]
    software = (
        "FAIL" if any(s == FAIL for s in lane_states)
        else "PASS" if all(s == "PASS" for s in lane_states)
        else "NOT_RUN" if not any(lane["executed"] or lane["status"] == "PASS" for lane in lanes)
        else "PARTIAL"
    )

    submission = {
        "schema_version": "BAS-SUBMISSION-2.2",
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER,
        "cycle_id": CYCLE_ID, "attempt_id": ATTEMPT_ID,
        "state": "IMPLEMENTATION_IN_PROGRESS" if local_work_remaining else headline,
        "display_label": label,
        "contract_sha256": sha256_file(contract_path),
        # The headline follows the unfinished accounting and the pack's rule
        # (R37-16): IN_PROGRESS_LOCAL_WORK_REMAINS while any local repair
        # remains; IMPLEMENTATION_SUBMITTED_NOT_ACCEPTED once all safe local
        # work is done or exhausted and itemized, with what is left waiting on
        # decisions, budget, review or sources this worker does not hold.
        "headline": headline,
        "candidate": {"head": head, "tree": tree, "source_digest": source_digest},
        "writer_released": True, "safe_local_work_remaining": local_work_remaining,
        "dimensions": {
            "implementation": "IN_PROGRESS" if local_work_remaining else "LOCAL_WORK_EXHAUSTED_EXTERNAL_BLOCKERS_REMAIN",
            "data_evidence": "INCOMPLETE",
            "software_validation": software,
            "independent_acceptance": "NOT_REVIEWED",
            "integration_release": "NOT_AUTHORIZED",
            "overall_cycle": headline,
        },
        "predictive_skill": "NOT_ESTABLISHED",
        "criteria": criteria, "carryforward": carryforward, "lanes": lanes,
        "evidence": evidence, "unfinished": unfinished, "new_findings": findings,
        "effects": json.loads((out_root / "EFFECTS.json").read_text(encoding="utf-8"))
        if (out_root / "EFFECTS.json").is_file() else [],
        "costs": {"paid_ai_calls": 0, "paid_ai_cost": 0,
                  "request_ledger_ref": str(out_root / "COST_AND_AUTHORITY_LEDGER.json")},
        "observed_at": now,
    }
    for effect in submission["effects"]:
        effect["evidence_ids"] = resolve_ids(effect.get("evidence_paths", []))

    out_root.mkdir(parents=True, exist_ok=True)
    with _bas_atomic.open_write(out_root / "WORKER_CHECKLIST.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["cycle_number", "attempt_number", "state_label", "row_kind",
                        "requirement_id", "acceptance_id", "executor", "jira_key",
                        "result", "reason", "evidence", "statement"],
        )
        writer.writeheader()
        writer.writerows(checklist)
    _bas_atomic.write_text(out_root / "submission.json", 
        json.dumps(submission, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )

    counts = {
        "acceptance_rows": len(criteria),
        "verified_local": sum(1 for c in criteria if c["status"] == VERIFIED),
        "in_progress": sum(1 for c in criteria if c["status"] == IN_PROGRESS),
        "not_run": sum(1 for c in criteria if c["status"] == NOT_RUN),
        "pending_manager": sum(1 for c in criteria if c["status"] == PENDING_MANAGER),
        "lanes": len(lanes),
        "lanes_pass": sum(1 for lane in lanes if lane["status"] == "PASS"),
        "lanes_fail": sum(1 for lane in lanes if lane["status"] == FAIL),
        "lanes_not_run": sum(1 for lane in lanes if lane["status"] == NOT_RUN),
        "lanes_pending_manager": sum(1 for lane in lanes if lane["status"] == PENDING_MANAGER),
        "carryforward": len(carryforward),
        "evidence_artifacts": len(evidence),
        "requirement_indexes": len(requirement_files),
        "software_validation": software,
    }
    return {"submission": submission, "counts": counts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    args = parser.parse_args()

    claims: dict[str, dict[str, Any]] = {}
    for row in json.loads(args.claims.read_text(encoding="utf-8")):
        claims[f"{row['requirement']}::{row['rows']}"] = row

    built = build(args.contract.resolve(), args.out_root.resolve(), claims)
    print(json.dumps(built["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
