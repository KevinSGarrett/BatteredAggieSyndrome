from __future__ import annotations

"""Admission policy for Phase-5 neural/sequence/graph challengers."""

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ChallengerAdmissionEvidence:
    candidate_class: str
    conventional_baseline_materialized: bool
    baseline_saturated_or_specific_gap_demonstrated: bool
    protected_protocol_sealed: bool
    development_only_plan: bool
    local_resource_budget_declared: bool
    incremental_hypothesis: str
    complexity_rationale: str
    required_inputs_available: bool
    rights_ok: bool
    maintenance_owner: str

    def evaluate(self) -> tuple[str, tuple[str, ...]]:
        reasons: list[str] = []
        if not self.conventional_baseline_materialized:
            reasons.append("CONVENTIONAL_BASELINE_NOT_MATERIALIZED")
        if not self.baseline_saturated_or_specific_gap_demonstrated:
            reasons.append("NO_INCREMENTAL_GAP_DEMONSTRATED")
        if not self.protected_protocol_sealed:
            reasons.append("PROTECTED_PROTOCOL_UNSEALED")
        if not self.development_only_plan:
            reasons.append("NON_DEVELOPMENT_SEARCH_PLAN")
        if not self.local_resource_budget_declared:
            reasons.append("RESOURCE_BUDGET_MISSING")
        if not self.incremental_hypothesis.strip():
            reasons.append("HYPOTHESIS_MISSING")
        if not self.complexity_rationale.strip():
            reasons.append("COMPLEXITY_RATIONALE_MISSING")
        if not self.required_inputs_available:
            reasons.append("REQUIRED_INPUTS_UNAVAILABLE")
        if not self.rights_ok:
            reasons.append("RIGHTS_NOT_CLEARED")
        if not self.maintenance_owner.strip():
            reasons.append("MAINTENANCE_OWNER_MISSING")
        if reasons:
            return "BLOCKED", tuple(reasons)
        return "ADMITTED_RESEARCH_ONLY", ()
