from __future__ import annotations

"""Experiment artifact manifests, retention classes, and repository exclusion rules."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .lineage import file_sha256, content_id


ARTIFACT_CLASSES = frozenset({
    "CONFIG", "LOG", "METRIC_PACKET", "PREDICTION_PACKET", "MODEL_BINARY",
    "TRAINING_MATRIX", "PLOT", "REPORT", "REPLAY_PACKET", "CHECKPOINT",
})
REPO_ALLOWED_CLASSES = frozenset({"CONFIG", "METRIC_PACKET", "REPORT", "REPLAY_PACKET"})
SENSITIVITY = frozenset({"PUBLIC", "INTERNAL", "RESTRICTED", "SECRET_FORBIDDEN"})


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    experiment_id: str
    attempt: int
    class_name: str
    uri: str
    sha256: str
    size_bytes: int
    sensitivity: str
    repo_embeddable: bool

    def validate(self) -> None:
        if self.class_name not in ARTIFACT_CLASSES:
            raise ValueError(f"unknown artifact class {self.class_name}")
        if self.sensitivity not in SENSITIVITY:
            raise ValueError(f"unknown sensitivity {self.sensitivity}")
        if self.sensitivity in {"RESTRICTED", "SECRET_FORBIDDEN"} and self.repo_embeddable:
            raise ValueError("restricted/secret artifacts cannot be embedded in repository")
        if self.class_name not in REPO_ALLOWED_CLASSES and self.repo_embeddable:
            raise ValueError(f"{self.class_name} must stay outside cumulative repository")


def record_local_artifact(path: Path, *, experiment_id: str, attempt: int,
                          class_name: str, sensitivity: str = "INTERNAL",
                          repo_embeddable: bool = False) -> ArtifactRecord:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = {
        "experiment_id": experiment_id,
        "attempt": attempt,
        "class_name": class_name,
        "uri": path.as_posix(),
        "sha256": file_sha256(path),
        "size_bytes": path.stat().st_size,
        "sensitivity": sensitivity,
        "repo_embeddable": repo_embeddable,
    }
    record = ArtifactRecord(content_id("ART", payload), **payload)
    record.validate()
    return record


def validate_manifest(records: Iterable[ArtifactRecord]) -> list[str]:
    findings: list[str] = []
    seen: set[str] = set()
    for record in records:
        try:
            record.validate()
        except Exception as exc:
            findings.append(f"{record.artifact_id}:{exc}")
        if record.artifact_id in seen:
            findings.append(f"duplicate artifact_id:{record.artifact_id}")
        seen.add(record.artifact_id)
    return findings
