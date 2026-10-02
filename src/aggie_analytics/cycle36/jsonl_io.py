"""Write a JSONL artifact atomically and prove every row survived the write.

This exists because of a real failure in this cycle, and the failure had a
cause worth naming. A 35 MB observation file read back with eleven records
truncated mid-value, the next record's opening brace following immediately
on the same line; the newline count still matched because the lost bytes
took their newline with them.

The cause was **two producers writing the same path at once**. An earlier
full-cache run was still alive, holding an open handle and writing at its
own file offsets, while a later run wrote the same name. Neither process was
wrong about what it had written; the file was simply not the output of
either one.

That is exactly why a row count is not verification and why a producer must
read its own artifact back. Two defences follow, and both are needed:

* **Atomicity.** Write to a temporary name, flush, fsync, then rename into
  place. A reader never observes a half-written file, and a concurrent
  writer collides on the temporary name rather than in the middle of the
  real one.
* **Verification.** Parse every line back from disk and compare the count.
  A file that fails raises rather than being returned, because an
  unverified artifact is not evidence.

Readers are strict for the same reason: a consumer reading tolerantly would
have dropped eleven staff records from a national release and reported a
smaller population as if it were the real one.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping
from aggie_analytics import atomic_io as _bas_atomic


class JsonlWriteError(RuntimeError):
    """Raised when a written artifact does not read back intact."""


def verify_jsonl(path: Path, expected_rows: int) -> dict[str, Any]:
    """Parse every line back from disk and report exactly what is wrong."""

    text = path.read_text(encoding="utf-8")
    parsed = 0
    broken: list[int] = []
    for index, line in enumerate(text.split("\n")):
        if not line.strip():
            continue
        try:
            json.loads(line)
            parsed += 1
        except ValueError:
            broken.append(index)
    # ``str.splitlines`` breaks on separators ``split("\n")`` does not. A
    # disagreement means a record carries a raw line separator inside it,
    # which is a defect even when both halves happen to parse.
    non_empty_splitlines = len([line for line in text.splitlines() if line.strip()])
    separator_disagreement = non_empty_splitlines - (parsed + len(broken))
    return {
        "path": str(path),
        "expected_rows": expected_rows,
        "parsed_rows": parsed,
        "broken_lines": len(broken),
        "broken_line_indexes": broken[:20],
        "separator_disagreement": separator_disagreement,
        "bytes": path.stat().st_size if path.is_file() else None,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
        if path.is_file()
        else None,
        "verified": (
            parsed == expected_rows and not broken and separator_disagreement == 0
        ),
    }


def write_jsonl_verified(
    path: Path, rows: Iterable[Mapping[str, Any]], *, sort_keys: bool = True
) -> dict[str, Any]:
    """Write rows atomically, then prove the file on disk holds all of them."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    written = 0
    with _bas_atomic.open_write(temporary, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=sort_keys) + "\n")
            written += 1
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    verification = verify_jsonl(path, written)
    if not verification["verified"]:
        raise JsonlWriteError(
            f"{path} did not read back intact: {verification['parsed_rows']} of "
            f"{written} rows parsed, {verification['broken_lines']} broken lines, "
            f"separator disagreement {verification['separator_disagreement']}"
        )
    return verification


def read_jsonl_strict(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file, failing loudly and specifically on a bad line.

    A tolerant reader that skips unparseable lines would turn a truncated
    artifact into a quietly smaller population, which is the failure mode
    this module exists to prevent.
    """

    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").split("\n")):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except ValueError as error:
            raise JsonlWriteError(
                f"{path} line {index} does not parse: {error}. The file is "
                "truncated or interleaved; it must be regenerated, not skipped."
            ) from error
    return rows
