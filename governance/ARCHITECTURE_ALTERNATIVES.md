# Architecture Alternatives — Wave 01 Baseline

These alternatives are preserved for later evidence-based review; Wave 01 does not freeze every Level-B choice.

| Decision area | Current direction | Credible alternatives retained | Why not frozen further in W01 |
|---|---|---|---|
| Statistical specialization | National foundation + A&M specialization | hierarchical multi-task, residual adapter, mixture-of-experts, stacked specialization | W14/W16 must compare with real data |
| Data storage | layered raw/normalized/PIT/features/training/snapshots | DuckDB-centric, PostgreSQL-centric canonical state, hybrid | W02/03/07 must fit local requirements |
| Orchestration | Prefect strong default | lightweight scheduler, another workflow engine | W21 should choose on operational evidence |
| Tabular champion | XGBoost/LightGBM candidates | CatBoost, regularized GLMs, Bayesian/hierarchical models | W16/17 empirical tournament |
| Neural challenger | small PyTorch tabular | FT-Transformer/other tabular NN later | advanced models must earn complexity |
| A&M decomposition | several logical adapters/components | one multi-task specialized model | exact decomposition is not invariant |
| Home-field | partial-pooled residual hierarchy | alternative hierarchical/Bayesian estimators | magnitude/representation must be learned |
| Player availability | scenario/value-over-replacement architecture | joint lineup latent model | W12 experimentation/data coverage decides |
| Market use | separate pure/market lanes | benchmark-only, residual teacher/student research | PIT safety invariant; exact experimental use flexible |
| Frontend | Streamlit candidate | React or another UI | W22 product requirements decide |
| Compute | local-first | temporary cloud burst for Phase5 | core must not require cloud; later experiments may |

# Wave 03 Architecture Challenge

Wave 03 compared architecture alternatives against the protected constraints: local Ryzen/32-GB execution, PIT correctness, immutable evidence, national+A&M specialization, reproducibility, autonomous weekly operation and no-cargo-cult complexity.

The detailed matrix is `ARCHITECTURE_DECISION_MATRIX.csv`.

## Accepted now
- offline-first modular monolith;
- immutable forecast snapshot serving;
- explicit evidence → PIT → feature → model → forecast boundaries;
- native raw + Parquet + DuckDB as early analytical default;
- storage adapter boundary with PostgreSQL conditional rather than mandatory;
- national→A&M specialization interface without freezing statistical family;
- coherent forecast-distribution assembly;
- isolated research plane and protected evaluation/promotion gate;
- LLMs as optional assistive capability;
- isolated future-live plane.

## Retained alternatives
- PostgreSQL for later transactional/concurrent entity or serving metadata workflows;
- hierarchical multi-task, residual, stacked or mixture-of-experts A&M specialization;
- alternative analytical/dataframe engines if benchmarks justify them;
- separate deployable services if later scaling/security/reliability requirements appear;
- online feature serving only if a future live/interactive product genuinely needs it.

## Explicitly not selected for current pregame architecture
- microservice decomposition;
- Kafka/event-bus backbone;
- Redis cache as a required dependency;
- network feature store;
- always-on model inference service;
- mandatory Kubernetes;
- mandatory PostgreSQL server;
- required forecast-time LLM.

These are not universally prohibited technologies. They currently fail the project's complexity-versus-value test.

## W08 temporal alternatives
### Single generic as-of timestamp — REJECTED
Rejected because it cannot correctly represent late-published old-period reports or facts known before their future effective date.

### Current-value backfill for mutable sources — REJECTED
Rejected because later corrections/revisions would rewrite historical knowledge and invalidate replay.

### Store only retrieved_at — NOT ADOPTED AS UNIVERSAL MODEL
Retrieval time is retained as a conservative fallback, but verified publication/provider availability may support earlier first-known timing when evidence exists.

## W24 final challenge notes

The detailed decision set is `docs/architecture/W24_FINAL_ARCHITECTURE_CHALLENGE.md`.

- **KEEP:** offline-first modular monolith, immutable raw/PIT/feature/forecast lineage, national+A&M specialization, separate pure/market lanes, coherent joint-score derivation, protected evaluation, local orchestration, snapshot-only serving.
- **REVISE:** SportsDataverse upstream provenance, target-game-output PIT guard, Open-Meteo access/ensemble semantics, effective-dated 2026 rule population.
- **DEFER:** React/service split, PostgreSQL, advanced neural/graph/live architectures pending actual evidence.
- **REJECT now:** Kubernetes/Kafka/Redis/online feature store/microservice expansion without demonstrated need; shared-upstream double counting; invented performance thresholds.

## W25 final disposition
See `docs/final/FINAL_REJECTED_ALTERNATIVES.md` for the final rejected/deferred set. Deferred options remain evidence-gated and are not silently rejected.
