from __future__ import annotations

"""Feature-tournament planning and evidence gating.

The tournament is a research triage mechanism.  It never emits CORE/SUPPORTED
or production promotion.  Final lifecycle changes remain under W10+W17
governance.
"""

from dataclasses import dataclass, field
from typing import Mapping, Sequence


BLOCKED_TEMPORAL_STATES = frozenset({"BANNED_FROM_PREGAME", "TEMPORAL_REVIEW_REQUIRED"})
RESEARCH_OUTCOMES = frozenset({
    "REJECT", "INCONCLUSIVE", "RETAIN_EXPERIMENTAL", "ADOPT_AS_CHALLENGER",
    "PROMOTION_REVIEW_REQUIRED",
})


@dataclass(frozen=True)
class FeatureFamilyCandidate:
    family_id: str
    target: str
    raw_field_ids: Sequence[str]
    temporal_states: Sequence[str]
    transformation_version: str
    baseline_feature_set_id: str
    feature_set_id: str
    hypotheses: Sequence[str] = field(default_factory=tuple)
    estimated_compute_class: str = "C2"

    def validate(self) -> None:
        if not self.family_id or not self.target:
            raise ValueError("family_id and target required")
        if not self.raw_field_ids:
            raise ValueError("feature family requires at least one raw field")
        if len(self.raw_field_ids) != len(self.temporal_states):
            raise ValueError("raw fields and temporal states must align")
        blocked = [s for s in self.temporal_states if s in BLOCKED_TEMPORAL_STATES]
        if blocked:
            raise ValueError(f"feature family contains blocked temporal states: {blocked}")
        if self.feature_set_id == self.baseline_feature_set_id:
            raise ValueError("candidate feature set must differ from frozen baseline")


@dataclass(frozen=True)
class FeatureTournamentEvidence:
    family_id: str
    baseline_experiment_id: str
    plus_family_experiment_id: str
    minus_family_experiment_id: str | None
    development_split: str
    primary_metric: str
    target: str
    temporal_stability_complete: bool
    subgroup_evidence_complete: bool
    replay_verified: bool
    search_multiplicity_count: int

    def validate(self) -> None:
        if self.development_split not in {"SPLIT-DEV-HIST", "SPLIT-DEV-SEL"}:
            raise ValueError("feature tournament evidence must be development-only")
        if self.search_multiplicity_count < 1:
            raise ValueError("search multiplicity must be retained")


def research_disposition(evidence: FeatureTournamentEvidence) -> str:
    evidence.validate()
    if not evidence.replay_verified:
        return "INCONCLUSIVE"
    if not evidence.temporal_stability_complete or not evidence.subgroup_evidence_complete:
        return "RETAIN_EXPERIMENTAL"
    return "PROMOTION_REVIEW_REQUIRED"


def validate_outcome(outcome: str) -> None:
    if outcome not in RESEARCH_OUTCOMES:
        raise ValueError("feature tournament cannot emit production lifecycle/promotion state")
