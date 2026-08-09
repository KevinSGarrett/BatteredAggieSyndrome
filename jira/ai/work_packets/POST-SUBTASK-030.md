# AI Work Packet — POST-SUBTASK-030

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Assign explicit tiered eligibility by season and domain without globally discarding partial older history

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-010: Player, roster, recruiting, market, weather, and contextual raw domains.

## Atomic execution scope

Consume the expanded acquisition/profile evidence and issue tiered, use-specific eligibility by source/endpoint, season/type, team/game, domain/grain, schema/version, reconciliation quality, immutable provenance, and historical known-at/PIT state. Preserve partial seasons and negative evidence; allow useful lower-tier history without promoting it into unsupported domains; hand the versioned gate to immutable-store and national-lake work.

### In scope

- Perform the exact action: Approve domain-by-domain production, experimental, conditional, rejected, or banned eligibility.
- Consume only verified prerequisite outputs from `POST-SUBTASK-027`, `POST-SUBTASK-028`, `POST-SUBTASK-029`.
- Demonstrate with saved evidence: Every record retains source/published/observed/retrieved time and canonical identity candidates; absence or ambiguous timing is not converted to healthy, available, or known.
- Demonstrate with saved evidence: Coverage and timestamp quality are measured by season/team/source/domain, with A&M detail reported separately and upstream-equivalent feeds not miscounted as independent corroboration.
- Demonstrate with saved evidence: Closing market, realized weather, final participation, restricted, thin, or unsupported domains cannot enter earlier production cutoffs or block the core v1 without explicit evidence.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/data_lake/historical_expansion_eligibility_gate.json`.
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

- artifacts/data_lake/historical_expansion_eligibility_gate.json
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

- artifacts/data_lake/historical_expansion_eligibility_gate.json

## Acceptance criteria

1. Every season/domain/grain receives an explicit production, experimental, conditional, rejected, unavailable, or banned disposition tied to measured evidence and intended downstream use.
2. Reliable games/outcomes may be admitted for Elo, team-strength priors, outcome modeling, calibration context, and long-run program context even when roster, player, play-by-play, box-score, gamebook, or advanced-stat domains are incomplete.
3. No season is silently promoted into a domain whose evidence is incomplete, unreconciled, unavailable, or not historically known, and no weak domain globally discards otherwise eligible domains.
4. Thresholds and exceptions are evidence-based, versioned, and preserve every partial/negative finding; no threshold is invented or weakened to obtain approval.
5. The gate explicitly retains GAP-002 and final historical readiness as unresolved pending POST-SUBTASK-033 and later chronological/protected gates.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w19_foundation.py — Run as a regression check after completing POST-SUBTASK-030; retain command, exit code, and relevant output.
- CHRONOLOGICAL_REPLAY / CHRONOLOGICAL_REPLAY: artifacts/data_lake/historical_expansion_eligibility_gate.json — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- SECURITY / SECURITY: artifacts/data_lake/historical_expansion_eligibility_gate.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- END_TO_END / END_TO_END: artifacts/data_lake/historical_expansion_eligibility_gate.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/data_lake/historical_expansion_eligibility_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.

## End-to-end handoff

Downstream snapshot, manifest, schema, PIT, and model-dataset consumers must reproduce the exact tier they consume and fail closed when a season/domain is missing, downgraded, rights-blocked, unreconciled, provenance-incomplete, or historically unknown.

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
