# Wave 06 Architecture Impact

## Decision

**KEEP the W03 offline-first modular-monolith + immutable forecast-snapshot architecture. REVISE the data semantics and future backlog.**

W06 found no evidence that microservices, Kafka, Redis, Kubernetes, an online feature store or an always-on model service are required for Phases 1–4. Source diversity is handled by provider adapters feeding the same immutable/raw→canonical→PIT pipeline.

## Required architectural refinements

1. Add a first-class **source observation / publication version** concept for web reports and mutable pages.
2. Availability observations must preserve conference/policy scope, report version, publication/retrieval time and status semantics.
3. Weather forecast evidence must preserve provider/model/model-version/run initialization/forecast lead/valid time; observed/reanalysis weather remains a separate evidence class.
4. Expand `rule era` into an **effective-dated regulatory environment** covering playing rules plus roster, eligibility, transfer and materially relevant competition-governance changes.
5. Lower-division sources become a bounded official-data lane for opponent strength and transfer translation, not a recursively equal-resolution national platform.
6. Market architecture remains two-lane; PIT-safe paid sources may enrich the market lane but cannot become a dependency of the pure-football model.
7. Derived repositories/APIs must record upstream provenance so overlapping upstreams are not mistaken for independent evidence.

## Future wave changes

- **W07:** add evidence/publication/source-mapping semantics needed for mutable official reports; preserve relational DB as conditional.
- **W08:** formalize report-version, weather model-run and regulatory effective-date temporal joins.
- **W09:** add upstream provenance, license/access metadata and new schemas to source/feature registry.
- **W11:** strengthen lower-division official-stat strength priors.
- **W12:** prioritize official conference availability + A&M/SEC reconstruction; explicitly model noncoverage.
- **W13:** expand regulatory environment and private-resource proxy semantics; keep officiating experimental.
- **W16-W17:** benchmark timestamped market sources only in market-augmented lane.
- **W24:** refresh the W06 source universe, especially availability/rules/weather/vendor status.

No wave is added, removed or renumbered.
