# AI Work Packet — POST-SUBTASK-036

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Approve or block schema and missingness readiness for entity resolution

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-012: Population schema and missingness contracts.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-012 (Population schema and missingness contracts): Approve or block schema and missingness readiness for entity resolution. Consume only verified prerequisite outputs from `POST-SUBTASK-033`, `POST-SUBTASK-034`, `POST-SUBTASK-035`. Produce `artifacts/entities/schema_readiness_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Approve or block schema and missingness readiness for entity resolution.
- Consume only verified prerequisite outputs from `POST-SUBTASK-033`, `POST-SUBTASK-034`, `POST-SUBTASK-035`.
- Demonstrate with saved evidence: Profiles are generated from pinned immutable snapshots by source/season/domain and reproduce exactly.
- Demonstrate with saved evidence: Every measured field is accepted, transformed, quarantined, deprecated, or rejected with reason; protected temporal/evidence fields are not weakened to accommodate dirty data.
- Demonstrate with saved evidence: All entity-bearing domains have measured key quality and a declared resolution strategy; unusable partitions remain enumerated rather than silently dropped.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/entities/schema_readiness_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Profile every materialized table for rows, types, nulls, uniqueness, ranges, duplicates, timestamps, and partitions; Reconcile measured fields with canonical contracts, compatibility policy, and quarantine/rejection decisions.

## Current gate state

- Workflow: `READY`
- Ready: `true`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-042`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-036_approve_or_block_schema_and_missingness_readiness_for_entity_resolution.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-036.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-036`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_entity_governance.py
- src/aggie_analytics/entities/resolution.py
- docs/14_CANONICAL_ENTITY_ARCHITECTURE.md
- docs/16_ENTITY_RESOLUTION_AND_REVIEW.md
- governance/ENTITY_RESOLUTION_STATES.csv

## Dependencies that must already be complete

- POST-SUBTASK-033
- POST-SUBTASK-034
- POST-SUBTASK-035

## Files I may modify or create

- artifacts/entities/schema_readiness_gate.json
- artifacts/jira_evidence/POST-SUBTASK-036.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- entities

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

Produce and validate these outputs within this atomic work unit:

- artifacts/entities/schema_readiness_gate.json

## Acceptance criteria

1. Profiles are generated from pinned immutable snapshots by source/season/domain and reproduce exactly.
2. Every measured field is accepted, transformed, quarantined, deprecated, or rejected with reason; protected temporal/evidence fields are not weakened to accommodate dirty data.
3. All entity-bearing domains have measured key quality and a declared resolution strategy; unusable partitions remain enumerated rather than silently dropped.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_entity_governance.py — Run as a regression check after completing POST-SUBTASK-036; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_entities.py — Run as a regression check after completing POST-SUBTASK-036; retain command, exit code, and relevant output.
- END_TO_END / END_TO_END: artifacts/entities/schema_readiness_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/entities/schema_readiness_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## End-to-end handoff

Real raw populations produce versioned schema/missingness contracts and an explicit readiness decision for resolution. The gate decision must explicitly reevaluate downstream issues: POST-STORY-013, POST-SUBTASK-037, POST-SUBTASK-038, POST-SUBTASK-039.

## Stop instead of improvising when

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Completion protocol

1. Produce an acceptance-evidence matrix for every criterion.
2. Run every applicable validation entry; implement each declared new automated test.
3. Hash and register every output and all source/data/code/config/tool/runtime identities.
4. Preserve negative, null, blocked, and failed results.
5. Confirm that the claimed maturity—not merely code or files—exists.
6. Update canonical/local Jira state and live Jira operational fields according to `jira/SYNC_CONTRACT.md`.
7. Rebuild all derivatives with `python -B jira/tools/rebuild_all_derivatives.py`.
8. Recompute READY/BLOCKED state and run `python -B jira/tools/validate_second_pass.py`.
9. Reevaluate every downstream issue in `blocks`.
