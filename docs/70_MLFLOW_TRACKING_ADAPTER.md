# MLflow Tracking Adapter Contract

## Decision
MLflow Tracking is the preferred replaceable adapter for run search, comparison, metadata, and artifacts.

Current official MLflow documentation supports local tracking, SQLAlchemy-compatible databases including SQLite, local artifact storage, and optional tracking-server deployment.

## Canonical mapping
Aggie concept → MLflow concept:
- experiment family → experiment;
- immutable attempt → run;
- canonical experiment ID → tag/parameter;
- data snapshot → logged input/tag;
- model/config → params/artifact;
- development metrics → metrics;
- artifact manifest/result packet → artifact/tag.

MLflow run ID is never the canonical experiment identity.

## Initial local configuration
- SQLite metadata;
- local artifact root outside cumulative repository;
- tracking server optional;
- no production promotion authority.

## Failure fallback
If MLflow is unavailable, canonical JSON/CSV/hash records remain sufficient to preserve experiment governance.

## Later implementation
W19/W20 may implement and pin an adapter version. Any adapter must preserve canonical experiment IDs and must not expose protected metrics to HPO.
