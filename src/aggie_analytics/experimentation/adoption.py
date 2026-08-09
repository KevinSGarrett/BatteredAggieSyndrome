from __future__ import annotations

ALLOWED = frozenset({"REJECT","INCONCLUSIVE","RETAIN_RESEARCH","ADOPT_AS_CHALLENGER","PROMOTION_REVIEW_REQUIRED"})

def adoption_decision(*, replay_status: str, recommendation: str) -> str:
    if recommendation == "PROMOTE":
        raise ValueError("research plane cannot promote")
    if recommendation not in ALLOWED:
        raise ValueError("unknown research adoption recommendation")
    if recommendation in {"ADOPT_AS_CHALLENGER","PROMOTION_REVIEW_REQUIRED"} and replay_status != "VERIFIED":
        return "BLOCKED_REPLAY_NOT_VERIFIED"
    return recommendation
