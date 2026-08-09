from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class EvidenceTier(str, Enum):
    OFFICIAL_CONFERENCE_REPORT="OFFICIAL_CONFERENCE_REPORT"
    OFFICIAL_TEAM_REPORT="OFFICIAL_TEAM_REPORT"
    OFFICIAL_GAME_NOTE_DEPTH="OFFICIAL_GAME_NOTE_DEPTH"
    CORROBORATED_REPUTABLE_REPORTING="CORROBORATED_REPUTABLE_REPORTING"
    SINGLE_SECONDARY_REPORT="SINGLE_SECONDARY_REPORT"
    SPECULATION_OR_UNVERIFIED="SPECULATION_OR_UNVERIFIED"
    UNKNOWN="UNKNOWN"

@dataclass(frozen=True)
class AvailabilityEvidence:
    evidence_id: str
    player_id: str
    first_known_at: datetime
    tier: EvidenceTier
    status: str
    policy_covered: bool
    report_version_id: str | None = None

def eligible_evidence(evidence: AvailabilityEvidence, cutoff: datetime) -> bool:
    return evidence.first_known_at <= cutoff

def noncoverage_state(*, policy_covered: bool, usable_evidence_present: bool) -> str:
    """Fail-safe availability classification.

    No report/noncoverage never becomes AVAILABLE merely by absence.
    """
    if not policy_covered or not usable_evidence_present:
        return "UNKNOWN"
    return "REVIEW_EVIDENCE"
