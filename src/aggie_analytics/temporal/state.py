from __future__ import annotations
from dataclasses import dataclass
from .contracts import ForecastCutoff, TemporalObservation
from .eligibility import evaluate_eligibility, knowledge_time
from aggie_analytics.lineage import LineageRecord, make_lineage
@dataclass(frozen=True)
class PitState:
    state_id:str; cutoff_id:str; observations:tuple[TemporalObservation,...]; lineage:LineageRecord

def build_pit_state(observations, cutoff:ForecastCutoff)->PitState:
    eligible=[]
    for obs in observations:
        result=evaluate_eligibility(obs,cutoff)
        if result.eligible: eligible.append(obs)
    eligible.sort(key=lambda o:(knowledge_time(o),o.observation_id))
    parent_ids=[o.observation_id for o in eligible]
    lineage=make_lineage('PIT_STATE',f'state_{cutoff.cutoff_id}',parent_ids,'w19.pit.fail_closed',{'cutoff':cutoff.cutoff_id})
    return PitState(f'state_{cutoff.cutoff_id}',cutoff.cutoff_id,tuple(eligible),lineage)
