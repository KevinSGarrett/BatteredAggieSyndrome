from __future__ import annotations

from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence

try:
    import numpy as np
except ModuleNotFoundError:
    np = None


CLASSIFICATION = "PRELIMINARY_UNPROTECTED_WMT_TAMU_SHADOW"
RUN_VERSION = "preliminary-wmt-tamu-shadow-walk-forward-v1"
WMT_FEATURES = (
    "action_penalty_rate",
    "play_scoring_rate",
    "drive_turnover_rate",
    "player_starter_rate",
)
LOGISTIC_FEATURES = ("baseline_tamu_logit",) + WMT_FEATURES
MARGIN_FEATURES = ("baseline_tamu_margin",) + WMT_FEATURES
NUMPY_AVAILABLE = np is not None


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


def fit_seasons_for_prediction(season: int) -> tuple[int, ...]:
    if season == 2023:
        return ()
    if season == 2024:
        return (2023,)
    if season == 2025:
        return (2023, 2024)
    raise ValueError(f"season {season} is outside the approved WMT A&M shadow replay")


def build_shadow_row(
    wmt: Mapping[str, Any],
    logistic_reference: Mapping[str, Any],
    margin_reference: Mapping[str, Any],
    canonical_tamu_team_id: str,
) -> dict[str, Any]:
    game_id = str(wmt["game_id"])
    for reference in (logistic_reference, margin_reference):
        if str(reference["target_game_id"]) != game_id:
            raise ValueError("WMT/reference game identity mismatch")
        if int(reference["season"]) != int(wmt["season"]):
            raise ValueError("WMT/reference season mismatch")
        if str(reference["start_utc"]) != str(wmt["start_utc"]):
            raise ValueError("WMT/reference start-time mismatch")
    if str(wmt["canonical_tamu_team_id"]) != canonical_tamu_team_id:
        raise ValueError("WMT feature row does not use the canonical Texas A&M identity")
    if bool(wmt["protected_eligible"]):
        raise ValueError("WMT feature unexpectedly claims protected eligibility")
    if bool(wmt["cold_start"]):
        raise ValueError("the pinned WMT target population unexpectedly contains a cold start")
    if str(wmt["latest_source_available_at_utc"]) >= str(wmt["cutoff_utc"]):
        raise ValueError("WMT available-at evidence is not strictly before the target cutoff")
    if str(wmt["latest_source_effective_at_utc"]) >= str(wmt["cutoff_utc"]):
        raise ValueError("WMT effective-at evidence is not strictly before the target cutoff")
    if str(logistic_reference["model_id"]) != "play_drive_logistic_stacker":
        raise ValueError("unexpected national logistic reference family")
    if str(margin_reference["model_id"]) != "play_drive_ridge_margin_stacker":
        raise ValueError("unexpected national margin reference family")

    role = str(wmt["team_role"]).upper()
    if role not in {"HOME", "AWAY"}:
        raise ValueError("WMT Texas A&M team role must be HOME or AWAY")
    expected_tamu = logistic_reference["home_team_id"] if role == "HOME" else logistic_reference["away_team_id"]
    expected_opponent = logistic_reference["away_team_id"] if role == "HOME" else logistic_reference["home_team_id"]
    if str(expected_tamu) != canonical_tamu_team_id or str(expected_opponent) != str(wmt["opponent_team_id"]):
        raise ValueError("WMT/reference team or opponent identity mismatch")

    home_probability = float(logistic_reference["home_win_probability"])
    home_margin = float(margin_reference["predicted_margin"])
    home_win = float(logistic_reference["home_win"])
    actual_margin = float(logistic_reference["margin"])
    tamu_probability = home_probability if role == "HOME" else 1.0 - home_probability
    tamu_margin = home_margin if role == "HOME" else -home_margin
    tamu_win = home_win if role == "HOME" else 1.0 - home_win
    tamu_actual_margin = actual_margin if role == "HOME" else -actual_margin
    values = {name: None if wmt.get(name) is None else float(wmt[name]) for name in WMT_FEATURES}

    result: dict[str, Any] = {
        "classification": CLASSIFICATION,
        "target_game_id": game_id,
        "season": int(wmt["season"]),
        "season_type": str(wmt["season_type"]),
        "week": int(wmt["week"]),
        "start_utc": str(wmt["start_utc"]),
        "cutoff_utc": str(wmt["cutoff_utc"]),
        "canonical_tamu_team_id": canonical_tamu_team_id,
        "tamu_team_role": role,
        "opponent_team_id": str(wmt["opponent_team_id"]),
        "neutral_site": bool(wmt["neutral_site"]),
        "baseline_tamu_probability": safe_probability(tamu_probability),
        "baseline_tamu_logit": logit(tamu_probability),
        "baseline_tamu_margin": tamu_margin,
        "tamu_win": tamu_win,
        "tamu_margin": tamu_actual_margin,
        "home_win": home_win,
        "home_margin": actual_margin,
        "latest_source_available_at_utc": str(wmt["latest_source_available_at_utc"]),
        "latest_source_effective_at_utc": str(wmt["latest_source_effective_at_utc"]),
        "source_record_count": int(wmt["source_record_count"]),
        "source_game_count": int(wmt["source_game_count"]),
        "wmt_protected_eligible": False,
        **values,
    }
    result["feature_row_identity"] = stable_hash(
        {
            "game_id": game_id,
            "cutoff_utc": result["cutoff_utc"],
            "role": role,
            "opponent_team_id": result["opponent_team_id"],
            "source_available_at": result["latest_source_available_at_utc"],
            "source_effective_at": result["latest_source_effective_at_utc"],
            "values": values,
        }
    )
    return result


def probability_metrics(labels: Sequence[float], probabilities: Sequence[float]) -> dict[str, float | int]:
    if np is None:
        raise RuntimeError("probability metrics require the optional NumPy modeling dependency")
    y = np.asarray(labels, dtype=float)
    p = np.clip(np.asarray(probabilities, dtype=float), 1e-9, 1.0 - 1e-9)
    if y.size == 0 or y.shape != p.shape:
        return {"rows": 0}
    edges = np.linspace(0.0, 1.0, 11)
    ece = 0.0
    for index in range(10):
        mask = (p >= edges[index]) & ((p <= edges[index + 1]) if index == 9 else (p < edges[index + 1]))
        if np.any(mask):
            ece += float(np.mean(mask)) * abs(float(np.mean(p[mask]) - np.mean(y[mask])))
    return {
        "rows": int(y.size),
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))),
        "ece_10": float(ece),
    }


def margin_metrics(labels: Sequence[float], predictions: Sequence[float]) -> dict[str, float | int]:
    if np is None:
        raise RuntimeError("margin metrics require the optional NumPy modeling dependency")
    y = np.asarray(labels, dtype=float)
    p = np.asarray(predictions, dtype=float)
    if y.size == 0 or y.shape != p.shape:
        return {"rows": 0}
    return {
        "rows": int(y.size),
        "mae": float(np.mean(np.abs(p - y))),
        "rmse": float(np.sqrt(np.mean((p - y) ** 2))),
    }
