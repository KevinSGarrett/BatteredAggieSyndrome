from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArchitectureRegistry:
    raw: dict[str, Any]

    @property
    def version(self) -> str:
        return str(self.raw["architecture_version"])

    @property
    def component_ids(self) -> tuple[str, ...]:
        return tuple(str(item["id"]) for item in self.raw["components"])


def load_architecture_registry(path: Path) -> ArchitectureRegistry:
    """Load the machine-readable W03 architecture registry."""
    return ArchitectureRegistry(json.loads(path.read_text(encoding="utf-8")))
