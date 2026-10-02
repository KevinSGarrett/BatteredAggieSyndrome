"""Independent PIT predicates. Must not import producer scientific helpers."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

SHA256_HEX = re.compile(r"^[0-9a-fA-F]{64}$")
REQUIRED = (
    "source_id",
    "effective_utc",
    "known_at_utc",
    "receipt_sha256",
    "classification",
    "evidence_class",
)
FREEZE = frozenset({"FORECAST_FREEZE_RECEIPT"})
UNPROVEN = frozenset(
    {
        "UNPROVEN",
        "SOURCE_AUTHORITY_UNPROVEN",
        "FLAG_ONLY",
        "CONSERVATIVE_BOUND_NOT_PUBLICATION",
    }
)


def _instant(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _temporal_failures(field: Any, cutoff_value: Any, now: datetime | None = None) -> list[str]:
    """R37-08: a publication instant must precede the cutoff it is used for.

    Presence was all this checked, so a well-formed authority whose
    publication lay in 2099 counted as proof for a 2013 contest. Every
    instant must be timezone-aware and not in the future; publication must
    come no later than known-at and strictly before the row's own cutoff,
    and effective must not follow the cutoff. A row that states no cutoff
    cannot show anything was known in time.
    """

    reasons: list[str] = []
    now = now or datetime.now(timezone.utc)
    cutoff = _instant(cutoff_value)
    if cutoff is None:
        reasons.append("NO_TARGET_CUTOFF")
    published = _instant(field("source_publication_utc"))
    known_at = _instant(field("known_at_utc"))
    effective = _instant(field("effective_utc"))
    for name, raw, parsed in (("PUBLICATION", field("source_publication_utc"), published),
                              ("KNOWN_AT", field("known_at_utc"), known_at),
                              ("EFFECTIVE", field("effective_utc"), effective)):
        if raw and parsed is None:
            reasons.append(f"{name}_NOT_AN_AWARE_INSTANT")
        elif parsed is not None and parsed > now:
            reasons.append(f"{name}_IN_THE_FUTURE")
    if published is not None and known_at is not None and known_at < published:
        reasons.append("KNOWN_AT_PRECEDES_PUBLICATION")
    if cutoff is not None:
        if published is not None and published >= cutoff:
            reasons.append("PUBLICATION_NOT_BEFORE_CUTOFF")
        if effective is not None and effective > cutoff:
            reasons.append("EFFECTIVE_AFTER_CUTOFF")
    return reasons


def independent_row_class(row: Mapping[str, Any]) -> dict[str, Any]:
    nested = row.get("authority") if isinstance(row.get("authority"), dict) else {}

    def field(name: str) -> Any:
        return row.get(name) or nested.get(name)

    missing = [name for name in REQUIRED if not field(name)]
    reasons: list[str] = []
    if missing:
        reasons.append("MISSING_ROW_AUTHORITY")
    receipt = str(field("receipt_sha256") or "")
    if receipt and not SHA256_HEX.fullmatch(receipt):
        reasons.append("RECEIPT_NOT_SHA256")
    if str(field("evidence_class") or "").upper() in FREEZE:
        reasons.append("FORECAST_FREEZE_IS_RETROSPECTIVE")
    if str(field("classification") or "").upper() in UNPROVEN:
        reasons.append("UNPROVEN_CLASSIFICATION")
    if not field("source_publication_utc"):
        reasons.append("NO_SOURCE_PUBLICATION_UTC")
    reasons.extend(_temporal_failures(field, row.get("target_cutoff_utc") or row.get("cutoff_utc")))
    season = int(row.get("season") or 0)
    if season in {2024, 2025}:
        reasons.append("EXPOSED_NON_BLIND_SEASON")
    if season == 2026:
        reasons.append("CURRENT_SEASON_NOT_HISTORICAL_PIT_TRAINING")
    producer = str(row.get("authority_class") or row.get("row_verdict") or "")
    if producer == "PROVEN_PIT_TRAINING_ROW" and missing:
        reasons.append("PRODUCER_PROVEN_LABEL_WITHOUT_RECEIPT")
    proven = not reasons
    return {
        "canonical_game_id": row.get("canonical_game_id"),
        "season": season or row.get("season"),
        "producer_authority_class": producer,
        "independently_proven": proven,
        "failed_predicates": reasons,
    }


def reconstruct_pit(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    results = [independent_row_class(row) for row in rows]
    proven = sum(1 for row in results if row["independently_proven"])
    reasons: Counter[str] = Counter()
    for row in results:
        for reason in row["failed_predicates"] or ["NONE"]:
            reasons[reason] += 1
    return {
        "artifact_type": "CYCLE33_INDEPENDENT_PIT_RECONSTRUCTION",
        "row_count": len(rows),
        "independently_proven_count": proven,
        "failed_predicate_reason_counts": dict(reasons),
        "producer_helpers_imported": False,
        "hardcoded_count_forbidden": True,
        "week1_week2_not_used_to_tune": True,
    }
