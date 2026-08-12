# AI Work Packet — POST-EPIC-009

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Build A&M-specific state and specialization candidates while requiring protected evidence and accepting a global-only/no-adjustment result.

## Why?

The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.

## Aggregate integration and closure scope

All Stories and Subtasks under this Epic for the tamu domain, including its explicit integrated completion gate.

### In scope

- Child implementation and evidence work
- Cross-domain hard dependencies
- Integrated end-to-end gate
- Preservation of source authority and protected controls

### Out of scope

- Declaring child code sufficient without integrated evidence
- Changing protected requirements or ADRs without governance review
- Creating Wave 26

## Current gate state

- Workflow: `BACKLOG`
- Ready: `false`
- Priority: `P1`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `FUNCTIONAL_STARTER` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-087`

## Read first

1. `jira/records/issues/epics/POST-EPIC-009_texas_a_and_m_high_resolution_specialization_and_no_lift_safe_evaluation.json`
2. `jira/sources/issue_source_manifests/POST-EPIC-009.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-EPIC-009`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_tamu_specialization_governance.py
- src/aggie_analytics/tamu/specialization.py
- src/aggie_analytics/tamu/state.py
- docs/40_TEXAS_AM_SPECIALIZATION_ARCHITECTURE.md
- docs/41_TAMU_HIGH_RESOLUTION_STATE.md
- docs/42_TAMU_PEERS_ANALOGS_AND_SNAPSHOTS.md

## Dependencies that must already be complete

- POST-SUBTASK-063
- POST-SUBTASK-069
- POST-SUBTASK-078

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-EPIC-009.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

## Components in scope

- tamu-specialization
- tamu

## What I must not modify or weaken

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_ACCEPTANCE_RULES.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv
- configs/judging_rule_seal.json
- docs/45_SCIENTIFIC_BAS_SPECIFICATION.md

## Exact outputs / integrated artifacts

Review and integrate these child-produced outputs; do not recreate them directly from this aggregate packet:

- artifacts/tamu/tamu_source_manifest.json
- artifacts/tamu/tamu_high_resolution_state_manifest.json
- artifacts/tamu/tamu_state_gate.json
- artifacts/tamu/peer_regime_analog_registry.json
- artifacts/tamu/tamu_specialization_runs.json
- artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json
- artifacts/tamu/tamu_protected_predictions.parquet
- artifacts/tamu/tamu_protected_evaluation.json
- artifacts/tamu/tamu_specialization_decision.json

## Acceptance criteria

1. The unchanged national model remains the mandatory A&M no-adjustment reference; the 39-game 2023-2025 WMT shadow result remains preliminary, small, negative, and insufficient for specialization.
2. No A&M adapter enters forecasts without a larger chronological sample and consistent out-of-sample improvement across seasons, declared metrics, calibration, and stability slices; no adjustment is an acceptable scientific result.
3. Every child issue completes at its declared maturity and evidence state, or has an explicit accepted-risk/deferred disposition.
4. The Epic's end-to-end gate proves the integrated capability on the required real data, target host, protected chronology, or operating path; file existence alone is insufficient.
5. All requirement, acceptance-control, ADR, risk, gap, test, artifact, and source references remain valid and no protected invariant is weakened.

## Tests / validation

- END_TO_END / END_TO_END: POST-SUBTASK-081 — Story gate `POST-SUBTASK-081` must complete with verified evidence before Epic completion.
- END_TO_END / END_TO_END: POST-SUBTASK-084 — Story gate `POST-SUBTASK-084` must complete with verified evidence before Epic completion.
- END_TO_END / END_TO_END: POST-SUBTASK-087 — Story gate `POST-SUBTASK-087` must complete with verified evidence before Epic completion.
- REPRODUCIBILITY / REPRODUCIBILITY: EPIC_EVIDENCE_MANIFEST — Aggregate all Story gates, artifact identities, residual blockers, accepted risks, and downstream readiness.

## Evidence to return

- Verified Story gate decisions for POST-SUBTASK-081, POST-SUBTASK-084, POST-SUBTASK-087.
- Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.
- A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities.

## End-to-end handoff

Exercise all child Story gates for Texas A&M high-resolution specialization and no-lift-safe evaluation and prove the integrated capability is safe and consumable by its downstream Epic/release path.

## Stop instead of improvising when

- Stop before execution if any hard dependency, protected gate, source-rights decision, or target-resource precondition is unresolved.

## Completion protocol

1. Verify every required child issue is complete at its claimed maturity with verified evidence; do not infer completion from file or code existence.
2. Run or review the declared integrated end-to-end gate and downstream-consumption proof.
3. Create the aggregate evidence manifest with pinned source/data/code/config/model/runtime identities, residual blockers, accepted risks, null/negative results, and gate decisions.
4. Keep this Epic/Story non-READY and non-executable; route any implementation change to a specific atomic Subtask or create a controlled backlog proposal.
5. Update canonical/local Jira state and live Jira operational fields according to `jira/SYNC_CONTRACT.md` only after the aggregate gate is truthfully satisfied.
6. Rebuild all derivatives with `python -B jira/tools/rebuild_all_derivatives.py`, recompute queues, and run `python -B jira/tools/validate_second_pass.py`.
7. Reevaluate downstream gates without weakening protected requirements or hiding incomplete child evidence.
