# AI Work Packet — POST-SUBTASK-047

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Build national pregame matrices at configured cutoffs with row/cell lineage, missingness class, fallback, and pinned versions

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-016: Append-only as-of state and pregame matrices.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-016 (Append-only as-of state and pregame matrices): Build national pregame matrices at configured cutoffs with row/cell lineage, missingness class, fallback, and pinned versions. Consume only verified prerequisite outputs from `POST-SUBTASK-045`, `POST-SUBTASK-046`. Produce `artifacts/pit/pregame_matrix_manifest.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-048.

### In scope

- Perform the exact action: Build national pregame matrices at configured cutoffs with row/cell lineage, missingness class, fallback, and pinned versions.
- Consume only verified prerequisite outputs from `POST-SUBTASK-045`, `POST-SUBTASK-046`.
- Demonstrate with saved evidence: Each game/cutoff row uses only eligible state, handles home/away/neutral/lower-division/cancellations deterministically, and separates structural/not-known/source/resolution/pipeline missingness.
- Demonstrate with saved evidence: The declared output `artifacts/pit/pregame_matrix_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/pit/pregame_matrix_manifest.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Materialize append-only game, team, conference, venue, player, roster, staff, availability, weather, market, and context as-of state; Approve or block immutable matrix versions for feature/model experimentation.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `READY`
- Ready: `true`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `DATA_MATERIALIZATION`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-051`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-047_build_national_pregame_matrices_at_configured_cutoffs_with_row_cell_lineage_miss.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-047.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-047`.
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
- docs/19_ASOF_QUERY_AND_CUTOFF_CONTRACT.md
- docs/readiness/W24_END_TO_END_READINESS.md

## Dependencies that must already be complete

- POST-SUBTASK-045
- POST-SUBTASK-046

## Files I may modify or create

- src/aggie_analytics/temporal/state.py
- artifacts/pit/pregame_matrix_manifest.json
- artifacts/jira_evidence/POST-SUBTASK-047.json

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

- artifacts/pit/pregame_matrix_manifest.json

## Acceptance criteria

1. Each game/cutoff row uses only eligible state, handles home/away/neutral/lower-division/cancellations deterministically, and separates structural/not-known/source/resolution/pipeline missingness.
2. The declared output `artifacts/pit/pregame_matrix_manifest.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_temporal_governance.py — Run as a regression check after completing POST-SUBTASK-047; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w24_readiness.py — Run as a regression check after completing POST-SUBTASK-047; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w24_readiness.py — Run as a regression check after completing POST-SUBTASK-047; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/pit/pregame_matrix_manifest.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SCIENTIFIC / SCIENTIFIC: artifacts/pit/pregame_matrix_manifest.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- INTEGRATION / INTEGRATION: artifacts/pit/pregame_matrix_manifest.json — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- NEW_AUTOMATED_TEST_REQUIRED / NEW_AUTOMATED_TEST_REQUIRED: NEW_TEST_REQUIRED::POST-SUBTASK-047 — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Evidence to return

- `artifacts/pit/pregame_matrix_manifest.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/pit/pregame_matrix_manifest.json` can be parsed and consumed by `POST-SUBTASK-048` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

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
