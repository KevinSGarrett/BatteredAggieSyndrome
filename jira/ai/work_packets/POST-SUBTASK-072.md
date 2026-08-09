# AI Work Packet — POST-SUBTASK-072

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Approve model dataset identity, leakage isolation, duplicate handling, and reproducibility

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-024: Model-ready targets, splits, weights, and datasets.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-024 (Model-ready targets, splits, weights, and datasets): Approve model dataset identity, leakage isolation, duplicate handling, and reproducibility. Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-060`, `POST-SUBTASK-070`, `POST-SUBTASK-071`. Produce `artifacts/modeling/model_dataset_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Approve model dataset identity, leakage isolation, duplicate handling, and reproducibility.
- Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-060`, `POST-SUBTASK-070`, `POST-SUBTASK-071`.
- Demonstrate with saved evidence: Targets declare cancellations, overtime, missing scores, neutral sites, lower divisions, and official outcome source; every row links to canonical game evidence.
- Demonstrate with saved evidence: Split assignments match protected registries, prevent duplicate/rematch/season-fragment leakage, and precommit weights/shrinkage before candidate results.
- Demonstrate with saved evidence: Pinned raw/entity/PIT/feature/target/split versions reproduce identical rows and protected labels are inaccessible to training/tuning paths.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/modeling/model_dataset_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Materialize official score, margin, win, distribution, market-lane, and BAS-support target tables with game lineage; Materialize chronological train/tune/protected assignments, sample weights, cold-start rules, and feature/target separation.
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
- Governance traceability gate: `POST-SUBTASK-078`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-072_approve_model_dataset_identity_leakage_isolation_duplicate_handling_and_reproduc.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-072.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-072`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- src/aggie_analytics/modeling/baselines.py
- src/aggie_analytics/modeling/joint.py
- src/aggie_analytics/modeling/runtime.py
- docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md
- docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md
- docs/52_MODEL_ARCHITECTURE_CANDIDATES.md

## Dependencies that must already be complete

- POST-SUBTASK-051
- POST-SUBTASK-060
- POST-SUBTASK-070
- POST-SUBTASK-071
- POST-SUBTASK-033

## Files I may modify or create

- artifacts/modeling/model_dataset_gate.json
- artifacts/jira_evidence/POST-SUBTASK-072.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- modeling

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

- artifacts/modeling/model_dataset_gate.json

## Acceptance criteria

1. The model dataset pins the expanded quality-supported historical population and exact season/domain eligibility tiers consumed; the bounded 2022-2025 tranche is not the terminal training population by default.
2. Any narrower window is admitted only by explicit empirical evidence produced without protected-period tuning and records the tradeoff, excluded seasons/domains, and protected acceptance decision.
3. Dataset identity, target-game exclusion, PIT eligibility, duplicate handling, feature/target separation, split assignment, and reproducibility all pass from immutable lineage.
4. Failure of one older domain causes scoped feature/season eligibility or fallback behavior, not silent global history removal or unsupported imputation.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_model_architecture_governance.py — Run as a regression check after completing POST-SUBTASK-072; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w20_model_starter.py — Run as a regression check after completing POST-SUBTASK-072; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_model_architecture.py — Run as a regression check after completing POST-SUBTASK-072; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/modeling/model_dataset_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/modeling/model_dataset_gate.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- END_TO_END / END_TO_END: artifacts/modeling/model_dataset_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/modeling/model_dataset_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

The same pinned identities always produce the same model-ready rows, targets, weights, and chronological partitions without protected leakage. The gate decision must explicitly reevaluate downstream issues: POST-STORY-025, POST-SUBTASK-073, POST-SUBTASK-074, POST-SUBTASK-075.

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
