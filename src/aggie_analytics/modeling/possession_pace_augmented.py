from __future__ import annotations

from typing import Any, Mapping, Sequence

from aggie_analytics.modeling import play_drive_augmented as prior


CLASSIFICATION = "PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE"
RUN_VERSION = "preliminary-possession-pace-nested-walk-forward-v1"
LOGISTIC_FAMILY = "possession_pace_logistic_stacker"
MARGIN_FAMILY = "possession_pace_ridge_margin_stacker"
PROFILE_LABEL = "possession_pace"
SOURCE_KNOWN_AT_FIELD = "possession_pace_source_known_at_utc"
HOME_SOURCE_KNOWN_AT_FIELD = "home_possession_pace_source_known_at_utc"
AWAY_SOURCE_KNOWN_AT_FIELD = "away_possession_pace_source_known_at_utc"
LINEAGE_FIELD = "possession_pace_lineage_sha256"
PROTECTED_FIELD = "possession_pace_protected_eligible"

PROFILE_FIELDS = (
    "offensive_plays_per_game",
    "offensive_drives_per_game",
    "observed_plays_per_drive_mean",
    "regulation_drive_span_seconds_mean",
    "regulation_drive_span_seconds_median",
    "overtime_drive_rate",
)
PACE_DIFFERENCE_FIELDS = tuple(f"possession_pace_{name}_diff" for name in PROFILE_FIELDS)
PRIOR_DIFFERENCE_FIELDS = prior.DIFFERENCE_FIELDS
DIFFERENCE_FIELDS = PRIOR_DIFFERENCE_FIELDS + PACE_DIFFERENCE_FIELDS
DIAGNOSTIC_FIELDS = (
    "possession_pace_regulation_drive_span_eligible_rate_diff",
    "possession_pace_source_endpoint_reverse_rate_diff",
    "home_rule_era_transfer_mismatch",
    "away_rule_era_transfer_mismatch",
    "prior_play_drive_lineage_sha256",
)
LOGISTIC_FEATURES = ("baseline_logit",) + DIFFERENCE_FIELDS + (
    "home_profile_cold_start",
    "away_profile_cold_start",
)
MARGIN_FEATURES = ("baseline_margin",) + DIFFERENCE_FIELDS + (
    "home_profile_cold_start",
    "away_profile_cold_start",
)

canonical_json = prior.canonical_json
stable_hash = prior.stable_hash
safe_probability = prior.safe_probability
logit = prior.logit
sigmoid = prior.sigmoid
fit_seasons_for_prediction = prior.fit_seasons_for_prediction
probability_metrics = prior.probability_metrics
margin_metrics = prior.margin_metrics


def _row_known_at(row: Mapping[str, Any]) -> str | None:
    values = [
        str(row[name])
        for name in ("play_source_known_at_utc_max", "drive_source_known_at_utc_max")
        if row.get(name) is not None
    ]
    return max(values) if values else None


def build_game_profile(
    target: Mapping[str, Any], profile_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if len(profile_rows) != 2:
        raise ValueError(f"exactly two possession/pace team rows required for {target['target_game_id']}")
    by_role = {str(row["team_role"]).upper(): row for row in profile_rows}
    if set(by_role) != {"HOME", "AWAY"}:
        raise ValueError("HOME and AWAY possession/pace rows required")
    home, away = by_role["HOME"], by_role["AWAY"]
    game_id = str(target["target_game_id"])
    for role, row, team_key, opponent_key in (
        ("home", home, "home_team_id", "away_team_id"),
        ("away", away, "away_team_id", "home_team_id"),
    ):
        if str(row["game_id"]) != game_id:
            raise ValueError(f"{role} target/possession-pace game identity mismatch")
        if str(row["team_id"]) != str(target[team_key]):
            raise ValueError(f"{role} target/possession-pace team identity mismatch")
        if str(row["opponent_team_id"]) != str(target[opponent_key]):
            raise ValueError(f"{role} target/possession-pace opponent identity mismatch")
        authority = row.get("authority")
        if authority != "DEVELOPMENT_ONLY" and not (
            authority is None and bool(row["cold_start"])
        ):
            raise ValueError(f"{role} possession/pace row has invalid authority")
        if bool(row.get("protected_eligible")):
            raise ValueError("possession/pace evidence unexpectedly claims protected eligibility")
        if bool(row["cold_start"]):
            if any(row.get(name) is not None for name in PROFILE_FIELDS):
                raise ValueError(f"{role} cold-start row contains fabricated profile values")
        known_at = _row_known_at(row)
        if known_at is not None and known_at > str(target["cutoff_utc"]):
            raise ValueError(f"{role} possession/pace evidence is after target cutoff")

    home_known_at, away_known_at = _row_known_at(home), _row_known_at(away)
    known_values = [value for value in (home_known_at, away_known_at) if value is not None]
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
        HOME_SOURCE_KNOWN_AT_FIELD: home_known_at,
        AWAY_SOURCE_KNOWN_AT_FIELD: away_known_at,
        SOURCE_KNOWN_AT_FIELD: max(known_values) if known_values else None,
        PROTECTED_FIELD: False,
    }
    for source_name, output_name in zip(PROFILE_FIELDS, PACE_DIFFERENCE_FIELDS):
        left, right = home.get(source_name), away.get(source_name)
        result[output_name] = (
            None if left is None or right is None else float(left) - float(right)
        )
    for source_name in (
        "regulation_drive_span_eligible_rate",
        "source_endpoint_reverse_rate",
    ):
        left, right = home.get(source_name), away.get(source_name)
        result[f"possession_pace_{source_name}_diff"] = (
            None if left is None or right is None else float(left) - float(right)
        )
    result["home_rule_era_transfer_mismatch"] = bool(home["rule_era_transfer_mismatch"])
    result["away_rule_era_transfer_mismatch"] = bool(away["rule_era_transfer_mismatch"])
    result[LINEAGE_FIELD] = stable_hash(
        {
            "target_game_id": game_id,
            "home_team_id": home["team_id"],
            "away_team_id": away["team_id"],
            "home_source_known_at_utc": home_known_at,
            "away_source_known_at_utc": away_known_at,
            "candidate_values": {name: result[name] for name in PACE_DIFFERENCE_FIELDS},
            "diagnostics": {
                name: result[name]
                for name in DIAGNOSTIC_FIELDS
                if name in result
            },
        }
    )
    return result


def merge_prior_features(
    feature: Mapping[str, Any], prior_row: Mapping[str, Any]
) -> dict[str, Any]:
    for name in ("target_game_id", "home_team_id", "away_team_id", "cutoff_utc"):
        if str(feature[name]) != str(prior_row[name]):
            raise ValueError(f"nested prior feature {name} mismatch")
    for name in ("home_profile_cold_start", "away_profile_cold_start"):
        if float(feature[name]) != float(prior_row[name]):
            raise ValueError(f"nested prior feature {name} mismatch")
    if bool(prior_row.get("play_drive_protected_eligible")):
        raise ValueError("nested prior feature unexpectedly claims protected eligibility")
    prior_known_at = prior_row.get("play_drive_source_known_at_utc")
    if prior_known_at is not None and str(prior_known_at) > str(feature["cutoff_utc"]):
        raise ValueError("nested prior feature evidence is after target cutoff")

    result = dict(feature)
    for name in PRIOR_DIFFERENCE_FIELDS:
        if name not in prior_row:
            raise ValueError(f"nested prior feature is missing {name}")
        result[name] = prior_row[name]
    result["prior_play_drive_lineage_sha256"] = str(prior_row["play_drive_lineage_sha256"])
    known_values = [
        str(value)
        for value in (result.get(SOURCE_KNOWN_AT_FIELD), prior_known_at)
        if value is not None
    ]
    result[SOURCE_KNOWN_AT_FIELD] = max(known_values) if known_values else None
    result[LINEAGE_FIELD] = stable_hash(
        {
            "possession_pace_lineage_sha256": result[LINEAGE_FIELD],
            "prior_play_drive_lineage_sha256": result["prior_play_drive_lineage_sha256"],
            "target_game_id": result["target_game_id"],
            "combined_values": {name: result[name] for name in DIFFERENCE_FIELDS},
        }
    )
    return result
