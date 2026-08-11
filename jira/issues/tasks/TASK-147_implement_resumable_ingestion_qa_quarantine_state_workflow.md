<!-- GENERATED VIEW. Canonical record: jira/records/issues/tasks/TASK-147_implement_resumable_ingestion_qa_quarantine_state_workflow.json -->
# TASK-147 — [TASK-147] Implement resumable ingestion/QA/quarantine/state workflow

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-031",
    "AC-055",
    "AC-056"
  ],
  "acceptance_criteria": [
    "Stable ID TASK-147, parent EPIC-026, owner wave W21, and original status DONE are preserved.",
    "Declared outputs are traceable to existing repository artifacts where resolvable, or remain recorded as historical output names without fabricating files.",
    "Requirement, acceptance-control, and dependency references resolve to authoritative registries.",
    "The record does not claim maturity beyond the task's original design, contract, functional-starter, synthetic-validation, or integration scope."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "This is historical WBS provenance. Execute the mapped post-wave issue for remaining maturity work.",
    "Completed W21 functional-starter scope with executable orchestration/replay evidence."
  ],
  "allowed_modification_paths": [
    "data refresh workflow"
  ],
  "blocked_reason": "",
  "blocks": [
    "TASK-151"
  ],
  "canonical_record": "jira/records/issues/tasks/TASK-147_implement_resumable_ingestion_qa_quarantine_state_workflow.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {},
  "component": "mlops",
  "components_expected_to_be_touched": [
    "mlops"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The original historical scope and status are preserved with source evidence and stable identifiers.",
    "The record does not claim production maturity beyond the original design, contract, starter, integration, or validation scope.",
    "Any remaining empirical, production, target-hardware, or operating obligation is represented by separate actionable post-wave work."
  ],
  "dependencies": [
    "TASK-046",
    "TASK-146"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 3,
    "adr_ids": 0,
    "gap_ids": 0,
    "requirement_ids": 3,
    "risk_ids": 0
  },
  "effective_traceability_total": 6,
  "end_to_end_validation": "Historical completion remains scoped; integrated product completion is evaluated only through the post-wave release path.",
  "epic_id": "EPIC-026",
  "evidence_manifest_path": "",
  "evidence_state": "VERIFIED",
  "execution_lane": "SOLO_WORKTREE",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "data refresh workflow"
  ],
  "files_expected_to_be_read": [
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "governance/REQUIREMENTS_INDEX.csv"
  ],
  "files_expected_to_be_touched": [
    "data refresh workflow"
  ],
  "files_to_inspect": [
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "governance/REQUIREMENTS_INDEX.csv"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/tasks/TASK-147_implement_resumable_ingestion_qa_quarantine_state_workflow.md",
  "governance_review_required": false,
  "governance_traceability_gate": "",
  "historical_classification": "HISTORICAL_SCOPED_COMPLETED",
  "import_id": 100250,
  "in_scope": [
    "Original WBS objective and outputs",
    "Original requirements and acceptance-control mappings",
    "Original dependency and execution-lane provenance"
  ],
  "issue_type": "Task",
  "jira_key": "BAT-250",
  "labels": [
    "historical",
    "implementation",
    "planning-program",
    "w21",
    "wave-completed"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "TASK-147",
  "maturity_before": "DESIGN_ONLY",
  "objective": "Implement resumable ingestion/QA/quarantine/state workflow",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24390",
    "jira_updated_at": "2026-08-09T00:40:44.018-0500",
    "last_synced_at": "2026-08-11T07:44:24.297472+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-523-tamu-availability-pages\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Reopening completed planning solely to rename it",
    "Treating a starter/design result as empirically validated production capability"
  ],
  "owner_wave": "W21",
  "parent_id": "EPIC-026",
  "phase": "PHASE-4",
  "prerequisites": [
    "Historical dependency TASK-146",
    "Historical dependency TASK-046"
  ],
  "primary_source_refs": [
    "SRCREF-00180",
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
    "POST-SUBTASK-114"
  ],
  "required_evidence": [
    "Authoritative WBS row TASK-147",
    "Existing artifact `data refresh workflow`"
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_w21_weekly_mlops.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tools/validate_w21_mlops.py"
    }
  ],
  "requirement_ids": [
    "REQ-115",
    "REQ-232",
    "REQ-233"
  ],
  "risk_failure_conditions": [
    "Original DONE status may be over-interpreted",
    "Source output path may have moved or been generated under a different canonical directory"
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Original task type IMPLEMENTATION with mutation scope: as defined by its source documents.",
  "source_ids": [
    "TASK-147"
  ],
  "source_refs": [
    "SRCREF-00180",
    "SRCREF-02116",
    "SRCREF-02117"
  ],
  "specificity_fingerprint": "8d2d45730380afcb2e23c840129efa0eddf79492c01ef8d1cfd0f2444233c236",
  "stop_conditions": [
    "Stop if completing this record would fabricate real-data, model-metric, source-rights, target-hardware, or operating evidence."
  ],
  "supporting_source_refs": [],
  "title": "[TASK-147] Implement resumable ingestion/QA/quarantine/state workflow",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT",
  "unblock_condition": "",
  "validation_classes": [
    "EXISTING_AUTOMATED_TEST"
  ],
  "why_this_exists": "Preserve the original W21 WBS work unit, its dependencies, outputs, and scoped completion semantics as provenance for post-wave execution.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Implement resumable ingestion/QA/quarantine/state workflow

## Why This Exists

Preserve the original W21 WBS work unit, its dependencies, outputs, and scoped completion semantics as provenance for post-wave execution.

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

- Historical dependency TASK-146
- Historical dependency TASK-046

## Hard Dependencies

- TASK-046
- TASK-146

## Blocks

- TASK-151

## Read / Inspect First

- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/IMPLEMENTATION_WBS.csv
- governance/REQUIREMENTS_INDEX.csv

## Files Expected To Be Modified

- data refresh workflow

## Components Expected To Be Touched

- mlops

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

- data refresh workflow

## Direct Requirements

- REQ-115
- REQ-232
- REQ-233

## Direct Acceptance Controls

- AC-031
- AC-055
- AC-056

## Governance Traceability Inheritance

- Gate: `None`
- Inherited from: None
- Resolution: `DIRECT`
- Effective counts: `{"acceptance_control_ids": 3, "adr_ids": 0, "gap_ids": 0, "requirement_ids": 3, "risk_ids": 0}`

## Acceptance Criteria

1. Stable ID TASK-147, parent EPIC-026, owner wave W21, and original status DONE are preserved.
2. Declared outputs are traceable to existing repository artifacts where resolvable, or remain recorded as historical output names without fabricating files.
3. Requirement, acceptance-control, and dependency references resolve to authoritative registries.
4. The record does not claim maturity beyond the task's original design, contract, functional-starter, synthetic-validation, or integration scope.

## Definition of Done

1. The original historical scope and status are preserved with source evidence and stable identifiers.
2. The record does not claim production maturity beyond the original design, contract, starter, integration, or validation scope.
3. Any remaining empirical, production, target-hardware, or operating obligation is represented by separate actionable post-wave work.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_w21_weekly_mlops.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tools/validate_w21_mlops.py` — Run and retain the result when this issue touches the covered contract.

## Required Evidence

- Authoritative WBS row TASK-147
- Existing artifact `data refresh workflow`

## Completion Evidence Contract

```json
{}
```

## End-to-End Validation Requirement

Historical completion remains scoped; integrated product completion is evaluated only through the post-wave release path.

## Expected Maturity After Completion

`INTEGRATED`

## Risk / Failure Conditions

- Original DONE status may be over-interpreted
- Source output path may have moved or been generated under a different canonical directory

## Stop Conditions

- Stop if completing this record would fabricate real-data, model-metric, source-rights, target-hardware, or operating evidence.

## Source References

- SRCREF-00180
- SRCREF-02116
- SRCREF-02117

## AI Context Notes

- This is historical WBS provenance. Execute the mapped post-wave issue for remaining maturity work.
- Completed W21 functional-starter scope with executable orchestration/replay evidence.
