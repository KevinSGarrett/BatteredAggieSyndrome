from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable

@dataclass(frozen=True)
class ArtifactRecord:
    logical_name: str
    sha256: str
    size_bytes: int
    artifact_class: str
    location: str
    sensitivity: str = "NORMAL"

def record_local_file(path: Path, *, logical_name: str | None = None,
                      artifact_class: str = "small_json_csv_report",
                      location: str | None = None,
                      sensitivity: str = "NORMAL") -> ArtifactRecord:
    data = path.read_bytes()
    return ArtifactRecord(
        logical_name=logical_name or path.name,
        sha256=sha256(data).hexdigest(),
        size_bytes=len(data),
        artifact_class=artifact_class,
        location=location or str(path),
        sensitivity=sensitivity,
    )

def manifest_digest(records: Iterable[ArtifactRecord]) -> str:
    payload = "\n".join(
        f"{r.logical_name}|{r.sha256}|{r.size_bytes}|{r.artifact_class}|{r.location}|{r.sensitivity}"
        for r in sorted(records, key=lambda x: x.logical_name)
    )
    return sha256(payload.encode("utf-8")).hexdigest()
