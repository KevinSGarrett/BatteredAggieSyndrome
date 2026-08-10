"""Canonical entity and conservative resolution contract surface."""

from .candidates import FuzzyAliasCandidateGenerator
from .contracts import ResolutionCandidate, ResolutionDecision, SourceEntityKey
from .ids import CanonicalEntityType, new_canonical_id, validate_canonical_id
from .registry_artifacts import CoreRegistryArtifactManifest, RegistryArtifactError
from .resolution import (
    AliasRecord,
    EntityResolver,
    RegistryAssignment,
    assign_registry_slots,
    canonical_id_from_assignment_slot,
    collapse_season_intervals,
    normalize_name,
)

__all__ = [
    "AliasRecord",
    "CanonicalEntityType",
    "CoreRegistryArtifactManifest",
    "EntityResolver",
    "FuzzyAliasCandidateGenerator",
    "RegistryArtifactError",
    "RegistryAssignment",
    "ResolutionCandidate",
    "ResolutionDecision",
    "SourceEntityKey",
    "assign_registry_slots",
    "canonical_id_from_assignment_slot",
    "collapse_season_intervals",
    "new_canonical_id",
    "normalize_name",
    "validate_canonical_id",
]
