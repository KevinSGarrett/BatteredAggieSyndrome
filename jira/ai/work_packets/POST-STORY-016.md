# AI Work Packet — POST-STORY-016

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Reconstruct what was known for each game/cutoff and materialize row-level model inputs with complete lineage.

## Why?

This coherent capability closes a defined portion of Point-in-time historical state and protected replay and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-016 (Append-only as-of state and pregame matrices) as one coherent, gated capability inside Epic POST-EPIC-005. Execute child subtasks POST-SUBTASK-046, POST-SUBTASK-047, POST-SUBTASK-048 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-048` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-046` — Materialize append-only game, team, conference, venue, player, roster, staff, availability, weather, market, and context as-of state.
- Complete and verify child `POST-SUBTASK-047` — Build national pregame matrices at configured cutoffs with row/cell lineage, missingness class, fallback, and pinned versions.
- Complete and verify child `POST-SUBTASK-048` — Approve or block immutable matrix versions for feature/model experimentation.
- Integrate the child outputs and execute final gate `POST-SUBTASK-048`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Out of scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/rights/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Current gate state

- Workflow: `BACKLOG`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `FUNCTIONAL_STARTER` → `INTEGRATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-051`

## Read first

1. `jira/records/issues/stories/POST-STORY-016_append_only_as_of_state_and_pregame_matrices.json`
2. `jira/sources/issue_source_manifests/POST-STORY-016.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-016`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_temporal_governance.py
- tests/test_w24_readiness.py
- src/aggie_analytics/temporal/eligibility.py
- src/aggie_analytics/temporal/state.py
- docs/readiness/W24_END_TO_END_READINESS.md
- docs/18_POINT_IN_TIME_DATA_ARCHITECTURE.md

## Dependencies that must already be complete

- POST-SUBTASK-045

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-016.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

## Components in scope

- pit-temporal
- pit

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

- artifacts/pit/asof_state_manifest.json
- artifacts/pit/pregame_matrix_manifest.json
- artifacts/pit/matrix_gate_decision.json

## Acceptance criteria

1. All child Subtasks satisfy their issue-specific observable checks and save their required evidence.
2. The final child gate verifies the combined output and explicitly approves, blocks, rejects, or defers downstream use.
3. No child completion is accepted if a hard prerequisite, PIT/right/security/protected-control requirement, or evidence identity is missing.

## Tests / validation

- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_temporal_governance.py — Run and retain the result when this issue touches the covered contract.
- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_w24_readiness.py — Run and retain the result when this issue touches the covered contract.
- END_TO_END / END_TO_END: POST-SUBTASK-048 — The final child gate `POST-SUBTASK-048` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-046, POST-SUBTASK-047, POST-SUBTASK-048.
- Final gate decision from `POST-SUBTASK-048` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

A pinned cutoff reconstructs the exact state and matrix row that was legitimately knowable before a historical game.

## Stop instead of improvising when

- Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.

## Completion protocol

1. Verify every required child issue is complete at its claimed maturity with verified evidence; do not infer completion from file or code existence.
2. Run or review the declared integrated end-to-end gate and downstream-consumption proof.
3. Create the aggregate evidence manifest with pinned source/data/code/config/model/runtime identities, residual blockers, accepted risks, null/negative results, and gate decisions.
4. Keep this Epic/Story non-READY and non-executable; route any implementation change to a specific atomic Subtask or create a controlled backlog proposal.
5. Update canonical/local Jira state and live Jira operational fields according to `jira/SYNC_CONTRACT.md` only after the aggregate gate is truthfully satisfied.
6. Rebuild all derivatives with `python -B jira/tools/rebuild_all_derivatives.py`, recompute queues, and run `python -B jira/tools/validate_second_pass.py`.
7. Reevaluate downstream gates without weakening protected requirements or hiding incomplete child evidence.
