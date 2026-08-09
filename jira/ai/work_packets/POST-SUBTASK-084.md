# AI Work Packet — POST-SUBTASK-084

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate peer/analog anti-selection, tuning lift/stability/uncertainty, and seal admissible candidates plus the no-adjustment fallback

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-028: Peers, regimes, historical analogs, and specialization candidates.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-028 (Peers, regimes, historical analogs, and specialization candidates): Validate peer/analog anti-selection, tuning lift/stability/uncertainty, and seal admissible candidates plus the no-adjustment fallback. Consume only verified prerequisite outputs from `POST-SUBTASK-078`, `POST-SUBTASK-081`, `POST-SUBTASK-082`, `POST-SUBTASK-083`. Produce `artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate peer/analog anti-selection, tuning lift/stability/uncertainty, and seal admissible candidates plus the no-adjustment fallback.
- Consume only verified prerequisite outputs from `POST-SUBTASK-078`, `POST-SUBTASK-081`, `POST-SUBTASK-082`, `POST-SUBTASK-083`.
- Demonstrate with saved evidence: Peer/regime/analog definitions use only pinned pregame features, exclude same/future outcomes, expose distance/sample/uncertainty, and retain alternative sensitivity specifications.
- Demonstrate with saved evidence: Every candidate includes global-only/no adjustment, uses shrinkage/minimum data, avoids protected A&M outcomes and favorable-regime selection, and preserves null/negative/unstable tuning evidence.
- Demonstrate with saved evidence: Outcome-label removal/future-append stability and multiple-comparison diagnostics pass; only precommitted candidates are sealed and no candidate is labeled production-improving yet.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Materialize pregame-observable peer/regime candidates and prior-only historical analog index with distance diagnostics; Train global-only, no-adjustment, residual, hierarchical, calibration, shrinkage, and feature-interaction A&M candidates on permitted history.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `false`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-087`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-084_validate_peer_analog_anti_selection_tuning_lift_stability_uncertainty_and_seal_a.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-084.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-084`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_tamu_specialization_governance.py
- src/aggie_analytics/tamu/specialization.py
- src/aggie_analytics/tamu/state.py
- docs/40_TEXAS_AM_SPECIALIZATION_ARCHITECTURE.md
- docs/43_TAMU_SPECIALIZATION_CANDIDATES_AND_OVERFIT_GUARDS.md
- docs/41_TAMU_HIGH_RESOLUTION_STATE.md
- docs/42_TAMU_PEERS_ANALOGS_AND_SNAPSHOTS.md

## Dependencies that must already be complete

- POST-SUBTASK-078
- POST-SUBTASK-081
- POST-SUBTASK-082
- POST-SUBTASK-083

## Files I may modify or create

- artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json
- artifacts/jira_evidence/POST-SUBTASK-084.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- tamu-specialization
- tamu

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

- artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json

## Acceptance criteria

1. Peer/regime/analog definitions use only pinned pregame features, exclude same/future outcomes, expose distance/sample/uncertainty, and retain alternative sensitivity specifications.
2. Every candidate includes global-only/no adjustment, uses shrinkage/minimum data, avoids protected A&M outcomes and favorable-regime selection, and preserves null/negative/unstable tuning evidence.
3. Outcome-label removal/future-append stability and multiple-comparison diagnostics pass; only precommitted candidates are sealed and no candidate is labeled production-improving yet.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_tamu_specialization_governance.py — Run as a regression check after completing POST-SUBTASK-084; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_tamu_specialization.py — Run as a regression check after completing POST-SUBTASK-084; retain command, exit code, and relevant output.
- END_TO_END / END_TO_END: artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/tamu/TAMU_CANDIDATE_REGISTRY.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## End-to-end handoff

A&M candidates and peer/analog definitions are frozen before protected outcomes and always retain a valid global-only/no-adjustment choice. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-010, POST-EPIC-011, POST-STORY-029, POST-STORY-031, POST-STORY-033, POST-SUBTASK-085, POST-SUBTASK-086, POST-SUBTASK-087, POST-SUBTASK-091, POST-SUBTASK-092, POST-SUBTASK-093, POST-SUBTASK-097….

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
