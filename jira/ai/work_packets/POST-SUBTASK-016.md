# AI Work Packet — POST-SUBTASK-016

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Reissue CFBD, SportsDataverse, Open-Meteo, and official A&M/SEC/NCAA decisions under private-research policy

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-006: Per-source license, terms, and redistribution decisions.

## Atomic execution scope

Execute the atomic 1 of 3 step in Story POST-STORY-006 (Universal private-research acquisition and future-publication boundary): Reissue CFBD, SportsDataverse, Open-Meteo, and official A&M/SEC/NCAA decisions under private-research policy. Consume only verified prerequisite outputs from `POST-SUBTASK-015`. Produce `artifacts/source_governance/tier1_rights_decisions.csv`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-017.

### In scope

- Perform the exact action: Reissue CFBD, SportsDataverse, Open-Meteo, and official A&M/SEC/NCAA decisions under private-research policy.
- Consume only verified prerequisite outputs from `POST-SUBTASK-015`.
- Demonstrate with saved evidence: Each decision records source URL/version, review date, local storage, local training, publication boundary, retention, and attribution metadata.
- Demonstrate with saved evidence: Ambiguous license, terms, scraping, redistribution, and upstream-authorization fields are explicitly nonblocking for private acquisition/training.
- Demonstrate with saved evidence: Bulk raw data remains local outside Git and is not published.
- Produce, validate, content-hash, and register `artifacts/source_governance/tier1_rights_decisions.csv`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy; Publish the private-research source-use matrix and block raw third-party publication.
- Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.

## Current gate state

- Workflow: `DONE`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `CONTRACT_DEFINED` → `IMPLEMENTED`
- Evidence state: `VERIFIED`
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

1. Each decision records source URL/version, review date, local storage, local training, publication boundary, retention, and attribution metadata.
2. Ambiguous license, terms, scraping, redistribution, and upstream-authorization fields are explicitly nonblocking for private acquisition/training.
3. Bulk raw data remains local outside Git and is not published.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_data_research.py — Run as a regression check after completing POST-SUBTASK-016; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: artifacts/source_governance/tier1_rights_decisions.csv — Run as a regression check after completing POST-SUBTASK-016; retain command, exit code, and relevant output.
- PUBLICATION_BOUNDARY_REVIEW / PUBLICATION_BOUNDARY_REVIEW: MANUAL — Verify license/terms/redistribution metadata is preserved without blocking private acquisition or training, and that raw third-party publication remains disabled.
- MANUAL / MANUAL: artifacts/source_governance/tier1_rights_decisions.csv — Verify the private-use decision, metadata state, technical/quality scope, and future-publication boundary.
- SECURITY / SECURITY: artifacts/source_governance/tier1_rights_decisions.csv — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- END_TO_END / END_TO_END: artifacts/source_governance/tier1_rights_decisions.csv — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/source_governance/tier1_rights_decisions.csv` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.

## End-to-end handoff

Validate that `artifacts/source_governance/tier1_rights_decisions.csv` can be parsed and consumed by `POST-SUBTASK-017` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

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
