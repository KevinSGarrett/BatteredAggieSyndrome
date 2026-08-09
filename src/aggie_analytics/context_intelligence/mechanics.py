from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
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
    eligible=[x for x in observations if x.known_at < cutoff]
    if not eligible:
        return None
    return eligible[-1].value

def referee_bias_bonus(*args, **kwargs) -> float:
    raise RuntimeError("Unsupported referee favors/dislikes-team bonuses are prohibited.")
