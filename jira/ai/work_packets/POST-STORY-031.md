# AI Work Packet — POST-STORY-031

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Separate ordinary football surprise from any incremental A&M effect and decompose outcomes without changing the headline.

## Why?

This coherent capability closes a defined portion of Scientific BAS, general FBS surprise, Aggie excess, and component validation and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-031 (General FBS baseline, Aggie excess, and components) as one coherent, gated capability inside Epic POST-EPIC-010. Execute child subtasks POST-SUBTASK-091, POST-SUBTASK-092, POST-SUBTASK-093 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-093` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-091` — Estimate out-of-sample general FBS severity probabilities and residual distributions across seasons/regimes/contexts.
- Complete and verify child `POST-SUBTASK-092` — Estimate A&M excess versus FBS, precommitted peers/regimes, and matched contexts plus offensive/defensive/special-teams/collapse component evidence.
- Complete and verify child `POST-SUBTASK-093` — Validate peer sensitivity, multiple comparisons, component coherence, uncertainty, coverage, and null-result handling.
- Integrate the child outputs and execute final gate `POST-SUBTASK-093`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Out of scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.
- Redefining BAS as generic Texas A&M loss probability or selecting specifications merely to manufacture a nonzero Aggie-specific effect.

## Current gate state

- Workflow: `BACKLOG`
- Ready: `false`
- Priority: `P1`
- Critical path: `false`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `FUNCTIONAL_STARTER` → `INTEGRATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-096`

## Read first

1. `jira/records/issues/stories/POST-STORY-031_general_fbs_baseline_aggie_excess_and_components.json`
2. `jira/sources/issue_source_manifests/POST-STORY-031.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-031`.
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

- POST-SUBTASK-084
- POST-SUBTASK-090

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-031.json

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

- artifacts/bas/general_fbs_baseline.json
- artifacts/bas/aggie_excess_components.json
- artifacts/bas/aggie_excess_component_gate.json

## Acceptance criteria

1. General rates/probabilities are cross-fitted and calibrated with uncertainty; sparse regimes and team effects are not smuggled into a universal baseline.
2. The declared output `artifacts/bas/general_fbs_baseline.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. A&M analyses use sealed expectations/peers, report effect/sample/sensitivity uncertainty, accept zero/negative/unstable excess, and make components unavailable when granular evidence is absent.
5. The declared output `artifacts/bas/aggie_excess_components.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. No post-hoc peer/time/threshold subgroup is elevated for a preferred effect, components do not replace the ≥7 headline or imply additive causality, and product claims are bounded to evidence.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
8. A null, non-significant, unstable, or directionally unsupported Aggie-specific excess result is accepted and reported without forcing a nonzero BAS effect; general FBS surprise and Texas A&M-specific excess remain distinct.

## Tests / validation

- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_bas_science_governance.py — Run and retain the result when this issue touches the covered contract.
- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_w20_model_starter.py — Run and retain the result when this issue touches the covered contract.
- END_TO_END / END_TO_END: POST-SUBTASK-093 — The final child gate `POST-SUBTASK-093` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-091, POST-SUBTASK-092, POST-SUBTASK-093.
- Final gate decision from `POST-SUBTASK-093` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

General surprise, possible Aggie excess, and explanatory components are estimated from sealed residual evidence with null results and uncertainty preserved.

## Stop instead of improvising when

- Stop if entry dependencies are not complete at required maturity or if the gate cannot evaluate the combined outputs.
- Stop if the proposed method, threshold, peer set, fold construction, or product wording would conceal, reject, or overwrite a valid null/no-effect result.

## Completion protocol

1. Verify every required child issue is complete at its claimed maturity with verified evidence; do not infer completion from file or code existence.
2. Run or review the declared integrated end-to-end gate and downstream-consumption proof.
3. Create the aggregate evidence manifest with pinned source/data/code/config/model/runtime identities, residual blockers, accepted risks, null/negative results, and gate decisions.
4. Keep this Epic/Story non-READY and non-executable; route any implementation change to a specific atomic Subtask or create a controlled backlog proposal.
5. Update canonical/local Jira state and live Jira operational fields according to `jira/SYNC_CONTRACT.md` only after the aggregate gate is truthfully satisfied.
6. Rebuild all derivatives with `python -B jira/tools/rebuild_all_derivatives.py`, recompute queues, and run `python -B jira/tools/validate_second_pass.py`.
7. Reevaluate downstream gates without weakening protected requirements or hiding incomplete child evidence.
