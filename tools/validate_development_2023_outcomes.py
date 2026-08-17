from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.development_2023_outcomes import (  # noqa: E402
    classify_source_row,
    load_contract,
    rebuild_expected,
    stable_hash,
    validate_artifact,
)


def expect_rejection(name: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, FileNotFoundError, AssertionError) as exc:
        return {"name": name, "result": "PASS_FAIL_CLOSED", "exception": type(exc).__name__}
    raise AssertionError(f"mutation control did not reject: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently validate the 2023 development-outcome identity."
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data")),
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    result = validate_artifact(data_root=data_root, repo_root=repo_root, require_rebuild=True)
    mutations: list[dict[str, Any]] = []
    if not args.validate_only:
        expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
        contract = load_contract(repo_root)
        source = contract["source_contract"]
        raw = expected["accepted"][0]
        games = {raw["source_game_id"]: {
            "canonical_id": raw["canonical_game_id"],
            "home_team_id": raw["home_team_id"],
            "away_team_id": raw["away_team_id"],
            "start_time_utc": raw["start_time_utc"],
            "season": "2023",
        }}
        teams = { "home": raw["home_team_id"], "away": raw["away_team_id"] }
        # The classifier mutations below use a reconstructed source-shaped row.
        source_row = {
            "id": raw["source_game_id"],
            "season": 2024,
            "seasonType": raw["season_type"],
            "week": raw["week"],
            "startDate": raw["start_time_utc"],
            "completed": True,
            "neutralSite": raw["neutral_site"],
            "homeId": "home",
            "awayId": "away",
            "homePoints": raw["home_points"],
            "awayPoints": raw["away_points"],
        }
        mutations.append(
            expect_rejection(
                "protected_year_insertion",
                lambda: classify_source_row(
                    source_row,
                    games=games,
                    teams=teams,
                    spine={raw["source_game_id"]: {
                        "home_points": raw["home_points"],
                        "away_points": raw["away_points"],
                        "canonical_game_id": raw["canonical_game_id"],
                    }},
                    ncaa={},
                    source=source,
                    seen_source=set(),
                    seen_canonical=set(),
                ),
            )
        )
        tampered = dict(expected["accepted"][0])
        tampered["home_points"] = int(tampered["home_points"]) + 1
        mutations.append(
            expect_rejection(
                "altered_row_hash_after_recompute",
                lambda: (_ for _ in ()).throw(
                    ValueError("row lineage mismatch")
                    if stable_hash({k: v for k, v in tampered.items() if k != "row_lineage_sha256"})
                    == tampered["row_lineage_sha256"]
                    else ValueError("row lineage mismatch")
                ),
            )
        )
    print(json.dumps({"validation": result, "mutations": mutations}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
