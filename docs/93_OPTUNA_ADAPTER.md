# Optuna HPO Adapter — Detailed Integration

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Role

Optuna is the preferred replaceable HPO execution adapter. Canonical study/search-space identity remains in Aggie schemas so studies are portable and auditable.

## Storage

For local work, journal/persistent storage is preferred when parallel workers need a durable shared study without standing up a database service. SQLite is not used for multi-host/NFS-style coordination. Future RDB-backed distributed optimization is allowed only when operational need exists.

## Study mapping

Study name includes canonical study ID. User attributes carry experiment family, data/feature versions, development split, objective registry, W17 seal, search-space version and resource budget. Trial parameters/values remain Optuna-native but are exported into canonical result/evidence packets.

## Sampler/pruner

Sampler/pruner names, versions, seeds/configuration and pruning objective are lineage. Changing them creates a new study version or explicit child study.

## Objectives

Only development metrics may be returned to Optuna. Protected holdout/forward-shadow metrics are not exposed to the objective callback, pruning callback or study dashboard used for selection.

## Fallback

The dependency-free reference enumerator in `hpo_engine.py` is used for governance tests and tiny deterministic grids. It does not claim to replace Optuna for real optimization.
