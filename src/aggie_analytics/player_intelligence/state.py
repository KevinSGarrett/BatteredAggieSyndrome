from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

@dataclass(frozen=True)
class PlayerValueEstimate:
    player_id: str
    position_scope: str
    value: float
    uncertainty: float
    method_id: str
    cutoff: datetime
    def __post_init__(self) -> None:
        if self.uncertainty < 0:
            raise ValueError("uncertainty must be non-negative")

@dataclass(frozen=True)
class AvailabilityScenario:
    scenario_id: str
    probability: float
    active_player_value: float
    active_effectiveness: float
    active_usage_share: float
    replacement_value: float
    replacement_usage_share: float
    uncertainty: float = 0.0
    def __post_init__(self) -> None:
        if not 0 <= self.probability <= 1:
            raise ValueError("probability must be in [0,1]")
        if self.active_effectiveness < 0:
            raise ValueError("effectiveness must be non-negative")
        for name, value in (("active_usage_share", self.active_usage_share),
                            ("replacement_usage_share", self.replacement_usage_share)):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0,1]")
        if self.uncertainty < 0:
            raise ValueError("uncertainty must be non-negative")

def scenario_lineup_value(s: AvailabilityScenario) -> float:
    """Abstract player-value units, not game points."""
    return (
        s.active_player_value * s.active_effectiveness * s.active_usage_share
        + s.replacement_value * s.replacement_usage_share
    )

def expected_lineup_value(scenarios: Tuple[AvailabilityScenario, ...], *, tolerance: float = 1e-9) -> float:
    if not scenarios:
        raise ValueError("at least one scenario is required")
    total = sum(s.probability for s in scenarios)
    if abs(total - 1.0) > tolerance:
        raise ValueError("scenario probabilities must sum to 1")
    return sum(s.probability * scenario_lineup_value(s) for s in scenarios)

def expected_replacement_gap(
    healthy_value: float,
    healthy_usage_share: float,
    scenarios: Tuple[AvailabilityScenario, ...],
) -> float:
    """Healthy reference minus scenario-weighted lineup value in abstract units.

    W12 deliberately provides no mapping from this value to expected game points.
    """
    if not 0 <= healthy_usage_share <= 1:
        raise ValueError("healthy_usage_share must be in [0,1]")
    return healthy_value * healthy_usage_share - expected_lineup_value(scenarios)
