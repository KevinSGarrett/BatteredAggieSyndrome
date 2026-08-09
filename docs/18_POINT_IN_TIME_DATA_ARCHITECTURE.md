# Point-in-Time Data Architecture — Wave 08

Status: **accepted design contract + synthetic executable fixtures**, not production historical materialization.

## Core invariant
A historical feature is eligible only when the exact information/version could have been known at the intended prediction cutoff **and** is applicable to the target game/state under its valid/effective interval.

W08 therefore uses two independent temporal axes:

1. **Knowledge/system time** — `published_at`, `source_reported_at`, `retrieved_at`, `first_known_at`, derived `prediction_eligible_at`.
2. **Validity/event time** — `observed_at`, `effective_at`, `valid_from`, `valid_to`, target game time, weather `forecast_valid_at`, reporting periods.

Do not use `effective_at` as a proxy for public knowability. Do not use a season/fiscal label as evidence that a fact was public.

## `first_known_at`
`first_known_at` is the earliest defensible public-knowledge timestamp for the **exact version/value**. It must be evidence-backed. Preferred evidence is an archived/versioned source publication or provider availability timestamp. When earlier public timing cannot be defended, use the project's retrieval timestamp or a documented conservative lag rather than guessing.

`prediction_eligible_at` is a derived/cache field under a named temporal policy. It never bypasses target-validity, revision, retrospective-evidence or domain-specific checks.

## Revisions
Mutable evidence is append-only. A later correction cannot rewrite a historical replay. At a historical cutoff, the gateway selects only versions known by that cutoff; later versions remain lineage but are ineligible.

## Mandatory gateway
`CMP-005 pit_state` is the only allowed state-to-feature temporal gateway. `CMP-006 feature_factory` consumes PIT-safe state; it does not query raw/current mutable source tables directly.

## Fail closed
Unknown or ambiguous temporal semantics are `REVIEW_REQUIRED`, quarantined, degraded or ineligible. They are never guessed into a historical feature row.

## Maturity
The W08 synthetic battery proves that the contract and reference selector behave as specified for controlled cases. It does **not** prove the future materialized historical lake is leakage-free; W19+ integration/replay must establish that evidence.
