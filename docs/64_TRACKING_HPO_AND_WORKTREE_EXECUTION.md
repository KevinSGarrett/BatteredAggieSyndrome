# Tracking, HPO & Worktree Execution

## MLflow Tracking adapter
MLflow Tracking remains the preferred replaceable adapter. Current official documentation supports local run tracking, SQLAlchemy-compatible metadata stores including SQLite, local artifact stores, optional server deployment, and run comparison.

Canonical Aggie experiment IDs remain independent from MLflow run IDs.

### Initial local recommendation
- SQLite metadata;
- local artifact directory outside repository ZIP;
- no mandatory server;
- no mandatory cloud;
- no model-promotion authority.

## Optuna HPO adapter
Optuna remains the preferred replaceable adapter for bounded development-only HPO.

Allowed objectives: approved development-history/development-selection evidence.
Forbidden objectives: W17 protected holdout and 2026+ forward-shadow evidence.

Search-space version, sampler, pruner, metric/direction, split, budget, concurrency, storage backend, and seed policy are frozen before trials.

### Storage
Persistent RDB or Journal storage is supported. Journal is preferred for file-backed/multiprocess workflows. SQLite is not treated as a distributed/NFS coordination backend.

## Worktrees
Code-changing experiments use a dedicated Git worktree when Git metadata exists, or an immutable verified source snapshot when operating from ZIP handoffs.

Experiment workers cannot edit protected judging files. Shared unfrozen contracts have one mutation owner.

## Concurrency
Concurrency is bounded and adaptive based on task DAG, CPU, RAM, GPU/VRAM, disk, artifact pressure, dataset contention, and shared-contract mutation conflicts. No global fixed worker count is treated as optimal.
