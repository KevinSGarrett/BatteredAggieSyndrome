from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass(frozen=True)
class SourceEntityKey:
    source_system_id: str
    entity_type: str
    source_entity_key: str

@dataclass(frozen=True)
class ResolutionCandidate:
    source_key: SourceEntityKey
    candidate_canonical_id: str
    mapping_method: str
    evidence_capture_ids: Tuple[str, ...] = ()
    diagnostic_score: Optional[float] = None

@dataclass(frozen=True)
class ResolutionDecision:
    resolution_decision_id: str
    source_key: SourceEntityKey
    decision_state: str
    selected_canonical_id: Optional[str]
    mapping_method: str
    evidence_capture_ids: Tuple[str, ...] = ()
    supersedes_decision_id: Optional[str] = None
