# Final Architecture Rationale

## Final shape
The final handoff is a **local-first modular monolith** with immutable source snapshots, canonical identities, a bitemporal/PIT gateway, an empirically governed feature lifecycle, coherent joint-score modeling, disproportionate Texas A&M specialization, scientific BAS targets, protected validation/promotion, durable local weekly orchestration, and immutable snapshot-only product serving.

## What remained stable from the original plan
- Broad national historical foundation + deeper Texas A&M resolution.
- Point-in-time correctness and no future leakage.
- Empirical feature/model promotion instead of intuition-driven adoption.
- Joint score/margin/win/BAS coherence.
- Pure-football and market-augmented lanes.
- Protected chronological validation and immutable judging rules.
- Local hardware as the primary Phases 1-4 execution target.

## What changed and why
1. **Dependency-free core instead of prematurely committing to a large stack.** Early defaults named DuckDB/Polars/PostgreSQL/Prefect/MLflow/Optuna/XGBoost/LightGBM/PyTorch/FastAPI/Streamlit/React. The final starter keeps most of these behind optional/adaptable boundaries until evidence requires them.
2. **Content-addressed local files are the initial persistence implementation.** PostgreSQL remains conditional on real multi-user/concurrency/query pressure rather than architectural fashion.
3. **Durable standard-library orchestration is the canonical W21 starter.** Prefect remains a replaceable candidate if W23+ operational evidence warrants it.
4. **Aggie-owned experiment evidence is canonical.** MLflow and Optuna are adapters/convenience layers, not governance truth.
5. **FastAPI is optional; the dashboard is build-free static HTML/JS.** This preserves one read-only snapshot-serving contract and avoids a second computation path.
6. **SportsDataverse provenance is explicit.** The raw and rectangularized sibling repositories are related upstream/derived evidence, not independent corroboration.
7. **Weather access/run provenance is explicit.** Open-Meteo access lane and ensemble-history limits are represented rather than assumed.
8. **PIT protection was strengthened with target-game identity exclusion.** The predicted game's own output is forbidden even under corrupt temporal metadata.

## Why no broader redesign was made in W25
W24's architecture challenge found no material evidence that microservices, Kubernetes, Kafka, Redis, an online feature store, a graph database, a compulsory neural stack, or cloud-first infrastructure would improve the current single-host objective enough to justify their complexity.

## Final honesty boundary
The architecture and starter implementation are **not a claim of an empirically finished forecasting model**. Real national materialization, protected historical replay, trained model selection, A&M specialization lift, and BAS/Aggie Excess science are implementation work after the wave program.
