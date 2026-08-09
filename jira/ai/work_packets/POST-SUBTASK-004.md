# AI Work Packet — POST-SUBTASK-004

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-002: Local data, artifact, and secret boundary bootstrap.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-002 (Local data, artifact, and secret boundary bootstrap): Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository. Consume only verified prerequisite outputs from `POST-SUBTASK-001`. Produce `artifacts/implementation_preflight/local_path_contract.json`, `docs/operations/LOCAL_RUNTIME_PATHS.md`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-005.

### In scope

- Perform the exact action: Configure AGGIE_ANALYTICS_DATA_ROOT and artifact roots outside the repository.
- Consume only verified prerequisite outputs from `POST-SUBTASK-001`.
- Demonstrate with saved evidence: Configured roots are absolute, writable, outside the Git repository, and survive process restart.
- Demonstrate with saved evidence: Raw, curated, model, forecast, log, backup, and quarantine roots are separated.
- Demonstrate with saved evidence: A path safety test rejects repository-internal bulk-data roots.
- Produce, validate, content-hash, and register `artifacts/implementation_preflight/local_path_contract.json`.
- Produce, validate, content-hash, and register `docs/operations/LOCAL_RUNTIME_PATHS.md`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Define and validate the non-repository credential inventory and redaction rules; Validate target storage permissions, free space, atomic writes, and quarantine behavior.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `DONE`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `OPERATIONS`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `VERIFIED`
- Governance traceability gate: `POST-SUBTASK-009`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-004_configure_aggie_analytics_data_root_and_artifact_roots_outside_the_repository.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-004.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-004`.
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
- src/aggie_analytics/operations/environment.py
- tests/test_w23_operations.py

## Dependencies that must already be complete

- POST-SUBTASK-001

## Files I may modify or create

- src/aggie_analytics/operations/environment.py
- tests/test_w23_operations.py
- docs/operations/LOCAL_RUNTIME_PATHS.md
- src/aggie_analytics/operations/benchmark.py
- artifacts/implementation_preflight/local_path_contract.json
- artifacts/jira_evidence/POST-SUBTASK-004.json

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

- artifacts/implementation_preflight/local_path_contract.json
- docs/operations/LOCAL_RUNTIME_PATHS.md

## Acceptance criteria

1. Configured roots are absolute, writable, outside the Git repository, and survive process restart.
2. Raw, curated, model, forecast, log, backup, and quarantine roots are separated.
3. A path safety test rejects repository-internal bulk-data roots.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w23_operations.py — Run as a regression check after completing POST-SUBTASK-004; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w23_operations.py — Run as a regression check after completing POST-SUBTASK-004; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_repository.py — Run as a regression check after completing POST-SUBTASK-004; retain command, exit code, and relevant output.
- BENCHMARK / BENCHMARK: artifacts/implementation_preflight/local_path_contract.json — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- SCIENTIFIC / SCIENTIFIC: artifacts/implementation_preflight/local_path_contract.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- OPERATIONS / OPERATIONS: artifacts/implementation_preflight/local_path_contract.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- INTEGRATION / INTEGRATION: artifacts/implementation_preflight/local_path_contract.json — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- NEW_AUTOMATED_TEST_REQUIRED / NEW_AUTOMATED_TEST_REQUIRED: NEW_TEST_REQUIRED::POST-SUBTASK-004 — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Evidence to return

- `artifacts/implementation_preflight/local_path_contract.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `docs/operations/LOCAL_RUNTIME_PATHS.md` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/implementation_preflight/local_path_contract.json`, `docs/operations/LOCAL_RUNTIME_PATHS.md` can be parsed and consumed by `POST-SUBTASK-005` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

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
