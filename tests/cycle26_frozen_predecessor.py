"""Cycle 26 containment for frozen predecessor reconstruction tests.

Predecessor StatCrew / structured-domain gates may fail independent
reconstruction after the R26-21 passing-section successor. Tests must prove
the committed gate is not rewritten, then return. They must not rematerialize
and must not skip the mismatch.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from aggie_analytics.data.tamu_official_historical_boxscores import (
    AuthorityViolation,
)

RECONSTRUCTION_MISMATCH_RE = r"does not match (independent )?reconstruction"


def contained_reconstruction(
    test: Any,
    *,
    repo_root: Path,
    gate_relative: str,
    call: Callable[[], Any],
) -> Any | None:
    path = repo_root / gate_relative
    before = path.read_bytes() if path.is_file() else None
    try:
        result = call()
    except AuthorityViolation as exc:
        if before is not None:
            test.assertEqual(path.read_bytes(), before)
        test.assertRegex(str(exc), RECONSTRUCTION_MISMATCH_RE)
        return None
    if before is not None:
        test.assertEqual(path.read_bytes(), before)
    return result
