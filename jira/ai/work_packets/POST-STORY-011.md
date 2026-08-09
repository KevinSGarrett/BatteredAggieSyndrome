# AI Work Packet — POST-STORY-011

## Packet mode

`AGGREGATE_GATE`

**DO NOT execute this Epic/Story as an atomic implementation task.** This is an aggregate integration, evidence-review, and closure-gate packet. Implementation mutations belong to READY atomic Subtask packets.

## What capability or closure gate am I coordinating?

Prove that every accepted raw domain is immutable, reproducible, source-policy-metadata-aware, and reconstructable.

## Why?

This coherent capability closes a defined portion of Immutable national historical data materialization and creates a verifiable output for the next dependency stage.

## Aggregate integration and closure scope

Deliver Story POST-STORY-011 (Immutable raw store, manifests, provenance, and population audit) as one coherent, gated capability inside Epic POST-EPIC-003. Execute child subtasks POST-SUBTASK-031, POST-SUBTASK-032, POST-SUBTASK-033 in dependency order, reconcile their pinned outputs, and require the final gate `POST-SUBTASK-033` to issue an evidence-backed approve/block/reject/defer decision before any downstream use.

### In scope

- Complete and verify child `POST-SUBTASK-031` — Enforce content-addressed raw snapshots, correction lineage, quarantine, and source-policy storage metadata.
- Complete and verify child `POST-SUBTASK-032` — Build the cross-domain acquisition, schema, quality, and source-to-snapshot provenance manifests.
- Complete and verify child `POST-SUBTASK-033` — Run and publish the national historical-lake readiness decision.
- Integrate the child outputs and execute final gate `POST-SUBTASK-033`.
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
- Maturity before → after: `SCAFFOLD` → `INTEGRATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-033`

## Read first

1. `jira/records/issues/stories/POST-STORY-011_immutable_raw_store_manifests_provenance_and_population_audit.json`
2. `jira/sources/issue_source_manifests/POST-STORY-011.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-STORY-011`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w19_foundation.py
- src/aggie_analytics/data/adapters.py
- src/aggie_analytics/data/contracts.py
- src/aggie_analytics/data/snapshots.py
- docs/101_W19_FOUNDATION_IMPLEMENTATION.md
- docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md

## Dependencies that must already be complete

- POST-SUBTASK-027
- POST-SUBTASK-030

## Aggregate packet modification authority

- artifacts/jira_evidence/POST-STORY-011.json

Only aggregate evidence/Jira-state artifacts listed above may be written. Do not edit production code, data, contracts, or child outputs from this packet; open the responsible atomic Subtask packet instead.

## Components in scope

- raw-snapshots
- raw-data

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

- artifacts/data_lake/immutability_and_correction_test.json
- artifacts/data_lake/NATIONAL_DATA_LAKE_MANIFEST.json
- artifacts/data_lake/national_lake_readiness.json

## Acceptance criteria

1. Repeated identical bytes resolve to the same content identity while changed/corrected bytes create a new immutable version without rewriting prior evidence.
2. The declared output `artifacts/data_lake/immutability_and_correction_test.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
4. The master manifest links every accepted snapshot to source contract, request, hash, parser/schema version, coverage, quality, and nonblocking source-policy metadata and reproduces population counts.
5. The declared output `artifacts/data_lake/NATIONAL_DATA_LAKE_MANIFEST.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
6. GAP-002 remains open unless actual national history—not fixtures, reconnaissance samples, or starter code—meets immutable, manifest, readback, and coverage requirements.
7. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tests/test_w19_foundation.py — Run and retain the result when this issue touches the covered contract.
- EXISTING_AUTOMATED_TEST / EXISTING_AUTOMATED_TEST: tools/validate_w19_foundation.py — Run and retain the result when this issue touches the covered contract.
- END_TO_END / END_TO_END: POST-SUBTASK-033 — The final child gate `POST-SUBTASK-033` must prove the integrated Story outcome and downstream-consumable output.
- REPRODUCIBILITY / REPRODUCIBILITY: STORY_EVIDENCE_MANIFEST — Aggregate child artifact hashes, input identities, gate decision, failures, and downstream readiness into a reproducible Story evidence manifest.

## Evidence to return

- Verified child completion/evidence manifests for POST-SUBTASK-031, POST-SUBTASK-032, POST-SUBTASK-033.
- Final gate decision from `POST-SUBTASK-033` with criterion-by-criterion PASS/FAIL/BLOCKED outcomes and output hashes.
- Story-level downstream-consumption evidence and an explicit list of issues unlocked, retained blocked, rejected, or deferred.

## End-to-end handoff

Pinned manifests reconstruct the accepted raw lake from immutable bytes while preserving every missing season, unavailable domain, correction, and technical or quality blocker.

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
