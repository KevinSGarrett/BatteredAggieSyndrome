# AI Work Packet — POST-STORY-009

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Materialize teams, conferences, venues, schedules, games, outcomes, drives, plays, and official game evidence.

## Why?

This coherent capability closes a defined portion of Immutable national historical data materialization and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-009 (Core national game spine) as one coherent, gated capability inside Epic POST-EPIC-003. Execute child subtasks POST-SUBTASK-025, POST-SUBTASK-026, POST-SUBTASK-027 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-027` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-025` — Acquire approved national team, schedule, game, score, drive, play, box-score, and gamebook history.
- Complete and verify child `POST-SUBTASK-026` — Normalize and reconcile core/game-event records while preserving immutable source evidence.
- Complete and verify child `POST-SUBTASK-027` — Approve or block the population-level core-history coverage gate.
- Integrate the child outputs and execute final gate `POST-SUBTASK-027`.
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
- Maturity before → after: `SCAFFOLD` → `INTEGRATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-033`

## Read first

1. `jira/records/issues/stories/POST-STORY-009_core_national_game_spine.json`
2. `jira/sources/issue_source_manifests/POST-STORY-009.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-009`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w19_foundation.py
- src/aggie_analytics/data/adapters.py
- src/aggie_analytics/data/contracts.py
- src/aggie_analytics/data/snapshots.py
- docs/101_W19_FOUNDATION_IMPLEMENTATION.md
- docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md

## Dependencies that must already be complete

- POST-SUBTASK-006
- POST-SUBTASK-018
- POST-SUBTASK-021
- POST-SUBTASK-022

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-009.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

## Components in scope

- raw-snapshots
- raw-data

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

- artifacts/data_lake/core_acquisition_manifest.json
- artifacts/data_lake/core_normalization_report.json
- artifacts/data_lake/core_coverage_gate.json

## Acceptance criteria

1. All child Subtasks satisfy their issue-specific observable checks and save their required evidence.
2. The final child gate verifies the combined output and explicitly approves, blocks, rejects, or defers downstream use.
3. No child completion is accepted if a hard prerequisite, PIT/right/security/protected-control requirement, or evidence identity is missing.

## Tests / validation

- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_w19_foundation.py — Run and retain the result when this issue touches the covered contract.
- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tools/validate_w19_foundation.py — Run and retain the result when this issue touches the covered contract.
- END_TO_END / END_TO_END: POST-SUBTASK-027 — The final child gate `POST-SUBTASK-027` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-025, POST-SUBTASK-026, POST-SUBTASK-027.
- Final gate decision from `POST-SUBTASK-027` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

A clean acquisition run produces immutable national game history, deterministic normalized evidence, and an honest coverage decision.

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
