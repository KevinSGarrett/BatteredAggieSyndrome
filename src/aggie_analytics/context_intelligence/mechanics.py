from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Iterable

def hidden_yards(*components: float) -> float:
    """Component-accounted hidden-yard candidate; callers must avoid duplicate components."""
    return sum(components)

def expected_possessions_baseline(team_prior: Iterable[float], opponent_prior: Iterable[float]) -> float | None:
    """Simple symmetric reference baseline, not a selected production formula."""
    a=list(team_prior); b=list(opponent_prior)
    if not a or not b:
        return None
    return (sum(a)/len(a) + sum(b)/len(b))/2.0

def crew_feature_eligible(*, assignment_first_known_at: datetime | None, cutoff: datetime) -> bool:
    return assignment_first_known_at is not None and assignment_first_known_at <= cutoff

@dataclass(frozen=True)
class OpponentObservation:
    value: float
    known_at: datetime

def strict_prior_opponent_value(observations: Iterable[OpponentObservation], cutoff: datetime) -> float | None:
    observations = list(observations)
    if (not isinstance(cutoff, datetime) or cutoff.utcoffset() is None
            or any(not isinstance(x.known_at, datetime) or x.known_at.utcoffset() is None for x in observations)):
        raise ValueError('opponent observation and cutoff times require an explicit timezone')
    eligible=[x for x in observations if x.known_at < cutoff]
    if not eligible:
        return None
    latest = max(x.known_at for x in eligible)
    values = [float(x.value) for x in eligible if x.known_at == latest]
    if not all(isfinite(value) for value in values):
        raise ValueError("latest prior opponent value must be finite")
    if len(set(values)) != 1:
        raise ValueError("conflicting opponent observations at the latest prior time")
    return values[0]

def referee_bias_bonus(*args, **kwargs) -> float:
    raise RuntimeError("Unsupported referee favors/dislikes-team bonuses are prohibited.")
