"""BAS-local All-22/C01 adapter. Not owner acceptance or Gridiron runtime."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

ADAPTER_VERSION = "BAS-C01-STAFF-SCHEME-ADAPTER-v33.1"
STAFF_SNAPSHOT_V1 = "StaffSnapshotV1"
LOSSLESS_ENVELOPE = "StaffRoleEpisodeV1Proposed"


class All22AdapterError(ValueError):
    """Raised when a payload cannot be transported without silent truncation."""


REQUIRED_EPISODE_FIELDS = (
    "person",
    "role",
    "source_title",
    "source_class",
    "valid_time_precision",
    "recorded_at_utc",
    "schema_version",
)


def compatibility_report(
    *, producer_version: str, consumer_version: str
) -> dict[str, Any]:
    lossless = (
        producer_version == LOSSLESS_ENVELOPE and consumer_version == LOSSLESS_ENVELOPE
    )
    return {
        "producer_version": producer_version,
        "consumer_version": consumer_version,
        "staff_snapshot_v1_is_not_lossless": STAFF_SNAPSHOT_V1 != producer_version,
        "transport": "LOSSLESS" if lossless else "REJECT_OR_LOSSY_PROJECTION",
        "c01_owner_adoption": "C01_OWNER_ADOPTION_PENDING",
        "gridiron_runtime_authorized": False,
    }


def encode_episode(row: Mapping[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_EPISODE_FIELDS if not row.get(field)]
    if missing:
        raise All22AdapterError(f"missing provenance/role/temporal fields: {missing}")
    if row.get("source_class") == "OPERATOR_CONTEMPORANEOUS_DECLARATION":
        raise All22AdapterError("operator declaration is not an appointment source")
    return {
        "envelope": LOSSLESS_ENVELOPE,
        "adapter_version": ADAPTER_VERSION,
        "person": row["person"],
        "role": row["role"],
        "qualifiers": list(row.get("qualifiers") or []),
        "source_title": row["source_title"],
        "source_class": row["source_class"],
        "valid_time_precision": row["valid_time_precision"],
        "recorded_at_utc": row["recorded_at_utc"],
        "schema_version": row["schema_version"],
        "scheme_is_not_film_inferred": True,
        "pit_admitted": False,
    }


def project_lossy_staff_snapshot_v1(
    episodes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "version": STAFF_SNAPSHOT_V1,
        "coach_ids": [str(row.get("person")) for row in episodes],
        "lossy_projection": True,
        "roles_schemes_tenure_dropped": True,
        "cannot_claim_lossless_transport": True,
    }
