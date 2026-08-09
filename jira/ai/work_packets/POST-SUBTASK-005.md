# AI Work Packet — POST-SUBTASK-005

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Define and validate the non-repository credential inventory and redaction rules

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-002: Local data, artifact, and secret boundary bootstrap.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-002 (Local data, artifact, and secret boundary bootstrap): Define and validate the non-repository credential inventory and redaction rules. Consume only verified prerequisite outputs from `POST-SUBTASK-001`, `POST-SUBTASK-004`. Produce `artifacts/implementation_preflight/credential_inventory.redacted.json`, `docs/operations/CREDENTIALS_AND_SECRETS.md`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-006.

### In scope

- Perform the exact action: Define and validate the non-repository credential inventory and redaction rules.
- Consume only verified prerequisite outputs from `POST-SUBTASK-001`, `POST-SUBTASK-004`.
- Demonstrate with saved evidence: Every credential is referenced by environment-variable name only.
- Demonstrate with saved evidence: No token, password, session cookie, or restricted URL is written to the repository or evidence logs.
- Demonstrate with saved evidence: A redaction test demonstrates that representative secret values are removed from logs and exception messages.
- Produce, validate, content-hash, and register `artifacts/implementation_preflight/credential_inventory.redacted.json`.
- Produce, validate, content-hash, and register `docs/operations/CREDENTIALS_AND_SECRETS.md`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository; Validate target storage permissions, free space, atomic writes, and quarantine behavior.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.

## Current gate state

- Workflow: `DONE`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `VERIFIED`
- Governance traceability gate: `POST-SUBTASK-009`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-005_define_and_validate_the_non_repository_credential_inventory_and_redaction_rules.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-005.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-005`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/operations/benchmark.py
- docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md
- docs/operations/TARGET_HARDWARE_BENCHMARK.md

## Dependencies that must already be complete

- POST-SUBTASK-001
- POST-SUBTASK-004

## Files I may modify or create

- docs/operations/CREDENTIALS_AND_SECRETS.md
- artifacts/implementation_preflight/credential_inventory.redacted.json
- artifacts/jira_evidence/POST-SUBTASK-005.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- operations-security
- environment

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

- artifacts/implementation_preflight/credential_inventory.redacted.json
- docs/operations/CREDENTIALS_AND_SECRETS.md

## Acceptance criteria

1. Every credential is referenced by environment-variable name only.
2. No token, password, session cookie, or restricted URL is written to the repository or evidence logs.
3. A redaction test demonstrates that representative secret values are removed from logs and exception messages.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w23_operations.py — Run as a regression check after completing POST-SUBTASK-005; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w23_operations.py — Run as a regression check after completing POST-SUBTASK-005; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_repository.py — Run as a regression check after completing POST-SUBTASK-005; retain command, exit code, and relevant output.
- SECURITY / SECURITY: artifacts/implementation_preflight/credential_inventory.redacted.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- END_TO_END / END_TO_END: docs/operations/CREDENTIALS_AND_SECRETS.md — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/implementation_preflight/credential_inventory.redacted.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `docs/operations/CREDENTIALS_AND_SECRETS.md` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.

## End-to-end handoff

Validate that `artifacts/implementation_preflight/credential_inventory.redacted.json`, `docs/operations/CREDENTIALS_AND_SECRETS.md` can be parsed and consumed by `POST-SUBTASK-006` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
