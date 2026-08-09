# Hyperparameter Optimization Study Governance

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Study identity

An HPO study binds candidate family, target, development split, objective metrics, search-space version, sampler, pruner, trial budget, concurrency, seed policy, storage backend, and resource budget. The search space is versioned **before** trials run.

## Development-only objectives

Only `SPLIT-DEV-HIST` and `SPLIT-DEV-SEL` may be optimization/pruning inputs. W17 protected holdout metrics and 2026+ forward-shadow results cannot be observed by the HPO engine.

This restriction applies to early stopping and pruning too: a trial cannot be pruned based on protected evidence.

## Parameter types

Search-space contracts support discrete categorical, integer, float/log-float, boolean, and conditional parameters. Bounds, steps, log scale, conditional parent values, and default/reference values are recorded. An unbounded search dimension is rejected.

## Budget

Trial count, concurrency, CPU/RAM/GPU/VRAM/disk limits, timeout/stop conditions, and paid-compute authorization are frozen at study creation. Expanding the search budget creates a new study version or explicit continuation event; it does not silently rewrite the old study.

## Storage

Optuna is the preferred replaceable adapter. Local studies can use journal or supported local persistent storage. Shared SQLite over distributed/NFS-style execution is prohibited. A future multi-host optimizer may use supported RDB storage, but canonical study/experiment identity remains tool-neutral.

## Pruning

Pruning is optional and recorded. Pruned trials remain first-class search history. A pruner cannot hide failed regions by deleting trial evidence. Pruner/sampler versions are part of lineage.

## Failure handling

Worker crash, OOM, invalid parameter combination, data/materialization error, governance block, and scientific poor performance are distinct trial outcomes. Infrastructure failure is never counted as evidence that a scientific hypothesis is false.
