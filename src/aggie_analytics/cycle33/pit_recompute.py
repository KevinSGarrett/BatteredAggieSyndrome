"""Independent PIT admission recompute. Producer labels are not proof.

A hardcoded zero and a desired positive count are both forbidden.
Forecast-freeze evidence is retrospective, not historical publication.
Week 1/2 2026 rows are not selection/calibration evidence.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle30.pit_kernel import (
    FREEZE_EVIDENCE_CLASSES,
    PROVEN,
    RETROSPECTIVE,
    SOURCE_UNPROVEN,
    PitKernelError,
    validate_row_authority,
)

REQUIRED_AUTHORITY = (
    "source_id",
    "effective_utc",
    "known_at_utc",
    "receipt_sha256",
    "classification",
    "evidence_class",
)


def authority_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    nested = row.get("authority") if isinstance(row.get("authority"), dict) else {}
    return {
        "source_id": row.get("source_id") or nested.get("source_id"),
        "effective_utc": row.get("effective_utc") or nested.get("effective_utc"),
        "known_at_utc": row.get("known_at_utc") or nested.get("known_at_utc"),
        "receipt_sha256": row.get("receipt_sha256") or nested.get("receipt_sha256"),
        "classification": row.get("classification") or nested.get("classification"),
        "evidence_class": row.get("evidence_class") or nested.get("evidence_class"),
        "source_publication_utc": row.get("source_publication_utc")
        or nested.get("source_publication_utc"),
        "suspended": row.get("suspended") or nested.get("suspended"),
        "future_publication": row.get("future_publication")
        or nested.get("future_publication"),
        "contemporaneous_fbs_authority": row.get("contemporaneous_fbs_authority")
        or nested.get("contemporaneous_fbs_authority"),
    }


def failed_predicates(row: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    authority = authority_from_row(row)
    missing = [field for field in REQUIRED_AUTHORITY if not authority.get(field)]
    if missing:
        reasons.append("MISSING_ROW_AUTHORITY:" + ",".join(missing))
    if int(row.get("season") or 0) in {2024, 2025}:
        reasons.append("EXPOSED_NON_BLIND_SEASON")
    if int(row.get("season") or 0) == 2026:
        reasons.append("CURRENT_SEASON_NOT_HISTORICAL_PIT_TRAINING")
    producer = str(row.get("authority_class") or row.get("row_verdict") or "")
    if producer == PROVEN and missing:
        reasons.append("PRODUCER_PROVEN_LABEL_WITHOUT_RECEIPT")
    evidence = str(authority.get("evidence_class") or "").upper()
    if evidence in FREEZE_EVIDENCE_CLASSES:
        reasons.append("FORECAST_FREEZE_IS_RETROSPECTIVE_NOT_PUBLICATION")
    return reasons


def independently_admit_row(
    row: Mapping[str, Any], *, target_cutoff: str | None = None
) -> dict[str, Any]:
    reasons = failed_predicates(row)
    cutoff = (
        target_cutoff
        or row.get("target_cutoff_utc")
        or row.get("known_at_utc")
        or row.get("start_date_utc_text")
        or "1970-01-01T00:00:00Z"
    )
    admitted = None
    try:
        admitted = validate_row_authority(
            authority_from_row(row), target_cutoff=str(cutoff)
        )
    except PitKernelError as exc:
        reasons.append(f"AUTHORITY_REJECTED:{exc}")
        admitted = SOURCE_UNPROVEN
    if admitted == PROVEN and reasons:
        admitted = SOURCE_UNPROVEN
    if admitted == PROVEN and not authority_from_row(row).get(
        "source_publication_utc"
    ):
        admitted = RETROSPECTIVE
        reasons.append("NO_SOURCE_PUBLICATION_UTC")
    return {
        "canonical_game_id": row.get("canonical_game_id"),
        "season": row.get("season"),
        "producer_authority_class": row.get("authority_class") or row.get("row_verdict"),
        "independent_class": admitted,
        "failed_predicates": reasons,
        "independently_proven": admitted == PROVEN and not reasons,
        "week1_week2_not_used_to_tune": True,
    }


def recompute_pit_population(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    results = [independently_admit_row(row) for row in rows]
    producer = Counter(
        str(row.get("authority_class") or row.get("row_verdict") or "UNDECLARED")
        for row in rows
    )
    independent = Counter(str(row.get("independent_class")) for row in results)
    proven = [row for row in results if row["independently_proven"]]
    failed = [row for row in results if not row["independently_proven"]]
    reason_counts: Counter[str] = Counter()
    for row in results:
        for reason in row["failed_predicates"] or ["NONE"]:
            reason_counts[reason.split(":")[0]] += 1
    return {
        "artifact_type": "CYCLE33_PIT_INDEPENDENT_RECOMPUTE",
        "row_count": len(rows),
        "producer_authority_class_counts": dict(producer),
        "independent_class_counts": dict(independent),
        "independently_proven_count": len(proven),
        "failed_predicate_rows": len(failed),
        "failed_predicate_reason_counts": dict(reason_counts),
        "hardcoded_zero_forbidden": True,
        "producer_label_is_not_independent_proof": True,
        "week1_week2_not_used_to_tune": True,
        "classification": "UNTRUSTED_SHADOW",
        "pit_admitted": False,
        "proven_rows": proven[:20],
        "failed_sample": failed[:20],
    }
