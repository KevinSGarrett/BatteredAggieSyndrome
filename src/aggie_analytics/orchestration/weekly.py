from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .checkpoints import LocalCheckpointStore
from .contracts import StepResult, WeeklyRunIdentity, WorkflowSummary, stable_hash

StepFn = Callable[[WeeklyRunIdentity, Mapping[str, StepResult]], StepResult]

DEFAULT_WEEKLY_STEPS = (
    "INGEST", "QA_QUARANTINE", "PIT_STATE", "FEATURES", "TRAIN_CHALLENGER",
    "CALIBRATE", "GOVERNED_EVALUATION", "PROMOTION_OR_RETAIN", "FORECAST",
    "PUBLISH", "RESULT_SCORING", "POSTMORTEM", "RESEARCH_QUEUE",
)


@dataclass
class LocalWeeklyOrchestrator:
    checkpoints: LocalCheckpointStore
    steps: Mapping[str, StepFn]
    order: tuple[str, ...] = DEFAULT_WEEKLY_STEPS

    def validate(self) -> None:
        missing=[s for s in self.order if s not in self.steps]
        if missing: raise ValueError(f"missing weekly step implementations: {missing}")
        if len(set(self.order)) != len(self.order): raise ValueError("duplicate weekly step id")

    def run(self, identity: WeeklyRunIdentity) -> WorkflowSummary:
        self.validate(); resumed=self.checkpoints.initialize(identity)
        results: dict[str,StepResult]={}
        for step_id in self.order:
            prior=self.checkpoints.get(identity.run_id,step_id)
            if prior is not None:
                results[step_id]=prior
                if prior.state != "SUCCEEDED":
                    status="QUARANTINED" if prior.state=="QUARANTINED" else "FAILED"
                    return WorkflowSummary(identity.run_id,status,self.checkpoints.completed_steps(identity.run_id),self.checkpoints.checkpoint_ref(identity.run_id),True)
                continue
            result=self.steps[step_id](identity,dict(results))
            if result.step_id != step_id: raise ValueError(f"step returned wrong identity: {result.step_id} != {step_id}")
            result.validate(); self.checkpoints.record(identity.run_id,result); results[step_id]=result
            if result.state != "SUCCEEDED":
                status="QUARANTINED" if result.state=="QUARANTINED" else "FAILED"
                return WorkflowSummary(identity.run_id,status,self.checkpoints.completed_steps(identity.run_id),self.checkpoints.checkpoint_ref(identity.run_id),resumed)
        summary=WorkflowSummary(identity.run_id,"SUCCEEDED",self.checkpoints.completed_steps(identity.run_id),self.checkpoints.checkpoint_ref(identity.run_id),resumed)
        summary.validate(); return summary


def result(step_id: str, payload: object, *, output_ref: str | None=None, state: str="SUCCEEDED", detail: str="") -> StepResult:
    h=stable_hash(payload)
    return StepResult(step_id,state,output_ref or f"memory:{step_id}:{h[:16]}",h,detail)
