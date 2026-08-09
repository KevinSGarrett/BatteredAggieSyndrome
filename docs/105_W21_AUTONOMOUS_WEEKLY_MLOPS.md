# W21 Autonomous Weekly MLOps Starter

## Status
Functional starter. This wave does **not** claim a trained champion, protected benchmark improvement, empirical feature winner, A&M correction, BAS effect, or production SLA.

## Orchestration decision
W21 uses a dependency-free local durable orchestrator built from explicit step functions plus an append-once checkpoint store. The backend is intentionally replaceable. Prefect remains a valid future adapter but is not a base dependency until operational evidence earns the complexity.

## Weekly dependency chain
`INGEST -> QA_QUARANTINE -> PIT_STATE -> FEATURES -> TRAIN_CHALLENGER -> CALIBRATE -> GOVERNED_EVALUATION -> PROMOTION_OR_RETAIN -> FORECAST -> PUBLISH -> RESULT_SCORING -> POSTMORTEM -> RESEARCH_QUEUE`

Each successful step records an immutable output reference and content hash. Replaying the same immutable run identity skips successful checkpoints. A failed or quarantined step terminates that run; remediation must be explicit rather than rewriting history.

## Promotion boundary
The W21 champion registry **does not evaluate protected metrics**. It consumes a completed protected decision carrying candidate/champion hashes, the W17 judging-rule seal hash, a protected-evidence hash, evaluator identity and decision timestamp. Only that external decision can promote a challenger.

## Rollback
Champion changes append decision history. Rollback requires the expected current artifact, explicit restore target and reason; it appends rollback evidence and atomically updates the current pointer.

## Publication
Forecast snapshots are immutable and bind game/snapshot ID, forecast cutoff, model artifact SHA, feature snapshot ID, public summary and lineage. Reusing a snapshot ID with different content is rejected.

## Postmortem/research loop
Completed-game results can produce append-only error evidence. Large errors may create a proposal whose only allowed automated action is `PROPOSE_EXPERIMENT_ONLY`. Postmortems cannot rewrite historical predictions, promotion rules or champion state.

## W22 handoff
W22 should build read-only API/dashboard/explanation surfaces over these immutable published forecast artifacts. Request paths should not retrain models or recompute mutable historical state.
