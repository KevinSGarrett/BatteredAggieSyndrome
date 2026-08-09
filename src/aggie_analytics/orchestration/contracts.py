from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Mapping

TERMINAL_STEP_STATES = frozenset({"SUCCEEDED", "FAILED", "QUARANTINED", "SKIPPED"})


def stable_hash(payload: object) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WeeklyRunIdentity:
    run_id: str
    forecast_week: str
    as_of: datetime
    source_snapshot_refs: tuple[str, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.run_id or not self.forecast_week:
            raise ValueError("run_id and forecast_week are required")
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

    @property
    def fingerprint(self) -> str:
        self.validate()
        return stable_hash({
            "run_id": self.run_id,
            "forecast_week": self.forecast_week,
            "as_of": self.as_of.isoformat(),
            "source_snapshot_refs": list(self.source_snapshot_refs),
            "metadata": dict(sorted(self.metadata.items())),
        })


@dataclass(frozen=True)
class StepResult:
    step_id: str
    state: str
    output_ref: str
    output_hash: str
    detail: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.step_id or self.state not in TERMINAL_STEP_STATES:
            raise ValueError("invalid step result")
        if self.state == "SUCCEEDED" and (not self.output_ref or not self.output_hash):
            raise ValueError("successful steps require output_ref and output_hash")


@dataclass(frozen=True)
class WorkflowSummary:
    run_id: str
    status: str
    completed_steps: tuple[str, ...]
    checkpoint_ref: str
    resumed: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def validate(self) -> None:
        if self.status not in {"SUCCEEDED", "FAILED", "BLOCKED", "QUARANTINED"}:
            raise ValueError("invalid workflow status")
        if not self.run_id or not self.checkpoint_ref or self.created_at.tzinfo is None:
            raise ValueError("workflow identity/checkpoint/timestamp required")
