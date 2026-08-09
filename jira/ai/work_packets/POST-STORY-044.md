# AI Work Packet — POST-STORY-044

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Prove canonical data/model/forecast/Jira state can be recovered to a verified point.

## Why?

This coherent capability closes a defined portion of Security, observability, backup/restore, drift, and incident operations and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-044 (Rights-aware backup, restore, retention, and disaster recovery) as one coherent, gated capability inside Epic POST-EPIC-014. Execute child subtasks POST-SUBTASK-130, POST-SUBTASK-131, POST-SUBTASK-132 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-132` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-130` — Finalize authority/retention/frequency/encryption/access/rights/deletion rules for raw, curated, model, forecast, log, evidence, and Jira metadata.
- Complete and verify child `POST-SUBTASK-131` — Implement content-hashed verified backups, catalog, integrity checking, last-known-good protection, and restricted-destination enforcement.
- Complete and verify child `POST-SUBTASK-132` — Execute clean-location restore of representative raw-to-forecast lineage and Jira metadata with measured RPO/RTO/manual steps.
- Integrate the child outputs and execute final gate `POST-SUBTASK-132`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Out of scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/rights/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Current gate state

- Workflow: `BACKLOG`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `FUNCTIONAL_STARTER` → `INTEGRATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-132`

## Read first

1. `jira/records/issues/stories/POST-STORY-044_rights_aware_backup_restore_retention_and_disaster_recovery.json`
2. `jira/sources/issue_source_manifests/POST-STORY-044.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-044`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w23_operations.py
- src/aggie_analytics/operations/backup.py
- src/aggie_analytics/operations/observability.py
- docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md
- docs/operations/BACKUP_RESTORE_RETENTION_RUNBOOK.md
- docs/operations/CI_SECURITY_SUPPLY_CHAIN.md

## Dependencies that must already be complete

- POST-SUBTASK-129

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-044.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

## Components in scope

- operations-security
- operations

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

- configs/backup_retention_policy.json
- artifacts/operations/backup_catalog_and_integrity.json
- artifacts/operations/restore_drill.json

## Acceptance criteria

1. All child Subtasks satisfy their issue-specific observable checks and save their required evidence.
2. The final child gate verifies the combined output and explicitly approves, blocks, rejects, or defers downstream use.
3. No child completion is accepted if a hard prerequisite, PIT/right/security/protected-control requirement, or evidence identity is missing.

## Tests / validation

- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_w23_operations.py — Run and retain the result when this issue touches the covered contract.
- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tools/validate_w23_operations.py — Run and retain the result when this issue touches the covered contract.
- END_TO_END / END_TO_END: POST-SUBTASK-132 — The final child gate `POST-SUBTASK-132` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-130, POST-SUBTASK-131, POST-SUBTASK-132.
- Final gate decision from `POST-SUBTASK-132` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

A verified backup can restore selected canonical lineage and Jira execution state into a clean location without rewriting history or violating data rights.

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
