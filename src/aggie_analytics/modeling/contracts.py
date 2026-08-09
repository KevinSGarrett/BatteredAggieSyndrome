
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class ScoreOutcome:
    team_score: int
    opponent_score: int
    probability: float
    def validate(self) -> None:
        if isinstance(self.team_score, bool) or isinstance(self.opponent_score, bool):
            raise ValueError("scores must be integers")
        if not isinstance(self.team_score, int) or not isinstance(self.opponent_score, int):
            raise ValueError("scores must be integers")
        if self.team_score < 0 or self.opponent_score < 0:
            raise ValueError("scores must be nonnegative")
        if not 0.0 <= float(self.probability) <= 1.0:
            raise ValueError("probability must be in [0,1]")

@dataclass(frozen=True)
class JointScoreDistribution:
    distribution_id: str
    model_id: str
    model_version: str
    forecast_cutoff: datetime
    outcomes: tuple[ScoreOutcome, ...]
    overtime_team_win_probability: float | None = None
    tolerance: float = 1e-9

    def validate(self) -> None:
        if not all([self.distribution_id, self.model_id, self.model_version]):
            raise ValueError("distribution/model identity fields are required")
        if not self.outcomes:
            raise ValueError("at least one score outcome is required")
        seen=set()
        total=0.0
        tie_mass=0.0
        for outcome in self.outcomes:
            outcome.validate()
            key=(outcome.team_score,outcome.opponent_score)
            if key in seen:
                raise ValueError("duplicate score support point")
            seen.add(key)
            total += float(outcome.probability)
            if outcome.team_score == outcome.opponent_score:
                tie_mass += float(outcome.probability)
        if abs(total-1.0) > self.tolerance:
            raise ValueError(f"joint distribution must sum to one, got {total}")
        if tie_mass > self.tolerance:
            if self.overtime_team_win_probability is None:
                raise ValueError("tie mass requires explicit overtime resolution probability")
            if not 0.0 <= float(self.overtime_team_win_probability) <= 1.0:
                raise ValueError("overtime team win probability must be in [0,1]")

@dataclass(frozen=True)
class SimulationScenario:
    scenario_id: str
    baseline_snapshot_id: str
    weight: float
    overrides: dict[str, Any] = field(default_factory=dict)
    lineage: dict[str, str] = field(default_factory=dict)
    def validate(self) -> None:
        if not self.scenario_id or not self.baseline_snapshot_id:
            raise ValueError("scenario and baseline snapshot IDs are required")
        if not 0.0 <= float(self.weight) <= 1.0:
            raise ValueError("scenario weight must be in [0,1]")
        if not self.lineage:
            raise ValueError("scenario lineage is required")

@dataclass(frozen=True)
class UncertaintySignal:
    name: str
    category: str
    status: str
    magnitude: float | None = None
    calibrated: bool = False
    evidence_id: str | None = None
