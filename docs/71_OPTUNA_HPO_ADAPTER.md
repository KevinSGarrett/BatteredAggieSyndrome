# Optuna HPO Adapter Contract

## Decision
Optuna is the preferred replaceable adapter for bounded development-only HPO.

Official Optuna documentation supports persistent RDB storage, Journal storage, and multiple parallelization modes.

## Study identity
A study binds hypothesis/model family, search-space version, sampler/pruner, development split, objective metrics/directions, seed policy, resource budget, storage backend, code/data/feature identity, and parent study where relevant.

## Search spaces
Search-space parameters are explicit and versioned:
- integer;
- float;
- log-float;
- categorical;
- conditional.

Changing bounds, choices, or conditional relationships creates a new search-space version.

## Objective restriction
Allowed: approved development-history/development-selection evidence.
Forbidden: W17 protected 2024–2025 holdout, 2026+ forward shadow, and any protected metric copied back from promotion review.

## Persistence
Local RDB or Journal storage may be used. Journal is preferred for file-backed/multiprocess workflows. SQLite is not treated as a distributed/NFS coordination backend.

## Pruning/history
Pruning may save development compute, but pruned/failed trials remain part of search history.

## Budget
Trial count/concurrency are bounded per study. There is no universal global trial count.
