# AI Work Packet — POST-SUBTASK-103

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Evaluate task-specific calibration, intervals, tails, coherence, OOD, missingness, season/regime/source shift, market ablation, and resource robustness

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-035: Calibration/robustness gates, A&M/BAS decisions, and champion promotion.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-035 (Calibration/robustness gates, A&M/BAS decisions, and champion promotion): Evaluate task-specific calibration, intervals, tails, coherence, OOD, missingness, season/regime/source shift, market ablation, and resource robustness. Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`. Produce `artifacts/validation/calibration_robustness_report.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-104.

### In scope

- Perform the exact action: Evaluate task-specific calibration, intervals, tails, coherence, OOD, missingness, season/regime/source shift, market ablation, and resource robustness.
- Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`.
- Demonstrate with saved evidence: Calibration failures cannot hide behind aggregate accuracy, unsupported conditions abstain/degrade, closing-market skill is separated, and every release-blocking control receives evidence-backed PASS/FAIL/BLOCKED/N-A/INCONCLUSIVE.
- Demonstrate with saved evidence: The declared output `artifacts/validation/calibration_robustness_report.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/validation/calibration_robustness_report.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision; Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `true`
- Execution lane: `SCIENTIFIC`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-105`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-103_evaluate_task_specific_calibration_intervals_tails_coherence_ood_missingness_sea.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-103.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-103`.
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
- docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md
- docs/58_MODEL_PROMOTION_AND_THRESHOLD_PRECOMMITMENT.md
- docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md

## Dependencies that must already be complete

- POST-SUBTASK-087
- POST-SUBTASK-096
- POST-SUBTASK-102

## Files I may modify or create

- artifacts/validation/calibration_robustness_report.json
- artifacts/jira_evidence/POST-SUBTASK-103.json

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

- artifacts/validation/calibration_robustness_report.json

## Acceptance criteria

1. Calibration failures cannot hide behind aggregate accuracy, unsupported conditions abstain/degrade, closing-market skill is separated, and every release-blocking control receives evidence-backed PASS/FAIL/BLOCKED/N-A/INCONCLUSIVE.
2. The declared output `artifacts/validation/calibration_robustness_report.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_validation_science_governance.py — Run as a regression check after completing POST-SUBTASK-103; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_validation_science.py — Run as a regression check after completing POST-SUBTASK-103; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/validation/calibration_robustness_report.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/validation/calibration_robustness_report.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- END_TO_END / END_TO_END: artifacts/validation/calibration_robustness_report.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/validation/calibration_robustness_report.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/validation/calibration_robustness_report.json` can be parsed and consumed by `POST-SUBTASK-104` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
