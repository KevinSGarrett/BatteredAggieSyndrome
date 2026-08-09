# AI Work Packet — POST-STORY-033

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Prove evaluation inputs and decisions were frozen before protected outcomes are accessed.

## Why?

This coherent capability closes a defined portion of Protected chronological evaluation, calibration, and champion promotion and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-033 (Protected split, judging rule, threshold, candidate, and access seal) as one coherent, gated capability inside Epic POST-EPIC-011. Execute child subtasks POST-SUBTASK-097, POST-SUBTASK-098, POST-SUBTASK-099 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-099` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-097` — Verify protected split, judging-rule, threshold, feature, model, A&M, BAS, peer, and candidate seal hashes.
- Complete and verify child `POST-SUBTASK-098` — Establish protected-outcome access isolation, audit logging, one-way evidence, and failure preservation.
- Complete and verify child `POST-SUBTASK-099` — Authorize or block the exact sealed protected evaluation run.
- Integrate the child outputs and execute final gate `POST-SUBTASK-099`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Out of scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Current gate state

- Workflow: `BACKLOG`
- Ready: `false`
- Priority: `P1`
- Critical path: `true`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `FUNCTIONAL_STARTER` → `INTEGRATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-105`

## Read first

1. `jira/records/issues/stories/POST-STORY-033_protected_split_judging_rule_threshold_candidate_and_access_seal.json`
2. `jira/sources/issue_source_manifests/POST-STORY-033.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-033`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- src/aggie_analytics/validation/promotion.py
- src/aggie_analytics/validation/protected.py
- docs/56_VALIDATION_AND_PROTECTED_SPLITS.md

## Dependencies that must already be complete

- POST-SUBTASK-078
- POST-SUBTASK-084
- POST-SUBTASK-090

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-033.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

## Components in scope

- validation-promotion
- validation

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

- artifacts/validation/protected_seal_verification.json
- artifacts/validation/protected_access_protocol_test.json
- artifacts/validation/protected_run_authorization.json

## Acceptance criteria

1. All seal files/registries/assignments/thresholds/data identities match recorded hashes; a mutation or missing seal blocks evaluation and cannot be waived to make a candidate pass.
2. The declared output `artifacts/validation/protected_seal_verification.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. Only evaluation code can access protected outcomes, every access is attributable, training/tuning cannot read labels/scorecards, and partial failures do not return outcomes for iterative tuning.
5. The declared output `artifacts/validation/protected_access_protocol_test.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. Authorization names exact candidates/tasks/cutoffs/lanes/splits/metrics/thresholds/evidence destinations and verifies all PIT/feature/model/A&M/BAS prerequisites or remains blocked.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_validation_science_governance.py — Run and retain the result when this issue touches the covered contract.
- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_w25_final_handoff.py — Run and retain the result when this issue touches the covered contract.
- END_TO_END / END_TO_END: POST-SUBTASK-099 — The final child gate `POST-SUBTASK-099` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-097, POST-SUBTASK-098, POST-SUBTASK-099.
- Final gate decision from `POST-SUBTASK-099` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

An immutable, auditable authorization proves what may be evaluated and prevents protected outcomes from influencing candidate construction.

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
