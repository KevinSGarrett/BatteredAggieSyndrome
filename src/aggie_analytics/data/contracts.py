from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    dataset: str
    row_number: int
    payload: dict[str, Any]

@dataclass(frozen=True)
class RawSnapshot:
    snapshot_id: str
    source_id: str
    dataset: str
    retrieved_at: datetime
    raw_sha256: str
    relative_path: str
    row_count: int
    schema_fields: tuple[str,...]
    source_uri: str
    publication_time: datetime|None = None
    metadata: dict[str,Any] = field(default_factory=dict)

@dataclass(frozen=True)
class SnapshotManifest:
    version: str
    snapshots: tuple[RawSnapshot,...]
