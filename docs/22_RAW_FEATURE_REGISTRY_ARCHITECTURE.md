# Raw Feature Registry Architecture — Wave 09

## Scope
Wave 09 registers **1,197** verified raw fields from the reconnaissance temporal registry and reconciles them with the W06 dataset/source universe. This is a metadata/contract layer, **not feature selection**.

## Invariant chain
`source evidence -> canonical identity -> W08 PIT gateway -> raw-field metadata -> W10 candidate experiment -> empirical lifecycle`

A field's presence in `RAW_FIELD_REGISTRY.csv` never implies predictive usefulness or production inclusion.

## Identity
`raw_field_id` is stable once assigned. Identity is source-scoped and includes source, dataset/model and exact field path. A rename or semantic repurpose creates a new raw-field identity and a supersession record rather than silently changing an existing ID.

## Temporal precedence
The 1,197 classifications imported from `UNIFIED_TEMPORAL_FIELD_REGISTRY.csv` are preserved exactly. Schema discovery may observe types or missingness but may not silently downgrade a known temporal/leakage risk. Unknown safety fails closed.

## Missingness
Reconnaissance sample missingness is retained as evidence only. It is not treated as population missingness. Population completeness is measured on each materialized source snapshot in later implementation.

## Dataset schemas
W06 endpoint rows lacking enumerated fields are `SCHEMA_PENDING_MATERIALIZATION`. Wave 09 does not invent column names to make the registry look complete.

## Redundancy
Exact field-name overlap creates a review cluster only. Semantic equivalence requires compatible grain, units, definitions, temporal semantics and canonical join path.
