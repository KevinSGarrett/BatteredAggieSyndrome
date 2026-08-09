# AI Work Packet — POST-SUBTASK-006

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate target storage permissions, free space, atomic writes, and quarantine behavior

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-002: Local data, artifact, and secret boundary bootstrap.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-002 (Local data, artifact, and secret boundary bootstrap): Validate target storage permissions, free space, atomic writes, and quarantine behavior. Consume only verified prerequisite outputs from `POST-SUBTASK-001`, `POST-SUBTASK-004`, `POST-SUBTASK-005`. Produce `artifacts/implementation_preflight/storage_probe.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate target storage permissions, free space, atomic writes, and quarantine behavior.
- Consume only verified prerequisite outputs from `POST-SUBTASK-001`, `POST-SUBTASK-004`, `POST-SUBTASK-005`.
- Demonstrate with saved evidence: The probe demonstrates atomic create/rename, fsync, readback hash verification, and quarantine moves on each configured root.
- Demonstrate with saved evidence: Available capacity is recorded without inventing a minimum threshold.
- Demonstrate with saved evidence: Insufficient permissions or capacity blocks downstream materialization.
- Produce, validate, content-hash, and register `artifacts/implementation_preflight/storage_probe.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository; Define and validate the non-repository credential inventory and redaction rules.

## Current gate state

- Workflow: `DONE`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `OPERATIONS`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `INTEGRATED`
- Evidence state: `VERIFIED`
- Governance traceability gate: `POST-SUBTASK-009`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-006_validate_target_storage_permissions_free_space_atomic_writes_and_quarantine_beha.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-006.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-006`.
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
- scripts/benchmark_target.ps1

## Dependencies that must already be complete

- POST-SUBTASK-001
- POST-SUBTASK-004
- POST-SUBTASK-005

## Files I may modify or create

- artifacts/implementation_preflight/storage_probe.json
- artifacts/jira_evidence/POST-SUBTASK-006.json

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

- artifacts/implementation_preflight/storage_probe.json

## Acceptance criteria

1. The probe demonstrates atomic create/rename, fsync, readback hash verification, and quarantine moves on each configured root.
2. Available capacity is recorded without inventing a minimum threshold.
3. Insufficient permissions or capacity blocks downstream materialization.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w23_operations.py — Run as a regression check after completing POST-SUBTASK-006; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: artifacts/implementation_preflight/storage_probe.json — Run as a regression check after completing POST-SUBTASK-006; retain command, exit code, and relevant output.
- END_TO_END / END_TO_END: artifacts/implementation_preflight/storage_probe.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/implementation_preflight/storage_probe.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## End-to-end handoff

Exercise the complete Local data, artifact, and secret boundary bootstrap path and verify downstream consumption of pinned outputs. The gate decision must explicitly reevaluate downstream issues: POST-STORY-003, POST-STORY-009, POST-SUBTASK-007, POST-SUBTASK-008, POST-SUBTASK-009, POST-SUBTASK-025, POST-SUBTASK-026, POST-SUBTASK-027.

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
