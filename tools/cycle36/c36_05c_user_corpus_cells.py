"""R36-05: preserve every user-corpus cell with its own program resolution.

TP36-03: "the user's 2000-2026 corpus [is a] valuable candidate observation,
not self-confirming official evidence." Cycle #35 parsed all 110,044 named
cells and left them outside the release, so a query against the delivered
database could not see them at all.

This tool writes one row per cell, at cell grain, carrying:

* the physical spreadsheet coordinates the parser read it from -- season,
  team as written, role column -- so a reviewer can go back to the source;
* the person exactly as the corpus states them, unnormalised;
* the canonical program the Cycle #36 crosswalk resolves the team to, or the
  reason it does not;
* an evidence tier that never rises above
  ``USER_COMPILED_RESEARCH_OBSERVATION``, because ingestion is not
  verification and a name agreeing with an official row is not corroboration.

Nothing here is promoted, joined to an official assertion, or admitted to a
point-in-time consumer. The cells are preserved and queryable, which is what
was missing.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.hashing import sha256_json
from aggie_analytics import atomic_io as _bas_atomic  # noqa: E402
from aggie_analytics.cycle36.jsonl_io import (  # noqa: E402
    read_jsonl_strict,
    write_jsonl_verified,
)
from aggie_analytics.cycle36.program_crosswalk import (  # noqa: E402
    build_crosswalk,
    load_payloads,
)

CELLS_2013_2026 = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs"
    r"\20260920T224700Z_mf35_11_user_cells"
    r"\CYCLE35_USER_CORPUS_2013_2026_STAFF_CELLS.jsonl"
)
CELLS_2000_2012 = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science\CYCLE33_USER_CORPUS_2000_2012_STAFF_CELLS.jsonl"
)
RAW_TEAMS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\teams")
HISTORICAL_MEMBERSHIP = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs"
    r"\HISTORICAL_MEMBERSHIP_1963_2012.jsonl"
)

TIER = "USER_COMPILED_RESEARCH_OBSERVATION"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def request_identity(endpoint: str, parameters: dict[str, Any]) -> str:
    return sha256_json({"endpoint": endpoint, "parameters": parameters})


def build(out_dir: Path) -> dict[str, Any]:
    payloads = load_payloads(RAW_TEAMS, range(1963, 2027), request_identity)
    crosswalk = build_crosswalk(
        payloads, declared_name_rows=read_jsonl_strict(HISTORICAL_MEMBERSHIP)
    )

    sources = [
        ("USER_CORPUS_2000_2012", CELLS_2000_2012),
        ("USER_CORPUS_2013_2026", CELLS_2013_2026),
    ]
    rows: list[dict[str, Any]] = []
    states: collections.Counter = collections.Counter()
    by_season: collections.Counter = collections.Counter()
    by_role: collections.Counter = collections.Counter()
    by_source: collections.Counter = collections.Counter()
    resolution_cache: dict[tuple[str, Any], dict[str, Any]] = {}

    for source_class, path in sources:
        cells = read_jsonl_strict(path)
        by_source[source_class] = len(cells)
        for index, cell in enumerate(cells):
            team = str(cell.get("team") or "")
            season_raw = cell.get("season")
            season = int(season_raw) if str(season_raw).isdigit() else None
            key = (team, season)
            if key not in resolution_cache:
                resolution_cache[key] = crosswalk.resolve(team, season)
            resolution = resolution_cache[key]
            states[resolution["state"]] += 1
            if season is not None:
                by_season[season] += 1
            by_role[str(cell.get("role_column") or "UNKNOWN")] += 1
            rows.append(
                {
                    "user_cell_index": index,
                    "source_class": source_class,
                    "source_path": str(path),
                    "season": season,
                    "season_as_written": season_raw,
                    "team_as_written": team,
                    "team_id_source": cell.get("team_id_source"),
                    "subdivision_as_written": cell.get("subdivision"),
                    "role_column": cell.get("role_column"),
                    "person_as_written": cell.get("person"),
                    "source_title_as_written": cell.get("source_title"),
                    "canonical_program_id": resolution.get("canonical_program_id"),
                    "program_resolution_state": resolution["state"],
                    "program_match_basis": resolution.get("match_basis"),
                    "candidate_program_ids": resolution.get(
                        "candidate_program_ids", []
                    ),
                    "evidence_tier": TIER,
                    "verified": False,
                    "pit_admitted": False,
                    "ingestion_is_not_confirmation": (
                        "Parsing a research spreadsheet preserves what it says. "
                        "It does not corroborate it, and a name matching an "
                        "official row is not corroboration either."
                    ),
                }
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / "CYCLE36_USER_CORPUS_CELLS.jsonl"
    verification = write_jsonl_verified(rows_path, rows)

    artifact = {
        "artifact_type": "CYCLE36_USER_CORPUS_CELLS",
        "generated_at_utc": utc_now(),
        "sources": [
            {
                "source_class": source_class,
                "path": str(path),
                "sha256": sha256_file(path),
                "rows": by_source[source_class],
            }
            for source_class, path in sources
        ],
        "cells_in": sum(by_source.values()),
        "cells_out": len(rows),
        "every_cell_preserved": sum(by_source.values()) == len(rows),
        "rows_by_source": dict(by_source),
        "program_resolution_states": dict(states),
        "distinct_seasons": len(by_season),
        "season_span": (
            [min(by_season), max(by_season)] if by_season else None
        ),
        "rows_by_season": {str(k): v for k, v in sorted(by_season.items())},
        "distinct_role_columns": len(by_role),
        "top_role_columns": dict(by_role.most_common(25)),
        "distinct_team_season_queries": len(resolution_cache),
        "evidence_tier": TIER,
        "nothing_promoted": (
            "Every row is a user-compiled research observation. None is "
            "verified, none is joined to an official assertion here, and none "
            "is point-in-time admitted."
        ),
        "post_write_verification": verification,
        "written": {"rows": str(rows_path)},
    }
    _bas_atomic.write_text(out_dir / "CYCLE36_USER_CORPUS_CELLS.json", 
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    artifact = build(args.out_dir)
    print(
        json.dumps(
            {
                key: artifact[key]
                for key in (
                    "cells_in",
                    "cells_out",
                    "every_cell_preserved",
                    "rows_by_source",
                    "program_resolution_states",
                    "distinct_seasons",
                    "season_span",
                    "distinct_role_columns",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
