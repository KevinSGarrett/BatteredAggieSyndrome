"""R36-14: a row-level discrepancy report between the private Jira mirror and
the live board.

R36-14's acceptance names a "live/private-mirror discrepancy report". Cycle
#36's first pass recorded the mirror as PRIVATE_MIRROR_PRESENT with
convergence NOT_CERTIFIED and wrote the comparison down as the next
deliverable. That was a deferral, not a blocker: the mirror is one file on
disk and the manager's live readback of all 742 issues is another, so the
comparison needs no credential, no network and no money.

The mirror is the Cycle #30 private delta. It records, for fourteen issues,
the status each carried when that delta was written, plus the comment id
Cycle #30 created on each. It is a point-in-time record, not a replica, so
the honest question is not "do the two agree" -- a status that moved between
Cycle #30 and now is the board working correctly -- but "for each mirrored
row, does the live board still show what the mirror asserts, and where it
does not, is the difference explained by a transition this project already
records?"

So each row gets one of four states rather than a pass or a fail:

  AGREES                          the live status equals the mirrored status.
  MOVED_FORWARD_AS_RECORDED       the status changed and the destination is a
                                  status this project's own hold semantics
                                  expect for that issue.
  MOVED_ON_OUTSIDE_BAS_SEMANTICS  the status changed on a board whose
                                  workflow this project does not govern. The
                                  mirror is stale for that row; nothing is
                                  contradicted.
  DIVERGES_FROM_A_RECORDED_STATE  the status changed away from a state this
                                  project explicitly records. This is the
                                  finding the report exists to produce.
  NOT_PRESENT_ON_THE_LIVE_BOARD   the mirrored key is absent from the
                                  readback.

The distinction between the middle two matters. A first version had only one
"diverges" bucket and put three CFIP rows in it, because BAS records no
expectation for the CFIP worker workflow -- WORKER_RUNNING to PM_REVIEW is
that board making ordinary progress after Cycle #30. Reporting it as an
unexplained divergence would have dressed a stale mirror row up as an
anomaly, and the whole point of this report is to stop doing that.

Counting agreements would have been the easy artifact and a false one: the
mirror's own header says mirror_parity is
UNSUPPORTED_NOT_CLAIMED_FROM_COUNTS, and this tool does not reintroduce from
statuses the parity claim that file refuses to make from counts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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

MIRROR_ROOT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\JIRA_PRIVATE")
MANAGER_RUN = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle35\20260921T131038Z"
)
LIVE_INVENTORY = MANAGER_RUN / "JIRA_LIVE_INVENTORY.json"

REPORT_VERSION = "BAS-JIRA-MIRROR-DISCREPANCY-v36.1"

AGREES = "AGREES"
MOVED = "MOVED_FORWARD_AS_RECORDED"
MOVED_OUTSIDE = "MOVED_ON_OUTSIDE_BAS_SEMANTICS"
DIVERGES = "DIVERGES_FROM_A_RECORDED_STATE"
ABSENT = "NOT_PRESENT_ON_THE_LIVE_BOARD"

#: Issues whose status this project actually records an expectation for. A
#: move away from one of these is a finding. Every other key belongs to a
#: workflow BAS does not govern.
BAS_GOVERNED_KEYS = frozenset({"BAT-523", "BAT-401", "BAT-429"})

#: Statuses this project's own hold semantics expect, per issue. These are
#: not a guess about Jira workflow: they are the states the Cycle #36 pack
#: and the preservation ledger already require to hold, so a move INTO one of
#: them is recorded rather than reported as a divergence. Anything else is a
#: divergence even when it looks benign.
EXPECTED_DESTINATIONS = {
    "BAT-523": {"In Progress"},
    "BAT-401": {"Done"},
    "BAT-429": {"To Do"},
    # A Cycle #30 "In Review" issue that has since been accepted is the
    # ordinary path for this board; nothing else is.
    "_DEFAULT_FROM_IN_REVIEW": {"Done", "In Review"},
    "_DEFAULT_FROM_TO_DO": {"To Do", "In Progress", "In Review", "Done"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def load_live_statuses(path: Path) -> tuple[dict[str, str], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    statuses: dict[str, str] = {}
    for page in payload.get("pages") or []:
        for issue in page.get("issues") or []:
            fields = issue.get("fields") or {}
            status = (fields.get("status") or {}).get("name")
            if issue.get("key") and status:
                statuses[str(issue["key"])] = str(status)
    return statuses, {
        "path": str(path),
        "sha256": digest(path),
        "observed_at": payload.get("observed_at"),
        "host": payload.get("host"),
        "issues_read": len(statuses),
    }


def classify(key: str, mirrored: str, live: str | None) -> tuple[str, str]:
    if live is None:
        return ABSENT, "The mirrored key does not appear in the live readback."
    if live == mirrored:
        return AGREES, "The live board still shows the mirrored status."
    expected = EXPECTED_DESTINATIONS.get(key)
    if expected is None:
        expected = EXPECTED_DESTINATIONS.get(
            "_DEFAULT_FROM_" + mirrored.upper().replace(" ", "_"), set()
        )
    if live in expected:
        return (
            MOVED,
            f"Moved from {mirrored!r} to {live!r}, which is a destination this "
            "project's own hold semantics expect for it.",
        )
    if key in BAS_GOVERNED_KEYS:
        return (
            DIVERGES,
            f"Moved from {mirrored!r} to {live!r}. This project records an "
            "explicit expected state for this issue and the live board does "
            "not show it.",
        )
    return (
        MOVED_OUTSIDE,
        f"Moved from {mirrored!r} to {live!r} on a workflow this project does "
        "not govern. The mirrored row is stale; no recorded expectation is "
        "contradicted, and this is not a certification that the move was "
        "correct.",
    )


def build(out_dir: Path) -> dict[str, Any]:
    mirror_files = sorted(MIRROR_ROOT.glob("*.json")) if MIRROR_ROOT.is_dir() else []
    live_statuses, live_meta = (
        load_live_statuses(LIVE_INVENTORY)
        if LIVE_INVENTORY.is_file()
        else ({}, {"path": str(LIVE_INVENTORY), "sha256": None})
    )

    rows: list[dict[str, Any]] = []
    mirror_records: list[dict[str, Any]] = []
    for path in mirror_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        snapshot = payload.get("live_status_snapshot") or {}
        comments = payload.get("comments") or {}
        mirror_records.append(
            {
                "path": str(path),
                "sha256": digest(path),
                "artifact_type": payload.get("artifact_type"),
                "mirror_parity_claim": payload.get("mirror_parity"),
                "rows_in_snapshot": len(snapshot),
                "comment_ids_recorded": len(comments),
                "skipped_keys": payload.get("skipped") or [],
                "operator_hold": payload.get("operator_hold"),
            }
        )
        for key in sorted(snapshot):
            mirrored = str(snapshot[key])
            live = live_statuses.get(key)
            state, reason = classify(key, mirrored, live)
            rows.append(
                {
                    "issue_key": key,
                    "mirror_file": path.name,
                    "mirrored_status": mirrored,
                    "live_status": live,
                    "state": state,
                    "reason": reason,
                    "comment_id_recorded_by_the_mirror": comments.get(key),
                    "comment_existence_verified": False,
                }
            )

    states = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1

    artifact = {
        "artifact_type": "CYCLE36_JIRA_MIRROR_DISCREPANCY",
        "report_version": REPORT_VERSION,
        "generated_at_utc": utc_now(),
        "mirror_root": str(MIRROR_ROOT),
        "mirror_files": mirror_records,
        "mirror_file_count": len(mirror_records),
        "live_readback": live_meta,
        "rows": rows,
        "row_count": len(rows),
        "states": states,
        "divergences_from_a_recorded_state": [
            row for row in rows if row["state"] == DIVERGES
        ],
        "stale_rows_outside_bas_semantics": [
            {
                "issue_key": row["issue_key"],
                "mirrored_status": row["mirrored_status"],
                "live_status": row["live_status"],
            }
            for row in rows
            if row["state"] == MOVED_OUTSIDE
        ],
        "keys_absent_from_the_live_board": [
            row["issue_key"] for row in rows if row["state"] == ABSENT
        ],
        "mirrored_keys_are_a_subset_not_a_replica": (
            f"The mirror records {len(rows)} issues. The live board carries "
            f"{live_meta.get('issues_read')}. The mirror was never a replica "
            "of the board, so the rows it does not contain are outside this "
            "comparison and are not counted as agreement."
        ),
        "parity_is_still_not_claimed": (
            "The mirror file's own header says mirror_parity is "
            "UNSUPPORTED_NOT_CLAIMED_FROM_COUNTS. This report compares the "
            "rows the mirror actually asserts and claims nothing about the "
            "rows it does not."
        ),
        "comment_ids_not_verified": (
            "The mirror records a comment id per issue. Confirming that each "
            "still exists needs a Jira read this cycle did not perform, so "
            "every row carries comment_existence_verified false rather than "
            "an assumed true."
        ),
        "convergence_state": (
            "NO_ROW_DIVERGES_FROM_A_STATE_THIS_PROJECT_RECORDS"
            if not states.get(DIVERGES) and not states.get(ABSENT)
            else "DIVERGENCES_PRESENT"
        ),
        # The governed set, not a claim that all three were compared: only
        # the keys the mirror actually asserts appear in rows, and this
        # mirror asserts one of them.
        "bas_governed_keys": sorted(BAS_GOVERNED_KEYS),
        "bas_governed_keys_present_in_the_mirror": sorted(
            {row["issue_key"] for row in rows} & BAS_GOVERNED_KEYS
        ),
        "what_this_is_not": (
            "Not a certification that the private mirror and the live board "
            "are in sync. It is a row-level comparison of the fourteen issues "
            "the mirror asserts, with the reason for every difference."
        ),
        "no_jira_write_performed": True,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out_dir / "CYCLE36_JIRA_MIRROR_DISCREPANCY.json", 
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    artifact = build(args.out_dir)
    print(
        json.dumps(
            {
                key: artifact[key]
                for key in (
                    "mirror_file_count",
                    "row_count",
                    "states",
                    "stale_rows_outside_bas_semantics",
                    "keys_absent_from_the_live_board",
                    "convergence_state",
                    "no_jira_write_performed",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
