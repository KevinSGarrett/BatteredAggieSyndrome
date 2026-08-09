# AI Work Packet — POST-STORY-006

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Apply the owner-authorized private-research policy universally while preserving license/terms/redistribution metadata and independently denying raw third-party publication.

## Why?

This coherent capability closes a defined portion of Source access, rights, credentials, and acquisition governance and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-006 (Universal private-research acquisition and future-publication boundary) as one coherent, gated capability inside Epic POST-EPIC-002. Execute child subtasks POST-SUBTASK-016, POST-SUBTASK-017, POST-SUBTASK-018 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-018` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-016` — Reissue CFBD, SportsDataverse, Open-Meteo, and official A&M/SEC/NCAA decisions under private-research policy.
- Complete and verify child `POST-SUBTASK-017` — Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy.
- Complete and verify child `POST-SUBTASK-018` — Publish the private-research source-use matrix and block raw third-party publication.
- Integrate the child outputs and execute final gate `POST-SUBTASK-018`.
- Preserve exact source/data/code/config/runtime identities, failures, unresolved blockers, and downstream-consumption evidence.

### Out of scope

- Work assigned to sibling Stories or another Epic.
- Closing the Story because implementation files exist while the final gate or downstream-consumption proof is incomplete.
- Weakening protected requirements, PIT/source-policy/security controls, accepted ADRs, or evidence thresholds to obtain a passing gate.

## Current gate state

- Workflow: `BACKLOG`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `AGGREGATE_GATE`
- Maturity before → after: `CONTRACT_DEFINED` → `INTEGRATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-024`

## Read first

1. `jira/records/issues/stories/POST-STORY-006_per_source_license_terms_and_redistribution_decisions.json`
2. `jira/sources/issue_source_manifests/POST-STORY-006.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-006`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/data/adapters.py
- docs/data_research/w06/DATA_ACQUISITION_PLAN.md
- docs/data_research/w06/SOURCE_ACCESS_LICENSE_MATRIX.csv
- docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md
- docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md

## Dependencies that must already be complete

- POST-SUBTASK-015

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-006.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

## Components in scope

- data-sources
- sources

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

- artifacts/source_governance/tier1_rights_decisions.csv
- artifacts/source_governance/supplemental_rights_decisions.csv
- configs/source_rights_registry.json
- artifacts/source_governance/source_rights_gate_test.json

## Acceptance criteria

1. Each decision records source URL/version, review date, local storage, local training, publication boundary, retention, and attribution metadata.
2. Ambiguous license, terms, scraping, redistribution, and upstream-authorization fields are explicitly nonblocking for private acquisition/training.
3. Bulk raw data remains local outside Git and is not published.
4. Every supplemental source is acquisition-eligible for private research; technical readiness and domain quality remain independent.
5. Genuinely private resources needing unsupplied credentials remain technically unavailable and public substitutes are sought.
6. Raw third-party publication is denied by project policy.
7. The registry is machine-readable and contains no credentials.
8. All registered sources and caller-declared public sources admit private acquisition and local training without a rights prerequisite.
9. Raw third-party export remains independently denied and validity/safety gates remain scoped.

## Tests / validation

- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_data_research.py — Run and retain the result when this issue touches the covered contract.
- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tools/validate_data_research.py — Run and retain the result when this issue touches the covered contract.
- END_TO_END / END_TO_END: POST-SUBTASK-018 — The final child gate `POST-SUBTASK-018` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-016, POST-SUBTASK-017, POST-SUBTASK-018.
- Final gate decision from `POST-SUBTASK-018` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

Private local acquisition and training succeed independently of rights ambiguity, raw third-party publication remains denied, and actual technical/quality/PIT/safety failures affect only their exact scope.

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
