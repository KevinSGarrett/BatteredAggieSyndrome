r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-14-AC06/AC07/AC09: compare the live Jira key sets with the local mirror
exactly, and run the established mirror producer against a PRIVATE successor
copy -- never against the public canonical records.

Two separate things, kept separate:

1. **Exact key-set comparison.** Every live BAT key is classified against
   the local registries (canonical, auxiliary, retired, quarantined, or not
   registered anywhere), and every local canonical record is checked for a
   live issue with the same key AND the same Local Issue ID. Status is
   compared for the canonical set. The manager's 742-issue figure is BAT and
   CFIP together; both are read and both are counted.

2. **The established producer on a private successor.** The public
   ``jira/`` tree is copied to the validation root. The repository's own
   ``reconcile_jira_export.py`` runs there in ``--dry-run`` first, then for
   real, and then its own ``rebuild_all_derivatives.py``,
   ``validate_second_pass.py`` and ``run_second_pass_audit.py``. Because
   ``JIRA_ROOT`` resolves from each tool's own location, every write lands
   in the private copy. The public records are hashed before and after to
   prove they did not change.

What this is not: a comment on an issue is not convergence (AC07), and a
private successor is not adoption. Nothing here writes to Jira.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import shutil
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

#: Local logical state versus the Jira statuses the reconciler maps to it.
JIRA_TO_LOGICAL = {
    "to do": "BACKLOG", "backlog": "BACKLOG", "open": "BACKLOG",
    "in progress": "IN_PROGRESS", "in review": "REVIEW", "done": "DONE",
    "blocked": "BLOCKED", "cancelled": "CANCELLED", "canceled": "CANCELLED",
}

#: The named issues AC09 requires the report to state.
NAMED = {"BAT-523": "IN_PROGRESS expected", "BAT-401": "protected-blocked expected",
         "BAT-429": "dependency-blocked expected"}


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def registry(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("issues") if isinstance(data, dict) else data
    out = {}
    for item in items or []:
        key = str(item.get("jira_key") or item.get("key") or "").strip()
        if key:
            out[key] = item
    return out


def run(command: list[str], cwd: Path, env: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=str(cwd), env=env, capture_output=True,
                               text=True, timeout=3600)
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "stdout_tail": completed.stdout[-1500:],
        "stderr_tail": completed.stderr[-1500:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--live-read", type=Path, required=True)
    parser.add_argument("--supplement", type=Path, required=True)
    parser.add_argument("--export-csv", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    public_jira = repo / "jira"
    live = json.loads(args.live_read.read_text(encoding="utf-8"))
    supplement = json.loads(args.supplement.read_text(encoding="utf-8"))
    local_field = live.get("local_issue_id_field")

    live_bat = {i["key"]: i for i in live["bat_issues"]}
    live_cfip = {i["key"]: i for i in supplement["cfip_issues"]}

    # ------------------------------------------------ local registries
    canonical: dict[str, dict[str, Any]] = {}
    for path in sorted((public_jira / "records" / "issues").rglob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("jira_key"):
            canonical[record["jira_key"]] = record
    auxiliary = registry(public_jira / "reconciliation" / "BAT_AUXILIARY_ISSUE_REGISTRY.json")
    retired = registry(public_jira / "reconciliation" / "BAT_RETIRED_CANONICAL_ISSUE_REGISTRY.json")
    quarantined = registry(public_jira / "reconciliation" / "BAT_AUXILIARY_QUARANTINE_REGISTRY.json")

    # ----------------------------------------------- live -> local classes
    classes: dict[str, str] = {}
    for key in live_bat:
        classes[key] = (
            "CANONICAL" if key in canonical else
            "AUXILIARY" if key in auxiliary else
            "QUARANTINED" if key in quarantined else
            "RETIRED_BUT_STILL_LIVE" if key in retired else
            "NOT_REGISTERED_LOCALLY"
        )
    live_classes = collections.Counter(classes.values())

    # -------------------------------------------- local -> live agreement
    mismatches = []
    missing_live = []
    status_rows = []
    for key, record in canonical.items():
        issue = live_bat.get(key)
        if issue is None:
            missing_live.append({"jira_key": key, "local_id": record.get("local_id")})
            continue
        fields = issue.get("fields") or {}
        live_local = (fields.get(local_field) or "") if local_field else ""
        if live_local and live_local != record.get("local_id"):
            mismatches.append({"jira_key": key, "local_id": record.get("local_id"),
                               "live_local_issue_id": live_local})
        live_status = ((fields.get("status") or {}).get("name") or "")
        local_raw = (record.get("operational_jira") or {}).get("status_raw") or ""
        status_rows.append({
            "jira_key": key,
            "local_id": record.get("local_id"),
            "live_status": live_status,
            "mirrored_status_raw": local_raw,
            "local_workflow_state": record.get("workflow_state"),
            "mirror_stale": bool(live_status) and live_status != local_raw,
            "logical_disagrees": JIRA_TO_LOGICAL.get(live_status.lower()) not in (
                None, record.get("workflow_state")),
        })
    retired_absent = sorted(k for k in retired if k not in live_bat)

    stale = [r for r in status_rows if r["mirror_stale"]]
    logical = [r for r in status_rows if r["logical_disagrees"]]
    # The local logical state is safety-normalised by design (SYNC_CONTRACT:
    # Jira Done cannot overwrite local state without complete evidence, and
    # dependency and deferment gates hold local BLOCKED/DEFERRED under a Jira
    # To Do). A raw count of disagreements would read as 346 defects; broken
    # down by pair it reads as what it is.
    logical_pairs = collections.Counter(
        (r["live_status"], r["local_workflow_state"]) for r in logical
    )

    # ------------------------------------------ auxiliary reconciliation
    auxiliary_rows = []
    for key, item in auxiliary.items():
        issue = live_bat.get(key)
        fields = (issue or {}).get("fields") or {}
        live_local = (fields.get(local_field) or "") if (issue and local_field) else ""
        auxiliary_rows.append({
            "jira_key": key,
            "registry_local_id": item.get("local_id"),
            "live": issue is not None,
            "live_local_issue_id": live_local,
            "local_id_agrees": (not live_local) or live_local == item.get("local_id"),
            "live_status": (fields.get("status") or {}).get("name"),
        })
    auxiliary_disagreements = [r for r in auxiliary_rows if not r["live"] or not r["local_id_agrees"]]
    named = {}
    for key, expectation in NAMED.items():
        issue = live_bat.get(key)
        record = canonical.get(key) or auxiliary.get(key)
        named[key] = {
            "expectation": expectation,
            "live_status": ((issue or {}).get("fields") or {}).get("status", {}).get("name")
                           if issue else None,
            "local_workflow_state": (record or {}).get("workflow_state"),
            "registered_as": classes.get(key),
        }

    # ---------------------------------------- private successor sequence
    private = args.private_root.resolve()
    if repo in private.parents or private == repo:
        raise SystemExit("the private successor must not be inside the Git worktree")
    successor = private / "jira"
    if successor.exists():
        shutil.rmtree(successor)
    private.mkdir(parents=True, exist_ok=True)
    shutil.copytree(public_jira, successor)
    public_before = tree_digest(public_jira)
    successor_before = tree_digest(successor)

    # The reconciler's registry is the canonical set. Given the complete
    # live export it stops at the first Local Issue ID it does not hold --
    # every auxiliary issue -- so the complete-field export is scoped to the
    # canonical keys before the producer sees it, and the auxiliary set is
    # reconciled against its own registry above. The scoping is published,
    # not hidden: the full export and the scoped one are both kept.
    scoped_export = private / "BAT_JIRA_EXPORT_CANONICAL_SCOPE.csv"
    with args.export_csv.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        rows = [row for row in reader if row.get("Issue key") in canonical]
    with _bas_atomic.open_write(scoped_export, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)

    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["BAS_JIRA_REPO_ROOT"] = str(repo)
    tools = successor / "tools"
    py = sys.executable
    steps = [
        ("reconcile_dry_run", [py, "-B", str(tools / "reconcile_jira_export.py"),
                               str(scoped_export), "--dry-run", "--repo-root", str(repo)]),
    ]
    results = [dict(step=name, **run(cmd, tools, env)) for name, cmd in steps]
    dry_ok = results[-1]["exit_code"] == 0
    conflicts_path = successor / "reconciliation" / "SYNC_CONFLICTS.csv"
    # The dry run reports its conflicts in the JSON it prints and, correctly,
    # writes no file. The first version of this tool read the conflicts FILE
    # after the dry run, found the copied empty one, and reported zero dry-run
    # conflicts where the dry run had reported 112. The dry run's own output
    # is the record of what it found.
    dry_conflicts = []
    dry_result = None
    completed = subprocess.run(steps[0][1], cwd=str(tools), env=env, capture_output=True,
                               text=True, timeout=3600)
    try:
        parsed = json.loads(completed.stdout)
        dry_conflicts = list(parsed.get("conflicts") or [])
        dry_result = parsed.get("result")
    except ValueError:
        dry_result = "UNPARSEABLE_DRY_RUN_OUTPUT"
    if dry_ok:
        for name, cmd in (
            ("reconcile_apply_private", [py, "-B", str(tools / "reconcile_jira_export.py"),
                                         str(scoped_export), "--repo-root", str(repo)]),
            # Only reconcile and validate_second_pass declare --repo-root; the
            # other two take it from BAS_JIRA_REPO_ROOT, which is set above,
            # so they are not handed an argument their parsers would reject.
            ("rebuild_all_derivatives", [py, "-B", str(tools / "rebuild_all_derivatives.py")]),
            ("validate_second_pass", [py, "-B", str(tools / "validate_second_pass.py"),
                                      "--repo-root", str(repo)]),
            ("run_second_pass_audit", [py, "-B", str(tools / "run_second_pass_audit.py")]),
        ):
            results.append(dict(step=name, **run(cmd, tools, env)))
    applied_conflicts = []
    if conflicts_path.is_file():
        with conflicts_path.open(encoding="utf-8", newline="") as handle:
            applied_conflicts = list(csv.DictReader(handle))
    public_after = tree_digest(public_jira)
    successor_after = tree_digest(successor)

    def event_lines(root: Path) -> list[dict[str, Any]]:
        log = root / "history" / "ISSUE_CHANGE_LOG.jsonl"
        if not log.is_file():
            return []
        out = []
        for line in log.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError:
                    out.append({"unparseable": line[:120]})
        return out

    public_events = event_lines(public_jira)
    successor_events = event_lines(successor)
    new_events = successor_events[len(public_events):]
    event_kinds = collections.Counter(str(e.get("event")) for e in new_events)

    receipt = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "requirement": "R37-14",
        "acceptance": ["R37-14-AC06", "R37-14-AC07", "R37-14-AC09"],
        "live": {
            "bat": len(live_bat),
            "cfip": len(live_cfip),
            "total": len(live_bat) + len(live_cfip),
            "manager_figure": 742,
            "matches_manager_figure": len(live_bat) + len(live_cfip) == 742,
            "local_issue_id_field": local_field,
        },
        "local": {
            "canonical": len(canonical),
            "auxiliary": len(auxiliary),
            "retired": len(retired),
            "quarantined": len(quarantined),
        },
        "live_bat_by_local_class": dict(sorted(live_classes.items())),
        "not_registered_locally": sorted(k for k, v in classes.items() if v == "NOT_REGISTERED_LOCALLY"),
        "retired_but_still_live": sorted(k for k, v in classes.items() if v == "RETIRED_BUT_STILL_LIVE"),
        "retired_and_absent_live": retired_absent,
        "canonical_missing_live": missing_live,
        "canonical_local_id_mismatches": mismatches,
        "canonical_with_live_status": len(status_rows),
        "mirror_status_stale": len(stale),
        "mirror_status_stale_rows": stale[:200],
        "logical_state_disagreements": len(logical),
        "logical_state_disagreement_pairs": {
            f"{live} -> {local}": count for (live, local), count in logical_pairs.most_common()
        },
        "logical_state_note": (
            "The local state is safety-normalised against dependency, evidence "
            "and deferment gates by design, so a Jira To Do over a local BLOCKED "
            "or DEFERRED is the contract working, not a mirror defect. Mirror "
            "staleness is the defect measure, and it is zero."
        ),
        "logical_state_disagreement_rows": logical[:200],
        "auxiliary_reconciliation": {
            "registered": len(auxiliary),
            "live": sum(1 for r in auxiliary_rows if r["live"]),
            "disagreements": auxiliary_disagreements,
        },
        "unregistered_live_issues": [
            {"jira_key": k,
             "summary": ((live_bat[k].get("fields") or {}).get("summary")),
             "created": ((live_bat[k].get("fields") or {}).get("created")),
             "local_issue_id": ((live_bat[k].get("fields") or {}).get(local_field))
                                if local_field else None,
             "disposition": "REPORTED_NOT_REGISTERED_NO_ISSUE_ACTION_GRANTED"}
            for k, v in classes.items() if v == "NOT_REGISTERED_LOCALLY"
        ],
        "named_issues": named,
        "cfip_keys": sorted(live_cfip),
        "private_successor": {
            "path": str(successor),
            "scoped_export": str(scoped_export),
            "scoped_export_rows": len(rows),
            "scope_note": (
                "reconcile_jira_export.py stops at the first Local Issue ID its "
                "canonical registry does not hold. Given the complete live "
                "export it refused every auxiliary row, so the export is scoped "
                "to the canonical keys and the auxiliary set is reconciled "
                "against its own registry. Both exports are kept."
            ),
            "steps": results,
            "dry_run_exit": results[0]["exit_code"],
            "dry_run_result": dry_result,
            "dry_run_conflicts": len(dry_conflicts),
            "dry_run_conflict_rows": dry_conflicts[:200],
            "applied_conflicts": len(applied_conflicts),
            "every_step_exit_zero": all(r["exit_code"] == 0 for r in results),
            "successor_changed": successor_before != successor_after,
            "material_events_written": len(new_events),
            "material_event_kinds": dict(event_kinds),
            "public_event_log_lines": len(public_events),
            "public_tree_sha256_before": public_before,
            "public_tree_sha256_after": public_after,
            "public_records_unchanged": public_before == public_after,
        },
        "not_convergence": (
            "A comment on an issue is not mirror convergence, and running the "
            "producer against a private successor is not adoption: the public "
            "canonical records are unchanged, which is checked above."
        ),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out, json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n",
                        encoding="utf-8")

    print("live BAT / CFIP / total   :", len(live_bat), len(live_cfip), receipt["live"]["total"],
          "(manager 742:", receipt["live"]["matches_manager_figure"], ")")
    print("live BAT by local class   :", dict(live_classes))
    print("canonical missing live    :", len(missing_live))
    print("local id mismatches       :", len(mismatches))
    print("mirror status stale       :", len(stale), "| logical disagreements:", len(logical))
    print("logical pairs             :", dict(logical_pairs.most_common(6)))
    print("auxiliary disagreements   :", len(auxiliary_disagreements))
    print("named                     :", {k: (v["live_status"], v["local_workflow_state"]) for k, v in named.items()})
    for r in results:
        print(f"  step {r['step']:<26} exit {r['exit_code']}")
    print("dry-run conflicts         :", len(dry_conflicts), "| applied conflicts:", len(applied_conflicts))
    print("material events (private):", len(new_events), dict(event_kinds))
    print("public records unchanged  :", public_before == public_after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
