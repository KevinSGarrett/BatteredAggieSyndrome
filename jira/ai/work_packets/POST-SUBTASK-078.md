# AI Work Packet — POST-SUBTASK-078

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Publish the immutable candidate artifact registry for sealed protected evaluation

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-026: Calibration, ensembles, OOD, abstention, and candidate artifact registry.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-026 (Calibration, ensembles, OOD, abstention, and candidate artifact registry): Publish the immutable candidate artifact registry for sealed protected evaluation. Consume only verified prerequisite outputs from `POST-SUBTASK-075`, `POST-SUBTASK-076`, `POST-SUBTASK-077`. Produce `artifacts/modeling/CANDIDATE_MODEL_REGISTRY.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Publish the immutable candidate artifact registry for sealed protected evaluation.
- Consume only verified prerequisite outputs from `POST-SUBTASK-075`, `POST-SUBTASK-076`, `POST-SUBTASK-077`.
- Demonstrate with saved evidence: Calibrators and ensemble weights are fit only on allowed tuning data, retain member/diversity/failure identities, and cannot use protected outcomes for selection.
- Demonstrate with saved evidence: Evidence-derived tuning thresholds identify unsupported conditions and return wider uncertainty/abstention reasons rather than confident defaults when required inputs are unavailable.
- Demonstrate with saved evidence: Every admitted candidate pins data/feature/split/code/dependency/model/calibrator/seed identities, supported modes, OOD policy, resource envelope, and caveats; GAP-008 remains open pending protected replay.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/modeling/CANDIDATE_MODEL_REGISTRY.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Train precommitted task/cutoff/lane calibration and ensemble candidates using permitted tuning predictions; Implement sparse-history, missingness, source/regime shift, feature-pattern OOD, uncertainty, and abstention diagnostics.
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

1. `jira/records/issues/subtasks/POST-SUBTASK-078_publish_the_immutable_candidate_artifact_registry_for_sealed_protected_evaluatio.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-078.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-078`.
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
- src/aggie_analytics/modeling/baselines.py
- docs/54_UNCERTAINTY_OOD_AND_MARKET_LANES.md
- docs/103_W20_MODEL_CALIBRATION_BAS_IMPLEMENTATION.md
- docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md
- docs/52_MODEL_ARCHITECTURE_CANDIDATES.md

## Dependencies that must already be complete

- POST-SUBTASK-075
- POST-SUBTASK-076
- POST-SUBTASK-077

## Files I may modify or create

- artifacts/modeling/CANDIDATE_MODEL_REGISTRY.json
- artifacts/jira_evidence/POST-SUBTASK-078.json

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

- artifacts/modeling/CANDIDATE_MODEL_REGISTRY.json

## Acceptance criteria

1. Calibrators and ensemble weights are fit only on allowed tuning data, retain member/diversity/failure identities, and cannot use protected outcomes for selection.
2. Evidence-derived tuning thresholds identify unsupported conditions and return wider uncertainty/abstention reasons rather than confident defaults when required inputs are unavailable.
3. Every admitted candidate pins data/feature/split/code/dependency/model/calibrator/seed identities, supported modes, OOD policy, resource envelope, and caveats; GAP-008 remains open pending protected replay.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_model_architecture_governance.py — Run as a regression check after completing POST-SUBTASK-078; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w20_model_starter.py — Run as a regression check after completing POST-SUBTASK-078; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_model_architecture.py — Run as a regression check after completing POST-SUBTASK-078; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/modeling/CANDIDATE_MODEL_REGISTRY.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/modeling/CANDIDATE_MODEL_REGISTRY.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- END_TO_END / END_TO_END: artifacts/modeling/CANDIDATE_MODEL_REGISTRY.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/modeling/CANDIDATE_MODEL_REGISTRY.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

All candidates enter protected evaluation as immutable reproducible artifacts with precommitted calibration, uncertainty, OOD, and abstention behavior. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-009, POST-EPIC-010, POST-EPIC-011, POST-STORY-028, POST-STORY-030, POST-STORY-033, POST-SUBTASK-082, POST-SUBTASK-083, POST-SUBTASK-084, POST-SUBTASK-088, POST-SUBTASK-089, POST-SUBTASK-090….

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
