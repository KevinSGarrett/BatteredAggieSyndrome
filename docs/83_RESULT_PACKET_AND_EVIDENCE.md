# Experiment Result Packet and Evidence Contract

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Separation from spec

The immutable experiment spec describes what was intended. The result packet describes what happened. Combining the two would make identity dependent on outcome.

## Result contents

A result packet includes experiment ID, attempt, execution status, development metrics, scorecard slices allowed to the research plane, data/feature/model lineage hashes, environment and runtime record, artifact manifest hash, warnings, failure taxonomy, and declared nondeterminism.

Protected holdout metrics and 2026+ forward-shadow metrics are intentionally absent from the research-plane result packet.

## Metrics

Metrics include registry IDs and directions rather than anonymous scalar names. A result is not directly comparable to another result unless target, split, data snapshot, feature version, metric registry, lane, and relevant BAS/A&M semantics are compatible.

## Warnings

Warnings capture sparse subgroup size, missing source coverage, OOD rate, calibration instability, schema drift, resource exhaustion, nondeterminism, degraded-mode inputs, or rights restrictions. Warnings remain evidence and cannot be deleted simply because the candidate otherwise ranks well.

## Protected handoff

A separate promotion-review packet can reference the research result and W17 judging seal. The research plane only requests review; it cannot insert a final champion state into its result packet.
