# AI Work Packet — POST-SUBTASK-087

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-029: Protected A&M lift, calibration, stability, and integration decision.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-029 (Protected A&M lift, calibration, stability, and integration decision): Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently. Consume only verified prerequisite outputs from `POST-SUBTASK-084`, `POST-SUBTASK-085`, `POST-SUBTASK-086`, `POST-SUBTASK-102`. Produce `artifacts/tamu/tamu_specialization_decision.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Publish the protected A&M specialization admission or no-adjustment decision and integrate it consistently.
- Consume only verified prerequisite outputs from `POST-SUBTASK-084`, `POST-SUBTASK-085`, `POST-SUBTASK-086`, `POST-SUBTASK-102`.
- Demonstrate with saved evidence: Sealed candidates receive identical games, cutoffs, state, missingness, metrics, and no post-hoc changes; partial failures preserve evidence without feeding outcomes back to tuning.
- Demonstrate with saved evidence: Evaluation reports confidence/sample/segments and accepts null, negative, unstable, or harmful results without subgroup shopping, relabeling, or unsupported causal claims.
- Demonstrate with saved evidence: The signed decision admits only bounded supported specialization or selects global-only/no adjustment, updates model/product semantics, preserves rejected evidence, and closes GAP-009 only empirically.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/tamu/tamu_specialization_decision.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Generate sealed global-only and A&M candidate predictions inside identical protected chronological replay; Measure incremental accuracy, calibration, stability, uncertainty, data-quality sensitivity, and multiple-comparison context.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

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

1. `jira/records/issues/subtasks/POST-SUBTASK-087_publish_the_protected_a_and_m_specialization_admission_or_no_adjustment_decision.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-087.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-087`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/ADR_INDEX.csv
- governance/REQUIREMENTS_INDEX.csv
- tests/test_tamu_specialization_governance.py
- docs/43_TAMU_SPECIALIZATION_CANDIDATES_AND_OVERFIT_GUARDS.md
- docs/41_TAMU_HIGH_RESOLUTION_STATE.md
- src/aggie_analytics/tamu/specialization.py
- src/aggie_analytics/tamu/state.py

## Dependencies that must already be complete

- POST-SUBTASK-084
- POST-SUBTASK-085
- POST-SUBTASK-086
- POST-SUBTASK-102

## Files I may modify or create

- artifacts/tamu/tamu_specialization_decision.json
- artifacts/jira_evidence/POST-SUBTASK-087.json

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

- artifacts/tamu/tamu_specialization_decision.json

## Acceptance criteria

1. Sealed candidates receive identical games, cutoffs, state, missingness, metrics, and no post-hoc changes; partial failures preserve evidence without feeding outcomes back to tuning.
2. Evaluation reports confidence/sample/segments and accepts null, negative, unstable, or harmful results without subgroup shopping, relabeling, or unsupported causal claims.
3. The signed decision admits only bounded supported specialization or selects global-only/no adjustment, updates model/product semantics, preserves rejected evidence, and closes GAP-009 only empirically.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_tamu_specialization_governance.py — Run as a regression check after completing POST-SUBTASK-087; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w20_model_starter.py — Run as a regression check after completing POST-SUBTASK-087; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_tamu_specialization.py — Run as a regression check after completing POST-SUBTASK-087; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/tamu/tamu_specialization_decision.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/tamu/tamu_specialization_decision.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- END_TO_END / END_TO_END: artifacts/tamu/tamu_specialization_decision.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/tamu/tamu_specialization_decision.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

An identical sealed replay yields an auditable A&M-specialization-or-no-adjustment decision consumed by the production forecast. The gate decision must explicitly reevaluate downstream issues: POST-STORY-035, POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105.

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
