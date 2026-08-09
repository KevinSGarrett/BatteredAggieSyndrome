from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Tuple

@dataclass(frozen=True)
class TamuStateOverlay:
    team_id: str
    cutoff: datetime
    national_team_state_ref: str
    canonical_pit_state_ref: str
    component_refs: Mapping[str, str]
    uncertainty_components: Mapping[str, float]
    state_version: str = "w14-v1"

    def __post_init__(self) -> None:
        if not self.team_id:
            raise ValueError("team_id is required")
        if any(v < 0 for v in self.uncertainty_components.values()):
            raise ValueError("uncertainty components must be non-negative")

@dataclass(frozen=True)
class ForecastSnapshotCandidate:
    snapshot_id: str
    game_id: str
    cutoff: datetime
    cadence_candidate_id: str
    immutable: bool = True

    def __post_init__(self) -> None:
        if not self.immutable:
            raise ValueError("A&M forecast snapshots are immutable")

def validate_snapshot_order(snapshots: Tuple[ForecastSnapshotCandidate, ...]) -> bool:
    """Reference-only ordering check; W14 does not freeze an operational cadence."""
    return all(a.cutoff <= b.cutoff for a, b in zip(snapshots, snapshots[1:]))
