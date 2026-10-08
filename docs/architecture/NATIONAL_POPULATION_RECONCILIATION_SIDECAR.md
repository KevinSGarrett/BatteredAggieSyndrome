# National population reconciliation sidecar, 2024-2025 (BAT-718)

Cycle #46 — Attempt #1. Governing plan TP46-A01 revision 2026-10-08.1 sections 1-6. Contract:
`configs/national_population_reconciliation_2024_2025_contract.json` (`BAT-718-NATIONAL-POPULATION-RECONCILIATION-2024-2025-V1`).

The accepted BAT-710 parent leaves every 2024 and 2025 contest `SINGLE_SOURCE_UNRECONCILED`. This sidecar reconciles
those 3,360 parent contests with the 1,854 rows of the two retained CFBD FBS-route captures in both directions. It is
explicit and never a default: it never changes the parent, its contract, its acceptance or any existing query view.
It establishes reconciliation, not independent historical truth, PIT availability or forecasting skill.

## Inputs

All inputs are bound by SHA-256 in the contract and read under the data root of the verified parent database:

| Input | Role |
| --- | --- |
| Parent query database `3baff07f…` (`national_population.sqlite`) | parent contests and program-season cells (assertions) |
| `identity_bindings.jsonl.gz` of program-season stage `711e9dfc…` | accepted NCAA organization ↔ provider team crosswalk |
| `canonical_core_registry.csv` (BAT-387 `10d0bd0a…`) | verified provider team entities and season-bounded aliases |
| `raw/SRC-002/games/sha256_6a49d6e1….json`, `…4bcce67d….json` | 2024 (920 rows) and 2025 (934 rows) provider captures |
| capture receipts `cap_6a97891fa5d6fdff8afab532`, `cap_f17f633d4e589a13300f2320` | route `/games classification=fbs year=<season>`, row count, raw hash |

## Rules

* **Crosswalk.** A participant is bound only through an accepted one-to-one binding (rule
  `NAME_CONFIRMED_BY_SCHEDULE`, `NAME_COLLISION_DISAMBIGUATED_BY_SCHEDULE` or `SCHEDULE_FINGERPRINT_ONLY`). NCAA
  organization ids and provider team ids are never compared with each other.
* **Dates.** A provider `startDate` must be a UTC instant. Its candidate local dates are the dates of the instant
  shifted by -4 h and -10 h (the accepted parent `cfbd_date_basis`). The UTC calendar date is never compared. No venue
  timezone is claimed.
* **Relation.** Within a season, a parent and a provider row are a dated edge when the parent's two bound provider ids
  equal the row's home/away ids as an unordered pair and the parent date is a candidate local date. A relation is
  one-to-one only when both sides have exactly one dated edge and the game id is unique among provider rows.
* **Participant verification** (each side of a relation): crosswalk `BOUND`; the contest side equals its parent
  program-season cell (team-season id, name, division label; a missing cell label equals `UNRESOLVED`); the provider
  display name is a verified registry alias of the provider id's canonical team effective for the season; and the
  normalized parent name equals the normalized provider name (`NAME_EQUAL`) or a verified alias of that canonical team
  effective for the season (`SEASON_ALIAS_DOCUMENTED`). An alias applies to season S when
  `from_year <= S < to_year_exclusive`. Names use the accepted BAT-554 normalization and token expansions.
* **Fields** are compared at their own authority with both values kept: `season`, `date`, `participants`,
  `neutral_status`, `home_orientation`, `completion`, `score` (oriented through the bound ids, never by provider
  order), `classification_a`, `classification_b`. A missing value is unknown, never zero. A non-integer, negative or
  boolean score and a non-boolean flag are invalid. `field_conflicts` lists every `DISAGREE`.

## Records

Canonical JSON (sorted keys, separators `,` and `:`, UTF-8, no binary float).

Parent record (one per parent contest, ordered by season, contest date, key): `record_type`
(`parent_reconciliation`), `contest_key`, `season`, `contest_date`, `parent` (every parent contest column verbatim),
`participants.a|b` (`key`, `org_id`, `team_name`, `membership`, `crosswalk{state, provider_team_id, rule, reason}`,
`program_season{state, mismatched_fields}`, `provider_name`, `name_link`, `verified`), `route_scope`
(`IN_FBS_ROUTE` or `OUTSIDE_FBS_ROUTE`), `candidates{same_pair_provider_rows, dated_provider_rows}`, `relation`
(`provider_row_key`, `provider_game_id`, `one_to_one`, `promoted`, `side_map`) or null, `comparisons` or null,
`field_conflicts`, `disposition`, `disposition_reason`.

Provider record (one per capture row, key `src002:<season>:<ordinal as four digits>`): `record_type`
(`provider_reconciliation`), `provider_row_key`, `capture_season`, `row_ordinal`, `capture{sha256, capture_id}`,
`raw_row_sha256` (SHA-256 of the row's canonical JSON), `provider` (the game-fact fields only), `provider_game_id`,
`candidate_local_dates`, `participants.home|away` (`provider_team_id`, `provider_team_name`,
`provider_classification`, `crosswalk{state, org_id, rule}`, `parent_key`), `candidates{same_pair_parent_contests,
dated_parent_contests}`, `relation` (`contest_key`, `one_to_one`, `promoted`) or null, `field_conflicts`,
`disposition`, `disposition_reason`.

Dispositions and their precedence are listed in the contract (`rules.parent_dispositions`,
`rules.provider_dispositions`). The summary (`summary.json`) holds the parent and provider totals by season and
disposition, the relation counts, field results for promoted and unpromoted relations, name-link states and route
scope, computed only from the records.

## Materialization and identity

* Content root `canonical/national_population_reconciliation_2024_2025/sha256/<content identity>/` holds
  `parent_reconciliation.jsonl`, `provider_reconciliation.jsonl` and `summary.json`. The content identity is the
  SHA-256 of the canonical content document (schema `BAS-NATIONAL-POPULATION-RECONCILIATION-CONTENT-1`).
* Database root `…/sha256/<database identity>/national_population_reconciliation.sqlite`. The database identity is the
  SHA-256 of the canonical database document (schema `BAS-NATIONAL-POPULATION-RECONCILIATION-DATABASE-1`), which binds
  the database bytes, the content identity and the table counts.
* Each manifest lives at `manifests/national_population_reconciliation_2024_2025/sha256/<identity>/run_manifest.json`.
  Writes are create-only. Input order, chunking and an interrupted, resumed build cannot change a byte.

## Reading it

```
bas-national-population-query --database <parent national_population.sqlite> \
  --reconciliation <…\sha256\<id>\national_population_reconciliation.sqlite> \
  --grain parent-reconciliation|provider-reconciliation [--season S] [--team T] [--contest K] [--disposition D] \
  [--limit N --offset M | --all]
```

Before any row is served, the reader verifies:

1. the sidecar's location, manifest identity, bytes and schema;
2. its meta claims (contract, parent, inputs, labels, scope, parameters) and table counts;
3. the accepted parent and every bound input.

It then re-derives every record, the summary and the content identity from those inputs. Any difference refuses with
its own code, for example `RECONCILIATION_PARENT_ROW_MISSING`, `RECONCILIATION_RELATION_MISMATCH`,
`RECONCILIATION_FIELD_MISMATCH`, `RECONCILIATION_SUMMARY_MISMATCH`, `RECONCILIATION_CONTENT_IDENTITY_MISMATCH`,
`RECONCILIATION_SCOPE_CLAIM_INVALID`, `RECONCILIATION_PIT_CLAIM_INVALID` or `RECONCILIATION_SOURCE_BYTES_MISMATCH`.
`--require-pit` is always refused. Without `--reconciliation`, every existing grain answers exactly as before.

Labels on every answer: `CACHED_SOURCE_RECONCILIATION_ONLY`, `NOT_ESTABLISHED_PROVIDER_MAY_SHARE_UPSTREAM_EVIDENCE`,
`PIT_ELIGIBILITY_NOT_ESTABLISHED`, `EXPOSED_NOT_PROTECTED`, `RETAIN_PROTECTED_LANE_BLOCKED`, predictive skill
`NOT_ESTABLISHED`, `EXPLICIT_SIDECAR_SELECTION_ONLY_NEVER_A_DEFAULT`.
