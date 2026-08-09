"""Canonical entity contract surface (Wave 07).

This is a contract-level starter, not the full W19 entity resolver.
"""
from .ids import CanonicalEntityType, new_canonical_id, validate_canonical_id
from .contracts import SourceEntityKey, ResolutionCandidate, ResolutionDecision

__all__ = [
    "CanonicalEntityType", "new_canonical_id", "validate_canonical_id",
    "SourceEntityKey", "ResolutionCandidate", "ResolutionDecision",
]
