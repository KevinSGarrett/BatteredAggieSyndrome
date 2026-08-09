# AI Work Packet — POST-SUBTASK-112

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Execute repeated real-source shadow weekly runs with timeliness, freshness, resource, coverage, intervention, and failure ledger

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-038: Repeated shadow operation, failure drills, and autonomous readiness.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-038 (Repeated shadow operation, failure drills, and autonomous readiness): Execute repeated real-source shadow weekly runs with timeliness, freshness, resource, coverage, intervention, and failure ledger. Consume only verified prerequisite outputs from `POST-SUBTASK-111`. Produce `artifacts/mlops/shadow_run_ledger.jsonl`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-113.

### In scope

- Perform the exact action: Execute repeated real-source shadow weekly runs with timeliness, freshness, resource, coverage, intervention, and failure ledger.
- Consume only verified prerequisite outputs from `POST-SUBTASK-111`.
- Demonstrate with saved evidence: Every scheduled success, miss, blocker, intervention, stale output, and resource result stays in the ledger; shadow uses real approved sources/paths and cannot omit bad weeks from reliability.
- Demonstrate with saved evidence: The declared output `artifacts/mlops/shadow_run_ledger.jsonl` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/mlops/shadow_run_ledger.jsonl`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Run source outage, schema drift, disk pressure, corrupt artifact, stale forecast, interrupted run, and rollback drills; Approve or retain-blocked the autonomous weekly operating maturity decision.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `OPERATIONS`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-114`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-112_execute_repeated_real_source_shadow_weekly_runs_with_timeliness_freshness_resour.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-112.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-112`.
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

- POST-SUBTASK-111

## Files I may modify or create

- artifacts/mlops/shadow_run_ledger.jsonl
- artifacts/jira_evidence/POST-SUBTASK-112.json

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

- artifacts/mlops/shadow_run_ledger.jsonl

## Acceptance criteria

1. Every scheduled success, miss, blocker, intervention, stale output, and resource result stays in the ledger; shadow uses real approved sources/paths and cannot omit bad weeks from reliability.
2. The declared output `artifacts/mlops/shadow_run_ledger.jsonl` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w21_weekly_mlops.py — Run as a regression check after completing POST-SUBTASK-112; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w21_mlops.py — Run as a regression check after completing POST-SUBTASK-112; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/mlops/shadow_run_ledger.jsonl — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/mlops/shadow_run_ledger.jsonl — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- OPERATIONS / OPERATIONS: artifacts/mlops/shadow_run_ledger.jsonl — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- STATIC_VALIDATION / STATIC_VALIDATION: artifacts/mlops/shadow_run_ledger.jsonl — Validate schema, required fields, unique identifiers, cross-references, provenance, and explicit unresolved states.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/mlops/shadow_run_ledger.jsonl` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/mlops/shadow_run_ledger.jsonl` can be parsed and consumed by `POST-SUBTASK-113` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
