# AI Work Packet — POST-SUBTASK-132

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Execute clean-location restore of representative raw-to-forecast lineage and Jira metadata with measured RPO/RTO/manual steps

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-044: Rights-aware backup, restore, retention, and disaster recovery.

## Atomic execution scope

Execute the atomic 3 of 3 step in Story POST-STORY-044 (Rights-aware backup, restore, retention, and disaster recovery): Execute clean-location restore of representative raw-to-forecast lineage and Jira metadata with measured RPO/RTO/manual steps. Consume only verified prerequisite outputs from `POST-SUBTASK-129`, `POST-SUBTASK-130`, `POST-SUBTASK-131`. Produce `artifacts/operations/restore_drill.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### In scope

- Perform the exact action: Execute clean-location restore of representative raw-to-forecast lineage and Jira metadata with measured RPO/RTO/manual steps.
- Consume only verified prerequisite outputs from `POST-SUBTASK-129`, `POST-SUBTASK-130`, `POST-SUBTASK-131`.
- Demonstrate with saved evidence: Canonical protected evidence, negative results, source-policy metadata, and issue history retain required immutability while raw third-party data never copies to publication destinations.
- Demonstrate with saved evidence: Backups are independently readable/content-hashed/cataloged/permission-checked, partial/corrupt copies never replace good state, and Jira canonical records/key map/change log/indexes are included efficiently.
- Demonstrate with saved evidence: A clean restore passes hash/schema/reference/lineage validation, identifies external credentials/rights reconfiguration, measures recovery, and success is not inferred from backup creation alone.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/operations/restore_drill.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Finalize authority/retention/frequency/encryption/access/rights/deletion rules for raw, curated, model, forecast, log, evidence, and Jira metadata; Implement content-hashed verified backups, catalog, integrity checking, last-known-good protection, and restricted-destination enforcement.
- Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.

## Current gate state

- Workflow: `READY`
- Ready: `true`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `PROTECTED_GATE`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `PRODUCTION_READY`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-132`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-132_execute_clean_location_restore_of_representative_raw_to_forecast_lineage_and_jir.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-132.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-132`.
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
- tests/test_w23_operations.py
- docs/operations/BACKUP_RESTORE_RETENTION_RUNBOOK.md
- src/aggie_analytics/operations/backup.py
- docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md
- docs/operations/CI_SECURITY_SUPPLY_CHAIN.md

## Dependencies that must already be complete

- POST-SUBTASK-129
- POST-SUBTASK-130
- POST-SUBTASK-131

## Files I may modify or create

- artifacts/operations/restore_drill.json
- artifacts/jira_evidence/POST-SUBTASK-132.json

No path outside this list is authorized. A necessary undeclared edit requires a controlled specification update before mutation.

## Components in scope

- operations-security
- operations

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

- artifacts/operations/restore_drill.json

## Acceptance criteria

1. Canonical protected evidence, negative results, source-policy metadata, and issue history retain required immutability while raw third-party data never copies to publication destinations.
2. Backups are independently readable/content-hashed/cataloged/permission-checked, partial/corrupt copies never replace good state, and Jira canonical records/key map/change log/indexes are included efficiently.
3. A clean restore passes hash/schema/reference/lineage validation, identifies external credentials/rights reconfiguration, measures recovery, and success is not inferred from backup creation alone.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Tests / validation

- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w23_operations.py — Run as a regression check after completing POST-SUBTASK-132; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w23_operations.py — Run as a regression check after completing POST-SUBTASK-132; retain command, exit code, and relevant output.
- BENCHMARK / BENCHMARK: artifacts/operations/restore_drill.json — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- SECURITY / SECURITY: artifacts/operations/restore_drill.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- OPERATIONS / OPERATIONS: artifacts/operations/restore_drill.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- END_TO_END / END_TO_END: artifacts/operations/restore_drill.json — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/operations/restore_drill.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.

## End-to-end handoff

A verified backup can restore selected canonical lineage and Jira execution state into a clean location without rewriting history or violating data rights. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-015, POST-STORY-045, POST-SUBTASK-133, POST-SUBTASK-134, POST-SUBTASK-135.

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
