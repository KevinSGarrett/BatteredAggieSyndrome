# AI Work Packet — POST-STORY-034

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Generate immutable protected predictions and independently reproducible evaluation evidence.

## Why?

This coherent capability closes a defined portion of Protected chronological evaluation, calibration, and champion promotion and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-034 (Sealed walk-forward predictions and complete scorecards) as one coherent, gated capability inside Epic POST-EPIC-011. Execute child subtasks POST-SUBTASK-100, POST-SUBTASK-101, POST-SUBTASK-102 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-102` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-100` — Execute the sealed national, A&M-candidate, and BAS-support chronological replay once.
- Complete and verify child `POST-SUBTASK-101` — Compute complete score, margin, win, distribution, calibration, BAS, A&M, OOD, coherence, robustness, market-lane, and segment scorecards.
- Complete and verify child `POST-SUBTASK-102` — Validate prediction coverage, scorecard completeness, hashes, ordering, no-early-access, and independent reproducibility.
- Integrate the child outputs and execute final gate `POST-SUBTASK-102`.
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

1. `jira/records/issues/stories/POST-STORY-034_sealed_walk_forward_predictions_and_complete_scorecards.json`
2. `jira/sources/issue_source_manifests/POST-STORY-034.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-034`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/validation/promotion.py
- src/aggie_analytics/validation/protected.py
- docs/56_VALIDATION_AND_PROTECTED_SPLITS.md
- docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md

## Dependencies that must already be complete

- POST-SUBTASK-099

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-034.json

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

- artifacts/validation/protected_predictions.parquet
- artifacts/validation/protected_scorecards.json
- artifacts/validation/protected_replay_gate.json

## Acceptance criteria

1. Replay advances chronologically with only then-available state/models/calibrators/thresholds, records every identity, and retries cannot change membership or expose partial scores.
2. The declared output `artifacts/validation/protected_predictions.parquet` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. All precommitted metrics/segments include baselines, sample sizes, uncertainty, missing predictions, failures, calibration/coherence/OOD and no unfavorable metric is omitted.
5. The declared output `artifacts/validation/protected_scorecards.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. Independent recomputation reproduces metrics/candidate ordering, verifies seals/access/row identity, and incomplete/corrupt evaluation cannot be summarized as a winner.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_validation_science_governance.py — Run and retain the result when this issue touches the covered contract.
- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_w25_final_handoff.py — Run and retain the result when this issue touches the covered contract.
- END_TO_END / END_TO_END: POST-SUBTASK-102 — The final child gate `POST-SUBTASK-102` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-100, POST-SUBTASK-101, POST-SUBTASK-102.
- Final gate decision from `POST-SUBTASK-102` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

Sealed immutable predictions generate complete scorecards that a separate process can reproduce without reopening tuning.

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
