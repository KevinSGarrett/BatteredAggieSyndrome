from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from .identity import content_id

ALLOWED_SPLITS = frozenset({"SPLIT-DEV-HIST", "SPLIT-DEV-SEL"})
FORBIDDEN_SPLITS = frozenset({"SPLIT-PROTECTED", "SPLIT-FORWARD"})

@dataclass(frozen=True)
class SearchParameter:
    name: str
    kind: str
    domain: Mapping[str, Any]
    condition: Mapping[str, Any] | None = None

    def validate(self) -> None:
        if self.kind not in {"int","float","log_float","categorical","conditional"}:
            raise ValueError("unsupported parameter kind")
        if not self.name:
            raise ValueError("parameter name required")
        if self.kind == "categorical" and not self.domain.get("choices"):
            raise ValueError("categorical choices required")
        if self.kind in {"int","float","log_float"}:
            if "low" not in self.domain or "high" not in self.domain:
                raise ValueError("numeric bounds required")
            if self.domain["low"] >= self.domain["high"]:
                raise ValueError("low must be < high")
        if self.kind == "log_float" and self.domain["low"] <= 0:
            raise ValueError("log-float low must be positive")

@dataclass(frozen=True)
class HPOStudySpec:
    candidate_family: str
    search_space_version: str
    parameters: Sequence[SearchParameter]
    development_split: str
    objective_metrics: Sequence[str]
    trial_budget: int
    concurrency: int = 1
    sampler: str = "TPE"
    pruner: str = "NONE"
    storage_backend: str = "JOURNAL"
    paid_compute_approved: bool = False

    def validate(self) -> None:
        if self.development_split not in ALLOWED_SPLITS:
            raise ValueError("HPO objective must use approved development split")
        if not self.objective_metrics:
            raise ValueError("objective metric required")
        if self.trial_budget < 1 or self.concurrency < 1:
            raise ValueError("positive trial budget/concurrency required")
        if self.storage_backend == "SQLITE_DISTRIBUTED_NFS":
            raise ValueError("SQLite is not allowed as distributed/NFS HPO coordination backend")
        for p in self.parameters:
            p.validate()

    @property
    def study_id(self) -> str:
        self.validate()
        payload = {
            "candidate_family": self.candidate_family,
            "search_space_version": self.search_space_version,
            "parameters": [
                {"name": p.name, "kind": p.kind, "domain": dict(p.domain), "condition": dict(p.condition) if p.condition else None}
                for p in self.parameters
            ],
            "development_split": self.development_split,
            "objective_metrics": list(self.objective_metrics),
            "trial_budget": self.trial_budget,
            "concurrency": self.concurrency,
            "sampler": self.sampler,
            "pruner": self.pruner,
            "storage_backend": self.storage_backend,
        }
        return content_id("HPO", payload, 20)
