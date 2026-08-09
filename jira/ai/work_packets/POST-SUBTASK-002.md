# AI Work Packet — POST-SUBTASK-002

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Run the full unit and governance validator suite on the target host

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-001: Canonical handoff and target-environment preflight.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-001 (Canonical handoff and target-environment preflight): Run the full unit and governance validator suite on the target host. Consume only verified prerequisite outputs from `POST-SUBTASK-001`. Produce `artifacts/implementation_preflight/target_validation_results.json`, `artifacts/implementation_preflight/target_validation.log`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-003.

### In scope

- Perform the exact action: Run the full unit and governance validator suite on the target host.
- Consume only verified prerequisite outputs from `POST-SUBTASK-001`.
- Demonstrate with saved evidence: All 229 baseline unit tests are executed and results are recorded without editing expected outcomes.
- Demonstrate with saved evidence: W25 final, acceptance, backlog, and strict repository validators run from a clean checkout.
- Demonstrate with saved evidence: Failures are recorded as blockers; they are not waived or hidden.
- Produce, validate, content-hash, and register `artifacts/implementation_preflight/target_validation_results.json`.
- Produce, validate, content-hash, and register `artifacts/implementation_preflight/target_validation.log`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Verify W25 repository identity, manifests, and no-Wave-26 state; Capture the authoritative target runtime and dependency manifest.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `VALIDATION`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `OPERATIONS`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `PARTIAL`
- Governance traceability gate: `POST-SUBTASK-009`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-002_run_the_full_unit_and_governance_validator_suite_on_the_target_host.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-002.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-002`.
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

## Files I may modify or create

- artifacts/implementation_preflight/target_validation_results.json
- artifacts/implementation_preflight/target_validation.log
- artifacts/jira_evidence/POST-SUBTASK-002.json

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

- artifacts/implementation_preflight/target_validation_results.json
- artifacts/implementation_preflight/target_validation.log

## Acceptance criteria

1. All 229 baseline unit tests are executed and results are recorded without editing expected outcomes.
2. W25 final, acceptance, backlog, and strict repository validators run from a clean checkout.
3. Failures are recorded as blockers; they are not waived or hidden.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w23_operations.py — Run as a regression check after completing POST-SUBTASK-002; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_repository.py — Run as a regression check after completing POST-SUBTASK-002; retain command, exit code, and relevant output.
- BENCHMARK / BENCHMARK: artifacts/implementation_preflight/target_validation_results.json — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- SCIENTIFIC / SCIENTIFIC: artifacts/implementation_preflight/target_validation_results.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- INTEGRATION / INTEGRATION: artifacts/implementation_preflight/target_validation_results.json — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/implementation_preflight/target_validation_results.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `artifacts/implementation_preflight/target_validation.log` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/implementation_preflight/target_validation_results.json`, `artifacts/implementation_preflight/target_validation.log` can be parsed and consumed by `POST-SUBTASK-003` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
