# Project Identity and Terminal W25 Handoff

## 1. Product identity

The repository builds the **Aggie Analytics Engine**, a national college-football forecasting system with disproportionate Texas A&M resolution and a scientifically testable **Battered Aggie Syndrome (BAS)** layer.

The predictive system is the core product. BAS is the memorable, witty project identity, but its headline quantity is not a joke metric and is not equivalent to loss probability. The accepted headline is the probability that Texas A&M performs at least seven points worse than a strictly valid pregame expected margin, with additional severity thresholds. The effect must be estimated without circular labels, future leakage, or an assumption that an Aggie-specific effect exists.

## 2. Terminal program state

The exactly-25-wave architecture/planning program is complete. W25 created the final consolidation and Codex handoff. Post-W25 work is implementation against the accepted handoff. The autonomous agent must never create Wave 26, Wave 27, or revive the one-wave-per-turn generation process unless the user explicitly changes the program structure.

Canonical terminal sources:

- `docs/113_W25_FINAL_CONSOLIDATION_AND_CODEX_HANDOFF.md`
- `docs/final/CODEX_HANDOFF.md`
- `docs/final/FINAL_BACKLOG.csv`
- `docs/final/FINAL_COMPONENT_MATURITY.csv`
- `docs/final/FINAL_KNOWN_GAPS.md`
- `docs/final/FINAL_IMPLEMENTATION_PRIORITY.md`
- `docs/final/FIRST_72_HOUR_IMPLEMENTATION_QUEUE.md`
- `governance/CURRENT_STATE.yaml`
- `governance/CURRENT_BACKLOG.yaml`

## 3. What is mature and what is not

### Implemented/validated control surfaces

- requirements, ADR, risk, acceptance, dependency, source-of-truth, and packaging governance;
- protected evaluation and judging-rule seals;
- deterministic repository validation and synthetic/reference test boundaries;
- functional interfaces across acquisition, raw snapshots, entities, PIT, features, models, BAS, MLOps, product, and operations.

### Functional starters awaiting real evidence

- source adapters and immutable raw snapshots;
- canonical identity and entity resolution;
- PIT state and replay inputs;
- feature registry/lifecycle and screening;
- model, calibration, uncertainty, simulation, and BAS runtime boundaries;
- weekly orchestration and immutable forecast publication;
- product API/dashboard and local operations.

### Explicit unresolved gaps

- AC-038 target-hardware benchmark; THR-011 and THR-012 remain TBD;
- source credentials, access, licensing, rights, and redistribution review;
- real national historical data materialization and population profiling;
- real canonical entity and PIT replay validation;
- production feature set and champion model;
- protected chronological performance/calibration results;
- Texas A&M specialization lift;
- BAS/Aggie Excess validity and stability;
- forecast freshness SLA and target-host operational evidence;
- advanced neural/sequence/graph challengers and live modeling, which remain conditional/deferred.

Never convert a functional starter or a historical governance `DONE` row into a production-readiness claim without empirical evidence.

## 4. Critical interpretation of repository registries

The repository contains 201 implementation-WBS rows, 745 requirements, 349 ADRs, 234 acceptance controls, 33 epics, and 323 dependency edges. Many WBS rows have historical statuses such as `DONE` because their wave produced the planned contract, governance artifact, reference implementation, or validation evidence. Those statuses do **not** automatically mean the real-data production capability is complete.

Use three separate state layers:

1. **Historical WBS state** — what the wave program produced.
2. **Terminal handoff state** — what real implementation/evidence remains, from `FINAL_BACKLOG.csv`, final maturity, gaps, and priorities.
3. **Live execution state** — current assignment, status, blockers, and integration state in Jira BAT after hydration.

The generated `jira/internal_task_catalog.jsonl` joins the historical task graph to requirements, acceptance controls, indirect ADR relationships, outputs, and work packets while preserving this distinction.

## 5. Accepted scientific and architectural invariants

- broad national historical learning with deep Texas A&M specialization;
- point-in-time reconstruction and explicit known-at semantics;
- target-game outcome exclusion from all pregame features;
- immutable source and forecast snapshots with provenance;
- canonical stable identities and controlled unresolved states;
- absence of evidence is not automatically negative evidence;
- feature/model/specialization/BAS promotion is empirical;
- protected evaluation is not iterative tuning feedback;
- simple baselines precede advanced challengers;
- null A&M specialization or BAS/Aggie Excess findings are valid;
- no fabricated performance, lift, effect, source payload, benchmark, or maturity claim;
- resource and target-hardware limits are measured, not invented.

Use the protected canonical files referenced by [14_DATA_ML_PIT_PROVENANCE_AND_EVALUATION.md](14_DATA_ML_PIT_PROVENANCE_AND_EVALUATION.md), rather than copying or casually rewriting their detailed rules.

## 6. Terminal implementation order

### P0 — Make empirical work possible

Target-host evidence; credentials/access/rights; immutable national history; canonical entities; PIT state; leakage/replay validation.

### P1 — Establish defensible forecasting

Simple Elo/logistic/score baselines; chronological evaluation; calibration; sealed champion/challenger promotion; A&M specialization against a no-adjustment reference; leakage-safe BAS science with null acceptance.

### P2 — Operate the product

Weekly real-data pipeline; immutable forecast serving; freshness; observability; backup/restore; security; drift monitoring.

### P3 — Complexity must earn admission

Neural, sequence, graph, live/in-game, distributed, or heavier infrastructure only after data sufficiency, baseline saturation, resource, and promotion gates pass.

## 7. Current known selection boundary

`HANDOFF-001` is P0 but blocked on representative target hardware. `HANDOFF-002` is the independent Ready P0 lane in the terminal backlog, subject to real credentials, access, licensing, and source-rights boundaries. This is a fallback from repository evidence, not a substitute for live Jira state. After Jira hydration, active assignments and dependencies may change the selected issue.
