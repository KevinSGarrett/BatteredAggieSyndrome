from __future__ import annotations

from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np


CLASSIFICATION = "PRELIMINARY_UNPROTECTED"
RUN_VERSION = "preliminary-play-enrichment-walk-forward-v1"
LOGISTIC_FAMILY = "play_enrichment_logistic_stacker"
MARGIN_FAMILY = "play_enrichment_ridge_margin_stacker"
PROFILE_LABEL = "play_enrichment"
SOURCE_KNOWN_AT_FIELD = "play_enrichment_source_known_at_utc"
HOME_SOURCE_KNOWN_AT_FIELD = "home_play_enrichment_source_known_at_utc"
AWAY_SOURCE_KNOWN_AT_FIELD = "away_play_enrichment_source_known_at_utc"
LINEAGE_FIELD = "play_enrichment_lineage_sha256"
PROTECTED_FIELD = "play_enrichment_protected_eligible"
PROFILE_FIELDS = (
    "source_play_count",
    "source_game_count",
    "source_season_count",
    "position_candidate_row_count",
    "unknown_position_row_count",
    "source_player_id_candidate_row_count",
    "source_epa_mean",
    "source_wpa_mean",
    "source_success_rate",
    "source_ppa_mean",
    "source_epa_revision_mean_abs",
    "source_wpa_revision_mean_abs",
    "rush_rate",
    "pass_rate",
    "sack_rate",
    "interception_rate",
    "completion_rate_on_pass_attempt",
    "target_rate",
    "touchdown_rate",
    "turnover_rate",
    "penalty_rate",
    "red_zone_play_rate",
    "scoring_opportunity_rate",
    "middle_eight_rate",
    "stuffed_run_rate",
    "position_candidate_rate",
    "unknown_position_rate",
    "source_player_id_candidate_rate",
)
DIFFERENCE_FIELDS = tuple(f"play_enrichment_{name}_diff" for name in PROFILE_FIELDS)
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
    raise ValueError(f"season {season} is outside the approved play-enrichment replay")


def build_game_profile(
    target: Mapping[str, Any], profile_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if len(profile_rows) != 2:
        raise ValueError(f"exactly two team profile rows required for {target['target_game_id']}")
    by_role = {str(row["team_role"]).upper(): row for row in profile_rows}
    if set(by_role) != {"HOME", "AWAY"}:
        raise ValueError("HOME and AWAY play-enrichment profile rows required")
    home, away = by_role["HOME"], by_role["AWAY"]
    game_id = str(target["target_game_id"])
    if str(home["game_id"]) != game_id or str(away["game_id"]) != game_id:
        raise ValueError("target/play-enrichment game identity mismatch")
    if str(home["team_id"]) != str(target["home_team_id"]):
        raise ValueError("home team/play-enrichment identity mismatch")
    if str(away["team_id"]) != str(target["away_team_id"]):
        raise ValueError("away team/play-enrichment identity mismatch")
    if str(home["opponent_team_id"]) != str(target["away_team_id"]):
        raise ValueError("home opponent/play-enrichment identity mismatch")
    if str(away["opponent_team_id"]) != str(target["home_team_id"]):
        raise ValueError("away opponent/play-enrichment identity mismatch")
    for side, row in (("home", home), ("away", away)):
        if row.get("classification") != "DEVELOPMENT_ONLY_HISTORICAL_KNOWN_AT_EXACT_PLAY_ENRICHMENT":
            raise ValueError(f"{side} play-enrichment classification drift")
        if bool(row.get("official_stat_authority")):
            raise ValueError(f"{side} play-enrichment claims official-stat authority")
        if bool(row.get("canonical_player_identity_promoted")):
            raise ValueError(f"{side} play-enrichment promotes candidate player identity")
        if bool(row["cold_start"]):
            if any(row.get(name) is not None for name in PROFILE_FIELDS):
                raise ValueError(f"{side} cold-start row contains fabricated profile values")
            if row.get("authority") is not None or row.get("metric_authority") is not None:
                raise ValueError(f"{side} cold-start row contains unsupported authority")
        else:
            if row.get("authority") != "DEVELOPMENT_ONLY":
                raise ValueError(f"{side} play-enrichment evidence is not development-only")
            if row.get("metric_authority") != "SOURCE_MODEL_CANDIDATE_NOT_OFFICIAL":
                raise ValueError(f"{side} play-enrichment metric authority drift")
    if bool(home.get("protected_eligible") or away.get("protected_eligible")):
        raise ValueError("play-enrichment evidence unexpectedly claims protected eligibility")
    for side, row in (("home", home), ("away", away)):
        if row.get("source_known_at_utc") is not None and str(row["source_known_at_utc"]) > str(target["cutoff_utc"]):
            raise ValueError(f"{side} play-enrichment evidence is after target cutoff")
        if row.get("maximum_source_effective_at_utc") is not None and str(row["maximum_source_effective_at_utc"]) >= str(target["start_utc"]):
            raise ValueError(f"{side} play-enrichment evidence includes target/future game time")

    known_values = [
        str(row["source_known_at_utc"])
        for row in (home, away)
        if row.get("source_known_at_utc") is not None
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
        HOME_SOURCE_KNOWN_AT_FIELD: home.get("source_known_at_utc"),
        AWAY_SOURCE_KNOWN_AT_FIELD: away.get("source_known_at_utc"),
        SOURCE_KNOWN_AT_FIELD: max(known_values) if known_values else None,
        PROTECTED_FIELD: False,
    }
    for source_name, output_name in zip(PROFILE_FIELDS, DIFFERENCE_FIELDS):
        left, right = home.get(source_name), away.get(source_name)
        result[output_name] = (
            None if left is None or right is None else float(left) - float(right)
        )
    result[LINEAGE_FIELD] = stable_hash(
        {
            "target_game_id": game_id,
            "home_team_id": home["team_id"],
            "away_team_id": away["team_id"],
            "home_source_known_at_utc": home.get("source_known_at_utc"),
            "away_source_known_at_utc": away.get("source_known_at_utc"),
            "values": {name: result[name] for name in DIFFERENCE_FIELDS},
        }
    )
    return result


def probability_metrics(
    labels: Sequence[float], probabilities: Sequence[float]
) -> dict[str, float | int]:
    y = np.asarray(labels, dtype=float)
    p = np.clip(np.asarray(probabilities, dtype=float), 1e-9, 1.0 - 1e-9)
    if y.size == 0 or y.shape != p.shape:
        return {"rows": 0}
    edges = np.linspace(0.0, 1.0, 11)
    ece = 0.0
    for index in range(10):
        mask = (p >= edges[index]) & (
            (p <= edges[index + 1]) if index == 9 else (p < edges[index + 1])
        )
        if np.any(mask):
            ece += float(np.mean(mask)) * abs(float(np.mean(p[mask]) - np.mean(y[mask])))
    return {
        "rows": int(y.size),
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))),
        "ece_10": float(ece),
    }


def margin_metrics(labels: Sequence[float], predictions: Sequence[float]) -> dict[str, float | int]:
    y = np.asarray(labels, dtype=float)
    p = np.asarray(predictions, dtype=float)
    if y.size == 0 or y.shape != p.shape:
        return {"rows": 0}
    return {
        "rows": int(y.size),
        "mae": float(np.mean(np.abs(p - y))),
        "rmse": float(np.sqrt(np.mean((p - y) ** 2))),
    }
