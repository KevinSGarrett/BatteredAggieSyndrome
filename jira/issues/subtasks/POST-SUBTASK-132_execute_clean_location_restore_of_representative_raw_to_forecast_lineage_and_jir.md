<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-132_execute_clean_location_restore_of_representative_raw_to_forecast_lineage_and_jir.json -->
# POST-SUBTASK-132 — [POST-SUBTASK-132] Execute clean-location restore of representative raw-to-forecast lineage and Jira metadata with measured RPO/RTO/manual steps

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-004",
    "AC-036",
    "AC-039",
    "AC-040",
    "AC-041",
    "AC-042",
    "AC-130",
    "AC-187",
    "AC-196",
    "AC-212",
    "AC-219"
  ],
  "acceptance_criteria": [
    "Canonical protected evidence, negative results, source-policy metadata, and issue history retain required immutability while raw third-party data never copies to publication destinations.",
    "Backups are independently readable/content-hashed/cataloged/permission-checked, partial/corrupt copies never replace good state, and Jira canonical records/key map/change log/indexes are included efficiently.",
    "A clean restore passes hash/schema/reference/lineage validation, identifies external credentials/rights reconfiguration, measures recovery, and success is not inferred from backup creation alone.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [
    "ADR-036",
    "ADR-039",
    "ADR-040",
    "ADR-061",
    "ADR-336",
    "ADR-338",
    "ADR-339"
  ],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-044. Governance traceability gate: POST-SUBTASK-132. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-132.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/operations/restore_drill.json",
    "artifacts/jira_evidence/POST-SUBTASK-132.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-129;POST-SUBTASK-130;POST-SUBTASK-131",
  "blocks": [
    "POST-EPIC-015",
    "POST-STORY-045",
    "POST-SUBTASK-133",
    "POST-SUBTASK-134",
    "POST-SUBTASK-135"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-132_execute_clean_location_restore_of_representative_raw_to_forecast_lineage_and_jir.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-044",
    "governance_traceability_gate": "POST-SUBTASK-132",
    "negative_results_preserved": true,
    "provenance_dimensions": [
      "source",
      "data",
      "code",
      "config",
      "tool",
      "runtime",
      "split/cutoff when applicable"
    ]
  },
  "component": "operations-security",
  "components_expected_to_be_touched": [
    "operations-security",
    "operations"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-132 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-044."
  ],
  "dependencies": [
    "POST-SUBTASK-129",
    "POST-SUBTASK-130",
    "POST-SUBTASK-131"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 11,
    "adr_ids": 7,
    "gap_ids": 0,
    "requirement_ids": 39,
    "risk_ids": 10
  },
  "effective_traceability_total": 67,
  "end_to_end_validation": "A verified backup can restore selected canonical lineage and Jira execution state into a clean location without rewriting history or violating data rights. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-015, POST-STORY-045, POST-SUBTASK-133, POST-SUBTASK-134, POST-SUBTASK-135.",
  "epic_id": "POST-EPIC-014",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-132.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/operations/restore_drill.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "governance/REQUIREMENTS_INDEX.csv",
    "tests/test_w23_operations.py",
    "docs/operations/BACKUP_RESTORE_RETENTION_RUNBOOK.md",
    "src/aggie_analytics/operations/backup.py",
    "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md",
    "docs/operations/CI_SECURITY_SUPPLY_CHAIN.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "governance/REQUIREMENTS_INDEX.csv",
    "tests/test_w23_operations.py",
    "docs/operations/BACKUP_RESTORE_RETENTION_RUNBOOK.md",
    "src/aggie_analytics/operations/backup.py",
    "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md",
    "docs/operations/CI_SECURITY_SUPPLY_CHAIN.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-132_execute_clean_location_restore_of_representative_raw_to_forecast_lineage_and_jir.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-132",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100436,
  "in_scope": [
    "Perform the exact action: Execute clean-location restore of representative raw-to-forecast lineage and Jira metadata with measured RPO/RTO/manual steps.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-129`, `POST-SUBTASK-130`, `POST-SUBTASK-131`.",
    "Demonstrate with saved evidence: Canonical protected evidence, negative results, source-policy metadata, and issue history retain required immutability while raw third-party data never copies to publication destinations.",
    "Demonstrate with saved evidence: Backups are independently readable/content-hashed/cataloged/permission-checked, partial/corrupt copies never replace good state, and Jira canonical records/key map/change log/indexes are included efficiently.",
    "Demonstrate with saved evidence: A clean restore passes hash/schema/reference/lineage validation, identifies external credentials/rights reconfiguration, measures recovery, and success is not inferred from backup creation alone.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/operations/restore_drill.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-482",
  "labels": [
    "actionable",
    "core-release",
    "operations",
    "post-wave",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-132",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Execute clean-location restore of representative raw-to-forecast lineage and Jira metadata with measured RPO/RTO/manual steps",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24622",
    "jira_updated_at": "2026-08-09T00:05:16.817-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Finalize authority/retention/frequency/encryption/access/rights/deletion rules for raw, curated, model, forecast, log, evidence, and Jira metadata; Implement content-hashed verified backups, catalog, integrity checking, last-known-good protection, and restricted-destination enforcement.",
    "Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.",
    "Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.",
    "Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-044",
  "phase": "PHASE-4",
  "prerequisites": [
    "Dependency POST-SUBTASK-129 complete at required maturity",
    "Dependency POST-SUBTASK-130 complete at required maturity",
    "Dependency POST-SUBTASK-131 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02092",
    "SRCREF-02093",
    "SRCREF-02094",
    "SRCREF-02095"
  ],
  "priority": "P2",
  "protected_change_required": false,
  "protected_files_and_interfaces": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_ACCEPTANCE_RULES.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv",
    "configs/judging_rule_seal.json",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md"
  ],
  "read_only_context_paths": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_ACCEPTANCE_RULES.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv",
    "configs/judging_rule_seal.json",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/ADR_INDEX.csv",
    "governance/REQUIREMENTS_INDEX.csv",
    "tests/test_w23_operations.py",
    "docs/operations/BACKUP_RESTORE_RETENTION_RUNBOOK.md",
    "src/aggie_analytics/operations/backup.py",
    "docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md",
    "docs/operations/CI_SECURITY_SUPPLY_CHAIN.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/operations/restore_drill.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.",
    "Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.",
    "Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-132; retain command, exit code, and relevant output.",
      "path": "tests/test_w23_operations.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-132; retain command, exit code, and relevant output.",
      "path": "tools/validate_w23_operations.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "BENCHMARK",
      "expectation": "Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.",
      "path": "artifacts/operations/restore_drill.json",
      "validation_class": "BENCHMARK"
    },
    {
      "classification": "SECURITY",
      "expectation": "Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.",
      "path": "artifacts/operations/restore_drill.json",
      "validation_class": "SECURITY"
    },
    {
      "classification": "OPERATIONS",
      "expectation": "Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.",
      "path": "artifacts/operations/restore_drill.json",
      "validation_class": "OPERATIONS"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/operations/restore_drill.json",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "REPRODUCIBILITY",
      "expectation": "Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.",
      "path": "ISSUE_COMPLETION_MANIFEST",
      "validation_class": "REPRODUCIBILITY"
    }
  ],
  "requirement_ids": [
    "REQ-018",
    "REQ-056",
    "REQ-112",
    "REQ-113",
    "REQ-114",
    "REQ-123",
    "REQ-134",
    "REQ-135",
    "REQ-136",
    "REQ-138",
    "REQ-140",
    "REQ-141",
    "REQ-145",
    "REQ-149",
    "REQ-151",
    "REQ-184",
    "REQ-185",
    "REQ-186",
    "REQ-187",
    "REQ-188",
    "REQ-189",
    "REQ-203",
    "REQ-214",
    "REQ-320",
    "REQ-393",
    "REQ-402",
    "REQ-622",
    "REQ-623",
    "REQ-658",
    "REQ-660",
    "REQ-661",
    "REQ-670",
    "REQ-672",
    "REQ-684",
    "REQ-685",
    "REQ-691",
    "REQ-731",
    "REQ-734",
    "REQ-735"
  ],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-132.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that canonical protected evidence, negative results, source-policy metadata, and issue history retain required immutability while raw third-party data never copies to publication destinations.",
    "Acceptance failure: the evidence cannot demonstrate that backups are independently readable/content-hashed/cataloged/permission-checked, partial/corrupt copies never replace good state, and Jira canonical records/key map/change log/indexes are included efficiently.",
    "Acceptance failure: the evidence cannot demonstrate that a clean restore passes hash/schema/reference/lineage validation, identifies external credentials/rights reconfiguration, measures recovery, and success is not inferred from backup creation alone.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [
    "RISK-033",
    "RISK-034",
    "RISK-035",
    "RISK-053",
    "RISK-153",
    "RISK-186",
    "RISK-259",
    "RISK-281",
    "RISK-305",
    "RISK-306"
  ],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-044 (Rights-aware backup, restore, retention, and disaster recovery): Execute clean-location restore of representative raw-to-forecast lineage and Jira metadata with measured RPO/RTO/manual steps. Consume only verified prerequisite outputs from `POST-SUBTASK-129`, `POST-SUBTASK-130`, `POST-SUBTASK-131`. Produce `artifacts/operations/restore_drill.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "HANDOFF-012"
  ],
  "source_refs": [
    "SRCREF-02092",
    "SRCREF-02093",
    "SRCREF-02094",
    "SRCREF-02095",
    "SRCREF-02096",
    "SRCREF-02097",
    "SRCREF-02098",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01898",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "specificity_fingerprint": "be1def5e2c45f6d26bc9579778188207b6332daebef85e9ddc3659843ab17172",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02096",
    "SRCREF-02097",
    "SRCREF-02098",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01898",
    "SRCREF-02116",
    "SRCREF-02117",
    "SRCREF-02118"
  ],
  "title": "[POST-SUBTASK-132] Execute clean-location restore of representative raw-to-forecast lineage and Jira metadata with measured RPO/RTO/manual steps",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "BENCHMARK",
    "END_TO_END",
    "OPERATIONS",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SECURITY"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-044: Rights-aware backup, restore, retention, and disaster recovery.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-132.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Execute clean-location restore of representative raw-to-forecast lineage and Jira metadata with measured RPO/RTO/manual steps

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-044: Rights-aware backup, restore, retention, and disaster recovery.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-044 (Rights-aware backup, restore, retention, and disaster recovery): Execute clean-location restore of representative raw-to-forecast lineage and Jira metadata with measured RPO/RTO/manual steps. Consume only verified prerequisite outputs from `POST-SUBTASK-129`, `POST-SUBTASK-130`, `POST-SUBTASK-131`. Produce `artifacts/operations/restore_drill.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Execute clean-location restore of representative raw-to-forecast lineage and Jira metadata with measured RPO/RTO/manual steps.
- Consume only verified prerequisite outputs from `POST-SUBTASK-129`, `POST-SUBTASK-130`, `POST-SUBTASK-131`.
- Demonstrate with saved evidence: Canonical protected evidence, negative results, source-policy metadata, and issue history retain required immutability while raw third-party data never copies to publication destinations.
- Demonstrate with saved evidence: Backups are independently readable/content-hashed/cataloged/permission-checked, partial/corrupt copies never replace good state, and Jira canonical records/key map/change log/indexes are included efficiently.
- Demonstrate with saved evidence: A clean restore passes hash/schema/reference/lineage validation, identifies external credentials/rights reconfiguration, measures recovery, and success is not inferred from backup creation alone.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/operations/restore_drill.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Finalize authority/retention/frequency/encryption/access/rights/deletion rules for raw, curated, model, forecast, log, evidence, and Jira metadata; Implement content-hashed verified backups, catalog, integrity checking, last-known-good protection, and restricted-destination enforcement.
- Reintroducing a license/terms/redistribution gate for private acquisition or training, or publishing raw third-party payloads without a separate future review.
- Placing credential values in Git, logs, screenshots, Jira descriptions, evidence payloads, or generated import files.
- Substituting a non-authoritative machine, estimated timing, or synthetic benchmark result for the declared target-host evidence.

## Prerequisites

- Dependency POST-SUBTASK-129 complete at required maturity
- Dependency POST-SUBTASK-130 complete at required maturity
- Dependency POST-SUBTASK-131 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-129
- POST-SUBTASK-130
- POST-SUBTASK-131

## Blocks

- POST-EPIC-015
- POST-STORY-045
- POST-SUBTASK-133
- POST-SUBTASK-134
- POST-SUBTASK-135

## Read / Inspect First

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

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- operations-security
- operations

## Protected Files / Interfaces

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_ACCEPTANCE_RULES.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv
- configs/judging_rule_seal.json
- docs/45_SCIENTIFIC_BAS_SPECIFICATION.md

## Expected Outputs / Artifacts

- artifacts/operations/restore_drill.json

## Direct Requirements

- REQ-018
- REQ-056
- REQ-112
- REQ-113
- REQ-114
- REQ-123
- REQ-134
- REQ-135
- REQ-136
- REQ-138
- REQ-140
- REQ-141
- REQ-145
- REQ-149
- REQ-151
- REQ-184
- REQ-185
- REQ-186
- REQ-187
- REQ-188
- REQ-189
- REQ-203
- REQ-214
- REQ-320
- REQ-393
- REQ-402
- REQ-622
- REQ-623
- REQ-658
- REQ-660
- REQ-661
- REQ-670
- REQ-672
- REQ-684
- REQ-685
- REQ-691
- REQ-731
- REQ-734
- REQ-735

## Direct Acceptance Controls

- AC-004
- AC-036
- AC-039
- AC-040
- AC-041
- AC-042
- AC-130
- AC-187
- AC-196
- AC-212
- AC-219

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-132`
- Inherited from: None
- Resolution: `DIRECT_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 11, "adr_ids": 7, "gap_ids": 0, "requirement_ids": 39, "risk_ids": 10}`

## Acceptance Criteria

1. Canonical protected evidence, negative results, source-policy metadata, and issue history retain required immutability while raw third-party data never copies to publication destinations.
2. Backups are independently readable/content-hashed/cataloged/permission-checked, partial/corrupt copies never replace good state, and Jira canonical records/key map/change log/indexes are included efficiently.
3. A clean restore passes hash/schema/reference/lineage validation, identifies external credentials/rights reconfiguration, measures recovery, and success is not inferred from backup creation alone.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-132 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-044.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w23_operations.py` — Run as a regression check after completing POST-SUBTASK-132; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_w23_operations.py` — Run as a regression check after completing POST-SUBTASK-132; retain command, exit code, and relevant output.
- **BENCHMARK** / `BENCHMARK` — `artifacts/operations/restore_drill.json` — Execute the declared workload with raw samples, repetitions, machine identity, resource telemetry, failures, and non-authoritative-environment labeling.
- **SECURITY** / `SECURITY` — `artifacts/operations/restore_drill.json` — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- **OPERATIONS** / `OPERATIONS` — `artifacts/operations/restore_drill.json` — Exercise the operating/failure/rollback or recovery path and retain timestamps, identifiers, alerts, and operator decisions.
- **END_TO_END** / `END_TO_END` — `artifacts/operations/restore_drill.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/operations/restore_drill.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- Nonblocking source-policy metadata recording provider/terms version, access purpose, retention, model-training use, publication boundary, redistribution metadata, source URL, acquisition time, and private-research allow decision.
- Redacted credential-inventory/smoke evidence proving values remained outside Git, Jira, logs, screenshots, and generated artifacts.
- Raw benchmark samples and machine inventory, including OS/CPU/RAM/GPU/storage, workload hash, repetitions, warm/cold distinction, errors, peak resources, and authority classification.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "PRODUCTION_READY",
  "downstream_consumer": "POST-STORY-044",
  "governance_traceability_gate": "POST-SUBTASK-132",
  "negative_results_preserved": true,
  "provenance_dimensions": [
    "source",
    "data",
    "code",
    "config",
    "tool",
    "runtime",
    "split/cutoff when applicable"
  ]
}
```

## End-to-End Validation Requirement

A verified backup can restore selected canonical lineage and Jira execution state into a clean location without rewriting history or violating data rights. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-015, POST-STORY-045, POST-SUBTASK-133, POST-SUBTASK-134, POST-SUBTASK-135.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-132.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that canonical protected evidence, negative results, source-policy metadata, and issue history retain required immutability while raw third-party data never copies to publication destinations.
- Acceptance failure: the evidence cannot demonstrate that backups are independently readable/content-hashed/cataloged/permission-checked, partial/corrupt copies never replace good state, and Jira canonical records/key map/change log/indexes are included efficiently.
- Acceptance failure: the evidence cannot demonstrate that a clean restore passes hash/schema/reference/lineage validation, identifies external credentials/rights reconfiguration, measures recovery, and success is not inferred from backup creation alone.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02092
- SRCREF-02093
- SRCREF-02094
- SRCREF-02095
- SRCREF-02096
- SRCREF-02097
- SRCREF-02098
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01898
- SRCREF-02116
- SRCREF-02117
- SRCREF-02118

## AI Context Notes

- Canonical parent Story: POST-STORY-044. Governance traceability gate: POST-SUBTASK-132. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-132.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.
