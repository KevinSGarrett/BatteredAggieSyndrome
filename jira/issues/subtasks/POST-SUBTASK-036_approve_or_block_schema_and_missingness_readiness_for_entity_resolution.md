<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-036_approve_or_block_schema_and_missingness_readiness_for_entity_resolution.json -->
# POST-SUBTASK-036 — [POST-SUBTASK-036] Approve or block schema and missingness readiness for entity resolution

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Profiles are generated from pinned immutable snapshots by source/season/domain and reproduce exactly.",
    "Every measured field is accepted, transformed, quarantined, deprecated, or rejected with reason; protected temporal/evidence fields are not weakened to accommodate dirty data.",
    "All entity-bearing domains have measured key quality and a declared resolution strategy; unusable partitions remain enumerated rather than silently dropped.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-012. Governance traceability gate: POST-SUBTASK-042. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-036.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/entities/schema_readiness_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-036.json"
  ],
  "blocked_reason": "UNSATISFIED_HARD_DEPENDENCIES: POST-SUBTASK-034;POST-SUBTASK-035",
  "blocks": [
    "POST-STORY-013",
    "POST-SUBTASK-037",
    "POST-SUBTASK-038",
    "POST-SUBTASK-039"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-036_approve_or_block_schema_and_missingness_readiness_for_entity_resolution.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-012",
    "governance_traceability_gate": "POST-SUBTASK-042",
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
  "component": "entities",
  "components_expected_to_be_touched": [
    "entities"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-036 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-012."
  ],
  "dependencies": [
    "POST-SUBTASK-033",
    "POST-SUBTASK-034",
    "POST-SUBTASK-035"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 11,
    "adr_ids": 13,
    "gap_ids": 1,
    "requirement_ids": 22,
    "risk_ids": 9
  },
  "effective_traceability_total": 56,
  "end_to_end_validation": "Real raw populations produce versioned schema/missingness contracts and an explicit readiness decision for resolution. The gate decision must explicitly reevaluate downstream issues: POST-STORY-013, POST-SUBTASK-037, POST-SUBTASK-038, POST-SUBTASK-039.",
  "epic_id": "POST-EPIC-004",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-036.json",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/entities/schema_readiness_gate.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_entity_governance.py",
    "src/aggie_analytics/entities/resolution.py",
    "docs/14_CANONICAL_ENTITY_ARCHITECTURE.md",
    "docs/16_ENTITY_RESOLUTION_AND_REVIEW.md",
    "governance/ENTITY_RESOLUTION_STATES.csv"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_entity_governance.py",
    "src/aggie_analytics/entities/resolution.py",
    "docs/14_CANONICAL_ENTITY_ARCHITECTURE.md",
    "docs/16_ENTITY_RESOLUTION_AND_REVIEW.md",
    "governance/ENTITY_RESOLUTION_STATES.csv"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-036_approve_or_block_schema_and_missingness_readiness_for_entity_resolution.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-042",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100340,
  "in_scope": [
    "Perform the exact action: Approve or block schema and missingness readiness for entity resolution.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-033`, `POST-SUBTASK-034`, `POST-SUBTASK-035`.",
    "Demonstrate with saved evidence: Profiles are generated from pinned immutable snapshots by source/season/domain and reproduce exactly.",
    "Demonstrate with saved evidence: Every measured field is accepted, transformed, quarantined, deprecated, or rejected with reason; protected temporal/evidence fields are not weakened to accommodate dirty data.",
    "Demonstrate with saved evidence: All entity-bearing domains have measured key quality and a declared resolution strategy; unusable partitions remain enumerated rather than silently dropped.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/entities/schema_readiness_gate.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-386",
  "labels": [
    "actionable",
    "core-release",
    "entities",
    "post-wave",
    "protected-gate",
    "subtask"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-036",
  "maturity_before": "FUNCTIONAL_STARTER",
  "objective": "Approve or block schema and missingness readiness for entity resolution",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24526",
    "jira_updated_at": "2026-08-09T00:03:33.299-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Profile every materialized table for rows, types, nulls, uniqueness, ranges, duplicates, timestamps, and partitions; Reconcile measured fields with canonical contracts, compatibility policy, and quarantine/rejection decisions."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-012",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-033 complete at required maturity",
    "Dependency POST-SUBTASK-034 complete at required maturity",
    "Dependency POST-SUBTASK-035 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02019",
    "SRCREF-02020",
    "SRCREF-02021",
    "SRCREF-02022"
  ],
  "priority": "P0",
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
    "tests/test_entity_governance.py",
    "src/aggie_analytics/entities/resolution.py",
    "docs/14_CANONICAL_ENTITY_ARCHITECTURE.md",
    "docs/16_ENTITY_RESOLUTION_AND_REVIEW.md",
    "governance/ENTITY_RESOLUTION_STATES.csv"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/entities/schema_readiness_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-036; retain command, exit code, and relevant output.",
      "path": "tests/test_entity_governance.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-036; retain command, exit code, and relevant output.",
      "path": "tools/validate_entities.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/entities/schema_readiness_gate.json",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "REPRODUCIBILITY",
      "expectation": "Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.",
      "path": "ISSUE_COMPLETION_MANIFEST",
      "validation_class": "REPRODUCIBILITY"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-036.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that profiles are generated from pinned immutable snapshots by source/season/domain and reproduce exactly.",
    "Acceptance failure: the evidence cannot demonstrate that every measured field is accepted, transformed, quarantined, deprecated, or rejected with reason; protected temporal/evidence fields are not weakened to accommodate dirty data.",
    "Acceptance failure: the evidence cannot demonstrate that all entity-bearing domains have measured key quality and a declared resolution strategy; unusable partitions remain enumerated rather than silently dropped.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-012 (Population schema and missingness contracts): Approve or block schema and missingness readiness for entity resolution. Consume only verified prerequisite outputs from `POST-SUBTASK-033`, `POST-SUBTASK-034`, `POST-SUBTASK-035`. Produce `artifacts/entities/schema_readiness_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-003",
    "GAP-004"
  ],
  "source_refs": [
    "SRCREF-02019",
    "SRCREF-02020",
    "SRCREF-02021",
    "SRCREF-02022",
    "SRCREF-02023",
    "SRCREF-02024",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01565",
    "SRCREF-01566"
  ],
  "specificity_fingerprint": "7ffa2c036450d323512d922c15bf1917283d63d90de8646cfe9065f901a9517b",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02023",
    "SRCREF-02024",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01565",
    "SRCREF-01566"
  ],
  "title": "[POST-SUBTASK-036] Approve or block schema and missingness readiness for entity resolution",
  "traceability_inherited_from": [
    "POST-SUBTASK-042"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "Complete and verify all hard dependencies at required maturity/evidence.",
  "validation_classes": [
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-012: Population schema and missingness contracts.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-036.md",
  "workflow_state": "BLOCKED"
}
```

## Objective

Approve or block schema and missingness readiness for entity resolution

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-012: Population schema and missingness contracts.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-012 (Population schema and missingness contracts): Approve or block schema and missingness readiness for entity resolution. Consume only verified prerequisite outputs from `POST-SUBTASK-033`, `POST-SUBTASK-034`, `POST-SUBTASK-035`. Produce `artifacts/entities/schema_readiness_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Approve or block schema and missingness readiness for entity resolution.
- Consume only verified prerequisite outputs from `POST-SUBTASK-033`, `POST-SUBTASK-034`, `POST-SUBTASK-035`.
- Demonstrate with saved evidence: Profiles are generated from pinned immutable snapshots by source/season/domain and reproduce exactly.
- Demonstrate with saved evidence: Every measured field is accepted, transformed, quarantined, deprecated, or rejected with reason; protected temporal/evidence fields are not weakened to accommodate dirty data.
- Demonstrate with saved evidence: All entity-bearing domains have measured key quality and a declared resolution strategy; unusable partitions remain enumerated rather than silently dropped.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/entities/schema_readiness_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Profile every materialized table for rows, types, nulls, uniqueness, ranges, duplicates, timestamps, and partitions; Reconcile measured fields with canonical contracts, compatibility policy, and quarantine/rejection decisions.

## Prerequisites

- Dependency POST-SUBTASK-033 complete at required maturity
- Dependency POST-SUBTASK-034 complete at required maturity
- Dependency POST-SUBTASK-035 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-033
- POST-SUBTASK-034
- POST-SUBTASK-035

## Blocks

- POST-STORY-013
- POST-SUBTASK-037
- POST-SUBTASK-038
- POST-SUBTASK-039

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_entity_governance.py
- src/aggie_analytics/entities/resolution.py
- docs/14_CANONICAL_ENTITY_ARCHITECTURE.md
- docs/16_ENTITY_RESOLUTION_AND_REVIEW.md
- governance/ENTITY_RESOLUTION_STATES.csv

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- entities

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

- artifacts/entities/schema_readiness_gate.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-042`
- Inherited from: POST-SUBTASK-042
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 11, "adr_ids": 13, "gap_ids": 1, "requirement_ids": 22, "risk_ids": 9}`

## Acceptance Criteria

1. Profiles are generated from pinned immutable snapshots by source/season/domain and reproduce exactly.
2. Every measured field is accepted, transformed, quarantined, deprecated, or rejected with reason; protected temporal/evidence fields are not weakened to accommodate dirty data.
3. All entity-bearing domains have measured key quality and a declared resolution strategy; unusable partitions remain enumerated rather than silently dropped.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-036 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-012.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_entity_governance.py` — Run as a regression check after completing POST-SUBTASK-036; retain command, exit code, and relevant output.
- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tools/validate_entities.py` — Run as a regression check after completing POST-SUBTASK-036; retain command, exit code, and relevant output.
- **END_TO_END** / `END_TO_END` — `artifacts/entities/schema_readiness_gate.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/entities/schema_readiness_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "PRODUCTION_READY",
  "downstream_consumer": "POST-STORY-012",
  "governance_traceability_gate": "POST-SUBTASK-042",
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

Real raw populations produce versioned schema/missingness contracts and an explicit readiness decision for resolution. The gate decision must explicitly reevaluate downstream issues: POST-STORY-013, POST-SUBTASK-037, POST-SUBTASK-038, POST-SUBTASK-039.

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-036.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that profiles are generated from pinned immutable snapshots by source/season/domain and reproduce exactly.
- Acceptance failure: the evidence cannot demonstrate that every measured field is accepted, transformed, quarantined, deprecated, or rejected with reason; protected temporal/evidence fields are not weakened to accommodate dirty data.
- Acceptance failure: the evidence cannot demonstrate that all entity-bearing domains have measured key quality and a declared resolution strategy; unusable partitions remain enumerated rather than silently dropped.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02019
- SRCREF-02020
- SRCREF-02021
- SRCREF-02022
- SRCREF-02023
- SRCREF-02024
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01565
- SRCREF-01566

## AI Context Notes

- Canonical parent Story: POST-STORY-012. Governance traceability gate: POST-SUBTASK-042. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-036.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.
