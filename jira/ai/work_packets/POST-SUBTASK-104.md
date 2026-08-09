# AI Work Packet — POST-SUBTASK-104

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-035: Calibration/robustness gates, A&M/BAS decisions, and champion promotion.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-035 (Calibration/robustness gates, A&M/BAS decisions, and champion promotion): Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision. Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`, `POST-SUBTASK-103`. Produce `artifacts/validation/promotion_ranking.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-105.

### In scope

- Perform the exact action: Apply the precommitted multi-task promotion policy, uncertainty, simplicity, operational compatibility, A&M decision, and BAS scientific decision.
- Consume only verified prerequisite outputs from `POST-SUBTASK-087`, `POST-SUBTASK-096`, `POST-SUBTASK-102`, `POST-SUBTASK-103`.
- Demonstrate with saved evidence: No new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.
- Demonstrate with saved evidence: The declared output `artifacts/validation/promotion_ranking.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/validation/promotion_ranking.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Evaluate task-specific calibration, intervals, tails, coherence, OOD, missingness, season/regime/source shift, market ablation, and resource robustness; Publish signed champion/retain-incumbent/no-champion artifacts and the full promotion gate matrix.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-105`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-104_apply_the_precommitted_multi_task_promotion_policy_uncertainty_simplicity_operat.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-104.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-104`.
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
- docs/58_MODEL_PROMOTION_AND_THRESHOLD_PRECOMMITMENT.md
- docs/56_VALIDATION_AND_PROTECTED_SPLITS.md
- docs/59_BAS_TAMU_UNCERTAINTY_MARKET_EVALUATION.md

## Dependencies that must already be complete

- POST-SUBTASK-087
- POST-SUBTASK-096
- POST-SUBTASK-102
- POST-SUBTASK-103

## Files I may modify or create

- artifacts/validation/promotion_ranking.json
- artifacts/jira_evidence/POST-SUBTASK-104.json

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

- artifacts/validation/promotion_ranking.json

## Acceptance criteria

1. No new metric/weight/threshold/candidate/segment is created after protected results; ties/inconclusive outcomes follow the sealed simpler/incumbent/no-promotion rule and null A&M/BAS findings remain valid.
2. The declared output `artifacts/validation/promotion_ranking.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_validation_science_governance.py — Run as a regression check after completing POST-SUBTASK-104; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_validation_science.py — Run as a regression check after completing POST-SUBTASK-104; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/validation/promotion_ranking.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- END_TO_END / END_TO_END: artifacts/validation/promotion_ranking.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/validation/promotion_ranking.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/validation/promotion_ranking.json` can be parsed and consumed by `POST-SUBTASK-105` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
