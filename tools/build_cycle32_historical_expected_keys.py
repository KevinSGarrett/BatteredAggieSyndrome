"""Build historical expected program-season keys from CFBD membership, not current×years."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.hashing import sha256_json  # noqa: E402
from aggie_analytics.cycle30.populations import (  # noqa: E402
    coverage_query,
    current_deletion_does_not_shrink_history,
    era_label,
    historical_program_season_keys,
    insert_discontinued_program_changes_coverage,
)

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    current = load_jsonl(PRED / "CURRENT_2026_PROGRAMS.jsonl")
    hist_1963 = load_jsonl(PRED / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl")
    hist_2013 = load_jsonl(PRED / "HISTORICAL_MEMBERSHIP_2013_2023.jsonl")
    current_ids = {str(row["program_id"]) for row in current}
    all_rows = [*hist_1963, *hist_2013]
    keys = historical_program_season_keys(all_rows)
    programs_by_id: dict[str, dict] = {}
    seasons_by_program: dict[str, set[int]] = defaultdict(set)
    for row in all_rows:
        pid = str(row["program_id"])
        seasons_by_program[pid].add(int(row["season"]))
        programs_by_id.setdefault(
            pid,
            {
                "program_id": pid,
                "display_name": row.get("display_name"),
                "source_id": row.get("source_id"),
            },
        )
    outside_current = sorted(
        (
            {
                **programs_by_id[pid],
                "in_current_266": False,
                "seasons": sorted(seasons),
                "season_count": len(seasons),
            }
            for pid, seasons in seasons_by_program.items()
            if pid not in current_ids
        ),
        key=lambda row: str(row.get("display_name") or ""),
    )
    years_present = sorted({int(row["season"]) for row in all_rows})
    absent_years = [year for year in range(1963, 2027) if year not in set(years_present)]
    probe = insert_discontinued_program_changes_coverage(
        keys, program_id="SRC-002:TEAM:DISCONTINUED-PROBE", season=1963
    )
    shrink = current_deletion_does_not_shrink_history(
        keys,
        sorted(current_ids),
        deleted_program_id=next(iter(current_ids)),
    )
    by_era = Counter()
    for pid, season in keys:
        by_era[era_label(season)] += 1
    payload = {
        "artifact_type": "CYCLE32_HISTORICAL_EXPECTED_PROGRAM_SEASON_KEYS",
        "artifact_class": "REAL_EVIDENCE",
        "authority": "CFBD_TEAMS_YEAR_MEMBERSHIP_NOT_CURRENT_TIMES_YEARS",
        "current_program_n": len(current_ids),
        "historical_key_n": len(keys),
        "historical_program_n": len(seasons_by_program),
        "programs_outside_current_266": len(outside_current),
        "outside_current_programs": outside_current,
        "years_present": years_present,
        "absent_years_including_exposed_2024_2025": absent_years,
        "coverage": coverage_query(keys),
        "by_era_key_counts": dict(by_era),
        "discontinued_insert_probe": probe,
        "current_deletion_does_not_shrink_history": shrink,
        "identity": sha256_json(sorted(f"{pid}|{season}" for pid, season in keys)),
        "gaps": {
            "2024_2025_membership_not_in_these_files": [2024, 2025],
            "complete_ncaa_census_not_claimed": True,
            "cfbd_presence_is_not_ncaa_sponsorship_truth": True,
        },
        "source_files": [
            str(PRED / "HISTORICAL_MEMBERSHIP_1963_2012.jsonl"),
            str(PRED / "HISTORICAL_MEMBERSHIP_2013_2023.jsonl"),
            str(PRED / "CURRENT_2026_PROGRAMS.jsonl"),
        ],
    }
    out = OUT / "science" / "CYCLE32_HISTORICAL_EXPECTED_KEYS.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "historical_key_n": payload["historical_key_n"],
                "historical_program_n": payload["historical_program_n"],
                "programs_outside_current_266": payload["programs_outside_current_266"],
                "outside_names": [row["display_name"] for row in outside_current],
                "absent_years": absent_years,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
