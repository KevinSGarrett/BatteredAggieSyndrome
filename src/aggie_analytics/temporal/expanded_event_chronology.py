from __future__ import annotations

"""Conservative event-chronology features for preliminary research only.

These helpers deliberately do not manufacture a historical publication or
known-at timestamp.  A prior outcome can contribute only from a strictly
earlier official season/week batch and only when its game start precedes the
target cutoff.  The resulting rows are useful for shadow team-strength
research but are not historical-known-at/PIT eligible.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from typing import Any, Iterable, Mapping

from .contracts import parse_time


CLASSIFICATION = "PRELIMINARY_UNPROTECTED_EVENT_CHRONOLOGY_ONLY"
POLICY_VERSION = "expanded-event-chronology-week-batched-v1"


def _stable_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _text(row: Mapping[str, Any], key: str) -> str:
    value = str(row.get(key) or "").strip()
    if not value:
        raise ValueError(f"{key} must be nonempty")
    return value


def _time(row: Mapping[str, Any], key: str) -> datetime:
    value = parse_time(row.get(key))
    if value is None:
        raise ValueError(f"{key} must be a timezone-aware timestamp")
    return value.astimezone(timezone.utc)


def _season_type_order(value: str) -> int:
    normalized = value.strip().lower()
    if normalized in {"regular", "regular_season", "2"}:
        return 0
    if normalized in {"postseason", "post_season", "3"}:
        return 1
    raise ValueError(f"unsupported season_type for event chronology: {value}")


def batch_key(row: Mapping[str, Any]) -> tuple[int, int, int]:
    return (
        int(row["season"]),
        _season_type_order(_text(row, "season_type")),
        int(row["week"]),
    )


def _normalized_game(row: Mapping[str, Any]) -> dict[str, Any]:
    game_id = _text(row, "target_game_id")
    home_team_id = _text(row, "home_team_id")
    away_team_id = _text(row, "away_team_id")
    if home_team_id == away_team_id:
        raise ValueError("home and away team identities must differ")
    home_points = int(row["home_points"])
    away_points = int(row["away_points"])
    if home_points < 0 or away_points < 0:
        raise ValueError("outcome scores must be nonnegative")
    start = _time(row, "start_utc")
    normalized = {
        **dict(row),
        "target_game_id": game_id,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "season": int(row["season"]),
        "season_type": _text(row, "season_type"),
        "week": int(row["week"]),
        "start_utc": start.isoformat().replace("+00:00", "Z"),
        "home_points": home_points,
        "away_points": away_points,
        "neutral_site": bool(row.get("neutral_site", False)),
    }
    normalized["batch_key"] = batch_key(normalized)
    return normalized


def _team_observation(
    game: Mapping[str, Any], *, home: bool
) -> dict[str, Any]:
    points_for = int(game["home_points"] if home else game["away_points"])
    points_against = int(game["away_points"] if home else game["home_points"])
    team_id = str(game["home_team_id"] if home else game["away_team_id"])
    observation_id = "event_outcome_" + _stable_hash(
        {
            "target_game_id": game["target_game_id"],
            "team_id": team_id,
            "side": "HOME" if home else "AWAY",
            "evidence": game.get("target_source_record_sha256")
            or game.get("source_record_evidence_sha256"),
        }
    )[:24]
    return {
        "observation_id": observation_id,
        "target_game_id": game["target_game_id"],
        "team_id": team_id,
        "points_for": points_for,
        "points_against": points_against,
        "win": float(points_for > points_against),
        "tie": float(points_for == points_against),
        "start_utc": game["start_utc"],
        "batch_key": tuple(game["batch_key"]),
    }


def _prior_summary(
    observations: Iterable[Mapping[str, Any]],
    *,
    target_game_id: str,
    target_batch: tuple[int, int, int],
    cutoff: datetime,
) -> dict[str, Any]:
    eligible = [
        row
        for row in observations
        if tuple(row["batch_key"]) < target_batch
        and row["target_game_id"] != target_game_id
        and _time(row, "start_utc") < cutoff
    ]
    eligible.sort(key=lambda row: (_time(row, "start_utc"), row["observation_id"]))
    if not eligible:
        return {
            "games": 0,
            "win_rate": None,
            "points_for_mean": None,
            "points_against_mean": None,
            "lineage_sha256": _stable_hash(
                {
                    "target_game_id": target_game_id,
                    "target_batch": target_batch,
                    "eligible_observation_ids": [],
                    "policy": POLICY_VERSION,
                }
            ),
            "observation_count": 0,
        }
    games = len(eligible)
    wins_with_half_ties = sum(float(row["win"]) + 0.5 * float(row["tie"]) for row in eligible)
    ids = [str(row["observation_id"]) for row in eligible]
    return {
        "games": games,
        "win_rate": wins_with_half_ties / games,
        "points_for_mean": sum(int(row["points_for"]) for row in eligible) / games,
        "points_against_mean": sum(int(row["points_against"]) for row in eligible) / games,
        "lineage_sha256": _stable_hash(
            {
                "target_game_id": target_game_id,
                "target_batch": target_batch,
                "eligible_observation_ids": ids,
                "policy": POLICY_VERSION,
            }
        ),
        "observation_count": games,
    }


def build_event_chronology_features(
    games: Iterable[Mapping[str, Any]],
    *,
    cutoff_lead: timedelta = timedelta(hours=24),
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if cutoff_lead <= timedelta(0):
        raise ValueError("cutoff_lead must be positive")
    normalized = [_normalized_game(row) for row in games]
    normalized.sort(key=lambda row: (_time(row, "start_utc"), row["target_game_id"]))
    ids = [row["target_game_id"] for row in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate target game identity")

    observations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for game in normalized:
        observations[str(game["home_team_id"])].append(_team_observation(game, home=True))
        observations[str(game["away_team_id"])].append(_team_observation(game, home=False))

    features: list[dict[str, Any]] = []
    same_batch_candidates = 0
    future_start_candidates = 0
    for game in normalized:
        game_id = str(game["target_game_id"])
        target_batch = tuple(game["batch_key"])
        cutoff = _time(game, "start_utc") - cutoff_lead
        for team_id in (str(game["home_team_id"]), str(game["away_team_id"])):
            for observation in observations.get(team_id, ()):  # negative-evidence accounting
                if observation["target_game_id"] == game_id:
                    continue
                if tuple(observation["batch_key"]) == target_batch:
                    same_batch_candidates += 1
                elif _time(observation, "start_utc") >= cutoff:
                    future_start_candidates += 1

        home = _prior_summary(
            observations.get(str(game["home_team_id"]), ()),
            target_game_id=game_id,
            target_batch=target_batch,
            cutoff=cutoff,
        )
        away = _prior_summary(
            observations.get(str(game["away_team_id"]), ()),
            target_game_id=game_id,
            target_batch=target_batch,
            cutoff=cutoff,
        )

        def difference(name: str) -> float | None:
            left, right = home[name], away[name]
            return None if left is None or right is None else float(left) - float(right)

        lineage = _stable_hash(
            {
                "target_game_id": game_id,
                "cutoff_utc": cutoff.isoformat(),
                "home_prior_lineage_sha256": home["lineage_sha256"],
                "away_prior_lineage_sha256": away["lineage_sha256"],
                "policy": POLICY_VERSION,
            }
        )
        features.append(
            {
                "classification": CLASSIFICATION,
                "target_game_id": game_id,
                "season": int(game["season"]),
                "season_type": str(game["season_type"]),
                "week": int(game["week"]),
                "start_utc": game["start_utc"],
                "cutoff_utc": cutoff.isoformat().replace("+00:00", "Z"),
                "home_team_id": str(game["home_team_id"]),
                "away_team_id": str(game["away_team_id"]),
                "neutral_site": float(bool(game["neutral_site"])),
                "home_field": float(not bool(game["neutral_site"])),
                "prior_win_rate_diff": difference("win_rate"),
                "prior_points_for_mean_diff": difference("points_for_mean"),
                "prior_points_against_mean_diff": difference("points_against_mean"),
                "log1p_prior_games_diff": math.log1p(home["games"])
                - math.log1p(away["games"]),
                "home_cold_start": float(home["games"] == 0),
                "away_cold_start": float(away["games"] == 0),
                "home_prior_games": int(home["games"]),
                "away_prior_games": int(away["games"]),
                "home_prior_lineage_sha256": home["lineage_sha256"],
                "away_prior_lineage_sha256": away["lineage_sha256"],
                "feature_lineage_sha256": lineage,
                "target_outcome_in_feature_evidence": False,
                "historical_known_at_eligible": False,
                "event_chronology_policy_version": POLICY_VERSION,
                "event_chronology_eligibility": "PRELIMINARY_ONLY_NOT_HISTORICAL_KNOWN_AT",
            }
        )
    report = {
        "classification": CLASSIFICATION,
        "policy_version": POLICY_VERSION,
        "games": len(normalized),
        "feature_rows": len(features),
        "seasons": sorted({int(row["season"]) for row in normalized}),
        "cold_start_games": sum(
            bool(row["home_cold_start"] or row["away_cold_start"]) for row in features
        ),
        "same_batch_candidates_excluded": same_batch_candidates,
        "future_or_cutoff_candidates_excluded": future_start_candidates,
        "target_game_evidence_rows": 0,
        "historical_known_at_eligible_rows": 0,
    }
    return features, report
