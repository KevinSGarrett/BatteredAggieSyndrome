# Wave Plan Revisions

## w01-plan-r1 — Wave 01

No numbered-wave mission was materially reallocated in Wave 01. The full 25-wave sequence remains intact.

Execution hardening added:
- source-chat ingestion is explicitly numeric 001→020 rather than archive order;
- artifact identity is content/version/hash based rather than host filename exact-match;
- authoritative reconnaissance integrity uses the final manifest/hash set; the root self-referential `PACK_MANIFEST.csv` discrepancy is non-blocking and documented;
- source contradictions are preserved through a supersession ledger;
- Level-C ideas are tracked in a hypothesis ledger rather than silently promoted to requirements.

Wave 06 retains the mandate to perform fresh comprehensive data-universe research and may revise Waves 07–25 while preserving exactly 25 waves.

## w02-plan-r1 — Wave 02

No numbered wave mission was reallocated.

Execution refinement:
- W02 establishes only the operational repository/src scaffold; W03 retains responsibility for logical/service/domain boundaries.
- W02 creates minimal Windows/Linux repository CI so W23 can focus on production-grade CI/CD/security/observability rather than first principles.
- Prior-wave verification and cumulative/hydration packaging are now executable deterministic tools and are expected to be reused every remaining wave.
- Docker/database/orchestration commitments remain deferred until the wave where requirements justify them.

## w03-plan-r1 — Wave 03

No numbered wave mission was reallocated.

Architecture refinements affecting later work:
- W07 should implement canonical/entity persistence behind the W03 storage boundary and determine whether a PostgreSQL adapter is justified; PostgreSQL is no longer an assumed mandatory local service.
- W08 owns detailed PIT internals but must preserve the W03 hard PIT gateway.
- W14/W16 may choose residual, multi-task, mixture-of-experts or another A&M statistical implementation without changing the W03 national→A&M semantic interface.
- W18 research must remain isolated from protected evaluation/promotion state.
- W21 chooses orchestration technology against the accepted batch/forecast-refresh lanes; Prefect remains a candidate rather than a W03 dependency.
- W22 product surfaces should consume immutable forecast snapshots.
- W23 may introduce service/deployment infrastructure only when operational evidence justifies it.
- Future live/in-game work remains a separate lane and may not destabilize the pregame feature path.

## w04-plan-r1 — Wave 04

No numbered wave mission was reallocated.

Acceptance/governance refinements affecting later work:
- W05 must decompose implementation work against acceptance-control IDs and owning waves, not only prose requirements.
- W06/W07-W09 must populate source/domain rights, contract, data-quality and entity/PIT acceptance evidence without inventing universal thresholds.
- W17 owns protected statistical promotion thresholds and the protected-test seal implementation.
- W19-W23 own target-hardware runtime/RAM/storage benchmark thresholds.
- Every later material ADR must update affected acceptance mappings in the same controlled change.
- Future controls remain defined/pending until evidence exists; W04 does not pre-mark later implementations PASS.


## W05 — implementation planning refinement
- No wave renumbering/reallocation.
- W06 is now an explicit backlog replan gate.
- W07-W25 source/schema-dependent tasks are provisional until W06 revalidation.
- Five capability phases are organizational and do not alter wave authority.

## W06 — data-universe research and backlog replan

No wave was added, removed or renumbered.

Evidence-driven refinements:
- W07 adds source publication/report-version evidence semantics.
- W08 adds availability-report policy/version and weather model-run PIT semantics.
- W09 adds explicit upstream provenance/access/license fields.
- W11 strengthens NCAA/NAIA/NJCAA bounded lower-division priors.
- W12 prioritizes official conference availability and A&M SEC report reconstruction while preserving missing/noncoverage uncertainty.
- W13 expands rule era to regulatory environment and preserves private-resource proxy semantics; officiating remains experimental.
- W16-W17 may evaluate timestamped paid market data in the market lane without making it a pure-football dependency.
- W24 refreshes official availability/weather/rule/vendor source status against the W06 baseline.

The W05 W06_REPLAN gate is **CLEARED_W06**. Source-dependent future tasks are revalidated; TASK-007 is the first READY W07 task.


## W07 — canonical identity refinement

No wave was added, removed or renumbered.

Evidence/design-driven refinements:
- W08 now consumes a frozen five-layer evidence identity hierarchy before assigning temporal eligibility.
- W19 must materialize/benchmark entity resolution and produce labeled review fixtures before `THR-008` can be set.
- PostgreSQL remains optional; W19/W22 reopen only if actual concurrency/transaction needs or measured performance justify it.
- Identity corrections are append-only merge/split/supersession events so W08+ replay remains reproducible.

## W08 — temporal-contract propagation
No wave mission changed. Later-wave detail was refined: W09 carries temporal metadata, W12 official availability uses report-policy/version semantics, W13 uses issued weather runs + regulatory dual time, W16-W17 enforce model-training cutoffs, and W19/W24 own real-data PIT replay evidence.

## W09 — raw-feature/schema registry refinement
No wave renumbering. W10 inherits explicit raw-field handoff states; W19 owns real-source population profiling/schema drift evidence; W24 revalidates source schemas/rights.

## W11 — team-state interface refinement

No wave was added, removed or renumbered.

- W12 inherits explicit `underlying_strength` versus `available_strength` semantics and must populate player/availability/replacement evidence without changing historical weighting rules.
- W13 supplies coaching/scheme/resource/regulatory continuity inputs into the W11 regime/prior interfaces.
- W14 may add A&M-specific relevance/adaptation but may not replace the national-history utility role.
- W16 consumes strength/uncertainty interfaces but remains free to choose the final statistical model family.
- W17 owns protected chronological selection of recency/blend/change-point/team-state alternatives.
- W19 materializes real cross-division history, population state evidence and parameter benchmarks.


## W12 revision — w12-plan-r1
- No wave count/numbering change.
- W13 now consumes a frozen player/availability/replacement interface.
- W14 may deepen A&M player/depth resolution without forking canonical identity.
- W17 owns empirical player-value/availability/transfer/honor/draft candidate selection.
- W19 owns real historical roster/depth/availability/transfer/recruiting materialization, official availability report acquisition and coverage measurement.
- W24 rechecks current availability/recruiting/transfer source access/rights.
- TASK-197 was completed as an explicit W12 catch-up so TASK-200 could execute without waiving its dependency.


## W13 revision — w13-plan-r1
- No wave count/numbering change.
- W14 TASK-088 dependency repaired from future W20 TASK-087 to frozen W12/W13 contract gates.
- W17 remains empirical owner for coach/home/resource/score-state/opponent/style/officiating selection.
- W19/W20 remain materialization/implementation owners.
- Officiating remains fail-closed experimental unless pregame assignment coverage is demonstrated.
## W14 impact
No wave was added, removed or renumbered.
- W15 receives a frozen A&M state/specialization candidate contract but must define BAS scientifically without treating specialization as ground truth.
- W16 integrates specialization signals into coherent joint-score/model architecture and may compare residual/hierarchical/partial-pooling/calibration/stacked candidates.
- W17 owns protected A&M incremental-value selection and any justified value for `THR-005`.
- W19/W20 materialize high-resolution A&M state and starter adapters; missing A&M historical detail must remain explicit.
- W22 may select operational A&M forecast cadence using actual product/update evidence.

## W15 — BAS contract and dependency repair
- W15 mission remains unchanged; TASK-100..108 complete contract/reference scope.
- TASK-101 no longer depends on future W17 TASK-040; it depends on W15 BAS definition + completed W08 PIT gate.
- TASK-116 no longer depends on future W17 TASK-040; W16 model-target design may proceed after W14/W15 contract gates.
- W17 retains protected baseline benchmarking, BAS significance/stability/calibration and component promotion decisions.


## W16 revision
W17 protected-evaluation task semantics are clarified as protocol/precommitment work until real data/model artifacts exist. TASK-128 is the recommended W17 entry point so protected splits precede any protected evidence inspection. Stable task IDs are preserved.


## W17 revision — w17-plan-r1
- No wave count/numbering change.
- Freeze 2024-2025 as governance-protected holdout and 2026+ as forecast-first shadow evidence.
- TASK-131 is clarified as threshold-method precommitment; numeric values remain pending development-only evidence.
- W18 inherits immutable W17 split/metric/threshold-method/promotion rules.
- W19/W20 materialized data/model work may populate development evidence, but protected holdout results may not tune thresholds.


## w21-plan-r1 — Wave 21

No wave count, numbering or core future mission changed.

- W21 selected a dependency-free durable local orchestration starter instead of making Prefect mandatory.
- W22 must serve immutable W21 publication artifacts and must not perform model training/protected evaluation in request paths.
- W23 retains authority to revisit orchestration backend choice if measured operational needs justify Prefect or another framework.


## W22 impact
No wave was added, removed or renumbered.
- W23 hardens the optional FastAPI/product dependency path, CI/security/observability, runtime benchmarks and backup/restore around immutable snapshot serving.
- THR-010 remains TBD until W23 operational evidence; W22 does not manufacture a freshness SLA.
- React/Streamlit remain optional product/analyst adapters; no frontend build pipeline is required yet.
- PostgreSQL remains conditional behind the repository boundary; current W22 reads do not justify it.


## W23 impact — w23-plan-r1
No wave was added, removed or renumbered. W23 implementation hardening proceeds as planned, but the release-blocking local production gate cannot be cleared without AC-038 evidence from the declared target machine. W24 remains dependency-blocked by TASK-163.

## W24 impact — w24-plan-r1
No wave was added, removed or renumbered.

- The user's explicit instruction to execute W24 supersedes the W23 sequencing guard only. TASK-173 now depends on completed W23 implementation substrate TASK-162 rather than blocked release gate TASK-163.
- TASK-161/TASK-163, AC-038 and THR-011/THR-012 remain unresolved; W25 must carry them if no target benchmark is supplied.
- W24 adds a cross-layer synthetic E2E/replay-readiness battery and a target-game-output identity leakage guard.
- W24 source refresh refines SportsDataverse raw→derived provenance and Open-Meteo access/ensemble uncertainty semantics without changing the core source architecture.
- W25 remains the final consolidation wave; TASK-179 is READY after the W24 scope gate.

## W25 terminal revision
- Exactly 25 numbered waves are complete. No Wave 26 is permitted.
- Post-wave work is implementation against the final handoff.
- Optional advanced/live tasks remain evidence-gated backlog.
- AC-038 remains a target-hardware validation condition, not a reason to fabricate closure.
