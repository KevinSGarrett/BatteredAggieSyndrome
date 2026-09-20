"""Cycle34 R34-05: rebuild the real 798 HC/OC/DC cells through the repaired
`confirmed_spans.quarantine_unlocatable_cell`, using the actual predecessor
span-adjudicated matrix as input.

READ-ONLY against the predecessor evidence directory. Output goes ONLY to a
new path under C:\\BatteredAggieSyndrome.data\\ops\\cycle34\\ -- never back
into ops/cycle33/runs/... or any other preserved-evidence path. This is a
brand-new script; it does not modify or retrofit any existing tools/*.py
file.

Input: the real, predecessor-produced, span-adjudicated matrix at
C:\\BatteredAggieSyndrome.data\\ops\\cycle33\\runs\\20260914T130736Z\\
implementation_output\\science\\CYCLE33_CURRENT_HC_OC_DC_MATRIX_SPAN_SUCCESSOR.jsonl
(798 cells; each already carries real per-episode `role_claim_supported`
determinations from prior real span-location work against cached official
staff pages -- this script does not re-derive those, it reconstructs each
cell's PRE-quarantine state from them and re-runs the repaired quarantine
step to see whether the MR33-05 conservation fix changes any real outcome).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle33.confirmed_spans import quarantine_unlocatable_cell  # noqa: E402

PREDECESSOR_SPAN_SUCCESSOR = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science\CYCLE33_CURRENT_HC_OC_DC_MATRIX_SPAN_SUCCESSOR.jsonl"
)
OUTPUT_DIR = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle34\20260919T_R34_receipts\pipeline_output"
)
OUTPUT_PATH = OUTPUT_DIR / "R34_05_SPAN_CONSERVATION_REBUILD.json"

QUARANTINE_TRIGGER_DISPOSITIONS = {"CONFIRMED_APPOINTMENT", "CONFIRMED_CO_SHARED_ROLE"}


def _reconstruct_pre_quarantine_cell(cell: dict) -> dict | None:
    """Undo whatever the predecessor's (buggy) quarantine pass already did,
    recovering the cell state as it would have looked BEFORE any quarantine
    step ran, so the REPAIRED function can be exercised on it for real.

    Returns None for cells quarantine_unlocatable_cell would never touch
    (disposition outside the trigger set to begin with, e.g. UNKNOWN_NOT_LISTED).
    """

    disposition = str(cell.get("disposition") or "")
    episode_refs = list(cell.get("episode_refs") or [])
    quarantined_refs = list(cell.get("quarantined_unlocatable_episodes") or [])
    cardinality = cell.get("episode_cardinality")

    if disposition in QUARANTINE_TRIGGER_DISPOSITIONS:
        # Already sitting at a pre/never-quarantined disposition; episode_refs
        # is already the full set (span_adjudicated True means the predecessor
        # kept it as-is, i.e. all episodes were supported).
        pre = dict(cell)
        pre["episode_refs"] = episode_refs + quarantined_refs
        return pre

    if disposition in {"CONFIRMED_PARTIAL_SPAN_LOCATABLE", "SPAN_NOT_LOCATABLE_QUARANTINE"}:
        # These dispositions ONLY exist because quarantine_unlocatable_cell
        # already ran once. Reconstruct the original disposition from
        # episode_cardinality (1 -> single appointment, >1 -> co-shared),
        # and recombine kept + quarantined episodes into the original set.
        if cardinality is None:
            return None
        original_disposition = (
            "CONFIRMED_APPOINTMENT" if int(cardinality) <= 1 else "CONFIRMED_CO_SHARED_ROLE"
        )
        pre = dict(cell)
        pre["disposition"] = original_disposition
        pre["episode_refs"] = episode_refs + quarantined_refs
        pre.pop("quarantined_unlocatable_episodes", None)
        pre.pop("span_adjudicated", None)
        return pre

    return None  # e.g. UNKNOWN_NOT_LISTED -- quarantine_unlocatable_cell never touches these


def run() -> dict:
    if not PREDECESSOR_SPAN_SUCCESSOR.is_file():
        raise SystemExit(f"predecessor input not found (read-only check): {PREDECESSOR_SPAN_SUCCESSOR}")

    total_cells = 0
    eligible_cells = 0  # cells quarantine_unlocatable_cell actually acts on
    skipped_cells = 0  # e.g. UNKNOWN_NOT_LISTED, or missing cardinality data
    disposition_counts_repaired: dict[str, int] = {}
    total_episodes_in = 0
    total_episodes_out = 0  # episode_refs + quarantined_unlocatable_episodes combined, post-repair
    changed_vs_recorded = []  # cells where the repaired result differs from the real recorded disposition
    conservation_violations = []  # cells where episode count is not conserved (should never happen)

    with PREDECESSOR_SPAN_SUCCESSOR.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            total_cells += 1
            recorded_cell = json.loads(line)
            recorded_disposition = str(recorded_cell.get("disposition") or "")

            pre = _reconstruct_pre_quarantine_cell(recorded_cell)
            if pre is None:
                skipped_cells += 1
                disposition_counts_repaired[recorded_disposition] = (
                    disposition_counts_repaired.get(recorded_disposition, 0) + 1
                )
                continue

            eligible_cells += 1
            episodes_in = len(pre.get("episode_refs") or [])
            total_episodes_in += episodes_in

            repaired = quarantine_unlocatable_cell(pre)
            repaired_disposition = str(repaired.get("disposition") or "")
            disposition_counts_repaired[repaired_disposition] = (
                disposition_counts_repaired.get(repaired_disposition, 0) + 1
            )

            kept = len(repaired.get("episode_refs") or [])
            quarantined = len(repaired.get("quarantined_unlocatable_episodes") or [])
            episodes_out = kept + quarantined
            total_episodes_out += episodes_out
            if episodes_out != episodes_in:
                conservation_violations.append(
                    {"line": line_no, "episodes_in": episodes_in, "episodes_out": episodes_out}
                )

            if repaired_disposition != recorded_disposition:
                changed_vs_recorded.append(
                    {
                        "line": line_no,
                        "program_id": recorded_cell.get("program_id"),
                        "role": recorded_cell.get("role"),
                        "recorded_disposition": recorded_disposition,
                        "repaired_disposition": repaired_disposition,
                    }
                )

    result = {
        "artifact_type": "CYCLE34_R34_05_SPAN_CONSERVATION_REBUILD",
        "read_only_input": str(PREDECESSOR_SPAN_SUCCESSOR),
        "total_cells": total_cells,
        "eligible_cells_quarantine_logic_applies_to": eligible_cells,
        "skipped_cells_not_applicable": skipped_cells,
        "disposition_counts_after_repair": disposition_counts_repaired,
        "historical_recorded_disposition_counts": {
            "CONFIRMED_APPOINTMENT": 643,
            "CONFIRMED_CO_SHARED_ROLE": 101,
            "UNKNOWN_NOT_LISTED": 26,
            "SPAN_NOT_LOCATABLE_QUARANTINE": 28,
        },
        "total_episodes_in": total_episodes_in,
        "total_episodes_out_after_repair": total_episodes_out,
        "episode_conservation_holds": total_episodes_in == total_episodes_out,
        "conservation_violations": conservation_violations,
        "cells_where_repaired_disposition_differs_from_recorded": changed_vs_recorded,
        "cells_changed_count": len(changed_vs_recorded),
        "interpretation": (
            "cells_changed_count == 0 means the real 798-cell dataset never contained a cell with a "
            "genuine mix of supported and unsupported episodes -- the exact MR33-05 bug condition -- so "
            "the repair does not change any real historical count for this specific dataset, even though "
            "the bug itself is real and the fix is independently proven by synthetic tests."
        ),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True)[:4000])
