# AI Work Packet — POST-SUBTASK-039

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate registry uniqueness, temporal consistency, collisions, and referential completeness

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-013: Canonical registries, aliases, and temporal relationships.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-013 (Canonical registries, aliases, and temporal relationships): Validate registry uniqueness, temporal consistency, collisions, and referential completeness. Consume only verified prerequisite outputs from `POST-SUBTASK-036`, `POST-SUBTASK-037`, `POST-SUBTASK-038`. Produce `artifacts/entities/registry_validation.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate registry uniqueness, temporal consistency, collisions, and referential completeness.
- Consume only verified prerequisite outputs from `POST-SUBTASK-036`, `POST-SUBTASK-037`, `POST-SUBTASK-038`.
- Demonstrate with saved evidence: Canonical IDs are deterministic, stable, source-independent, and do not depend on row order or mutable display names; realignment, neutral-site, rename, and cancellation history is represented.
- Demonstrate with saved evidence: Person mappings preserve source IDs, name/team/season/position evidence, transfers, duplicate names, suffixes, and uncertainty; low-confidence cases enter review instead of forced name-only merges.
- Demonstrate with saved evidence: No incompatible active aliases, duplicate canonical identities, impossible intervals, or accepted normalized record without a resolution/review disposition remain hidden.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/entities/registry_validation.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Build canonical team, conference, venue, game, season, and source registries with effective-dated aliases; Build coach, staff, player, roster, recruiting, and transfer identity registries with confidence and review state.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-042`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-039_validate_registry_uniqueness_temporal_consistency_collisions_and_referential_com.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-039.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-039`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_entity_governance.py
- src/aggie_analytics/entities/resolution.py
- docs/14_CANONICAL_ENTITY_ARCHITECTURE.md
- docs/16_ENTITY_RESOLUTION_AND_REVIEW.md
- governance/ENTITY_RESOLUTION_STATES.csv

## Dependencies that must already be complete

- POST-SUBTASK-036
- POST-SUBTASK-037
- POST-SUBTASK-038

## Files I may modify or create

- artifacts/entities/registry_validation.json
- artifacts/jira_evidence/POST-SUBTASK-039.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- entities

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

- artifacts/entities/registry_validation.json

## Acceptance criteria

1. Canonical IDs are deterministic, stable, source-independent, and do not depend on row order or mutable display names; realignment, neutral-site, rename, and cancellation history is represented.
2. Person mappings preserve source IDs, name/team/season/position evidence, transfers, duplicate names, suffixes, and uncertainty; low-confidence cases enter review instead of forced name-only merges.
3. No incompatible active aliases, duplicate canonical identities, impossible intervals, or accepted normalized record without a resolution/review disposition remain hidden.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_entity_governance.py — Run as a regression check after completing POST-SUBTASK-039; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_entities.py — Run as a regression check after completing POST-SUBTASK-039; retain command, exit code, and relevant output.
- END_TO_END / END_TO_END: artifacts/entities/registry_validation.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/entities/registry_validation.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## End-to-end handoff

Versioned canonical registries reproduce historical identity membership and retain every ambiguity rather than silently applying current mappings. The gate decision must explicitly reevaluate downstream issues: POST-STORY-014, POST-SUBTASK-040, POST-SUBTASK-041, POST-SUBTASK-042.

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
