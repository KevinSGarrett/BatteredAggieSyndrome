<!-- GENERATED VIEW. Canonical record: jira/records/issues/epics/EPIC-005_feature_engineering_and_lifecycle.json -->
# EPIC-005 — [EPIC-005] Feature engineering and lifecycle

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "The epic retains stable ID EPIC-005, owner wave W10, phase PHASE-1, and all authoritative WBS children.",
    "The workflow state represents original scoped completion/open state only and is not interpreted as empirical product completion.",
    "Any remaining real-data, model, validation, hardware, operational, conditional, or deferred obligation is represented in post-wave issues and traceability indexes."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Do not execute this Epic as new work; select an actionable post-wave Subtask instead.",
    "DONE means the original scoped planning/design/starter work completed, not that the final product is operating."
  ],
  "allowed_modification_paths": [
    "governance/EPIC_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv"
  ],
  "blocked_reason": "",
  "blocks": [],
  "canonical_record": "jira/records/issues/epics/EPIC-005_feature_engineering_and_lifecycle.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {},
  "component": "validation-promotion",
  "components_expected_to_be_touched": [
    "validation-promotion"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "The original historical scope and status are preserved with source evidence and stable identifiers.",
    "The record does not claim production maturity beyond the original design, contract, starter, integration, or validation scope.",
    "Any remaining empirical, production, target-hardware, or operating obligation is represented by separate actionable post-wave work."
  ],
  "dependencies": [],
  "effective_traceability_counts": {
    "acceptance_control_ids": 0,
    "adr_ids": 0,
    "gap_ids": 0,
    "requirement_ids": 0,
    "risk_ids": 0
  },
  "effective_traceability_total": 0,
  "end_to_end_validation": "Historical traceability is complete only when every child and every remaining maturity obligation has an explicit disposition.",
  "epic_id": "",
  "evidence_manifest_path": "",
  "evidence_state": "VERIFIED",
  "execution_lane": "SHARED_CONTRACT",
  "execution_mode": "HISTORICAL_REFERENCE",
  "expected_maturity_after_completion": "CONTRACT_DEFINED",
  "expected_outputs": [
    "CORE/SUPPORTED/CONDITIONAL/EXPERIMENTAL/REJECTED/BANNED transitions",
    "approved feature lifecycle contract and evidence rules",
    "family ablation/stability evidence",
    "feature transform library/contracts",
    "opponent/matchup transform interfaces",
    "screening reports",
    "selection evidence"
  ],
  "files_expected_to_be_read": [
    "governance/EPIC_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv"
  ],
  "files_expected_to_be_touched": [
    "governance/EPIC_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv"
  ],
  "files_to_inspect": [
    "governance/EPIC_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/epics/EPIC-005_feature_engineering_and_lifecycle.md",
  "governance_review_required": false,
  "governance_traceability_gate": "",
  "historical_classification": "HISTORICAL_SCOPED_COMPLETED",
  "import_id": 100005,
  "in_scope": [
    "Original planning/design/starter work",
    "Stable source IDs and child traceability",
    "Scoped historical completion evidence"
  ],
  "issue_type": "Epic",
  "jira_key": "BAT-5",
  "labels": [
    "historical",
    "planning-program",
    "w10",
    "wave-completed"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "EPIC-005",
  "maturity_before": "CONTRACT_DEFINED",
  "objective": "Create PIT-safe transforms, screening, ablation and promotion/demotion workflow.",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24145",
    "jira_updated_at": "2026-08-09T00:40:10.370-0500",
    "last_synced_at": "2026-08-11T07:25:49.170544+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\POST-SUBTASK-178-wmt-known-at\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Claiming real-data, protected-evaluation, production-ready, or operating maturity unless separately evidenced",
    "Creating a Wave 26"
  ],
  "owner_wave": "W10",
  "parent_id": "",
  "phase": "PHASE-1",
  "prerequisites": [],
  "primary_source_refs": [
    "SRCREF-00005",
    "SRCREF-01965"
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
    "governance/EPIC_CATALOG.csv",
    "governance/IMPLEMENTATION_WBS.csv"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [
    "POST-SUBTASK-105"
  ],
  "required_evidence": [],
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
  "requirement_ids": [],
  "risk_failure_conditions": [
    "Historical status could be misread as product completion",
    "Stale catalog status could outrank final handoff if source authority is ignored"
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Historical epic scope exactly as represented by the authoritative Epic Catalog and its WBS children.",
  "source_ids": [
    "EPIC-005"
  ],
  "source_refs": [
    "SRCREF-00005",
    "SRCREF-01965"
  ],
  "specificity_fingerprint": "abce255b5175a185f77cd9936abd3e82c27c4968cb62deb59bc62d807cd46f30",
  "stop_conditions": [
    "Stop if a proposed update renumbers the historical epic or rewrites its original wave provenance."
  ],
  "supporting_source_refs": [],
  "title": "[EPIC-005] Feature engineering and lifecycle",
  "traceability_inherited_from": [],
  "traceability_resolution": "DIRECT",
  "unblock_condition": "",
  "validation_classes": [
    "EXISTING_AUTOMATED_TEST"
  ],
  "why_this_exists": "Preserve the authoritative 25-wave planning/design capability and its original scoped status without claiming that empirical production maturity was achieved.",
  "work_packet_path": "",
  "workflow_state": "DONE"
}
```

## Objective

Create PIT-safe transforms, screening, ablation and promotion/demotion workflow.

## Why This Exists

Preserve the authoritative 25-wave planning/design capability and its original scoped status without claiming that empirical production maturity was achieved.

## Scope

Historical epic scope exactly as represented by the authoritative Epic Catalog and its WBS children.

### Explicit In Scope

- Original planning/design/starter work
- Stable source IDs and child traceability
- Scoped historical completion evidence

### Explicit Out of Scope

- Claiming real-data, protected-evaluation, production-ready, or operating maturity unless separately evidenced
- Creating a Wave 26

## Prerequisites

- None.

## Hard Dependencies

- None.

## Blocks

- None.

## Read / Inspect First

- governance/EPIC_CATALOG.csv
- governance/IMPLEMENTATION_WBS.csv

## Files Expected To Be Modified

- governance/EPIC_CATALOG.csv
- governance/IMPLEMENTATION_WBS.csv

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
- approved feature lifecycle contract and evidence rules
- family ablation/stability evidence
- feature transform library/contracts
- opponent/matchup transform interfaces
- screening reports
- selection evidence

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `None`
- Inherited from: None
- Resolution: `DIRECT`
- Effective counts: `{"acceptance_control_ids": 0, "adr_ids": 0, "gap_ids": 0, "requirement_ids": 0, "risk_ids": 0}`

## Acceptance Criteria

1. The epic retains stable ID EPIC-005, owner wave W10, phase PHASE-1, and all authoritative WBS children.
2. The workflow state represents original scoped completion/open state only and is not interpreted as empirical product completion.
3. Any remaining real-data, model, validation, hardware, operational, conditional, or deferred obligation is represented in post-wave issues and traceability indexes.

## Definition of Done

1. The original historical scope and status are preserved with source evidence and stable identifiers.
2. The record does not claim production maturity beyond the original design, contract, starter, integration, or validation scope.
3. Any remaining empirical, production, target-hardware, or operating obligation is represented by separate actionable post-wave work.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_validation_science_governance.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tests/test_w25_final_handoff.py` — Run and retain the result when this issue touches the covered contract.
- **EXISTING_AUTOMATED_TEST** / `EXISTING_AUTOMATED_TEST` — `tools/validate_validation_science.py` — Run and retain the result when this issue touches the covered contract.

## Required Evidence

- None.

## Completion Evidence Contract

```json
{}
```

## End-to-End Validation Requirement

Historical traceability is complete only when every child and every remaining maturity obligation has an explicit disposition.

## Expected Maturity After Completion

`CONTRACT_DEFINED`

## Risk / Failure Conditions

- Historical status could be misread as product completion
- Stale catalog status could outrank final handoff if source authority is ignored

## Stop Conditions

- Stop if a proposed update renumbers the historical epic or rewrites its original wave provenance.

## Source References

- SRCREF-00005
- SRCREF-01965

## AI Context Notes

- Do not execute this Epic as new work; select an actionable post-wave Subtask instead.
- DONE means the original scoped planning/design/starter work completed, not that the final product is operating.
