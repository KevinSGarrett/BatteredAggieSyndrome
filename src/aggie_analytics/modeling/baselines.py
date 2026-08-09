from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import math
from typing import Iterable, Sequence
from .runtime import FeatureVector, ModelArtifact, ScalarPrediction, assert_training_precedes_prediction

@dataclass
class ConstantProbabilityBaseline:
    artifact: ModelArtifact
    probability: float
    def __post_init__(self):
        if not 0 <= self.probability <= 1: raise ValueError('probability must be in [0,1]')
    def predict(self,row:FeatureVector)->ScalarPrediction:
        assert_training_precedes_prediction(self.artifact,row)
        return ScalarPrediction(row.game_id,self.artifact.model_id,self.artifact.model_version,self.artifact.target,
            float(self.probability),row.forecast_cutoff,row.feature_snapshot_id,self.artifact.artifact_sha256,row.lineage_refs)

@dataclass
class LinearLogisticBaseline:
    artifact: ModelArtifact
    coefficients: dict[str,float]
    intercept: float = 0.0
    def predict(self,row:FeatureVector)->ScalarPrediction:
        assert_training_precedes_prediction(self.artifact,row)
        missing=set(self.coefficients)-set(row.values)
        if missing: raise ValueError(f'missing model features: {sorted(missing)}')
        z=self.intercept+sum(self.coefficients[k]*float(row.values[k]) for k in self.coefficients)
        p=1/(1+math.exp(-max(min(z,40.0),-40.0)))
        return ScalarPrediction(row.game_id,self.artifact.model_id,self.artifact.model_version,self.artifact.target,p,
            row.forecast_cutoff,row.feature_snapshot_id,self.artifact.artifact_sha256,row.lineage_refs)

@dataclass
class EloProbabilityBaseline:
    artifact: ModelArtifact
    team_rating_feature: str='team_elo'
    opponent_rating_feature: str='opponent_elo'
    home_adjustment: float=0.0
    scale: float=400.0
    def predict(self,row:FeatureVector)->ScalarPrediction:
        assert_training_precedes_prediction(self.artifact,row)
        if self.scale<=0: raise ValueError('scale must be positive')
        try: delta=float(row.values[self.team_rating_feature])-float(row.values[self.opponent_rating_feature])+self.home_adjustment
        except KeyError as e: raise ValueError(f'missing Elo feature: {e.args[0]}') from e
        p=1/(1+10**(-delta/self.scale))
        return ScalarPrediction(row.game_id,self.artifact.model_id,self.artifact.model_version,self.artifact.target,p,
            row.forecast_cutoff,row.feature_snapshot_id,self.artifact.artifact_sha256,row.lineage_refs)

@dataclass(frozen=True)
class BoostingAdapterSpec:
    backend: str
    objective: str
    feature_names: tuple[str,...]
    params: dict[str,object]
    def validate(self)->None:
        if self.backend not in {'xgboost','lightgbm','catboost','sklearn_hist_gradient_boosting'}:
            raise ValueError('unsupported boosting backend')
        if not self.objective or not self.feature_names: raise ValueError('objective/features required')

class OptionalBoostingRuntime:
    """Dependency boundary only. W20 does not force a boosting library into the base install."""
    def __init__(self, artifact:ModelArtifact, spec:BoostingAdapterSpec, predictor=None):
        artifact.validate(); spec.validate(); self.artifact=artifact; self.spec=spec; self._predictor=predictor
    @property
    def available(self)->bool: return self._predictor is not None
    def predict(self,row:FeatureVector)->ScalarPrediction:
        assert_training_precedes_prediction(self.artifact,row)
        if self._predictor is None:
            raise RuntimeError('boosting backend is optional and no trained predictor was injected')
        x=[float(row.values[k]) for k in self.spec.feature_names]
        value=float(self._predictor(x))
        return ScalarPrediction(row.game_id,self.artifact.model_id,self.artifact.model_version,self.artifact.target,value,
            row.forecast_cutoff,row.feature_snapshot_id,self.artifact.artifact_sha256,row.lineage_refs)
