# AI Work Packet — POST-SUBTASK-069

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate context correctness, forecast-versus-realized isolation, fallback behavior, and production eligibility

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-023: Weather, travel, rest, venue, schedule sequence, mechanics, officiating, and sparse-opponent priors.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-023 (Weather, travel, rest, venue, schedule sequence, mechanics, officiating, and sparse-opponent priors): Validate context correctness, forecast-versus-realized isolation, fallback behavior, and production eligibility. Consume only verified prerequisite outputs from `POST-SUBTASK-030`, `POST-SUBTASK-048`, `POST-SUBTASK-067`, `POST-SUBTASK-068`. Produce `artifacts/context_intelligence/context_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate context correctness, forecast-versus-realized isolation, fallback behavior, and production eligibility.
- Consume only verified prerequisite outputs from `POST-SUBTASK-030`, `POST-SUBTASK-048`, `POST-SUBTASK-067`, `POST-SUBTASK-068`.
- Demonstrate with saved evidence: Weather uses forecast snapshots available at each cutoff; travel/rest/sequence derive from canonical schedules/venues and update for postponements/neutral sites with unknown coordinates left uncertain.
- Demonstrate with saved evidence: Mechanics/officiating/resource data are used only where rights/depth/timing support them, and lower-division opponents receive explicit decreasing-information priors rather than zero strength or dropped games.
- Demonstrate with saved evidence: Source spot checks, orientation, timing, sparse-opponent uncertainty, and unsupported-lane isolation pass before the context state is production eligible.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/context_intelligence/context_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Materialize forecast-time weather, venue, coordinates, travel, rest, opponent sequence, neutral-site, schedule-change, and local-time state; Materialize supported mechanics/officiating/resource candidates and FCS/DII/DIII/NAIA decreasing-information opponent priors.
- Automatically granting legal approval, assuming public accessibility permits retention/redistribution, or bypassing human terms review.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.

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

1. `jira/records/issues/subtasks/POST-SUBTASK-069_validate_context_correctness_forecast_versus_realized_isolation_fallback_behavio.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-069.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-069`.
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
- src/aggie_analytics/context_intelligence/context.py
- src/aggie_analytics/player_intelligence/advanced_state.py
- docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md
- docs/29_TEAM_STATE_ARCHITECTURE.md

## Dependencies that must already be complete

- POST-SUBTASK-030
- POST-SUBTASK-048
- POST-SUBTASK-067
- POST-SUBTASK-068

## Files I may modify or create

- artifacts/context_intelligence/context_gate.json
- artifacts/jira_evidence/POST-SUBTASK-069.json

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

- artifacts/context_intelligence/context_gate.json

## Acceptance criteria

1. Weather uses forecast snapshots available at each cutoff; travel/rest/sequence derive from canonical schedules/venues and update for postponements/neutral sites with unknown coordinates left uncertain.
2. Mechanics/officiating/resource data are used only where rights/depth/timing support them, and lower-division opponents receive explicit decreasing-information priors rather than zero strength or dropped games.
3. Source spot checks, orientation, timing, sparse-opponent uncertainty, and unsupported-lane isolation pass before the context state is production eligible.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_player_intelligence_governance.py — Run as a regression check after completing POST-SUBTASK-069; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_context_intelligence_governance.py — Run as a regression check after completing POST-SUBTASK-069; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_team_state_governance.py — Run as a regression check after completing POST-SUBTASK-069; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/context_intelligence/context_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- END_TO_END / END_TO_END: artifacts/context_intelligence/context_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/context_intelligence/context_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.

## End-to-end handoff

A matchup snapshot reconstructs weather forecast, venue/travel/rest/sequence, supported mechanics, and sparse-opponent priors with honest uncertainty. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-009, POST-STORY-027, POST-SUBTASK-079, POST-SUBTASK-080, POST-SUBTASK-081.

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
