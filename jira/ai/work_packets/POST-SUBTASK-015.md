# AI Work Packet — POST-SUBTASK-015

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate source inventory completeness and unresolved decision coverage

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-005: Reconcile the final source universe and authority decisions.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-005 (Reconcile the final source universe and authority decisions): Validate source inventory completeness and unresolved decision coverage. Consume only verified prerequisite outputs from `POST-SUBTASK-013`, `POST-SUBTASK-014`. Produce `artifacts/source_governance/source_inventory_validation.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate source inventory completeness and unresolved decision coverage.
- Consume only verified prerequisite outputs from `POST-SUBTASK-013`, `POST-SUBTASK-014`.
- Demonstrate with saved evidence: All source IDs referenced by adapters, registries, and acquisition plans resolve to the production inventory.
- Demonstrate with saved evidence: Every unresolved technical or quality decision has a Jira action or scoped quarantine.
- Demonstrate with saved evidence: No required domain is silently marked complete when only reconnaissance samples exist.
- Produce, validate, content-hash, and register `artifacts/source_governance/source_inventory_validation.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Reconcile W06 source inventory with W24 refresh and current handoff gaps; Freeze source priority, fallback, and required-versus-optional classifications.

## Current gate state

- Workflow: `DONE`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `CONTRACT_DEFINED` → `CONTRACT_DEFINED`
- Evidence state: `VERIFIED`
- Governance traceability gate: `POST-SUBTASK-024`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-015_validate_source_inventory_completeness_and_unresolved_decision_coverage.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-015.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-015`.
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

- POST-SUBTASK-013
- POST-SUBTASK-014

## Files I may modify or create

- artifacts/source_governance/source_inventory_validation.json
- artifacts/jira_evidence/POST-SUBTASK-015.json

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

- artifacts/source_governance/source_inventory_validation.json

## Acceptance criteria

1. All source IDs referenced by adapters, registries, and acquisition plans resolve to the production inventory.
2. Every unresolved technical or quality decision has a Jira action or scoped quarantine.
3. No required domain is silently marked complete when only reconnaissance samples exist.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_data_research.py — Run as a regression check after completing POST-SUBTASK-015; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: artifacts/source_governance/source_inventory_validation.json — Run as a regression check after completing POST-SUBTASK-015; retain command, exit code, and relevant output.
- END_TO_END / END_TO_END: artifacts/source_governance/source_inventory_validation.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/source_governance/source_inventory_validation.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## End-to-end handoff

Exercise the complete Reconcile the final source universe and authority decisions path and verify downstream consumption of pinned outputs. The gate decision must explicitly reevaluate downstream issues: POST-STORY-006, POST-STORY-007, POST-SUBTASK-016, POST-SUBTASK-017, POST-SUBTASK-018, POST-SUBTASK-019, POST-SUBTASK-020, POST-SUBTASK-021.

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
