# AI Work Packet — POST-STORY-024

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Freeze task definitions and model inputs before candidate training.

## Why?

This coherent capability closes a defined portion of Reproducible baseline, coherent score, probability, and uncertainty modeling and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-024 (Model-ready targets, splits, weights, and datasets) as one coherent, gated capability inside Epic POST-EPIC-008. Execute child subtasks POST-SUBTASK-070, POST-SUBTASK-071, POST-SUBTASK-072 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-072` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-070` — Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage.
- Complete and verify child `POST-SUBTASK-071` — Materialize chronological train/tune/protected assignments, sample weights, cold-start rules, and feature/target separation.
- Complete and verify child `POST-SUBTASK-072` — Approve model dataset identity, leakage isolation, duplicate handling, and reproducibility.
- Integrate the child outputs and execute final gate `POST-SUBTASK-072`.
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
- Governance traceability gate: `POST-SUBTASK-078`

## Read first

1. `jira/records/issues/stories/POST-STORY-024_model_ready_targets_splits_weights_and_datasets.json`
2. `jira/sources/issue_source_manifests/POST-STORY-024.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-024`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- src/aggie_analytics/modeling/baselines.py
- src/aggie_analytics/modeling/joint.py
- src/aggie_analytics/modeling/runtime.py
- docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md
- docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md

## Dependencies that must already be complete

- POST-SUBTASK-051
- POST-SUBTASK-060

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-024.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

## Components in scope

- modeling

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

- artifacts/modeling/target_dataset_manifest.json
- artifacts/modeling/model_split_manifest.json
- artifacts/modeling/model_dataset_gate.json

## Acceptance criteria

1. Targets declare cancellations, overtime, missing scores, neutral sites, lower divisions, and official outcome source; every row links to canonical game evidence.
2. The declared output `artifacts/modeling/target_dataset_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. Split assignments match protected registries, prevent duplicate/rematch/season-fragment leakage, and precommit weights/shrinkage before candidate results.
5. The declared output `artifacts/modeling/model_split_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. Pinned raw/entity/PIT/feature/target/split versions reproduce identical rows and protected labels are inaccessible to training/tuning paths.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_model_architecture_governance.py — Run and retain the result when this issue touches the covered contract.
- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_w20_model_starter.py — Run and retain the result when this issue touches the covered contract.
- END_TO_END / END_TO_END: POST-SUBTASK-072 — The final child gate `POST-SUBTASK-072` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-070, POST-SUBTASK-071, POST-SUBTASK-072.
- Final gate decision from `POST-SUBTASK-072` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

The same pinned identities always produce the same model-ready rows, targets, weights, and chronological partitions without protected leakage.

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
