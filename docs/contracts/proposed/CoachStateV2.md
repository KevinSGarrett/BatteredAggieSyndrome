# CoachStateV2 — proposed person/career state

**Status:** PROPOSED. Adoption pending C01 / CFIP-22. Not a fitted-model input.

## Grain

Person × employment episode, with separately scoped career context. A snapshot cell is not a career.

## Identity

`person_id` is `stable_person_id(program_id, person, source_person_id=)`. The same surface name at two programs must not share an ID. Source-native IDs, when present, are hashed in; they are not reused across programs.

## Required fields

| Field | Type | Notes |
|---|---|---|
| `person_id` | string | Program-scoped stable person |
| `episode_id` | string | Employment episode; distinct from snapshot `span_id` |
| `program_id` | string or null | Null only for non-program jobs; never `DISPLAY:` |
| `formal_title` | string | Exact source title |
| `role_normalization` | string or `UNNORMALIZED` | HC/OC/DC families or unnormalized; does not redefine the opportunity denominator |
| `effective_from` | string or `UNKNOWN_DAY` | No guessed start day |
| `effective_to_exclusive` | string or `UNKNOWN_DAY` | `present` does not expand through a later calendar year |
| `relationship` | `CONCURRENT_SHARED` \| `SEQUENTIAL_CHANGE` \| `SOLE` | |
| `evidence` | object[] | Source URI, revision, rights, retrieval, known-at |
| `conflict` | object or null | |
| `career_scope` | `IN_PERIOD_1963_2026` \| `PRE_1963` \| `PROFESSIONAL` \| `OTHER_LEVEL` | |
| `wikimedia_revision` | string or null | Required if Wikimedia used; Wikipedia is not official confirmation |
| `pit_admitted` | boolean | Wikimedia career pages remain false |

## Career preservation

Infobox career indices pair **within one template**. Both coordinator links are preserved. Basketball/baseball infoboxes are skipped. Unwrapped `| coach_yearsN` still parses when no templates exist. Complete career-assertion roundtrip for every historical occupant remains unfinished; missingness stays visible.

## Observed vs inferred

An official staff-directory appointment is observed. Play-caller, schematic influence, and latent team state are different epistemic surfaces and must not be filled from title text.

## Migration

StaffSnapshotV1 / CoachStateV1 remain skeletal. Unknown fields must not be dropped. No personal email/phone ingestion.
