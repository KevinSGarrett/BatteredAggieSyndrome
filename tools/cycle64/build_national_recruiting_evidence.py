r"""Build the national recruiting evidence release 2010-2017 (BAT-735, Cycle #64 TP64-A01).

``python -B tools/cycle64/build_national_recruiting_evidence.py
--contract configs/national_recruiting_evidence_2010_2017_contract.json --data-root <data>
--output-root <data>/canonical/national_recruiting_evidence_2010_2017
--manifest-root <data>/manifests/national_recruiting_evidence_2010_2017
[--input-order natural|reverse|shuffle:<seed>] [--chunk-size N --checkpoint-dir <dir> [--stop-after-chunks K]
[--resume]] [--work-root <dir>] [--variant NAME] [--receipt <new file>]``

A thin front of :mod:`aggie_analytics.personnel_evidence.recruiting_build`: the source-faithful qualification of every
retained recruiting observation (no fit), the deterministic database and its create-only content-addressed
materialization (an identical rebuild is ALREADY_PRESENT_IDENTICAL; differing bytes are REFUSED_IMMUTABLE_COLLISION).
Exit 0 built or already present, 2 refused, 3 interrupted at a checkpoint.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.personnel_evidence import recruiting_build  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(recruiting_build.main(repo_root=ROOT))
