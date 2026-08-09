from __future__ import annotations

"""Tool-neutral local JSONL tracking adapter.

Useful when MLflow is unavailable.  This is intentionally simple and append-only;
it is not a replacement for canonical governance or the SQLite evidence store.
"""

from dataclasses import dataclass
from pathlib import Path
import json
import os
from typing import Any, Mapping

from .lineage import utc_now, canonical_json


@dataclass
class JsonlTracker:
    path: Path

    def log(self, event_type: str, payload: Mapping[str, Any]) -> None:
        if not event_type:
            raise ValueError("event_type required")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = {"event_type": event_type, "logged_at": utc_now(), "payload": payload}
        line = canonical_json(row) + "\n"
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        for lineno, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at line {lineno}") from exc
        return out
