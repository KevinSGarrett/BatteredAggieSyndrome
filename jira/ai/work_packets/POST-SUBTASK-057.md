# AI Work Packet — POST-SUBTASK-057

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Validate feature values, home/away orientation, future-append invariance, lineage, missingness, and candidate eligibility

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-019: Foundation and advanced feature materialization.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-019 (Foundation and advanced feature materialization): Validate feature values, home/away orientation, future-append invariance, lineage, missingness, and candidate eligibility. Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-054`, `POST-SUBTASK-055`, `POST-SUBTASK-056`. Produce `artifacts/features/feature_materialization_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Validate feature values, home/away orientation, future-append invariance, lineage, missingness, and candidate eligibility.
- Consume only verified prerequisite outputs from `POST-SUBTASK-051`, `POST-SUBTASK-054`, `POST-SUBTASK-055`, `POST-SUBTASK-056`.
- Demonstrate with saved evidence: Rolling/expanding/opponent-adjusted statistics fit only on eligible prior history, declare shrinkage/minimum history, and use visible uncertainty for early-season/lower-division cold starts.
- Demonstrate with saved evidence: Advanced features use versioned PIT state, separate market-free/market-aware lanes, preserve availability uncertainty, and keep thin/unsupported domains isolated.
- Demonstrate with saved evidence: Representative values reconcile to source/as-of evidence; repeated build, swap, future append, NaN/inf, and unsupported-domain tests pass before experiments.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/features/feature_materialization_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Materialize team/opponent form, efficiency, scoring, schedule strength, recency, continuity, rest, travel, venue, sequence, cold-start, and lower-division prior features; Materialize supported player value/depth/replacement/availability, recruiting/transfer, coaching, weather, market, resource, officiating, and game-mechanics candidates.
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
- Governance traceability gate: `POST-SUBTASK-060`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-057_validate_feature_values_home_away_orientation_future_append_invariance_lineage_m.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-057.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-057`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/features/factory.py
- src/aggie_analytics/features/lifecycle.py
- src/aggie_analytics/features/screening.py
- docs/22_RAW_FEATURE_REGISTRY_ARCHITECTURE.md
- docs/25_FEATURE_ENGINEERING_ARCHITECTURE.md
- docs/26_FEATURE_SCREENING_AND_SELECTION.md
- docs/27_FEATURE_LIFECYCLE_GOVERNANCE.md

## Dependencies that must already be complete

- POST-SUBTASK-051
- POST-SUBTASK-054
- POST-SUBTASK-055
- POST-SUBTASK-056

## Files I may modify or create

- artifacts/features/feature_materialization_gate.json
- artifacts/jira_evidence/POST-SUBTASK-057.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- feature-engineering
- features

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

- artifacts/features/feature_materialization_gate.json

## Acceptance criteria

1. Rolling/expanding/opponent-adjusted statistics fit only on eligible prior history, declare shrinkage/minimum history, and use visible uncertainty for early-season/lower-division cold starts.
2. Advanced features use versioned PIT state, separate market-free/market-aware lanes, preserve availability uncertainty, and keep thin/unsupported domains isolated.
3. Representative values reconcile to source/as-of evidence; repeated build, swap, future append, NaN/inf, and unsupported-domain tests pass before experiments.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_feature_registry_governance.py — Run as a regression check after completing POST-SUBTASK-057; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_feature_lifecycle_governance.py — Run as a regression check after completing POST-SUBTASK-057; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_feature_tournament_full.py — Run as a regression check after completing POST-SUBTASK-057; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/features/feature_materialization_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- END_TO_END / END_TO_END: artifacts/features/feature_materialization_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/features/feature_materialization_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.

## End-to-end handoff

Pinned real PIT matrices deterministically produce foundation and advanced feature candidates with explicit uncertainty and no future information. The gate decision must explicitly reevaluate downstream issues: POST-STORY-020, POST-SUBTASK-058, POST-SUBTASK-059, POST-SUBTASK-060.

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
