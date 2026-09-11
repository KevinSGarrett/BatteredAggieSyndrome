# StaffSnapshotV2 — proposed coaching snapshot

**Status:** PROPOSED. Adoption pending C01 / CFIP-22 / CFIP-23. Not consumed by fitted models. This document does not adopt shared contracts.

## Grain

Program × as-of UTC × role family (`head_coach` | `offensive_coordinator` | `defensive_coordinator`).

## Checker packet (local `contracts_v2`)

The executable local checker uses **string** `episode_refs` and these dispositions:

| Field | Type | Notes |
|---|---|---|
| `program_id` | string | Canonical; never `DISPLAY:` |
| `as_of_utc` | aware UTC | Snapshot cutoff, not first-publication |
| `role` | enum | Role family, not the observed title |
| `formal_title` | string or null | Exact source title when one occupant |
| `responsibility` | `UNKNOWN` \| `UNVERIFIED` \| `ROLE_FAMILY_ONLY` | Play-caller never inferred from title |
| `episode_refs` | string[] | Distinct `span_id` values |
| `episode_cardinality` | integer | Must equal `len(episode_refs)` |
| `disposition` | enum | `CONFIRMED_SINGLE_OCCUPANT`, `CONFIRMED_CO_SHARED_ROLE`, `SEQUENTIAL_MULTI_OCCUPANT`, `CONFLICTING_CANDIDATES`, `UNKNOWN_NOT_LISTED`, `ACQUISITION_FAILED`, `NOT_ATTEMPTED` |
| `attempt_count` | integer | Ledger-derived; `0` is allowed only with `NOT_ATTEMPTED` |
| `pit_admitted` | boolean | Official HTML snapshots remain `false` while the scientific-trust gate is closed |

Optional: `source_id`, `source_span_id`, `source_receipt_id`, `role_scope`, `notes`, `bas_episode_extension`.

## BAS matrix adapter

BAS cells currently use object episode refs and `CONFIRMED_APPOINTMENT`. `staff_snapshot_v2_from_bas_matrix_cell` maps:

- object refs → `span_id` strings; original objects preserved in `bas_episode_extension`
- `CONFIRMED_APPOINTMENT` → `CONFIRMED_SINGLE_OCCUPANT` when cardinality is 1
- multi-occupant `CONFIRMED_APPOINTMENT` → `CONFIRMED_CO_SHARED_ROLE` (does not invent a vacancy)
- `responsibility` = `ROLE_FAMILY_ONLY` until a sourced play-caller field exists

Adapter success is not C01 acceptance.

## Required episode semantics (proposed C01 field set)

Each underlying StaffRoleEpisode (not collapsed into the snapshot) must carry:

- stable `person_id` scoped by program (namesakes at different programs remain distinct)
- original title plus normalized family
- coaching vs support classification; deputy/director/unit “head coach of X” are not program HC
- effective start/end with date precision; unknown days stay `UNKNOWN_DAY`
- concurrency vs sequential reason when cardinality > 1
- publication / known-at / retrieval / snapshot cutoff as distinct clocks
- source raw/content/revision/span/rights
- disposition, conflict, and missingness; no vacancy inferred from absence

## Negative fixtures

- Equal-length name/title array zip
- `DISPLAY:` program IDs
- Literal `attempted:true` with zero ledger rows
- CFBD-inferred OC/DC
- Vacancy inferred from absence
- Collapsed co-coordinator from sequential occupants
- Deputy / director / “head coach of offense|defense” as program HC
- Conference-host pages (WAC/Big 12/SEC) as a program athletics origin
