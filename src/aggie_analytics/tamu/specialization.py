from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Tuple

@dataclass(frozen=True)
class SpecializationSignal:
    candidate_id: str
    target_scope: str
    raw_adjustment: float
    shrinkage: float
    uncertainty: float
    production_selected: bool = False
    evidence_refs: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.shrinkage <= 1:
            raise ValueError("shrinkage must be in [0,1]")
        if self.uncertainty < 0:
            raise ValueError("uncertainty must be non-negative")
        if self.production_selected:
            raise ValueError("W14 cannot mark a specialization signal production-selected")

    @property
    def shrunk_adjustment(self) -> float:
        return self.raw_adjustment * self.shrinkage

def no_adjustment_signal(target_scope: str = "national_forecast") -> SpecializationSignal:
    return SpecializationSignal(
        candidate_id="TAMU-SP-00",
        target_scope=target_scope,
        raw_adjustment=0.0,
        shrinkage=0.0,
        uncertainty=0.0,
        production_selected=False,
    )

def shrink_adjustment(raw_adjustment: float, shrinkage: float) -> float:
    if not 0 <= shrinkage <= 1:
        raise ValueError("shrinkage must be in [0,1]")
    return raw_adjustment * shrinkage

def weighted_similarity(values: Mapping[str, float], weights: Mapping[str, float]) -> float:
    """Explicitly parameterized peer/analog similarity; no W14 default weights."""
    if set(values) != set(weights):
        raise ValueError("values and weights must have identical keys")
    if any(w < 0 for w in weights.values()):
        raise ValueError("weights must be non-negative")
    total=sum(weights.values())
    if total <= 0:
        raise ValueError("positive total weight required")
    return sum(values[k]*weights[k] for k in values)/total

def manual_aggie_bonus(*args, **kwargs) -> float:
    raise RuntimeError("W14 forbids manually assigned Aggie/12th-Man/narrative prediction bonuses")
