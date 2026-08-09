# Entity Storage Evaluation — Wave 07

## Decision
**PostgreSQL remains deferred and non-mandatory.**

This is not a claim that PostgreSQL is unsuitable. It is a claim that the current project has not demonstrated the concurrency/transaction requirement that would justify operating it in Phases 1-3.

## Current workload evidence
The accepted product is local-first and batch/snapshot oriented. Canonicalization and entity resolution currently have:
- one authoritative pipeline/writer;
- append-only raw evidence;
- append-only mapping/decision events;
- review state derivable from those events;
- no current multi-user editing service;
- no current requirement for cross-process high-contention writes.

That structure can be represented as versioned Parquet datasets queried by DuckDB behind the existing storage boundary.

## Why append-only matters
Instead of updating a mutable `current_mapping` row in place, W07 stores mapping/decision events and derives current state from the latest non-superseded valid decision. That preserves reproducibility and removes much of the transactional need.

## Reopen triggers
A relational transaction server becomes justified if later implementation demonstrates one or more of:
- multiple concurrent human/service writers;
- atomic multi-record corrections across processes;
- external multi-user review workflows;
- contention or integrity problems that the single-writer event model cannot safely handle;
- measured performance showing the local default is materially inadequate.

## Benchmark honesty
W07 does not have a materialized national entity corpus and therefore does **not** invent throughput/latency numbers. W19 owns the implementation/data-volume benchmark. The storage port remains explicit so PostgreSQL can be introduced without changing canonical semantics.

## Alternatives
SQLite could be investigated for a future single-machine transactional review UI, but W07 does not add a database merely to have one. PostgreSQL remains the preferred relational-server candidate if genuine concurrent workflow requirements appear.

## Decision matrix
See `governance/ENTITY_STORAGE_DECISION_MATRIX.csv`.
