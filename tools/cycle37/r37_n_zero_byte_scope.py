r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-N-AC02: establish how many canonical payloads are actually corrupt.

The restoration request names one zero-byte file. "One" is a claim, and a
restoration scope stated without checking is the same shape of claim MF37-07
objects to. So this walks the content-addressed payload roots and separates
two things an ordinary file listing runs together:

* a file that is empty **and declared empty** -- its manifest records
  ``row_count: 0`` and the SHA-256 of the empty string
  (``e3b0c442...b855``), which is what an honest parser writes when a source
  states nothing in that domain. Twelve of the thirteen empty payload files
  are this, and restoring them would invent rows the source never stated;
* a file that is empty **and declared non-empty** -- its content-addressed
  directory is named for the digest of a payload that cannot be empty. One
  file is this, and it is the inventory the restoration candidate targets.

Read-only. It writes only ``--out``.
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

#: SHA-256 of zero bytes. A manifest entry carrying this digest is declaring
#: that the file is empty, not failing to describe it.
EMPTY_DIGEST = hashlib.sha256(b"").hexdigest()

MANIFEST_NAMES = ("corpus_manifest.json", "manifest.json", "payload_manifest.json")


def declared_entries(directory: Path) -> list[dict[str, Any]]:
    """Every child-payload declaration a sibling manifest makes."""

    found: list[dict[str, Any]] = []
    for name in MANIFEST_NAMES:
        path = directory / name
        if not path.is_file():
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        children = document.get("child_payloads")
        if isinstance(children, dict):
            for key, value in children.items():
                if isinstance(value, dict):
                    found.append({"manifest": name, "key": key, **value})
        elif isinstance(children, list):
            for value in children:
                if isinstance(value, dict):
                    found.append({"manifest": name, **value})
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    scanned = 0
    empty: list[dict[str, Any]] = []
    roots_reported: list[dict[str, Any]] = []
    for root in args.root:
        root = root.resolve()
        if not root.exists():
            roots_reported.append({"root": str(root), "state": "ABSENT"})
            continue
        files = 0
        for path in root.rglob("*"):
            try:
                if not path.is_file():
                    continue
            except OSError:
                continue
            files += 1
            if path.stat().st_size:
                continue
            declarations = [
                entry
                for entry in declared_entries(path.parent)
                if str(entry.get("filename") or entry.get("key")) == path.name
            ]
            declared_empty = any(
                str(entry.get("sha256")) == EMPTY_DIGEST
                or entry.get("row_count") == 0
                for entry in declarations
            )
            empty.append(
                {
                    "path": str(path),
                    "declared_by_a_manifest": bool(declarations),
                    "declared_empty": declared_empty,
                    "declarations": declarations,
                    "verdict": (
                        "INTACT_DECLARED_EMPTY"
                        if declared_empty
                        else "CORRUPT_EMPTY_BUT_NOT_DECLARED_EMPTY"
                    ),
                }
            )
        scanned += files
        roots_reported.append({"root": str(root), "state": "SCANNED", "files": files})

    corrupt = [row for row in empty if row["verdict"].startswith("CORRUPT")]
    intact = [row for row in empty if not row["verdict"].startswith("CORRUPT")]

    receipt = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "requirement": "R37-N",
        "acceptance": ["R37-N-AC02"],
        "question": (
            "how many content-addressed canonical payloads are zero bytes "
            "without a manifest declaring them empty"
        ),
        "empty_digest": EMPTY_DIGEST,
        "roots": roots_reported,
        "files_scanned": scanned,
        "zero_byte_files": len(empty),
        "intact_declared_empty": len(intact),
        "corrupt_not_declared_empty": len(corrupt),
        "corrupt": corrupt,
        "intact": intact,
        "what_this_establishes": (
            "The restoration scope. A zero-byte payload whose manifest records "
            "row_count 0 and the empty-string digest is an honest record that "
            "a source stated nothing in that domain; restoring it would invent "
            "rows. A zero-byte payload whose content address names a non-empty "
            "digest cannot be right. Counting the first as corruption would "
            "have overstated the damage by an order of magnitude."
        ),
        "what_this_does_not_establish": (
            "That every non-empty payload is intact. This asks one question "
            "about zero-byte files and answers only that."
        ),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out, 
        json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    print("files scanned            :", scanned)
    print("zero-byte files          :", len(empty))
    print("intact (declared empty)  :", len(intact))
    print("corrupt (not declared)   :", len(corrupt))
    for row in corrupt:
        print("   ", row["path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
