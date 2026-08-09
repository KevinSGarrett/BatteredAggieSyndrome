# AI Work Packet — POST-SUBTASK-051

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Open or retain-blocked the protected experimentation lane through the PIT/replay readiness gate

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-017: Leakage battery and chronological replay infrastructure.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-017 (Leakage battery and chronological replay infrastructure): Open or retain-blocked the protected experimentation lane through the PIT/replay readiness gate. Consume only verified prerequisite outputs from `POST-SUBTASK-048`, `POST-SUBTASK-049`, `POST-SUBTASK-050`. Produce `artifacts/pit/PIT_REPLAY_READINESS.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Open or retain-blocked the protected experimentation lane through the PIT/replay readiness gate.
- Consume only verified prerequisite outputs from `POST-SUBTASK-048`, `POST-SUBTASK-049`, `POST-SUBTASK-050`.
- Demonstrate with saved evidence: Future/postgame injections or appended records cannot change earlier eligible matrix hashes/predictions; every failure names exact source, field, row, transformation, and remediation.
- Demonstrate with saved evidence: Replay advances chronologically, fits only on permitted history, pins all identities, never returns protected outcomes to tuning code, and resumes without future-fitted state.
- Demonstrate with saved evidence: GAP-005 remains open until real historical replay—not fixture or synthetic replay—passes with approved matrix, split, seal, entity, source, and runner hashes.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/pit/PIT_REPLAY_READINESS.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Run static, future-append, value-mutation, same-game, normalization, entity-correction, weather, market, roster, and label leakage tests on real matrices; Implement deterministic walk-forward replay with frozen train/tune/protected boundaries, fold-local transforms, checkpoint/resume, and evidence identities.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-051`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-051_open_or_retain_blocked_the_protected_experimentation_lane_through_the_pit_replay.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-051.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-051`.
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
- tests/test_temporal_governance.py
- docs/21_LEAKAGE_AND_REPLAY_TEST_SPEC.md
- docs/readiness/W24_END_TO_END_READINESS.md
- src/aggie_analytics/temporal/state.py
- tests/test_w24_readiness.py

## Dependencies that must already be complete

- POST-SUBTASK-048
- POST-SUBTASK-049
- POST-SUBTASK-050

## Files I may modify or create

- artifacts/pit/PIT_REPLAY_READINESS.json
- artifacts/jira_evidence/POST-SUBTASK-051.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- pit-temporal
- pit

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

- artifacts/pit/PIT_REPLAY_READINESS.json

## Acceptance criteria

1. Future/postgame injections or appended records cannot change earlier eligible matrix hashes/predictions; every failure names exact source, field, row, transformation, and remediation.
2. Replay advances chronologically, fits only on permitted history, pins all identities, never returns protected outcomes to tuning code, and resumes without future-fitted state.
3. GAP-005 remains open until real historical replay—not fixture or synthetic replay—passes with approved matrix, split, seal, entity, source, and runner hashes.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_temporal_governance.py — Run as a regression check after completing POST-SUBTASK-051; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w24_readiness.py — Run as a regression check after completing POST-SUBTASK-051; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w24_readiness.py — Run as a regression check after completing POST-SUBTASK-051; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/pit/PIT_REPLAY_READINESS.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- END_TO_END / END_TO_END: artifacts/pit/PIT_REPLAY_READINESS.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/pit/PIT_REPLAY_READINESS.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.

## End-to-end handoff

A sealed chronological run can rebuild every pregame matrix and demonstrate future/postgame mutations cannot alter earlier state or predictions. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-008, POST-STORY-019, POST-STORY-024, POST-STORY-030, POST-SUBTASK-055, POST-SUBTASK-056, POST-SUBTASK-057, POST-SUBTASK-070, POST-SUBTASK-071, POST-SUBTASK-072, POST-SUBTASK-088, POST-SUBTASK-089….

## Stop instead of improvising when

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

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
