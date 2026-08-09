from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class CoachRoleEpisode:
    coach_id: str
    role_family: str
    valid_from: datetime
    valid_to: datetime | None
    first_known_at: datetime
    responsibility_scope: str | None = None
    play_caller: bool | None = None

def eligible_role(episode: CoachRoleEpisode, *, cutoff: datetime, target_time: datetime) -> bool:
    if episode.first_known_at > cutoff:
        return False
    if target_time < episode.valid_from:
        return False
    if episode.valid_to is not None and target_time >= episode.valid_to:
        return False
    return True

def coach_residual(observed: float, expected_without_current_effect: float) -> float:
    """Abstract residual evidence, not a calibrated game-point coach effect."""
    return observed - expected_without_current_effect

def manual_coach_bonus(*args, **kwargs) -> float:
    raise RuntimeError("W13 forbids manually assigned coach point bonuses; empirical W17/W19 evidence is required.")
