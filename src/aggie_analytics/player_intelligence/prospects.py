from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

@dataclass(frozen=True)
class ProspectPrior:
    player_id: str
    position: str
    cutoff: datetime
    prior_value: float
    uncertainty: float
    evidence_ids: Tuple[str, ...]
    college_snaps_known: int = 0
    def __post_init__(self) -> None:
        if self.uncertainty <= 0:
            raise ValueError("prospect uncertainty must be positive")
        if self.college_snaps_known < 0:
            raise ValueError("college snaps must be non-negative")

def eligible_for_transfer_production_model(college_snaps_known: int) -> bool:
    if college_snaps_known < 0:
        raise ValueError("college snaps must be non-negative")
    return college_snaps_known > 0
