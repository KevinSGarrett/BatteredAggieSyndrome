# AI Work Packet — POST-SUBTASK-063

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate player-state coverage, uncertainty, double-counting controls, and production eligibility

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-021: Historical player, roster, depth, value, replacement, and availability.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-021 (Historical player, roster, depth, value, replacement, and availability): Validate player-state coverage, uncertainty, double-counting controls, and production eligibility. Consume only verified prerequisite outputs from `POST-SUBTASK-030`, `POST-SUBTASK-048`, `POST-SUBTASK-061`, `POST-SUBTASK-062`. Produce `artifacts/player_intelligence/player_intelligence_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate player-state coverage, uncertainty, double-counting controls, and production eligibility.
- Consume only verified prerequisite outputs from `POST-SUBTASK-030`, `POST-SUBTASK-048`, `POST-SUBTASK-061`, `POST-SUBTASK-062`.
- Demonstrate with saved evidence: Player-team-position-depth relationships retain source and known-at/effective time; current rosters cannot retroactively populate history and ambiguous identities remain reviewable.
- Demonstrate with saved evidence: Value fits permitted history, sparse roles use transparent shrinkage, replacement reflects actual depth, availability remains probabilistic, and team impact is starter value minus plausible replacement without double counting.
- Demonstrate with saved evidence: Coverage is measured by season/team/position/source and missing reports are uncertainty—not healthy/absent certainty; unsupported periods remain conditional.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/player_intelligence/player_intelligence_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Materialize effective-dated roster, depth, position, participation, eligibility, transfer, and role state; Estimate leakage-safe player value, replacement distributions, and timestamped availability probabilities.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P1`
- Critical path: `false`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-069`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-063_validate_player_state_coverage_uncertainty_double_counting_controls_and_producti.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-063.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-063`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/context_intelligence/context.py
- src/aggie_analytics/player_intelligence/advanced_state.py
- docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md
- docs/29_TEAM_STATE_ARCHITECTURE.md
- docs/35_PLAYER_VALUE_REPLACEMENT_AND_AVAILABILITY.md
- docs/34_PLAYER_ROSTER_DEPTH_ARCHITECTURE.md

## Dependencies that must already be complete

- POST-SUBTASK-030
- POST-SUBTASK-048
- POST-SUBTASK-061
- POST-SUBTASK-062

## Files I may modify or create

- artifacts/player_intelligence/player_intelligence_gate.json
- artifacts/jira_evidence/POST-SUBTASK-063.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- player-context-intelligence
- advanced-football

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

- artifacts/player_intelligence/player_intelligence_gate.json

## Acceptance criteria

1. Player-team-position-depth relationships retain source and known-at/effective time; current rosters cannot retroactively populate history and ambiguous identities remain reviewable.
2. Value fits permitted history, sparse roles use transparent shrinkage, replacement reflects actual depth, availability remains probabilistic, and team impact is starter value minus plausible replacement without double counting.
3. Coverage is measured by season/team/position/source and missing reports are uncertainty—not healthy/absent certainty; unsupported periods remain conditional.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_player_intelligence_governance.py — Run as a regression check after completing POST-SUBTASK-063; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_context_intelligence_governance.py — Run as a regression check after completing POST-SUBTASK-063; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_team_state_governance.py — Run as a regression check after completing POST-SUBTASK-063; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/player_intelligence/player_intelligence_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/player_intelligence/player_intelligence_gate.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- END_TO_END / END_TO_END: artifacts/player_intelligence/player_intelligence_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/player_intelligence/player_intelligence_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## End-to-end handoff

At any historical cutoff the system can reconstruct expected players, depth, availability probabilities, replacement options, and uncertainty from evidence. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-009, POST-STORY-022, POST-STORY-027, POST-SUBTASK-064, POST-SUBTASK-065, POST-SUBTASK-066, POST-SUBTASK-079, POST-SUBTASK-080, POST-SUBTASK-081.

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
