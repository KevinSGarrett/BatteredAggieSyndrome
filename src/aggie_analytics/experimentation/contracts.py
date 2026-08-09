from __future__ import annotations
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Sequence
import json


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class ExperimentSpec:
    hypothesis_id: str
    task_id: str
    candidate_family: str
    code_ref: str
    data_snapshot_id: str
    feature_registry_version: str
    model_config: Mapping[str, Any]
    split_protocol_id: str
    metric_registry_hash: str
    threshold_method_hash: str
    environment_fingerprint: str
    random_seeds: Sequence[int]
    resource_budget_id: str
    parent_experiment_id: str | None = None

    def identity_payload(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "parent_experiment_id": self.parent_experiment_id,
            "task_id": self.task_id,
            "candidate_family": self.candidate_family,
            "code_ref": self.code_ref,
            "data_snapshot_id": self.data_snapshot_id,
            "feature_registry_version": self.feature_registry_version,
            "model_config": dict(self.model_config),
            "split_protocol_id": self.split_protocol_id,
            "metric_registry_hash": self.metric_registry_hash,
            "threshold_method_hash": self.threshold_method_hash,
            "environment_fingerprint": self.environment_fingerprint,
            "random_seeds": list(self.random_seeds),
            "resource_budget_id": self.resource_budget_id,
        }

    @property
    def experiment_id(self) -> str:
        return "EXP-" + digest(self.identity_payload())[:20]

@dataclass(frozen=True)
class ExperimentResultPacket:
    experiment_id: str
    attempt_id: str
    artifact_manifest_hash: str
    development_metrics: Mapping[str, float]
    environment_fingerprint: str
    replay_status: str
    recommendation: str
    reason: str
    protected_metrics: None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    _allowed_recommendations = frozenset({"REJECT","INCONCLUSIVE","ADOPT_AS_CHALLENGER","PROMOTION_REVIEW_REQUIRED"})

    def validate(self) -> None:
        if self.recommendation not in self._allowed_recommendations:
            raise ValueError("research result cannot self-promote or emit an unknown recommendation")
        if self.protected_metrics is not None:
            raise ValueError("research-plane result packet cannot contain protected metrics")
        if self.replay_status not in {"PENDING","VERIFIED","MISMATCH","NOT_REQUIRED"}:
            raise ValueError("invalid replay status")

    @property
    def result_id(self) -> str:
        self.validate()
        payload={"experiment_id":self.experiment_id,"attempt_id":self.attempt_id,"artifact_manifest_hash":self.artifact_manifest_hash,
                 "development_metrics":dict(self.development_metrics),"environment_fingerprint":self.environment_fingerprint,
                 "replay_status":self.replay_status,"recommendation":self.recommendation,"reason":self.reason,"extra":dict(self.extra)}
        return "RES-" + digest(payload)[:24]
