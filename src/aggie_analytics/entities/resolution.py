from __future__ import annotations
from dataclasses import dataclass
import re, unicodedata
from .contracts import SourceEntityKey, ResolutionDecision

def normalize_name(value:str)->str:
    value=unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode('ascii').lower()
    return ' '.join(re.findall(r'[a-z0-9]+',value))

@dataclass(frozen=True)
class AliasRecord:
    entity_type:str; alias:str; canonical_id:str; source_system_id:str='*'

class EntityResolver:
    """Fail-closed exact/normalized alias starter. No probabilistic auto-linking."""
    def __init__(self, aliases):
        self._index={}
        for a in aliases:
            key=(a.source_system_id,a.entity_type,normalize_name(a.alias))
            self._index.setdefault(key,set()).add(a.canonical_id)
    def resolve(self, source_key:SourceEntityKey, display_name:str, decision_id:str)->ResolutionDecision:
        norm=normalize_name(display_name)
        candidates=set()
        for scope in (source_key.source_system_id,'*'):
            candidates |= self._index.get((scope,source_key.entity_type,norm),set())
        if len(candidates)==1:
            selected=next(iter(candidates)); state='RESOLVED'; method='NORMALIZED_ALIAS_EXACT'
        elif len(candidates)>1:
            selected=None; state='REVIEW_REQUIRED'; method='AMBIGUOUS_ALIAS'
        else:
            selected=None; state='UNRESOLVED'; method='NO_MATCH'
        return ResolutionDecision(decision_id,source_key,state,selected,method)


# The legacy resolver above is a pinned Jira source anchor. New registry
# assignment primitives remain below it so that the accepted anchor stays
# relocatable when this implementation grows.
import uuid
from collections.abc import Iterable, Mapping

from .ids import CanonicalEntityType, validate_canonical_id


_CORE_REGISTRY_NAMESPACE = uuid.UUID("a4cfb063-a2ab-5b3d-8a9b-39af49c66e36")
_CORE_ENTITY_PREFIXES = {
    "team": CanonicalEntityType.TEAM,
    "conference": CanonicalEntityType.CONFERENCE,
    "game": CanonicalEntityType.GAME,
    "venue": CanonicalEntityType.VENUE,
    "source_system": CanonicalEntityType.SOURCE_SYSTEM,
    "source_resource": CanonicalEntityType.SOURCE_RESOURCE,
}
_ASSIGNMENT_SLOT = re.compile(r"^core-v1:(team|conference|game|venue|source_system|source_resource):([0-9]{8})$")


@dataclass(frozen=True)
class RegistryAssignment:
    """One append-only internal assignment-ledger entry.

    ``identity_key`` is resolver evidence used to recover an existing slot.  It
    is never embedded in the opaque canonical identifier.  Accepted artifacts
    must be reused as the ledger when a later population adds identities.
    """

    identity_key: str
    assignment_slot: str
    canonical_id: str


def canonical_id_from_assignment_slot(entity_type: str, assignment_slot: str) -> str:
    """Derive an opaque canonical ID from an internal, source-free slot.

    The slot is an append-only registry ordinal, not a provider ID, name,
    season, or mutable attribute.  UUID5 supplies deterministic bytes for a
    pinned ledger while the public identifier retains the canonical prefix and
    opaque 32-hex representation required by the W07 contract.
    """

    match = _ASSIGNMENT_SLOT.fullmatch(assignment_slot)
    if not match or match.group(1) != entity_type or entity_type not in _CORE_ENTITY_PREFIXES:
        raise ValueError(f"Invalid {entity_type!r} assignment slot: {assignment_slot!r}")
    value = f"{_CORE_ENTITY_PREFIXES[entity_type].value}_{uuid.uuid5(_CORE_REGISTRY_NAMESPACE, assignment_slot).hex}"
    if not validate_canonical_id(value):
        raise ValueError(f"Generated canonical ID violates the W07 format: {value}")
    return value


def assign_registry_slots(
    entity_type: str,
    identity_keys: Iterable[str],
    existing: Mapping[str, RegistryAssignment] | None = None,
) -> dict[str, RegistryAssignment]:
    """Return stable assignments independent of input row order.

    Existing assignments are verified and retained.  New identities are sorted
    by their immutable resolver key and appended after the greatest accepted
    ordinal.  Callers must pass the prior accepted registry when expanding a
    population; this is what prevents insertions from renumbering old IDs.
    """

    if entity_type not in _CORE_ENTITY_PREFIXES:
        raise ValueError(f"Unsupported core entity type: {entity_type}")
    prior = dict(existing or {})
    seen_slots: set[str] = set()
    max_ordinal = 0
    for key, assignment in prior.items():
        if key != assignment.identity_key:
            raise ValueError(f"Existing assignment key mismatch for {key!r}")
        match = _ASSIGNMENT_SLOT.fullmatch(assignment.assignment_slot)
        if not match or match.group(1) != entity_type:
            raise ValueError(f"Existing assignment has invalid slot: {assignment}")
        if assignment.assignment_slot in seen_slots:
            raise ValueError(f"Duplicate assignment slot: {assignment.assignment_slot}")
        if assignment.canonical_id != canonical_id_from_assignment_slot(entity_type, assignment.assignment_slot):
            raise ValueError(f"Existing assignment ID does not match its internal slot: {assignment}")
        seen_slots.add(assignment.assignment_slot)
        max_ordinal = max(max_ordinal, int(match.group(2)))

    result = dict(prior)
    for identity_key in sorted(set(identity_keys)):
        if not identity_key:
            raise ValueError("Registry identity keys must be non-empty")
        if identity_key in result:
            continue
        max_ordinal += 1
        slot = f"core-v1:{entity_type}:{max_ordinal:08d}"
        result[identity_key] = RegistryAssignment(
            identity_key=identity_key,
            assignment_slot=slot,
            canonical_id=canonical_id_from_assignment_slot(entity_type, slot),
        )
    return result


def collapse_season_intervals(seasons: Iterable[int]) -> tuple[tuple[int, int], ...]:
    """Collapse observed seasons into inclusive-start/exclusive-end intervals."""

    ordered = sorted(set(int(season) for season in seasons))
    if not ordered:
        return ()
    intervals: list[tuple[int, int]] = []
    start = previous = ordered[0]
    for season in ordered[1:]:
        if season == previous + 1:
            previous = season
            continue
        intervals.append((start, previous + 1))
        start = previous = season
    intervals.append((start, previous + 1))
    return tuple(intervals)
