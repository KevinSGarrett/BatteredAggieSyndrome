# Final Rejected / Deferred Alternatives

## Rejected as current architecture
- Texas A&M-only historical training set.
- Hard-coded "12th Man" home bonus.
- Hard-coded conference/transfer penalties.
- Eventual NFL Draft outcomes as historical pregame features.
- Closing market lines in earlier forecast snapshots.
- Actual observed weather substituted for a historical issued forecast.
- LLM intuition as production feature-selection authority.
- SportsDataverse raw/derived sibling layers counted as independent evidence.
- Research automation allowed to rewrite protected judging rules or self-promote.
- On-request API retraining/PIT reconstruction/feature generation.
- Kubernetes/Kafka/Redis/online feature-store/microservice architecture without demonstrated operational need.

## Deferred / conditional rather than rejected
- PostgreSQL: reopen for real multi-user/concurrent relational workloads.
- Prefect: reopen if workflow observability/retry/scheduling requirements exceed the local kernel.
- MLflow/Optuna: optional adapters after dependency/cost benefit is demonstrated.
- XGBoost/LightGBM/CatBoost: model backends to compare empirically; none is preselected.
- Small PyTorch/temporal/sequence/graph challengers: gated by conventional-baseline saturation and data sufficiency.
- React: only if the static product surface becomes too complex.
- Commercial/licensed enrichment including PFF: optional and rights/cost governed.
- Live/in-game modeling: isolated later research, never allowed to contaminate pregame inputs.
