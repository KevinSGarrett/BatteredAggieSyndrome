from __future__ import annotations
from dataclasses import dataclass
from .contracts import ExpectedMarginEvidence
from .labels import build_tamu_bas_label, validate_nested_probability_forecast

@dataclass(frozen=True)
class BasProbabilityForecast:
    game_id:str; anchor_evidence_id:str; p_ge_3:float; p_ge_7:float; p_ge_14:float; p_ge_21:float
    model_artifact_sha256:str; lineage_refs:tuple[str,...]
    def validate(self)->None:
        if not self.lineage_refs or not self.anchor_evidence_id or not self.model_artifact_sha256: raise ValueError('BAS lineage required')
        validate_nested_probability_forecast(self.p_ge_3,self.p_ge_7,self.p_ge_14,self.p_ge_21)

def label_completed_game(game_id:str, actual_margin:float, anchor:ExpectedMarginEvidence):
    return build_tamu_bas_label(game_id,actual_margin,anchor)
