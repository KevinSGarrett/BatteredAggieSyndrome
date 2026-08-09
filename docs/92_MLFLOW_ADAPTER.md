# MLflow Tracking Adapter — Detailed Integration

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Role

MLflow is a convenience tracking/search/UI adapter, not the source of governance truth. Canonical Aggie experiment IDs, queue states, W17 seals, acceptance controls and promotion decisions live in the Aggie contracts.

## Local deployment

The default local pattern uses a SQLite backend and local artifact directory when MLflow is installed. No always-on server is required for the baseline workflow. A future server can be introduced if concurrent users/automation justify it.

## Mapping

Aggie experiment ID maps to an MLflow tag. Parent experiment, hypothesis, data snapshot, feature set, target, lane, W17 seal, code state and development split are also tags/params where reasonable. Large configs remain canonical files/manifests and may be referenced by hash rather than flattened into hundreds of parameters.

## Artifacts

MLflow artifact storage does not override repository exclusion/rights rules. Model binaries/training matrices stay outside cumulative ZIP. Sensitive/restricted content must respect artifact policy.

## Registry boundary

An MLflow Model Registry state cannot independently make a model the Aggie production champion. Final champion state remains governed by the W17/W21 promotion interface.

## Fallback

If MLflow is unavailable, the local JSONL tracker and SQLite ExperimentStore preserve the canonical workflow. This prevents tool availability from blocking governance.
