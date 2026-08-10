from __future__ import annotations

import re
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .ids import CanonicalEntityType, validate_canonical_id


_NAMESPACE = uuid.UUID("0b9087ea-43c1-5f46-a133-63cc34d403c4")
_PREFIX = {"player": CanonicalEntityType.PLAYER.value, "coach": CanonicalEntityType.COACH.value}
_SLOT = re.compile(r"^people-v1:(player|coach):([0-9]{8})$")


@dataclass(frozen=True)
class PeopleRegistryAssignment:
    identity_key: str
    assignment_slot: str
    canonical_id: str


def canonical_people_id_from_slot(entity_type: str, assignment_slot: str) -> str:
    match = _SLOT.fullmatch(assignment_slot)
    if not match or match.group(1) != entity_type or entity_type not in _PREFIX:
        raise ValueError(f"Invalid {entity_type!r} people assignment slot: {assignment_slot!r}")
    value = f"{_PREFIX[entity_type]}_{uuid.uuid5(_NAMESPACE, assignment_slot).hex}"
    if not validate_canonical_id(value):
        raise ValueError(f"Generated people ID violates the canonical format: {value}")
    return value


def assign_people_registry_slots(
    entity_type: str,
    identity_keys: Iterable[str],
    existing: Mapping[str, PeopleRegistryAssignment] | None = None,
) -> dict[str, PeopleRegistryAssignment]:
    """Assign opaque append-only slots; prior accepted assignments must be supplied on expansion."""

    if entity_type not in _PREFIX:
        raise ValueError(f"Unsupported people entity type: {entity_type}")
    prior = dict(existing or {})
    seen_slots: set[str] = set()
    max_ordinal = 0
    for key, assignment in prior.items():
        match = _SLOT.fullmatch(assignment.assignment_slot)
        if key != assignment.identity_key or not match or match.group(1) != entity_type:
            raise ValueError(f"Invalid existing people assignment: {assignment}")
        if assignment.assignment_slot in seen_slots:
            raise ValueError(f"Duplicate people assignment slot: {assignment.assignment_slot}")
        if assignment.canonical_id != canonical_people_id_from_slot(entity_type, assignment.assignment_slot):
            raise ValueError(f"Existing people assignment ID does not match its slot: {assignment}")
        seen_slots.add(assignment.assignment_slot)
        max_ordinal = max(max_ordinal, int(match.group(2)))
    result = dict(prior)
    for identity_key in sorted(set(identity_keys)):
        if not identity_key:
            raise ValueError("People registry identity keys must be non-empty")
        if identity_key in result:
            continue
        max_ordinal += 1
        slot = f"people-v1:{entity_type}:{max_ordinal:08d}"
        result[identity_key] = PeopleRegistryAssignment(
            identity_key=identity_key,
            assignment_slot=slot,
            canonical_id=canonical_people_id_from_slot(entity_type, slot),
        )
    return result
