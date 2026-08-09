from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping, Sequence

ALLOWED_RESEARCH_DECISIONS = frozenset({"REJECT","INCONCLUSIVE","RETAIN_EXPERIMENTAL","RETAIN_RESEARCH","ADOPT_AS_CHALLENGER","PROMOTION_REVIEW_REQUIRED"})
PROHIBITED_DECISIONS = frozenset({"PROMOTE","CORE","SUPPORTED"})

@dataclass(frozen=True)
class TournamentEntry:
    entry_id: str
    experiment_id: str
    candidate_class: str
    development_metrics: Mapping[str, float]
    replay_status: str = "PENDING"
    resource_cost: float = 0.0
    warnings: Sequence[str] = field(default_factory=tuple)

@dataclass(frozen=True)
class TournamentSpec:
    tournament_id: str
    kind: str
    target: str
    development_split: str
    primary_metric: str
    metric_direction: str
    entrants: Sequence[str]
    baseline_entry_id: str
    lane: str = "PURE_FOOTBALL"
    tamu_specialization: bool = False

    def validate(self) -> None:
        if self.kind not in {"FEATURE","MODEL"}:
            raise ValueError("tournament kind must be FEATURE or MODEL")
        if self.development_split not in {"SPLIT-DEV-HIST","SPLIT-DEV-SEL"}:
            raise ValueError("tournament must use development-only split")
        if self.metric_direction not in {"min","max"}:
            raise ValueError("metric direction must be min/max")
        if len(set(self.entrants)) < 2:
            raise ValueError("at least two distinct entrants required")
        if self.baseline_entry_id not in self.entrants:
            raise ValueError("baseline must be an entrant")
        if self.tamu_specialization and self.baseline_entry_id != "TAMU-SP-00":
            raise ValueError("A&M specialization tournament must use TAMU-SP-00 baseline")

def rank_entries(spec: TournamentSpec, entries: Sequence[TournamentEntry]) -> list[TournamentEntry]:
    spec.validate()
    by_id = {e.entry_id: e for e in entries}
    missing = set(spec.entrants) - set(by_id)
    if missing:
        raise ValueError(f"missing tournament entries: {sorted(missing)}")
    for e in entries:
        if spec.primary_metric not in e.development_metrics:
            raise ValueError(f"{e.entry_id} missing primary metric")
    reverse = spec.metric_direction == "max"
    return sorted((by_id[i] for i in spec.entrants), key=lambda e: (e.development_metrics[spec.primary_metric], e.entry_id), reverse=reverse)

def validate_research_decision(decision: str) -> None:
    if decision in PROHIBITED_DECISIONS or decision not in ALLOWED_RESEARCH_DECISIONS:
        raise ValueError("tournament/research plane cannot emit production feature/model promotion")
