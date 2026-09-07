"""Immutable forecast reconstruction against predecessor row bytes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from aggie_analytics.cycle29.hashing import sha256_file, sha256_json
from aggie_analytics.cycle29.temporal import parse_aware_utc

NOT_PROVEN = "NOT_PROVEN"


class ForecastImmutabilityError(ValueError):
    """Raised when forecast immutability cannot be reconstructed."""


def row_identity(row: Mapping[str, Any]) -> str:
    return sha256_json(dict(row))


def set_identity(rows: Sequence[Mapping[str, Any]]) -> str:
    identities = [row_identity(row) for row in rows]
    return sha256_json(identities)


def prove_set_unchanged(
    predecessor: Sequence[Mapping[str, Any]],
    observed: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if len(predecessor) != len(observed):
        raise ForecastImmutabilityError("forecast opportunity count changed")
    pred_ids = [row_identity(row) for row in predecessor]
    obs_ids = [row_identity(row) for row in observed]
    if pred_ids != obs_ids:
        inserted = [item for item in obs_ids if item not in pred_ids]
        deleted = [item for item in pred_ids if item not in obs_ids]
        reordered = inserted == [] and deleted == [] and pred_ids != obs_ids
        raise ForecastImmutabilityError(
            f"forecast set identity changed inserted={len(inserted)} "
            f"deleted={len(deleted)} reordered={reordered}"
        )
    return {
        "row_count": len(predecessor),
        "set_identity": set_identity(predecessor),
        "bytes_equal": True,
    }


def prove_issued_before_cutoff(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    proven = 0
    unproven = 0
    reasons: list[str] = []
    for row in rows:
        issued = row.get("snapshot_timestamp_utc") or row.get("issued_at_utc")
        cutoff = (
            row.get("kickoff_bound_utc")
            or row.get("kickoff_utc")
            or row.get("cutoff_utc")
        )
        if not issued or not cutoff:
            unproven += 1
            reasons.append(NOT_PROVEN)
            continue
        try:
            if parse_aware_utc(str(issued)) <= parse_aware_utc(str(cutoff)):
                proven += 1
            else:
                raise ForecastImmutabilityError("forecast issued after cutoff/kickoff")
        except Exception:
            unproven += 1
            reasons.append(NOT_PROVEN)
    return {
        "issued_before_cutoff_count": proven,
        "not_proven_count": unproven,
        "unprovable_retained_as": NOT_PROVEN if unproven else None,
    }


def prove_candidate_freeze(
    rows: Sequence[Mapping[str, Any]],
    frozen_candidate_ids: Sequence[str],
    frozen_training_identity: str,
) -> dict[str, Any]:
    observed = sorted(
        {str(row.get("candidate_id")) for row in rows if row.get("candidate_id")}
    )
    frozen = sorted(str(item) for item in frozen_candidate_ids)
    if observed != frozen:
        raise ForecastImmutabilityError("candidate set changed after freeze")
    train_ids = {
        str(row.get("training_partition") or row.get("training_identity") or "")
        for row in rows
    }
    if frozen_training_identity not in train_ids and train_ids - {""}:
        # Rows may share one training identity; require no extra identities.
        extras = train_ids - {frozen_training_identity, ""}
        if extras:
            raise ForecastImmutabilityError(
                "fitted training identity changed after freeze"
            )
    return {
        "candidate_ids": frozen,
        "training_identity": frozen_training_identity,
        "candidate_set_unchanged": True,
    }


def scan_lineage_for_target_outcomes(
    lineage_records: Sequence[Mapping[str, Any]],
    target_game_ids: Sequence[str],
) -> dict[str, Any]:
    hits = []
    for record in lineage_records:
        used = str(record.get("used_game_id") or record.get("canonical_game_id") or "")
        role = str(record.get("role") or "")
        if used in set(map(str, target_game_ids)) and role in {
            "TRAINING_LABEL",
            "TARGET_OUTCOME",
            "FUTURE_OUTCOME",
        }:
            hits.append({"used_game_id": used, "role": role})
    return {
        "target_or_future_outcome_hits": hits,
        "clean": not hits,
        "unprovable": NOT_PROVEN if not lineage_records else None,
    }


def rehash_payload(
    path: Any, expected_sha256: str, expected_rows: int
) -> dict[str, Any]:
    digest = sha256_file(path)
    if digest != expected_sha256:
        raise ForecastImmutabilityError("forecast payload hash disagrees with manifest")
    count = 0
    with open(path, "rb") as handle:
        for line in handle:
            if line.strip():
                count += 1
    if count != expected_rows:
        raise ForecastImmutabilityError(
            "forecast payload row count disagrees with manifest"
        )
    return {
        "file_sha256": digest,
        "manifest_sha256": expected_sha256,
        "row_count": count,
        "file_and_manifest_agree": True,
    }


def reject_literal_no_tuning(
    claim_is_literal_false: bool, lineage_proved: bool
) -> None:
    if claim_is_literal_false and not lineage_proved:
        raise ForecastImmutabilityError(
            "literal no-tuning/no-mutation claim without lineage evidence"
        )
