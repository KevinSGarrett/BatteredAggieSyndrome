# AI Work Packet — POST-STORY-053

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Require a full independent release path for any live capability.

## Why?

This coherent capability closes a defined portion of Deferred live and in-game modeling and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-053 (Separate protected evaluation, product integration, and operating authorization) as one coherent, gated capability inside Epic POST-EPIC-017. Execute child subtasks POST-SUBTASK-157, POST-SUBTASK-158, POST-SUBTASK-159 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-159` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-157` — Run sealed event-time chronological evaluation with precommitted accuracy/calibration/latency/reliability/outage metrics and simple/pregame baselines.
- Complete and verify child `POST-SUBTASK-158` — Implement timestamped live snapshot/stream API and UI states for stale, disconnected, corrected, suspended, halftime, final, replay, and restricted data.
- Complete and verify child `POST-SUBTASK-159` — Conduct rights/science/security/product/target-resource/backup/incident review and authorize or reject live operation separately.
- Integrate the child outputs and execute final gate `POST-SUBTASK-159`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Out of scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/rights/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Current gate state

- Workflow: `DEFERRED`
- Ready: `false`
- Priority: `DEFERRED`
- Critical path: `false`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `DEFERRED` → `INTEGRATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-159`

## Read first

1. `jira/records/issues/stories/POST-STORY-053_separate_protected_evaluation_product_integration_and_operating_authorization.json`
2. `jira/sources/issue_source_manifests/POST-STORY-053.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-053`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/IMPLEMENTATION_WBS.csv
- governance/OPEN_ISSUES.md

## Dependencies that must already be complete

- POST-SUBTASK-156

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-053.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

## Components in scope

- live-modeling
- live

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

- artifacts/live/live_protected_scorecard.json
- artifacts/live/live_product_validation.json
- artifacts/live/live_operating_decision.json

## Acceptance criteria

1. All child Subtasks satisfy their issue-specific observable checks and save their required evidence.
2. The final child gate verifies the combined output and explicitly approves, blocks, rejects, or defers downstream use.
3. No child completion is accepted if a hard prerequisite, PIT/right/security/protected-control requirement, or evidence identity is missing.

## Tests / validation

- END_TO_END / END_TO_END: POST-SUBTASK-159 — The final child gate `POST-SUBTASK-159` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-157, POST-SUBTASK-158, POST-SUBTASK-159.
- Final gate decision from `POST-SUBTASK-159` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

Any live capability independently earns operating authorization from licensed replayable evidence; rejection has no effect on the completed pregame system.

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
