"""Inventory frozen forecast artifacts. Absence is not proven by forecasts=[]."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

SEARCH_ROOTS: tuple[Path, ...] = (
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle33"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle32"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle31"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\forecasts"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle29"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle28"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle27"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle26"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\manager_reviews"),
    Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr\artifacts\forecast"),
    Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr\artifacts\pit"),
    Path(
        r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr\artifacts\predictions"
    ),
    Path(
        r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr"
        r"\artifacts\scientific_integrity"
    ),
)

NAME_HINTS = ("frozen", "forecast", "checkpoint", "t24h", "t90m", "shadow")
SKIP_NAME_TOKENS = ("forecast_file_inventory", "unfinished_items")


def _looks_relevant(path: Path) -> bool:
    name = path.name.casefold()
    if any(token in name for token in SKIP_NAME_TOKENS):
        return False
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
    failed: list[str] = []
    freeze_present = False
    if path.suffix.lower() != ".json":
        failed.append("NOT_JSON_FORECAST_PACKET")
    if payload is None and path.suffix.lower() == ".json":
        failed.append("JSON_UNREADABLE")
    if isinstance(payload, dict):
        blob = json.dumps(payload).casefold()
        freeze_present = "frozen" in blob or "freeze" in blob
        if payload.get("frozen") is True or payload.get("freeze_present") is True:
            if not payload.get("receipt_sha256"):
                failed.append("FROZEN_BOOLEAN_WITHOUT_RECEIPT_SHA256")
        if not payload.get("receipt_sha256"):
            failed.append("MISSING_RECEIPT_SHA256")
        if not (payload.get("issued_at_utc") or payload.get("snapshot_timestamp_utc")):
            failed.append("MISSING_ISSUED_OR_SNAPSHOT_UTC")
        if not (payload.get("known_at_utc") or payload.get("known_at")):
            failed.append("MISSING_KNOWN_AT_UTC")
        if not payload.get("contest_id") and not payload.get("canonical_contest_id"):
            failed.append("MISSING_CANONICAL_CONTEST_ID")
        if freeze_present and not (
            payload.get("receipt_sha256")
            and (payload.get("issued_at_utc") or payload.get("snapshot_timestamp_utc"))
            and (payload.get("known_at_utc") or payload.get("known_at"))
        ):
            failed.append("FREEZE_TOKEN_WITHOUT_ELIGIBILITY_PROOF")
    else:
        failed.append("PAYLOAD_NOT_OBJECT")
    unique_failed = list(dict.fromkeys(failed))
    proof = not unique_failed and bool(payload)
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "suffix": path.suffix,
        "eligibility_verdict": "ELIGIBLE" if proof else "INELIGIBLE",
        "failed_predicates": unique_failed,
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
            found[-1]["searched_root"] = str(root)
    proof_count = sum(1 for row in found if row.get("eligibility_proof_present"))
    existing_roots = [str(root) for root in (roots or SEARCH_ROOTS) if root.exists()]
    return {
        "artifact_type": "CYCLE33_FORECAST_FILE_INVENTORY",
        "file_count": len(found),
        "eligibility_proof_count": proof_count,
        "files": found[:400],
        "truncated": len(found) > 400,
        "missing_roots": missing_roots,
        "roots_searched": existing_roots,
        "inspected_set_scope": "AUTHORIZED_EXISTING_ARCHIVES_AND_PREDECESSOR_OUTPUTS",
        "none_eligible_in_inspected_set_is_not_global_absence": True,
        "empty_forecasts_arg_is_not_repository_absence": True,
        "no_retrospective_forecast_created": True,
        "frozen_boolean_alone_insufficient": True,
        "pit_admitted": False,
    }
