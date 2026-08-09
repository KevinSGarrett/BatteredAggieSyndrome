# AI Work Packet — POST-SUBTASK-114

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Approve or retain-blocked the autonomous weekly operating maturity decision

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-038: Repeated shadow operation, failure drills, and autonomous readiness.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-038 (Repeated shadow operation, failure drills, and autonomous readiness): Approve or retain-blocked the autonomous weekly operating maturity decision. Consume only verified prerequisite outputs from `POST-SUBTASK-111`, `POST-SUBTASK-112`, `POST-SUBTASK-113`. Produce `artifacts/mlops/weekly_operating_readiness.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Approve or retain-blocked the autonomous weekly operating maturity decision.
- Consume only verified prerequisite outputs from `POST-SUBTASK-111`, `POST-SUBTASK-112`, `POST-SUBTASK-113`.
- Demonstrate with saved evidence: Every scheduled success, miss, blocker, intervention, stale output, and resource result stays in the ledger; shadow uses real approved sources/paths and cannot omit bad weeks from reliability.
- Demonstrate with saved evidence: Each injected failure is detected, classified, stopped, alerted, recovered, and evidenced without weakening gates or deleting canonical evidence; recovery time/manual steps are measured.
- Demonstrate with saved evidence: OPERATING requires repeated successful real evidence plus freshness/recovery/resource/security/operator proof and documents residual manual gates; GAP-012 stays open otherwise.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/mlops/weekly_operating_readiness.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Execute repeated real-source shadow weekly runs with timeliness, freshness, resource, coverage, intervention, and failure ledger; Run source outage, schema drift, disk pressure, corrupt artifact, stale forecast, interrupted run, and rollback drills.

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

1. `jira/records/issues/subtasks/POST-SUBTASK-114_approve_or_retain_blocked_the_autonomous_weekly_operating_maturity_decision.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-114.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-114`.
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
- tests/test_w21_weekly_mlops.py
- docs/105_W21_AUTONOMOUS_WEEKLY_MLOPS.md
- src/aggie_analytics/orchestration/weekly.py

## Dependencies that must already be complete

- POST-SUBTASK-111
- POST-SUBTASK-112
- POST-SUBTASK-113

## Files I may modify or create

- artifacts/mlops/weekly_operating_readiness.json
- artifacts/jira_evidence/POST-SUBTASK-114.json

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

- artifacts/mlops/weekly_operating_readiness.json

## Acceptance criteria

1. Every scheduled success, miss, blocker, intervention, stale output, and resource result stays in the ledger; shadow uses real approved sources/paths and cannot omit bad weeks from reliability.
2. Each injected failure is detected, classified, stopped, alerted, recovered, and evidenced without weakening gates or deleting canonical evidence; recovery time/manual steps are measured.
3. OPERATING requires repeated successful real evidence plus freshness/recovery/resource/security/operator proof and documents residual manual gates; GAP-012 stays open otherwise.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w21_weekly_mlops.py — Run as a regression check after completing POST-SUBTASK-114; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w21_mlops.py — Run as a regression check after completing POST-SUBTASK-114; retain command, exit code, and relevant output.
- CALIBRATION / CALIBRATION: artifacts/mlops/weekly_operating_readiness.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- SECURITY / SECURITY: artifacts/mlops/weekly_operating_readiness.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- OPERATIONS / OPERATIONS: artifacts/mlops/weekly_operating_readiness.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- END_TO_END / END_TO_END: artifacts/mlops/weekly_operating_readiness.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/mlops/weekly_operating_readiness.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## End-to-end handoff

Repeated real weekly runs publish immutable forecasts, survive representative failures, and produce measured evidence for or against autonomous operation. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-015, POST-STORY-045, POST-SUBTASK-133, POST-SUBTASK-134, POST-SUBTASK-135.

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
