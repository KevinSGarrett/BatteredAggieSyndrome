# Product Context — W22

- Serving mode: immutable published forecast snapshots only.
- API: versioned read-only v1 contract.
- Market lanes: PURE_FOOTBALL and MARKET_AUGMENTED remain explicit/separate.
- Dashboard: build-free static HTML/JS over the same API.
- Framework: dependency-free core; optional FastAPI adapter.
- Freshness: exact cutoff/published/serve times; THR-010 still TBD_BY_OPERATIONS; no false CURRENT label.
- Explanations: precomputed associational/model evidence only, not causal claims and no request-time model/SHAP execution.
- Lineage: model artifact hash + feature snapshot + data/source refs.
- W23 owns CI/security/observability/runtime/restore hardening.
