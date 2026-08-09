<!-- GENERATED VIEW. Canonical record: jira/records/issues/tasks/TASK-168_promote_or_reject_advanced_challengers_via_unchanged_w17_gate.json -->
# TASK-168 — [TASK-168] Promote or reject advanced challengers via unchanged W17 gate

## Canonical metadata

```json
{
  "acceptance_control_ids": [
    "AC-023",
    "AC-055",
    "AC-056"
  ],
  "acceptance_criteria": [
    "Stable ID TASK-168, parent EPIC-029, owner wave W18+, and original status PLANNED are preserved.",
    "Declared outputs are traceable to existing repository artifacts where resolvable, or remain recorded as historical output names without fabricating files.",
    "Requirement, acceptance-control, and dependency references resolve to authoritative registries.",
    "The record does not claim maturity beyond the task's original design, contract, functional-starter, synthetic-validation, or integration scope."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "This is historical WBS provenance. Execute the mapped post-wave issue for remaining maturity work.",
    "No additional historical note."
  ],
  "allowed_modification_paths": [
    "advanced challenger promotion/rejection record"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/tasks/TASK-168_promote_or_reject_advanced_challengers_via_unchanged_w17_gate.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {},
  "component": "advanced-challengers",
  "components_expected_to_be_touched": [
    "advanced-challengers"
  ],
  "content_contract_version": "2.0",
  "critical_path": false,
  "definition_of_done": [
    "The original historical scope and status are preserved with source evidence and stable identifiers.",
    "The record does not claim production maturity beyond the original design, contract, starter, integration, or validation scope.",
    "Any remaining empirical, production, target-hardware, or operating obligation is represented by separate actionable post-wave work."
  ],
  "dependencies": [
    "TASK-165",
    "TASK-166",
    "TASK-167"
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
  "epic_id": "EPIC-029",
  "evidence_manifest_path": "",
  "evidence_state": "PLANNED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "FUNCTIONAL_STARTER",
  "expected_outputs": [
    "advanced challenger promotion/rejection record"
  ],
  "files_expected_to_be_read": [
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "governance/REQUIREMENTS_INDEX.csv"
  ],
  "files_expected_to_be_touched": [
    "advanced challenger promotion/rejection record"
  ],
  "files_to_inspect": [
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "governance/REQUIREMENTS_INDEX.csv"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/tasks/TASK-168_promote_or_reject_advanced_challengers_via_unchanged_w17_gate.md",
  "governance_review_required": false,
  "governance_traceability_gate": "",
  "historical_classification": "HISTORICAL_OPEN_OR_DEFERRED",
  "import_id": 100271,
  "in_scope": [
    "Original WBS objective and outputs",
    "Original requirements and acceptance-control mappings",
    "Original dependency and execution-lane provenance"
  ],
  "issue_type": "Task",
  "jira_key": "BAT-278",
  "labels": [
    "gate",
    "historical",
    "historical-open",
    "planning-program",
    "w18"
  ],
  "last_content_audit": "2026-08-08",
  "local_id": "TASK-168",
  "maturity_before": "DESIGN_ONLY",
  "objective": "Promote or reject advanced challengers via unchanged W17 gate",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24418",
    "jira_updated_at": "2026-08-09T00:05:14.553-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Reopening completed planning solely to rename it",
    "Treating a starter/design result as empirically validated production capability"
  ],
  "owner_wave": "W18+",
  "parent_id": "EPIC-029",
  "phase": "PHASE-5",
  "prerequisites": [
    "Historical dependency TASK-165",
    "Historical dependency TASK-166",
    "Historical dependency TASK-167"
  ],
  "primary_source_refs": [
    "SRCREF-00201",
    "SRCREF-02116",
    "SRCREF-02117"
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
    "governance/ACCEPTANCE_CONTROL_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv",
    "governance/REQUIREMENTS_INDEX.csv"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [
    "POST-SUBTASK-150"
  ],
  "required_evidence": [
    "Authoritative WBS row TASK-168",
    "Existing artifact `advanced challenger promotion/rejection record`"
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tests/test_advanced_challenger_full.py"
    },
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run and retain the result when this issue touches the covered contract.",
      "path": "tools/check_advanced_challenger_admission.py"
    }
  ],
  "requirement_ids": [
    "REQ-108",
    "REQ-232",
    "REQ-233"
  ],
  "risk_failure_conditions": [
    "Original DONE status may be over-interpreted",
    "Source output path may have moved or been generated under a different canonical directory"
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Original task type GATE with mutation scope: as defined by its source documents.",
  "source_ids": [
    "TASK-168"
  ],
  "source_refs": [
    "SRCREF-00201",
    "SRCREF-02116",
    "SRCREF-02117"
  ],
  "specificity_fingerprint": "afeb15cc9041bbfe58a0870d91feb5acd2e028e98cbd466ff6ccf09c480f584a",
  "stop_conditions": [
    "Stop if completing this record would fabricate real-data, model-metric, source-rights, target-hardware, or operating evidence."
  ],
  "supporting_source_refs": [],
  "title": "[TASK-168] Promote or reject advanced challengers via unchanged W17 gate",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT",
  "unblock_condition": "",
  "validation_classes": [
    "EXISTING_AUTOMATED_TEST"
  ],
  "why_this_exists": "Preserve the original W18+ WBS work unit, its dependencies, outputs, and scoped completion semantics as provenance for post-wave execution.",
  "work_packet_path": "",
  "workflow_state": "DEFERRED"
}
```

## Objective

Promote or reject advanced challengers via unchanged W17 gate

## Why This Exists

Preserve the original W18+ WBS work unit, its dependencies, outputs, and scoped completion semantics as provenance for post-wave execution.

## Scope

Original task type GATE with mutation scope: as defined by its source documents.

### Explicit In Scope

- Original WBS objective and outputs
- Original requirements and acceptance-control mappings
- Original dependency and execution-lane provenance

### Explicit Out of Scope

- Reopening completed planning solely to rename it
- Treating a starter/design result as empirically validated production capability

## Prerequisites

- Historical dependency TASK-165
- Historical dependency TASK-166
- Historical dependency TASK-167

## Hard Dependencies

- TASK-165
- TASK-166
- TASK-167

## Blocks

- None.

## Read / Inspect First

- governance/ACCEPTANCE_CONTROL_CATALOG.csv
- governance/IMPLEMENTATION_WBS.csv
- governance/REQUIREMENTS_INDEX.csv

## Files Expected To Be Modified

- advanced challenger promotion/rejection record

## Components Expected To Be Touched

- advanced-challengers

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

- advanced challenger promotion/rejection record

## Direct Requirements

- REQ-108
- REQ-232
- REQ-233

## Direct Acceptance Controls

- AC-023
- AC-055
- AC-056

## Governance Traceability Inheritance

- Gate: `None`
- Inherited from: None
- Resolution: `DIRECT`
- Effective counts: `{"acceptance_control_ids": 3, "adr_ids": 0, "gap_ids": 0, "requirement_ids": 3, "risk_ids": 0}`

## Acceptance Criteria

1. Stable ID TASK-168, parent EPIC-029, owner wave W18+, and original status PLANNED are preserved.
2. Declared outputs are traceable to existing repository artifacts where resolvable, or remain recorded as historical output names without fabricating files.
3. Requirement, acceptance-control, and dependency references resolve to authoritative registries.
4. The record does not claim maturity beyond the task's original design, contract, functional-starter, synthetic-validation, or integration scope.

## Definition of Done

1. The original historical scope and status are preserved with source evidence and stable identifiers.
2. The record does not claim production maturity beyond the original design, contract, starter, integration, or validation scope.
3. Any remaining empirical, production, target-hardware, or operating obligation is represented by separate actionable post-wave work.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_advanced_challenger_full.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tools/check_advanced_challenger_admission.py` — Run and retain the result when this issue touches the covered contract.

## Required Evidence

- Authoritative WBS row TASK-168
- Existing artifact `advanced challenger promotion/rejection record`

## Completion Evidence Contract

```json
{}
```

## End-to-End Validation Requirement

Historical completion remains scoped; integrated product completion is evaluated only through the post-wave release path.

## Expected Maturity After Completion

`FUNCTIONAL_STARTER`

## Risk / Failure Conditions

- Original DONE status may be over-interpreted
- Source output path may have moved or been generated under a different canonical directory

## Stop Conditions

- Stop if completing this record would fabricate real-data, model-metric, source-rights, target-hardware, or operating evidence.

## Source References

- SRCREF-00201
- SRCREF-02116
- SRCREF-02117

## AI Context Notes

- This is historical WBS provenance. Execute the mapped post-wave issue for remaining maturity work.
- No additional historical note.
