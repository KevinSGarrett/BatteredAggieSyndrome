# AI Work Packet — POST-SUBTASK-012

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Implement and test resource stop conditions and graceful degradation

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-004: Evidence-backed resource, concurrency, and degradation envelope.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-004 (Evidence-backed resource, concurrency, and degradation envelope): Implement and test resource stop conditions and graceful degradation. Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-010`, `POST-SUBTASK-011`. Produce `artifacts/benchmarks/resource_stop_condition_test.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Implement and test resource stop conditions and graceful degradation.
- Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-010`, `POST-SUBTASK-011`.
- Demonstrate with saved evidence: Peak-RAM, free-space, runtime, and concurrency breaches stop or defer work predictably.
- Demonstrate with saved evidence: The system does not silently downsample protected evaluation or omit required data.
- Demonstrate with saved evidence: The operator receives a clear blocker, recovery action, and preserved partial evidence.
- Produce, validate, content-hash, and register `artifacts/benchmarks/resource_stop_condition_test.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Measure safe local worktree and pipeline concurrency under target resource limits; Measure disk growth and define evidence-backed artifact retention budgets.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `OPERATIONS`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `OPERATING`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-009`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-012_implement_and_test_resource_stop_conditions_and_graceful_degradation.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-012.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-012`.
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

- POST-SUBTASK-009
- POST-SUBTASK-010
- POST-SUBTASK-011

## Files I may modify or create

- tools/capture_runtime_manifest.py
- artifacts/benchmarks/resource_stop_condition_test.json
- artifacts/jira_evidence/POST-SUBTASK-012.json

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

- artifacts/benchmarks/resource_stop_condition_test.json

## Acceptance criteria

1. Peak-RAM, free-space, runtime, and concurrency breaches stop or defer work predictably.
2. The system does not silently downsample protected evaluation or omit required data.
3. The operator receives a clear blocker, recovery action, and preserved partial evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w23_operations.py — Run as a regression check after completing POST-SUBTASK-012; retain command, exit code, and relevant output.
- BENCHMARK / BENCHMARK: artifacts/benchmarks/resource_stop_condition_test.json — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- END_TO_END / END_TO_END: artifacts/benchmarks/resource_stop_condition_test.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/benchmarks/resource_stop_condition_test.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.

## End-to-end handoff

Autonomous work respects measured CPU/RAM/disk/concurrency limits and fails safely without corrupting state or weakening evaluation. The gate decision must explicitly record that no downstream issue is silently unlocked.

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
