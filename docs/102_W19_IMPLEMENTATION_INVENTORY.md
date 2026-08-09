# W19 Implementation Inventory

## Functional starter
- `aggie_analytics.data.adapters`: CSV/JSON source adapter contract.
- `aggie_analytics.data.snapshots`: immutable content-addressed raw store + manifests.
- `aggie_analytics.entities.resolution`: fail-closed exact normalized aliases.
- `aggie_analytics.lineage`: deterministic parent/transform lineage records.
- `aggie_analytics.temporal.state`: W08 eligibility-backed PIT state.
- `aggie_analytics.features.factory`: PIT-only feature specs/factory + feature lineage.

## Evidence/fixtures
- synthetic W19 source fixture;
- curated real SportsDataverse schedule row + its reconnaissance manifest copied from FINAL v1.2.

## Explicitly not completed
- full historical national materialization;
- authenticated CFBD pulls;
- population missingness/coverage claims;
- calibrated fuzzy entity matching;
- trained feature/model selection;
- protected benchmark evaluation.
