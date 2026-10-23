r"""Build the explicit national retrospective site/calendar association release 2016-2023 (BAT-734 bounded research
contribution, Cycle #63 TP63-A01).

``python -B tools/cycle63/build_national_site_calendar_association.py
--contract configs/national_site_calendar_association_2016_2023_contract.json
--data-root <data>
--output-root <data>/canonical/national_site_calendar_association_2016_2023
--manifest-root <data>/manifests/national_site_calendar_association_2016_2023``

A thin command-line front of :mod:`aggie_analytics.retrospective_baseline.context_association_build` (the pinned input
loading, source qualification, frozen derivation, create-only materialization, checkpoint and receipt machinery live
there). Exit 0 on a materialized or ALREADY_PRESENT_IDENTICAL release, 2 with ``{"refused": CODE, "error": text}`` on
stderr when refused, 3 when stopped at a checkpoint (``--stop-after-chunks``).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.retrospective_baseline import context_association_build as cab  # noqa: E402

main = cab.main
BuildRefused = cab.BuildRefused
load_contract = cab.load_contract

if __name__ == "__main__":
    raise SystemExit(cab.main(repo_root=REPO_ROOT))
