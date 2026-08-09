# AI Work Packet — POST-SUBTASK-159

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Conduct rights/science/security/product/target-resource/backup/incident review and authorize or reject live operation separately

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-053: Separate protected evaluation, product integration, and operating authorization.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-053 (Separate protected evaluation, product integration, and operating authorization): Conduct rights/science/security/product/target-resource/backup/incident review and authorize or reject live operation separately. Consume only verified prerequisite outputs from `POST-SUBTASK-156`, `POST-SUBTASK-157`, `POST-SUBTASK-158`. Produce `artifacts/live/live_operating_decision.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Conduct rights/science/security/product/target-resource/backup/incident review and authorize or reject live operation separately.
- Consume only verified prerequisite outputs from `POST-SUBTASK-156`, `POST-SUBTASK-157`, `POST-SUBTASK-158`.
- Demonstrate with saved evidence: Protected outcomes cannot tune event handling/thresholds/model selection, all outage/delay scenarios and uncertainty are reported, and comparison includes pregame-only/simple live baselines.
- Demonstrate with saved evidence: Live outputs expose source/state/model/timestamp and remain distinguishable from immutable pregame forecasts; stale/disconnected/corrected/final states are explicit and restricted feed data is not exposed.
- Demonstrate with saved evidence: Authorization requires approved rights, protected evidence, latency/reliability/security/product/resources/backup/incidents; rejection leaves pregame valid and GAP-014 deferred/closed-by-disposition.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/live/live_operating_decision.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Run sealed event-time chronological evaluation with precommitted accuracy/calibration/latency/reliability/outage metrics and simple/pregame baselines; Implement timestamped live snapshot/stream API and UI states for stale, disconnected, corrected, suspended, halftime, final, replay, and restricted data.
- Automatically granting legal approval, assuming public accessibility permits retention/redistribution, or bypassing human terms review.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.
- Treating deferred live/in-game work as admitted production scope or describing it as Wave 26.

## Current gate state

- Workflow: `DEFERRED`
- Ready: `false`
- Priority: `DEFERRED`
- Critical path: `false`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `DEFERRED` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-159`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-159_conduct_rights_science_security_product_target_resource_backup_incident_review_a.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-159.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-159`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ADR_INDEX.csv
- governance/IMPLEMENTATION_WBS.csv
- governance/REQUIREMENTS_INDEX.csv
- governance/OPEN_ISSUES.md

## Dependencies that must already be complete

- POST-SUBTASK-156
- POST-SUBTASK-157
- POST-SUBTASK-158

## Files I may modify or create

- artifacts/live/live_operating_decision.json
- artifacts/jira_evidence/POST-SUBTASK-159.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- live-modeling
- live

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

- artifacts/live/live_operating_decision.json

## Acceptance criteria

1. Protected outcomes cannot tune event handling/thresholds/model selection, all outage/delay scenarios and uncertainty are reported, and comparison includes pregame-only/simple live baselines.
2. Live outputs expose source/state/model/timestamp and remain distinguishable from immutable pregame forecasts; stale/disconnected/corrected/final states are explicit and restricted feed data is not exposed.
3. Authorization requires approved rights, protected evidence, latency/reliability/security/product/resources/backup/incidents; rejection leaves pregame valid and GAP-014 deferred/closed-by-disposition.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- BENCHMARK / BENCHMARK: artifacts/live/live_operating_decision.json — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/live/live_operating_decision.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/live/live_operating_decision.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/live/live_operating_decision.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- SECURITY / SECURITY: artifacts/live/live_operating_decision.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- OPERATIONS / OPERATIONS: artifacts/live/live_operating_decision.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- END_TO_END / END_TO_END: artifacts/live/live_operating_decision.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/live/live_operating_decision.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Any live capability independently earns operating authorization from licensed replayable evidence; rejection has no effect on the completed pregame system. The gate decision must explicitly record that no downstream issue is silently unlocked.

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
