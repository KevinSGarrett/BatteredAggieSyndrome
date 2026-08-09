# Adaptive Architecture Context — through W06

W06 **kept** W03's offline-first modular-monolith and immutable snapshot-serving architecture. Source research did not justify microservices/Kafka/Redis/Kubernetes/online feature-store complexity.

W06 **revised** data contracts: source publication/version observations, weather model-run provenance, policy-aware availability and an effective-dated regulatory environment. Future waves may replace source adapters/providers through ADRs without changing the protected canonical/PIT boundaries.

## W08 architecture impact
W08 does not replace the W03 modular-monolith/snapshot-serving architecture. It hardens CMP-005 `pit_state` into the protected bitemporal gateway feeding CMP-006 feature construction. No online feature store, database server or microservice was introduced.


## W16
The modular-monolith/snapshot architecture remains appropriate. W16 improves the statistical/output contract rather than adding online services: coherent joint score derivation, scenario interfaces and explicit pure/market lanes. No distributed-system change is justified.

## W17
W17 converts validation science into a sealed, versioned protocol: 2024-2025 protected holdout, 2026+ forward shadow, predeclared metrics/scorecards, development-only threshold derivation and fail-closed promotion. This is protocol architecture, not trained empirical performance.


W22 implements the snapshot-serving plane as a dependency-free read-only product service with an optional FastAPI/static-dashboard adapter. Streamlit/React and PostgreSQL remain replaceable/conditional rather than mandatory. THR-010 remains operationally TBD.


## W24 architecture challenge
The final pre-consolidation challenge KEEPs the local-first modular monolith, immutable raw snapshots, protected PIT gateway, coherent joint-score outputs, protected W17 evaluation boundary, W21 durable local orchestration and W22 immutable snapshot-only serving. W24 REVISES only evidence-backed provenance/temporal details: an explicit target-game output hard stop, SportsDataverse raw→derived provenance, and Open-Meteo access/ensemble semantics. Distributed infrastructure, a mandatory relational service, React build tooling, and advanced neural/graph/live systems remain deferred/rejected until evidence creates a real need.
