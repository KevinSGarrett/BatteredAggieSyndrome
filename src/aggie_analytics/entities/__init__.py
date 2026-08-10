"""Canonical entity and conservative resolution contract surface."""

from .candidates import FuzzyAliasCandidateGenerator
from .contracts import ResolutionCandidate, ResolutionDecision, SourceEntityKey
from .ids import CanonicalEntityType, new_canonical_id, validate_canonical_id
from .people_registry import (
    PeopleRegistryAssignment,
    assign_people_registry_slots,
    canonical_people_id_from_slot,
)
from .registry_artifacts import CoreRegistryArtifactManifest, PeopleRegistryArtifactManifest, RegistryArtifactError
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
    "PeopleRegistryArtifactManifest",
    "PeopleRegistryAssignment",
    "ResolutionCandidate",
    "ResolutionDecision",
    "SourceEntityKey",
    "assign_registry_slots",
    "assign_people_registry_slots",
    "canonical_people_id_from_slot",
    "canonical_id_from_assignment_slot",
    "collapse_season_intervals",
    "new_canonical_id",
    "normalize_name",
    "validate_canonical_id",
]
