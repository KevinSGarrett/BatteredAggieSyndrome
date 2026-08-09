from __future__ import annotations

"""One-way handoff from W18 research evidence to the external W17 promotion gate."""

from dataclasses import dataclass
from typing import Mapping, Sequence

RESEARCH_HANDOFF_STATES = frozenset({
    "REJECT", "INCONCLUSIVE", "RETAIN_RESEARCH", "ADOPT_AS_CHALLENGER",
    "PROMOTION_REVIEW_REQUIRED",
})


@dataclass(frozen=True)
class PromotionReviewPacket:
    experiment_id: str
    result_id: str
    replay_id: str
    judging_rule_seal_hash: str
    development_evidence_hash: str
    artifact_manifest_hash: str
    requested_state: str
    notes: str = ""

    def validate(self) -> None:
        if self.requested_state != "PROMOTION_REVIEW_REQUIRED":
            raise ValueError("W18 can only request external promotion review")
        for field in (
            self.experiment_id, self.result_id, self.replay_id,
            self.judging_rule_seal_hash, self.development_evidence_hash,
            self.artifact_manifest_hash,
        ):
            if not field:
                raise ValueError("promotion review packet fields cannot be blank")


def validate_research_handoff(decision: str) -> None:
    if decision not in RESEARCH_HANDOFF_STATES:
        raise ValueError("research plane cannot emit champion/promotion state")


def contains_protected_result_feedback(packet: Mapping[str, object]) -> bool:
    forbidden = {
        "protected_metrics", "protected_holdout_metrics", "forward_shadow_metrics",
        "promotion_threshold_result", "champion_decision",
    }
    return bool(forbidden.intersection(packet))
