from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
PRIMARY_ANCHOR="BAS_INDEPENDENT_NATIONAL_PREGAME_EXPECTATION"

@dataclass(frozen=True)
class ExpectedMarginEvidence:
    evidence_id:str; target_game_id:str; model_id:str; model_version:str; fold_id:str
    expected_margin:float; prediction_cutoff:datetime; model_training_cutoff:datetime
    target_game_excluded:bool=True; canonical_game_group_excluded:bool=True
    uses_bas_target:bool=False; uses_aggie_underperformance_target:bool=False
    anchor_lane:str=PRIMARY_ANCHOR
    def validate(self)->None:
        if not self.target_game_excluded or not self.canonical_game_group_excluded:
            raise ValueError("Target canonical game and mirrored representations must be excluded")
        if self.model_training_cutoff>=self.prediction_cutoff:
            raise ValueError("Historical expectation model training cutoff must precede prediction cutoff")
        if self.uses_bas_target or self.uses_aggie_underperformance_target:
            raise ValueError("Primary BAS expectation anchor must be BAS-independent")
        if self.anchor_lane!=PRIMARY_ANCHOR: raise ValueError("Protected primary BAS anchor required")
        if not all([self.evidence_id,self.target_game_id,self.model_id,self.model_version,self.fold_id]):
            raise ValueError("Expectation provenance fields may not be empty")

@dataclass(frozen=True)
class BasLabel:
    game_id:str; team_id:str; actual_margin:float; expected_margin:float
    performance_residual:float; shortfall:float
    ge_3:bool; ge_7:bool; ge_14:bool; ge_21:bool
    expectation_evidence_id:str; label_definition_version:str="BAS_LABEL_V1_W15"
