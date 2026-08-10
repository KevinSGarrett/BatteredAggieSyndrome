# AI Work Packet — POST-SUBTASK-038

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Build coach, staff, player, roster, recruiting, and transfer identity registries with confidence and review state

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-013: Canonical registries, aliases, and temporal relationships.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-013 (Canonical registries, aliases, and temporal relationships): Build coach, staff, player, roster, recruiting, and transfer identity registries with confidence and review state. Consume only verified prerequisite outputs from `POST-SUBTASK-036`, `POST-SUBTASK-037`. Produce `artifacts/entities/canonical_people_registry.csv`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-039.

### In scope

- Perform the exact action: Build coach, staff, player, roster, recruiting, and transfer identity registries with confidence and review state.
- Consume only verified prerequisite outputs from `POST-SUBTASK-036`, `POST-SUBTASK-037`.
- Demonstrate with saved evidence: Person mappings preserve source IDs, name/team/season/position evidence, transfers, duplicate names, suffixes, and uncertainty; low-confidence cases enter review instead of forced name-only merges.
- Demonstrate with saved evidence: The declared output `artifacts/entities/canonical_people_registry.csv` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/entities/canonical_people_registry.csv`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Build canonical team, conference, venue, game, season, and source registries with effective-dated aliases; Validate registry uniqueness, temporal consistency, collisions, and referential completeness.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `DONE`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `EMPIRICALLY_VALIDATED`
- Evidence state: `VERIFIED`
- Governance traceability gate: `POST-SUBTASK-042`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-038_build_coach_staff_player_roster_recruiting_and_transfer_identity_registries_with.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-038.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-038`.
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

## Files I may modify or create

- src/aggie_analytics/entities/__init__.py
- src/aggie_analytics/entities/people_registry.py
- src/aggie_analytics/entities/registry_artifacts.py
- artifacts/entities/canonical_people_registry.csv
- artifacts/entities/canonical_people_registry_manifest.json
- tests/test_people_registry.py
- artifacts/jira_evidence/POST-SUBTASK-038.json

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

- artifacts/entities/canonical_people_registry.csv
- artifacts/entities/canonical_people_registry_manifest.json

## Acceptance criteria

1. Person mappings preserve source IDs, name/team/season/position evidence, transfers, duplicate names, suffixes, and uncertainty; low-confidence cases enter review instead of forced name-only merges.
2. The declared output `artifacts/entities/canonical_people_registry.csv` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_entity_governance.py — Run as a regression check after completing POST-SUBTASK-038; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_entities.py — Run as a regression check after completing POST-SUBTASK-038; retain command, exit code, and relevant output.
- SCIENTIFIC / SCIENTIFIC: artifacts/entities/canonical_people_registry.csv — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- INTEGRATION / INTEGRATION: artifacts/entities/canonical_people_registry.csv — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- NEW_AUTOMATED_TEST_REQUIRED / NEW_AUTOMATED_TEST_REQUIRED: tests/test_people_registry.py — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Evidence to return

- `artifacts/entities/canonical_people_registry.csv` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/entities/canonical_people_registry.csv` can be parsed and consumed by `POST-SUBTASK-039` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

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
