from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class ReplayReport:
    experiment_id: str
    attempt_id: str
    checks: Mapping[str, bool]
    failure_code: str | None = None

    @property
    def status(self) -> str:
        if self.failure_code:
            return "MISMATCH"
        return "VERIFIED" if self.checks and all(self.checks.values()) else "MISMATCH"

def compare_hashes(expected: Mapping[str,str], actual: Mapping[str,str]) -> ReplayReport:
    keys = sorted(set(expected) | set(actual))
    checks = {k: expected.get(k) == actual.get(k) for k in keys}
    return ReplayReport(
        experiment_id="UNKNOWN",
        attempt_id="UNKNOWN",
        checks=checks,
        failure_code=None if all(checks.values()) else "HASH_MISMATCH",
    )
