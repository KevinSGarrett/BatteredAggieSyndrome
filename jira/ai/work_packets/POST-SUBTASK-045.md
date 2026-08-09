# AI Work Packet — POST-SUBTASK-045

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate fail-closed cutoff eligibility and deliberate future/same-game/postgame rejection

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-015: Known-at registry and timestamp normalization.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-015 (Known-at registry and timestamp normalization): Validate fail-closed cutoff eligibility and deliberate future/same-game/postgame rejection. Consume only verified prerequisite outputs from `POST-SUBTASK-042`, `POST-SUBTASK-043`, `POST-SUBTASK-044`. Produce `artifacts/pit/known_at_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate fail-closed cutoff eligibility and deliberate future/same-game/postgame rejection.
- Consume only verified prerequisite outputs from `POST-SUBTASK-042`, `POST-SUBTASK-043`, `POST-SUBTASK-044`.
- Demonstrate with saved evidence: Every candidate input field has an approved temporal class and cutoff rule; realized weather, closing markets, final participation, box scores, and outcomes are excluded from earlier snapshots.
- Demonstrate with saved evidence: Original timestamps are preserved, ambiguity/impossibility is quarantined, and retrieval time is never substituted for publication time when it would make history appear known earlier.
- Demonstrate with saved evidence: All fields entering matrices resolve to approved rules and mutation tests reject same-game, future, postgame, or naming-convention-based eligibility.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/pit/known_at_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Reconcile field temporal classes, source known-at rules, cutoffs, correction policies, and prohibited uses against real schemas; Normalize observed, published, effective, retrieved, and corrected timestamps with source-specific precedence and timezone rules.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-051`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-045_validate_fail_closed_cutoff_eligibility_and_deliberate_future_same_game_postgame.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-045.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-045`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- docs/final/FINAL_RISK_REGISTER.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- tests/test_temporal_governance.py
- tests/test_w24_readiness.py
- src/aggie_analytics/temporal/eligibility.py
- docs/18_POINT_IN_TIME_DATA_ARCHITECTURE.md
- docs/19_ASOF_QUERY_AND_CUTOFF_CONTRACT.md

## Dependencies that must already be complete

- POST-SUBTASK-042
- POST-SUBTASK-043
- POST-SUBTASK-044

## Files I may modify or create

- artifacts/pit/known_at_gate.json
- artifacts/jira_evidence/POST-SUBTASK-045.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- pit-temporal
- pit

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

- artifacts/pit/known_at_gate.json

## Acceptance criteria

1. Every candidate input field has an approved temporal class and cutoff rule; realized weather, closing markets, final participation, box scores, and outcomes are excluded from earlier snapshots.
2. Original timestamps are preserved, ambiguity/impossibility is quarantined, and retrieval time is never substituted for publication time when it would make history appear known earlier.
3. All fields entering matrices resolve to approved rules and mutation tests reject same-game, future, postgame, or naming-convention-based eligibility.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_temporal_governance.py — Run as a regression check after completing POST-SUBTASK-045; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w24_readiness.py — Run as a regression check after completing POST-SUBTASK-045; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_temporal.py — Run as a regression check after completing POST-SUBTASK-045; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/pit/known_at_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/pit/known_at_gate.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- END_TO_END / END_TO_END: artifacts/pit/known_at_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/pit/known_at_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Every value in every pregame horizon has a conservative, testable known-at decision grounded in source timing evidence. The gate decision must explicitly reevaluate downstream issues: POST-STORY-016, POST-SUBTASK-046, POST-SUBTASK-047, POST-SUBTASK-048.

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
