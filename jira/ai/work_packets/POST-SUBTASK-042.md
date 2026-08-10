# AI Work Packet — POST-SUBTASK-042

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Publish the canonical entity snapshot and approve or block downstream PIT consumption

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-014: Population resolution, review workflow, transitions, and entity gate.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-014 (Population resolution, review workflow, transitions, and entity gate): Publish the canonical entity snapshot and approve or block downstream PIT consumption. Consume only verified prerequisite outputs from `POST-SUBTASK-039`, `POST-SUBTASK-040`, `POST-SUBTASK-041`. Produce `artifacts/entities/CANONICAL_ENTITY_SNAPSHOT.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Publish the canonical entity snapshot and approve or block downstream PIT consumption.
- Consume only verified prerequisite outputs from `POST-SUBTASK-039`, `POST-SUBTASK-040`, `POST-SUBTASK-041`.
- Demonstrate with saved evidence: Every resolution records resolver version, candidate set, evidence, confidence, decision rule, and deterministic replay; probability never substitutes for proof.
- Demonstrate with saved evidence: Manual decisions are append-only and attributable, transitions have known-at/effective intervals, and adding future aliases cannot change prior accepted identities without an explicit correction event.
- Demonstrate with saved evidence: Coverage/ambiguity/collision/orphan metrics are reported by domain/source/season/entity class; high-impact unresolved identities block affected work and GAP-004 closes only on population evidence.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/entities/CANONICAL_ENTITY_SNAPSHOT.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Run exact, alias, contextual, and bounded probabilistic resolution over the full population with evidence per decision; Operate unresolved/collision/merge/split review and materialize temporal team, conference, staff, roster, and player transitions.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.

## Current gate state

- Workflow: `IN_PROGRESS`
- Ready: `true`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-042`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-042_publish_the_canonical_entity_snapshot_and_approve_or_block_downstream_pit_consum.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-042.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-042`.
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
- tests/test_entity_governance.py
- docs/14_CANONICAL_ENTITY_ARCHITECTURE.md
- docs/16_ENTITY_RESOLUTION_AND_REVIEW.md
- governance/ENTITY_RESOLUTION_STATES.csv
- src/aggie_analytics/entities/resolution.py

## Dependencies that must already be complete

- POST-SUBTASK-039
- POST-SUBTASK-040
- POST-SUBTASK-041

## Files I may modify or create

- artifacts/entities/CANONICAL_ENTITY_SNAPSHOT.json
- artifacts/jira_evidence/POST-SUBTASK-042.json

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

- artifacts/entities/CANONICAL_ENTITY_SNAPSHOT.json

## Acceptance criteria

1. Every resolution records resolver version, candidate set, evidence, confidence, decision rule, and deterministic replay; probability never substitutes for proof.
2. Manual decisions are append-only and attributable, transitions have known-at/effective intervals, and adding future aliases cannot change prior accepted identities without an explicit correction event.
3. Coverage/ambiguity/collision/orphan metrics are reported by domain/source/season/entity class; high-impact unresolved identities block affected work and GAP-004 closes only on population evidence.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_entity_governance.py — Run as a regression check after completing POST-SUBTASK-042; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_entities.py — Run as a regression check after completing POST-SUBTASK-042; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/entities/CANONICAL_ENTITY_SNAPSHOT.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/entities/CANONICAL_ENTITY_SNAPSHOT.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- CALIBRATION / CALIBRATION: artifacts/entities/CANONICAL_ENTITY_SNAPSHOT.json — Report calibration/reliability evidence on the allowed evaluation lane with sample size and uncertainty.
- END_TO_END / END_TO_END: artifacts/entities/CANONICAL_ENTITY_SNAPSHOT.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/entities/CANONICAL_ENTITY_SNAPSHOT.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.

## End-to-end handoff

Pinned source/schema inputs resolve through auditable canonical identities and temporal transitions into a reproducible entity snapshot with no silent merges or orphans. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-005, POST-STORY-015, POST-SUBTASK-043, POST-SUBTASK-044, POST-SUBTASK-045.

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
