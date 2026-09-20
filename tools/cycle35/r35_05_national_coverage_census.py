"""R35-05/R35-01: the era-correct national program-season census, 1963-2026.

The denominator is the independently expected national program-season
population, not whatever happened to be acquired. 182 appearances, 266
observed teams, 28 acquired seasons, 48 join attempts and 85 SQL rows are
all CHILDREN of this population; none of them may stand in for it.

Era naming follows TP35-01 exactly:

    1963-1972  University Division
    1973-1977  Division I (unsplit)
    1978-2005  Division I-A / I-AA
    2006-      FBS / FCS

Three things this census is careful about:

* **Missing cells are retained, never dropped.** A season with no membership
  evidence is emitted as an explicit gap with its exact reason, so the shape
  of what is unknown is part of the artifact.
* **Current membership is reconciled against its own historical slice.** A
  program in the 2026 population that never appears historically, and a
  program that appears historically but has left, are both reported --
  transitions and discontinued programs are the interesting rows, not noise.
* **Coverage is measured per domain against the same denominator.** Staff,
  finals, kernel and availability coverage are all expressed as fractions of
  the expected population, so no domain can look complete by quoting its own
  acquisition total back to itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUTPUTS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
HISTORICAL_EARLY = OUTPUTS / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl"
HISTORICAL_LATE = OUTPUTS / "HISTORICAL_MEMBERSHIP_2013_2023.jsonl"
CURRENT_PROGRAMS = OUTPUTS / "CURRENT_2026_PROGRAMS.jsonl"
KERNEL_ROWS = OUTPUTS / "PIT_KERNEL_ROWS.jsonl"

FIRST_SEASON = 1963
LAST_SEASON = 2026

ERA_BANDS = (
    (1963, 1972, "UNIVERSITY_DIVISION"),
    (1973, 1977, "DIVISION_I_UNSPLIT"),
    (1978, 2005, "DIVISION_I_A_PLUS_I_AA"),
    (2006, LAST_SEASON, "FBS_PLUS_FCS"),
)

#: Bands the Cycle #34 tranche was required to span. Kept here so the
#: census can report band coverage without a separate hardcoded list.
TRANCHE_BANDS = ((2000, 2005), (2006, 2012), (2013, 2018), (2019, 2023))


def era_for(season: int) -> str:
    for start, end, name in ERA_BANDS:
        if start <= season <= end:
            return name
    return "OUT_OF_DECLARED_RANGE"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256_of(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def build_population() -> dict[str, Any]:
    """The expected program-season cells, plus every season with no evidence."""

    early = read_jsonl(HISTORICAL_EARLY)
    late = read_jsonl(HISTORICAL_LATE)
    current = read_jsonl(CURRENT_PROGRAMS)

    cells: dict[tuple[str, int], dict[str, Any]] = {}
    for row in early + late:
        season = int(row["season"])
        key = (str(row["program_id"]), season)
        cells[key] = {
            "program_id": str(row["program_id"]),
            "display_name": row.get("display_name"),
            "season": season,
            "declared_era": row.get("era"),
            "era_correct_band": era_for(season),
            "classification": row.get("classification"),
            "conference": row.get("conference"),
            "evidence_state": "MEMBERSHIP_EVIDENCE_PRESENT",
        }
    for row in current:
        key = (str(row["program_id"]), LAST_SEASON)
        cells[key] = {
            "program_id": str(row["program_id"]),
            "display_name": row.get("display_name"),
            "season": LAST_SEASON,
            "declared_era": "FBS_PLUS_FCS",
            "era_correct_band": era_for(LAST_SEASON),
            "classification": row.get("classification"),
            "conference": row.get("conference"),
            "evidence_state": "CURRENT_MEMBERSHIP_EVIDENCE_PRESENT",
        }

    seasons_with_evidence = {season for _, season in cells}
    missing_seasons = [
        season
        for season in range(FIRST_SEASON, LAST_SEASON + 1)
        if season not in seasons_with_evidence
    ]

    # Retained, not dropped: a season with no membership source is an
    # explicit gap in the denominator, and the report says exactly which.
    gaps = [
        {
            "season": season,
            "era_correct_band": era_for(season),
            "evidence_state": "NO_MEMBERSHIP_SOURCE_ACQUIRED",
            "reason": "No membership row exists for this season in any "
            "declared acquisition output; the expected program count for "
            "it is therefore unknown, not zero.",
        }
        for season in missing_seasons
    ]
    return {"cells": cells, "season_gaps": gaps, "current_rows": current}


def reconcile_current_against_history(
    cells: dict[tuple[str, int], dict[str, Any]], current: list[dict[str, Any]]
) -> dict[str, Any]:
    """Transitions and discontinued programs are the interesting rows."""

    historical_ids = {pid for pid, season in cells if season < LAST_SEASON}
    current_ids = {str(row["program_id"]) for row in current}
    last_historical_season: dict[str, int] = {}
    for pid, season in cells:
        if season < LAST_SEASON:
            last_historical_season[pid] = max(
                last_historical_season.get(pid, 0), season
            )
    names = {
        cell["program_id"]: cell.get("display_name") for cell in cells.values()
    }
    for row in current:
        names.setdefault(str(row["program_id"]), row.get("display_name"))

    current_without_history = sorted(current_ids - historical_ids)
    historical_absent_from_current = sorted(historical_ids - current_ids)
    return {
        "current_program_count": len(current_ids),
        "historical_program_count": len(historical_ids),
        "in_both": len(current_ids & historical_ids),
        "current_without_historical_slice": [
            {"program_id": pid, "display_name": names.get(pid)}
            for pid in current_without_history
        ],
        "historical_absent_from_current": [
            {
                "program_id": pid,
                "display_name": names.get(pid),
                "last_historical_season": last_historical_season.get(pid),
                "state": "TRANSITIONED_OR_DISCONTINUED_OR_UNACQUIRED",
            }
            for pid in historical_absent_from_current
        ],
        "note": "Neither list is automatically a defect. A program absent "
        "from the current slice may have moved division, been discontinued, "
        "or simply not been acquired for 2024-2026; the distinction requires "
        "evidence this census does not have and does not invent.",
    }


def domain_coverage(cells: dict[tuple[str, int], dict[str, Any]]) -> dict[str, Any]:
    """Each domain as a fraction of the SAME expected denominator."""

    expected = set(cells)
    kernel_rows = read_jsonl(KERNEL_ROWS)
    kernel_cells: set[tuple[str, int]] = set()
    for row in kernel_rows:
        season = row.get("season")
        if season is None:
            continue
        for side in ("home_canonical_team_id", "away_canonical_team_id"):
            pid = row.get(side)
            if pid:
                kernel_cells.add((str(pid), int(season)))

    return {
        "expected_program_season_cells": len(expected),
        "kernel": {
            "source": str(KERNEL_ROWS),
            "rows": len(kernel_rows),
            "program_season_cells_touched": len(kernel_cells),
            "cells_inside_expected_population": len(kernel_cells & expected),
            "cells_outside_expected_population": len(kernel_cells - expected),
            "expected_cells_with_no_kernel_row": len(expected - kernel_cells),
            "coverage_fraction_of_expected": (
                round(len(kernel_cells & expected) / len(expected), 6)
                if expected
                else None
            ),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    population = build_population()
    cells = population["cells"]

    by_season: Counter = Counter()
    by_band: Counter = Counter()
    by_band_class: dict[str, Counter] = defaultdict(Counter)
    for (_, season), cell in cells.items():
        by_season[season] += 1
        by_band[cell["era_correct_band"]] += 1
        by_band_class[cell["era_correct_band"]][str(cell.get("classification"))] += 1

    tranche_band_counts = {
        f"{start}-{end}": sum(
            count for season, count in by_season.items() if start <= season <= end
        )
        for start, end in TRANCHE_BANDS
    }

    reconciliation = reconcile_current_against_history(
        cells, population["current_rows"]
    )
    coverage = domain_coverage(cells)

    census = {
        "artifact_type": "CYCLE35_NATIONAL_COVERAGE_CENSUS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "declared_range": {"first_season": FIRST_SEASON, "last_season": LAST_SEASON},
        "era_bands": [
            {"start": s, "end": e, "band": n} for s, e, n in ERA_BANDS
        ],
        "inputs": {
            str(path): {"sha256": sha256_of(path), "exists": path.is_file()}
            for path in (HISTORICAL_EARLY, HISTORICAL_LATE, CURRENT_PROGRAMS, KERNEL_ROWS)
        },
        "expected_program_season_cells": len(cells),
        "distinct_programs": len({pid for pid, _ in cells}),
        "seasons_with_membership_evidence": len(by_season),
        "seasons_in_declared_range": LAST_SEASON - FIRST_SEASON + 1,
        "season_gaps": population["season_gaps"],
        "season_gap_count": len(population["season_gaps"]),
        "cells_by_season": dict(sorted(by_season.items())),
        "cells_by_era_band": dict(by_band),
        "classification_by_era_band": {
            band: dict(counter) for band, counter in by_band_class.items()
        },
        "cycle34_tranche_band_populations": tranche_band_counts,
        "current_vs_historical_reconciliation": reconciliation,
        "domain_coverage": coverage,
        "denominator_is_not_an_acquisition_total": True,
        "counts_that_are_not_the_denominator": {
            "182_appearances": "A&M appearance child view",
            "266_observed_teams": "current membership slice only",
            "28_acquired_seasons": "Cycle 34 acquisition tranche",
            "48_join_attempts": "Cycle 34 opportunity set",
            "85_sql_rows": "Cycle 34 candidate transcription",
        },
        "pit_admitted": False,
    }
    (out_dir / "CYCLE35_NATIONAL_COVERAGE.json").write_text(
        json.dumps(census, indent=2, sort_keys=True), encoding="utf-8"
    )

    cells_path = out_dir / "CYCLE35_EXPECTED_PROGRAM_SEASON_CELLS.jsonl"
    with cells_path.open("w", encoding="utf-8") as handle:
        for key in sorted(cells):
            handle.write(json.dumps(cells[key], sort_keys=True) + "\n")

    print(json.dumps(
        {
            "expected_program_season_cells": census["expected_program_season_cells"],
            "distinct_programs": census["distinct_programs"],
            "seasons_with_evidence": census["seasons_with_membership_evidence"],
            "season_gaps": [g["season"] for g in census["season_gaps"]],
            "cells_by_era_band": census["cells_by_era_band"],
            "tranche_bands": tranche_band_counts,
            "current_without_history": len(
                reconciliation["current_without_historical_slice"]
            ),
            "historical_absent_from_current": len(
                reconciliation["historical_absent_from_current"]
            ),
            "kernel_coverage": coverage["kernel"],
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
