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

# MR33-06 repair: identity, temporal and provenance fields the round-trip was
# silently dropping while `compatibility_report` still reported LOSSLESS.
# `valid_to` is intentionally excluded here (an open-ended interval is legal
# and represented by `None`), but every other field below is mandatory.
REQUIRED_IDENTITY_FIELDS = (
    "program_id",
    "person_id",
    "season",
    "valid_from",
    "receipt_sha256",
    "source_span",
)
OPTIONAL_PRESERVED_FIELDS = ("valid_to",)

# MR34-07 repair: these four semantic fields were supplied by callers and
# silently dropped while `verify_lossless_round_trip` still reported
# `lossless: true`. They are not decoration. `rights_state` governs whether a
# row may be shared at all, `conflict_state` says whether the assertion is
# disputed, `responsibility` distinguishes a title from what the person
# actually did, and `source_revision` is what makes the claim re-checkable.
# Losing any of them changes what the payload means to its consumer.
SEMANTIC_PRESERVED_FIELDS = (
    "conflict_state",
    "responsibility",
    "rights_state",
    "source_revision",
)


def compatibility_report(
    *, producer_version: str, consumer_version: str
) -> dict[str, Any]:
    """Version-string agreement alone. MR33-06 repair: this is now explicitly
    labeled as necessary but NOT sufficient to claim LOSSLESS -- callers must
    also pass an executable fixture through `verify_lossless_round_trip` to
    certify an actual transport, not just matching version identifiers."""

    lossless_versions = (
        producer_version == LOSSLESS_ENVELOPE and consumer_version == LOSSLESS_ENVELOPE
    )
    return {
        "producer_version": producer_version,
        "consumer_version": consumer_version,
        "staff_snapshot_v1_is_not_lossless": STAFF_SNAPSHOT_V1 != producer_version,
        "transport": "LOSSLESS_VERSIONS_MATCH" if lossless_versions else "REJECT_OR_LOSSY_PROJECTION",
        "matching_version_strings_do_not_prove_compatibility": True,
        "requires_executable_round_trip_fixture": "verify_lossless_round_trip",
        "c01_owner_adoption": "C01_OWNER_ADOPTION_PENDING",
        "gridiron_runtime_authorized": False,
    }


def verify_lossless_round_trip(row: Mapping[str, Any]) -> dict[str, Any]:
    """Actually encode `row` and confirm every mandatory identity/temporal/
    provenance field survives with an equal value -- the executable check
    `compatibility_report` cannot perform from version strings alone."""

    mandatory = tuple(REQUIRED_EPISODE_FIELDS) + tuple(REQUIRED_IDENTITY_FIELDS)
    try:
        encoded = encode_episode(row)
    except All22AdapterError as exc:
        return {
            "lossless": False,
            "reason": f"encode_rejected: {exc}",
            "missing_fields": [f for f in mandatory if not row.get(f)],
            "mismatched_fields": [],
        }
    missing_fields = [field for field in mandatory if field not in encoded]
    mismatched_fields = [
        field
        for field in mandatory
        if field in encoded and encoded.get(field) != row.get(field)
    ]
    optional_dropped = [
        field for field in OPTIONAL_PRESERVED_FIELDS if field not in encoded
    ]
    # MR34-07: a field the caller SUPPLIED and the envelope did not carry is
    # a loss, whether or not the envelope considers it mandatory.
    semantic_dropped = [
        field
        for field in SEMANTIC_PRESERVED_FIELDS
        if field in row and encoded.get(field) != row.get(field)
    ]
    retained_extensions = sorted(encoded.get("unmodelled_extension_fields") or {})
    lossless = (
        not missing_fields
        and not mismatched_fields
        and not optional_dropped
        and not semantic_dropped
    )
    return {
        "lossless": lossless,
        "missing_fields": missing_fields,
        "mismatched_fields": mismatched_fields,
        "optional_fields_dropped": optional_dropped,
        "semantic_fields_dropped": semantic_dropped,
        "retained_unmodelled_extension_fields": retained_extensions,
        "unknown_fields_are_retained_not_discarded": True,
        "envelope": LOSSLESS_ENVELOPE,
    }


def encode_episode(row: Mapping[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_EPISODE_FIELDS if not row.get(field)]
    missing += [field for field in REQUIRED_IDENTITY_FIELDS if not row.get(field)]
    if missing:
        raise All22AdapterError(f"missing provenance/role/temporal fields: {missing}")
    if row.get("source_class") == "OPERATOR_CONTEMPORANEOUS_DECLARATION":
        raise All22AdapterError("operator declaration is not an appointment source")
    encoded = {
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
        "program_id": row["program_id"],
        "person_id": row["person_id"],
        "season": row["season"],
        "valid_from": row["valid_from"],
        "receipt_sha256": row["receipt_sha256"],
        "source_span": row["source_span"],
        "scheme_is_not_film_inferred": True,
        "pit_admitted": False,
    }
    for field in OPTIONAL_PRESERVED_FIELDS:
        encoded[field] = row.get(field)
    for field in SEMANTIC_PRESERVED_FIELDS:
        encoded[field] = row.get(field)
    # Any field the caller supplied that this envelope does not model is
    # reported rather than discarded. Declaring LOSSLESS while quietly
    # dropping an unknown extension is the defect, not the unknown field.
    known = set(encoded) | set(REQUIRED_EPISODE_FIELDS) | set(REQUIRED_IDENTITY_FIELDS)
    unmodelled = sorted(key for key in row if key not in known)
    if unmodelled:
        encoded["unmodelled_extension_fields"] = {
            key: row[key] for key in unmodelled
        }
    return encoded


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
