# AI Work Packet — POST-SUBTASK-109

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Implement season/week/data-drift/performance retraining triggers and execute reproducible challenger runs against the current champion

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-037: Governed retraining, promotion, immutable forecasts, and activation.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-037 (Governed retraining, promotion, immutable forecasts, and activation): Implement season/week/data-drift/performance retraining triggers and execute reproducible challenger runs against the current champion. Consume only verified prerequisite outputs from `POST-SUBTASK-108`. Produce `artifacts/mlops/retraining_challenger_report.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-110.

### In scope

- Perform the exact action: Implement season/week/data-drift/performance retraining triggers and execute reproducible challenger runs against the current champion.
- Consume only verified prerequisite outputs from `POST-SUBTASK-108`.
- Demonstrate with saved evidence: Triggers predeclare evidence/budget/freeze/skip reasons, cannot repeatedly tune on protected outcomes, preserve all failed/no-improvement challengers, and never corrupt the active champion.
- Demonstrate with saved evidence: The declared output `artifacts/mlops/retraining_challenger_report.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/mlops/retraining_challenger_report.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Build immutable forecast snapshots containing coherent scores/probabilities/uncertainty/A&M/BAS outputs plus exact state/run/model identities; Apply promotion/rollback policy, atomically activate approved snapshots, and validate immutability/freshness/consumer compatibility.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `RESEARCH_LANE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-114`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-109_implement_season_week_data_drift_performance_retraining_triggers_and_execute_rep.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-109.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-109`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w21_weekly_mlops.py
- src/aggie_analytics/orchestration/checkpoints.py
- src/aggie_analytics/orchestration/promotion.py
- src/aggie_analytics/orchestration/publication.py
- docs/105_W21_AUTONOMOUS_WEEKLY_MLOPS.md

## Dependencies that must already be complete

- POST-SUBTASK-108

## Files I may modify or create

- tests/test_w21_weekly_mlops.py
- artifacts/mlops/retraining_challenger_report.json
- artifacts/jira_evidence/POST-SUBTASK-109.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- mlops

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

- artifacts/mlops/retraining_challenger_report.json

## Acceptance criteria

1. Triggers predeclare evidence/budget/freeze/skip reasons, cannot repeatedly tune on protected outcomes, preserve all failed/no-improvement challengers, and never corrupt the active champion.
2. The declared output `artifacts/mlops/retraining_challenger_report.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w21_weekly_mlops.py — Run as a regression check after completing POST-SUBTASK-109; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w21_mlops.py — Run as a regression check after completing POST-SUBTASK-109; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/mlops/retraining_challenger_report.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- OPERATIONS / OPERATIONS: artifacts/mlops/retraining_challenger_report.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- INTEGRATION / INTEGRATION: artifacts/mlops/retraining_challenger_report.json — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- NEW_AUTOMATED_TEST_REQUIRED / NEW_AUTOMATED_TEST_REQUIRED: NEW_TEST_REQUIRED::POST-SUBTASK-109 — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Evidence to return

- `artifacts/mlops/retraining_challenger_report.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/mlops/retraining_challenger_report.json` can be parsed and consumed by `POST-SUBTASK-110` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
