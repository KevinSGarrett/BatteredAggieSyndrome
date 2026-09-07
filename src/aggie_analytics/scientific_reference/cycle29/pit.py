"""Independent PIT kernel reconstruction.

Must not import ``aggie_analytics.cycle29`` or ``aggie_analytics.data``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from aggie_analytics.scientific_reference.cycle29.metrics import (
    brier_score,
    directional_accuracy,
    log_loss,
)
from aggie_analytics.scientific_reference.cycle29.temporal import (
    completion_bound,
    earliest_start_bound,
    parse_aware_utc,
)

SEALED = {2024, 2025}


class IndependentPitError(ValueError):
    """Raised when independent kernel reconstruction fails."""


def _ratio(numerator: float, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 12)


class IndependentPrior:
    def __init__(self) -> None:
        self.games = 0
        self.wins = 0
        self.points_for = 0
        self.points_against = 0
        self.margin = 0
        self.by_season: dict[int, list[int]] = defaultdict(lambda: [0, 0])

    def admit(self, outcome: Mapping[str, Any]) -> None:
        self.games += 1
        won = 1 if outcome.get("label_win") else 0
        self.wins += won
        self.points_for += int(outcome.get("points_for") or 0)
        self.points_against += int(outcome.get("points_against") or 0)
        self.margin += int(outcome.get("margin") or 0)
        bucket = self.by_season[int(outcome["season"])]
        bucket[0] += 1
        bucket[1] += won

    def emit(self, season: int) -> dict[str, Any]:
        previous = self.by_season.get(season - 1, [0, 0])
        return {
            "pit_prior_games_played": self.games,
            "pit_prior_win_rate": _ratio(self.wins, self.games),
            "pit_prior_season_win_rate": _ratio(previous[1], previous[0]),
        }


def reconstruct_game_features(
    games: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    policy = {
        "date_only_start_offset_days": -1,
        "date_only_completion_offset_days": 2,
        "published_duration_hours": 12.0,
    }
    by_outcome: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in outcomes:
        by_outcome[str(row["canonical_game_id"])].append(row)
    by_team: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    starts = {}
    for game in games:
        gid = str(game["canonical_game_id"])
        instant = parse_aware_utc(str(game["start_date_utc_text"]))
        starts[gid] = instant
        by_team[str(game["home_canonical_team_id"])].append(
            {**dict(game), "canonical_team_id": game["home_canonical_team_id"]}
        )
        by_team[str(game["away_canonical_team_id"])].append(
            {**dict(game), "canonical_team_id": game["away_canonical_team_id"]}
        )
    rows: list[dict[str, Any]] = []
    for team_id, observations in by_team.items():
        targets = []
        priors = []
        for observation in observations:
            gid = str(observation["canonical_game_id"])
            instant = starts[gid]
            matching = [
                row
                for row in by_outcome.get(gid, [])
                if str(row["canonical_team_id"]) == team_id
            ]
            if not matching:
                continue
            targets.append((earliest_start_bound(instant, policy), observation))
            priors.append((completion_bound(instant, policy), matching[0]))
        targets.sort(key=lambda item: (item[0], str(item[1]["canonical_game_id"])))
        priors.sort(key=lambda item: (item[0], str(item[1]["canonical_game_id"])))
        acc = IndependentPrior()
        cursor = 0
        for earliest, observation in targets:
            while cursor < len(priors) and priors[cursor][0] <= earliest:
                acc.admit(priors[cursor][1])
                cursor += 1
            if int(observation["season"]) in SEALED:
                continue
            rows.append(
                {
                    "canonical_game_id": str(observation["canonical_game_id"]),
                    "canonical_team_id": team_id,
                    **acc.emit(int(observation["season"])),
                }
            )
    rows.sort(key=lambda row: (row["canonical_game_id"], row["canonical_team_id"]))
    return rows


def compare_producer_rows(
    producer_rows: Sequence[Mapping[str, Any]],
    reconstructed: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    # Producer game-grain rows store home/away features.
    matches = 0
    for row in reconstructed:
        key = (str(row["canonical_game_id"]), str(row["canonical_team_id"]))
        parent = None
        for prow in producer_rows:
            if str(prow.get("canonical_game_id")) != key[0]:
                continue
            if key[1] == str(prow.get("home_canonical_team_id")):
                parent = prow.get("home_features") or prow
            elif key[1] == str(prow.get("away_canonical_team_id")):
                parent = prow.get("away_features") or prow
        if parent is None:
            continue
        if parent.get("pit_prior_games_played") != row.get("pit_prior_games_played"):
            raise IndependentPitError("independent prior games_played disagrees")
        matches += 1
    return {"matched_team_rows": matches, "reconstructed_count": len(reconstructed)}


def scoring_metrics(
    predicted: Sequence[float], observed: Sequence[float], unique_games: int
) -> dict[str, Any]:
    if unique_games != len(predicted):
        raise IndependentPitError("metrics must be computed at unique-game grain")
    return {
        "unique_games": unique_games,
        "brier": brier_score(predicted, observed),
        "log_loss": log_loss(predicted, observed),
        "directional": directional_accuracy(predicted, observed),
    }
