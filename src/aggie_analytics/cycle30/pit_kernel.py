"""Authority-clean PIT kernel with independent semantic admission.

Global contemporaneous flags and kickoff+12h are not publication proof.
Historical ties use a predeclared estimand. Future-append rebuilds the kernel.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle30.hashing import sha256_json
from aggie_analytics.cycle30.temporal import (
    PRECISION_UNKNOWN,
    completion_bound,
    earliest_start_bound,
    parse_aware_utc,
    resolve_precision,
)

EXPOSED_NON_BLIND_SEASONS = {2024, 2025}
ADMITTED_DOMAINS = (
    "canonical_game_identity",
    "canonical_team_identity",
    "scheduled_participants_and_orientation",
    "kickoff_or_date_bound",
    "prior_completed_game_results",
    "site_home_neutral_when_authoritative",
    "ordinary_home_exposure",
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
RETROSPECTIVE = "RETROSPECTIVE_BOUNDED_CANDIDATE"
BLOCKED = "BLOCKED"
SOURCE_UNPROVEN = "SOURCE_AUTHORITY_UNPROVEN"
ABSTAIN_GRAPH = "ABSTAIN_HISTORICAL_COMPETITION_GRAPH_INCOMPLETE"
ABSTAIN_STRENGTH = "ABSTAIN_CROSS_SUBDIVISION_STRENGTH_NOT_ESTABLISHED"
ABSTAIN_TIE = "ABSTAIN_TIE_EXCLUDED_FROM_BINARY_ESTIMAND"
SCOPE = "FBS_ROUTE_OBSERVED_NOT_COMPLETE_EXPECTED_FBS_UNIVERSE"

TIE_POLICY_EXCLUDE_BINARY = "EXCLUDE_TIES_FROM_BINARY_ESTIMAND"
TIE_POLICY = TIE_POLICY_EXCLUDE_BINARY


class PitKernelError(ValueError):
    """Raised when a kernel contract is violated."""


def _ratio(numerator: float, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 12)


def _require_int_finite(value: Any, field: str) -> int:
    if isinstance(value, bool) or value is None:
        raise PitKernelError(f"{field} must be an integer")
    if isinstance(value, float) and (not math.isfinite(value) or value != int(value)):
        raise PitKernelError(f"{field} must be a finite integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise PitKernelError(f"{field} must be an integer") from exc
    if not math.isfinite(float(number)):
        raise PitKernelError(f"{field} must be finite")
    return number


def winner_from_scores(home_points: int, away_points: int) -> str:
    if home_points > away_points:
        return "HOME"
    if away_points > home_points:
        return "AWAY"
    return "TIE"


def validate_oriented_outcomes(
    game: Mapping[str, Any], outcomes: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Independent score/label/tie specification. Does not copy accumulators."""

    game_id = str(game["canonical_game_id"])
    home = str(game["home_canonical_team_id"])
    away = str(game["away_canonical_team_id"])
    if home == away:
        raise PitKernelError(f"{game_id}: identical participants")
    if len(outcomes) != 2:
        raise PitKernelError(f"{game_id}: expected two oriented outcomes")
    by_team = {str(row["canonical_team_id"]): row for row in outcomes}
    if set(by_team) != {home, away}:
        raise PitKernelError(f"{game_id}: outcome participants disagree with game")
    home_row = by_team[home]
    away_row = by_team[away]
    home_for = _require_int_finite(home_row.get("points_for"), "home.points_for")
    home_against = _require_int_finite(
        home_row.get("points_against"), "home.points_against"
    )
    away_for = _require_int_finite(away_row.get("points_for"), "away.points_for")
    away_against = _require_int_finite(
        away_row.get("points_against"), "away.points_against"
    )
    if home_for != away_against or away_for != home_against:
        raise PitKernelError(f"{game_id}: oriented points are not complementary")
    home_margin = _require_int_finite(home_row.get("margin"), "home.margin")
    away_margin = _require_int_finite(away_row.get("margin"), "away.margin")
    if home_margin != home_for - home_against:
        raise PitKernelError(f"{game_id}: home margin disagrees with points")
    if away_margin != away_for - away_against:
        raise PitKernelError(f"{game_id}: away margin disagrees with points")
    if home_margin + away_margin != 0:
        raise PitKernelError(f"{game_id}: margins are not antisymmetric")
    game_home = game.get("home_points")
    game_away = game.get("away_points")
    if (
        game_home is not None
        and _require_int_finite(game_home, "game.home_points") != home_for
    ):
        raise PitKernelError(f"{game_id}: game home_points disagrees with outcomes")
    if (
        game_away is not None
        and _require_int_finite(game_away, "game.away_points") != away_for
    ):
        raise PitKernelError(f"{game_id}: game away_points disagrees with outcomes")
    winner = winner_from_scores(home_for, away_for)
    home_win = home_row.get("label_win")
    away_win = away_row.get("label_win")
    if home_win is True and away_win is True:
        raise PitKernelError(f"{game_id}: both teams cannot be labeled winners")
    if winner == "TIE":
        if home_win is True or away_win is True:
            raise PitKernelError(f"{game_id}: tied game cannot have a binary winner")
        if home_row.get("label_tie") is False or away_row.get("label_tie") is False:
            raise PitKernelError(f"{game_id}: tie labels must be preserved")
    else:
        expected_home = winner == "HOME"
        if home_win is not None and bool(home_win) != expected_home:
            raise PitKernelError(f"{game_id}: home label_win disagrees with scores")
        if away_win is not None and bool(away_win) == expected_home:
            raise PitKernelError(f"{game_id}: away label_win disagrees with scores")
    return {
        "canonical_game_id": game_id,
        "winner": winner,
        "home_points": home_for,
        "away_points": away_for,
        "home_margin": home_margin,
        "tie": winner == "TIE",
        "tie_policy": TIE_POLICY,
    }


def validate_row_authority(authority: Mapping[str, Any], *, target_cutoff: str) -> str:
    """Per-row source/effective/known-at/receipt/classification evidence."""

    required = (
        "source_id",
        "effective_utc",
        "known_at_utc",
        "receipt_sha256",
        "classification",
        "evidence_class",
    )
    missing = [field for field in required if not authority.get(field)]
    if missing:
        raise PitKernelError(f"row authority missing {missing}")
    if authority.get("contemporaneous_fbs_authority") is True and not authority.get(
        "source_publication_utc"
    ):
        return SOURCE_UNPROVEN
    cutoff = parse_aware_utc(target_cutoff)
    known_at = parse_aware_utc(str(authority["known_at_utc"]))
    effective = parse_aware_utc(str(authority["effective_utc"]))
    publication = authority.get("source_publication_utc")
    if publication:
        published = parse_aware_utc(str(publication))
        if published > cutoff:
            raise PitKernelError("future publication cannot admit a historical prior")
        if known_at < published:
            raise PitKernelError("known-at precedes declared source publication")
        return PROVEN
    if authority.get("suspended") or authority.get("future_publication"):
        raise PitKernelError("suspended or future-publication counterexample")
    if known_at > cutoff:
        return SOURCE_UNPROVEN
    if effective > cutoff:
        return SOURCE_UNPROVEN
    return RETROSPECTIVE


class PriorAccumulator:
    def __init__(self) -> None:
        self.games = 0
        self.wins = 0
        self.points_for = 0
        self.points_against = 0
        self.margin = 0
        self.by_season: dict[int, list[int]] = defaultdict(lambda: [0, 0])

    def admit(self, outcome: Mapping[str, Any], *, tie: bool) -> None:
        if outcome.get("label_win") is None and not tie:
            raise PitKernelError("missing label_win cannot be imputed as a loss")
        for field in ("points_for", "points_against", "margin"):
            if outcome.get(field) is None:
                raise PitKernelError("missing points/margin cannot be imputed as zero")
        self.games += 1
        won = 0 if tie else (1 if outcome.get("label_win") else 0)
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


def _game_precision(game: Mapping[str, Any]) -> str:
    declared = game.get("date_precision") or game.get("start_precision")
    if declared:
        return str(declared)
    return PRECISION_UNKNOWN


def build_game_grain_kernel(
    games: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
    *,
    expected_population_complete: bool,
    authorities: Mapping[str, Mapping[str, Any]] | None = None,
    target_cutoff_by_game: Mapping[str, str] | None = None,
    contemporaneous_fbs_authority: bool | None = None,
    cross_subdivision: bool = False,
    site_rows: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build game-grain rows after independent semantic admission."""

    del contemporaneous_fbs_authority  # global flags are not source authority
    outcome_by_game: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    seen_outcome_keys: set[tuple[str, str]] = set()
    for row in outcomes:
        key = (str(row["canonical_game_id"]), str(row["canonical_team_id"]))
        if key in seen_outcome_keys:
            raise PitKernelError(f"duplicate outcome key {key}")
        seen_outcome_keys.add(key)
        outcome_by_game[str(row["canonical_game_id"])].append(row)

    seen_games: set[str] = set()
    blockers: list[dict[str, Any]] = []
    proven: list[dict[str, Any]] = []
    retrospective: list[dict[str, Any]] = []
    policy = {
        "date_only_start_offset_days": -1,
        "date_only_completion_offset_days": 2,
        "published_duration_hours": 12.0,
    }

    by_team: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    starts: dict[str, datetime] = {}
    precision: dict[str, str] = {}
    validated: dict[str, dict[str, Any]] = {}
    for game in games:
        game_id = str(game["canonical_game_id"])
        if game_id in seen_games:
            raise PitKernelError(f"duplicate canonical game {game_id}")
        seen_games.add(game_id)
        labels = outcome_by_game.get(game_id, [])
        try:
            validated[game_id] = validate_oriented_outcomes(game, labels)
        except PitKernelError as exc:
            blockers.append({"canonical_game_id": game_id, "blocker": str(exc)})
            continue
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
        precision[game_id] = resolve_precision(
            declared_precision=_game_precision(game), instant=instant
        )
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
            instant = starts.get(game_id)
            matching = [
                row
                for row in outcome_by_game.get(game_id, [])
                if str(row["canonical_team_id"]) == team_id
            ]
            if instant is None or not matching or game_id not in validated:
                continue
            outcome = matching[0]
            earliest, _ = earliest_start_bound(
                instant, precision=precision[game_id], policy=policy
            )
            complete, _ = completion_bound(
                instant, precision=precision[game_id], policy=policy
            )
            team_targets.append((earliest, observation))
            team_outcomes.append(
                (complete, outcome, validated[game_id]["tie"], game_id)
            )
        team_targets.sort(key=lambda item: (item[0], str(item[1]["canonical_game_id"])))
        team_outcomes.sort(
            key=lambda item: (item[0], str(item[1]["canonical_game_id"]))
        )
        acc = PriorAccumulator()
        cursor = 0
        for earliest, observation in team_targets:
            while cursor < len(team_outcomes) and team_outcomes[cursor][0] <= earliest:
                prior_game_id = team_outcomes[cursor][3]
                prior_auth = (authorities or {}).get(prior_game_id, {})
                cutoff = (target_cutoff_by_game or {}).get(
                    str(observation["canonical_game_id"]),
                    observation.get("target_cutoff_utc")
                    or observation.get("start_date_utc_text"),
                )
                try:
                    class_ = validate_row_authority(
                        {
                            "source_id": prior_auth.get("source_id")
                            or observation.get("source_id")
                            or "MISSING",
                            "effective_utc": prior_auth.get("effective_utc")
                            or team_outcomes[cursor][0].strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "known_at_utc": prior_auth.get("known_at_utc")
                            or team_outcomes[cursor][0].strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "receipt_sha256": prior_auth.get("receipt_sha256")
                            or "UNPROVEN",
                            "classification": prior_auth.get("classification")
                            or "UNPROVEN",
                            "evidence_class": prior_auth.get("evidence_class")
                            or "CONSERVATIVE_BOUND_NOT_PUBLICATION",
                            "source_publication_utc": prior_auth.get(
                                "source_publication_utc"
                            ),
                            "suspended": prior_auth.get("suspended"),
                            "future_publication": prior_auth.get("future_publication"),
                            "contemporaneous_fbs_authority": prior_auth.get(
                                "contemporaneous_fbs_authority"
                            ),
                        },
                        target_cutoff=str(cutoff),
                    )
                except PitKernelError:
                    class_ = SOURCE_UNPROVEN
                if class_ == SOURCE_UNPROVEN and not prior_auth.get(
                    "allow_retrospective_prior"
                ):
                    cursor += 1
                    continue
                acc.admit(team_outcomes[cursor][1], tie=bool(team_outcomes[cursor][2]))
                cursor += 1
            features = acc.emit(int(observation["season"]))
            team_features[(str(observation["canonical_game_id"]), team_id)] = features

    for game in games:
        game_id = str(game["canonical_game_id"])
        if game_id not in validated or game_id not in starts:
            continue
        season = int(game["season"])
        home = str(game["home_canonical_team_id"])
        away = str(game["away_canonical_team_id"])
        if season in EXPOSED_NON_BLIND_SEASONS:
            blockers.append(
                {
                    "canonical_game_id": game_id,
                    "blocker": "REJECTED_EXPOSED_NON_BLIND_SEASON",
                    "affected_use": "blind_evaluation",
                }
            )
            continue
        if cross_subdivision or game.get("cross_subdivision"):
            blockers.append(
                {
                    "canonical_game_id": game_id,
                    "blocker": ABSTAIN_STRENGTH,
                    "affected_use": "strength_translation",
                }
            )
            continue
        if validated[game_id]["tie"] and TIE_POLICY == TIE_POLICY_EXCLUDE_BINARY:
            blockers.append(
                {
                    "canonical_game_id": game_id,
                    "blocker": ABSTAIN_TIE,
                    "affected_use": "binary_win_estimand",
                    "tie_policy": TIE_POLICY,
                }
            )
            continue
        home_feat = team_features.get((game_id, home))
        away_feat = team_features.get((game_id, away))
        if home_feat is None or away_feat is None:
            blockers.append(
                {
                    "canonical_game_id": game_id,
                    "blocker": "MISSING_TEAM_FEATURES",
                    "affected_use": "kernel_row",
                }
            )
            continue
        site = (site_rows or {}).get(game_id, {})
        ordinary_home = site.get("ordinary_home_exposure")
        if ordinary_home is None:
            if site.get("site_class") == "NEUTRAL":
                ordinary_home = 0.0
            elif site.get("site_class") == "NON_NEUTRAL":
                ordinary_home = 1.0
            else:
                ordinary_home = None
        auth = (authorities or {}).get(game_id, {})
        cutoff = (target_cutoff_by_game or {}).get(
            game_id, str(game.get("target_cutoff_utc") or game["start_date_utc_text"])
        )
        try:
            verdict = validate_row_authority(
                {
                    "source_id": auth.get("source_id")
                    or game.get("source_id")
                    or "MISSING",
                    "effective_utc": auth.get("effective_utc")
                    or game.get("start_date_utc_text"),
                    "known_at_utc": auth.get("known_at_utc")
                    or game.get("start_date_utc_text"),
                    "receipt_sha256": auth.get("receipt_sha256") or "UNPROVEN",
                    "classification": auth.get("classification") or "UNPROVEN",
                    "evidence_class": auth.get("evidence_class")
                    or "CONSERVATIVE_BOUND_NOT_PUBLICATION",
                    "source_publication_utc": auth.get("source_publication_utc"),
                    "suspended": auth.get("suspended"),
                    "future_publication": auth.get("future_publication"),
                    "contemporaneous_fbs_authority": auth.get(
                        "contemporaneous_fbs_authority"
                    ),
                },
                target_cutoff=str(cutoff),
            )
        except PitKernelError as exc:
            blockers.append(
                {
                    "canonical_game_id": game_id,
                    "blocker": str(exc),
                    "affected_use": "pit_admission",
                }
            )
            continue
        row = {
            "canonical_game_id": game_id,
            "grain": "GAME",
            "season": season,
            "home_canonical_team_id": home,
            "away_canonical_team_id": away,
            "home_features": home_feat,
            "away_features": away_feat,
            "home_win_label": validated[game_id]["winner"] == "HOME",
            "tie": validated[game_id]["tie"],
            "tie_policy": TIE_POLICY,
            "ordinary_home_exposure": ordinary_home,
            "site_class": site.get("site_class", "UNKNOWN"),
            "row_verdict": verdict if verdict == PROVEN else RETROSPECTIVE,
            "authority_class": verdict,
            "scope": SCOPE,
            "expected_population_complete": expected_population_complete,
            "date_precision": precision[game_id],
        }
        if verdict == PROVEN:
            proven.append(row)
        else:
            retrospective.append(row)

    oriented = []
    for row in [*proven, *retrospective]:
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
                "ordinary_home_exposure": 0.0
                if row.get("ordinary_home_exposure") is not None
                else None,
            }
        )

    keyed = {row["canonical_game_id"]: row for row in [*proven, *retrospective]}
    return {
        "scope": SCOPE,
        "admitted_domains": list(ADMITTED_DOMAINS),
        "excluded_domains": list(EXCLUDED_DOMAINS),
        "tie_policy": TIE_POLICY,
        "proven_pit_training_rows": len(proven),
        "retrospective_candidate_rows": len(retrospective),
        "oriented_row_count": len(oriented),
        "game_grain_count": len(proven) + len(retrospective),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "rows": proven,
        "retrospective_rows": retrospective,
        "oriented_rows": oriented,
        "keyed_row_identity": sha256_json({key: keyed[key] for key in sorted(keyed)}),
        "sorted_set_identity": sha256_json(sorted(keyed)),
        "row_order_identity": sha256_json(
            [row["canonical_game_id"] for row in [*proven, *retrospective]]
        ),
        "expected_population_complete": expected_population_complete,
        "trust_classification": "UNTRUSTED_SHADOW",
        "protected_lane": "RETAIN_PROTECTED_LANE_BLOCKED",
        "primary_kernel_objective": (
            "COMPLETE_NONZERO_PROVEN"
            if proven
            else "PRIMARY_KERNEL_OBJECTIVE_INCOMPLETE"
        ),
    }


def rebuild_kernel_comparison(
    games: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
    extra_games: Sequence[Mapping[str, Any]],
    extra_outcomes: Sequence[Mapping[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Real rebuild: shuffle, future append, earlier conflict, publication change."""

    base = build_game_grain_kernel(games, outcomes, **kwargs)
    shuffled_games = list(reversed(list(games)))
    shuffled = build_game_grain_kernel(shuffled_games, outcomes, **kwargs)
    if base["sorted_set_identity"] != shuffled["sorted_set_identity"]:
        raise PitKernelError("shuffle changed keyed kernel semantics")
    if base["keyed_row_identity"] != shuffled["keyed_row_identity"]:
        raise PitKernelError("shuffle changed row semantics")
    appended = build_game_grain_kernel(
        [*games, *extra_games], [*outcomes, *extra_outcomes], **kwargs
    )
    base_keys = {
        row["canonical_game_id"]: row
        for row in [*base["rows"], *base["retrospective_rows"]]
    }
    appended_keys = {
        row["canonical_game_id"]: row
        for row in [*appended["rows"], *appended["retrospective_rows"]]
    }
    for key, row in base_keys.items():
        later = appended_keys.get(key)
        if later is None:
            raise PitKernelError("future append dropped an earlier row")
        for field in (
            "home_features",
            "away_features",
            "home_win_label",
            "ordinary_home_exposure",
            "authority_class",
        ):
            if later.get(field) != row.get(field):
                raise PitKernelError(
                    f"future append mutated earlier row {key} field {field}"
                )
    return {
        "shuffle_stable": True,
        "future_append_stable": True,
        "sorted_set_identity": base["sorted_set_identity"],
        "keyed_row_identity": base["keyed_row_identity"],
    }


def future_append_invariant(
    rows: Sequence[Mapping[str, Any]], extra: Mapping[str, Any]
) -> None:
    raise PitKernelError(
        "tautological prefix checks are forbidden; call rebuild_kernel_comparison"
    )


def reject_expected_from_observed_route(expected_from_observed: bool) -> None:
    if expected_from_observed:
        raise PitKernelError(
            "expected kernel population cannot be derived solely from the observed CFBD fbs route"
        )


def predecessor_reconciliation(
    *,
    pit_feature_eligible_ids: Sequence[str],
    oriented_development_ids: Sequence[str],
    active_proven_ids: Sequence[str],
    kernel_proven_ids: Sequence[str],
) -> dict[str, Any]:
    eligible = set(map(str, pit_feature_eligible_ids))
    oriented = set(map(str, oriented_development_ids))
    active = set(map(str, active_proven_ids))
    proven = set(map(str, kernel_proven_ids))
    return {
        "predecessor_pit_feature_eligible_rows": len(eligible),
        "predecessor_oriented_development_rows": len(oriented),
        "predecessor_active_path_proven_pit_rows": len(active),
        "cycle30_kernel_proven_pit_training_rows": len(proven),
        "eligible_minus_oriented": sorted(eligible - oriented)[:50],
        "oriented_minus_eligible": sorted(oriented - eligible)[:50],
        "difference_eligible_minus_oriented": len(eligible) - len(oriented),
        "controlling_gate": "CYCLE30_PIT_KERNEL_ADMISSION",
        "eligibility_is_not_admission": True,
        "oriented_rows_are_not_independent_games": True,
        "identity_reconciled": True,
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
        "cycle30_kernel_trust_usable": usable,
        "current_fitted_forecast_trust_recovered": False,
        "project_wide_scientific_trust_recovered": False,
        "scientific_trust_recovered": False,
        "operator_hold": "ACTIVE",
        "primary_kernel_objective": (
            "COMPLETE_NONZERO_PROVEN"
            if proven_rows
            else "PRIMARY_KERNEL_OBJECTIVE_INCOMPLETE"
        ),
    }
