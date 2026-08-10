<!-- GENERATED VIEW. Canonical record: jira/records/issues/tasks/TASK-154_implement_a_and_m_forecast_dashboard_starter.json -->
# TASK-154 — [TASK-154] Implement A&M forecast dashboard starter

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-033",
    "AC-055",
    "AC-056"
  ],
  "acceptance_criteria": [
    "Stable ID TASK-154, parent EPIC-027, owner wave W22, and original status DONE are preserved.",
    "Declared outputs are traceable to existing repository artifacts where resolvable, or remain recorded as historical output names without fabricating files.",
    "Requirement, acceptance-control, and dependency references resolve to authoritative registries.",
    "The record does not claim maturity beyond the task's original design, contract, functional-starter, synthetic-validation, or integration scope."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "This is historical WBS provenance. Execute the mapped post-wave issue for remaining maturity work.",
    "Completed W22 functional snapshot-serving/product starter with executable tests"
  ],
  "allowed_modification_paths": [
    "A&M dashboard"
  ],
  "blocked_reason": "",
  "blocks": [
    "TASK-155"
  ],
  "canonical_record": "jira/records/issues/tasks/TASK-154_implement_a_and_m_forecast_dashboard_starter.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {},
  "component": "serving-product",
  "components_expected_to_be_touched": [
    "serving-product"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The original historical scope and status are preserved with source evidence and stable identifiers.",
    "The record does not claim production maturity beyond the original design, contract, starter, integration, or validation scope.",
    "Any remaining empirical, production, target-hardware, or operating obligation is represented by separate actionable post-wave work."
  ],
  "dependencies": [
    "TASK-115",
    "TASK-145",
    "TASK-152",
    "TASK-153"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 3,
    "adr_ids": 0,
    "gap_ids": 0,
    "requirement_ids": 4,
    "risk_ids": 0
  },
  "effective_traceability_total": 7,
  "end_to_end_validation": "Historical completion remains scoped; integrated product completion is evaluated only through the post-wave release path.",
  "epic_id": "EPIC-027",
  "evidence_manifest_path": "",
  "evidence_state": "VERIFIED",
  "execution_lane": "SOLO_WORKTREE",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "INTEGRATED",
  "expected_outputs": [
    "A&M dashboard"
  ],
  "files_expected_to_be_read": [
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "governance/REQUIREMENTS_INDEX.csv"
  ],
  "files_expected_to_be_touched": [
    "A&M dashboard"
  ],
  "files_to_inspect": [
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "governance/REQUIREMENTS_INDEX.csv"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/tasks/TASK-154_implement_a_and_m_forecast_dashboard_starter.md",
  "governance_review_required": false,
  "governance_traceability_gate": "",
  "historical_classification": "HISTORICAL_SCOPED_COMPLETED",
  "import_id": 100257,
  "in_scope": [
    "Original WBS objective and outputs",
    "Original requirements and acceptance-control mappings",
    "Original dependency and execution-lane provenance"
  ],
  "issue_type": "Task",
  "jira_key": "BAT-257",
  "labels": [
    "historical",
    "implementation",
    "planning-program",
    "w22",
    "wave-completed"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "TASK-154",
  "maturity_before": "DESIGN_ONLY",
  "objective": "Implement A&M forecast dashboard starter",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24397",
    "jira_updated_at": "2026-08-09T00:40:45.442-0500",
    "last_synced_at": "2026-08-10T04:24:34.496382+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-516-openai-foundation-complete\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Reopening completed planning solely to rename it",
    "Treating a starter/design result as empirically validated production capability"
  ],
  "owner_wave": "W22",
  "parent_id": "EPIC-027",
  "phase": "PHASE-4",
  "prerequisites": [
    "Historical dependency TASK-152",
    "Historical dependency TASK-153",
    "Historical dependency TASK-115",
    "Historical dependency TASK-145"
  ],
  "primary_source_refs": [
    "SRCREF-00187",
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
    "POST-SUBTASK-123"
  ],
  "required_evidence": [
    "Authoritative WBS row TASK-154",
    "Existing artifact `A&M dashboard`"
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_w22_product_serving.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tools/validate_w22_product.py"
    }
  ],
  "requirement_ids": [
    "REQ-122",
    "REQ-232",
    "REQ-233",
    "REQ-725"
  ],
  "risk_failure_conditions": [
    "Original DONE status may be over-interpreted",
    "Source output path may have moved or been generated under a different canonical directory"
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Original task type IMPLEMENTATION with mutation scope: as defined by its source documents.",
  "source_ids": [
    "TASK-154"
  ],
  "source_refs": [
    "SRCREF-00187",
    "SRCREF-02116",
    "SRCREF-02117"
  ],
  "specificity_fingerprint": "c49d27004ce66c5fde92a4629f12a9b148b5bca52f2d507dc596e4e1ce30a5d6",
  "stop_conditions": [
    "Stop if completing this record would fabricate real-data, model-metric, source-rights, target-hardware, or operating evidence."
  ],
  "supporting_source_refs": [],
  "title": "[TASK-154] Implement A&M forecast dashboard starter",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT",
  "unblock_condition": "",
  "validation_classes": [
    "EXISTING_AUTOMATED_TEST"
  ],
  "why_this_exists": "Preserve the original W22 WBS work unit, its dependencies, outputs, and scoped completion semantics as provenance for post-wave execution.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Implement A&M forecast dashboard starter

## Why This Exists

Preserve the original W22 WBS work unit, its dependencies, outputs, and scoped completion semantics as provenance for post-wave execution.

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

- Historical dependency TASK-152
- Historical dependency TASK-153
- Historical dependency TASK-115
- Historical dependency TASK-145

## Hard Dependencies

- TASK-115
- TASK-145
- TASK-152
- TASK-153

## Blocks

- TASK-155

## Read / Inspect First

- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/IMPLEMENTATION_WBS.csv
- governance/REQUIREMENTS_INDEX.csv

## Files Expected To Be Modified

- A&M dashboard

## Components Expected To Be Touched

- serving-product

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

- A&M dashboard

## Direct Requirements

- REQ-122
- REQ-232
- REQ-233
- REQ-725

## Direct Acceptance Controls

- AC-033
- AC-055
- AC-056

## Governance Traceability Inheritance

- Gate: `None`
- Inherited from: None
- Resolution: `DIRECT`
- Effective counts: `{"acceptance_control_ids": 3, "adr_ids": 0, "gap_ids": 0, "requirement_ids": 4, "risk_ids": 0}`

## Acceptance Criteria

1. Stable ID TASK-154, parent EPIC-027, owner wave W22, and original status DONE are preserved.
2. Declared outputs are traceable to existing repository artifacts where resolvable, or remain recorded as historical output names without fabricating files.
3. Requirement, acceptance-control, and dependency references resolve to authoritative registries.
4. The record does not claim maturity beyond the task's original design, contract, functional-starter, synthetic-validation, or integration scope.

## Definition of Done

1. The original historical scope and status are preserved with source evidence and stable identifiers.
2. The record does not claim production maturity beyond the original design, contract, starter, integration, or validation scope.
3. Any remaining empirical, production, target-hardware, or operating obligation is represented by separate actionable post-wave work.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_w22_product_serving.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tools/validate_w22_product.py` — Run and retain the result when this issue touches the covered contract.

## Required Evidence

- Authoritative WBS row TASK-154
- Existing artifact `A&M dashboard`

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

- SRCREF-00187
- SRCREF-02116
- SRCREF-02117

## AI Context Notes

- This is historical WBS provenance. Execute the mapped post-wave issue for remaining maturity work.
- Completed W22 functional snapshot-serving/product starter with executable tests
