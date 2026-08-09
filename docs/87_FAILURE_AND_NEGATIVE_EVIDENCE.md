# Failure Taxonomy, Negative Results, and Inconclusive Experiments

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Why negative evidence matters

Autonomous research becomes wasteful and biased if only successful trials survive. W18 therefore treats negative and inconclusive evidence as first-class searchable lineage.

## Outcome taxonomy

Scientific outcomes include REJECTED, DOMINATED, NO_INCREMENTAL_VALUE, UNSTABLE, SUBGROUP_CONFLICT, CALIBRATION_WORSE, COST_NOT_JUSTIFIED, INCONCLUSIVE, and RETAIN_RESEARCH.

Operational outcomes include DATA_UNAVAILABLE, RIGHTS_BLOCKED, SCHEMA_ERROR, CODE_ERROR, OOM, TIMEOUT, ARTIFACT_FAILURE, REPLAY_FAILURE, and GOVERNANCE_BLOCKED.

## No false inference

An OOM does not mean a model is scientifically bad. Missing historical injury coverage does not prove injuries are irrelevant. Conversely, a successful run does not prove predictive value. Scientific and operational outcomes remain separate.

## Retry rules

An operational retry under identical scientific identity increments attempt. A parameter/model/feature/data change creates a child experiment. Repeated identical failures can trigger stop conditions, but failure history is retained.

## Avoiding dead-end repetition

Before proposing new experiments, research automation can query rejected/failed lineage for exact or near-identical prior configurations. Repeating a rejected hypothesis requires a documented reason such as new data, corrected bug, changed model class, or new evaluation capability.
