# AI Work Packet — POST-SUBTASK-019

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Define credential names, scopes, owners, rotation, and non-repository storage contract

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-007: Credential configuration and access smoke tests.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-007 (Credential configuration and access smoke tests): Define credential names, scopes, owners, rotation, and non-repository storage contract. Consume only verified prerequisite outputs from `POST-SUBTASK-015`. Produce `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md`, `artifacts/source_governance/credential_contract.redacted.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-020.

### In scope

- Perform the exact action: Define credential names, scopes, owners, rotation, and non-repository storage contract.
- Consume only verified prerequisite outputs from `POST-SUBTASK-015`.
- Demonstrate with saved evidence: Credential variables are source-scoped and least-privilege where the provider supports scopes.
- Demonstrate with saved evidence: Rotation/revocation ownership and expiry handling are documented.
- Demonstrate with saved evidence: No credential value appears in Git-tracked files or evidence.
- Produce, validate, content-hash, and register `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md`.
- Produce, validate, content-hash, and register `artifacts/source_governance/credential_contract.redacted.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Run authenticated and no-key source access smoke tests with rate-limit capture; Validate access readiness and generate source-specific unblock conditions.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `CONTRACT_DEFINED` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-024`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-019_define_credential_names_scopes_owners_rotation_and_non_repository_storage_contra.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-019.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-019`.
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

## Files I may modify or create

- docs/operations/SOURCE_CREDENTIAL_CONTRACT.md
- artifacts/source_governance/credential_contract.redacted.json
- artifacts/jira_evidence/POST-SUBTASK-019.json

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

- docs/operations/SOURCE_CREDENTIAL_CONTRACT.md
- artifacts/source_governance/credential_contract.redacted.json

## Acceptance criteria

1. Credential variables are source-scoped and least-privilege where the provider supports scopes.
2. Rotation/revocation ownership and expiry handling are documented.
3. No credential value appears in Git-tracked files or evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_data_research.py — Run as a regression check after completing POST-SUBTASK-019; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_repository.py — Run as a regression check after completing POST-SUBTASK-019; retain command, exit code, and relevant output.
- SECURITY / SECURITY: docs/operations/SOURCE_CREDENTIAL_CONTRACT.md — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- END_TO_END / END_TO_END: artifacts/source_governance/credential_contract.redacted.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `artifacts/source_governance/credential_contract.redacted.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.

## End-to-end handoff

Validate that `docs/operations/SOURCE_CREDENTIAL_CONTRACT.md`, `artifacts/source_governance/credential_contract.redacted.json` can be parsed and consumed by `POST-SUBTASK-020` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
