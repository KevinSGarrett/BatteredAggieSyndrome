from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

@dataclass(frozen=True)
class AdvancedPregameState:
    game_id:str; cutoff:datetime; player_state_ref:str; availability_state_ref:str; transfer_prior_ref:str
    coaching_context_ref:str; mechanics_context_ref:str; feature_snapshot_ref:str; lineage_refs:tuple[str,...]
    values:Mapping[str,float]
    def validate(self)->None:
        if self.cutoff.tzinfo is None: raise ValueError('cutoff must be timezone-aware')
        if not self.lineage_refs or not self.feature_snapshot_ref: raise ValueError('PIT feature lineage required')
        if any(not isinstance(v,(int,float)) or isinstance(v,bool) for v in self.values.values()): raise ValueError('values must be numeric')
