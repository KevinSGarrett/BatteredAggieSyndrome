"""Inventory frozen forecast artifacts. Absence is not proven by forecasts=[]."""

from __future__ import annotations

import json
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


def inspect_forecast_eligibility(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] | None = None
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = None
    keys = payload.keys() if isinstance(payload, dict) else ()
    freeze_present = False
    if isinstance(payload, dict):
        blob = json.dumps(payload).casefold()
        freeze_present = "frozen" in blob or "freeze" in blob
    proof = bool(
        isinstance(payload, dict)
        and payload.get("receipt_sha256")
        and (payload.get("issued_at_utc") or payload.get("snapshot_timestamp_utc"))
        and (payload.get("known_at_utc") or payload.get("known_at"))
    )
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "suffix": path.suffix,
        "eligibility_proof_present": proof,
        "frozen_boolean_alone_insufficient": True,
        "freeze_token_present": freeze_present,
        "top_level_keys": sorted(str(key) for key in keys)[:40],
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
            found.append(inspect_forecast_eligibility(path))
    proof_count = sum(1 for row in found if row.get("eligibility_proof_present"))
    return {
        "artifact_type": "CYCLE33_FORECAST_FILE_INVENTORY",
        "file_count": len(found),
        "eligibility_proof_count": proof_count,
        "files": found[:400],
        "truncated": len(found) > 400,
        "missing_roots": missing_roots,
        "empty_forecasts_arg_is_not_repository_absence": True,
        "no_retrospective_forecast_created": True,
        "frozen_boolean_alone_insufficient": True,
        "pit_admitted": False,
    }
