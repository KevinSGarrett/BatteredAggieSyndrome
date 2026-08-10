<!-- GENERATED VIEW. Canonical record: jira/records/issues/tasks/TASK-019_ingest_recon_w06_schema_inventories_into_registry_staging.json -->
# TASK-019 — [TASK-019] Ingest recon/W06 schema inventories into registry staging

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-009",
    "AC-055",
    "AC-056",
    "AC-077",
    "AC-078"
  ],
  "acceptance_criteria": [
    "Stable ID TASK-019, parent EPIC-004, owner wave W09, and original status DONE are preserved.",
    "Declared outputs are traceable to existing repository artifacts where resolvable, or remain recorded as historical output names without fabricating files.",
    "Requirement, acceptance-control, and dependency references resolve to authoritative registries.",
    "The record does not claim maturity beyond the task's original design, contract, functional-starter, synthetic-validation, or integration scope."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "This is historical WBS provenance. Execute the mapped post-wave issue for remaining maturity work.",
    "Completed W09; registry gate evidence in configs/raw_feature_registry.json and governance/RAW_FIELD_REGISTRY.csv."
  ],
  "allowed_modification_paths": [
    "registry staging imports"
  ],
  "blocked_reason": "",
  "blocks": [
    "TASK-020"
  ],
  "canonical_record": "jira/records/issues/tasks/TASK-019_ingest_recon_w06_schema_inventories_into_registry_staging.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {},
  "component": "feature-engineering",
  "components_expected_to_be_touched": [
    "feature-engineering"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The original historical scope and status are preserved with source evidence and stable identifiers.",
    "The record does not claim production maturity beyond the original design, contract, starter, integration, or validation scope.",
    "Any remaining empirical, production, target-hardware, or operating obligation is represented by separate actionable post-wave work."
  ],
  "dependencies": [
    "TASK-018"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 5,
    "adr_ids": 0,
    "gap_ids": 0,
    "requirement_ids": 8,
    "risk_ids": 0
  },
  "effective_traceability_total": 13,
  "end_to_end_validation": "Historical completion remains scoped; integrated product completion is evaluated only through the post-wave release path.",
  "epic_id": "EPIC-004",
  "evidence_manifest_path": "",
  "evidence_state": "VERIFIED",
  "execution_lane": "SOLO_WORKTREE",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "CONTRACT_DEFINED",
  "expected_outputs": [
    "registry staging imports"
  ],
  "files_expected_to_be_read": [
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "governance/REQUIREMENTS_INDEX.csv"
  ],
  "files_expected_to_be_touched": [
    "registry staging imports"
  ],
  "files_to_inspect": [
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "governance/REQUIREMENTS_INDEX.csv"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/tasks/TASK-019_ingest_recon_w06_schema_inventories_into_registry_staging.md",
  "governance_review_required": false,
  "governance_traceability_gate": "",
  "historical_classification": "HISTORICAL_SCOPED_COMPLETED",
  "import_id": 100122,
  "in_scope": [
    "Original WBS objective and outputs",
    "Original requirements and acceptance-control mappings",
    "Original dependency and execution-lane provenance"
  ],
  "issue_type": "Task",
  "jira_key": "BAT-122",
  "labels": [
    "historical",
    "implementation",
    "planning-program",
    "w09",
    "wave-completed"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "TASK-019",
  "maturity_before": "DESIGN_ONLY",
  "objective": "Ingest recon/W06 schema inventories into registry staging",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24262",
    "jira_updated_at": "2026-08-09T00:40:19.407-0500",
    "last_synced_at": "2026-08-10T04:24:34.496382+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-516-openai-foundation-complete\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Reopening completed planning solely to rename it",
    "Treating a starter/design result as empirically validated production capability"
  ],
  "owner_wave": "W09",
  "parent_id": "EPIC-004",
  "phase": "PHASE-1",
  "prerequisites": [
    "Historical dependency TASK-018"
  ],
  "primary_source_refs": [
    "SRCREF-00052",
    "SRCREF-02116",
    "SRCREF-02117"
  ],
  "priority": "P1",
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
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "governance/REQUIREMENTS_INDEX.csv"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [
    "POST-SUBTASK-060"
  ],
  "required_evidence": [
    "Authoritative WBS row TASK-019",
    "Existing artifact `registry staging imports`"
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_feature_registry_governance.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_feature_lifecycle_governance.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_feature_tournament_full.py"
    }
  ],
  "requirement_ids": [
    "REQ-051",
    "REQ-232",
    "REQ-233",
    "REQ-313",
    "REQ-314",
    "REQ-315",
    "REQ-316",
    "REQ-317"
  ],
  "risk_failure_conditions": [
    "Original DONE status may be over-interpreted",
    "Source output path may have moved or been generated under a different canonical directory"
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Original task type IMPLEMENTATION with mutation scope: as defined by its source documents.",
  "source_ids": [
    "TASK-019"
  ],
  "source_refs": [
    "SRCREF-00052",
    "SRCREF-02116",
    "SRCREF-02117"
  ],
  "specificity_fingerprint": "0aedf06548cb9a3b77b5f362a77e05105db9dd571e5a3f56144aa6a36934c185",
  "stop_conditions": [
    "Stop if completing this record would fabricate real-data, model-metric, source-rights, target-hardware, or operating evidence."
  ],
  "supporting_source_refs": [],
  "title": "[TASK-019] Ingest recon/W06 schema inventories into registry staging",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT",
  "unblock_condition": "",
  "validation_classes": [
    "EXISTING_AUTOMATED_TEST"
  ],
  "why_this_exists": "Preserve the original W09 WBS work unit, its dependencies, outputs, and scoped completion semantics as provenance for post-wave execution.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Ingest recon/W06 schema inventories into registry staging

## Why This Exists

Preserve the original W09 WBS work unit, its dependencies, outputs, and scoped completion semantics as provenance for post-wave execution.

## Scope

Original task type IMPLEMENTATION with mutation scope: as defined by its source documents.

### Explicit In Scope

- Original WBS objective and outputs
- Original requirements and acceptance-control mappings
- Original dependency and execution-lane provenance

### Explicit Out of Scope

- Reopening completed planning solely to rename it
- Treating a starter/design result as empirically validated production capability

## Prerequisites

- Historical dependency TASK-018

## Hard Dependencies

- TASK-018

## Blocks

- TASK-020

## Read / Inspect First

- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/IMPLEMENTATION_WBS.csv
- governance/REQUIREMENTS_INDEX.csv

## Files Expected To Be Modified

- registry staging imports

## Components Expected To Be Touched

- feature-engineering

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

- registry staging imports

## Direct Requirements

- REQ-051
- REQ-232
- REQ-233
- REQ-313
- REQ-314
- REQ-315
- REQ-316
- REQ-317

## Direct Acceptance Controls

- AC-009
- AC-055
- AC-056
- AC-077
- AC-078

## Governance Traceability Inheritance

- Gate: `None`
- Inherited from: None
- Resolution: `DIRECT`
- Effective counts: `{"acceptance_control_ids": 5, "adr_ids": 0, "gap_ids": 0, "requirement_ids": 8, "risk_ids": 0}`

## Acceptance Criteria

1. Stable ID TASK-019, parent EPIC-004, owner wave W09, and original status DONE are preserved.
2. Declared outputs are traceable to existing repository artifacts where resolvable, or remain recorded as historical output names without fabricating files.
3. Requirement, acceptance-control, and dependency references resolve to authoritative registries.
4. The record does not claim maturity beyond the task's original design, contract, functional-starter, synthetic-validation, or integration scope.

## Definition of Done

1. The original historical scope and status are preserved with source evidence and stable identifiers.
2. The record does not claim production maturity beyond the original design, contract, starter, integration, or validation scope.
3. Any remaining empirical, production, target-hardware, or operating obligation is represented by separate actionable post-wave work.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_feature_registry_governance.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_feature_lifecycle_governance.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_feature_tournament_full.py` — Run and retain the result when this issue touches the covered contract.

## Required Evidence

- Authoritative WBS row TASK-019
- Existing artifact `registry staging imports`

## Completion Evidence Contract

```json
{}
```

## End-to-End Validation Requirement

Historical completion remains scoped; integrated product completion is evaluated only through the post-wave release path.

## Expected Maturity After Completion

`CONTRACT_DEFINED`

## Risk / Failure Conditions

- Original DONE status may be over-interpreted
- Source output path may have moved or been generated under a different canonical directory

## Stop Conditions

- Stop if completing this record would fabricate real-data, model-metric, source-rights, target-hardware, or operating evidence.

## Source References

- SRCREF-00052
- SRCREF-02116
- SRCREF-02117

## AI Context Notes

- This is historical WBS provenance. Execute the mapped post-wave issue for remaining maturity work.
- Completed W09; registry gate evidence in configs/raw_feature_registry.json and governance/RAW_FIELD_REGISTRY.csv.
