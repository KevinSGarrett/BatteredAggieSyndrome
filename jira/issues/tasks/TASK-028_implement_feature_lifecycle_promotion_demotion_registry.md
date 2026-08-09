<!-- GENERATED VIEW. Canonical record: jira/records/issues/tasks/TASK-028_implement_feature_lifecycle_promotion_demotion_registry.json -->
# TASK-028 — [TASK-028] Implement feature lifecycle promotion/demotion registry

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-021",
    "AC-055",
    "AC-056",
    "AC-089",
    "AC-090",
    "AC-091"
  ],
  "acceptance_criteria": [
    "Stable ID TASK-028, parent EPIC-005, owner wave W10, and original status DONE are preserved.",
    "Declared outputs are traceable to existing repository artifacts where resolvable, or remain recorded as historical output names without fabricating files.",
    "Requirement, acceptance-control, and dependency references resolve to authoritative registries.",
    "The record does not claim maturity beyond the task's original design, contract, functional-starter, synthetic-validation, or integration scope."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "This is historical WBS provenance. Execute the mapped post-wave issue for remaining maturity work.",
    "W10 contract/reference implementation complete; empirical feature value/promotion remains pending real-data chronological evaluation."
  ],
  "allowed_modification_paths": [
    "CORE/SUPPORTED/CONDITIONAL/EXPERIMENTAL/REJECTED/BANNED transitions"
  ],
  "blocked_reason": "",
  "blocks": [
    "TASK-029"
  ],
  "canonical_record": "jira/records/issues/tasks/TASK-028_implement_feature_lifecycle_promotion_demotion_registry.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {},
  "component": "validation-promotion",
  "components_expected_to_be_touched": [
    "validation-promotion"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The original historical scope and status are preserved with source evidence and stable identifiers.",
    "The record does not claim production maturity beyond the original design, contract, starter, integration, or validation scope.",
    "Any remaining empirical, production, target-hardware, or operating obligation is represented by separate actionable post-wave work."
  ],
  "dependencies": [
    "TASK-027"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 6,
    "adr_ids": 0,
    "gap_ids": 0,
    "requirement_ids": 9,
    "risk_ids": 0
  },
  "effective_traceability_total": 15,
  "end_to_end_validation": "Historical completion remains scoped; integrated product completion is evaluated only through the post-wave release path.",
  "epic_id": "EPIC-005",
  "evidence_manifest_path": "",
  "evidence_state": "VERIFIED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "CONTRACT_DEFINED",
  "expected_outputs": [
    "CORE/SUPPORTED/CONDITIONAL/EXPERIMENTAL/REJECTED/BANNED transitions"
  ],
  "files_expected_to_be_read": [
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "governance/REQUIREMENTS_INDEX.csv"
  ],
  "files_expected_to_be_touched": [
    "CORE/SUPPORTED/CONDITIONAL/EXPERIMENTAL/REJECTED/BANNED transitions"
  ],
  "files_to_inspect": [
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "governance/REQUIREMENTS_INDEX.csv"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/tasks/TASK-028_implement_feature_lifecycle_promotion_demotion_registry.md",
  "governance_review_required": false,
  "governance_traceability_gate": "",
  "historical_classification": "HISTORICAL_SCOPED_COMPLETED",
  "import_id": 100131,
  "in_scope": [
    "Original WBS objective and outputs",
    "Original requirements and acceptance-control mappings",
    "Original dependency and execution-lane provenance"
  ],
  "issue_type": "Task",
  "jira_key": "BAT-131",
  "labels": [
    "governance-implementation",
    "historical",
    "planning-program",
    "w10",
    "wave-completed"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "TASK-028",
  "maturity_before": "DESIGN_ONLY",
  "objective": "Implement feature lifecycle promotion/demotion registry",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24271",
    "jira_updated_at": "2026-08-09T00:40:20.956-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Reopening completed planning solely to rename it",
    "Treating a starter/design result as empirically validated production capability"
  ],
  "owner_wave": "W10",
  "parent_id": "EPIC-005",
  "phase": "PHASE-1",
  "prerequisites": [
    "Historical dependency TASK-027"
  ],
  "primary_source_refs": [
    "SRCREF-00061",
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
    "POST-SUBTASK-105"
  ],
  "required_evidence": [
    "Authoritative WBS row TASK-028",
    "Existing artifact `CORE/SUPPORTED/CONDITIONAL/EXPERIMENTAL/REJECTED/BANNED transitions`"
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_validation_science_governance.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_w25_final_handoff.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tools/validate_validation_science.py"
    }
  ],
  "requirement_ids": [
    "REQ-064",
    "REQ-232",
    "REQ-233",
    "REQ-353",
    "REQ-354",
    "REQ-355",
    "REQ-356",
    "REQ-357",
    "REQ-359"
  ],
  "risk_failure_conditions": [
    "Original DONE status may be over-interpreted",
    "Source output path may have moved or been generated under a different canonical directory"
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Original task type GOVERNANCE_IMPLEMENTATION with mutation scope: as defined by its source documents.",
  "source_ids": [
    "TASK-028"
  ],
  "source_refs": [
    "SRCREF-00061",
    "SRCREF-02116",
    "SRCREF-02117"
  ],
  "specificity_fingerprint": "b8fe1160df60788753b01cf946569abca86c7dbad27afa69e89a3801e0ccd480",
  "stop_conditions": [
    "Stop if completing this record would fabricate real-data, model-metric, source-rights, target-hardware, or operating evidence."
  ],
  "supporting_source_refs": [],
  "title": "[TASK-028] Implement feature lifecycle promotion/demotion registry",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT",
  "unblock_condition": "",
  "validation_classes": [
    "EXISTING_AUTOMATED_TEST"
  ],
  "why_this_exists": "Preserve the original W10 WBS work unit, its dependencies, outputs, and scoped completion semantics as provenance for post-wave execution.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Implement feature lifecycle promotion/demotion registry

## Why This Exists

Preserve the original W10 WBS work unit, its dependencies, outputs, and scoped completion semantics as provenance for post-wave execution.

## Scope

Original task type GOVERNANCE_IMPLEMENTATION with mutation scope: as defined by its source documents.

### Explicit In Scope

- Original WBS objective and outputs
- Original requirements and acceptance-control mappings
- Original dependency and execution-lane provenance

### Explicit Out of Scope

- Reopening completed planning solely to rename it
- Treating a starter/design result as empirically validated production capability

## Prerequisites

- Historical dependency TASK-027

## Hard Dependencies

- TASK-027

## Blocks

- TASK-029

## Read / Inspect First

- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/IMPLEMENTATION_WBS.csv
- governance/REQUIREMENTS_INDEX.csv

## Files Expected To Be Modified

- CORE/SUPPORTED/CONDITIONAL/EXPERIMENTAL/REJECTED/BANNED transitions

## Components Expected To Be Touched

- validation-promotion

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

- CORE/SUPPORTED/CONDITIONAL/EXPERIMENTAL/REJECTED/BANNED transitions

## Direct Requirements

- REQ-064
- REQ-232
- REQ-233
- REQ-353
- REQ-354
- REQ-355
- REQ-356
- REQ-357
- REQ-359

## Direct Acceptance Controls

- AC-021
- AC-055
- AC-056
- AC-089
- AC-090
- AC-091

## Governance Traceability Inheritance

- Gate: `None`
- Inherited from: None
- Resolution: `DIRECT`
- Effective counts: `{"acceptance_control_ids": 6, "adr_ids": 0, "gap_ids": 0, "requirement_ids": 9, "risk_ids": 0}`

## Acceptance Criteria

1. Stable ID TASK-028, parent EPIC-005, owner wave W10, and original status DONE are preserved.
2. Declared outputs are traceable to existing repository artifacts where resolvable, or remain recorded as historical output names without fabricating files.
3. Requirement, acceptance-control, and dependency references resolve to authoritative registries.
4. The record does not claim maturity beyond the task's original design, contract, functional-starter, synthetic-validation, or integration scope.

## Definition of Done

1. The original historical scope and status are preserved with source evidence and stable identifiers.
2. The record does not claim production maturity beyond the original design, contract, starter, integration, or validation scope.
3. Any remaining empirical, production, target-hardware, or operating obligation is represented by separate actionable post-wave work.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_validation_science_governance.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_w25_final_handoff.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tools/validate_validation_science.py` — Run and retain the result when this issue touches the covered contract.

## Required Evidence

- Authoritative WBS row TASK-028
- Existing artifact `CORE/SUPPORTED/CONDITIONAL/EXPERIMENTAL/REJECTED/BANNED transitions`

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

- SRCREF-00061
- SRCREF-02116
- SRCREF-02117

## AI Context Notes

- This is historical WBS provenance. Execute the mapped post-wave issue for remaining maturity work.
- W10 contract/reference implementation complete; empirical feature value/promotion remains pending real-data chronological evaluation.
