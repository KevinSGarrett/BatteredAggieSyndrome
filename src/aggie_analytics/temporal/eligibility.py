from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Any

from .contracts import ForecastCutoff, TemporalObservation, parse_time


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reason: str
    knowledge_time: datetime | None


BANNED_PREGAME_DOMAINS = {"WEATHER_OBSERVED"}


def _attr(obs: TemporalObservation, key: str, default=None):
    return (obs.attributes or {}).get(key, default)


def knowledge_time(obs: TemporalObservation) -> datetime:
    # first_known_at is policy-derived when defensible. Retrieval is the
    # conservative fallback; published_at alone is not universally trusted.
    return obs.first_known_at or obs.retrieved_at


def evaluate_eligibility(obs: TemporalObservation, cutoff: ForecastCutoff) -> EligibilityResult:
    kt = knowledge_time(obs)
    if obs.domain in BANNED_PREGAME_DOMAINS and cutoff.purpose != "LIVE_RESEARCH":
        return EligibilityResult(False, "DOMAIN_POLICY_BANNED", kt)
    if obs.retrospective_flag and not obs.corroborated_for_historical_use:
        return EligibilityResult(False, "RETROSPECTIVE_UNCORROBORATED", kt)
    if kt > cutoff.prediction_timestamp:
        return EligibilityResult(False, "KNOWN_AFTER_CUTOFF", kt)
    if obs.valid_from and cutoff.target_event_time < obs.valid_from:
        return EligibilityResult(False, "TARGET_OUTSIDE_VALIDITY", kt)
    if obs.valid_to and cutoff.target_event_time >= obs.valid_to:
        return EligibilityResult(False, "TARGET_OUTSIDE_VALIDITY", kt)
    if obs.domain == "AVAILABILITY_REPORT" and _attr(obs, "report_scope_applies", True) is not True:
        return EligibilityResult(False, "REPORT_POLICY_NONCOVERAGE", kt)
    if obs.domain == "WEATHER_FORECAST":
        available = parse_time(_attr(obs, "model_available_at")) or kt
        if available > cutoff.prediction_timestamp:
            return EligibilityResult(False, "KNOWN_AFTER_CUTOFF", available)
        valid = parse_time(_attr(obs, "forecast_valid_at"))
        # Exact/interpolation tolerance belongs to source/domain implementation;
        # synthetic W08 contract requires a target-valid timestamp when supplied.
        if valid is not None and valid != cutoff.target_event_time:
            return EligibilityResult(False, "TARGET_OUTSIDE_VALIDITY", kt)
    if obs.domain == "HISTORICAL_GAME_OUTPUT":
        # A row containing the target game's own outcome is never eligible for
        # that target game's pregame feature state, even if malformed metadata
        # would otherwise make it appear chronologically old. This explicit
        # identity guard complements the game-end cutoff rule.
        game_id = _attr(obs, "game_id")
        if cutoff.target_game_id and game_id == cutoff.target_game_id:
            return EligibilityResult(False, "TARGET_GAME_OUTPUT", kt)
        game_end = parse_time(_attr(obs, "game_end_at"))
        if game_end is None or game_end > cutoff.prediction_timestamp:
            return EligibilityResult(False, "GAME_NOT_COMPLETE_BY_CUTOFF", kt)
    return EligibilityResult(True, "ELIGIBLE", kt)


def select_latest_eligible(observations: Iterable[TemporalObservation], cutoff: ForecastCutoff) -> TemporalObservation | None:
    eligible=[]
    for obs in observations:
        result=evaluate_eligibility(obs, cutoff)
        if result.eligible:
            eligible.append((result.knowledge_time, obs.observation_id, obs))
    if not eligible:
        return None
    eligible.sort(key=lambda x:(x[0],x[1]))
    return eligible[-1][2]


def evaluate_fixture(case: dict[str, Any]) -> EligibilityResult:
    cutoff=ForecastCutoff(
        cutoff_id=f"cutoff-{case['scenario_id']}", purpose="FORECAST_SNAPSHOT",
        prediction_timestamp=parse_time(case['prediction_cutoff']),
        target_event_time=parse_time(case.get('target_time') or '2025-10-11T19:00:00Z'),
        forecast_lane="MARKET_AUGMENTED" if case['domain']=="MARKET" else "PURE_FOOTBALL",
        temporal_policy_version="w08-v1.0", data_snapshot_id="synthetic"
    )
    data={
        "observation_id":f"obs-{case['scenario_id']}","source_observation_id":f"src-{case['scenario_id']}",
        "domain":case['domain'],"retrieved_at":case.get('retrieved_at') or case['first_known_at'],
        "first_known_at":case['first_known_at'],"temporal_policy_version":"w08-v1.0",
        "valid_from":case.get('valid_from'),"valid_to":case.get('valid_to'),
        "retrospective_flag":case.get('retrospective_flag',False),
        "corroborated_for_historical_use":case.get('corroborated_for_historical_use',False),
        "report_scope_applies":case.get('report_scope_applies',True),
        "model_available_at":case.get('model_available_at'),"forecast_valid_at":case.get('forecast_valid_at'),
        "game_end_at":case.get('game_end_at')
    }
    return evaluate_eligibility(TemporalObservation.from_mapping(data), cutoff)
