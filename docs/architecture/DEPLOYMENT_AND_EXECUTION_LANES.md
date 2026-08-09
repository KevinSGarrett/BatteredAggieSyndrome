# Deployment and Execution Lanes

## OFFLINE_BATCH
Historical ingestion, normalization, canonicalization, feature materialization, training, calibration, evaluation and research.

## FORECAST_REFRESH
Game-week updates and deterministic pregame inference at scheduled/as-needed snapshot times.

## SERVING_READ
Dashboard/API/report retrieval of immutable forecast snapshots. Read-oriented and lightweight.

## RESEARCH
Isolated experiments and analysis. May be CPU/GPU intensive but cannot mutate protected governance.

## FUTURE_LIVE
Deferred in-game replay/inference lane. Isolated from the pregame feature path.

## Default deployment

One local repository/process environment may execute all non-live lanes. Separate processes/worktrees/jobs are useful operational isolation, but they are not automatically separate network services.

A later split into services requires evidence. W03 does not add:
- Kubernetes;
- Kafka;
- Redis;
- a network feature store;
- always-on model server;
- distributed task queue.

## Failure and resumability

Batch stages should produce checkpointable immutable artifacts. A failed later stage should be restartable without re-downloading or mutating prior valid evidence.

Quarantine is preferable to silent coercion.
