from __future__ import annotations
from hashlib import sha256
import json
from typing import Any

TRANSITIONS={
 "PROPOSED":{"APPROVED":{"research_governor"},"REJECTED":{"research_governor"}},
 "APPROVED":{"QUEUED":{"scheduler","research_governor"},"REJECTED":{"research_governor"}},
 "QUEUED":{"RUNNING":{"experiment_worker"},"REJECTED":{"research_governor"}},
 "RUNNING":{"SUCCEEDED":{"experiment_worker"},"FAILED":{"experiment_worker"}},
 "SUCCEEDED":{"REPLAY_PENDING":{"research_governor"},"REJECTED":{"research_governor"}},
 "FAILED":{"REPLAY_PENDING":{"research_governor"},"ARCHIVED":{"research_governor"}},
 "REPLAY_PENDING":{"REPLAY_VERIFIED":{"replay_verifier"},"REJECTED":{"research_governor"}},
 "REPLAY_VERIFIED":{"ADOPTED_AS_CHALLENGER":{"research_governor"},"REJECTED":{"research_governor"}},
 "ADOPTED_AS_CHALLENGER":{"PROMOTION_REVIEW_REQUIRED":{"research_governor"},"ARCHIVED":{"research_governor"}},
 "PROMOTION_REVIEW_REQUIRED":{"ARCHIVED":{"research_governor"}},
 "REJECTED":{},"ARCHIVED":{},
}

def validate_transition(current: str, nxt: str, actor_role: str) -> None:
    if nxt == "PROMOTE" or current == "PROMOTE":
        raise ValueError("PROMOTE is not a research-queue state")
    allowed=TRANSITIONS.get(current)
    if allowed is None or nxt not in allowed:
        raise ValueError(f"invalid transition {current}->{nxt}")
    if actor_role not in allowed[nxt]:
        raise PermissionError(f"role {actor_role} cannot perform {current}->{nxt}")

def make_event(*,experiment_id:str,state:str,actor_role:str,reason:str,event_index:int,previous_event_hash:str="") -> dict[str,Any]:
    payload={"experiment_id":experiment_id,"state":state,"actor_role":actor_role,"reason":reason,"event_index":event_index,"previous_event_hash":previous_event_hash}
    payload["event_hash"]=sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return payload
