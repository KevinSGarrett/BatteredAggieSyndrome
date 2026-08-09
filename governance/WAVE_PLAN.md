# 25-Wave Plan — Current Accepted Baseline

Plan revision: `w24-plan-r1`. Exactly 25 waves. Missions remain minimum centers of gravity; Level-B details remain evidence-revisable.

- **W01:** Source synthesis + reconnaissance ingestion — **COMPLETE**
- **W02:** Repository, local environment, GitHub & Codex operating structure — **COMPLETE**
- **W03:** Full logical/system architecture — **COMPLETE**
- **W04:** Requirements hardening, ADR framework & acceptance architecture — **COMPLETE**
- **W05:** Five-phase implementation master plan & Codex backlog — **COMPLETE**
- **W06:** Comprehensive data-universe research & source audit — **COMPLETE**
- **W07:** Canonical entities, IDs, source mappings & entity resolution — **COMPLETE**
- **W08:** Point-in-time data architecture — **COMPLETE**
- **W09:** Raw feature registry & schema-discovery system — **COMPLETE**
- **W10:** Feature engineering, screening & lifecycle system — **COMPLETE**
- **W11:** Historical weighting, team state & early-season intelligence — **COMPLETE**
- **W12:** Player, roster, depth, availability & transfer intelligence — **COMPLETE**
- **W13:** Football context, coaching & game-mechanics intelligence — **COMPLETE**
- **W14:** Texas A&M specialization architecture — **COMPLETE**
- **W15:** Scientific BAS specification — **COMPLETE**
- **W16:** Model targets, architecture, joint score & simulation — **COMPLETE**
- **W17:** Validation, benchmarking & model-promotion science — **COMPLETE**
- **W18:** Experimentation & autonomous research full reference implementation — **COMPLETE**
- **W19:** Starter data/entity/feature implementation — **COMPLETE**
- **W20:** Starter model/calibration/BAS implementation — **COMPLETE**
- **W21:** Autonomous weekly MLOps starter — **COMPLETE**
- **W22:** API, dashboard, explainability & forecast product — **COMPLETE**
- **W23:** CI/CD, security, observability & local operations — **IMPLEMENTATION COMPLETE / TARGET-HARDWARE GATE CARRIED**
- **W24:** End-to-end readiness + source refresh + architecture challenge — **COMPLETE WITH CARRIED W23 CONDITION**
- **W25:** Final consolidation & Codex handoff — **COMPLETE — TERMINAL NUMBERED WAVE**


## W07 impact
No wave was added, removed or renumbered.

- W08 inherits the frozen source-system/resource/publication-version/raw-capture/source-observation identity hierarchy and must define exact PIT/known-at/effective-date semantics.
- W09 inherits source-scoped entity mappings and upstream provenance.
- W12 uses one canonical player identity across transfer/roster episodes.
- W13 uses one canonical coach identity across role episodes and keeps weak officiating identities unresolved/experimental.
- W19 implements/materializes the W07 entity contracts, creates labeled resolver fixtures, benchmarks storage at real data volume, and may revisit `THR-008`/PostgreSQL only with evidence.
- W22 may reopen relational persistence if a real multi-user review/service workflow exists.


## W08 impact
No wave was added, removed or renumbered.

- W09 must carry W08 temporal classes/lineage into raw-field registry metadata.
- W10 transformations may only operate on PIT-safe inputs from the W08 gateway.
- W12 availability materialization uses W08 policy/version/noncoverage semantics.
- W13 weather/regulatory/resource systems use W08 dual-time contracts.
- W16-W17 training/walk-forward evaluation uses both per-example pregame cutoffs and model-training cutoffs.
- W19 materialization must convert synthetic PIT controls into real source-contract/integration evidence.
- W24 must rerun historical leakage/source timing challenges against actual data.


## W09 impact
No wave was added, removed or renumbered.

- W10 must consume the W09 handoff states and may not treat registry membership as production-feature approval.
- W10 transformations remain behind W08 PIT eligibility and must preserve W09 raw-field/source lineage.
- W19 materialization must run the W09 scanner against real source snapshots, profile population missingness, and record schema drift.
- W24 source refresh must compare current schemas/access/rights with W06/W09 registry assumptions.


## W10 impact
No wave was added, removed or renumbered.

- W11 consumes W10 transforms/lifecycle rules but must not treat candidate seeds as production-approved.
- W14/W17 evaluate A&M-specific and target-specific incremental feature value.
- W17 owns protected walk-forward feature promotion evidence and any justified value for `THR-007`.
- W19 materialization supplies population missingness/schema/real transform evidence.
- W24 source refresh must reassess lifecycle decisions affected by source/schema/rule drift.

## W11 impact
No wave was added, removed or renumbered.

- W12 inherits underlying-vs-available strength and uncertainty interfaces; player-specific availability/replacement construction remains W12-owned.
- W13 supplies effective-dated coaching/scheme/resource/regulatory continuity inputs into W11 prior/regime interfaces.
- W14 may specialize A&M historical relevance but cannot discard the national historical foundation.
- W17 selects weighting/blend/change-point candidates only through protected chronology.
- W19 materializes/calibrates lower-division translation and real team-state evidence.


## W12 impact
No wave was added, removed or renumbered.

- W13 consumes the frozen W12 player/availability/replacement interface for coaching/context/mechanics without altering W08 PIT semantics.
- W14 may deepen A&M player/depth/availability resolution while preserving national canonical player identity.
- W16 may integrate scenario-weighted player/availability evidence into coherent score/uncertainty modeling, but W12 provides no point conversion.
- W17 owns protected empirical comparison of player-value, availability-impact, transfer translation, preseason-honor and draft-development candidates.
- W19 owns real historical roster/depth/availability/transfer/recruiting materialization and coverage measurement, including official SEC availability reports.
- W24 rechecks transfer/recruiting/availability source access and rights against the W06/W12 baseline.


## W13 impact
No wave was added, removed or renumbered.

- W14 consumes frozen W12/W13 player/staff/context/mechanics interfaces and may deepen A&M evidence without forking canonical identities.
- W14 specialization architecture is no longer blocked by future W20 implementation task `TASK-087`; `TASK-088` now depends on contract gates through W13.
- W17 owns protected empirical selection of coach, home-field, resources, score-state, opponent-adjustment, style and officiating candidates.
- W19/W20 own real materialization/implementation evidence for coaching/context/mechanics.
- W24 refreshes officiating/source/regulatory availability where needed.

## W14 impact
No wave was added, removed or renumbered.
- W15 consumes the frozen A&M state/specialization contract while defining BAS labels independently and leakage-safely.
- W16/W17 compare specialization candidates against mandatory no-adjustment baseline.
- THR-005 remains unset until protected W17 evidence.
- W19/W20 own materialized high-resolution A&M state and starter specialization implementation.

## W15 impact
No wave was added, removed or renumbered.
- W16 consumes fixed BAS outcome semantics but still owns model-family/joint-score architecture.
- TASK-101 and TASK-116 no longer depend on future W17 TASK-040; W17 retains empirical baseline/promotion authority.
- W17 owns protected Aggie Excess/significance/stability/calibration evaluation and `THR-006` precommitment.
- W18+ owns chronological live Collapse BAS research.
- W20 owns starter BAS implementation after W17 scientific decisions where required.


## W16 completion note
W16 contract gate is complete. Model/joint-score families remain unselected. W17 is next and begins with protected validation protocol, not fabricated benchmark results.


## W17 completion note
W17 protocol gate is complete. The project now has a sealed 2024-2025 governance-protected holdout, 2026+ forward shadow lane, metric/scorecard registry, threshold-precommitment methodology and fail-closed promotion decision contract. Numerical model-science thresholds remain blank until development-only materialized evidence exists. W18 is next; W18 research automation cannot mutate W17 judging rules.


## Corrected W18 completion note
Corrected W18 revision `0.18.1-w18` supersedes the thin first draft. The research-governance gate now includes first-class feature/model tournaments, hypothesis lifecycle, versioned HPO search spaces/studies, artifact manifests, replay-failure/adoption policy, worktree/resource policy, MLflow/Optuna adapter contracts, and master-requirement coverage validation. W17 judging files remain hash-sealed; research cannot self-promote; no protected/trained winner is claimed. W19 is next and begins with TASK-041.

## W18 full-rebuild impact
No wave was added, removed or renumbered.

- W19 inherits executable experiment identity/store/queue/resource/artifact/replay contracts, but still owns real data/entity/feature materialization.
- W20 may run real model/HPO/tournament experiments only after W19 supplies compatible materialized inputs and conventional baselines.
- W21 retains production champion/challenger orchestration and promotion authority; W18 cannot self-promote.
- W23 may replace local metadata/tracking/HPO backends only if measured concurrency/operations justify the added complexity.
- W24 must audit negative-result/search history and source/tool drift in addition to refreshing the data-source landscape.

## W19 completion impact
W19 implemented the source→immutable snapshot→entity→PIT→feature starter chain and preserved fail-closed lineage. Full national historical materialization, population missingness, calibrated fuzzy matching and empirical feature selection remain later implementation/data work; no architecture reallocation is required. W20 is next.


## W20 completion impact
No wave was added, removed or renumbered.

- W20 repaired the inherited TASK-083..087 dependency gap by pulling the advanced-state starter evidence forward rather than falsely clearing TASK-087.
- W21 consumes the W19 PIT/feature lineage and W20 model/artifact/calibration/registry boundaries.
- W20 selected no empirical model, boosting backend, A&M adjustment or BAS effect winner.
- W17 protected evaluation/promotion authority remains unchanged.
- W23 may revisit optional model/runtime dependencies only if measured operational evidence justifies them.


## W22 completion impact
No wave was added, removed or renumbered.
- W22 froze and implemented a versioned, read-only immutable snapshot-serving contract.
- FastAPI is an optional adapter; the canonical serving core remains framework-neutral and dependency-free.
- A build-free static A&M dashboard renders forecast/BAS/uncertainty/availability/matchup/analog/lineage evidence from published artifacts only.
- THR-010 remains TBD_BY_OPERATIONS; stale semantics are implemented without inventing a production SLA.
- TASK-158 is READY and W23 owns CI/security/observability/benchmark/backup hardening.


## W23 execution state
- TASK-158/159/160/162: DONE.
- TASK-161: BLOCKED_TARGET_HARDWARE.
- TASK-163: BLOCKED_AC038_TARGET_HARDWARE.
- THR-011/THR-012 remain TBD_BY_TARGET_BENCHMARK.
- The user explicitly authorized W24 sequencing without clearing this evidence gate.

## W24 completion impact
No wave was added, removed or renumbered.

- W24 completed TASK-173..178 and TASK-199 under ADR-341's explicit user-directed sequencing override.
- Synthetic E2E/replay readiness uses the actual W19-W22 starter boundaries; empirical historical replay remains unclaimed.
- The leakage audit added an explicit target-game identity hard stop for `HISTORICAL_GAME_OUTPUT`.
- Current source refresh refined SportsDataverse upstream provenance and Open-Meteo access/ensemble semantics without replacing the core architecture.
- The final architecture challenge overwhelmingly KEEPs the modular-monolith, immutable/PIT, joint-score, protected-evaluation and snapshot-serving boundaries; only evidence-backed refinements were adopted.
- W25 begins with TASK-179 and must expose AC-038/TASK-161/TASK-163/THR-011/THR-012 as unresolved if target evidence is still absent.


## W25 final impact
- Exactly 25 waves are complete. No Wave 26 exists.
- Post-wave work is `CODEX_IMPLEMENTATION_HANDOFF`.
- TASK-161/TASK-163/AC-038/THR-011/THR-012 remain unresolved pending target-machine evidence.
- TASK-165..168 remain conditional advanced-challenger backlog; TASK-169..172 remain deferred live-model backlog.
- Final implementation order is in `docs/final/FINAL_IMPLEMENTATION_PRIORITY.md`.
