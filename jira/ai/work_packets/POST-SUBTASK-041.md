# AI Work Packet — POST-SUBTASK-041

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Operate unresolved/collision/merge/split review and materialize temporal team, conference, staff, roster, and player transitions

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-014: Population resolution, review workflow, transitions, and entity gate.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-014 (Population resolution, review workflow, transitions, and entity gate): Operate unresolved/collision/merge/split review and materialize temporal team, conference, staff, roster, and player transitions. Consume only verified prerequisite outputs from `POST-SUBTASK-039`, `POST-SUBTASK-040`. Produce `artifacts/entities/entity_decision_and_transition_log.jsonl`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-042.

### In scope

- Perform the exact action: Operate unresolved/collision/merge/split review and materialize temporal team, conference, staff, roster, and player transitions.
- Consume only verified prerequisite outputs from `POST-SUBTASK-039`, `POST-SUBTASK-040`.
- Demonstrate with saved evidence: Manual decisions are append-only and attributable, transitions have known-at/effective intervals, and adding future aliases cannot change prior accepted identities without an explicit correction event.
- Demonstrate with saved evidence: The declared output `artifacts/entities/entity_decision_and_transition_log.jsonl` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/entities/entity_decision_and_transition_log.jsonl`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Run exact, alias, contextual, and bounded probabilistic resolution over the full population with evidence per decision; Publish the canonical entity snapshot and approve or block downstream PIT consumption.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `DONE`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `EMPIRICALLY_VALIDATED`
- Evidence state: `VERIFIED`
- Governance traceability gate: `POST-SUBTASK-042`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-041_operate_unresolved_collision_merge_split_review_and_materialize_temporal_team_co.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-041.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-041`.
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
- docs/17_ENTITY_STORAGE_EVALUATION.md
- governance/ENTITY_RESOLUTION_STATES.csv

## Dependencies that must already be complete

- POST-SUBTASK-039
- POST-SUBTASK-040

## Files I may modify or create

- artifacts/entities/entity_decision_and_transition_log.jsonl
- artifacts/jira_evidence/POST-SUBTASK-041.json

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

- artifacts/entities/entity_decision_and_transition_log.jsonl

## Acceptance criteria

1. Manual decisions are append-only and attributable, transitions have known-at/effective intervals, and adding future aliases cannot change prior accepted identities without an explicit correction event.
2. The declared output `artifacts/entities/entity_decision_and_transition_log.jsonl` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_entity_governance.py — Run as a regression check after completing POST-SUBTASK-041; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_entities.py — Run as a regression check after completing POST-SUBTASK-041; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/entities/entity_decision_and_transition_log.jsonl — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/entities/entity_decision_and_transition_log.jsonl — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- END_TO_END / END_TO_END: artifacts/entities/entity_decision_and_transition_log.jsonl — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/entities/entity_decision_and_transition_log.jsonl` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/entities/entity_decision_and_transition_log.jsonl` can be parsed and consumed by `POST-SUBTASK-042` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

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
