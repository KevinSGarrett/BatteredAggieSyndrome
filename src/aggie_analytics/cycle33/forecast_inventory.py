"""Inventory frozen forecast artifacts. Absence is not proven by forecasts=[]."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ISO8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


def _looks_like_real_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.match(value.strip().casefold()))


def _looks_like_real_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not _ISO8601_RE.match(value.strip()):
        return False
    try:
        datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _has_actual_forecast_content(payload: Mapping[str, Any]) -> bool:
    """A receipt/time/contest-id shell with no forecast value at all (e.g. no
    `probability_home`/`probabilities`/`forecast` field) is metadata, not a
    forecast packet -- it must never read ELIGIBLE regardless of how many
    envelope fields are present."""

    if "probability_home" in payload:
        value = payload.get("probability_home")
        try:
            number = float(value)
        except (TypeError, ValueError):
            return False
        return math.isfinite(number) and 0.0 <= number <= 1.0
    for key in ("probabilities", "forecast", "forecast_rows"):
        value = payload.get(key)
        if isinstance(value, (list, dict)) and value:
            return True
    return False

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
    Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr\artifacts\predictions"),
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
        receipt_hash = payload.get("receipt_sha256")
        issued_at = payload.get("issued_at_utc") or payload.get("snapshot_timestamp_utc")
        known_at = payload.get("known_at_utc") or payload.get("known_at")
        if payload.get("frozen") is True or payload.get("freeze_present") is True:
            if not receipt_hash:
                failed.append("FROZEN_BOOLEAN_WITHOUT_RECEIPT_SHA256")
        if not receipt_hash:
            failed.append("MISSING_RECEIPT_SHA256")
        elif not _looks_like_real_sha256(receipt_hash):
            # MR33-10 repair: a forged/placeholder value (e.g. "fake") must not
            # satisfy "receipt present" just because the field is nonempty.
            failed.append("RECEIPT_SHA256_NOT_WELL_FORMED")
        if not issued_at:
            failed.append("MISSING_ISSUED_OR_SNAPSHOT_UTC")
        elif not _looks_like_real_utc_timestamp(issued_at):
            failed.append("ISSUED_OR_SNAPSHOT_UTC_NOT_PARSEABLE")
        if not known_at:
            failed.append("MISSING_KNOWN_AT_UTC")
        elif not _looks_like_real_utc_timestamp(known_at):
            failed.append("KNOWN_AT_UTC_NOT_PARSEABLE")
        if not payload.get("contest_id") and not payload.get("canonical_contest_id"):
            failed.append("MISSING_CANONICAL_CONTEST_ID")
        if freeze_present and not (
            receipt_hash
            and _looks_like_real_sha256(receipt_hash)
            and issued_at
            and _looks_like_real_utc_timestamp(issued_at)
            and known_at
            and _looks_like_real_utc_timestamp(known_at)
        ):
            failed.append("FREEZE_TOKEN_WITHOUT_ELIGIBILITY_PROOF")
        if not _has_actual_forecast_content(payload):
            # MR33-10 repair: an envelope with only receipt/time/contest-id
            # metadata and no actual forecast value is not a forecast packet.
            failed.append("MISSING_ACTUAL_FORECAST_CONTENT")
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
