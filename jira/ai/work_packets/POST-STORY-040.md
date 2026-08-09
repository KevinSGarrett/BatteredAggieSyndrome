# AI Work Packet — POST-STORY-040

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Present serious forecast outputs first while retaining the project’s humorous BAS identity and truthful null-result handling.

## Why?

This coherent capability closes a defined portion of Snapshot API, dashboard, explanations, analogs, and freshness-safe product and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-040 (Prediction-first dashboard and BAS experience) as one coherent, gated capability inside Epic POST-EPIC-013. Execute child subtasks POST-SUBTASK-118, POST-SUBTASK-119, POST-SUBTASK-120 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-120` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-118` — Build game/A&M views for score, win probability, margin, distributions, intervals, scenarios, cutoff, freshness, and model identity.
- Complete and verify child `POST-SUBTASK-119` — Build BAS ≥3/7/14/21, component, witty-copy, scientific caveat, no-effect, and unavailable presentation.
- Complete and verify child `POST-SUBTASK-120` — Validate prediction-first hierarchy, accessibility, responsive/loading/stale/blocked/no-data states, and snapshot-only values.
- Integrate the child outputs and execute final gate `POST-SUBTASK-120`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Out of scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Current gate state

- Workflow: `BACKLOG`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `FUNCTIONAL_STARTER` → `INTEGRATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-123`

## Read first

1. `jira/records/issues/stories/POST-STORY-040_prediction_first_dashboard_and_bas_experience.json`
2. `jira/sources/issue_source_manifests/POST-STORY-040.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-040`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w22_product_serving.py
- src/aggie_analytics/api/fastapi_app.py
- src/aggie_analytics/product/freshness.py
- src/aggie_analytics/product/repository.py
- src/aggie_analytics/product/service.py
- docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md

## Dependencies that must already be complete

- POST-SUBTASK-117

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-040.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

## Components in scope

- serving-product
- product

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

- artifacts/product/dashboard_contract_test.json
- artifacts/product/bas_presentation_validation.json
- artifacts/product/dashboard_gate.json

## Acceptance criteria

1. Main views make prediction and uncertainty primary, show specialization only if admitted or global-only otherwise, and never calculate independent client-side percentages/scores.
2. The declared output `artifacts/product/dashboard_contract_test.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. BAS is explicitly underperformance versus valid pregame expected margin—not loss probability—witty copy is separate from science, and thresholds/components appear only when supported with uncertainty.
5. The declared output `artifacts/product/bas_presentation_validation.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. Every displayed value traces to a snapshot field and loading/stale/blocked/missing/no-champion/null-effect/source-outage states are accessible and keyboard/screen-reader understandable.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_w22_product_serving.py — Run and retain the result when this issue touches the covered contract.
- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tools/validate_w22_product.py — Run and retain the result when this issue touches the covered contract.
- END_TO_END / END_TO_END: POST-SUBTASK-120 — The final child gate `POST-SUBTASK-120` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-118, POST-SUBTASK-119, POST-SUBTASK-120.
- Final gate decision from `POST-SUBTASK-120` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

The user sees a serious predictive product with honest uncertainty and freshness, plus clearly separated witty BAS framing that never overstates scientific evidence.

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
