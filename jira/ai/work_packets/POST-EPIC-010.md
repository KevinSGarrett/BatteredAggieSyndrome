# AI Work Packet — POST-EPIC-010

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Validate BAS as out-of-sample A&M underperformance relative to a strictly valid pregame expectation, never as generic loss probability and never by forcing a nonzero effect.

## Why?

The final W25 handoff identifies this capability as necessary to move from accepted design/functional starters to evidence-backed implementation, empirical validation, production readiness, or operation.

## Aggregate integration and closure scope

All Stories and Subtasks under this Epic for the bas domain, including its explicit integrated completion gate.

### In scope

- Child implementation and evidence work
- Cross-domain hard dependencies
- Integrated end-to-end gate
- Preservation of source authority and protected controls

### Out of scope

- Declaring child code sufficient without integrated evidence
- Changing protected requirements or ADRs without governance review
- Creating Wave 26
- Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect.

## Current gate state

- Workflow: `BACKLOG`
- Ready: `false`
- Priority: `P1`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `FUNCTIONAL_STARTER` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-096`

## Read first

1. `jira/records/issues/epics/POST-EPIC-010_scientific_bas_general_fbs_surprise_aggie_excess_and_component_validation.json`
2. `jira/sources/issue_source_manifests/POST-EPIC-010.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-EPIC-010`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_bas_science_governance.py
- src/aggie_analytics/bas/labels.py
- src/aggie_analytics/bas/runtime.py
- docs/45_SCIENTIFIC_BAS_SPECIFICATION.md
- docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md
- docs/47_BAS_GENERAL_FBS_AGGIE_EXCESS_AND_PEERS.md

## Dependencies that must already be complete

- POST-SUBTASK-078
- POST-SUBTASK-084

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-EPIC-010.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

## Components in scope

- bas-science
- bas

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

- artifacts/bas/crossfit_expectation_manifest.json
- artifacts/bas/bas_label_manifest.json
- artifacts/bas/bas_label_gate.json
- artifacts/bas/general_fbs_baseline.json
- artifacts/bas/aggie_excess_components.json
- artifacts/bas/aggie_excess_component_gate.json
- artifacts/bas/bas_protected_scorecard.json
- artifacts/bas/bas_stability_analysis.json
- artifacts/bas/BAS_SCIENTIFIC_DECISION.json

## Acceptance criteria

1. Every child issue completes at its declared maturity and evidence state, or has an explicit accepted-risk/deferred disposition.
2. The Epic's end-to-end gate proves the integrated capability on the required real data, target host, protected chronology, or operating path; file existence alone is insufficient.
3. All requirement, acceptance-control, ADR, risk, gap, test, artifact, and source references remain valid and no protected invariant is weakened.
4. A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct.

## Tests / validation

- END_TO_END / END_TO_END: POST-SUBTASK-090 — Story gate `POST-SUBTASK-090` must complete with verified evidence before Epic completion.
- END_TO_END / END_TO_END: POST-SUBTASK-093 — Story gate `POST-SUBTASK-093` must complete with verified evidence before Epic completion.
- END_TO_END / END_TO_END: POST-SUBTASK-096 — Story gate `POST-SUBTASK-096` must complete with verified evidence before Epic completion.
- REPRODUCIBILITY / REPRODUCIBILITY: EPIC_EVIDENCE_MANIFEST — Aggregate all Story gates, artifact identities, residual blockers, accepted risks, and downstream readiness.

## Evidence to return

- Verified Story gate decisions for POST-SUBTASK-090, POST-SUBTASK-093, POST-SUBTASK-096.
- Epic-level integrated execution/review evidence demonstrating actual downstream consumption and safe failure behavior.
- A residual-risk/blocker disposition and maturity/evidence claim audit tied to exact artifact and runtime identities.

## End-to-end handoff

The entire Scientific BAS, general FBS surprise, Aggie excess, and component validation capability must be exercised through its final gate and produce reproducible evidence consumable by its downstream Epic.

## Stop instead of improvising when

- Stop before execution if any hard dependency, protected gate, source-rights decision, or target-resource precondition is unresolved.
- Stop if the proposed method, threshold, peer set, fold construction, or product wording would conceal, reject, or overwrite a valid null/no-effect result.

## Completion protocol

1. Verify every required child issue is complete at its claimed maturity with verified evidence; do not infer completion from file or code existence.
2. Run or review the declared integrated end-to-end gate and downstream-consumption proof.
3. Create the aggregate evidence manifest with pinned source/data/code/config/model/runtime identities, residual blockers, accepted risks, null/negative results, and gate decisions.
4. Keep this Epic/Story non-READY and non-executable; route any implementation change to a specific atomic Subtask or create a controlled backlog proposal.
5. Update canonical/local Jira state and live Jira operational fields according to `jira/SYNC_CONTRACT.md` only after the aggregate gate is truthfully satisfied.
6. Rebuild all derivatives with `python -B jira/tools/rebuild_all_derivatives.py`, recompute queues, and run `python -B jira/tools/validate_second_pass.py`.
7. Reevaluate downstream gates without weakening protected requirements or hiding incomplete child evidence.
