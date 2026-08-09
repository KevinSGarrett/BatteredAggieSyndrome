# AI Work Packet — POST-SUBTASK-023

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Implement compliant retries, caching, rate-limit handling, and fallback activation

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-008: Production acquisition contracts, rate limits, fallbacks, and drift hooks.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-008 (Production acquisition contracts, rate limits, fallbacks, and drift hooks): Implement compliant retries, caching, rate-limit handling, and fallback activation. Consume only verified prerequisite outputs from `POST-SUBTASK-018`, `POST-SUBTASK-021`, `POST-SUBTASK-022`. Produce `artifacts/source_governance/acquisition_resilience_test.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-024.

### In scope

- Perform the exact action: Implement compliant retries, caching, rate-limit handling, and fallback activation.
- Consume only verified prerequisite outputs from `POST-SUBTASK-018`, `POST-SUBTASK-021`, `POST-SUBTASK-022`.
- Demonstrate with saved evidence: Retries honor provider rate limits and bounded backoff.
- Demonstrate with saved evidence: Cached raw responses remain immutable and are keyed by request/source identity.
- Demonstrate with saved evidence: Fallbacks activate only under documented conditions and preserve source provenance.
- Produce, validate, content-hash, and register `artifacts/source_governance/acquisition_resilience_test.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Create source-specific endpoint, parameter, pagination, season, and version acquisition specifications; Establish source API/schema/terms drift baselines and monitoring inputs.

## Current gate state

- Workflow: `READY`
- Ready: `true`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `DATA_MATERIALIZATION`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `CONTRACT_DEFINED` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-024`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-023_implement_compliant_retries_caching_rate_limit_handling_and_fallback_activation.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-023.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-023`.
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
- src/aggie_analytics/data/snapshots.py
- tests/test_acquisition_resilience.py
- docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md

## Dependencies that must already be complete

- POST-SUBTASK-018
- POST-SUBTASK-021
- POST-SUBTASK-022

## Files I may modify or create

- src/aggie_analytics/data/adapters.py
- src/aggie_analytics/data/snapshots.py
- tests/test_acquisition_resilience.py
- artifacts/source_governance/acquisition_resilience_test.json
- artifacts/jira_evidence/POST-SUBTASK-023.json

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

- artifacts/source_governance/acquisition_resilience_test.json

## Acceptance criteria

1. Retries honor provider rate limits and bounded backoff.
2. Cached raw responses remain immutable and are keyed by request/source identity.
3. Fallbacks activate only under documented conditions and preserve source provenance.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_data_research.py — Run as a regression check after completing POST-SUBTASK-023; retain command, exit code, and relevant output.
- INTEGRATION / INTEGRATION: artifacts/source_governance/acquisition_resilience_test.json — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- NEW_AUTOMATED_TEST_REQUIRED / NEW_AUTOMATED_TEST_REQUIRED: NEW_TEST_REQUIRED::POST-SUBTASK-023 — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Evidence to return

- `artifacts/source_governance/acquisition_resilience_test.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## End-to-end handoff

Validate that `artifacts/source_governance/acquisition_resilience_test.json` can be parsed and consumed by `POST-SUBTASK-024` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

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
