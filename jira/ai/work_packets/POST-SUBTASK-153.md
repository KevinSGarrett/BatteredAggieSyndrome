# AI Work Packet — POST-SUBTASK-153

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Apply the separate live-scope admission gate without creating Wave 26

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-051: Live need, source, rights, latency, cost, and value gate.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-051 (Live need, source, rights, latency, cost, and value gate): Apply the separate live-scope admission gate without creating Wave 26. Consume only verified prerequisite outputs from `POST-SUBTASK-141`, `POST-SUBTASK-151`, `POST-SUBTASK-152`. Produce `artifacts/live/live_admission_decision.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Apply the separate live-scope admission gate without creating Wave 26.
- Consume only verified prerequisite outputs from `POST-SUBTASK-141`, `POST-SUBTASK-151`, `POST-SUBTASK-152`.
- Demonstrate with saved evidence: Research does not bypass CAPTCHA/authentication/rate limits/access controls, assumes no public-equals-redistributable rights, and records unavailable/unaffordable sources as blockers.
- Demonstrate with saved evidence: Use cases distinguish in-game from pregame updates, targets are evidence-backed, pregame operation remains isolated, and no-build is valid when rights/history/cost/value/resources are inadequate.
- Demonstrate with saved evidence: TASK-169–172 remain deferred unless user/governance explicitly admits the separate scope; no Wave 26 exists and deferred live work is not unfinished core v1.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/live/live_admission_decision.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Research licensed live play/state/market feeds, authentication, terms, history, replayability, latency, reliability, cost, retention, and redistribution; Define exact live use cases, incremental value versus pregame, latency/reliability/resource/failure targets, isolation, and no-build criteria.
- Automatically granting legal approval, assuming public accessibility permits retention/redistribution, or bypassing human terms review.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.
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

1. `jira/records/issues/subtasks/POST-SUBTASK-153_apply_the_separate_live_scope_admission_gate_without_creating_wave_26.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-153.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-153`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/IMPLEMENTATION_WBS.csv
- governance/OPEN_ISSUES.md

## Dependencies that must already be complete

- POST-SUBTASK-141
- POST-SUBTASK-151
- POST-SUBTASK-152

## Files I may modify or create

- artifacts/live/live_admission_decision.json
- artifacts/jira_evidence/POST-SUBTASK-153.json

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

- artifacts/live/live_admission_decision.json

## Acceptance criteria

1. Research does not bypass CAPTCHA/authentication/rate limits/access controls, assumes no public-equals-redistributable rights, and records unavailable/unaffordable sources as blockers.
2. Use cases distinguish in-game from pregame updates, targets are evidence-backed, pregame operation remains isolated, and no-build is valid when rights/history/cost/value/resources are inadequate.
3. TASK-169–172 remain deferred unless user/governance explicitly admits the separate scope; no Wave 26 exists and deferred live work is not unfinished core v1.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- SECURITY / SECURITY: artifacts/live/live_admission_decision.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- END_TO_END / END_TO_END: artifacts/live/live_admission_decision.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/live/live_admission_decision.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.

## End-to-end handoff

Live work remains deferred unless licensed replayable evidence and clear value justify a separate isolated program. The gate decision must explicitly reevaluate downstream issues: POST-STORY-052, POST-SUBTASK-154, POST-SUBTASK-155, POST-SUBTASK-156.

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
