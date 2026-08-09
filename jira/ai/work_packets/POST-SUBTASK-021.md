# AI Work Packet — POST-SUBTASK-021

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate access readiness and generate source-specific unblock conditions

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-007: Credential configuration and access smoke tests.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-007 (Credential configuration and access smoke tests): Validate access readiness and generate source-specific unblock conditions. Consume only verified prerequisite outputs from `POST-SUBTASK-015`, `POST-SUBTASK-019`, `POST-SUBTASK-020`. Produce `artifacts/source_governance/source_access_readiness.csv`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate access readiness and generate source-specific unblock conditions.
- Consume only verified prerequisite outputs from `POST-SUBTASK-015`, `POST-SUBTASK-019`, `POST-SUBTASK-020`.
- Demonstrate with saved evidence: Every required source is READY, BLOCKED_CREDENTIAL, BLOCKED_RIGHTS, BLOCKED_PROVIDER, or REJECTED with a concrete reason.
- Demonstrate with saved evidence: Downstream materialization tasks consume this readiness file.
- Demonstrate with saved evidence: A source cannot become READY from a successful sample if rights review is incomplete.
- Produce, validate, content-hash, and register `artifacts/source_governance/source_access_readiness.csv`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Define credential names, scopes, owners, rotation, and non-repository storage contract; Run authenticated and no-key source access smoke tests with rate-limit capture.
- Automatically granting legal approval, assuming public accessibility permits retention/redistribution, or bypassing human terms review.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `CONTRACT_DEFINED` → `INTEGRATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-024`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-021_validate_access_readiness_and_generate_source_specific_unblock_conditions.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-021.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-021`.
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
- POST-SUBTASK-019
- POST-SUBTASK-020

## Files I may modify or create

- artifacts/source_governance/source_access_readiness.csv
- artifacts/jira_evidence/POST-SUBTASK-021.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

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

Produce and validate these outputs within this atomic work unit:

- artifacts/source_governance/source_access_readiness.csv

## Acceptance criteria

1. Every required source is READY, BLOCKED_CREDENTIAL, BLOCKED_RIGHTS, BLOCKED_PROVIDER, or REJECTED with a concrete reason.
2. Downstream materialization tasks consume this readiness file.
3. A source cannot become READY from a successful sample if rights review is incomplete.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_data_research.py — Run as a regression check after completing POST-SUBTASK-021; retain command, exit code, and relevant output.
- LEGAL_RIGHTS_REVIEW / LEGAL_RIGHTS_REVIEW: MANUAL_REVIEW_REQUIRED — A named human reviewer records source-specific access, retention, training, publication, and redistribution decisions with terms/version/date evidence.
- MANUAL / MANUAL: artifacts/source_governance/source_access_readiness.csv — Verify reviewer identity, decision date, unresolved questions, and explicit allow/block conditions.
- SECURITY / SECURITY: artifacts/source_governance/source_access_readiness.csv — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- END_TO_END / END_TO_END: artifacts/source_governance/source_access_readiness.csv — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/source_governance/source_access_readiness.csv` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.

## End-to-end handoff

Exercise the complete Credential configuration and access smoke tests path and verify downstream consumption of pinned outputs. The gate decision must explicitly reevaluate downstream issues: POST-STORY-008, POST-STORY-009, POST-SUBTASK-022, POST-SUBTASK-023, POST-SUBTASK-024, POST-SUBTASK-025, POST-SUBTASK-026, POST-SUBTASK-027.

## Stop instead of improvising when

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

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
