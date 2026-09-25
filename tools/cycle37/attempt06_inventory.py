r"""Cycle #37 — Attempt #6 — inventory of what this attempt created, for the owner (nothing is removed).

    attempt06_inventory.py --out <new evidence file>

Every directory this attempt created or wrote under its granted roots, with its bytes and files, what it holds, and
whether the owner may remove it after the manager's review. This tool only reads and writes one new file; the
contract grants no cleanup, so nothing is deleted or moved.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

EVIDENCE_ROOT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempt06")
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a06")
PACKAGING_ROOT = Path(r"C:\BatteredAggieSyndrome.packaging\c37a06")
#: What each top-level directory holds, and whether the owner may remove it after the manager's review.
PURPOSE = {
    (VALIDATION_ROOT, "fixtures"): ("Owned forgery fixtures (full successor copies restored before every case), including "
                                    "the stopped FORGERY-SMOKE-02 fixture and its hot rollback journal (W37A06-02) and "
                                    "the manager-probe fixture of the before-repair reproduction", True),
    (VALIDATION_ROOT, "rc"): ("Scratch repositories of the candidate-append rehearsals (borrowing the shared objects "
                              "read-only), each with its checkout and generated view", True),
    (VALIDATION_ROOT, "cv"): ("The granted append's validation view: a byte-for-byte materialization of the appended "
                              "candidate tree in which the canonical generator wrote its provenance; the committed-blob "
                              "proof cites it", False),
    (VALIDATION_ROOT, "cv2"): ("The second granted append's validation view (the outputs-tool repair carried onto "
                               "the candidate); the committed-blob proof cites it", False),
    (VALIDATION_ROOT, "cn"): ("Scratch repositories of the candidate lane's committed-provenance negatives", True),
    (VALIDATION_ROOT, "lanes"): ("Lane work directories (manager-probe replay copies and fixtures)", True),
    (VALIDATION_ROOT, "rehearsal"): ("Rehearsal lane runs (labelled REHEARSAL, never evidence)", True),
    (VALIDATION_ROOT, "jira"): ("Private Jira successor copies (never the committed pack or live Jira)", True),
    (VALIDATION_ROOT, "tmp"): ("Temporary files of the platform tool's children", True),
    (VALIDATION_ROOT, "dev"): ("Development scripts and their outputs (not evidence)", True),
    (PACKAGING_ROOT, "b"): ("Fresh noneditable BAS wheels and installed environments of the installed lane", True),
    (PACKAGING_ROOT, "c"): ("Wheels and environments built from the candidate tree, and its control exports", True),
    (PACKAGING_ROOT, "candidate"): ("The granted append's private index and commit message", False),
    (EVIDENCE_ROOT, "lanes"): ("Lane receipts, logs and census records -- evidence", False),
    (EVIDENCE_ROOT, "evidence"): ("Worker evidence: before-repair reproduction, platform receipts, storage segments and "
                                  "snapshots, candidate append record, final-packet receipts", False),
}


def measure(path: Path) -> dict[str, int]:
    total = files = 0
    for folder, _dirs, names in os.walk(path):
        for name in names:
            try:
                total += (Path(folder) / name).stat().st_size
                files += 1
            except OSError:
                continue
    return {"bytes": total, "files": files}


def inventory() -> dict[str, Any]:
    rows = []
    for root in (EVIDENCE_ROOT, VALIDATION_ROOT, PACKAGING_ROOT):
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if child.is_dir():
                purpose, removable = PURPOSE.get((root, child.name), ("Unclassified; the owner decides", False))
                rows.append({"path": str(child), **measure(child), "holds": purpose,
                             "owner_may_remove_after_manager_review": removable})
            else:
                rows.append({"path": str(child), "bytes": child.stat().st_size, "files": 1,
                             "holds": "Declared worker output or ledger at the attempt root" if root == EVIDENCE_ROOT
                             else "Loose file", "owner_may_remove_after_manager_review": False})
    return {"label": "Cycle #37 \u2014 Attempt #6 \u2014 IN_PROGRESS_LOCAL_WORK_REMAINS (inventory for the owner)",
            "cycle_number": 37, "attempt_number": 6, "observed_at": datetime.now(timezone.utc).isoformat(),
            "roots": [str(r) for r in (EVIDENCE_ROOT, VALIDATION_ROOT, PACKAGING_ROOT)], "entries": rows,
            "total_bytes": sum(r["bytes"] for r in rows),
            "removable_bytes": sum(r["bytes"] for r in rows if r["owner_may_remove_after_manager_review"]),
            "rule": ("Nothing was deleted or moved: the contract grants no cleanup. Removal of the listed scratch is an "
                     "owner action after the manager's review; the evidence root and the append's view and index stay.")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    document = inventory()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"entries": len(document["entries"]), "total_bytes": document["total_bytes"],
                      "removable_bytes": document["removable_bytes"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
