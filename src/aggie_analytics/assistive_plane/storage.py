from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any

from .contracts import canonical_json_bytes


CLASSES = (
    "requests", "responses", "manifests", "evals", "quarantine", "usage", "runtime",
    "tmp", "worker_packets", "worker_results",
)


class ContentAddressedStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def initialize(self) -> None:
        for name in CLASSES:
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def put_json(self, storage_class: str, value: Any) -> tuple[Path, str, int]:
        if storage_class not in CLASSES:
            raise ValueError(f"unregistered assistive storage class: {storage_class}")
        payload = canonical_json_bytes(value) + b"\n"
        digest = hashlib.sha256(payload).hexdigest()
        directory = self.root / storage_class / "sha256" / digest[:2] / digest
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / "artifact.json"
        if not destination.exists():
            fd, temporary = tempfile.mkstemp(prefix=".write-", dir=directory)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, destination)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise RuntimeError("content-addressed artifact verification failed")
        return destination, digest, len(payload)

    def cleanup_tmp(self) -> dict[str, int]:
        removed_files = 0
        removed_bytes = 0
        for path in sorted((self.root / "tmp").rglob("*"), reverse=True):
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
