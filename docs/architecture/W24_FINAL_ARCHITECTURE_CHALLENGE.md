# Wave 24 Final Architecture Challenge

Question: **If the project started today using everything learned through W24, would we make the same major decisions?**

The answer is mostly yes. W24 recommends controlled refinements rather than a broad redesign.

| Decision area | Verdict | W24 rationale |
|---|---|---|
| Broad national foundation + disproportionately deep Texas A&M specialization | **KEEP** | Still best matches the product objective without overfitting the training universe to A&M. |
| Immutable raw → canonical/PIT → features → model/prediction snapshots | **KEEP** | Cross-layer W24 tests validate the dependency boundary and lineage model. |
| Fail-closed point-in-time gateway | **KEEP** | W24 found and repaired an additional target-game-output identity leakage edge case, reinforcing rather than replacing the design. |
| Pure-football vs market-augmented lanes | **KEEP** | Preserves scientific benchmarking and prevents market leakage/identity ambiguity. |
| Joint-score distribution as coherence source for score/margin/win/BAS outputs | **KEEP** | Avoids contradictory isolated outputs; no superior evidence warrants replacement. |
| W17 protected evaluation/promotion rules | **KEEP** | Research/operations must not rewrite judging rules. |
| Local-first modular monolith and dependency-light core | **KEEP** | Current target remains a single Windows workstation/laptop; W23 produced no evidence requiring distributed services. |
| W21 durable standard-library orchestration kernel | **KEEP** | Sufficient functional starter; Prefect remains a replaceable option if W23+ operational evidence justifies it. |
| W22 immutable snapshot-only serving | **KEEP** | Keeps APIs/dashboard out of training/PIT internals and makes historical forecast auditability tractable. |
| SportsDataverse source graph | **REVISE** | Explicitly represent `cfbfastR-cfb-raw` as upstream of `cfbfastR-cfb-data`; never treat the sibling layers as independent corroboration. |
| Open-Meteo weather access/uncertainty lane | **REVISE** | Record non-commercial vs customer access mode; historical/ensemble customer APIs require eligible Professional+ access. Add Ensemble Mean/Spread as optional current/recent uncertainty research, not mandatory long-history training. |
| 2026 NCAA rules/availability semantics | **REVISE** | Populate effective-dated regulatory records for 2026 targeting carryover changes; architecture already supports this. |
| PostgreSQL/Redis/Kafka/Kubernetes/online feature store | **REJECT** | No demonstrated requirement currently earns this complexity. Repository abstractions preserve future migration options. |
| React build pipeline / separate frontend service | **DEFER** | The W22 static dashboard + FastAPI adapter covers present product needs; revisit if UI complexity materially grows. |
| Advanced neural/graph/live model families | **DEFER** | Phase-5 research candidates only after materialized historical baselines and protected empirical evidence exist. |
| Open-Meteo ensemble mean as a required historical training feature | **REJECT** | Historical depth is too shallow for the broad national foundation and feature value remains untested. |
| Treat derived/related source layers as independent evidence | **REJECT** | Shared upstream data would create false corroboration and confidence. |
| Fabricate THR-011/THR-012 to unblock operations | **REJECT** | AC-038 remains unresolved until the declared target hardware is actually benchmarked. |

## User-directed W23 → W24 override

The W23 checkpoint correctly blocked automatic progression because AC-038 lacks target-hardware evidence. The user's explicit W24 instruction overrides **wave sequencing only**. It does not override the evidence standard.

Therefore W24 executes its audit/research/readiness scope while:

- `TASK-161` remains target-hardware blocked;
- `TASK-163` remains blocked by AC-038;
- THR-011 and THR-012 remain TBD;
- Wave 25 must carry the target-hardware item into the final known-gap/readiness register if it is still unresolved.

This is a controlled plan revision, not a declaration that W23 local-production readiness passed.
