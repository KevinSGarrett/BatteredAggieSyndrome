from __future__ import annotations

"""Simple process-safe local lock records for research worktrees/shared contracts."""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import json
import os
import time
from typing import Iterator

from .lineage import utc_now


@dataclass(frozen=True)
class LockRecord:
    lock_name: str
    owner: str
    pid: int
    acquired_at: str
    purpose: str


class FileLock:
    def __init__(self, path: Path, *, owner: str, purpose: str):
        self.path = Path(path)
        self.owner = owner
        self.purpose = purpose
        self._fd: int | None = None

    def acquire(self) -> LockRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            fd = os.open(self.path, flags, 0o600)
        except FileExistsError:
            raise RuntimeError(f"lock already held: {self.path}")
        self._fd = fd
        rec = LockRecord(self.path.name, self.owner, os.getpid(), utc_now(), self.purpose)
        os.write(fd, json.dumps(rec.__dict__, sort_keys=True).encode("utf-8"))
        os.fsync(fd)
        return rec

    def release(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def read_existing(self) -> dict | None:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
