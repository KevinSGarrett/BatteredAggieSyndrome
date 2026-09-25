"""Clean-CI row evidence: open and rehash, or fail closed as blocked."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aggie_analytics.cycle29.hashing import sha256_file


class CiEvidenceError(ValueError):
    """Raised when clean CI cannot access claimed row-level evidence."""


def open_and_rehash(
    path: Path,
    *,
    expected_sha256: str,
    expected_rows: int,
    payload_available: bool,
) -> dict[str, Any]:
    if not payload_available:
        return {
            "result": "BLOCKED_PAYLOAD_UNAVAILABLE",
            "pass": False,
            "rows_opened": 0,
        }
    if not path.is_file():
        raise CiEvidenceError("scientific row payload missing while gate claimed PASS")
    digest = sha256_file(path)
    if digest != expected_sha256:
        raise CiEvidenceError("scientific row payload hash mismatch")
    count = 0
    with path.open("rb") as handle:
        for line in handle:
            if line.strip():
                count += 1
    if count != expected_rows:
        raise CiEvidenceError("scientific row payload count mismatch")
    return {
        "result": "REHASHED",
        "pass": True,
        "rows_opened": count,
        "sha256": digest,
    }


def reject_pass_without_opening(
    claimed_pass: bool, rows_opened: int, expected_rows: int
) -> None:
    if claimed_pass and (rows_opened == 0 or rows_opened != expected_rows):
        raise CiEvidenceError(
            "CI may not PASS a scientific result without opening and rehashing rows"
        )
