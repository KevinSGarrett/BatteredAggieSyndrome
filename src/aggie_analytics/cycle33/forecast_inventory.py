"""Inventory frozen forecast artifacts. Absence is not proven by forecasts=[]."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
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


def _canonical_payload_digest(payload: Mapping[str, Any]) -> str:
    """The actual sha256 of this payload's own canonical bytes, EXCLUDING the
    `receipt_sha256` field itself (a hash cannot include itself). This is
    computed independently here every time -- never trusted from the file."""

    canonical = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _has_actual_forecast_content(payload: Mapping[str, Any]) -> bool:
    """A receipt/time/contest-id shell with no forecast value at all (e.g. no
    `probability_home`/`probabilities`/`forecast` field) is metadata, not a
    forecast packet -- it must never read ELIGIBLE regardless of how many
    envelope fields are present.

    MR34-02 repair: the Boolean rejection must come FIRST. `isinstance(True,
    int)` is True in Python, so `float(True) == 1.0` satisfies both the
    finiteness and the [0, 1] range test -- which is exactly how a packet
    whose `probability_home` was the Boolean `true` read ELIGIBLE. `True` is
    not a forecast of certainty; in a scientific payload it is a type error.
    """

    if "probability_home" in payload:
        value = payload.get("probability_home")
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            return False
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
    Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr\artifacts\forecast"),
    Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr\artifacts\pit"),
    Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr\artifacts\predictions"),
    Path(
        r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr"
        r"\artifacts\scientific_integrity"
    ),
)

# MR34-02 repair: manager-review directories are review workspaces, not
# forecast stores. Leaving them in SEARCH_ROOTS meant any JSON written there
# during a review became discoverable "forecast authority" -- which is how a
# synthetic probe packet entered the inventory in the first place. They stay
# named here so their exclusion is an explicit, auditable decision rather
# than a silently dropped line.
EXCLUDED_NON_AUTHORITY_ROOTS: tuple[Path, ...] = (
    Path(r"C:\BatteredAggieSyndrome.data\ops\manager_reviews"),
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


def _future_utc(value: Any, reference: datetime) -> bool:
    """True when a parseable timestamp is later than the reference instant."""

    if not isinstance(value, str) or not _ISO8601_RE.match(value.strip()):
        return False
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        return False
    return parsed.astimezone(timezone.utc) > reference


def inspect_forecast_eligibility(
    path: Path, *, as_of_utc: datetime | None = None
) -> dict[str, Any]:
    """Describe one candidate forecast artifact's STRUCTURAL well-formedness.

    MR34-02 repair, scope correction: an ELIGIBLE verdict here means the file
    is a structurally well-formed forecast packet whose declared timestamps
    are parseable and not in the future, and whose self-declared receipt hash
    actually matches its own canonical bytes. It does NOT mean the forecast
    was committed before any cutoff, by any trusted issuer, about any
    particular participants. A payload can hash itself; self-consistency is
    integrity, not authority. Scoring admission is decided exclusively by
    `aggie_analytics.cycle35.forecast_admission.admit`, which requires an
    allowlisted issuer and a commitment time at or before the contest cutoff.

    `as_of_utc` is injected (defaulting to the real clock) so a future-dated
    packet is rejected deterministically rather than depending on when the
    inventory happens to run.
    """

    reference = as_of_utc or datetime.now(timezone.utc)
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
        elif receipt_hash.strip().casefold() != _canonical_payload_digest(payload):
            # MR33-10 re-repair: a hex64-shaped string is not evidence on its
            # own -- an INVENTED hash (e.g. "a"*64) satisfying only the format
            # check, with no genuine relationship to the payload it claims to
            # describe, must not read ELIGIBLE. The receipt must equal the
            # ACTUAL, independently recomputed hash of this payload's own
            # canonical bytes -- self-referential integrity, not a copied or
            # fabricated string. A copied hash from an unrelated packet, or an
            # altered payload whose hash was never updated, is rejected here.
            failed.append("RECEIPT_SHA256_DOES_NOT_MATCH_PAYLOAD_BYTES")
        if not issued_at:
            failed.append("MISSING_ISSUED_OR_SNAPSHOT_UTC")
        elif not _looks_like_real_utc_timestamp(issued_at):
            failed.append("ISSUED_OR_SNAPSHOT_UTC_NOT_PARSEABLE")
        elif _future_utc(issued_at, reference):
            # MR34-02 repair: a 2099 issue date is not a forecast, it is a
            # timestamp defect or a fabrication. Either way it cannot be an
            # eligible packet.
            failed.append("ISSUED_OR_SNAPSHOT_UTC_IN_THE_FUTURE")
        if not known_at:
            failed.append("MISSING_KNOWN_AT_UTC")
        elif not _looks_like_real_utc_timestamp(known_at):
            failed.append("KNOWN_AT_UTC_NOT_PARSEABLE")
        elif _future_utc(known_at, reference):
            failed.append("KNOWN_AT_UTC_IN_THE_FUTURE")
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
        "eligibility_scope": "STRUCTURAL_WELL_FORMEDNESS_ONLY",
        "self_hash_is_not_issuer_authority": True,
        "self_hash_is_not_commitment_evidence": True,
        "admission_authority": "aggie_analytics.cycle35.forecast_admission.admit",
        "as_of_utc": reference.isoformat(),
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
        "excluded_non_authority_roots": [str(r) for r in EXCLUDED_NON_AUTHORITY_ROOTS],
        "eligibility_scope": "STRUCTURAL_WELL_FORMEDNESS_ONLY",
        "admission_authority": "aggie_analytics.cycle35.forecast_admission.admit",
        "none_eligible_in_inspected_set_is_not_global_absence": True,
        "empty_forecasts_arg_is_not_repository_absence": True,
        "no_retrospective_forecast_created": True,
        "frozen_boolean_alone_insufficient": True,
        "pit_admitted": False,
    }
