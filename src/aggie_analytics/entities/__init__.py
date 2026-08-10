"""Canonical entity and conservative resolution contract surface."""

from .candidates import FuzzyAliasCandidateGenerator
from .contracts import ResolutionCandidate, ResolutionDecision, SourceEntityKey
from .ids import CanonicalEntityType, new_canonical_id, validate_canonical_id
from .resolution import AliasRecord, EntityResolver, normalize_name

__all__ = [
    "AliasRecord",
    "CanonicalEntityType",
    "EntityResolver",
    "FuzzyAliasCandidateGenerator",
    "ResolutionCandidate",
    "ResolutionDecision",
    "SourceEntityKey",
    "new_canonical_id",
    "normalize_name",
    "validate_canonical_id",
]
