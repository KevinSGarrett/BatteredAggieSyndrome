# AI Work Packet — POST-SUBTASK-011

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Measure disk growth and define evidence-backed artifact retention budgets

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-004: Evidence-backed resource, concurrency, and degradation envelope.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-004 (Evidence-backed resource, concurrency, and degradation envelope): Measure disk growth and define evidence-backed artifact retention budgets. Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-010`. Produce `artifacts/benchmarks/storage_growth_profile.json`, `docs/operations/LOCAL_RESOURCE_ENVELOPE.md`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-012.

### In scope

- Perform the exact action: Measure disk growth and define evidence-backed artifact retention budgets.
- Consume only verified prerequisite outputs from `POST-SUBTASK-009`, `POST-SUBTASK-010`.
- Demonstrate with saved evidence: Raw snapshots, matrices, model artifacts, forecasts, logs, and backups are measured separately.
- Demonstrate with saved evidence: Retention recommendations preserve required lineage and protected evidence.
- Demonstrate with saved evidence: Deletion rules never remove canonical negative results or source-rights evidence.
- Produce, validate, content-hash, and register `artifacts/benchmarks/storage_growth_profile.json`.
- Produce, validate, content-hash, and register `docs/operations/LOCAL_RESOURCE_ENVELOPE.md`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Measure safe local worktree and pipeline concurrency under target resource limits; Implement and test resource stop conditions and graceful degradation.
- Automatically granting legal approval, assuming public accessibility permits retention/redistribution, or bypassing human terms review.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `OPERATIONS`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-009`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-011_measure_disk_growth_and_define_evidence_backed_artifact_retention_budgets.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-011.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-011`.
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

- POST-SUBTASK-009
- POST-SUBTASK-010

## Files I may modify or create

- docs/operations/LOCAL_RESOURCE_ENVELOPE.md
- artifacts/benchmarks/storage_growth_profile.json
- artifacts/jira_evidence/POST-SUBTASK-011.json

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

- artifacts/benchmarks/storage_growth_profile.json
- docs/operations/LOCAL_RESOURCE_ENVELOPE.md

## Acceptance criteria

1. Raw snapshots, matrices, model artifacts, forecasts, logs, and backups are measured separately.
2. Retention recommendations preserve required lineage and protected evidence.
3. Deletion rules never remove canonical negative results or source-rights evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w23_operations.py — Run as a regression check after completing POST-SUBTASK-011; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w23_operations.py — Run as a regression check after completing POST-SUBTASK-011; retain command, exit code, and relevant output.
- BENCHMARK / BENCHMARK: artifacts/benchmarks/storage_growth_profile.json — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- SCIENTIFIC / SCIENTIFIC: artifacts/benchmarks/storage_growth_profile.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- OPERATIONS / OPERATIONS: artifacts/benchmarks/storage_growth_profile.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- STATIC_VALIDATION / STATIC_VALIDATION: artifacts/benchmarks/storage_growth_profile.json — Validate schema, required fields, unique identifiers, cross-references, provenance, and explicit unresolved states.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/benchmarks/storage_growth_profile.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `docs/operations/LOCAL_RESOURCE_ENVELOPE.md` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/benchmarks/storage_growth_profile.json`, `docs/operations/LOCAL_RESOURCE_ENVELOPE.md` can be parsed and consumed by `POST-SUBTASK-012` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
