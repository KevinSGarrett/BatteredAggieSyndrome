# AI Work Packet — POST-SUBTASK-081

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate A&M coverage, source conflicts, rights, identity, PIT integrity, and snapshot reproducibility

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-027: Official A&M evidence and high-resolution PIT state.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-027 (Official A&M evidence and high-resolution PIT state): Validate A&M coverage, source conflicts, rights, identity, PIT integrity, and snapshot reproducibility. Consume only verified prerequisite outputs from `POST-SUBTASK-048`, `POST-SUBTASK-063`, `POST-SUBTASK-066`, `POST-SUBTASK-069`, `POST-SUBTASK-079`, `POST-SUBTASK-080`. Produce `artifacts/tamu/tamu_state_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate A&M coverage, source conflicts, rights, identity, PIT integrity, and snapshot reproducibility.
- Consume only verified prerequisite outputs from `POST-SUBTASK-048`, `POST-SUBTASK-063`, `POST-SUBTASK-066`, `POST-SUBTASK-069`, `POST-SUBTASK-079`, `POST-SUBTASK-080`.
- Demonstrate with saved evidence: Every A&M record retains rights, content/source identity, published/observed/retrieved timing, and canonical links; historical gaps/conflicts preserve both evidence lanes.
- Demonstrate with saved evidence: A&M detail uses the same cutoffs as national state, augments rather than silently overwrites it, retains uncertainty, and reproduces from pinned versions.
- Demonstrate with saved evidence: Future/postgame/current-page detail cannot alter earlier snapshots, restricted data is not redistributed, and unsupported fields remain absent/conditional rather than narrative-filled.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/tamu/tamu_state_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Acquire approved A&M schedules, rosters, depth, staff, media-guide, participation, availability, and official evidence; Build high-resolution A&M team/player/staff/context as-of snapshots reconciled with national state.
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
- Governance traceability gate: `POST-SUBTASK-087`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-081_validate_a_and_m_coverage_source_conflicts_rights_identity_pit_integrity_and_sna.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-081.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-081`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_tamu_specialization_governance.py
- src/aggie_analytics/tamu/specialization.py
- src/aggie_analytics/tamu/state.py
- docs/40_TEXAS_AM_SPECIALIZATION_ARCHITECTURE.md
- docs/41_TAMU_HIGH_RESOLUTION_STATE.md
- docs/42_TAMU_PEERS_ANALOGS_AND_SNAPSHOTS.md
- docs/43_TAMU_SPECIALIZATION_CANDIDATES_AND_OVERFIT_GUARDS.md

## Dependencies that must already be complete

- POST-SUBTASK-048
- POST-SUBTASK-063
- POST-SUBTASK-066
- POST-SUBTASK-069
- POST-SUBTASK-079
- POST-SUBTASK-080

## Files I may modify or create

- artifacts/tamu/tamu_state_gate.json
- artifacts/jira_evidence/POST-SUBTASK-081.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- tamu-specialization
- tamu

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

- artifacts/tamu/tamu_state_gate.json

## Acceptance criteria

1. Every A&M record retains rights, content/source identity, published/observed/retrieved timing, and canonical links; historical gaps/conflicts preserve both evidence lanes.
2. A&M detail uses the same cutoffs as national state, augments rather than silently overwrites it, retains uncertainty, and reproduces from pinned versions.
3. Future/postgame/current-page detail cannot alter earlier snapshots, restricted data is not redistributed, and unsupported fields remain absent/conditional rather than narrative-filled.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_tamu_specialization_governance.py — Run as a regression check after completing POST-SUBTASK-081; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_tamu_specialization.py — Run as a regression check after completing POST-SUBTASK-081; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/tamu/tamu_state_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SECURITY / SECURITY: artifacts/tamu/tamu_state_gate.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- END_TO_END / END_TO_END: artifacts/tamu/tamu_state_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/tamu/tamu_state_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.

## End-to-end handoff

Any A&M pregame cutoff reconstructs a richer but governance-compatible state with conflicts, missingness, and uncertainty preserved. The gate decision must explicitly reevaluate downstream issues: POST-STORY-028, POST-SUBTASK-082, POST-SUBTASK-083, POST-SUBTASK-084.

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
