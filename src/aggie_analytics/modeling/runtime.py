from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Mapping, Protocol, Sequence

@dataclass(frozen=True)
class FeatureVector:
    game_id: str
    forecast_cutoff: datetime
    feature_snapshot_id: str
    values: Mapping[str, float]
    lineage_refs: tuple[str, ...]
    def validate(self) -> None:
        if not self.game_id or not self.feature_snapshot_id or not self.lineage_refs:
            raise ValueError('game, feature snapshot and lineage are required')
        if self.forecast_cutoff.tzinfo is None:
            raise ValueError('forecast_cutoff must be timezone-aware')
        if not self.values:
            raise ValueError('at least one feature is required')
        if any(not isinstance(v, (int,float)) or isinstance(v,bool) for v in self.values.values()):
            raise ValueError('feature values must be numeric')

@dataclass(frozen=True)
class ModelArtifact:
    model_id: str
    model_version: str
    model_family: str
    target: str
    feature_names: tuple[str, ...]
    parameters: Mapping[str, object]
    training_data_ref: str
    training_cutoff: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    protected_results_used: bool = False
    production_selected: bool = False
    metadata: Mapping[str, str] = field(default_factory=dict)
    def validate(self) -> None:
        if not all((self.model_id,self.model_version,self.model_family,self.target,self.training_data_ref)):
            raise ValueError('model identity/target/training lineage are required')
        if self.training_cutoff.tzinfo is None or self.created_at.tzinfo is None:
            raise ValueError('timestamps must be timezone-aware')
        if self.protected_results_used:
            raise ValueError('W20 starter artifacts may not be fit/selected using protected results')
        if self.production_selected:
            raise ValueError('W20 starter artifacts may not self-declare production selection')
    @property
    def artifact_sha256(self) -> str:
        self.validate()
        payload={
            'model_id':self.model_id,'model_version':self.model_version,'model_family':self.model_family,
            'target':self.target,'feature_names':list(self.feature_names),'parameters':self.parameters,
            'training_data_ref':self.training_data_ref,'training_cutoff':self.training_cutoff.isoformat(),
            'protected_results_used':self.protected_results_used,'production_selected':self.production_selected,
            'metadata':dict(sorted(self.metadata.items())),
        }
        return sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()

@dataclass(frozen=True)
class ScalarPrediction:
    game_id: str
    model_id: str
    model_version: str
    target: str
    value: float
    forecast_cutoff: datetime
    feature_snapshot_id: str
    artifact_sha256: str
    lineage_refs: tuple[str, ...]
    def validate(self)->None:
        if not all((self.game_id,self.model_id,self.model_version,self.target,self.feature_snapshot_id,self.artifact_sha256)):
            raise ValueError('prediction identity and lineage are required')
        if self.forecast_cutoff.tzinfo is None or not self.lineage_refs:
            raise ValueError('prediction cutoff and lineage are required')

class ScalarModelRuntime(Protocol):
    artifact: ModelArtifact
    def predict(self, row: FeatureVector) -> ScalarPrediction: ...


def assert_training_precedes_prediction(artifact: ModelArtifact, row: FeatureVector) -> None:
    artifact.validate(); row.validate()
    if artifact.training_cutoff >= row.forecast_cutoff:
        raise ValueError('model training cutoff must precede forecast cutoff')
