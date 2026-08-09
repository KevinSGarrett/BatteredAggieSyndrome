# AI Work Packet — POST-SUBTASK-033

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Run and publish the national historical-lake readiness decision

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-011: Immutable raw store, manifests, provenance, and population audit.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-011 (Immutable raw store, manifests, provenance, and population audit): Run and publish the national historical-lake readiness decision. Consume only verified prerequisite outputs from `POST-SUBTASK-027`, `POST-SUBTASK-030`, `POST-SUBTASK-031`, `POST-SUBTASK-032`. Produce `artifacts/data_lake/national_lake_readiness.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Run and publish the national historical-lake readiness decision.
- Consume only verified prerequisite outputs from `POST-SUBTASK-027`, `POST-SUBTASK-030`, `POST-SUBTASK-031`, `POST-SUBTASK-032`.
- Demonstrate with saved evidence: Repeated identical bytes resolve to the same content identity while changed/corrected bytes create a new immutable version without rewriting prior evidence.
- Demonstrate with saved evidence: The master manifest links every accepted snapshot to source contract, request, hash, parser/schema version, coverage, quality, and nonblocking source-policy metadata and reproduces population counts.
- Demonstrate with saved evidence: GAP-002 remains open unless actual national history—not fixtures, reconnaissance samples, or starter code—meets immutable, manifest, readback, and coverage requirements.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/data_lake/national_lake_readiness.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Enforce content-addressed raw snapshots, correction lineage, quarantine, and source-policy storage metadata; Build the cross-domain acquisition, schema, quality, and source-to-snapshot provenance manifests.

## Current gate state

- Workflow: `READY`
- Ready: `true`
- Priority: `P0`
- Critical path: `true`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `SCAFFOLD` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-033`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-033_run_and_publish_the_national_historical_lake_readiness_decision.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-033.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-033`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/ADR_INDEX.csv
- governance/REQUIREMENTS_INDEX.csv
- tests/test_w19_foundation.py
- docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md

## Dependencies that must already be complete

- POST-SUBTASK-027
- POST-SUBTASK-030
- POST-SUBTASK-031
- POST-SUBTASK-032

## Files I may modify or create

- artifacts/data_lake/national_lake_readiness.json
- artifacts/jira_evidence/POST-SUBTASK-033.json

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

- artifacts/data_lake/national_lake_readiness.json

## Acceptance criteria

1. Repeated identical bytes resolve to the same content identity while changed/corrected bytes create a new immutable version without rewriting prior evidence.
2. The master manifest links every accepted snapshot to source contract, request, hash, parser/schema version, coverage, quality, and nonblocking source-policy metadata and reproduces population counts.
3. GAP-002 remains open unless actual national history—not fixtures, reconnaissance samples, or starter code—meets immutable, manifest, readback, and coverage requirements.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w19_foundation.py — Run as a regression check after completing POST-SUBTASK-033; retain command, exit code, and relevant output.
- END_TO_END / END_TO_END: artifacts/data_lake/national_lake_readiness.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- NEW_AUTOMATED_TEST_REQUIRED / NEW_AUTOMATED_TEST_REQUIRED: NEW_TEST_REQUIRED::POST-SUBTASK-033 — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Evidence to return

- `artifacts/data_lake/national_lake_readiness.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## End-to-end handoff

Pinned manifests reconstruct the accepted raw lake from immutable bytes while preserving every missing season, unavailable domain, correction, and technical or quality blocker. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-004, POST-STORY-012, POST-SUBTASK-034, POST-SUBTASK-035, POST-SUBTASK-036, POST-SUBTASK-072.

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
