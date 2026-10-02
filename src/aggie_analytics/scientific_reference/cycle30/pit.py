"""Independent PIT reconstruction that challenges the producer specification.

Winner is recomputed from scores. Both-win, complementary-point failures, and
missing publication receipts cannot become PROVEN. Priors are rebuilt by
filtering completed games per team rather than copying the producer cursor.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from aggie_analytics.scientific_reference.cycle30.metrics import (
    brier_score,
    directional_accuracy,
    log_loss,
)
from aggie_analytics.scientific_reference.cycle30.temporal import (
    PRECISION_UNKNOWN,
    completion_bound,
    earliest_start_bound,
    parse_aware_utc,
    resolve_precision,
)

EXPOSED_NON_BLIND = {2024, 2025}
TIE_POLICY = "EXCLUDE_TIES_FROM_BINARY_ESTIMAND"
SOURCE_UNPROVEN = "SOURCE_AUTHORITY_UNPROVEN"


class IndependentPitError(ValueError):
    """Raised when independent kernel reconstruction fails."""


def winner_from_scores(home_points: int, away_points: int) -> str:
    if home_points > away_points:
        return "HOME"
    if away_points > home_points:
        return "AWAY"
    return "TIE"


def challenge_game(
    game: Mapping[str, Any], outcomes: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    home = str(game["home_canonical_team_id"])
    away = str(game["away_canonical_team_id"])
    if home == away:
        raise IndependentPitError("participants are not distinct")
    by_team = {str(row["canonical_team_id"]): row for row in outcomes}
    if set(by_team) != {home, away} or len(outcomes) != 2:
        raise IndependentPitError("oriented outcomes do not match participants")
    home_for = int(by_team[home]["points_for"])
    away_for = int(by_team[away]["points_for"])
    if int(by_team[home]["points_against"]) != away_for:
        raise IndependentPitError("home points_against is not away points_for")
    if int(by_team[away]["points_against"]) != home_for:
        raise IndependentPitError("away points_against is not home points_for")
    if int(by_team[home]["margin"]) != home_for - int(by_team[home]["points_against"]):
        raise IndependentPitError("home margin disagrees with points")
    if int(by_team[away]["margin"]) != away_for - int(by_team[away]["points_against"]):
        raise IndependentPitError("away margin disagrees with points")
    if int(by_team[home]["margin"]) + int(by_team[away]["margin"]) != 0:
        raise IndependentPitError("margins are not antisymmetric")
    winner = winner_from_scores(home_for, away_for)
    if (
        by_team[home].get("label_win") is True
        and by_team[away].get("label_win") is True
    ):
        raise IndependentPitError("both teams labeled winners")
    if winner == "TIE" and (
        by_team[home].get("label_win") is True or by_team[away].get("label_win") is True
    ):
        raise IndependentPitError("tie mapped to a binary win/loss")
    return {
        "winner": winner,
        "tie": winner == "TIE",
        "home_points": home_for,
        "away_points": away_for,
        "tie_policy": TIE_POLICY,
    }


def _ratio(numerator: float, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 12)


def _prefix_features(
    played: Sequence[Mapping[str, Any]], season: int
) -> dict[str, Any]:
    games_n = 0
    wins = 0
    points_for = 0
    points_against = 0
    margin = 0
    by_season: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for row in played:
        games_n += 1
        won = 0 if row["tie"] else (1 if row.get("label_win") else 0)
        wins += won
        points_for += int(row["points_for"])
        points_against += int(row["points_against"])
        margin += int(row["margin"])
        bucket = by_season[int(row["season"])]
        bucket[0] += 1
        bucket[1] += won
    previous = by_season.get(season - 1, [0, 0])
    current = by_season.get(season, [0, 0])
    return {
        "pit_prior_games_played": games_n,
        "pit_prior_margin_mean": _ratio(margin, games_n),
        "pit_prior_points_against_mean": _ratio(points_against, games_n),
        "pit_prior_points_for_mean": _ratio(points_for, games_n),
        "pit_prior_season_win_rate": _ratio(previous[1], previous[0]),
        "pit_prior_win_rate": _ratio(wins, games_n),
        "pit_season_to_date_games": current[0],
        "pit_season_to_date_win_rate": _ratio(current[1], current[0]),
    }


def _prior_authority_class(
    *,
    prior_game_id: str,
    prior_complete_utc: Any,
    observation: Mapping[str, Any],
    authorities: Mapping[str, Mapping[str, Any]] | None,
) -> str:
    prior_auth = (authorities or {}).get(prior_game_id, {})
    cutoff = parse_aware_utc(
        str(
            observation.get("target_cutoff_utc")
            or observation.get("start_date_utc_text")
            or ""
        )
    )
    known_at = parse_aware_utc(
        str(
            prior_auth.get("known_at_utc")
            or prior_complete_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        )
    )
    effective = parse_aware_utc(
        str(
            prior_auth.get("effective_utc")
            or prior_complete_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        )
    )
    if known_at > cutoff or effective > cutoff:
        return SOURCE_UNPROVEN
    publication = prior_auth.get("source_publication_utc")
    if publication:
        published = parse_aware_utc(str(publication))
        if published > cutoff:
            raise IndependentPitError("future publication cannot admit a prior")
        if known_at < published:
            raise IndependentPitError("known-at precedes declared source publication")
    if prior_auth.get("suspended") or prior_auth.get("future_publication"):
        raise IndependentPitError("suspended or future-publication counterexample")
    return (
        "PROVEN_PIT_TRAINING_ROW" if publication else "RETROSPECTIVE_BOUNDED_CANDIDATE"
    )


def reconstruct_game_features(
    games: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
    *,
    authorities: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    policy = {
        "date_only_start_offset_days": -1,
        "date_only_completion_offset_days": 2,
        "published_duration_hours": 12.0,
    }
    by_outcome: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in outcomes:
        by_outcome[str(row["canonical_game_id"])].append(row)
    validated: dict[str, dict[str, Any]] = {}
    precision: dict[str, str] = {}
    completions: dict[str, Any] = {}
    earliest: dict[str, Any] = {}
    for game in games:
        gid = str(game["canonical_game_id"])
        validated[gid] = challenge_game(game, by_outcome.get(gid, []))
        instant = parse_aware_utc(str(game["start_date_utc_text"]))
        precision[gid] = resolve_precision(
            str(game.get("date_precision") or PRECISION_UNKNOWN), instant
        )
        completions[gid] = completion_bound(
            instant, precision=precision[gid], policy=policy
        )
        earliest[gid] = earliest_start_bound(
            instant, precision=precision[gid], policy=policy
        )
    by_team: dict[str, list[tuple[Any, Mapping[str, Any]]]] = defaultdict(list)
    for game in games:
        gid = str(game["canonical_game_id"])
        if gid not in validated:
            continue
        for team_id, slot in (
            (str(game["home_canonical_team_id"]), "home"),
            (str(game["away_canonical_team_id"]), "away"),
        ):
            matching = [
                row
                for row in by_outcome.get(gid, [])
                if str(row["canonical_team_id"]) == team_id
            ]
            if not matching:
                continue
            by_team[team_id].append(
                (
                    completions[gid],
                    {
                        **dict(matching[0]),
                        "season": int(game["season"]),
                        "tie": validated[gid]["tie"],
                        "canonical_game_id": gid,
                    },
                )
            )
    for team_id in by_team:
        by_team[team_id].sort(
            key=lambda item: (item[0], str(item[1]["canonical_game_id"]))
        )
    targets_by_team: dict[str, list[tuple[Any, Mapping[str, Any], str]]] = defaultdict(
        list
    )
    for game in games:
        gid = str(game["canonical_game_id"])
        if int(game["season"]) in EXPOSED_NON_BLIND or validated[gid]["tie"]:
            continue
        instant = parse_aware_utc(str(game["start_date_utc_text"]))
        authority = (authorities or {}).get(gid, {})
        if authority.get("source_publication_utc"):
            published = parse_aware_utc(str(authority["source_publication_utc"]))
            if published > instant:
                raise IndependentPitError("future publication cannot admit a prior")
            verdict = "PROVEN_PIT_TRAINING_ROW"
        else:
            verdict = "RETROSPECTIVE_BOUNDED_CANDIDATE"
        home = str(game["home_canonical_team_id"])
        away = str(game["away_canonical_team_id"])
        targets_by_team[home].append((earliest[gid], game, verdict))
        targets_by_team[away].append((earliest[gid], game, verdict))
    rows: list[dict[str, Any]] = []
    for team_id, targets in targets_by_team.items():
        targets.sort(key=lambda item: (item[0], str(item[1]["canonical_game_id"])))
        completed = by_team.get(team_id, [])
        played: list[Mapping[str, Any]] = []
        cursor = 0
        pending: list[tuple[Any, Mapping[str, Any]]] = []
        for target_start, game, verdict in targets:
            gid = str(game["canonical_game_id"])
            while cursor < len(completed) and completed[cursor][0] <= target_start:
                pending.append(completed[cursor])
                cursor += 1
            remaining: list[tuple[Any, Mapping[str, Any]]] = []
            for prior_complete, prior in pending:
                prior_gid = str(prior["canonical_game_id"])
                prior_auth = (authorities or {}).get(prior_gid, {})
                class_ = _prior_authority_class(
                    prior_game_id=prior_gid,
                    prior_complete_utc=prior_complete,
                    observation=game,
                    authorities=authorities,
                )
                if class_ == SOURCE_UNPROVEN and not prior_auth.get(
                    "allow_retrospective_prior"
                ):
                    remaining.append((prior_complete, prior))
                    continue
                played.append(prior)
            pending = remaining
            feat = _prefix_features(
                [prior for prior in played if str(prior["canonical_game_id"]) != gid],
                int(game["season"]),
            )
            orientation = (
                "HOME" if str(game["home_canonical_team_id"]) == team_id else "AWAY"
            )
            rows.append(
                {
                    "canonical_game_id": gid,
                    "canonical_team_id": team_id,
                    "orientation": orientation,
                    "row_verdict": verdict,
                    **feat,
                }
            )
    rows.sort(key=lambda row: (row["canonical_game_id"], row["canonical_team_id"]))
    return rows


COMPARE_KEYS = (
    "pit_prior_games_played",
    "pit_prior_margin_mean",
    "pit_prior_points_against_mean",
    "pit_prior_points_for_mean",
    "pit_prior_season_win_rate",
    "pit_prior_win_rate",
    "pit_season_to_date_games",
    "pit_season_to_date_win_rate",
)


def challenge_kernel_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Fail closed on flipped labels and impossible reconstructed priors."""

    challenged = 0
    for row in rows:
        home_points = row.get("home_points")
        away_points = row.get("away_points")
        if home_points is not None and away_points is not None:
            winner = winner_from_scores(int(home_points), int(away_points))
            label = row.get("home_win_label")
            if winner == "TIE":
                if label is True:
                    raise IndependentPitError("tie mapped to a binary home win")
            elif label is not None and bool(label) != (winner == "HOME"):
                raise IndependentPitError("label disagrees with scores")
            challenged += 1
        for feat in (row.get("home_features") or {}, row.get("away_features") or {}):
            margin = feat.get("pit_prior_margin_mean")
            if margin is None:
                continue
            try:
                numeric = float(margin)
            except (TypeError, ValueError) as exc:
                raise IndependentPitError("prior margin is not numeric") from exc
            if abs(numeric) > 80:
                raise IndependentPitError(
                    "prior margin is not independently reconstructable"
                )
            challenged += 1
    return {"rows": len(rows), "checks": challenged, "matched": True}


def compare_producer_rows(
    producer_rows: Sequence[Mapping[str, Any]],
    reconstructed: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not reconstructed:
        raise IndependentPitError("independent reconstruction is empty")
    producer_features: dict[tuple[str, str], Mapping[str, Any]] = {}
    producer_labels: dict[str, Any] = {}
    for prow in producer_rows:
        gid = str(prow.get("canonical_game_id"))
        if "home_win_label" in prow:
            producer_labels[gid] = prow.get("home_win_label")
        if "home_features" in prow:
            producer_features[(gid, str(prow.get("home_canonical_team_id")))] = prow[
                "home_features"
            ]
            producer_features[(gid, str(prow.get("away_canonical_team_id")))] = prow[
                "away_features"
            ]
        else:
            producer_features[(gid, str(prow.get("canonical_team_id")))] = prow
    matches = 0
    for row in reconstructed:
        key = (str(row["canonical_game_id"]), str(row["canonical_team_id"]))
        parent = producer_features.get(key)
        if parent is None:
            raise IndependentPitError(
                "independent reconstruction row has no producer match"
            )
        for field in COMPARE_KEYS:
            if parent.get(field) != row.get(field):
                raise IndependentPitError(
                    f"independent reconstruction disagrees on {field}"
                )
        if "home_win_label" in row and str(row["canonical_game_id"]) in producer_labels:
            if producer_labels[str(row["canonical_game_id"])] != row.get("home_win_label"):
                raise IndependentPitError("independent reconstruction disagrees on label")
        matches += 1
    challenge_kernel_rows(producer_rows)
    return {
        "matched_team_rows": matches,
        "reconstructed_count": len(reconstructed),
        "matched": True,
    }


def scoring_metrics(
    predicted: Sequence[float], observed: Sequence[float], unique_games: int
) -> dict[str, Any]:
    if unique_games != len(predicted):
        raise IndependentPitError("metrics must be computed at unique-game grain")
    directional = directional_accuracy(predicted, observed)
    return {
        "unique_games": unique_games,
        "brier": brier_score(predicted, observed),
        "log_loss": log_loss(predicted, observed),
        "directional": directional,
        "home_choice_prevalence_is_not_skill": True,
    }
