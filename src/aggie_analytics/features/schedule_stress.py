from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


CLASSIFICATION = "PRELIMINARY_UNPROTECTED_EVENT_CHRONOLOGY_ONLY"


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def stable_hash(value: object) -> str:
    return sha256(canonical_json(value)).hexdigest()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone aware")
    return parsed


def mean(values: Iterable[float]) -> float | None:
    items = list(values)
    return None if not items else sum(items) / len(items)


def _team_state() -> dict[str, Any]:
    return {"games": 0, "win_sum": 0.0, "margin_sum": 0.0, "history": []}


def _snapshot(
    state: Mapping[str, Any], target: Mapping[str, Any], team_id: str, role: str
) -> dict[str, Any]:
    start = parse_utc(str(target["start_utc"]))
    history = list(state["history"])
    recent = history[-5:]
    windows = {
        days: [
            row
            for row in history
            if 0.0 < (start - row["start"]).total_seconds() / 86400.0 <= days
        ]
        for days in (7, 14, 28)
    }
    consecutive = 0
    for row in reversed(history):
        if row["away_or_neutral"]:
            consecutive += 1
        else:
            break
    evidence_ids = [str(row["game_id"]) for row in history]
    evidence_starts = [row["start"] for row in history]
    last_start = evidence_starts[-1] if evidence_starts else None
    source_max = max(evidence_starts).isoformat().replace("+00:00", "Z") if evidence_starts else None
    return {
        "classification": CLASSIFICATION,
        "game_id": str(target["target_game_id"]),
        "season": int(target["season"]),
        "season_type": str(target["season_type"]),
        "week": int(target["week"]),
        "start_utc": str(target["start_utc"]),
        "cutoff_utc": str(target["cutoff_utc"]),
        "team_id": team_id,
        "opponent_team_id": str(
            target["away_team_id"] if role == "HOME" else target["home_team_id"]
        ),
        "team_role": role,
        "neutral_site": bool(target["neutral_site"]),
        "prior_game_count": len(history),
        "prior_season_game_count": sum(
            int(row["season"]) == int(target["season"]) for row in history
        ),
        "days_since_last_game_start": (
            None if last_start is None else (start - last_start).total_seconds() / 86400.0
        ),
        "games_last_7d": len(windows[7]),
        "games_last_14d": len(windows[14]),
        "games_last_28d": len(windows[28]),
        "away_or_neutral_games_last_28d": sum(
            bool(row["away_or_neutral"]) for row in windows[28]
        ),
        "consecutive_away_or_neutral_games": consecutive,
        "recent_5_margin_mean": mean(float(row["margin"]) for row in recent),
        "recent_5_opponent_pregame_win_share_mean": mean(
            float(row["opponent_pregame_win_share"])
            for row in recent
            if row["opponent_pregame_win_share"] is not None
        ),
        "recent_5_opponent_adjusted_margin_mean": mean(
            float(row["opponent_adjusted_margin"])
            for row in recent
            if row["opponent_adjusted_margin"] is not None
        ),
        "cold_start": not history,
        "evidence_game_count": len(evidence_ids),
        "evidence_game_ids_sha256": stable_hash(evidence_ids),
        "evidence_source_start_utc_max": source_max,
        "historical_original_pit_eligible": False,
        "event_chronology_eligible": True,
        "protected_eligible": False,
    }


def materialize(
    rows: Iterable[Mapping[str, Any]], target_seasons: set[int]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    games = sorted(
        (dict(row) for row in rows),
        key=lambda row: (str(row["start_utc"]), str(row["target_game_id"])),
    )
    if len({str(row["target_game_id"]) for row in games}) != len(games):
        raise ValueError("source game identities must be unique")
    states: defaultdict[str, dict[str, Any]] = defaultdict(_team_state)
    pending_index = 0
    features: list[dict[str, Any]] = []

    def admit(game: Mapping[str, Any]) -> None:
        home_id, away_id = str(game["home_team_id"]), str(game["away_team_id"])
        home, away = states[home_id], states[away_id]
        home_margin = float(game["margin"])
        home_prior_margin = home["margin_sum"] / home["games"] if home["games"] else None
        away_prior_margin = away["margin_sum"] / away["games"] if away["games"] else None
        home_expected = (
            None
            if home_prior_margin is None or away_prior_margin is None
            else home_prior_margin - away_prior_margin
        )
        home_residual = None if home_expected is None else home_margin - home_expected
        home_opp_win = away["win_sum"] / away["games"] if away["games"] else None
        away_opp_win = home["win_sum"] / home["games"] if home["games"] else None
        start = parse_utc(str(game["start_utc"]))
        neutral = bool(game["neutral_site"])
        for team, margin, opponent_win, residual, away_or_neutral in (
            (home, home_margin, home_opp_win, home_residual, neutral),
            (away, -home_margin, away_opp_win, None if home_residual is None else -home_residual, True),
        ):
            team["history"].append(
                {
                    "game_id": str(game["target_game_id"]),
                    "season": int(game["season"]),
                    "start": start,
                    "margin": margin,
                    "opponent_pregame_win_share": opponent_win,
                    "opponent_adjusted_margin": residual,
                    "away_or_neutral": away_or_neutral,
                }
            )
            team["games"] += 1
            team["margin_sum"] += margin
        home_win = float(game["home_win"])
        home["win_sum"] += home_win
        away["win_sum"] += 1.0 - home_win

    for target in games:
        cutoff = parse_utc(str(target["cutoff_utc"]))
        while pending_index < len(games) and parse_utc(
            str(games[pending_index]["start_utc"])
        ) < cutoff:
            admit(games[pending_index])
            pending_index += 1
        if int(target["season"]) not in target_seasons:
            continue
        home = _snapshot(states[str(target["home_team_id"])], target, str(target["home_team_id"]), "HOME")
        away = _snapshot(states[str(target["away_team_id"])], target, str(target["away_team_id"]), "AWAY")
        for item in (home, away):
            if str(target["target_game_id"]) in {
                str(row["game_id"]) for row in states[item["team_id"]]["history"]
            }:
                raise ValueError("target game entered its own feature evidence")
            item["feature_row_identity"] = stable_hash(item)
            features.append(item)
    features.sort(key=lambda row: (row["start_utc"], row["game_id"], row["team_role"]))
    diagnostics = {
        "source_games": len(games),
        "target_games": len({row["game_id"] for row in features}),
        "target_team_rows": len(features),
        "cold_start_rows": sum(bool(row["cold_start"]) for row in features),
        "missing_days_since_last": sum(row["days_since_last_game_start"] is None for row in features),
        "missing_recent_opponent_strength": sum(
            row["recent_5_opponent_pregame_win_share_mean"] is None for row in features
        ),
        "missing_recent_opponent_adjusted_margin": sum(
            row["recent_5_opponent_adjusted_margin_mean"] is None for row in features
        ),
    }
    return features, diagnostics
