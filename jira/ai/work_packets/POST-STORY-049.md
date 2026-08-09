# AI Work Packet — POST-STORY-049

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Run an admitted challenger in isolation without contaminating production or the protected test.

## Why?

This coherent capability closes a defined portion of Conditional advanced challenger research and admission and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-049 (Bounded implementation, tuning, ablation, and protected admission) as one coherent, gated capability inside Epic POST-EPIC-016. Execute child subtasks POST-SUBTASK-145, POST-SUBTASK-146, POST-SUBTASK-147 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-147` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-145` — Implement the admitted neural/Bayesian/graph/sequence challenger against pinned matrices/splits within fixed scope and compute.
- Complete and verify child `POST-SUBTASK-146` — Run bounded tuning, ablation, calibration, OOD, robustness, stability, runtime, memory, maintainability, and simple-baseline comparisons retaining all failures.
- Complete and verify child `POST-SUBTASK-147` — Decide whether tuning evidence warrants a one-time sealed protected comparison.
- Integrate the child outputs and execute final gate `POST-SUBTASK-147`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Out of scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/rights/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Current gate state

- Workflow: `DEFERRED`
- Ready: `false`
- Priority: `P3`
- Critical path: `false`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `CONDITIONAL` → `INTEGRATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-150`

## Read first

1. `jira/records/issues/stories/POST-STORY-049_bounded_implementation_tuning_ablation_and_protected_admission.json`
2. `jira/sources/issue_source_manifests/POST-STORY-049.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-049`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/IMPLEMENTATION_WBS.csv
- tests/test_advanced_challenger_full.py
- src/aggie_analytics/experimentation/advanced_challengers.py
- docs/72_ADVANCED_CHALLENGER_ADMISSION.md
- docs/91_ADVANCED_CHALLENGER_GATE.md
- governance/ADVANCED_CHALLENGER_ADMISSION.csv

## Dependencies that must already be complete

- POST-SUBTASK-144

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-049.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

## Components in scope

- advanced-challengers
- advanced

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

- artifacts/advanced/challenger_build_manifest.json
- artifacts/advanced/challenger_tuning_scorecard.json
- artifacts/advanced/challenger_protected_admission.json

## Acceptance criteria

1. All child Subtasks satisfy their issue-specific observable checks and save their required evidence.
2. The final child gate verifies the combined output and explicitly approves, blocks, rejects, or defers downstream use.
3. No child completion is accepted if a hard prerequisite, PIT/right/security/protected-control requirement, or evidence identity is missing.

## Tests / validation

- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_advanced_challenger_full.py — Run and retain the result when this issue touches the covered contract.
- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tools/check_advanced_challenger_admission.py — Run and retain the result when this issue touches the covered contract.
- END_TO_END / END_TO_END: POST-SUBTASK-147 — The final child gate `POST-SUBTASK-147` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-145, POST-SUBTASK-146, POST-SUBTASK-147.
- Final gate decision from `POST-SUBTASK-147` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

An admitted challenger produces bounded, reproducible, fully logged tuning evidence without changing production or leaking protected outcomes.

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
