# AI Work Packet — POST-SUBTASK-022

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Create source-specific endpoint, parameter, pagination, season, and version acquisition specifications

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-008: Production acquisition contracts, rate limits, fallbacks, and drift hooks.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-008 (Production acquisition contracts, rate limits, fallbacks, and drift hooks): Create source-specific endpoint, parameter, pagination, season, and version acquisition specifications. Consume only verified prerequisite outputs from `POST-SUBTASK-018`, `POST-SUBTASK-021`. Produce `configs/source_acquisition_registry.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-023.

### In scope

- Perform the exact action: Create source-specific endpoint, parameter, pagination, season, and version acquisition specifications.
- Consume only verified prerequisite outputs from `POST-SUBTASK-018`, `POST-SUBTASK-021`.
- Demonstrate with saved evidence: Each source specification declares endpoint/version, allowed seasons, required parameters, pagination, cutoff semantics, and raw content type.
- Demonstrate with saved evidence: The specification records upstream lineage and avoids duplicate independent-source claims.
- Demonstrate with saved evidence: Unknown historical coverage remains explicit rather than backfilled by assumption.
- Produce, validate, content-hash, and register `configs/source_acquisition_registry.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Implement compliant retries, caching, rate-limit handling, and fallback activation; Establish source API/schema/terms drift baselines and monitoring inputs.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.

## Current gate state

- Workflow: `DONE`
- Ready: `false`
- Priority: `P0`
- Critical path: `false`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `CONTRACT_DEFINED` → `IMPLEMENTED`
- Evidence state: `VERIFIED`
- Governance traceability gate: `POST-SUBTASK-024`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-022_create_source_specific_endpoint_parameter_pagination_season_and_version_acquisit.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-022.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-022`.
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

- POST-SUBTASK-018
- POST-SUBTASK-021

## Files I may modify or create

- configs/source_acquisition_registry.json
- artifacts/jira_evidence/POST-SUBTASK-022.json

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

- configs/source_acquisition_registry.json

## Acceptance criteria

1. Each source specification declares endpoint/version, allowed seasons, required parameters, pagination, cutoff semantics, and raw content type.
2. The specification records upstream lineage and avoids duplicate independent-source claims.
3. Unknown historical coverage remains explicit rather than backfilled by assumption.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_data_research.py — Run as a regression check after completing POST-SUBTASK-022; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: configs/source_acquisition_registry.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- STATIC_VALIDATION / STATIC_VALIDATION: configs/source_acquisition_registry.json — Validate schema, required fields, unique identifiers, cross-references, provenance, and explicit unresolved states.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `configs/source_acquisition_registry.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.

## End-to-end handoff

Validate that `configs/source_acquisition_registry.json` can be parsed and consumed by `POST-SUBTASK-023` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
