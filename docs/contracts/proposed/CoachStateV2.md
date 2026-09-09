# CoachStateV2 — proposed person/career state

**Status:** PROPOSED. Adoption pending C01 / CFIP-22.

## Grain

Person × employment episode, with separately scoped career context.

## Required fields

| Field | Type | Notes |
|---|---|---|
| `person_id` | string | Canonical person |
| `episode_id` | string | Employment episode |
| `program_id` | string or null | Null for non-program jobs |
| `formal_title` | string | Exact source title |
| `role_normalization` | string or `UNNORMALIZED` | Does not redefine the opportunity denominator |
| `effective_from` | string or `UNKNOWN_DAY` | No guessed start day |
| `effective_to_exclusive` | string or `UNKNOWN_DAY` | No guessed end day |
| `relationship` | `CONCURRENT_SHARED` \| `SEQUENTIAL_CHANGE` \| `SOLE` | |
| `evidence` | object[] | Source URI, revision, rights, retrieval |
| `conflict` | object or null | |
| `career_scope` | `IN_PERIOD_1963_2026` \| `PRE_1963` \| `PROFESSIONAL` \| `OTHER_LEVEL` | |
| `wikimedia_revision` | string or null | Required if Wikimedia used; never earlier PIT |

## Migration

StaffSnapshotV1 / CoachStateV1 remain skeletal. Unknown fields must not be dropped. No personal email/phone ingestion.
