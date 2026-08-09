# AI Work Packet — POST-SUBTASK-108

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate representative real end-to-end run lineage, resources, blockers, and no-fixture production behavior

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-036: Production weekly acquisition-to-prediction chain.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-036 (Production weekly acquisition-to-prediction chain): Validate representative real end-to-end run lineage, resources, blockers, and no-fixture production behavior. Consume only verified prerequisite outputs from `POST-SUBTASK-024`, `POST-SUBTASK-105`, `POST-SUBTASK-106`, `POST-SUBTASK-107`. Produce `artifacts/mlops/weekly_pipeline_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate representative real end-to-end run lineage, resources, blockers, and no-fixture production behavior.
- Consume only verified prerequisite outputs from `POST-SUBTASK-024`, `POST-SUBTASK-105`, `POST-SUBTASK-106`, `POST-SUBTASK-107`.
- Demonstrate with saved evidence: Each stage pins source/raw/entity/state/matrix/feature/model/cutoff/config identities, consumes only passed prerequisites, and fails on rights/drift/PIT/model blockers without synthetic shortcuts.
- Demonstrate with saved evidence: Identical inputs produce the same run identity/outcomes, resume starts at the last verified checkpoint, duplicates are prevented, and quarantine/failed gates cannot be skipped.
- Demonstrate with saved evidence: A real representative run emits complete timing/resource/test/evidence lineage and injected source/schema/disk/model/publication failures stop and recover at the correct boundary.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/mlops/weekly_pipeline_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Wire approved adapters through immutable raw capture, normalization, entities, PIT state, features, approved model, calibration, and prediction; Implement deterministic run identities, checkpoints, retries, resume, quarantine, rerun, and failure propagation.
- Automatically granting legal approval, assuming public accessibility permits retention/redistribution, or bypassing human terms review.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-114`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-108_validate_representative_real_end_to_end_run_lineage_resources_blockers_and_no_fi.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-108.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-108`.
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
- src/aggie_analytics/orchestration/weekly.py

## Dependencies that must already be complete

- POST-SUBTASK-024
- POST-SUBTASK-105
- POST-SUBTASK-106
- POST-SUBTASK-107

## Files I may modify or create

- artifacts/mlops/weekly_pipeline_gate.json
- artifacts/jira_evidence/POST-SUBTASK-108.json

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

- artifacts/mlops/weekly_pipeline_gate.json

## Acceptance criteria

1. Each stage pins source/raw/entity/state/matrix/feature/model/cutoff/config identities, consumes only passed prerequisites, and fails on rights/drift/PIT/model blockers without synthetic shortcuts.
2. Identical inputs produce the same run identity/outcomes, resume starts at the last verified checkpoint, duplicates are prevented, and quarantine/failed gates cannot be skipped.
3. A real representative run emits complete timing/resource/test/evidence lineage and injected source/schema/disk/model/publication failures stop and recover at the correct boundary.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w21_weekly_mlops.py — Run as a regression check after completing POST-SUBTASK-108; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w21_mlops.py — Run as a regression check after completing POST-SUBTASK-108; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/mlops/weekly_pipeline_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/mlops/weekly_pipeline_gate.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- OPERATIONS / OPERATIONS: artifacts/mlops/weekly_pipeline_gate.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- END_TO_END / END_TO_END: artifacts/mlops/weekly_pipeline_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/mlops/weekly_pipeline_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

A weekly run moves approved real data through every production stage, stops safely on invalid state, and resumes without duplicate or stale artifacts. The gate decision must explicitly reevaluate downstream issues: POST-STORY-037, POST-SUBTASK-109, POST-SUBTASK-110, POST-SUBTASK-111.

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
