# AI Work Packet — POST-SUBTASK-106

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Wire approved adapters through immutable raw capture, normalization, entities, PIT state, features, approved model, calibration, and prediction

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-036: Production weekly acquisition-to-prediction chain.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-036 (Production weekly acquisition-to-prediction chain): Wire approved adapters through immutable raw capture, normalization, entities, PIT state, features, approved model, calibration, and prediction. Consume only verified prerequisite outputs from `POST-SUBTASK-024`, `POST-SUBTASK-105`. Produce `artifacts/mlops/weekly_pipeline_integration.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-107.

### In scope

- Perform the exact action: Wire approved adapters through immutable raw capture, normalization, entities, PIT state, features, approved model, calibration, and prediction.
- Consume only verified prerequisite outputs from `POST-SUBTASK-024`, `POST-SUBTASK-105`.
- Demonstrate with saved evidence: Each stage pins source/raw/entity/state/matrix/feature/model/cutoff/config identities, consumes only passed prerequisites, and fails on rights/drift/PIT/model blockers without synthetic shortcuts.
- Demonstrate with saved evidence: The declared output `artifacts/mlops/weekly_pipeline_integration.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/mlops/weekly_pipeline_integration.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Implement deterministic run identities, checkpoints, retries, resume, quarantine, rerun, and failure propagation; Validate representative real end-to-end run lineage, resources, blockers, and no-fixture production behavior.
- Automatically granting legal approval, assuming public accessibility permits retention/redistribution, or bypassing human terms review.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-114`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-106_wire_approved_adapters_through_immutable_raw_capture_normalization_entities_pit_.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-106.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-106`.
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

## Files I may modify or create

- artifacts/mlops/weekly_pipeline_integration.json
- artifacts/jira_evidence/POST-SUBTASK-106.json

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

- artifacts/mlops/weekly_pipeline_integration.json

## Acceptance criteria

1. Each stage pins source/raw/entity/state/matrix/feature/model/cutoff/config identities, consumes only passed prerequisites, and fails on rights/drift/PIT/model blockers without synthetic shortcuts.
2. The declared output `artifacts/mlops/weekly_pipeline_integration.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w21_weekly_mlops.py — Run as a regression check after completing POST-SUBTASK-106; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w21_mlops.py — Run as a regression check after completing POST-SUBTASK-106; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/mlops/weekly_pipeline_integration.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/mlops/weekly_pipeline_integration.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/mlops/weekly_pipeline_integration.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- OPERATIONS / OPERATIONS: artifacts/mlops/weekly_pipeline_integration.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- STATIC_VALIDATION / STATIC_VALIDATION: artifacts/mlops/weekly_pipeline_integration.json — Validate schema, required fields, unique identifiers, cross-references, provenance, and explicit unresolved states.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/mlops/weekly_pipeline_integration.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/mlops/weekly_pipeline_integration.json` can be parsed and consumed by `POST-SUBTASK-107` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
