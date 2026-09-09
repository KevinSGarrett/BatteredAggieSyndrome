# StaffSnapshotV2 — proposed coaching snapshot

**Status:** PROPOSED. Adoption pending C01 / CFIP-22. Not consumed by Cycle #30 fitted models.

## Grain

Program × as-of UTC × role family.

## Required fields

| Field | Type | Notes |
|---|---|---|
| `program_id` | string | Canonical; never `DISPLAY:` |
| `as_of_utc` | string | Aware UTC |
| `role` | string | Predeclared family, not observed title |
| `formal_title` | string or null | Exact source title |
| `responsibility` | string or `UNKNOWN` | Distinct from title; play-caller never inferred |
| `episode_refs` | object[] | Zero, one, or many effective-dated episodes |
| `episode_cardinality` | integer | |
| `disposition` | enum | `CONFIRMED_APPOINTMENT`, `CONFIRMED_CO_SHARED_ROLE`, `CONFIRMED_VACANCY`, `ROLE_NOT_APPLICABLE`, `UNKNOWN_NOT_LISTED`, `ACQUISITION_FAILED`, `RIGHTS_BLOCKED`, `CONFLICT`, `CANDIDATE_ONLY`, `APPLICABILITY_UNRESOLVED`, `QUEUED_FOR_BACKFILL`, `NOT_ATTEMPTED` |
| `person_id` | string or null | Bound in the same source span as title |
| `source_span_id` | string or null | DOM node / table row / announcement block |
| `attempt_count` | integer | Derived from request/receipt ledger |
| `conflict` | object or null | Title-versus-responsibility or multi-occupant |
| `coverage` | object | Route, status, receipt identities |
| `pit_admitted` | boolean | Retrospective documented episodes may be false |

## Negative fixtures

- Equal-length name/title array zip
- `DISPLAY:` program IDs
- Literal `attempted:true` with zero ledger rows
- CFBD-inferred OC/DC
- Vacancy inferred from absence
- Collapsed co-coordinator from sequential occupants
