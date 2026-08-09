# AI Work Packet — POST-SUBTASK-001

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Verify W25 repository identity, manifests, and no-Wave-26 state

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-001: Canonical handoff and target-environment preflight.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-001 (Canonical handoff and target-environment preflight): Verify W25 repository identity, manifests, and no-Wave-26 state. Begin from the verified repository/current-state contract and the exact source sections in this issue manifest. Produce `artifacts/implementation_preflight/repository_identity.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-002.

### In scope

- Perform the exact action: Verify W25 repository identity, manifests, and no-Wave-26 state.
- Begin from the verified repository/current-state contract and the exact source sections in this issue manifest.
- Demonstrate with saved evidence: The recorded repository hash and project identity match the W25 handoff.
- Demonstrate with saved evidence: The preflight explicitly records that the next state is CODEX_IMPLEMENTATION_HANDOFF and no Wave 26 is created.
- Demonstrate with saved evidence: Any manifest mismatch fails closed before mutation.
- Produce, validate, content-hash, and register `artifacts/implementation_preflight/repository_identity.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Run the full unit and governance validator suite on the target host; Capture the authoritative target runtime and dependency manifest.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `PARTIAL`
- Governance traceability gate: `POST-SUBTASK-009`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-001_verify_w25_repository_identity_manifests_and_no_wave_26_state.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-001.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-001`.
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
- tools/capture_runtime_manifest.py

## Dependencies that must already be complete

- None.

## Files I may modify or create

- artifacts/implementation_preflight/repository_identity.json
- artifacts/jira_evidence/POST-SUBTASK-001.json

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

- artifacts/implementation_preflight/repository_identity.json

## Acceptance criteria

1. The recorded repository hash and project identity match the W25 handoff.
2. The preflight explicitly records that the next state is CODEX_IMPLEMENTATION_HANDOFF and no Wave 26 is created.
3. Any manifest mismatch fails closed before mutation.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w23_operations.py — Run as a regression check after completing POST-SUBTASK-001; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_repository.py — Run as a regression check after completing POST-SUBTASK-001; retain command, exit code, and relevant output.
- END_TO_END / END_TO_END: artifacts/implementation_preflight/repository_identity.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/implementation_preflight/repository_identity.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## End-to-end handoff

Validate that `artifacts/implementation_preflight/repository_identity.json` can be parsed and consumed by `POST-SUBTASK-002` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
