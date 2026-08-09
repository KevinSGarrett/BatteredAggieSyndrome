# AI Work Packet — POST-SUBTASK-102

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate prediction coverage, scorecard completeness, hashes, ordering, no-early-access, and independent reproducibility

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-034: Sealed walk-forward predictions and complete scorecards.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-034 (Sealed walk-forward predictions and complete scorecards): Validate prediction coverage, scorecard completeness, hashes, ordering, no-early-access, and independent reproducibility. Consume only verified prerequisite outputs from `POST-SUBTASK-099`, `POST-SUBTASK-100`, `POST-SUBTASK-101`. Produce `artifacts/validation/protected_replay_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate prediction coverage, scorecard completeness, hashes, ordering, no-early-access, and independent reproducibility.
- Consume only verified prerequisite outputs from `POST-SUBTASK-099`, `POST-SUBTASK-100`, `POST-SUBTASK-101`.
- Demonstrate with saved evidence: Replay advances chronologically with only then-available state/models/calibrators/thresholds, records every identity, and retries cannot change membership or expose partial scores.
- Demonstrate with saved evidence: All precommitted metrics/segments include baselines, sample sizes, uncertainty, missing predictions, failures, calibration/coherence/OOD and no unfavorable metric is omitted.
- Demonstrate with saved evidence: Independent recomputation reproduces metrics/candidate ordering, verifies seals/access/row identity, and incomplete/corrupt evaluation cannot be summarized as a winner.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/validation/protected_replay_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Execute the sealed national, A&M-candidate, and BAS-support chronological replay once; Compute complete score, margin, win, distribution, calibration, BAS, A&M, OOD, coherence, robustness, market-lane, and segment scorecards.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-105`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-102_validate_prediction_coverage_scorecard_completeness_hashes_ordering_no_early_acc.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-102.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-102`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/validation/promotion.py
- src/aggie_analytics/validation/protected.py
- docs/56_VALIDATION_AND_PROTECTED_SPLITS.md
- docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md
- docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md

## Dependencies that must already be complete

- POST-SUBTASK-099
- POST-SUBTASK-100
- POST-SUBTASK-101

## Files I may modify or create

- artifacts/validation/protected_replay_gate.json
- artifacts/jira_evidence/POST-SUBTASK-102.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- validation-promotion
- validation

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

- artifacts/validation/protected_replay_gate.json

## Acceptance criteria

1. Replay advances chronologically with only then-available state/models/calibrators/thresholds, records every identity, and retries cannot change membership or expose partial scores.
2. All precommitted metrics/segments include baselines, sample sizes, uncertainty, missing predictions, failures, calibration/coherence/OOD and no unfavorable metric is omitted.
3. Independent recomputation reproduces metrics/candidate ordering, verifies seals/access/row identity, and incomplete/corrupt evaluation cannot be summarized as a winner.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_validation_science_governance.py — Run as a regression check after completing POST-SUBTASK-102; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_validation_science.py — Run as a regression check after completing POST-SUBTASK-102; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/validation/protected_replay_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/validation/protected_replay_gate.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/validation/protected_replay_gate.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- END_TO_END / END_TO_END: artifacts/validation/protected_replay_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/validation/protected_replay_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Sealed immutable predictions generate complete scorecards that a separate process can reproduce without reopening tuning. The gate decision must explicitly reevaluate downstream issues: POST-STORY-029, POST-STORY-032, POST-STORY-035, POST-SUBTASK-085, POST-SUBTASK-086, POST-SUBTASK-087, POST-SUBTASK-094, POST-SUBTASK-095, POST-SUBTASK-096, POST-SUBTASK-103, POST-SUBTASK-104, POST-SUBTASK-105.

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
