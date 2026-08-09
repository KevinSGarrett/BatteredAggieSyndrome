from __future__ import annotations

"""Model-tournament planning with mandatory simple comparators and lane isolation."""

from dataclasses import dataclass, field
from typing import Mapping, Sequence


SIMPLE_BASELINE_CLASSES = frozenset({"EMPIRICAL", "ELO", "LOGISTIC_GLM", "SIMPLE_SCORE"})
RESEARCH_DECISIONS = frozenset({
    "REJECT", "INCONCLUSIVE", "RETAIN_RESEARCH", "ADOPT_AS_CHALLENGER",
    "PROMOTION_REVIEW_REQUIRED",
})


@dataclass(frozen=True)
class ModelEntrant:
    entrant_id: str
    model_family: str
    model_class: str
    target: str
    lane: str
    experiment_id: str
    complexity_class: str
    coherent_output: bool
    tamu_specialization_id: str | None = None
    bas_label_version: str | None = None


@dataclass(frozen=True)
class ModelTournamentPlan:
    tournament_id: str
    target: str
    development_split: str
    lane: str
    entrants: Sequence[ModelEntrant]
    primary_metric: str
    metric_direction: str
    tamu_specialization: bool = False
    bas_target: bool = False

    def validate(self) -> None:
        if self.development_split not in {"SPLIT-DEV-HIST", "SPLIT-DEV-SEL"}:
            raise ValueError("model tournament must be development-only")
        if self.metric_direction not in {"min", "max"}:
            raise ValueError("metric direction must be min/max")
        if len(self.entrants) < 2:
            raise ValueError("model tournament requires at least two entrants")
        if any(e.lane != self.lane for e in self.entrants):
            raise ValueError("pure-football and market-augmented entrants cannot share one direct tournament")
        if not any(e.model_class in SIMPLE_BASELINE_CLASSES for e in self.entrants):
            raise ValueError("model tournament requires at least one simple baseline")
        if self.tamu_specialization and not any(e.tamu_specialization_id == "TAMU-SP-00" for e in self.entrants):
            raise ValueError("A&M specialization tournament requires TAMU-SP-00 no-adjustment baseline")
        if any(not e.coherent_output for e in self.entrants):
            raise ValueError("entrant violates W16 cross-target coherence contract")
        if self.bas_target:
            versions = {e.bas_label_version for e in self.entrants}
            if None in versions or len(versions) != 1:
                raise ValueError("BAS tournament entrants must use one frozen W15 label version")


def validate_research_decision(decision: str) -> None:
    if decision not in RESEARCH_DECISIONS:
        raise ValueError("model tournament cannot promote production champion")
