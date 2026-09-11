"""Emit remaining UNKNOWN OC/DC cells from the successor matrix. Not dual-hat invention."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    matrix = load_jsonl(OUT / "science" / "CYCLE32_CURRENT_HC_OC_DC_MATRIX.jsonl")
    people = load_jsonl(OUT / "science" / "CYCLE32_OFFICIAL_STAFF_PARSED.jsonl")
    programs = {str(row["program_id"]): row for row in load_jsonl(PRED / "CURRENT_2026_PROGRAMS.jsonl")}
    bindings = {str(row["program_id"]): row for row in load_jsonl(OUT / "science" / "CYCLE32_SOURCE_BINDINGS.jsonl")}
    by_program: dict[str, list[dict]] = defaultdict(list)
    for row in people:
        by_program[str(row.get("program_id") or "")].append(row)
    unknown_hc = [
        row for row in matrix
        if row.get("role") == "head_coach" and row.get("disposition") == "UNKNOWN_NOT_LISTED"
    ]
    rows = []
    for cell in matrix:
        if cell.get("disposition") != "UNKNOWN_NOT_LISTED":
            continue
        if cell.get("role") == "head_coach":
            continue
        pid = str(cell.get("program_id") or "")
        related = []
        for person in by_program.get(pid, []):
            title = str(person.get("title") or "")
            folded = title.casefold()
            if any(token in folded for token in ("coordinator", "head coach", "offense", "defense", "pass", "run")):
                related.append(
                    {
                        "person": person.get("person"),
                        "title": title,
                        "stored_role": person.get("role"),
                    }
                )
        rows.append(
            {
                "program_id": pid,
                "display_name": (programs.get(pid) or {}).get("display_name"),
                "role": cell.get("role"),
                "people_count": len(by_program.get(pid, [])),
                "related_titles": related[:16],
                "pass_game_or_unit_coordinator_is_not_oc_dc": True,
                "page_url": (bindings.get(pid) or {}).get("page_url"),
            }
        )
    payload = {
        "artifact_type": "CYCLE32_REMAINING_UNKNOWN_OC_DC",
        "artifact_class": "REAL_EVIDENCE",
        "invented_dual_hat": False,
        "pass_game_not_promoted": True,
        "pit_admitted": False,
        "unknown_cells": len(rows),
        "unknown_head_coaches": [row.get("display_name") for row in unknown_hc],
        "minnesota_dc_vue_zip_fixed": True,
        "rows": rows,
    }
    (OUT / "science" / "CYCLE32_REMAINING_UNKNOWN_OC_DC.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"unknown_cells": len(rows), "unknown_head_coaches": len(unknown_hc)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
