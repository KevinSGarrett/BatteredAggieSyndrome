# AI Work Packet — POST-SUBTASK-018

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Publish the private-research source-use matrix and block raw third-party publication

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-006: Per-source license, terms, and redistribution decisions.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-006 (Universal private-research acquisition and future-publication boundary): Publish the private-research source-use matrix and block raw third-party publication. Consume only verified prerequisite outputs from `POST-SUBTASK-015`, `POST-SUBTASK-016`, `POST-SUBTASK-017`. Produce `configs/source_rights_registry.json`, `artifacts/source_governance/source_rights_gate_test.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Publish the private-research source-use matrix and block raw third-party publication.
- Consume only verified prerequisite outputs from `POST-SUBTASK-015`, `POST-SUBTASK-016`, `POST-SUBTASK-017`.
- Demonstrate with saved evidence: The registry is machine-readable and contains no credentials.
- Demonstrate with saved evidence: All registered sources and caller-declared public sources admit private acquisition and local training without a rights prerequisite.
- Demonstrate with saved evidence: Raw third-party export remains independently denied and validity/safety gates remain scoped.
- Produce, validate, content-hash, and register `configs/source_rights_registry.json`.
- Produce, validate, content-hash, and register `artifacts/source_governance/source_rights_gate_test.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Reissue CFBD, SportsDataverse, Open-Meteo, and official A&M/SEC/NCAA decisions under private-research policy; Reissue recruiting, transfer, market, resources, gamebook, and officiating decisions under private-research policy.
- Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.

## Current gate state

- Workflow: `DONE`
- Ready: `false`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `SHARED_CONTRACT`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `CONTRACT_DEFINED` → `INTEGRATED`
- Evidence state: `VERIFIED`
- Governance traceability gate: `POST-SUBTASK-024`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-018_publish_the_approved_source_rights_matrix_and_block_disallowed_acquisition_expor.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-018.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-018`.
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
- src/aggie_analytics/data/contracts.py
- tests/test_data_research.py
- docs/data_research/w24/SOURCE_REFRESH_FINDINGS.md

## Dependencies that must already be complete

- POST-SUBTASK-015
- POST-SUBTASK-016
- POST-SUBTASK-017

## Files I may modify or create

- src/aggie_analytics/data/contracts.py
- tests/test_data_research.py
- configs/source_rights_registry.json
- artifacts/source_governance/source_rights_gate_test.json
- artifacts/jira_evidence/POST-SUBTASK-018.json

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

- configs/source_rights_registry.json
- artifacts/source_governance/source_rights_gate_test.json

## Acceptance criteria

1. The registry is machine-readable and contains no credentials.
2. All registered sources and caller-declared public sources admit private acquisition and local training without a rights prerequisite.
3. Raw third-party export remains independently denied and validity/safety gates remain scoped.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_data_research.py — Run as a regression check after completing POST-SUBTASK-018; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: configs/source_rights_registry.json — Run as a regression check after completing POST-SUBTASK-018; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: artifacts/source_governance/source_rights_gate_test.json — Run as a regression check after completing POST-SUBTASK-018; retain command, exit code, and relevant output.
- SECURITY / SECURITY: configs/source_rights_registry.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- END_TO_END / END_TO_END: artifacts/source_governance/source_rights_gate_test.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `configs/source_rights_registry.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- `artifacts/source_governance/source_rights_gate_test.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.

## End-to-end handoff

Private local acquisition and training succeed independently of rights ambiguity, raw third-party publication remains denied, and actual technical/quality/PIT/safety failures affect only their exact scope. The gate decision must explicitly reevaluate downstream issues: POST-STORY-008, POST-STORY-009, POST-SUBTASK-022, POST-SUBTASK-023, POST-SUBTASK-024, POST-SUBTASK-025, POST-SUBTASK-026, POST-SUBTASK-027.

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
