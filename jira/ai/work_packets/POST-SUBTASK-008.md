# AI Work Packet — POST-SUBTASK-008

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Run scripts/benchmark_target.ps1 on the declared Windows/Ryzen 7 HX/32 GB/RTX 5060/NVMe target

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-003: Authoritative target-hardware benchmark and threshold governance.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-003 (Authoritative target-hardware benchmark and threshold governance): Run scripts/benchmark_target.ps1 on the declared Windows/Ryzen 7 HX/32 GB/RTX 5060/NVMe target. Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-006`, `POST-SUBTASK-007`. Produce `artifacts/benchmarks/ac038_target_benchmark.json`, `artifacts/benchmarks/ac038_target_benchmark.log`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-009.

### In scope

- Perform the exact action: Run scripts/benchmark_target.ps1 on the declared Windows/Ryzen 7 HX/32 GB/RTX 5060/NVMe target.
- Consume only verified prerequisite outputs from `POST-SUBTASK-002`, `POST-SUBTASK-006`, `POST-SUBTASK-007`.
- Demonstrate with saved evidence: The benchmark is executed on the declared target rather than a substitute host.
- Demonstrate with saved evidence: Peak RAM, runtime, CPU/GPU utilization, disk usage, and workload identity are captured.
- Demonstrate with saved evidence: At least one repeat run verifies that the result is not a one-off artifact.
- Produce, validate, content-hash, and register `artifacts/benchmarks/ac038_target_benchmark.json`.
- Produce, validate, content-hash, and register `artifacts/benchmarks/ac038_target_benchmark.log`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Stage the representative AC-038 workload and benchmark input manifest; Govern THR-011 and THR-012 values and clear or retain the W23 local-production gate.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-009`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-008_run_scripts_benchmark_target_ps1_on_the_declared_windows_ryzen_7_hx_32_gb_rtx_50.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-008.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-008`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/IMPLEMENTATION_WBS.csv
- src/aggie_analytics/operations/benchmark.py
- scripts/benchmark_target.ps1
- docs/operations/TARGET_HARDWARE_BENCHMARK.md
- tools/capture_runtime_manifest.py

## Dependencies that must already be complete

- POST-SUBTASK-002
- POST-SUBTASK-006
- POST-SUBTASK-007

## Files I may modify or create

- artifacts/benchmarks/ac038_target_benchmark.json
- artifacts/benchmarks/ac038_target_benchmark.log
- artifacts/jira_evidence/POST-SUBTASK-008.json

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

- artifacts/benchmarks/ac038_target_benchmark.json
- artifacts/benchmarks/ac038_target_benchmark.log

## Acceptance criteria

1. The benchmark is executed on the declared target rather than a substitute host.
2. Peak RAM, runtime, CPU/GPU utilization, disk usage, and workload identity are captured.
3. At least one repeat run verifies that the result is not a one-off artifact.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w23_operations.py — Run as a regression check after completing POST-SUBTASK-008; retain command, exit code, and relevant output.
- BENCHMARK / BENCHMARK: artifacts/benchmarks/ac038_target_benchmark.json — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- END_TO_END / END_TO_END: artifacts/benchmarks/ac038_target_benchmark.log — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/benchmarks/ac038_target_benchmark.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `artifacts/benchmarks/ac038_target_benchmark.log` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.

## End-to-end handoff

Validate that `artifacts/benchmarks/ac038_target_benchmark.json`, `artifacts/benchmarks/ac038_target_benchmark.log` can be parsed and consumed by `POST-SUBTASK-009` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
