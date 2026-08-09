# AI Work Packet — POST-SUBTASK-013

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Reconcile W06 source inventory with W24 refresh and current handoff gaps

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-005: Reconcile the final source universe and authority decisions.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-005 (Reconcile the final source universe and authority decisions): Reconcile W06 source inventory with W24 refresh and current handoff gaps. Begin from the verified repository/current-state contract and the exact source sections in this issue manifest. Produce `artifacts/source_governance/production_source_inventory.csv`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-014.

### In scope

- Perform the exact action: Reconcile W06 source inventory with W24 refresh and current handoff gaps.
- Begin from the verified repository/current-state contract and the exact source sections in this issue manifest.
- Demonstrate with saved evidence: Every prioritized source has a stable source ID, domain, upstream relationship, access method, historical depth, and PIT feasibility.
- Demonstrate with saved evidence: SportsDataverse/CFBD upstream relationships are represented without false independent-corroboration claims.
- Demonstrate with saved evidence: Superseded or unavailable sources retain explicit dispositions.
- Produce, validate, content-hash, and register `artifacts/source_governance/production_source_inventory.csv`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Freeze source priority, fallback, and required-versus-optional classifications; Validate source inventory completeness and unresolved decision coverage.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.

## Current gate state

- Workflow: `DONE`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `RESEARCH_LANE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `CONTRACT_DEFINED` → `IMPLEMENTED`
- Evidence state: `VERIFIED`
- Governance traceability gate: `POST-SUBTASK-024`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-013_reconcile_w06_source_inventory_with_w24_refresh_and_current_handoff_gaps.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-013.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-013`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- src/aggie_analytics/data/adapters.py
- docs/data_research/w06/DATA_ACQUISITION_PLAN.md
- docs/data_research/w06/SOURCE_ACCESS_LICENSE_MATRIX.csv
- docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md
- docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md

## Dependencies that must already be complete

- None.

## Files I may modify or create

- artifacts/source_governance/production_source_inventory.csv
- artifacts/jira_evidence/POST-SUBTASK-013.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- data-sources
- sources

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

- artifacts/source_governance/production_source_inventory.csv

## Acceptance criteria

1. Every prioritized source has a stable source ID, domain, upstream relationship, access method, historical depth, and PIT feasibility.
2. SportsDataverse/CFBD upstream relationships are represented without false independent-corroboration claims.
3. Superseded or unavailable sources retain explicit dispositions.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_data_research.py — Run as a regression check after completing POST-SUBTASK-013; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/source_governance/production_source_inventory.csv — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- STATIC_VALIDATION / STATIC_VALIDATION: artifacts/source_governance/production_source_inventory.csv — Validate schema, required fields, unique identifiers, cross-references, provenance, and explicit unresolved states.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/source_governance/production_source_inventory.csv` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.

## End-to-end handoff

Validate that `artifacts/source_governance/production_source_inventory.csv` can be parsed and consumed by `POST-SUBTASK-014` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
