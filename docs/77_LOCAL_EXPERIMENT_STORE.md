# Local Experiment Store and Persistence Contract

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Rationale

Wave 18 targets a local-first research workflow. A full distributed metadata service is unnecessary before measured concurrency justifies it. The reference store therefore uses SQLite for local canonical experiment metadata and evidence while keeping large datasets, model binaries, and checkpoints outside the repository and outside the metadata database.

## Tables

The reference schema contains `experiment_specs`, `queue_events`, `result_packets`, `artifact_records`, and `replay_reports`.

`experiment_specs` is immutable by identity. `queue_events` is append-only and hash chained. `result_packets` are append-only by `(experiment_id, attempt)`. `artifact_records` store content hashes and locations rather than embedding large bytes. `replay_reports` bind the replay to the source result and record a deterministic status taxonomy.

## Transactions

Experiment creation, queue-event append, result insertion, artifact registration, and replay insertion are transactional. A failed transaction is rolled back. Queue event indexes must be contiguous and their `previous_event_hash` must match the prior event. This prevents a UI or worker from silently rewriting queue history.

## Concurrency boundary

SQLite is approved for the local single-machine metadata reference path. It is **not** approved as a shared NFS/distributed coordination backend. If W21/W23 later require multi-host transactional scheduling, the storage interface can move to PostgreSQL or another evidence-backed backend without changing canonical IDs or event semantics.

## Backups

The metadata database is small enough for frequent file-level backups after checkpoint/transaction boundaries. Backup artifacts receive their own manifest/hash. The database does not replace the canonical repository governance files, W17 protected-rule seal, or external large-artifact storage.

## Integrity checks

`PRAGMA integrity_check`, foreign-key checks, duplicate-ID checks, queue hash-chain checks, and result/experiment references are part of the reference validation surface. A corrupt metadata database blocks adoption/replay until restored or reconstructed from immutable event/result artifacts.
