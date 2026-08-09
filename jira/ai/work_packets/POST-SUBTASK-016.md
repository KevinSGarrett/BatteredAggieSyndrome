# AI Work Packet — POST-SUBTASK-016

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Complete rights review for CFBD, SportsDataverse, Open-Meteo, and official A&M/SEC/NCAA lanes

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-006: Per-source license, terms, and redistribution decisions.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-006 (Per-source license, terms, and redistribution decisions): Complete rights review for CFBD, SportsDataverse, Open-Meteo, and official A&M/SEC/NCAA lanes. Consume only verified prerequisite outputs from `POST-SUBTASK-015`. Produce `artifacts/source_governance/tier1_rights_decisions.csv`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-017.

### In scope

- Perform the exact action: Complete rights review for CFBD, SportsDataverse, Open-Meteo, and official A&M/SEC/NCAA lanes.
- Consume only verified prerequisite outputs from `POST-SUBTASK-015`.
- Demonstrate with saved evidence: Each decision records terms URL/version, review date, allowed access, local storage, derived use, redistribution, retention, and attribution.
- Demonstrate with saved evidence: Ambiguous legal terms remain MANUAL_REVIEW_REQUIRED rather than assumed permissive.
- Demonstrate with saved evidence: Restricted bulk raw data is classified local-only.
- Produce, validate, content-hash, and register `artifacts/source_governance/tier1_rights_decisions.csv`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, legal-rights, or operating readiness.
- Work assigned to sibling subtasks: Complete rights review for recruiting, transfer, market, resources, gamebook, and officiating lanes; Publish the approved source-rights matrix and block disallowed acquisition/export paths.
- Automatically granting legal approval, assuming public accessibility permits retention/redistribution, or bypassing human terms review.

## Current gate state

- Workflow: `BLOCKED`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `CONTRACT_DEFINED` → `IMPLEMENTED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-024`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-016_complete_rights_review_for_cfbd_sportsdataverse_open_meteo_and_official_a_and_m_.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-016.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-016`.
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

- POST-SUBTASK-015

## Files I may modify or create

- artifacts/source_governance/tier1_rights_decisions.csv
- artifacts/jira_evidence/POST-SUBTASK-016.json

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

- artifacts/source_governance/tier1_rights_decisions.csv

## Acceptance criteria

1. Each decision records terms URL/version, review date, allowed access, local storage, derived use, redistribution, retention, and attribution.
2. Ambiguous legal terms remain MANUAL_REVIEW_REQUIRED rather than assumed permissive.
3. Restricted bulk raw data is classified local-only.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_data_research.py — Run as a regression check after completing POST-SUBTASK-016; retain command, exit code, and relevant output.
- LEGAL_RIGHTS_REVIEW / LEGAL_RIGHTS_REVIEW: MANUAL_REVIEW_REQUIRED — A named human reviewer records source-specific access, retention, training, publication, and redistribution decisions with terms/version/date evidence.
- MANUAL / MANUAL: artifacts/source_governance/tier1_rights_decisions.csv — Verify reviewer identity, decision date, unresolved questions, and explicit allow/block conditions.
- SECURITY / SECURITY: artifacts/source_governance/tier1_rights_decisions.csv — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- END_TO_END / END_TO_END: artifacts/source_governance/tier1_rights_decisions.csv — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/source_governance/tier1_rights_decisions.csv` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Human rights-review record containing reviewer, provider/terms version, access purpose, retention, model-training use, publication, redistribution, deletion, and allow/block decision.

## End-to-end handoff

Validate that `artifacts/source_governance/tier1_rights_decisions.csv` can be parsed and consumed by `POST-SUBTASK-017` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, rights-blocked, or provenance-incomplete input without manual repair.

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
