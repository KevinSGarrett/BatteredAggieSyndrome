"""Inventory frozen forecast artifacts. Absence is not proven by forecasts=[]."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

SEARCH_ROOTS: tuple[Path, ...] = (
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle33"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle32"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work"),
    Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr\artifacts\forecast"),
    Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr\artifacts\pit"),
)

NAME_HINTS = ("frozen", "forecast", "checkpoint", "t24h", "t90m", "shadow")


def _looks_relevant(path: Path) -> bool:
    name = path.name.casefold()
    return any(hint in name for hint in NAME_HINTS) and path.suffix.lower() in {
        ".json",
        ".jsonl",
        ".csv",
        ".parquet",
    }


def inventory_forecast_files(roots: Sequence[Path] | None = None) -> dict[str, Any]:
    found: list[dict[str, Any]] = []
    missing_roots: list[str] = []
    for root in roots or SEARCH_ROOTS:
        if not root.exists():
            missing_roots.append(str(root))
            continue
        for path in root.rglob("*"):
            if not path.is_file() or not _looks_relevant(path):
                continue
            found.append(
                {
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "suffix": path.suffix,
                    "eligibility_proof_present": False,
                    "frozen_boolean_alone_insufficient": True,
                }
            )
    return {
        "artifact_type": "CYCLE33_FORECAST_FILE_INVENTORY",
        "file_count": len(found),
        "files": found[:400],
        "truncated": len(found) > 400,
        "missing_roots": missing_roots,
        "empty_forecasts_arg_is_not_repository_absence": True,
        "no_retrospective_forecast_created": True,
        "pit_admitted": False,
    }
