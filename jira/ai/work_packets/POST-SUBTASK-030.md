# AI Work Packet — POST-SUBTASK-030

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Approve domain-by-domain production, experimental, conditional, rejected, or banned eligibility

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-010: Player, roster, recruiting, market, weather, and contextual raw domains.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-010 (Player, roster, recruiting, market, weather, and contextual raw domains): Approve domain-by-domain production, experimental, conditional, rejected, or banned eligibility. Consume only verified prerequisite outputs from `POST-SUBTASK-027`, `POST-SUBTASK-028`, `POST-SUBTASK-029`. Produce `artifacts/data_lake/context_eligibility_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Approve domain-by-domain production, experimental, conditional, rejected, or banned eligibility.
- Consume only verified prerequisite outputs from `POST-SUBTASK-027`, `POST-SUBTASK-028`, `POST-SUBTASK-029`.
- Demonstrate with saved evidence: Every record retains source/published/observed/retrieved time and canonical identity candidates; absence or ambiguous timing is not converted to healthy, available, or known.
- Demonstrate with saved evidence: Coverage and timestamp quality are measured by season/team/source/domain, with A&M detail reported separately and upstream-equivalent feeds not miscounted as independent corroboration.
- Demonstrate with saved evidence: Closing market, realized weather, final participation, restricted, thin, or unsupported domains cannot enter earlier production cutoffs or block the core v1 without explicit evidence.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/data_lake/context_eligibility_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Acquire timestamped roster, depth, participation, injury, recruiting, transfer, coaching, weather, venue, travel, market, resource, and mechanics evidence; Profile supporting-domain schema, historical coverage, timestamp quality, upstream lineage, and rights class.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `SCAFFOLD` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-033`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-030_approve_domain_by_domain_production_experimental_conditional_rejected_or_banned_.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-030.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-030`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w19_foundation.py
- src/aggie_analytics/data/adapters.py
- src/aggie_analytics/data/contracts.py
- src/aggie_analytics/data/snapshots.py
- docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md

## Dependencies that must already be complete

- POST-SUBTASK-027
- POST-SUBTASK-028
- POST-SUBTASK-029

## Files I may modify or create

- artifacts/data_lake/context_eligibility_gate.json
- artifacts/jira_evidence/POST-SUBTASK-030.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- raw-snapshots
- raw-data

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

- artifacts/data_lake/context_eligibility_gate.json

## Acceptance criteria

1. Every record retains source/published/observed/retrieved time and canonical identity candidates; absence or ambiguous timing is not converted to healthy, available, or known.
2. Coverage and timestamp quality are measured by season/team/source/domain, with A&M detail reported separately and upstream-equivalent feeds not miscounted as independent corroboration.
3. Closing market, realized weather, final participation, restricted, thin, or unsupported domains cannot enter earlier production cutoffs or block the core v1 without explicit evidence.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w19_foundation.py — Run as a regression check after completing POST-SUBTASK-030; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/data_lake/context_eligibility_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SECURITY / SECURITY: artifacts/data_lake/context_eligibility_gate.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- END_TO_END / END_TO_END: artifacts/data_lake/context_eligibility_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/data_lake/context_eligibility_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.

## End-to-end handoff

Supporting domains are acquired and classified from real historical evidence without inventing timing, coverage, rights, or certainty. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-007, POST-STORY-011, POST-STORY-021, POST-STORY-023, POST-SUBTASK-031, POST-SUBTASK-032, POST-SUBTASK-033, POST-SUBTASK-061, POST-SUBTASK-062, POST-SUBTASK-063, POST-SUBTASK-067, POST-SUBTASK-068….

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
