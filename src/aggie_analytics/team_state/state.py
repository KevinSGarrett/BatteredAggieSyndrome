from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

@dataclass(frozen=True)
class StrengthEstimate:
    value: float
    uncertainty: float
    source: str = ""
    def __post_init__(self) -> None:
        if self.uncertainty < 0:
            raise ValueError("uncertainty must be non-negative")

@dataclass(frozen=True)
class TeamStateSnapshot:
    team_id: str
    cutoff: datetime
    prior_strength: StrengthEstimate
    underlying_strength: StrengthEstimate
    available_strength: StrengthEstimate
    current_form_signal: StrengthEstimate | None
    opponent_strength: StrengthEstimate | None
    current_season_games: int
    regime_id: str
    uncertainty_components: Mapping[str, float]
    state_version: str = "w11-v1"
    def __post_init__(self) -> None:
        if self.current_season_games < 0:
            raise ValueError("current_season_games must be non-negative")
        if any(v < 0 for v in self.uncertainty_components.values()):
            raise ValueError("uncertainty components must be non-negative")

def placeholder_available_strength(underlying: StrengthEstimate) -> StrengthEstimate:
    """W11 boundary only.

    Until W12 materializes player-specific availability/replacement evidence,
    callers may carry underlying strength forward unchanged. This function is
    deliberately not an injury adjustment model.
    """
    return underlying
