from __future__ import annotations

"""Replay-plan validation and deterministic evidence comparison."""

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .lineage import file_sha256


REPLAY_STATUSES = frozenset({
    "VERIFIED", "INPUT_MISMATCH", "CODE_MISMATCH", "ENVIRONMENT_MISMATCH",
    "JUDGING_RULE_MISMATCH", "ARTIFACT_MISSING", "OUTPUT_MISMATCH",
    "NONDETERMINISTIC_WITHIN_DECLARED_TOLERANCE", "FAILED",
})


@dataclass(frozen=True)
class ReplayInput:
    name: str
    uri: str
    sha256: str


@dataclass(frozen=True)
class ReplayPlan:
    experiment_id: str
    source_result_id: str
    code_commit: str
    environment_lock_hash: str
    judging_rule_seal_hash: str
    inputs: Sequence[ReplayInput]
    stochastic: bool = False
    declared_tolerance: float | None = None

    def validate(self) -> None:
        if not self.inputs:
            raise ValueError("replay plan requires immutable inputs")
        if self.stochastic and self.declared_tolerance is None:
            raise ValueError("stochastic replay requires declared tolerance")
        if self.declared_tolerance is not None and self.declared_tolerance < 0:
            raise ValueError("declared tolerance cannot be negative")


def verify_local_inputs(plan: ReplayPlan, resolver: Mapping[str, Path]) -> list[str]:
    plan.validate()
    findings: list[str] = []
    for inp in plan.inputs:
        path = resolver.get(inp.uri)
        if path is None or not Path(path).exists():
            findings.append(f"ARTIFACT_MISSING:{inp.name}:{inp.uri}")
            continue
        actual = file_sha256(Path(path))
        if actual != inp.sha256:
            findings.append(f"INPUT_MISMATCH:{inp.name}:{actual}")
    return findings


def compare_scalar_outputs(
    expected: Mapping[str, float],
    actual: Mapping[str, float],
    *,
    tolerance: float = 0.0,
) -> list[str]:
    if tolerance < 0:
        raise ValueError("tolerance cannot be negative")
    findings: list[str] = []
    for key in sorted(set(expected).union(actual)):
        if key not in expected or key not in actual:
            findings.append(f"OUTPUT_MISSING:{key}")
            continue
        if abs(float(expected[key]) - float(actual[key])) > tolerance:
            findings.append(f"OUTPUT_MISMATCH:{key}:{expected[key]}!={actual[key]}")
    return findings
