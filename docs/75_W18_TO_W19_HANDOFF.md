# W18 → W19 Handoff

W19 may begin only from the bound **Wave 18 v0.18.2 full-rebuild** cumulative/hydration pair. Both earlier W18 pairs are rejected and must never be used as a W19 parent.

## First task
`TASK-041` remains the first W19 implementation task: approved source-adapter/raw-snapshot starters.

## W18 assets W19 should use
- canonical experiment/study IDs and immutable lineage;
- transactional local experiment metadata/evidence store;
- append-only hash-chained research queue;
- bounded local resource scheduler and worktree/shared-contract locks;
- feature tournament and model tournament engines;
- development-only HPO/search-space governance;
- artifact manifests, retention/sensitivity policy, and replay engine;
- semantic result-comparison/adoption logic;
- one-way promotion-review bridge into W17 governance;
- advanced challenger admission gate;
- MLflow/Optuna replaceable adapter contracts;
- W17 immutable judging-rule seal.

## W19 must not infer
- a tournament winner exists;
- HPO has found superior parameters;
- MLflow/Optuna are mandatory or already installed;
- advanced challengers are empirically admitted;
- protected benchmark values exist;
- any feature/model is empirically superior;
- any A&M/BAS effect has been established.

## Parent proof
`governance/W18_W17_PARENT_PRESERVATION.csv` provides a row-level proof for all 521 authoritative W17 files, including W17 hash, current W18 hash, size, and unchanged/modified status.

## Rejected W18 pairs
See `governance/W18_CORRECTION_AUDIT.md`. The thin first W18 and first corrected W18 are superseded and invalid as W19 parents.
