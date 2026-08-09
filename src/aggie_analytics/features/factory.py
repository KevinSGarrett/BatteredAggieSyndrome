from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from aggie_analytics.temporal.state import PitState
from aggie_analytics.lineage import LineageRecord, make_lineage
@dataclass(frozen=True)
class FeatureSpec:
    feature_id:str; domain:str; attribute:str; aggregation:str='LATEST'; default:Any=None
@dataclass(frozen=True)
class FeatureVector:
    state_id:str; values:dict[str,Any]; lineage:tuple[LineageRecord,...]

def build_features(state:PitState, specs)->FeatureVector:
    values={}; lineage=[]
    for spec in specs:
        candidates=[o for o in state.observations if o.domain==spec.domain and spec.attribute in (o.attributes or {})]
        if spec.aggregation=='LATEST': val=(candidates[-1].attributes or {})[spec.attribute] if candidates else spec.default
        elif spec.aggregation=='COUNT': val=len(candidates)
        elif spec.aggregation=='MEAN':
            nums=[float((o.attributes or {})[spec.attribute]) for o in candidates]; val=sum(nums)/len(nums) if nums else spec.default
        else: raise ValueError(f'unsupported aggregation {spec.aggregation}')
        values[spec.feature_id]=val
        lineage.append(make_lineage('FEATURE',spec.feature_id,[o.observation_id for o in candidates],f'w19.feature.{spec.aggregation.lower()}',{'state_id':state.state_id,'domain':spec.domain,'attribute':spec.attribute}))
    return FeatureVector(state.state_id,values,tuple(lineage))
