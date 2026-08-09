from __future__ import annotations
from dataclasses import dataclass

TRANSITIONS = {
    "PROPOSED": {"TRIAGED", "REJECTED", "DEFERRED"},
    "TRIAGED": {"APPROVED_FOR_EXPERIMENT", "REJECTED", "DEFERRED"},
    "APPROVED_FOR_EXPERIMENT": {"TESTING"},
    "TESTING": {"SUPPORTED_CANDIDATE", "REJECTED", "INCONCLUSIVE", "DEFERRED"},
    "SUPPORTED_CANDIDATE": set(),
    "REJECTED": set(),
    "INCONCLUSIVE": set(),
    "DEFERRED": set(),
}

@dataclass(frozen=True)
class HypothesisRecord:
    hypothesis_id: str
    statement: str
    target: str
    comparator: str
    disconfirming_evidence: str
    state: str = "PROPOSED"
    mechanism: str = ""

    def validate(self) -> None:
        if self.state not in TRANSITIONS:
            raise ValueError("invalid hypothesis state")
        for name in ("hypothesis_id","statement","target","comparator","disconfirming_evidence"):
            if not getattr(self, name).strip():
                raise ValueError(f"missing {name}")

def validate_transition(current: str, nxt: str) -> None:
    if current not in TRANSITIONS or nxt not in TRANSITIONS[current]:
        raise ValueError(f"invalid hypothesis transition {current}->{nxt}")
