from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from typing import Iterable, Sequence

@dataclass(frozen=True, order=True)
class HistoryPoint:
    event_time: datetime
    value: float
    event_id: str = ""

def strict_prior(points: Iterable[HistoryPoint], cutoff: datetime) -> tuple[HistoryPoint, ...]:
    """Return observations strictly before cutoff, deterministically ordered."""
    return tuple(sorted((p for p in points if p.event_time < cutoff), key=lambda p: (p.event_time, p.event_id)))

def _tail(points: Iterable[HistoryPoint], cutoff: datetime, window: int | None) -> tuple[HistoryPoint, ...]:
    prior = strict_prior(points, cutoff)
    if window is None: return prior
    if window <= 0: raise ValueError("window must be positive")
    return prior[-window:]

def lagged_last(points: Iterable[HistoryPoint], cutoff: datetime) -> float | None:
    prior = strict_prior(points, cutoff)
    return prior[-1].value if prior else None

def rolling_mean(points: Iterable[HistoryPoint], cutoff: datetime, window: int) -> float | None:
    xs=_tail(points,cutoff,window)
    return sum(p.value for p in xs)/len(xs) if xs else None

def rolling_sum(points: Iterable[HistoryPoint], cutoff: datetime, window: int) -> float | None:
    xs=_tail(points,cutoff,window)
    return sum(p.value for p in xs) if xs else None

def rolling_std(points: Iterable[HistoryPoint], cutoff: datetime, window: int) -> float | None:
    xs=_tail(points,cutoff,window)
    if not xs: return None
    vals=[p.value for p in xs]; mu=sum(vals)/len(vals)
    return sqrt(sum((x-mu)**2 for x in vals)/len(vals))

def ewma(points: Iterable[HistoryPoint], cutoff: datetime, alpha: float, window: int | None=None) -> float | None:
    if not 0 < alpha <= 1: raise ValueError("alpha must be in (0,1]")
    xs=_tail(points,cutoff,window)
    if not xs: return None
    out=xs[0].value
    for p in xs[1:]: out=alpha*p.value+(1-alpha)*out
    return out

def linear_trend(points: Iterable[HistoryPoint], cutoff: datetime, window: int) -> float | None:
    xs=_tail(points,cutoff,window)
    n=len(xs)
    if n < 2: return None
    xbar=(n-1)/2; ybar=sum(p.value for p in xs)/n
    den=sum((i-xbar)**2 for i in range(n))
    return sum((i-xbar)*(p.value-ybar) for i,p in enumerate(xs))/den if den else 0.0

def prior_change(points: Iterable[HistoryPoint], cutoff: datetime) -> float | None:
    xs=strict_prior(points,cutoff)
    return xs[-1].value-xs[-2].value if len(xs)>=2 else None

def rate_per_opportunity(value: float, opportunities: float) -> float | None:
    if opportunities <= 0: return None
    return value/opportunities

def opponent_adjusted_residual(observed: float, expected_given_opponent: float) -> float:
    return observed-expected_given_opponent

def matchup_difference(team_value: float, opponent_value: float) -> float:
    return team_value-opponent_value

def matchup_product(team_value: float, opponent_value: float) -> float:
    return team_value*opponent_value
