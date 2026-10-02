"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-03 / R35-02: the 880 references behind the 798 submitted role cells,
each reconciled with the whole-cache staff reparse.

Every R35-02 reference names a raw capture, a person and the role cell it
supported. The reparse row of the same capture and person is found (by the
capture path and the person's own name, never by an employer match), and the
reference ends RETAINED, CORRECTED (school, title or role differ, with the
difference), NO_LONGER_ADMITTED (with the reparse's reason) or NOT_FOUND. The
sets are compared exactly; no reference is dropped.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
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

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
R35_ROWS = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle35/runs/20260920T172801Z/implementation_output"
                r"/R35_02_STAFF_REBUILD_ROWS.jsonl")
STAFF = ATTEMPT / "evidence" / "repairs" / "R37_03_STAFF_REPARSE_ROWS.jsonl"
CORE = ("head_coach", "offensive_coordinator", "defensive_coordinator")


def _fold(name: str) -> str:
    """A name without case, punctuation or a trailing class year ("James Perry '00")."""

    name = re.sub(r"\s+['’]?\d{2}$", "", str(name or "").strip())
    return re.sub(r"[^a-z0-9]+", "", name.casefold())


def _principal(row: dict[str, Any]) -> list[str]:
    return sorted({a["role"] for a in row["assignments"]
                   if a["role"] in CORE and a.get("occupancy") in ("PRINCIPAL", "CO_SHARED")})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs"
                        / "R37_03_R35_02_RECONCILIATION.json")
    args = parser.parse_args(argv)
    references = [json.loads(line) for line in R35_ROWS.read_text(encoding="utf-8").splitlines() if line.strip()]
    wanted = {r["raw_path"] for r in references}
    by_capture: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    with STAFF.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["capture_path"] in wanted:
                by_capture[row["capture_path"]].append(row)
    rows, counts = [], collections.Counter()
    cells: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for index, ref in enumerate(references):
        candidates = [r for r in by_capture.get(ref["raw_path"], [])
                      if _fold(r["person"]) == _fold(ref["person"]) or _fold(r["person_parsed"]) == _fold(ref["person"])]
        with_role = [r for r in candidates if ref["cell_role"] in _principal(r)]
        match = (with_role or candidates or [None])[0]
        if match is None:
            # Say what the capture itself shows about the person, so a missing row is explained, not assumed.
            text = Path(ref["raw_path"]).read_bytes().decode("utf-8", "replace")
            plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
            surname = ref["person"].split()[-1] if ref["person"].split() else ref["person"]
            at = plain.find(re.sub(r"\s+['’]?\d{2}$", "", ref["person"]).strip())
            state, detail = "NOT_FOUND_IN_THE_REPARSE", {
                "capture_rows_reparsed": len(by_capture.get(ref["raw_path"], [])),
                "capture_text_at_the_name": plain[at:at + 120] if at >= 0 else None,
                "surname_on_the_page": surname in plain,
                "why": "the capture's parse yields no row for this person; the text at the name is shown as the "
                       "page states it"}
        else:
            detail = {}
            if match["program_id"] != ref["program_id"]:
                detail["program"] = {"r35": ref["program_id"], "r37": match["program_id"]}
            if re.sub(r"\s+", " ", match["source_title"]).strip() != re.sub(r"\s+", " ", ref["source_title"]).strip():
                detail["title"] = {"r35": ref["source_title"], "r37": match["source_title"]}
            if ref["cell_role"] not in _principal(match):
                detail["role"] = {"r35": ref["cell_role"], "r37_principal_or_co": _principal(match)}
            if not match["admitted_for_coverage"]:
                state = "NO_LONGER_ADMITTED"
                detail["reason"] = {"identity_state": match["identity_state"],
                                    "person_record_bound": match["binding"]["person_record_bound"],
                                    "role_claim_supported": match["binding"]["role_claim_supported"],
                                    "sport_scope": match["sport_scope"]["scope"], "season_state": match["season_state"]}
            elif detail:
                state = "CORRECTED"
            else:
                state = "RETAINED"
        counts[state] += 1
        cells[(ref["program_id"], ref["cell_role"])].append(state)
        rows.append({"reference_index": index, "episode_key": ref["episode_key"], "raw_path": ref["raw_path"],
                     "person": ref["person"], "r35_program_id": ref["program_id"], "cell_role": ref["cell_role"],
                     "r35_disposition": ref["disposition"], "state": state, "differences": detail,
                     "r37_row": {"observation_index": match["observation_index"], "season": match["season"],
                                 "title_source": match.get("title_source")} if match else None})
    report = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-03",
        "rows": ["R37-03-CF-R35-02", "R37-05-CF-R35-02"], "references": len(references),
        "distinct_r35_cells": len(cells), "states": dict(counts),
        "cells_any_reference_retained": sum(1 for v in cells.values() if "RETAINED" in v or "CORRECTED" in v),
        "references_conserved": sum(counts.values()) == len(references),
        "reconciliation": rows,
        "inputs": {"r35_rows": {"path": str(R35_ROWS), "sha256": hashlib.sha256(R35_ROWS.read_bytes()).hexdigest()},
                   "staff_rows": {"path": str(STAFF), "sha256": hashlib.sha256(STAFF.read_bytes()).hexdigest()}},
    }
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("reconciliation", "inputs")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
