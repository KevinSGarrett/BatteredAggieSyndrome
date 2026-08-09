from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence, Mapping

PROTECTED_PREFIXES = (
    "governance/PROTECTED_SPLIT",
    "governance/METRIC_REGISTRY",
    "governance/THRESHOLD_PRECOMMITMENT",
    "governance/PROMOTION_DECISION",
    "governance/PROTECTED_JUDGING_RULE",
)

@dataclass(frozen=True)
class WorktreePlan:
    experiment_id: str
    isolation_mode: str
    mutation_scope: Sequence[str]
    resource_budget: Mapping[str, float | int | str]
    paid_compute_approved: bool = False

    def validate(self) -> None:
        if self.isolation_mode not in {"GIT_WORKTREE","IMMUTABLE_SOURCE_SNAPSHOT"}:
            raise ValueError("invalid isolation mode")
        if not self.mutation_scope:
            raise ValueError("mutation scope required")
        for p in self.mutation_scope:
            if any(p.startswith(prefix) for prefix in PROTECTED_PREFIXES):
                raise PermissionError(f"protected path in mutation scope: {p}")
        if self.resource_budget.get("paid_remote_compute") and not self.paid_compute_approved:
            raise PermissionError("paid remote compute requires explicit approval")
