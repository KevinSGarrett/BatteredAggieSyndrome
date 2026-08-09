# Wave 18 → Wave 19 Integration Contract

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## What W19 receives

W19 receives a protected research plane ready to consume **real materialized data/entity/feature implementations** without changing the W17 rules. Source adapters and PIT feature factories can now produce immutable snapshots/manifests that become experiment inputs.

## First W19 task

`TASK-041` remains the first ready W19 task: implement approved source-adapter/raw-snapshot starters. W18 does not execute that work early.

## Experiment hooks

W19 source materialization should emit data snapshot IDs, source manifests, schema/coverage reports and entity/PIT lineage that can be bound into experiment specs. Synthetic/reference tests remain available even before full historical coverage is materialized.

## Tournament readiness

Feature/model tournaments remain development-only and may be populated incrementally as W19/W20 artifacts appear. A missing baseline or training matrix blocks an entrant instead of generating fake results.

## Operational boundary

The local experiment store, queue, replay and artifact manifests are development/research infrastructure. W21 later owns weekly MLOps orchestration and final champion/challenger operations.
