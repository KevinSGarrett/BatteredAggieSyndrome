from __future__ import annotations

from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence


CLASSIFICATION = "PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE"
RUN_VERSION = "preliminary-sustainability-nested-walk-forward-v1"
LOGISTIC_FAMILY = "sustainability_logistic_stacker"
MARGIN_FAMILY = "sustainability_ridge_margin_stacker"
PROFILE_LABEL = "sustainability"
SOURCE_KNOWN_AT_FIELD = "sustainability_source_known_at_utc"
HOME_SOURCE_KNOWN_AT_FIELD = "home_sustainability_source_known_at_utc"
AWAY_SOURCE_KNOWN_AT_FIELD = "away_sustainability_source_known_at_utc"
LINEAGE_FIELD = "sustainability_lineage_sha256"
PROTECTED_FIELD = "sustainability_protected_eligible"

PROFILE_FIELDS = (
    "all_win_share_minus_score_share",
    "all_close_win_share_minus_overall",
    "all_margin_stddev",
    "all_downside_tail_rate",
    "recent_win_share_minus_score_share",
    "recent_close_win_share_minus_overall",
    "recent_margin_stddev",
    "recent_downside_tail_rate",
)
DIFFERENCE_FIELDS = tuple(f"sustainability_{name}_diff" for name in PROFILE_FIELDS)
DIAGNOSTIC_SOURCE_FIELDS = (
    "all_source_game_count",
    "all_source_season_count",
    "recent_source_game_count",
    "recent_source_season_count",
    "all_upside_tail_rate",
    "recent_upside_tail_rate",
    "pandemic_2020_game_share",
)
DIAGNOSTIC_FIELDS = tuple(
    f"sustainability_{name}_diff" for name in DIAGNOSTIC_SOURCE_FIELDS
)
LOGISTIC_FEATURES = ("baseline_logit",) + DIFFERENCE_FIELDS + (
    "home_profile_cold_start",
    "away_profile_cold_start",
)
MARGIN_FEATURES = ("baseline_margin",) + DIFFERENCE_FIELDS + (
    "home_profile_cold_start",
    "away_profile_cold_start",
)

def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def stable_hash(value: object) -> str:
    return sha256(canonical_json(value)).hexdigest()


def safe_probability(value: float) -> float:
    return float(min(max(value, 1e-9), 1.0 - 1e-9))


def logit(probability: float) -> float:
    value = safe_probability(probability)
    return float(math.log(value / (1.0 - value)))


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return safe_probability(1.0 / (1.0 + z))
    z = math.exp(value)
    return safe_probability(z / (1.0 + z))


def fit_seasons_for_prediction(season: int) -> tuple[int, ...]:
    if season == 2023:
        return ()
    if season == 2024:
        return (2023,)
    if season == 2025:
        return (2023, 2024)
    raise ValueError(f"season {season} is outside the approved sustainability replay")


def probability_metrics(
    labels: Sequence[float], probabilities: Sequence[float]
) -> dict[str, float | int]:
    if not labels or len(labels) != len(probabilities):
        return {"rows": 0}
    y = [float(value) for value in labels]
    p = [safe_probability(float(value)) for value in probabilities]
    rows = len(y)
    ece = 0.0
    for index in range(10):
        lower, upper = index / 10.0, (index + 1) / 10.0
        selected = [
            offset
            for offset, value in enumerate(p)
            if value >= lower and (value <= upper if index == 9 else value < upper)
        ]
        if selected:
            mean_p = sum(p[offset] for offset in selected) / len(selected)
            mean_y = sum(y[offset] for offset in selected) / len(selected)
            ece += (len(selected) / rows) * abs(mean_p - mean_y)
    return {
        "rows": rows,
        "brier": sum((probability - label) ** 2 for label, probability in zip(y, p))
        / rows,
        "log_loss": -sum(
            label * math.log(probability)
            + (1.0 - label) * math.log(1.0 - probability)
            for label, probability in zip(y, p)
        )
        / rows,
        "ece_10": ece,
    }


def margin_metrics(
    labels: Sequence[float], predictions: Sequence[float]
) -> dict[str, float | int]:
    if not labels or len(labels) != len(predictions):
        return {"rows": 0}
    errors = [float(prediction) - float(label) for label, prediction in zip(labels, predictions)]
    return {
        "rows": len(errors),
        "mae": sum(abs(value) for value in errors) / len(errors),
        "rmse": math.sqrt(sum(value * value for value in errors) / len(errors)),
    }


def empirical_direction_from_comparisons(
    prior_comparison: Mapping[str, Mapping[str, Mapping[str, Any]]],
    baseline_comparison: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> tuple[str, str, str]:
    if prior_comparison:
        selected = prior_comparison
        suffix = "_candidate_minus_prior"
        reference = "PINNED_PRIOR_CANDIDATE"
    else:
        selected = baseline_comparison
        suffix = "_candidate_minus_frozen"
        reference = "UNCHANGED_FROZEN_BASELINE"
    deltas = [
        float(value)
        for seasons in selected.values()
        for season, item in seasons.items()
        if season != "2023"
        for key, value in item.items()
        if key.endswith(suffix)
    ]
    if not deltas:
        return "NOT_EVALUATED", "RESEARCH_ONLY_NO_PROMOTION", reference
    has_improvement = any(value < 0.0 for value in deltas)
    has_degradation = any(value > 0.0 for value in deltas)
    if has_improvement and has_degradation:
        return (
            "MIXED_SEASON_OR_METRIC_DIRECTION",
            "REJECT_UNSTABLE_MIXED_SEASON_EFFECT",
            reference,
        )
    if has_degradation:
        return (
            "CONSISTENT_NONNEGATIVE",
            "REJECT_CONSISTENT_DEGRADATION",
            reference,
        )
    if has_improvement:
        return "CONSISTENT_NONPOSITIVE", "RESEARCH_ONLY_NO_PROMOTION", reference
    return "NO_INCREMENTAL_CHANGE", "PREFER_UNCHANGED_REFERENCE", reference


def _difference(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    return float(left) - float(right)


def build_game_profile(
    target: Mapping[str, Any], profile_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if len(profile_rows) != 2:
        raise ValueError(
            f"exactly two sustainability team rows required for {target['target_game_id']}"
        )
    by_role = {str(row["team_role"]).upper(): row for row in profile_rows}
    if set(by_role) != {"HOME", "AWAY"}:
        raise ValueError("HOME and AWAY sustainability rows required")
    home, away = by_role["HOME"], by_role["AWAY"]
    game_id = str(target["target_game_id"])
    for role, row, team_key, opponent_key in (
        ("home", home, "home_team_id", "away_team_id"),
        ("away", away, "away_team_id", "home_team_id"),
    ):
        if str(row["game_id"]) != game_id:
            raise ValueError(f"{role} target/sustainability game identity mismatch")
        if str(row["team_id"]) != str(target[team_key]):
            raise ValueError(f"{role} target/sustainability team identity mismatch")
        if str(row["opponent_team_id"]) != str(target[opponent_key]):
            raise ValueError(f"{role} target/sustainability opponent identity mismatch")
        if row.get("classification") != CLASSIFICATION:
            raise ValueError(f"{role} sustainability classification drift")
        if bool(row.get("protected_eligible")) or bool(
            row.get("historical_original_pit_eligible")
        ):
            raise ValueError("sustainability evidence unexpectedly claims protected authority")
        if bool(row["cold_start"]):
            if row.get("authority") is not None:
                raise ValueError(f"{role} cold-start sustainability authority must be null")
            if any(row.get(name) is not None for name in PROFILE_FIELDS):
                raise ValueError(f"{role} cold-start row contains fabricated profile values")
        elif row.get("authority") != "DEVELOPMENT_ONLY_RETROSPECTIVE":
            raise ValueError(f"{role} sustainability row has invalid authority")
        known_at = row.get("source_known_at_utc_max")
        if known_at is not None and str(known_at) > str(target["cutoff_utc"]):
            raise ValueError(f"{role} sustainability evidence is after target cutoff")

    home_known_at = home.get("source_known_at_utc_max")
    away_known_at = away.get("source_known_at_utc_max")
    known_values = [
        str(value) for value in (home_known_at, away_known_at) if value is not None
    ]
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
    for source_name, output_name in zip(PROFILE_FIELDS, DIFFERENCE_FIELDS):
        result[output_name] = _difference(home.get(source_name), away.get(source_name))
    for source_name, output_name in zip(
        DIAGNOSTIC_SOURCE_FIELDS, DIAGNOSTIC_FIELDS
    ):
        result[output_name] = _difference(home.get(source_name), away.get(source_name))
    result[LINEAGE_FIELD] = stable_hash(
        {
            "target_game_id": game_id,
            "home_team_id": home["team_id"],
            "away_team_id": away["team_id"],
            "home_source_known_at_utc": home_known_at,
            "away_source_known_at_utc": away_known_at,
            "candidate_values": {name: result[name] for name in DIFFERENCE_FIELDS},
            "diagnostics": {name: result[name] for name in DIAGNOSTIC_FIELDS},
        }
    )
    return result
