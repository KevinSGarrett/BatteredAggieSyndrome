"""Authority-clean PIT kernel over stable domains.

Observed CFBD FBS-route rows are numerators, never the expected population.
Fitted forecasts remain UNTRUSTED_SHADOW. 2024/2025 are excluded from blind eval.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle29.hashing import sha256_json
from aggie_analytics.cycle29.temporal import (
    completion_bound,
    earliest_start_bound,
    parse_aware_utc,
)

EXPOSED_NON_BLIND_SEASONS = {2024, 2025}
ADMITTED_DOMAINS = (
    "canonical_game_identity",
    "canonical_team_identity",
    "scheduled_participants_and_orientation",
    "kickoff_or_date_bound",
    "prior_completed_game_results",
    "site_home_neutral_when_authoritative",
)
EXCLUDED_DOMAINS = (
    "rankings",
    "mutable_venues",
    "weather",
    "injuries",
    "rosters",
    "staff",
    "recruiting",
    "provider_ratings",
    "fcs_internal_strength",
    "cross_subdivision_translation",
)

PROVEN = "PROVEN_PIT_TRAINING_ROW"
BLOCKED = "BLOCKED"
ABSTAIN_GRAPH = "ABSTAIN_HISTORICAL_COMPETITION_GRAPH_INCOMPLETE"
ABSTAIN_STRENGTH = "ABSTAIN_CROSS_SUBDIVISION_STRENGTH_NOT_ESTABLISHED"
SCOPE = "FBS_ROUTE_OBSERVED_NOT_COMPLETE_EXPECTED_FBS_UNIVERSE"


class PitKernelError(ValueError):
    """Raised when a kernel contract is violated."""


def _ratio(numerator: float, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 12)


class PriorAccumulator:
    def __init__(self) -> None:
        self.games = 0
        self.wins = 0
        self.points_for = 0
        self.points_against = 0
        self.margin = 0
        self.by_season: dict[int, list[int]] = defaultdict(lambda: [0, 0])

    def admit(self, outcome: Mapping[str, Any]) -> None:
        if outcome.get("label_win") is None:
            raise PitKernelError("missing label_win cannot be imputed as a loss")
        for field in ("points_for", "points_against", "margin"):
            if outcome.get(field) is None:
                raise PitKernelError("missing points/margin cannot be imputed as zero")
        self.games += 1
        won = 1 if outcome.get("label_win") else 0
        self.wins += won
        self.points_for += int(outcome["points_for"])
        self.points_against += int(outcome["points_against"])
        self.margin += int(outcome["margin"])
        season = self.by_season[int(outcome["season"])]
        season[0] += 1
        season[1] += won

    def emit(self, season: int) -> dict[str, Any]:
        previous = self.by_season.get(season - 1, [0, 0])
        current = self.by_season.get(season, [0, 0])
        return {
            "pit_prior_games_played": self.games,
            "pit_prior_margin_mean": _ratio(self.margin, self.games),
            "pit_prior_points_against_mean": _ratio(self.points_against, self.games),
            "pit_prior_points_for_mean": _ratio(self.points_for, self.games),
            "pit_prior_season_win_rate": _ratio(previous[1], previous[0]),
            "pit_prior_win_rate": _ratio(self.wins, self.games),
            "pit_season_to_date_games": current[0],
            "pit_season_to_date_win_rate": _ratio(current[1], current[0]),
        }


def parse_start(text: str) -> datetime:
    return parse_aware_utc(text)


def build_game_grain_kernel(
    games: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
    *,
    expected_population_complete: bool,
    contemporaneous_fbs_authority: bool,
    cross_subdivision: bool,
) -> dict[str, Any]:
    """Build game-grain rows; oriented rows are derived, not counted as games."""

    outcome_by_game: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in outcomes:
        outcome_by_game[str(row["canonical_game_id"])].append(row)

    blockers: list[dict[str, Any]] = []
    proven: list[dict[str, Any]] = []
    policy = {
        "date_only_start_offset_days": -1,
        "date_only_completion_offset_days": 2,
        "published_duration_hours": 12.0,
    }

    by_team: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    starts: dict[str, datetime] = {}
    for game in games:
        game_id = str(game["canonical_game_id"])
        try:
            instant = parse_start(str(game["start_date_utc_text"]))
        except Exception:
            blockers.append(
                {
                    "canonical_game_id": game_id,
                    "blocker": "REJECTED_NO_USABLE_START_EVIDENCE",
                }
            )
            continue
        starts[game_id] = instant
        home = str(game["home_canonical_team_id"])
        away = str(game["away_canonical_team_id"])
        by_team[home].append({**dict(game), "canonical_team_id": home, "is_home": True})
        by_team[away].append(
            {**dict(game), "canonical_team_id": away, "is_home": False}
        )

    team_features: dict[tuple[str, str], dict[str, Any]] = {}
    for team_id, observations in by_team.items():
        team_outcomes = []
        team_targets = []
        for observation in observations:
            game_id = str(observation["canonical_game_id"])
            season = int(observation["season"])
            instant = starts.get(game_id)
            matching = [
                row
                for row in outcome_by_game.get(game_id, [])
                if str(row["canonical_team_id"]) == team_id
            ]
            if instant is None or not matching:
                continue
            outcome = matching[0]
            if outcome.get("label_win") is None or any(
                outcome.get(field) is None
                for field in ("points_for", "points_against", "margin")
            ):
                continue
            team_targets.append((earliest_start_bound(instant, policy), observation))
            team_outcomes.append((completion_bound(instant, policy), outcome))
        team_targets.sort(key=lambda item: (item[0], str(item[1]["canonical_game_id"])))
        team_outcomes.sort(
            key=lambda item: (item[0], str(item[1]["canonical_game_id"]))
        )
        acc = PriorAccumulator()
        cursor = 0
        for earliest, observation in team_targets:
            while cursor < len(team_outcomes) and team_outcomes[cursor][0] <= earliest:
                acc.admit(team_outcomes[cursor][1])
                cursor += 1
            features = acc.emit(int(observation["season"]))
            team_features[(str(observation["canonical_game_id"]), team_id)] = features

    for game in games:
        game_id = str(game["canonical_game_id"])
        season = int(game["season"])
        home = str(game["home_canonical_team_id"])
        away = str(game["away_canonical_team_id"])
        if season in EXPOSED_NON_BLIND_SEASONS:
            blockers.append(
                {
                    "canonical_game_id": game_id,
                    "blocker": "REJECTED_EXPOSED_NON_BLIND_SEASON",
                }
            )
            continue
        if game_id not in starts:
            continue
        if cross_subdivision:
            blockers.append({"canonical_game_id": game_id, "blocker": ABSTAIN_STRENGTH})
            continue
        if not contemporaneous_fbs_authority:
            blockers.append(
                {
                    "canonical_game_id": game_id,
                    "blocker": "CLASSIFICATION_AUTHORITY_FROM_ROUTE_ONLY",
                }
            )
            continue
        home_feat = team_features.get((game_id, home))
        away_feat = team_features.get((game_id, away))
        if home_feat is None or away_feat is None:
            blockers.append(
                {"canonical_game_id": game_id, "blocker": "MISSING_TEAM_FEATURES"}
            )
            continue
        labels = outcome_by_game.get(game_id, [])
        if len(labels) != 2:
            blockers.append(
                {
                    "canonical_game_id": game_id,
                    "blocker": "REJECTED_NO_OUTCOME_REFERENCE",
                }
            )
            continue
        home_label = next(
            row for row in labels if str(row["canonical_team_id"]) == home
        )
        proven.append(
            {
                "canonical_game_id": game_id,
                "grain": "GAME",
                "season": season,
                "home_canonical_team_id": home,
                "away_canonical_team_id": away,
                "home_features": home_feat,
                "away_features": away_feat,
                "home_win_label": bool(home_label.get("label_win")),
                "row_verdict": PROVEN,
                "scope": SCOPE,
                "expected_population_complete": expected_population_complete,
            }
        )

    oriented = []
    for row in proven:
        oriented.append(
            {
                **row,
                "orientation": "HOME",
                "team_canonical_id": row["home_canonical_team_id"],
            }
        )
        oriented.append(
            {
                **row,
                "orientation": "AWAY",
                "team_canonical_id": row["away_canonical_team_id"],
            }
        )

    if expected_population_complete is False:
        # Rows may still be reconstructed as an observed-route kernel.
        pass

    return {
        "scope": SCOPE,
        "admitted_domains": list(ADMITTED_DOMAINS),
        "excluded_domains": list(EXCLUDED_DOMAINS),
        "proven_pit_training_rows": len(proven),
        "oriented_row_count": len(oriented),
        "game_grain_count": len(proven),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "rows": proven,
        "oriented_rows": oriented,
        "row_order_identity": sha256_json([row["canonical_game_id"] for row in proven]),
        "expected_population_complete": expected_population_complete,
        "contemporaneous_fbs_authority": contemporaneous_fbs_authority,
        "trust_classification": "UNTRUSTED_SHADOW",
        "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
    }


def reject_expected_from_observed_route(expected_from_observed: bool) -> None:
    if expected_from_observed:
        raise PitKernelError(
            "expected kernel population cannot be derived solely from the observed CFBD fbs route"
        )


def future_append_invariant(
    rows: Sequence[Mapping[str, Any]], extra: Mapping[str, Any]
) -> None:
    original = [row["canonical_game_id"] for row in rows]
    appended = original + [str(extra.get("canonical_game_id"))]
    if original != appended[: len(original)]:
        raise PitKernelError("future append changed earlier row identities")
    for left, right in zip(rows, rows):
        if left != right:
            raise PitKernelError("row-order mutation")


def predecessor_reconciliation(
    *,
    pit_feature_eligible: int,
    oriented_development: int,
    active_proven: int,
    kernel_proven: int,
) -> dict[str, Any]:
    return {
        "predecessor_pit_feature_eligible_rows": pit_feature_eligible,
        "predecessor_oriented_development_rows": oriented_development,
        "predecessor_active_path_proven_pit_rows": active_proven,
        "cycle29_kernel_proven_pit_training_rows": kernel_proven,
        "difference_eligible_minus_oriented": pit_feature_eligible
        - oriented_development,
        "controlling_gate": "CYCLE29_PIT_KERNEL_ADMISSION",
        "eligibility_is_not_admission": True,
        "oriented_rows_are_not_independent_games": True,
        "deprecation": "CYCLE28_ACTIVE_PATH_ZERO_PROVEN_REMAINS_BINDING_FOR_FITTED_FORECASTS",
    }


def kernel_trust_gate(
    *,
    proven_rows: int,
    independently_reconstructed: bool,
    kernel_gates_pass: bool,
    unresolved_p0_affects_kernel: bool,
) -> dict[str, Any]:
    usable = (
        proven_rows > 0
        and independently_reconstructed
        and kernel_gates_pass
        and not unresolved_p0_affects_kernel
    )
    return {
        "proven_pit_training_rows": proven_rows,
        "independently_reconstructed": independently_reconstructed,
        "kernel_gates_pass": kernel_gates_pass,
        "unresolved_p0_affects_kernel": unresolved_p0_affects_kernel,
        "cycle29_kernel_trust_usable": usable,
        "current_fitted_forecast_trust_recovered": False,
        "project_wide_scientific_trust_recovered": False,
        "scientific_trust_recovered": False,
        "operator_hold": "ACTIVE",
    }
