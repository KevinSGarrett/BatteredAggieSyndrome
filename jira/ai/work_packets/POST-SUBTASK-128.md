# AI Work Packet — POST-SUBTASK-128

## Packet mode

`ATOMIC_EXECUTION`

**This is an atomic execution packet.** It may be selected only when the canonical record is `READY=true` and every hard dependency/evidence gate is satisfied.

## What am I implementing?

Implement source/API/terms/schema/entity/feature/data/model/concept/freshness/security/governance drift detectors plus alert severity/dedup/ack/escalation

## Why?

This is an independently executable and verifiable work unit required by Story POST-STORY-043: Structured observability, alerts, drift, and incident response.

## Atomic execution scope

Execute the atomic 2 of 3 step in Story POST-STORY-043 (Structured observability, alerts, drift, and incident response): Implement source/API/terms/schema/entity/feature/data/model/concept/freshness/security/governance drift detectors plus alert severity/dedup/ack/escalation. Consume only verified prerequisite outputs from `POST-SUBTASK-024`, `POST-SUBTASK-126`, `POST-SUBTASK-127`. Produce `artifacts/operations/drift_alert_validation.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to POST-SUBTASK-129.

### In scope

- Perform the exact action: Implement source/API/terms/schema/entity/feature/data/model/concept/freshness/security/governance drift detectors plus alert severity/dedup/ack/escalation.
- Consume only verified prerequisite outputs from `POST-SUBTASK-024`, `POST-SUBTASK-126`, `POST-SUBTASK-127`.
- Demonstrate with saved evidence: Versioned baselines and evidence-derived thresholds identify affected scope, block unsafe downstream training/publication, and route alerts without claiming resolution until evidence changes.
- Demonstrate with saved evidence: The declared output `artifacts/operations/drift_alert_validation.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
- Demonstrate with saved evidence: The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.
- Produce, validate, content-hash, and register `artifacts/operations/drift_alert_validation.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Out of scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Instrument run/stage/source/snapshot/entity/matrix/feature/model/product identifiers, metrics, structured events, health, and redaction; Run outage, schema, stale forecast, disk, corrupt artifact, model, security, and governance-conflict game days through incident/rollback/substitution runbooks.
- Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.
- Forcing a nonzero A&M/BAS effect, unsealing protected evaluation early, cherry-picking a winner, or suppressing null/negative results.

## Current gate state

- Workflow: `READY`
- Ready: `true`
- Priority: `P2`
- Critical path: `false`
- Execution lane: `OPERATIONS`
- Execution mode: `ATOMIC_EXECUTION`
- Maturity before → after: `FUNCTIONAL_STARTER` → `EMPIRICALLY_VALIDATED`
- Evidence state: `PLANNED`
- Governance traceability gate: `POST-SUBTASK-132`

## Read first

1. `jira/records/issues/subtasks/POST-SUBTASK-128_implement_source_api_terms_schema_entity_feature_data_model_concept_freshness_se.json`
2. `jira/sources/issue_source_manifests/POST-SUBTASK-128.json`
3. `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv` row for `POST-SUBTASK-128`.
4. Only these additional files/sections, plus verified prerequisite outputs:

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w23_operations.py
- src/aggie_analytics/operations/backup.py
- src/aggie_analytics/operations/observability.py
- docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md
- docs/operations/CI_SECURITY_SUPPLY_CHAIN.md
- docs/operations/BACKUP_RESTORE_RETENTION_RUNBOOK.md
- docs/operations/OBSERVABILITY.md

## Dependencies that must already be complete

- POST-SUBTASK-024
- POST-SUBTASK-126
- POST-SUBTASK-127

## Files I may modify or create

- src/aggie_analytics/operations/drift_alerts.py
- src/aggie_analytics/operations/__init__.py
- tests/test_operations_drift_alerts.py
- tools/build_drift_alert_validation.py
- tools/validate_drift_alerts.py
- docs/operations/OBSERVABILITY.md
- artifacts/operations/drift_alert_validation.json
- artifacts/jira_evidence/POST-SUBTASK-128.json
- jira/records/issues/subtasks/POST-SUBTASK-128_implement_source_api_terms_schema_entity_feature_data_model_concept_freshness_se.json
- jira/issues/subtasks/POST-SUBTASK-128_implement_source_api_terms_schema_entity_feature_data_model_concept_freshness_se.md
- jira/ai/work_packets/POST-SUBTASK-128.md
- jira/sources/issue_source_manifests/POST-SUBTASK-128.json
- jira/index/
- jira/import/
- jira/sources/SOURCE_ANCHOR_INDEX.csv
- jira/sources/issue_source_manifests/
- jira/validation/
- configs/codex_usage_interlock_change_manifest.json
- configs/unified_assistive_change_routing_binding.json
- provenance/CURRENT_TREE.txt
- provenance/PROJECT_FILE_HASHES.sha256
- provenance/PROJECT_FILE_MANIFEST.csv

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

- artifacts/operations/drift_alert_validation.json

## Acceptance criteria

1. Versioned baselines and evidence-derived thresholds identify affected scope, block unsafe downstream training/publication, and route alerts without claiming resolution until evidence changes.
2. The declared output `artifacts/operations/drift_alert_validation.json` is produced with deterministic identity, provenance, and validation metadata appropriate to this work.
3. The work does not fabricate source availability, empirical results, thresholds, model performance, operational readiness, or completion evidence.

## Tests / validation

- EXISTING_AUTOMATED_TEST / OPERATIONS: tests/test_operations_drift_alerts.py — All twelve drift classes, threshold provenance, scoped effects, deterministic deduplication, acknowledgement, evidence-backed escalation, resolution-after-evidence-change, terms metadata nonblocking behavior, and mutation rejection pass.
- EXISTING_AUTOMATED_TEST / INTEGRATION: tools/validate_drift_alerts.py — The content-addressed validation artifact and downstream POST-SUBTASK-129 interface reject stale, mutated, incomplete, or policy-incompatible evidence.
- EXISTING_AUTOMATED_TEST / REGRESSION: tests/test_w23_operations.py — Run as a regression check after completing POST-SUBTASK-128; retain command, exit code, and relevant output.
- EXISTING_AUTOMATED_TEST / REGRESSION: tools/validate_w23_operations.py — Run as a regression check after completing POST-SUBTASK-128; retain command, exit code, and relevant output.
- PUBLICATION_BOUNDARY_REVIEW / PUBLICATION_BOUNDARY_REVIEW: MANUAL — Verify license/terms/redistribution metadata is preserved without blocking private acquisition or training, and that raw third-party publication remains disabled.
- MANUAL / MANUAL: artifacts/operations/drift_alert_validation.json — Verify the private-use decision, metadata state, technical/quality scope, and future-publication boundary.
- SCIENTIFIC / SCIENTIFIC: artifacts/operations/drift_alert_validation.json — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- SECURITY / SECURITY: artifacts/operations/drift_alert_validation.json — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- OPERATIONS / OPERATIONS: artifacts/operations/drift_alert_validation.json — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- INTEGRATION / INTEGRATION: artifacts/operations/drift_alert_validation.json — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- REPRODUCIBILITY / REPRODUCIBILITY: ISSUE_COMPLETION_MANIFEST — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Evidence to return

- `artifacts/operations/drift_alert_validation.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.
- Scientific/model evidence with dataset/matrix/split/model/calibrator identities, sample size, metrics/uncertainty, precommitment, failed/null results, and protected-evaluation status.

## End-to-end handoff

Validate that `artifacts/operations/drift_alert_validation.json` can be parsed and consumed by `POST-SUBTASK-129` using only documented identities and interfaces; the consumer must reject missing, stale, schema-incompatible, technically or quality-ineligible, or provenance-incomplete input without manual repair.

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
