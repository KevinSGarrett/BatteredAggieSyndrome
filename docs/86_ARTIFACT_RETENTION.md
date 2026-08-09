# Experiment Artifact Manifest, Retention, and Cache Policy

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Repository boundary

The cumulative repository does not contain large training matrices, model binaries, checkpoints, full MLflow stores, Optuna databases, or raw data. It contains manifests, schemas, tiny fixtures, code, decisions, and reproducible acquisition/rebuild instructions.

## Artifact classes

Canonical classes include CONFIG, LOG, METRIC_PACKET, PREDICTION_PACKET, MODEL_BINARY, TRAINING_MATRIX, PLOT, REPORT, REPLAY_PACKET, and CHECKPOINT. Each artifact records experiment/attempt, content hash, size, URI, producer, sensitivity, retention class, and whether it is repository-embeddable.

## Retention

Negative/rejected experiment metadata is retained even when large derived artifacts are garbage-collected. A deleted large artifact leaves a tombstone/manifest state explaining the retention decision rather than disappearing from lineage.

## Cache versus evidence

Caches are rebuildable and not authoritative evidence. Evidence artifacts needed for replay/promotion have stronger retention. A cache hit cannot substitute for validating content hash and input identity.

## Sensitivity

Raw and normalized third-party bulk payloads and secrets cannot be committed. Secret-like content is prohibited from artifact manifests. License and redistribution metadata does not constrain private local retention or training; public-repository suitability receives a separate review only when publication is actually proposed.
