# AI Work Packet — POST-SUBTASK-048

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Approve or block immutable matrix versions for feature/model experimentation

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-016: Append-only as-of state and pregame matrices.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-016 (Append-only as-of state and pregame matrices): Approve or block immutable matrix versions for feature/model experimentation. Consume only verified prerequisite outputs from `POST-SUBTASK-045`, `POST-SUBTASK-046`, `POST-SUBTASK-047`. Produce `artifacts/pit/matrix_gate_decision.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Approve or block immutable matrix versions for feature/model experimentation.
- Consume only verified prerequisite outputs from `POST-SUBTASK-045`, `POST-SUBTASK-046`, `POST-SUBTASK-047`.
- Demonstrate with saved evidence: State rows retain canonical identity, effective/known-at time, source evidence, and version; corrections append and future observations do not alter prior as-of reads.
- Demonstrate with saved evidence: Each game/cutoff row uses only eligible state, handles home/away/neutral/lower-division/cancellations deterministically, and separates structural/not-known/source/resolution/pipeline missingness.
- Demonstrate with saved evidence: Approved matrices are content-hashed, split-blind, reproducible from pinned raw/entity/state versions, and cannot pass on successful file creation alone.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/pit/matrix_gate_decision.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Materialize append-only game, team, conference, venue, player, roster, staff, availability, weather, market, and context as-of state; Build national pregame matrices at configured cutoffs with row/cell lineage, missingness class, fallback, and pinned versions.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `IN_PROGRESS`
- Ready: `true`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-051`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-048_approve_or_block_immutable_matrix_versions_for_feature_model_experimentation.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-048.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-048`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_temporal_governance.py
- tests/test_w24_readiness.py
- src/aggie_analytics/temporal/eligibility.py
- src/aggie_analytics/temporal/state.py
- docs/18_POINT_IN_TIME_DATA_ARCHITECTURE.md
- docs/19_ASOF_QUERY_AND_CUTOFF_CONTRACT.md

## Dependencies that must already be complete

- POST-SUBTASK-045
- POST-SUBTASK-046
- POST-SUBTASK-047

## Files I may modify or create

- artifacts/pit/matrix_gate_decision.json
- artifacts/jira_evidence/POST-SUBTASK-048.json

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

- artifacts/pit/matrix_gate_decision.json

## Acceptance criteria

1. State rows retain canonical identity, effective/known-at time, source evidence, and version; corrections append and future observations do not alter prior as-of reads.
2. Each game/cutoff row uses only eligible state, handles home/away/neutral/lower-division/cancellations deterministically, and separates structural/not-known/source/resolution/pipeline missingness.
3. Approved matrices are content-hashed, split-blind, reproducible from pinned raw/entity/state versions, and cannot pass on successful file creation alone.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_temporal_governance.py — Run as a regression check after completing POST-SUBTASK-048; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/pit/matrix_gate_decision.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/pit/matrix_gate_decision.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- END_TO_END / END_TO_END: artifacts/pit/matrix_gate_decision.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/pit/matrix_gate_decision.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

A pinned cutoff reconstructs the exact state and matrix row that was legitimately knowable before a historical game. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-006, POST-EPIC-007, POST-STORY-017, POST-STORY-018, POST-STORY-021, POST-STORY-023, POST-STORY-027, POST-SUBTASK-049, POST-SUBTASK-050, POST-SUBTASK-051, POST-SUBTASK-052, POST-SUBTASK-053….

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
