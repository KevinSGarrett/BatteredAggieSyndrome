from __future__ import annotations

"""Deterministic reference HPO enumerator used for contract tests and small searches.

This does not replace Optuna.  It provides a dependency-free execution/reference
surface so the experiment governance can be tested without installing a tuner.
"""

from dataclasses import dataclass
from itertools import product
from typing import Any, Callable, Iterable, Mapping, Sequence

from .lineage import content_id


@dataclass(frozen=True)
class DiscreteParameter:
    name: str
    values: Sequence[Any]

    def validate(self) -> None:
        if not self.name or not self.values:
            raise ValueError("parameter requires name and values")


@dataclass(frozen=True)
class Trial:
    trial_id: str
    number: int
    params: Mapping[str, Any]


@dataclass(frozen=True)
class TrialResult:
    trial: Trial
    objective: float
    state: str
    reason: str = ""


def enumerate_trials(study_id: str, parameters: Sequence[DiscreteParameter], budget: int) -> list[Trial]:
    if budget < 1:
        raise ValueError("budget must be positive")
    for p in parameters:
        p.validate()
    names = [p.name for p in parameters]
    if len(names) != len(set(names)):
        raise ValueError("duplicate parameter names")
    trials: list[Trial] = []
    for number, values in enumerate(product(*(p.values for p in parameters))):
        if number >= budget:
            break
        params = dict(zip(names, values))
        trial_id = content_id("TRIAL", {"study_id": study_id, "number": number, "params": params})
        trials.append(Trial(trial_id, number, params))
    return trials


def run_trials(
    trials: Sequence[Trial],
    objective: Callable[[Mapping[str, Any]], float],
    *,
    failure_value: float | None = None,
) -> list[TrialResult]:
    out: list[TrialResult] = []
    for trial in trials:
        try:
            value = float(objective(trial.params))
            out.append(TrialResult(trial, value, "COMPLETE"))
        except Exception as exc:
            if failure_value is None:
                out.append(TrialResult(trial, float("nan"), "FAILED", type(exc).__name__))
            else:
                out.append(TrialResult(trial, float(failure_value), "FAILED", type(exc).__name__))
    return out
