from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence

@dataclass(frozen=True)
class PromotionContext:
    protocol_sealed: bool
    required_artifacts_present: bool
    required_threshold_ids: Sequence[str]
    threshold_values: Mapping[str, float | None]
    protected_results_available: bool = False
    precommitted_criteria_passed: bool | None = None

def evaluate_promotion(ctx: PromotionContext) -> str:
    if not ctx.protocol_sealed:
        return "BLOCKED_PROTOCOL_UNSEALED"
    if not ctx.required_artifacts_present:
        return "BLOCKED_ARTIFACT_MISSING"
    for tid in ctx.required_threshold_ids:
        if ctx.threshold_values.get(tid) is None:
            return "BLOCKED_THRESHOLD_UNSET"
    if not ctx.protected_results_available:
        return "PROTECTED_READY"
    if ctx.precommitted_criteria_passed is True:
        return "PROMOTE"
    if ctx.precommitted_criteria_passed is False:
        return "REJECT"
    return "INCONCLUSIVE"
