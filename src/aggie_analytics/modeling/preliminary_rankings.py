from __future__ import annotations

from typing import Any, Mapping, Sequence

from .preliminary import *  # noqa: F401,F403
from . import preliminary as base


BASE_FEATURE_COLUMNS = base.FEATURE_COLUMNS
RANKING_FEATURE_COLUMNS = (
    "ap_rank_diff",
    "home_ap_rank_observed",
    "away_ap_rank_observed",
    "ap_poll_available",
    "home_ap_listed",
    "away_ap_listed",
)
FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + RANKING_FEATURE_COLUMNS
RUN_VERSION = "preliminary-unprotected-team-outcome-plus-ap-rankings-v1"


def augment_with_rankings(
    features: Sequence[Mapping[str, Any]], ranking_rows: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_game: dict[str, dict[str, Mapping[str, Any]]] = {}
    for row in ranking_rows:
        game_id = str(row["target_game_id"])
        side = str(row["team_side"])
        sides = by_game.setdefault(game_id, {})
        if side in sides:
            raise ValueError(f"duplicate rankings game/side: {game_id}/{side}")
        sides[side] = row

    output: list[dict[str, Any]] = []
    by_season: dict[str, dict[str, int]] = {}
    for feature in features:
        game_id = str(feature["target_game_id"])
        sides = by_game.get(game_id)
        if not sides or set(sides) != {"HOME", "AWAY"}:
            raise ValueError(f"rankings join is not exactly two-sided: {game_id}")
        home, away = sides["HOME"], sides["AWAY"]
        if str(home["canonical_team_id"]) != str(feature["home_team_id"]):
            raise ValueError(f"home rankings identity mismatch: {game_id}")
        if str(away["canonical_team_id"]) != str(feature["away_team_id"]):
            raise ValueError(f"away rankings identity mismatch: {game_id}")
        if str(home["cutoff_utc"]) != str(feature["cutoff_utc"]) or str(away["cutoff_utc"]) != str(feature["cutoff_utc"]):
            raise ValueError(f"rankings cutoff mismatch: {game_id}")
        if bool(home["poll_available"]) != bool(away["poll_available"]):
            raise ValueError(f"rankings poll availability mismatch: {game_id}")
        for row in (home, away):
            known = row.get("poll_first_eligible_at_utc")
            if known is not None and str(known) > str(feature["cutoff_utc"]):
                raise ValueError(f"future rankings evidence: {game_id}")
        home_rank, away_rank = home.get("rank"), away.get("rank")
        item = dict(feature)
        item.update(
            {
                "ap_rank_diff": (
                    float(away_rank) - float(home_rank)
                    if home_rank is not None and away_rank is not None
                    else None
                ),
                "home_ap_rank_observed": float(home_rank is not None),
                "away_ap_rank_observed": float(away_rank is not None),
                "ap_poll_available": float(bool(home["poll_available"])),
                "home_ap_listed": float(bool(home["team_listed_in_poll"])),
                "away_ap_listed": float(bool(away["team_listed_in_poll"])),
                "home_ap_feature_row_id": str(home["feature_row_id"]),
                "away_ap_feature_row_id": str(away["feature_row_id"]),
                "home_ap_source_observation_id": home.get("source_observation_id"),
                "away_ap_source_observation_id": away.get("source_observation_id"),
                "rankings_target_outcome_in_feature_evidence": False,
            }
        )
        output.append(item)
        season = str(item["season"])
        stats = by_season.setdefault(season, {"rows": 0, "both_numeric": 0, "poll_available": 0})
        stats["rows"] += 1
        stats["both_numeric"] += int(home_rank is not None and away_rank is not None)
        stats["poll_available"] += int(bool(home["poll_available"]))
    if len(output) != len(features):
        raise ValueError("rankings augmentation changed target-game population")
    return output, {
        "rows": len(output),
        "unmatched_games": 0,
        "by_season": by_season,
        "rank_diff_missing": sum(row["ap_rank_diff"] is None for row in output),
    }
