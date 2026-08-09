from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

@dataclass(frozen=True)
class TransferEpisode:
    player_id: str
    source_team_id: str
    destination_team_id: str
    first_known_at: datetime
    source_context: Mapping[str, float]
    destination_context: Mapping[str, float]

@dataclass(frozen=True)
class TranslationExample:
    player_id: str
    position_scope: str
    pre_transfer_value: float
    post_transfer_target: float
    source_strength: float
    destination_strength: float
    source_context: Mapping[str, float]
    destination_context: Mapping[str, float]

def competition_strength_delta(source_strength: float, destination_strength: float) -> float:
    """Continuous context descriptor, not a fixed transfer penalty."""
    return destination_strength - source_strength

def fixed_conference_penalty(*args, **kwargs):
    raise RuntimeError("W12 forbids hand-authored fixed conference transfer penalties")
