# AI Work Packet — POST-EPIC-013

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Serve the predictive system and witty BAS experience from immutable approved snapshots with truthful freshness, uncertainty, provenance, accessibility, and no live recomputation drift.

## Why?

The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.

## Aggregate integration and closure scope

All Stories and Subtasks under this Epic for the product domain, including its explicit integrated completion gate.

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
- Priority: `P2`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `FUNCTIONAL_STARTER` → `OPERATING`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-123`

## Read first

1. `jira/records/issues/epics/POST-EPIC-013_snapshot_api_dashboard_explanations_analogs_and_freshness_safe_product.json`
2. `jira/sources/issue_source_manifests/POST-EPIC-013.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-EPIC-013`.
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

- POST-SUBTASK-111

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-EPIC-013.json

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

- artifacts/product/snapshot_repository_test.json
- docs/product/OPENAPI_SNAPSHOT.json
- artifacts/product/api_gate.json
- artifacts/product/dashboard_contract_test.json
- artifacts/product/bas_presentation_validation.json
- artifacts/product/dashboard_gate.json
- artifacts/product/explanation_analog_validation.json
- artifacts/product/product_performance_benchmark.json
- artifacts/product/PRODUCT_READINESS.json

## Acceptance criteria

1. Every child issue completes at its declared maturity and evidence state, or has an explicit accepted-risk/deferred disposition.
2. The Epic's end-to-end gate proves the integrated capability on the required real data, target host, protected chronology, or operating path; file existence alone is insufficient.
3. All requirement, acceptance-control, ADR, risk, gap, test, artifact, and source references remain valid and no protected invariant is weakened.

## Tests / validation

- END_TO_END / END_TO_END: POST-SUBTASK-117 — Story gate `POST-SUBTASK-117` must complete with verified evidence before Epic completion.
- END_TO_END / END_TO_END: POST-SUBTASK-120 — Story gate `POST-SUBTASK-120` must complete with verified evidence before Epic completion.
- END_TO_END / END_TO_END: POST-SUBTASK-123 — Story gate `POST-SUBTASK-123` must complete with verified evidence before Epic completion.
- REPRODUCIBILITY / REPRODUCIBILITY: EPIC_EVIDENCE_MANIFEST — Aggregate all Story gates, artifact identities, residual blockers, accepted risks, and downstream readiness.

## Evidence to return

- Verified Story gate decisions for POST-SUBTASK-117, POST-SUBTASK-120, POST-SUBTASK-123.
- Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.
- A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities.

## End-to-end handoff

The entire Snapshot API, dashboard, explanations, analogs, and freshness-safe product capability must be exercised through its final gate and produce reproducible evidence consumable by its downstream Epic.

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
