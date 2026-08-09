# Dataflow and Storage Architecture

## Data zones

1. **RAW** — immutable external payloads/files exactly as received.
2. **QUARANTINE** — invalid, ambiguous or contract-failing evidence awaiting repair/review.
3. **CANONICAL** — normalized entities/observations with stable internal IDs and provenance.
4. **PIT_STATE** — effective-dated/as-of snapshots eligible at a specific prediction timestamp.
5. **FEATURES** — derived PIT-safe features with transform version and parent lineage.
6. **TRAINING** — immutable training/evaluation matrices and labels tied to split policy.
7. **MODEL_ARTIFACTS** — trained candidates/champions, calibration artifacts and metadata.
8. **FORECAST_SNAPSHOTS** — immutable prediction products for a game + prediction timestamp.

No zone overwrites history merely to represent "latest".

## Preferred local physical implementation

### Raw
Preserve native files/payloads and a manifest. Convert only in downstream zones.

### Analytical zones
Use partitioned Parquet as the preferred durable columnar representation. Query/materialize locally with DuckDB. Polars remains a strong candidate execution library when its lazy/streaming behavior is useful.

This is a strong default, not a claim that every domain must be physically Parquet.

### Relational state
Do not make PostgreSQL mandatory in Phases 1-3. W07 should test whether canonical identity/review workflows genuinely require a transactional relational server. If they do, implement a storage port and PostgreSQL adapter without changing upstream/downstream contracts.

## Storage responsibilities

| Need | W03 default |
|---|---|
| exact source bytes | filesystem/object-like local storage + hashes |
| large tabular history | Parquet |
| local analytical joins/aggregations | DuckDB |
| feature/training matrices | Parquet + DuckDB |
| small configuration/governance | repository JSON/CSV/YAML/Markdown |
| model binaries | external artifact directory, not cumulative repo |
| forecast product | immutable JSON/Parquet snapshot + lineage |
| concurrent relational workflow | deferred adapter; PostgreSQL candidate |
| online cache | not required |
| event bus | not required |

## Point-in-time flow

A feature builder receives an explicit `AsOfContext`. It may only read observations eligible under that context through the PIT-state interface.

Forbidden pattern:

`feature -> provider API/current table -> value`

Accepted pattern:

`feature -> PIT state -> eligible observation -> lineage`

## Data-location rule

Large runtime data lives outside repository ZIPs. The repository contains schemas, contracts, acquisition code, tiny fixtures, manifests and documentation.
## W08 temporal flow
Source publication/version/capture evidence is converted into canonical observations with distinct knowledge and validity times. `pit_state` performs deterministic as-of selection under an immutable cutoff before any feature construction. Later source corrections remain append-only and cannot rewrite prior snapshots.
