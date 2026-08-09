from __future__ import annotations
from enum import Enum
import re
import uuid

class CanonicalEntityType(str, Enum):
    TEAM="team"; INSTITUTION="inst"; CONFERENCE="conf"; GAME="game"
    VENUE="venue"; PLAYER="player"; COACH="coach"; OFFICIAL="official"
    SOURCE_SYSTEM="srcsys"; SOURCE_RESOURCE="srcres"; PUBLICATION_VERSION="pubver"
    RAW_CAPTURE="capture"; SOURCE_OBSERVATION="obs"; MAPPING_RECORD="map"
    RESOLUTION_DECISION="resdec"

_PATTERN = re.compile(r"^(team|inst|conf|game|venue|player|coach|official|srcsys|srcres|pubver|capture|obs|map|resdec)_[0-9a-f]{32}$")

def new_canonical_id(entity_type: CanonicalEntityType) -> str:
    """Return an opaque non-source-derived identifier.

    UUID4 is the current W07 Level-B representation default. Assigned IDs are
    treated as immutable; full persistence/materialization remains W19 work.
    """
    return f"{entity_type.value}_{uuid.uuid4().hex}"

def validate_canonical_id(value: str) -> bool:
    return bool(_PATTERN.fullmatch(value))
