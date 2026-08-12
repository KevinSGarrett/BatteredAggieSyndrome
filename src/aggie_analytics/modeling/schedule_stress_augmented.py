from __future__ import annotations

from typing import Any, Mapping, Sequence

from aggie_analytics.modeling import sustainability_augmented as shared


CLASSIFICATION = "PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE"
RUN_VERSION = "preliminary-schedule-stress-walk-forward-v1"
LOGISTIC_FAMILY = "schedule_stress_logistic_stacker"
MARGIN_FAMILY = "schedule_stress_ridge_margin_stacker"
PROFILE_LABEL = "schedule_stress"
SOURCE_KNOWN_AT_FIELD = "schedule_stress_evidence_start_utc_max"
HOME_SOURCE_KNOWN_AT_FIELD = "home_schedule_stress_evidence_start_utc_max"
AWAY_SOURCE_KNOWN_AT_FIELD = "away_schedule_stress_evidence_start_utc_max"
LINEAGE_FIELD = "schedule_stress_lineage_sha256"
PROTECTED_FIELD = "schedule_stress_protected_eligible"

PROFILE_FIELDS = (
    "days_since_last_game_start",
    "games_last_7d",
    "games_last_14d",
    "games_last_28d",
    "away_or_neutral_games_last_28d",
    "consecutive_away_or_neutral_games",
    "recent_5_margin_mean",
    "recent_5_opponent_pregame_win_share_mean",
    "recent_5_opponent_adjusted_margin_mean",
)
DIFFERENCE_FIELDS = tuple(f"schedule_stress_{name}_diff" for name in PROFILE_FIELDS)
DIAGNOSTIC_FIELDS = (
    "schedule_stress_prior_game_count_diff",
    "schedule_stress_prior_season_game_count_diff",
)
LOGISTIC_FEATURES = ("baseline_logit",) + DIFFERENCE_FIELDS + (
    "home_profile_cold_start",
    "away_profile_cold_start",
)
MARGIN_FEATURES = ("baseline_margin",) + DIFFERENCE_FIELDS + (
    "home_profile_cold_start",
    "away_profile_cold_start",
)

canonical_json = shared.canonical_json
stable_hash = shared.stable_hash
safe_probability = shared.safe_probability
logit = shared.logit
sigmoid = shared.sigmoid
fit_seasons_for_prediction = shared.fit_seasons_for_prediction
probability_metrics = shared.probability_metrics
margin_metrics = shared.margin_metrics
empirical_direction_from_comparisons = shared.empirical_direction_from_comparisons


def _difference(left: Any, right: Any) -> float | None:
    return None if left is None or right is None else float(left) - float(right)


def build_game_profile(
    target: Mapping[str, Any], profile_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if len(profile_rows) != 2:
        raise ValueError(
            f"exactly two schedule-stress rows required for {target['target_game_id']}"
        )
    by_role = {str(row["team_role"]).upper(): row for row in profile_rows}
    if set(by_role) != {"HOME", "AWAY"}:
        raise ValueError("HOME and AWAY schedule-stress rows required")
    home, away = by_role["HOME"], by_role["AWAY"]
    game_id = str(target["target_game_id"])
    for role, row, team_key, opponent_key in (
        ("home", home, "home_team_id", "away_team_id"),
        ("away", away, "away_team_id", "home_team_id"),
    ):
        if str(row["game_id"]) != game_id:
            raise ValueError(f"{role} target/schedule-stress game mismatch")
        if str(row["team_id"]) != str(target[team_key]):
            raise ValueError(f"{role} target/schedule-stress team mismatch")
        if str(row["opponent_team_id"]) != str(target[opponent_key]):
            raise ValueError(f"{role} target/schedule-stress opponent mismatch")
        if bool(row["historical_original_pit_eligible"]):
            raise ValueError("schedule-stress row unexpectedly claims historical PIT")
        if bool(row["protected_eligible"]):
            raise ValueError("schedule-stress row unexpectedly claims protected authority")
        if not bool(row["event_chronology_eligible"]):
            raise ValueError("schedule-stress row lacks event chronology eligibility")
        known = row.get("evidence_source_start_utc_max")
        if known is not None and str(known) >= str(target["cutoff_utc"]):
            raise ValueError(f"{role} schedule-stress evidence is not before cutoff")
        if bool(row["cold_start"]) and any(row.get(name) is not None for name in (
            "days_since_last_game_start",
            "recent_5_margin_mean",
            "recent_5_opponent_pregame_win_share_mean",
            "recent_5_opponent_adjusted_margin_mean",
        )):
            raise ValueError(f"{role} cold-start row contains fabricated summaries")

    home_known = home.get("evidence_source_start_utc_max")
    away_known = away.get("evidence_source_start_utc_max")
    known_values = [str(value) for value in (home_known, away_known) if value is not None]
    result: dict[str, Any] = {
        "classification": CLASSIFICATION,
        "target_game_id": game_id,
        "season": int(target["season"]),
        "start_utc": str(target["start_utc"]),
        "cutoff_utc": str(target["cutoff_utc"]),
        "home_team_id": str(target["home_team_id"]),
        "away_team_id": str(target["away_team_id"]),
        "home_profile_cold_start": float(bool(home["cold_start"])),
        "away_profile_cold_start": float(bool(away["cold_start"])),
        HOME_SOURCE_KNOWN_AT_FIELD: home_known,
        AWAY_SOURCE_KNOWN_AT_FIELD: away_known,
        SOURCE_KNOWN_AT_FIELD: max(known_values) if known_values else None,
        PROTECTED_FIELD: False,
    }
    for source_name, output_name in zip(PROFILE_FIELDS, DIFFERENCE_FIELDS):
        result[output_name] = _difference(home.get(source_name), away.get(source_name))
    result[DIAGNOSTIC_FIELDS[0]] = _difference(
        home.get("prior_game_count"), away.get("prior_game_count")
    )
    result[DIAGNOSTIC_FIELDS[1]] = _difference(
        home.get("prior_season_game_count"), away.get("prior_season_game_count")
    )
    result[LINEAGE_FIELD] = stable_hash(
        {
            "target_game_id": game_id,
            "home_evidence": home["evidence_game_ids_sha256"],
            "away_evidence": away["evidence_game_ids_sha256"],
            "candidate_values": {name: result[name] for name in DIFFERENCE_FIELDS},
        }
    )
    return result
