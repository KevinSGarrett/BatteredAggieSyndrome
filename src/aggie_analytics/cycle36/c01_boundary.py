"""BAS-local staff assertion envelope and its lossy C01 projection.

TP36-09: the released ``StaffSnapshotV1`` value is ``{team_id, coach_ids}``.
That shape cannot express a per-person role episode -- it has no person-level
role, no unit or position scope, no qualifier, no effective interval, no
source locator, no conflicting claim and no rights statement. Exporting BAS
staff evidence through it is therefore a **lossy projection**, and the losses
have to be enumerated rather than discovered later by a consumer.

Three rules hold here:

1. The BAS-local envelope is the lossless record. It keeps every field the
   accepted staff plan names, including the ones C01 v0.1.2 has nowhere to
   put.
2. The projection **declares what it drops**. ``project_to_staff_snapshot``
   returns the C01 value beside a field-level matrix of represented, lost and
   pending fields, and a consumer that needs a lost field must refuse the
   projection rather than read around it.
3. A richer local envelope is a **proposal**, never an adopted shared
   contract. Nothing here claims C01 released these fields, and nothing here
   writes to an owner repository.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

#: Bumped for R37-13-AC04. v36.1 projected mixed cutoffs, assertions with no
#: known_at, known_at later than the cutoff, assertions with no evidence and
#: offset-form timestamps the released schema rejects, and its membership
#: consumer admitted an empty mapping. The predecessor is named so a document
#: produced under the weaker rule is never mistaken for one produced here.
BOUNDARY_VERSION = "BAS-C01-STAFF-BOUNDARY-v37.1"
PREDECESSOR_BOUNDARY_VERSION = "BAS-C01-STAFF-BOUNDARY-v36.1"

#: The released schema's identifier and timestamp patterns, copied from
#: StaffSnapshotV1 0.1.2 so the adapter can refuse what the owner schema
#: would reject, and say why, before a consumer sees it.
C01_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]+$")
C01_UTC_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
C01_UNKNOWN_REASONS = frozenset(
    {"UNKNOWN", "NOT_VISIBLE", "AMBIGUOUS", "OUT_OF_DOMAIN",
     "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE"}
)
C01_CONTRACT = "context/StaffSnapshotV1"
C01_SCHEMA_VERSION = "0.1.2"

REPRESENTED = "REPRESENTED_IN_RELEASED_C01_SCHEMA"
LOST = "LOST_BY_PROJECTION_NO_RELEASED_FIELD"
PENDING = "PENDING_OWNER_PROPOSAL"


@dataclass(frozen=True)
class RoleScope:
    """One formal role plus the unit or position it applies to."""

    role_code: str
    unit: str
    qualifiers: tuple[str, ...] = ()
    occupancy: str = "OBSERVED"

    def as_dict(self) -> dict[str, Any]:
        return {
            "role_code": self.role_code,
            "unit": self.unit,
            "qualifiers": list(self.qualifiers),
            "occupancy": self.occupancy,
        }


@dataclass
class StaffAssertion:
    """One person-program-role-interval claim with its evidence and rights.

    Every field below exists because an accepted owner plan or a BAS finding
    names it. ``source_effective_*`` is what the source says the assertion
    covers; ``known_at_utc`` is when the bytes demonstrably existed. Keeping
    them apart is TP36-02's requirement and is exactly what a single
    ``coach_ids`` list destroys.
    """

    assertion_id: str
    person_id: str
    person_display_name: str
    program_id: str
    season: int | None
    roles: tuple[RoleScope, ...]
    source_title: str
    source_system: str
    evidence_refs: tuple[str, ...]
    source_locator: str | None = None
    source_effective_start: str | None = None
    source_effective_end: str | None = None
    known_at_utc: str | None = None
    point_in_time_cutoff: str | None = None
    evidence_tier: str = "CANDIDATE"
    conflicts_with: tuple[str, ...] = ()
    rights: str = "SOURCE_TERMS_APPLY_NOT_REDISTRIBUTABLE"
    unknown_reason: str | None = None
    pit_admitted: bool = False
    play_calling_stated: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "boundary_version": BOUNDARY_VERSION,
            "assertion_id": self.assertion_id,
            "person_id": self.person_id,
            "person_display_name": self.person_display_name,
            "program_id": self.program_id,
            "season": self.season,
            "roles": [role.as_dict() for role in self.roles],
            "source_title": self.source_title,
            "source_system": self.source_system,
            "evidence_refs": list(self.evidence_refs),
            "source_locator": self.source_locator,
            "source_effective_start": self.source_effective_start,
            "source_effective_end": self.source_effective_end,
            "known_at_utc": self.known_at_utc,
            "point_in_time_cutoff": self.point_in_time_cutoff,
            "evidence_tier": self.evidence_tier,
            "conflicts_with": list(self.conflicts_with),
            "rights": self.rights,
            "unknown_reason": self.unknown_reason,
            "pit_admitted": self.pit_admitted,
            "play_calling_stated": self.play_calling_stated,
        }


#: What the released schema can and cannot carry, field by field. The
#: ``REPRESENTED`` rows are the only ones a C01 consumer may rely on.
FIELD_MATRIX: dict[str, dict[str, str]] = {
    "program_id": {
        "state": REPRESENTED,
        "c01_path": "value.team_id",
        "note": "Carried as the team identifier.",
    },
    "person_id": {
        "state": REPRESENTED,
        "c01_path": "value.coach_ids[]",
        "note": "Carried only as a membership list; the list says nothing about what each person does.",
    },
    "known_at_utc": {
        "state": REPRESENTED,
        "c01_path": "known_at",
        "note": "Envelope field with a UTC pattern.",
    },
    "point_in_time_cutoff": {
        "state": REPRESENTED,
        "c01_path": "point_in_time_cutoff",
        "note": "Envelope field; a BAS assertion with no cutoff cannot be projected.",
    },
    "source_system": {
        "state": REPRESENTED,
        "c01_path": "provenance.source_system",
        "note": "Envelope provenance.",
    },
    "evidence_refs": {
        "state": REPRESENTED,
        "c01_path": "provenance.evidence_refs[]",
        "note": "Envelope provenance; at least one reference is required.",
    },
    "unknown_reason": {
        "state": REPRESENTED,
        "c01_path": "unknown_reason",
        "note": "Enumerated; a BAS reason outside the enum cannot be projected.",
    },
    "roles": {
        "state": LOST,
        "c01_path": None,
        "note": "No per-person role field exists. A head coach and a strength assistant project identically.",
    },
    "roles[].unit": {
        "state": LOST,
        "c01_path": None,
        "note": "No unit or position scope field exists.",
    },
    "roles[].qualifiers": {
        "state": LOST,
        "c01_path": None,
        "note": "Co-, interim, acting, assistant and associate all vanish.",
    },
    "roles[].occupancy": {
        "state": LOST,
        "c01_path": None,
        "note": "Principal versus qualified-not-principal cannot be distinguished.",
    },
    "season": {
        "state": LOST,
        "c01_path": None,
        "note": "The snapshot has a cutoff instant but no season the staff list describes.",
    },
    "source_effective_start": {
        "state": LOST,
        "c01_path": None,
        "note": "Source-effective interval is not the same as known_at and has no field.",
    },
    "source_effective_end": {"state": LOST, "c01_path": None, "note": "As above."},
    "source_title": {
        "state": LOST,
        "c01_path": None,
        "note": "The exact source wording, which every role decomposition is derived from, is dropped.",
    },
    "source_locator": {
        "state": LOST,
        "c01_path": None,
        "note": "evidence_refs is a list of opaque strings, not a record-level locator.",
    },
    "conflicts_with": {
        "state": LOST,
        "c01_path": None,
        "note": "Competing claims cannot be carried, so a projection silently looks unanimous.",
    },
    "evidence_tier": {
        "state": LOST,
        "c01_path": None,
        "note": "Official and candidate evidence project identically.",
    },
    "rights": {
        "state": LOST,
        "c01_path": None,
        "note": "No rights or redistribution field; a consumer cannot tell what it may republish.",
    },
    "play_calling_stated": {
        "state": LOST,
        "c01_path": None,
        "note": "Responsibility is a separate BAS table with no C01 counterpart.",
    },
    "person_display_name": {
        "state": PENDING,
        "c01_path": None,
        "note": "Proposed for an owner-side identity object rather than the snapshot value.",
    },
}

#: Fields a consumer may not silently do without. Asking a projection for one
#: of these must fail rather than return a value that does not mean what the
#: consumer thinks.
REQUIRED_BY_ROLE_AWARE_CONSUMERS = (
    "roles",
    "roles[].unit",
    "roles[].qualifiers",
    "roles[].occupancy",
    "source_title",
    "evidence_tier",
)


class ProjectionRefused(ValueError):
    """Raised when a projection cannot honestly satisfy a consumer's needs."""


def _utc(value: Any, label: str) -> datetime:
    """Parse an instant that is explicitly UTC, or refuse.

    Accepts the two spellings of UTC -- a trailing ``Z`` and ``+00:00`` --
    and nothing else. A naive timestamp has no zone and a non-zero offset is
    not UTC; converting either would be choosing an instant on the source's
    behalf.
    """

    if not isinstance(value, str) or not value.strip():
        raise ProjectionRefused(f"{label} is missing; it must be stated, not invented")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise ProjectionRefused(f"{label} {value!r} is not an ISO 8601 instant") from error
    if parsed.tzinfo is None:
        raise ProjectionRefused(f"{label} {value!r} has no zone; a naive instant is not UTC")
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ProjectionRefused(
            f"{label} {value!r} carries a non-UTC offset; it is refused rather "
            "than converted, because the source stated a different zone"
        )
    return parsed.astimezone(timezone.utc)


def _z(instant: datetime) -> str:
    """The released schema's RFC 3339 UTC form, with a trailing Z."""

    text = instant.astimezone(timezone.utc).isoformat()
    return text[:-6] + "Z" if text.endswith("+00:00") else text


def _refuse_unprojectable(assertion: "StaffAssertion") -> None:
    """Everything one assertion must carry before it may be projected."""

    if not (assertion.program_id or "").strip():
        raise ProjectionRefused(
            f"assertion {assertion.assertion_id} names no program; the snapshot's "
            "parent team cannot be invented"
        )
    if not (assertion.person_id or "").strip():
        raise ProjectionRefused(
            f"assertion {assertion.assertion_id} names no person"
        )
    if not any((ref or "").strip() for ref in assertion.evidence_refs):
        raise ProjectionRefused(
            f"assertion {assertion.assertion_id} carries no evidence reference; "
            "a membership claim with no evidence cannot be projected"
        )
    if not (assertion.rights or "").strip():
        raise ProjectionRefused(
            f"assertion {assertion.assertion_id} carries no rights statement"
        )
    if assertion.conflicts_with:
        raise ProjectionRefused(
            f"assertion {assertion.assertion_id} is in unresolved conflict with "
            f"{', '.join(assertion.conflicts_with)}; the released value has no "
            "field for a competing claim, so projecting it would make the "
            "snapshot look unanimous"
        )
    if assertion.unknown_reason is not None and assertion.unknown_reason not in C01_UNKNOWN_REASONS:
        raise ProjectionRefused(
            f"assertion {assertion.assertion_id} has unknown_reason "
            f"{assertion.unknown_reason!r}, outside the released enum"
        )


def _refuse_conflicting_intervals(assertions: Sequence["StaffAssertion"]) -> None:
    """One person, one role, one unit, two different stated intervals.

    That is a role/interval conflict the sources have not resolved. A
    ``coach_ids`` list would carry the person once and erase the question, so
    the projection refuses instead.
    """

    seen: dict[tuple[str, str, str], tuple[Any, Any, str]] = {}
    for assertion in assertions:
        interval = (assertion.source_effective_start, assertion.source_effective_end)
        for role in assertion.roles:
            key = (assertion.person_id, role.role_code, role.unit)
            if key in seen and seen[key][:2] != interval:
                raise ProjectionRefused(
                    f"person {assertion.person_id} holds {role.role_code}/{role.unit} "
                    f"over two different stated intervals ({seen[key][2]} and "
                    f"{assertion.assertion_id}); resolve the interval conflict before "
                    "projecting"
                )
            seen.setdefault(key, (*interval, assertion.assertion_id))


def project_to_staff_snapshot(
    assertions: Sequence[StaffAssertion],
    *,
    object_id: str,
    ruleset_id: str,
    required_fields: Iterable[str] = (),
) -> dict[str, Any]:
    """Project BAS staff assertions into a released ``StaffSnapshotV1``.

    All assertions must share one program, because the released value has one
    ``team_id``. The result carries the C01 document beside the explicit loss
    report; a caller that declares a required field the schema cannot carry
    gets ``ProjectionRefused`` instead of a plausible-looking document.
    """

    required = list(required_fields)
    unsatisfiable = [
        name
        for name in required
        if FIELD_MATRIX.get(name, {}).get("state") != REPRESENTED
    ]
    if unsatisfiable:
        raise ProjectionRefused(
            "the released StaffSnapshotV1 cannot carry "
            + ", ".join(sorted(unsatisfiable))
            + "; use the BAS-local envelope instead of this projection"
        )
    if not assertions:
        raise ProjectionRefused("no assertions to project")
    for name, value in (("object_id", object_id), ("ruleset_id", ruleset_id)):
        if not isinstance(value, str) or not C01_IDENTIFIER.fullmatch(value):
            raise ProjectionRefused(
                f"{name} {value!r} is not a released C01 identifier "
                "(lowercase, starting alphanumeric, [a-z0-9._-])"
            )

    # Each assertion is checked on its own. The v36.1 checks looked at the
    # set of values across assertions, so one good assertion hid a bad one:
    # a single known_at satisfied "some assertion has a known_at", and a
    # union of evidence satisfied "there is evidence".
    for assertion in assertions:
        _refuse_unprojectable(assertion)

    programs = {assertion.program_id for assertion in assertions}
    if len(programs) != 1:
        raise ProjectionRefused(
            "StaffSnapshotV1 has a single team_id; "
            f"{len(programs)} programs were supplied"
        )
    cutoffs = {
        _utc(assertion.point_in_time_cutoff, "point_in_time_cutoff")
        for assertion in assertions
    }
    if len(cutoffs) != 1:
        # One snapshot has one cutoff. Taking the earliest of several, which
        # v36.1 did, stamps later-cutoff assertions with an instant they were
        # never evaluated against -- a cutoff the evidence does not support.
        raise ProjectionRefused(
            "the assertions carry "
            f"{len(cutoffs)} different point_in_time_cutoff values; a single "
            "snapshot has a single cutoff, so they must be projected separately"
        )
    cutoff = next(iter(cutoffs))
    known: list[datetime] = []
    for assertion in assertions:
        instant = _utc(assertion.known_at_utc, "known_at_utc")
        if instant > cutoff:
            raise ProjectionRefused(
                f"assertion {assertion.assertion_id} became known at "
                f"{_z(instant)}, after the cutoff {_z(cutoff)}; information "
                "from after the cutoff cannot appear in a point-in-time snapshot"
            )
        known.append(instant)
    _refuse_conflicting_intervals(assertions)

    evidence: list[str] = []
    for assertion in assertions:
        for reference in assertion.evidence_refs:
            if reference not in evidence:
                evidence.append(reference)
    coach_ids = sorted({assertion.person_id for assertion in assertions})
    systems = sorted({assertion.source_system for assertion in assertions})

    document = {
        "schema_version": C01_SCHEMA_VERSION,
        "contract": C01_CONTRACT,
        "object_id": object_id,
        # Emitted in the Z form the released schema's pattern requires. BAS
        # records instants with isoformat(), which writes +00:00; the owner
        # schema rejects that form (V37-03), so the adapter normalises a UTC
        # instant and refuses anything that is not one.
        "known_at": _z(max(known)),
        "point_in_time_cutoff": _z(cutoff),
        "provenance": {
            "source_system": systems[0] if len(systems) == 1 else "MULTIPLE",
            "evidence_refs": evidence,
        },
        "ruleset_id": ruleset_id,
        "unit": "record",
        "coordinate_system": "none",
        "value": {"team_id": next(iter(programs)), "coach_ids": coach_ids},
        "unknown_reason": None,
        "compatibility": {
            "classification": "patch",
            "minimum_consumer_version": C01_SCHEMA_VERSION,
        },
    }
    lost = sorted(
        name for name, row in FIELD_MATRIX.items() if row["state"] == LOST
    )
    return {
        "boundary_version": BOUNDARY_VERSION,
        "document": document,
        "projection_is_lossy": True,
        "assertions_projected": len(assertions),
        "distinct_people": len(coach_ids),
        "lost_fields": lost,
        "lost_field_count": len(lost),
        "pending_fields": sorted(
            name for name, row in FIELD_MATRIX.items() if row["state"] == PENDING
        ),
        "not_an_adoption": (
            "This is a BAS-side projection into a released owner schema. It is "
            "not an adoption of a richer contract, not an owner approval and "
            "not a claim that C01 carries the lost fields."
        ),
        "consumers_needing_lost_fields_must_refuse": list(
            REQUIRED_BY_ROLE_AWARE_CONSUMERS
        ),
    }


def read_only_role_consumer(projection: Mapping[str, Any]) -> dict[str, Any]:
    """A stub consumer that needs roles and therefore refuses the projection.

    This exists so the boundary's failure mode is executable rather than
    described. A consumer that asks a ``{team_id, coach_ids}`` value which
    coach is the offensive coordinator has to fail; reading the first id, or
    the longest list, would be inventing an answer.
    """

    value = (projection.get("document") or {}).get("value") or {}
    return {
        "consumer": "ROLE_AWARE_READ_ONLY_STUB",
        "admitted": False,
        "reason": (
            "The released StaffSnapshotV1 value carries a team and a list of "
            "person ids and no role for any of them. This consumer needs "
            f"{', '.join(REQUIRED_BY_ROLE_AWARE_CONSUMERS)} and refuses rather "
            "than guessing which id is which."
        ),
        "people_seen": len(value.get("coach_ids") or []),
        "roles_available": 0,
        "wrote_anything": False,
    }


def read_only_membership_consumer(projection: Mapping[str, Any]) -> dict[str, Any]:
    """A stub consumer that only needs membership, and is therefore satisfied.

    It is satisfied only by an actual membership. v36.1 admitted an empty
    mapping and returned ``team_id: None`` with an empty people list, which is
    a consumer reporting success about nothing. A projection with no document,
    no value, no team or a non-list of people is now refused, and so is one
    this boundary did not produce.
    """

    refusal = _membership_refusal(projection)
    if refusal:
        return {
            "consumer": "MEMBERSHIP_READ_ONLY_STUB",
            "admitted": False,
            "reason": refusal,
            "wrote_anything": False,
        }
    value = projection["document"]["value"]
    return {
        "consumer": "MEMBERSHIP_READ_ONLY_STUB",
        "admitted": True,
        "team_id": value.get("team_id"),
        "people": list(value.get("coach_ids") or []),
        "limits": (
            "Membership only. This consumer must not be used where a role, a "
            "scope, an interval, a conflict or a rights statement matters."
        ),
        "wrote_anything": False,
    }


def _membership_refusal(projection: Any) -> str | None:
    if not isinstance(projection, Mapping) or not projection:
        return "no projection was supplied"
    if projection.get("boundary_version") not in (BOUNDARY_VERSION,):
        return (
            f"projection boundary version {projection.get('boundary_version')!r} "
            f"is not {BOUNDARY_VERSION}; a document from another producer or an "
            "older rule is not admitted as this boundary's output"
        )
    document = projection.get("document")
    if not isinstance(document, Mapping):
        return "the projection carries no document"
    if document.get("contract") != C01_CONTRACT:
        return f"the document is not a {C01_CONTRACT}"
    value = document.get("value")
    if not isinstance(value, Mapping):
        return "the document carries no value"
    team = value.get("team_id")
    if not isinstance(team, str) or not team.strip():
        return "the value names no team"
    people = value.get("coach_ids")
    if not isinstance(people, list) or not people:
        return "the value names no people"
    if not all(isinstance(person, str) and person.strip() for person in people):
        return "the value's people are not all non-empty identifiers"
    return None


#: Things a BAS source can say that are NOT an F10 realized-scheme or coach
#: state conclusion. R37-13-AC06/AC07: BAS facts, the C01 representation,
#: Film inference, F10 state and F11 scientific eligibility stay separate.
F10_STATE_CONTRACTS = frozenset(
    {"intelligence/CoachStateSnapshotV1", "intelligence/TeamSchemeSnapshotV1"}
)


def refuse_source_scheme_as_realized_state(
    source_scheme_claim: Mapping[str, Any], target_contract: str
) -> None:
    """A coaching scheme a source states is not a realized team scheme.

    A page saying a coordinator "runs the Air Raid" is a candidate historical
    claim about intent. An F10 realized-scheme or coach-state conclusion is
    an inference from observed play. Emitting the first as the second would
    launder a source string into a Film-owned conclusion, so this refuses
    every attempt, whatever the claim's evidence tier.
    """

    if target_contract in F10_STATE_CONTRACTS or target_contract.startswith("intelligence/"):
        raise ProjectionRefused(
            f"a source-stated coaching scheme cannot be emitted as {target_contract}: "
            "that is an F10 inference from observed play owned by the Film program, "
            "and BAS holds only the source's claim "
            f"({str(source_scheme_claim.get('source_text') or '')[:60]!r})"
        )


def owner_proposal(matrix: Mapping[str, Mapping[str, str]] = FIELD_MATRIX) -> dict[str, Any]:
    """The specific schema additions BAS proposes, as a proposal only."""

    return {
        "boundary_version": BOUNDARY_VERSION,
        "target_contract": C01_CONTRACT,
        "observed_release": C01_SCHEMA_VERSION,
        "status": "PROPOSED_NOT_ADOPTED",
        "requested_value_fields": [
            {
                "field": "value.staff[]",
                "shape": {
                    "person_id": "string",
                    "roles": [
                        {
                            "role_code": "string",
                            "unit": "string",
                            "qualifiers": ["string"],
                            "occupancy": "string",
                        }
                    ],
                    "source_title": "string",
                    "source_effective_start": "string|null",
                    "source_effective_end": "string|null",
                    "evidence_tier": "string",
                    "conflicts_with": ["string"],
                },
                "why": (
                    "A per-person role episode is the unit BAS actually holds "
                    "evidence for. A flat coach_ids list cannot express it and "
                    "forces every consumer to guess."
                ),
            },
            {
                "field": "rights",
                "shape": {"redistribution": "string", "source_terms": "string"},
                "why": (
                    "A consumer cannot tell what it may republish without a "
                    "rights statement on the document."
                ),
            },
        ],
        "not_self_adopted": (
            "BAS does not adopt a shared representation on the owner's behalf. "
            "Until the owner accepts, the BAS-local envelope stays the record "
            "and the projection stays declared-lossy."
        ),
    }
