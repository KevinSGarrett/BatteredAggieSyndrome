"""Rebuild the current-staff HTML successor and seven dispute rows only."""

from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Tool scripts must import the local package after PATH setup.
# ruff: noqa: E402
from aggie_analytics.cycle33.nameset_adjudication import (
    adjudicate_disputes,
    load_html,
    page_url_from_matrix,
    rebuild_matrix_from_html,
    reconstruct_comparison_row,
)

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
)
PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
REVIEW = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle33_user_coaches"
    r"\20260914T051702Z"
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _preserve_superseded(name: str) -> None:
    src = OUT / name
    dest = OUT / name.replace(".json", "_OPERATOR_OVERLAY_SUPERSEDED.json")
    dest_l = OUT / name.replace(".jsonl", "_OPERATOR_OVERLAY_SUPERSEDED.jsonl")
    if src.suffix == ".jsonl":
        dest = dest_l
    if src.is_file() and not dest.is_file():
        shutil.copyfile(src, dest)


def main() -> int:
    for name in (
        "CYCLE33_CURRENT_HC_OC_DC_MATRIX_HTML_SUCCESSOR.json",
        "CYCLE33_CURRENT_HC_OC_DC_MATRIX_HTML_SUCCESSOR.jsonl",
        "CYCLE33_NAMESET_DISPUTE_ADJUDICATION.json",
    ):
        _preserve_superseded(name)
    predecessor = load_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX.jsonl")
    programs = {
        str(row["program_id"]): row
        for row in load_jsonl(PRED / "CURRENT_2026_PROGRAMS.jsonl")
    }
    print("rebuild matrix from html", len(predecessor), flush=True)
    successor = rebuild_matrix_from_html(predecessor)
    print("html successor cells", len(successor), flush=True)
    write_jsonl(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX_HTML_SUCCESSOR.jsonl", successor)
    fbs = fcs = 0
    for cell in successor:
        if str(cell.get("disposition") or "") not in {
            "CONFIRMED_APPOINTMENT",
            "CONFIRMED_CO_SHARED_ROLE",
        }:
            continue
        if not cell.get("episode_refs"):
            continue
        klass = str(
            (programs.get(str(cell.get("program_id"))) or {}).get("classification")
            or ""
        )
        if klass == "fbs":
            fbs += 1
        elif klass == "fcs":
            fcs += 1
    summary = {
        "artifact_type": "CYCLE33_CURRENT_HC_OC_DC_MATRIX_HTML_SUCCESSOR",
        "cell_count": len(successor),
        "disposition_counts": dict(
            Counter(str(row.get("disposition") or "") for row in successor)
        ),
        "supported_fbs_role_cells": fbs,
        "supported_fcs_role_cells": fcs,
        "nonempty_fbs_and_fcs": fbs > 0 and fcs > 0,
        "predecessor_not_overwritten": True,
        "operator_overlay_not_applied": True,
        "superseded_operator_overlay_preserved": True,
        "pit_admitted": False,
    }
    write_json(OUT / "CYCLE33_CURRENT_HC_OC_DC_MATRIX_HTML_SUCCESSOR.json", summary)
    disputes = adjudicate_disputes(predecessor, successor)
    write_json(
        OUT / "CYCLE33_NAMESET_DISPUTE_ADJUDICATION.json",
        {
            "artifact_type": "CYCLE33_NAMESET_DISPUTE_ADJUDICATION",
            "count": len(disputes),
            "season": 2026,
            "rows": disputes,
            "name_presence_is_not_concurrency": True,
            "operator_overlay_not_applied": True,
            "pit_admitted": False,
        },
    )
    comparison = json.loads(
        (REVIEW / "BAS_CURRENT_COMPARISON.json").read_text(encoding="utf-8")
    )
    suc_by = {
        (str(cell.get("program_id")), str(cell.get("role"))): cell for cell in successor
    }
    html_by_program: dict[str, str] = {}
    url_by_program: dict[str, str] = {}
    for cell in predecessor:
        pid = str(cell.get("program_id") or "")
        if pid in html_by_program:
            continue
        url = page_url_from_matrix(predecessor, pid)
        html, _cache = load_html(url)
        html_by_program[pid] = html
        url_by_program[pid] = url
    reconstructed = [
        reconstruct_comparison_row(row, suc_by, html_by_program, url_by_program)
        for row in comparison.get("rows") or []
    ]
    counts = Counter(
        str(row.get("reconstruction_classification") or "") for row in reconstructed
    )
    write_json(
        OUT / "CYCLE33_CORE_COMPARISON_RECONSTRUCTION.json",
        {
            "artifact_type": "CYCLE33_CORE_COMPARISON_RECONSTRUCTION",
            "row_count": len(reconstructed),
            "classification_counts": dict(counts),
            "name_agreement_is_not_independent_confirmation": True,
            "pit_admitted": False,
        },
    )
    write_jsonl(OUT / "CYCLE33_CORE_COMPARISON_RECONSTRUCTION.jsonl", reconstructed)
    print(
        json.dumps(
            {
                "cells": len(successor),
                "fbs": fbs,
                "fcs": fcs,
                "disputes": [
                    {
                        "team": row["team"],
                        "role": row["role"],
                        "principal": row.get("principal_people"),
                        "co": row.get("co_people"),
                        "after": row.get("after_people"),
                    }
                    for row in disputes
                ],
                "reconstruction": dict(counts),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
