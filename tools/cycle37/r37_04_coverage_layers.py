"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-04 AC06: every expected HC/OC/DC cell (program x season x role) with its
coverage in separate layers, never summed into one.

* CONFIRMED: the cell's official source-scoped coverage (core_role_cell).
* CANDIDATE_USER_CORPUS: a user-compiled observation in the cell's principal
  column ("Head Coach", "Offensive Coordinator", "Defensive Coordinator") for
  a cell-bound program and season; alias bindings are counted separately.
* CANDIDATE_CAREER: an in-population revision-bound career episode whose
  principal or co-shared role is the cell's role and whose interval contains
  the season.
* PIT_ADMITTED: none; nothing here is point-in-time.

Assistant, associate and other qualified roles never count toward a principal
cell. The denominator is the full expected-cell set; no cell is dropped.
"""

from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path
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
R = ATTEMPT / "evidence" / "repairs"
COLUMNS = {"Head Coach": "head_coach", "Offensive Coordinator": "offensive_coordinator",
           "Defensive Coordinator": "defensive_coordinator"}
PRINCIPAL = ("PRINCIPAL", "CO_SHARED")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=R / "R37_04_COVERAGE_LAYERS.json")
    args = parser.parse_args(argv)
    conn = sqlite3.connect(f"file:{args.release}?mode=ro", uri=True)
    cells = {(pid, season, role): state for pid, season, role, state in conn.execute(
        "select program_id, season, role_code, coverage_state from core_role_cell")}
    user = collections.Counter()
    for pid, season, column in conn.execute(
            "select canonical_program_id, season, role_column from user_corpus_cell "
            "where canonical_program_id is not null"):
        if column in COLUMNS:
            user[(pid, int(season), COLUMNS[column])] += 1
    alias = collections.Counter()
    bindings = R / "R37_04_ALIAS_CELL_BINDINGS.jsonl"
    column_of = dict(conn.execute("select user_cell_id, role_column from user_corpus_cell"))
    for line in bindings.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        column = column_of.get(row["user_cell_id"])
        if column in COLUMNS:
            alias[(row["program_id"], int(row["season"]), COLUMNS[column])] += 1
    career = collections.Counter()
    with (R / "R37_05_CAREER_EPISODES.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            episode = json.loads(line)
            if episode["population_state"] != "IN_POPULATION_CANDIDATE_EPISODE" or episode["family"] != "COACHING":
                continue
            pid = (episode.get("resolution") or {}).get("program_id")
            end = episode["end"] if episode["end"] is not None else 2026
            for assignment in episode["assignments"]:
                if assignment["role"] in COLUMNS.values() and assignment.get("occupancy") in PRINCIPAL:
                    for season in range(max(episode["start"], 1963), min(end, 2026) + 1):
                        career[(pid, season, assignment["role"])] += 1
    rows, layers = [], collections.Counter()
    for (pid, season, role), state in sorted(cells.items()):
        row = {"program_id": pid, "season": season, "role": role,
               "confirmed": state == "CONFIRMED_SOURCE_SCOPED", "confirmed_state": state,
               "candidate_user_corpus": user.get((pid, season, role), 0),
               "candidate_user_corpus_via_alias_binding": alias.get((pid, season, role), 0),
               "candidate_career_episodes": career.get((pid, season, role), 0), "pit_admitted": False}
        rows.append(row)
        layers["confirmed"] += row["confirmed"]
        layers["candidate_user_corpus"] += bool(row["candidate_user_corpus"])
        layers["candidate_user_corpus_via_alias"] += bool(row["candidate_user_corpus_via_alias_binding"])
        layers["candidate_career"] += bool(row["candidate_career_episodes"])
        layers["any_candidate_without_confirmation"] += (not row["confirmed"]) and bool(
            row["candidate_user_corpus"] or row["candidate_user_corpus_via_alias_binding"] or row["candidate_career_episodes"])
        layers["no_layer_at_all"] += not (row["confirmed"] or row["candidate_user_corpus"]
                                          or row["candidate_user_corpus_via_alias_binding"]
                                          or row["candidate_career_episodes"])
    path = args.out.with_name("R37_04_COVERAGE_LAYER_ROWS.jsonl")
    _bas_atomic.write_text(path, "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    by_era = collections.defaultdict(collections.Counter)
    for row in rows:
        era = "1963-1999" if row["season"] < 2000 else "2000-2012" if row["season"] < 2013 else "2013-2026"
        by_era[era]["cells"] += 1
        by_era[era]["confirmed"] += row["confirmed"]
        by_era[era]["candidate_user_corpus"] += bool(row["candidate_user_corpus"])
        by_era[era]["candidate_career"] += bool(row["candidate_career_episodes"])
    report = {"label": LABEL, "cycle_number": 37, "attempt_number": 2, "requirement": "R37-04-AC06",
              "expected_cells": len(rows), "cells_with_each_layer": dict(layers),
              "by_era": {k: dict(v) for k, v in sorted(by_era.items())}, "pit_admitted_cells": 0,
              "rule": "layers are reported side by side and never summed; assistant or associate roles never count "
                      "toward a principal cell",
              "rows_path": str(path), "release": str(args.release)}
    _bas_atomic.write_text(args.out, json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("rows_path", "release")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
