"""Independent Cycle32 reconciliation of the declared 46,953-game parent.

Provider field agreement is not independent event truth and is not NCAA
official-final reconstruction. Fitted 2013-2023 exclusions stay explicit.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
GAMES_PATH = Path(
    r"C:\BatteredAggieSyndrome.data\canonical\national_foundation_reconciliation"
    r"\sha256\d2af2bab981f8e7b33a6823e3e4b4b65eb2f96593a0eeafd56dedce1b84fd477"
    r"\national_normalized_games.jsonl"
)
PRED_TRACE = Path(
    r"C:\BatteredAggieSyndrome.data\worktrees\cycle30-scr"
    r"\artifacts\scientific_integrity\cycle30"
    r"\HISTORICAL_RAW_TO_NORMALIZED_SEMANTIC_TRACE.json"
)
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
DECLARED_PARENT = 46953
TRAIN_SEASONS = set(range(2013, 2020))
EVAL_SEASONS = set(range(2020, 2024))
FITTED_SEASONS = TRAIN_SEASONS | EVAL_SEASONS


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def main() -> int:
    if not GAMES_PATH.is_file():
        payload = {
            "artifact_type": "CYCLE32_NATIONAL_GAME_CORE_AUDIT",
            "as_of_utc": utc_now(),
            "parent_file_present": False,
            "declared_parent_rows": DECLARED_PARENT,
            "observed_parent_rows": 0,
            "all_local_reconstruction_complete": False,
            "provider_agreement_is_not_event_truth": True,
        }
        out = OUT / "science" / "CYCLE32_NATIONAL_GAME_CORE_AUDIT.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"observed": 0, "missing_file": True}))
        return 0

    counts = Counter()
    seasons: Counter[int] = Counter()
    missing_ids = 0
    missing_season = 0
    missing_home = 0
    missing_away = 0
    missing_scores = 0
    ties = 0
    canceled = 0
    neutrals = 0
    fitted = 0
    fitted_missing_scores = 0
    protected_2024_2025 = 0
    unique_ids: set[str] = set()
    duplicate_ids = 0
    first_fields: tuple[str, ...] | None = None
    with GAMES_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            counts["observed"] += 1
            if first_fields is None:
                first_fields = tuple(sorted(row.keys()))
            gid = str(row.get("canonical_game_id") or row.get("game_id") or "")
            if not gid:
                missing_ids += 1
            elif gid in unique_ids:
                duplicate_ids += 1
            else:
                unique_ids.add(gid)
            season = row.get("season")
            if season is None:
                missing_season += 1
            else:
                seasons[int(season)] += 1
                if int(season) in {2024, 2025}:
                    protected_2024_2025 += 1
            home = (
                row.get("home_team_source_id")
                or row.get("home_team_id")
                or row.get("home_id")
                or row.get("home_team")
                or row.get("home_team_name")
            )
            away = (
                row.get("away_team_source_id")
                or row.get("away_team_id")
                or row.get("away_id")
                or row.get("away_team")
                or row.get("away_team_name")
            )
            if not present(home):
                missing_home += 1
            if not present(away):
                missing_away += 1
            home_pts = row.get("home_points")
            if home_pts is None:
                home_pts = row.get("home_score")
            away_pts = row.get("away_points")
            if away_pts is None:
                away_pts = row.get("away_score")
            if home_pts is None or away_pts is None:
                missing_scores += 1
            elif home_pts == away_pts:
                ties += 1
            status = str(row.get("status") or row.get("game_status") or "").casefold()
            if status in {"canceled", "cancelled", "postponed"}:
                canceled += 1
            if row.get("neutral_site") is True or str(row.get("site_class") or "") == "NEUTRAL":
                neutrals += 1
            if season is not None and int(season) in FITTED_SEASONS:
                fitted += 1
                if home_pts is None or away_pts is None:
                    fitted_missing_scores += 1

    pred_trace = load_json(PRED_TRACE)
    kernel_rows = 0
    kernel_path = PRED / "PIT_KERNEL_ROWS.jsonl"
    if kernel_path.is_file():
        with kernel_path.open(encoding="utf-8") as handle:
            kernel_rows = sum(1 for line in handle if line.strip())

    payload = {
        "artifact_type": "CYCLE32_NATIONAL_GAME_CORE_AUDIT",
        "as_of_utc": utc_now(),
        "parent_file_present": True,
        "parent_path": str(GAMES_PATH),
        "declared_parent_rows": DECLARED_PARENT,
        "observed_parent_rows": counts["observed"],
        "unique_canonical_ids": len(unique_ids),
        "duplicate_ids": duplicate_ids,
        "missing_canonical_id": missing_ids,
        "missing_season": missing_season,
        "missing_home_identity": missing_home,
        "missing_away_identity": missing_away,
        "missing_numeric_scores": missing_scores,
        "ties": ties,
        "canceled_or_postponed_status_token": canceled,
        "neutral_flag_true": neutrals,
        "fitted_window_2013_2023_rows": fitted,
        "fitted_window_missing_scores": fitted_missing_scores,
        "protected_2024_2025_rows": protected_2024_2025,
        "season_min": min(seasons) if seasons else None,
        "season_max": max(seasons) if seasons else None,
        "predecessor_raw_to_normalized_compared_count": pred_trace.get("compared_count"),
        "predecessor_known_parent_exclusion_count": pred_trace.get(
            "known_parent_exclusion_count"
        ),
        "kernel_row_file_count": kernel_rows,
        "count_matches_declared_parent": counts["observed"] == DECLARED_PARENT,
        "provider_agreement_is_not_event_truth": True,
        "not_ncaa_official_final_reconstruction": True,
        "all_local_reconstruction_complete": False,
        "sample_fields": list(first_fields or ()),
    }
    out = OUT / "science" / "CYCLE32_NATIONAL_GAME_CORE_AUDIT.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "observed": counts["observed"],
                "matches_declared": payload["count_matches_declared_parent"],
                "fitted": fitted,
                "kernel_rows": kernel_rows,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
