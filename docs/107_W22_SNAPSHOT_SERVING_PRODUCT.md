# W22 — Snapshot Serving, API, Dashboard, Explainability & Forecast Product

Wave 22 converts the immutable W21 publication artifact into a real read-only product boundary.

## Functional starter
Implemented:
1. Versioned published-forecast envelope compatible with prior W21 snapshots.
2. Read-only artifact repository with safe game IDs, snapshot lookup, chronological latest selection and market-lane filtering.
3. Explicit freshness state with exact cutoff/publish/serve times and a configurable operations threshold.
4. Framework-neutral product service returning forecast, BAS, uncertainty, availability, matchup/analog context and lineage.
5. Optional FastAPI adapter with OpenAPI and static dashboard hosting.
6. Build-free Texas A&M dashboard starter.
7. Snapshot/model/feature/data/source provenance view.
8. Synthetic immutable publication fixtures/tests proving snapshot-only serving behavior.

## Honesty boundary
W22 does not create trained performance results, causal explanation claims, empirical historical analog quality, real player-availability effects, or a production freshness SLA. Product fields are rendered only when the immutable publication artifact already contains them.

## Serving boundary
The `aggie_analytics.product` and `aggie_analytics.api` packages do not import data, features, PIT-state, modeling, calibration/training or experimentation modules. HTTP/dashboard reads cannot train or recompute forecasts.

## W23 handoff
W23 should productionize dependency pinning/CI/security/observability/backup/runtime benchmarking around this boundary rather than rewriting it.
