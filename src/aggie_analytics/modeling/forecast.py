from __future__ import annotations
from dataclasses import dataclass
from .contracts import JointScoreDistribution, UncertaintySignal
from .coherence import derive_summary, bas_severity_probabilities
from .uncertainty import validate_uncertainty_signals

@dataclass(frozen=True)
class ForecastSnapshot:
    snapshot_id:str; game_id:str; feature_snapshot_id:str; model_artifact_sha256:str
    distribution:JointScoreDistribution; bas_anchor_expected_margin:float
    uncertainty:tuple[UncertaintySignal,...]=(); tamu_state_ref:str|None=None; specialization_candidate_id:str|None=None
    lineage_refs:tuple[str,...]=()
    def validate(self)->None:
        self.distribution.validate(); validate_uncertainty_signals(list(self.uncertainty))
        if not all((self.snapshot_id,self.game_id,self.feature_snapshot_id,self.model_artifact_sha256)) or not self.lineage_refs:
            raise ValueError('forecast snapshot identity/lineage required')
    def public_summary(self)->dict[str,float]:
        self.validate(); out=derive_summary(self.distribution); out.update({f'bas_{k}':v for k,v in bas_severity_probabilities(self.distribution,self.bas_anchor_expected_margin).items()}); return out
