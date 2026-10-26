r"""Build the national frozen shallow-tree comparison release 2016-2023 (BAT-736, Cycle #65 TP65-A01).

``python -B tools/cycle65/build_national_shallow_boosting_comparison.py
--contract configs/national_shallow_boosting_comparison_2016_2023_contract.json
--parent-database <data>/canonical/national_retrospective_reference_2016_2023/sha256/<id>/national_retrospective_reference.sqlite
--output-root <data>/canonical/national_shallow_boosting_comparison_2016_2023
--manifest-root <data>/manifests/national_shallow_boosting_comparison_2016_2023
[--input-order natural|reverse|shuffle:<seed>] [--chunk-size N --checkpoint-dir <dir> [--stop-after-chunks K]
[--resume]] [--repeat-fits N] [--work-root <dir>] [--variant NAME] [--receipt <new file>]``

A thin front of :mod:`aggie_analytics.retrospective_baseline.boosting_build`, run only under the pinned offline build
runtime (the two frozen fits import the build-only backend lazily): the deterministic database and its create-only
content-addressed materialization (an identical rebuild is ALREADY_PRESENT_IDENTICAL; differing bytes are
REFUSED_IMMUTABLE_COLLISION). Exit 0 built or already present, 2 refused, 3 interrupted at a checkpoint.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.retrospective_baseline import boosting_build  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(boosting_build.main())
