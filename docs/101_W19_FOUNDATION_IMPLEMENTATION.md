# Wave 19 — Starter Data / Entity / Feature Implementation

Status: **functional starter implementation**, not production historical materialization.

## Implemented chain
`approved source evidence -> immutable content-addressed raw snapshot -> canonical entity resolution -> W08 fail-closed PIT state -> W10-style feature factory -> explicit lineage`

### Source adapters and raw snapshots
W19 adds dependency-free CSV/JSON adapters plus an immutable content-addressed raw snapshot store. Snapshot identity is derived from raw bytes, raw bytes are preserved unchanged, and each snapshot receives retrieval/source/schema/row-count metadata. This satisfies the starter form of REQ-058/AC-008 without pretending that all national sources have been materialized.

The repository includes a tiny **curated real reconnaissance fixture** (`fixtures/w19/recon_real/`) copied from the authoritative reconnaissance pack. It is evidence for adapter/contract behavior, not a historical lake or population-quality sample.

### Entity resolution
W19 adds a fail-closed resolver using source-scoped or global normalized exact aliases. Unknown names remain `UNRESOLVED`; ambiguous aliases become `REVIEW_REQUIRED`. W19 deliberately does not auto-accept fuzzy/probabilistic links without evidence.

### PIT state + lineage
`build_pit_state` calls the existing W08 eligibility gateway and includes only observations eligible at the forecast cutoff. It emits deterministic lineage over included observation IDs. Feature construction consumes this PIT state only.

### Feature factory
The starter supports explicit registered feature specifications with `LATEST`, `COUNT`, and `MEAN` aggregations. It emits feature-level lineage. It does **not** promote any feature, select windows, or claim predictive value.

### Synthetic end-to-end fixture
The W19 test battery proves a future game is excluded from a pregame state and therefore cannot enter a derived feature. It also verifies immutable snapshot hashes and fail-closed entity resolution.

## Deliberate limits
- No authenticated CFBD acquisition is executed because no user secret is embedded or requested.
- No full-population source completeness, missingness, or schema-stability claim is made.
- No trained model, HPO winner, feature winner, A&M effect, BAS effect, or protected metric is claimed.
- PostgreSQL remains unnecessary for this single-writer starter; the storage boundary remains open to later evidence.
