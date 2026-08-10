from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import canonical_json_bytes


@dataclass(frozen=True)
class StoredArtifact:
    path: Path
    sha256: str
    bytes: int


class ExternalStore:
    def __init__(self, root: Path, subdirectories: list[str]) -> None:
        self.root = root.resolve()
        self.subdirectories = tuple(subdirectories)

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for name in self.subdirectories:
            if not name or Path(name).name != name:
                raise ValueError(f"invalid external storage subdirectory: {name!r}")
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def directory(self, name: str) -> Path:
        if name not in self.subdirectories:
            raise ValueError(f"unregistered OpenAI storage class: {name}")
        return self.root / name

    def put_json(self, storage_class: str, value: Any, *, suffix: str = ".json") -> StoredArtifact:
        return self.put_bytes(storage_class, canonical_json_bytes(value) + b"\n", suffix=suffix)

    def put_bytes(self, storage_class: str, payload: bytes, *, suffix: str) -> StoredArtifact:
        digest = hashlib.sha256(payload).hexdigest()
        directory = self.directory(storage_class) / "sha256" / digest[:2] / digest
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"artifact{suffix}"
        if destination.exists():
            current = destination.read_bytes()
            if hashlib.sha256(current).hexdigest() != digest:
                raise RuntimeError("content-address collision or corrupt existing artifact")
        else:
            fd, raw_tmp = tempfile.mkstemp(prefix=".write-", dir=directory)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(raw_tmp, destination)
            finally:
                if os.path.exists(raw_tmp):
                    os.unlink(raw_tmp)
        if destination.stat().st_size != len(payload):
            raise RuntimeError("stored artifact byte count mismatch")
        return StoredArtifact(destination, digest, len(payload))

    def cleanup_tmp(self) -> dict[str, int]:
        directory = self.directory("tmp")
        removed_files = 0
        removed_bytes = 0
        for path in sorted(directory.rglob("*"), reverse=True):
            if path.is_file():
                removed_bytes += path.stat().st_size
                path.unlink()
                removed_files += 1
            elif path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass
        return {"removed_files": removed_files, "removed_bytes": removed_bytes}
